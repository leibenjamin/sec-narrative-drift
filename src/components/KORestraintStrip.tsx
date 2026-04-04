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
      className="grid gap-3 rounded-[1.1rem] border border-emerald-300/18 bg-emerald-400/6 p-3 sm:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]"
    >
      <article className="rounded-2xl border border-emerald-300/20 bg-slate-950/34 p-4">
        <div className="text-[10px] uppercase tracking-[0.24em] text-emerald-100">Main takeaway</div>
        <p className="mt-2 text-lg font-semibold leading-7 text-slate-50">
          {compactText(bundle.story.why_this_case_matters, 132)}
        </p>
        <p className="mt-3 text-sm leading-6 text-slate-200">
          The filing is mostly stable, so the route earns trust only if restraint stays explicit.
        </p>
      </article>

      <div className="grid gap-2.5">
        <article className="rounded-[0.95rem] border border-white/10 bg-slate-950/34 p-3">
          <div className="text-[10px] uppercase tracking-[0.24em] text-slate-300">
            Selectively sharpened
          </div>
          <p className="mt-2 text-sm leading-5 text-slate-100 text-clamp-3">
            {compactText(skepticCase.finding_summary, 92)}
          </p>
        </article>

        <article className="rounded-[0.95rem] border border-white/10 bg-slate-950/34 p-3">
          <div className="text-[10px] uppercase tracking-[0.24em] text-slate-300">
            Why restraint matters
          </div>
          <p className="mt-2 text-sm leading-5 text-slate-100 text-clamp-3">
            {compactText(skepticCase.product_interpretation, 92)}
          </p>
        </article>
      </div>
    </section>
  )
}
