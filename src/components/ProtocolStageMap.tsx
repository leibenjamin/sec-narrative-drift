import { Fragment } from "react"

export type ProtocolStageStep = {
  title: string
  detail: string
  chips: string[]
}

type ProtocolStageMapProps = {
  steps: ProtocolStageStep[]
}

export default function ProtocolStageMap({ steps }: ProtocolStageMapProps) {
  return (
    <section className="relative overflow-hidden rounded-[1.55rem] border border-white/10 bg-slate-950/55 p-4 shadow-[0_22px_48px_rgba(2,6,23,0.28)] sm:p-5">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.14),transparent_48%),linear-gradient(135deg,rgba(8,13,26,0.16),rgba(8,13,26,0))]" />
      <div className="relative">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="text-[11px] uppercase tracking-[0.32em] text-slate-400">Protocol map</div>
          <div className="text-[11px] uppercase tracking-[0.22em] text-slate-400">
            claim {"->"} prove {"->"} stop
          </div>
        </div>

        <div className="mt-4 grid gap-2 md:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)_auto_minmax(0,1fr)] md:items-stretch">
          {steps.map((step, index) => (
            <Fragment key={step.title}>
              <article className="relative overflow-hidden rounded-[1.15rem] border border-white/10 bg-slate-950/72 px-3.5 py-3.5">
                <div className="flex items-center gap-2.5">
                  <div className="grid h-8 w-8 place-items-center rounded-full border border-sky-300/25 bg-sky-400/12 text-[11px] font-semibold tracking-[0.22em] text-sky-100">
                    {`0${index + 1}`}
                  </div>
                  <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
                    {step.chips[0]}
                  </div>
                </div>

                <div className="mt-3 text-[1.45rem] font-semibold tracking-[-0.03em] text-slate-50 sm:text-[1.7rem]">
                  {step.title}
                </div>
                <p className="mt-1.5 text-[13px] leading-5 text-slate-300">{step.detail}</p>
              </article>

              {index < steps.length - 1 ? (
                <div
                  aria-hidden="true"
                  className="hidden items-center justify-center px-1 md:flex"
                >
                  <div className="h-px w-10 bg-linear-to-r from-sky-300/40 to-emerald-200/30" />
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
