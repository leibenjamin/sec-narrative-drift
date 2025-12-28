import { useMemo } from "react"
import { copy } from "../lib/copy"
import type { Metrics, ShiftPairs, ShiftTerm } from "../lib/types"

type ExecutiveSummaryProps = {
  metrics: Metrics | null
  shifts: ShiftPairs | null
  onJumpToPair: (fromYear: number, toYear: number) => void
}

type LargestDriftSummary = {
  fromYear: number | null
  toYear: number | null
  drift: number | null
  ciLow: number | null
  ciHigh: number | null
  risers: ShiftTerm[]
  fallers: ShiftTerm[]
}

function formatValue(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "-"
  return value.toFixed(2)
}

function getShiftPair(
  shifts: ShiftPairs | null,
  fromYear: number,
  toYear: number
): { topRisers: ShiftTerm[]; topFallers: ShiftTerm[] } | null {
  if (!shifts?.yearPairs?.length) return null
  for (const pair of shifts.yearPairs) {
    if (pair.from === fromYear && pair.to === toYear) {
      return { topRisers: pair.topRisers, topFallers: pair.topFallers }
    }
  }
  return null
}

export default function ExecutiveSummary({
  metrics,
  shifts,
  onJumpToPair,
}: ExecutiveSummaryProps) {
  const summary = useMemo<LargestDriftSummary>(() => {
    const years = metrics?.years ?? []
    const drift = metrics?.drift_vs_prev ?? []
    let maxIndex = -1
    let maxValue = -Infinity

    for (let i = 1; i < drift.length; i += 1) {
      const value = drift[i]
      if (typeof value !== "number") continue
      if (value > maxValue) {
        maxValue = value
        maxIndex = i
      }
    }

    if (maxIndex < 1 || !years[maxIndex] || !years[maxIndex - 1]) {
      return {
        fromYear: null,
        toYear: null,
        drift: null,
        ciLow: null,
        ciHigh: null,
        risers: [],
        fallers: [],
      }
    }

    const fromYear = years[maxIndex - 1]
    const toYear = years[maxIndex]
    const ciLowRaw = metrics?.drift_ci_low?.[maxIndex]
    const ciHighRaw = metrics?.drift_ci_high?.[maxIndex]
    const pairShifts = getShiftPair(shifts, fromYear, toYear)

    return {
      fromYear,
      toYear,
      drift: maxValue,
      ciLow: typeof ciLowRaw === "number" ? ciLowRaw : null,
      ciHigh: typeof ciHighRaw === "number" ? ciHighRaw : null,
      risers: pairShifts?.topRisers ?? [],
      fallers: pairShifts?.topFallers ?? [],
    }
  }, [metrics, shifts])

  const topRisers = summary.risers.slice(0, 3).map((item) => item.term)
  const topFallers = summary.fallers.slice(0, 3).map((item) => item.term)
  const hasPair = summary.fromYear !== null && summary.toYear !== null

  let largestDriftLine: string = copy.company.executiveSummary.empty
  if (summary.fromYear !== null && summary.toYear !== null) {
    largestDriftLine = copy.company.executiveSummary.largestDriftLine({
      year: summary.toYear,
      prevYear: summary.fromYear,
    })
  }

  const driftCiLine = copy.company.executiveSummary.driftCiLine({
    drift: formatValue(summary.drift),
    low: formatValue(summary.ciLow),
    high: formatValue(summary.ciHigh),
  })

  return (
    <section className="rounded-xl border border-black/10 bg-white/70 p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-wider text-slate-300">
            {copy.company.executiveSummary.title}
          </p>
          <p className="text-sm text-slate-300">{copy.company.executiveSummary.helper}</p>
        </div>
        <button
          type="button"
          className="inline-flex items-center rounded-md border border-black/20 px-3 py-2 text-xs font-medium hover:bg-black/5 disabled:cursor-not-allowed disabled:opacity-60"
          onClick={() => {
            if (!hasPair || summary.fromYear === null || summary.toYear === null) return
            onJumpToPair(summary.fromYear, summary.toYear)
          }}
          disabled={!hasPair}
        >
          {copy.company.executiveSummary.jumpButton}
        </button>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-lg border border-black/10 p-4">
          <div className="mt-2 text-base font-semibold">{largestDriftLine}</div>
          <div className="mt-2 text-sm text-slate-300">{driftCiLine}</div>
        </div>

        <div className="rounded-lg border border-black/10 p-4">
          <div className="text-xs uppercase tracking-wider text-slate-300">
            {copy.termShifts.risersLabel}
          </div>
          {topRisers.length ? (
            <div className="mt-2 flex flex-wrap gap-2 text-xs">
              {topRisers.map((term) => (
                <span
                  key={`riser-${term}`}
                  className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-1 text-emerald-700"
                >
                  {term}
                </span>
              ))}
            </div>
          ) : (
            <p className="mt-2 text-xs text-slate-300">
              {copy.company.executiveSummary.noTerms}
            </p>
          )}
        </div>

        <div className="rounded-lg border border-black/10 p-4">
          <div className="text-xs uppercase tracking-wider text-slate-300">
            {copy.termShifts.fallersLabel}
          </div>
          {topFallers.length ? (
            <div className="mt-2 flex flex-wrap gap-2 text-xs">
              {topFallers.map((term) => (
                <span
                  key={`faller-${term}`}
                  className="rounded-full border border-rose-200 bg-rose-50 px-2 py-1 text-rose-700"
                >
                  {term}
                </span>
              ))}
            </div>
          ) : (
            <p className="mt-2 text-xs text-slate-300">
              {copy.company.executiveSummary.noTerms}
            </p>
          )}
        </div>
      </div>

      <div className="mt-4 space-y-1 text-xs text-slate-300">
        <p>{copy.global.caveatLine}</p>
        <p>{copy.company.executiveSummary.subtleLine}</p>
      </div>
    </section>
  )
}
