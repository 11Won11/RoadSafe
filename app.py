import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import pickle
from pathlib import Path
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Polygon
import os

st.set_page_config(page_title="국가 PM 공간 위험 관제 시스템", layout="wide", page_icon="🏛️", initial_sidebar_state="expanded")

# ── Custom CSS ──
st.markdown("""
<style>
    .reportview-container .main .block-container{
        padding-top: 1rem;
    }
    h1 {
        color: #e0e0e0;
        font-size: 28px !important;
        font-weight: 700;
        border-bottom: 2px solid #333;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    h3 {
        color: #ffba08;
        font-size: 20px !important;
    }
    .metric-card {
        background-color: #1e1e1e;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏛️ 국가 전동킥보드(PM) 공간 위험 관제 시스템")

# ── 1. 데이터 및 모델 로드 ──
@st.cache_resource
def load_model():
    model_path = Path("data/interim/xgb_grid_model.pkl")
    if not model_path.exists():
        return None, None
    with open(model_path, "rb") as f:
        data = pickle.load(f)
    return data["model"], data["feature_names"]

@st.cache_data
def load_grid_data(city):
    path = Path(f"data/interim/grid_features_with_labels_{city}.csv")
    if not path.exists():
        return None
    df = pd.read_csv(path)
    df = df[df["intersection_count_500m"] > 0].copy()
    return df

@st.cache_data
def get_city_mask(city_name):
    query = "Seoul, South Korea" if city_name == "seoul" else "Busan, South Korea"
    try:
        city_gdf = ox.geocode_to_gdf(query)
        city_geom = city_gdf.geometry.iloc[0]
        world = Polygon([[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]])
        mask_geom = world.difference(city_geom)
        return gpd.GeoDataFrame(geometry=[mask_geom], crs="EPSG:4326")
    except:
        return None

model, feature_names = load_model()

if model is None:
    st.error("🚨 제어 시스템(AI 엔진)에 연결할 수 없습니다. 터미널에서 스크립트를 먼저 실행해주세요.")
    st.stop()

# ── 2. 사이드바 (관제 설정) ──
st.sidebar.header("⚙️ 시스템 설정 (System Config)")
target_city = st.sidebar.selectbox("📍 모니터링 권역 선택", ["seoul", "busan"], format_func=lambda x: "서울특별시" if x=="seoul" else "부산광역시")

grid_df = load_grid_data(target_city)
if grid_df is None:
    st.sidebar.error(f"🚨 {target_city}의 공간 데이터베이스가 오프라인 상태입니다.")
    st.stop()

st.sidebar.markdown("---")
target_pct = st.sidebar.slider("🚨 현장 순찰/단속 투입 규모 (%)", min_value=1, max_value=50, value=10, step=1,
                               help="행정력을 투입할 상위 위험 구역의 비율을 설정합니다.")

st.sidebar.markdown("---")
map_style = st.sidebar.radio("🗺️ 관제망 렌즈 (Lens)", ["다크 모드 (야간투시)", "라이트 모드 (주간)", "위성 모드 (정밀)"])

if map_style == "다크 모드 (야간투시)":
    tiles = "CartoDB dark_matter"
    attr = None
    mask_color = "#0e0e0e"
elif map_style == "라이트 모드 (주간)":
    tiles = "CartoDB positron"
    attr = None
    mask_color = "#ffffff"
else:
    tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    attr = "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
    mask_color = "#000000"

# ── 3. AI 위험도 예측 및 등급화 ──
X = grid_df[feature_names].fillna(0)
preds = model.predict(X)
robust_max = np.percentile(preds, 99)
if robust_max == 0: robust_max = preds.max()
risk_scores = (preds / robust_max * 100).clip(0, 100) if robust_max > 0 else preds

grid_df["risk_score"] = risk_scores
threshold_score = np.percentile(grid_df["risk_score"], 100 - target_pct)
grid_df["is_target"] = grid_df["risk_score"] >= threshold_score

def get_risk_level_color(score):
    if score >= 75: return "#d00000" # 심각 (Red)
    elif score >= 50: return "#e85d04" # 경계 (Orange)
    elif score >= 25: return "#ffba08" # 주의 (Yellow)
    else: return "#43aa8b" # 관심 (Green)

def get_risk_label(score):
    if score >= 75: return "심각"
    elif score >= 50: return "경계"
    elif score >= 25: return "주의"
    else: return "관심"

# ── 4. 현황 지표 계산 ──
total_grids = len(grid_df)
target_grids = grid_df["is_target"].sum()

label_col = "label_2024" if target_city == "seoul" else "label_all"
if label_col not in grid_df.columns:
    label_col = "acc_total" if "acc_total" in grid_df.columns else "label_all"

total_accidents = grid_df[label_col].sum()
captured_accidents = grid_df[grid_df["is_target"]][label_col].sum()

hit_rate = (captured_accidents / total_accidents * 100) if total_accidents > 0 else 0
area_rate = (target_grids / total_grids * 100) if total_grids > 0 else 0
efficiency = (hit_rate / area_rate) if area_rate > 0 else 0

# 선택된 타겟 내의 등급 분포 계산
target_df = grid_df[grid_df["is_target"]]
level_counts = target_df["risk_score"].apply(get_risk_label).value_counts()

# ── 5. 레이아웃 분할 (좌측: 맵, 우측: 현황판) ──
col_map, col_panel = st.columns([7, 3])

with col_map:
    st.markdown(f"### 📍 실시간 위험 구역 모니터링 ({'서울특별시' if target_city=='seoul' else '부산광역시'})")
    
    center_lat = grid_df["lat_min"].mean() + 0.0045/2
    center_lon = grid_df["lon_min"].mean() + 0.0056/2
    min_lat, max_lat = grid_df["lat_min"].min(), grid_df["lat_min"].max() + 0.0045
    min_lon, max_lon = grid_df["lon_min"].min(), grid_df["lon_min"].max() + 0.0056

    m = folium.Map(location=[center_lat, center_lon], zoom_start=11, min_zoom=11, max_zoom=16, tiles=tiles, attr=attr)
    m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

    # Focus Mask
    mask_gdf = get_city_mask(target_city)
    if mask_gdf is not None:
        folium.GeoJson(mask_gdf, style_function=lambda x: {"fillColor": mask_color, "color": "transparent", "weight": 0, "fillOpacity": 1.0}).add_to(m)

    target_layer = folium.FeatureGroup(name="🚨 관제 구역", show=True)
    
    for _, row in target_df.iterrows():
        lat_min, lon_min = row["lat_min"], row["lon_min"]
        score = row["risk_score"]
        color = get_risk_level_color(score)
        label = get_risk_label(score)
        
        cell_geo = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[lon_min, lat_min], [lon_min + 0.0056, lat_min],
                                 [lon_min + 0.0056, lat_min + 0.0045], [lon_min, lat_min + 0.0045],
                                 [lon_min, lat_min]]]
            }
        }
        
        popup_html = f"<b>경보 등급:</b> {label}<br><b>위험도 점수:</b> {score:.1f}점<br><b>시설물 수:</b> {row['poi_count_total']}개"
        
        folium.GeoJson(
            cell_geo,
            style_function=lambda x, c=color: {"fillColor": c, "color": c, "weight": 1, "fillOpacity": 0.65},
            tooltip=f"{label} ({score:.1f})",
            popup=folium.Popup(popup_html, max_width=200),
        ).add_to(target_layer)

    target_layer.add_to(m)
    
    # Legend
    legend_html = '''
     <div style="position: fixed; bottom: 50px; right: 50px; width: 120px; height: 130px; 
     border:2px solid grey; z-index:9999; font-size:14px; background-color:rgba(20,20,20,0.8);
     color: white; font-weight: bold; border-radius: 5px; padding: 10px;">
     &nbsp;<b>재난경보 등급</b><br>
     &nbsp;<i class="fa fa-square" style="color:#d00000"></i> 심각 (75~)<br>
     &nbsp;<i class="fa fa-square" style="color:#e85d04"></i> 경계 (50~74)<br>
     &nbsp;<i class="fa fa-square" style="color:#ffba08"></i> 주의 (25~49)<br>
     &nbsp;<i class="fa fa-square" style="color:#43aa8b"></i> 관심 (~24)
     </div>
     '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    st_folium(m, use_container_width=True, height=650, returned_objects=[])

with col_panel:
    st.markdown("### 📊 종합 관제 현황판")
    
    st.metric("🚨 감시 대상 행정 구역 (면적)", f"{target_grids} 구역", f"전체 도시의 {target_pct}%")
    st.metric("🛡️ 예상 사고 예방률", f"{hit_rate:.1f}%", f"{int(captured_accidents)} 건 사전 차단 가능")
    st.metric("⚙️ 관제 효율성 지수", f"{efficiency:.2f} 배", "무작위 순찰 대비 예방 효과", delta_color="normal")
    
    st.markdown("---")
    st.markdown("#### ⚠️ 감시 구역 내 위험 등급 분포")
    st.markdown(f"- 🔴 **심각:** {level_counts.get('심각', 0)} 개소")
    st.markdown(f"- 🟠 **경계:** {level_counts.get('경계', 0)} 개소")
    st.markdown(f"- 🟡 **주의:** {level_counts.get('주의', 0)} 개소")
    st.markdown(f"- 🟢 **관심:** {level_counts.get('관심', 0)} 개소")
    
    st.markdown("---")
    with st.expander("🔍 관할 구역 주요 위험 유발 시설물", expanded=True):
        st.caption("AI가 지목한 해당 도시의 사고 유발 핵심 환경 요인입니다.")
        shap_path = f"outputs/shap_grid_bar.png"
        if os.path.exists(shap_path):
            st.image(shap_path, use_column_width=True)
        else:
            st.info("현재 분석된 시설물 데이터가 없습니다.")
