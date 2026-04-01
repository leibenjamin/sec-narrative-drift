import type {
  ProtocolLabPilotMatrixBundle,
  ProtocolLabSkepticCaseCanonizedMatrix,
} from "../lib/protocolLabMatrixTypes.ts"

type KORestraintStripProps = {
  bundle: ProtocolLabPilotMatrixBundle
  skepticCase: ProtocolLabSkepticCaseCanonizedMatrix
}

function compactText(text: string, maxLength = 150): string {
  const normalized = text.replace(/\s+/g, " ").trim()
  if (normalized.length <= maxLength) return normalized
  const clipped = normalized.slice(0, maxLength).trimEnd()
  const lastSpace = clipped.lastIndexOf(" ")
  return `${(lastSpace > 0 ? clipped.slice(0, lastSpace) : clipped).trimEnd()}...`
}

export default function KORestraintStrip({ bundle, skepticCase }: KORestraintStripProps) {
  return (
    <section
      id="lab-ko-restraint-strip"
      className="grid gap-2.5 rounded-[1.1rem] border border-emerald-300/20 bg-emerald-400/8 p-3 sm:grid-cols-3 sm:p-4"
    >
      <article className="rounded-[0.95rem] border border-white/10 bg-slate-950/34 p-3">
        <div className="text-[10px] uppercase tracking-[0.24em] text-emerald-100">Mostly stable</div>
        <p className="mt-2 text-sm leading-6 text-slate-100 text-clamp-3">
          {compactText(bundle.story.why_this_case_matters, 130)}
        </p>
      </article>

      <article className="rounded-[0.95rem] border border-white/10 bg-slate-950/34 p-3">
        <div className="text-[10px] uppercase tracking-[0.24em] text-slate-300">
          Selectively sharpened
        </div>
        <p className="mt-2 text-sm leading-6 text-slate-100 text-clamp-3">
          {compactText(skepticCase.finding_summary, 140)}
        </p>
      </article>

      <article className="rounded-[0.95rem] border border-white/10 bg-slate-950/34 p-3">
        <div className="text-[10px] uppercase tracking-[0.24em] text-slate-300">
          Why restraint matters
        </div>
        <p className="mt-2 text-sm leading-6 text-slate-100 text-clamp-3">
          {compactText(skepticCase.product_interpretation, 140)}
        </p>
      </article>
    </section>
  )
}
