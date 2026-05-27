import React from 'react';

const AnalyticsPanel = () => {
  return (
    <div className="w-[380px] h-[calc(100vh-112px)] glass-panel rounded-xl flex flex-col pointer-events-auto transform transition-all hover:-translate-y-1 hover:shadow-lg">
      <div className="p-panel-internal border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
        <h3 className="text-headline-sm font-headline-sm font-semibold text-white tracking-tight">Analytics & Insights</h3>
        <span className="material-symbols-outlined text-primary-container text-[20px]">auto_awesome</span>
      </div>
      
      <div className="p-panel-internal flex-1 overflow-y-auto flex flex-col gap-card-gap">
        {/* Model Performance */}
        <div className="glass-card p-panel-internal rounded-lg">
          <div className="flex justify-between items-end mb-4">
            <div>
              <div className="text-label-md font-label-md text-on-surface-variant uppercase tracking-widest mb-1">XGB-Ensemble V3</div>
              <div className="text-headline-sm font-headline-sm text-white">
                AUROC <span className="text-primary-fixed-dim ml-1">0.8024</span>
              </div>
            </div>
            <div className="text-xs text-on-surface-variant bg-black/30 px-2 py-1 rounded border border-white/5">
              Acc: 92.4%
            </div>
          </div>
          
          {/* Mini Chart Placeholder (CSS Only) */}
          <div className="h-16 flex items-end gap-1 opacity-80">
            <div className="w-full bg-white/5 rounded-t h-[30%] hover:bg-primary-container/30 transition-colors"></div>
            <div className="w-full bg-white/5 rounded-t h-[50%] hover:bg-primary-container/30 transition-colors"></div>
            <div className="w-full bg-white/5 rounded-t h-[40%] hover:bg-primary-container/30 transition-colors"></div>
            <div className="w-full bg-primary-container/40 border-t-2 border-primary-container rounded-t h-[80%] relative group">
              <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-[10px] bg-black px-1 rounded hidden group-hover:block">Peak</div>
            </div>
            <div className="w-full bg-white/5 rounded-t h-[60%] hover:bg-primary-container/30 transition-colors"></div>
            <div className="w-full bg-white/5 rounded-t h-[75%] hover:bg-primary-container/30 transition-colors"></div>
          </div>
        </div>

        {/* Key Insights (Bento Grid Style) */}
        <h4 className="text-body-sm font-body-sm text-on-surface-variant mt-2 font-semibold tracking-wide">SHAP FEATURE IMPORTANCE</h4>
        <div className="grid gap-2">
          {/* Insight 1 */}
          <div className="glass-card p-3 rounded flex flex-col gap-2 relative overflow-hidden group">
            <div className="absolute left-0 top-0 bottom-0 w-1 bg-error"></div>
            <div className="flex justify-between items-center pl-2">
              <span className="text-body-sm font-body-sm text-white font-medium">Intersection Density</span>
              <span className="text-mono-data font-mono-data text-on-surface-variant text-xs">+0.42</span>
            </div>
            <div className="w-full h-1.5 bg-black/50 rounded-full ml-2 overflow-hidden">
              <div className="h-full bg-error w-[85%] rounded-full"></div>
            </div>
          </div>
          
          {/* Insight 2 */}
          <div className="glass-card p-3 rounded flex flex-col gap-2 relative overflow-hidden">
            <div className="absolute left-0 top-0 bottom-0 w-1 bg-[#ffcc00]"></div>
            <div className="flex justify-between items-center pl-2">
              <span className="text-body-sm font-body-sm text-white font-medium">Topography (Slope)</span>
              <span className="text-mono-data font-mono-data text-on-surface-variant text-xs">+0.31</span>
            </div>
            <div className="w-full h-1.5 bg-black/50 rounded-full ml-2 overflow-hidden">
              <div className="h-full bg-[#ffcc00] w-[70%] rounded-full"></div>
            </div>
          </div>

          {/* Insight 3 */}
          <div className="glass-card p-3 rounded flex flex-col gap-2 relative overflow-hidden">
            <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary-container"></div>
            <div className="flex justify-between items-center pl-2">
              <span className="text-body-sm font-body-sm text-white font-medium">CCTV Coverage Impact</span>
              <span className="text-mono-data font-mono-data text-on-surface-variant text-xs">-0.28</span>
            </div>
            <div className="w-full h-1.5 bg-black/50 rounded-full ml-2 overflow-hidden">
              <div className="h-full bg-primary-container w-[60%] rounded-full"></div>
            </div>
          </div>
        </div>

        <div className="mt-auto pt-4">
          <button className="w-full py-3 bg-transparent border border-white/20 text-white rounded hover:bg-white/5 transition-all text-body-sm font-body-sm flex justify-center items-center gap-2">
            <span className="material-symbols-outlined text-[16px]">tune</span>
            Adjust Parameters
          </button>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsPanel;
