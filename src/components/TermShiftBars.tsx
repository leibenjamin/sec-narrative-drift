import { useMemo } from "react"
import InlinePopover from "./InlinePopover"
import { copy } from "../lib/copy"
import { getShiftTermLabel, isShiftTermItem } from "../lib/shiftTerms"
import type { ShiftTerm } from "../lib/types"

export type TermLens = "primary" | "alt"

type TermShiftBarsProps = {
  selectedPair: { from: number; to: number } | null
  topRisers: ShiftTerm[]
  topFallers: ShiftTerm[]
  lens?: TermLens
  hasAlt?: boolean
  onLensChange?: (lens: TermLens) => void
  onClickTerm: (term: string, includes?: string[]) => void
}

const MAX_VARIANTS_INLINE = 4
const MAX_VARIANT_LENGTH = 36

function normalizeForCompare(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim()
}

function tokenCount(value: string): number {
  const normalized = normalizeForCompare(value)
  return normalized ? normalized.split(" ").length : 0
}

function compareVariants(a: string, b: string): number {
  const tokenDelta = tokenCount(b) - tokenCount(a)
  if (tokenDelta !== 0) return tokenDelta
  const lengthDelta = b.length - a.length
  if (lengthDelta !== 0) return lengthDelta
  return a.localeCompare(b)
}

function cleanVariants(raw: string[] | undefined): string[] {
  if (!raw) return []
  const seen = new Set<string>()
  const cleaned: string[] = []

  for (const entry of raw) {
    if (typeof entry !== "string") continue
    const trimmed = entry.trim()
    if (!trimmed) continue
    const key = normalizeForCompare(trimmed)
    if (!key || seen.has(key)) continue
    seen.add(key)
    cleaned.push(trimmed)
  }

  return cleaned.sort(compareVariants)
}

function truncateVariant(value: string): { text: string; title?: string } {
  if (value.length <= MAX_VARIANT_LENGTH) return { text: value }
  const truncated = `${value.slice(0, Math.max(MAX_VARIANT_LENGTH - 3, 1))}...`
  return { text: truncated, title: value }
}

function renderVariantList(variants: string[]) {
  const shown = variants.slice(0, MAX_VARIANTS_INLINE)
  const extraCount = Math.max(variants.length - shown.length, 0)

  return (
    <>
      {shown.map((variant, index) => {
        const { text, title } = truncateVariant(variant)
        return (
          <span key={`${variant}-${index}`} title={title}>
            {index > 0 ? ", " : ""}
            {text}
          </span>
        )
      })}
      {extraCount > 0 ? ` (and ${extraCount} more)` : null}
    </>
  )
}

function buildIncludesContent(variants: string[]) {
  return (
    <div className="space-y-1 text-xs text-slate-700">
      <div className="font-semibold text-slate-900">
        {copy.terms.includesTooltipTitle}
      </div>
      <div>
        <span className="font-semibold">{copy.terms.includesLabel}:</span>{" "}
        {renderVariantList(variants)}
      </div>
      <div>{copy.terms.includesTooltipCountsNote}</div>
      <div className="text-[11px] text-slate-500">
        {copy.terms.includesTooltipTip}
      </div>
    </div>
  )
}

