import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import PageMetadata from "../components/PageMetadata"
import ProtocolLabUseCaseGuide from "../components/ProtocolLabUseCaseGuide"
import { formatFiscalYearRange } from "../lib/fiscalYear"
import {
  buildProtocolLabCaseHref,
  getProtocolLabRecommendedPilot,
  listProtocolLabVisiblePilots,
  loadProtocolLabVisiblePilotSystem,
  type ProtocolLabVisiblePilotEntry,
  type ProtocolLabVisiblePilotSystem,
} from "../lib/protocolLabProductPositioning"

const COMPANIES_TITLE = "Pilot Cases | Document Protocol Lab"
const COMPANIES_DESCRIPTION =
  "Choose the current Document Protocol Lab SEC Item 1A fixture: NVDA, LLY, or KO."

function formatPilotPairLabel(pilot: ProtocolLabVisiblePilotEntry): string {
  return `${formatFiscalYearRange(pilot.year_from, pilot.year_to)} Item 1A`
}

export default function Companies() {
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
        setError("Selected case guidance is unavailable right now.")
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const currentCaseMix = visiblePilotSystem?.currentCaseMix ?? null
  const startHere = visiblePilotSystem?.startHere ?? null
  const visiblePilots = visiblePilotSystem ? listProtocolLabVisiblePilots(visiblePilotSystem) : []
  const recommendedPilot = visiblePilotSystem ? getProtocolLabRecommendedPilot(visiblePilotSystem) : null

  return (
    <main className="min-h-screen page-fade">
      <PageMetadata title={COMPANIES_TITLE} description={COMPANIES_DESCRIPTION} />
      <div className="mx-auto max-w-6xl space-y-8 px-6 py-12">
        <header className="space-y-4">
          <p className="text-xs uppercase tracking-[0.28em] text-slate-300">Cases</p>
          <h1 className="text-3xl font-semibold text-slate-50 sm:text-4xl">
            Choose the current pilot fixture.
          </h1>
          <p className="max-w-3xl text-sm text-slate-300">
            Document Protocol Lab currently stays fixed to three SEC Item 1A fixtures. NVDA is the
            clearest first shift, LLY is the bounded policy-heavy contrast case, and KO is the
            restraint check that keeps the workflow honest on low drift.
          </p>
          <div className="flex flex-wrap gap-2 text-xs text-slate-200">
            <span className="rounded-full border border-sky-300/30 bg-sky-400/12 px-3 py-1">
              Document Protocol Lab
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
              SEC Item 1A pilot
            </span>
            <span className="rounded-full border border-emerald-300/25 bg-emerald-400/10 px-3 py-1">
              Three fixed fixtures
            </span>
          </div>
          {error ? (
            <div className="rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
              {error}
            </div>
          ) : null}
        </header>

        <section className="rounded-[1.4rem] border border-white/10 bg-slate-900/45 p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="text-xs uppercase tracking-[0.24em] text-slate-400">Choose by goal</div>
              <p className="mt-1 text-sm text-slate-300">
                Pick the first fixture by what you want to learn from the protocol.
              </p>
            </div>
            <Link
              to={recommendedPilot?.href ?? buildProtocolLabCaseHref("NVDA", 2024, 2025)}
              className="inline-flex w-full items-center justify-center rounded-full bg-sky-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 sm:w-auto"
            >
              Open the NVDA fixture
            </Link>
          </div>

          {isLoading ? (
            <p className="mt-4 text-sm text-slate-300">Loading start guidance...</p>
          ) : !visiblePilotSystem || !currentCaseMix || !startHere ? (
            <p className="mt-4 rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
              Start guidance is unavailable because the case list did not load cleanly.
            </p>
          ) : (
            <>
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                {visiblePilots.map((pilot) => (
                  <Link
                    key={pilot.ticker}
                    to={pilot.href}
                    className={`rounded-2xl border p-4 transition ${
                      pilot.is_recommended_first_case
                        ? "border-sky-300/30 bg-sky-400/12 hover:border-sky-200/45 hover:bg-sky-400/16"
                        : "border-white/10 bg-slate-950/35 hover:border-white/20 hover:bg-white/6"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-sm font-semibold text-slate-100">{pilot.ticker}</div>
                      <span className="text-[11px] uppercase tracking-wide text-slate-400">
                        {pilot.is_recommended_first_case ? "Recommended first" : "Alternate start"}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-slate-100">{pilot.guidance.why_pick}</p>
                    <p className="mt-2 text-xs text-slate-300">{pilot.guidance.what_you_learn}</p>
                  </Link>
                ))}
              </div>

              <ProtocolLabUseCaseGuide
                visiblePilots={visiblePilots}
                className="mt-4"
              />
            </>
          )}
        </section>

        <section className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-2xl font-semibold text-slate-50">Current pilot fixtures</h2>
              <p className="mt-1 max-w-3xl text-sm text-slate-400">
                {currentCaseMix?.why_this_mix_matters ??
                  "Three selected cases are enough to make the current product story legible without broadening scope."}
              </p>
            </div>
            <p className="max-w-md text-xs text-slate-400">
              {currentCaseMix?.anti_hype_statement ??
                "This remains an intentionally compact three-case product."}
            </p>
          </div>

          {isLoading ? (
            <p className="text-sm text-slate-300">Loading selected cases...</p>
          ) : !visiblePilotSystem || !currentCaseMix || !startHere ? (
            <p className="rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
              Selected case cards are unavailable because the case list did not load cleanly.
            </p>
          ) : (
            <div className="grid gap-4 lg:grid-cols-3 stagger-children">
              {visiblePilots.map((pilot) => (
                <article
                  key={pilot.ticker}
                  className="flex h-full flex-col rounded-[1.35rem] border border-white/10 bg-slate-900/50 p-5 transition hover:border-sky-300/35 hover:bg-slate-900/65"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h2 className="text-lg font-semibold text-slate-50">{pilot.ticker}</h2>
                      <p className="text-xs text-slate-300">{pilot.company_name}</p>
                    </div>
                    <span className="rounded-full border border-sky-300/30 bg-sky-400/12 px-2 py-0.5 text-[11px] text-sky-100">
                      {pilot.role_label}
                    </span>
                  </div>

                  <div className="mt-4 space-y-3 text-sm text-slate-200">
                    <p>{pilot.why_case_exists}</p>
                    <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                      <div className="text-[11px] uppercase tracking-wide text-slate-400">
                        Best first if
                      </div>
                      <p className="mt-1 text-sm text-slate-100">{pilot.guidance.why_pick}</p>
                      <p className="mt-2 text-xs text-slate-300">{pilot.guidance.what_you_learn}</p>
                    </div>
                  </div>

                  <div className="mt-4 space-y-1 text-xs text-slate-400">
                    <p>Active case: {formatPilotPairLabel(pilot)}</p>
                    <p>Case type: {pilot.role_label}</p>
                    <p>Best first if: {pilot.best_for}</p>
                  </div>

                  <div className="mt-5">
                    <Link
                      to={pilot.href}
                      className="inline-flex items-center rounded-full bg-sky-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-sky-500"
                    >
                      {`Open ${pilot.ticker} case`}
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  )
}
