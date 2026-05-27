import { useEffect, useState, useRef } from "react";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";

const RISK_COLORS = {
  very_high: "#ff2d2d",
  high:      "#ff7b2d",
  medium:    "#ffd166",
  low:       "#4dffb4",
  very_low:  "#1a2840",
};

function getRiskColor(level) {
  return RISK_COLORS[level] ?? RISK_COLORS.very_low;
}

function styleFeature(feature) {
  const level = feature.properties.risk_level;
  const color = getRiskColor(level);
  return {
    fillColor:   color,
    fillOpacity: level === "very_low" ? 0.05 : 0.55,
    color:       color,
    weight:      level === "very_high" || level === "high" ? 1.5 : 0.5,
    opacity:     level === "very_low" ? 0.2 : 0.8,
  };
}

export function RiskMap() {
  const [geoData, setGeoData] = useState(null);
  const [selectedGrid, setSelectedGrid] = useState(null);
  const [counts, setCounts] = useState({});

  useEffect(() => {
    fetch("/data/grid_predictions.geojson")
      .then(r => r.json())
      .then(data => {
        setGeoData(data);
        // 위험 등급 집계
        const c = {};
        data.features.forEach(f => {
          const lv = f.properties.risk_level;
          c[lv] = (c[lv] || 0) + 1;
        });
        setCounts(c);
      });
  }, []);

  function onEachFeature(feature, layer) {
    const p = feature.properties;
    layer.on({
      mouseover(e) {
        e.target.setStyle({ weight: 2, fillOpacity: 0.8 });
        setSelectedGrid(p);
      },
      mouseout(e) {
        e.target.setStyle(styleFeature(feature));
        setSelectedGrid(null);
      },
    });
  }

  const LEGEND_ITEMS = [
    { level: "very_high", label: "매우 위험 (80~100)" },
    { level: "high",      label: "위험 (60~80)" },
    { level: "medium",    label: "주의 (40~60)" },
    { level: "low",       label: "낮음 (20~40)" },
    { level: "very_low",  label: "안전 (0~20)" },
  ];

  return (
    <section className="map-section" id="map">
      <div className="container-wide">
        <div className="section-header">
          <span className="section-eyebrow">Risk Heatmap</span>
          <h2 className="section-title">서울시 PM 사고 위험도 지도</h2>
          <p className="section-desc">
            격자 위로 마우스를 올리면 해당 구역의 위험도 상세 정보를 확인할 수 있습니다.
          </p>
        </div>

        <div className="map-wrapper">
          {geoData ? (
            <MapContainer
              center={[37.5665, 126.978]}
              zoom={11}
              style={{ height: "100%", width: "100%" }}
              zoomControl={true}
            >
              <TileLayer
                url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                attribution='&copy; <a href="https://carto.com">CARTO</a>'
                maxZoom={19}
              />
              <GeoJSON
                key={geoData.features.length}
                data={geoData}
                style={styleFeature}
                onEachFeature={onEachFeature}
              />
            </MapContainer>
          ) : (
            <div style={{ height:"100%",display:"flex",alignItems:"center",justifyContent:"center",color:"var(--text-muted)" }}>
              지도 로딩 중...
            </div>
          )}

          {/* 선택된 격자 정보 패널 */}
          {selectedGrid && (
            <div className="map-info-panel">
              <div className="map-info-title">📍 격자 위험도 상세</div>
              {[
                ["위험도 점수", `${selectedGrid.risk_pct}/100`],
                ["누적 사고", `${selectedGrid.acc_total}건`],
                ["2025 사고", `${selectedGrid.acc_2025}건`],
                ["평균 차선", `${selectedGrid.avg_lanes}개`],
                ["CCTV 수", `${selectedGrid.cctv_total}대`],
                ["경사도", `±${selectedGrid.elev_range}m`],
                ["POI 수", `${selectedGrid.poi_total}개`],
              ].map(([k, v]) => (
                <div className="map-info-row" key={k}>
                  <span className="map-info-key">{k}</span>
                  <span className="map-info-val">{v}</span>
                </div>
              ))}
            </div>
          )}

          {/* 범례 */}
          <div className="map-legend">
            <div className="legend-title">위험도 등급</div>
            {LEGEND_ITEMS.map(item => (
              <div className="legend-item" key={item.level}>
                <div className="legend-dot" style={{ background: getRiskColor(item.level) }} />
                <span style={{ color: "var(--text-secondary)", fontSize: "0.75rem" }}>
                  {item.label}
                  {counts[item.level] ? ` (${counts[item.level]})` : ""}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
