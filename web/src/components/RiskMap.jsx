import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const RISK_COLORS = {
  very_high: "#FF3B30",
  high:      "#FF9500",
  medium:    "#FFCC00",
  low:       "#34C759",
  very_low:  "#0B0E14", // dark void
};

function getRiskColor(level) {
  return RISK_COLORS[level] ?? RISK_COLORS.very_low;
}

function styleFeature(feature) {
  const level = feature.properties.risk_level;
  const color = getRiskColor(level);
  return {
    fillColor:   color,
    fillOpacity: level === "very_low" ? 0.05 : 0.6,
    color:       color,
    weight:      level === "very_high" || level === "high" ? 1.5 : 0.5,
    opacity:     level === "very_low" ? 0.1 : 0.8,
  };
}

export function RiskMap({ geoData }) {
  const [selectedGrid, setSelectedGrid] = useState(null);
  const [counts, setCounts] = useState({});

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

  function onEachFeature(feature, layer) {
    const p = feature.properties;
    layer.on({
      mouseover(e) {
        e.target.setStyle({ weight: 2, fillOpacity: 0.9, color: "#00F2FF" });
        setSelectedGrid(p);
      },
      mouseout(e) {
        e.target.setStyle(styleFeature(feature));
        setSelectedGrid(null);
      },
    });
  }

  const LEGEND_ITEMS = [
    { level: "very_high", label: "Critical (80~100)" },
    { level: "high",      label: "Elevated (60~80)" },
    { level: "medium",    label: "Warning (40~60)" },
    { level: "low",       label: "Monitor (20~40)" },
    { level: "very_low",  label: "Optimal (0~20)" },
  ];

  if (!geoData) {
    return (
      <div className="w-full h-full flex items-center justify-center text-on-surface-variant font-mono-data">
        <span className="material-symbols-outlined animate-spin mr-2">sync</span>
        Loading Spatial Data...
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

      {/* Floating Info Panel (Hover) */}
      {selectedGrid && (
        <div className="absolute top-24 left-1/2 -translate-x-1/2 z-[400] pointer-events-none transition-opacity duration-200">
          <div className="glass-card px-4 py-3 rounded-lg shadow-[0_0_15px_rgba(0,0,0,0.5)] border-t border-primary-fixed-dim/40 min-w-[240px]">
            <div className="flex items-center gap-2 mb-2 pb-2 border-b border-white/10">
              <span className="material-symbols-outlined text-[16px] text-primary-fixed-dim">location_on</span>
              <span className="text-body-sm font-body-sm font-semibold text-white tracking-wider">GRID INSPECTION</span>
            </div>
            
            <div className="flex flex-col gap-1">
              <div className="flex justify-between">
                <span className="text-label-md font-label-md text-on-surface-variant">Risk Score</span>
                <span className="text-mono-data font-mono-data text-white">{selectedGrid.risk_pct}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-label-md font-label-md text-on-surface-variant">Intersections</span>
                <span className="text-mono-data font-mono-data text-white">{selectedGrid.intersections_500m}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-label-md font-label-md text-on-surface-variant">Signals / Crosswalks</span>
                <span className="text-mono-data font-mono-data text-white">{selectedGrid.signal_total} / {selectedGrid.crosswalk_count || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-label-md font-label-md text-on-surface-variant">Elevation Range</span>
                <span className="text-mono-data font-mono-data text-[#ffcc00]">{selectedGrid.elev_range}m</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-8 right-8 z-[400] glass-card p-4 rounded-lg pointer-events-none">
        <h4 className="text-label-md font-label-md text-on-surface-variant uppercase tracking-widest mb-3 border-b border-white/5 pb-2">Risk Legend</h4>
        <div className="flex flex-col gap-2">
          {LEGEND_ITEMS.map(item => (
            <div key={item.level} className="flex items-center gap-3">
              <div 
                className="w-3 h-3 rounded-full shadow-[0_0_8px_rgba(255,255,255,0.2)]" 
                style={{ backgroundColor: getRiskColor(item.level), border: `1px solid ${getRiskColor(item.level)}80` }}
              />
              <span className="text-body-sm font-body-sm text-white">
                {item.label}
                {counts[item.level] && <span className="text-on-surface-variant ml-1 font-mono-data">({counts[item.level]})</span>}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default RiskMap;
