// src/pages/Home.tsx
import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { copy, t } from "../lib/copy"
import {
  listFeaturedTickers,
  listFeaturedTickersFromIndex,
  loadCompanyIndex,
} from "../lib/data"
import type { CompanyIndex } from "../lib/types"

export default function Home() {
  const [index, setIndex] = useState<CompanyIndex | null>(null)
  const [indexError, setIndexError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    loadCompanyIndex()
      .then((data) => {
        if (!mounted) return
        setIndex(data)
      })
      .catch((e) => {
        if (!mounted) return
        setIndexError(e?.message ?? copy.global.errors.missingDataset)
      })
    return () => {
      mounted = false
    }
  }, [])

  const featuredCases = useMemo(() => {
    return index?.companies.filter((company) => !!company.featuredCase) ?? []
  }, [index])

  const featuredTickers = useMemo(() => {
    return index ? listFeaturedTickersFromIndex(index) : listFeaturedTickers()
  }, [index])

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
          <Link
            to="/companies"
            className="inline-flex items-center rounded-md bg-black px-4 py-2 text-white hover:opacity-90"
          >
            {copy.buttons.browseCompanies}
          </Link>

          <Link
            to="/methodology"
            className="inline-flex items-center rounded-md border border-black/20 px-4 py-2 hover:bg-black/5"
          >
            {copy.nav.methodology}
          </Link>
        </div>

        <section className="mt-14 space-y-6">
          <div>
            <h2 className="text-xl font-semibold">{copy.home.howToReadTitle}</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-black/10 p-4">
              <div className="text-xs uppercase tracking-wider text-slate-300">1</div>
              <p className="mt-2 text-sm text-slate-200">{copy.home.howToReadSteps.drift}</p>
            </div>
            <div className="rounded-lg border border-black/10 p-4">
              <div className="text-xs uppercase tracking-wider text-slate-300">2</div>
              <p className="mt-2 text-sm text-slate-200">
                {copy.home.howToReadSteps.similarity}
              </p>
            </div>
            <div className="rounded-lg border border-black/10 p-4">
              <div className="text-xs uppercase tracking-wider text-slate-300">3</div>
              <p className="mt-2 text-sm text-slate-200">
                {copy.home.howToReadSteps.evidence}
              </p>
            </div>
          </div>
          <div className="rounded-lg border border-black/10 p-4">
            <div className="text-xs uppercase tracking-wider text-slate-300">
              {copy.home.exampleLabel}
            </div>
            <p className="mt-2 text-sm text-slate-200">{copy.home.exampleText}</p>
            <Link
              to="/company/NVDA"
              className="mt-3 inline-flex items-center rounded-md border border-black/20 px-3 py-2 text-xs hover:bg-black/5"
            >
              {copy.home.exampleLink}
            </Link>
          </div>
        </section>

        <section className="mt-14">
          <h2 className="text-xl font-semibold">
            {copy.home.featuredHeading}
          </h2>
          <p className="mt-2 text-sm text-slate-300">
            {copy.home.featuredHelper}
          </p>
          {index && !indexError ? (
            <p className="mt-2 text-xs text-slate-400">
              {t(copy.companies.coverageLine, {
                n: index.companyCount,
                target: index.lookbackTargetYears,
              })}
            </p>
          ) : null}

          {featuredCases.length ? (
            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              {featuredCases.slice(0, 6).map((company) => {
                const featured = company.featuredCase!
                const link = `/company/${company.ticker}?from=${featured.from}&to=${featured.to}`
                return (
                  <Link
                    key={company.ticker}
                    to={link}
                    className="rounded-lg border border-black/10 p-4 hover:bg-black/5"
                  >
                    <div className="text-sm font-medium">{company.ticker}</div>
                    <div className="mt-1 text-xs text-slate-300">
                      {company.companyName}
                    </div>
                    <div className="mt-3 text-sm font-medium">{featured.title}</div>
                    <div className="mt-2 text-xs text-slate-300">{featured.blurb}</div>
                  </Link>
                )
              })}
            </div>
          ) : (
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
          )}
        </section>

        <footer className="mt-16 text-xs text-slate-400">
          {copy.global.sourceLine} {copy.global.caveatLine}
        </footer>
      </div>
    </main>
  )
}
