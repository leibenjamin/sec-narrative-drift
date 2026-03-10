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
  KO: "As a global beverage company operating in 200+ markets, Coca-Cola's risk disclosures track currency exposure, sugar-tax and labeling regulation, supply chain resilience, and product-mix shifts across beverage categories.",
  WM: "As the largest US waste hauler, Waste Management's risk disclosures track environmental regulation, landfill capacity, and the economics of recycling and sustainability mandates.",
  GE: "Following its three-way split, GE Aerospace's risk disclosures track defense procurement cycles, supply chain constraints, and the transition to next-generation engine programs.",
}

const SHOWCASE_COMPANY_THESIS: Record<string, string> = {
  NVDA: "Use this page to see whether export controls and supply concentration are becoming more central, or simply being restated with different wording.",
  KO: "Use this page to separate true regulatory and product-mix shifts from the defensive-company boilerplate that appears stable year after year.",
  WM: "Use this page to track when operational execution and sustainability economics become more important than generic environmental or policy language.",
  GE: "Use this page to see whether GE Aerospace's filing is emphasizing services execution and installed-base risk more than broader macro or trade-policy framing.",
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
        <header className="space-y-5">
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
                  Showcase
                </Link>
              </li>
              <li aria-hidden="true" className="text-slate-500">/</li>
              <li className="text-slate-100" aria-current="page">
                {ticker}
              </li>
            </ol>
          </nav>

          <section className="grid gap-4 rounded-[1.7rem] border border-white/10 bg-linear-to-br from-slate-950/80 via-slate-900/58 to-slate-950/40 p-6 shadow-[0_22px_56px_rgba(2,6,23,0.35)] lg:grid-cols-[1.45fr_0.55fr]">
            <div className="space-y-4">
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-[0.28em] text-sky-100">Company case</p>
                <h1 className="text-3xl font-semibold text-slate-50 sm:text-4xl">
                  {displayName} ({ticker})
                </h1>
                {SHOWCASE_COMPANY_SECTORS[ticker] ? (
                  <p className="text-sm font-medium text-slate-400">{SHOWCASE_COMPANY_SECTORS[ticker]}</p>
                ) : null}
              </div>
              <p className="max-w-3xl text-sm text-slate-200">
                Year-over-year analysis of {displayName}'s 10-K Item 1A risk disclosures, focused on which themes intensified,
                which faded, and whether the filing is really changing its economic story or just reorganizing familiar language.
              </p>
              {SHOWCASE_COMPANY_CONTEXT[ticker] ? (
                <p className="max-w-3xl text-sm text-slate-400">{SHOWCASE_COMPANY_CONTEXT[ticker]}</p>
              ) : null}
              <div className="rounded-[1.1rem] border border-sky-300/22 bg-sky-400/10 p-4">
                <div className="text-xs uppercase tracking-[0.24em] text-sky-100">Case thesis</div>
                <p className="mt-2 text-sm text-slate-100">{SHOWCASE_COMPANY_THESIS[ticker] ?? "Use the deterministic baseline first, then compare the precomputed model sidecars."}</p>
              </div>
            </div>

            <aside className="space-y-3 rounded-[1.25rem] border border-white/10 bg-slate-950/55 p-4">
              <div className="text-xs uppercase tracking-[0.24em] text-slate-400">How to use this case</div>
              <ol className="space-y-2 text-sm text-slate-200">
                <li>1. Start with the risk narrative summary and lead evidence pair.</li>
                <li>2. Check whether the deterministic methods agree on the same story.</li>
                <li>3. Use outline compare to see where Codex and ChatGPT differ in salience or framing.</li>
              </ol>
              <div className="flex flex-wrap gap-2 pt-1">
                <Link
                  to="/companies"
                  className="inline-flex items-center rounded-full border border-white/20 px-3 py-1.5 text-xs text-slate-200 hover:border-white/40 hover:bg-white/5"
                >
                  Browse showcase
                </Link>
                <Link
                  to="/methodology"
                  className="inline-flex items-center rounded-full border border-white/20 px-3 py-1.5 text-xs text-slate-200 hover:border-white/40 hover:bg-white/5"
                >
                  Methodology
                </Link>
              </div>
            </aside>
          </section>

          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-xl border border-sky-300/25 bg-sky-400/10 p-4">
              <div className="text-xs uppercase tracking-[0.24em] text-sky-100">Risk narrative drift</div>
              <p className="mt-2 text-sm text-slate-100">
                See which themes were added, removed, intensified, or softened using deterministic detectors plus precomputed outline-compare sidecars.
              </p>
            </div>
            <div className="rounded-xl border border-white/10 bg-slate-950/35 p-4">
              <div className="text-xs uppercase tracking-[0.24em] text-slate-300">Investor read</div>
              <p className="mt-2 text-sm text-slate-200">
                The useful question is not whether the filing changed. It is whether the company is now emphasizing a more important operating, regulatory, or commercial risk channel.
              </p>
            </div>
            <div className="rounded-xl border border-emerald-300/20 bg-emerald-400/10 p-4">
              <div className="text-xs uppercase tracking-[0.24em] text-emerald-100">Compare-first flow</div>
              <p className="mt-2 text-sm text-slate-100">
                The page now puts the paired campaign read first, then deterministic support, then agreement, then the deeper outline-compare drill-down.
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
