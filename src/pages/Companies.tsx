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
      <div className="mx-auto max-w-6xl space-y-6 px-6 py-12">
        <header className="space-y-4">
          <p className="text-xs uppercase tracking-[0.28em] text-slate-300">Cases</p>
          <h1 className="text-3xl font-semibold text-slate-50 sm:text-4xl">
            Choose the fixture that matches your goal.
          </h1>
          <p className="max-w-2xl text-sm leading-6 text-slate-300">
            Pick the fixed pilot fixture that matches the first read you need.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              to="/"
              className="inline-flex items-center justify-center rounded-full border border-white/20 px-4 py-2 text-sm text-slate-200 transition hover:border-white/40 hover:bg-white/5"
            >
              Back to Home
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
        ) : !visiblePilotSystem ? (
          <p className="rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
            Fixture chooser is unavailable because the case list did not load cleanly.
          </p>
        ) : (
          <>
            <ProtocolLabUseCaseGuide
              visiblePilots={visiblePilots}
              title="Choose by goal"
              description="The cards are the chooser. Open the one that matches your read."
            />
          </>
        )}
      </div>
    </main>
  )
}
