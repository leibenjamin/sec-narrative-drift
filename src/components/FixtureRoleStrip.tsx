export type FixtureRoleStripItem = {
  ticker: string
  role: string
  detail: string
}

type FixtureRoleStripProps = {
  items: FixtureRoleStripItem[]
}

export default function FixtureRoleStrip({ items }: FixtureRoleStripProps) {
  return (
    <section className="rounded-[1.35rem] border border-white/10 bg-slate-950/42 p-3.5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-2xl">
          <div className="text-[11px] uppercase tracking-[0.28em] text-slate-400">
            Visible fixture roles
          </div>
          <p className="mt-1.5 text-sm leading-5 text-slate-300">
            Three visible fixtures are enough to show vivid change, honest stop, and low-drift
            restraint without widening the public pilot claim.
          </p>
        </div>
        <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-slate-300">
          NVDA / LLY / KO only
        </div>
      </div>

      <div className="mt-3 grid gap-2.5 md:grid-cols-3">
        {items.map((item) => (
          <article
            key={item.ticker}
            className="rounded-[1.1rem] border border-white/10 bg-slate-950/70 p-3"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-base font-semibold text-slate-50">{item.ticker}</div>
                <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500">Role</div>
              </div>
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] text-slate-200">
                {item.role}
              </span>
            </div>
            <p className="mt-2 text-sm leading-5 text-slate-300">{item.detail}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
