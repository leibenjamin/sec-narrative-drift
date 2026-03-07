import { useMemo, useState } from "react"
import { formatFiscalYearLabel } from "../lib/fiscalYear"
import type {
  LabOutlineCompareOutput,
  LabOutlineCompareV2Output,
  LabOutlineEvidence,
  LabOutlineEvidenceRef,
} from "../lib/labTypes"

type RiskNarrativeSummaryProps = {
  ticker: string
  yearFrom: number
  yearTo: number
  modelALabel: string
  modelBLabel: string
  modelARuntime: LabOutlineCompareOutput | null
  modelBRuntime: LabOutlineCompareOutput | null
  modelAStructured: LabOutlineCompareV2Output | null
  modelBStructured: LabOutlineCompareV2Output | null
}

const CHANGE_CLASS_DISPLAY: Record<string, { label: string; color: string }> = {
  added: { label: "Added", color: "text-emerald-300 bg-emerald-400/15 border-emerald-400/30" },
  removed: { label: "Removed", color: "text-rose-300 bg-rose-400/15 border-rose-400/30" },
  intensified: { label: "Intensified", color: "text-amber-300 bg-amber-400/15 border-amber-400/30" },
  softened: { label: "Softened", color: "text-sky-300 bg-sky-400/15 border-sky-400/30" },
  reworded: { label: "Reworded", color: "text-violet-300 bg-violet-400/15 border-violet-400/30" },
  split: { label: "Split", color: "text-cyan-300 bg-cyan-400/15 border-cyan-400/30" },
  merged: { label: "Merged", color: "text-indigo-300 bg-indigo-400/15 border-indigo-400/30" },
  moved: { label: "Moved", color: "text-slate-300 bg-slate-400/15 border-slate-400/30" },
  stable: { label: "Stable", color: "text-slate-400 bg-slate-400/10 border-slate-400/20" },
}

function formatClassBadge(changeClass: string) {
  const info = CHANGE_CLASS_DISPLAY[changeClass] ?? { label: changeClass, color: "text-slate-300 bg-slate-400/10 border-slate-400/20" }
  return (
    <span className={`inline-block rounded-full border px-2 py-0.5 text-[11px] font-medium ${info.color}`}>
      {info.label}
    </span>
  )
}

function formatEvidenceRef(ref: LabOutlineEvidenceRef): string {
  return `${ref.year} para ${ref.paragraph_idx + 1}`
}

function buildAlignmentDistribution(output: LabOutlineCompareOutput): Map<string, number> {
  const counts = new Map<string, number>()
  for (const row of output.node_alignment) {
    counts.set(row.change_class, (counts.get(row.change_class) ?? 0) + 1)
  }
  return counts
}

function buildEvidenceLookup(bank: LabOutlineEvidence[]): Map<string, LabOutlineEvidence> {
  const lookup = new Map<string, LabOutlineEvidence>()
  for (const row of bank) {
    lookup.set(`${row.year}:${row.paragraph_idx}`, row)
  }
  return lookup
}

function buildDriftScore(output: LabOutlineCompareOutput): { score: number; label: string } {
  const counts = buildAlignmentDistribution(output)
  const total = output.node_alignment.length
  if (total === 0) return { score: 0, label: "No data" }
  const dynamic = (counts.get("added") ?? 0) + (counts.get("removed") ?? 0) + (counts.get("intensified") ?? 0) + (counts.get("softened") ?? 0) + (counts.get("split") ?? 0) + (counts.get("merged") ?? 0)
  const ratio = dynamic / total
  if (ratio >= 0.6) return { score: ratio, label: "High drift" }
  if (ratio >= 0.3) return { score: ratio, label: "Moderate drift" }
  return { score: ratio, label: "Low drift" }
}

