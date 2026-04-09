import {
  getPublicCasebookEntry,
  type PublicCasebookTicker,
} from "../lib/casebookContent"

type CaseTeachingLayerProps = {
  ticker: string
  className?: string
}

type TeachingCard = {
  label: string
  value: string
}

function buildTeachingCards(ticker: PublicCasebookTicker): TeachingCard[] {
  const entry = getPublicCasebookEntry(ticker)
  if (!entry) return []

  return [
    {
      label: "What this case proves",
      value: entry.teaching.proves,
    },
    {
      label: "What it doesn't prove",
      value: entry.teaching.doesntProve,
    },
    {
      label: "Lesson",
      value: entry.teaching.lesson,
    },
    {
      label: "Common mistake this case prevents",
      value: entry.teaching.commonMistake,
    },
  ]
}

export default function CaseTeachingLayer({
  ticker,
  className = "",
}: CaseTeachingLayerProps) {
  const entry = getPublicCasebookEntry(ticker)
  if (!entry) return null

  const cards = buildTeachingCards(entry.ticker)

  return (
    <section
      id="case-teaching-layer"
      className={`rounded-[1.35rem] border border-white/10 bg-slate-950/46 p-4 shadow-[0_18px_40px_rgba(2,6,23,0.18)] sm:p-5 ${className}`.trim()}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
            Teaching layer
          </div>
          <h2 className="mt-1.5 text-xl font-semibold text-slate-50 sm:text-2xl">
            {entry.publicRoleLabel}
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
            {entry.teachingSummary}
          </p>
        </div>
        <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-slate-300">
          {entry.artifactPolicy.primary}
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {cards.map((card) => (
          <article
            key={card.label}
            className="rounded-[1.1rem] border border-white/10 bg-slate-950/70 p-3.5"
          >
            <div className="text-[10px] uppercase tracking-[0.24em] text-slate-400">
              {card.label}
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-100">{card.value}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
