"""
서울 견인 데이터 → 격자별 견인 건수 집계 모듈
- 5개의 엑셀 파일을 모두 불러와 합치고, 좌표 기반으로 격자에 맵핑
"""
import pandas as pd
import glob
import logging
from pathlib import Path

log = logging.getLogger(__name__)

TOWING_DIR_PATH = Path("data/raw/서울특별시_견인데이터")

# 서울 유효 좌표 범위
LAT_RANGE = (37.4, 37.8)
LON_RANGE = (126.7, 127.3)

def load_towing(cutoff_year: int = 2024) -> pd.DataFrame:
    """모든 견인 엑셀 데이터 로드 및 전처리 (cutoff_year 이전 데이터만 필터링)"""
    if not TOWING_DIR_PATH.exists():
        return pd.DataFrame(columns=["LAT", "LON"])
        
    files = glob.glob(f"{TOWING_DIR_PATH}/*.xlsx")
    if not files:
        return pd.DataFrame(columns=["LAT", "LON"])

    dfs = []
    for f in files:
        log.info(f"견인 데이터 로드: {f}")
        try:
            # 첫 번째 행은 버리고 두 번째 행을 헤더로 사용
            df = pd.read_excel(f, header=1)
            
            # '신고일' 또는 '조치일' 컬럼이 존재하는지 확인하여 연도 필터링
            date_col = None
            if '신고일' in df.columns:
                date_col = '신고일'
            elif '조치일' in df.columns:
                date_col = '조치일'
                
            if date_col:
                df['year'] = pd.to_datetime(df[date_col], errors='coerce').dt.year
                df = df[~(df['year'] > cutoff_year)]
            
            # '위도', '경도' 컬럼이 존재하는지 확인
            if '위도' in df.columns and '경도' in df.columns:
                df = df[['위도', '경도']].rename(columns={'위도': 'LAT', '경도': 'LON'})
                dfs.append(df)
            else:
                log.warning(f"위도/경도 컬럼 없음: {f}")
        except Exception as e:
            log.warning(f"파일 읽기 오류 ({f}): {e}")
            
    if not dfs:
        return pd.DataFrame(columns=["LAT", "LON"])
        
    combined = pd.concat(dfs, ignore_index=True)
    
    # 숫자형 변환 및 결측치 제거
    combined["LAT"] = pd.to_numeric(combined["LAT"], errors="coerce")
    combined["LON"] = pd.to_numeric(combined["LON"], errors="coerce")
    combined = combined.dropna(subset=["LAT", "LON"])

    # 서울 범위 내 유효 좌표만 필터링
    mask = (
        combined["LAT"].between(*LAT_RANGE) &
        combined["LON"].between(*LON_RANGE)
    )
    combined = combined[mask].copy()
    log.info(f"유효 킥보드 견인 데이터 (cutoff={cutoff_year}): 총 {len(combined)}건")
    
    return combined
 
def assign_towing_to_grids(
    grid_df: pd.DataFrame,
    grid_lat: float = 0.0045,
    grid_lon: float = 0.0056,
    cutoff_year: int = 2024,
) -> pd.DataFrame:
    """
    각 격자 안에 있는 킥보드 견인 건수를 카운트하여 grid_df에 추가.
 
    추가되는 Feature:
        towing_count - 격자 내 킥보드 견인 건수
    """
    if not TOWING_DIR_PATH.exists() or not list(TOWING_DIR_PATH.glob("*.xlsx")):
        log.warning(f"견인 데이터 없음: {TOWING_DIR_PATH} — towing_count 0으로 채웁니다.")
        grid_df = grid_df.copy()
        grid_df["towing_count"] = 0
        return grid_df
 
    towing_df = load_towing(cutoff_year=cutoff_year)
    if len(towing_df) == 0:
        grid_df = grid_df.copy()
        grid_df["towing_count"] = 0
        return grid_df

    # 격자 기준점 (최솟값) 계산
    lat_base = grid_df["lat_min"].min()
    lon_base = grid_df["lon_min"].min()

    # 포인트 → 격자 인덱스 변환
    towing_df = towing_df.copy()
    towing_df["_lat_idx"] = ((towing_df["LAT"] - lat_base) / grid_lat).astype(int)
    towing_df["_lon_idx"] = ((towing_df["LON"] - lon_base) / grid_lon).astype(int)

    # grid_df에도 인덱스 부여
    grid_df = grid_df.copy()
    grid_df["_lat_idx"] = ((grid_df["lat_min"] - lat_base) / grid_lat).round().astype(int)
    grid_df["_lon_idx"] = ((grid_df["lon_min"] - lon_base) / grid_lon).round().astype(int)

    # 집계
    agg = (
        towing_df
        .groupby(["_lat_idx", "_lon_idx"])
        .size()
        .reset_index(name="towing_count")
    )
    
    if "towing_count" in grid_df.columns:
        grid_df = grid_df.drop(columns=["towing_count"])
    
    grid_df = grid_df.merge(agg, on=["_lat_idx", "_lon_idx"], how="left")
    grid_df["towing_count"] = grid_df["towing_count"].fillna(0).astype(int)
    
    log.info(f"  towing_count: 총 {grid_df['towing_count'].sum()}건 매핑 완료")

    grid_df = grid_df.drop(columns=["_lat_idx", "_lon_idx"])
    log.info(f"견인 Feature 매핑 완료 → {len(grid_df)}개 격자")
    return grid_df