export default function RiskNarrativeSummary({
  ticker,
  yearFrom,
  yearTo,
  modelALabel,
  modelBLabel,
  modelARuntime,
  modelBRuntime,
  modelAStructured,
  modelBStructured,
}: RiskNarrativeSummaryProps) {
  const [activeModel, setActiveModel] = useState<"A" | "B">("A")
  const [showEvidence, setShowEvidence] = useState<string | null>(null)

  const runtime = activeModel === "A" ? modelARuntime : modelBRuntime
  const structured = activeModel === "A" ? modelAStructured : modelBStructured
  const modelLabel = activeModel === "A" ? modelALabel : modelBLabel

  const hasBothModels = modelARuntime !== null && modelBRuntime !== null

  const drift = useMemo(() => {
    if (!runtime) return null
    return buildDriftScore(runtime)
  }, [runtime])

  const alignmentCounts = useMemo(() => {
    if (!runtime) return new Map<string, number>()
    return buildAlignmentDistribution(runtime)
  }, [runtime])

  const topChanges = useMemo(() => {
    if (!runtime) return []
    return [...runtime.material_changes]
      .sort((a, b) => b.salience - a.salience)
      .slice(0, 5)
  }, [runtime])

  const evidenceLookup = useMemo(() => {
    if (!structured) return new Map<string, LabOutlineEvidence>()
    return buildEvidenceLookup(structured.evidence_bank)
  }, [structured])

  const investorItems = useMemo(() => {
    if (!structured) return []
    return structured.investor_relevance.slice(0, 4)
  }, [structured])

  const mechanismItems = useMemo(() => {
    if (!structured) return []
    return structured.change_mechanisms.slice(0, 4)
  }, [structured])

  const limitItems = useMemo(() => {
    if (!structured) return []
    return structured.uncertainty_and_limits.slice(0, 3)
  }, [structured])

  if (!modelARuntime && !modelBRuntime) {
    return (
      <section className="rounded-xl border border-slate-600/30 bg-slate-900/40 p-5">
        <h3 className="text-base font-semibold text-slate-200">Risk narrative analysis</h3>
        <p className="mt-2 text-sm text-slate-400">
          AI-generated outline comparison data is not yet available for {ticker}. Deterministic methods below
          provide quantitative drift signals.
        </p>
      </section>
    )
  }

  return (
    <section id="lab-risk-narrative" className="space-y-5 rounded-xl border border-slate-500/25 bg-linear-to-b from-slate-900/60 to-slate-950/40 p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-slate-100">
            Risk narrative changes: {ticker} {formatFiscalYearLabel(yearFrom)} to {formatFiscalYearLabel(yearTo)}
          </h3>
          <p className="mt-1 text-xs text-slate-400">
            AI-generated structural analysis of how the risk disclosure narrative evolved between filings.
            Based on outline comparison of Item 1A risk factors.
          </p>
        </div>
        {hasBothModels ? (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveModel("A")}
              className={`rounded-md border px-2.5 py-1 text-xs transition ${
                activeModel === "A"
                  ? "border-sky-300/60 bg-sky-400/20 text-sky-100"
                  : "border-white/15 bg-slate-900/50 text-slate-300 hover:border-white/30"
              }`}
            >
              {modelALabel}
            </button>
            <button
              type="button"
              onClick={() => setActiveModel("B")}
              className={`rounded-md border px-2.5 py-1 text-xs transition ${
                activeModel === "B"
                  ? "border-emerald-300/60 bg-emerald-400/20 text-emerald-100"
                  : "border-white/15 bg-slate-900/50 text-slate-300 hover:border-white/30"
              }`}
            >
              {modelBLabel}
            </button>
          </div>
        ) : (
          <div className="text-xs text-slate-400">Model: {modelLabel}</div>
        )}
      </div>

      {drift ? (
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg border border-white/10 bg-slate-950/40 p-3">
            <div className="text-[11px] uppercase tracking-wide text-slate-400">Structural drift</div>
            <div className="mt-1 text-lg font-semibold text-slate-100">
              {(drift.score * 100).toFixed(0)}%
            </div>
            <div className="text-xs text-slate-300">{drift.label}</div>
          </div>
          <div className="rounded-lg border border-white/10 bg-slate-950/40 p-3">
            <div className="text-[11px] uppercase tracking-wide text-slate-400">Material changes</div>
            <div className="mt-1 text-lg font-semibold text-slate-100">
              {runtime?.material_changes.length ?? 0}
            </div>
            <div className="text-xs text-slate-300">
              {runtime ? `Top salience: ${runtime.material_changes[0]?.salience.toFixed(2) ?? "n/a"}` : ""}
            </div>
          </div>
          <div className="rounded-lg border border-white/10 bg-slate-950/40 p-3">
            <div className="text-[11px] uppercase tracking-wide text-slate-400">Change distribution</div>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {(["added", "removed", "intensified", "softened", "split", "stable"] as const).map((cls) => {
                const count = alignmentCounts.get(cls) ?? 0
                if (count === 0) return null
                return (
                  <span key={cls} className="text-xs text-slate-200">
                    {formatClassBadge(cls)} <span className="ml-0.5">{count}</span>
                  </span>
                )
              })}
            </div>
          </div>
        </div>
      ) : null}

      {topChanges.length > 0 ? (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-300">
            Top material changes
          </h4>
          {topChanges.map((change) => (
            <div
              key={change.id}
              className="rounded-lg border border-white/10 bg-slate-950/35 p-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm font-medium text-slate-100">{change.title}</div>
                <div className="flex items-center gap-2">
                  {formatClassBadge(change.change_class)}
                  <span className="text-[11px] text-slate-400">salience {change.salience.toFixed(2)}</span>
                </div>
              </div>
              <p className="mt-1.5 text-xs text-slate-300">{change.caveat}</p>
              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                {change.evidence_refs.map((ref, idx) => {
                  const key = `${change.id}:${idx}`
                  const evidence = evidenceLookup.get(`${ref.year}:${ref.paragraph_idx}`)
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setShowEvidence(showEvidence === key ? null : key)}
                      className="rounded-full border border-white/15 bg-white/5 px-2 py-0.5 text-[11px] text-slate-200 transition hover:border-white/30"
                    >
                      {formatEvidenceRef(ref)}
                    </button>
                  )
                })}
              </div>
              {showEvidence?.startsWith(change.id + ":") ? (() => {
                const idx = parseInt(showEvidence.split(":")[1], 10)
                const ref = change.evidence_refs[idx]
                if (!ref) return null
                const evidence = evidenceLookup.get(`${ref.year}:${ref.paragraph_idx}`)
                if (!evidence) return null
                return (
                  <div className="mt-2 rounded-md border border-white/10 bg-slate-900/50 p-2.5 text-xs">
                    <div className="text-[11px] text-slate-400">{ref.year} para {ref.paragraph_idx + 1}</div>
                    <p className="mt-1 text-slate-200 italic">"{evidence.snippet}"</p>
                    <p className="mt-1 text-slate-400">{evidence.why}</p>
                  </div>
                )
              })() : null}
            </div>
          ))}
        </div>
      ) : null}

      {investorItems.length > 0 || mechanismItems.length > 0 ? (
        <div className="grid gap-3 lg:grid-cols-2">
          {investorItems.length > 0 ? (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-300">
                Why it matters for investors
              </h4>
              {investorItems.map((item) => (
                <div key={item.id} className="rounded-lg border border-white/10 bg-slate-950/35 p-3 text-xs">
                  <p className="text-slate-200">{item.why_it_matters}</p>
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {item.evidence_refs.map((ref, idx) => (
                      <span key={`${item.id}-${idx}`} className="rounded bg-slate-800/60 px-1.5 py-0.5 text-[11px] text-slate-400">
                        {formatEvidenceRef(ref)}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
          {mechanismItems.length > 0 ? (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-300">
                Change mechanisms
              </h4>
              {mechanismItems.map((item) => (
                <div key={item.id} className="rounded-lg border border-white/10 bg-slate-950/35 p-3 text-xs">
                  <p className="font-medium text-slate-100">{item.mechanism}</p>
                  <div className="mt-1 text-slate-300">Channel: {item.transmission_channel}</div>
                  <div className="mt-0.5 text-slate-300">Effect: {item.business_effect}</div>
                  <div className="mt-1 flex flex-wrap items-center gap-1.5">
                    <span className="rounded bg-slate-800/60 px-1.5 py-0.5 text-[11px] text-slate-400">
                      {item.time_horizon === "near_term" ? "Near term" : item.time_horizon === "medium_term" ? "Medium term" : item.time_horizon === "long_term" ? "Long term" : item.time_horizon}
                    </span>
                    {item.evidence_refs.map((ref, idx) => (
                      <span key={`${item.id}-${idx}`} className="rounded bg-slate-800/60 px-1.5 py-0.5 text-[11px] text-slate-400">
                        {formatEvidenceRef(ref)}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      {limitItems.length > 0 ? (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-300">
            Analysis limitations
          </h4>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {limitItems.map((item) => (
              <div key={item.id} className="rounded-lg border border-amber-400/15 bg-amber-400/5 p-3 text-xs text-slate-300">
                {item.limitation}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  )
}
