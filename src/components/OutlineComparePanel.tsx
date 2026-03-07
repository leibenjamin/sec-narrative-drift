import { useMemo, useState, type ReactNode } from "react"
import { formatFiscalYearLabel } from "../lib/fiscalYear"
import type {
  LabOutlineChangeMechanismRow,
  LabOutlineCompareOutput,
  LabOutlineCompareV2Output,
  LabOutlineEvidence,
  LabOutlineEvidenceRef,
  LabOutlineInvestorRelevanceRow,
  LabOutlineLimitRow,
  LabOutlineMaterialChange,
  LabOutlineRiskGraphRow,
  OutlineChangeClass,
} from "../lib/labTypes"

type OutlineArtifactDebugInfo = {
  expectedPath: string | null
  requestedUrl: string | null
  errorText: string | null
}

type OutlineComparePanelProps = {
  modelALabel: string
  modelBLabel: string
  modelAOutput: LabOutlineCompareOutput | null
  modelBOutput: LabOutlineCompareOutput | null
  modelADebug?: OutlineArtifactDebugInfo | null
  modelBDebug?: OutlineArtifactDebugInfo | null
  modelADebugPath?: string | null
  modelBDebugPath?: string | null
  modelAStructuredOutput?: LabOutlineCompareV2Output | null
  modelBStructuredOutput?: LabOutlineCompareV2Output | null
  modelAStructuredDebug?: OutlineArtifactDebugInfo | null
  modelBStructuredDebug?: OutlineArtifactDebugInfo | null
  modelAStructuredDebugPath?: string | null
  modelBStructuredDebugPath?: string | null
}

const CHANGE_CLASSES: Array<{ id: "all" | OutlineChangeClass; label: string }> = [
  { id: "all", label: "All classes" },
  { id: "added", label: "Added" },
  { id: "removed", label: "Removed" },
  { id: "moved", label: "Moved" },
  { id: "split", label: "Split" },
  { id: "merged", label: "Merged" },
  { id: "reworded", label: "Reworded" },
  { id: "intensified", label: "Intensified" },
  { id: "softened", label: "Softened" },
  { id: "stable", label: "Stable" },
]

function isNeedleChange(change: LabOutlineMaterialChange): boolean {
  return change.evidence_refs.length <= 2
}

function formatClassLabel(value: string): string {
  if (!value) return "Change"
  return value.charAt(0).toUpperCase() + value.slice(1)
}

function formatTimeHorizon(value: string): string {
  if (value === "near_term") return "Near term"
  if (value === "medium_term") return "Medium term"
  if (value === "long_term") return "Long term"
  return value
}

function buildAlignmentSummary(output: LabOutlineCompareOutput): string {
  const counts = new Map<string, number>()
  for (const row of output.node_alignment) {
    counts.set(row.change_class, (counts.get(row.change_class) ?? 0) + 1)
  }
  const classes = ["added", "removed", "moved", "reworded", "intensified", "softened"]
  const parts: string[] = []
  for (const key of classes) {
    const count = counts.get(key) ?? 0
    if (count > 0) {
      parts.push(`${key}:${count}`)
    }
  }
  if (parts.length === 0) {
    return "No high-salience structural shifts detected."
  }
  return parts.join(" | ")
}

function renderMissingPanel(
  label: string,
  debug: OutlineArtifactDebugInfo | null | undefined,
  debugPath: string | null | undefined
) {
  return (
    <div className="rounded-md border border-amber-400/30 bg-amber-400/10 p-3 text-xs text-slate-200">
      <div className="font-semibold text-amber-100">{label}: outline artifact missing</div>
      {debug?.expectedPath ? (
        <p className="mt-1 break-all text-[11px] text-slate-100">Expected path: {debug.expectedPath}</p>
      ) : null}
      {debug?.requestedUrl ? (
        <p className="mt-1 break-all text-[11px] text-slate-300">Requested URL: {debug.requestedUrl}</p>
      ) : null}
      {debug?.errorText ? (
        <p className="mt-1 text-[11px] text-amber-100">{debug.errorText}</p>
      ) : null}
      {debugPath ? <p className="mt-1 break-all text-[11px] text-slate-300">{debugPath}</p> : null}
    </div>
  )
}

function buildEvidenceKey(ref: LabOutlineEvidenceRef): string {
  return `${ref.year}:${ref.paragraph_idx}`
}

function buildEvidenceLookup(evidenceBank: LabOutlineEvidence[]): Map<string, LabOutlineEvidence> {
  const lookup = new Map<string, LabOutlineEvidence>()
  for (const row of evidenceBank) {
    lookup.set(`${row.year}:${row.paragraph_idx}`, row)
  }
  return lookup
}

