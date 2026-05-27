"""
서울시 대로변 횡단보도 위치정보 데이터 → 격자별 횡단보도 Feature 생성 모듈
- 원본 좌표계: EPSG:4326 (WGS84) WKT 형식
- 19,518개 횡단보도 노드 포인트 매핑
추가되는 Feature:
    crosswalk_count - 격자 내 횡단보도 노드 수 (보행자 횡단 밀도 및 사고 위험 구역 대리변수)
"""
import pandas as pd
import logging
from pathlib import Path

log = logging.getLogger(__name__)

CROSSWALK_CSV = Path("data/raw/서울시 대로변 횡단보도 위치정보.csv")

def load_crosswalks() -> pd.DataFrame:
    """횡단보도 CSV 로드 및 WKT 파싱하여 (lon, lat) 데이터프레임 반환"""
    log.info(f"횡단보도 데이터 로드: {CROSSWALK_CSV}")
    df = pd.read_csv(CROSSWALK_CSV, encoding="cp949")
    
    # 노드 데이터만 추출 (횡단보도 양끝점)
    df_node = df[df["노드링크 유형"] == "NODE"].copy()
    
    # WKT 'POINT(lon lat)'에서 위경도 추출
    df_node["lon"] = df_node["노드 WKT"].str.extract(r"POINT\(([^ ]+) ")[0].astype(float)
    df_node["lat"] = df_node["노드 WKT"].str.extract(r"POINT\([^ ]+ ([^)]+)\)")[0].astype(float)
    
    # 필요없는 컬럼 제거
    df_node = df_node[["lon", "lat"]].dropna()
    log.info(f"유효 횡단보도 노드: {len(df_node):,}개")
    return df_node

def assign_crosswalk_to_grids(
    grid_df: pd.DataFrame,
    grid_lat: float = 0.0045,
    grid_lon: float = 0.0056,
) -> pd.DataFrame:
    """
    횡단보도 노드 포인트를 격자에 매핑하여 Feature를 추가합니다.
    추가 Feature: crosswalk_count
    """
    if not CROSSWALK_CSV.exists():
        log.warning(f"횡단보도 파일 없음: {CROSSWALK_CSV} — 0으로 채웁니다.")
        grid_df = grid_df.copy()
        grid_df["crosswalk_count"] = 0
        return grid_df

    cw_df = load_crosswalks()

    lat_base = grid_df["lat_min"].min()
    lon_base = grid_df["lon_min"].min()

    # 포인트 → 격자 인덱스
    cw_df = cw_df.copy()
    cw_df["_lat_idx"] = ((cw_df["lat"] - lat_base) / grid_lat).astype(int)
    cw_df["_lon_idx"] = ((cw_df["lon"] - lon_base) / grid_lon).astype(int)

    # 격자별 집계
    agg = (
        cw_df
        .groupby(["_lat_idx", "_lon_idx"])
        .agg(crosswalk_count=("lat", "count"))
        .reset_index()
    )

    # grid_df에 병합
    grid_df = grid_df.copy()
    grid_df["_lat_idx"] = ((grid_df["lat_min"] - lat_base) / grid_lat).round().astype(int)
    grid_df["_lon_idx"] = ((grid_df["lon_min"] - lon_base) / grid_lon).round().astype(int)

    grid_df = grid_df.merge(agg, on=["_lat_idx", "_lon_idx"], how="left")
    grid_df["crosswalk_count"] = grid_df["crosswalk_count"].fillna(0).astype(int)
    grid_df = grid_df.drop(columns=["_lat_idx", "_lon_idx"])

    mapped = (grid_df["crosswalk_count"] > 0).sum()
    log.info(
        f"횡단보도 Feature 매핑 완료: {mapped}개 격자 ({mapped/len(grid_df)*100:.1f}%) | "
        f"평균 {grid_df['crosswalk_count'].mean():.1f}개 / 최대 {grid_df['crosswalk_count'].max()}개"
    )
    return grid_df
