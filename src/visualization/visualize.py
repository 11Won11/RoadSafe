"""
Phase 2 공간 위험도 대시보드
실제 PM 사고 지점 위에 위험도 점수(0~100) 히트맵 + SHAP Top-5 팝업 표시
"""
import json
import logging
import numpy as np
import pandas as pd
import folium
import shap
import requests
from pathlib import Path

log = logging.getLogger(__name__)


def _risk_color(score: float) -> str:
    if score >= 80: return "#d00000"
    if score >= 60: return "#f48c06"
    if score >= 40: return "#ffba08"
    if score >= 20: return "#a7c957"
    return "#386641"


def _shap_popup_html(lat: float, lon: float, score: float, top5: list) -> str:
    """위험도 점수 + SHAP Top-5 자동 해설 팝업 HTML"""
    color = _risk_color(score)
    rows = ""
    for feat, val in top5:
        arrow = "▲" if val > 0 else "▼"
        font_color = "#c0392b" if val > 0 else "#2980b9"
        rows += (
            f"<tr>"
            f"<td style='padding:3px 8px 3px 0;'>{feat}</td>"
            f"<td style='color:{font_color}; font-weight:bold;'>{arrow} {val:+.3f}</td>"
            f"</tr>"
        )
    return f"""
<div style='font-family:sans-serif; min-width:290px;'>
  <div style='background:{color}; color:white; padding:10px 14px; border-radius:8px 8px 0 0;'>
    <span style='font-size:0.95em;'>📍 공간 위험도 점수</span>
    <span style='float:right; font-size:2em; font-weight:bold; line-height:1;'>{score:.0f}</span>
  </div>
  <div style='padding:10px 14px; border:1px solid #ddd; border-top:none; border-radius:0 0 8px 8px; background:#fff;'>
    <div style='font-size:0.8em; color:#666; margin-bottom:6px;'>📍 {lat:.5f}, {lon:.5f}</div>
    <b style='font-size:0.9em;'>위험 요인 Top-5 (SHAP)</b>
    <table style='width:100%; font-size:0.85em; margin-top:5px; border-collapse:collapse;'>
      {rows}
    </table>
  </div>
</div>"""


def create_risk_dashboard(
    pos_df: pd.DataFrame,
    features_df: pd.DataFrame,
    model,
    explainer,
    feature_names: list,
    output_dir: str = "outputs",
):
    """
    PM 사고 지점별 위험도 점수(0~100) 히트맵 대시보드 생성.
    클릭 시 SHAP Top-5 요인 자동 해설 팝업 표시.
    """
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
            style_function=lambda x: {"fillColor": "transparent", "color": "#888", "weight": 1, "opacity": 0.5},
        ).add_to(m)
    except Exception as e:
        log.warning(f"GeoJSON 로드 실패: {e}")

    # ── 위험도 점수 계산 ──────────────────────────────────────────
    drop_cols = [c for c in ["is_hotspot", "is_daytime", "is_severe"] if c in features_df.columns]
    # 양성 샘플(실제 사고 지점)만 시각화
    pos_mask = features_df["is_hotspot"] == 1
    X_pos = features_df[pos_mask].drop(columns=drop_cols)
    pos_coords = pos_df[["위도", "경도"]].reset_index(drop=True)

    proba = model.predict_proba(X_pos)[:, 1]
    risk_scores = (proba * 100).clip(0, 100)

    # SHAP 값 계산
    shap_vals = explainer.shap_values(X_pos)

    # ── 위험도 레이어: 전체 ────────────────────────────────────
    all_layer = folium.FeatureGroup(name="🔴 PM 사고 위험도 (전체)", show=True)

    for i, (score, (_, coord)) in enumerate(zip(risk_scores, pos_coords.iterrows())):
        lat, lon = coord["위도"], coord["경도"]
        color = _risk_color(score)

        # SHAP Top-5
        row_shap = shap_vals[i] if len(shap_vals.shape) == 2 else shap_vals[0][i]
        top_idx = np.argsort(np.abs(row_shap))[-5:][::-1]
        top5 = [(feature_names[j], row_shap[j]) for j in top_idx]

        folium.CircleMarker(
            location=[lat, lon],
            radius=max(4, score / 18),
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.75,
            popup=folium.Popup(_shap_popup_html(lat, lon, score, top5), max_width=330),
            tooltip=f"위험도: {score:.0f}점",
        ).add_to(all_layer)

    all_layer.add_to(m)

    # ── 위험도 레이어: 고위험 지점 (80점 이상) ──────────────────
    high_layer = folium.FeatureGroup(name="⚠️ 고위험 지점 (80점 이상)", show=False)
    high_count = 0
    for i, (score, (_, coord)) in enumerate(zip(risk_scores, pos_coords.iterrows())):
        if score < 80:
            continue
        lat, lon = coord["위도"], coord["경도"]
        row_shap = shap_vals[i] if len(shap_vals.shape) == 2 else shap_vals[0][i]
        top_idx = np.argsort(np.abs(row_shap))[-5:][::-1]
        top5 = [(feature_names[j], row_shap[j]) for j in top_idx]
        folium.Marker(
            location=[lat, lon],
            icon=folium.Icon(color="red", icon="exclamation-sign"),
            popup=folium.Popup(_shap_popup_html(lat, lon, score, top5), max_width=330),
            tooltip=f"⚠️ 고위험: {score:.0f}점",
        ).add_to(high_layer)
        high_count += 1

    high_layer.add_to(m)
    log.info(f"고위험 지점(80+): {high_count}개")

    # ── 이륜차 사고 다발 구역 (기존 레이어) ─────────────────────
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

    # 범례 추가
    legend_html = """
    <div style='position:fixed; bottom:30px; left:30px; z-index:1000;
                background:white; padding:12px 16px; border-radius:8px;
                box-shadow:0 2px 8px rgba(0,0,0,0.3); font-family:sans-serif; font-size:13px;'>
      <b>위험도 점수</b><br>
      <span style='color:#d00000'>●</span> 80~100 (매우 높음)<br>
      <span style='color:#f48c06'>●</span> 60~79 (높음)<br>
      <span style='color:#ffba08'>●</span> 40~59 (중간)<br>
      <span style='color:#a7c957'>●</span> 20~39 (낮음)<br>
      <span style='color:#386641'>●</span> 0~19 (매우 낮음)
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))

    output_path = f"{output_dir}/seoul_pm_risk_map.html"
    m.save(output_path)
    log.info(f"SAFERIDE 대시보드 저장 완료: {output_path}")
    log.info(f"위험도 분포: 평균={risk_scores.mean():.1f} | 최고={risk_scores.max():.1f} | 80점↑={high_count}개")
