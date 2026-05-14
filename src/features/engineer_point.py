"""
Phase 2 지점 단위 공간 Feature 추출 (OSMnx 반경별 버퍼 분석)
Chengula et al.(2024) 방법론 기반
"""
import numpy as np
import pandas as pd
import osmnx as ox
import logging
from pathlib import Path
from shapely.geometry import Point

log = logging.getLogger(__name__)

CACHE_PATH = Path("data/interim/point_features.csv")
GRAPH_CACHE_PATH = Path("data/interim/seoul_graph.graphml")

# 분석 반경 (미터 단위)
BUFFERS = [100, 200, 500]

# 카테고리 인코딩 맵
WEATHER_MAP = {"맑음": 0, "흐림": 1, "비": 2, "눈": 3, "기타": 4}
ROAD_MAP = {
    "단일로 - 기타": 0,
    "교차로 - 교차로안": 1,
    "교차로 - 교차로부근": 2,
    "교차로 - 교차로횡단보도내": 3,
    "기타 - 기타": 4,
    "단일로 - 지하차도(도로)내": 5,
    "단일로 - 교량": 6,
    "주차장 - 주차장": 7,
    "단일로 - 터널": 8,
}
SURFACE_MAP = {"건조": 0, "습기": 1, "서리/결빙": 2, "침수": 3, "기타": 4}


def _load_graph():
    if GRAPH_CACHE_PATH.exists():
        log.info("도로망 그래프 캐시 로드 중...")
        return ox.load_graphml(GRAPH_CACHE_PATH)
    log.info("서울시 도로망 다운로드 중... (1~3분 소요)")
    G = ox.graph_from_place("Seoul, South Korea", network_type="drive")
    GRAPH_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(G, GRAPH_CACHE_PATH)
    return G


def _extract_point_features(lat: float, lon: float, G, nodes) -> dict:
    """단일 지점(lat, lon)에 대한 OSMnx 기반 공간 Feature 딕셔너리 반환"""
    feat = {}
    try:
        # 반경별 교차로 수 카운트
        for r in BUFFERS:
            nearby = nodes[
                ((nodes["y"] - lat).abs() < r / 111000) &
                ((nodes["x"] - lon).abs() < r / 88000)
            ]
            feat[f"intersection_count_{r}m"] = len(nearby)

        # 가장 가까운 노드 찾기
        nearest_node = ox.distance.nearest_nodes(G, lon, lat)
        node_data = G.nodes[nearest_node]

        # 연결 도로 수 (degree)
        feat["node_degree"] = G.degree(nearest_node)

        # 가장 가까운 교차로까지의 거리 (degree >= 3인 노드 = 교차로)
        intersection_nodes = [n for n, d in G.degree() if d >= 3]
        if intersection_nodes:
            nearest_inter = ox.distance.nearest_nodes(
                G,
                [lon] * min(10, len(intersection_nodes)),
                [lat] * min(10, len(intersection_nodes)),
            )
            inter_node = G.nodes[nearest_inter] if not isinstance(nearest_inter, list) else G.nodes[nearest_inter[0]]
            dist = ((inter_node["y"] - lat) ** 2 + (inter_node["x"] - lon) ** 2) ** 0.5 * 111000
            feat["dist_to_nearest_intersection"] = dist
        else:
            feat["dist_to_nearest_intersection"] = 9999

        # 연결된 엣지(도로)의 속성
        edges_from_node = list(G.edges(nearest_node, data=True))
        if edges_from_node:
            lanes = [e[2].get("lanes", 1) for e in edges_from_node]
            lanes_numeric = []
            for l in lanes:
                try:
                    lanes_numeric.append(int(l) if not isinstance(l, list) else int(l[0]))
                except:
                    lanes_numeric.append(1)
            feat["avg_lanes"] = np.mean(lanes_numeric)
            feat["max_lanes"] = max(lanes_numeric)

            # 도로 등급 (highway 속성)
            highway_types = [e[2].get("highway", "unclassified") for e in edges_from_node]
            primary = any("primary" in str(h) for h in highway_types)
            secondary = any("secondary" in str(h) for h in highway_types)
            residential = any("residential" in str(h) or "service" in str(h) for h in highway_types)
            feat["is_primary_road"] = int(primary)
            feat["is_secondary_road"] = int(secondary)
            feat["is_residential_road"] = int(residential)
        else:
            feat.update({"avg_lanes": 1, "max_lanes": 1,
                         "is_primary_road": 0, "is_secondary_road": 0, "is_residential_road": 0})

    except Exception as e:
        # 추출 실패 시 기본값
        for r in BUFFERS:
            feat.setdefault(f"intersection_count_{r}m", 0)
        feat.setdefault("node_degree", 0)
        feat.setdefault("dist_to_nearest_intersection", 9999)
        feat.setdefault("avg_lanes", 1)
        feat.setdefault("max_lanes", 1)
        feat.setdefault("is_primary_road", 0)
        feat.setdefault("is_secondary_road", 0)
        feat.setdefault("is_residential_road", 0)

    return feat


