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

type AnalysisMode = "executive" | "deep"

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
  analysisMode?: AnalysisMode
}

type OutlineCompareColumn = {
  id: "A" | "B"
  label: string
  runtime: LabOutlineCompareOutput | null
  structured: LabOutlineCompareV2Output | null
  runtimeDebug: OutlineArtifactDebugInfo | null
  runtimeDebugPath: string | null
  structuredDebug: OutlineArtifactDebugInfo | null
  structuredDebugPath: string | null
  accentClass: string
  accentSurfaceClass: string
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

function sortMaterialChanges(output: LabOutlineCompareOutput | null): LabOutlineMaterialChange[] {
  if (!output) return []
  return [...output.material_changes].sort((left, right) => right.salience - left.salience)
}

function buildPanelCompareSummary(columns: OutlineCompareColumn[]): string {
  const available = columns.filter((column) => column.runtime)
  if (available.length < 2) {
    return "One compare campaign is active. Shared filters still apply, but the panel is currently a single-column read."
  }

  const leftLead = sortMaterialChanges(available[0].runtime)[0]
  const rightLead = sortMaterialChanges(available[1].runtime)[0]
  if (!leftLead || !rightLead) {
    return "Lead material changes are missing for at least one campaign."
  }

  if (leftLead.title === rightLead.title) {
    return `Both campaigns converge on the same lead change: ${leftLead.title}`
  }

  return `${available[0].label} leads with "${leftLead.title}"; ${available[1].label} leads with "${rightLead.title}".`
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

function renderEvidenceRefs(
  refs: LabOutlineEvidenceRef[],
  evidenceLookup: Map<string, LabOutlineEvidence>
) {
  if (refs.length === 0) return null
  return (
    <div className="mt-3 space-y-2">
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
  which: "prev" | "curr",
  analysisMode: AnalysisMode
) {
  const nodes = which === "prev" ? output.outline_prev : output.outline_curr
  const levelOneNodes = nodes.filter((node) => node.level === 1).sort((a, b) => a.order - b.order)
  const childByParent = new Map<string, typeof nodes>()
  for (const node of nodes) {
    if (!node.parent_id) continue
    const bucket = childByParent.get(node.parent_id) ?? []
    bucket.push(node)
    childByParent.set(node.parent_id, bucket)
  }
  const maxLevelTwo = analysisMode === "executive" ? 3 : 4

  return (
    <div className="rounded-md border border-white/10 bg-slate-950/35 p-3">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-300">{label}</h4>
      <div className="mt-2 space-y-2 text-xs text-slate-200">
        {levelOneNodes.map((root) => {
          const levelTwoNodes = (childByParent.get(root.node_id) ?? [])
            .filter((node) => node.level === 2)
            .sort((a, b) => a.order - b.order)
          return (
            <div key={root.node_id} className="rounded border border-white/10 bg-slate-900/40 p-2">
              <p className="font-semibold text-slate-100">{root.label}</p>
              <p className="mt-1 text-[11px] text-slate-300">{root.risk_thesis}</p>
              {levelTwoNodes.length > 0 ? (
                <div className="mt-2 space-y-1">
                  {levelTwoNodes.slice(0, maxLevelTwo).map((node) => (
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
  analysisMode: AnalysisMode
}) {
  const { title, rows, year, analysisMode } = props
  const maxRows = analysisMode === "executive" ? 2 : 3
  return (
    <div className="rounded-md border border-white/10 bg-slate-950/35 p-3">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-300">{title}</h4>
      <div className="mt-2 space-y-2 text-xs text-slate-200">
        {rows.length === 0 ? (
          <p className="text-slate-400">No risk-graph rows in the structured sidecar.</p>
        ) : (
          rows.slice(0, maxRows).map((row) => (
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

function renderCompareColumn(props: {
  column: OutlineCompareColumn
  selectedClass: "all" | OutlineChangeClass
  needleOnly: boolean
  analysisMode: AnalysisMode
}) {
  const { column, selectedClass, needleOnly, analysisMode } = props
  const runtime = column.runtime
  const structured = column.structured
  const maxChanges = analysisMode === "executive" ? 4 : 6

  if (!runtime) {
    return (
      <div className="space-y-3 rounded-[1.05rem] border border-white/10 bg-slate-950/24 p-4">
        <div className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-medium ${column.accentClass}`}>
          {column.label || `Campaign ${column.id}`}
        </div>
        {renderMissingPanel(column.label || `Campaign ${column.id}`, column.runtimeDebug, column.runtimeDebugPath)}
      </div>
    )
  }

  const filteredChanges = sortMaterialChanges(runtime)
    .filter((change) => (selectedClass === "all" ? true : change.change_class === selectedClass))
    .filter((change) => (needleOnly ? isNeedleChange(change) : true))
    .slice(0, maxChanges)
  const summary = buildAlignmentSummary(runtime)
  const evidenceLookup = structured ? buildEvidenceLookup(structured.evidence_bank) : new Map<string, LabOutlineEvidence>()

  return (
    <div className="space-y-4 rounded-[1.05rem] border border-white/10 bg-slate-950/24 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-medium ${column.accentClass}`}>
            {column.label || `Campaign ${column.id}`}
          </div>
          <p className="mt-2 text-sm font-semibold text-slate-100">{runtime.material_changes.length} material changes surfaced</p>
          <p className="mt-1 text-[11px] text-slate-400">{summary}</p>
        </div>
        <div className={`rounded-xl border px-3 py-2 text-xs ${column.accentSurfaceClass}`}>
          <div className="font-medium text-slate-100">Lead row</div>
          <p className="mt-1 text-slate-200">{sortMaterialChanges(runtime)[0]?.title ?? "Unavailable"}</p>
        </div>
      </div>

      <div className="space-y-3">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-300">Material changes</h4>
        {filteredChanges.length === 0 ? (
          <p className="rounded-md border border-white/10 bg-slate-950/35 px-3 py-2 text-xs text-slate-300">
            No changes matched the active filters.
          </p>
        ) : (
          filteredChanges.map((change) => (
            <div key={`${column.id}:${change.id}`} className="rounded-md border border-white/10 bg-slate-950/35 p-3 text-xs text-slate-200">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="font-semibold text-slate-100">{change.title}</div>
                <div className="rounded-full border border-white/20 bg-white/5 px-2 py-0.5 text-[11px] text-slate-200">
                  {formatClassLabel(change.change_class)} | salience {change.salience.toFixed(2)}
                </div>
              </div>
              <p className="mt-2 text-[11px] text-slate-300">{change.caveat}</p>
              {renderEvidenceRefs(change.evidence_refs, evidenceLookup)}
            </div>
          ))
        )}
      </div>

      {structured ? (
        <>
          <div className="rounded-md border border-white/10 bg-slate-950/30 px-3 py-2 text-xs text-slate-200">
            Structured sidecar coverage: investor relevance {structured.investor_relevance.length} |
            mechanisms {structured.change_mechanisms.length} | limits {structured.uncertainty_and_limits.length}
          </div>

          <div className="grid gap-3 xl:grid-cols-2">
            {renderStructuredListCard({
              title: "Why it matters",
              items: structured.investor_relevance.slice(0, analysisMode === "executive" ? 2 : 3),
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
              items: structured.change_mechanisms.slice(0, analysisMode === "executive" ? 2 : 3),
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
              items: structured.uncertainty_and_limits.slice(0, 3),
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
                title: `${formatFiscalYearLabel(structured.year_from)} risk graph`,
                rows: structured.risk_graph_prev,
                year: structured.year_from,
                analysisMode,
              })}
              {renderRiskGraphCard({
                title: `${formatFiscalYearLabel(structured.year_to)} risk graph`,
                rows: structured.risk_graph_curr,
                year: structured.year_to,
                analysisMode,
              })}
            </div>
          </div>
        </>
      ) : (
        <div className="rounded-md border border-white/10 bg-slate-950/30 px-3 py-2 text-xs text-slate-300">
          Structured sidecar unavailable for {column.label || `Campaign ${column.id}`}. Showing runtime-only compare.
          {column.structuredDebug?.errorText ? ` ${column.structuredDebug.errorText}` : ""}
          {column.structuredDebug?.expectedPath ? ` Expected path: ${column.structuredDebug.expectedPath}` : ""}
          {column.structuredDebugPath ? ` ${column.structuredDebugPath}` : ""}
        </div>
      )}

      <div className="grid gap-3 lg:grid-cols-2">
        {renderOutlineColumn(`${formatFiscalYearLabel(runtime.year_from)} outline`, runtime, "prev", analysisMode)}
        {renderOutlineColumn(`${formatFiscalYearLabel(runtime.year_to)} outline`, runtime, "curr", analysisMode)}
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
  analysisMode = "deep",
}: OutlineComparePanelProps) {
  const [selectedClass, setSelectedClass] = useState<"all" | OutlineChangeClass>("all")
  const [needleOnly, setNeedleOnly] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)

  const columns = useMemo(() => {
    const configured: OutlineCompareColumn[] = [
      {
        id: "A",
        label: modelALabel,
        runtime: modelAOutput,
        structured: modelAStructuredOutput,
        runtimeDebug: modelADebug,
        runtimeDebugPath: modelADebugPath,
        structuredDebug: modelAStructuredDebug,
        structuredDebugPath: modelAStructuredDebugPath,
        accentClass: "border-sky-200/70 bg-sky-400/18 text-sky-50",
        accentSurfaceClass: "border-sky-300/20 bg-sky-400/10 text-sky-50",
      },
      {
        id: "B",
        label: modelBLabel,
        runtime: modelBOutput,
        structured: modelBStructuredOutput,
        runtimeDebug: modelBDebug,
        runtimeDebugPath: modelBDebugPath,
        structuredDebug: modelBStructuredDebug,
        structuredDebugPath: modelBStructuredDebugPath,
        accentClass: "border-emerald-200/70 bg-emerald-400/18 text-emerald-50",
        accentSurfaceClass: "border-emerald-300/20 bg-emerald-400/10 text-emerald-50",
      },
    ]

    return configured.filter((column) => {
      if (column.label.trim().length > 0) return true
      return Boolean(column.runtime || column.structured)
    })
  }, [
    modelALabel,
    modelAOutput,
    modelAStructuredOutput,
    modelADebug,
    modelADebugPath,
    modelAStructuredDebug,
    modelAStructuredDebugPath,
    modelBLabel,
    modelBOutput,
    modelBStructuredOutput,
    modelBDebug,
    modelBDebugPath,
    modelBStructuredDebug,
    modelBStructuredDebugPath,
  ])

  return (
    <section id="lab-outline-compare" className="space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-white/8 bg-slate-950/16 px-3 py-3">
        <div className="max-w-3xl">
          <p className="text-sm font-medium text-slate-100">{buildPanelCompareSummary(columns)}</p>
          <p className="mt-1 text-[11px] text-slate-400">
            {analysisMode === "executive"
              ? "Executive mode keeps four material changes per campaign in view."
              : "Deep mode restores the fuller ranked compare, structured context, and outline read."}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setIsExpanded((previous) => !previous)}
          className="rounded-md border border-white/20 bg-slate-900/50 px-2.5 py-1.5 text-xs text-slate-100 transition hover:border-white/35"
        >
          {isExpanded ? "Hide detailed compare" : "Open detailed compare"}
        </button>
      </div>

      {!isExpanded ? (
        <p className="text-[11px] text-slate-400">
          Side-by-side ranked changes, structured mechanisms, limits, and outline structure stay one
          layer deeper until you open them.
        </p>
      ) : (
        <>
          <div className="rounded-xl border border-white/8 bg-slate-950/12 p-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="text-xs text-slate-300">
                Filter the detailed compare without changing the visible briefing above.
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
            </div>
          </div>

          <div className={`grid gap-4 ${columns.length > 1 ? "2xl:grid-cols-2" : "grid-cols-1"}`}>
            {columns.map((column) => (
              <div key={`outline-column-${column.id}`}>
                {renderCompareColumn({
                  column,
                  selectedClass,
                  needleOnly,
                  analysisMode,
                })}
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  )
}
