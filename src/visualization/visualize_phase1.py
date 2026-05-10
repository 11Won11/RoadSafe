import pandas as pd
import folium
import requests
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

def create_district_heatmap(df: pd.DataFrame, output_dir: str = "outputs"):
    """
    구(區)별 PM 사고 건수 및 평균 심각도를 Folium 지도에 표시 (Phase 1 시제품용)
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # 구별 통계 집계
    district_stats = df.groupby('구').agg(
        사고건수=('구분번호', 'count'),
        평균심각도=('is_severe', 'mean')
    ).reset_index()
    
    # OSMnx 공간 변수 로드
    osmnx_path = Path("data/interim/district_osmnx_features.csv")
    if osmnx_path.exists():
        osmnx_df = pd.read_csv(osmnx_path)
        district_stats = district_stats.merge(osmnx_df, on='구', how='left')
        district_stats.fillna(0, inplace=True)
        has_osmnx = True
    else:
        has_osmnx = False
    
    # 서울시 구 경계 GeoJSON 다운로드
    geojson_url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"
    response = requests.get(geojson_url)
    if response.status_code != 200:
        log.error("GeoJSON 다운로드 실패. 지도를 생성할 수 없습니다.")
        return
    
    seoul_geo = response.json()
    
    # Folium 맵 초기화 (서울 중심)
    m = folium.Map(location=[37.5665, 126.9780], zoom_start=11, tiles="CartoDB positron")
    
    # Choropleth 1: 사고 건수 히트맵
    folium.Choropleth(
        geo_data=seoul_geo,
        name='PM 사고 위험도 (사고 건수)',
        data=district_stats,
        columns=['구', '사고건수'],
        key_on='feature.properties.name',
        fill_color='YlOrRd',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name='PM 사고 발생 건수'
    ).add_to(m)
    
    # Choropleth 2: 교차로 밀도 히트맵 (osmnx 데이터가 있을 경우)
    if has_osmnx:
        folium.Choropleth(
            geo_data=seoul_geo,
            name='교차로 밀도 (1km당)',
            data=district_stats,
            columns=['구', 'intersection_density_per_km'],
            key_on='feature.properties.name',
            fill_color='PuBu',
            fill_opacity=0.6,
            line_opacity=0.2,
            legend_name='도로 1km당 교차로 수',
            show=False  # 기본으로는 꺼둠
        ).add_to(m)
        
    # GeoJson 툴팁 추가
    # 통계 데이터를 딕셔너리로 변환
    stats_dict = district_stats.set_index('구').to_dict('index')
    
    # GeoJSON 속성에 통계 데이터 주입
    for feature in seoul_geo['features']:
        gu_name = feature['properties']['name']
        if gu_name in stats_dict:
            feature['properties']['사고건수'] = str(stats_dict[gu_name]['사고건수']) + " 건"
            feature['properties']['고위험비율'] = f"{stats_dict[gu_name]['평균심각도']*100:.1f} %"
            if has_osmnx:
                feature['properties']['교차로수'] = f"{int(stats_dict[gu_name]['intersection_count']):,} 개"
                feature['properties']['도로길이'] = f"{stats_dict[gu_name]['street_length_total']/1000:.1f} km"
                feature['properties']['교차로밀도'] = f"{stats_dict[gu_name]['intersection_density_per_km']:.1f} 개/km"
        else:
            feature['properties']['사고건수'] = "데이터 없음"
            feature['properties']['고위험비율'] = "데이터 없음"
            if has_osmnx:
                feature['properties']['교차로수'] = "데이터 없음"
                feature['properties']['도로길이'] = "데이터 없음"
                feature['properties']['교차로밀도'] = "데이터 없음"
            
    tooltip_fields = ['name', '사고건수', '고위험비율']
    tooltip_aliases = ['구:', '사고 건수:', '고위험 사고 비율:']
    if has_osmnx:
        tooltip_fields.extend(['교차로수', '도로길이', '교차로밀도'])
        tooltip_aliases.extend(['총 교차로 수:', '총 도로 길이:', '교차로 밀도:'])

    folium.GeoJson(
        seoul_geo,
        name='상세 정보 툴팁',
        style_function=lambda x: {'fillColor': 'transparent', 'color': 'black', 'weight': 1, 'opacity': 0.1},
        tooltip=folium.features.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=tooltip_aliases,
            labels=True,
            sticky=True
        )
    ).add_to(m)
    
    folium.LayerControl().add_to(m)
    
    output_path = f"{output_dir}/seoul_pm_risk_map.html"
    m.save(output_path)
    log.info(f"위험도 히트맵 지도 저장 완료: {output_path}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from src.data.loader_phase1 import load_phase1_data
    
    df = load_phase1_data("사고분석-지역별.xlsx")
    create_district_heatmap(df)
