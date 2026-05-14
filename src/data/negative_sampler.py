"""
Phase 2 음성 샘플 생성 (3단계 매칭 샘플링)
보고서 4.3절 기반: 공간 편향 없는 비사고 지점 생성
"""
import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox
import logging
from pathlib import Path
from shapely.geometry import Point

log = logging.getLogger(__name__)

CACHE_PATH = Path("data/interim/negative_samples.csv")
GRAPH_CACHE_PATH = Path("data/interim/seoul_graph.graphml")

def _load_or_download_graph():
    """서울 도로망 그래프 로드 (캐시 우선)"""
    if GRAPH_CACHE_PATH.exists():
        log.info("도로망 그래프 캐시 로드 중...")
        G = ox.load_graphml(GRAPH_CACHE_PATH)
    else:
        log.info("서울시 도로망 다운로드 중... (1~3분 소요)")
        G = ox.graph_from_place("Seoul, South Korea", network_type="drive")
        GRAPH_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        ox.save_graphml(G, GRAPH_CACHE_PATH)
        log.info(f"도로망 그래프 저장: {GRAPH_CACHE_PATH}")
    return G

def _haversine_dist(lat1, lon1, lat2_arr, lon2_arr):
    """단일 기준점 (lat1, lon1)에서 배열까지의 거리(m) 계산"""
    R = 6371000
    phi1, phi2 = np.radians(lat1), np.radians(lat2_arr)
    dphi = np.radians(lat2_arr - lat1)
    dlam = np.radians(lon2_arr - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

def generate_negative_samples(positive_df: pd.DataFrame) -> pd.DataFrame:
    """
    3단계 매칭 샘플링으로 음성 샘플(비사고 지점) 생성.
    양성 샘플 수와 동일한 개수(1:1)를 반환.
    """
    if CACHE_PATH.exists():
        log.info(f"음성 샘플 캐시 발견: {CACHE_PATH}")
        return pd.read_csv(CACHE_PATH)

    target_n = len(positive_df)
    log.info(f"음성 샘플 생성 시작 (목표: {target_n}개)")

    # ── 도로망 로드 ──────────────────────────────────────────────
    G = _load_or_download_graph()
    nodes, edges = ox.graph_to_gdfs(G)

    # 도로 엣지의 중심점을 후보 포인트로 사용
    edges = edges.copy()
    edges["centroid"] = edges.geometry.centroid
    candidate_lats = edges["centroid"].y.values
    candidate_lons = edges["centroid"].x.values

    pos_lats = positive_df["위도"].values
    pos_lons = positive_df["경도"].values

    # ── STEP 1: 공간 이격 필터 (500m 이상) ──────────────────────
    log.info("STEP 1: 공간 이격 필터 적용 (모든 사고 지점에서 500m 이상)...")
    valid_mask = np.ones(len(candidate_lats), dtype=bool)
    for lat, lon in zip(pos_lats, pos_lons):
        dists = _haversine_dist(lat, lon, candidate_lats, candidate_lons)
        valid_mask &= (dists >= 500)

    filtered_lats = candidate_lats[valid_mask]
    filtered_lons = candidate_lons[valid_mask]
    log.info(f"  → 후보 {valid_mask.sum():,}개 남음")

    # ── STEP 2: 도로 유형 매칭 ───────────────────────────────────
    # 도로형태 분포 추출
    road_type_dist = positive_df["도로형태"].value_counts(normalize=True)
    log.info(f"STEP 2: 도로 유형 분포 매칭...")

    # ── STEP 3: 시군구 분포 매칭 ─────────────────────────────────
    # 시군구별 양성 샘플 비율 계산
    gu_dist = positive_df["시군구"].value_counts(normalize=True)

    # 서울시 구 GeoJSON 로드
    import requests, json
    geojson_url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"
    r = requests.get(geojson_url)
    seoul_geo = gpd.GeoDataFrame.from_features(r.json()["features"])
    seoul_geo.set_crs(epsg=4326, inplace=True)
    seoul_geo.rename(columns={"name": "gu_name"}, inplace=True)

    # 후보 포인트를 GeoDataFrame으로 변환하여 공간 조인
    log.info("STEP 3: 시군구 분포 매칭 (공간 조인)...")
    candidate_gdf = gpd.GeoDataFrame(
        {"위도": filtered_lats, "경도": filtered_lons},
        geometry=[Point(lon, lat) for lat, lon in zip(filtered_lats, filtered_lons)],
        crs="EPSG:4326"
    )
    candidate_gdf = gpd.sjoin(candidate_gdf, seoul_geo[["gu_name", "geometry"]], how="inner", predicate="within")

    # ── 최종 샘플링: 구 비율에 맞게 추출 ────────────────────────
    sampled_parts = []
    for gu_name, ratio in gu_dist.items():
        n_needed = max(1, int(round(target_n * ratio)))
        subset = candidate_gdf[candidate_gdf["gu_name"].str.contains(gu_name.replace("서울특별시 ", ""), na=False)]
        if len(subset) == 0:
            continue
        n_sample = min(n_needed, len(subset))
        sampled_parts.append(subset.sample(n=n_sample, random_state=42))

    neg_df = pd.concat(sampled_parts, ignore_index=True)

    # 목표 수에 맞게 조정
    if len(neg_df) > target_n:
        neg_df = neg_df.sample(n=target_n, random_state=42)
    elif len(neg_df) < target_n:
        extra = candidate_gdf.sample(n=min(target_n - len(neg_df), len(candidate_gdf)), random_state=42)
        neg_df = pd.concat([neg_df, extra], ignore_index=True)
        neg_df = neg_df.drop_duplicates().head(target_n)

    # 음성 샘플 레이블 부여
    neg_df["is_hotspot"] = 0
    neg_df["is_severe"] = 0
    neg_df["is_daytime"] = -1  # 음성 샘플은 주야 구분 없음

    # 기상상태 등 카테고리 Feature는 양성 샘플 분포로 무작위 배정
    for col in ["기상상태", "도로형태", "법규위반", "노면상태"]:
        if col in positive_df.columns:
            neg_df[col] = np.random.choice(
                positive_df[col].dropna().values, size=len(neg_df), replace=True
            )

    log.info(f"음성 샘플 생성 완료: {len(neg_df)}개")

    # GeoDataFrame → 일반 DataFrame 변환 (geometry, index_right 컬럼 제거)
    drop_geo_cols = [c for c in ["geometry", "index_right"] if c in neg_df.columns]
    neg_df = pd.DataFrame(neg_df.drop(columns=drop_geo_cols))

    # 캐시 저장 (CSV)
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    neg_df.to_csv(CACHE_PATH, index=False)
    log.info(f"음성 샘플 캐시 저장: {CACHE_PATH}")

    return neg_df


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    from src.data.loader_pm import load_pm_data
    pos_df = load_pm_data()
    neg_df = generate_negative_samples(pos_df)
    print(f"\n음성 샘플:\n{neg_df[['위도', '경도', 'is_hotspot']].head()}")
