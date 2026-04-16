import { Link } from "react-router-dom"

type FixtureRoleCardProps = {
  ticker: string
  companyName: string
  roleLabel: string
  description: string
  href: string
  ctaLabel: string
  bestFor?: string | null
  emphasis?: "primary" | "default"
  variant?: "home" | "cases"
}

export default function FixtureRoleCard({
  ticker,
  companyName,
  roleLabel,
  description,
  href,
  ctaLabel,
  bestFor = null,
  emphasis = "default",
  variant = "home",
}: FixtureRoleCardProps) {
  const isPrimary = emphasis === "primary"
  const isCases = variant === "cases"
  const linkClassName = isCases
    ? isPrimary
      ? "group relative flex h-full flex-col rounded-[1.55rem] border border-sky-300/34 bg-linear-to-br from-sky-400/15 via-slate-950/80 to-slate-950/92 p-4 shadow-[0_22px_48px_rgba(14,165,233,0.12)] transition duration-150 hover:-translate-y-0.5 hover:border-sky-200/55 hover:shadow-[0_28px_60px_rgba(14,165,233,0.18)] focus-visible:border-sky-200/70 active:translate-y-px sm:p-5"
      : "group relative flex h-full flex-col rounded-[1.55rem] border border-white/14 bg-slate-950/78 p-4 shadow-[0_18px_38px_rgba(2,6,23,0.18)] transition duration-150 hover:-translate-y-0.5 hover:border-sky-300/40 hover:bg-slate-950/90 focus-visible:border-sky-300/55 active:translate-y-px sm:p-5"
    : isPrimary
      ? "fixture-role-card--home fixture-role-card--primary group relative flex h-full min-h-[19rem] flex-col overflow-hidden rounded-[1.6rem] border border-sky-300/34 bg-linear-to-br from-sky-400/18 via-slate-950/82 to-slate-950/96 p-5 shadow-[0_24px_56px_rgba(14,165,233,0.16)] transition duration-200 hover:-translate-y-1 hover:border-sky-200/58 hover:shadow-[0_34px_80px_rgba(14,165,233,0.24)] focus-visible:border-sky-200/70 active:translate-y-px sm:p-5"
      : "fixture-role-card--home group relative flex h-full min-h-[19rem] flex-col overflow-hidden rounded-[1.6rem] border border-white/14 bg-slate-950/82 p-5 shadow-[0_20px_42px_rgba(2,6,23,0.24)] transition duration-200 hover:-translate-y-1 hover:border-sky-300/42 hover:bg-slate-950/92 hover:shadow-[0_30px_70px_rgba(2,6,23,0.3)] focus-visible:border-sky-300/55 active:translate-y-px sm:p-5"
  const tickerClassName = isCases
    ? "mt-3 text-[1.75rem] leading-none font-semibold tracking-[-0.04em] text-slate-50 sm:text-[1.95rem]"
    : "mt-3 text-[1.95rem] leading-none font-semibold tracking-[-0.05em] text-slate-50 sm:text-[2.2rem]"
  const descriptionClassName = isCases
    ? "mt-4 max-w-sm text-[0.97rem] leading-6 text-slate-100"
    : "mt-4 max-w-[24ch] text-[0.98rem] leading-6 text-slate-100"

  return (
    <Link to={href} className={linkClassName}>
      <div className="flex h-full flex-col">
        <div className={isCases ? "min-h-34 sm:min-h-36" : "min-h-55 sm:min-h-58"}>
          <div
            className={
              isPrimary
                ? "text-[11px] uppercase tracking-[0.24em] text-sky-100"
                : "text-[11px] uppercase tracking-[0.24em] text-slate-300"
            }
          >
            {roleLabel}
          </div>
          <div className={tickerClassName}>{ticker}</div>
          <div className="mt-1.5 text-sm leading-5 text-slate-400">{companyName}</div>
          <p className={descriptionClassName}>{description}</p>
          {bestFor ? (
            <p className="mt-3 text-[13px] leading-5 text-slate-400">
              <span className="uppercase tracking-[0.18em] text-slate-500">Best for</span>{" "}
              <span className="text-slate-300">{bestFor}</span>
            </p>
          ) : null}
        </div>

        <div className="mt-auto flex items-center justify-between gap-3 border-t border-white/10 pt-4">
          <span
            className={
              isPrimary
                ? "text-sm font-semibold tracking-[0.01em] text-sky-50 transition group-hover:text-white"
                : "text-sm font-semibold tracking-[0.01em] text-slate-100 transition group-hover:text-white"
            }
          >
            {ctaLabel}
          </span>
          <span
            className={
              isPrimary
                ? "grid h-10 w-10 shrink-0 place-items-center rounded-full border border-sky-300/36 bg-sky-400/12 text-base text-sky-100 transition group-hover:border-sky-200/55 group-hover:text-white"
                : "grid h-10 w-10 shrink-0 place-items-center rounded-full border border-white/14 bg-white/6 text-base text-slate-200 transition group-hover:border-sky-300/45 group-hover:text-white"
            }
            aria-hidden="true"
          >
            →
          </span>
        </div>
      </div>
      <span className="sr-only">
        Open the {ticker} chooser card for {companyName}.
      </span>
    </Link>
  )
}
