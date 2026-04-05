import { useEffect, useMemo, useRef, useState, type MutableRefObject } from "react"
import { loadLabInputFile } from "../lib/labData"
import { formatFiscalYearLabel } from "../lib/fiscalYear"
import type {
  LabOutlineCompareInsightOutput,
  LabOutlineInsightEvidenceMapEntry,
  LabOutlineInsightCard,
} from "../lib/labTypes"

type OutlineArtifactDebugInfo = {
  expectedPath: string | null
  requestedUrl: string | null
  errorText: string | null
}

type ParagraphBundle = {
  prev: string[]
  curr: string[]
}

type InsightLensPanelProps = {
  modelALabel: string
  modelBLabel: string
  modelAOutput: LabOutlineCompareInsightOutput | null
  modelBOutput: LabOutlineCompareInsightOutput | null
  modelADebug?: OutlineArtifactDebugInfo | null
  modelBDebug?: OutlineArtifactDebugInfo | null
  modelADebugPath?: string | null
  modelBDebugPath?: string | null
}

type YearEvidenceIndex = {
  prev: Set<number>
  curr: Set<number>
}

type TextSegment = {
  text: string
  highlight: boolean
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

function asStringArray(value: unknown): string[] | null {
  if (!Array.isArray(value)) return null
  const output: string[] = []
  for (const item of value) {
    if (typeof item !== "string") return null
    output.push(item)
  }
  return output
}

async function loadParagraphBundle(inputFile: string): Promise<ParagraphBundle> {
  const pairPayload = await loadLabInputFile(inputFile)
  const pairRoot = asRecord(pairPayload)
  if (!pairRoot) {
    throw new Error("Input pair payload is not an object.")
  }

  const yearInputs = asRecord(pairRoot.year_inputs)
  if (yearInputs) {
    const prevRef = typeof yearInputs.prev === "string" ? yearInputs.prev : ""
    const currRef = typeof yearInputs.curr === "string" ? yearInputs.curr : ""
    if (!prevRef || !currRef) {
      throw new Error("Pair payload year_inputs is missing prev/curr references.")
    }
    const [prevPayload, currPayload] = await Promise.all([
      loadLabInputFile(prevRef),
      loadLabInputFile(currRef),
    ])
    const prevTexts = asRecord(asRecord(prevPayload)?.texts)
    const currTexts = asRecord(asRecord(currPayload)?.texts)
    const prevParagraphs = asStringArray(prevTexts?.paragraphs)
    const currParagraphs = asStringArray(currTexts?.paragraphs)
    if (!prevParagraphs || !currParagraphs) {
      throw new Error("Year payload texts.paragraphs could not be resolved.")
    }
    return { prev: prevParagraphs, curr: currParagraphs }
  }

  const texts = asRecord(pairRoot.texts)
  const prevLegacy = asStringArray(texts?.prev_paragraphs)
  const currLegacy = asStringArray(texts?.curr_paragraphs)
  if (prevLegacy && currLegacy) {
    return { prev: prevLegacy, curr: currLegacy }
  }

  throw new Error("No resolvable year paragraphs found for insight lens view.")
}

function renderMissingPanel(
  label: string,
  debug: OutlineArtifactDebugInfo | null | undefined,
  debugPath: string | null | undefined
) {
  return (
    <div className="rounded-md border border-white/10 bg-slate-950/30 p-3 text-xs text-slate-200">
      <div className="font-semibold text-slate-100">{label}: insight lens unavailable</div>
      {debug?.expectedPath ? (
        <p className="mt-1 break-all text-[11px] text-slate-100">Expected path: {debug.expectedPath}</p>
      ) : null}
      {debug?.requestedUrl ? (
        <p className="mt-1 break-all text-[11px] text-slate-300">Requested URL: {debug.requestedUrl}</p>
      ) : null}
      {debug?.errorText ? <p className="mt-1 text-[11px] text-slate-300">{debug.errorText}</p> : null}
      {debugPath ? <p className="mt-1 break-all text-[11px] text-slate-300">{debugPath}</p> : null}
    </div>
  )
}

function addEvidenceRef(index: YearEvidenceIndex, yearFrom: number, yearTo: number, year: number, idx: number) {
  if (year === yearFrom) {
    index.prev.add(idx)
  } else if (year === yearTo) {
    index.curr.add(idx)
  }
}

function buildSegments(text: string, snippets: string[]): TextSegment[] {
  if (!snippets.length) return [{ text, highlight: false }]

  const ranges: Array<{ start: number; end: number }> = []
  for (const snippet of snippets) {
    if (!snippet) continue
    const at = text.indexOf(snippet)
    if (at >= 0) {
      ranges.push({ start: at, end: at + snippet.length })
    }
  }
  if (!ranges.length) return [{ text, highlight: false }]

  ranges.sort((a, b) => a.start - b.start)
  const merged: Array<{ start: number; end: number }> = []
  for (const range of ranges) {
    const last = merged[merged.length - 1]
    if (!last || range.start > last.end) {
      merged.push({ ...range })
      continue
    }
    if (range.end > last.end) {
      last.end = range.end
    }
  }

  const output: TextSegment[] = []
  let cursor = 0
  for (const range of merged) {
    if (range.start > cursor) {
      output.push({ text: text.slice(cursor, range.start), highlight: false })
    }
    output.push({ text: text.slice(range.start, range.end), highlight: true })
    cursor = range.end
  }
  if (cursor < text.length) {
    output.push({ text: text.slice(cursor), highlight: false })
  }
  return output
}

function insightTypeLabel(value: string): string {
  if (value === "difference") return "Difference"
  if (value === "similarity") return "Similarity"
  return value
}

function buildEvidencePillLabel(ref: { year: number; paragraph_idx: number }): string {
  return `${ref.year} para ${ref.paragraph_idx + 1}`
}

export default function InsightLensPanel({
  modelALabel,
  modelBLabel,
  modelAOutput,
  modelBOutput,
  modelADebug = null,
  modelBDebug = null,
  modelADebugPath = null,
  modelBDebugPath = null,
}: InsightLensPanelProps) {
  const [activeModel, setActiveModel] = useState<"A" | "B">("A")
  const [isExpanded, setIsExpanded] = useState(false)
  const resolvedActiveModel =
    activeModel === "A" && !modelAOutput && modelBOutput
      ? "B"
      : activeModel === "B" && !modelBOutput && modelAOutput
        ? "A"
        : activeModel
  const activeOutput = resolvedActiveModel === "A" ? modelAOutput : modelBOutput

  const [selectedInsightId, setSelectedInsightId] = useState<string | null>(null)
  const [hoveredInsightId, setHoveredInsightId] = useState<string | null>(null)
  const [showFullSection, setShowFullSection] = useState(false)
  const [showNeighbors, setShowNeighbors] = useState(false)
  const [paragraphBundle, setParagraphBundle] = useState<ParagraphBundle | null>(null)
  const [paragraphError, setParagraphError] = useState<string | null>(null)
  const [isLoadingParagraphs, setIsLoadingParagraphs] = useState(false)

  const prevRefs = useRef<Map<number, HTMLDivElement | null>>(new Map())
  const currRefs = useRef<Map<number, HTMLDivElement | null>>(new Map())

  const insightCards = useMemo(() => {
    if (!activeOutput) return []
    const order = new Map<string, number>()
    activeOutput.ui_contract.recommended_insight_order.forEach((id, idx) => {
      order.set(id, idx)
    })
    return [...activeOutput.insight_cards].sort((left, right) => {
      const leftOrder = order.get(left.id)
      const rightOrder = order.get(right.id)
      if (leftOrder !== undefined && rightOrder !== undefined) return leftOrder - rightOrder
      if (leftOrder !== undefined) return -1
      if (rightOrder !== undefined) return 1
      return right.salience - left.salience
    })
  }, [activeOutput])

  const clusteredInsightCards = useMemo(() => {
    if (!activeOutput) return [] as Array<{ id: string; label: string; cards: LabOutlineInsightCard[] }>
    const byId = new Map<string, LabOutlineInsightCard>()
    for (const card of insightCards) {
      byId.set(card.id, card)
    }
    const consumed = new Set<string>()
    const groups: Array<{ id: string; label: string; cards: LabOutlineInsightCard[] }> = []
    for (const cluster of activeOutput.ui_contract.suggested_clusters) {
      const cards: LabOutlineInsightCard[] = []
      for (const insightId of cluster.insight_ids) {
        const card = byId.get(insightId)
        if (!card) continue
        cards.push(card)
        consumed.add(card.id)
      }
      if (cards.length > 0) {
        groups.push({ id: cluster.cluster_id, label: cluster.label, cards })
      }
    }
    const ungrouped = insightCards.filter((card) => !consumed.has(card.id))
    if (ungrouped.length > 0) {
      groups.push({ id: "cluster_ungrouped", label: "Other insights", cards: ungrouped })
    }
    if (groups.length === 0) {
      groups.push({ id: "cluster_all", label: "Insights", cards: insightCards })
    }
    return groups
  }, [activeOutput, insightCards])

  // Render-time state adjustment: reset derived state when activeOutput changes
  // (avoids synchronous setState inside useEffect per react-hooks/set-state-in-effect)
  const [prevActiveOutput, setPrevActiveOutput] = useState(activeOutput)
  if (activeOutput !== prevActiveOutput) {
    setPrevActiveOutput(activeOutput)
    if (!activeOutput) {
      setSelectedInsightId(null)
    } else {
      const defaultId = activeOutput.ui_contract.default_selected_insight_id
      const hasDefault = insightCards.some((card) => card.id === defaultId)
      setSelectedInsightId(hasDefault ? defaultId : (insightCards[0]?.id ?? null))
    }
    setHoveredInsightId(null)
    setShowFullSection(false)
    setShowNeighbors(false)
    const inputFile = activeOutput?.provenance.input_file
    if (!activeOutput || typeof inputFile !== "string" || !inputFile) {
      setParagraphBundle(null)
      setParagraphError(null)
      setIsLoadingParagraphs(false)
    } else {
      setIsLoadingParagraphs(true)
      setParagraphError(null)
    }
  }

  const resolvedInputFile = (() => {
    const f = activeOutput?.provenance.input_file
    return activeOutput && typeof f === "string" && f ? f : null
  })()

  useEffect(() => {
    if (!resolvedInputFile) return

    let cancelled = false
    loadParagraphBundle(resolvedInputFile)
      .then((bundle) => {
        if (cancelled) return
        setParagraphBundle(bundle)
      })
      .catch((error) => {
        if (cancelled) return
        const message = error instanceof Error ? error.message : "Failed to load full section text."
        setParagraphBundle(null)
        setParagraphError(message)
      })
      .finally(() => {
        if (cancelled) return
        setIsLoadingParagraphs(false)
      })

    return () => {
      cancelled = true
    }
  }, [resolvedInputFile])

  const evidenceById = useMemo(() => {
    const map = new Map<string, LabOutlineInsightEvidenceMapEntry>()
    if (!activeOutput) return map
    for (const row of activeOutput.evidence_map) {
      map.set(row.evidence_id, row)
    }
    return map
  }, [activeOutput])

  const insightById = useMemo(() => {
    const map = new Map<string, LabOutlineInsightCard>()
    for (const card of insightCards) {
      map.set(card.id, card)
    }
    return map
  }, [insightCards])

  const activeInsight = useMemo(() => {
    const id = hoveredInsightId ?? selectedInsightId
    if (!id) return null
    return insightById.get(id) ?? null
  }, [hoveredInsightId, selectedInsightId, insightById])

  const activeEvidenceIndex = useMemo(() => {
    if (!activeOutput || !activeInsight) {
      return { prev: new Set<number>(), curr: new Set<number>() }
    }
    const output: YearEvidenceIndex = { prev: new Set<number>(), curr: new Set<number>() }
    for (const ref of activeInsight.evidence_refs_prev) {
      addEvidenceRef(output, activeOutput.year_from, activeOutput.year_to, ref.year, ref.paragraph_idx)
    }
    for (const ref of activeInsight.evidence_refs_curr) {
      addEvidenceRef(output, activeOutput.year_from, activeOutput.year_to, ref.year, ref.paragraph_idx)
    }
    for (const evidenceId of activeInsight.evidence_ref_ids) {
      const row = evidenceById.get(evidenceId)
      if (!row) continue
      addEvidenceRef(output, activeOutput.year_from, activeOutput.year_to, row.year, row.paragraph_idx)
    }
    return output
  }, [activeInsight, activeOutput, evidenceById])

  const normalizedEvidenceIndex = useMemo(() => {
    const out: YearEvidenceIndex = {
      prev: new Set(activeEvidenceIndex.prev),
      curr: new Set(activeEvidenceIndex.curr),
    }
    if (!showNeighbors) return out

    const addNeighbors = (bucket: Set<number>) => {
      const base = [...bucket]
      for (const idx of base) {
        if (idx > 0) bucket.add(idx - 1)
        bucket.add(idx + 1)
      }
    }
    addNeighbors(out.prev)
    addNeighbors(out.curr)
    return out
  }, [activeEvidenceIndex, showNeighbors])

  const snippetsByParagraph = useMemo(() => {
    const prev = new Map<number, string[]>()
    const curr = new Map<number, string[]>()
    if (!activeOutput || !activeInsight) return { prev, curr }
    for (const evidenceId of activeInsight.evidence_ref_ids) {
      const row = evidenceById.get(evidenceId)
      if (!row) continue
      const targetMap = row.year === activeOutput.year_from ? prev : row.year === activeOutput.year_to ? curr : null
      if (!targetMap) continue
      const existing = targetMap.get(row.paragraph_idx) ?? []
      existing.push(row.snippet)
      targetMap.set(row.paragraph_idx, existing)
    }
    return { prev, curr }
  }, [activeInsight, activeOutput, evidenceById])

  const scrollToEvidence = (year: number, paragraphIdx: number) => {
    if (!activeOutput) return
    const map = year === activeOutput.year_from ? prevRefs.current : currRefs.current
    const node = map.get(paragraphIdx)
    if (node) {
      node.scrollIntoView({ behavior: "smooth", block: "center" })
    }
  }

  const jumpToInsight = (insight: LabOutlineInsightCard) => {
    setSelectedInsightId(insight.id)
    const firstPrev = insight.evidence_refs_prev[0]?.paragraph_idx
    const firstCurr = insight.evidence_refs_curr[0]?.paragraph_idx
    if (typeof firstPrev === "number" && activeOutput) {
      scrollToEvidence(activeOutput.year_from, firstPrev)
    }
    if (typeof firstCurr === "number" && activeOutput) {
      scrollToEvidence(activeOutput.year_to, firstCurr)
    }
  }

  const renderYearPane = (
    label: string,
    year: number,
    paragraphs: string[] | null,
    indices: Set<number>,
    snippetMap: Map<number, string[]>,
    refStore: MutableRefObject<Map<number, HTMLDivElement | null>>
  ) => {
    if (!paragraphs) {
      return (
        <div className="rounded-md border border-white/10 bg-slate-950/35 p-3 text-xs text-slate-300">
          Full section paragraphs unavailable for {label}.
        </div>
      )
    }

    const visible = showFullSection
      ? paragraphs.map((_, idx) => idx)
      : [...indices].filter((idx) => idx >= 0 && idx < paragraphs.length).sort((a, b) => a - b)

    if (!visible.length) {
      return (
        <div className="rounded-md border border-white/10 bg-slate-950/35 p-3 text-xs text-slate-300">
          Select an insight card to focus this pane.
        </div>
      )
    }

    return (
      <div className="space-y-2">
        {visible.map((idx) => {
          const paragraph = paragraphs[idx]
          const snippets = snippetMap.get(idx) ?? []
          const segments = buildSegments(paragraph, snippets)
          const isPrimaryEvidence = year === activeOutput?.year_from
            ? activeEvidenceIndex.prev.has(idx)
            : activeEvidenceIndex.curr.has(idx)
          return (
            <div
              key={`${label}-${idx}`}
              ref={(node) => {
                refStore.current.set(idx, node)
              }}
              className={`rounded-md border p-3 text-sm leading-relaxed ${
                isPrimaryEvidence
                  ? "border-emerald-300/50 bg-emerald-400/10"
                  : "border-white/10 bg-slate-950/35"
              }`}
            >
              <div className="mb-1 text-[11px] text-slate-400">
                {year} para {idx + 1}
              </div>
              <p className="text-slate-100">
                {segments.map((segment, segmentIdx) =>
                  segment.highlight ? (
                    <mark key={segmentIdx} className="rounded-sm bg-amber-200/20 px-0.5 text-amber-100">
                      {segment.text}
                    </mark>
                  ) : (
                    <span key={segmentIdx}>{segment.text}</span>
                  )
                )}
              </p>
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <section id="lab-insight-lens" className="space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-white/8 bg-slate-950/14 px-3 py-3">
        <div className="max-w-3xl">
          <p className="text-sm font-medium text-slate-100">Paragraph-level drilldown stays optional.</p>
          <p className="mt-1 text-[11px] text-slate-400">
            Keep the filing answer and structure check primary unless you need clustered insight cards
            and direct paragraph drilldown.
          </p>
        </div>
        {modelAOutput || modelBOutput ? (
          <button
            type="button"
            onClick={() => setIsExpanded((previous) => !previous)}
            className="rounded-md border border-white/20 bg-slate-900/55 px-3 py-1.5 text-xs text-slate-100 transition hover:border-white/35"
          >
            {isExpanded ? "Hide paragraph drilldown" : "Open paragraph drilldown"}
          </button>
        ) : null}
      </div>

      {!modelAOutput && !modelBOutput ? (
        <div className="rounded-md border border-amber-400/20 bg-amber-400/7 p-3 text-xs text-slate-200">
          Optional insight sidecars are not published for these compare lanes. The shipped compare flow
          stays with the runtime and structured outline artifacts instead.
        </div>
      ) : null}
      {!modelAOutput ? renderMissingPanel(modelALabel, modelADebug, modelADebugPath) : null}
      {!modelBOutput ? renderMissingPanel(modelBLabel, modelBDebug, modelBDebugPath) : null}

      {activeOutput && !isExpanded ? (
        <div className="rounded-md border border-white/8 bg-slate-950/12 p-3 text-sm text-slate-100">
          <div className="font-medium">{resolvedActiveModel === "A" ? modelALabel : modelBLabel}</div>
          <div className="mt-1 text-xs text-slate-300">{activeOutput.executive_digest.summary_text}</div>
          <div className="mt-2 text-[11px] text-slate-400">
            Open this panel only if you want insight cards and direct paragraph drilldown.
          </div>
        </div>
      ) : null}

      {activeOutput && isExpanded ? (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-white/8 bg-slate-950/12 p-3 text-sm text-slate-100">
            <div>
              <div className="font-medium">{resolvedActiveModel === "A" ? modelALabel : modelBLabel}</div>
              <div className="mt-1 text-xs text-slate-300">
                {activeOutput.executive_digest.summary_text}
              </div>
              <div className="mt-2 text-[11px] text-slate-400">
                Audience: {activeOutput.executive_digest.audience} | Estimated read: {activeOutput.executive_digest.reading_time_sec_estimate}s
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setActiveModel("A")}
                className={`rounded-md border px-2 py-1 text-xs transition ${
                  resolvedActiveModel === "A"
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
                  resolvedActiveModel === "B"
                    ? "border-emerald-200/70 bg-emerald-400/25 text-emerald-50"
                    : "border-white/20 bg-slate-900/50 text-slate-200"
                }`}
              >
                Model B
              </button>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setShowFullSection((prev) => !prev)}
              className="rounded-md border border-white/20 bg-slate-900/50 px-2 py-1 text-xs text-slate-200"
            >
              {showFullSection ? "Show evidence only" : "Show full section"}
            </button>
            <button
              type="button"
              onClick={() => setShowNeighbors((prev) => !prev)}
              className="rounded-md border border-white/20 bg-slate-900/50 px-2 py-1 text-xs text-slate-200"
            >
              {showNeighbors ? "Hide neighbors" : "Show neighbors (+/-1)"}
            </button>
            {isLoadingParagraphs ? <span className="text-xs text-slate-300">Loading full section text...</span> : null}
            {paragraphError ? <span className="text-xs text-amber-200">{paragraphError}</span> : null}
          </div>

          <div className="grid gap-4 lg:grid-cols-[minmax(260px,340px)_1fr]">
            <div className="space-y-2 rounded-md border border-white/10 bg-slate-950/35 p-3">
              <div className="flex items-center justify-between gap-2 text-xs uppercase tracking-wide text-slate-300">
                <span>Insights</span>
                <span>{activeOutput.insight_coverage.difference_count} diff / {activeOutput.insight_coverage.similarity_count} sim</span>
              </div>
              {clusteredInsightCards.map((cluster) => (
                <div key={cluster.id} className="space-y-1">
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">{cluster.label}</div>
                  {cluster.cards.map((insight) => {
                    const isActive = insight.id === (hoveredInsightId ?? selectedInsightId)
                    return (
                      <button
                        key={insight.id}
                        type="button"
                        onClick={() => jumpToInsight(insight)}
                        onMouseEnter={() => setHoveredInsightId(insight.id)}
                        onMouseLeave={() => setHoveredInsightId(null)}
                        className={`w-full rounded-md border px-3 py-2 text-left text-xs transition ${
                          isActive
                            ? "border-sky-200/60 bg-sky-400/20 text-sky-100"
                            : "border-white/10 bg-slate-900/40 text-slate-200 hover:border-white/30"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-semibold">{insight.title}</span>
                          <span className="text-[10px] uppercase tracking-wide text-slate-300">
                            {insightTypeLabel(insight.insight_type)} {insight.salience.toFixed(2)}
                          </span>
                        </div>
                        <div className="mt-1 text-[11px] text-slate-300">{insight.claim}</div>
                      </button>
                    )
                  })}
                </div>
              ))}
            </div>

            <div className="space-y-3">
              {activeInsight ? (
                <div className="rounded-md border border-white/10 bg-slate-950/35 p-3 text-xs text-slate-200">
                  <div className="font-semibold text-slate-100">{activeInsight.title}</div>
                  <p className="mt-1">{activeInsight.why_it_matters}</p>
                  <p className="mt-1 text-slate-300">Limit: {activeInsight.counterpoint_or_limit}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {[...activeInsight.evidence_refs_prev, ...activeInsight.evidence_refs_curr].map((ref, idx) => (
                      <button
                        key={`${activeInsight.id}-pill-${idx}`}
                        type="button"
                        onClick={() => scrollToEvidence(ref.year, ref.paragraph_idx)}
                        className="rounded-full border border-white/20 bg-white/5 px-2 py-0.5 text-[11px] text-slate-100"
                      >
                        {buildEvidencePillLabel(ref)}
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}

              <div className="grid gap-3 xl:grid-cols-2">
                <div className="space-y-2 rounded-md border border-white/10 bg-slate-950/30 p-3">
                  <div className="text-xs uppercase tracking-wide text-slate-300">{formatFiscalYearLabel(activeOutput.year_from)} full risk section</div>
                  {renderYearPane(
                    "prev",
                    activeOutput.year_from,
                    paragraphBundle?.prev ?? null,
                    normalizedEvidenceIndex.prev,
                    snippetsByParagraph.prev,
                    prevRefs
                  )}
                </div>
                <div className="space-y-2 rounded-md border border-white/10 bg-slate-950/30 p-3">
                  <div className="text-xs uppercase tracking-wide text-slate-300">{formatFiscalYearLabel(activeOutput.year_to)} full risk section</div>
                  {renderYearPane(
                    "curr",
                    activeOutput.year_to,
                    paragraphBundle?.curr ?? null,
                    normalizedEvidenceIndex.curr,
                    snippetsByParagraph.curr,
                    currRefs
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  )
}
