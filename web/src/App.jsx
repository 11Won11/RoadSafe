import React, { useState, useEffect, useCallback } from 'react';
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
  const [selectedGu, setSelectedGu] = useState(null); // 선택된 구(District)

  useEffect(() => {
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

  // ESC 키로 드릴다운 해제
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setSelectedGu(null);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    fetch('data/grid_predictions.geojson')
      .then(res => res.json())
      .then(data => setGeoData(data))
      .catch(err => console.error("Error loading geojson", err));

    fetch('data/seoul_boundary.geojson')
      .then(res => res.json())
      .then(data => setBoundaryData(data))
      .catch(err => console.error("Error loading boundary", err));

    fetch('data/metrics_summary.json')
      .then(res => res.json())
      .then(data => setMetrics(data))
      .catch(err => console.error("Error loading metrics", err));

    fetch('data/shap_importance.json')
      .then(res => res.json())
      .then(data => setShapData(data))
      .catch(err => console.error("Error loading SHAP data", err));
  }, []);

  const handleGuSelect = useCallback((guName) => {
    setSelectedGu(prev => prev === guName ? null : guName);
    setSearchQuery(""); // 검색창 초기화
  }, []);

  const handleGuClear = useCallback(() => {
    setSelectedGu(null);
  }, []);

  return (
    <div className="bg-slate-50 text-slate-900 dark:bg-background dark:text-on-surface min-h-screen overflow-hidden selection:bg-primary-container selection:text-on-primary-container transition-colors duration-300">
      <Navbar
        isDarkMode={isDarkMode}
        toggleTheme={toggleTheme}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        selectedGu={selectedGu}
        onGuClear={handleGuClear}
      />
      <Sidebar />
      
      {/* Main Content Canvas (Map Background) */}
      <main className="relative w-full h-screen pt-16 lg:pl-64 bg-slate-100 dark:bg-[#0a0c10] overflow-hidden transition-colors duration-300">
        
        {/* Full-screen Leaflet Map */}
        <div className="absolute inset-0 z-0">
          <RiskMap
            geoData={geoData}
            boundaryData={boundaryData}
            isDarkMode={isDarkMode}
            searchQuery={searchQuery}
            selectedGu={selectedGu}
            onGuSelect={handleGuSelect}
          />
        </div>

        {/* Map Grid Overlay for styling (pointer-events-none) */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none z-[1]"></div>
        
        {/* Dashboard Overlay Panels */}
        <div className="relative z-10 w-full h-full p-container-padding flex justify-between items-start gap-gutter pointer-events-none">
          {/* Left Panel */}
          <RiskOverviewPanel 
            metrics={metrics}
            geoData={geoData}
            selectedGu={selectedGu}
            onGuSelect={handleGuSelect}
            onGuClear={handleGuClear}
          />
          
          {/* Right Panel */}
          <AnalyticsPanel 
            metrics={metrics}
            shapData={shapData}
            geoData={geoData}
            selectedGu={selectedGu}
          />
        </div>

        {/* 드릴다운 선택 시 — 뒤로가기 Floating Button */}
        {selectedGu && (
          <div className="absolute bottom-8 left-[calc(50%+128px)] -translate-x-1/2 z-20 pointer-events-auto">
            <button
              onClick={handleGuClear}
              className="glass-panel px-5 py-2 rounded-full flex items-center gap-2 shadow-lg hover:bg-white/10 transition-colors text-slate-900 dark:text-white text-body-sm font-body-sm"
            >
              <span className="material-symbols-outlined text-[18px]">arrow_back</span>
              서울 전체 보기
            </button>
          </div>
        )}

      </main>
    </div>
  );
}

export default App;
