import { useEffect, useMemo, useState } from "react"
import { Link, useParams, useSearchParams } from "react-router-dom"
import LabPanel from "../components/LabPanel"
import PageMetadata from "../components/PageMetadata"
import { formatFiscalYearRange } from "../lib/fiscalYear"
import {
  findProtocolLabVisiblePilotEntry,
  loadProtocolLabVisiblePilotSystem,
  type ProtocolLabVisiblePilotEntry,
  type ProtocolLabVisiblePilotSystem,
} from "../lib/protocolLabProductPositioning"

const SHOWCASE_COMPANY_NAMES: Record<string, string> = {
  NVDA: "NVIDIA",
  LLY: "Eli Lilly and Company",
  KO: "Coca-Cola",
  WM: "Waste Management",
  GE: "General Electric",
}

const SHOWCASE_COMPANY_SECTORS: Record<string, string> = {
  NVDA: "Semiconductors / AI Infrastructure",
  LLY: "Pharmaceuticals / Cardiometabolic and Obesity",
  KO: "Consumer Staples / Beverages",
  WM: "Industrials / Waste Services",
  GE: "Industrials / Aerospace & Energy",
}

const SHOWCASE_COMPANY_TOP_CUE: Record<string, string> = {
  NVDA: "Read the filing answer first; use the protocol layer and audit below only to pressure-test it.",
  LLY: "Bounded case: take the filing answer first, use protocol meaning second, then stop at the explicit scope boundary.",
  KO: "Low drift is the point here: read the answer as selective sharpening, not forced novelty.",
  WM: "Read the filing answer first, then use the lower protocol and audit layers only as supporting checks.",
  GE: "Read the filing answer first, then use the lower protocol and audit layers only as supporting checks.",
}

type Pair = { from: number; to: number }

function formatPilotPairLabel(pilot: ProtocolLabVisiblePilotEntry): string {
  return `${formatFiscalYearRange(pilot.year_from, pilot.year_to)} Item 1A`
}

function parseYear(value: string | null): number | null {
  if (!value) return null
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return null
  return Math.trunc(parsed)
}

function normalizePair(fromYear: number | null, toYear: number | null): Pair | null {
  if (fromYear === null || toYear === null) return null
  if (fromYear === toYear) return null
  return fromYear < toYear
    ? { from: fromYear, to: toYear }
    : { from: toYear, to: fromYear }
}

function mergeSearchParams(
  current: URLSearchParams,
  updates: Record<string, string | null>
): URLSearchParams {
  const next = new URLSearchParams(current)
  for (const [key, value] of Object.entries(updates)) {
    if (value === null || value === undefined) {
      next.delete(key)
    } else {
      next.set(key, value)
    }
  }
  return next
}

