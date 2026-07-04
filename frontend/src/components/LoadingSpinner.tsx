const STEPS = [
  "Retrieving relevant biomedical literature",
  "Grading retrieved evidence for relevance",
  "Generating grounded answer with citations",
  "Checking for hallucinations against sources",
  "Verifying answer addresses the question",
  "Finalizing response",
]

interface LoadingSpinnerProps {
  currentStep?: number
}

export function LoadingSpinner({ currentStep = 0 }: LoadingSpinnerProps) {
  const activeIndex = Math.min(currentStep, STEPS.length - 1)

  return (
    <div className="flex items-start gap-6 py-4 animate-fade-in">
      <div className="relative flex shrink-0 items-center justify-center">
        <div className="absolute h-12 w-12 rounded-full border-4 border-teal-500/20 animate-pulse-ring" />
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-teal-500 to-teal-600 shadow-lg shadow-teal-500/20">
          <svg
            className="h-5 w-5 animate-spin-slow text-white"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          >
            <path d="M21 12a9 9 0 11-6.219-8.56" />
          </svg>
        </div>
      </div>

      <div className="flex-1">
        <p className="text-sm font-medium text-slate-200">
          Self-RAG Pipeline Running
        </p>
        <p className="mt-0.5 text-xs text-slate-500">
          Retrieving and verifying evidence — typically 5–15 seconds
        </p>
        <div className="mt-4 space-y-2">
          {STEPS.map((step, i) => {
            const isActive = i === activeIndex
            const isDone = i < activeIndex
            return (
              <div key={i} className="flex items-center gap-2.5">
                <div
                  className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold transition-all duration-300 ${
                    isDone
                      ? "bg-teal-500 text-slate-950"
                      : isActive
                        ? "bg-teal-500/20 text-teal-300 ring-2 ring-teal-500/40 ring-offset-1 ring-offset-slate-950 animate-step-pulse"
                        : "bg-slate-800 text-slate-500"
                  }`}
                >
                  {isDone ? (
                    <svg className="h-3 w-3" viewBox="0 0 16 16" fill="currentColor">
                      <path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z" />
                    </svg>
                  ) : (
                    i + 1
                  )}
                </div>
                <span
                  className={`text-xs transition-all duration-300 ${
                    isDone
                      ? "text-slate-600 line-through"
                      : isActive
                        ? "font-medium text-teal-400"
                        : "text-slate-500"
                  }`}
                >
                  {step}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
