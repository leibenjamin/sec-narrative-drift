import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import {
  listLabTickerSummaries,
  listLabShowcaseTickers,
  type LabTickerSummary,
} from "../lib/labData"
import { formatFiscalYearRange } from "../lib/fiscalYear"

const ACTIVE_SCOPE_LABEL = "FY2024 to FY2025"

const SHOWCASE_COMPANY_NAMES: Record<string, string> = {
  NVDA: "NVIDIA",
  KO: "Coca-Cola",
  WM: "Waste Management",
  GE: "General Electric",
}

const SHOWCASE_THESES: Record<string, string> = {
  NVDA: "Export controls, supply concentration, and AI demand concentration keep shifting the risk story faster than a normal semiconductor cycle.",
  KO: "Currency, labeling regulation, and product-mix shifts show how a defensive global consumer company still rewrites its risk language over time.",
  WM: "Environmental regulation, landfill economics, and sustainability execution make small disclosure changes economically meaningful.",
  GE: "Installed-base services execution, defense exposure, and supply chain stress dominate the post-spin risk narrative for GE Aerospace.",
}

function buildCaseLink(ticker: string, pair: { from: number; to: number } | null): string {
  if (!pair) return `/company/${ticker}?tab=lab`
  return `/company/${ticker}?tab=lab&from=${pair.from}&to=${pair.to}`
}

