import { Fragment } from "react"

export type WorkflowAnatomyStage = {
  title: string
  detail: string
  chip: string
  discipline: string
  tone: "source" | "claim" | "proof" | "stop" | "audit"
}

type WorkflowAnatomyDiagramProps = {
  stages: WorkflowAnatomyStage[]
}

const TONE_STYLES: Record<WorkflowAnatomyStage["tone"], string> = {
  source: "text-slate-300",
  claim: "text-sky-100",
  proof: "text-emerald-100",
  stop: "text-amber-100",
  audit: "text-slate-300",
}

export default function WorkflowAnatomyDiagram({
  stages,
}: WorkflowAnatomyDiagramProps) {
  return (
    <section className="relative overflow-hidden rounded-[1.7rem] border border-white/10 bg-slate-950/55 p-3 shadow-[0_24px_52px_rgba(2,6,23,0.3)] sm:p-4">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.13),transparent_52%),linear-gradient(135deg,rgba(8,13,26,0.18),rgba(8,13,26,0))]" />
      <div className="relative">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="text-[11px] uppercase tracking-[0.32em] text-slate-400">
            Workflow anatomy
          </div>
          <div className="hidden text-[11px] uppercase tracking-[0.18em] text-slate-400 sm:block">
            claim {"->"} proof {"->"} stop {"->"} appendix
          </div>
        </div>

        <div className="mt-3 grid gap-2 lg:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)_auto_minmax(0,1fr)_auto_minmax(0,1fr)_auto_minmax(0,1fr)] lg:items-stretch">
          {stages.map((stage, index) => (
            <Fragment key={stage.title}>
              <article className="relative overflow-hidden rounded-[1.05rem] border border-white/10 bg-slate-950/78 px-3 py-3">
                <div className="flex items-center gap-2">
                  <div className="grid h-7 w-7 place-items-center rounded-full border border-white/10 bg-white/5 text-[10px] font-semibold tracking-[0.22em] text-slate-100">
                    {`0${index + 1}`}
                  </div>
                  <span className={`text-[10px] uppercase tracking-[0.22em] ${TONE_STYLES[stage.tone]}`}>
                    {stage.chip}
                  </span>
                </div>

                <div className="mt-3 text-base font-semibold text-slate-50">
                  {stage.title}
                </div>
                <p className="mt-1.5 text-[13px] leading-5 text-slate-300">{stage.detail}</p>
                <div className="mt-2 text-[11px] uppercase tracking-[0.22em] text-slate-500">
                  {stage.discipline}
                </div>
              </article>

              {index < stages.length - 1 ? (
                <div aria-hidden="true" className="hidden items-center justify-center px-1 lg:flex">
                  <div className="h-px w-7 bg-linear-to-r from-sky-300/40 to-emerald-200/30" />
                  <div className="ml-2 h-2.5 w-2.5 rotate-45 border-r border-t border-sky-200/60" />
                </div>
              ) : null}
            </Fragment>
          ))}
        </div>
      </div>
    </section>
  )
}
