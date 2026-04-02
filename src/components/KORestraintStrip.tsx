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
      className="grid gap-2 rounded-[1.05rem] border border-emerald-300/18 bg-emerald-400/6 p-2.5 sm:grid-cols-3 sm:p-3"
    >
      <article className="rounded-[0.95rem] border border-white/10 bg-slate-950/34 p-2.5">
        <div className="text-[10px] uppercase tracking-[0.24em] text-emerald-100">Mostly stable</div>
        <p className="mt-2 text-sm leading-5 text-slate-100 text-clamp-3">
          {compactText(bundle.story.why_this_case_matters, 120)}
        </p>
      </article>

      <article className="rounded-[0.95rem] border border-white/10 bg-slate-950/34 p-2.5">
        <div className="text-[10px] uppercase tracking-[0.24em] text-slate-300">
          Selectively sharpened
        </div>
        <p className="mt-2 text-sm leading-5 text-slate-100 text-clamp-3">
          {compactText(skepticCase.finding_summary, 128)}
        </p>
      </article>

      <article className="rounded-[0.95rem] border border-white/10 bg-slate-950/34 p-2.5">
        <div className="text-[10px] uppercase tracking-[0.24em] text-slate-300">
          Why restraint matters
        </div>
        <p className="mt-2 text-sm leading-5 text-slate-100 text-clamp-3">
          {compactText(skepticCase.product_interpretation, 128)}
        </p>
      </article>
    </section>
  )
}
