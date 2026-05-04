"""
평가 지표 모듈
AUROC, F1-macro, Precision@K 일괄 계산 및 출력
"""
import numpy as np
from sklearn.metrics import roc_auc_score, f1_score, classification_report


def precision_at_k(y_true: np.ndarray, y_prob: np.ndarray, k: int = 100) -> float:
    """상위 k개 위험 예측 격자 중 실제 사고 발생 비율"""
    top_k_idx = np.argsort(y_prob)[::-1][:k]
    return float(y_true[top_k_idx].mean())


def evaluate(model, X_test, y_test, k: int = 100, threshold: float = 0.5) -> dict:
    """세 지표 일괄 계산 + 분류 리포트 출력"""
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= threshold).astype(int)

    results = {
        "AUROC":       round(roc_auc_score(y_test, y_prob), 4),
        "F1_macro":    round(f1_score(y_test, y_pred, average="macro"), 4),
        f"Prec@{k}":  round(precision_at_k(np.asarray(y_test), y_prob, k), 4),
    }

    print("\n📊 평가 결과")
    for name, val in results.items():
        print(f"  {name}: {val}")
    print(classification_report(y_test, y_pred, target_names=["안전", "위험"]))
    return results
