import { useEffect, useState } from "react";
import "./index.css";
import { Navbar }          from "./components/Navbar";
import { HeroSection }     from "./components/HeroSection";
import { RiskMap }         from "./components/RiskMap";
import { AnalysisSection } from "./components/AnalysisSection";
import { FeaturesSection } from "./components/FeaturesSection";

function StatsBar({ metrics }) {
  const stats = [
    { value: metrics?.grid_count    ?? 2426,   suffix: "개",  label: "분석 격자 수" },
    { value: metrics?.accident_count ?? 2132,   suffix: "건",  label: "PM 사고 건수" },
    { value: "0.7908",                          suffix: "",    label: "AUROC (2025)" },
    { value: metrics?.high_risk_grids ?? 53,    suffix: "개",  label: "초고위험 격자" },
  ];
  return (
    <div className="container" style={{ marginTop: "-1px", position: "relative", zIndex: 10 }}>
      <div className="stats-bar">
        {stats.map(s => (
          <div className="stat-item" key={s.label}>
            <div className="stat-value" style={{ color: s.label.includes("AUROC") ? "var(--accent)" : "var(--text-primary)" }}>
              {s.value}{s.suffix}
            </div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Footer() {
  return (
    <footer className="footer">
      <div className="container">
        <p style={{ marginBottom: 8 }}>
          🛴 <strong>SAFERIDE</strong> — PM 사고 공간 위험도 예측 플랫폼
        </p>
        <p>
          XGBoost · OSMnx · CCTV · 지형 데이터 기반 | 서울시 500m 격자 분석 |{" "}
          <a href="https://github.com/11Won11/RoadSafe" target="_blank" rel="noreferrer">
            GitHub ↗
          </a>
        </p>
      </div>
    </footer>
  );
}

export default function App() {
  const [metrics, setMetrics] = useState(null);
  const [shap,    setShap]    = useState(null);

  useEffect(() => {
    fetch("/data/metrics_summary.json").then(r => r.json()).then(setMetrics);
    fetch("/data/shap_importance.json").then(r => r.json()).then(setShap);
  }, []);

  return (
    <div className="app">
      <Navbar />
      <main>
        <HeroSection metrics={metrics} />
        <StatsBar metrics={metrics} />
        <RiskMap />
        <AnalysisSection metrics={metrics} shap={shap} />
        <FeaturesSection />
      </main>
      <Footer />
    </div>
  );
}
