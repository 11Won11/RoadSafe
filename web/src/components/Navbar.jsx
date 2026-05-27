import React from 'react';

const Navbar = () => {
  return (
    <nav className="fixed top-0 left-0 w-full z-[100] flex justify-between items-center px-container-padding h-16 bg-surface/60 backdrop-blur-xl backdrop-filter border-b border-white/5 shadow-sm">
      <div className="flex items-center gap-6">
        <div className="text-headline-md font-headline-md font-bold text-primary tracking-tighter">MobilityFlow AI</div>
        
        <div className="hidden md:flex gap-6 ml-8">
          <a href="#" className="text-on-surface-variant hover:text-on-surface transition-colors duration-200 text-label-md font-label-md uppercase tracking-wider py-5">
            Network
          </a>
          <a href="#" className="text-on-surface-variant hover:text-on-surface transition-colors duration-200 text-label-md font-label-md uppercase tracking-wider py-5">
            Predictive
          </a>
          <a href="#" className="text-primary border-b-2 border-primary-fixed-dim pb-1 font-bold text-label-md font-label-md uppercase tracking-wider py-5 relative">
            Regional
            <div className="absolute bottom-0 left-0 w-full h-[1px] bg-primary-container shadow-[0_0_8px_rgba(0,242,255,0.6)]"></div>
          </a>
          <a href="#" className="text-on-surface-variant hover:text-on-surface transition-colors duration-200 text-label-md font-label-md uppercase tracking-wider py-5">
            Heatmap
          </a>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative hidden sm:block">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-sm">search</span>
          <input 
            type="text" 
            placeholder="Search region or ID..." 
            className="bg-black/20 border-b border-white/10 focus:border-primary-fixed-dim focus:ring-0 text-body-sm font-body-sm text-on-surface px-9 py-2 rounded-t w-64 transition-colors placeholder:text-on-surface-variant/50 focus:shadow-[0_1px_0_rgba(0,242,255,1)]"
          />
        </div>
        
        <button className="text-on-surface-variant hover:text-on-surface hover:bg-white/5 p-2 rounded-full transition-all duration-300">
          <span className="material-symbols-outlined text-[20px]">settings</span>
        </button>
        
        <button className="text-on-surface-variant hover:text-on-surface hover:bg-white/5 p-2 rounded-full transition-all duration-300 relative">
          <span className="material-symbols-outlined text-[20px]">notifications</span>
          <span className="absolute top-2 right-2 w-2 h-2 bg-primary-container rounded-full shadow-[0_0_4px_rgba(0,242,255,0.8)]"></span>
        </button>
        
        <div className="w-8 h-8 rounded-full bg-surface-container-high border border-white/10 overflow-hidden ml-2 cursor-pointer hover:border-primary-fixed-dim transition-colors">
          <img 
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuB3R2i6UaoyCEwiqTEh-BPLlCsmXklmt2vHZZ97iWCQpdu85aDXTQ6Mf8H4Aab3J3GZrnTI-Y26zZIkaeOB0181Fw8glYueB0rimS3elLnT4GQBG-oIPMrgad6r4pMJdCEvLaK24EjUfF9wnUgCg0HicRbxSE2Xj2KFn_wAfTppiO-YghmA-75wqZ53XLBskTrqTfKLhTP4yc3Z3o25pl5anT_UqoJruk62he-pmqbND62wxBmyF6OsAP9jvV5eQ6j9Z3ga_GMJXLN5" 
            alt="Analyst Profile" 
            className="w-full h-full object-cover"
          />
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
