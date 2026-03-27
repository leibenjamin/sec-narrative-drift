import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import PageMetadata from "../components/PageMetadata"
import { formatFiscalYearRange } from "../lib/fiscalYear"
import {
  buildProtocolLabCaseHref,
  getProtocolLabRecommendedPilot,
  listProtocolLabVisiblePilots,
  loadProtocolLabDemoShareV3,
  loadProtocolLabVisiblePilotSystem,
  type ProtocolLabDemoShareV3,
  type ProtocolLabVisiblePilotEntry,
  type ProtocolLabVisiblePilotSystem,
} from "../lib/protocolLabProductPositioning"

const HERO_TITLE = "Document Protocol Lab is a bounded SEC Item 1A pilot."
const HERO_SUBHEAD =
  "The visible pilot stays fixed to three fixtures so the product thesis stays legible: strongest first signal, policy-heavy bounded contrast, and low-drift restraint."
const HOME_TITLE = "Document Protocol Lab | SEC Item 1A pilot"
const HOME_META_DESCRIPTION =
  "Document Protocol Lab is a bounded, evidence-first SEC Item 1A pilot across NVDA, LLY, and KO: answer first, evidence nearby, audit on demand."

function formatPilotPairLabel(pilot: ProtocolLabVisiblePilotEntry): string {
  return `${formatFiscalYearRange(pilot.year_from, pilot.year_to)} Item 1A`
}

