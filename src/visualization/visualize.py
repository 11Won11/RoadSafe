"""
SAFERIDE 공간 위험도 대시보드
- 500m 격자 단위 위험도 히트맵 (Choropleth)
- 격자 클릭 시 SHAP Top-5 요인 팝업
- 이륜차 사고 다발 구역 레이어
"""
import json
import logging
import numpy as np
import pandas as pd
import folium
import shap
import requests
from pathlib import Path
from shapely.geometry import box, Point
import geopandas as gpd

log = logging.getLogger(__name__)

# 서울 바운딩박스 (위도, 경도)
SEOUL_BBOX = dict(lat_min=37.413, lat_max=37.715, lon_min=126.734, lon_max=127.270)

# 격자 크기 (도 단위, 약 500m)
GRID_LAT = 0.0045
GRID_LON = 0.0056


def _risk_color(score: float) -> str:
    if score >= 80: return "#d00000"
    if score >= 60: return "#f48c06"
    if score >= 40: return "#ffba08"
    if score >= 20: return "#a7c957"
    return "#386641"


def _score_to_fill(score: float) -> tuple:
    """위험도 점수 → (fill_color, fill_opacity)"""
    color = _risk_color(score)
    opacity = 0.2 + (score / 100) * 0.55   # 0.2 ~ 0.75
    return color, round(opacity, 2)


def _shap_popup_html(score: float, count: int, top5: list) -> str:
    """격자 클릭 팝업: 위험도 점수 + 평균 SHAP Top-5"""
    color = _risk_color(score)
    rows = ""
    for feat, val in top5:
        arrow = "▲" if val > 0 else "▼"
        fc = "#c0392b" if val > 0 else "#2980b9"
        rows += f"<tr><td style='padding:3px 8px 3px 0'>{feat}</td><td style='color:{fc};font-weight:bold'>{arrow} {val:+.3f}</td></tr>"
    return f"""
<div style='font-family:sans-serif; min-width:290px;'>
  <div style='background:{color}; color:white; padding:10px 14px; border-radius:8px 8px 0 0;'>
    <span style='font-size:0.9em'>🟥 격자 평균 위험도</span>
    <span style='float:right; font-size:2em; font-weight:bold; line-height:1'>{score:.0f}</span>
  </div>
  <div style='padding:10px 14px; border:1px solid #ddd; border-top:none; border-radius:0 0 8px 8px; background:#fff'>
    <div style='font-size:0.8em; color:#666; margin-bottom:6px'>포함 사고 지점: {count}개</div>
    <b style='font-size:0.9em'>주요 위험 요인 Top-5 (SHAP 평균)</b>
    <table style='width:100%; font-size:0.85em; margin-top:5px; border-collapse:collapse'>
      {rows}
    </table>
  </div>
</div>"""


def _build_grid(risk_scores: np.ndarray, pos_coords: pd.DataFrame, shap_vals: np.ndarray, feature_names: list):
    """
    서울 전체를 ~500m 격자로 나누고 각 격자 안의
    평균 위험도 점수와 SHAP 평균을 계산하여 GeoJSON Feature 목록 반환
    """
    lat_min, lat_max = SEOUL_BBOX["lat_min"], SEOUL_BBOX["lat_max"]
    lon_min, lon_max = SEOUL_BBOX["lon_min"], SEOUL_BBOX["lon_max"]

    # 사고 지점 GeoDataFrame 생성
    pts = gpd.GeoDataFrame(
        {"risk": risk_scores, "idx": np.arange(len(risk_scores))},
        geometry=[Point(lon, lat) for lat, lon in zip(pos_coords["위도"], pos_coords["경도"])],
        crs="EPSG:4326",
    )

    features = []
    lat = lat_min
    while lat < lat_max:
        lon = lon_min
        while lon < lon_max:
            cell = box(lon, lat, lon + GRID_LON, lat + GRID_LAT)
            cell_gdf = gpd.GeoDataFrame(geometry=[cell], crs="EPSG:4326")

            # 격자 안의 사고 지점 찾기
            inside = gpd.sjoin(pts, cell_gdf, how="inner", predicate="within")

            if len(inside) == 0:
                lon += GRID_LON
                continue

            idxs = inside["idx"].values
            mean_score = float(risk_scores[idxs].mean())
            count = len(idxs)

            # SHAP 평균 Top-5
            mean_shap = np.abs(shap_vals[idxs]).mean(axis=0)
            top_idx = np.argsort(mean_shap)[-5:][::-1]
            # 방향성은 평균 SHAP (부호 있는 값)
            mean_shap_signed = shap_vals[idxs].mean(axis=0)
            top5 = [(feature_names[j], float(mean_shap_signed[j])) for j in top_idx]

            fill_color, fill_opacity = _score_to_fill(mean_score)
            cx = lon + GRID_LON / 2
            cy = lat + GRID_LAT / 2

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [lon, lat], [lon + GRID_LON, lat],
                        [lon + GRID_LON, lat + GRID_LAT],
                        [lon, lat + GRID_LAT], [lon, lat],
                    ]]
                },
                "properties": {
                    "score": round(mean_score, 1),
                    "count": count,
                    "fill_color": fill_color,
                    "fill_opacity": fill_opacity,
                    "top5": top5,
                    "cx": cx,
                    "cy": cy,
                }
            })
            lon += GRID_LON
        lat += GRID_LAT

    log.info(f"격자 생성 완료: 총 {len(features)}개 (사고 포함 격자만)")
    return features


