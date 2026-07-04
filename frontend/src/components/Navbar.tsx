export function Navbar() {
  return (
    <header className="sticky top-0 z-40 bg-slate-950/80 backdrop-blur-md border-b border-slate-900">
      <div className="flex items-center justify-between h-14 px-4 lg:px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-500 shadow-md shadow-teal-500/20">
            <svg className="h-4 w-4 text-white" viewBox="0 0 20 20" fill="currentColor">
              <path d="M10.362 1.093a.75.75 0 00-.724 0L2.523 5.018 10 9.143l7.477-4.125-7.115-3.925zM18 6.443l-7.25 4v8.25l6.862-3.786A.75.75 0 0018 14.25V6.443zm-8.75 12.25v-8.25l-7.25-4v7.807a.75.75 0 00.388.657l6.862 3.786z" />
            </svg>
          </div>
          <div>
            <h1 className="text-sm font-semibold text-white tracking-wide">BioNexus AI</h1>
            <p className="text-[10px] text-slate-400 leading-tight">Research Intelligence</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-teal-500 to-teal-600 text-white text-[10px] font-semibold shadow-sm">
              SR
            </div>
            <span className="hidden sm:block text-xs text-slate-400">Senior Researcher</span>
          </div>
        </div>
      </div>
    </header>
  )
}
