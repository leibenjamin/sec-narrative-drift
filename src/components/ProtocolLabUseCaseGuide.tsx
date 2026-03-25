import { Link } from "react-router-dom"
import {
  buildProtocolLabCaseHref,
  type ProtocolLabVisiblePilotEntry,
} from "../lib/protocolLabProductPositioning"

type ProtocolLabUseCaseGuideProps = {
  visiblePilots: ProtocolLabVisiblePilotEntry[]
  title?: string
  className?: string
}

type UseCaseRow = {
  objective: string
  ticker: "NVDA" | "KO" | "LLY"
  note: string
}

const USE_CASE_ROWS: UseCaseRow[] = [
  {
    objective: "Fastest strong signal",
    ticker: "NVDA",
    note: "Start with the clearest answer-first case.",
  },
  {
    objective: "Policy-heavy contrast",
    ticker: "LLY",
    note: "See how the protocol stays honest when the case remains intentionally bounded.",
  },
  {
    objective: "Restraint / skeptic check",
    ticker: "KO",
    note: "Check that the workflow stays useful on a mostly stable filing.",
  },
]

function resolveHref(
  visiblePilots: ProtocolLabVisiblePilotEntry[],
  ticker: UseCaseRow["ticker"]
): string {
  for (const pilot of visiblePilots) {
    if (pilot.ticker === ticker) return pilot.href
  }
  return buildProtocolLabCaseHref(ticker, 2024, 2025)
}

export default function ProtocolLabUseCaseGuide({
  visiblePilots,
  title = "Choose by objective",
  className = "",
}: ProtocolLabUseCaseGuideProps) {
  return (
    <section className={`rounded-xl border border-white/10 bg-slate-950/35 p-4 ${className}`.trim()}>
      <div className="text-xs uppercase tracking-[0.24em] text-slate-400">{title}</div>
      <div className="mt-3 space-y-2">
        {USE_CASE_ROWS.map((row) => (
          <Link
            key={row.objective}
            to={resolveHref(visiblePilots, row.ticker)}
            className="flex items-start justify-between gap-3 rounded-lg border border-white/10 bg-white/5 px-3 py-2 transition hover:border-white/20 hover:bg-white/8"
          >
            <div>
              <div className="text-sm font-medium text-slate-100">
                {row.objective}
              </div>
              <div className="mt-1 text-xs text-slate-300">{row.note}</div>
            </div>
            <span className="rounded-full border border-sky-300/30 bg-sky-400/12 px-2 py-0.5 text-[11px] text-sky-100">
              {row.ticker}
            </span>
          </Link>
        ))}
      </div>
    </section>
  )
}
