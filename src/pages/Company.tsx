import { useEffect, useMemo, useRef, useState } from "react"
import { Link, useParams, useSearchParams } from "react-router-dom"
import ComparePane from "../components/ComparePane"
import DataProvenanceDrawer from "../components/DataProvenanceDrawer"
import DriftTimeline from "../components/DriftTimeline"
import ExecutiveSummary from "../components/ExecutiveSummary"
import ExecBriefCard, { type ExecBriefData } from "../components/ExecBriefCard"
import InlinePopover from "../components/InlinePopover"
import QualityBadge from "../components/QualityBadge"
import SectionCaptureBadge from "../components/SectionCaptureBadge"
import SelectedPairCallout from "../components/SelectedPairCallout"
import SimilarityHeatmap from "../components/SimilarityHeatmap"
import TermShiftBars, { type TermLens } from "../components/TermShiftBars"
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
  resolveDefaultPair,
} from "../lib/data"
import { exportExecBriefPng } from "../lib/exportPng"
import { assertSafeExternalUrl } from "../lib/sanitize"
import { getShiftTermIncludes, getShiftTermLabel } from "../lib/shiftTerms"
import type {
  ExcerptPair,
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

type ActiveCell = {
  row: number
  col: number
}

function getHeatmapCell(
  years: number[],
  fromYear: number,
  toYear: number
): ActiveCell | null {
  const rowIndex = years.indexOf(fromYear)
  const colIndex = years.indexOf(toYear)
  if (rowIndex < 0 || colIndex < 0) return null
  return { row: rowIndex, col: colIndex }
}

function buildPairKey(fromYear: number, toYear: number): string {
  return `${fromYear}-${toYear}`
}

function parseYearParam(value: string | null): number | null {
  if (!value) return null
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return null
  return Math.trunc(parsed)
}


export default function Company() {
  const params = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const fallbackTicker = listFeaturedTickers()[0] ?? "AAPL"
  const ticker = (params.ticker ?? fallbackTicker).toUpperCase()

  const [meta, setMeta] = useState<Meta | null>(null)
  const [filings, setFilings] = useState<FilingRow[]>([])
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [similarity, setSimilarity] = useState<SimilarityMatrix | null>(null)
  const [shifts, setShifts] = useState<ShiftPairs | null>(null)
  const [excerptPairs, setExcerptPairs] = useState<Record<string, ExcerptPair>>({})
  const [isExcerptsLoading, setIsExcerptsLoading] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [excerptsError, setExcerptsError] = useState<string | null>(null)
  const [selectedPair, setSelectedPair] = useState<{ from: number; to: number } | null>(
    null
  )
  const [activeCell, setActiveCell] = useState<ActiveCell | null>(null)
  const [selectedTerm, setSelectedTerm] = useState<{
    term: string
    includes?: string[]
  } | null>(null)
  const [termLens, setTermLens] = useState<TermLens>("primary")
  const [isDataQualityOpen, setIsDataQualityOpen] = useState(false)
  const [isTourOpen, setIsTourOpen] = useState(false)
  const [shouldScrollToEvidence, setShouldScrollToEvidence] = useState(false)
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
      setExcerptPairs({})
      setIsExcerptsLoading(false)
      setSelectedPair(null)
      setActiveCell(null)
      setSelectedTerm(null)
      setIsDataQualityOpen(false)
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
        let initialPair: { from: number; to: number } | null = null
        if (shiftsData.yearPairs?.length) {
          const firstPair = shiftsData.yearPairs[0]
          initialPair = { from: firstPair.from, to: firstPair.to }
        } else if (similarityData.years.length >= 2) {
          const lastIndex = similarityData.years.length - 1
          initialPair = {
            from: similarityData.years[lastIndex - 1],
            to: similarityData.years[lastIndex],
          }
        }

        if (initialPair) {
          setSelectedPair(initialPair)
          setSelectedTerm(null)
          setActiveCell(
            getHeatmapCell(similarityData.years, initialPair.from, initialPair.to)
          )
        }
        setLoading(false)
      } catch (err) {
        if (cancelled) return
        setError(getErrorMessage(err, copy.global.errors.missingDataset))
        setLoading(false)
        return
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

  const hasAltShiftLists = useMemo(() => {
    if (!selectedShiftPair) return false
    const altRisers = selectedShiftPair.topRisersAlt ?? []
    const altFallers = selectedShiftPair.topFallersAlt ?? []
    return altRisers.length > 0 || altFallers.length > 0
  }, [selectedShiftPair])

  useEffect(() => {
    if (!hasAltShiftLists && termLens !== "primary") {
      setTermLens("primary")
    }
  }, [hasAltShiftLists, termLens])

  useEffect(() => {
    if (!similarity) return
    const queryFrom = parseYearParam(searchParams.get("from"))
    const queryTo = parseYearParam(searchParams.get("to"))
    if (queryFrom === null || queryTo === null || queryFrom === queryTo) return

    const desired =
      queryFrom <= queryTo ? { from: queryFrom, to: queryTo } : { from: queryTo, to: queryFrom }
    const years = similarity.years ?? []
    const resolved = resolveDefaultPair(years, desired.from, desired.to)
    if (!resolved) return
    if (selectedPair && selectedPair.from === resolved.from && selectedPair.to === resolved.to) {
      return
    }

    if (resolved.from !== desired.from || resolved.to !== desired.to) {
      setSearchParams({ from: String(resolved.from), to: String(resolved.to) })
    }

    setSelectedPair(resolved)
    setSelectedTerm(null)
    setActiveCell(getHeatmapCell(years, resolved.from, resolved.to))
    setShouldScrollToEvidence(true)
  }, [searchParams, selectedPair, setSearchParams, similarity])

  useEffect(() => {
    if (!shouldScrollToEvidence || !selectedPair) return
    const target = document.getElementById("evidence")
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "start" })
    }
    setShouldScrollToEvidence(false)
  }, [shouldScrollToEvidence, selectedPair])

  const activeShiftLists = useMemo(() => {
    if (!selectedShiftPair) {
      return { risers: [], fallers: [], summary: "" }
    }
    if (termLens === "alt" && hasAltShiftLists) {
      return {
        risers: selectedShiftPair.topRisersAlt ?? [],
        fallers: selectedShiftPair.topFallersAlt ?? [],
        summary: selectedShiftPair.summaryAlt ?? selectedShiftPair.summary,
      }
    }
    return {
      risers: selectedShiftPair.topRisers,
      fallers: selectedShiftPair.topFallers,
      summary: selectedShiftPair.summary,
    }
  }, [hasAltShiftLists, selectedShiftPair, termLens])

  function handleSelectPair(fromYear: number, toYear: number) {
    const ordered =
      fromYear <= toYear ? { from: fromYear, to: toYear } : { from: toYear, to: fromYear }
    setSelectedPair(ordered)
    setSelectedTerm(null)
    setActiveCell(getHeatmapCell(similarity?.years ?? [], ordered.from, ordered.to))
    setSearchParams({ from: String(ordered.from), to: String(ordered.to) })
  }

  const highlightTerms = useMemo(() => {
    const terms: string[] = []
    const pushTerm = (value: string) => {
      if (value) {
        terms.push(value)
      }
    }
    const pushIncludes = (includes?: string[]) => {
      if (!includes) return
      includes.forEach((entry) => {
        if (entry) {
          terms.push(entry)
        }
      })
    }

    if (selectedTerm) {
      pushTerm(selectedTerm.term)
      pushIncludes(selectedTerm.includes)
      return Array.from(new Set(terms))
    }

    if (!selectedShiftPair) return []

    for (const item of activeShiftLists.risers.slice(0, 15)) {
      pushTerm(getShiftTermLabel(item))
      pushIncludes(getShiftTermIncludes(item))
    }
    for (const item of activeShiftLists.fallers.slice(0, 15)) {
      pushTerm(getShiftTermLabel(item))
      pushIncludes(getShiftTermIncludes(item))
    }
    return Array.from(new Set(terms))
  }, [activeShiftLists, selectedShiftPair, selectedTerm])

  const selectedExcerptPair = useMemo(() => {
    if (!selectedPair) return null
    const key = buildPairKey(selectedPair.from, selectedPair.to)
    return excerptPairs[key] ?? null
  }, [excerptPairs, selectedPair])

  useEffect(() => {
    if (!selectedPair) return
    const key = buildPairKey(selectedPair.from, selectedPair.to)
    if (excerptPairs[key]) {
      setExcerptsError(null)
      return
    }

    let cancelled = false

    async function loadPair() {
      setIsExcerptsLoading(true)
      setExcerptsError(null)
      try {
        const excerptsData = await loadExcerpts(ticker)
        if (cancelled) return
        const nextPairs: Record<string, ExcerptPair> = {}
        for (const pair of excerptsData.pairs) {
          nextPairs[buildPairKey(pair.from, pair.to)] = pair
        }
        setExcerptPairs((prev) => ({ ...prev, ...nextPairs }))
        if (!nextPairs[key]) {
          setExcerptsError(copy.global.errors.missingExcerpts)
        }
      } catch (err) {
        if (cancelled) return
        setExcerptsError(getErrorMessage(err, copy.global.errors.missingExcerpts))
      } finally {
        if (!cancelled) {
          setIsExcerptsLoading(false)
        }
      }
    }

    loadPair()

    return () => {
      cancelled = true
    }
  }, [excerptPairs, selectedPair, ticker])

  const hasLowConfidence = filings.some(
    (filing) => filing.extraction && filing.extraction.confidence < 0.5
  )

  const dataQualityLevel = useMemo<"high" | "medium" | "low" | "unknown">(() => {
    const confidences: number[] = []
    for (const filing of filings) {
      const confidence = filing.extraction?.confidence
      if (typeof confidence === "number") {
        confidences.push(confidence)
      }
    }
    if (confidences.length === 0) return "unknown"
    const sorted = [...confidences].sort((a, b) => a - b)
    const mid = Math.floor(sorted.length / 2)
    const median =
      sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid]
    if (median >= 0.85) return "high"
    if (median >= 0.65) return "medium"
    return "low"
  }, [filings])

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
    const largestDriftValue = maxIndex >= 0 && Number.isFinite(maxValue) ? maxValue : null
    const ciLowRaw = maxIndex >= 0 ? metrics?.drift_ci_low?.[maxIndex] : null
    const ciHighRaw = maxIndex >= 0 ? metrics?.drift_ci_high?.[maxIndex] : null
    const largestDriftCiLow = typeof ciLowRaw === "number" ? ciLowRaw : null
    const largestDriftCiHigh = typeof ciHighRaw === "number" ? ciHighRaw : null
    const matchedPair =
      shifts?.yearPairs?.find(
        (pair) => pair.from === prevYear && pair.to === largestDriftYear
      ) ?? shifts?.yearPairs?.[0] ?? null

    const summary = matchedPair?.summary ?? ""

    const topRisers = matchedPair?.topRisers?.map((item) => getShiftTermLabel(item)) ?? []
    const topFallers = matchedPair?.topFallers?.map((item) => getShiftTermLabel(item)) ?? []
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
      largestDriftValue,
      largestDriftCiLow,
      largestDriftCiHigh,
      summary,
      topRisers,
      topFallers,
      driftValues,
      provenanceLine,
      dataQualityLevel,
    }
  }, [meta, ticker, metrics, shifts, filings, dataQualityLevel])

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

  const selectedToSecUrl = useMemo(() => {
    if (!selectedPair) return null
    const match = secLinks.find((link) => link.year === selectedPair.to)
    return match?.url ?? null
  }, [secLinks, selectedPair])

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
          <nav
            className="text-xs uppercase tracking-wider text-slate-300"
            aria-label="Breadcrumb"
          >
            <ol className="flex flex-wrap items-center gap-2">
              <li>
                <Link to="/" className="hover:text-slate-100">
                  {copy.nav.home}
                </Link>
              </li>
              <li aria-hidden="true" className="text-slate-500">
                /
              </li>
              <li>
                <Link to="/companies" className="hover:text-slate-100">
                  {copy.nav.companies}
                </Link>
              </li>
              <li aria-hidden="true" className="text-slate-500">
                /
              </li>
              <li className="text-slate-100" aria-current="page">
                {meta?.ticker ?? ticker}
              </li>
            </ol>
          </nav>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-semibold">
              {meta?.companyName ?? ticker}
              {meta?.ticker ? ` (${meta.ticker})` : ""}
            </h1>
            <QualityBadge
              level={dataQualityLevel}
              onClick={() => setIsDataQualityOpen(true)}
            />
            <SectionCaptureBadge confidence={meta?.extraction?.confidence} />
          </div>
          <p className="text-sm text-slate-300">{copy.company.sectionValueMvp}</p>
        </header>

        <div className="flex flex-wrap items-center gap-3">
          <Link
            to="/companies"
            className="inline-flex items-center rounded-md border border-black/20 px-3 py-2 text-sm hover:bg-black/5"
          >
            {copy.company.topButtons.allCompanies}
          </Link>
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
          <DataProvenanceDrawer
            isOpen={isDataQualityOpen}
            onOpenChange={setIsDataQualityOpen}
          />
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

        <ExecutiveSummary
          metrics={metrics}
          shifts={shifts}
          onJumpToPair={handleSelectPair}
        />

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
              activeCell={activeCell}
            />
          ) : null}
        </section>

        <section className="space-y-3" id="tour-shifts">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-semibold">{copy.terms.header}</h2>
              <InlinePopover
                label={<span aria-hidden="true">?</span>}
                ariaLabel={copy.terms.whyGroupTitle}
                triggerClassName="flex h-5 w-5 items-center justify-center rounded-full border border-slate-300 text-[10px] text-slate-500 hover:text-slate-700"
                content={
                  <div className="space-y-2 text-xs text-slate-700">
                    <div className="font-semibold text-slate-900">
                      {copy.terms.whyGroupTitle}
                    </div>
                    <p>{copy.terms.whyGroupBody1}</p>
                    <p>{copy.terms.whyGroupBody2}</p>
                  </div>
                }
              />
            </div>
            <p className="text-xs text-slate-400">{copy.terms.subnote}</p>
            <p className="text-sm text-slate-300">{copy.termShifts.helper}</p>
          </div>
          <SelectedPairCallout
            selectedPair={selectedPair}
            metrics={metrics}
            secUrl={selectedToSecUrl}
            evidenceAnchorId="evidence"
          />
          {activeShiftLists.summary ? (
            <p className="text-sm text-slate-200">{activeShiftLists.summary}</p>
          ) : null}
          <TermShiftBars
            selectedPair={
              selectedShiftPair ? { from: selectedShiftPair.from, to: selectedShiftPair.to } : null
            }
            topRisers={activeShiftLists.risers}
            topFallers={activeShiftLists.fallers}
            lens={termLens}
            hasAlt={hasAltShiftLists}
            onLensChange={setTermLens}
            onClickTerm={(term, includes) => setSelectedTerm({ term, includes })}
          />
        </section>

        <div id="tour-compare">
          <div id="evidence">
            <ComparePane
              excerptPair={selectedExcerptPair}
              highlightTerms={highlightTerms}
              secLinks={secLinks}
              errorMessage={excerptsError}
              isLoading={isExcerptsLoading}
              showLowConfidenceWarning={hasLowConfidence}
            />
          </div>
        </div>
        <div aria-hidden="true" style={{ position: "absolute", left: "-9999px", top: 0 }}>
          <ExecBriefCard data={execBriefData} svgRef={execBriefRef} />
        </div>
      </div>
      <Tour isOpen={isTourOpen} steps={tourSteps} onClose={() => setIsTourOpen(false)} />
    </main>
  )
}
