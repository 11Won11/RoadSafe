"""
서울 전역 POI(관심지점) 다운로드 및 격자별 할당 모듈
- 유동인구 및 사람 활동량을 대변하는 Proxy 변수 생성
- 카페, 식당, 대학교, 버스정류장, 지하철역 등 추출
"""
import osmnx as ox
import pandas as pd
import numpy as np
import logging
import pickle
from pathlib import Path

log = logging.getLogger(__name__)
ox.settings.log_console = False
ox.settings.use_cache = True

POI_CACHE_PATH = Path("data/interim/seoul_pois.pkl")

# 추출할 POI 태그 정의
POI_TAGS = {
    "public_transport": "station",       # 지하철역 등
    "highway": "bus_stop",               # 버스 정류장
    "amenity": [
        "cafe", "restaurant", "bar",     # 상업/여가 시설 (유동인구 Proxy)
        "university", "college",         # 대학가 (PM 주요 사용처)
        "convenience"                    # 편의점 (생활 밀착형)
    ]
}

def download_city_pois(city_name: str = "Seoul", force: bool = False) -> pd.DataFrame:
    """대상 도시의 전체 POI를 다운로드하고 전처리된 DataFrame으로 반환합니다."""
    
    # 캐시 파일명 동적 할당
    cache_path = Path(f"data/interim/{city_name.lower()}_pois.pkl")
    
    if cache_path.exists() and not force:
        log.info(f"POI 캐시 로드: {cache_path}")
        with open(cache_path, "rb") as f:
            return pickle.load(f)

    log.info(f"{city_name} 전역 POI 데이터 다운로드 중... (약 1~2분 소요)")
    try:
        # OSMnx features 모듈 사용 (예: "Seoul, South Korea")
        query = f"{city_name}, South Korea"
        gdf = ox.features_from_place(query, tags=POI_TAGS)
        
        # 중심점(Point) 좌표로 변환 (Polygon 건물 등 처리)
        gdf["geometry"] = gdf["geometry"].centroid
        gdf["lat"] = gdf["geometry"].y
        gdf["lon"] = gdf["geometry"].x
        
        # 카테고리화 (하나의 통일된 컬럼으로 병합)
        def determine_category(row):
            if pd.notna(row.get("public_transport")) and row["public_transport"] == "station":
                return "station"
            if pd.notna(row.get("highway")) and row["highway"] == "bus_stop":
                return "bus_stop"
            amenity = row.get("amenity")
            if pd.notna(amenity):
                if amenity in ["cafe", "restaurant", "bar", "convenience"]:
                    return "commercial"
                if amenity in ["university", "college"]:
                    return "university"
            return "other"
            
        gdf["poi_category"] = gdf.apply(determine_category, axis=1)
        
        # 필요한 컬럼만 추출
        poi_df = gdf[["lat", "lon", "poi_category"]].copy()
        # GeoDataFrame -> DataFrame 변환
        poi_df = pd.DataFrame(poi_df)
        
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "wb") as f:
            pickle.dump(poi_df, f)
            
        log.info(f"POI 다운로드 완료: {len(poi_df)}개 위치 추출 (캐시 저장됨)")
        log.info("카테고리별 수량:\n" + poi_df["poi_category"].value_counts().to_string())
        
        return poi_df
        
    except Exception as e:
        log.error(f"POI 다운로드 실패: {e}")
        return pd.DataFrame(columns=["lat", "lon", "poi_category"])


def assign_pois_to_grids(
    grid_df: pd.DataFrame, 
    poi_df: pd.DataFrame, 
    grid_lat_size: float = 0.0045, 
    grid_lon_size: float = 0.0056
) -> pd.DataFrame:
    """각 500m 격자 안에 존재하는 POI 개수를 카테고리별로 카운트하여 병합합니다."""
    
    log.info("격자별 POI 카운트 매핑 중...")
    
    lat_min = grid_df["lat_min"].values
    lon_min = grid_df["lon_min"].values
    lat_max = lat_min + grid_lat_size
    lon_max = lon_min + grid_lon_size
    
    # 카테고리별로 분리해서 행렬 연산
    categories = poi_df["poi_category"].unique()
    
    grid_df = grid_df.copy()
    
    for cat in categories:
        if cat == "other":
            continue
            
        cat_df = poi_df[poi_df["poi_category"] == cat]
        p_lat = cat_df["lat"].values.astype(float)
        p_lon = cat_df["lon"].values.astype(float)
        
        if len(p_lat) == 0:
            grid_df[f"poi_count_{cat}"] = 0
            continue
            
        # 브로드캐스팅 연산 (Grid x POI)
        in_lat = (p_lat[None, :] >= lat_min[:, None]) & (p_lat[None, :] < lat_max[:, None])
        in_lon = (p_lon[None, :] >= lon_min[:, None]) & (p_lon[None, :] < lon_max[:, None])
        
        # 격자별 포함된 개수 합산
        counts = (in_lat & in_lon).sum(axis=1)
        grid_df[f"poi_count_{cat}"] = counts
        
    # 총 POI 수
    poi_cols = [c for c in grid_df.columns if c.startswith("poi_count_")]
    grid_df["poi_count_total"] = grid_df[poi_cols].sum(axis=1)
    
    log.info(f"POI 매핑 완료. 생성된 Feature: {poi_cols + ['poi_count_total']}")
    return grid_df

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    df = download_seoul_pois(force=True)
