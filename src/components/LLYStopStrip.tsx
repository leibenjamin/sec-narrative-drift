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
      className="space-y-2.5 rounded-[1.25rem] border border-amber-300/25 bg-linear-to-r from-amber-400/12 via-slate-950/78 to-slate-950/45 p-3.5 shadow-[0_18px_36px_rgba(15,23,42,0.22)] sm:p-4"
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

      <div className="grid gap-2.5 lg:grid-cols-[minmax(0,1.12fr)_minmax(0,0.88fr)]">
        <article className="rounded-2xl border border-amber-300/22 bg-amber-400/10 p-4">
          <div className="text-[10px] uppercase tracking-[0.24em] text-amber-100">Stop signal</div>
          <p className="mt-2 text-lg font-semibold leading-7 text-slate-50 sm:text-xl">
            Stop at the explicit boundary before the public route pretends to broader certainty.
          </p>
          <p className="mt-3 text-sm leading-6 text-slate-100">{compactText(disciplinedStop, 220)}</p>
        </article>

        <div className="grid gap-2.5">
          <article className="rounded-2xl border border-white/10 bg-slate-950/36 p-3">
            <div className="text-[10px] uppercase tracking-[0.24em] text-slate-300">Available here</div>
            <div className="mt-2 flex flex-wrap gap-1.5 text-[11px] text-slate-100">
              {availableParts.map((part) => (
                <span
                  key={part}
                  className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1"
                >
                  {part}
                </span>
              ))}
            </div>
          </article>

          <article className="rounded-2xl border border-white/10 bg-slate-950/36 p-3">
            <div className="text-[10px] uppercase tracking-[0.24em] text-slate-300">
              Intentionally not shown
            </div>
            <p className="mt-2 text-sm leading-5 text-slate-100">
              No lower audit stack, broader benchmark claim, or deeper multi-panel route ships on the
              public LLY page.
            </p>
          </article>
        </div>
      </div>
    </section>
  )
}
