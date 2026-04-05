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
import { getRouteFamilyConfig } from "../lib/routeFamilyUi"

const FALLBACK_COMPANY_NAMES: Record<string, string> = {
  WM: "Waste Management",
  GE: "General Electric",
}

const FALLBACK_COMPANY_SECTORS: Record<string, string> = {
  WM: "Industrials / Waste Services",
  GE: "Industrials / Aerospace & Energy",
}

const DEFAULT_TOP_CUE =
  "Read the filing answer first, then use the supporting read and lower audit only when you need more pressure."

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
  const familyConfig = getRouteFamilyConfig(ticker)

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

  const displayName = visiblePilot?.company_name ?? familyConfig?.companyName ?? FALLBACK_COMPANY_NAMES[ticker] ?? ticker
  const activeRoleLabel = familyConfig?.publicRoleLabel ?? visiblePilot?.role_label ?? "Public case"
  const activeCaseLabel = visiblePilot
    ? formatPilotPairLabel(visiblePilot)
    : requestedPair
      ? `${formatFiscalYearRange(requestedPair.from, requestedPair.to)} Item 1A`
      : "FY2024 to FY2025 Item 1A"
  const companyMetaDescription = `Document Protocol Lab public pilot case for ${displayName}: start with the filing answer, then the supporting read, then the deeper audit only when you need it.`
  const inlineCue = familyConfig?.topCue ?? DEFAULT_TOP_CUE
  const sectorLabel = familyConfig?.sector ?? FALLBACK_COMPANY_SECTORS[ticker] ?? null

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
      <div className="mx-auto max-w-6xl space-y-4 px-5 py-5 sm:space-y-5 sm:px-6 sm:py-6">
        <header className="space-y-2.5 sm:space-y-3">
          <nav
            className="text-[11px] uppercase tracking-[0.24em] text-slate-300 sm:text-xs"
            aria-label="Breadcrumb"
          >
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

          <section className="rounded-[1.35rem] border border-white/10 bg-linear-to-br from-slate-950/86 via-slate-900/60 to-slate-950/40 p-4 shadow-[0_18px_42px_rgba(2,6,23,0.3)] sm:p-4.5">
            <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start sm:gap-4">
              <div className="min-w-0 space-y-2.5">
                <div className="flex flex-wrap gap-1 text-[11px] text-slate-200 sm:text-xs">
                  <span className="rounded-full border border-sky-300/25 bg-sky-400/10 px-2 py-1">
                    Case
                  </span>
                  <span className="rounded-full border border-white/10 bg-white/5 px-2 py-1">
                    {activeRoleLabel}
                  </span>
                  <span className="rounded-full border border-white/8 bg-white/4 px-2 py-1 text-slate-300">
                    {activeCaseLabel}
                  </span>
                </div>
                <div className="space-y-1.5">
                  <h1 className="text-[clamp(1.7rem,3.6vw,3.05rem)] leading-tight font-semibold text-slate-50">
                    {displayName} <span className="text-slate-400">({ticker})</span>
                  </h1>
                  {sectorLabel ? (
                    <p className="text-[13px] font-medium text-slate-400 sm:text-sm">{sectorLabel}</p>
                  ) : null}
                </div>
                <p className="max-w-3xl text-sm leading-6 text-slate-300">
                  {inlineCue}
                </p>
              </div>
              <div className="flex flex-wrap gap-1.5 sm:justify-end sm:gap-2 sm:pt-1">
                <Link
                  to="/companies"
                  className="inline-flex items-center rounded-full border border-white/20 px-2.5 py-1 text-[11px] text-slate-200 hover:border-white/40 hover:bg-white/5 sm:px-3 sm:py-1.5 sm:text-xs"
                >
                  Back to 3 cases
                </Link>
                <Link
                  to="/methodology"
                  className="inline-flex items-center rounded-full border border-white/20 px-2.5 py-1 text-[11px] text-slate-200 hover:border-white/40 hover:bg-white/5 sm:px-3 sm:py-1.5 sm:text-xs"
                >
                  Methodology
                </Link>
              </div>
            </div>
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