def create_risk_dashboard(
    pos_df: pd.DataFrame,
    features_df: pd.DataFrame,
    model,
    explainer,
    feature_names: list,
    output_dir: str = "outputs",
):
    from src.features.engineer_grid import predict_grid_risk, GRID_LAT, GRID_LON

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    m = folium.Map(location=[37.5665, 126.9780], zoom_start=11, tiles="CartoDB dark_matter")

    # 서울 구 경계 GeoJSON (배경)
    try:
        r = requests.get(
            "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json",
            timeout=10,
        )
        folium.GeoJson(
            r.json(),
            name="서울시 구 경계",
            style_function=lambda x: {"fillColor": "transparent", "color": "#aaa", "weight": 1.5, "opacity": 0.6},
        ).add_to(m)
    except Exception as e:
        log.warning(f"GeoJSON 로드 실패: {e}")

    # ── 서울 전체 격자 위험도 예측 ─────────────────────────────
    log.info("서울 전체 격자 위험도 예측 중...")
    grid_df = predict_grid_risk(model, feature_names)

    # ── 격자 히트맵 레이어 ───────────────────────────────────────
    grid_layer = folium.FeatureGroup(name="🟥 격자 위험도 히트맵 (500m, 전체)", show=True)
    high_count = 0

    for _, row in grid_df.iterrows():
        lat_min = row["lat_min"]
        lon_min = row["lon_min"]
        score = row["risk_score"]
        fill_color, fill_opacity = _score_to_fill(score)

        cell_geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [lon_min, lat_min],
                    [lon_min + GRID_LON, lat_min],
                    [lon_min + GRID_LON, lat_min + GRID_LAT],
                    [lon_min, lat_min + GRID_LAT],
                    [lon_min, lat_min],
                ]]
            }
        }

        folium.GeoJson(
            cell_geojson,
            style_function=lambda x, fc=fill_color, fo=fill_opacity: {
                "fillColor": fc,
                "color": "transparent",
                "weight": 0,
                "fillOpacity": fo,
            },
            tooltip=f"위험도: {score:.0f}점",
        ).add_to(grid_layer)

        if score >= 80:
            high_count += 1

    grid_layer.add_to(m)
    log.info(f"격자 히트맵 완료: 총 {len(grid_df)}개 | 고위험(80+) {high_count}개")

    # ── 이륜차 사고 다발 구역 레이어 ─────────────────────────────
    hotspot_file = Path("data/raw/이륜차_사고다발지역_utf8.csv")
    if hotspot_file.exists():
        try:
            hotspot_df = pd.read_csv(hotspot_file)
            seoul_hs = hotspot_df[hotspot_df["시도시군구명"].str.contains("서울특별시", na=False)]
            hs_layer = folium.FeatureGroup(name="🚫 이륜차 사고 다발 구역", show=False)
            for _, row in seoul_hs.iterrows():
                folium.CircleMarker(
                    location=[row["위도"], row["경도"]],
                    radius=4, color="darkred", fill=True, fill_color="red", fill_opacity=0.6,
                    popup=f"<b>{row['지점명']}</b><br>사고 {row['사고건수']}건",
                    tooltip=row["지점명"],
                ).add_to(hs_layer)
            hs_layer.add_to(m)
        except Exception as e:
            log.warning(f"이륜차 다발 구역 로드 실패: {e}")

    folium.LayerControl(collapsed=False).add_to(m)

    # 범례
    legend_html = """
    <div style='position:fixed; bottom:30px; left:30px; z-index:1000;
                background:rgba(20,20,20,0.85); color:white; padding:12px 16px;
                border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.5);
                font-family:sans-serif; font-size:13px; line-height:1.7;'>
      <b>격자 평균 위험도</b><br>
      <span style='color:#d00000'>■</span> 80~100 (매우 높음)<br>
      <span style='color:#f48c06'>■</span> 60~79 (높음)<br>
      <span style='color:#ffba08'>■</span> 40~59 (중간)<br>
      <span style='color:#a7c957'>■</span> 20~39 (낮음)<br>
      <span style='color:#386641'>■</span> 0~19 (매우 낮음)
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))

    output_path = f"{output_dir}/seoul_pm_risk_map.html"
    m.save(output_path)

    high_grid = sum(1 for f in grid_features if f["properties"]["score"] >= 80)
    log.info(f"SAFERIDE 대시보드 저장 완료: {output_path}")
    log.info(f"격자 통계: 총 {len(grid_features)}개 | 고위험(80+) {high_grid}개")
