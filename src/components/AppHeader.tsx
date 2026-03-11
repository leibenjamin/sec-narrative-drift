import { Link, useLocation } from "react-router-dom"

type NavItem = {
  to: string
  label: string
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Home" },
  { to: "/companies", label: "Companies" },
  { to: "/methodology", label: "Methodology" },
]

function isActive(pathname: string, to: string): boolean {
  if (to === "/") return pathname === "/"
  if (to === "/companies") {
    return pathname.startsWith("/companies") || pathname.startsWith("/company")
  }
  return pathname.startsWith(to)
}

export default function AppHeader() {
  const { pathname } = useLocation()

  return (
    <header className="sticky top-0 z-30 border-b border-white/10 bg-slate-950/78 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-4">
        <div className="flex items-center gap-3">
          <div>
            <Link
              to="/"
              className="text-xs uppercase tracking-[0.24em] text-slate-200 hover:text-slate-50"
            >
              SEC Narrative Drift Lab
            </Link>
            <div className="mt-1 text-[11px] text-slate-400">Investor-first, evidence-backed filing comparison</div>
          </div>
          <span className="rounded bg-amber-600/80 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-amber-100">
            Beta
          </span>
        </div>
        <nav className="flex flex-wrap items-center gap-4 text-sm" aria-label="Primary">
          {NAV_ITEMS.map((item) => {
            const active = isActive(pathname, item.to)
            return (
              <Link
                key={item.to}
                to={item.to}
                aria-current={active ? "page" : undefined}
                className={
                  active
                    ? "text-slate-50"
                    : "text-slate-300 hover:text-slate-100"
                }
              >
                {item.label}
              </Link>
            )
          })}
        </nav>
      </div>
    </header>
  )
}

