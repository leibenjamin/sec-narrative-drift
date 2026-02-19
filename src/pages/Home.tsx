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
  return `${summary.availableDetectors.length} methods across ${summary.availableLenses.length} lenses`
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
      <div className="mx-auto grid max-w-6xl gap-8 px-6 py-12">
        <section className="grid gap-6 rounded-2xl border border-white/10 bg-slate-900/45 p-6 shadow-[0_18px_48px_rgba(2,6,23,0.35)] lg:grid-cols-[1.45fr_0.55fr]">
          <div className="space-y-4">
            <p className="text-xs uppercase tracking-widest text-slate-300">SEC Narrative Drift Lab</p>
            <h1 className="max-w-3xl text-4xl font-semibold leading-tight">
              Deterministic risk-language evidence first, reproducible LLM overlays second.
            </h1>
            <p className="max-w-3xl text-sm text-slate-200">
              This Lab compares adjacent 10-K Item 1A years and keeps every result path-auditable.
              Reviewers can inspect deterministic detectors, then rerun optional LLM sidecars with
              the same input bundles and starter prompts.
            </p>
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <Link
                to={buildCaseLink(starter?.ticker ?? preferredTicker, starter?.defaultPair ?? null)}
                className="inline-flex items-center rounded-md bg-sky-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-sky-500"
              >
                Start recommended case
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
                Methodology and reproducibility
              </Link>
            </div>
          </div>

          <aside className="space-y-3 rounded-xl border border-white/10 bg-slate-950/40 p-4">
            <h2 className="text-sm font-semibold text-slate-100">Hiring demo framing</h2>
            <ul className="space-y-2 text-sm text-slate-200">
              <li>1. Show one adjacent pair and detector agreement.</li>
              <li>2. Explain deterministic contract and path-level transparency.</li>
              <li>3. Show optional LLM sidecar reproducibility workflow.</li>
            </ul>
            <p className="text-xs text-slate-400">
              Runtime data source:
              <code className="ml-1 rounded bg-slate-950/70 px-1 py-0.5">
                public/data/sec_narrative_drift_lab/
              </code>
            </p>
          </aside>
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <article className="rounded-xl border border-sky-300/30 bg-sky-400/10 p-5">
            <div className="text-xs uppercase tracking-widest text-sky-100">Path A</div>
            <h2 className="mt-2 text-xl font-semibold text-slate-100">30-second executive read</h2>
            <ol className="mt-3 space-y-1 text-sm text-slate-200">
              <li>1. Open recommended pair (deboilerplated lens).</li>
              <li>2. Read log-odds + JSD cards for top shift narrative.</li>
              <li>3. Confirm with agreement matrix and one evidence excerpt.</li>
            </ol>
            <Link
              to={buildCaseLink(starter?.ticker ?? preferredTicker, starter?.defaultPair ?? null)}
              className="mt-4 inline-flex items-center rounded-md border border-sky-200/40 px-3 py-1.5 text-xs text-sky-100 transition hover:border-sky-100/70 hover:bg-sky-200/10"
            >
              Launch executive path
            </Link>
          </article>

          <article className="rounded-xl border border-white/10 bg-slate-900/50 p-5">
            <div className="text-xs uppercase tracking-widest text-slate-300">Path B</div>
            <h2 className="mt-2 text-xl font-semibold text-slate-100">Technical deep dive</h2>
            <ol className="mt-3 space-y-1 text-sm text-slate-200">
              <li>1. Compare lenses and inspect structure/reuse detectors.</li>
              <li>2. Open LLM sidecars and inspect expected input/output paths.</li>
              <li>3. Validate reproducibility with manifest and strict validator.</li>
            </ol>
            <Link
              to="/methodology"
              className="mt-4 inline-flex items-center rounded-md border border-white/20 px-3 py-1.5 text-xs text-slate-100 transition hover:border-white/40 hover:bg-white/5"
            >
              Launch technical path
            </Link>
          </article>
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
                    className="rounded-xl border border-white/10 bg-slate-900/45 p-4 transition hover:border-sky-300/40 hover:bg-slate-900/65"
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
