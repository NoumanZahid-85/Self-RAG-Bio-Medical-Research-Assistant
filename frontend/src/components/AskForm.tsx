import { useState, useRef } from "react"
import { LoadingSpinner } from "./LoadingSpinner"
import { AnswerCard } from "./AnswerCard"

interface AskResponse {
  answer: string
  citations: string[]
  abstained: boolean
  graph_path: string[]
}

interface StreamProgress {
  step: string
  detail: string
}

interface StreamComplete {
  step: "complete"
  answer: string
  citations: string[]
  abstained: boolean
  graph_path: string[]
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"

type FormState =
  | { status: "idle" }
  | { status: "loading"; startedAt: number; currentStep: number }
  | { status: "success"; data: AskResponse }
  | { status: "error"; message: string }

const STEP_ORDER = [
  "retrieve",
  "grade_documents",
  "generate",
  "check_hallucination",
  "grade_answer",
  "rewrite_query",
]

export function AskForm() {
  const [question, setQuestion] = useState("")
  const [state, setState] = useState<FormState>({ status: "idle" })
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!question.trim()) return

    setState({ status: "loading", startedAt: Date.now(), currentStep: 0 })

    try {
      const res = await fetch(`${API_BASE}/ask/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: question.trim() }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => null)
        if (res.status === 429) {
          const retry = body?.retry_after_seconds ?? 30
          setState({
            status: "error",
            message: `The system is busy. Please wait ${retry} seconds before trying again.`,
          })
        } else {
          setState({
            status: "error",
            message: body?.detail ?? `Server error (${res.status})`,
          })
        }
        return
      }

      const reader = res.body?.getReader()
      if (!reader) throw new Error("No response body")

      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = lines.pop() ?? ""

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue
          const raw = line.slice(6).trim()
          if (!raw) continue

          try {
            const data = JSON.parse(raw)

            if (data.step === "complete") {
              const complete = data as StreamComplete
              setState({
                status: "success",
                data: {
                  answer: complete.answer,
                  citations: complete.citations,
                  abstained: complete.abstained,
                  graph_path: complete.graph_path,
                },
              })
            } else if (data.step === "started") {
              // ignore
            } else {
              const progress = data as StreamProgress
              const idx = STEP_ORDER.indexOf(progress.step)
              if (idx >= 0) {
                setState((prev) =>
                  prev.status === "loading"
                    ? { ...prev, currentStep: idx }
                    : prev,
                )
              }
            }
          } catch {
            // skip malformed JSON
          }
        }
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        setState({
          status: "error",
          message: "Request timed out after 90 seconds. The pipeline may be experiencing high load.",
        })
      } else {
        setState({
          status: "error",
          message: "Could not reach the server. Make sure the backend is running.",
        })
      }
    }
  }

  function handleReset() {
    setQuestion("")
    setState({ status: "idle" })
    inputRef.current?.focus()
  }

  return (
    <div className="w-full">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="relative">
          <input
            ref={inputRef}
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder='e.g. "Does metformin reduce cardiovascular events in type 2 diabetes?"'
            disabled={state.status === "loading"}
            className="w-full rounded-xl border border-slate-800 bg-slate-950/80 px-4 py-3 pr-10 text-sm text-white placeholder-slate-500 shadow-inner shadow-black/40 transition-all duration-200 outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-900/40 disabled:cursor-not-allowed disabled:opacity-60"
          />
          {question && (
            <button
              type="button"
              onClick={() => setQuestion("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
            >
              <svg className="h-4 w-4" viewBox="0 0 16 16" fill="currentColor">
                <path d="M4.646 4.646a.5.5 0 01.708 0L8 7.293l2.646-2.647a.5.5 0 01.708.708L8.707 8l2.647 2.646a.5.5 0 01-.708.708L8 8.707l-2.646 2.647a.5.5 0 01-.708-.708L7.293 8 4.646 5.354a.5.5 0 010-.708z" />
              </svg>
              <span className="sr-only">Clear</span>
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            type="submit"
            disabled={state.status === "loading" || !question.trim()}
            className="flex items-center justify-center gap-2 rounded-xl bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-teal-700/20 transition-all duration-200 hover:bg-teal-500 hover:shadow-teal-600/30 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {state.status === "loading" ? (
              <>
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Processing...
              </>
            ) : (
              <>
                <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10.668 1.032a.75.75 0 01.659.455l2.387 5.91 5.989.718a.75.75 0 01.433 1.31l-4.46 3.968 1.308 5.868a.75.75 0 01-1.116.809L10 16.025l-4.868 3.085a.75.75 0 01-1.116-.809l1.308-5.868-4.46-3.968a.75.75 0 01.433-1.31l5.989-.718 2.387-5.91a.75.75 0 01.727-.495z" clipRule="evenodd" />
                </svg>
                Search Literature
              </>
            )}
          </button>
          {state.status === "success" && (
            <button
              type="button"
              onClick={handleReset}
              className="flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900 px-4 py-2.5 text-sm font-medium text-slate-300 shadow-sm transition-all duration-200 hover:bg-slate-800 hover:text-white hover:border-slate-700"
            >
              <svg className="h-4 w-4" viewBox="0 0 16 16" fill="currentColor">
                <path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z" />
              </svg>
              New Question
            </button>
          )}
        </div>
      </form>

      {state.status === "loading" && (
        <div className="mt-4 rounded-2xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-md p-5 shadow-xl shadow-black/20">
          <LoadingSpinner currentStep={state.currentStep} />
        </div>
      )}

      {state.status === "success" && (
        <div className="mt-4">
          <AnswerCard
            answer={state.data.answer}
            citations={state.data.citations}
            abstained={state.data.abstained}
            graphPath={state.data.graph_path}
          />
        </div>
      )}

      {state.status === "error" && (
        <div className="mt-4 rounded-2xl border border-red-500/20 bg-red-500/5 p-5 shadow-lg animate-fade-in">
          <div className="flex items-start gap-3">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-red-500/10">
              <svg className="h-4 w-4 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
              </svg>
            </div>
            <p className="text-sm leading-relaxed text-red-300">{state.message}</p>
          </div>
        </div>
      )}
    </div>
  )
}
