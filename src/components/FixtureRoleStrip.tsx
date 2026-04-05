import { compactText } from "../lib/compactText"

export type FixtureRoleStripItem = {
  ticker: string
  role: string
  detail: string
}

type FixtureRoleStripProps = {
  items: FixtureRoleStripItem[]
}

function formatRoleList(roles: string[]): string {
  if (roles.length === 0) return "the approved route family"
  if (roles.length === 1) return roles[0]
  if (roles.length === 2) return `${roles[0]} and ${roles[1]}`
  return `${roles.slice(0, -1).join(", ")}, and ${roles[roles.length - 1]}`
}

export default function FixtureRoleStrip({ items }: FixtureRoleStripProps) {
  const roleSummary = formatRoleList(items.map((item) => item.role.toLowerCase()))

  return (
    <section className="rounded-[1.35rem] border border-white/10 bg-slate-950/42 p-3.5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-2xl">
          <div className="text-[11px] uppercase tracking-[0.28em] text-slate-400">
            Case roles
          </div>
          <p className="mt-1.5 text-sm leading-5 text-slate-300">
            Three cases are enough to show {roleSummary} without widening the public claim.
          </p>
        </div>
        <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-slate-300">
          NVDA / LLY / KO only
        </div>
      </div>

      <div className="mt-3 grid gap-2 md:grid-cols-3">
        {items.map((item) => (
          <article
            key={item.ticker}
            className="rounded-[1.1rem] border border-white/10 bg-slate-950/70 p-3"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-base font-semibold text-slate-50">{item.ticker}</div>
              </div>
              <span className="rounded-full border border-white/10 bg-white/5 px-2 py-1 text-[10px] tracking-[0.06em] text-slate-200">
                {item.role}
              </span>
            </div>
            <p className="mt-2 text-[13px] leading-5 text-slate-300">{compactText(item.detail, 84)}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
