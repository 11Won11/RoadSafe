import logging
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.loader_phase1 import load_phase1_data
from src.features.engineer_phase1 import engineer_features_phase1
from src.models.train_xgb_phase1 import train_phase1_model
from src.visualization.visualize_phase1 import create_district_heatmap

log = logging.getLogger(__name__)

def run_phase1_pipeline():
    log.info("=== Phase 1 파이프라인 시작 ===")
    
    # 1. 데이터 로드
    log.info("1. 데이터 로드 및 정제")
    df = load_phase1_data("사고분석-지역별.xlsx")
    
    # 2. Feature Engineering
    log.info("2. Feature Engineering")
    df_features = engineer_features_phase1(df)
    
    # 3. 모델 학습 및 SHAP 추출
    log.info("3. XGBoost 학습 및 SHAP 중요도 분석")
    train_phase1_model(df_features, n_trials=30, output_dir="outputs")
    
    # 4. 히트맵 시각화
    log.info("4. 구(區)별 위험도 지도 생성")
    create_district_heatmap(df, output_dir="outputs")
    
    log.info("=== Phase 1 파이프라인 완료! (결과물: outputs/ 폴더 확인) ===")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    run_phase1_pipeline()
