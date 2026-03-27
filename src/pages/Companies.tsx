import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import PageMetadata from "../components/PageMetadata"
import ProtocolLabUseCaseGuide from "../components/ProtocolLabUseCaseGuide"
import {
  buildProtocolLabCaseHref,
  getProtocolLabRecommendedPilot,
  listProtocolLabVisiblePilots,
  loadProtocolLabVisiblePilotSystem,
  type ProtocolLabVisiblePilotSystem,
} from "../lib/protocolLabProductPositioning"

const COMPANIES_TITLE = "Pilot Cases | Document Protocol Lab"
const COMPANIES_DESCRIPTION =
  "Choose the current Document Protocol Lab SEC Item 1A fixture: NVDA, LLY, or KO."

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
  const visiblePilots = visiblePilotSystem ? listProtocolLabVisiblePilots(visiblePilotSystem) : []
  const recommendedPilot = visiblePilotSystem ? getProtocolLabRecommendedPilot(visiblePilotSystem) : null

  return (
    <main className="min-h-screen page-fade">
      <PageMetadata title={COMPANIES_TITLE} description={COMPANIES_DESCRIPTION} />
      <div className="mx-auto max-w-6xl space-y-8 px-6 py-12">
        <header className="space-y-4">
          <p className="text-xs uppercase tracking-[0.28em] text-slate-300">Cases</p>
          <h1 className="text-3xl font-semibold text-slate-50 sm:text-4xl">
            Choose the fixture that matches your goal.
          </h1>
          <p className="max-w-3xl text-sm text-slate-300">
            This is the lean chooser for the visible three-fixture pilot. Pick the strongest first
            signal, the policy-heavy bounded contrast, or the restraint / low-drift honesty check.
          </p>
          <div className="flex flex-wrap gap-2 text-xs text-slate-200">
            <span className="rounded-full border border-sky-300/30 bg-sky-400/12 px-3 py-1">
              Three fixed fixtures
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
              Choose by goal
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
              Open one case
            </span>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              to={recommendedPilot?.href ?? buildProtocolLabCaseHref("NVDA", 2024, 2025)}
              className="inline-flex items-center justify-center rounded-full bg-sky-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-400"
            >
              Open the NVDA fixture
            </Link>
            <Link
              to="/"
              className="inline-flex items-center justify-center rounded-full border border-white/20 px-4 py-2 text-sm text-slate-200 transition hover:border-white/40 hover:bg-white/5"
            >
              Back to Home thesis
            </Link>
          </div>
          {error ? (
            <div className="rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
              {error}
            </div>
          ) : null}
        </header>

        {isLoading ? (
          <p className="text-sm text-slate-300">Loading fixture chooser...</p>
        ) : !visiblePilotSystem || !currentCaseMix ? (
          <p className="rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
            Fixture chooser is unavailable because the case list did not load cleanly.
          </p>
        ) : (
          <>
            <ProtocolLabUseCaseGuide
              visiblePilots={visiblePilots}
              title="Choose by goal"
              description="Each option below is a fixed visible pilot fixture for a different first question."
            />

            <section className="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
              <article className="rounded-[1.35rem] border border-white/10 bg-slate-900/45 p-5">
                <div className="text-xs uppercase tracking-[0.24em] text-slate-400">
                  Why the chooser stays fixed
                </div>
                <p className="mt-3 text-sm text-slate-100">
                  {currentCaseMix.anti_hype_statement}
                </p>
                <p className="mt-2 text-sm text-slate-300">{currentCaseMix.why_this_mix_matters}</p>
              </article>

              <article className="rounded-[1.35rem] border border-emerald-300/20 bg-emerald-400/10 p-5">
                <div className="text-xs uppercase tracking-[0.24em] text-emerald-100">
                  What stays constant after you choose
                </div>
                <p className="mt-3 text-sm text-slate-100">
                  Every fixture keeps the same speaking order: filing answer first, protocol
                  meaning second, deeper audit third.
                </p>
                <p className="mt-2 text-sm text-slate-200">
                  The app stays static JSON only at runtime. LLY remains explicitly bounded, and
                  the lower runtime registry can stay broader backstage without widening the visible
                  chooser claim.
                </p>
              </article>
            </section>
          </>
        )}
      </div>
    </main>
  )
}
