"""
서울 CCTV 데이터 → 격자별 카메라 수 집계 모듈
- 생활방범 / 교통단속 / 어린이보호 유형별로 격자에 매핑
- Shapefile(data/raw/CCTV/SEOUL_CCTV_DATA.shp) 사용
"""
import geopandas as gpd
import pandas as pd
import logging
from pathlib import Path

log = logging.getLogger(__name__)

CCTV_SHP_PATH = Path("data/raw/CCTV/SEOUL_CCTV_DATA.shp")

# 서울 유효 좌표 범위
LAT_RANGE = (37.4, 37.8)
LON_RANGE = (126.7, 127.3)


def load_cctv(path: Path = CCTV_SHP_PATH) -> pd.DataFrame:
    """CCTV Shapefile 로드 및 전처리"""
    log.info(f"CCTV 데이터 로드: {path}")
    gdf = gpd.read_file(path)

    gdf["LAT"] = pd.to_numeric(gdf["LAT"], errors="coerce")
    gdf["LON"] = pd.to_numeric(gdf["LON"], errors="coerce")
    gdf["CAMERA_CNT"] = pd.to_numeric(gdf["CAMERA_CNT"], errors="coerce").fillna(1)

    # 서울 범위 내 유효 좌표만
    mask = (
        gdf["LAT"].between(*LAT_RANGE) &
        gdf["LON"].between(*LON_RANGE)
    )
    gdf = gdf[mask].copy()
    log.info(f"유효 CCTV: {len(gdf)}개소 / 총 카메라: {gdf['CAMERA_CNT'].sum():.0f}대")
    return pd.DataFrame(gdf[["LAT", "LON", "CAMERA_CNT", "INSTL_SE"]])


def assign_cctv_to_grids(
    grid_df: pd.DataFrame,
    grid_lat: float = 0.0045,
    grid_lon: float = 0.0056,
) -> pd.DataFrame:
    """
    각 격자 안에 있는 CCTV 카메라 수를 유형별로 카운트하여 grid_df에 추가.

    추가되는 Feature:
        cctv_count_total    - 격자 내 전체 카메라 수
        cctv_count_traffic  - 교통단속 카메라 수
        cctv_count_child    - 어린이보호 카메라 수
        cctv_count_safety   - 생활방범 카메라 수
    """
    if not CCTV_SHP_PATH.exists():
        log.warning(f"CCTV Shapefile 없음: {CCTV_SHP_PATH} — CCTV Feature 0으로 채웁니다.")
        grid_df = grid_df.copy()
        for col in ["cctv_count_total", "cctv_count_traffic", "cctv_count_child", "cctv_count_safety"]:
            grid_df[col] = 0
        return grid_df

    cctv_df = load_cctv()

    # 격자 기준점 (최솟값) 계산
    lat_base = grid_df["lat_min"].min()
    lon_base = grid_df["lon_min"].min()

    # CCTV 포인트 → 격자 인덱스 변환 (O(n_cctv), 메모리 효율적)
    cctv_df = cctv_df.copy()
    cctv_df["_lat_idx"] = ((cctv_df["LAT"] - lat_base) / grid_lat).astype(int)
    cctv_df["_lon_idx"] = ((cctv_df["LON"] - lon_base) / grid_lon).astype(int)

    # grid_df에도 인덱스 부여
    grid_df = grid_df.copy()
    grid_df["_lat_idx"] = ((grid_df["lat_min"] - lat_base) / grid_lat).round().astype(int)
    grid_df["_lon_idx"] = ((grid_df["lon_min"] - lon_base) / grid_lon).round().astype(int)

    # 유형별 집계 정의
    type_configs = [
        ("cctv_count_total",   None),           # 전체
        ("cctv_count_traffic", "교통단속"),      # 교통단속
        ("cctv_count_child",   "어린이보호"),    # 어린이보호
        ("cctv_count_safety",  "생활방범"),      # 생활방범
    ]

    for col_name, instl_type in type_configs:
        if instl_type is None:
            subset = cctv_df
        else:
            subset = cctv_df[cctv_df["INSTL_SE"] == instl_type]

        agg = (
            subset
            .groupby(["_lat_idx", "_lon_idx"])["CAMERA_CNT"]
            .sum()
            .reset_index()
            .rename(columns={"CAMERA_CNT": col_name})
        )
        grid_df = grid_df.merge(agg, on=["_lat_idx", "_lon_idx"], how="left")
        grid_df[col_name] = grid_df[col_name].fillna(0).astype(int)
        log.info(f"  {col_name}: {grid_df[col_name].sum():.0f}대 배정 완료")

    grid_df = grid_df.drop(columns=["_lat_idx", "_lon_idx"])
    log.info(f"CCTV Feature 매핑 완료 → {len(grid_df)}개 격자")
    return grid_df
