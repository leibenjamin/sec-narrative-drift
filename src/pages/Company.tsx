import { useEffect, useMemo, useRef, useState } from "react"
import { Link, useParams } from "react-router-dom"
import ComparePane from "../components/ComparePane"
import DataProvenanceDrawer from "../components/DataProvenanceDrawer"
import DriftTimeline from "../components/DriftTimeline"
import ExecBriefCard, { type ExecBriefData } from "../components/ExecBriefCard"
import SimilarityHeatmap from "../components/SimilarityHeatmap"
import TermShiftBars from "../components/TermShiftBars"
import Tour from "../components/Tour"
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
import { exportExecBriefPng } from "../lib/exportPng"
import { assertSafeExternalUrl } from "../lib/sanitize"
import type { Excerpts, FilingRow, Meta, Metrics, ShiftPairs, SimilarityMatrix } from "../lib/types"

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
  const [isTourOpen, setIsTourOpen] = useState(false)
  const execBriefRef = useRef<SVGSVGElement | null>(null)

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
      setIsTourOpen(false)

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

  function handleSelectPair(fromYear: number, toYear: number) {
    const ordered =
      fromYear <= toYear ? { from: fromYear, to: toYear } : { from: toYear, to: fromYear }
    setSelectedPair(ordered)
    setSelectedTerm(null)
  }

  const highlightTerms = useMemo(() => {
    if (selectedTerm) return [selectedTerm]
    if (!selectedShiftPair) return []
    const risers = selectedShiftPair.topRisers.slice(0, 15).map((item) => item.term)
    const fallers = selectedShiftPair.topFallers.slice(0, 15).map((item) => item.term)
    return Array.from(new Set([...risers, ...fallers]))
  }, [selectedTerm, selectedShiftPair])

  const hasLowConfidence = filings.some(
    (filing) => filing.extraction && filing.extraction.confidence < 0.5
  )

  const callouts = useMemo(() => {
    const years = metrics?.years ?? []
    const drift = metrics?.drift_vs_prev ?? []
    const boilerplate = metrics?.boilerplate_score ?? []

    const driftEntries = years
      .map((year, index) => ({ year, value: drift[index] ?? null }))
      .filter((entry): entry is { year: number; value: number } => entry.value !== null)

    const boilerplateEntries = years
      .map((year, index) => ({ year, value: boilerplate[index] ?? null }))
      .filter((entry): entry is { year: number; value: number } => entry.value !== null)

    const largestDrift = driftEntries.reduce(
      (acc, entry) => (entry.value > acc.value ? entry : acc),
      driftEntries[0] ?? { year: 0, value: -Infinity }
    )
    const mostStable = driftEntries.reduce(
      (acc, entry) => (entry.value < acc.value ? entry : acc),
      driftEntries[0] ?? { year: 0, value: Infinity }
    )
    const mostTemplated = boilerplateEntries.reduce(
      (acc, entry) => (entry.value > acc.value ? entry : acc),
      boilerplateEntries[0] ?? { year: 0, value: -Infinity }
    )

    return {
      largestDrift: driftEntries.length ? largestDrift.year : null,
      mostStable: driftEntries.length ? mostStable.year : null,
      mostTemplated: boilerplateEntries.length ? mostTemplated.year : null,
    }
  }, [metrics])

  const execBriefData = useMemo<ExecBriefData>(() => {
    const companyName = meta?.companyName ?? ticker
    const years = metrics?.years ?? []
    const startYear = years[0] ?? null
    const endYear = years[years.length - 1] ?? null
    const driftValues = metrics?.drift_vs_prev ?? []

    let maxIndex = -1
    let maxValue = -Infinity
    driftValues.forEach((value, index) => {
      if (value === null || value === undefined) return
      if (value > maxValue) {
        maxValue = value
        maxIndex = index
      }
    })

    const largestDriftYear = maxIndex >= 0 ? years[maxIndex] : null
    const prevYear = maxIndex > 0 ? years[maxIndex - 1] : null
    const matchedPair =
      shifts?.yearPairs?.find(
        (pair) => pair.from === prevYear && pair.to === largestDriftYear
      ) ?? shifts?.yearPairs?.[0] ?? null

    const summary = matchedPair?.summary ?? ""

    const topRisers = matchedPair?.topRisers?.map((item) => item.term) ?? []
    const topFallers = matchedPair?.topFallers?.map((item) => item.term) ?? []
    const filingDates = filings
      .map((filing) => filing.filingDate)
      .filter((date) => Boolean(date))
    const filingDatesText = filingDates.length > 0 ? filingDates.join(", ") : ""
    const provenanceLine = filingDatesText
      ? `${copy.global.sourceLine} ${filingDatesText}`
      : copy.global.sourceLine

    return {
      companyName,
      ticker,
      startYear,
      endYear,
      largestDriftYear,
      prevYear,
      summary,
      topRisers,
      topFallers,
      driftValues,
      provenanceLine,
    }
  }, [meta, ticker, metrics, shifts, filings])

  const execBriefFilename = useMemo(() => {
    const start = execBriefData.startYear ?? "na"
    const end = execBriefData.endYear ?? "na"
    return `sec-narrative-drift-${ticker}-${start}-${end}.png`
  }, [execBriefData, ticker])

  function handleExportExecBrief() {
    if (!execBriefRef.current) return
    void exportExecBriefPng(execBriefRef.current, execBriefFilename)
  }

  const tourSteps = useMemo(
    () => [
      {
        targetId: "tour-drift",
        title: copy.driftTimeline.title,
        body: copy.tour.steps.drift,
      },
      {
        targetId: "tour-heatmap",
        title: copy.heatmap.title,
        body: copy.tour.steps.heatmap,
      },
      {
        targetId: "tour-shifts",
        title: copy.termShifts.title,
        body: copy.tour.steps.shifts,
      },
      {
        targetId: "tour-compare",
        title: copy.comparePane.title,
        body: copy.tour.steps.compare,
      },
    ],
    []
  )

  const secLinks = useMemo(() => {
    if (!selectedPair) return []
    const years = [selectedPair.from, selectedPair.to]
    return years
      .map((year) => {
        const filing = filings.find((item) => item.year === year)
        if (!filing?.secUrl) return null
        try {
          return { year, url: assertSafeExternalUrl(filing.secUrl) }
        } catch {
          return null
        }
      })
      .filter((link): link is { year: number; url: string } => Boolean(link))
  }, [selectedPair, filings])

  if (loading) {
    return (
      <main className="min-h-screen">
        <div className="mx-auto max-w-5xl px-6 py-16">
          <p className="text-sm text-slate-300">{copy.global.loading.base}</p>
        </div>
      </main>
    )
  }

  if (error) {
    return (
      <main className="min-h-screen">
        <div className="mx-auto max-w-5xl px-6 py-16 space-y-4">
          <p className="text-sm text-slate-200">{error}</p>
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
          <p className="text-xs uppercase tracking-wider text-slate-300">
            {copy.global.appName}
          </p>
          <h1 className="text-3xl font-semibold">
            {meta?.companyName ?? ticker}
            {meta?.ticker ? ` (${meta.ticker})` : ""}
          </h1>
          <p className="text-sm text-slate-300">{copy.company.sectionValueMvp}</p>
        </header>

        <div className="flex flex-wrap items-center gap-3">
          <Link
            to="/methodology"
            className="inline-flex items-center rounded-md border border-black/20 px-3 py-2 text-sm hover:bg-black/5"
          >
            {copy.company.topButtons.methodology}
          </Link>
          <button
            type="button"
            className="inline-flex items-center rounded-md border border-black/20 px-3 py-2 text-sm hover:bg-black/5"
            onClick={() => setIsTourOpen((prev) => !prev)}
          >
            {copy.company.topButtons.startTour}
          </button>
          <button
            type="button"
            className="inline-flex items-center rounded-md border border-black/20 px-3 py-2 text-sm hover:bg-black/5"
            onClick={handleExportExecBrief}
          >
            {copy.company.topButtons.exportExecBrief}
          </button>
          <DataProvenanceDrawer />
        </div>

        <section className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-lg border border-black/10 p-4">
            <div className="text-xs uppercase tracking-wider text-slate-300">
              {copy.company.labels.company}
            </div>
            <div className="mt-2 text-lg font-semibold">
              {meta?.companyName ?? ticker}
            </div>
          </div>
          <div className="rounded-lg border border-black/10 p-4">
            <div className="text-xs uppercase tracking-wider text-slate-300">
              {copy.company.labels.section}
            </div>
            <div className="mt-2 text-sm">{copy.company.sectionValueMvp}</div>
          </div>
          <div className="rounded-lg border border-black/10 p-4">
            <div className="text-xs uppercase tracking-wider text-slate-300">
              {copy.company.labels.years}
            </div>
            <div className="mt-2 text-sm">{yearRange}</div>
          </div>
        </section>

        <section className="space-y-3" id="tour-drift">
          <div>
            <h2 className="text-xl font-semibold">{copy.driftTimeline.title}</h2>
            <p className="text-sm text-slate-300">{copy.driftTimeline.helper}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <div
              className="rounded-full border border-black/10 px-3 py-1 text-xs"
              title={copy.company.callouts.largestDrift.tooltip}
            >
              <span className="font-medium">{copy.company.callouts.largestDrift.label}</span>
              <span className="ml-2">{callouts.largestDrift ?? "-"}</span>
            </div>
            <div
              className="rounded-full border border-black/10 px-3 py-1 text-xs"
              title={copy.company.callouts.mostStable.tooltip}
            >
              <span className="font-medium">{copy.company.callouts.mostStable.label}</span>
              <span className="ml-2">{callouts.mostStable ?? "-"}</span>
            </div>
            <div
              className="rounded-full border border-black/10 px-3 py-1 text-xs"
              title={copy.company.callouts.highestBoilerplate.tooltip}
            >
              <span className="font-medium">
                {copy.company.callouts.highestBoilerplate.label}
              </span>
              <span className="ml-2">{callouts.mostTemplated ?? "-"}</span>
            </div>
          </div>
          <DriftTimeline
            years={metrics?.years ?? []}
            drift_vs_prev={metrics?.drift_vs_prev ?? []}
            drift_ci_low={metrics?.drift_ci_low}
            drift_ci_high={metrics?.drift_ci_high}
            boilerplate_score={metrics?.boilerplate_score}
          />
        </section>

        <section className="space-y-3" id="tour-heatmap">
          <div>
            <h2 className="text-xl font-semibold">{copy.heatmap.title}</h2>
            <p className="text-sm text-slate-300">{copy.heatmap.helper}</p>
          </div>
          {similarity?.years?.length ? (
            <SimilarityHeatmap
              years={similarity.years}
              cosineSimilarity={similarity.cosineSimilarity ?? []}
              onSelectPair={handleSelectPair}
            />
          ) : null}
        </section>

        <section className="space-y-3" id="tour-shifts">
          <div>
            <h2 className="text-xl font-semibold">{copy.termShifts.title}</h2>
            <p className="text-sm text-slate-300">{copy.termShifts.helper}</p>
          </div>
          {selectedShiftPair?.summary ? (
            <p className="text-sm text-slate-200">{selectedShiftPair.summary}</p>
          ) : null}
          <TermShiftBars
            selectedPair={selectedShiftPair ? { from: selectedShiftPair.from, to: selectedShiftPair.to } : null}
            topRisers={selectedShiftPair?.topRisers ?? []}
            topFallers={selectedShiftPair?.topFallers ?? []}
            onClickTerm={(term) => setSelectedTerm(term)}
          />
        </section>

        <div id="tour-compare">
          <ComparePane
            selectedPair={selectedPair}
            excerpts={excerpts}
            highlightTerms={highlightTerms}
            secLinks={secLinks}
            errorMessage={excerptsError}
            showLowConfidenceWarning={hasLowConfidence}
          />
        </div>
        <div aria-hidden="true" style={{ position: "absolute", left: "-9999px", top: 0 }}>
          <ExecBriefCard data={execBriefData} svgRef={execBriefRef} />
        </div>
      </div>
      <Tour isOpen={isTourOpen} steps={tourSteps} onClose={() => setIsTourOpen(false)} />
    </main>
  )
}
