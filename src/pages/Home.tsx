import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import FixtureRoleCard from "../components/FixtureRoleCard"
import PageMetadata from "../components/PageMetadata"
import ProtocolStageMap, { type ProtocolStageStep } from "../components/ProtocolStageMap"
import {
  buildProtocolLabCaseHref,
  getProtocolLabRecommendedPilot,
  loadProtocolLabVisiblePilotSystem,
  type ProtocolLabVisiblePilotSystem,
} from "../lib/protocolLabProductPositioning"
import {
  VISIBLE_FAMILY_TICKERS,
  getRouteFamilyConfig,
  type VisibleFamilyTicker,
} from "../lib/routeFamilyUi"

const HOME_TITLE = "Document Protocol Lab | SEC Item 1A pilot"
const HOME_META_DESCRIPTION =
  "Document Protocol Lab is a bounded public pilot across NVDA, LLY, and KO: claim first, protocol proof second, deeper audit only when needed."
const HOME_HOOK = "How do you show what changed in a document without overstating what you know?"
const HOME_SUPPORT =
  "A bounded public pilot across NVDA, LLY, and KO makes the protocol visible in one pass."

const PROTOCOL_STAGE_STEPS: ProtocolStageStep[] = [
  {
    title: "Claim",
    detail: "Lead with the filing answer before explanation takes over.",
    chips: ["answer first"],
  },
  {
    title: "Prove",
    detail: "Show why the fixture belongs in the lab and what the framing adds.",
    chips: ["fixture meaning"],
  },
  {
    title: "Stop",
    detail: "Open deeper audit only when the first read needs pressure.",
    chips: ["audit on demand"],
  },
]

type HomeFixtureCardModel = {
  ticker: VisibleFamilyTicker
  companyName: string
  roleLabel: string
  demonstration: string
  href: string
  ctaLabel: string
  emphasis: "primary" | "default"
}

function buildFixtureCardModel(
  ticker: VisibleFamilyTicker,
  href: string,
  companyName: string | null = null
): HomeFixtureCardModel {
  const familyConfig = getRouteFamilyConfig(ticker)
  if (!familyConfig) {
    throw new Error(`Missing route-family config for ${ticker}.`)
  }

  return {
    ticker,
    companyName: companyName ?? familyConfig.companyName,
    roleLabel: familyConfig.homeCardLabel,
    demonstration: familyConfig.homeCardDemo,
    href,
    ctaLabel: ticker === "NVDA" ? "Open NVDA" : `Open ${ticker}`,
    emphasis: ticker === "NVDA" ? "primary" : "default",
  }
}

export default function Home() {
  const [visiblePilotSystem, setVisiblePilotSystem] = useState<ProtocolLabVisiblePilotSystem | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    loadProtocolLabVisiblePilotSystem()
      .then((result) => {
        if (cancelled) return
        setVisiblePilotSystem(result)
        setError(null)
      })
      .catch(() => {
        if (cancelled) return
        setVisiblePilotSystem(null)
        setError("Fixture guidance did not load cleanly. Showing the fixed pilot routes instead.")
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const fixtureCards = VISIBLE_FAMILY_TICKERS.map((ticker) => {
    const pilot = visiblePilotSystem?.visiblePilots.find((entry) => entry.ticker === ticker) ?? null
    return buildFixtureCardModel(
      ticker,
      pilot?.href ?? buildProtocolLabCaseHref(ticker, 2024, 2025),
      pilot?.company_name ?? null
    )
  })
  const recommendedHref = visiblePilotSystem
    ? getProtocolLabRecommendedPilot(visiblePilotSystem).href
    : buildProtocolLabCaseHref("NVDA", 2024, 2025)

  return (
    <main className="min-h-screen page-fade">
      <PageMetadata title={HOME_TITLE} description={HOME_META_DESCRIPTION} />
      <div className="mx-auto max-w-6xl px-5 py-5 sm:px-6 sm:py-8">
        <section className="relative overflow-hidden rounded-[2.2rem] border border-white/10 bg-linear-to-br from-slate-950/92 via-slate-950/82 to-slate-900/72 shadow-[0_32px_80px_rgba(2,6,23,0.44)]">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.16),transparent_34%),radial-gradient(circle_at_bottom_right,rgba(16,185,129,0.12),transparent_28%)]" />
          <div className="relative grid gap-4 p-5 sm:gap-5 sm:p-6 xl:p-7">
            <div className="flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-slate-300">
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                Document Protocol Lab
              </span>
              <span className="rounded-full border border-sky-300/25 bg-sky-400/10 px-3 py-1 text-sky-100">
                Bounded public pilot
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                NVDA / LLY / KO
              </span>
            </div>

            <div className="grid gap-4 lg:grid-cols-[1.08fr_0.92fr] lg:items-end">
              <div className="space-y-4">
                <div className="space-y-3">
                  <h1 className="text-[clamp(2.15rem,4vw,4.2rem)] font-semibold leading-[0.95] tracking-[-0.04em] text-slate-50">
                    {HOME_HOOK}
                  </h1>
                  <p className="max-w-2xl text-sm leading-6 text-slate-200 sm:text-base">
                    {HOME_SUPPORT}
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <Link
                    to={recommendedHref}
                    className="inline-flex min-h-11 items-center justify-center rounded-full bg-sky-500 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-sky-400"
                  >
                    Start with NVDA
                  </Link>
                  <Link
                    to="/companies"
                    className="inline-flex min-h-11 items-center justify-center rounded-full border border-white/20 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:border-white/40 hover:bg-white/5"
                  >
                    See all fixtures
                  </Link>
                  <Link
                    to="/methodology"
                    className="inline-flex min-h-11 items-center justify-center rounded-full border border-transparent px-2 py-2.5 text-sm font-medium text-slate-300 transition hover:text-white"
                  >
                    How the protocol works
                  </Link>
                </div>
              </div>

              <ProtocolStageMap steps={PROTOCOL_STAGE_STEPS} />
            </div>

            <div className="grid gap-4 md:grid-cols-3 stagger-children">
              {fixtureCards.map((fixture) => (
                <FixtureRoleCard
                  key={fixture.ticker}
                  ticker={fixture.ticker}
                  companyName={fixture.companyName}
                  roleLabel={fixture.roleLabel}
                  demonstration={fixture.demonstration}
                  href={fixture.href}
                  ctaLabel={fixture.ctaLabel}
                  emphasis={fixture.emphasis}
                />
              ))}
            </div>

            <div className="flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-[0.22em] text-slate-400">
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                Static JSON only
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                Audit stays secondary
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                Pilot claim stays bounded
              </span>
            </div>

            {isLoading ? (
              <p className="text-sm text-slate-400">Loading current pilot guidance...</p>
            ) : null}

            {error ? (
              <p className="rounded-2xl border border-amber-400/25 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
                {error}
              </p>
            ) : null}
          </div>
        </section>
      </div>
    </main>
  )
}
