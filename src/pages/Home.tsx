import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import FixtureRoleCard from "../components/FixtureRoleCard"
import PageMetadata from "../components/PageMetadata"
import ProtocolStageMap, { type ProtocolStageStep } from "../components/ProtocolStageMap"
import { compactText } from "../lib/compactText"
import {
  HOME_ANCHOR_TICKERS,
  casebookFraming,
  getPublicCasebookEntry,
  type HomeAnchorTicker,
} from "../lib/casebookContent"
import {
  buildProtocolLabCaseHref,
  getProtocolLabRecommendedPilot,
  loadProtocolLabVisiblePilotSystem,
  type ProtocolLabVisiblePilotSystem,
} from "../lib/protocolLabProductPositioning"
import { getRouteFamilyConfig } from "../lib/routeFamilyUi"

const PROTOCOL_STAGE_STEPS: ProtocolStageStep[] = [
  {
    title: "Claim",
    detail: "Lead with the filing answer.",
    chips: ["answer first"],
  },
  {
    title: "Prove",
    detail: "Keep proof beside the answer.",
    chips: ["evidence nearby"],
  },
  {
    title: "Stop",
    detail: "Make the honest boundary visible.",
    chips: ["bounded route"],
  },
]

type HomeFixtureCardModel = {
  ticker: HomeAnchorTicker
  companyName: string
  roleLabel: string
  description: string
  href: string
  ctaLabel: string
  emphasis: "primary" | "default"
}

function buildFallbackHref(ticker: HomeAnchorTicker): string {
  const entry = getPublicCasebookEntry(ticker)
  if (!entry) {
    throw new Error(`Missing casebook entry for ${ticker}.`)
  }
  return buildProtocolLabCaseHref(ticker, entry.yearFrom, entry.yearTo)
}

