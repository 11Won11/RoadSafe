"""
서울 전체 격자 위험도 예측 (사고 미발생 지점 포함)
- 서울을 ~500m 격자로 나누어 각 격자 중심점의 공간 Feature 추출
- 학습된 XGBoost 모델로 위험도 점수(0~100) 예측
- data/interim/grid_risk_scores.csv 에 캐싱
"""
import numpy as np
import pandas as pd
import osmnx as ox
import logging
from pathlib import Path
from shapely.geometry import box

log = logging.getLogger(__name__)

GRID_CACHE = Path("data/interim/grid_risk_scores.csv")
GRAPH_CACHE = Path("data/interim/seoul_graph.graphml")

# 서울 바운딩박스
SEOUL_BBOX = dict(lat_min=37.413, lat_max=37.715, lon_min=126.734, lon_max=127.270)
GRID_LAT = 0.0045   # ~500m
GRID_LON = 0.0056   # ~500m

# 카테고리 기본값 (맑음, 건조, 기타 등 가장 일반적인 상황)
DEFAULT_FEATURE_VALS = {
    "weather_code": 0,      # 맑음
    "road_type_code": 0,    # 단일로-기타
    "surface_code": 0,      # 건조
    "is_intersection": 0,   # OSMnx 데이터로 덮어씀
    "is_daytime": 1,        # 주간
}


def _extract_spatial_features(lat: float, lon: float, G, nodes) -> dict:
    """단일 격자 중심점의 OSMnx 공간 Feature 추출 (engineer_point.py 공유 로직)"""
    feat = {}
    BUFFERS = [100, 200, 500]
    try:
        for r in BUFFERS:
            nearby = nodes[
                ((nodes["y"] - lat).abs() < r / 111000) &
                ((nodes["x"] - lon).abs() < r / 88000)
            ]
            feat[f"intersection_count_{r}m"] = len(nearby)

        nearest_node = ox.distance.nearest_nodes(G, lon, lat)
        feat["node_degree"] = G.degree(nearest_node)

        # 최근접 교차로까지 거리
        inter_nodes = [n for n, d in G.degree() if d >= 3]
        if inter_nodes:
            cands = inter_nodes[:min(50, len(inter_nodes))]
            dists = [
                ((G.nodes[n]["y"] - lat) ** 2 + (G.nodes[n]["x"] - lon) ** 2) ** 0.5 * 111000
                for n in cands
            ]
            feat["dist_to_nearest_intersection"] = min(dists)
        else:
            feat["dist_to_nearest_intersection"] = 9999

        # 도로 등급 / 차선 수
        edges_from = list(G.edges(nearest_node, data=True))
        if edges_from:
            lanes = []
            for e in edges_from:
                try:
                    l = e[2].get("lanes", 1)
                    lanes.append(int(l) if not isinstance(l, list) else int(l[0]))
                except:
                    lanes.append(1)
            feat["avg_lanes"] = float(np.mean(lanes))
            feat["max_lanes"] = float(max(lanes))
            htypes = [e[2].get("highway", "") for e in edges_from]
            feat["is_primary_road"] = int(any("primary" in str(h) for h in htypes))
            feat["is_secondary_road"] = int(any("secondary" in str(h) for h in htypes))
            feat["is_residential_road"] = int(any("residential" in str(h) or "service" in str(h) for h in htypes))
            # 교차로 여부: 연결 도로 3개 이상
            feat["is_intersection"] = int(feat["node_degree"] >= 3)
        else:
            feat.update({"avg_lanes": 1, "max_lanes": 1,
                         "is_primary_road": 0, "is_secondary_road": 0,
                         "is_residential_road": 0, "is_intersection": 0})
    except Exception:
        for r in BUFFERS:
            feat.setdefault(f"intersection_count_{r}m", 0)
        feat.setdefault("node_degree", 0)
        feat.setdefault("dist_to_nearest_intersection", 9999)
        feat.setdefault("avg_lanes", 1)
        feat.setdefault("max_lanes", 1)
        feat.setdefault("is_primary_road", 0)
        feat.setdefault("is_secondary_road", 0)
        feat.setdefault("is_residential_road", 0)
        feat.setdefault("is_intersection", 0)
    return feat


