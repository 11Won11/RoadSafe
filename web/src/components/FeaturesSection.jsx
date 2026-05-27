/* Feature 소개 섹션 */
export function FeaturesSection() {
  const groups = [
    {
      icon: "🛣️",
      title: "도로망 인프라",
      desc: "OSMnx 기반 교차로 밀도, 차선 수, 도로 유형 등 도로 구조적 특성 16개",
      count: "16개 Feature",
      items: ["반경 500m 교차로 수 (SHAP 1위)", "평균/최대 차선 수", "간선도로·이면도로 여부", "버스정류장·지하철역·상업시설 POI"],
    },
    {
      icon: "📹",
      title: "CCTV 감시 억제",
      desc: "서울시 전체 7만여 대 CCTV를 격자에 매핑하여 감시·억제 효과를 정량화",
      count: "3개 Feature",
      items: ["전체 카메라 수", "교통단속 카메라 수", "어린이보호구역 카메라 수"],
    },
    {
      icon: "⛰️",
      title: "지형 / 경사도",
      desc: "서울시 76,580개 표고 측정점 기반. PM 브레이크 제동력 한계 지형 특성 반영",
      count: "2개 Feature",
      items: ["평균 표고 (m)", "격자 내 경사도 (최고-최저 표고 차)"],
    },
    {
      icon: "🧠",
      title: "Poisson Regression",
      desc: "사고 건수는 희귀 사건 계수형 데이터이므로 XGBoost에 Poisson 목적함수 적용",
      count: "count:poisson",
      items: ["과분산(Overdispersion) 자동 처리", "Optuna 30회 HPO 자동 튜닝", "Zero-exposure 격자 사전 필터링"],
    },
    {
      icon: "📊",
      title: "시간적 홀드아웃",
      desc: "2021~2024년 데이터로 학습, 2025년 실제 미래 사고 대비 예측력 검증",
      count: "AUROC 0.7908",
      items: ["데이터 누수(Leakage) 없는 평가", "PAI·RRI 지표 동시 계산", "부산 Zero-shot 전이성 검증"],
    },
    {
      icon: "🌏",
      title: "공간 일반화",
      desc: "서울 데이터만으로 학습한 모델이 부산광역시에서도 최고 수준 예측력 달성",
      count: "부산 AUROC 0.9105",
      items: ["도시 간 공간 패턴의 보편성 입증", "PAI@10% = 5.64 (부산)", "Zero-shot 예측, 부산 데이터 미사용"],
    },
  ];

  return (
    <section className="section" id="features">
      <div className="container">
        <div className="section-header">
          <span className="section-eyebrow">Architecture</span>
          <h2 className="section-title">모델 구성 및 방법론</h2>
          <p className="section-desc">
            세 가지 데이터 소스에서 추출한 21개 공간 Feature와 엄밀한 검증 체계로 구성됩니다.
          </p>
        </div>

        <div className="features-grid">
          {groups.map(g => (
            <div className="glass-card feature-card" key={g.title}>
              <div className="feature-icon">{g.icon}</div>
              <div className="feature-title">{g.title}</div>
              <div className="feature-desc">{g.desc}</div>
              <ul style={{ marginTop: 14, paddingLeft: 16, color: "var(--text-secondary)", fontSize: "0.78rem", lineHeight: 1.8 }}>
                {g.items.map(item => <li key={item}>{item}</li>)}
              </ul>
              <span className="feature-count">{g.count}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
