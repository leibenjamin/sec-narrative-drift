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
              deterministic detectors, then layers in optional precomputed LLM sidecars for
              transparent model-to-model comparison.
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
        </header>

        <LabPanel
          ticker={ticker}
          requestedPair={requestedPair}
          onSelectedPairChange={handleSelectedPairChange}
        />
      </div>
    </main>
  )
}
