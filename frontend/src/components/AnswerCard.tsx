interface AnswerCardProps {
  answer: string
  citations: string[]
  abstained: boolean
  graphPath: string[]
}

function CitationBadge({ pmid }: { pmid: string }) {
  const id = pmid.replace(/^PMID[:\s]*/i, "")
  const url = `https://pubmed.ncbi.nlm.nih.gov/${id}/`

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 rounded-lg bg-teal-500/10 px-3 py-1.5 text-xs font-medium text-teal-300 border border-teal-500/20 transition-all duration-200 hover:bg-teal-500/20 hover:text-teal-200 hover:border-teal-500/30"
    >
      <svg className="h-3 w-3 shrink-0" viewBox="0 0 16 16" fill="currentColor">
        <path d="M8 0a8 8 0 110 16A8 8 0 018 0zm.75 3.5h-1.5v4.5H7l.5.5.5-.5h.75V3.5zM8 10.5a1 1 0 100 2 1 1 0 000-2z" />
      </svg>
      PMID: {id}
      <svg className="h-2.5 w-2.5 text-teal-400" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M4.25 5.5a.75.75 0 00-.75.75v8.5c0 .414.336.75.75.75h8.5a.75.75 0 00.75-.75v-4a.75.75 0 011.5 0v4A2.25 2.25 0 0112.75 17h-8.5A2.25 2.25 0 012 14.75v-8.5A2.25 2.25 0 014.25 4h5a.75.75 0 010 1.5h-5z" clipRule="evenodd" />
        <path fillRule="evenodd" d="M6.194 12.753a.75.75 0 001.06.053L16.5 4.44v2.81a.75.75 0 001.5 0v-4.5a.75.75 0 00-.75-.75h-4.5a.75.75 0 000 1.5h2.553l-9.056 8.194a.75.75 0 00-.053 1.06z" clipRule="evenodd" />
      </svg>
    </a>
  )
}

function AbstainCard({ answer }: { answer: string }) {
  return (
    <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-5 shadow-lg shadow-amber-950/10 animate-slide-up">
      <div className="flex items-start gap-4">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-amber-500/10">
          <svg className="h-4 w-4 text-amber-400" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.168 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
          </svg>
        </div>
        <div className="flex-1 space-y-1.5">
          <h3 className="text-sm font-semibold text-amber-400">Insufficient Evidence</h3>
          <p className="text-sm leading-relaxed text-slate-300">{answer}</p>
          <p className="text-xs text-amber-500/70">
            The available biomedical literature does not contain enough relevant evidence
            to confidently answer this question.
          </p>
        </div>
      </div>
    </div>
  )
}

function AnswerContent({ answer, citations }: { answer: string; citations: string[] }) {
  return (
    <div className="space-y-4 animate-slide-up">
      <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-5 shadow-lg shadow-emerald-950/10">
        <div className="flex items-center gap-2 mb-3">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-emerald-500/10">
            <svg className="h-3.5 w-3.5 text-emerald-400" viewBox="0 0 16 16" fill="currentColor">
              <path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z" />
            </svg>
          </div>
          <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Grounded Answer</span>
        </div>
        <p className="text-sm leading-relaxed text-slate-200">{answer}</p>
      </div>

      {citations.length > 0 && (
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/30 p-5 shadow-xl">
          <h4 className="mb-2.5 text-xs font-semibold uppercase tracking-wider text-teal-400 flex items-center gap-1.5">
            <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
              <path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z" />
            </svg>
            Sources ({citations.length})
          </h4>
          <div className="flex flex-wrap gap-2">
            {citations.map((pmid) => (
              <CitationBadge key={pmid} pmid={pmid} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export function AnswerCard(props: AnswerCardProps) {
  return props.abstained ? (
    <AbstainCard answer={props.answer} />
  ) : (
    <AnswerContent answer={props.answer} citations={props.citations} />
  )
}
