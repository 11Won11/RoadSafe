import React, { useState } from 'react';

const Sidebar = () => {
  const [activeTab, setActiveTab] = useState('Overview');

  const navItems = [
    { id: 'Overview', icon: 'dashboard', label: 'Overview' },
    { id: 'Real-time', icon: 'monitoring', label: 'Real-time' },
    { id: 'Historical', icon: 'history', label: 'Historical' },
    { id: 'Predictions', icon: 'online_prediction', label: 'Predictions' },
  ];

  return (
    <aside className="fixed top-16 left-0 h-[calc(100vh-64px)] w-64 flex flex-col z-[90] bg-surface-container-lowest/40 backdrop-blur-2xl glass-effect-sidebar border-r border-black/10 dark:border-white/10 no-shadow hidden lg:flex">
      <div className="p-6 border-b border-black/5 dark:border-white/5">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-2 h-2 rounded-full bg-primary-container pulse-marker"></div>
          <h2 className="text-primary font-bold text-headline-sm font-headline-sm tracking-tight">Core Metrics</h2>
        </div>
        <p className="text-body-sm font-body-sm text-slate-600 dark:text-on-surface-variant/70">V3.4 Active</p>
      </div>
      
      <div className="flex-1 py-4 flex flex-col gap-1 overflow-y-auto">
        {navItems.map(item => (
          <button 
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className={`w-full flex items-center gap-3 px-4 py-3 transition-all text-body-md font-body-md ${
              activeTab === item.id 
                ? 'text-primary-fixed-dim bg-black/10 dark:bg-white/10 font-bold border-l-2 border-primary-fixed-dim' 
                : 'text-slate-600 dark:text-on-surface-variant hover:text-slate-900 dark:hover:text-on-surface hover:bg-black/5 dark:hover:bg-white/5 border-l-2 border-transparent'
            }`}
          >
            <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
            {item.label}
          </button>
        ))}
      </div>

      <div className="p-4 border-t border-black/5 dark:border-white/5">
        <button className="w-full bg-primary-container text-black hover:bg-primary-fixed font-semibold py-2 px-4 rounded text-body-md font-body-md transition-colors shadow-[0_0_15px_rgba(0,242,255,0.2)]">
          Export Data
        </button>
        <div className="mt-4 flex flex-col gap-1">
          <a className="text-slate-600 dark:text-on-surface-variant flex items-center gap-3 px-2 py-2 hover:text-slate-900 dark:hover:text-on-surface hover:bg-black/5 dark:bg-white/5 rounded transition-all text-body-sm font-body-sm" href="#">
            <span className="material-symbols-outlined text-[18px]">help</span>
            Support
          </a>
          <a className="text-slate-600 dark:text-on-surface-variant flex items-center gap-3 px-2 py-2 hover:text-slate-900 dark:hover:text-on-surface hover:bg-black/5 dark:bg-white/5 rounded transition-all text-body-sm font-body-sm" href="#">
            <span className="material-symbols-outlined text-[18px]">account_circle</span>
            Account
          </a>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
