import React, { useMemo } from 'react';

const RiskOverviewPanel = ({ metrics, geoData }) => {
  const topDistricts = useMemo(() => {
    if (!geoData || !geoData.features) return [];
    
    // Group by district (SIG_KOR_NM) and accumulate risk_score
    const districtStats = {};
    geoData.features.forEach(f => {
      const p = f.properties;
      const district = p.SIG_KOR_NM || 'Unknown';
      if (!districtStats[district]) {
        districtStats[district] = { sum: 0, count: 0 };
      }
      districtStats[district].sum += (p.risk_score || 0);
      districtStats[district].count += 1;
    });

    // Calculate average and sort
    const ranked = Object.keys(districtStats).map(district => {
      const avg = districtStats[district].sum / districtStats[district].count;
      return { district, avgRisk: avg };
    });
    
    ranked.sort((a, b) => b.avgRisk - a.avgRisk);
    return ranked.slice(0, 5);
  }, [geoData]);

  const totalIncidents = metrics?.accident_count || '-';
  const totalRiskGrids = metrics?.high_risk_grids || '-';
  const fatalityRate = '1.2%'; // Static mockup or could be from metrics
  // calculate total average risk from geoData
  const totalRisk = useMemo(() => {
    if (!geoData || !geoData.features) return '0.0';
    let sum = 0;
    geoData.features.forEach(f => sum += (f.properties.risk_score || 0));
    return (sum / geoData.features.length).toFixed(1);
  }, [geoData]);

  return (
    <div className="w-[340px] h-[calc(100vh-112px)] glass-panel rounded-xl flex flex-col pointer-events-auto transform transition-all hover:-translate-y-1 hover:shadow-lg">
      <div className="p-panel-internal border-b border-black/5 dark:border-white/5 flex justify-between items-center bg-white/[0.02]">
        <h3 className="text-headline-sm font-headline-sm font-semibold text-slate-900 dark:text-white tracking-tight">Risk Overview</h3>
        <span className="material-symbols-outlined text-slate-600 dark:text-on-surface-variant text-[20px]">filter_list</span>
      </div>
      
      <div className="p-panel-internal flex-1 overflow-y-auto flex flex-col gap-card-gap">
        {/* Total Risk Score */}
        <div className="glass-card p-panel-internal rounded-lg neon-border-active">
          <div className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant uppercase tracking-widest mb-1">Seoul Metro Area</div>
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-display-lg font-display-lg text-primary-fixed-dim">{totalRisk}</span>
            <span className="text-body-sm font-body-sm text-error flex items-center">
              <span className="material-symbols-outlined text-[14px]">trending_up</span> Avg Risk
            </span>
          </div>
          <div className="w-full h-1 bg-black/10 dark:bg-white/10 rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-primary-fixed-dim to-error" style={{ width: `${Math.min(100, parseFloat(totalRisk))}%` }}></div>
          </div>
        </div>

        {/* Annual Stats */}
        <div className="grid grid-cols-2 gap-card-gap">
          <div className="glass-card p-4 rounded-lg">
            <div className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant mb-1">Total Incidents</div>
            <div className="text-headline-md font-headline-md text-slate-900 dark:text-white font-mono-data">{totalIncidents}</div>
          </div>
          <div className="glass-card p-4 rounded-lg">
            <div className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant mb-1">High Risk Grids</div>
            <div className="text-headline-md font-headline-md text-error font-mono-data">{totalRiskGrids}</div>
          </div>
        </div>

        {/* Top Risk Districts */}
        <div className="mt-2">
          <h4 className="text-body-sm font-body-sm text-slate-600 dark:text-on-surface-variant mb-3 font-semibold tracking-wide">TOP RISK DISTRICTS (AVG SCORE)</h4>
          <div className="flex flex-col gap-2">
            {topDistricts.length > 0 ? (
              topDistricts.map((item, index) => (
                <div key={item.district} className="flex items-center gap-3 p-2 hover:bg-black/5 dark:hover:bg-white/5 rounded transition-colors">
                  <div className={`w-6 h-6 rounded flex items-center justify-center text-label-md font-label-md font-bold ${
                    index === 0 ? 'bg-error text-white shadow-[0_0_8px_rgba(255,59,48,0.4)]' : 
                    index === 1 ? 'bg-[#ff9500] text-white shadow-[0_0_8px_rgba(255,149,0,0.4)]' : 
                    index === 2 ? 'bg-[#ffcc00] text-slate-900 shadow-[0_0_8px_rgba(255,204,0,0.4)]' : 'bg-black/10 dark:bg-white/10 text-slate-600 dark:text-on-surface-variant'
                  }`}>
                    {index + 1}
                  </div>
                  <span className="text-body-md font-body-md text-slate-900 dark:text-white flex-1">{item.district}</span>
                  <span className="text-mono-data font-mono-data text-slate-600 dark:text-on-surface-variant text-sm">
                    {item.avgRisk.toFixed(1)}
                  </span>
                </div>
              ))
            ) : (
              <div className="text-center text-slate-500 py-4 text-sm">Loading district data...</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RiskOverviewPanel;
