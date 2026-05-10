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
    
    # '구' 이름 보정 (JSON 데이터와 매핑을 위해. '중구' -> '중구' 등 기본적으로 맞을 것임)
    
    # 서울시 구 경계 GeoJSON 다운로드
    geojson_url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"
    response = requests.get(geojson_url)
    if response.status_code != 200:
        log.error("GeoJSON 다운로드 실패. 지도를 생성할 수 없습니다.")
        return
    
    seoul_geo = response.json()
    
    # Folium 맵 초기화 (서울 중심)
    m = folium.Map(location=[37.5665, 126.9780], zoom_start=11, tiles="CartoDB positron")
    
    # Choropleth 추가 (사고 건수 기준 히트맵)
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
    
    # 구별 툴팁 정보 추가를 위한 마커
    for idx, row in district_stats.iterrows():
        # 각 구의 대략적인 중심 좌표를 찾기 어려우므로 GeoJSON 피처에 직접 툴팁 적용하는 방법 사용
        pass
        
    # GeoJson 툴팁 추가
    # 통계 데이터를 딕셔너리로 변환
    stats_dict = district_stats.set_index('구').to_dict('index')
    
    # GeoJSON 속성에 통계 데이터 주입
    for feature in seoul_geo['features']:
        gu_name = feature['properties']['name']
        if gu_name in stats_dict:
            feature['properties']['사고건수'] = str(stats_dict[gu_name]['사고건수']) + " 건"
            feature['properties']['고위험비율'] = f"{stats_dict[gu_name]['평균심각도']*100:.1f} %"
        else:
            feature['properties']['사고건수'] = "데이터 없음"
            feature['properties']['고위험비율'] = "데이터 없음"
            
    folium.GeoJson(
        seoul_geo,
        name='상세 정보',
        style_function=lambda x: {'fillColor': 'transparent', 'color': 'black', 'weight': 1, 'opacity': 0.1},
        tooltip=folium.features.GeoJsonTooltip(
            fields=['name', '사고건수', '고위험비율'],
            aliases=['구:', '사고 건수:', '고위험 사고 비율:'],
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
