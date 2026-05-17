"""
SAFERIDE 전체 파이프라인 실행 스크립트
전국 광역시 데이터로 학습 → 서울 격자 위험도 예측 및 대시보드 생성

STEP 1: 전국 PM 사고 데이터 로드 (학습용)
STEP 2: 서울 음성 샘플 생성 (서울 도로망 기반 매칭)
STEP 3: 지점 단위 OSMnx 공간 Feature 추출
STEP 4: XGBoost 모델 학습 + SHAP 분석
STEP 5: 서울 전역 격자 위험도 예측 → 대시보드 생성
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.loader_pm import load_pm_data, load_seoul_only
from src.data.negative_sampler import generate_negative_samples
from src.features.engineer_point import engineer_point_features
from src.models.train_xgb_point import train_risk_model
from src.visualization.visualize import create_risk_dashboard

import pandas as pd

log = logging.getLogger(__name__)


def run_pipeline(n_trials: int = 50, output_dir: str = "outputs"):
    log.info("=" * 60)
    log.info("SAFERIDE 파이프라인 시작 (전국 학습 → 서울 예측)")
    log.info("=" * 60)

    # ── STEP 1: 전국 PM 사고 데이터 로드 (학습용) ───────────────
    log.info("\n[STEP 1] 전국 광역시 PM 사고 데이터 로드 (2021~2024)")
    pos_df_nationwide = load_pm_data(nationwide=True)

    # 서울 데이터만 별도 보관 (음성 샘플 생성·시각화용)
    log.info("[STEP 1-b] 서울 데이터 단독 분리 (음성 샘플·시각화 전용)")
    pos_df_seoul = load_seoul_only()

    # ── STEP 2: 음성 샘플 생성 (서울 기반) ──────────────────────
    log.info("\n[STEP 2] 3단계 매칭 샘플링으로 음성 샘플 생성 (서울 도로망 기준)")
    neg_df = generate_negative_samples(pos_df_seoul)

    # ── 학습 데이터 구성: 전국 양성 + 서울 음성 ─────────────────
    # 음성 샘플에 city 더미 컬럼 채우기 (전국 데이터 city 컬럼 맞추기)
    city_dummy_cols = [c for c in pos_df_nationwide.columns if c.startswith("city_")]
    for col in city_dummy_cols:
        if col not in neg_df.columns:
            neg_df[col] = 0

    combined_df = pd.concat([pos_df_nationwide, neg_df], ignore_index=True)
    log.info(
        f"학습 데이터 구성: 총 {len(combined_df)}행 "
        f"(전국 양성 {len(pos_df_nationwide)} / 서울 음성 {len(neg_df)})"
    )

    # ── STEP 3: 지점 단위 Feature 추출 ─────────────────────────
    log.info("\n[STEP 3] 지점 단위 OSMnx 공간 Feature 추출 (캐시 있으면 즉시 로드)")
    features_df = engineer_point_features(combined_df)

    # ── STEP 4: XGBoost 공간 위험도 모델 학습 ───────────────────
    log.info("\n[STEP 4] XGBoost 공간 위험도 모델 학습 + SHAP 분석")
    model, explainer, feature_names, shap_values, X_test = train_risk_model(
        features_df=features_df,
        n_trials=n_trials,
        output_dir=output_dir,
    )

    # ── STEP 5: 서울 격자 위험도 대시보드 생성 ──────────────────
    log.info("\n[STEP 5] 서울 전역 격자 위험도 예측 → 대시보드 생성")
    # 시각화는 서울 사고 지점만 기준으로 함
    seoul_features_mask = features_df.index < len(pos_df_seoul)  # 서울 양성 샘플 인덱스
    create_risk_dashboard(
        pos_df=pos_df_seoul,
        features_df=features_df,
        model=model,
        explainer=explainer,
        feature_names=feature_names,
        output_dir=output_dir,
    )

    log.info("\n" + "=" * 60)
    log.info("✅ SAFERIDE 파이프라인 완료!")
    log.info(f"결과물 위치: {output_dir}/")
    log.info("  - seoul_pm_risk_map.html : 서울 격자 위험도 대시보드")
    log.info("  - shap_risk_bar.png       : Feature 중요도 순위")
    log.info("  - shap_risk_dot.png       : Feature 영향 방향성")
    log.info("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    run_pipeline(n_trials=50)
