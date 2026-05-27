/* Hero Section */
export function HeroSection({ metrics }) {
  const auroc = metrics?.auroc_2025 ?? 0.7908;
  const pai   = metrics?.pai_table_2025?.find(r => r.k === 50)?.capture ?? 90.4;

  return (
    <section className="hero" id="overview">
      <div className="hero-bg" />
      <div className="hero-grid" />
      <div className="hero-content">
        <div className="hero-badge">
          <span>🛴</span>
          <span>PM 사고 공간 위험도 예측 AI</span>
        </div>

        <h1 className="hero-title">
          사고가 나기 전에<br />
          <span className="gradient">위험한 공간</span>을<br />
          먼저 바꿉니다.
        </h1>

        <p className="hero-sub">
          서울시 전동킥보드(PM) 사고 데이터와 도로망·CCTV·지형 정보를 결합하여
          서울 전역의 사고 위험도를 <strong>500m 격자 단위</strong>로 예측합니다.
        </p>

        <div className="hero-cta">
          <a className="btn-primary" href="#map">
            🗺️ 위험 지도 보기
          </a>
          <a className="btn-secondary" href="#analysis">
            📊 성능 분석
          </a>
        </div>

        {/* 핵심 지표 배지 */}
        <div
          style={{
            display: "flex",
            gap: 16,
            justifyContent: "center",
            marginTop: 48,
            flexWrap: "wrap",
          }}
        >
          {[
            { label: "AUROC", value: auroc.toFixed(4), color: "var(--accent)" },
            { label: "상위 50% 포착률", value: `${pai}%`, color: "var(--accent-orange)" },
            { label: "부산 전이성", value: "0.9105", color: "var(--accent-blue)" },
            { label: "Feature", value: "21개", color: "var(--accent-green)" },
          ].map(b => (
            <div
              key={b.label}
              style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 12,
                padding: "14px 22px",
                textAlign: "center",
                backdropFilter: "blur(8px)",
              }}
            >
              <div style={{ fontSize: "1.5rem", fontWeight: 800, color: b.color, fontFamily: "Inter,sans-serif", letterSpacing: "-0.03em" }}>
                {b.value}
              </div>
              <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)", marginTop: 4, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                {b.label}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