def predict_grid_risk(model, feature_names: list, force: bool = False) -> pd.DataFrame:
    """
    서울 전체 격자 중심점에 대해 공간 위험도 점수 예측.
    캐시가 있으면 즉시 반환.

    Returns:
        DataFrame with columns: lat, lon, lat_min, lon_min, risk_score
    """
    if GRID_CACHE.exists() and not force:
        log.info(f"격자 위험도 캐시 로드: {GRID_CACHE}")
        return pd.read_csv(GRID_CACHE)

    log.info("서울 전체 격자 위험도 예측 시작...")

    # 도로망 로드
    if GRAPH_CACHE.exists():
        log.info("도로망 그래프 캐시 로드 중...")
        G = ox.load_graphml(GRAPH_CACHE)
    else:
        log.info("서울시 도로망 다운로드 중... (1~3분)")
        G = ox.graph_from_place("Seoul, South Korea", network_type="drive")
        GRAPH_CACHE.parent.mkdir(parents=True, exist_ok=True)
        ox.save_graphml(G, GRAPH_CACHE)

    nodes, _ = ox.graph_to_gdfs(G)

    # 격자 중심점 목록 생성
    grid_points = []
    lat = SEOUL_BBOX["lat_min"]
    while lat < SEOUL_BBOX["lat_max"]:
        lon = SEOUL_BBOX["lon_min"]
        while lon < SEOUL_BBOX["lon_max"]:
            cy = lat + GRID_LAT / 2
            cx = lon + GRID_LON / 2
            grid_points.append((lat, lon, cy, cx))
            lon += GRID_LON
        lat += GRID_LAT

    total = len(grid_points)
    log.info(f"격자 수: {total}개 | Feature 추출 중...")

    records = []
    for i, (lat_min, lon_min, cy, cx) in enumerate(grid_points):
        if i % 200 == 0:
            log.info(f"  진행 중: {i}/{total}")
        spatial = _extract_spatial_features(cy, cx, G, nodes)
        records.append({"lat": cy, "lon": cx, "lat_min": lat_min, "lon_min": lon_min, **spatial})

    spatial_df = pd.DataFrame(records)

    # 카테고리 Feature 채우기 (학습 시 기본값 적용)
    for col, val in DEFAULT_FEATURE_VALS.items():
        spatial_df[col] = val
        # is_intersection은 OSMnx에서 계산한 값 우선
        if col == "is_intersection" and "is_intersection" in spatial_df.columns:
            pass  # 이미 위에서 설정됨

    # 법규위반 더미 컬럼 (학습 시 존재했던 컬럼들, 기본값 0)
    viol_cols = [c for c in feature_names if c.startswith("viol_")]
    for c in viol_cols:
        spatial_df[c] = 0

    # feature_names 순서에 맞게 컬럼 정렬 (누락 컬럼은 0)
    for col in feature_names:
        if col not in spatial_df.columns:
            spatial_df[col] = 0
    X_grid = spatial_df[feature_names].fillna(0)

    # 위험도 예측
    log.info("XGBoost 위험도 예측 중...")
    proba = model.predict_proba(X_grid)[:, 1]
    spatial_df["risk_score"] = (proba * 100).clip(0, 100)

    # 캐시 저장
    GRID_CACHE.parent.mkdir(parents=True, exist_ok=True)
    spatial_df[["lat", "lon", "lat_min", "lon_min", "risk_score"]].to_csv(GRID_CACHE, index=False)
    log.info(f"격자 위험도 저장 완료: {GRID_CACHE} ({len(spatial_df)}개 격자)")

    return spatial_df[["lat", "lon", "lat_min", "lon_min", "risk_score"]]
