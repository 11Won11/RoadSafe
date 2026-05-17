"""
Cross-City Generalization Evaluation
- 서울에서 학습된 Grid-Level XGBoost 모델을 타 도시(예: 부산)에 적용하여 공간적 전이성 검증
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import logging
import pickle
from sklearn.metrics import roc_auc_score
from src.data.loader_pm import load_pm_data
from src.models.train_xgb_grid import build_grid_dataset, SPATIAL_FEAT_COLS, _eval_and_print

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

def _build_cross_city_dashboard(grid_scored: pd.DataFrame, target_city: str):
    """타겟 도시의 격자 위험도 히트맵 생성"""
    import folium
    import numpy as np

    def _color(score):
        if score >= 80: return "#d00000"
        if score >= 60: return "#f48c06"
        if score >= 40: return "#ffba08"
        if score >= 20: return "#a7c957"
        return "#386641"

    # 중심 좌표 계산
    center_lat = grid_scored["위도"].mean()
    center_lon = grid_scored["경도"].mean()

    m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles="CartoDB dark_matter")
    grid_layer = folium.FeatureGroup(name=f"🟥 {target_city} 격자 위험도 히트맵", show=True)
    high_count = 0

    GRID_LAT = 0.0045
    GRID_LON = 0.0056

    for _, row in grid_scored.iterrows():
        lat_min = row["lat_min"]
        lon_min = row["lon_min"]
        score   = row["risk_score"]
        acc_cnt = int(row.get("label_all", 0)) # 해당 격자의 총 사고 발생 여부
        
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
        
        popup_html = f"위험도: {score:.0f}점 <br> 사고발생이력: {'있음' if acc_cnt > 0 else '없음'}"

        folium.GeoJson(
            cell_geo,
            style_function=lambda x, fc=fill_color, fo=fill_opacity: {
                "fillColor": fc, "color": "transparent", "weight": 0, "fillOpacity": fo,
            },
            tooltip=f"위험도: {score:.0f}점",
            popup=folium.Popup(popup_html, max_width=200),
        ).add_to(grid_layer)
        
        if score >= 80:
            high_count += 1

    grid_layer.add_to(m)

    legend_html = f"""
    <div style='position:fixed; bottom:30px; left:30px; z-index:1000;
                background:rgba(20,20,20,0.85); color:white; padding:12px 16px;
                border-radius:8px; font-family:sans-serif; font-size:13px; line-height:1.7;'>
      <b>{target_city} 위험도 예측 (Seoul Transfer Model)</b><br>
      <span style='color:#d00000'>■</span> 80~100 (매우 높음)<br>
      <span style='color:#f48c06'>■</span> 60~79 (높음)<br>
      <span style='color:#ffba08'>■</span> 40~59 (중간)<br>
      <span style='color:#a7c957'>■</span> 20~39 (낮음)<br>
      <span style='color:#386641'>■</span> 0~19 (매우 낮음)
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))
    folium.LayerControl(collapsed=False).add_to(m)

    output_path = f"outputs/{target_city.lower()}_pm_risk_grid.html"
    m.save(output_path)
    log.info(f"대시보드 저장: {output_path} | 고위험(80+) {high_count}개 격자")

def run_cross_city_eval(target_city: str = "Busan", city_code: str = "busan"):
    log.info(f"=== Cross-City Validation 시작: 학습(Seoul) -> 테스트({target_city}) ===")
    
    # 1. 서울 모델 로드
    model_path = Path("data/interim/xgb_grid_model.pkl")
    if not model_path.exists():
        log.error("학습된 서울 모델이 없습니다. 먼저 python scripts/run_grid.py를 실행하세요.")
        return
        
    with open(model_path, "rb") as f:
        saved_data = pickle.load(f)
        model = saved_data["model"]
        feature_names = saved_data["feature_names"]
        
    log.info(f"서울 모델 로드 완료 (사용 Feature: {len(feature_names)}개)")
    
    # 2. 타겟 도시 데이터 로드
    log.info(f"\n[STEP 1] {target_city} PM 사고 데이터 로드")
    all_df = load_pm_data(nationwide=True)
    target_df = all_df[all_df["city"] == city_code].copy()
    
    if len(target_df) == 0:
        log.error(f"{target_city} 사고 데이터를 찾을 수 없습니다.")
        return
        
    log.info(f"{target_city} 양성 샘플 수: {len(target_df)}건")
    
    # 3. 타겟 도시 격자 데이터셋 및 POI 구축
    log.info(f"\n[STEP 2] {target_city} 전역 격자 공간 Feature + POI 구축")
    grid_df = build_grid_dataset(target_df, force=False, city_name=target_city)
    
    # 노출량 0 지역 필터링 (서울과 동일한 기준)
    before_len = len(grid_df)
    grid_df = grid_df[grid_df["intersection_count_500m"] > 0].copy()
    log.info(f"산/강/외곽 지역 필터링: {before_len} -> {len(grid_df)}개 격자")
    
    # 4. 모델 예측
    log.info(f"\n[STEP 3] 서울 모델로 {target_city} 위험도 예측 및 평가")
    
    # 입력 데이터 구성
    X_target = grid_df[feature_names].fillna(0)
    
    # 예측 수행
    proba = model.predict_proba(X_target)[:, 1]
    grid_df["risk_score"] = (proba * 100).clip(0, 100)
    
    # 평가 (PAI 및 AUROC)
    # 여기서는 시간적 구분이 아닌, 도시 전체 데이터(label_all)로 예측 능력을 봅니다.
    auroc, pai_df = _eval_and_print(grid_df, label_col="label_all", tag=f"Cross-City: {target_city}")
    
    # 지표 저장
    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    pai_df.to_csv(output_dir / f"pai_metrics_{target_city.lower()}.csv", index=False)
    
    with open(output_dir / f"evaluation_summary_{target_city.lower()}.txt", "w", encoding="utf-8") as f:
        f.write(f"=== Cross-City Validation (Train: Seoul, Test: {target_city}) ===\n\n")
        f.write(f"- 대상 격자 수: {len(grid_df)}개\n")
        f.write(f"- 사고 포함 격자 수: {grid_df['label_all'].sum()}개\n")
        f.write(f"- AUROC: {auroc:.4f}\n")
        f.write(f"- PAI@10%: {pai_df.loc[9, 'pai']:.2f}\n")
        f.write(f"- PAI@20%: {pai_df.loc[19, 'pai']:.2f}\n")
        
    log.info(f"평가 결과 저장: outputs/evaluation_summary_{target_city.lower()}.txt")
    
    # 5. 시각화 대시보드 생성
    log.info(f"\n[STEP 4] {target_city} 위험도 히트맵 대시보드 생성")
    grid_df["위도"] = grid_df["lat_min"] + 0.0045 / 2
    grid_df["경도"] = grid_df["lon_min"] + 0.0056 / 2
    _build_cross_city_dashboard(grid_df, target_city)
    
    log.info("\n✅ Cross-City Validation 완료!")
    log.info(f"결과물: outputs/{target_city.lower()}_pm_risk_grid.html")

if __name__ == "__main__":
    run_cross_city_eval("Busan", "busan")
