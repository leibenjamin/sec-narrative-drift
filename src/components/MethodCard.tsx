import EvidenceStack from "./EvidenceStack"
import LabExcerptPickerPanel from "./LabExcerptPickerPanel"
import type { LabOutput, RankedItem } from "../lib/labTypes"

const EMPTY_ITEMS: RankedItem[] = []

type MethodCardProps = {
  title: string
  description?: string
  output: LabOutput | null
  isLoading?: boolean
  emptyMessage?: string
  debugPath?: string | null
}

function normalizeRankedList(raw: unknown): RankedItem[] {
  if (!Array.isArray(raw)) return EMPTY_ITEMS
  const items: RankedItem[] = []
  for (const entry of raw) {
    if (!entry || typeof entry !== "object") continue
    const record = entry as RankedItem
    if (typeof record.label === "string" && typeof record.score === "number") {
      items.push(record)
    }
  }
  return items
}

function formatMetric(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "-"
  return value.toFixed(3)
}

export default function MethodCard({
  title,
  description,
  output,
  isLoading,
  emptyMessage,
  debugPath,
}: MethodCardProps) {
  const warnings = output?.metrics.warnings ?? []
  const rankedItems = normalizeRankedList(output?.artifacts.ranked_items)
  const topRisers = normalizeRankedList(output?.artifacts.top_risers)
  const topFallers = normalizeRankedList(output?.artifacts.top_fallers)
  const isExcerptPicker = output?.detector_id === "det_llm_excerpt_picker_v1"
  const isDeltaBrief = output?.detector_id === "det_llm_delta_brief_v1"
  const deltaBriefRaw = isDeltaBrief ? output?.artifacts.delta_brief : null
  const deltaBriefText =
    typeof deltaBriefRaw === "string"
      ? deltaBriefRaw.trim()
      : deltaBriefRaw
        ? JSON.stringify(deltaBriefRaw, null, 2)
        : ""

  return (
    <section className="rounded-xl border border-white/10 bg-slate-950/40 p-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-100">{title}</h3>
          {description ? <p className="text-xs text-slate-400">{description}</p> : null}
        </div>
        <div className="flex flex-wrap gap-3 text-xs text-slate-300">
          <span>drift {formatMetric(output?.metrics.drift_score)}</span>
          <span>confidence {formatMetric(output?.metrics.confidence)}</span>
          <span>coverage {formatMetric(output?.metrics.coverage)}</span>
        </div>
      </header>

      {isLoading ? (
        <p className="mt-3 text-xs text-slate-400">Loading detector output...</p>
      ) : null}

      {!isLoading && !output ? (
        <div className="mt-3 space-y-1">
          <p className="text-xs text-slate-400">{emptyMessage ?? "No lab output yet."}</p>
          {debugPath ? <p className="break-all text-[11px] text-slate-500">{debugPath}</p> : null}
        </div>
      ) : null}

      {output ? (
        <div className="mt-4 space-y-4">
          {warnings.length ? (
            <div className="rounded-md border border-amber-400/30 bg-amber-400/10 p-3 text-xs text-amber-100">
              Warnings: {warnings.join(", ")}
            </div>
          ) : null}

          {rankedItems.length ? (
            <div>
              <div className="text-xs uppercase tracking-wide text-slate-400">Top ranked</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {rankedItems.slice(0, 8).map((item) => (
                  <span
                    key={item.label}
                    className="rounded-full border border-white/10 bg-white/5 px-2 py-1 text-xs text-slate-200"
                  >
                    {item.label} · {item.score.toFixed(2)}
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          {topRisers.length || topFallers.length ? (
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <div className="text-xs uppercase tracking-wide text-slate-400">Risers</div>
                <ul className="mt-2 space-y-1 text-xs text-slate-200">
                  {topRisers.slice(0, 6).map((item) => (
                    <li key={item.label}>{item.label}</li>
                  ))}
                </ul>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-slate-400">Fallers</div>
                <ul className="mt-2 space-y-1 text-xs text-slate-200">
                  {topFallers.slice(0, 6).map((item) => (
                    <li key={item.label}>{item.label}</li>
                  ))}
                </ul>
              </div>
            </div>
          ) : null}

          <div>
            <div className="text-xs uppercase tracking-wide text-slate-400">Evidence</div>
            <div className="mt-2">
              {isDeltaBrief && deltaBriefText ? (
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-400">Delta brief</div>
                  <div className="mt-2 whitespace-pre-wrap rounded-md border border-white/10 bg-white/5 p-3 text-xs text-slate-200">
                    {deltaBriefText}
                  </div>
                </div>
              ) : null}

              {isExcerptPicker ? (
                <LabExcerptPickerPanel output={output} />
              ) : (
                <EvidenceStack
                  evidence={output.evidence ?? []}
                  fallbackMessage="No evidence blocks for this detector yet."
                />
              )}
            </div>
          </div>
        </div>
      ) : null}
    </section>
  )
}
