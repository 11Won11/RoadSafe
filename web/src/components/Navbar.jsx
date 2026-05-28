import React from 'react';

const Navbar = ({ isDarkMode, toggleTheme, searchQuery, setSearchQuery, selectedGu, onGuClear }) => {
  return (
    <nav className="fixed top-0 left-0 w-full z-[100] flex justify-between items-center px-container-padding h-16 bg-white/60 dark:bg-surface/60 backdrop-blur-xl backdrop-filter border-b border-black/5 dark:border-white/5 shadow-sm">
      <div className="flex items-center gap-6">
        <div className="text-headline-md font-headline-md font-bold text-primary tracking-tighter">
          🛴 SAFERIDE
        </div>

        {/* 선택된 구 breadcrumb */}
        {selectedGu && (
          <div className="hidden md:flex items-center gap-2 ml-4 text-body-sm">
            <span className="text-slate-500 dark:text-on-surface-variant">서울시</span>
            <span className="material-symbols-outlined text-[14px] text-slate-400">chevron_right</span>
            <span className="text-primary-fixed-dim font-semibold">{selectedGu}</span>
            <button onClick={onGuClear} className="ml-1 text-slate-400 hover:text-error transition-colors">
              <span className="material-symbols-outlined text-[16px]">close</span>
            </button>
          </div>
        )}
        
        <div className="hidden md:flex gap-6 ml-8">
          <a href="#" className="text-primary border-b-2 border-primary-fixed-dim pb-1 font-bold text-label-md font-label-md uppercase tracking-wider py-5 relative">
            위험도 지도
            <div className="absolute bottom-0 left-0 w-full h-[1px] bg-primary-container shadow-[0_0_8px_rgba(0,242,255,0.6)]"></div>
          </a>
          <a href="#" className="text-slate-600 dark:text-on-surface-variant hover:text-slate-900 dark:hover:text-on-surface transition-colors duration-200 text-label-md font-label-md uppercase tracking-wider py-5">
            예측 분석
          </a>
          <a href="#" className="text-slate-600 dark:text-on-surface-variant hover:text-slate-900 dark:hover:text-on-surface transition-colors duration-200 text-label-md font-label-md uppercase tracking-wider py-5">
            통계
          </a>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative hidden sm:block">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-600 dark:text-on-surface-variant text-sm">search</span>
          <input 
            type="text" 
            placeholder="구 이름 검색 (예: 강남구)" 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-slate-200 dark:bg-black/20 border-b border-black/10 dark:border-white/10 focus:border-primary-fixed-dim focus:ring-0 text-body-sm font-body-sm text-slate-900 dark:text-on-surface px-9 py-2 rounded-t w-64 transition-colors placeholder:text-slate-600 dark:placeholder:text-on-surface-variant/50 focus:shadow-[0_1px_0_rgba(0,242,255,1)]"
          />
        </div>
        
        <button onClick={toggleTheme} className="text-slate-600 dark:text-on-surface-variant hover:text-slate-900 dark:hover:text-on-surface hover:bg-black/5 dark:hover:bg-black/5 dark:bg-white/5 p-2 rounded-full transition-all duration-300" title="테마 전환">
          <span className="material-symbols-outlined text-[20px]">
            {isDarkMode ? 'light_mode' : 'dark_mode'}
          </span>
        </button>
        
        <button className="text-slate-600 dark:text-on-surface-variant hover:text-slate-900 dark:hover:text-on-surface hover:bg-black/5 dark:hover:bg-black/5 dark:bg-white/5 p-2 rounded-full transition-all duration-300">
          <span className="material-symbols-outlined text-[20px]">settings</span>
        </button>
      </div>
    </nav>
  );
};

export default Navbar;
