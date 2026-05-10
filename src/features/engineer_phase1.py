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
    
    # 2. One-Hot Encoding 적용 (XGBoost는 카테고리 변수를 직접 처리할 수도 있지만, 명시적으로 One-Hot)
    # pd.get_dummies 사용
    df_encoded = pd.get_dummies(df_engineered[feature_cols], drop_first=False)
    
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
