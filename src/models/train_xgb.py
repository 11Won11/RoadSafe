"""
XGBoost 베이스라인 학습 + Optuna 하이퍼파라미터 튜닝
scale_pos_weight 포함 7개 파라미터 TPE 탐색
"""
import optuna
import xgboost as xgb
from sklearn.metrics import roc_auc_score

optuna.logging.set_verbosity(optuna.logging.WARNING)


def _objective(trial, X_tr, y_tr, X_va, y_va) -> float:
    params = {
        "n_estimators":     trial.suggest_int  ("n_estimators", 100, 1000),
        "max_depth":        trial.suggest_int  ("max_depth", 3, 10),
        "learning_rate":    trial.suggest_float("learning_rate", 1e-3, 0.3, log=True),
        "subsample":        trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "min_child_weight": trial.suggest_int  ("min_child_weight", 1, 10),
        "scale_pos_weight": trial.suggest_float("scale_pos_weight", 1.0, 20.0),
        "tree_method": "hist", "device": "cpu", "random_state": 42,
    }
    model = xgb.XGBClassifier(**params)
    model.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], verbose=False)
    return roc_auc_score(y_va, model.predict_proba(X_va)[:, 1])


def train_xgb(X_tr, y_tr, X_va, y_va, n_trials: int = 50):
    """Optuna 탐색 후 최적 파라미터로 최종 모델 학습"""
    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=42)
    )
    study.optimize(
        lambda t: _objective(t, X_tr, y_tr, X_va, y_va),
        n_trials=n_trials
    )
    print(f"✓ Best AUROC: {study.best_value:.4f}  params: {study.best_params}")

    best_model = xgb.XGBClassifier(
        **study.best_params, tree_method="hist", random_state=42
    )
    best_model.fit(X_tr, y_tr)
    return best_model, study.best_params
