import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import CasebookComparisonTable from "../components/CasebookComparisonTable"
import FixtureRoleCard from "../components/FixtureRoleCard"
import PageMetadata from "../components/PageMetadata"
import {
  CASEBOOK_BANDS,
  casebookFraming,
  getPublicCasebookEntry,
} from "../lib/casebookContent"
import {
  buildProtocolLabCaseHref,
  loadProtocolLabVisiblePilotSystem,
  type ProtocolLabVisiblePilotSystem,
} from "../lib/protocolLabProductPositioning"

function resolveHref(
  visiblePilotSystem: ProtocolLabVisiblePilotSystem | null,
  ticker: string
): string {
  const visiblePilot = visiblePilotSystem?.visiblePilots.find((entry) => entry.ticker === ticker)
  if (visiblePilot) return visiblePilot.href

  const casebookEntry = getPublicCasebookEntry(ticker)
  if (!casebookEntry) {
    throw new Error(`Missing casebook entry for ${ticker}.`)
  }

  return buildProtocolLabCaseHref(ticker, casebookEntry.yearFrom, casebookEntry.yearTo)
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
        setVisiblePilotSystem(null)
        setError("Selected case guidance is unavailable right now. Showing fixed casebook routes instead.")
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <main className="min-h-screen page-fade">
      <PageMetadata
        title={casebookFraming.casebook.title}
        description={casebookFraming.casebook.metaDescription}
      />
      <div className="mx-auto max-w-6xl space-y-5 px-5 py-8 sm:space-y-6 sm:px-6 sm:py-10">
        <header
          id="casebook-top-fold"
          className="space-y-3 rounded-[1.7rem] border border-white/10 bg-linear-to-br from-slate-950/90 via-slate-950/76 to-slate-900/62 p-4 shadow-[0_22px_55px_rgba(2,6,23,0.32)] sm:p-6"
        >
          <p className="text-xs uppercase tracking-[0.28em] text-slate-300">
            {casebookFraming.casebook.eyebrow}
          </p>
          <h1 className="max-w-3xl text-3xl font-semibold text-slate-50 sm:text-4xl">
            {casebookFraming.casebook.heading}
          </h1>
          <p className="max-w-3xl text-sm leading-6 text-slate-300">
            {casebookFraming.casebook.intro}
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Link
              to="/"
              className="inline-flex items-center gap-2 text-sm font-medium text-slate-300 transition hover:text-white"
            >
              <span aria-hidden="true">←</span>
              <span>Back to Home</span>
            </Link>
            <Link
              to="/methodology"
              className="inline-flex items-center gap-2 text-sm font-medium text-slate-300 transition hover:text-white"
            >
              <span>Methodology</span>
              <span aria-hidden="true">→</span>
            </Link>
          </div>
          <div className="rounded-[1.1rem] border border-white/10 bg-slate-950/38 px-4 py-3 text-sm text-slate-200">
            {casebookFraming.casebook.boundednessNote}
          </div>
          {error ? (
            <div className="rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
              {error}
            </div>
          ) : null}
        </header>

        <section
          id="casebook-curation-note"
          className="rounded-[1.45rem] border border-white/10 bg-slate-950/42 p-4 sm:p-5"
        >
          <div className="space-y-2">
            <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
              {casebookFraming.casebook.rosterNoteTitle}
            </div>
            <p className="max-w-3xl text-sm leading-6 text-slate-100">
              {casebookFraming.casebook.rosterNoteLead}
            </p>
            <p className="max-w-3xl text-sm leading-6 text-slate-300">
              {casebookFraming.casebook.rosterNoteSupport}
            </p>
          </div>
        </section>

        {isLoading ? (
          <p className="text-sm text-slate-300">Loading casebook roster...</p>
        ) : (
          <section id="casebook-roster" className="space-y-5">
            {CASEBOOK_BANDS.map((band) => (
              <section
                key={band.id}
                className="space-y-4 rounded-[1.6rem] border border-white/10 bg-slate-950/42 p-4 sm:p-5"
              >
                <div className="space-y-2">
                  <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
                    {band.title}
                  </div>
                  <p className="max-w-3xl text-sm leading-6 text-slate-300">
                    {band.description}
                  </p>
                </div>

                <div className="grid gap-4 xl:grid-cols-3">
                  {band.tickers.map((ticker) => {
                    const entry = getPublicCasebookEntry(ticker)
                    if (!entry) {
                      throw new Error(`Missing casebook entry for ${ticker}.`)
                    }

                    return (
                      <FixtureRoleCard
                        key={ticker}
                        ticker={ticker}
                        companyName={entry.companyName}
                        roleLabel={entry.publicRoleLabel}
                        description={entry.teachingSummary}
                        bestFor={entry.bestUsedWhen}
                        href={resolveHref(visiblePilotSystem, ticker)}
                        ctaLabel={`Open ${ticker}`}
                        emphasis={band.id === "anchor_shapes" && ticker === "NVDA" ? "primary" : "default"}
                        variant="cases"
                      />
                    )
                  })}
                </div>
              </section>
            ))}
          </section>
        )}

        <section
          id="casebook-comparison"
          className="space-y-3 rounded-[1.6rem] border border-white/10 bg-slate-950/42 p-4 sm:p-5"
        >
          <div className="space-y-2">
            <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
              {casebookFraming.casebook.comparisonTitle}
            </div>
            <p className="max-w-3xl text-sm leading-6 text-slate-300">
              {casebookFraming.casebook.comparisonIntro}
            </p>
          </div>
          <CasebookComparisonTable />
        </section>
      </div>
    </main>
  )
}
