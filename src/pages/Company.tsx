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

const SHOWCASE_COMPANY_CONTEXT: Record<string, string> = {
  NVDA: "As the dominant GPU supplier for AI training, NVIDIA's risk disclosures track the rapid evolution of export controls, supply concentration, and demand cyclicality in the AI hardware market.",
  LLY: "As Eli Lilly's obesity and cardiometabolic franchises become a larger share of the business, its risk disclosures now reveal whether pricing access, reimbursement design, and commercialization channels are moving closer to the center of near-term execution risk.",
  KO: "As a global beverage company operating in 200+ markets, Coca-Cola's risk disclosures track currency exposure, sugar-tax and labeling regulation, supply chain resilience, and product-mix shifts across beverage categories. KO also serves as the restraint case: the filing is mostly stable, but useful selective sharpening is still visible.",
  WM: "As the largest US waste hauler, Waste Management's risk disclosures track environmental regulation, landfill capacity, and the economics of recycling and sustainability mandates.",
  GE: "Following its three-way split, GE Aerospace's risk disclosures track defense procurement cycles, supply chain constraints, and the transition to next-generation engine programs.",
}

const SHOWCASE_COMPANY_LEAD: Record<string, string> = {
  NVDA: "NVDA is the clearest first filing-shift case: export controls, supply concentration, and AI demand concentration all move closer to the center of the risk story.",
  LLY: "LLY is the bounded policy-heavy contrast case: pricing access, reimbursement design, and concentration pressure matter more, but the visible claim stays intentionally narrower than a full lower-audit build.",
  KO: "KO is the restraint case: the filing is mostly stable, and the point is to see whether the workflow stays honest when selective sharpening matters more than dramatic novelty.",
  WM: "Use this page to track when operational execution and sustainability economics become more important than generic environmental or policy language.",
  GE: "Use this page to see whether GE Aerospace's filing is emphasizing services execution and installed-base risk more than broader macro or trade-policy framing.",
}

const SHOWCASE_COMPANY_BOUNDARY: Record<string, string> = {
  NVDA: "Read the filing answer first, then use the protocol layer and audit to pressure-test it rather than replace it.",
  LLY: "This issuer intentionally ships as a bounded visible case. The public surface shows the filing answer and protocol meaning honestly without pretending the lower audit is broader than it is.",
  KO: "Low drift is part of the test. The goal is to stay disciplined about what is actually new, not to force novelty where the filing does not justify it.",
  WM: "This page stays bounded to the visible filing pair and deterministic evidence paths that are actually present.",
  GE: "This page stays bounded to the visible filing pair and deterministic evidence paths that are actually present.",
}

const COMPANY_AVAILABLE_READS: Record<string, string[]> = {
  NVDA: [
    "Primary read",
    "Comparison read",
    "Secondary comparison",
    "Control read",
  ],
  LLY: [
    "Primary read",
    "Comparison read",
    "Control read",
  ],
  KO: [
    "Primary read",
    "Restraint note",
    "Fresh vs reused",
  ],
}

