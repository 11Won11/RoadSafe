import React from 'react';

const Sidebar = () => {
  return (
    <aside className="fixed top-16 left-0 h-[calc(100vh-64px)] w-64 flex flex-col z-[90] bg-surface-container-lowest/40 backdrop-blur-2xl glass-effect-sidebar border-r border-white/10 no-shadow hidden lg:flex">
      <div className="p-6 border-b border-white/5">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-2 h-2 rounded-full bg-primary-container pulse-marker"></div>
          <h2 className="text-primary font-bold text-headline-sm font-headline-sm tracking-tight">Core Metrics</h2>
        </div>
        <p className="text-body-sm font-body-sm text-on-surface-variant/70">V3.4 Active</p>
      </div>
      
      <div className="flex-1 py-4 flex flex-col gap-1 overflow-y-auto">
        <a className="text-on-surface-variant flex items-center gap-3 px-4 py-3 hover:text-on-surface hover:bg-white/5 transition-all text-body-md font-body-md" href="#">
          <span className="material-symbols-outlined text-[20px]">dashboard</span>
          Dashboard
        </a>
        <a className="text-on-surface-variant flex items-center gap-3 px-4 py-3 hover:text-on-surface hover:bg-white/5 transition-all text-body-md font-body-md" href="#">
          <span className="material-symbols-outlined text-[20px]">query_stats</span>
          Analytics
        </a>
        <a className="bg-primary-container/20 text-primary-fixed-dim border-r-2 border-primary-fixed-dim flex items-center gap-3 px-4 py-3 text-body-md font-body-md relative overflow-hidden group" href="#">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent to-primary-container/10 translate-x-[-100%] group-hover:translate-x-0 transition-transform duration-500"></div>
          <span className="material-symbols-outlined text-[20px]" style={{fontVariationSettings: "'FILL' 1"}}>map</span>
          Risk Map
        </a>
        <a className="text-on-surface-variant flex items-center gap-3 px-4 py-3 hover:text-on-surface hover:bg-white/5 transition-all text-body-md font-body-md" href="#">
          <span className="material-symbols-outlined text-[20px]">insights</span>
          Model Insights
        </a>
        <a className="text-on-surface-variant flex items-center gap-3 px-4 py-3 hover:text-on-surface hover:bg-white/5 transition-all text-body-md font-body-md" href="#">
          <span className="material-symbols-outlined text-[20px]">description</span>
          Reports
        </a>
      </div>

      <div className="p-4 border-t border-white/5">
        <button className="w-full bg-primary-container text-black hover:bg-primary-fixed font-semibold py-2 px-4 rounded text-body-md font-body-md transition-colors shadow-[0_0_15px_rgba(0,242,255,0.2)]">
          Export Data
        </button>
        <div className="mt-4 flex flex-col gap-1">
          <a className="text-on-surface-variant flex items-center gap-3 px-2 py-2 hover:text-on-surface hover:bg-white/5 rounded transition-all text-body-sm font-body-sm" href="#">
            <span className="material-symbols-outlined text-[18px]">help</span>
            Support
          </a>
          <a className="text-on-surface-variant flex items-center gap-3 px-2 py-2 hover:text-on-surface hover:bg-white/5 rounded transition-all text-body-sm font-body-sm" href="#">
            <span className="material-symbols-outlined text-[18px]">account_circle</span>
            Account
          </a>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
