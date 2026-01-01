import { Link, useLocation } from "react-router-dom"
import { copy } from "../lib/copy"

type NavItem = {
  to: string
  label: string
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: copy.nav.home },
  { to: "/companies", label: copy.nav.companies },
  { to: "/methodology", label: copy.nav.methodology },
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
    <header className="border-b border-white/10 bg-slate-950/70 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-4">
        <Link
          to="/"
          className="text-xs uppercase tracking-wider text-slate-200 hover:text-slate-50"
        >
          {copy.global.appName}
        </Link>
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
