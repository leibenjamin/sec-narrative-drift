// src/pages/Home.tsx
import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { copy, t } from "../lib/copy"
import {
  loadCompanyIndex,
  loadFeaturedCases,
} from "../lib/data"
import type { CompanyIndex, FeaturedCase } from "../lib/types"

export default function Home() {
  const [index, setIndex] = useState<CompanyIndex | null>(null)
  const [featuredCases, setFeaturedCases] = useState<FeaturedCase[]>([])
  const [featuredError, setFeaturedError] = useState<string | null>(null)
  const companyNameMap = useMemo(() => {
    const map = new Map<string, string>()
    if (!index) return map
    for (const company of index.companies) {
      if (company.ticker && company.companyName) {
        map.set(company.ticker.toUpperCase(), company.companyName)
      }
    }
    return map
  }, [index])

  useEffect(() => {
    let mounted = true
    loadCompanyIndex()
      .then((data) => {
        if (!mounted) return
        setIndex(data)
      })
      .catch(() => {
        if (!mounted) return
        setIndex(null)
      })
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    let mounted = true
    loadFeaturedCases()
      .then((data) => {
        if (!mounted) return
        setFeaturedCases(data.cases.slice(0, 6))
      })
      .catch((e) => {
        if (!mounted) return
        setFeaturedError(e?.message ?? copy.global.errors.missingDataset)
      })
    return () => {
      mounted = false
    }
  }, [])

  return (
    <main className="min-h-screen page-fade">
      <div className="mx-auto max-w-6xl px-6 pt-8 pb-6 space-y-6">
        <section className="grid gap-6 lg:grid-cols-[1.35fr_0.65fr]">
          <header className="space-y-2">
            <p className="text-xs uppercase tracking-wider text-slate-300">
              {copy.global.appName}
            </p>

            <h1 className="text-2xl font-semibold leading-snug">
              {copy.home.heroTitle}
            </h1>

            <p className="text-sm text-slate-200">
              {copy.global.subtitle}
            </p>

            <p className="text-sm text-slate-200">
              {copy.global.oneLiner}
            </p>

            <p className="text-xs text-slate-300">
              {copy.home.heroFootnote}
            </p>

            <div className="flex flex-wrap gap-2 pt-1">
              <Link
                to="/companies"
                className="inline-flex items-center rounded-md bg-sky-400 px-3 py-1.5 text-sm font-semibold text-slate-900 hover:bg-sky-300"
              >
                {copy.buttons.browseCompanies}
              </Link>

              <Link
                to="/methodology"
                className="inline-flex items-center rounded-md border border-white/20 px-3 py-1.5 text-sm text-slate-200 hover:border-white/40 hover:bg-white/5"
              >
                {copy.nav.methodology}
              </Link>
            </div>
          </header>

          <aside className="rounded-lg border border-white/10 bg-slate-900/60 p-3 shadow-sm">
            <div className="text-xs uppercase tracking-wider text-slate-300">
              {copy.home.howToReadTitle}
            </div>
            <ol className="mt-2 space-y-1 text-sm text-slate-200">
              <li>
                <span className="text-slate-400">1.</span>{" "}
                {copy.home.howToReadSteps.drift}
              </li>
              <li>
                <span className="text-slate-400">2.</span>{" "}
                {copy.home.howToReadSteps.similarity}
              </li>
              <li>
                <span className="text-slate-400">3.</span>{" "}
                {copy.home.howToReadSteps.evidence}
              </li>
            </ol>
            <p className="mt-2 text-xs text-slate-400 leading-snug">
              {copy.global.sourceLine} {copy.global.caveatLine}
            </p>
          </aside>
        </section>

        <section className="space-y-3">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div>
              <h2 className="text-lg font-semibold">
                {copy.home.featuredHeading}
              </h2>
              <p className="text-xs text-slate-300">
                {copy.home.featuredHelper}
              </p>
            </div>
            {index ? (
              <p className="text-xs text-slate-400">
                {t(copy.companies.coverageLine, {
                  n: index.companyCount,
                  target: index.lookbackTargetYears,
                })}
              </p>
            ) : null}
          </div>

          {featuredCases.length ? (
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 stagger-children">
              {featuredCases.map((featured) => {
                const link = `/company/${featured.ticker}?from=${featured.defaultPair.from}&to=${featured.defaultPair.to}`
                const companyName = companyNameMap.get(featured.ticker.toUpperCase())
                return (
                  <Link
                    key={featured.id}
                    to={link}
                    className="min-w-0 rounded-lg border border-white/10 bg-slate-900/40 p-2 hover:bg-slate-900/60"
                    aria-label={featured.cta}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="text-sm font-semibold">{featured.ticker}</div>
                        {companyName ? (
                          <div className="text-xs text-slate-300 truncate">
                            {companyName}
                          </div>
                        ) : null}
                      </div>
                      <span className="rounded-full border border-sky-400/40 bg-sky-400/10 px-2 py-1 text-[11px] text-sky-100">
                        {copy.companies.featuredChip}
                      </span>
                    </div>
                    <div
                      className="mt-1 text-sm font-medium leading-snug truncate"
                      title={featured.headline}
                    >
                      {featured.headline}
                    </div>
                    {featured.hook ? (
                      <div className="mt-0.5 text-xs text-slate-300 truncate" title={featured.hook}>
                        {featured.hook}
                      </div>
                    ) : null}
                    <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-300">
                      <span className="rounded-full border border-white/15 bg-white/5 px-2 py-0.5">
                        {t(copy.companies.compareYearsLabel, {
                          from: featured.defaultPair.from,
                          to: featured.defaultPair.to,
                        })}
                      </span>
                      {featured.tags?.slice(0, 2).map((tag) => (
                        <span
                          key={`${featured.id}-${tag}`}
                          className="rounded-full border border-white/15 bg-white/5 px-2 py-0.5"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </Link>
                )
              })}
            </div>
          ) : featuredError ? (
            <p className="text-xs text-slate-400">{featuredError}</p>
          ) : null}
        </section>
      </div>
    </main>
  )
}
