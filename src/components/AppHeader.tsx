import { Link, useLocation } from "react-router-dom"
import { casebookFraming } from "../lib/casebookContent"

type NavItem = {
  to: string
  label: string
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Home" },
  { to: "/story", label: "Story" },
  { to: "/companies", label: "Casebook" },
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
    <header className="sticky top-0 z-30 border-b border-white/10 bg-slate-950/84 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-start justify-between gap-x-5 gap-y-2 px-5 py-3 sm:items-center sm:px-6 sm:py-4">
        <div className="min-w-0">
          <Link
            to="/"
            className="text-[11px] uppercase tracking-[0.24em] text-slate-200 hover:text-slate-50 sm:text-xs"
          >
            Document Protocol Lab
          </Link>
          <div className="mt-1 text-[10px] text-slate-400 sm:text-[11px]">
            {casebookFraming.casebookOneLiner}
          </div>
        </div>
        <nav className="flex flex-wrap items-center gap-4 pt-0.5 text-sm" aria-label="Primary">
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
