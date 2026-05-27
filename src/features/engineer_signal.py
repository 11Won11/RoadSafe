"""
서울시 신호등 표준데이터 → 격자별 신호등 Feature 생성 모듈
- 원본 좌표계: EPSG:5186 (GRS80 TM중부원점) → EPSG:4326 (WGS84) 자동 변환
- 65,001개 신호등 데이터 처리
추가되는 Feature:
    signal_count_total       - 격자 내 전체 신호등 수
    signal_count_pedestrian  - 보행등 수 (보행자 횡단 밀도)
    signal_count_vehicle     - 차량 신호등 수 (3색/4색등, 교통량 밀도)
    signal_has_audio         - 음향 신호기 수 (시각장애인/보행자 보호 수준)
"""
import pandas as pd
import logging
from pathlib import Path

log = logging.getLogger(__name__)

SIGNAL_CSV = Path("data/raw/서울특별시_신호등표준데이터.csv")

# 서울 유효 좌표 범위 (WGS84)
LAT_RANGE = (37.40, 37.73)
LON_RANGE = (126.73, 127.22)

# 차량 신호등 유형
VEHICLE_TYPES = {"3색등", "4색등", "버스전용3색등", "3색등(종형)", "4색등(종형)"}


def load_signals() -> pd.DataFrame:
    """신호등 CSV 로드 → EPSG:5186 → WGS84 변환 → DataFrame 반환"""
    from pyproj import Transformer

    log.info(f"신호등 데이터 로드: {SIGNAL_CSV}")
    df = pd.read_csv(SIGNAL_CSV, encoding="cp949")

    transformer = Transformer.from_crs("EPSG:5186", "EPSG:4326", always_xy=True)
    lons, lats = transformer.transform(df["X좌표"].values, df["Y좌표"].values)
    df["lat"] = lats
    df["lon"] = lons

    # 서울 범위 필터
    mask = (
        df["lat"].between(*LAT_RANGE) &
        df["lon"].between(*LON_RANGE)
    )
    df = df[mask].copy()
    log.info(f"유효 신호등: {len(df):,}개 | 좌표 범위 위도 {df['lat'].min():.4f}~{df['lat'].max():.4f}")
    return df


def assign_signal_to_grids(
    grid_df: pd.DataFrame,
    grid_lat: float = 0.0045,
    grid_lon: float = 0.0056,
) -> pd.DataFrame:
    """
    신호등 포인트를 격자에 매핑하여 신호등 Feature를 추가합니다.

    추가 Feature:
        signal_count_total       - 전체 신호등 수
        signal_count_pedestrian  - 보행등 수 (보행자 충돌 위험 대리변수)
        signal_count_vehicle     - 차량 신호등 수 (교차로 복잡도 대리변수)
        signal_has_audio         - 음향 신호기 수
    """
    if not SIGNAL_CSV.exists():
        log.warning(f"신호등 파일 없음: {SIGNAL_CSV} — 신호등 Feature 0으로 채웁니다.")
        grid_df = grid_df.copy()
        for col in ["signal_count_total", "signal_count_pedestrian",
                    "signal_count_vehicle", "signal_has_audio"]:
            grid_df[col] = 0
        return grid_df

    sig_df = load_signals()

    lat_base = grid_df["lat_min"].min()
    lon_base = grid_df["lon_min"].min()

    # 신호등 포인트 → 격자 인덱스
    sig_df = sig_df.copy()
    sig_df["_lat_idx"] = ((sig_df["lat"] - lat_base) / grid_lat).astype(int)
    sig_df["_lon_idx"] = ((sig_df["lon"] - lon_base) / grid_lon).astype(int)

    # 격자별 집계
    agg = (
        sig_df
        .groupby(["_lat_idx", "_lon_idx"])
        .agg(
            signal_count_total=("신호등종류", "count"),
            signal_count_pedestrian=("신호등종류", lambda x: (x == "보행등").sum()),
            signal_count_vehicle=("신호등종류", lambda x: x.isin(VEHICLE_TYPES).sum()),
            signal_has_audio=("음향신호기유무", lambda x: (x == "유").sum()),
        )
        .reset_index()
    )

    # grid_df에 인덱스 부여 후 병합
    grid_df = grid_df.copy()
    grid_df["_lat_idx"] = ((grid_df["lat_min"] - lat_base) / grid_lat).round().astype(int)
    grid_df["_lon_idx"] = ((grid_df["lon_min"] - lon_base) / grid_lon).round().astype(int)

    grid_df = grid_df.merge(agg, on=["_lat_idx", "_lon_idx"], how="left")

    # 신호등 없는 격자는 0으로 채움
    for col in ["signal_count_total", "signal_count_pedestrian",
                "signal_count_vehicle", "signal_has_audio"]:
        grid_df[col] = grid_df[col].fillna(0).astype(int)

    grid_df = grid_df.drop(columns=["_lat_idx", "_lon_idx"])

    mapped = (grid_df["signal_count_total"] > 0).sum()
    log.info(
        f"신호등 Feature 매핑 완료: {mapped}개 격자 ({mapped/len(grid_df)*100:.1f}%) | "
        f"평균 신호등 수 {grid_df['signal_count_total'].mean():.1f}개 / 최대 {grid_df['signal_count_total'].max()}개"
    )
    return grid_df
