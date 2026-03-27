import { Link } from "react-router-dom"
import {
  buildProtocolLabCaseHref,
  type ProtocolLabVisiblePilotEntry,
} from "../lib/protocolLabProductPositioning"

type ProtocolLabUseCaseGuideProps = {
  visiblePilots: ProtocolLabVisiblePilotEntry[]
  title?: string
  description?: string
  className?: string
}

type UseCaseRow = {
  objective: string
  ticker: "NVDA" | "KO" | "LLY"
}

const USE_CASE_ROWS: UseCaseRow[] = [
  {
    objective: "Strongest first signal",
    ticker: "NVDA",
  },
  {
    objective: "Policy-heavy bounded contrast",
    ticker: "LLY",
  },
  {
    objective: "Restraint / low-drift honesty check",
    ticker: "KO",
  },
]

function resolvePilot(
  visiblePilots: ProtocolLabVisiblePilotEntry[],
  ticker: UseCaseRow["ticker"]
): ProtocolLabVisiblePilotEntry | null {
  for (const pilot of visiblePilots) {
    if (pilot.ticker === ticker) return pilot
  }
  return null
}

function resolveHref(
  visiblePilots: ProtocolLabVisiblePilotEntry[],
  ticker: UseCaseRow["ticker"]
): string {
  const pilot = resolvePilot(visiblePilots, ticker)
  if (pilot) return pilot.href
  return buildProtocolLabCaseHref(ticker, 2024, 2025)
}

export default function ProtocolLabUseCaseGuide({
  visiblePilots,
  title = "Choose by goal",
  description = "Each option below is a fixed protocol-demo fixture.",
  className = "",
}: ProtocolLabUseCaseGuideProps) {
  return (
    <section className={`rounded-[1.4rem] border border-white/10 bg-slate-900/45 p-5 ${className}`.trim()}>
      <div className="text-xs uppercase tracking-[0.24em] text-slate-400">{title}</div>
      <p className="mt-2 max-w-3xl text-sm text-slate-300">{description}</p>
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        {USE_CASE_ROWS.map((row) => {
          const pilot = resolvePilot(visiblePilots, row.ticker)
          return (
            <Link
              key={row.objective}
              to={resolveHref(visiblePilots, row.ticker)}
              className="block rounded-[1.2rem] border border-white/10 bg-slate-950/35 p-4 transition hover:border-sky-300/35 hover:bg-slate-950/55"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-slate-400">
                    {row.objective}
                  </div>
                  <h2 className="mt-2 text-base font-semibold text-slate-50">
                    {pilot ? `${pilot.company_name} (${pilot.ticker})` : row.ticker}
                  </h2>
                </div>
                <span className="rounded-full border border-sky-300/30 bg-sky-400/12 px-2 py-0.5 text-[11px] text-sky-100">
                  {pilot?.role_label ?? row.objective}
                </span>
              </div>

              <p className="mt-4 text-sm text-slate-100">
                {pilot?.why_case_exists ?? "Open the current fixture for this pilot role."}
              </p>

              <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-3">
                <div className="text-[11px] uppercase tracking-wide text-slate-400">
                  What this fixture proves
                </div>
                <p className="mt-2 text-sm text-slate-100">
                  {pilot?.guidance.what_you_learn ?? "Current pilot guidance is unavailable."}
                </p>
              </div>

              <div className="mt-4 flex items-center justify-between gap-3 text-xs text-slate-300">
                <span>{pilot?.guidance.why_pick ?? "Open this fixture."}</span>
                <span className="text-sky-200">{`Open ${row.ticker}`}</span>
              </div>
            </Link>
          )
        })}
      </div>
    </section>
  )
}
