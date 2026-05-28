import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import "leaflet/dist/leaflet.css";

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

function styleFeature(feature, isDarkMode, searchQuery = "") {
  const level = feature.properties.risk_level;
  const districtName = feature.properties.SIG_KOR_NM || "";
  const color = getRiskColor(level, isDarkMode);
  
  let isMuted = false;
  if (searchQuery.trim().length > 0) {
    if (!districtName.toLowerCase().includes(searchQuery.trim().toLowerCase())) {
      isMuted = true;
    }
  }

  return {
    fillColor:   color,
    fillOpacity: isMuted ? 0.02 : (level === "very_low" ? (isDarkMode ? 0.1 : 0.0) : 0.7),
    color:       color,
    weight:      isMuted ? 0.1 : (level === "very_high" || level === "high" ? 1.5 : (level === "very_low" ? 0.2 : 0.8)),
    opacity:     isMuted ? 0.05 : (level === "very_low" ? (isDarkMode ? 0.3 : 0.1) : 0.9),
  };
}

export function RiskMap({ geoData, boundaryData, isDarkMode, searchQuery = "" }) {
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
        e.target.setStyle(styleFeature(feature, isDarkMode, searchQuery));
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
      <div className="w-full h-full flex items-center justify-center text-slate-600 dark:text-on-surface-variant font-mono-data">
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
        preferCanvas={true}
      >
        <TileLayer
          key={isDarkMode ? "dark" : "light"}
          url={isDarkMode 
            ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            : "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"}
          attribution='&copy; <a href="https://carto.com">CARTO</a>'
          maxZoom={19}
        />
        
        {/* Custom Vector Base Map (Seoul Boundary) */}
        {boundaryData && (
          <GeoJSON 
            data={boundaryData} 
            style={{
              color: isDarkMode ? "#00F2FF" : "#005a63",     // Glowing neon cyan outline for dark, deep teal for light
              weight: 2,
              fillOpacity: isDarkMode ? 0.05 : 0.1,    // Faint fill
              fillColor: isDarkMode ? "#00F2FF" : "#005a63",
              interactive: false,   // Disable pointer events on the boundary
            }}
          />
        )}
        
        {/* Grid Overlay */}
        <GeoJSON
          key={geoData.features.length + searchQuery}
          data={geoData}
          style={(feature) => styleFeature(feature, isDarkMode, searchQuery)}
          onEachFeature={onEachFeature}
        />
      </MapContainer>

      {/* Floating Info Panel (Hover) */}
      {selectedGrid && (
        <div className="absolute top-24 left-1/2 -translate-x-1/2 z-[400] pointer-events-none transition-opacity duration-200">
          <div className="glass-card px-4 py-3 rounded-lg shadow-[0_0_15px_rgba(0,0,0,0.5)] border-t border-primary-fixed-dim/40 min-w-[240px]">
            <div className="flex items-center gap-2 mb-2 pb-2 border-b border-black/10 dark:border-white/10">
              <span className="material-symbols-outlined text-[16px] text-primary-fixed-dim">location_on</span>
              <span className="text-body-sm font-body-sm font-semibold text-slate-900 dark:text-white tracking-wider">GRID INSPECTION</span>
            </div>
            
            <div className="flex flex-col gap-1">
              <div className="flex justify-between">
                <span className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant">Risk Score</span>
                <span className="text-mono-data font-mono-data text-slate-900 dark:text-white">{selectedGrid.risk_pct}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant">Intersections</span>
                <span className="text-mono-data font-mono-data text-slate-900 dark:text-white">{selectedGrid.intersections_500m}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant">Signals / Crosswalks</span>
                <span className="text-mono-data font-mono-data text-slate-900 dark:text-white">{selectedGrid.signal_total} / {selectedGrid.crosswalk_count || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant">Elevation Range</span>
                <span className="text-mono-data font-mono-data text-[#ffcc00]">{selectedGrid.elev_range}m</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-8 right-8 z-[400] glass-card p-4 rounded-lg pointer-events-none">
        <h4 className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant uppercase tracking-widest mb-3 border-b border-black/5 dark:border-white/5 pb-2">Risk Legend</h4>
        <div className="flex flex-col gap-2">
          {LEGEND_ITEMS.map(item => (
            <div key={item.level} className="flex items-center gap-3">
              <div 
                className="w-3 h-3 rounded-full shadow-[0_0_8px_rgba(255,255,255,0.2)]" 
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
