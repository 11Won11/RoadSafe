"""
Phase 2 XGBoost 공간 위험도 예측 모델
"이 공간적 특성을 가진 지점에서 PM 사고가 발생할 확률은?" → 위험도 점수 0~100
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import xgboost as xgb
import shap
import optuna
import logging
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, f1_score, classification_report
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import pickle

optuna.logging.set_verbosity(optuna.logging.WARNING)
log = logging.getLogger(__name__)

MODEL_CACHE = Path("data/interim/xgb_risk_model.pkl")

# 한글 폰트 설정 (macOS)
for font in fm.findSystemFonts():
    if "AppleGothic" in font or "NanumGothic" in font:
        plt.rcParams["font.family"] = fm.FontProperties(fname=font).get_name()
        break
plt.rcParams["axes.unicode_minus"] = False


def _tune_xgb(X_train, y_train, n_trials=50):
    """Optuna TPE로 XGBoost 하이퍼파라미터 탐색"""
    def objective(trial):
        params = {
            "max_depth": trial.suggest_int("max_depth", 3, 8),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "n_estimators": trial.suggest_int("n_estimators", 100, 500),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "tree_method": "hist",
            "random_state": 42,
        }
        model = xgb.XGBClassifier(**params, eval_metric="auc", use_label_encoder=False)
        from sklearn.model_selection import cross_val_score
        scores = cross_val_score(model, X_train, y_train, cv=5, scoring="roc_auc", n_jobs=-1)
        return scores.mean()

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    log.info(f"Optuna 완료 | Best AUROC: {study.best_value:.4f} | Params: {study.best_params}")
    return study.best_params


def train_risk_model(
    features_df: pd.DataFrame,
    n_trials: int = 50,
    output_dir: str = "outputs",
):
    """
    단일 XGBoost 공간 위험도 예측 모델 학습.
    양성(사고 지점, is_hotspot=1) vs 음성(비사고 지점, is_hotspot=0) 이진 분류.
    예측 확률 → 위험도 점수 0~100으로 스케일링.

    Returns:
        model: 학습된 XGBClassifier
        shap_explainer: TreeExplainer
        feature_names: Feature 컬럼명 리스트
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # ── Feature / Target 분리 ────────────────────────────────────
    drop_cols = [c for c in ["is_hotspot", "is_daytime", "is_severe"] if c in features_df.columns]
    y = features_df["is_hotspot"].values
    X = features_df.drop(columns=drop_cols)
    feature_names = X.columns.tolist()

    log.info(f"학습 데이터 | 전체: {len(y)}개 | 양성(사고): {y.sum()} | 음성(비사고): {(y==0).sum()}")

    # Train / Test 분리 (80:20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    # ── Optuna 하이퍼파라미터 튜닝 ──────────────────────────────
    log.info(f"Optuna 하이퍼파라미터 탐색 중 (n_trials={n_trials})...")
    best_params = _tune_xgb(X_train, y_train, n_trials=n_trials)

    # ── 최종 XGBoost 모델 학습 ──────────────────────────────────
    model = xgb.XGBClassifier(
        **best_params,
        eval_metric="auc",
        use_label_encoder=False,
        random_state=42,
        tree_method="hist",
    )
    model.fit(X_train, y_train)

    # ── 성능 평가 ────────────────────────────────────────────────
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_pred_proba >= 0.5).astype(int)
    auroc = roc_auc_score(y_test, y_pred_proba)
    f1 = f1_score(y_test, y_pred, zero_division=0)

    log.info(f"XGBoost | AUROC: {auroc:.4f} | F1: {f1:.4f}")
    log.info(f"\n{classification_report(y_test, y_pred, zero_division=0)}")

    # 비교 모델
    for name, clf in [
        ("LogisticRegression", LogisticRegression(max_iter=500, random_state=42)),
        ("RandomForest", RandomForestClassifier(n_estimators=100, random_state=42)),
    ]:
        clf.fit(X_train, y_train)
        score = roc_auc_score(y_test, clf.predict_proba(X_test)[:, 1])
        log.info(f"  {name} AUROC: {score:.4f}")

    # ── SHAP 분석 ────────────────────────────────────────────────
    log.info("SHAP Feature Importance 계산 중...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test)

    # SHAP Bar Plot (Feature 중요도 순위)
    plt.figure(figsize=(10, 7))
    shap.summary_plot(shap_values, X_test, plot_type="bar", show=False, max_display=15)
    plt.title("SHAP Feature Importance — PM 사고 공간 위험도 모델", fontsize=13)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/shap_risk_bar.png", dpi=150)
    plt.close()
    log.info(f"SHAP bar plot 저장: {output_dir}/shap_risk_bar.png")

    # SHAP Dot Plot (방향성 포함)
    plt.figure(figsize=(10, 7))
    shap.summary_plot(shap_values, X_test, show=False, max_display=15)
    plt.title("SHAP Summary — 각 Feature가 위험도에 미치는 영향", fontsize=13)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/shap_risk_dot.png", dpi=150)
    plt.close()
    log.info(f"SHAP dot plot 저장: {output_dir}/shap_risk_dot.png")

    # ── 모델 캐싱 ────────────────────────────────────────────────
    MODEL_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_CACHE, "wb") as f:
        pickle.dump({"model": model, "feature_names": feature_names}, f)
    log.info(f"모델 저장: {MODEL_CACHE}")

    return model, explainer, feature_names, shap_values, X_test


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    from src.data.loader_pm import load_pm_data
    from src.data.negative_sampler import generate_negative_samples
    from src.features.engineer_point import engineer_point_features

    pos_df = load_pm_data()
    neg_df = generate_negative_samples(pos_df)
    combined = pd.concat([pos_df, neg_df], ignore_index=True)
    features_df = engineer_point_features(combined)
    train_risk_model(features_df, n_trials=50)
