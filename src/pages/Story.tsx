import { Link } from "react-router-dom"
import PageMetadata from "../components/PageMetadata"
import {
  CASEBOOK_BANDS,
  HOME_ANCHOR_TICKERS,
  casebookFraming,
  getPublicCasebookEntry,
} from "../lib/casebookContent"
import { buildProtocolLabCaseHref } from "../lib/protocolLabProductPositioning"

function buildCaseHref(ticker: string): string {
  const entry = getPublicCasebookEntry(ticker)
  if (!entry) {
    throw new Error(`Missing casebook entry for ${ticker}.`)
  }

  return buildProtocolLabCaseHref(ticker, entry.yearFrom, entry.yearTo)
}

export default function Story() {
  const anchorEntries = HOME_ANCHOR_TICKERS.map((ticker) => {
    const entry = getPublicCasebookEntry(ticker)
    if (!entry) {
      throw new Error(`Missing anchor casebook entry for ${ticker}.`)
    }

    return entry
  })

  const pressureEntries = CASEBOOK_BANDS.find((band) => band.id === "pressure_cases")?.tickers.map((ticker) => {
    const entry = getPublicCasebookEntry(ticker)
    if (!entry) {
      throw new Error(`Missing pressure casebook entry for ${ticker}.`)
    }

    return entry
  }) ?? []

  return (
    <main className="min-h-screen page-fade">
      <PageMetadata
        title={casebookFraming.story.title}
        description={casebookFraming.story.metaDescription}
      />
      <div className="mx-auto max-w-5xl space-y-5 px-5 py-5 sm:space-y-6 sm:px-6 sm:py-7">
        <section
          id="story-top-fold"
          className="relative overflow-hidden rounded-[2.2rem] border border-white/10 bg-linear-to-br from-slate-950/94 via-slate-950/84 to-slate-900/70 p-5 shadow-[0_30px_80px_rgba(2,6,23,0.42)] sm:p-7"
        >
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.16),transparent_34%),radial-gradient(circle_at_bottom_right,rgba(16,185,129,0.12),transparent_30%)]" />
          <div className="relative space-y-5">
            <div className="flex flex-wrap items-center gap-1.5 text-[11px] uppercase tracking-[0.24em] text-slate-300">
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                {casebookFraming.story.eyebrow}
              </span>
              <span className="rounded-full border border-sky-300/25 bg-sky-400/10 px-3 py-1 text-sky-100">
                Compact guided argument
              </span>
            </div>

            <header className="space-y-3">
              <h1 className="max-w-4xl text-[clamp(2.3rem,4vw,4rem)] font-semibold leading-[0.92] tracking-[-0.05em] text-slate-50">
                {casebookFraming.story.heading}
              </h1>
              <p className="max-w-3xl text-sm leading-6 text-slate-200 sm:text-base">
                {casebookFraming.story.intro}
              </p>
            </header>

            <div className="grid gap-3 md:grid-cols-2">
              <Link
                to="/companies"
                className="inline-flex min-h-12 items-center justify-center rounded-full bg-sky-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-sky-400"
              >
                {casebookFraming.story.primaryCta}
              </Link>
              <Link
                to="/methodology"
                className="inline-flex min-h-12 items-center justify-center rounded-full border border-white/20 px-5 py-3 text-sm font-medium text-slate-200 transition hover:border-white/40 hover:bg-white/5"
              >
                {casebookFraming.story.secondaryCta}
              </Link>
            </div>
          </div>
        </section>

        <section
          id="story-core-question"
          className="rounded-[1.6rem] border border-white/10 bg-slate-950/48 p-5 sm:p-6"
        >
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
            {casebookFraming.story.coreQuestionTitle}
          </div>
          <div className="mt-3 grid gap-3">
            {casebookFraming.story.coreQuestionBody.map((item) => (
              <p key={item} className="max-w-3xl text-sm leading-6 text-slate-100">
                {item}
              </p>
            ))}
          </div>
        </section>

        <section
          id="story-answer-shape"
          className="rounded-[1.6rem] border border-white/10 bg-slate-950/48 p-5 sm:p-6"
        >
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
            {casebookFraming.story.answerTitle}
          </div>
          <div className="mt-3 grid gap-3">
            {casebookFraming.story.answerBody.map((item) => (
              <p key={item} className="max-w-3xl text-sm leading-6 text-slate-100">
                {item}
              </p>
            ))}
          </div>
        </section>

        <section
          id="story-grammar"
          className="rounded-[1.6rem] border border-sky-300/18 bg-sky-400/6 p-5 sm:p-6"
        >
          <div className="space-y-2">
            <div className="text-[11px] uppercase tracking-[0.24em] text-sky-100">
              {casebookFraming.story.grammarTitle}
            </div>
            <p className="max-w-3xl text-sm leading-6 text-slate-100">
              {casebookFraming.story.grammarIntro}
            </p>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {casebookFraming.story.grammarCards.map((card) => (
              <article
                key={card.label}
                className="rounded-[1.2rem] border border-white/10 bg-slate-950/68 p-4"
              >
                <div className="text-[11px] uppercase tracking-[0.24em] text-sky-100">
                  {card.label}
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-100">{card.detail}</p>
              </article>
            ))}
          </div>
        </section>

        <section
          id="story-six-cases"
          className="rounded-[1.6rem] border border-white/10 bg-slate-950/48 p-5 sm:p-6"
        >
          <div className="space-y-2">
            <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
              {casebookFraming.story.rosterTitle}
            </div>
            {casebookFraming.story.rosterBody.map((item) => (
              <p key={item} className="max-w-3xl text-sm leading-6 text-slate-100">
                {item}
              </p>
            ))}
          </div>
          <div className="mt-4 rounded-[1.2rem] border border-white/10 bg-slate-950/62 px-4 py-3 text-sm text-slate-200">
            {casebookFraming.casebook.boundednessNote}
          </div>
        </section>

        <section
          id="story-anchor-lessons"
          className="rounded-[1.6rem] border border-white/10 bg-slate-950/48 p-5 sm:p-6"
        >
          <div className="space-y-2">
            <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
              {casebookFraming.story.anchorTitle}
            </div>
            <p className="max-w-3xl text-sm leading-6 text-slate-100">
              {casebookFraming.story.anchorIntro}
            </p>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {anchorEntries.map((entry) => (
              <Link
                key={entry.ticker}
                to={buildCaseHref(entry.ticker)}
                className="group rounded-[1.25rem] border border-white/10 bg-slate-950/70 p-4 transition hover:border-sky-300/40 hover:bg-slate-950/84"
              >
                <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
                  {entry.publicRoleLabel}
                </div>
                <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-slate-50">
                  {entry.ticker}
                </h2>
                <p className="mt-2 text-sm leading-6 text-slate-200">{entry.teachingSummary}</p>
                <div className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-sky-100 transition group-hover:text-white">
                  <span>Open {entry.ticker}</span>
                  <span aria-hidden="true">→</span>
                </div>
              </Link>
            ))}
          </div>

          <div className="mt-5 space-y-2">
            <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
              {casebookFraming.story.pressureTitle}
            </div>
            <p className="max-w-3xl text-sm leading-6 text-slate-100">
              {casebookFraming.story.pressureBody}
            </p>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {pressureEntries.map((entry) => (
              <article
                key={entry.ticker}
                className="rounded-[1.15rem] border border-white/10 bg-slate-950/62 p-4"
              >
                <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
                  {entry.publicRoleLabel}
                </div>
                <div className="mt-2 text-lg font-semibold text-slate-50">{entry.ticker}</div>
                <p className="mt-2 text-sm leading-6 text-slate-200">{entry.teachingSummary}</p>
              </article>
            ))}
          </div>
        </section>

        <section
          id="story-enter-lab"
          className="rounded-[1.6rem] border border-sky-300/18 bg-linear-to-br from-sky-400/10 via-slate-950/78 to-slate-950/56 p-5 sm:p-6"
        >
          <div className="space-y-2">
            <div className="text-[11px] uppercase tracking-[0.24em] text-sky-100">
              {casebookFraming.story.ctaTitle}
            </div>
            <p className="max-w-3xl text-sm leading-6 text-slate-100">
              {casebookFraming.story.ctaBody}
            </p>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <Link
              to="/companies"
              className="inline-flex min-h-11 items-center justify-center rounded-full bg-sky-500 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-sky-400"
            >
              {casebookFraming.story.primaryCta}
            </Link>
            <Link
              to="/methodology"
              className="inline-flex min-h-11 items-center justify-center rounded-full border border-white/20 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:border-white/40 hover:bg-white/5"
            >
              {casebookFraming.story.secondaryCta}
            </Link>
          </div>
        </section>
      </div>
    </main>
  )
}
