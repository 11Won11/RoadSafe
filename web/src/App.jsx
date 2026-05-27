import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import RiskOverviewPanel from './components/RiskOverviewPanel';
import AnalyticsPanel from './components/AnalyticsPanel';
import { RiskMap } from './components/RiskMap';

function App() {
  const [geoData, setGeoData] = useState(null);
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    // Load GeoJSON
    fetch('/data/risk_grid_seoul.geojson')
      .then(res => res.json())
      .then(data => setGeoData(data))
      .catch(err => console.error("Error loading geojson", err));

    // Load Metrics
    fetch('/data/metrics_summary.json')
      .then(res => res.json())
      .then(data => setMetrics(data))
      .catch(err => console.error("Error loading metrics", err));
  }, []);

  return (
    <div className="bg-background text-on-surface min-h-screen overflow-hidden selection:bg-primary-container selection:text-on-primary-container">
      <Navbar />
      <Sidebar />
      
      {/* Main Content Canvas (Map Background) */}
      <main className="relative w-full h-screen pt-16 lg:pl-64 bg-[#0a0c10] overflow-hidden">
        
        {/* Full-screen Leaflet Map */}
        <div className="absolute inset-0 z-0">
          <RiskMap geoData={geoData} />
        </div>

        {/* Map Grid Overlay for styling (pointer-events-none) */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none z-[1]"></div>
        
        {/* Dashboard Overlay Panels */}
        <div className="relative z-10 w-full h-full p-container-padding flex justify-between items-start gap-gutter pointer-events-none">
          {/* Left Panel */}
          <RiskOverviewPanel 
            totalIncidents={metrics?.accident_count || 2132}
            totalRisk={metrics?.grid_count || 2426}
          />
          
          {/* Right Panel */}
          <AnalyticsPanel />
        </div>

        {/* Floating Map Controls (Bottom Center) */}
        <div className="absolute bottom-8 left-[calc(50%+128px)] -translate-x-1/2 z-20 pointer-events-auto">
          <div className="glass-panel p-2 rounded-full flex gap-1 shadow-lg">
            <button className="w-10 h-10 rounded-full hover:bg-white/10 flex items-center justify-center text-white transition-colors" title="Zoom In">
              <span className="material-symbols-outlined text-[20px]">add</span>
            </button>
            <button className="w-10 h-10 rounded-full hover:bg-white/10 flex items-center justify-center text-white transition-colors" title="Reset View">
              <span className="material-symbols-outlined text-[20px]">my_location</span>
            </button>
            <button className="w-10 h-10 rounded-full hover:bg-white/10 flex items-center justify-center text-white transition-colors" title="Zoom Out">
              <span className="material-symbols-outlined text-[20px]">remove</span>
            </button>
          </div>
        </div>

      </main>
    </div>
  );
}

export default App;
