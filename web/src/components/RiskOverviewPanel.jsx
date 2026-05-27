import React from 'react';

const RiskOverviewPanel = ({ totalRisk, totalIncidents, fatalityRate, topDistricts }) => {
  return (
    <div className="w-[340px] h-[calc(100vh-112px)] glass-panel rounded-xl flex flex-col pointer-events-auto transform transition-all hover:-translate-y-1 hover:shadow-lg">
      <div className="p-panel-internal border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
        <h3 className="text-headline-sm font-headline-sm font-semibold text-white tracking-tight">Risk Overview</h3>
        <span className="material-symbols-outlined text-on-surface-variant text-[20px]">filter_list</span>
      </div>
      
      <div className="p-panel-internal flex-1 overflow-y-auto flex flex-col gap-card-gap">
        {/* Total Risk Score */}
        <div className="glass-card p-panel-internal rounded-lg neon-border-active">
          <div className="text-label-md font-label-md text-on-surface-variant uppercase tracking-widest mb-1">Seoul Metro Area</div>
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-display-lg font-display-lg text-primary-fixed-dim">{totalRisk || '94.2'}</span>
            <span className="text-body-sm font-body-sm text-error flex items-center">
              <span className="material-symbols-outlined text-[14px]">trending_up</span> 2.4%
            </span>
          </div>
          <div className="w-full h-1 bg-white/10 rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-primary-fixed-dim to-error w-[84%]"></div>
          </div>
        </div>

        {/* Annual Stats */}
        <div className="grid grid-cols-2 gap-card-gap">
          <div className="glass-card p-4 rounded-lg">
            <div className="text-label-md font-label-md text-on-surface-variant mb-1">Total Incidents</div>
            <div className="text-headline-md font-headline-md text-white font-mono-data">{totalIncidents || '2,132'}</div>
          </div>
          <div className="glass-card p-4 rounded-lg">
            <div className="text-label-md font-label-md text-on-surface-variant mb-1">Fatalities/Severe</div>
            <div className="text-headline-md font-headline-md text-error font-mono-data">{fatalityRate || '84'}<span className="text-body-sm">%</span></div>
          </div>
        </div>

        {/* Top Risk Districts */}
        <div className="mt-2">
          <h4 className="text-body-sm font-body-sm text-on-surface-variant mb-3 font-semibold tracking-wide">TOP RISK DISTRICTS</h4>
          <div className="flex flex-col gap-2">
            {/* District 1 (High) */}
            <div className="flex items-center justify-between glass-card px-3 py-2 rounded">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-error border border-error-container"></div>
                <span className="text-body-md font-body-md text-white">Gangnam-gu</span>
              </div>
              <span className="text-mono-data font-mono-data text-error bg-error-container/20 px-2 py-0.5 rounded text-xs border border-error/20">Critical</span>
            </div>
            
            {/* District 2 (Medium) */}
            <div className="flex items-center justify-between glass-card px-3 py-2 rounded">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-[#ffcc00] border border-[#ffcc00]/30"></div>
                <span className="text-body-md font-body-md text-white">Mapo-gu</span>
              </div>
              <span className="text-mono-data font-mono-data text-[#ffcc00] bg-[#ffcc00]/10 px-2 py-0.5 rounded text-xs border border-[#ffcc00]/20">Elevated</span>
            </div>
            
            {/* District 3 (Low) */}
            <div className="flex items-center justify-between glass-card px-3 py-2 rounded">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-primary-container border border-primary-container/30"></div>
                <span className="text-body-md font-body-md text-white">Seocho-gu</span>
              </div>
              <span className="text-mono-data font-mono-data text-primary-container bg-primary-container/10 px-2 py-0.5 rounded text-xs border border-primary-container/20">Monitor</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RiskOverviewPanel;
