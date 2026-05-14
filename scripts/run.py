"""
Phase 2 전체 파이프라인 실행 스크립트
STEP 1(로드) → STEP 2(음성 샘플) → STEP 3(OSMnx Feature) → STEP 4(모델) → STEP 5(대시보드)
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.loader_pm import load_pm_data
from src.data.negative_sampler import generate_negative_samples
from src.features.engineer_point import engineer_point_features
from src.models.train_xgb_point import train_risk_model
from src.visualization.visualize import create_risk_dashboard

import pandas as pd

log = logging.getLogger(__name__)


def run_pipeline(n_trials: int = 50, output_dir: str = "outputs"):
    log.info("=" * 60)
    log.info("SAFERIDE SAFERIDE 파이프라인 시작")
    log.info("=" * 60)

    # ── STEP 1: 양성 샘플 로드 ──────────────────────────────────
    log.info("\n[STEP 1] PM 사고 데이터 로드 (2021~2024)")
    pos_df = load_pm_data()

    # ── STEP 2: 음성 샘플 생성 ──────────────────────────────────
    log.info("\n[STEP 2] 3단계 매칭 샘플링으로 음성 샘플 생성")
    neg_df = generate_negative_samples(pos_df)

    # ── 양성 + 음성 합산 ─────────────────────────────────────────
    combined_df = pd.concat([pos_df, neg_df], ignore_index=True)
    log.info(f"합산: {len(combined_df)}행 (양성 {int(combined_df['is_hotspot'].sum())} / 음성 {int((combined_df['is_hotspot']==0).sum())})")

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

    # ── STEP 5: 위험도 대시보드 생성 ───────────────────────────
    log.info("\n[STEP 5] 위험도 점수 대시보드 생성")
    create_risk_dashboard(
        pos_df=pos_df,
        features_df=features_df,
        model=model,
        explainer=explainer,
        feature_names=feature_names,
        output_dir=output_dir,
    )

    log.info("\n" + "=" * 60)
    log.info("✅ SAFERIDE 파이프라인 완료!")
    log.info(f"결과물 위치: {output_dir}/")
    log.info("  - seoul_pm_risk_map.html : 공간 위험도 대시보드 (브라우저에서 열기)")
    log.info("  - shap_risk_bar.png          : Feature 중요도 순위")
    log.info("  - shap_risk_dot.png          : Feature 영향 방향성")
    log.info("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    run_pipeline(n_trials=50)
