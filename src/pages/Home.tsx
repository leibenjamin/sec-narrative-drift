import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import {
  listLabTickerSummaries,
  listLabShowcaseTickers,
  type LabTickerSummary,
} from "../lib/labData"

const SHOWCASE_COMPANY_NAMES: Record<string, string> = {
  NVDA: "NVIDIA",
  KO: "Coca-Cola",
  WM: "Waste Management",
  GE: "General Electric",
}

function buildCaseLink(ticker: string, pair: { from: number; to: number } | null): string {
  if (!pair) return `/company/${ticker}?tab=lab`
  return `/company/${ticker}?tab=lab&from=${pair.from}&to=${pair.to}`
}

function summarizeMethods(summary: LabTickerSummary): string {
  const detectorCount = summary.availableDetectors.length
  const lensCount = summary.availableLenses.length
  return `${detectorCount} methods across ${lensCount} lenses`
}

export default function Home() {
  const [summaries, setSummaries] = useState<LabTickerSummary[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    listLabTickerSummaries({ showcaseOnly: true })
      .then((result) => {
        if (cancelled) return
        setSummaries(result)
        setError(null)
      })
      .catch((loadError) => {
        if (cancelled) return
        setError(loadError instanceof Error ? loadError.message : "Failed to load Lab showcase data.")
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const preferredTicker = listLabShowcaseTickers()[0] ?? "NVDA"
  const starter = useMemo(() => {
    const preferred = summaries.find((entry) => entry.ticker === preferredTicker)
    return preferred ?? summaries[0] ?? null
  }, [preferredTicker, summaries])

  return (
    <main className="min-h-screen page-fade">
      <div className="mx-auto grid max-w-6xl gap-10 px-6 py-12">
        <section className="grid gap-6 rounded-2xl border border-white/10 bg-slate-900/45 p-6 shadow-[0_18px_48px_rgba(2,6,23,0.35)] lg:grid-cols-[1.45fr_0.55fr]">
          <div className="space-y-4">
            <p className="text-xs uppercase tracking-widest text-slate-300">SEC Narrative Drift Lab</p>
            <h1 className="max-w-3xl text-3xl font-semibold leading-tight">
              Deterministic risk-text analysis first, reproducible LLM sidecars second.
            </h1>
            <p className="max-w-3xl text-sm text-slate-200">
              Compare adjacent 10-K Item 1A years and inspect evidence directly. Each detector card
              links outputs to canonical JSON paths so reviewers can rerun, audit, and compare models
              without hidden runtime calls.
            </p>
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <Link
                to={buildCaseLink(starter?.ticker ?? preferredTicker, starter?.defaultPair ?? null)}
                className="inline-flex items-center rounded-md bg-sky-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-sky-500"
              >
                Start with recommended case
              </Link>
              <Link
                to="/companies"
                className="inline-flex items-center rounded-md border border-white/20 px-4 py-2 text-sm text-slate-200 transition hover:border-white/40 hover:bg-white/5"
              >
                Open showcase catalog
              </Link>
              <Link
                to="/methodology"
                className="inline-flex items-center rounded-md border border-white/20 px-4 py-2 text-sm text-slate-200 transition hover:border-white/40 hover:bg-white/5"
              >
                Read methodology
              </Link>
            </div>
          </div>

          <aside className="space-y-3 rounded-xl border border-white/10 bg-slate-950/40 p-4">
            <h2 className="text-sm font-semibold text-slate-100">What to do first</h2>
            <ol className="space-y-2 text-sm text-slate-200">
              <li>1. Open a showcase company.</li>
              <li>2. Keep lens on deboilerplated for the first read.</li>
              <li>3. Compare detector evidence before reading LLM sidecars.</li>
            </ol>
            <p className="text-xs text-slate-400">
              All runtime results load from static Lab JSON under
              <code className="ml-1 rounded bg-slate-950/70 px-1 py-0.5">public/data/sec_narrative_drift_lab/</code>.
            </p>
          </aside>
        </section>

        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-xl font-semibold">Showcase companies</h2>
            <p className="text-xs text-slate-400">Primary scope: NVDA, KO, WM, GE</p>
          </div>
          {isLoading ? (
            <p className="text-sm text-slate-300">Loading Lab showcase data...</p>
          ) : error ? (
            <p className="rounded-md border border-amber-400/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
              {error}
            </p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4 stagger-children">
              {summaries.map((summary) => {
                const companyName = SHOWCASE_COMPANY_NAMES[summary.ticker] ?? summary.ticker
                return (
                  <Link
                    key={summary.ticker}
                    to={buildCaseLink(summary.ticker, summary.defaultPair)}
                    className="rounded-xl border border-white/10 bg-slate-900/40 p-4 transition hover:border-sky-300/40 hover:bg-slate-900/60"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-base font-semibold">{summary.ticker}</div>
                        <div className="text-xs text-slate-300">{companyName}</div>
                      </div>
                      <span className="rounded-full border border-sky-300/30 bg-sky-400/10 px-2 py-0.5 text-[11px] text-sky-100">
                        Showcase
                      </span>
                    </div>
                    <div className="mt-3 space-y-1 text-xs text-slate-300">
                      <div>{summary.caseCount} adjacent pairs</div>
                      <div>{summarizeMethods(summary)}</div>
                      {summary.defaultPair ? (
                        <div>
                          Recommended: {summary.defaultPair.from}-{summary.defaultPair.to}
                        </div>
                      ) : null}
                    </div>
                  </Link>
                )
              })}
            </div>
          )}
        </section>
      </div>
    </main>
  )
}
