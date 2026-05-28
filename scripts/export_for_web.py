"""
웹 대시보드용 정적 데이터 내보내기 스크립트
모델 예측 결과 → GeoJSON + JSON 파일 생성 (React 앱에서 직접 사용)
"""
import json
import pickle
import pandas as pd
import numpy as np
import logging
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

WEB_DATA_DIR = Path("web/public/data")
WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)

GRID_LAT = 0.0045
GRID_LON = 0.0056

RISK_FEAT_COLS = [
    "intersection_count_100m", "intersection_count_200m", "intersection_count_500m",
    "node_degree", "dist_to_nearest_intersection",
    "avg_lanes", "max_lanes",
    "is_primary_road", "is_secondary_road", "is_residential_road", "is_intersection",
    "poi_count_commercial", "poi_count_bus_stop", "poi_count_station",
    "poi_count_university",
    "cctv_count_total", "cctv_count_traffic", "cctv_count_child",
    "elev_mean", "elev_range",
    "signal_count_total", "signal_count_pedestrian", "signal_count_vehicle",
    "signal_has_audio", "crosswalk_count", "towing_count"
]


def _build_gu_lookup(boundary_path="web/public/data/seoul_boundary.geojson"):
    """서울 구 경계 GeoJSON 기반으로 포인트-인-폴리곤 검색 준비"""
    import geopandas as gpd
    gdf = gpd.read_file(boundary_path)
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    return gdf[["name", "geometry"]].rename(columns={"name": "gu_name"})


def export_grid_geojson():
    """격자별 위험도 예측값 → GeoJSON (구 이름은 경계 폴리곤 기반 정확 매핑)"""
    import geopandas as gpd
    from shapely.geometry import Point

    log.info("격자 데이터 로드 및 GeoJSON 변환 중...")
    df = pd.read_csv("data/interim/grid_features_with_labels_seoul.csv")

    # 모델 로드
    model_path = Path("data/interim/xgb_grid_model.pkl")
    with open(model_path, "rb") as f:
        obj = pickle.load(f)
    model = obj["model"] if isinstance(obj, dict) else obj

    # 노출량 0 구역 필터
    valid_mask = df["intersection_count_500m"] > 0
    df_valid = df[valid_mask].copy()

    X = df_valid[RISK_FEAT_COLS].fillna(0)
    df_valid["risk_score"] = model.predict(X)

    # 정규화 (0 ~ 100)
    rmin = df_valid["risk_score"].min()
    rmax = df_valid["risk_score"].max()
    df_valid["risk_pct"] = ((df_valid["risk_score"] - rmin) / (rmax - rmin) * 100).round(1)

    # 위험 등급 분류
    def classify_risk(p):
        if p >= 80: return "very_high"
        if p >= 60: return "high"
        if p >= 40: return "medium"
        if p >= 20: return "low"
        return "very_low"

    df_valid["risk_level"] = df_valid["risk_pct"].apply(classify_risk)

    # 구 경계 GeoJSON 을 사용한 정확한 포인트-인-폴리곤 건스 매핑
    log.info("구 경계 기반 공간 조인 중 (geopandas sjoin)...")
    gu_gdf = _build_gu_lookup()
    grid_geom = [Point(row["cx"], row["cy"]) for _, row in df_valid.iterrows()]
    grid_gdf = gpd.GeoDataFrame(df_valid.reset_index(drop=True), geometry=grid_geom, crs="EPSG:4326")
    joined = gpd.sjoin(grid_gdf, gu_gdf, how="left", predicate="within")
    
    # 중복 제거 (경계선에 걸친 격자가 여러 구에 조인되는 문제 방지)
    joined = joined[~joined.index.duplicated(keep="first")]
    
    # 엄격한 포함 판정으로 매핑되지 않은 격자는 nearest 방식으로 안전망
    unmatched = joined["gu_name"].isna()
    if unmatched.sum() > 0:
        log.info(f"⚠️  매핑 안된 격자 {unmatched.sum()}개 → nearest 구로 보완")
        joined_nearest = gpd.sjoin_nearest(grid_gdf[unmatched], gu_gdf, how="left")
        joined_nearest = joined_nearest[~joined_nearest.index.duplicated(keep="first")]
        joined.loc[unmatched, "gu_name"] = joined_nearest["gu_name"].values
        
    df_valid["gu_name"] = joined["gu_name"].fillna("서울시").values
    log.info(f"구 매핑 완료: {df_valid['gu_name'].nunique()}개 구")

    # GeoJSON Feature 목록 생성
    features = []
    for _, row in df_valid.iterrows():
        lat_min, lon_min = row["lat_min"], row["lon_min"]
        lat_max = lat_min + GRID_LAT
        lon_max = lon_min + GRID_LON
        # GeoJSON 폴리곤 (시계방향)
        coords = [[
            [lon_min, lat_min],
            [lon_max, lat_min],
            [lon_max, lat_max],
            [lon_min, lat_max],
            [lon_min, lat_min],
        ]]
        cy_val = float(row["cy"])
        cx_val = float(row["cx"])
        feature = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": coords},
            "properties": {
                "risk_pct":       round(float(row["risk_pct"]), 1),
                "risk_level":     row["risk_level"],
                "acc_total":      int(row.get("acc_total", 0)),
                "acc_2025":       int(row.get("acc_2025", 0)),
                "cx":             round(cx_val, 6),
                "cy":             round(cy_val, 6),
                "gu_name":        row["gu_name"],
                "cctv_total":     int(row.get("cctv_count_total", 0)),
                "elev_range":     round(float(row.get("elev_range", 0)), 1),
                "avg_lanes":      round(float(row.get("avg_lanes", 0)), 1),
                "poi_commercial": int(row.get("poi_count_commercial", 0)),
                "intersect_500":  int(row.get("intersection_count_500m", 0)),
                "towing_cnt":     int(row.get("towing_count", 0)),
                "crosswalk_cnt":  int(row.get("crosswalk_count", 0)),
                "signal_total":   int(row.get("signal_count_total", 0)),
            }
        }
        features.append(feature)

    geojson = {"type": "FeatureCollection", "features": features}
    out_path = WEB_DATA_DIR / "grid_predictions.geojson"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, separators=(",", ":"))
    log.info(f"GeoJSON 저장: {out_path} ({len(features)}개 격자)")
    return df_valid




