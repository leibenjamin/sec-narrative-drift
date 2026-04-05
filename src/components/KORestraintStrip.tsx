import type {
  ProtocolLabPilotMatrixBundle,
  ProtocolLabSkepticCaseCanonizedMatrix,
} from "../lib/protocolLabMatrixTypes.ts"
import { compactText } from "../lib/compactText"

type KORestraintStripProps = {
  bundle: ProtocolLabPilotMatrixBundle
  skepticCase: ProtocolLabSkepticCaseCanonizedMatrix
}

export default function KORestraintStrip({ bundle, skepticCase }: KORestraintStripProps) {
  return (
    <section
      id="lab-ko-restraint-strip"
      className="space-y-3 rounded-[1.1rem] border border-emerald-300/16 bg-emerald-400/5 p-3"
    >
      <article className="rounded-[1.1rem] border border-emerald-300/18 bg-slate-950/30 p-4">
        <div className="text-[10px] uppercase tracking-[0.24em] text-emerald-100">
          Restraint takeaway
        </div>
        <p className="mt-2 text-base font-semibold leading-7 text-slate-50 sm:text-[1.05rem]">
          {compactText(bundle.story.why_this_case_matters, 108)}
        </p>
        <p className="mt-3 text-sm leading-6 text-slate-200">
          The filing is mostly stable, so trust comes from keeping the visible read selective and calm.
        </p>
      </article>

      <article className="rounded-2xl border border-white/8 bg-slate-950/22 p-3.5">
        <div className="text-[10px] uppercase tracking-[0.24em] text-slate-300">
          Selective sharpening
        </div>
        <p className="mt-2 text-sm leading-5 text-slate-100">
          {compactText(skepticCase.finding_summary, 108)}
        </p>
      </article>
    </section>
  )
}
