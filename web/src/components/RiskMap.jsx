import React, { useEffect, useState, useRef, useCallback } from "react";
import { MapContainer, TileLayer, GeoJSON, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

const RISK_COLORS_DARK = {
  very_high: "#FF2A2A",
  high:      "#C61A1A",
  medium:    "#8E1212",
  low:       "#540A0A",
  very_low:  "#220505",
};

const RISK_COLORS_LIGHT = {
  very_high: "#E60000",
  high:      "#FF4D4D",
  medium:    "#FF9999",
  low:       "#FFCCCC",
  very_low:  "#F5F5F5",
};

function getRiskColor(level, isDarkMode) {
  const palette = isDarkMode ? RISK_COLORS_DARK : RISK_COLORS_LIGHT;
  return palette[level] ?? palette.very_low;
}

function styleFeature(feature, isDarkMode, searchQuery = "", selectedGu = null) {
  const level = feature.properties.risk_level;
  const guName = feature.properties.gu_name || "";
  const color = getRiskColor(level, isDarkMode);

  // 구 선택 모드: 선택된 구 외 흐리게
  let isMuted = false;
  if (selectedGu) {
    isMuted = guName !== selectedGu;
  } else if (searchQuery.trim().length > 0) {
    isMuted = !guName.toLowerCase().includes(searchQuery.trim().toLowerCase());
  }

  const isSelected = selectedGu && guName === selectedGu;

  return {
    fillColor:   color,
    fillOpacity: isMuted ? 0.02 : (level === "very_low" ? (isDarkMode ? 0.12 : 0.0) : 0.75),
    color:       isSelected ? "#00F2FF" : color,
    weight:      isMuted ? 0.1 : (isSelected ? 1.5 : (level === "very_high" || level === "high" ? 1.5 : (level === "very_low" ? 0.2 : 0.8))),
    opacity:     isMuted ? 0.05 : (level === "very_low" ? (isDarkMode ? 0.3 : 0.1) : 0.9),
  };
}

const RISK_LEVEL_LABEL = {
  very_high: "매우 위험",
  high: "위험",
  medium: "주의",
  low: "관찰",
  very_low: "안전",
};

// 특정 구의 BBox로 자동 줌인하는 내부 컴포넌트
function MapController({ geoData, selectedGu }) {
  const map = useMap();

  useEffect(() => {
    if (!geoData || !selectedGu) {
      // 구 선택 해제 시 서울 전체 뷰로 복귀
      map.flyTo([37.5665, 126.978], 11.5, { duration: 1.0 });
      return;
    }

    // 선택된 구의 모든 격자 bbox 계산
    const guFeatures = geoData.features.filter(
      f => f.properties.gu_name === selectedGu
    );
    if (guFeatures.length === 0) return;

    try {
      const layer = L.geoJSON(guFeatures);
      const bounds = layer.getBounds();
      if (bounds.isValid()) {
        map.flyToBounds(bounds, { padding: [60, 60], duration: 0.8, maxZoom: 14 });
      }
    } catch (e) {
      console.warn("fitBounds error:", e);
    }
  }, [selectedGu, geoData, map]);

  return null;
}

export function RiskMap({ geoData, boundaryData, isDarkMode, searchQuery = "", selectedGu, onGuSelect }) {
  const [selectedGrid, setSelectedGrid] = useState(null);
  const [counts, setCounts] = useState({});
  const geoJsonRef = useRef(null);

  useEffect(() => {
    if (geoData) {
      const c = {};
      geoData.features.forEach(f => {
        const lv = f.properties.risk_level;
        c[lv] = (c[lv] || 0) + 1;
      });
      setCounts(c);
    }
  }, [geoData]);

  // selectedGu / searchQuery 바뀌면 스타일 새로고침
  useEffect(() => {
    if (geoJsonRef.current && geoData) {
      geoJsonRef.current.setStyle(feature =>
        styleFeature(feature, isDarkMode, searchQuery, selectedGu)
      );
    }
  }, [selectedGu, searchQuery, isDarkMode, geoData]);

  function onEachFeature(feature, layer) {
    const p = feature.properties;
    layer.on({
      mouseover(e) {
        e.target.setStyle({
          weight: 2,
          fillOpacity: 0.95,
          color: "#00F2FF",
        });
        setSelectedGrid(p);
      },
      mouseout(e) {
        if (geoJsonRef.current) {
          geoJsonRef.current.resetStyle(e.target);
        }
        setSelectedGrid(null);
      },
      click() {
        if (onGuSelect) onGuSelect(p.gu_name);
      },
    });
  }

  const LEGEND_ITEMS = [
    { level: "very_high", label: "매우 위험 (80~100점)" },
    { level: "high",      label: "위험 (60~80점)" },
    { level: "medium",    label: "주의 (40~60점)" },
    { level: "low",       label: "관찰 (20~40점)" },
    { level: "very_low",  label: "안전 (0~20점)" },
  ];

  if (!geoData) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center text-slate-600 dark:text-on-surface-variant font-mono-data gap-3">
        <span className="material-symbols-outlined animate-spin text-[40px] text-primary-container">sync</span>
        <span>공간 데이터 로딩 중...</span>
      </div>
    );
  }

  return (
    <div className="w-full h-full relative">
      <MapContainer
        center={[37.5665, 126.978]}
        zoom={11.5}
        style={{ height: "100%", width: "100%", background: "#0a0c10" }}
        zoomControl={false}
        preferCanvas={false}
      >
        {/* 자동 줌인 컨트롤러 */}
        <MapController geoData={geoData} selectedGu={selectedGu} />

        <TileLayer
          key={isDarkMode ? "dark" : "light"}
          url={isDarkMode
            ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            : "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"}
          attribution='&copy; <a href="https://carto.com">CARTO</a>'
          maxZoom={19}
        />

        {/* 서울 경계 */}
        {boundaryData && (
          <GeoJSON
            data={boundaryData}
            style={{
              color: isDarkMode ? "#00F2FF" : "#005a63",
              weight: 2,
              fillOpacity: isDarkMode ? 0.04 : 0.08,
              fillColor: isDarkMode ? "#00F2FF" : "#005a63",
              interactive: false,
            }}
          />
        )}

        {/* 격자 오버레이 */}
        <GeoJSON
          ref={geoJsonRef}
          key={`geojson-${geoData.features.length}`}
          data={geoData}
          style={(feature) => styleFeature(feature, isDarkMode, searchQuery, selectedGu)}
          onEachFeature={onEachFeature}
        />
      </MapContainer>

      {/* 선택된 구 배너 */}
      {selectedGu && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[400] pointer-events-none">
          <div className="glass-card px-5 py-2 rounded-full border border-primary-fixed-dim/50 shadow-[0_0_20px_rgba(0,242,255,0.2)] flex items-center gap-2">
            <span className="material-symbols-outlined text-[16px] text-primary-fixed-dim">map</span>
            <span className="text-body-sm font-body-sm text-slate-900 dark:text-white font-semibold">
              {selectedGu} 드릴다운 뷰
            </span>
            <span className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant ml-2">
              ESC로 전체 복귀
            </span>
          </div>
        </div>
      )}

      {/* 격자 호버 정보 패널 */}
      {selectedGrid && (
        <div className="absolute top-16 left-1/2 -translate-x-1/2 z-[400] pointer-events-none transition-opacity duration-200">
          <div className="glass-card px-4 py-3 rounded-lg shadow-[0_0_15px_rgba(0,0,0,0.5)] border-t border-primary-fixed-dim/40 min-w-[280px]">
            <div className="flex items-center gap-2 mb-2 pb-2 border-b border-black/10 dark:border-white/10">
              <span className="material-symbols-outlined text-[16px] text-primary-fixed-dim">location_on</span>
              <span className="text-body-sm font-body-sm font-semibold text-slate-900 dark:text-white tracking-wider">
                {selectedGrid.gu_name || '격자 정보'} · 격자 상세
              </span>
              <span className={`ml-auto text-[10px] px-2 py-0.5 rounded-full font-bold ${
                selectedGrid.risk_level === 'very_high' ? 'bg-error text-white' :
                selectedGrid.risk_level === 'high' ? 'bg-[#C61A1A] text-white' :
                selectedGrid.risk_level === 'medium' ? 'bg-[#8E1212] text-white' :
                'bg-black/20 dark:bg-white/10 text-slate-700 dark:text-white'
              }`}>
                {RISK_LEVEL_LABEL[selectedGrid.risk_level] || '-'}
              </span>
            </div>

            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between">
                <span className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant">위험 점수</span>
                <span className="text-mono-data font-mono-data text-slate-900 dark:text-white font-bold">{selectedGrid.risk_pct}점</span>
              </div>
              <div className="flex justify-between">
                <span className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant">킥보드 견인 수</span>
                <span className="text-mono-data font-mono-data text-[#ff9500] font-bold">{selectedGrid.towing_cnt}건</span>
              </div>
              <div className="flex justify-between">
                <span className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant">상업시설 수</span>
                <span className="text-mono-data font-mono-data text-slate-900 dark:text-white">{selectedGrid.poi_commercial}개</span>
              </div>
              <div className="flex justify-between">
                <span className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant">교차로 수 (500m)</span>
                <span className="text-mono-data font-mono-data text-slate-900 dark:text-white">{selectedGrid.intersect_500}개</span>
              </div>
              <div className="flex justify-between">
                <span className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant">신호등 / 횡단보도</span>
                <span className="text-mono-data font-mono-data text-slate-900 dark:text-white">
                  {selectedGrid.signal_total ?? '-'} / {selectedGrid.crosswalk_cnt ?? 0}개
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant">경사도 (표고 범위)</span>
                <span className="text-mono-data font-mono-data text-[#ffcc00]">{selectedGrid.elev_range}m</span>
              </div>
              <div className="flex justify-between">
                <span className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant">사고 (전체 / 2025)</span>
                <span className="text-mono-data font-mono-data text-error">{selectedGrid.acc_total}건 / {selectedGrid.acc_2025}건</span>
              </div>
            </div>

            <div className="mt-2 pt-2 border-t border-black/10 dark:border-white/10 text-[10px] text-slate-500 text-center">
              클릭하면 {selectedGrid.gu_name} 드릴다운
            </div>
          </div>
        </div>
      )}

      {/* 범례 */}
      <div className="absolute bottom-8 right-8 z-[400] glass-card p-4 rounded-lg pointer-events-none">
        <h4 className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant uppercase tracking-widest mb-3 border-b border-black/5 dark:border-white/5 pb-2">위험도 범례</h4>
        <div className="flex flex-col gap-2">
          {LEGEND_ITEMS.map(item => (
            <div key={item.level} className="flex items-center gap-3">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: getRiskColor(item.level, isDarkMode), border: `1px solid ${getRiskColor(item.level, isDarkMode)}80` }}
              />
              <span className="text-body-sm font-body-sm text-slate-900 dark:text-white">
                {item.label}
                {counts[item.level] && <span className="text-slate-600 dark:text-on-surface-variant ml-1 font-mono-data">({counts[item.level]})</span>}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default RiskMap;
