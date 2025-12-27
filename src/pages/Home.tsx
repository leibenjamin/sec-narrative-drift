// src/pages/Home.tsx
import { Link } from "react-router-dom"
import { copy } from "../lib/copy"
import { listFeaturedTickers } from "../lib/data"

export default function Home() {
  const featuredTickers = listFeaturedTickers()

  return (
    <main className="min-h-screen">
      <div className="mx-auto max-w-3xl px-6 py-16">
        <header className="space-y-4">
          <p className="text-sm uppercase tracking-wider text-slate-300">
            {copy.global.appName}
          </p>

          <h1 className="text-4xl font-semibold leading-tight">
            {copy.home.heroTitle}
          </h1>

          <p className="text-lg text-slate-200">
            {copy.global.subtitle}
          </p>

          <p className="text-base text-slate-200">
            {copy.global.oneLiner}
          </p>

          <p className="text-sm text-slate-300">
            {copy.home.heroFootnote}
          </p>
        </header>

        <div className="mt-10 flex flex-wrap gap-3">
          {/* Placeholder for now: route later when Company page exists */}
          <Link
            to="/company"
            className="inline-flex items-center rounded-md bg-black px-4 py-2 text-white hover:opacity-90"
          >
            {copy.buttons.exploreFeatured}
          </Link>

          <Link
            to="/methodology"
            className="inline-flex items-center rounded-md border border-black/20 px-4 py-2 hover:bg-black/5"
          >
            {copy.nav.methodology}
          </Link>
        </div>

        <section className="mt-14">
          <h2 className="text-xl font-semibold">
            {copy.home.featuredHeading}
          </h2>
          <p className="mt-2 text-sm text-slate-300">
            {copy.home.featuredHelper}
          </p>

          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            {featuredTickers.map((ticker) => (
              <Link
                key={ticker}
                to={`/company/${ticker}`}
                className="rounded-lg border border-black/10 p-4 hover:bg-black/5"
              >
                <div className="text-sm font-medium">{ticker}</div>
                <div className="mt-1 text-xs text-slate-300">
                  {copy.company.sectionValueMvp}
                </div>
              </Link>
            ))}
          </div>
        </section>

        <footer className="mt-16 text-xs text-slate-400">
          {copy.global.sourceLine} · {copy.global.caveatLine}
        </footer>
      </div>
    </main>
  )
}
