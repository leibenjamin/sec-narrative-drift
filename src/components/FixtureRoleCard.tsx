import { Link } from "react-router-dom"

type FixtureRoleCardProps = {
  ticker: string
  companyName: string
  roleLabel: string
  demonstration: string
  href: string
  ctaLabel: string
  emphasis?: "primary" | "default"
}

export default function FixtureRoleCard({
  ticker,
  companyName,
  roleLabel,
  demonstration,
  href,
  ctaLabel,
  emphasis = "default",
}: FixtureRoleCardProps) {
  const isPrimary = emphasis === "primary"

  return (
    <Link
      to={href}
      className={
        isPrimary
          ? "group block rounded-[1.35rem] border border-sky-300/30 bg-linear-to-br from-sky-400/14 via-slate-950/72 to-slate-950/84 p-4 shadow-[0_22px_44px_rgba(14,165,233,0.12)] transition hover:-translate-y-0.5 hover:border-sky-200/45 hover:shadow-[0_24px_52px_rgba(14,165,233,0.18)]"
          : "group block rounded-[1.35rem] border border-white/10 bg-slate-950/68 p-4 transition hover:-translate-y-0.5 hover:border-sky-300/28 hover:bg-slate-950/84"
      }
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-base font-semibold text-slate-50">{ticker}</div>
          <div className="text-[13px] text-slate-400">{companyName}</div>
        </div>
        <span
          className={
            isPrimary
              ? "rounded-full border border-sky-300/30 bg-sky-400/14 px-2.5 py-1 text-[11px] uppercase tracking-[0.18em] text-sky-100"
              : "rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] uppercase tracking-[0.18em] text-slate-200"
          }
        >
          {roleLabel}
        </span>
      </div>

      <p className="mt-3 text-sm leading-5 text-slate-200">{demonstration}</p>

      <div className="mt-4 flex items-center justify-between gap-3 border-t border-white/10 pt-3">
        <div className="text-[11px] uppercase tracking-[0.24em] text-slate-500">
          {isPrimary ? "Recommended first case" : "Pilot case"}
        </div>
        <span
          className={
            isPrimary
              ? "inline-flex items-center gap-2 rounded-full border border-sky-300/30 bg-sky-400/12 px-3 py-1.5 text-sm font-semibold text-sky-100 transition group-hover:border-sky-200/50 group-hover:text-white"
              : "inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/5 px-3 py-1.5 text-sm font-semibold text-slate-100 transition group-hover:border-sky-300/28 group-hover:text-white"
          }
        >
          {ctaLabel}
          <span aria-hidden="true" className="text-base leading-none transition group-hover:translate-x-0.5">
            →
          </span>
        </span>
      </div>
    </Link>
  )
}
