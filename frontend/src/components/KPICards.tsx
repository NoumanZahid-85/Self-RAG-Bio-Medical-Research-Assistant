interface KPICardProps {
  label: string
  value: string
  trend: string
  trendUp: boolean
  icon: string
  color: "teal" | "indigo" | "emerald" | "amber"
}

const CARDS: KPICardProps[] = [
  {
    label: "Total Queries",
    value: "12,847",
    trend: "+12.5%",
    trendUp: true,
    icon: "M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z",
    color: "indigo",
  },
  {
    label: "Avg Response Time",
    value: "1.2s",
    trend: "-8.3%",
    trendUp: false,
    icon: "M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z",
    color: "teal",
  },
  {
    label: "Evidence Accuracy",
    value: "94.7%",
    trend: "+2.1%",
    trendUp: true,
    icon: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
    color: "emerald",
  },
  {
    label: "Active Sessions",
    value: "23",
    trend: "Live",
    trendUp: true,
    icon: "M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z",
    color: "amber",
  },
]

const SPARKLINE_PATHS: Record<string, string> = {
  "Total Queries": "M0 30 Q10 25 20 28 T40 20 T60 22 T80 15 T100 18",
  "Avg Response Time": "M0 10 Q10 15 20 12 T40 18 T60 15 T80 20 T100 18",
  "Evidence Accuracy": "M0 20 Q10 18 20 15 T40 12 T60 10 T80 8 T100 5",
  "Active Sessions": "M0 25 Q10 20 20 22 T40 18 T60 15 T80 10 T100 12",
}

function Sparkline({ label }: { label: string }) {
  const path = SPARKLINE_PATHS[label] ?? SPARKLINE_PATHS["Total Queries"]
  return (
    <svg className="absolute bottom-1 right-2 h-8 w-20 opacity-30" viewBox="0 0 100 32" preserveAspectRatio="none">
      <path d={path} fill="none" stroke="currentColor" strokeWidth="2" vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

export function KPICards() {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {CARDS.map((card) => (
        <div
          key={card.label}
          className="relative bg-slate-900/40 backdrop-blur-md rounded-2xl border border-slate-800/80 p-4 shadow-lg hover:shadow-xl hover:border-slate-700/80 transition-all duration-300 overflow-hidden animate-fade-in"
        >
          <div className="flex items-start justify-between mb-3">
            <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${
              card.color === "teal" ? "bg-teal-500/10 text-teal-400" :
              card.color === "indigo" ? "bg-indigo-500/10 text-indigo-400" :
              card.color === "emerald" ? "bg-emerald-500/10 text-emerald-400" :
              "bg-amber-500/10 text-amber-400"
            }`}>
              <svg className="h-4.5 w-4.5" viewBox="0 0 20 20" fill="currentColor">
                <path d={card.icon} />
              </svg>
            </div>
            <span className={`inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-[10px] font-medium border ${
              card.trendUp
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                : "bg-teal-500/10 text-teal-400 border-teal-500/20"
            }`}>
              <svg className={`h-3 w-3 ${card.trendUp ? "" : "rotate-180"}`} viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 17a.75.75 0 01-.75-.75V5.612L5.29 9.77a.75.75 0 01-1.08-1.04l5.25-5.5a.75.75 0 011.08 0l5.25 5.5a.75.75 0 11-1.08 1.04l-3.96-4.158V16.25A.75.75 0 0110 17z" clipRule="evenodd" />
              </svg>
              {card.trend}
            </span>
          </div>
          <p className="text-2xl font-bold text-white tracking-tight mb-0.5">{card.value}</p>
          <p className="text-xs text-slate-400">{card.label}</p>
          <Sparkline label={card.label} />
        </div>
      ))}
    </div>
  )
}