function formatEvidenceRef(ref: LabOutlineEvidenceRef): string {
  return `${ref.year} para ${ref.paragraph_idx + 1}`
}

function renderEvidenceRefs(
  refs: LabOutlineEvidenceRef[],
  evidenceLookup: Map<string, LabOutlineEvidence>
) {
  if (refs.length === 0) return null
  return (
    <div className="mt-2 space-y-2">
      <div className="flex flex-wrap gap-2 text-[11px]">
        {refs.map((ref, index) => (
          <span key={`${buildEvidenceKey(ref)}:${index}`} className="rounded bg-slate-900/60 px-2 py-0.5 text-slate-200">
            {formatEvidenceRef(ref)}
          </span>
        ))}
      </div>
      <div className="space-y-1">
        {refs.slice(0, 2).map((ref, index) => {
          const evidence = evidenceLookup.get(buildEvidenceKey(ref))
          if (!evidence) return null
          return (
            <p key={`${buildEvidenceKey(ref)}:snippet:${index}`} className="text-[11px] text-slate-400">
              "{evidence.snippet}"
            </p>
          )
        })}
      </div>
    </div>
  )
}

function renderOutlineColumn(
  label: string,
  output: LabOutlineCompareOutput,
  which: "prev" | "curr"
) {
  const nodes = which === "prev" ? output.outline_prev : output.outline_curr
  const levelOneNodes = nodes
    .filter((node) => node.level === 1)
    .sort((a, b) => a.order - b.order)
  const childByParent = new Map<string, typeof nodes>()
  for (const node of nodes) {
    if (!node.parent_id) continue
    const bucket = childByParent.get(node.parent_id) ?? []
    bucket.push(node)
    childByParent.set(node.parent_id, bucket)
  }

  return (
    <div className="rounded-md border border-white/10 bg-slate-950/35 p-3">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-300">{label}</h4>
      <div className="mt-2 space-y-2 text-xs text-slate-200">
        {levelOneNodes.map((root) => {
          const l2Nodes = (childByParent.get(root.node_id) ?? [])
            .filter((node) => node.level === 2)
            .sort((a, b) => a.order - b.order)
          return (
            <div key={root.node_id} className="rounded border border-white/10 bg-slate-900/40 p-2">
              <p className="font-semibold text-slate-100">{root.label}</p>
              <p className="mt-1 text-[11px] text-slate-300">{root.risk_thesis}</p>
              {l2Nodes.length ? (
                <div className="mt-2 space-y-1">
                  {l2Nodes.slice(0, 4).map((node) => (
                    <div key={node.node_id} className="text-[11px] text-slate-300">
                      {node.label}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function renderStructuredListCard(props: {
  title: string
  items: Array<LabOutlineInvestorRelevanceRow | LabOutlineChangeMechanismRow | LabOutlineLimitRow>
  evidenceLookup: Map<string, LabOutlineEvidence>
  renderBody: (
    item: LabOutlineInvestorRelevanceRow | LabOutlineChangeMechanismRow | LabOutlineLimitRow
  ) => ReactNode
  emptyText: string
}) {
  const { title, items, evidenceLookup, renderBody, emptyText } = props
  return (
    <div className="rounded-md border border-white/10 bg-slate-950/35 p-3">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-300">{title}</h4>
      <div className="mt-2 space-y-3 text-xs text-slate-200">
        {items.length === 0 ? (
          <p className="text-slate-400">{emptyText}</p>
        ) : (
          items.map((item) => (
            <div key={item.id} className="rounded border border-white/10 bg-slate-900/40 p-2">
              {renderBody(item)}
              {renderEvidenceRefs(item.evidence_refs, evidenceLookup)}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function renderRiskGraphCard(props: {
  title: string
  rows: LabOutlineRiskGraphRow[]
  year: number
}) {
  const { title, rows, year } = props
  return (
    <div className="rounded-md border border-white/10 bg-slate-950/35 p-3">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-300">{title}</h4>
      <div className="mt-2 space-y-2 text-xs text-slate-200">
        {rows.length === 0 ? (
          <p className="text-slate-400">No risk-graph rows in the structured sidecar.</p>
        ) : (
          rows.slice(0, 3).map((row) => (
            <div key={row.id} className="rounded border border-white/10 bg-slate-900/40 p-2">
              <div className="font-medium text-slate-100">{row.driver}</div>
              <div className="mt-1 text-[11px] text-slate-300">Exposure: {row.exposure}</div>
              <div className="mt-1 text-[11px] text-slate-300">Impact: {row.impact}</div>
              <div className="mt-2 text-[11px] text-slate-400">
                {row.evidence_paragraph_idx.slice(0, 3).map((idx) => `${year} para ${idx + 1}`).join(" | ")}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default function OutlineComparePanel({
  modelALabel,
  modelBLabel,
  modelAOutput,
  modelBOutput,
  modelADebug = null,
  modelBDebug = null,
  modelADebugPath = null,
  modelBDebugPath = null,
  modelAStructuredOutput = null,
  modelBStructuredOutput = null,
  modelAStructuredDebug = null,
  modelBStructuredDebug = null,
  modelAStructuredDebugPath = null,
  modelBStructuredDebugPath = null,
}: OutlineComparePanelProps) {
  const [activeModel, setActiveModel] = useState<"A" | "B">("A")
  const [selectedClass, setSelectedClass] = useState<"all" | OutlineChangeClass>("all")
  const [needleOnly, setNeedleOnly] = useState(false)

  const activeOutput = activeModel === "A" ? modelAOutput : modelBOutput
  const activeStructuredOutput = activeModel === "A" ? modelAStructuredOutput : modelBStructuredOutput
  const activeStructuredDebug = activeModel === "A" ? modelAStructuredDebug : modelBStructuredDebug
  const activeStructuredDebugPath = activeModel === "A" ? modelAStructuredDebugPath : modelBStructuredDebugPath
  const activeModelLabel = activeModel === "A" ? modelALabel : modelBLabel

  const filteredChanges = useMemo(() => {
    if (!activeOutput) return []
    return activeOutput.material_changes
      .filter((change) => (selectedClass === "all" ? true : change.change_class === selectedClass))
      .filter((change) => (needleOnly ? isNeedleChange(change) : true))
      .sort((a, b) => b.salience - a.salience)
  }, [activeOutput, needleOnly, selectedClass])

  const summary = useMemo(() => {
    if (!activeOutput) return "Outline compare output unavailable."
    return buildAlignmentSummary(activeOutput)
  }, [activeOutput])

  const evidenceLookup = useMemo(() => {
    if (!activeStructuredOutput) return new Map<string, LabOutlineEvidence>()
    return buildEvidenceLookup(activeStructuredOutput.evidence_bank)
  }, [activeStructuredOutput])

  return (
    <section id="lab-outline-compare" className="space-y-4 rounded-xl border border-emerald-300/25 bg-emerald-400/10 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-emerald-100">Outline Compare</h3>
          <p className="mt-1 text-[11px] text-slate-200">
            Filing-first structure-aware comparison. Runtime data anchors the compare, and structured sidecars
            add the investor, mechanism, and limitation sections.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setActiveModel("A")}
            className={`rounded-md border px-2 py-1 text-xs transition ${
              activeModel === "A"
                ? "border-sky-200/70 bg-sky-400/25 text-sky-50"
                : "border-white/20 bg-slate-900/50 text-slate-200"
            }`}
          >
            Model A
          </button>
          <button
            type="button"
            onClick={() => setActiveModel("B")}
            className={`rounded-md border px-2 py-1 text-xs transition ${
              activeModel === "B"
                ? "border-emerald-200/70 bg-emerald-400/25 text-emerald-50"
                : "border-white/20 bg-slate-900/50 text-slate-200"
            }`}
          >
            Model B
          </button>
        </div>
      </div>

      <div className="rounded-md border border-white/10 bg-slate-950/30 px-3 py-2 text-sm text-slate-100">
        Active model: {activeModelLabel}
      </div>

      <div className="rounded-md border border-white/10 bg-slate-950/30 px-3 py-2 text-xs text-slate-200">
        Structure summary: {summary}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <select
          value={selectedClass}
          onChange={(event) => setSelectedClass(event.target.value as "all" | OutlineChangeClass)}
          className="rounded-md border border-white/20 bg-slate-950/50 px-2 py-1 text-xs text-slate-100"
        >
          {CHANGE_CLASSES.map((option) => (
            <option key={option.id} value={option.id}>
              {option.label}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 rounded-md border border-white/20 bg-slate-950/50 px-2 py-1 text-xs text-slate-200">
          <input
            type="checkbox"
            checked={needleOnly}
            onChange={(event) => setNeedleOnly(event.target.checked)}
            className="h-3 w-3"
          />
          Needle changes only
        </label>
      </div>

      {!modelAOutput ? renderMissingPanel(modelALabel, modelADebug, modelADebugPath) : null}
      {!modelBOutput ? renderMissingPanel(modelBLabel, modelBDebug, modelBDebugPath) : null}

      {activeOutput ? (
        <>
          <div className="space-y-2">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-300">
              Material changes ({filteredChanges.length})
            </h4>
            {filteredChanges.length === 0 ? (
              <p className="rounded-md border border-white/10 bg-slate-950/35 px-3 py-2 text-xs text-slate-300">
                No changes matched the active filters.
              </p>
            ) : (
              filteredChanges.slice(0, 6).map((change) => (
                <div
                  key={change.id}
                  className="rounded-md border border-white/10 bg-slate-950/35 p-3 text-xs text-slate-200"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="font-semibold text-slate-100">{change.title}</div>
                    <div className="rounded-full border border-white/20 bg-white/5 px-2 py-0.5 text-[11px] text-slate-200">
                      {formatClassLabel(change.change_class)} | salience {change.salience.toFixed(2)}
                    </div>
                  </div>
                  <p className="mt-1 text-[11px] text-slate-300">{change.caveat}</p>
                  <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
                    {change.evidence_refs.map((ref, index) => (
                      <span key={`${change.id}:${index}`} className="rounded bg-slate-900/60 px-2 py-0.5 text-slate-200">
                        {formatEvidenceRef(ref)}
                      </span>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>

          {activeStructuredOutput ? (
            <>
              <div className="rounded-md border border-white/10 bg-slate-950/30 px-3 py-2 text-xs text-slate-200">
                Structured sidecar coverage: investor relevance {activeStructuredOutput.investor_relevance.length} |
                mechanisms {activeStructuredOutput.change_mechanisms.length} | limits {activeStructuredOutput.uncertainty_and_limits.length}
              </div>

              <div className="grid gap-3 xl:grid-cols-2">
                {renderStructuredListCard({
                  title: "Why it matters",
                  items: activeStructuredOutput.investor_relevance.slice(0, 3),
                  evidenceLookup,
                  emptyText: "No investor-relevance rows in the structured sidecar.",
                  renderBody: (item) => (
                    <p className="text-[11px] text-slate-200">
                      {(item as LabOutlineInvestorRelevanceRow).why_it_matters}
                    </p>
                  ),
                })}
                {renderStructuredListCard({
                  title: "Change mechanisms",
                  items: activeStructuredOutput.change_mechanisms.slice(0, 3),
                  evidenceLookup,
                  emptyText: "No mechanism rows in the structured sidecar.",
                  renderBody: (item) => {
                    const mechanism = item as LabOutlineChangeMechanismRow
                    return (
                      <>
                        <p className="text-[11px] font-medium text-slate-100">{mechanism.mechanism}</p>
                        <p className="mt-1 text-[11px] text-slate-300">Channel: {mechanism.transmission_channel}</p>
                        <p className="mt-1 text-[11px] text-slate-300">Business effect: {mechanism.business_effect}</p>
                        <p className="mt-1 text-[11px] text-slate-400">{formatTimeHorizon(mechanism.time_horizon)}</p>
                      </>
                    )
                  },
                })}
              </div>

              <div className="grid gap-3 xl:grid-cols-2">
                {renderStructuredListCard({
                  title: "Uncertainty and limits",
                  items: activeStructuredOutput.uncertainty_and_limits.slice(0, 3),
                  evidenceLookup,
                  emptyText: "No limitation rows in the structured sidecar.",
                  renderBody: (item) => (
                    <p className="text-[11px] text-slate-200">
                      {(item as LabOutlineLimitRow).limitation}
                    </p>
                  ),
                })}
                <div className="space-y-3">
                  {renderRiskGraphCard({
                    title: `${formatFiscalYearLabel(activeStructuredOutput.year_from)} risk graph`,
                    rows: activeStructuredOutput.risk_graph_prev,
                    year: activeStructuredOutput.year_from,
                  })}
                  {renderRiskGraphCard({
                    title: `${formatFiscalYearLabel(activeStructuredOutput.year_to)} risk graph`,
                    rows: activeStructuredOutput.risk_graph_curr,
                    year: activeStructuredOutput.year_to,
                  })}
                </div>
              </div>
            </>
          ) : (
            <div className="rounded-md border border-white/10 bg-slate-950/30 px-3 py-2 text-xs text-slate-300">
              Structured sidecar unavailable for {activeModelLabel}. Showing runtime-only compare.
              {activeStructuredDebug?.errorText ? ` ${activeStructuredDebug.errorText}` : ""}
              {activeStructuredDebug?.expectedPath ? ` Expected path: ${activeStructuredDebug.expectedPath}` : ""}
              {activeStructuredDebugPath ? ` ${activeStructuredDebugPath}` : ""}
            </div>
          )}

          <div className="grid gap-3 lg:grid-cols-2">
            {renderOutlineColumn(`${formatFiscalYearLabel(activeOutput.year_from)} outline`, activeOutput, "prev")}
            {renderOutlineColumn(`${formatFiscalYearLabel(activeOutput.year_to)} outline`, activeOutput, "curr")}
          </div>
        </>
      ) : null}
    </section>
  )
}