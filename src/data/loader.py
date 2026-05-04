"""
SAFERIDE — 데이터 로딩 및 병합 파이프라인 (2단계)
=======================================================
지원 데이터 소스:
  1. TAAS 교통사고 통계 CSV
  2. 기상청 초단기실황 API (JSON 캐시 또는 실시간 요청)
  3. 행안부 생활인구 CSV (격자별 시간대별)
  4. osmnx 서울 도로망

엣지 케이스 처리:
  - TAAS  : 인코딩 자동 감지, 좌표 범위 검증, 중복 제거
  - 기상  : API Rate Limit 지수 백오프, 결측 카테고리 보간
  - 생활인구: 격자 결측 시간대 전방/후방 채우기, 음수 보정
  - osmnx : 로컬 캐시 우선 로드, 타임아웃 재시도
  - 병합  : 타임존 정규화, 격자 미배정 사고점 좌표 snap
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional, Tuple

import geopandas as gpd
import numpy as np
import osmnx as ox
import pandas as pd
import requests

# ---------------------------------------------------------------------------
# 로거 설정
# ---------------------------------------------------------------------------
log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------
# 한국 위경도 유효 범위 (제주 포함)
_KR_LAT = (33.0, 38.9)
_KR_LON = (124.5, 132.0)

# 기상청 초단기실황 유효 카테고리
_WEATHER_CATS = {
    "T1H": "temp",       # 기온 (°C)
    "RN1": "rain",       # 1시간 강수량 (mm)
    "WSD": "wind",       # 풍속 (m/s)
    "REH": "humidity",   # 습도 (%)
    "PTY": "precip_type",# 강수형태 (0=없음,1=비,2=비/눈,3=눈)
    "VVV": "visibility", # 가시거리 (10m 단위) — 없을 수 있음
}

# 기상청 API 베이스 URL
_KMA_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"


# ===========================================================================
# 1. TAAS 교통사고 통계
# ===========================================================================

def load_taas(path: str = "data/raw/taas.csv") -> pd.DataFrame:
    """
    TAAS CSV 로드 → PM(개인형 이동장치) 사고만 반환.

    엣지 케이스:
      - cp949/utf-8/euc-kr 인코딩 자동 탐지
      - 좌표 범위 이상값 제거 (한국 영역 밖)
      - 동일 시각·동일 좌표 중복 행 제거
      - 날짜 파싱 실패 행 경고 후 제거
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"TAAS 파일 없음: {p.resolve()}")

    # 인코딩 자동 탐지 (cp949 → utf-8-sig → utf-8 순 시도)
    df: Optional[pd.DataFrame] = None
    for enc in ("cp949", "utf-8-sig", "utf-8", "euc-kr"):
        try:
            df = pd.read_csv(path, encoding=enc, low_memory=False)
            log.info("TAAS 로드 성공 (인코딩=%s, 행=%d)", enc, len(df))
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if df is None:
        raise ValueError("TAAS CSV 인코딩을 감지할 수 없습니다.")

    # ── 날짜 파싱 ──────────────────────────────────────────────────────────
    # "사고일시" 컬럼이 없으면 대안 컬럼 탐색
    dt_col = next(
        (c for c in df.columns if "일시" in c or "datetime" in c.lower()),
        None,
    )
    if dt_col is None:
        raise KeyError("날짜 컬럼을 찾을 수 없습니다. TAAS CSV 헤더를 확인하세요.")

    before = len(df)
    df["datetime"] = pd.to_datetime(df[dt_col], errors="coerce")
    invalid_dt = df["datetime"].isna().sum()
    if invalid_dt:
        log.warning("날짜 파싱 실패 %d행 제거", invalid_dt)
    df = df.dropna(subset=["datetime"])

    # ── PM 사고 필터 ───────────────────────────────────────────────────────
    # "사고유형대분류" 컬럼이 없으면 전체 반환하고 경고
    type_col = next((c for c in df.columns if "사고유형" in c), None)
    if type_col:
        pm_mask = df[type_col].str.contains("개인형이동장치|전동킥보드|PM", na=False)
        df = df[pm_mask]
        log.info("PM 사고 필터 후 행=%d (전체=%d)", len(df), before)
    else:
        log.warning("'사고유형' 컬럼 없음 — 전체 사고 데이터 사용")

    # ── 좌표 컬럼 탐지 ────────────────────────────────────────────────────
    lat_col = next((c for c in df.columns if "위도" in c or c.lower() == "lat"), None)
    lon_col = next((c for c in df.columns if "경도" in c or c.lower() == "lon"), None)
    if lat_col is None or lon_col is None:
        raise KeyError("위도/경도 컬럼을 찾을 수 없습니다.")

    df = df.rename(columns={lat_col: "lat", lon_col: "lon"})
    df[["lat", "lon"]] = df[["lat", "lon"]].apply(pd.to_numeric, errors="coerce")

    # 한국 영역 밖 좌표 제거
    valid_coord = (
        df["lat"].between(*_KR_LAT) & df["lon"].between(*_KR_LON)
    )
    n_invalid = (~valid_coord).sum()
    if n_invalid:
        log.warning("좌표 범위 이상 %d행 제거 (lat=%s, lon=%s)", n_invalid, _KR_LAT, _KR_LON)
    df = df[valid_coord]

    # ── 중복 제거 (동일 시각 + 동일 위경도) ───────────────────────────────
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["datetime", "lat", "lon"])
    if len(df) < before_dedup:
        log.info("중복 제거: %d행 → %d행", before_dedup, len(df))

    # ── 사상자 수 결측 → 0 채우기 ─────────────────────────────────────────
    for col in ["사망자수", "부상자수"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    output_cols = ["datetime", "lat", "lon"]
    for col in ["사망자수", "부상자수"]:
        if col in df.columns:
            output_cols.append(col)

    return df[output_cols].reset_index(drop=True)


# ===========================================================================
# 2. 기상청 초단기실황 API
# ===========================================================================

def _round_base_time(dt: pd.Timestamp) -> str:
    """
    기상청 API 유효 베이스 타임으로 내림 (매 정시 발표).
    예: 09:34 → '0900'
    """
    # 초단기실황은 매 시각 30분 후 발표 → 현재 시각 기준 직전 정시
    return f"{dt.hour:02d}00"


def fetch_weather_api(
    api_key: str,
    nx: int,
    ny: int,
    date: str,          # "20240501" 형식
    base_time: str,     # "0900" 형식
    max_retries: int = 5,
    base_wait: float = 1.0,
) -> list[dict]:
    """
    기상청 초단기실황 API 단건 호출.

    엣지 케이스:
      - HTTP 429 / resultCode "03" (일일 트래픽 초과) → 지수 백오프 재시도
      - 응답 items 가 null 이거나 리스트가 비어있으면 빈 리스트 반환
      - 네트워크 타임아웃 (10초) 재시도
    """
    params = {
        "serviceKey": api_key,
        "pageNo": 1,
        "numOfRows": 100,
        "dataType": "JSON",
        "base_date": date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(_KMA_URL, params=params, timeout=10)

            # HTTP 레벨 Rate Limit
            if resp.status_code == 429:
                wait = base_wait * (2 ** attempt)
                log.warning("HTTP 429 — %ds 후 재시도 (%d/%d)", wait, attempt, max_retries)
                time.sleep(wait)
                continue

            resp.raise_for_status()
            body = resp.json().get("response", {}).get("body", {})
            result_code = resp.json()["response"]["header"].get("resultCode", "00")

            # API 레벨 오류 코드 처리
            if result_code == "03":
                # 일일 트래픽 초과
                wait = base_wait * (2 ** attempt)
                log.warning("API 트래픽 초과(03) — %ds 후 재시도", wait)
                time.sleep(wait)
                continue
            elif result_code not in ("00", "0000"):
                log.error("API 오류 코드: %s", result_code)
                return []

            items = body.get("items")
            if not items:
                return []
            item_list = items.get("item", [])
            # items.item 이 단건일 때 dict로 올 수 있음
            if isinstance(item_list, dict):
                item_list = [item_list]
            return item_list

        except requests.exceptions.Timeout:
            wait = base_wait * (2 ** attempt)
            log.warning("타임아웃 — %ds 후 재시도 (%d/%d)", wait, attempt, max_retries)
            time.sleep(wait)
        except requests.exceptions.RequestException as e:
            log.error("요청 오류: %s", e)
            return []

    log.error("최대 재시도 초과: nx=%d ny=%d %s %s", nx, ny, date, base_time)
    return []


def load_weather(path: str = "data/raw/weather.json") -> pd.DataFrame:
    """
    기상청 API 응답 JSON 캐시 파일 로드 → 정제된 기상 DataFrame 반환.

    엣지 케이스:
      - JSON 경로 구조 다를 때 (items 직접 리스트인 경우) 자동 탐지
      - 존재하지 않는 카테고리 → NaN 유지 후 forward-fill 보간
      - obsrValue 가 "강수없음" 등 문자열 → 0 변환
      - 동일 datetime 중복 → 첫 번째 값 유지
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"기상 JSON 없음: {p.resolve()}")

    raw = json.loads(p.read_text(encoding="utf-8"))

    # JSON 구조 탐지: 표준 API 응답 or 직접 리스트
    if isinstance(raw, list):
        items = raw
    else:
        try:
            items = raw["response"]["body"]["items"]["item"]
        except (KeyError, TypeError):
            # 일부 저장 형식: {"items": [...]}
            items = raw.get("items", raw.get("item", []))

    if not items:
        raise ValueError("기상 JSON에 관측 데이터가 없습니다.")

    df = pd.DataFrame(items)

    # datetime 생성 — baseDate+baseTime or fcstDate+fcstTime 모두 처리
    if "baseDate" in df.columns and "baseTime" in df.columns:
        date_col, time_col = "baseDate", "baseTime"
    elif "fcstDate" in df.columns and "fcstTime" in df.columns:
        date_col, time_col = "fcstDate", "fcstTime"
    else:
        raise KeyError("날짜/시각 컬럼(baseDate 등)을 찾을 수 없습니다.")

    df["datetime"] = pd.to_datetime(
        df[date_col].astype(str) + df[time_col].astype(str).str.zfill(4),
        format="%Y%m%d%H%M",
        errors="coerce",
    )
    df = df.dropna(subset=["datetime"])

    # obsrValue 정제: 문자열 → 숫자 변환
    # "강수없음", "1mm 미만" 같은 값 → 0
    def _parse_value(v: str) -> float:
        v = str(v).strip()
        if any(k in v for k in ("없음", "미만", "-")):
            return 0.0
        try:
            return float(v)
        except ValueError:
            return np.nan

    df["obsrValue"] = df["obsrValue"].apply(_parse_value)

    # category 컬럼이 없으면 종료
    if "category" not in df.columns:
        raise KeyError("'category' 컬럼이 없습니다.")

    # 유효 카테고리만 유지
    df = df[df["category"].isin(_WEATHER_CATS.keys())]

    # 피벗: datetime × category
    pivot = df.pivot_table(
        index="datetime",
        columns="category",
        values="obsrValue",
        aggfunc="first",  # 중복 시 첫 번째 값
    ).reset_index()
    pivot.columns.name = None  # MultiIndex 이름 제거

    # 표준 컬럼명으로 rename (없는 컬럼은 무시)
    pivot = pivot.rename(columns=_WEATHER_CATS)

    # 누락된 필수 컬럼 → NaN 컬럼으로 추가
    for std_name in _WEATHER_CATS.values():
        if std_name not in pivot.columns:
            log.warning("기상 카테고리 '%s' 누락 — NaN 컬럼 추가", std_name)
            pivot[std_name] = np.nan

    # 시계열 정렬 후 결측 보간
    pivot = pivot.sort_values("datetime").reset_index(drop=True)
    numeric_cols = [c for c in _WEATHER_CATS.values() if c in pivot.columns]
    # 1) 전방 채우기(최대 2시간), 2) 후방 채우기로 나머지 처리
    pivot[numeric_cols] = (
        pivot[numeric_cols]
        .ffill(limit=2)
        .bfill(limit=2)
    )

    log.info("기상 데이터 로드 완료: %d 타임스텝", len(pivot))
    return pivot


# ===========================================================================
# 3. 행안부 생활인구 CSV
# ===========================================================================

def load_population(path: str = "data/raw/population.csv") -> pd.DataFrame:
    """
    행안부 생활인구 CSV 로드 → (grid_id, datetime, population) 반환.

    엣지 케이스:
      - 격자 ID 컬럼명 다양 (격자ID / GRID_ID / grid_id)
      - 인구 수 음수·비정상값 → 0으로 클리핑
      - 격자별 시간 구멍(gap) → 0으로 채우기 (PM 활동 없는 시간)
      - 중복 (grid_id, datetime) → 합산
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"생활인구 파일 없음: {p.resolve()}")

    for enc in ("cp949", "utf-8-sig", "utf-8"):
        try:
            df = pd.read_csv(path, encoding=enc, low_memory=False)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("생활인구 CSV 인코딩 감지 실패")

    # ── 컬럼명 정규화 ─────────────────────────────────────────────────────
    col_map: dict[str, str] = {}
    for c in df.columns:
        cl = c.strip()
        if any(k in cl for k in ("격자ID", "GRID_ID", "grid_id", "격자id")):
            col_map[c] = "grid_id"
        elif any(k in cl for k in ("기준일시", "datetime", "일시", "시각")):
            col_map[c] = "raw_dt"
        elif any(k in cl for k in ("총생활인구", "population", "인구수")):
            col_map[c] = "population"
    df = df.rename(columns=col_map)

    missing = [c for c in ("grid_id", "raw_dt", "population") if c not in df.columns]
    if missing:
        raise KeyError(f"필수 컬럼 없음: {missing}\n  현재 컬럼: {list(df.columns)}")

    # ── 타입 변환 ─────────────────────────────────────────────────────────
    df["datetime"]   = pd.to_datetime(df["raw_dt"], errors="coerce")
    df["population"] = pd.to_numeric(df["population"], errors="coerce")
    df = df.dropna(subset=["datetime", "grid_id"])

    # 인구 음수·이상값 보정
    df["population"] = df["population"].clip(lower=0).fillna(0).astype(int)

    # ── 중복 (grid_id, datetime) → 합산 ───────────────────────────────────
    before = len(df)
    df = (
        df.groupby(["grid_id", "datetime"], as_index=False)["population"]
        .sum()
    )
    if len(df) < before:
        log.info("생활인구 중복 집계: %d → %d행", before, len(df))

    # ── 시간 구멍 채우기: 격자별 누락 시간대 → 0 ──────────────────────────
    # 전체 시간 범위를 시간 단위로 생성 후 reindex
    dt_min, dt_max = df["datetime"].min(), df["datetime"].max()
    full_index = pd.date_range(dt_min, dt_max, freq="h")  # 1시간 단위
    grids = df["grid_id"].unique()

    # MultiIndex (grid_id × datetime) reindex
    df = df.set_index(["grid_id", "datetime"])
    full_mi = pd.MultiIndex.from_product(
        [grids, full_index], names=["grid_id", "datetime"]
    )
    df = df.reindex(full_mi, fill_value=0).reset_index()

    log.info("생활인구 로드 완료: %d 격자 × %d 타임스텝", len(grids), len(full_index))
    return df[["grid_id", "datetime", "population"]]


# ===========================================================================
# 4. osmnx 서울 도로망
# ===========================================================================

def load_road_graph(
    place: str = "Seoul, South Korea",
    cache_path: str = "data/interim/seoul_road_graph.graphml",
    network_type: str = "all",
) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    osmnx로 서울 도로망 로드 → (nodes, edges) GeoDataFrame 반환.

    엣지 케이스:
      - 로컬 GraphML 캐시 존재 시 네트워크 요청 생략
      - 다운로드 실패(타임아웃) → 재시도 3회
      - ox.settings로 캐시 디렉터리 설정
    """
    cache = Path(cache_path)

    if cache.exists():
        log.info("osmnx 캐시 로드: %s", cache)
        G = ox.load_graphml(cache)
    else:
        log.info("osmnx 다운로드 시작: %s", place)
        cache.parent.mkdir(parents=True, exist_ok=True)

        # 재시도 루프
        G = None
        for attempt in range(1, 4):
            try:
                G = ox.graph_from_place(place, network_type=network_type)
                ox.save_graphml(G, cache)
                log.info("도로망 저장: %s", cache)
                break
            except Exception as e:
                wait = 10 * attempt
                log.warning("다운로드 실패(%s) — %ds 후 재시도 (%d/3)", e, wait, attempt)
                time.sleep(wait)

        if G is None:
            raise RuntimeError("osmnx 도로망 다운로드 실패 (3회 재시도 초과)")

    nodes, edges = ox.graph_to_gdfs(G)

    # ── 도로 feature 정제 ─────────────────────────────────────────────────
    # lanes 컬럼: 리스트 또는 None → 첫 번째 값(숫자) 추출
    if "lanes" in edges.columns:
        edges["lanes"] = (
            edges["lanes"]
            .apply(lambda v: int(v[0]) if isinstance(v, list) else
                   (int(v) if pd.notna(v) else 1))
        )

    # 보도(sidewalk) 여부: footway / pedestrian 포함 여부
    if "highway" in edges.columns:
        edges["has_sidewalk"] = edges["highway"].apply(
            lambda v: int(
                any(k in str(v) for k in ("footway", "pedestrian", "path"))
            )
        )

    log.info("도로망 로드 완료: 노드=%d, 엣지=%d", len(nodes), len(edges))
    return nodes, edges


# ===========================================================================
# 5. 전체 병합 파이프라인
# ===========================================================================

def merge_all(
    taas: pd.DataFrame,
    weather: pd.DataFrame,
    population: pd.DataFrame,
    grid: gpd.GeoDataFrame,
    crs_proj: int = 5186,
) -> pd.DataFrame:
    """
    (grid_id, datetime) 단위로 TAAS + 기상 + 생활인구를 병합.

    Steps:
      1. 사고 포인트 → 격자 공간 조인 (격자 ID 할당)
      2. 기상 데이터 datetime 기준 left join
      3. 생활인구 (grid_id, datetime) 기준 left join
      4. 결측 보정

    Returns:
      (grid_id, datetime, lat, lon, ..., rain, temp, ..., population, ...) DataFrame
    """
    # ── 1) 사고 포인트 GeoDataFrame 생성 ──────────────────────────────────
    taas_gdf = gpd.GeoDataFrame(
        taas,
        geometry=gpd.points_from_xy(taas["lon"], taas["lat"]),
        crs="EPSG:4326",
    ).to_crs(epsg=crs_proj)

    grid_proj = grid.to_crs(epsg=crs_proj)

    # 공간 조인: 사고점이 속한 격자 ID 할당
    joined = gpd.sjoin(
        taas_gdf,
        grid_proj[["grid_id", "geometry"]],
        how="left",
        predicate="within",
    )

    # 격자 밖 사고(grid_id NaN) → 가장 가까운 격자로 snap
    unmatched = joined["grid_id"].isna()
    if unmatched.any():
        n = unmatched.sum()
        log.info("격자 미할당 사고 %d건 → nearest 격자로 snap", n)
        # nearest_grid_id 찾기
        unmatched_gdf = taas_gdf[unmatched.values]
        nearest_idx = grid_proj.sindex.nearest(
            unmatched_gdf.geometry, return_all=False
        )
        joined.loc[unmatched, "grid_id"] = grid_proj.iloc[nearest_idx]["grid_id"].values

    # GeoDataFrame → DataFrame
    df = pd.DataFrame(joined.drop(columns=["geometry", "index_right"], errors="ignore"))

    # datetime을 시간 단위로 truncate (분·초 제거 → 기상/인구와 키 통일)
    df["datetime"] = df["datetime"].dt.floor("h")

    # ── 2) 기상 데이터 병합 ────────────────────────────────────────────────
    weather["datetime"] = weather["datetime"].dt.floor("h")
    df = df.merge(weather, on="datetime", how="left")

    # 기상 결측 → 전방 채우기 (최대 3시간)
    weather_cols = list(_WEATHER_CATS.values())
    existing_w = [c for c in weather_cols if c in df.columns]
    df[existing_w] = df[existing_w].ffill(limit=3).bfill(limit=1)

    # ── 3) 생활인구 병합 ───────────────────────────────────────────────────
    population["datetime"] = population["datetime"].dt.floor("h")
    df = df.merge(population, on=["grid_id", "datetime"], how="left")
    # 인구 결측(해당 격자·시간 데이터 없음) → 0
    df["population"] = df["population"].fillna(0).astype(int)

    # ── 4) 최종 정리 ──────────────────────────────────────────────────────
    df = df.sort_values(["grid_id", "datetime"]).reset_index(drop=True)
    log.info(
        "병합 완료: %d행 | 격자=%d | 기간=%s ~ %s",
        len(df),
        df["grid_id"].nunique(),
        df["datetime"].min(),
        df["datetime"].max(),
    )
    return df
