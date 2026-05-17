"""
격자 수준(Grid-Level) XGBoost 위험도 모델
- 서울 전체 500m 격자 각각을 샘플로 사용
- 타겟: 격자 내 PM 사고 발생 여부 (is_accident=1/0)
- 시간적 홀드아웃: 2021-2023 훈련 → 2024 검증
- PAI 곡선으로 공간 예측력 평가
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
import pickle
from pathlib import Path
from sklearn.metrics import roc_auc_score, f1_score, classification_report

optuna.logging.set_verbosity(optuna.logging.WARNING)
log = logging.getLogger(__name__)

# 한글 폰트
for font in fm.findSystemFonts():
    if "AppleGothic" in font or "NanumGothic" in font:
        plt.rcParams["font.family"] = fm.FontProperties(fname=font).get_name()
        break
plt.rcParams["axes.unicode_minus"] = False

GRID_FEAT_CACHE = Path("data/interim/grid_features_with_labels.csv")
GRID_MODEL_PATH = Path("data/interim/xgb_grid_model.pkl")
GRID_LAT = 0.0045
GRID_LON = 0.0056


# ─── STEP 1: 격자별 Feature + 사고 라벨 생성 ──────────────────────────────

def build_grid_dataset(
    acc_df: pd.DataFrame,
    force: bool = False,
) -> pd.DataFrame:
    """
    서울 전역 격자 × OSMnx 공간 Feature + 사고 건수 라벨 DataFrame 생성.
    acc_df에는 '위도', '경도', '발생연도' 컬럼이 있어야 함.

    캐시: data/interim/grid_features_with_labels.csv
    """
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from src.features.engineer_grid import _extract_spatial_features, SEOUL_BBOX
    import osmnx as ox

    if GRID_FEAT_CACHE.exists() and not force:
        log.info(f"격자 Feature 캐시 로드: {GRID_FEAT_CACHE}")
        return pd.read_csv(GRID_FEAT_CACHE)

    # 도로망 로드
    graph_cache = Path("data/interim/seoul_graph.graphml")
    if graph_cache.exists():
        G = ox.load_graphml(graph_cache)
    else:
        G = ox.graph_from_place("Seoul, South Korea", network_type="drive")
        ox.save_graphml(G, graph_cache)
    nodes, _ = ox.graph_to_gdfs(G)

    # 격자 목록 생성
    grid_cells = []
    lat = SEOUL_BBOX["lat_min"]
    while lat < SEOUL_BBOX["lat_max"]:
        lon = SEOUL_BBOX["lon_min"]
        while lon < SEOUL_BBOX["lon_max"]:
            cy = lat + GRID_LAT / 2
            cx = lon + GRID_LON / 2
            grid_cells.append((lat, lon, cy, cx))
            lon += GRID_LON
        lat += GRID_LAT

    total = len(grid_cells)
    log.info(f"격자 수: {total}개 | 공간 Feature 추출 중...")

    # 사고 좌표 사전 계산
    acc_lat = acc_df["위도"].values.astype(float)
    acc_lon = acc_df["경도"].values.astype(float)

    # 연도 파싱
    if "발생연도" in acc_df.columns:
        acc_year = acc_df["발생연도"].astype(int).values
    else:
        acc_year = acc_df["발생년월"].astype(str).str.extract(r"(\d{4})")[0].astype(int).values

    records = []
    for i, (lat_min, lon_min, cy, cx) in enumerate(grid_cells):
        if i % 500 == 0:
            log.info(f"  진행: {i}/{total}")

        # OSMnx 공간 Feature
        spatial = _extract_spatial_features(cy, cx, G, nodes)

        # 격자 내 사고 카운팅 (연도별)
        lat_max_cell = lat_min + GRID_LAT
        lon_max_cell = lon_min + GRID_LON
        in_cell = (
            (acc_lat >= lat_min) & (acc_lat < lat_max_cell) &
            (acc_lon >= lon_min) & (acc_lon < lon_max_cell)
        )
        total_acc = in_cell.sum()
        acc_2021_23 = ((acc_year <= 2023) & in_cell).sum()
        acc_2024 = ((acc_year == 2024) & in_cell).sum()

        records.append({
            "lat_min": lat_min,
            "lon_min": lon_min,
            "cy": cy,
            "cx": cx,
            "acc_total": int(total_acc),
            "acc_2021_23": int(acc_2021_23),
            "acc_2024": int(acc_2024),
            **spatial,
        })

    df = pd.DataFrame(records)
    df["label_all"]     = (df["acc_total"] > 0).astype(int)
    df["label_2021_23"] = (df["acc_2021_23"] > 0).astype(int)
    df["label_2024"]    = (df["acc_2024"] > 0).astype(int)

    GRID_FEAT_CACHE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(GRID_FEAT_CACHE, index=False)
    log.info(f"격자 Feature 저장: {GRID_FEAT_CACHE} ({len(df)}개 격자)")
    log.info(f"  사고 있는 격자: {df['label_all'].sum()} / {len(df)}")
    return df


# ─── STEP 2: 격자 수준 XGBoost 학습 ──────────────────────────────────────

SPATIAL_FEAT_COLS = [
    "intersection_count_100m", "intersection_count_200m", "intersection_count_500m",
    "node_degree", "dist_to_nearest_intersection",
    "avg_lanes", "max_lanes",
    "is_primary_road", "is_secondary_road", "is_residential_road", "is_intersection",
]


def _tune(X_train, y_train, n_trials=30):
    def objective(trial):
        params = dict(
            max_depth=trial.suggest_int("max_depth", 3, 7),
            learning_rate=trial.suggest_float("lr", 0.01, 0.3, log=True),
            n_estimators=trial.suggest_int("n_est", 100, 400),
            subsample=trial.suggest_float("sub", 0.5, 1.0),
            colsample_bytree=trial.suggest_float("col", 0.5, 1.0),
            min_child_weight=trial.suggest_int("mcw", 1, 10),
        )
        spw = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
        model = xgb.XGBClassifier(
            **params, scale_pos_weight=spw,
            eval_metric="auc", use_label_encoder=False, tree_method="hist", random_state=42,
        )
        from sklearn.model_selection import cross_val_score
        return cross_val_score(model, X_train, y_train, cv=5, scoring="roc_auc", n_jobs=-1).mean()

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    log.info(f"Optuna | Best AUROC={study.best_value:.4f}")
    return study.best_params


def train_grid_model(
    grid_df: pd.DataFrame,
    n_trials: int = 30,
    output_dir: str = "outputs",
):
    """
    격자 수준 XGBoost 학습 + 시간적 검증(2021-23 → 2024)
    Returns: (model, explainer, feature_names, grid_df_with_scores)
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # ── [비판 1, 2 방어] 산/강/외곽 지역 필터링 ──────────────────
    # 교차로가 반경 500m 내에 1개도 없는 곳은 PM 주행 자체가 불가능한 산/강/시외곽으로 간주
    before_len = len(grid_df)
    grid_df = grid_df[grid_df["intersection_count_500m"] > 0].copy()
    log.info(f"산/강/외곽 지역 필터링: {before_len} -> {len(grid_df)}개 격자 (노출량 0 지역 제외)")

    feat_cols = [c for c in SPATIAL_FEAT_COLS if c in grid_df.columns]
    log.info(f"사용 Feature: {feat_cols}")

    # ── 훈련: 2021-2023 사고 기준 ───────────────────────────────
    X = grid_df[feat_cols].fillna(0)
    y_train_label = grid_df["label_2021_23"]
    y_all_label   = grid_df["label_all"]

    pos = y_train_label.sum(); neg = (y_train_label == 0).sum()
    spw = neg / max(pos, 1)
    log.info(f"학습 라벨 | 양성(사고 격자 2021-23): {pos} | 음성: {neg} | scale_pos_weight={spw:.1f}")

    # Optuna
    log.info(f"Optuna HPO 중 (n_trials={n_trials})...")
    best_params = _tune(X, y_train_label, n_trials=n_trials)
    best_params.update({"lr": best_params.pop("lr", 0.1)})

    model = xgb.XGBClassifier(
        max_depth=best_params.get("max_depth", 5),
        learning_rate=best_params.get("learning_rate", best_params.get("lr", 0.1)),
        n_estimators=best_params.get("n_est", 200),
        subsample=best_params.get("sub", 0.8),
        colsample_bytree=best_params.get("col", 0.8),
        min_child_weight=best_params.get("mcw", 1),
        scale_pos_weight=spw,
        eval_metric="auc", use_label_encoder=False,
        tree_method="hist", random_state=42,
    )
    model.fit(X, y_train_label)

    # ── 전체 격자 위험도 예측 ────────────────────────────────────
    proba = model.predict_proba(X)[:, 1]
    risk_scores = (proba * 100).clip(0, 100)
    grid_df = grid_df.copy()
    grid_df["risk_score"] = risk_scores

    # ── 시간적 검증: 2024 사고 기준 PAI ─────────────────────────
    log.info("\n--- 시간적 검증 (2024 사고 기준) ---")
    auroc_2024, pai_2024 = _eval_and_print(grid_df, label_col="label_2024", tag="2024년 사고")

    # ── 전체 기준 AUROC ──────────────────────────────────────────
    log.info("--- 전체 기간 기준 ---")
    auroc_all, pai_all = _eval_and_print(grid_df, label_col="label_all", tag="전체(2021-24)")

    # ── 지표 저장 (보고서/논문용) ──────────────────────────────
    pai_2024.to_csv(f"{output_dir}/pai_metrics_2024.csv", index=False)
    pai_all.to_csv(f"{output_dir}/pai_metrics_all.csv", index=False)
    
    with open(f"{output_dir}/evaluation_summary.txt", "w", encoding="utf-8") as f:
        f.write("=== SAFERIDE 격자 위험도 모델 평가 요약 ===\n\n")
        f.write(f"[1] 2024년 시간적 검증 (미래 예측)\n")
        f.write(f"  - AUROC: {auroc_2024:.4f}\n")
        f.write(f"  - PAI@10%: {pai_2024.loc[9, 'pai']:.2f}\n")
        f.write(f"  - PAI@20%: {pai_2024.loc[19, 'pai']:.2f}\n\n")
        f.write(f"[2] 전체(2021-2024) 데이터 기준\n")
        f.write(f"  - AUROC: {auroc_all:.4f}\n")
        f.write(f"  - PAI@10%: {pai_all.loc[9, 'pai']:.2f}\n")
        f.write(f"  - PAI@20%: {pai_all.loc[19, 'pai']:.2f}\n")
    log.info(f"평가 결과 저장: {output_dir}/evaluation_summary.txt, pai_metrics_*.csv")

    # ── SHAP 분석 ────────────────────────────────────────────────
    explainer = shap.TreeExplainer(model)
    shap_vals = explainer.shap_values(X)

    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_vals, X, plot_type="bar", show=False, max_display=12)
    plt.title("SHAP Feature Importance — 격자 수준 PM 위험도 모델", fontsize=13)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/shap_grid_bar.png", dpi=150)
    plt.close()

    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_vals, X, show=False, max_display=12)
    plt.title("SHAP Summary — 격자 Feature별 위험도 영향", fontsize=13)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/shap_grid_dot.png", dpi=150)
    plt.close()
    log.info(f"SHAP 저장: {output_dir}/shap_grid_*.png")

    # ── 모델 저장 ─────────────────────────────────────────────────
    with open(GRID_MODEL_PATH, "wb") as f:
        pickle.dump({"model": model, "feature_names": feat_cols}, f)
    log.info(f"모델 저장: {GRID_MODEL_PATH}")

    return model, explainer, feat_cols, grid_df


