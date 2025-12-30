import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { copy, t } from "../lib/copy"
import { loadCompanyIndex, loadUniverseFeatured } from "../lib/data"
import type {
  CompanyIndex,
  CompanyIndexRow,
  QualityLevel,
  UniverseFeatured,
} from "../lib/types"
import QualityBadge from "../components/QualityBadge"

type CoverageFilter = "all" | "ge8"
type QualityFilter = "all" | "high" | "high_med"
type StoryFilter = "all" | "story"
type SortMode = "featured" | "az" | "peak_drift" | "coverage"

function normalize(s: string): string {
  return s.trim().toLowerCase()
}

function passesCoverage(row: CompanyIndexRow, f: CoverageFilter): boolean {
  if (f === "all") return true
  if (f === "ge8") return row.coverage.count >= 8
  return true
}

function passesQuality(level: QualityLevel, f: QualityFilter): boolean {
  if (f === "all") return true
  if (f === "high") return level === "high"
  if (f === "high_med") return level === "high" || level === "medium"
  return true
}

function passesStory(isStory: boolean, f: StoryFilter): boolean {
  if (f === "all") return true
  return isStory
}

function passesExchange(exchange: string | undefined, filter: string): boolean {
  if (filter === "all") return true
  if (!exchange) return false
  return exchange === filter
}

function formatCoverage(row: CompanyIndexRow): string {
  const { count, minYear, maxYear } = row.coverage
  return `${count}y ${minYear}-${maxYear}`
}

function formatLatestYear(row: CompanyIndexRow): string {
  const { maxYear } = row.coverage
  return maxYear ? `${copy.companies.latestYearLabel} ${maxYear}` : copy.companies.latestYearUnknown
}

