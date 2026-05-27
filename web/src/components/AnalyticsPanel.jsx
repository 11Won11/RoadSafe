import React from 'react';

const AnalyticsPanel = ({ metrics, shapData }) => {
  const topFeatures = shapData ? shapData.slice(0, 3) : [];
  return (
    <div className="w-[380px] h-[calc(100vh-112px)] glass-panel rounded-xl flex flex-col pointer-events-auto transform transition-all hover:-translate-y-1 hover:shadow-lg">
      <div className="p-panel-internal border-b border-black/5 dark:border-white/5 flex justify-between items-center bg-white/[0.02]">
        <h3 className="text-headline-sm font-headline-sm font-semibold text-slate-900 dark:text-white tracking-tight">Analytics & Insights</h3>
        <span className="material-symbols-outlined text-primary-container text-[20px]">auto_awesome</span>
      </div>
      
      <div className="p-panel-internal flex-1 overflow-y-auto flex flex-col gap-card-gap">
        {/* Model Performance */}
        <div className="glass-card p-panel-internal rounded-lg">
          <div className="flex justify-between items-end mb-4">
            <div>
              <div className="text-label-md font-label-md text-slate-600 dark:text-on-surface-variant uppercase tracking-widest mb-1">XGB-Ensemble V3</div>
              <div className="text-headline-sm font-headline-sm text-slate-900 dark:text-white">
                AUROC <span className="text-primary-fixed-dim ml-1">{metrics ? metrics.auroc_all : '...'}</span>
              </div>
            </div>
            <div className="text-xs text-slate-600 dark:text-on-surface-variant bg-slate-300 dark:bg-black/30 px-2 py-1 rounded border border-black/5 dark:border-white/5">
              Acc: {metrics ? (metrics.auroc_2025 * 100).toFixed(1) : '...'}%
            </div>
          </div>
          
          {/* Mini Chart Placeholder (CSS Only) */}
          <div className="h-16 flex items-end gap-1 opacity-80">
            <div className="w-full bg-black/5 dark:bg-white/5 rounded-t h-[30%] hover:bg-primary-container/30 transition-colors"></div>
            <div className="w-full bg-black/5 dark:bg-white/5 rounded-t h-[50%] hover:bg-primary-container/30 transition-colors"></div>
            <div className="w-full bg-black/5 dark:bg-white/5 rounded-t h-[40%] hover:bg-primary-container/30 transition-colors"></div>
            <div className="w-full bg-primary-container/40 border-t-2 border-primary-container rounded-t h-[80%] relative group">
              <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-[10px] bg-black px-1 rounded hidden group-hover:block">Peak</div>
            </div>
            <div className="w-full bg-black/5 dark:bg-white/5 rounded-t h-[60%] hover:bg-primary-container/30 transition-colors"></div>
            <div className="w-full bg-black/5 dark:bg-white/5 rounded-t h-[75%] hover:bg-primary-container/30 transition-colors"></div>
          </div>
        </div>

        {/* Key Insights (Bento Grid Style) */}
        <h4 className="text-body-sm font-body-sm text-slate-600 dark:text-on-surface-variant mt-2 font-semibold tracking-wide">SHAP FEATURE IMPORTANCE</h4>
        <div className="grid gap-2">
          {topFeatures.length > 0 ? topFeatures.map((feat, idx) => {
            const colors = ['bg-error', 'bg-[#ffcc00]', 'bg-primary-container'];
            const color = colors[idx % colors.length];
            // Compute percentage relative to first feature
            const pct = Math.min(100, Math.max(10, (feat.value / topFeatures[0].value) * 100));
            return (
              <div key={feat.feature} className="glass-card p-3 rounded flex flex-col gap-2 relative overflow-hidden group">
                <div className={`absolute left-0 top-0 bottom-0 w-1 ${color}`}></div>
                <div className="flex justify-between items-center pl-2">
                  <span className="text-body-sm font-body-sm text-slate-900 dark:text-white font-medium">{feat.label}</span>
                  <span className="text-mono-data font-mono-data text-slate-600 dark:text-on-surface-variant text-xs">+{feat.value.toFixed(4)}</span>
                </div>
                <div className="w-full h-1.5 bg-black/10 dark:bg-black/50 rounded-full ml-2 overflow-hidden">
                  <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }}></div>
                </div>
              </div>
            );
          }) : (
            <div className="text-center text-slate-500 py-4 text-sm">Loading insights...</div>
          )}
        </div>

        <div className="mt-auto pt-4">
          <button className="w-full py-3 bg-transparent border border-black/20 dark:border-white/20 text-slate-900 dark:text-white rounded hover:bg-black/5 dark:bg-white/5 transition-all text-body-sm font-body-sm flex justify-center items-center gap-2">
            <span className="material-symbols-outlined text-[16px]">tune</span>
            Adjust Parameters
          </button>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsPanel;
