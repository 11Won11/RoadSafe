import React, { useMemo } from 'react';

const AnalyticsPanel = ({ metrics, shapData, geoData, selectedGu }) => {
  const topFeatures = shapData ? shapData.slice(0, 5) : [];
  const paiTable = metrics?.pai_table_2025 || [];

  // 선택된 구의 격자 통계
  const guGrids = useMemo(() => {
    if (!geoData || !selectedGu) return [];
    return geoData.features
      .map(f => f.properties)
      .filter(p => p.gu_name === selectedGu);
  }, [geoData, selectedGu]);

  // 구 선택 시 SHAP 변수별 평균값 계산 (서울 전체 대비 비교)
  const guAvgStats = useMemo(() => {
    if (!guGrids.length) return null;
    const fields = ['towing_cnt', 'poi_commercial', 'intersect_500', 'signal_total', 'crosswalk_cnt', 'cctv_total'];
    const labels = { towing_cnt: '킥보드 견인', poi_commercial: '상업시설', intersect_500: '교차로(500m)', signal_total: '신호등', crosswalk_cnt: '횡단보도', cctv_total: 'CCTV' };
    const result = {};
    fields.forEach(f => {
      result[f] = { label: labels[f], avg: 0 };
      result[f].avg = guGrids.reduce((s, p) => s + (p[f] || 0), 0) / guGrids.length;
    });
    return result;
  }, [guGrids]);

  const seoulAvgStats = useMemo(() => {
    if (!geoData) return null;
    const fields = ['towing_cnt', 'poi_commercial', 'intersect_500', 'signal_total', 'crosswalk_cnt', 'cctv_total'];
    const result = {};
    const features = geoData.features.map(f => f.properties);
    fields.forEach(f => {
      result[f] = features.reduce((s, p) => s + (p[f] || 0), 0) / features.length;
    });
    return result;
  }, [geoData]);

  return (
    <div className="w-[380px] h-[calc(100vh-112px)] glass-panel rounded-xl flex flex-col pointer-events-auto transform transition-all hover:-translate-y-1 hover:shadow-lg">
      <div className="p-panel-internal border-b border-black/5 dark:border-white/5 flex justify-between items-center bg-white/[0.02]">
        <h3 className="text-headline-sm font-headline-sm font-semibold text-slate-900 dark:text-white tracking-tight">
          {selectedGu ? `${selectedGu} 분석` : '분석 & 인사이트'}
        </h3>
        <span className="material-symbols-outlined text-primary-container text-[20px]">auto_awesome</span>
      </div>

      <div className="p-panel-internal flex-1 overflow-y-auto flex flex-col gap-card-gap">

        {/* ====== 전체 뷰 ====== */}
        {!selectedGu && (
          <>
            {/* 모델 성능 카드 */}
            <div className="glass-card p-panel-internal rounded-lg">
              <div className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant uppercase tracking-widest mb-1">XGBoost 포아송 회귀 모델</div>
              <div className="text-headline-sm font-headline-sm text-slate-900 dark:text-white">
                AUROC <span className="text-primary-fixed-dim ml-1">{metrics ? metrics.auroc_all.toFixed(4) : '...'}</span>
              </div>
              <div className="text-body-sm text-slate-600 dark:text-on-surface-variant mt-1">
                2025 홀드아웃: <span className="text-[#4ade80] font-mono-data">{metrics ? metrics.auroc_2025.toFixed(4) : '...'}</span>
                &nbsp;|&nbsp;부산 전이: <span className="text-[#4ade80] font-mono-data">{metrics ? metrics.auroc_busan : '...'}</span>
              </div>

              {/* PAI 포착률 바 차트 */}
              {paiTable.length > 0 && (
                <div className="mt-3">
                  <div className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant mb-2">정책 포착률 (PAI) — 상위 k% 단속 시</div>
                  <div className="flex flex-col gap-1.5">
                    {paiTable.map(row => (
                      <div key={row.k} className="flex items-center gap-2">
                        <span className="text-[11px] text-slate-600 dark:text-on-surface-variant w-8 text-right shrink-0">k={row.k}%</span>
                        <div className="flex-1 h-4 bg-black/10 dark:bg-white/10 rounded overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-primary-container to-primary-fixed-dim rounded flex items-center justify-end pr-1 transition-all duration-700"
                            style={{ width: `${row.capture}%` }}
                          ></div>
                        </div>
                        <span className="text-[11px] font-mono-data text-primary-fixed-dim w-12 shrink-0">{row.capture}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* SHAP Feature Importance */}
            <h4 className="text-body-sm font-body-sm text-slate-600 dark:text-on-surface-variant mt-2 font-semibold tracking-wide">SHAP 피처 중요도 (Top 5)</h4>
            <div className="grid gap-2">
              {topFeatures.length > 0 ? topFeatures.map((feat, idx) => {
                const colors = ['bg-error', 'bg-[#ff9500]', 'bg-[#ffcc00]', 'bg-primary-container', 'bg-[#4ade80]'];
                const color = colors[idx % colors.length];
                const pct = Math.min(100, Math.max(10, (feat.value / topFeatures[0].value) * 100));
                const medals = ['🥇', '🥈', '🥉', '4위', '5위'];
                return (
                  <div key={feat.feature} className="glass-card p-3 rounded flex flex-col gap-2 relative overflow-hidden">
                    <div className={`absolute left-0 top-0 bottom-0 w-1 ${color}`}></div>
                    <div className="flex justify-between items-center pl-2">
                      <span className="text-body-sm font-body-sm text-slate-900 dark:text-white font-medium">
                        <span className="mr-1">{medals[idx]}</span>{feat.label}
                      </span>
                      <span className="text-mono-data font-mono-data text-slate-600 dark:text-on-surface-variant text-xs">{feat.value.toFixed(4)}</span>
                    </div>
                    <div className="w-full h-1.5 bg-black/10 dark:bg-black/50 rounded-full ml-2 overflow-hidden">
                      <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }}></div>
                    </div>
                  </div>
                );
              }) : (
                <div className="text-center text-slate-500 py-4 text-sm">데이터 로딩 중...</div>
              )}
            </div>

            {/* 핵심 인사이트 */}
            <div className="glass-card p-4 rounded-lg mt-1">
              <div className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant mb-2 flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px] text-primary-container">lightbulb</span>
                핵심 인사이트
              </div>
              <ul className="flex flex-col gap-2 text-body-sm font-body-sm text-slate-900 dark:text-white/80">
                <li className="flex gap-2"><span className="text-error shrink-0">•</span>상업시설 밀집 지역 → PM 사고 위험 1위</li>
                <li className="flex gap-2"><span className="text-[#ff9500] shrink-0">•</span>킥보드 무단 방치 구역 = 사고 위험 2위</li>
                <li className="flex gap-2"><span className="text-[#4ade80] shrink-0">•</span>상위 50% 집중 관리 시 92.3% 사고 예방</li>
              </ul>
            </div>
          </>
        )}

        {/* ====== 구 드릴다운 뷰 ====== */}
        {selectedGu && guAvgStats && seoulAvgStats && (
          <>
            <div className="glass-card p-4 rounded-lg">
              <div className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant mb-3 flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px] text-primary-container">compare_arrows</span>
                {selectedGu} vs 서울 전체 평균 비교
              </div>
              <div className="flex flex-col gap-3">
                {Object.entries(guAvgStats).map(([field, { label, avg }]) => {
                  const seoulAvg = seoulAvgStats[field] || 0;
                  const maxVal = Math.max(avg, seoulAvg) * 1.2 || 1;
                  const guPct = Math.min(100, (avg / maxVal) * 100);
                  const seoulPct = Math.min(100, (seoulAvg / maxVal) * 100);
                  const isHigher = avg > seoulAvg;
                  return (
                    <div key={field}>
                      <div className="flex justify-between mb-1">
                        <span className="text-body-sm font-body-sm text-slate-900 dark:text-white">{label}</span>
                        <span className={`text-[11px] font-mono-data ${isHigher ? 'text-error' : 'text-[#4ade80]'}`}>
                          {isHigher ? '▲' : '▼'} {avg > 0 ? avg.toFixed(1) : '0'}
                        </span>
                      </div>
                      <div className="flex flex-col gap-0.5">
                        <div className="flex items-center gap-2">
                          <span className="text-[9px] text-primary-fixed-dim w-8 shrink-0">{selectedGu.replace('구','')}</span>
                          <div className="flex-1 h-2.5 bg-black/10 dark:bg-white/10 rounded overflow-hidden">
                            <div className="h-full bg-primary-fixed-dim rounded" style={{ width: `${guPct}%` }}></div>
                          </div>
                          <span className="text-[9px] font-mono-data text-primary-fixed-dim w-6">{avg.toFixed(0)}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-[9px] text-slate-500 w-8 shrink-0">서울</span>
                          <div className="flex-1 h-2.5 bg-black/10 dark:bg-white/10 rounded overflow-hidden">
                            <div className="h-full bg-slate-400/50 rounded" style={{ width: `${seoulPct}%` }}></div>
                          </div>
                          <span className="text-[9px] font-mono-data text-slate-500 w-6">{seoulAvg.toFixed(0)}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 구별 위험 요인 요약 */}
            <div className="glass-card p-4 rounded-lg">
              <div className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant mb-2 flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px] text-error">warning</span>
                {selectedGu} 주요 위험 요인
              </div>
              {guGrids.length > 0 && (() => {
                const avgTowing = guGrids.reduce((s, p) => s + p.towing_cnt, 0) / guGrids.length;
                const avgComm = guGrids.reduce((s, p) => s + p.poi_commercial, 0) / guGrids.length;
                const highRiskPct = (guGrids.filter(p => p.risk_level === 'very_high' || p.risk_level === 'high').length / guGrids.length * 100);
                return (
                  <ul className="flex flex-col gap-2 text-body-sm font-body-sm text-slate-900 dark:text-white/80">
                    <li className="flex gap-2">
                      <span className="text-[#ff9500] shrink-0">•</span>
                      격자당 평균 견인 <span className="text-[#ff9500] font-mono-data font-bold mx-1">{avgTowing.toFixed(1)}건</span>
                      {avgTowing > seoulAvgStats['towing_cnt'] ? '(서울 평균 초과 🔺)' : '(서울 평균 이하)'}
                    </li>
                    <li className="flex gap-2">
                      <span className="text-error shrink-0">•</span>
                      격자당 평균 상업시설 <span className="text-error font-mono-data font-bold mx-1">{avgComm.toFixed(1)}개</span>
                    </li>
                    <li className="flex gap-2">
                      <span className="text-[#ffcc00] shrink-0">•</span>
                      고위험 격자 비율 <span className="text-[#ffcc00] font-mono-data font-bold mx-1">{highRiskPct.toFixed(1)}%</span>
                    </li>
                  </ul>
                );
              })()}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default AnalyticsPanel;