export default function Home() {
  const [visiblePilotSystem, setVisiblePilotSystem] = useState<ProtocolLabVisiblePilotSystem | null>(null)
  const [demoShare, setDemoShare] = useState<ProtocolLabDemoShareV3 | null>(null)
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
        setError("Home page case guidance is unavailable right now.")
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false

    loadProtocolLabDemoShareV3()
      .then((result) => {
        if (cancelled) return
        setDemoShare(result)
      })
      .catch(() => {
        if (cancelled) return
        setDemoShare(null)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const currentCaseMix = visiblePilotSystem?.currentCaseMix ?? null
  const startHere = visiblePilotSystem?.startHere ?? null
  const visiblePilots = visiblePilotSystem ? listProtocolLabVisiblePilots(visiblePilotSystem) : []
  const recommendedPilot = visiblePilotSystem ? getProtocolLabRecommendedPilot(visiblePilotSystem) : null
  const alternativeFirstPilots = visiblePilotSystem?.alternativeFirstPilots ?? []

  return (
    <main className="min-h-screen page-fade">
      <PageMetadata
        title={demoShare?.canonical_share_title ?? HOME_TITLE}
        description={demoShare?.canonical_share_description ?? HOME_META_DESCRIPTION}
      />
      <div className="mx-auto grid max-w-6xl gap-8 px-6 py-12">
        <section className="grid gap-6 rounded-[1.8rem] border border-white/10 bg-linear-to-br from-slate-950/82 via-slate-900/62 to-slate-950/46 p-6 shadow-[0_26px_60px_rgba(2,6,23,0.38)] lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-5">
            <div className="space-y-3">
              <p className="text-xs uppercase tracking-[0.28em] text-sky-100">Document Protocol Lab</p>
              <h1 className="max-w-4xl text-4xl font-semibold leading-tight text-slate-50 sm:text-5xl">
                {HERO_TITLE}
              </h1>
              <p className="max-w-3xl text-lg text-sky-100/95">{HERO_SUBHEAD}</p>
              <p className="max-w-3xl text-base text-slate-200">
                This lab tests a narrow product claim: can an evidence-first document workflow put
                the filing answer first, explain the protocol meaning second, and leave the deeper
                audit third instead of making it lead the page?
              </p>
            </div>

            <div className="rounded-[1.25rem] border border-white/10 bg-slate-950/45 p-4">
              <div className="text-xs uppercase tracking-[0.24em] text-slate-400">
                Why this pilot stays bounded
              </div>
              <p className="mt-3 text-sm text-slate-100">
                {currentCaseMix?.product_statement ??
                  "The current live product is a bounded Document Protocol Lab pilot for three SEC Item 1A fixtures."}
              </p>
              <p className="mt-2 text-sm text-slate-300">
                {currentCaseMix?.anti_hype_statement ??
                  "This remains an intentionally compact three-case product, not a broad issuer catalog or research platform."}
              </p>
            </div>

            <div className="flex flex-wrap gap-2 text-xs text-slate-200">
              <span className="rounded-full border border-sky-300/30 bg-sky-400/12 px-3 py-1">
                Document Protocol Lab
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                SEC Item 1A pilot
              </span>
              <span className="rounded-full border border-emerald-300/25 bg-emerald-400/10 px-3 py-1">
                Filing answer first
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                Static JSON only
              </span>
            </div>

            <div className="flex flex-wrap items-stretch gap-3 pt-1">
              <Link
                to={recommendedPilot?.href ?? buildProtocolLabCaseHref("NVDA", 2024, 2025)}
                className="inline-flex w-full items-center justify-center rounded-full bg-sky-500 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 sm:w-auto"
              >
                Open the NVDA fixture
              </Link>
              <Link
                to="/companies"
                className="inline-flex w-full items-center justify-center rounded-full border border-white/20 px-5 py-2.5 text-sm text-slate-200 transition hover:border-white/40 hover:bg-white/5 sm:w-auto"
              >
                Browse the 3 fixtures
              </Link>
              <Link
                to="/methodology"
                className="inline-flex w-full items-center justify-center rounded-full border border-white/20 px-5 py-2.5 text-sm text-slate-200 transition hover:border-white/40 hover:bg-white/5 sm:w-auto"
              >
                Methodology
              </Link>
            </div>

            {error ? (
              <p className="rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
                {error}
              </p>
            ) : null}
          </div>

          <aside className="space-y-4 rounded-[1.3rem] border border-white/10 bg-slate-950/55 p-5">
            <div className="text-xs uppercase tracking-[0.24em] text-slate-400">Recommended start</div>
            {isLoading ? (
              <p className="text-sm text-slate-300">Loading start guidance...</p>
            ) : !visiblePilotSystem || !currentCaseMix || !startHere || !recommendedPilot ? (
              <p className="rounded-lg border border-amber-400/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
                Start guidance is unavailable because the case list did not load cleanly.
              </p>
            ) : (
              <>
                <Link
                  to={recommendedPilot.href}
                  className="block rounded-[1.2rem] border border-sky-300/25 bg-sky-400/12 p-4 transition hover:border-sky-200/40 hover:bg-sky-400/16"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-sm font-semibold text-slate-50">
                        {`Start with ${recommendedPilot.ticker}`}
                      </div>
                      <div className="mt-1 text-[11px] uppercase tracking-wide text-sky-100/85">
                        {recommendedPilot.role_label}
                      </div>
                    </div>
                    <span className="rounded-full border border-sky-300/30 bg-sky-400/15 px-2 py-0.5 text-[11px] text-sky-100">
                      {formatPilotPairLabel(recommendedPilot)}
                    </span>
                  </div>
                  <p className="mt-3 text-sm text-slate-100">{recommendedPilot.why_case_exists}</p>
                  <div className="mt-3 rounded-xl border border-white/10 bg-slate-950/30 p-3">
                    <div className="text-[11px] uppercase tracking-wide text-slate-400">
                      Why start here
                    </div>
                    <p className="mt-2 text-sm text-slate-100">{recommendedPilot.guidance.why_pick}</p>
                    <p className="mt-2 text-xs text-slate-300">
                      {recommendedPilot.guidance.what_you_learn}
                    </p>
                  </div>
                </Link>

                <div className="space-y-2">
                  <div className="text-xs uppercase tracking-[0.24em] text-slate-400">
                    Alternate first paths
                  </div>
                  {alternativeFirstPilots.map((pilot) => (
                    <Link
                      key={pilot.ticker}
                      to={pilot.href}
                      className="block rounded-xl border border-white/10 bg-white/5 px-4 py-3 transition hover:border-white/20 hover:bg-white/8"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="text-sm font-medium text-slate-100">{pilot.company_name}</div>
                        <span className="text-[11px] uppercase tracking-wide text-slate-400">
                          {pilot.role_label}
                        </span>
                      </div>
                      <p className="mt-2 text-sm text-slate-200">{pilot.guidance.why_pick}</p>
                    </Link>
                  ))}
                </div>
              </>
            )}
          </aside>
        </section>

        <section className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-2xl font-semibold text-slate-50">Why these three fixtures</h2>
              <p className="mt-1 max-w-3xl text-sm text-slate-400">
                {currentCaseMix?.why_this_mix_matters ??
                  "Three selected cases are enough to show the workflow clearly without widening the product."}
              </p>
            </div>
            <Link
              to="/companies"
              className="inline-flex items-center rounded-full border border-white/20 px-4 py-2 text-xs text-slate-200 transition hover:border-white/40 hover:bg-white/5"
            >
              Open the chooser page
            </Link>
          </div>

          {isLoading ? (
            <p className="text-sm text-slate-300">Loading selected fixtures...</p>
          ) : !visiblePilotSystem || !currentCaseMix || !startHere ? (
            <p className="rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
              Fixture rationale is unavailable because the case list did not load cleanly.
            </p>
          ) : (
            <div className="grid gap-4 lg:grid-cols-3 stagger-children">
              {visiblePilots.map((pilot) => (
                <article
                  key={pilot.ticker}
                  className="rounded-[1.35rem] border border-white/10 bg-slate-900/50 p-5"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-base font-semibold text-slate-50">{pilot.ticker}</div>
                      <div className="text-xs text-slate-300">{pilot.company_name}</div>
                    </div>
                    <span className="rounded-full border border-sky-300/30 bg-sky-400/12 px-2 py-0.5 text-[11px] text-sky-100">
                      {pilot.role_label}
                    </span>
                  </div>
                  <p className="mt-4 text-sm text-slate-200">{pilot.why_case_exists}</p>
                  <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-slate-200">
                    <div className="text-[11px] uppercase tracking-wide text-slate-400">
                      What this fixture proves
                    </div>
                    <p className="mt-2">{pilot.guidance.what_you_learn}</p>
                  </div>
                  <div className="mt-4 flex items-center justify-between gap-3 text-xs text-slate-400">
                    <span>{pilot.best_for}</span>
                    <Link
                      to={pilot.href}
                      className="text-sky-200 transition hover:text-sky-100"
                    >
                      {`Open ${pilot.ticker}`}
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-[1.35rem] border border-white/10 bg-slate-900/45 p-5">
            <div className="text-xs uppercase tracking-[0.24em] text-slate-400">Default reading order</div>
            {isLoading ? (
              <p className="mt-3 text-sm text-slate-300">Loading reading flow...</p>
            ) : !startHere ? (
              <p className="mt-3 text-sm text-amber-100">
                Reading flow is unavailable because the start guidance did not load cleanly.
              </p>
            ) : (
              <div className="mt-3 grid gap-3 sm:grid-cols-3">
                {startHere.reading_flow.map((step, index) => (
                  <article
                    key={step.step}
                    className="rounded-xl border border-white/10 bg-slate-950/35 p-4"
                  >
                    <div className="text-[11px] uppercase tracking-wide text-slate-500">
                      Step {index + 1}
                    </div>
                    <h3 className="mt-2 text-sm font-semibold text-slate-100">{step.step}</h3>
                    <p className="mt-2 text-sm text-slate-300">{step.description}</p>
                  </article>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-[1.35rem] border border-emerald-300/20 bg-emerald-400/10 p-5">
            <div className="text-xs uppercase tracking-[0.24em] text-emerald-100">Pilot boundary</div>
            <p className="mt-3 text-sm text-slate-100">
              Start with the filing answer on a company page. Use the protocol layer to understand
              why the fixture is in the lab. Open the deeper audit only when you want the extra
              structure, method detail, or provenance.
            </p>
            <p className="mt-3 text-sm text-slate-200">
              Static JSON only. No runtime model calls. Filing text stays untrusted, and the lower
              runtime registry can remain broader backstage without changing the visible
              three-fixture claim.
            </p>
          </div>
        </section>
      </div>
    </main>
  )
}
