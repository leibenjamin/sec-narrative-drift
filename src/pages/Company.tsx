import { useEffect, useMemo, useState } from "react"
import type { ReactNode } from "react"
import { Link, useParams } from "react-router-dom"
import DriftTimeline from "../components/DriftTimeline"
import SimilarityHeatmap from "../components/SimilarityHeatmap"
import TermShiftBars from "../components/TermShiftBars"
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
  const [selectedPair, setSelectedPair] = useState<{ from: number; to: number } | null>(
    null
  )
  const [selectedTerm, setSelectedTerm] = useState<string | null>(null)

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
      setSelectedPair(null)
      setSelectedTerm(null)

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
        if (shiftsData.yearPairs?.length) {
          const firstPair = shiftsData.yearPairs[0]
          setSelectedPair({ from: firstPair.from, to: firstPair.to })
          setSelectedTerm(null)
        } else if (similarityData.years.length >= 2) {
          const lastIndex = similarityData.years.length - 1
          setSelectedPair({
            from: similarityData.years[lastIndex - 1],
            to: similarityData.years[lastIndex],
          })
          setSelectedTerm(null)
        }
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

  const selectedShiftPair = useMemo(() => {
    if (!shifts?.yearPairs?.length) return null
    if (!selectedPair) return shifts.yearPairs[0]
    return (
      shifts.yearPairs.find(
        (pair) => pair.from === selectedPair.from && pair.to === selectedPair.to
      ) ?? shifts.yearPairs[0]
    )
  }, [shifts, selectedPair])

  const selectedExcerptPair = useMemo(() => {
    if (!excerpts?.pairs?.length) return null
    if (!selectedPair) return excerpts.pairs[0]
    return (
      excerpts.pairs.find(
        (pair) => pair.from === selectedPair.from && pair.to === selectedPair.to
      ) ?? excerpts.pairs[0]
    )
  }, [excerpts, selectedPair])

  function handleSelectPair(fromYear: number, toYear: number) {
    const ordered =
      fromYear <= toYear ? { from: fromYear, to: toYear } : { from: toYear, to: fromYear }
    setSelectedPair(ordered)
    setSelectedTerm(null)
  }

  function escapeRegExp(value: string): string {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  }

  function highlightSelectedTerm(text: string, term: string | null) {
    if (!term) return text
    const trimmed = term.trim()
    if (!trimmed) return text
    const regex = new RegExp(`\\b${escapeRegExp(trimmed)}\\b`, "gi")
    const matches = Array.from(text.matchAll(regex))
    if (matches.length === 0) return text

    const nodes: ReactNode[] = []
    let lastIndex = 0

    matches.forEach((match, index) => {
      const start = match.index ?? 0
      if (start > lastIndex) {
        nodes.push(text.slice(lastIndex, start))
      }
      const matchText = match[0]
      nodes.push(
        <mark key={`${start}-${index}`} className="rounded bg-yellow-200 px-0.5">
          {matchText}
        </mark>
      )
      lastIndex = start + matchText.length
    })

    if (lastIndex < text.length) {
      nodes.push(text.slice(lastIndex))
    }

    return nodes
  }

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
          <DriftTimeline
            years={metrics?.years ?? []}
            drift_vs_prev={metrics?.drift_vs_prev ?? []}
            drift_ci_low={metrics?.drift_ci_low}
            drift_ci_high={metrics?.drift_ci_high}
            boilerplate_score={metrics?.boilerplate_score}
          />
        </section>

        <section className="space-y-3">
          <div>
            <h2 className="text-xl font-semibold">{copy.heatmap.title}</h2>
            <p className="text-sm opacity-70">{copy.heatmap.helper}</p>
          </div>
          {similarity?.years?.length ? (
            <SimilarityHeatmap
              years={similarity.years}
              cosineSimilarity={similarity.cosineSimilarity ?? []}
              onSelectPair={handleSelectPair}
            />
          ) : null}
        </section>

        <section className="space-y-3">
          <div>
            <h2 className="text-xl font-semibold">{copy.termShifts.title}</h2>
            <p className="text-sm opacity-70">{copy.termShifts.helper}</p>
          </div>
          {selectedShiftPair?.summary ? (
            <p className="text-sm opacity-80">{selectedShiftPair.summary}</p>
          ) : null}
          <TermShiftBars
            selectedPair={selectedShiftPair ? { from: selectedShiftPair.from, to: selectedShiftPair.to } : null}
            topRisers={selectedShiftPair?.topRisers ?? []}
            topFallers={selectedShiftPair?.topFallers ?? []}
            onClickTerm={(term) => setSelectedTerm(term)}
          />
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
                      {highlightSelectedTerm(para.text, selectedTerm)}
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