function formatScore(value: number | null): string {
  if (value === null || Number.isNaN(value)) return "-"
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
    const magnitudes = [...topRisers, ...topFallers].map((item) => {
      if (!isShiftTermItem(item) || typeof item.score !== "number") return 0
      return Math.abs(item.score)
    })
    return Math.max(...magnitudes, 1)
  }, [topRisers, topFallers])

  const hasData = topRisers.length > 0 || topFallers.length > 0

  if (!selectedPair || !hasData) {
    return <p className="text-sm text-slate-300">{copy.global.errors.noShifts}</p>
  }

  const pairKey = `${selectedPair.from}-${selectedPair.to}-${lens}`

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
            {topRisers.map((item, index) => {
              const termLabel = getShiftTermLabel(item)
              const scoreValue =
                isShiftTermItem(item) && typeof item.score === "number" ? item.score : null
              const width =
                scoreValue !== null
                  ? Math.round((Math.abs(scoreValue) / maxMagnitude) * 100)
                  : 0
              const delta = isShiftTermItem(item) ? formatDeltaPer10k(item.deltaPer10k) : null
              const showNotable =
                isShiftTermItem(item) &&
                (Boolean(item.distinctive) || (item.z !== undefined && Math.abs(item.z) >= 2))
              const includes = isShiftTermItem(item) ? cleanVariants(item.includes) : []
              const normalizedLabel = normalizeForCompare(termLabel)
              const showIncludes =
                includes.length >= 2 ||
                (includes.length === 1 &&
                  normalizeForCompare(includes[0]) !== normalizedLabel)

              return (
                <li key={`riser-${termLabel}-${index}`}>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      className="flex min-w-0 flex-1 items-center gap-2 text-left"
                      onClick={() =>
                        onClickTerm(termLabel, includes.length ? includes : undefined)
                      }
                      title={copy.termShifts.scoreTooltip}
                    >
                      <span className="min-w-28 font-medium">{termLabel}</span>
                      {showNotable ? (
                        <span
                          className="rounded bg-slate-900/80 px-1.5 py-0.5 text-[10px] text-white"
                          title={copy.termShifts.distinctiveTooltip}
                        >
                          {copy.termShifts.distinctiveBadge}
                        </span>
                      ) : null}
                      <span className="text-[10px] text-slate-300">
                        {formatScore(scoreValue)}
                        {isShiftTermItem(item) && item.z !== undefined ? ` | z=${item.z.toFixed(1)}` : ""}
                        {delta ? ` | ${delta}` : ""}
                      </span>
                      <span className="flex-1 h-2 rounded bg-emerald-100">
                        <span
                          className="block h-2 rounded bg-emerald-500"
                          style={{ width: `${width}%` }}
                        />
                      </span>
                    </button>
                    {showIncludes ? (
                      <InlinePopover
                        label={copy.terms.includesLabel}
                        ariaLabel={`${copy.terms.includesLabel} variants`}
                        triggerClassName="shrink-0 text-[10px] text-slate-400 hover:text-slate-600 hover:underline"
                        content={buildIncludesContent(includes)}
                        align="right"
                        resetKey={pairKey}
                      />
                    ) : null}
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
        <div className="rounded-lg border border-black/10 p-3">
          <div className="text-sm font-semibold">{copy.termShifts.fallersLabel}</div>
          <ul className="mt-3 space-y-2 text-xs">
            {topFallers.map((item, index) => {
              const termLabel = getShiftTermLabel(item)
              const scoreValue =
                isShiftTermItem(item) && typeof item.score === "number" ? item.score : null
              const width =
                scoreValue !== null
                  ? Math.round((Math.abs(scoreValue) / maxMagnitude) * 100)
                  : 0
              const delta = isShiftTermItem(item) ? formatDeltaPer10k(item.deltaPer10k) : null
              const showNotable =
                isShiftTermItem(item) &&
                (Boolean(item.distinctive) || (item.z !== undefined && Math.abs(item.z) >= 2))
              const includes = isShiftTermItem(item) ? cleanVariants(item.includes) : []
              const normalizedLabel = normalizeForCompare(termLabel)
              const showIncludes =
                includes.length >= 2 ||
                (includes.length === 1 &&
                  normalizeForCompare(includes[0]) !== normalizedLabel)

              return (
                <li key={`faller-${termLabel}-${index}`}>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      className="flex min-w-0 flex-1 items-center gap-2 text-left"
                      onClick={() =>
                        onClickTerm(termLabel, includes.length ? includes : undefined)
                      }
                      title={copy.termShifts.scoreTooltip}
                    >
                      <span className="min-w-28 font-medium">{termLabel}</span>
                      {showNotable ? (
                        <span
                          className="rounded bg-slate-900/80 px-1.5 py-0.5 text-[10px] text-white"
                          title={copy.termShifts.distinctiveTooltip}
                        >
                          {copy.termShifts.distinctiveBadge}
                        </span>
                      ) : null}
                      <span className="text-[10px] text-slate-300">
                        {formatScore(scoreValue)}
                        {isShiftTermItem(item) && item.z !== undefined ? ` | z=${item.z.toFixed(1)}` : ""}
                        {delta ? ` | ${delta}` : ""}
                      </span>
                      <span className="flex-1 h-2 rounded bg-rose-100">
                        <span
                          className="block h-2 rounded bg-rose-500"
                          style={{ width: `${width}%` }}
                        />
                      </span>
                    </button>
                    {showIncludes ? (
                      <InlinePopover
                        label={copy.terms.includesLabel}
                        ariaLabel={`${copy.terms.includesLabel} variants`}
                        triggerClassName="shrink-0 text-[10px] text-slate-400 hover:text-slate-600 hover:underline"
                        content={buildIncludesContent(includes)}
                        align="right"
                        resetKey={pairKey}
                      />
                    ) : null}
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      </div>
    </div>
  )
}
