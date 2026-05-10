import pandas as pd
from sklearn.preprocessing import LabelEncoder
import logging

log = logging.getLogger(__name__)

def engineer_features_phase1(df: pd.DataFrame) -> pd.DataFrame:
    """
    Phase 1 데이터의 범주형 변수를 인코딩하여 머신러닝 모델(XGBoost) 입력 형태로 변환.
    """
    df_engineered = df.copy()
    
    # 1. 사용할 특성(Feature) 선택
    feature_cols = [
        '주야',
        '구',
        '기상상태',
        '노면상태',
        '도로형태',
        '사고유형',
        '법규위반'
    ]
    
    # 결측치 처리 (문자열 '알수없음' 등으로 채움)
    for col in feature_cols:
        df_engineered[col] = df_engineered[col].fillna('알수없음').astype(str)
    
    # 2. OSMnx 공간 변수 병합
    try:
        from pathlib import Path
        osmnx_path = Path("data/interim/district_osmnx_features.csv")
        if osmnx_path.exists():
            osmnx_df = pd.read_csv(osmnx_path)
            # df_engineered['구']와 osmnx_df['구']를 기준으로 병합
            df_engineered = df_engineered.merge(osmnx_df, on='구', how='left')
            # 결측치(데이터 없는 구) 0으로 채우기
            df_engineered[['intersection_count', 'street_length_total', 'intersection_density_per_km']] = df_engineered[['intersection_count', 'street_length_total', 'intersection_density_per_km']].fillna(0)
            log.info("OSMnx 공간 변수 병합 완료")
        else:
            log.warning("OSMnx 파일이 없습니다. 공간 변수 없이 진행합니다.")
    except Exception as e:
        log.error(f"OSMnx 병합 중 오류: {e}")
    
    # 3. One-Hot Encoding 적용 (XGBoost는 카테고리 변수를 직접 처리할 수도 있지만, 명시적으로 One-Hot)
    # pd.get_dummies 사용 (숫자형 변수들은 get_dummies에서 무시되고 그대로 유지됨)
    df_encoded = pd.get_dummies(df_engineered[feature_cols + ['intersection_count', 'street_length_total', 'intersection_density_per_km'] if 'intersection_count' in df_engineered.columns else feature_cols], drop_first=False)
    
    # 3. Target 변수 합치기
    df_final = pd.concat([df_encoded, df_engineered[['is_severe']]], axis=1)
    
    log.info(f"Feature Engineering 완료: {df_final.shape[1]-1}개의 feature 생성")
    
    return df_final

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys
    from pathlib import Path
    
    # 임포트 경로 추가
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from src.data.loader_phase1 import load_phase1_data
    
    df = load_phase1_data("사고분석-지역별.xlsx")
    df_features = engineer_features_phase1(df)
    
    print(df_features.head())
    print("생성된 컬럼들:", df_features.columns.tolist())
