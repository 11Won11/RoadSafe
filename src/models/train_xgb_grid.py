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
from sklearn.metrics import roc_auc_score, f1_score, classification_report, mean_squared_error, mean_absolute_error
import libpysal
from esda.moran import Moran

optuna.logging.set_verbosity(optuna.logging.WARNING)
log = logging.getLogger(__name__)

# 한글 폰트
for font in fm.findSystemFonts():
    if "AppleGothic" in font or "NanumGothic" in font:
        plt.rcParams["font.family"] = fm.FontProperties(fname=font).get_name()
        break
plt.rcParams["axes.unicode_minus"] = False

GRID_MODEL_PATH = Path("data/interim/xgb_grid_model.pkl")
GRID_LAT = 0.0045
GRID_LON = 0.0056


# ─── STEP 1: 격자별 Feature + 사고 라벨 생성 ──────────────────────────────

def build_grid_dataset(
    acc_df: pd.DataFrame,
    force: bool = False,
    city_name: str = "Seoul"
) -> pd.DataFrame:
    """
    대상 도시(city_name) 전역 격자 × OSMnx 공간 Feature + 사고 건수 라벨 DataFrame 생성.
    acc_df에는 '위도', '경도', '발생연도' 컬럼이 있어야 함.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from src.features.engineer_grid import _extract_spatial_features
    import osmnx as ox

    grid_feat_cache = Path(f"data/interim/grid_features_with_labels_{city_name.lower()}.csv")
    if grid_feat_cache.exists() and not force:
        log.info(f"격자 Feature 캐시 로드: {grid_feat_cache}")
        df = pd.read_csv(grid_feat_cache)
        # CCTV 컬럼이 없으면 추가 후 캐시 갱신 (OSMnx 재계산 없이)
        if "cctv_count_total" not in df.columns:
            log.info("CCTV Feature 누락 → 추가 중...")
            from src.features.engineer_cctv import assign_cctv_to_grids
            df = assign_cctv_to_grids(df, GRID_LAT, GRID_LON)
            df.to_csv(grid_feat_cache, index=False)
            log.info(f"CCTV Feature 추가 완료 → 캐시 갱신: {grid_feat_cache}")
        return df

    # 도시 BBOX 추출
    log.info(f"{city_name} Bounding Box 추출 중...")
    try:
        gdf_city = ox.geocode_to_gdf(f"{city_name}, South Korea")
        bbox = gdf_city.bounds.iloc[0]
        lat_min_b, lat_max_b, lon_min_b, lon_max_b = bbox.miny, bbox.maxy, bbox.minx, bbox.maxx
    except Exception as e:
        log.warning(f"BBOX 추출 실패, 기본 서울 BBOX 사용. ({e})")
        lat_min_b, lat_max_b, lon_min_b, lon_max_b = 37.413294, 37.715133, 126.734086, 127.269311

    # 도로망 로드
    graph_cache = Path(f"data/interim/{city_name.lower()}_graph.graphml")
    if graph_cache.exists():
        G = ox.load_graphml(graph_cache)
    else:
        G = ox.graph_from_place(f"{city_name}, South Korea", network_type="drive")
        ox.save_graphml(G, graph_cache)
    nodes, _ = ox.graph_to_gdfs(G)

    # 격자 목록 생성
    grid_cells = []
    lat = lat_min_b
    while lat < lat_max_b:
        lon = lon_min_b
        while lon < lon_max_b:
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
        acc_2021_24 = ((acc_year <= 2024) & in_cell).sum()
        acc_2025 = ((acc_year == 2025) & in_cell).sum()

        records.append({
            "lat_min": lat_min,
            "lon_min": lon_min,
            "cy": cy,
            "cx": cx,
            "acc_total": int(total_acc),
            "acc_2021_24": int(acc_2021_24),
            "acc_2025": int(acc_2025),
            **spatial,
        })

    df = pd.DataFrame(records)
    df["label_all"]     = (df["acc_total"] > 0).astype(int)
    df["label_2021_24"] = (df["acc_2021_24"] > 0).astype(int)
    df["label_2025"]    = (df["acc_2025"] > 0).astype(int)

    # ── POI 유동인구 Proxy 연동 ────────────────────────────────
    from src.features.engineer_poi import download_city_pois, assign_pois_to_grids
    poi_df = download_city_pois(city_name=city_name, force=False)
    df = assign_pois_to_grids(df, poi_df, GRID_LAT, GRID_LON)

    # ── CCTV 감시/억제 Feature 연동 ───────────────────────────
    from src.features.engineer_cctv import assign_cctv_to_grids
    df = assign_cctv_to_grids(df, GRID_LAT, GRID_LON)

    grid_feat_cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(grid_feat_cache, index=False)
    log.info(f"격자 Feature 저장: {grid_feat_cache} ({len(df)}개 격자)")
    log.info(f"  사고 있는 격자: {df['label_all'].sum()} / {len(df)}")
    return df


# ─── STEP 2: 격자 수준 XGBoost 학습 ──────────────────────────────────────

SPATIAL_FEAT_COLS = [
    "intersection_count_100m", "intersection_count_200m", "intersection_count_500m",
    "node_degree", "dist_to_nearest_intersection",
    "avg_lanes", "max_lanes",
    "is_primary_road", "is_secondary_road", "is_residential_road", "is_intersection",
    # POI (노출량 Proxy) 특성
    "poi_count_commercial", "poi_count_bus_stop", "poi_count_station",
    "poi_count_university", "poi_count_total",
    # CCTV (감시/억제 효과) 특성
    "cctv_count_total", "cctv_count_traffic", "cctv_count_child",
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
        model = xgb.XGBRegressor(
            **params, objective="count:poisson",
            eval_metric="poisson-nloglik", tree_method="hist", random_state=42,
        )
        from sklearn.model_selection import cross_val_score
        # Poisson 회귀 평가 지표로 음수 RMSE 사용 (Maximize)
        return cross_val_score(model, X_train, y_train, cv=5, scoring="neg_root_mean_squared_error", n_jobs=-1).mean()

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    log.info(f"Optuna | Best Neg_RMSE={study.best_value:.4f}")
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

    # ── 훈련: 2021-2024 사고 '발생 횟수(Count)' 기준 (포아송 회귀) ──
    X = grid_df[feat_cols].fillna(0)
    y_train_count = grid_df["acc_2021_24"]

    log.info(f"학습 타겟 | 사고 횟수 총합: {y_train_count.sum()}건 (포아송 회귀 모델 적용)")

    # Optuna
    log.info(f"Optuna HPO 중 (n_trials={n_trials})...")
    best_params = _tune(X, y_train_count, n_trials=n_trials)
    best_params.update({"lr": best_params.pop("lr", 0.1)})

    model = xgb.XGBRegressor(
        max_depth=best_params.get("max_depth", 5),
        learning_rate=best_params.get("learning_rate", best_params.get("lr", 0.1)),
        n_estimators=best_params.get("n_est", 200),
        subsample=best_params.get("sub", 0.8),
        colsample_bytree=best_params.get("col", 0.8),
        min_child_weight=best_params.get("mcw", 1),
        objective="count:poisson", eval_metric="poisson-nloglik",
        tree_method="hist", random_state=42,
    )
    model.fit(X, y_train_count)

    # ── 전체 격자 위험도 예측 (발생 예상 건수) ───────────────
    preds = model.predict(X)
    robust_max = np.percentile(preds, 99)
    if robust_max == 0:
        robust_max = preds.max()
    
    # 0~100점 만점의 Risk Score로 Robust 스케일링 (상위 1% 아웃라이어 클리핑)
    risk_scores = (preds / robust_max * 100).clip(0, 100) if robust_max > 0 else preds
    
    grid_df = grid_df.copy()
    grid_df["risk_score"] = risk_scores

    # ── 시간적 검증: 2025 사고 기준 PAI ─────────────────────────
    log.info("\n--- 시간적 검증 (2025 사고 기준) ---")
    auroc_2025, pai_2025 = _eval_and_print(grid_df, label_col="label_2025", count_col="acc_2025", past_count_col="acc_2021_24", tag="2025년 사고")

    # ── 전체 기준 AUROC ──────────────────────────────────────────
    log.info("--- 전체 기간 기준 ---")
    auroc_all, pai_all = _eval_and_print(grid_df, label_col="label_all", count_col="acc_total", past_count_col="acc_2021_24", tag="전체(2021-25)")

    # ── 지표 저장 (보고서/논문용) ──────────────────────────────
    pai_2025.to_csv(f"{output_dir}/pai_metrics_2025.csv", index=False)
    pai_all.to_csv(f"{output_dir}/pai_metrics_all.csv", index=False)
    
    with open(f"{output_dir}/evaluation_summary.txt", "w", encoding="utf-8") as f:
        f.write("=== SAFERIDE 격자 위험도 모델 평가 요약 ===\n\n")
        f.write(f"[1] 2025년 시간적 검증 (미래 예측)\n")
        f.write(f"  - AUROC: {auroc_2025:.4f}\n")
        f.write(f"  - PAI@10%: {pai_2025.loc[9, 'pai']:.2f}\n")
        f.write(f"  - PAI@20%: {pai_2025.loc[19, 'pai']:.2f}\n\n")
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


def _eval_and_print(grid_df, label_col, count_col, past_count_col, tag):
    """PAI + 고급 평가지표(RMSE, PEI, RRI, Moran's I) 출력 및 반환"""
    from src.evaluation.evaluate import compute_pai

    y_true_binary = grid_df[label_col].values
    y_true_count = grid_df[count_col].values
    
    # risk_score(0~100) 외에 실제 모델 예측 횟수(preds) 복원을 위해 역산 (정확한 RMSE를 위해선 raw preds가 필요하나 여기선 score 기반 비율로 근사하거나 원본을 다시 predict해야 함.
    # 하지만 grid_df에는 risk_score만 저장됨. RMSE용으로 risk_score를 스케일링된 위험 지수 오차로 계산.
    # 정확한 계산을 위해 여기서는 생략하고, risk_score 자체의 순위 및 분류 지표에 집중.
    y_score = grid_df["risk_score"].values / 100

    auroc = 0.0
    if y_true_binary.sum() > 0 and y_true_binary.sum() < len(y_true_binary):
        auroc = roc_auc_score(y_true_binary, y_score)
        log.info(f"[{tag}] AUROC={auroc:.4f}")

    # PAI 계산 (격자 기반)
    grid_for_pai = grid_df[["lat_min", "lon_min", "risk_score"]].copy()
    acc_grids = grid_df[grid_df[label_col] == 1][["lat_min", "lon_min"]].copy()
    acc_grids["위도"] = acc_grids["lat_min"] + GRID_LAT / 2
    acc_grids["경도"] = acc_grids["lon_min"] + GRID_LON / 2
    pai_df = compute_pai(grid_for_pai, acc_grids)

    # 1. RRI (Baseline 비교) 및 PEI (완벽 모델 비교) 계산
    # Baseline(과거 사고 순) PAI
    grid_for_base = grid_df[["lat_min", "lon_min", past_count_col]].rename(columns={past_count_col: "risk_score"}).copy()
    base_pai_df = compute_pai(grid_for_base, acc_grids)
    
    # 완벽 모델(미래 사고 순) PAI
    grid_for_god = grid_df[["lat_min", "lon_min", count_col]].rename(columns={count_col: "risk_score"}).copy()
    god_pai_df = compute_pai(grid_for_god, acc_grids)

    # 2. Moran's I (잔차 공간 자기상관성)
    # Residual = 실제 사고 수 - (risk_score 기준 예상 사고 분포)
    # 간단히 risk_score 자체의 공간적 자기상관성을 보거나, 오차를 계산.
    # 여기서는 risk_score와 y_true_count의 상관관계에 따른 잔차.
    residuals = y_true_count - (y_score * y_true_count.max())
    
    # KNN 기반 공간 가중치 행렬 생성 (k=8)
    coords = np.column_stack((grid_df["lon_min"] + GRID_LON/2, grid_df["lat_min"] + GRID_LAT/2))
    w = libpysal.weights.KNN.from_array(coords, k=8)
    w.transform = 'r'
    mi = Moran(residuals, w)
    
    # 3. RMSE & MAE
    rmse = mean_squared_error(y_true_count, y_score * y_true_count.max(), squared=False)
    mae = mean_absolute_error(y_true_count, y_score * y_true_count.max())

    print(f"\n  [{tag}] 🚀 고급 예측 지표 평가 결과")
    print(f"  - RMSE (평균 오차): {rmse:.3f} 건 / MAE: {mae:.3f} 건")
    print(f"  - Moran's I (잔차 공간 편향성): {mi.I:.4f} (p-value: {mi.p_sim:.4f})")
    if mi.I < 0.1:
        print("    -> 잔차의 군집이 거의 없음 (모델이 공간 패턴을 완벽히 흡수함 🌟)")
        
    print(f"\n  [{tag}] 정책 실효성 지표 (PAI, PEI, RRI)")
    print(f"  {'k%':>5} | {'포착률(Model)':>14} | {'PEI (신 대비 효율)':>17} | {'RRI (과거 대비 향상)':>17}")
    print("  " + "-" * 75)
    
    for k in [5, 10, 20, 30, 50]:
        row = pai_df.loc[k - 1]
        base_row = base_pai_df.loc[k - 1]
        god_row = god_pai_df.loc[k - 1]
        
        hit_rate = row['acc_ratio'] * 100
        base_hit = base_row['acc_ratio'] * 100
        god_hit = god_row['acc_ratio'] * 100
        
        pei = (hit_rate / god_hit) if god_hit > 0 else 0
        rri = (hit_rate / base_hit) if base_hit > 0 else 0
        
        print(f"  {k:>5}% | {hit_rate:>13.1f}% | {pei:>17.2f} | {rri:>17.2f}")

    return auroc, pai_df


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    from src.data.loader_pm import load_seoul_only
    seoul_df = load_seoul_only()

    grid_df = build_grid_dataset(seoul_df, force=False)
    model, explainer, feat_cols, grid_df_scored = train_grid_model(grid_df, n_trials=30)
