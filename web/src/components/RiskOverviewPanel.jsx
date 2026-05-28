import React, { useMemo } from 'react';

const RiskOverviewPanel = ({ metrics, geoData, selectedGu, onGuSelect, onGuClear }) => {

  // 구별 통계 집계 (전체 및 드릴다운용)
  const allDistrictStats = useMemo(() => {
    if (!geoData || !geoData.features) return {};
    const stats = {};
    geoData.features.forEach(f => {
      const p = f.properties;
      const gu = p.gu_name || '미분류';
      if (!stats[gu]) stats[gu] = { riskSum: 0, count: 0, accidents: 0, acc2025: 0, highRisk: 0, towing: 0 };
      stats[gu].riskSum += (p.risk_pct || 0);
      stats[gu].count += 1;
      stats[gu].accidents += (p.acc_total || 0);
      stats[gu].acc2025 += (p.acc_2025 || 0);
      stats[gu].towing += (p.towing_cnt || 0);
      if (p.risk_level === 'very_high' || p.risk_level === 'high') stats[gu].highRisk += 1;
    });
    return stats;
  }, [geoData]);

  const topDistricts = useMemo(() => {
    return Object.entries(allDistrictStats)
      .map(([district, s]) => ({ district, avgRisk: s.riskSum / s.count, ...s }))
      .sort((a, b) => b.avgRisk - a.avgRisk)
      .slice(0, 5);
  }, [allDistrictStats]);

  // 선택된 구의 격자 목록 (위험도 상위 5개)
  const guFeatures = useMemo(() => {
    if (!geoData || !selectedGu) return [];
    return geoData.features
      .map(f => f.properties)
      .filter(p => p.gu_name === selectedGu)
      .sort((a, b) => b.risk_pct - a.risk_pct);
  }, [geoData, selectedGu]);

  const guStats = selectedGu ? allDistrictStats[selectedGu] : null;

  // 전체 평균 위험도
  const totalAvgRisk = useMemo(() => {
    if (!geoData || !geoData.features) return '0.0';
    let sum = 0;
    geoData.features.forEach(f => sum += (f.properties.risk_pct || 0));
    return (sum / geoData.features.length).toFixed(1);
  }, [geoData]);

  const highRiskCount = useMemo(() => {
    if (!geoData || !geoData.features) return 0;
    return geoData.features.filter(f =>
      f.properties.risk_level === 'very_high' || f.properties.risk_level === 'high'
    ).length;
  }, [geoData]);

  const totalFeatures = geoData?.features?.length ?? 2426;

  return (
    <div className="w-[340px] h-[calc(100vh-112px)] glass-panel rounded-xl flex flex-col pointer-events-auto transform transition-all hover:-translate-y-1 hover:shadow-lg overflow-hidden">
      {/* 헤더 */}
      <div className="p-panel-internal border-b border-black/5 dark:border-white/5 flex justify-between items-center bg-white/[0.02] shrink-0">
        {selectedGu ? (
          <div className="flex items-center gap-2">
            <button onClick={onGuClear} className="text-slate-600 dark:text-on-surface-variant hover:text-primary-fixed-dim transition-colors">
              <span className="material-symbols-outlined text-[20px]">arrow_back</span>
            </button>
            <h3 className="text-headline-sm font-headline-sm font-semibold text-primary-fixed-dim tracking-tight">{selectedGu}</h3>
          </div>
        ) : (
          <h3 className="text-headline-sm font-headline-sm font-semibold text-slate-900 dark:text-white tracking-tight">위험도 개요</h3>
        )}
        <span className="material-symbols-outlined text-slate-600 dark:text-on-surface-variant text-[20px]">
          {selectedGu ? 'location_city' : 'filter_list'}
        </span>
      </div>

      <div className="p-panel-internal flex-1 overflow-y-auto flex flex-col gap-card-gap">

        {/* ====== 전체 뷰 ====== */}
        {!selectedGu && (
          <>
            {/* 서울 전체 평균 위험도 */}
            <div className="glass-card p-panel-internal rounded-lg neon-border-active">
              <div className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant uppercase tracking-widest mb-1">서울시 전체</div>
              <div className="flex items-baseline gap-2 mb-2">
                <span className="text-display-lg font-display-lg text-primary-fixed-dim">{totalAvgRisk}</span>
                <span className="text-body-sm font-body-sm text-error flex items-center">
                  <span className="material-symbols-outlined text-[14px]">trending_up</span> 평균 위험 점수
                </span>
              </div>
              <div className="w-full h-1 bg-black/10 dark:bg-white/10 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-primary-fixed-dim to-error" style={{ width: `${Math.min(100, parseFloat(totalAvgRisk))}%` }}></div>
              </div>
            </div>

            {/* 주요 통계 */}
            <div className="grid grid-cols-2 gap-card-gap">
              <div className="glass-card p-4 rounded-lg">
                <div className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant mb-1">총 사고 건수</div>
                <div className="text-headline-md font-headline-md text-slate-900 dark:text-white font-mono-data">{metrics?.accident_count ?? '-'}건</div>
                <div className="text-[10px] text-slate-500 mt-1">2021~2025년</div>
              </div>
              <div className="glass-card p-4 rounded-lg">
                <div className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant mb-1">고위험 격자</div>
                <div className="text-headline-md font-headline-md text-error font-mono-data">{highRiskCount}개</div>
                <div className="text-[10px] text-slate-500 mt-1">전체 {totalFeatures}개 중</div>
              </div>
            </div>

            {/* 모델 성능 */}
            <div className="glass-card p-4 rounded-lg">
              <div className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant mb-2">모델 성능 (2025 홀드아웃)</div>
              <div className="flex justify-between items-center">
                <span className="text-body-sm text-slate-900 dark:text-white">AUROC</span>
                <span className="text-primary-fixed-dim font-mono-data font-bold">{metrics?.auroc_2025?.toFixed(4) ?? '-'}</span>
              </div>
              <div className="flex justify-between items-center mt-1">
                <span className="text-body-sm text-slate-900 dark:text-white">피처 수</span>
                <span className="text-slate-900 dark:text-white font-mono-data">{metrics?.feature_count ?? 26}개</span>
              </div>
              <div className="flex justify-between items-center mt-1">
                <span className="text-body-sm text-slate-900 dark:text-white">k=50% 포착률</span>
                <span className="text-[#4ade80] font-mono-data font-bold">92.3%</span>
              </div>
            </div>

            {/* 위험도 상위 구 — 클릭 가능 */}
            <div className="mt-2">
              <h4 className="text-body-sm font-body-sm text-slate-600 dark:text-on-surface-variant mb-3 font-semibold tracking-wide">
                위험도 상위 구 <span className="font-normal text-[10px] ml-1 opacity-70">(클릭하면 드릴다운)</span>
              </h4>
              <div className="flex flex-col gap-2">
                {topDistricts.map((item, index) => (
                  <button
                    key={item.district}
                    onClick={() => onGuSelect(item.district)}
                    className="flex items-center gap-3 p-2 hover:bg-black/5 dark:hover:bg-white/5 rounded transition-colors text-left w-full group"
                  >
                    <div className={`w-6 h-6 rounded flex items-center justify-center text-label-md font-label-md font-bold shrink-0 ${
                      index === 0 ? 'bg-error text-white shadow-[0_0_8px_rgba(255,59,48,0.4)]' :
                      index === 1 ? 'bg-[#ff9500] text-white shadow-[0_0_8px_rgba(255,149,0,0.4)]' :
                      index === 2 ? 'bg-[#ffcc00] text-slate-900 shadow-[0_0_8px_rgba(255,204,0,0.4)]' : 'bg-black/10 dark:bg-white/10 text-slate-600 dark:text-on-surface-variant'
                    }`}>
                      {index + 1}
                    </div>
                    <span className="text-body-md font-body-md text-slate-900 dark:text-white flex-1 group-hover:text-primary-fixed-dim transition-colors">{item.district}</span>
                    <div className="flex flex-col items-end">
                      <span className="text-mono-data font-mono-data text-slate-600 dark:text-on-surface-variant text-sm">{item.avgRisk.toFixed(1)}점</span>
                      <span className="text-[10px] text-slate-500">{item.accidents}건</span>
                    </div>
                    <span className="material-symbols-outlined text-[16px] text-slate-400 group-hover:text-primary-fixed-dim transition-colors">chevron_right</span>
                  </button>
                ))}
              </div>
            </div>
          </>
        )}

        {/* ====== 구 드릴다운 뷰 ====== */}
        {selectedGu && guStats && (
          <>
            {/* 구 요약 카드 */}
            <div className="glass-card p-panel-internal rounded-lg neon-border-active">
              <div className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant uppercase tracking-widest mb-2">구역 요약</div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="text-[10px] text-slate-500 mb-0.5">평균 위험 점수</div>
                  <div className="text-headline-md font-headline-md text-primary-fixed-dim font-mono-data">{(guStats.riskSum / guStats.count).toFixed(1)}점</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 mb-0.5">고위험 격자</div>
                  <div className="text-headline-md font-headline-md text-error font-mono-data">{guStats.highRisk}개</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 mb-0.5">총 사고 건수</div>
                  <div className="text-headline-sm font-headline-sm text-slate-900 dark:text-white font-mono-data">{guStats.accidents}건</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 mb-0.5">2025년 사고</div>
                  <div className="text-headline-sm font-headline-sm text-slate-900 dark:text-white font-mono-data">{guStats.acc2025}건</div>
                </div>
              </div>
              <div className="mt-3 flex justify-between items-center">
                <span className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant">킥보드 견인 합계</span>
                <span className="text-mono-data font-mono-data text-[#ff9500] font-bold">{guStats.towing}건</span>
              </div>
              <div className="flex justify-between items-center mt-1">
                <span className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant">전체 격자 수</span>
                <span className="text-mono-data font-mono-data text-slate-900 dark:text-white">{guStats.count}개</span>
              </div>
            </div>

            {/* 위험도 분포 바 */}
            <div className="glass-card p-4 rounded-lg">
              <div className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant mb-3">격자 위험도 분포</div>
              {['very_high', 'high', 'medium', 'low', 'very_low'].map(level => {
                const levelLabel = { very_high: '매우 위험', high: '위험', medium: '주의', low: '관찰', very_low: '안전' };
                const levelColor = { very_high: 'bg-error', high: 'bg-[#C61A1A]', medium: 'bg-[#8E1212]', low: 'bg-[#540A0A]', very_low: 'bg-white/10' };
                const cnt = guFeatures.filter(p => p.risk_level === level).length;
                const pct = guStats.count > 0 ? (cnt / guStats.count * 100) : 0;
                return (
                  <div key={level} className="flex items-center gap-2 mb-1.5">
                    <span className="text-[10px] text-slate-600 dark:text-on-surface-variant w-16 shrink-0">{levelLabel[level]}</span>
                    <div className="flex-1 h-3 bg-black/10 dark:bg-white/10 rounded overflow-hidden">
                      <div className={`h-full ${levelColor[level]} rounded`} style={{ width: `${pct}%` }}></div>
                    </div>
                    <span className="text-[10px] font-mono-data text-slate-600 dark:text-on-surface-variant w-8 text-right">{cnt}</span>
                  </div>
                );
              })}
            </div>

            {/* 위험 격자 TOP 5 */}
            <div>
              <h4 className="text-body-sm font-body-sm text-slate-600 dark:text-on-surface-variant mb-2 font-semibold">위험 격자 TOP 5</h4>
              <div className="flex flex-col gap-1.5">
                {guFeatures.slice(0, 5).map((p, idx) => (
                  <div key={idx} className="glass-card p-3 rounded flex justify-between items-center">
                    <div className="flex flex-col">
                      <span className="text-body-sm text-slate-900 dark:text-white">
                        <span className="font-mono-data text-[10px] text-slate-500 mr-1">#{idx + 1}</span>
                        견인 {p.towing_cnt}건 · 상업시설 {p.poi_commercial}개
                      </span>
                      <span className="text-[10px] text-slate-500">교차로 {p.intersect_500}개 · 사고 {p.acc_total}건</span>
                    </div>
                    <span className={`text-mono-data font-bold text-sm px-2 py-0.5 rounded ${
                      p.risk_level === 'very_high' ? 'text-error' : p.risk_level === 'high' ? 'text-[#C61A1A]' : 'text-slate-600 dark:text-on-surface-variant'
                    }`}>{p.risk_pct}점</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default RiskOverviewPanel;
