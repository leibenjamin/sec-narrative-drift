import { useEffect, useMemo, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { copy } from "../lib/copy"
import {
  listFeaturedTickers,
  loadCompanyFilings,
  loadCompanyMeta,
  loadExcerpts,
  loadMetrics,
  loadShifts,
  loadSimilarity,
} from "../lib/data"
import type {
  Excerpts,
  FilingRow,
  Meta,
  Metrics,
  ShiftPairs,
  SimilarityMatrix,
} from "../lib/types"

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return ""
  return value.toFixed(2)
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) return error.message
  return fallback
}

export default function Company() {
  const params = useParams()
  const fallbackTicker = listFeaturedTickers()[0] ?? "AAPL"
  const ticker = (params.ticker ?? fallbackTicker).toUpperCase()

  const [meta, setMeta] = useState<Meta | null>(null)
  const [filings, setFilings] = useState<FilingRow[]>([])
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [similarity, setSimilarity] = useState<SimilarityMatrix | null>(null)
  const [shifts, setShifts] = useState<ShiftPairs | null>(null)
  const [excerpts, setExcerpts] = useState<Excerpts | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [excerptsError, setExcerptsError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function loadData() {
      setLoading(true)
      setError(null)
      setExcerptsError(null)
      setMeta(null)
      setFilings([])
      setMetrics(null)
      setSimilarity(null)
      setShifts(null)
      setExcerpts(null)

      try {
        const [metaData, filingsData, metricsData, similarityData, shiftsData] =
          await Promise.all([
            loadCompanyMeta(ticker),
            loadCompanyFilings(ticker),
            loadMetrics(ticker),
            loadSimilarity(ticker),
            loadShifts(ticker),
          ])

        if (cancelled) return

        setMeta(metaData)
        setFilings(filingsData)
        setMetrics(metricsData)
        setSimilarity(similarityData)
        setShifts(shiftsData)
        setLoading(false)
      } catch (err) {
        if (cancelled) return
        setError(getErrorMessage(err, copy.global.errors.missingDataset))
        setLoading(false)
        return
      }

      try {
        const excerptsData = await loadExcerpts(ticker)
        if (cancelled) return
        setExcerpts(excerptsData)
      } catch (err) {
        if (cancelled) return
        setExcerptsError(getErrorMessage(err, copy.global.errors.missingExcerpts))
        setExcerpts(null)
      }
    }

    loadData()

    return () => {
      cancelled = true
    }
  }, [ticker])

  const yearRange = useMemo(() => {
    const years = metrics?.years ?? []
    if (years.length === 0) return ""
    const start = years[0]
    const end = years[years.length - 1]
    return start === end ? String(start) : `${start}-${end}`
  }, [metrics])

  const driftRows = useMemo(() => {
    if (!metrics) return []
    return metrics.years.map((year, index) => ({
      year,
      prevYear: metrics.years[index - 1],
      drift: metrics.drift_vs_prev?.[index] ?? null,
      ciLow: metrics.drift_ci_low?.[index] ?? null,
      ciHigh: metrics.drift_ci_high?.[index] ?? null,
      boilerplate: metrics.boilerplate_score?.[index] ?? null,
    }))
  }, [metrics])

  const selectedShiftPair = shifts?.yearPairs?.[0] ?? null
  const selectedExcerptPair = useMemo(() => {
    if (!excerpts?.pairs?.length) return null
    if (!selectedShiftPair) return excerpts.pairs[0]
    return (
      excerpts.pairs.find(
        (pair) => pair.from === selectedShiftPair.from && pair.to === selectedShiftPair.to
      ) ?? excerpts.pairs[0]
    )
  }, [excerpts, selectedShiftPair])

  const hasLowConfidence = filings.some(
    (filing) => filing.extraction && filing.extraction.confidence < 0.5
  )

  if (loading) {
    return (
      <main className="min-h-screen">
        <div className="mx-auto max-w-5xl px-6 py-16">
          <p className="text-sm opacity-70">{copy.global.loading.base}</p>
        </div>
      </main>
    )
  }

  if (error) {
    return (
      <main className="min-h-screen">
        <div className="mx-auto max-w-5xl px-6 py-16 space-y-4">
          <p className="text-sm opacity-80">{error}</p>
          <Link
            to="/"
            className="inline-flex items-center rounded-md border border-black/20 px-3 py-2 text-sm hover:bg-black/5"
          >
            {copy.nav.home}
          </Link>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen">
      <div className="mx-auto max-w-6xl px-6 py-12 space-y-10">
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-wider opacity-70">
            {copy.global.appName}
          </p>
          <h1 className="text-3xl font-semibold">
            {meta?.companyName ?? ticker}
            {meta?.ticker ? ` (${meta.ticker})` : ""}
          </h1>
          <p className="text-sm opacity-70">{copy.company.sectionValueMvp}</p>
        </header>

        <section className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-lg border border-black/10 p-4">
            <div className="text-xs uppercase tracking-wider opacity-70">
              {copy.company.labels.company}
            </div>
            <div className="mt-2 text-lg font-semibold">
              {meta?.companyName ?? ticker}
            </div>
          </div>
          <div className="rounded-lg border border-black/10 p-4">
            <div className="text-xs uppercase tracking-wider opacity-70">
              {copy.company.labels.section}
            </div>
            <div className="mt-2 text-sm">{copy.company.sectionValueMvp}</div>
          </div>
          <div className="rounded-lg border border-black/10 p-4">
            <div className="text-xs uppercase tracking-wider opacity-70">
              {copy.company.labels.years}
            </div>
            <div className="mt-2 text-sm">{yearRange}</div>
          </div>
        </section>

        <section className="space-y-3">
          <div>
            <h2 className="text-xl font-semibold">{copy.driftTimeline.title}</h2>
            <p className="text-sm opacity-70">{copy.driftTimeline.helper}</p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {driftRows.map((row) => (
              <div key={row.year} className="rounded-lg border border-black/10 p-3">
                <div className="text-sm font-semibold">{row.year}</div>
                {row.drift !== null && row.prevYear !== undefined && (
                  <div className="text-xs opacity-70">
                    {copy.driftTimeline.tooltip.driftLine({
                      prevYear: row.prevYear,
                      drift: formatNumber(row.drift),
                    })}
                  </div>
                )}
                {row.ciLow !== null && row.ciHigh !== null && (
                  <div className="text-xs opacity-70">
                    {copy.driftTimeline.tooltip.ciLine({
                      low: formatNumber(row.ciLow),
                      high: formatNumber(row.ciHigh),
                    })}
                  </div>
                )}
                {row.boilerplate !== null && (
                  <div className="text-xs opacity-70">
                    {copy.driftTimeline.tooltip.boilerplateLine({
                      boilerplatePct: formatNumber(row.boilerplate),
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>

        <section className="space-y-3">
          <div>
            <h2 className="text-xl font-semibold">{copy.heatmap.title}</h2>
            <p className="text-sm opacity-70">{copy.heatmap.helper}</p>
          </div>
          {similarity?.years?.length ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-xs">
                <thead>
                  <tr>
                    <th className="p-2 text-left" />
                    {similarity.years.map((year) => (
                      <th key={year} className="p-2 text-left">
                        {year}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {similarity.years.map((rowYear, rowIndex) => (
                    <tr key={rowYear}>
                      <td className="p-2 font-semibold">{rowYear}</td>
                      {similarity.years.map((colYear, colIndex) => (
                        <td key={`${rowYear}-${colYear}`} className="p-2">
                          {formatNumber(
                            similarity.cosineSimilarity?.[rowIndex]?.[colIndex]
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>

        <section className="space-y-3">
          <div>
            <h2 className="text-xl font-semibold">{copy.termShifts.title}</h2>
            <p className="text-sm opacity-70">{copy.termShifts.helper}</p>
          </div>
          {selectedShiftPair ? (
            <div className="space-y-4">
              <p className="text-sm opacity-80">{selectedShiftPair.summary}</p>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-lg border border-black/10 p-3">
                  <div className="text-sm font-semibold">
                    {copy.termShifts.risersLabel}
                  </div>
                  <ul className="mt-2 space-y-1 text-xs">
                    {selectedShiftPair.topRisers.map((item) => (
                      <li key={`riser-${item.term}`}>
                        {item.term} ({formatNumber(item.score)})
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="rounded-lg border border-black/10 p-3">
                  <div className="text-sm font-semibold">
                    {copy.termShifts.fallersLabel}
                  </div>
                  <ul className="mt-2 space-y-1 text-xs">
                    {selectedShiftPair.topFallers.map((item) => (
                      <li key={`faller-${item.term}`}>
                        {item.term} ({formatNumber(item.score)})
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm opacity-70">{copy.global.errors.noShifts}</p>
          )}
        </section>

        <section className="space-y-3">
          <div>
            <h2 className="text-xl font-semibold">{copy.comparePane.title}</h2>
            <p className="text-sm opacity-70">{copy.comparePane.helper}</p>
          </div>
          {hasLowConfidence ? (
            <p className="text-xs opacity-70">{copy.comparePane.warnLowConfidence}</p>
          ) : null}
          {excerptsError ? (
            <p className="text-sm opacity-70">{excerptsError}</p>
          ) : selectedExcerptPair ? (
            <div className="space-y-3">
              <div className="text-xs uppercase tracking-wider opacity-70">
                {copy.comparePane.pairLabel}
              </div>
              <div className="text-sm font-semibold">
                {selectedExcerptPair.from}-{selectedExcerptPair.to}
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                {selectedExcerptPair.representativeParagraphs.map((para, index) => (
                  <div
                    key={`${para.year}-${para.paragraphIndex}-${index}`}
                    className="rounded-lg border border-black/10 p-3"
                  >
                    <div className="text-xs uppercase tracking-wider opacity-70">
                      {para.year}
                    </div>
                    <p className="mt-2 text-sm leading-relaxed whitespace-pre-line">
                      {para.text}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm opacity-70">{copy.comparePane.emptyNoPair}</p>
          )}
        </section>
      </div>
    </main>
  )
}
