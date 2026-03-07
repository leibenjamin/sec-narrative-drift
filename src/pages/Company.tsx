import { useEffect, useMemo } from "react"
import { Link, useParams, useSearchParams } from "react-router-dom"
import LabPanel from "../components/LabPanel"
import { listLabShowcaseTickers } from "../lib/labData"

const SHOWCASE_COMPANY_NAMES: Record<string, string> = {
  NVDA: "NVIDIA",
  KO: "Coca-Cola",
  WM: "Waste Management",
  GE: "General Electric",
}

const SHOWCASE_COMPANY_SECTORS: Record<string, string> = {
  NVDA: "Semiconductors / AI Infrastructure",
  KO: "Consumer Staples / Beverages",
  WM: "Industrials / Waste Services",
  GE: "Industrials / Aerospace & Energy",
}

const SHOWCASE_COMPANY_CONTEXT: Record<string, string> = {
  NVDA: "As the dominant GPU supplier for AI training, NVIDIA's risk disclosures track the rapid evolution of export controls, supply concentration, and demand cyclicality in the AI hardware market.",
  KO: "As a global defensive stock with 200+ markets, Coca-Cola's risk disclosures track currency exposure, regulatory shifts in sugar taxation, supply chain resilience, and the ongoing portfolio pivot toward non-carbonated beverages.",
  WM: "As the largest US waste hauler, Waste Management's risk disclosures track environmental regulation, landfill capacity, and the economics of recycling and sustainability mandates.",
  GE: "Following its three-way split, GE Aerospace's risk disclosures track defense procurement cycles, supply chain constraints, and the transition to next-generation engine programs.",
}

type Pair = { from: number; to: number }

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
  const fallbackTicker = listLabShowcaseTickers()[0] ?? "NVDA"
  const ticker = (tickerParam ?? fallbackTicker).toUpperCase()

  const requestedPair = useMemo(() => {
    const from = parseYear(searchParams.get("from"))
    const to = parseYear(searchParams.get("to"))
    return normalizePair(from, to)
  }, [searchParams])

  const requestedLlmCampaignA = searchParams.get("llmA")
  const requestedLlmCampaignB = searchParams.get("llmB")

  useEffect(() => {
    const tab = searchParams.get("tab")
    const from = parseYear(searchParams.get("from"))
    const to = parseYear(searchParams.get("to"))
    const normalizedPair = normalizePair(from, to)
    const next = mergeSearchParams(searchParams, {
      tab: "lab",
      from: normalizedPair ? String(normalizedPair.from) : null,
      to: normalizedPair ? String(normalizedPair.to) : null,
    })
    if (tab === "lab" && next.toString() === searchParams.toString()) {
      return
    }
    setSearchParams(next, { replace: true })
  }, [searchParams, setSearchParams])

  const displayName = SHOWCASE_COMPANY_NAMES[ticker] ?? ticker

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
      <div className="mx-auto max-w-6xl space-y-8 px-6 py-10">
        <header className="space-y-4">
          <nav
            className="text-xs uppercase tracking-wider text-slate-300"
            aria-label="Breadcrumb"
          >
            <ol className="flex flex-wrap items-center gap-2">
              <li>
                <Link to="/" className="hover:text-slate-100">
                  Home
                </Link>
              </li>
              <li aria-hidden="true" className="text-slate-500">
                /
              </li>
              <li>
                <Link to="/companies" className="hover:text-slate-100">
                  Showcase
                </Link>
              </li>
              <li aria-hidden="true" className="text-slate-500">
                /
              </li>
              <li className="text-slate-100" aria-current="page">
                {ticker}
              </li>
            </ol>
          </nav>

          <div className="space-y-2">
            <h1 className="text-3xl font-semibold">
              {displayName} ({ticker})
            </h1>
            {SHOWCASE_COMPANY_SECTORS[ticker] ? (
              <p className="text-sm font-medium text-slate-400">
                {SHOWCASE_COMPANY_SECTORS[ticker]}
              </p>
            ) : null}
            <p className="max-w-3xl text-sm text-slate-300">
              Year-over-year analysis of {displayName}'s 10-K risk disclosures (Item 1A) — surfacing
              which risk themes intensified, which faded, and where the narrative shifted between
              adjacent filing years.
            </p>
            {SHOWCASE_COMPANY_CONTEXT[ticker] ? (
              <p className="max-w-3xl text-sm text-slate-400">
                {SHOWCASE_COMPANY_CONTEXT[ticker]}
              </p>
            ) : null}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Link
              to="/companies"
              className="inline-flex items-center rounded-md border border-white/20 px-3 py-2 text-sm text-slate-200 hover:border-white/40 hover:bg-white/5"
            >
              Browse showcase
            </Link>
            <Link
              to="/methodology"
              className="inline-flex items-center rounded-md border border-white/20 px-3 py-2 text-sm text-slate-200 hover:border-white/40 hover:bg-white/5"
            >
              Methodology
            </Link>
          </div>

          <div className="grid gap-3 rounded-xl border border-white/10 bg-slate-900/45 p-4 md:grid-cols-3">
            <div className="rounded-md border border-sky-300/25 bg-sky-400/10 p-3">
              <div className="text-xs uppercase tracking-wide text-sky-100">Risk narrative drift</div>
              <p className="mt-1 text-sm text-slate-100">
                Identifies which risk themes {displayName} added, removed, intensified, or softened compared
                to the prior year's filing — using both statistical detectors and LLM-based analysis.
              </p>
            </div>
            <div className="rounded-md border border-white/10 bg-slate-950/35 p-3">
              <div className="text-xs uppercase tracking-wide text-slate-300">Why this matters</div>
              <p className="mt-1 text-sm text-slate-200">
                Changes in risk language often precede strategic shifts, regulatory responses, or emerging
                exposures. Comparing across methods separates real narrative change from boilerplate churn.
              </p>
            </div>
            <div className="rounded-md border border-emerald-300/20 bg-emerald-400/10 p-3">
              <div className="text-xs uppercase tracking-wide text-emerald-100">
                How to read results
              </div>
              <p className="mt-1 text-sm text-slate-100">
                Each method card shows a drift score, confidence band, and supporting evidence excerpts.
                The Insight Lens at the top provides an executive summary. Use the agreement matrix
                to see where methods converge or diverge.
              </p>
            </div>
          </div>
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
