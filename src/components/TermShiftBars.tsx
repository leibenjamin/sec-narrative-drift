import { useMemo } from "react"
import { copy } from "../lib/copy"
import type { ShiftTerm } from "../lib/types"

export type TermLens = "primary" | "alt"

type TermShiftBarsProps = {
  selectedPair: { from: number; to: number } | null
  topRisers: ShiftTerm[]
  topFallers: ShiftTerm[]
  lens?: TermLens
  hasAlt?: boolean
  onLensChange?: (lens: TermLens) => void
  onClickTerm: (term: string) => void
}

function formatScore(value: number): string {
  return value.toFixed(2)
}

function formatDeltaPer10k(value?: number): string | null {
  if (value === undefined || value === null) return null
  const sign = value >= 0 ? "+" : ""
  return `${sign}${value.toFixed(1)}/10k`
}

export default function TermShiftBars({
  selectedPair,
  topRisers,
  topFallers,
  lens = "primary",
  hasAlt = false,
  onLensChange = () => undefined,
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
      <div className="flex items-start justify-between gap-3">
        <div className="text-xs uppercase tracking-wider text-slate-300">
          {selectedPair.from} → {selectedPair.to}
        </div>

        {hasAlt ? (
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-300">{copy.termShifts.lensLabel}</span>
            <div className="inline-flex overflow-hidden rounded-md border border-black/10 bg-white/70">
              <button
                type="button"
                className={`px-2 py-1 ${
                  lens === "primary" ? "bg-white font-semibold" : "opacity-80 hover:opacity-100"
                }`}
                onClick={() => onLensChange("primary")}
                title={copy.termShifts.lensPrimaryHelp}
              >
                {copy.termShifts.lensPrimary}
              </button>
              <button
                type="button"
                className={`px-2 py-1 ${
                  lens === "alt" ? "bg-white font-semibold" : "opacity-80 hover:opacity-100"
                }`}
                onClick={() => onLensChange("alt")}
                title={copy.termShifts.lensAltHelp}
              >
                {copy.termShifts.lensAlt}
              </button>
            </div>
          </div>
        ) : null}
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-black/10 p-3">
          <div className="text-sm font-semibold">{copy.termShifts.risersLabel}</div>
          <ul className="mt-3 space-y-2 text-xs">
            {topRisers.map((item) => {
              const width = Math.round((Math.abs(item.score) / maxMagnitude) * 100)
              const delta = formatDeltaPer10k(item.deltaPer10k)
              const showNotable =
                Boolean(item.distinctive) || (item.z !== undefined && Math.abs(item.z) >= 2)
              return (
                <li key={`riser-${item.term}`}>
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 text-left"
                    onClick={() => onClickTerm(item.term)}
                    title={copy.termShifts.scoreTooltip}
                  >
                    <span className="min-w-28 font-medium">{item.term}</span>
                    {showNotable ? (
                      <span
                        className="rounded bg-slate-900/80 px-1.5 py-0.5 text-[10px] text-white"
                        title={copy.termShifts.distinctiveTooltip}
                      >
                        {copy.termShifts.distinctiveBadge}
                      </span>
                    ) : null}
                    <span className="text-[10px] text-slate-300">
                      {formatScore(item.score)}
                      {item.z !== undefined ? ` · z=${item.z.toFixed(1)}` : ""}
                      {delta ? ` · ${delta}` : ""}
                    </span>
                    <span className="flex-1 h-2 rounded bg-emerald-100">
                      <span className="block h-2 rounded bg-emerald-500" style={{ width: `${width}%` }} />
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
              const delta = formatDeltaPer10k(item.deltaPer10k)
              const showNotable =
                Boolean(item.distinctive) || (item.z !== undefined && Math.abs(item.z) >= 2)
              return (
                <li key={`faller-${item.term}`}>
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 text-left"
                    onClick={() => onClickTerm(item.term)}
                    title={copy.termShifts.scoreTooltip}
                  >
                    <span className="min-w-28 font-medium">{item.term}</span>
                    {showNotable ? (
                      <span
                        className="rounded bg-slate-900/80 px-1.5 py-0.5 text-[10px] text-white"
                        title={copy.termShifts.distinctiveTooltip}
                      >
                        {copy.termShifts.distinctiveBadge}
                      </span>
                    ) : null}
                    <span className="text-[10px] text-slate-300">
                      {formatScore(item.score)}
                      {item.z !== undefined ? ` · z=${item.z.toFixed(1)}` : ""}
                      {delta ? ` · ${delta}` : ""}
                    </span>
                    <span className="flex-1 h-2 rounded bg-rose-100">
                      <span className="block h-2 rounded bg-rose-500" style={{ width: `${width}%` }} />
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