def export_shap_importance():
    """SHAP Feature Importance → JSON"""
    log.info("SHAP 데이터 내보내기 중...")
    import shap, pickle

    df = pd.read_csv("data/interim/grid_features_with_labels_seoul.csv")
    valid_mask = df["intersection_count_500m"] > 0
    df_valid = df[valid_mask].copy()
    X = df_valid[RISK_FEAT_COLS].fillna(0)

    with open("data/interim/xgb_grid_model.pkl", "rb") as f:
        obj = pickle.load(f)
    model = obj["model"] if isinstance(obj, dict) else obj

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    feature_labels = {
        "intersection_count_100m":       "반경 100m 교차로 수",
        "intersection_count_200m":       "반경 200m 교차로 수",
        "intersection_count_500m":       "반경 500m 교차로 수",
        "node_degree":                   "도로 노드 연결 차수",
        "dist_to_nearest_intersection":  "최근 교차로까지 거리",
        "avg_lanes":                     "평균 차선 수",
        "max_lanes":                     "최대 차선 수",
        "is_primary_road":               "간선도로 여부",
        "is_secondary_road":             "집산도로 여부",
        "is_residential_road":           "이면도로 여부",
        "is_intersection":               "교차로 존재 여부",
        "poi_count_commercial":          "상업시설 수",
        "poi_count_bus_stop":            "버스 정류장 수",
        "poi_count_station":             "지하철역 수",
        "poi_count_university":          "대학교 수",
        "cctv_count_total":              "CCTV 전체 수",
        "cctv_count_traffic":            "교통단속 CCTV",
        "cctv_count_child":              "어린이보호 CCTV",
        "elev_mean":                     "평균 표고 (m)",
        "elev_range":                    "경사도 (표고 범위)",
        "signal_count_total":            "신호등 전체 수",
        "signal_count_pedestrian":       "보행자 신호등 수",
        "signal_count_vehicle":          "차량 신호등 수",
        "signal_has_audio":              "음향 신호기 수",
        "crosswalk_count":               "횡단보도 수",
        "towing_count":                  "킥보드 견인 수",
    }

    shap_data = sorted([
        {
            "feature": RISK_FEAT_COLS[i],
            "label":   feature_labels.get(RISK_FEAT_COLS[i], RISK_FEAT_COLS[i]),
            "value":   round(float(mean_abs_shap[i]), 4)
        }
        for i in range(len(RISK_FEAT_COLS))
    ], key=lambda x: x["value"], reverse=True)

    out_path = WEB_DATA_DIR / "shap_importance.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(shap_data, f, ensure_ascii=False, indent=2)
    log.info(f"SHAP JSON 저장: {out_path}")


def export_metrics():
    """핵심 평가 지표 → JSON"""
    log.info("평가 지표 내보내기 중...")

    metrics = {
        "auroc_2025":   0.7950,
        "auroc_all":    0.8757,
        "auroc_busan":  0.9105,
        "mae_2025":     0.810,
        "rmse_2025":    1.159,
        "pai_table_2025": [
            {"k": 5,  "capture": 14.6, "rri": 0.68},
            {"k": 10, "capture": 26.4, "rri": 0.82},
            {"k": 20, "capture": 49.8, "rri": 0.94},
            {"k": 30, "capture": 65.9, "rri": 0.97},
            {"k": 50, "capture": 92.3, "rri": 1.19},
        ],
        "pai_table_busan": [
            {"k": 10, "capture": 56.4},
            {"k": 20, "capture": 72.1},
        ],
        "feature_count":    26,
        "grid_count":       2426,
        "accident_count":   2132,
        "high_risk_grids":  38,
    }

    out_path = WEB_DATA_DIR / "metrics_summary.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    log.info(f"지표 JSON 저장: {out_path}")


if __name__ == "__main__":
    log.info("=== 웹 대시보드용 데이터 내보내기 시작 ===")
    export_grid_geojson()
    export_shap_importance()
    export_metrics()
    log.info(f"=== 완료! 저장 위치: {WEB_DATA_DIR} ===")
