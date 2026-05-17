"""
SAFERIDE 격자 수준 파이프라인 실행 스크립트
STEP 1: 서울 PM 사고 데이터 로드
STEP 2: 격자별 OSMnx Feature + 사고 라벨 생성 (캐시)
STEP 3: 격자 수준 XGBoost 학습 + 시간적 검증 PAI
STEP 4: 위험도 히트맵 대시보드 생성
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.loader_pm import load_seoul_only
from src.models.train_xgb_grid import build_grid_dataset, train_grid_model, GRID_LAT, GRID_LON

import pandas as pd

log = logging.getLogger(__name__)


def run_grid_pipeline(n_trials: int = 30, output_dir: str = "outputs"):
    log.info("=" * 60)
    log.info("SAFERIDE 격자 수준 파이프라인 시작")
    log.info("=" * 60)

    # ── STEP 1: 서울 사고 데이터 ─────────────────────────────────
    log.info("\n[STEP 1] 서울 PM 사고 데이터 로드 (2021~2024)")
    seoul_df = load_seoul_only()

    # ── STEP 2: 격자 Feature + 사고 라벨 생성 ──────────────────
    log.info("\n[STEP 2] 격자 OSMnx Feature + 사고 라벨 생성 (캐시 있으면 즉시)")
    grid_df = build_grid_dataset(seoul_df, force=False)
    log.info(f"  격자 수: {len(grid_df)} | 사고 격자: {grid_df['label_all'].sum()}")

    # ── STEP 3: 격자 수준 모델 학습 + PAI ──────────────────────
    log.info("\n[STEP 3] 격자 수준 XGBoost 학습 + 시간적 검증 PAI")
    model, explainer, feat_cols, grid_scored = train_grid_model(
        grid_df=grid_df,
        n_trials=n_trials,
        output_dir=output_dir,
    )

    # ── STEP 4: 위험도 히트맵 대시보드 ──────────────────────────
    log.info("\n[STEP 4] 위험도 히트맵 대시보드 생성")
    _build_dashboard(grid_scored, output_dir)

    log.info("\n" + "=" * 60)
    log.info("✅ 격자 파이프라인 완료!")
    log.info(f"결과물 위치: {output_dir}/")
    log.info("  - seoul_pm_risk_grid.html : 격자 수준 위험도 대시보드")
    log.info("  - shap_grid_bar.png        : 격자 Feature 중요도")
    log.info("  - shap_grid_dot.png        : Feature 영향 방향성")
    log.info("=" * 60)


def _build_dashboard(grid_scored: pd.DataFrame, output_dir: str):
    """격자 위험도 히트맵 Folium 대시보드 생성"""
    import folium, requests
    from pathlib import Path

    def _color(score):
        if score >= 80: return "#d00000"
        if score >= 60: return "#f48c06"
        if score >= 40: return "#ffba08"
        if score >= 20: return "#a7c957"
        return "#386641"

    m = folium.Map(location=[37.5665, 126.9780], zoom_start=11, tiles="CartoDB dark_matter")

    # 서울 구 경계
    try:
        r = requests.get(
            "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json",
            timeout=10)
        folium.GeoJson(
            r.json(), name="서울시 구 경계",
            style_function=lambda x: {"fillColor": "transparent", "color": "#aaa", "weight": 1.5, "opacity": 0.6},
        ).add_to(m)
    except Exception:
        pass

    grid_layer = folium.FeatureGroup(name="🟥 격자 위험도 히트맵 (격자 수준 모델)", show=True)
    high_count = 0

    for _, row in grid_scored.iterrows():
        lat_min = row["lat_min"]
        lon_min = row["lon_min"]
        score   = row["risk_score"]
        acc_cnt = int(row.get("acc_total", 0))
        fill_color = _color(score)
        fill_opacity = 0.15 + (score / 100) * 0.6

        cell_geo = {
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
        popup_html = f"""
        <div style='font-family:sans-serif; min-width:200px'>
          <div style='background:{fill_color}; color:white; padding:8px 12px; border-radius:6px 6px 0 0'>
            <b>격자 위험도</b>
            <span style='float:right; font-size:1.8em; font-weight:bold'>{score:.0f}</span>
          </div>
          <div style='padding:8px 12px; border:1px solid #ddd; border-radius:0 0 6px 6px; background:#fff'>
            <b>기간 내 사고:</b> {acc_cnt}건<br>
            <b>2021-23 사고:</b> {int(row.get('acc_2021_23', 0))}건<br>
            <b>2024 사고:</b> {int(row.get('acc_2024', 0))}건
          </div>
        </div>"""

        folium.GeoJson(
            cell_geo,
            style_function=lambda x, fc=fill_color, fo=fill_opacity: {
                "fillColor": fc, "color": "transparent", "weight": 0, "fillOpacity": fo,
            },
            tooltip=f"위험도: {score:.0f}점 | 사고 {acc_cnt}건",
            popup=folium.Popup(popup_html, max_width=260),
        ).add_to(grid_layer)
        if score >= 80:
            high_count += 1

    grid_layer.add_to(m)

    # 범례
    legend_html = """
    <div style='position:fixed; bottom:30px; left:30px; z-index:1000;
                background:rgba(20,20,20,0.85); color:white; padding:12px 16px;
                border-radius:8px; font-family:sans-serif; font-size:13px; line-height:1.7;'>
      <b>격자 위험도 (격자 수준 모델)</b><br>
      <span style='color:#d00000'>■</span> 80~100 (매우 높음)<br>
      <span style='color:#f48c06'>■</span> 60~79 (높음)<br>
      <span style='color:#ffba08'>■</span> 40~59 (중간)<br>
      <span style='color:#a7c957'>■</span> 20~39 (낮음)<br>
      <span style='color:#386641'>■</span> 0~19 (매우 낮음)
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))
    folium.LayerControl(collapsed=False).add_to(m)

    output_path = f"{output_dir}/seoul_pm_risk_grid.html"
    m.save(output_path)
    log.info(f"대시보드 저장: {output_path} | 고위험(80+) {high_count}개 격자")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    run_grid_pipeline(n_trials=30)