def engineer_point_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    전체 DataFrame의 각 행(지점)에 대한 OSMnx 공간 Feature 추출 + 기존 카테고리 인코딩.
    캐시가 있으면 즉시 반환.
    """
    if CACHE_PATH.exists():
        log.info(f"지점 Feature 캐시 발견: {CACHE_PATH}")
        return pd.read_csv(CACHE_PATH)

    log.info(f"지점 단위 OSMnx Feature 추출 시작 (총 {len(df)}개 지점)...")
    G = _load_graph()
    nodes, _ = ox.graph_to_gdfs(G)

    spatial_feats = []
    for i, (_, row) in enumerate(df.iterrows()):
        if i % 100 == 0:
            log.info(f"  진행 중: {i}/{len(df)}")
        feat = _extract_point_features(row["위도"], row["경도"], G, nodes)
        spatial_feats.append(feat)

    spatial_df = pd.DataFrame(spatial_feats)
    df = df.reset_index(drop=True)

    # ── 카테고리 Feature 인코딩 ──────────────────────────────────
    df["weather_code"] = df["기상상태"].map(WEATHER_MAP).fillna(4).astype(int)
    df["road_type_code"] = df["도로형태"].map(ROAD_MAP).fillna(4).astype(int)

    if "노면상태" in df.columns:
        df["surface_code"] = df["노면상태"].map(SURFACE_MAP).fillna(4).astype(int)
    else:
        df["surface_code"] = 0

    # is_intersection: 교차로 관련 도로형태
    df["is_intersection"] = df["도로형태"].str.contains("교차로", na=False).astype(int)

    # 법규위반 One-Hot (상위 빈도만)
    violation_dummies = pd.get_dummies(df["법규위반"].fillna("기타"), prefix="viol")

    # ── 최종 Feature 병합 ────────────────────────────────────────
    feature_cols = ["is_hotspot", "is_daytime", "weather_code", "road_type_code",
                    "surface_code", "is_intersection"]
    result = pd.concat([
        df[feature_cols],
        violation_dummies,
        spatial_df
    ], axis=1)

    # 캐시 저장
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(CACHE_PATH, index=False)
    log.info(f"지점 Feature 캐시 저장: {CACHE_PATH}")
    log.info(f"Feature Engineering 완료: {result.shape[1]}개 feature, {len(result)}개 지점")

    return result


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    from src.data.loader_pm import load_pm_data
    from src.data.negative_sampler import generate_negative_samples

    pos_df = load_pm_data()
    neg_df = generate_negative_samples(pos_df)
    combined = pd.concat([pos_df, neg_df], ignore_index=True)
    features = engineer_point_features(combined)
    print(f"\nFeature shape: {features.shape}")
    print(features.dtypes)
