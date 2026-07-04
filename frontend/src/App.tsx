import { Navbar } from "./components/Navbar"
import { AskForm } from "./components/AskForm"
import { KPICards } from "./components/KPICards"
import { ActivityFeed } from "./components/ActivityFeed"

function App() {
  return (
    <div className="min-h-screen bg-surface text-slate-100 selection:bg-teal-500/30 selection:text-teal-200">
      <Navbar />

      <main className="px-4 lg:px-6 py-6 max-w-7xl mx-auto space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-900 pb-5">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
              Research Dashboard
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Self-RAG pipeline — grounded biomedical literature analysis with self-verification
            </p>
          </div>
        </div>

        <div className="animate-fade-in">
          <KPICards />
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 space-y-6">
            <div className="bg-slate-900/40 backdrop-blur-md rounded-2xl border border-slate-800/80 p-6 shadow-xl shadow-black/20">
              <h2 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-teal-400 animate-pulse" />
                Research Query
              </h2>
              <AskForm />
            </div>

            <div className="bg-slate-900/40 backdrop-blur-md rounded-2xl border border-slate-800/80 shadow-xl shadow-black/20 overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-800/80">
                <h2 className="text-sm font-semibold text-slate-200">Recent Queries</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-800/80 bg-slate-950/40">
                      <th className="text-left px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Query</th>
                      <th className="text-left px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Status</th>
                      <th className="text-left px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Evidence</th>
                      <th className="text-left px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {[
                      { query: "Metformin cardiovascular outcomes in T2DM", status: "verified" as const, evidence: 24, date: "2024-03-15" },
                      { query: "mRNA-1273 booster Omicron efficacy", status: "verified" as const, evidence: 18, date: "2024-03-15" },
                      { query: "Gut microbiome Parkinson's correlation", status: "pending" as const, evidence: 31, date: "2024-03-14" },
                      { query: "CRISPR-Cas9 off-target HSCs", status: "pending" as const, evidence: 7, date: "2024-03-14" },
                      { query: "CAR-T therapy pediatric ALL outcomes", status: "failed" as const, evidence: 0, date: "2024-03-13" },
                    ].map((row, i) => (
                      <tr key={i} className="hover:bg-slate-800/20 transition-colors">
                        <td className="px-6 py-4.5 text-sm text-slate-300 max-w-[280px] truncate">{row.query}</td>
                        <td className="px-6 py-4.5">
                          <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-medium border ${
                            row.status === "verified" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                            row.status === "pending" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                            "bg-red-500/10 text-red-400 border-red-500/20"
                          }`}>
                            <span className={`h-1.5 w-1.5 rounded-full ${
                              row.status === "verified" ? "bg-emerald-400" :
                              row.status === "pending" ? "bg-amber-400" : "bg-red-400"
                            }`} />
                            {row.status === "verified" ? "Verified" : row.status === "pending" ? "Pending" : "Failed"}
                          </span>
                        </td>
                        <td className="px-6 py-4.5 text-sm text-slate-300">{row.evidence}</td>
                        <td className="px-6 py-4.5 text-sm text-slate-400">{row.date}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <ActivityFeed />
          </div>
        </div>
      </main>

      <footer className="border-t border-slate-900 bg-slate-950/80 backdrop-blur-md px-6 py-4 mt-12">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <span className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-[11px] text-slate-400">Connected to backend pipeline</span>
          </span>
          <span className="text-[11px] text-slate-500">v2.4.1</span>
        </div>
      </footer>
    </div>
  )
}

export default App
