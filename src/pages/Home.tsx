import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import PageMetadata from "../components/PageMetadata"
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

function buildFallbackHref(ticker: HomeAnchorTicker): string {
  const entry = getPublicCasebookEntry(ticker)
  if (!entry) {
    throw new Error(`Missing casebook entry for ${ticker}.`)
  }

  return buildProtocolLabCaseHref(ticker, entry.yearFrom, entry.yearTo)
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

  const recommendedPilot = visiblePilotSystem
    ? getProtocolLabRecommendedPilot(visiblePilotSystem)
    : null
  const recommendedTicker = recommendedPilot?.ticker ?? "NVDA"
  const recommendedHref = recommendedPilot?.href ?? buildFallbackHref("NVDA")

  const anchorEntries = HOME_ANCHOR_TICKERS.map((ticker) => {
    const entry = getPublicCasebookEntry(ticker)
    if (!entry) {
      throw new Error(`Missing casebook entry for ${ticker}.`)
    }

    return {
      ...entry,
      href: visiblePilotSystem?.visiblePilots.find((pilot) => pilot.ticker === ticker)?.href ?? buildFallbackHref(ticker),
    }
  })

  return (
    <main className="min-h-screen page-fade">
      <PageMetadata
        title={casebookFraming.home.title}
        description={casebookFraming.home.metaDescription}
      />
      <div className="mx-auto max-w-6xl space-y-4 px-5 py-4 sm:space-y-5 sm:px-6 sm:py-6 xl:py-8">
        <section
          id="home-top-fold"
          className="relative overflow-hidden rounded-[2.35rem] border border-white/10 bg-linear-to-br from-slate-950/94 via-slate-950/86 to-slate-900/74 shadow-[0_36px_90px_rgba(2,6,23,0.46)]"
        >
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.14),transparent_32%),radial-gradient(circle_at_bottom_right,rgba(16,185,129,0.1),transparent_28%)]" />
          <div className="relative grid gap-5 p-5 sm:gap-6 sm:p-6 xl:p-7">
            <article className="rounded-[1.9rem] border border-white/10 bg-slate-950/32 p-5 backdrop-blur sm:p-6 xl:p-7">
              <div className="flex flex-wrap items-center gap-1.5 text-[11px] uppercase tracking-[0.24em] text-slate-300">
                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                  {casebookFraming.appName}
                </span>
                <span className="rounded-full border border-sky-300/25 bg-sky-400/10 px-3 py-1 text-sky-100">
                  Bounded six-case casebook
                </span>
              </div>

              <div className="mt-5 grid gap-5 sm:mt-6 sm:gap-6">
                <div className="space-y-4">
                  <h1 className="max-w-4xl text-[clamp(2.4rem,4vw,4.8rem)] font-semibold leading-[0.92] tracking-[-0.05em] text-slate-50">
                    {casebookFraming.home.hook}
                  </h1>
                  <p className="max-w-3xl text-sm leading-6 text-slate-200 sm:text-base">
                    {casebookFraming.home.support}
                  </p>
                </div>

                <div className="flex flex-wrap gap-2.5">
                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[11px] uppercase tracking-[0.22em] text-slate-300">
                    6 curated cases
                  </span>
                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[11px] uppercase tracking-[0.22em] text-slate-300">
                    3 live approaches
                  </span>
                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[11px] uppercase tracking-[0.22em] text-slate-300">
                    claim / prove / stop
                  </span>
                </div>
              </div>
            </article>

            <div className="grid gap-4 xl:grid-cols-2">
              <article className="rounded-[1.75rem] border border-white/10 bg-slate-950/44 p-5 backdrop-blur sm:p-6">
                <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
                  {casebookFraming.home.storyEntryTitle}
                </div>
                <p className="mt-3 text-lg font-semibold leading-7 text-slate-50">
                  Understand the argument before you inspect the proof.
                </p>
                <p className="mt-3 max-w-xl text-sm leading-6 text-slate-200">
                  {casebookFraming.home.storyEntryBody}
                </p>
                <div className="mt-4 grid gap-2.5">
                  {casebookFraming.home.storyEntryPoints.map((item) => (
                    <div
                      key={item}
                      className="rounded-[1.1rem] border border-white/10 bg-slate-950/56 px-4 py-3 text-sm leading-6 text-slate-100"
                    >
                      {item}
                    </div>
                  ))}
                </div>
                <div className="mt-5 flex flex-wrap items-center gap-3">
                  <Link
                    to="/story"
                    className="inline-flex min-h-11 items-center justify-center rounded-full bg-sky-500 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-sky-400"
                  >
                    {casebookFraming.home.storyEntryCta}
                  </Link>
                  <Link
                    to="/methodology"
                    className="inline-flex items-center gap-2 text-sm font-medium text-slate-200 transition hover:text-white"
                  >
                    <span>Field guide</span>
                    <span aria-hidden="true">→</span>
                  </Link>
                </div>
              </article>

              <article className="rounded-[1.75rem] border border-sky-300/18 bg-linear-to-br from-sky-400/10 via-slate-950/78 to-slate-950/58 p-5 backdrop-blur sm:p-6">
                <div className="text-[11px] uppercase tracking-[0.24em] text-sky-100">
                  {casebookFraming.home.casebookEntryTitle}
                </div>
                <p className="mt-3 text-lg font-semibold leading-7 text-slate-50">
                  Browse the six-case instrument without widening the claim.
                </p>
                <p className="mt-3 max-w-xl text-sm leading-6 text-slate-100">
                  {casebookFraming.home.casebookEntryBody}
                </p>
                <div className="mt-4 grid gap-2.5">
                  {casebookFraming.home.casebookEntryPoints.map((item) => (
                    <div
                      key={item}
                      className="rounded-[1.1rem] border border-white/10 bg-slate-950/56 px-4 py-3 text-sm leading-6 text-slate-100"
                    >
                      {item}
                    </div>
                  ))}
                </div>
                <div className="mt-4 rounded-[1.1rem] border border-white/10 bg-slate-950/62 px-4 py-3">
                  <div className="text-[11px] uppercase tracking-[0.22em] text-slate-400">
                    {`${casebookFraming.home.casebookEntrySecondaryCta} ${recommendedTicker}`}
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-200">
                    {recommendedPilot?.guidance.why_pick ?? "Begin with the clearest anchor verdict before moving through the full roster."}
                  </p>
                </div>
                <div className="mt-5 flex flex-wrap items-center gap-3">
                  <Link
                    to="/companies"
                    className="inline-flex min-h-11 items-center justify-center rounded-full border border-sky-300/30 bg-sky-400/10 px-5 py-2.5 text-sm font-semibold text-sky-100 transition hover:border-sky-200/45 hover:bg-sky-400/14"
                  >
                    {casebookFraming.home.casebookEntryCta}
                  </Link>
                  <Link
                    to={recommendedHref}
                    className="inline-flex min-h-11 items-center justify-center rounded-full border border-white/20 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:border-white/40 hover:bg-white/5"
                  >
                    {`Open ${recommendedTicker}`}
                  </Link>
                </div>
              </article>
            </div>

            <div className="rounded-[1.25rem] border border-white/10 bg-slate-950/42 px-4 py-3 text-sm leading-6 text-slate-200">
              <span className="mr-2 text-[11px] uppercase tracking-[0.22em] text-slate-400">
                {casebookFraming.home.boundednessLabel}
              </span>
              {casebookFraming.home.boundednessBody}
            </div>

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
          id="home-anchor-preview"
          className="rounded-[1.75rem] border border-white/10 bg-slate-950/46 p-5 shadow-[0_22px_55px_rgba(2,6,23,0.2)] sm:p-6"
        >
          <div className="space-y-2">
            <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
              {casebookFraming.home.anchorPreviewTitle}
            </div>
            <p className="max-w-3xl text-sm leading-6 text-slate-200">
              {casebookFraming.home.anchorPreviewBody}
            </p>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {anchorEntries.map((entry) => (
              <Link
                key={entry.ticker}
                to={entry.href}
                className="group rounded-[1.25rem] border border-white/10 bg-slate-950/68 p-4 transition hover:border-sky-300/40 hover:bg-slate-950/82"
              >
                <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
                  {entry.publicRoleLabel}
                </div>
                <div className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-slate-50">
                  {entry.ticker}
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-200">{entry.teachingSummary}</p>
                <div className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-sky-100 transition group-hover:text-white">
                  <span>Open {entry.ticker}</span>
                  <span aria-hidden="true">→</span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </main>
  )
}
