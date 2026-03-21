import { useEffect, useMemo } from "react"
import { Link, useParams, useSearchParams } from "react-router-dom"
import LabPanel from "../components/LabPanel"
import { listLabShowcaseTickers } from "../lib/labData"

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

const SHOWCASE_COMPANY_CONTEXT: Record<string, string> = {
  NVDA: "As the dominant GPU supplier for AI training, NVIDIA's risk disclosures track the rapid evolution of export controls, supply concentration, and demand cyclicality in the AI hardware market.",
  LLY: "As Eli Lilly's obesity and cardiometabolic franchises become a larger share of the business, its risk disclosures now reveal whether pricing access, reimbursement design, and commercialization channels are moving closer to the center of near-term execution risk.",
  KO: "As a global beverage company operating in 200+ markets, Coca-Cola's risk disclosures track currency exposure, sugar-tax and labeling regulation, supply chain resilience, and product-mix shifts across beverage categories.",
  WM: "As the largest US waste hauler, Waste Management's risk disclosures track environmental regulation, landfill capacity, and the economics of recycling and sustainability mandates.",
  GE: "Following its three-way split, GE Aerospace's risk disclosures track defense procurement cycles, supply chain constraints, and the transition to next-generation engine programs.",
}

const SHOWCASE_COMPANY_THESIS: Record<string, string> = {
  NVDA: "Start with the filing shift and why it matters, then compare how the four lanes surface NVDA's export-control and supply-execution story and whether that winner holds up under lower effort before moving into the audit layers below.",
  LLY: "Start with the filing shift and why it matters, then compare how the three pilot lanes surface Lilly's pricing-access, concentration, and policy-channel story and the lower-effort robustness read before stopping at the matrix proof boundary for this issuer.",
  KO: "Use this page to separate true regulatory and product-mix shifts from the defensive-company boilerplate that appears stable year after year.",
  WM: "Use this page to track when operational execution and sustainability economics become more important than generic environmental or policy language.",
  GE: "Use this page to see whether GE Aerospace's filing is emphasizing services execution and installed-base risk more than broader macro or trade-policy framing.",
}

const COMPANY_VISIBLE_LANES: Record<string, string> = {
  NVDA: "02 hero, 03 main comparator, 01 secondary comparator, 00 recovered control",
  LLY: "02 hero, 03 main comparator, 00 recovered control",
}

const COMPANY_DEFAULT_READ: Record<string, string[]> = {
  NVDA: [
    "1. Start with what changed in NVDA's filing and why it matters.",
    "2. Compare how the four lanes emphasize the same filing differently, then check the effort-robustness block.",
    "3. Use the narrative, deterministic methods, agreement, and outline compare below for the deeper audit.",
  ],
  LLY: [
    "1. Start with why this case matters and what changed in Lilly's filing.",
    "2. Compare how 02, 03, and recovered B0 tell the same fixed filing pair differently, then read the effort-robustness block.",
    "3. Use the matrix caveat and auditability notes as the stopping boundary; legacy lower audit surfaces are not yet integrated for this issuer.",
  ],
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
  const defaultReadItems =
    COMPANY_DEFAULT_READ[ticker] ?? [
      "1. Start with the risk narrative summary and paired filing evidence.",
      "2. Confirm the signal with the core deterministic methods and agreement.",
      "3. Open outline compare when you want the deeper structural audit.",
    ]

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
                  Companies
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
              <div className="text-xs uppercase tracking-[0.24em] text-slate-400">Active case</div>
              <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-slate-100">
                FY2024 to FY2025 Item 1A
              </div>
              <div className="text-xs uppercase tracking-[0.24em] text-slate-400">Visible compare lanes</div>
              <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-slate-200">
                {COMPANY_VISIBLE_LANES[ticker] ?? "Codex real and ChatGPT 5.4 real"}
              </div>
              <div className="text-xs uppercase tracking-[0.24em] text-slate-400">Default read</div>
              <ol className="space-y-2 text-sm text-slate-200">
                {defaultReadItems.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ol>
              <div className="flex flex-wrap gap-2 pt-1">
                <Link
                  to="/companies"
                  className="inline-flex items-center rounded-full border border-white/20 px-3 py-1.5 text-xs text-slate-200 hover:border-white/40 hover:bg-white/5"
                >
                  Browse companies
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
