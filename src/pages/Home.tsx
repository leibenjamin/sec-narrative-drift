// src/pages/Home.tsx
import { useEffect, useState } from "react"
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
          {index ? (
            <p className="mt-2 text-xs text-slate-400">
              {t(copy.companies.coverageLine, {
                n: index.companyCount,
                target: index.lookbackTargetYears,
              })}
            </p>
          ) : null}

          {featuredCases.length ? (
            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              {featuredCases.map((featured) => {
                const link = `/company/${featured.ticker}?from=${featured.defaultPair.from}&to=${featured.defaultPair.to}`
                return (
                  <Link
                    key={featured.id}
                    to={link}
                    className="rounded-lg border border-black/10 p-4 hover:bg-black/5"
                  >
                    <div className="text-sm font-medium">{featured.ticker}</div>
                    <div className="mt-2 text-sm font-medium">{featured.headline}</div>
                    <div className="mt-2 text-xs text-slate-300">{featured.hook}</div>
                  </Link>
                )
              })}
            </div>
          ) : featuredError ? (
            <p className="mt-4 text-xs text-slate-400">{featuredError}</p>
          ) : null}
        </section>

        <footer className="mt-16 text-xs text-slate-400">
          {copy.global.sourceLine} {copy.global.caveatLine}
        </footer>
      </div>
    </main>
  )
}
