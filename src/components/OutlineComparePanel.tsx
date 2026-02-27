import { useMemo, useState } from "react"
import type {
  LabOutlineCompareOutput,
  LabOutlineMaterialChange,
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

export default function OutlineComparePanel({
  modelALabel,
  modelBLabel,
  modelAOutput,
  modelBOutput,
  modelADebug = null,
  modelBDebug = null,
  modelADebugPath = null,
  modelBDebugPath = null,
}: OutlineComparePanelProps) {
  const [activeModel, setActiveModel] = useState<"A" | "B">("A")
  const [selectedClass, setSelectedClass] = useState<"all" | OutlineChangeClass>("all")
  const [needleOnly, setNeedleOnly] = useState(false)

  const activeOutput = activeModel === "A" ? modelAOutput : modelBOutput

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

  return (
    <section id="lab-outline-compare" className="space-y-4 rounded-xl border border-emerald-300/25 bg-emerald-400/10 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-emerald-100">Outline Compare</h3>
          <p className="mt-1 text-[11px] text-slate-200">
            Filing-first structure-aware comparison (precomputed). Use filters to isolate material
            and needle changes.
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
        Active model: {activeModel === "A" ? modelALabel : modelBLabel}
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
          <div className="grid gap-3 lg:grid-cols-2">
            {renderOutlineColumn(`${activeOutput.year_from} outline`, activeOutput, "prev")}
            {renderOutlineColumn(`${activeOutput.year_to} outline`, activeOutput, "curr")}
          </div>

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
                        {ref.year} para {ref.paragraph_idx + 1}
                      </span>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      ) : null}
    </section>
  )
}