export default function Company() {
  const { ticker: tickerParam } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const [visiblePilotSystem, setVisiblePilotSystem] = useState<ProtocolLabVisiblePilotSystem | null>(
    null
  )
  const fallbackTicker = "NVDA"
  const ticker = (tickerParam ?? fallbackTicker).toUpperCase()

  useEffect(() => {
    let cancelled = false

    loadProtocolLabVisiblePilotSystem()
      .then((result) => {
        if (cancelled) return
        setVisiblePilotSystem(result)
      })
      .catch(() => {
        if (cancelled) return
        setVisiblePilotSystem(null)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const requestedPair = useMemo(() => {
    const from = parseYear(searchParams.get("from"))
    const to = parseYear(searchParams.get("to"))
    return normalizePair(from, to)
  }, [searchParams])

  const requestedLlmCampaignA = searchParams.get("llmA")
  const requestedLlmCampaignB = searchParams.get("llmB")
  const visiblePilot = visiblePilotSystem ? findProtocolLabVisiblePilotEntry(visiblePilotSystem, ticker) : null

  useEffect(() => {
    const tab = searchParams.get("tab")
    const from = parseYear(searchParams.get("from"))
    const to = parseYear(searchParams.get("to"))
    const normalizedPair = normalizePair(from, to) ?? (
      visiblePilot
        ? { from: visiblePilot.year_from, to: visiblePilot.year_to }
        : null
    )
    const next = mergeSearchParams(searchParams, {
      tab: "lab",
      from: normalizedPair ? String(normalizedPair.from) : null,
      to: normalizedPair ? String(normalizedPair.to) : null,
    })
    if (tab === "lab" && next.toString() === searchParams.toString()) {
      return
    }
    setSearchParams(next, { replace: true })
  }, [searchParams, setSearchParams, visiblePilot])

  const displayName = visiblePilot?.company_name ?? SHOWCASE_COMPANY_NAMES[ticker] ?? ticker
  const activeCaseLabel = visiblePilot
    ? formatPilotPairLabel(visiblePilot)
    : requestedPair
      ? `${formatFiscalYearRange(requestedPair.from, requestedPair.to)} Item 1A`
      : "FY2024 to FY2025 Item 1A"
  const companyMetaDescription = `Document Protocol Lab pilot case for ${displayName}: start with the filing answer, then the protocol meaning, then the deeper audit only when you need it.`
  const inlineCue =
    SHOWCASE_COMPANY_TOP_CUE[ticker] ??
    "Read the filing answer first, then use the protocol layer and deeper audit only as secondary checks."

  const handleSelectedPairChange = (pair: Pair) => {
    const next = mergeSearchParams(searchParams, {
      tab: "lab",
      from: String(pair.from),
      to: String(pair.to),
    })
    if (next.toString() === searchParams.toString()) return
    setSearchParams(next, { replace: true })
  }

  const handleSelectedLlmCampaignsChange = (selection: { llmA: string; llmB: string }) => {
    const next = mergeSearchParams(searchParams, {
      llmA: selection.llmA,
      llmB: selection.llmB,
    })
    if (next.toString() === searchParams.toString()) return
    setSearchParams(next, { replace: true })
  }

  return (
    <main className="min-h-screen page-fade">
      <PageMetadata
        title={`${displayName} (${ticker}) | Document Protocol Lab`}
        description={companyMetaDescription}
      />
      <div className="mx-auto max-w-6xl space-y-8 px-6 py-10">
        <header className="space-y-4">
          <nav className="text-xs uppercase tracking-[0.24em] text-slate-300" aria-label="Breadcrumb">
            <ol className="flex flex-wrap items-center gap-2">
              <li>
                <Link to="/" className="hover:text-slate-100">
                  Home
                </Link>
              </li>
              <li aria-hidden="true" className="text-slate-500">/</li>
              <li>
                <Link to="/companies" className="hover:text-slate-100">
                  Cases
                </Link>
              </li>
              <li aria-hidden="true" className="text-slate-500">/</li>
              <li className="text-slate-100" aria-current="page">
                {ticker}
              </li>
            </ol>
          </nav>

          <section className="rounded-[1.45rem] border border-white/10 bg-linear-to-br from-slate-950/80 via-slate-900/58 to-slate-950/40 p-5 shadow-[0_22px_56px_rgba(2,6,23,0.35)]">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-3">
                <p className="text-xs uppercase tracking-[0.28em] text-sky-100">Current pilot case</p>
                <h1 className="text-3xl font-semibold text-slate-50 sm:text-4xl">
                  {displayName} ({ticker})
                </h1>
                {SHOWCASE_COMPANY_SECTORS[ticker] ? (
                  <p className="text-sm font-medium text-slate-400">{SHOWCASE_COMPANY_SECTORS[ticker]}</p>
                ) : null}
              </div>
              <div className="flex flex-wrap gap-2">
                <Link
                  to="/companies"
                  className="inline-flex items-center rounded-full border border-white/20 px-3 py-1.5 text-xs text-slate-200 hover:border-white/40 hover:bg-white/5"
                >
                  Back to 3 fixtures
                </Link>
                <Link
                  to="/methodology"
                  className="inline-flex items-center rounded-full border border-white/20 px-3 py-1.5 text-xs text-slate-200 hover:border-white/40 hover:bg-white/5"
                >
                  Methodology
                </Link>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-200">
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                Fixture role: {visiblePilot?.role_label ?? "Visible pilot"}
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                Filing pair: {activeCaseLabel}
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
                Bounded SEC Item 1A pilot
              </span>
            </div>
            <p className="mt-4 max-w-4xl text-sm text-slate-300">{inlineCue}</p>
          </section>
        </header>

        <LabPanel
          ticker={ticker}
          requestedPair={requestedPair}
          onSelectedPairChange={handleSelectedPairChange}
          requestedLlmCampaignA={requestedLlmCampaignA}
          requestedLlmCampaignB={requestedLlmCampaignB}
          onSelectedLlmCampaignsChange={handleSelectedLlmCampaignsChange}
        />
      </div>
    </main>
  )
}
