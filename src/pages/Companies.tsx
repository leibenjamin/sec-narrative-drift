import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { listLabTickerSummaries, type LabTickerSummary } from "../lib/labData"
import { formatFiscalYearRange } from "../lib/fiscalYear"

const ACTIVE_SCOPE_LABEL = "FY2024 to FY2025"

const SHOWCASE_COMPANY_NAMES: Record<string, string> = {
  NVDA: "NVIDIA",
  KO: "Coca-Cola",
  WM: "Waste Management",
  GE: "General Electric",
}

const SHOWCASE_THESES: Record<string, string> = {
  NVDA: "Export controls, supply concentration, and AI demand concentration are now the main test of whether NVIDIA's risk language is truly changing or just intensifying familiar themes.",
  KO: "Currency, labeling regulation, and product-mix shifts show whether Coca-Cola's filing is updating the economic story or preserving defensive-company boilerplate.",
  WM: "Environmental regulation, landfill economics, and sustainability execution make small wording changes disproportionately meaningful for Waste Management.",
  GE: "Installed-base services execution, defense exposure, and supply chain stress dominate the current GE Aerospace case and make the compare lanes unusually interpretable.",
}

function buildLabLink(ticker: string, pair: { from: number; to: number } | null): string {
  if (!pair) return `/company/${ticker}?tab=lab`
  return `/company/${ticker}?tab=lab&from=${pair.from}&to=${pair.to}`
}

function getActivePair(summary: LabTickerSummary): { from: number; to: number } | null {
  return summary.defaultPair ?? summary.latestPair ?? null
}

export default function Companies() {
  const [summaries, setSummaries] = useState<LabTickerSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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

  return (
    <main className="min-h-screen page-fade">
      <div className="mx-auto max-w-6xl space-y-8 px-6 py-12">
        <header className="space-y-4">
          <p className="text-xs uppercase tracking-widest text-slate-300">Companies</p>
          <h1 className="text-3xl font-semibold">Open one active case per company</h1>
          <p className="max-w-3xl text-sm text-slate-300">
            The shipped catalog is intentionally narrow: four companies, one active FY2024 to FY2025 Item 1A case each,
            and one consistent reading path from compare-first narrative summary to deeper audit.
          </p>
          <div className="grid gap-3 rounded-xl border border-white/10 bg-slate-900/45 p-4 md:grid-cols-3">
            <div className="rounded-md border border-white/10 bg-slate-950/35 p-3">
              <div className="text-[11px] uppercase tracking-wide text-slate-400">Scope</div>
              <div className="mt-1 text-sm text-slate-100">Core4 only: NVDA, KO, WM, and GE.</div>
            </div>
            <div className="rounded-md border border-white/10 bg-slate-950/35 p-3">
              <div className="text-[11px] uppercase tracking-wide text-slate-400">Active case</div>
              <div className="mt-1 text-sm text-slate-100">{ACTIVE_SCOPE_LABEL} for every company card.</div>
            </div>
            <div className="rounded-md border border-white/10 bg-slate-950/35 p-3">
              <div className="text-[11px] uppercase tracking-wide text-slate-400">Default read</div>
              <div className="mt-1 text-sm text-slate-100">Narrative summary, core methods, agreement, then outline compare.</div>
            </div>
          </div>
        </header>

        {isLoading ? (
          <p className="text-sm text-slate-300">Loading company catalog...</p>
        ) : error ? (
          <div className="rounded-lg border border-amber-400/30 bg-amber-500/10 p-4 text-sm text-amber-100">
            {error}
          </div>
        ) : (
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4 stagger-children">
            {summaries.map((summary) => {
              const companyName = SHOWCASE_COMPANY_NAMES[summary.ticker] ?? summary.ticker
              const activePair = getActivePair(summary)
              return (
                <article
                  key={summary.ticker}
                  className="flex h-full flex-col rounded-xl border border-white/10 bg-slate-900/45 p-4 transition hover:border-sky-300/40"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h2 className="text-lg font-semibold">{summary.ticker}</h2>
                      <p className="text-xs text-slate-300">{companyName}</p>
                    </div>
                    <span className="rounded-full border border-sky-300/30 bg-sky-400/10 px-2 py-0.5 text-[11px] text-sky-100">
                      Core4
                    </span>
                  </div>

                  <p className="mt-4 text-sm text-slate-200">
                    {SHOWCASE_THESES[summary.ticker] ?? "Open the company case to review the active filing-to-filing comparison."}
                  </p>

                  <div className="mt-3 space-y-1 text-xs text-slate-300">
                    <p>Active case: {activePair ? formatFiscalYearRange(activePair.from, activePair.to) : ACTIVE_SCOPE_LABEL}</p>
                    <p>{summary.availableDetectors.length} methods available</p>
                    <p>Lenses: {summary.availableLenses.join(", ")}</p>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    <Link
                      to={buildLabLink(summary.ticker, activePair)}
                      className="inline-flex items-center rounded-md bg-sky-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-sky-500"
                    >
                      Open company case
                    </Link>
                  </div>
                </article>
              )
            })}
          </section>
        )}
      </div>
    </main>
  )
}
