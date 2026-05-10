import optuna
import xgboost as xgb
import shap
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, f1_score, classification_report
import logging
import os
from pathlib import Path

# 한글 폰트 설정 (Mac)
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

log = logging.getLogger(__name__)
optuna.logging.set_verbosity(optuna.logging.WARNING)

def _objective(trial, X_tr, y_tr, X_va, y_va) -> float:
    params = {
        "n_estimators":     trial.suggest_int("n_estimators", 50, 300),
        "max_depth":        trial.suggest_int("max_depth", 3, 8),
        "learning_rate":    trial.suggest_float("learning_rate", 1e-3, 0.2, log=True),
        "subsample":        trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 5),
        "scale_pos_weight": trial.suggest_float("scale_pos_weight", 1.0, 10.0),
        "tree_method": "hist", 
        "device": "cpu", 
        "random_state": 42,
    }
    model = xgb.XGBClassifier(**params)
    model.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], verbose=False)
    return roc_auc_score(y_va, model.predict_proba(X_va)[:, 1])

def train_phase1_model(df_features: pd.DataFrame, n_trials: int = 20, output_dir: str = "outputs"):
    """
    XGBoost 학습 및 SHAP 중요도 분석
    """
    X = df_features.drop(columns=['is_severe'])
    y = df_features['is_severe']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    log.info(f"학습 데이터 크기: {X_train.shape}, 테스트 데이터 크기: {X_test.shape}")
    
    # Optuna 탐색
    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(lambda t: _objective(t, X_train, y_train, X_test, y_test), n_trials=n_trials)
    
    log.info(f"Best AUROC: {study.best_value:.4f}")
    
    # 최적 파라미터로 최종 모델 학습
    best_params = study.best_params
    best_model = xgb.XGBClassifier(**best_params, tree_method="hist", random_state=42)
    best_model.fit(X_train, y_train)
    
    # 평가
    y_pred_proba = best_model.predict_proba(X_test)[:, 1]
    y_pred = best_model.predict(X_test)
    
    auroc = roc_auc_score(y_test, y_pred_proba)
    f1 = f1_score(y_test, y_pred)
    log.info(f"Test AUROC: {auroc:.4f}, Test F1: {f1:.4f}")
    log.info(f"\n{classification_report(y_test, y_pred)}")
    
    # SHAP 분석
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    explainer = shap.TreeExplainer(best_model)
    shap_values = explainer.shap_values(X_test)
    
    # SHAP Summary Plot 저장
    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_values, X_test, plot_type="bar", show=False)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/shap_summary_bar.png")
    plt.close()
    
    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_values, X_test, show=False)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/shap_summary_dot.png")
    plt.close()
    
    log.info(f"SHAP plot 저장 완료: {output_dir}")
    
    return best_model, explainer

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys
    
    # 임포트 경로 설정
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from src.data.loader_phase1 import load_phase1_data
    from src.features.engineer_phase1 import engineer_features_phase1
    
    df = load_phase1_data("사고분석-지역별.xlsx")
    df_features = engineer_features_phase1(df)
    
    model, explainer = train_phase1_model(df_features, n_trials=10)
