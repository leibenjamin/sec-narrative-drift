import { useMemo } from "react"
import { copy } from "../lib/copy"

type ShiftTerm = {
  term: string
  score: number
}

type TermShiftBarsProps = {
  selectedPair: { from: number; to: number } | null
  topRisers: ShiftTerm[]
  topFallers: ShiftTerm[]
  onClickTerm: (term: string) => void
}

function formatScore(value: number): string {
  return value.toFixed(2)
}

export default function TermShiftBars({
  selectedPair,
  topRisers,
  topFallers,
  onClickTerm,
}: TermShiftBarsProps) {
  const maxMagnitude = useMemo(() => {
    const magnitudes = [...topRisers, ...topFallers].map((item) =>
      Math.abs(item.score)
    )
    return Math.max(...magnitudes, 1)
  }, [topRisers, topFallers])

  const hasData = topRisers.length > 0 || topFallers.length > 0

  if (!selectedPair || !hasData) {
    return <p className="text-sm text-slate-300">{copy.global.errors.noShifts}</p>
  }

  return (
    <div className="space-y-4">
      <div className="text-xs uppercase tracking-wider text-slate-300">
        {selectedPair.from} → {selectedPair.to}
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-black/10 p-3">
          <div className="text-sm font-semibold">{copy.termShifts.risersLabel}</div>
          <ul className="mt-3 space-y-2 text-xs">
            {topRisers.map((item) => {
              const width = Math.round((Math.abs(item.score) / maxMagnitude) * 100)
              return (
                <li key={`riser-${item.term}`}>
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 text-left"
                    onClick={() => onClickTerm(item.term)}
                  >
                    <span className="min-w-22.5 font-medium">{item.term}</span>
                    <span className="text-[10px] text-slate-300">
                      {formatScore(item.score)}
                    </span>
                    <span className="flex-1 h-2 rounded bg-emerald-100">
                      <span
                        className="block h-2 rounded bg-emerald-500"
                        style={{ width: `${width}%` }}
                      />
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
        <div className="rounded-lg border border-black/10 p-3">
          <div className="text-sm font-semibold">{copy.termShifts.fallersLabel}</div>
          <ul className="mt-3 space-y-2 text-xs">
            {topFallers.map((item) => {
              const width = Math.round((Math.abs(item.score) / maxMagnitude) * 100)
              return (
                <li key={`faller-${item.term}`}>
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 text-left"
                    onClick={() => onClickTerm(item.term)}
                  >
                    <span className="min-w-22.5 font-medium">{item.term}</span>
                    <span className="text-[10px] text-slate-300">
                      {formatScore(item.score)}
                    </span>
                    <span className="flex-1 h-2 rounded bg-rose-100">
                      <span
                        className="block h-2 rounded bg-rose-400"
                        style={{ width: `${width}%` }}
                      />
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      </div>
    </div>
  )
}
