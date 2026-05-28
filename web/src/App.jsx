import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import RiskOverviewPanel from './components/RiskOverviewPanel';
import AnalyticsPanel from './components/AnalyticsPanel';
import { RiskMap } from './components/RiskMap';

function App() {
  const [geoData, setGeoData] = useState(null);
  const [boundaryData, setBoundaryData] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [shapData, setShapData] = useState(null);
  const [isDarkMode, setIsDarkMode] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    // Sync initial state with html class
    if (document.documentElement.classList.contains('dark')) {
      setIsDarkMode(true);
    } else {
      setIsDarkMode(false);
    }
  }, []);

  const toggleTheme = () => {
    setIsDarkMode((prev) => {
      const next = !prev;
      if (next) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
      return next;
    });
  };

  useEffect(() => {
    // Load GeoJSON
    fetch('/data/grid_predictions.geojson')
      .then(res => res.json())
      .then(data => setGeoData(data))
      .catch(err => console.error("Error loading geojson", err));

    // Load Boundary GeoJSON
    fetch('/data/seoul_boundary.geojson')
      .then(res => res.json())
      .then(data => setBoundaryData(data))
      .catch(err => console.error("Error loading boundary", err));

    // Load Metrics
    fetch('/data/metrics_summary.json')
      .then(res => res.json())
      .then(data => setMetrics(data))
      .catch(err => console.error("Error loading metrics", err));

    // Load SHAP Importance
    fetch('/data/shap_importance.json')
      .then(res => res.json())
      .then(data => setShapData(data))
      .catch(err => console.error("Error loading SHAP data", err));
  }, []);

  return (
    <div className="bg-slate-50 text-slate-900 dark:bg-background dark:text-on-surface min-h-screen overflow-hidden selection:bg-primary-container selection:text-on-primary-container transition-colors duration-300">
      <Navbar isDarkMode={isDarkMode} toggleTheme={toggleTheme} searchQuery={searchQuery} setSearchQuery={setSearchQuery} />
      <Sidebar />
      
      {/* Main Content Canvas (Map Background) */}
      <main className="relative w-full h-screen pt-16 lg:pl-64 bg-slate-100 dark:bg-[#0a0c10] overflow-hidden transition-colors duration-300">
        
        {/* Full-screen Leaflet Map */}
        <div className="absolute inset-0 z-0">
          <RiskMap geoData={geoData} boundaryData={boundaryData} isDarkMode={isDarkMode} searchQuery={searchQuery} />
        </div>

        {/* Map Grid Overlay for styling (pointer-events-none) */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none z-[1]"></div>
        
        {/* Dashboard Overlay Panels */}
        <div className="relative z-10 w-full h-full p-container-padding flex justify-between items-start gap-gutter pointer-events-none">
          {/* Left Panel */}
          <RiskOverviewPanel 
            metrics={metrics}
            geoData={geoData}
          />
          
          {/* Right Panel */}
          <AnalyticsPanel 
            metrics={metrics}
            shapData={shapData}
          />
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
