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
    <section className="protocol-stage-map relative overflow-hidden rounded-[1.7rem] border border-white/10 bg-slate-950/62 p-4 shadow-[0_26px_60px_rgba(2,6,23,0.24)] sm:p-5">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.16),transparent_44%),linear-gradient(135deg,rgba(8,13,26,0.08),rgba(8,13,26,0))]" />
      <div className="relative">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="text-[11px] uppercase tracking-[0.32em] text-slate-400">Protocol map</div>
            <h3 className="mt-2 text-lg font-semibold tracking-[-0.03em] text-slate-50 sm:text-xl">
              Claim, prove, stop.
            </h3>
          </div>
          <div className="text-[11px] uppercase tracking-[0.22em] text-slate-400">
            claim {"->"} prove {"->"} stop
          </div>
        </div>

        <div className="protocol-stage-map__sequence mt-5 grid gap-3 md:grid-cols-3">
          {steps.map((step, index) => (
            <article
              key={step.title}
              className="protocol-stage-map__step relative overflow-hidden rounded-[1.25rem] border border-white/10 bg-slate-950/78 px-4 py-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-2">
                  <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full border border-sky-300/25 bg-sky-400/12 text-[11px] font-semibold tracking-[0.22em] text-sky-100">
                    {`0${index + 1}`}
                  </div>
                  <div className="max-w-[11ch] text-[11px] leading-4 uppercase tracking-[0.24em] text-slate-400">
                    {step.chips[0]}
                  </div>
                </div>
                <div
                  aria-hidden="true"
                  className="protocol-stage-map__step-dot mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-sky-300/80"
                />
              </div>

              <div className="mt-4 text-[1.45rem] font-semibold tracking-[-0.03em] text-slate-50 sm:text-[1.7rem]">
                {step.title}
              </div>
              <p className="mt-2 max-w-[24ch] text-sm leading-6 text-slate-300">{step.detail}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}
