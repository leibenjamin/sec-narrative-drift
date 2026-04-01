import type {
  ProtocolLabEffortRobustnessBundle,
  ProtocolLabNoveltyLedgerCase,
  ProtocolLabPilotMatrixBundle,
} from "../lib/protocolLabMatrixTypes.ts"

type LLYStopStripProps = {
  bundle: ProtocolLabPilotMatrixBundle
  noveltyLedger: ProtocolLabNoveltyLedgerCase | null
  effortRobustness: ProtocolLabEffortRobustnessBundle | null
}

function compactText(text: string, maxLength = 150): string {
  const normalized = text.replace(/\s+/g, " ").trim()
  if (normalized.length <= maxLength) return normalized
  const clipped = normalized.slice(0, maxLength).trimEnd()
  const lastSpace = clipped.lastIndexOf(" ")
  return `${(lastSpace > 0 ? clipped.slice(0, lastSpace) : clipped).trimEnd()}...`
}

export default function LLYStopStrip({
  bundle,
  noveltyLedger,
  effortRobustness,
}: LLYStopStripProps) {
  const availableParts = [
    "Bounded filing answer",
    "Protocol meaning preview",
    noveltyLedger ? "Fresh vs reused cue" : null,
    effortRobustness ? "Matched-effort integrity check" : null,
  ].filter((value): value is string => Boolean(value))

  const disciplinedStop = effortRobustness?.case_artifact.caveat ?? bundle.story.caveat

  return (
    <section
      id="lab-lly-stop-strip"
      className="space-y-3 rounded-[1.25rem] border border-amber-300/25 bg-linear-to-r from-amber-400/12 via-slate-950/78 to-slate-950/45 p-4 shadow-[0_18px_36px_rgba(15,23,42,0.22)] sm:p-5"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1.5">
          <p className="text-[11px] uppercase tracking-[0.24em] text-amber-100">Honest stop</p>
          <h2 className="text-lg font-semibold text-slate-50 sm:text-xl">Scope boundary, designed early</h2>
        </div>
        <span className="rounded-full border border-amber-300/25 bg-amber-400/12 px-2.5 py-1 text-[11px] text-amber-100">
          Stop here on purpose
        </span>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <article className="rounded-[1rem] border border-white/10 bg-slate-950/36 p-3">
          <div className="text-[10px] uppercase tracking-[0.24em] text-slate-300">Available here</div>
          <p className="mt-2 text-sm leading-6 text-slate-100">{availableParts.join(" • ")}</p>
        </article>

        <article className="rounded-[1rem] border border-white/10 bg-slate-950/36 p-3">
          <div className="text-[10px] uppercase tracking-[0.24em] text-slate-300">
            Intentionally not shown
          </div>
          <p className="mt-2 text-sm leading-6 text-slate-100">
            Full lower-audit runtime stacks, broader benchmark claims, and a deeper multi-panel route
            do not ship on the public LLY page.
          </p>
        </article>

        <article className="rounded-[1rem] border border-amber-300/20 bg-amber-400/10 p-3">
          <div className="text-[10px] uppercase tracking-[0.24em] text-amber-100">
            Why this stop is disciplined
          </div>
          <p className="mt-2 text-sm leading-6 text-slate-100">{compactText(disciplinedStop, 170)}</p>
        </article>
      </div>
    </section>
  )
}