def _eval_and_print(grid_df, label_col, tag):
    """PAI + AUROC 출력 및 반환"""
    from src.evaluation.evaluate import compute_pai

    y_true = grid_df[label_col].values
    y_score = grid_df["risk_score"].values / 100

    auroc = 0.0
    # 라벨이 있는 경우만 AUROC
    if y_true.sum() > 0 and y_true.sum() < len(y_true):
        auroc = roc_auc_score(y_true, y_score)
        log.info(f"[{tag}] AUROC={auroc:.4f}")

    # PAI 계산 (격자 기반)
    grid_for_pai = grid_df[["lat_min", "lon_min", "risk_score"]].copy()
    acc_grids = grid_df[grid_df[label_col] == 1][["lat_min", "lon_min"]].copy()
    acc_grids["위도"] = acc_grids["lat_min"] + GRID_LAT / 2
    acc_grids["경도"] = acc_grids["lon_min"] + GRID_LON / 2

    pai_df = compute_pai(grid_for_pai, acc_grids)

    print(f"\n  [{tag}] PAI 결과")
    print(f"  {'k%':>5} | {'포착 격자':>8} | {'포착률':>7} | {'PAI':>6}")
    print("  " + "-" * 38)
    for k in [5, 10, 20, 30, 50]:
        row = pai_df.loc[k - 1]
        print(f"  {k:>5}% | {int(row['acc_captured']):>8} | {row['acc_ratio']*100:>6.1f}% | {row['pai']:>6.2f}")

    return auroc, pai_df


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    from src.data.loader_pm import load_seoul_only
    seoul_df = load_seoul_only()

    grid_df = build_grid_dataset(seoul_df, force=False)
    model, explainer, feat_cols, grid_df_scored = train_grid_model(grid_df, n_trials=30)
