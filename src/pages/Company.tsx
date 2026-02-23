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
            <p className="max-w-3xl text-sm text-slate-300">
              SEC Narrative Drift Lab compares adjacent 10-K Item 1A risk-factor years with
              deterministic detectors, then layers optional precomputed LLM sidecars for transparent
              model-to-model comparison.
            </p>
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
              <div className="text-xs uppercase tracking-wide text-sky-100">What changed</div>
              <p className="mt-1 text-sm text-slate-100">
                Compare adjacent years to see which risk themes intensified, faded, or stayed stable.
              </p>
            </div>
            <div className="rounded-md border border-white/10 bg-slate-950/35 p-3">
              <div className="text-xs uppercase tracking-wide text-slate-300">Why this matters</div>
              <p className="mt-1 text-sm text-slate-200">
                The same detectors and case controls make it easy to contrast company narratives and model choices side by side.
              </p>
            </div>
            <div className="rounded-md border border-emerald-300/20 bg-emerald-400/10 p-3">
              <div className="text-xs uppercase tracking-wide text-emerald-100">
                How to read confidence
              </div>
              <p className="mt-1 text-sm text-slate-100">
                Confidence bands are heuristic tri-level signals (0.25/0.50/0.75) supported by deterministic baselines, explicit evidence, provenance, and path-level debug states.
              </p>
            </div>
          </div>
          <p className="text-sm text-slate-300">
            Deterministic baseline + dual-model A/B compare + path-level reproducibility in one
            flow.
          </p>
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
