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
          ? "group relative flex h-full flex-col rounded-[1.45rem] border border-sky-300/28 bg-linear-to-br from-sky-400/14 via-slate-950/72 to-slate-950/82 p-4 shadow-[0_22px_44px_rgba(14,165,233,0.12)] transition hover:-translate-y-0.5 hover:border-sky-200/45 hover:shadow-[0_24px_52px_rgba(14,165,233,0.18)]"
          : "group relative flex h-full flex-col rounded-[1.45rem] border border-white/10 bg-slate-950/72 p-4 transition hover:-translate-y-0.5 hover:border-sky-300/28 hover:bg-slate-950/84"
      }
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div
            className={
              isPrimary
                ? "text-[11px] uppercase tracking-[0.22em] text-sky-100"
                : "text-[11px] uppercase tracking-[0.22em] text-slate-300"
            }
          >
            {roleLabel}
          </div>
          <div className="mt-2 text-[1.35rem] font-semibold tracking-[-0.03em] text-slate-50">
            {ticker}
          </div>
          <div className="text-sm text-slate-400">{companyName}</div>
        </div>
        <span
          className={
            isPrimary
              ? "grid h-10 w-10 shrink-0 place-items-center rounded-full border border-sky-300/30 bg-sky-400/12 text-lg text-sky-100 transition group-hover:border-sky-200/50 group-hover:text-white"
              : "grid h-10 w-10 shrink-0 place-items-center rounded-full border border-white/10 bg-white/5 text-lg text-slate-200 transition group-hover:border-sky-300/28 group-hover:text-white"
          }
          aria-hidden="true"
        >
          →
        </span>
      </div>

      <p className="mt-4 max-w-xs text-sm leading-6 text-slate-100">{demonstration}</p>

      <div className="mt-auto flex items-end justify-between gap-3 pt-5">
        <div className="text-[11px] uppercase tracking-[0.24em] text-slate-500">
          {isPrimary ? "Recommended first case" : "Pilot case"}
        </div>
        <span className="text-sm font-semibold text-slate-100 transition group-hover:text-white">
          {ctaLabel}
        </span>
      </div>
    </Link>
  )
}
