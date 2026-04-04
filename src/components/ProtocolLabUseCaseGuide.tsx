import { Link } from "react-router-dom"
import { compactText } from "../lib/compactText"
import {
  buildProtocolLabCaseHref,
  type ProtocolLabVisiblePilotEntry,
} from "../lib/protocolLabProductPositioning"
import {
  VISIBLE_FAMILY_TICKERS,
  getRouteFamilyConfig,
  type VisibleFamilyTicker,
} from "../lib/routeFamilyUi"

type ProtocolLabUseCaseGuideProps = {
  visiblePilots: ProtocolLabVisiblePilotEntry[]
  title?: string
  description?: string
  className?: string
}

function resolvePilot(
  visiblePilots: ProtocolLabVisiblePilotEntry[],
  ticker: VisibleFamilyTicker
): ProtocolLabVisiblePilotEntry | null {
  for (const pilot of visiblePilots) {
    if (pilot.ticker === ticker) return pilot
  }
  return null
}

function resolveHref(
  visiblePilots: ProtocolLabVisiblePilotEntry[],
  ticker: VisibleFamilyTicker
): string {
  const pilot = resolvePilot(visiblePilots, ticker)
  if (pilot) return pilot.href
  return buildProtocolLabCaseHref(ticker, 2024, 2025)
}

export default function ProtocolLabUseCaseGuide({
  visiblePilots,
  title = "Choose by goal",
  description = "Each option below is a fixed visible pilot fixture.",
  className = "",
}: ProtocolLabUseCaseGuideProps) {
  return (
    <section className={`space-y-4 ${className}`.trim()}>
      <div>
        <div className="text-xs uppercase tracking-[0.24em] text-slate-400">{title}</div>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">{description}</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        {VISIBLE_FAMILY_TICKERS.map((ticker) => {
          const pilot = resolvePilot(visiblePilots, ticker)
          const familyConfig = getRouteFamilyConfig(ticker)
          const primaryLine = compactText(
            pilot?.why_case_exists ?? "Open the current fixture for this pilot role.",
            136
          )
          const supportLine = compactText(
            pilot?.best_for ?? pilot?.guidance.why_pick ?? "Open this fixture.",
            74
          )
          const isRecommended = Boolean(pilot?.is_recommended_first_case)
          return (
            <Link
              key={ticker}
              to={resolveHref(visiblePilots, ticker)}
              className={
                isRecommended
                  ? "group flex h-full flex-col rounded-[1.45rem] border border-sky-300/26 bg-linear-to-br from-sky-400/12 via-slate-950/72 to-slate-950/82 p-4 shadow-[0_20px_44px_rgba(14,165,233,0.1)] transition hover:-translate-y-0.5 hover:border-sky-200/45 hover:shadow-[0_24px_52px_rgba(14,165,233,0.16)]"
                  : "group flex h-full flex-col rounded-[1.45rem] border border-white/10 bg-slate-950/50 p-4 transition hover:-translate-y-0.5 hover:border-sky-300/35 hover:bg-slate-950/72"
              }
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-[11px] uppercase tracking-[0.22em] text-slate-400">
                    {familyConfig?.chooserObjectiveLabel ?? ticker}
                  </div>
                  <h2 className="mt-2 text-xl font-semibold tracking-[-0.02em] text-slate-50">
                    {pilot ? `${pilot.company_name} (${pilot.ticker})` : ticker}
                  </h2>
                </div>
                <span
                  className={
                    isRecommended
                      ? "grid h-10 w-10 shrink-0 place-items-center rounded-full border border-sky-300/30 bg-sky-400/12 text-lg text-sky-100 transition group-hover:border-sky-200/45 group-hover:text-white"
                      : "grid h-10 w-10 shrink-0 place-items-center rounded-full border border-white/10 bg-white/5 text-lg text-slate-200 transition group-hover:border-sky-300/35 group-hover:text-white"
                  }
                  aria-hidden="true"
                >
                  →
                </span>
              </div>

              <p className="mt-4 text-sm leading-7 text-slate-100">
                {primaryLine}
              </p>

              <div className="mt-auto pt-5">
                <p className="text-sm leading-6 text-slate-300">
                  Best for: {supportLine}
                </p>
                <div className="mt-3 text-sm font-semibold text-slate-100 transition group-hover:text-white">
                  {`Open ${ticker}`}
                </div>
              </div>
            </Link>
          )
        })}
      </div>
    </section>
  )
}
