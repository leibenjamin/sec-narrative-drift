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
      className="grid gap-2.5 rounded-[1.05rem] border border-emerald-300/18 bg-emerald-400/6 p-2.5 sm:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)] sm:p-3"
    >
      <article className="rounded-[0.95rem] border border-emerald-300/20 bg-slate-950/34 p-3">
        <div className="text-[10px] uppercase tracking-[0.24em] text-emerald-100">Mostly stable</div>
        <p className="mt-2 text-base font-semibold leading-6 text-slate-50">
          {compactText(bundle.story.why_this_case_matters, 146)}
        </p>
        <p className="mt-3 text-sm leading-6 text-slate-200">
          The filing is mostly stable, but the useful signal is still visible when restraint stays
          explicit.
        </p>
      </article>

      <div className="grid gap-2.5">
        <article className="rounded-[0.95rem] border border-white/10 bg-slate-950/34 p-2.5">
          <div className="text-[10px] uppercase tracking-[0.24em] text-slate-300">
            Selectively sharpened
          </div>
          <p className="mt-2 text-sm leading-5 text-slate-100 text-clamp-3">
            {compactText(skepticCase.finding_summary, 112)}
          </p>
        </article>

        <article className="rounded-[0.95rem] border border-white/10 bg-slate-950/34 p-2.5">
          <div className="text-[10px] uppercase tracking-[0.24em] text-slate-300">
            Why restraint matters
          </div>
          <p className="mt-2 text-sm leading-5 text-slate-100 text-clamp-3">
            {compactText(skepticCase.product_interpretation, 112)}
          </p>
        </article>
      </div>
    </section>
  )
}