export default function Companies() {
  const [index, setIndex] = useState<CompanyIndex | null>(null)
  const [universe, setUniverse] = useState<UniverseFeatured | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [query, setQuery] = useState("")
  const [coverageFilter, setCoverageFilter] = useState<CoverageFilter>("all")
  const [storyFilter, setStoryFilter] = useState<StoryFilter>("all")
  const [exchangeFilter, setExchangeFilter] = useState("all")
  const [qualityFilter, setQualityFilter] = useState<QualityFilter>("all")
  const [sortMode, setSortMode] = useState<SortMode>("featured")

  useEffect(() => {
    let mounted = true
    loadCompanyIndex()
      .then((d) => {
        if (!mounted) return
        setIndex(d)
      })
      .catch((e) => {
        if (!mounted) return
        setError(e?.message ?? copy.global.errors.missingDataset)
      })
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    let mounted = true
    loadUniverseFeatured()
      .then((data) => {
        if (!mounted) return
        setUniverse(data)
      })
      .catch(() => {
        if (!mounted) return
        setUniverse(null)
      })
    return () => {
      mounted = false
    }
  }, [])

  const rows = useMemo(() => index?.companies ?? [], [index])

  const storyTickers = useMemo(() => {
    const set = new Set<string>()
    if (universe?.stories) {
      for (const story of universe.stories) {
        if (story.ticker) {
          set.add(story.ticker.toUpperCase())
        }
      }
    }
    return set
  }, [universe])

  const exchangeOptions = useMemo(() => {
    const set = new Set<string>()
    for (const row of rows) {
      if (row.exchange) {
        set.add(row.exchange)
      }
    }
    const options = Array.from(set).sort((a, b) => a.localeCompare(b))
    return ["all", ...options]
  }, [rows])

  const featuredRows = useMemo(() => {
    return rows.filter((r) => !!r.featuredCase)
  }, [rows])

  const filtered = useMemo(() => {
    const q = normalize(query)
    const base = rows.filter((r) => {
      const hay = `${r.ticker} ${r.companyName ?? ""}`.toLowerCase()
      return !q || hay.includes(q)
    })

    const afterFilters = base.filter((r) => {
      const isStory = storyTickers.has(r.ticker)
      return (
        passesCoverage(r, coverageFilter) &&
        passesQuality(r.quality.level, qualityFilter) &&
        passesStory(isStory, storyFilter) &&
        passesExchange(r.exchange, exchangeFilter)
      )
    })

    const sorted = [...afterFilters].sort((a, b) => {
      if (sortMode === "az") {
        return a.ticker.localeCompare(b.ticker)
      }
      if (sortMode === "coverage") {
        return (b.coverage.count - a.coverage.count) || a.ticker.localeCompare(b.ticker)
      }
      if (sortMode === "peak_drift") {
        const av = a.metricsSummary?.peakDrift?.value ?? -1
        const bv = b.metricsSummary?.peakDrift?.value ?? -1
        return (bv - av) || a.ticker.localeCompare(b.ticker)
      }
      const af = a.featuredCase ? 1 : 0
      const bf = b.featuredCase ? 1 : 0
      return (bf - af) || a.ticker.localeCompare(b.ticker)
    })

    return sorted
  }, [rows, query, coverageFilter, qualityFilter, storyFilter, exchangeFilter, sortMode, storyTickers])

  return (
    <main className="min-h-screen">
      <div className="mx-auto max-w-5xl space-y-10 px-6 py-16">
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-wider text-slate-300">{copy.global.appName}</p>
          <h1 className="text-3xl font-semibold">{copy.companies.title}</h1>
          <p className="text-sm text-slate-300">
            {index
              ? t(copy.companies.coverageLine, {
                  n: index.companyCount,
                  target: index.lookbackTargetYears,
                })
              : copy.global.loading.base}
          </p>

          <div className="flex flex-wrap gap-3">
            <Link
              to="/"
              className="inline-flex items-center rounded-md border border-black/20 px-4 py-2 hover:bg-black/5"
            >
              {copy.nav.home}
            </Link>
            <Link
              to="/methodology"
              className="inline-flex items-center rounded-md border border-black/20 px-4 py-2 hover:bg-black/5"
            >
              {copy.nav.methodology}
            </Link>
          </div>
        </header>

        {error ? (
          <div className="rounded-lg border border-black/10 p-4 text-sm text-slate-200">
            {error}
          </div>
        ) : null}

        <section className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="rounded-md border border-black/20 px-3 py-2 text-sm"
              placeholder={copy.companies.searchPlaceholder}
              aria-label={copy.companies.searchAria}
            />

            <select
              value={coverageFilter}
              onChange={(e) => setCoverageFilter(e.target.value as CoverageFilter)}
              className="rounded-md border border-black/20 px-3 py-2 text-sm"
              aria-label={copy.companies.coverageFilterAria}
            >
              <option value="all">{copy.companies.filters.coverageAll}</option>
              <option value="ge8">{copy.companies.filters.coverageGe8}</option>
            </select>

            <select
              value={storyFilter}
              onChange={(e) => setStoryFilter(e.target.value as StoryFilter)}
              className="rounded-md border border-black/20 px-3 py-2 text-sm"
              aria-label={copy.companies.storyFilterAria}
            >
              <option value="all">{copy.companies.filters.storyAll}</option>
              <option value="story">{copy.companies.filters.storyOnly}</option>
            </select>

            <select
              value={exchangeFilter}
              onChange={(e) => setExchangeFilter(e.target.value)}
              className="rounded-md border border-black/20 px-3 py-2 text-sm"
              aria-label={copy.companies.exchangeFilterAria}
            >
              {exchangeOptions.map((exchange) => (
                <option key={exchange} value={exchange}>
                  {exchange === "all"
                    ? copy.companies.filters.exchangeAll
                    : exchange}
                </option>
              ))}
            </select>

            <select
              value={qualityFilter}
              onChange={(e) => setQualityFilter(e.target.value as QualityFilter)}
              className="rounded-md border border-black/20 px-3 py-2 text-sm"
              aria-label={copy.companies.qualityFilterAria}
            >
              <option value="all">{copy.companies.filters.qualityAll}</option>
              <option value="high">{copy.companies.filters.qualityHigh}</option>
              <option value="high_med">{copy.companies.filters.qualityHighMed}</option>
            </select>

            <select
              value={sortMode}
              onChange={(e) => setSortMode(e.target.value as SortMode)}
              className="rounded-md border border-black/20 px-3 py-2 text-sm"
              aria-label={copy.companies.sortAria}
            >
              <option value="featured">{copy.companies.sort.featured}</option>
              <option value="az">{copy.companies.sort.az}</option>
              <option value="peak_drift">{copy.companies.sort.peakDrift}</option>
              <option value="coverage">{copy.companies.sort.coverage}</option>
            </select>
          </div>
        </section>

        {featuredRows.length ? (
          <section className="space-y-3">
            <h2 className="text-lg font-semibold">{copy.companies.featuredTitle}</h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {featuredRows.slice(0, 12).map((r) => {
                const fc = r.featuredCase!
                const link = `/company/${r.ticker}?from=${fc.from}&to=${fc.to}`
                return (
                  <Link
                    key={r.ticker}
                    to={link}
                    className="rounded-lg border border-black/10 p-4 hover:bg-black/5"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-sm font-semibold">{r.ticker}</div>
                        <div className="text-xs text-slate-300">{r.companyName}</div>
                      </div>
                      <span className="rounded-full border border-black/20 px-2 py-1 text-[11px]">
                        {copy.companies.featuredChip}
                      </span>
                    </div>
                    <div className="mt-3 text-sm font-medium">{fc.title}</div>
                    <div className="mt-2 text-xs text-slate-300">{fc.blurb}</div>
                    <div className="mt-3 text-xs text-slate-300">
                      {t(copy.companies.compareYearsLabel, { from: fc.from, to: fc.to })}
                    </div>
                  </Link>
                )
              })}
            </div>
          </section>
        ) : null}

        <section className="space-y-3">
          <div className="text-sm text-slate-300">
            {t(copy.companies.resultsCount, { n: filtered.length })}
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((r) => {
              const auto = r.autoPair
              const isStory = storyTickers.has(r.ticker)
              const jump = auto
                ? `/company/${r.ticker}?from=${auto.from}&to=${auto.to}`
                : `/company/${r.ticker}`
              return (
                <div key={r.ticker} className="rounded-lg border border-black/10 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <Link to={`/company/${r.ticker}`} className="text-sm font-semibold hover:underline">
                        {r.ticker}
                      </Link>
                      <div className="mt-1 text-xs text-slate-300">{r.companyName}</div>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      {isStory ? (
                        <span className="rounded-full border border-black/20 px-2 py-1 text-[11px]">
                          {copy.companies.storyChip}
                        </span>
                      ) : null}
                      <QualityBadge level={r.quality.level} />
                    </div>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-300">
                    <span className="rounded-full border border-black/20 px-2 py-1">
                      {formatCoverage(r)}
                    </span>
                    <span className="rounded-full border border-black/20 px-2 py-1">
                      {formatLatestYear(r)}
                    </span>
                    {r.metricsSummary?.peakDrift ? (
                      <span className="rounded-full border border-black/20 px-2 py-1">
                        {t(copy.companies.peakDriftLabel, {
                          from: r.metricsSummary.peakDrift.from,
                          to: r.metricsSummary.peakDrift.to,
                          v: r.metricsSummary.peakDrift.value.toFixed(2),
                        })}
                      </span>
                    ) : null}
                  </div>

                  <div className="mt-4 flex gap-3">
                    <Link
                      to={jump}
                      className="inline-flex items-center rounded-md border border-black/20 px-3 py-2 text-xs hover:bg-black/5"
                    >
                      {copy.companies.jumpBiggestShift}
                    </Link>
                  </div>
                </div>
              )
            })}
          </div>
        </section>

        <footer className="pt-8 text-xs text-slate-400">
          {copy.global.sourceLine} {copy.global.caveatLine}
        </footer>
      </div>
    </main>
  )
}
