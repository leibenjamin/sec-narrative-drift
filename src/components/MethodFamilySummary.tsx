import { compactText } from "../lib/compactText"

export type MethodFamilyDetector = {
  id: string
  label: string
  question: string
  summary: string
}

export type MethodFamily = {
  title: string
  summary: string
  detectors: MethodFamilyDetector[]
}

type MethodFamilySummaryProps = {
  families: MethodFamily[]
}

export default function MethodFamilySummary({ families }: MethodFamilySummaryProps) {
  return (
    <section className="space-y-4 rounded-[1.55rem] border border-white/10 bg-slate-900/45 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.28em] text-slate-400">
            Method families
          </div>
          <h2 className="mt-2 text-2xl font-semibold text-slate-100">
            Deeper audit stays grouped below the workflow
          </h2>
        </div>
        <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-slate-300">
          Appendix layer
        </div>
      </div>

      <p className="max-w-3xl text-sm leading-6 text-slate-300">
        The workflow explains the route. These families stay below it for readers who want the audit shape.
      </p>

      <div className="grid gap-3 lg:grid-cols-3">
        {families.map((family) => (
          <article
            key={family.title}
            className="rounded-[1.25rem] border border-white/10 bg-slate-950/62 p-4"
          >
            <div className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Family</div>
            <h3 className="mt-2 text-lg font-semibold text-slate-100">{family.title}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-300">{compactText(family.summary, 116)}</p>

            <ul className="mt-4 space-y-2 border-t border-white/10 pt-3">
              {family.detectors.map((detector) => (
                <li
                  key={detector.id}
                  id={`detector-${detector.id}`}
                  className="scroll-mt-28"
                >
                  <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
                    {detector.question}
                  </div>
                  <p className="mt-1 text-sm leading-6 text-slate-200">
                    <span className="font-semibold text-slate-100">{detector.label}</span>
                    {" — "}
                    {compactText(detector.summary, 58)}
                  </p>
                </li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </section>
  )
}
