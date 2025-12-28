import { useMemo } from "react"
import { copy } from "../lib/copy"
import type { Metrics } from "../lib/types"

type SelectedPairCalloutProps = {
  selectedPair: { from: number; to: number } | null
  metrics: Metrics | null
  secUrl?: string | null
  evidenceAnchorId: string
}

function formatValue(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "-"
  return value.toFixed(2)
}

export default function SelectedPairCallout({
  selectedPair,
  metrics,
  secUrl,
  evidenceAnchorId,
}: SelectedPairCalloutProps) {
  const driftSummary = useMemo(() => {
    if (!selectedPair || !metrics?.years?.length) {
      return { drift: null, ciLow: null, ciHigh: null }
    }
    const index = metrics.years.indexOf(selectedPair.to)
    if (index < 0) {
      return { drift: null, ciLow: null, ciHigh: null }
    }
    const driftRaw = metrics.drift_vs_prev?.[index]
    const ciLowRaw = metrics.drift_ci_low?.[index]
    const ciHighRaw = metrics.drift_ci_high?.[index]
    return {
      drift: typeof driftRaw === "number" ? driftRaw : null,
      ciLow: typeof ciLowRaw === "number" ? ciLowRaw : null,
      ciHigh: typeof ciHighRaw === "number" ? ciHighRaw : null,
    }
  }, [selectedPair, metrics])

  if (!selectedPair) return null

  let driftLine: string = copy.company.selectedPairCallout.driftUnavailable
  if (driftSummary.drift !== null) {
    const driftValue = formatValue(driftSummary.drift)
    if (driftSummary.ciLow !== null && driftSummary.ciHigh !== null) {
      driftLine = copy.company.selectedPairCallout.driftWithCi({
        drift: driftValue,
        low: formatValue(driftSummary.ciLow),
        high: formatValue(driftSummary.ciHigh),
      })
    } else {
      driftLine = copy.company.selectedPairCallout.driftLine({ drift: driftValue })
    }
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="text-xs uppercase tracking-wider text-slate-500">
            {copy.company.selectedPairCallout.label}
          </div>
          <div className="text-sm font-semibold text-slate-900">
            {copy.company.selectedPairCallout.title({
              fromYear: selectedPair.from,
              toYear: selectedPair.to,
            })}
          </div>
          <div className="text-xs text-slate-600">{driftLine}</div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <a
            href={`#${evidenceAnchorId}`}
            className="rounded-full border border-slate-300 px-2.5 py-1 text-slate-700 hover:bg-white"
          >
            {copy.company.selectedPairCallout.jumpToEvidence}
          </a>
          {secUrl ? (
            <a
              href={secUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-full border border-slate-300 px-2.5 py-1 text-slate-700 hover:bg-white"
            >
              {copy.company.selectedPairCallout.openFiling({
                year: selectedPair.to,
              })}
            </a>
          ) : null}
        </div>
      </div>
    </div>
  )
}
