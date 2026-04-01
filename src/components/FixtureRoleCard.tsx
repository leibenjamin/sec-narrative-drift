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
    <article
      className={
        isPrimary
          ? "rounded-[1.35rem] border border-sky-300/30 bg-linear-to-br from-sky-400/14 via-slate-950/72 to-slate-950/84 p-4 shadow-[0_22px_44px_rgba(14,165,233,0.12)]"
          : "rounded-[1.35rem] border border-white/10 bg-slate-950/68 p-4"
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

      <div className="mt-4 flex items-center justify-between gap-3">
        <div className="text-[11px] uppercase tracking-[0.26em] text-slate-500">
          {isPrimary ? "Recommended first case" : "Pilot case"}
        </div>
        <Link
          to={href}
          className={
            isPrimary
              ? "text-sm font-semibold text-sky-100 transition hover:text-white"
              : "text-sm font-semibold text-slate-200 transition hover:text-white"
          }
        >
          {ctaLabel}
        </Link>
      </div>
    </article>
  )
}
