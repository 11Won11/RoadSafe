"""
서울시 경사도/표고 데이터 → 격자별 경사 Feature 생성 모듈
- 표고점(N3P_F002.shp): 76,580개 측정점의 해발 높이(m)
- 격자당 평균 표고(elev_mean), 표고 범위(elev_range) 계산
- CRS: EPSG:5174 (한국 중부원점) → EPSG:4326 (WGS84) 자동 변환
"""
import geopandas as gpd
import pandas as pd
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# 표고 Shapefile 경로 (점 데이터 우선, 더 정밀)
ELEV_SHP_PATH = Path("data/raw/서울시 경사도/표고 5000/N3P_F002.shp")

# 서울 유효 좌표 범위 (WGS84)
LAT_RANGE = (37.40, 37.73)
LON_RANGE = (126.73, 127.22)


def load_elevation(path: Path = ELEV_SHP_PATH) -> pd.DataFrame:
    """표고 Shapefile 로드 → WGS84 변환 → DataFrame 반환"""
    log.info(f"표고 데이터 로드: {path}")
    gdf = gpd.read_file(path)                 # CRS: EPSG:5174
    gdf = gdf.to_crs("EPSG:4326")            # WGS84로 변환

    gdf["lat"] = gdf.geometry.y
    gdf["lon"] = gdf.geometry.x
    gdf["height"] = pd.to_numeric(gdf["HEIGHT"], errors="coerce")

    # 서울 범위 필터
    mask = (
        gdf["lat"].between(*LAT_RANGE) &
        gdf["lon"].between(*LON_RANGE) &
        gdf["height"].notna()
    )
    gdf = gdf[mask].copy()
    log.info(f"유효 표고 측정점: {len(gdf):,}개 | 표고 범위: {gdf['height'].min():.1f}~{gdf['height'].max():.1f}m")
    return pd.DataFrame(gdf[["lat", "lon", "height"]])


def assign_slope_to_grids(
    grid_df: pd.DataFrame,
    grid_lat: float = 0.0045,
    grid_lon: float = 0.0056,
) -> pd.DataFrame:
    """
    각 격자 안에 있는 표고 측정점을 집계하여 경사 Feature를 추가합니다.

    추가되는 Feature:
        elev_mean   - 격자 내 평균 표고 (m) — 고도 지역 특성
        elev_range  - 격자 내 최고-최저 표고 차 (m) — 경사도 대리변수
                      → 클수록 급경사 → PM 제동 위험↑ / 사고 심각도↑
    """
    if not ELEV_SHP_PATH.exists():
        log.warning(f"표고 Shapefile 없음: {ELEV_SHP_PATH} — 경사 Feature 0으로 채웁니다.")
        grid_df = grid_df.copy()
        grid_df["elev_mean"] = 0.0
        grid_df["elev_range"] = 0.0
        return grid_df

    elev_df = load_elevation()

    # 격자 기준점 계산
    lat_base = grid_df["lat_min"].min()
    lon_base = grid_df["lon_min"].min()

    # 표고 측정점 → 격자 인덱스 (O(n_elev), 메모리 효율)
    elev_df = elev_df.copy()
    elev_df["_lat_idx"] = ((elev_df["lat"] - lat_base) / grid_lat).astype(int)
    elev_df["_lon_idx"] = ((elev_df["lon"] - lon_base) / grid_lon).astype(int)

    # 격자별 집계
    agg = (
        elev_df
        .groupby(["_lat_idx", "_lon_idx"])["height"]
        .agg(elev_mean="mean", elev_max="max", elev_min="min")
        .reset_index()
    )
    agg["elev_range"] = agg["elev_max"] - agg["elev_min"]

    # grid_df에 인덱스 부여 후 병합
    grid_df = grid_df.copy()
    grid_df["_lat_idx"] = ((grid_df["lat_min"] - lat_base) / grid_lat).round().astype(int)
    grid_df["_lon_idx"] = ((grid_df["lon_min"] - lon_base) / grid_lon).round().astype(int)

    grid_df = grid_df.merge(
        agg[["_lat_idx", "_lon_idx", "elev_mean", "elev_range"]],
        on=["_lat_idx", "_lon_idx"],
        how="left",
    )

    # 표고 데이터 없는 격자(산지 외곽 등)는 0으로 채움
    grid_df["elev_mean"]  = grid_df["elev_mean"].fillna(0.0)
    grid_df["elev_range"] = grid_df["elev_range"].fillna(0.0)

    grid_df = grid_df.drop(columns=["_lat_idx", "_lon_idx"])

    mapped = (grid_df["elev_mean"] > 0).sum()
    log.info(f"경사 Feature 매핑 완료: {mapped}개 격자 ({mapped/len(grid_df)*100:.1f}%) | "
             f"평균 표고 {grid_df['elev_mean'].mean():.1f}m / "
             f"평균 경사폭 {grid_df['elev_range'].mean():.1f}m")
    return grid_df