function getActivePair(summary: LabTickerSummary | null): { from: number; to: number } | null {
  if (!summary) return null
  return summary.defaultPair ?? summary.latestPair ?? null
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
        setError(loadError instanceof Error ? loadError.message : "Failed to load company data.")
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
        <section className="grid gap-6 rounded-[1.8rem] border border-white/10 bg-linear-to-br from-slate-950/82 via-slate-900/62 to-slate-950/48 p-6 shadow-[0_26px_60px_rgba(2,6,23,0.38)] lg:grid-cols-[1.4fr_0.6fr]">
          <div className="space-y-5">
            <p className="text-xs uppercase tracking-[0.28em] text-sky-100">SEC Narrative Drift Lab</p>
            <h1 className="max-w-4xl text-4xl font-semibold leading-tight text-slate-50 sm:text-5xl">
              Open one company and see where the risk story actually changed.
            </h1>
            <p className="max-w-3xl text-base text-slate-200">
              The shipped Lab focuses on one active FY2024 to FY2025 Item 1A case for each Core4 company. Start with the
              compare-first narrative summary, confirm it with deterministic methods, then audit the side-by-side Codex and
              ChatGPT reads with filing-backed evidence.
            </p>
            <div className="flex flex-wrap gap-2 text-xs text-slate-200">
              <span className="rounded-full border border-sky-300/30 bg-sky-400/12 px-3 py-1">Core4 {ACTIVE_SCOPE_LABEL}</span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">One active case per company</span>
              <span className="rounded-full border border-emerald-300/25 bg-emerald-400/10 px-3 py-1">Codex vs ChatGPT compare</span>
            </div>
            <div className="flex flex-wrap items-center gap-3 pt-1">
              <Link
                to={buildCaseLink(starter?.ticker ?? preferredTicker, getActivePair(starter))}
                className="inline-flex items-center rounded-full bg-sky-500 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-sky-400"
              >
                Open first company case
              </Link>
              <Link
                to="/companies"
                className="inline-flex items-center rounded-full border border-white/20 px-5 py-2.5 text-sm text-slate-200 transition hover:border-white/40 hover:bg-white/5"
              >
                Browse companies
              </Link>
              <Link
                to="/methodology"
                className="inline-flex items-center rounded-full border border-white/20 px-5 py-2.5 text-sm text-slate-200 transition hover:border-white/40 hover:bg-white/5"
              >
                How to evaluate a case
              </Link>
            </div>
          </div>

          <aside className="space-y-4 rounded-[1.4rem] border border-white/10 bg-slate-950/55 p-5">
            <div>
              <div className="text-xs uppercase tracking-[0.24em] text-slate-400">Default reading flow</div>
              <ol className="mt-3 space-y-3 text-sm text-slate-200">
                <li>1. Read the risk narrative summary and the paired prior-year versus current-year evidence.</li>
                <li>2. Check the two core deterministic methods and agreement to confirm the filing signal.</li>
                <li>3. Open outline compare when you want the deeper structural audit.</li>
              </ol>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-slate-200">
              <div className="text-xs uppercase tracking-[0.24em] text-slate-400">Runtime contract</div>
              <p className="mt-2">
                Static JSON only. No runtime LLM calls. SEC text treated as untrusted. Missing artifacts stay explicit.
              </p>
            </div>
            <p className="text-xs text-slate-400">
              Runtime data source:
              <code className="ml-1 rounded bg-slate-950/70 px-1 py-0.5">
                public/data/sec_narrative_drift_lab/
              </code>
            </p>
          </aside>
        </section>

        <section className="grid gap-4 lg:grid-cols-3">
          <article className="rounded-[1.35rem] border border-sky-300/25 bg-sky-400/10 p-5">
            <div className="text-xs uppercase tracking-[0.24em] text-sky-100">Step 1</div>
            <h2 className="mt-2 text-xl font-semibold text-slate-100">Read the lead narrative</h2>
            <p className="mt-3 text-sm text-slate-200">
              Open a company and start with the risk narrative summary, paired filing evidence, and the side-by-side compare lanes.
            </p>
          </article>
          <article className="rounded-[1.35rem] border border-white/10 bg-slate-900/50 p-5">
            <div className="text-xs uppercase tracking-[0.24em] text-slate-300">Step 2</div>
            <h2 className="mt-2 text-xl font-semibold text-slate-100">Confirm the filing signal</h2>
            <p className="mt-3 text-sm text-slate-200">
              Use the two core deterministic methods plus agreement to separate real narrative movement from boilerplate churn.
            </p>
          </article>
          <article className="rounded-[1.35rem] border border-emerald-300/20 bg-emerald-400/10 p-5">
            <div className="text-xs uppercase tracking-[0.24em] text-emerald-100">Step 3</div>
            <h2 className="mt-2 text-xl font-semibold text-slate-100">Audit the deeper structure</h2>
            <p className="mt-3 text-sm text-slate-200">
              Use outline compare for mechanisms, investor relevance, limits, and structure when you want a deeper case read.
            </p>
          </article>
        </section>

        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-2xl font-semibold text-slate-50">Companies</h2>
              <p className="mt-1 text-sm text-slate-400">
                Current shipped scope: NVDA, KO, WM, and GE, each with one active {ACTIVE_SCOPE_LABEL} case.
              </p>
            </div>
            <p className="text-xs text-slate-400">Compare-visible campaigns: Codex real and ChatGPT real</p>
          </div>
          {isLoading ? (
            <p className="text-sm text-slate-300">Loading company data...</p>
          ) : error ? (
            <p className="rounded-md border border-amber-400/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
              {error}
            </p>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4 stagger-children">
              {summaries.map((summary) => {
                const companyName = SHOWCASE_COMPANY_NAMES[summary.ticker] ?? summary.ticker
                const activePair = getActivePair(summary)
                return (
                  <Link
                    key={summary.ticker}
                    to={buildCaseLink(summary.ticker, activePair)}
                    className="rounded-[1.45rem] border border-white/10 bg-slate-900/50 p-5 transition hover:border-sky-300/40 hover:bg-slate-900/68"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-base font-semibold text-slate-50">{summary.ticker}</div>
                        <div className="text-xs text-slate-300">{companyName}</div>
                      </div>
                      <span className="rounded-full border border-sky-300/30 bg-sky-400/10 px-2 py-0.5 text-[11px] text-sky-100">
                        Core4
                      </span>
                    </div>
                    <p className="mt-4 text-sm text-slate-200">
                      {SHOWCASE_THESES[summary.ticker] ?? "Review the active filing-to-filing comparison in the Lab experience."}
                    </p>
                    <div className="mt-4 space-y-1 text-xs text-slate-400">
                      <div>Active case: {activePair ? formatFiscalYearRange(activePair.from, activePair.to) : ACTIVE_SCOPE_LABEL}</div>
                      <div>{summarizeMethods(summary)}</div>
                    </div>
                    <div className="mt-4 inline-flex items-center rounded-full border border-white/15 px-3 py-1 text-xs text-slate-100">
                      Open company case
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
