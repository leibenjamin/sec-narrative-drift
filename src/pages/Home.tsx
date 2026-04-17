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
import { getRouteFamilyConfig, isHomeAnchorTicker } from "../lib/routeFamilyUi"

const PROTOCOL_STAGE_STEPS: ProtocolStageStep[] = [
  {
    title: "Read",
    detail: "See what each approach actually produced on the same filing pair.",
    chips: ["approach output"],
  },
  {
    title: "Compare",
    detail: "Hold the reads side by side on the same evidence substrate.",
    chips: ["same substrate"],
  },
  {
    title: "Verdict",
    detail: "Name what the approach added, and where it honestly should stop.",
    chips: ["honest takeaway"],
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

type HomeHeroSignal = {
  label: string
  detail: string
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
  const readingFlow = visiblePilotSystem?.startHere.reading_flow ?? [
    { step: "filing answer", description: "Read the filing claim first." },
    { step: "protocol meaning", description: "Keep the route visible." },
    { step: "audit if needed", description: "Leave the deeper audit lower." },
  ]
  const liveCaseCount = visiblePilotSystem?.currentCaseMix.visible_pilots.length ?? 6
  const anchorSummary =
    visiblePilotSystem?.currentCaseMix.why_this_mix_matters ?? casebookFraming.home.chooserSummary
  const antiHypeStatement =
    visiblePilotSystem?.currentCaseMix.anti_hype_statement ??
    "Curated casebook, not a broad filing browser."
  const heroSignals: HomeHeroSignal[] = [
    {
      label: `${liveCaseCount} curated cases`,
      detail: "live public roster",
    },
    {
      label: "3 approaches compared",
      detail: "plain prompt / structured contract / tagged protocol",
    },
    {
      label: `Start with ${recommendedTicker}`,
      detail: recommendedPilot?.role_label ?? "structure earns its weight",
    },
  ]
  const pressurePilots =
    visiblePilotSystem?.visiblePilots.filter((pilot) => !isHomeAnchorTicker(pilot.ticker)).slice(0, 3) ?? []

  return (
    <main className="min-h-screen page-fade">
      <PageMetadata
        title={casebookFraming.home.title}
        description={casebookFraming.home.metaDescription}
      />
      <div className="mx-auto max-w-6xl space-y-4 px-5 py-4 sm:space-y-5 sm:px-6 sm:py-6 xl:py-8">
        <section
          id="home-top-fold"
          className="relative overflow-hidden rounded-[2.4rem] border border-white/10 bg-linear-to-br from-slate-950/94 via-slate-950/86 to-slate-900/76 shadow-[0_36px_90px_rgba(2,6,23,0.46)]"
        >
          <div className="relative grid gap-4 p-4 sm:gap-5 sm:p-6 xl:gap-5 xl:p-7">
            <div className="grid gap-4 xl:grid-cols-[minmax(0,0.96fr)_minmax(0,1.04fr)] xl:items-stretch">
              <article className="home-hero-panel home-reveal home-reveal--1 rounded-[1.95rem] border border-white/10 bg-slate-950/26 p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)] sm:p-6 xl:p-7">
                <div className="flex flex-wrap items-center gap-1.5 text-[11px] uppercase tracking-[0.24em] text-slate-300">
                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                    {casebookFraming.appName}
                  </span>
                  <span className="rounded-full border border-sky-300/25 bg-sky-400/10 px-3 py-1 text-sky-100">
                    Interactive casebook
                  </span>
                </div>

                <div className="mt-5 grid gap-5 sm:mt-6 sm:gap-6">
                  <div className="grid gap-5">
                    <div className="space-y-4">
                      <h1 className="max-w-3xl text-[clamp(2.4rem,4vw,4.55rem)] font-semibold leading-[0.92] tracking-[-0.05em] text-slate-50">
                        {casebookFraming.home.hook}
                      </h1>
                      <p className="max-w-xl text-sm leading-6 text-slate-200 sm:text-base">
                        {casebookFraming.home.support}
                      </p>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-3">
                      {heroSignals.map((signal) => (
                        <div
                          key={signal.label}
                          className="home-hero-signal rounded-[1.2rem] border border-white/10 bg-slate-950/34 px-4 py-3"
                        >
                          <div className="text-[11px] uppercase tracking-[0.24em] text-sky-100">
                            {signal.label}
                          </div>
                          <p className="mt-2 text-sm leading-5 text-slate-300">{signal.detail}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-3">
                      <Link
                        to={recommendedHref}
                        className="home-cta-primary inline-flex min-h-11 items-center justify-center rounded-full bg-sky-500 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-sky-400"
                      >
                        {`Start with ${recommendedTicker}`}
                      </Link>
                      <Link
                        to="/companies"
                        className="home-cta-secondary inline-flex min-h-11 items-center justify-center rounded-full border border-white/20 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:border-white/40 hover:bg-white/5"
                      >
                        {casebookFraming.home.casebookEntryCta}
                      </Link>
                    </div>

                    <div className="flex flex-wrap items-center gap-3">
                      <Link
                        to="/methodology"
                        className="inline-flex items-center gap-2 text-sm font-medium text-slate-200 transition hover:text-white"
                      >
                        <span>How the workflow works</span>
                        <span aria-hidden="true" className="text-base leading-none">
                          →
                        </span>
                      </Link>
                      <span aria-hidden="true" className="hidden h-4 w-px bg-white/10 sm:block" />
                      <p className="max-w-md text-[11px] uppercase leading-5 tracking-[0.24em] text-slate-500">
                        {antiHypeStatement}
                      </p>
                    </div>
                  </div>
                </div>
              </article>

              <div className="home-reveal home-reveal--2">
                <div className="home-stage-shell rounded-[1.95rem] border border-sky-300/16 bg-slate-950/34 p-4 shadow-[0_24px_60px_rgba(2,6,23,0.18)] sm:p-5 xl:flex xl:h-full xl:flex-col xl:justify-between xl:p-6">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
                    <div className="max-w-xl">
                      <div className="text-[11px] uppercase tracking-[0.28em] text-sky-100">
                        Presentation route
                      </div>
                      <h2 className="mt-2 text-[1.55rem] font-semibold leading-tight text-slate-50 sm:text-[1.8rem]">
                        Compare approaches, then call the verdict.
                      </h2>
                      <p className="mt-2 max-w-xl text-sm leading-6 text-slate-300">
                        Each case holds two or more approaches against the same filing pair, and the
                        verdict names what structure actually added over a plain prompt.
                      </p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      {readingFlow.map((item) => (
                        <span
                          key={item.step}
                          className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] uppercase tracking-[0.22em] text-slate-300"
                        >
                          {item.step}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="mt-4 xl:mt-5">
                    <ProtocolStageMap steps={PROTOCOL_STAGE_STEPS} />
                  </div>
                </div>
              </div>
            </div>

            <article className="home-anchor-shell home-reveal home-reveal--3 rounded-[1.95rem] border border-sky-300/14 bg-slate-950/40 p-4 shadow-[0_24px_60px_rgba(2,6,23,0.18)] sm:p-5 xl:p-6">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div className="max-w-2xl">
                  <div className="text-[11px] uppercase tracking-[0.28em] text-sky-100">
                    Anchor cases
                  </div>
                  <h2 className="mt-2 text-[1.7rem] font-semibold tracking-[-0.03em] text-slate-50 sm:text-[2rem]">
                    Start with the three anchor approach verdicts.
                  </h2>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
                    {anchorSummary}
                  </p>
                </div>

                {pressurePilots.length > 0 ? (
                  <div className="max-w-xl">
                    <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
                      Then pressure-test with
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2.5">
                      {pressurePilots.map((pilot) => (
                        <Link
                          key={pilot.ticker}
                          to={pilot.href}
                          className="home-pressure-chip inline-flex items-center gap-2 rounded-full border border-white/10 bg-slate-950/50 px-3.5 py-2 text-sm text-slate-200 transition hover:border-sky-300/45 hover:text-white"
                        >
                          <span className="font-semibold tracking-[0.04em] text-slate-50">
                            {pilot.ticker}
                          </span>
                          <span className="text-slate-400">{pilot.role_label}</span>
                        </Link>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>

              <div className="mt-5 grid gap-4 md:grid-cols-3 stagger-children">
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
            </article>

            {isLoading || error ? (
              <div className="grid gap-2">
                {isLoading ? (
                  <p className="text-sm text-slate-400">Loading current case guidance...</p>
                ) : null}

                {error ? (
                  <p className="rounded-2xl border border-amber-400/25 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
                    {error}
                  </p>
                ) : null}
              </div>
            ) : null}
          </div>
        </section>

        <section
          id="home-framing"
          className="grid gap-4 xl:grid-cols-[minmax(0,1.02fr)_minmax(0,0.98fr)]"
        >
          <article className="home-support-panel rounded-[1.7rem] border border-white/10 bg-slate-950/48 p-4 sm:p-5">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="home-support-tile rounded-[1.2rem] border border-white/10 bg-slate-950/58 p-4">
                <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
                  {casebookFraming.home.whatThisIsTitle}
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-100">
                  {casebookFraming.home.whatThisIs}
                </p>
              </div>
              <div className="home-support-tile rounded-[1.2rem] border border-white/10 bg-slate-950/58 p-4">
                <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
                  {casebookFraming.home.whatThisIsntTitle}
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-100">
                  {casebookFraming.home.whatThisIsnt}
                </p>
              </div>
            </div>
          </article>

          <article className="home-support-panel rounded-[1.7rem] border border-white/10 bg-slate-950/48 p-4 sm:p-5">
            <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
              {casebookFraming.home.whyThisMattersTitle}
            </div>
            <div className="mt-3 grid gap-2.5">
              {casebookFraming.home.whyThisMatters.map((item) => (
                <div
                  key={item}
                  className="home-support-pill rounded-2xl border border-white/10 bg-slate-950/58 px-3.5 py-3 text-sm leading-6 text-slate-100"
                >
                  {item}
                </div>
              ))}
            </div>
          </article>
        </section>

        <section className="grid gap-4 xl:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
          <article
            id="home-casebook-entry"
            className="home-support-panel rounded-[1.7rem] border border-sky-300/16 bg-linear-to-br from-sky-400/10 via-slate-950/70 to-slate-950/48 p-4 sm:p-5"
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
                className="home-cta-secondary inline-flex min-h-11 items-center justify-center rounded-full border border-sky-300/30 bg-sky-400/10 px-4 py-2.5 text-sm font-medium text-sky-100 transition hover:border-sky-200/45 hover:bg-sky-400/14"
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

          <article className="home-support-panel rounded-[1.7rem] border border-white/10 bg-slate-950/48 p-4 sm:p-5">
            <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
              {casebookFraming.home.commonFailureModesTitle}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {casebookFraming.home.commonFailureModes.map((item) => (
                <span
                  key={item}
                  className="home-failure-chip rounded-full border border-white/10 bg-slate-950/60 px-3 py-1.5 text-[13px] text-slate-200"
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
