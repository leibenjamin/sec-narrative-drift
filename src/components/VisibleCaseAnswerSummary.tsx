import type {
  ProtocolLabEffortRobustnessBundle,
  ProtocolLabNoveltyLedgerCase,
  ProtocolLabPilotMatrixBundle,
  ProtocolLabPilotMatrixCell,
} from "../lib/protocolLabMatrixTypes.ts"
import { compactText } from "../lib/compactText"

type VisibleCaseAnswerSummaryProps = {
  bundle: ProtocolLabPilotMatrixBundle
  noveltyLedger: ProtocolLabNoveltyLedgerCase | null
  effortRobustness: ProtocolLabEffortRobustnessBundle | null
}

function getPrimaryCell(bundle: ProtocolLabPilotMatrixBundle): ProtocolLabPilotMatrixCell | null {
  return (
    bundle.cells_by_id[bundle.matrix.selected_default_cell_id] ??
    bundle.ordered_cells[0] ??
    null
  )
}

function formatSurfaceCoverageLabel(props: {
  noveltyLedger: ProtocolLabNoveltyLedgerCase | null
  effortRobustness: ProtocolLabEffortRobustnessBundle | null
}): string {
  const parts = ["the primary read"]

  if (props.noveltyLedger) {
    parts.push("the fresh-vs-reused cue")
  }

  if (props.effortRobustness) {
    parts.push("the matched-effort check")
  }

  if (parts.length === 1) {
    return parts[0]
  }

  if (parts.length === 2) {
    return `${parts[0]} and ${parts[1]}`
  }

  return `${parts.slice(0, -1).join(", ")}, and ${parts[parts.length - 1]}`
}

export default function VisibleCaseAnswerSummary({
  bundle,
  noveltyLedger,
  effortRobustness,
}: VisibleCaseAnswerSummaryProps) {
  const primaryCell = getPrimaryCell(bundle)
  const primarySummary = compactText(primaryCell?.summary ?? bundle.story.investor_read, 340)
  const matterSummary = compactText(bundle.story.investor_read, 240)
  const surfaceCoverage = formatSurfaceCoverageLabel({ noveltyLedger, effortRobustness })

  return (
    <section
      id="lab-visible-case-answer"
      className="space-y-3 rounded-[1.35rem] border border-sky-300/20 bg-linear-to-br from-sky-400/12 via-slate-950/78 to-slate-950/40 p-4 shadow-[0_18px_40px_rgba(2,6,23,0.2)] sm:space-y-4 sm:p-5"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <div className="text-[11px] uppercase tracking-[0.24em] text-sky-100">Filing answer</div>
          <h2 className="text-lg font-semibold text-slate-50 sm:text-xl">LLY filing answer</h2>
        </div>
        <span className="rounded-full border border-sky-300/25 bg-sky-400/10 px-2.5 py-1 text-[11px] text-sky-100">
          Honest stop
        </span>
      </div>

      <div className="flex flex-wrap gap-1.5 text-[11px] text-slate-200 sm:gap-2">
        <span className="rounded-full border border-sky-300/25 bg-sky-400/10 px-2.5 py-1 sm:px-3">
          Basis: {primaryCell?.short_label ?? "Primary read"}
        </span>
        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 sm:px-3">
          Pilot case
        </span>
        {noveltyLedger ? (
          <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 sm:px-3">
            Fresh vs reused
          </span>
        ) : null}
        {effortRobustness ? (
          <span className="rounded-full border border-amber-300/25 bg-amber-400/10 px-2.5 py-1 sm:px-3">
            Integrity caveat
          </span>
        ) : null}
      </div>

      <div className="grid gap-3 sm:gap-4 lg:grid-cols-2">
        <article className="rounded-[1.1rem] border border-sky-300/20 bg-slate-950/35 p-3 sm:p-4">
          <div className="text-[10px] uppercase tracking-[0.24em] text-sky-100">What changed</div>
          <p className="mt-2.5 text-sm leading-6 text-slate-100">{primarySummary}</p>
        </article>

        <article className="rounded-[1.1rem] border border-emerald-300/20 bg-slate-950/35 p-3 sm:p-4">
          <div className="text-[10px] uppercase tracking-[0.24em] text-emerald-100">Why it matters</div>
          <p className="mt-2.5 text-sm leading-6 text-slate-100">
            Supported by {surfaceCoverage}. {matterSummary}
          </p>
        </article>
      </div>
    </section>
  )
}
