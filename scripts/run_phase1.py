import logging
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.loader_phase1 import load_phase1_data
from src.features.engineer_osmnx import create_osmnx_district_features
from src.features.engineer_phase1 import engineer_features_phase1
from src.models.train_xgb_phase1 import train_phase1_model
from src.visualization.visualize_phase1 import create_district_heatmap

log = logging.getLogger(__name__)

def run_phase1_pipeline():
    log.info("=== Phase 1 파이프라인 (OSMnx 고도화) 시작 ===")
    
    # 1. 공간 데이터 추출
    log.info("1. OSMnx 도로망 공간 변수 생성 (기존 캐시가 있으면 스킵됨)")
    create_osmnx_district_features("data/interim/district_osmnx_features.csv")
    
    # 2. 사고 데이터 로드
    log.info("2. 사고 데이터 로드 및 정제")
    df = load_phase1_data("data/raw/사고분석-지역별.xlsx")
    
    # 3. Feature Engineering
    log.info("3. Feature Engineering (공간 변수 병합 포함)")
    df_features = engineer_features_phase1(df)
    
    # 4. 모델 학습 및 SHAP 추출
    log.info("4. XGBoost 학습 및 SHAP 중요도 분석")
    train_phase1_model(df_features, n_trials=30, output_dir="outputs")
    
    # 5. 히트맵 시각화
    log.info("5. 구(區)별 위험도 다중 레이어 지도 생성")
    create_district_heatmap(df, output_dir="outputs")
    
    log.info("=== Phase 1 고도화 파이프라인 완료! (결과물: outputs/ 폴더 확인) ===")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    run_phase1_pipeline()
