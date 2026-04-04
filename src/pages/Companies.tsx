import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import PageMetadata from "../components/PageMetadata"
import ProtocolLabUseCaseGuide from "../components/ProtocolLabUseCaseGuide"
import {
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

  const visiblePilots = visiblePilotSystem ? listProtocolLabVisiblePilots(visiblePilotSystem) : []

  return (
    <main className="min-h-screen page-fade">
      <PageMetadata title={COMPANIES_TITLE} description={COMPANIES_DESCRIPTION} />
      <div className="mx-auto max-w-6xl space-y-5 px-5 py-8 sm:px-6 sm:py-10">
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-[0.28em] text-slate-300">Cases</p>
          <h1 className="max-w-3xl text-3xl font-semibold text-slate-50 sm:text-4xl">
            Choose the fixture that matches your goal.
          </h1>
          <p className="max-w-3xl text-sm leading-6 text-slate-300">
            Pick the fixed pilot fixture that matches the first read you need.
          </p>
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-sm font-medium text-slate-300 transition hover:text-white"
          >
            <span aria-hidden="true">←</span>
            <span>Back to Home</span>
          </Link>
          {error ? (
            <div className="rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
              {error}
            </div>
          ) : null}
        </header>

        {isLoading ? (
          <p className="text-sm text-slate-300">Loading fixture chooser...</p>
        ) : !visiblePilotSystem ? (
          <p className="rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
            Fixture chooser is unavailable because the case list did not load cleanly.
          </p>
        ) : (
          <>
            <ProtocolLabUseCaseGuide
              visiblePilots={visiblePilots}
              showIntro={false}
            />
          </>
        )}
      </div>
    </main>
  )
}
