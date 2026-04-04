import type {
  ProtocolLabEffortRobustnessBundle,
  ProtocolLabNoveltyLedgerCase,
  ProtocolLabPilotMatrixBundle,
} from "../lib/protocolLabMatrixTypes.ts"
import { compactText } from "../lib/compactText"

type LLYStopStripProps = {
  bundle: ProtocolLabPilotMatrixBundle
  noveltyLedger: ProtocolLabNoveltyLedgerCase | null
  effortRobustness: ProtocolLabEffortRobustnessBundle | null
}

export default function LLYStopStrip({
  bundle,
  noveltyLedger,
  effortRobustness,
}: LLYStopStripProps) {
  const availableParts = [
    "Filing answer",
    "Protocol meaning",
    noveltyLedger ? "Fresh vs reused" : null,
    effortRobustness ? "Integrity check" : null,
  ].filter((value): value is string => Boolean(value))

  const disciplinedStop = effortRobustness?.case_artifact.caveat ?? bundle.story.caveat

  return (
    <section
      id="lab-lly-stop-strip"
      className="space-y-3 rounded-[1.25rem] border border-amber-300/25 bg-linear-to-r from-amber-400/12 via-slate-950/78 to-slate-950/45 p-3.5 shadow-[0_18px_36px_rgba(15,23,42,0.22)] sm:p-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1.5">
          <p className="text-[11px] uppercase tracking-[0.24em] text-amber-100">Honest stop</p>
          <h2 className="text-lg font-semibold text-slate-50 sm:text-xl">Scope boundary, kept visible</h2>
        </div>
        <span className="rounded-full border border-amber-300/25 bg-amber-400/12 px-2.5 py-1 text-[11px] text-amber-100">
          Stop here on purpose
        </span>
      </div>

      <article className="rounded-2xl border border-amber-300/22 bg-amber-400/10 p-4 sm:p-5">
        <div className="text-[10px] uppercase tracking-[0.24em] text-amber-100">Stop signal</div>
        <p className="mt-2 text-[1.35rem] font-semibold leading-tight text-slate-50 sm:text-[1.7rem]">
          Stop here on purpose before the public route pretends to broader certainty.
        </p>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-100">
          {compactText(disciplinedStop, 170)}
        </p>

        <div className="mt-4 grid gap-2.5 text-sm leading-6 text-slate-200 sm:grid-cols-[auto_1fr]">
          <div className="text-[10px] uppercase tracking-[0.24em] text-slate-300">Shown here</div>
          <p>{availableParts.join(", ")}.</p>
          <div className="text-[10px] uppercase tracking-[0.24em] text-slate-300">Not shown</div>
          <p>No lower audit stack, broader benchmark claim, or deeper multi-panel public route.</p>
        </div>
      </article>
    </section>
  )
}