const COMPANY_DEFAULT_READ: Record<string, string[]> = {
  NVDA: [
    "Read the filing answer and paired evidence first.",
    "Use the protocol layer to compare the primary, comparison, and control reads.",
    "Open the deeper audit only when you want method detail, agreement, or structure.",
  ],
  LLY: [
    "Read the filing answer and bounded comparison story first.",
    "Use the protocol layer to see why this policy-heavy case is in the lab.",
    "Treat the visible stopping point as intentional scope honesty, not a missing fake full audit.",
  ],
  KO: [
    "Read the filing answer and restraint note first.",
    "Use Fresh vs reused only as a bounded secondary check.",
    "Continue into the audit only when you want to confirm the low-drift signal without overstating it.",
  ],
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
  const availableReadItems = COMPANY_AVAILABLE_READS[ticker] ?? ["Codex real compare", "ChatGPT 5.4 compare"]
  const defaultReadItems =
    COMPANY_DEFAULT_READ[ticker] ?? [
      "Start with the risk narrative summary and paired filing evidence.",
      "Confirm the signal with the core deterministic methods and agreement.",
      "Open outline compare when you want the deeper structural audit.",
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
      <PageMetadata
        title={`${displayName} (${ticker}) | Document Protocol Lab`}
        description={companyMetaDescription}
      />
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
                  Cases
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
                <p className="text-xs uppercase tracking-[0.28em] text-sky-100">Current pilot case</p>
                <h1 className="text-3xl font-semibold text-slate-50 sm:text-4xl">
                  {displayName} ({ticker})
                </h1>
                {SHOWCASE_COMPANY_SECTORS[ticker] ? (
                  <p className="text-sm font-medium text-slate-400">{SHOWCASE_COMPANY_SECTORS[ticker]}</p>
                ) : null}
              </div>
              <p className="max-w-3xl text-sm text-slate-200">
                This page is the current {visiblePilot?.role_label?.toLowerCase() ?? "visible"} fixture
                inside Document Protocol Lab&apos;s bounded SEC Item 1A pilot. The answer section below
                should land the filing shift first, the protocol layer should explain why this case is
                in the lab second, and the audit stack should stay lower.
              </p>
              {SHOWCASE_COMPANY_CONTEXT[ticker] ? (
                <p className="max-w-3xl text-sm text-slate-400">{SHOWCASE_COMPANY_CONTEXT[ticker]}</p>
              ) : null}
              <div className="grid gap-3 lg:grid-cols-3">
                <article className="rounded-[1.1rem] border border-sky-300/22 bg-sky-400/10 p-4">
                  <div className="text-xs uppercase tracking-[0.24em] text-sky-100">Filing answer first</div>
                  <p className="mt-2 text-sm text-slate-100">
                    {SHOWCASE_COMPANY_LEAD[ticker] ??
                      "Use the filing answer below as the first voice on the page."}
                  </p>
                </article>
                <article className="rounded-[1.1rem] border border-white/10 bg-slate-950/35 p-4">
                  <div className="text-xs uppercase tracking-[0.24em] text-slate-400">Evidence route</div>
                  <p className="mt-2 text-sm text-slate-100">
                    The answer section pairs the filing shift with evidence first. The protocol
                    layer and deeper audit follow only when you want more context or verification.
                  </p>
                </article>
                <article className="rounded-[1.1rem] border border-amber-300/20 bg-amber-400/10 p-4">
                  <div className="text-xs uppercase tracking-[0.24em] text-amber-100">Boundary note</div>
                  <p className="mt-2 text-sm text-slate-100">
                    {SHOWCASE_COMPANY_BOUNDARY[ticker] ??
                      "This page stays bounded to the visible filing pair and the evidence paths that are actually present."}
                  </p>
                </article>
              </div>
            </div>

            <aside className="space-y-3 rounded-[1.25rem] border border-white/10 bg-slate-950/55 p-4">
              <div className="text-xs uppercase tracking-[0.24em] text-slate-400">Fixture role</div>
              <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-slate-100">
                {visiblePilot?.role_label ?? "Visible pilot"}
              </div>
              <div className="text-xs uppercase tracking-[0.24em] text-slate-400">Active case</div>
              <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-slate-100">
                {activeCaseLabel}
              </div>
              <div className="text-xs uppercase tracking-[0.24em] text-slate-400">Read order</div>
              <ol className="space-y-2 text-sm text-slate-200">
                {defaultReadItems.map((item, index) => (
                  <li
                    key={item}
                    className="flex items-start gap-3 rounded-lg border border-white/10 bg-white/5 px-3 py-2"
                  >
                    <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-sky-400/15 text-[11px] font-medium text-sky-100">
                      {index + 1}
                    </span>
                    <span>{item}</span>
                  </li>
                ))}
              </ol>
              <div className="text-xs uppercase tracking-[0.24em] text-slate-400">Available reads</div>
              <div className="flex flex-wrap gap-2 rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-slate-200">
                {availableReadItems.map((item) => (
                  <span
                    key={item}
                    className="rounded-full border border-white/10 bg-slate-950/45 px-2.5 py-1 text-xs text-slate-100"
                  >
                    {item}
                  </span>
                ))}
              </div>
              <div className="flex flex-wrap gap-2 pt-1">
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
