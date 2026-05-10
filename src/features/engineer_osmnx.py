import osmnx as ox
import geopandas as gpd
import pandas as pd
import requests
import logging
from pathlib import Path

log = logging.getLogger(__name__)

def get_seoul_districts_gdf() -> gpd.GeoDataFrame:
    """서울 구별 GeoJSON을 GeoDataFrame으로 로드"""
    url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"
    r = requests.get(url)
    if r.status_code != 200:
        raise ValueError("GeoJSON 다운로드 실패")
    
    gdf = gpd.GeoDataFrame.from_features(r.json()["features"])
    gdf.set_crs(epsg=4326, inplace=True)
    return gdf

def create_osmnx_district_features(output_csv: str = "data/interim/district_osmnx_features.csv"):
    """
    OSMnx에서 서울시 도로망을 추출하고 구(區)별 통계(교차로 수, 도로 길이)를 생성.
    기존에 파일이 있으면 다운로드를 생략합니다.
    """
    p = Path(output_csv)
    if p.exists():
        log.info(f"OSMnx 공간 변수 캐시 발견: {output_csv}")
        return pd.read_csv(p)

    log.info("서울 구 경계 데이터 로드 중...")
    districts = get_seoul_districts_gdf()
    districts.rename(columns={'name': 'gu_name'}, inplace=True)
    
    log.info("OSMnx 서울시 도로망(drive) 다운로드 중... (약 1~3분 소요)")
    # PM은 자전거나 차량용 도로를 주로 이용하므로 drive 또는 bike 네트워크 사용. 여기선 drive 기준.
    G = ox.graph_from_place("Seoul, South Korea", network_type="drive")
    nodes, edges = ox.graph_to_gdfs(G)
    
    log.info(f"다운로드 완료: 노드 {len(nodes):,}개, 엣지 {len(edges):,}개")
    
    # 교차로만 필터링 (street_count가 2 이상인 경우 보통 교차로, 1은 막다른 길)
    # 여기서는 단순화를 위해 모든 노드를 교차로/분기점으로 간주
    
    # 공간 조인: 노드가 어느 구에 속하는지
    log.info("구별 교차로 및 도로 길이 공간 매핑 중...")
    nodes_joined = gpd.sjoin(nodes, districts[['gu_name', 'geometry']], how='inner', predicate='within')
    
    # 구별 교차로 수 집계
    intersection_count = nodes_joined.groupby('gu_name').size().rename('intersection_count')
    
    # 도로 엣지가 어느 구에 속하는지 대략적 매핑 (엣지의 중심점 기준)
    edges['centroid'] = edges.geometry.centroid
    edges_point = edges.set_geometry('centroid')
    edges_joined = gpd.sjoin(edges_point, districts[['gu_name', 'geometry']], how='inner', predicate='within')
    
    # 도로 길이 집계 (length는 미터 단위)
    road_length = edges_joined.groupby('gu_name')['length'].sum().rename('street_length_total')
    
    # 데이터 병합
    osmnx_features = pd.concat([intersection_count, road_length], axis=1).fillna(0)
    
    # 파생 변수: 1km 당 교차로 밀도
    # street_length_total은 m 단위이므로 km로 변환
    osmnx_features['intersection_density_per_km'] = osmnx_features['intersection_count'] / (osmnx_features['street_length_total'] / 1000)
    
    osmnx_features.index.name = '구'
    osmnx_features.reset_index(inplace=True)
    
    # 파일 저장
    p.parent.mkdir(parents=True, exist_ok=True)
    osmnx_features.to_csv(p, index=False)
    log.info(f"OSMnx 구별 통계 저장 완료: {output_csv}")
    
    return osmnx_features

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    df = create_osmnx_district_features("data/interim/district_osmnx_features.csv")
    print(df.head())
