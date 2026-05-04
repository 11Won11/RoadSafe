"""
SHAP 분석 및 Feature 중요도 시각화
TreeExplainer → Summary Plot + Waterfall Plot 저장
"""
import shap
import matplotlib.pyplot as plt
from pathlib import Path


def plot_shap_summary(
    model,
    X_test,
    feature_names: list,
    save_path: str = "outputs/figures/shap_summary.png",
) -> None:
    """전체 feature 중요도 Summary Plot (bee-swarm)"""
    explainer   = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test)

    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_values, X_test,
                      feature_names=feature_names, show=False)
    plt.tight_layout()
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"✓ SHAP summary → {save_path}")


def plot_shap_waterfall(
    model,
    X_sample,
    idx: int = 0,
    save_path: str = "outputs/figures/shap_waterfall.png",
) -> None:
    """단일 예측 샘플에 대한 Waterfall Plot (설명 가능성)"""
    explainer    = shap.TreeExplainer(model)
    explanation  = explainer(X_sample)

    shap.plots.waterfall(explanation[idx], show=False)
    plt.tight_layout()
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"✓ SHAP waterfall → {save_path}")