function buildFixtureCardModel(
  ticker: HomeAnchorTicker,
  href: string
): HomeFixtureCardModel {
  const familyConfig = getRouteFamilyConfig(ticker)
  if (!familyConfig) {
    throw new Error(`Missing route-family config for ${ticker}.`)
  }

  return {
    ticker,
    companyName: familyConfig.companyName,
    roleLabel: familyConfig.homeCardLabel,
    description: compactText(familyConfig.chooserCardDescription, 84),
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
        setError("Case guidance did not load cleanly. Showing the fixed casebook routes instead.")
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const fixtureCards = HOME_ANCHOR_TICKERS.map((ticker) => {
    const pilot = visiblePilotSystem?.visiblePilots.find((entry) => entry.ticker === ticker) ?? null
    return buildFixtureCardModel(ticker, pilot?.href ?? buildFallbackHref(ticker))
  })

  const recommendedPilot = visiblePilotSystem
    ? getProtocolLabRecommendedPilot(visiblePilotSystem)
    : null
  const recommendedTicker = recommendedPilot?.ticker ?? "NVDA"
  const recommendedHref = recommendedPilot?.href ?? buildFallbackHref("NVDA")

  return (
    <main className="min-h-screen page-fade">
      <PageMetadata
        title={casebookFraming.home.title}
        description={casebookFraming.home.metaDescription}
      />
      <div className="mx-auto max-w-6xl space-y-5 px-5 py-4 sm:space-y-6 sm:px-6 sm:py-8">
        <section
          id="home-top-fold"
          className="relative overflow-hidden rounded-[2.2rem] border border-white/10 bg-linear-to-br from-slate-950/92 via-slate-950/82 to-slate-900/72 shadow-[0_32px_80px_rgba(2,6,23,0.44)]"
        >
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.16),transparent_34%),radial-gradient(circle_at_bottom_right,rgba(16,185,129,0.12),transparent_28%)]" />
          <div className="relative grid gap-4 p-4 sm:gap-6 sm:p-6 xl:p-7">
            <div className="grid gap-4 lg:grid-cols-[minmax(0,0.94fr)_minmax(0,1.06fr)] lg:items-start">
              <div className="rounded-[1.8rem] border border-white/10 bg-slate-950/24 p-4 sm:p-5 xl:p-6">
                <div className="flex flex-wrap items-center gap-1.5 text-[11px] uppercase tracking-[0.24em] text-slate-300">
                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                    {casebookFraming.appName}
                  </span>
                  <span className="rounded-full border border-sky-300/25 bg-sky-400/10 px-3 py-1 text-sky-100">
                    Interactive casebook
                  </span>
                </div>

                <div className="mt-4 space-y-4 sm:mt-5 sm:space-y-5">
                  <div className="space-y-3">
                    <h1 className="max-w-3xl text-[clamp(2.15rem,4vw,4.2rem)] font-semibold leading-[0.95] tracking-[-0.04em] text-slate-50">
                      {casebookFraming.home.hook}
                    </h1>
                    <p className="max-w-xl text-sm leading-6 text-slate-200 sm:text-base">
                      {casebookFraming.home.support}
                    </p>
                  </div>

                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-3">
                      <Link
                        to={recommendedHref}
                        className="inline-flex min-h-11 items-center justify-center rounded-full bg-sky-500 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-sky-400"
                      >
                        {`Start with ${recommendedTicker}`}
                      </Link>
                      <Link
                        to="/companies"
                        className="inline-flex min-h-11 items-center justify-center rounded-full border border-white/20 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:border-white/40 hover:bg-white/5"
                      >
                        {casebookFraming.home.casebookEntryCta}
                      </Link>
                    </div>
                    <Link
                      to="/methodology"
                      className="inline-flex items-center gap-2 text-sm font-medium text-slate-300 transition hover:text-white"
                    >
                      <span>How the workflow works</span>
                      <span aria-hidden="true" className="text-base leading-none">
                        →
                      </span>
                    </Link>
                  </div>
                </div>
              </div>

              <div className="order-2 rounded-[1.8rem] border border-sky-300/14 bg-slate-950/42 p-4 shadow-[0_20px_50px_rgba(2,6,23,0.22)] sm:p-5 lg:order-3 lg:col-span-2">
                <div className="max-w-2xl">
                  <div className="text-[11px] uppercase tracking-[0.28em] text-sky-100">Anchor cases</div>
                  <h2 className="mt-2 text-xl font-semibold text-slate-50 sm:text-2xl">
                    Start with the three anchor answer shapes.
                  </h2>
                  <p className="mt-2 text-sm leading-6 text-slate-300">
                    {casebookFraming.home.chooserSummary}
                  </p>
                </div>

                <div className="mt-4 grid gap-4 md:grid-cols-3 stagger-children">
                  {fixtureCards.map((fixture) => (
                    <FixtureRoleCard
                      key={fixture.ticker}
                      ticker={fixture.ticker}
                      companyName={fixture.companyName}
                      roleLabel={fixture.roleLabel}
                      description={fixture.description}
                      href={fixture.href}
                      ctaLabel={fixture.ctaLabel}
                      emphasis={fixture.emphasis}
                      variant="home"
                    />
                  ))}
                </div>
              </div>

              <div className="order-3 lg:order-2">
                <ProtocolStageMap steps={PROTOCOL_STAGE_STEPS} />
              </div>
            </div>

            {isLoading ? (
              <p className="text-sm text-slate-400">Loading current case guidance...</p>
            ) : null}

            {error ? (
              <p className="rounded-2xl border border-amber-400/25 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
                {error}
              </p>
            ) : null}
          </div>
        </section>

        <section
          id="home-framing"
          className="grid gap-4 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]"
        >
          <article className="rounded-[1.6rem] border border-white/10 bg-slate-950/48 p-4 sm:p-5">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-[1.2rem] border border-white/10 bg-slate-950/58 p-4">
                <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
                  {casebookFraming.home.whatThisIsTitle}
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-100">
                  {casebookFraming.home.whatThisIs}
                </p>
              </div>
              <div className="rounded-[1.2rem] border border-white/10 bg-slate-950/58 p-4">
                <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
                  {casebookFraming.home.whatThisIsntTitle}
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-100">
                  {casebookFraming.home.whatThisIsnt}
                </p>
              </div>
            </div>
          </article>

          <article className="rounded-[1.6rem] border border-white/10 bg-slate-950/48 p-4 sm:p-5">
            <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
              {casebookFraming.home.whyThisMattersTitle}
            </div>
            <div className="mt-3 grid gap-2.5">
              {casebookFraming.home.whyThisMatters.map((item) => (
                <div
                  key={item}
                  className="rounded-[1rem] border border-white/10 bg-slate-950/58 px-3.5 py-3 text-sm leading-6 text-slate-100"
                >
                  {item}
                </div>
              ))}
            </div>
          </article>
        </section>

        <section className="grid gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <article
            id="home-casebook-entry"
            className="rounded-[1.6rem] border border-sky-300/16 bg-linear-to-br from-sky-400/10 via-slate-950/70 to-slate-950/48 p-4 sm:p-5"
          >
            <div className="text-[11px] uppercase tracking-[0.24em] text-sky-100">
              {casebookFraming.home.casebookEntryTitle}
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-100">
              {casebookFraming.home.casebookEntryBody}
            </p>
            <p className="mt-3 text-sm leading-6 text-slate-200">
              {casebookFraming.home.compareTeaser}
            </p>
            <div className="mt-4 flex flex-wrap items-center gap-4">
              <Link
                to="/companies"
                className="inline-flex min-h-11 items-center justify-center rounded-full border border-sky-300/30 bg-sky-400/10 px-4 py-2.5 text-sm font-medium text-sky-100 transition hover:border-sky-200/45 hover:bg-sky-400/14"
              >
                {casebookFraming.home.casebookEntryCta}
              </Link>
              <Link
                to="/methodology#methodology-compare"
                className="inline-flex items-center gap-2 text-sm font-medium text-slate-200 transition hover:text-white"
              >
                <span>{casebookFraming.home.compareTeaserCta}</span>
                <span aria-hidden="true">→</span>
              </Link>
            </div>
          </article>

          <article className="rounded-[1.6rem] border border-white/10 bg-slate-950/48 p-4 sm:p-5">
            <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
              {casebookFraming.home.commonFailureModesTitle}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {casebookFraming.home.commonFailureModes.map((item) => (
                <span
                  key={item}
                  className="rounded-full border border-white/10 bg-slate-950/60 px-3 py-1.5 text-[13px] text-slate-200"
                >
                  {item}
                </span>
              ))}
            </div>
          </article>
        </section>
      </div>
    </main>
  )
}
