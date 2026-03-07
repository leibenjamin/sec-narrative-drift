import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { listLabTickerSummaries, type LabTickerSummary } from "../lib/labData"
import { formatFiscalYearRange } from "../lib/fiscalYear"

const SHOWCASE_COMPANY_NAMES: Record<string, string> = {
  NVDA: "NVIDIA",
  KO: "Coca-Cola",
  WM: "Waste Management",
  GE: "General Electric",
}

type LensFilter = "all" | "deboilerplated" | "raw"

function buildLabLink(ticker: string, pair: { from: number; to: number } | null): string {
  if (!pair) return `/company/${ticker}?tab=lab`
  return `/company/${ticker}?tab=lab&from=${pair.from}&to=${pair.to}`
}

export default function Companies() {
  const [summaries, setSummaries] = useState<LabTickerSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState("")
  const [lensFilter, setLensFilter] = useState<LensFilter>("all")

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

  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()
    return summaries.filter((summary) => {
      const companyName = SHOWCASE_COMPANY_NAMES[summary.ticker] ?? summary.ticker
      if (
        normalizedQuery &&
        !`${summary.ticker} ${companyName}`.toLowerCase().includes(normalizedQuery)
      ) {
        return false
      }
      if (lensFilter === "all") return true
      return summary.availableLenses.includes(lensFilter)
    })
  }, [lensFilter, query, summaries])

  return (
    <main className="min-h-screen page-fade">
      <div className="mx-auto max-w-6xl space-y-8 px-6 py-12">
        <header className="space-y-4">
          <p className="text-xs uppercase tracking-widest text-slate-300">Lab showcase</p>
          <h1 className="text-3xl font-semibold">Choose a company and pair</h1>
          <p className="max-w-3xl text-sm text-slate-300">
            This catalog is curated for high-signal adjacent pair analysis. Each card routes
            directly to a recommended Lab case and preserves deep-link stability.
          </p>
          <div className="grid gap-3 rounded-xl border border-white/10 bg-slate-900/45 p-4 md:grid-cols-3">
            <div className="rounded-md border border-white/10 bg-slate-950/35 p-3">
              <div className="text-[11px] uppercase tracking-wide text-slate-400">Fast path</div>
              <div className="mt-1 text-sm text-slate-100">Open recommended pair first.</div>
            </div>
            <div className="rounded-md border border-white/10 bg-slate-950/35 p-3">
              <div className="text-[11px] uppercase tracking-wide text-slate-400">Interpretation</div>
              <div className="mt-1 text-sm text-slate-100">Deterministic evidence before LLM sidecars.</div>
            </div>
            <div className="rounded-md border border-white/10 bg-slate-950/35 p-3">
              <div className="text-[11px] uppercase tracking-wide text-slate-400">Scope</div>
              <div className="mt-1 text-sm text-slate-100">Showcase tickers only: NVDA, KO, WM, GE.</div>
            </div>
          </div>
        </header>

        <section className="grid gap-3 rounded-xl border border-white/10 bg-slate-900/45 p-4 sm:grid-cols-2 lg:grid-cols-3">
          <label className="space-y-1 text-sm">
            <span className="text-xs uppercase tracking-wide text-slate-400">Search</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="w-full rounded-md border border-white/15 bg-slate-950/40 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-400 focus:border-sky-400/60 focus:outline-none focus:ring-2 focus:ring-sky-400/20"
              placeholder="Ticker or company"
              aria-label="Search showcase companies"
            />
          </label>

          <label className="space-y-1 text-sm">
            <span className="text-xs uppercase tracking-wide text-slate-400">Lens availability</span>
            <select
              value={lensFilter}
              onChange={(event) => setLensFilter(event.target.value as LensFilter)}
              className="w-full rounded-md border border-white/15 bg-slate-950/40 px-3 py-2 text-sm text-slate-100 focus:border-sky-400/60 focus:outline-none focus:ring-2 focus:ring-sky-400/20"
              aria-label="Filter by lens availability"
            >
              <option value="all">All</option>
              <option value="deboilerplated">Deboilerplated</option>
              <option value="raw">Raw</option>
            </select>
          </label>

          <div className="self-end text-xs text-slate-400">
            Showing {filtered.length} of {summaries.length} showcase companies.
          </div>
        </section>

        {isLoading ? (
          <p className="text-sm text-slate-300">Loading showcase catalog...</p>
        ) : error ? (
          <div className="rounded-lg border border-amber-400/30 bg-amber-500/10 p-4 text-sm text-amber-100">
            {error}
          </div>
        ) : (
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4 stagger-children">
            {filtered.map((summary) => {
              const companyName = SHOWCASE_COMPANY_NAMES[summary.ticker] ?? summary.ticker
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
                      Showcase
                    </span>
                  </div>

                  <div className="mt-3 space-y-1 text-xs text-slate-300">
                    <p>{summary.caseCount} adjacent year pairs</p>
                    <p>{summary.availableDetectors.length} methods available</p>
                    <p>Lenses: {summary.availableLenses.join(", ")}</p>
                    {summary.defaultPair ? (
                      <p>
                        Recommended pair: {formatFiscalYearRange(summary.defaultPair.from, summary.defaultPair.to)}
                      </p>
                    ) : null}
                    {summary.latestPair ? (
                      <p>
                        Latest pair: {formatFiscalYearRange(summary.latestPair.from, summary.latestPair.to)}
                      </p>
                    ) : null}
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    <Link
                      to={buildLabLink(summary.ticker, summary.defaultPair)}
                      className="inline-flex items-center rounded-md bg-sky-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-sky-500"
                    >
                      Open recommended
                    </Link>
                    <Link
                      to={buildLabLink(summary.ticker, summary.latestPair)}
                      className="inline-flex items-center rounded-md border border-white/20 px-3 py-1.5 text-xs text-slate-200 hover:border-white/40 hover:bg-white/5"
                    >
                      Open latest
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

