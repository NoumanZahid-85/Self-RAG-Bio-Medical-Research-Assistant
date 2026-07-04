const ACTIVITIES = [
  {
    query: 'Does metformin reduce cardiovascular events in type 2 diabetes?',
    timestamp: '2 minutes ago',
    evidenceCount: 24,
    status: 'verified' as const,
  },
  {
    query: 'Efficacy of mRNA-1273 booster against Omicron variants',
    timestamp: '15 minutes ago',
    evidenceCount: 18,
    status: 'verified' as const,
  },
  {
    query: 'Correlation between gut microbiome and Parkinson\'s disease progression',
    timestamp: '1 hour ago',
    evidenceCount: 31,
    status: 'pending' as const,
  },
  {
    query: 'CRISPR-Cas9 off-target effects in hematopoietic stem cells',
    timestamp: '3 hours ago',
    evidenceCount: 7,
    status: 'pending' as const,
  },
  {
    query: 'Long-term outcomes of CAR-T therapy in pediatric ALL',
    timestamp: '6 hours ago',
    evidenceCount: 0,
    status: 'failed' as const,
  },
]

const STATUS_STYLES = {
  verified: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  pending: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  failed: 'bg-red-500/10 text-red-400 border-red-500/20',
}

const STATUS_LABELS = {
  verified: 'Verified',
  pending: 'Pending',
  failed: 'Failed',
}

export function ActivityFeed() {
  return (
    <div className="bg-slate-900/40 backdrop-blur-md rounded-2xl border border-slate-800/80 shadow-xl shadow-black/20">
      <div className="px-5 py-4 border-b border-slate-800/80">
        <h3 className="text-sm font-semibold text-slate-200">Recent Activity</h3>
      </div>
      <div className="divide-y divide-slate-800/60">
        {ACTIVITIES.map((activity, i) => (
          <div key={i} className="px-5 py-4 hover:bg-slate-800/10 transition-colors">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <p className="text-sm text-slate-300 font-medium truncate">
                  {activity.query}
                </p>
                <div className="flex items-center gap-3 mt-1.5">
                  <span className="text-[11px] text-slate-500">{activity.timestamp}</span>
                  <span className="text-[11px] text-slate-500">{activity.evidenceCount} sources</span>
                </div>
              </div>
              <span className={`shrink-0 inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border ${
                STATUS_STYLES[activity.status]
              }`}>
                <span className={`h-1.5 w-1.5 rounded-full mr-1.5 ${
                  activity.status === 'verified' ? 'bg-emerald-400' :
                  activity.status === 'pending' ? 'bg-amber-400' :
                  'bg-red-400'
                }`} />
                {STATUS_LABELS[activity.status]}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
