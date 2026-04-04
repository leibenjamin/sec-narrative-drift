import { useMemo } from "react"
import { compactText } from "../lib/compactText"
import { formatFiscalYearLabel } from "../lib/fiscalYear"
import type {
  LabOutlineCompareOutput,
  LabOutlineCompareV2Output,
  LabOutlineEvidence,
  LabOutlineEvidenceRef,
  LabOutlineInvestorRelevanceRow,
  LabOutlineLimitRow,
  LabOutlineMaterialChange,
} from "../lib/labTypes"

type AnalysisMode = "executive" | "deep"

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
  analysisMode?: AnalysisMode
}

type NarrativeCampaignColumn = {
  id: "A" | "B"
  label: string
  runtime: LabOutlineCompareOutput | null
  structured: LabOutlineCompareV2Output | null
  accentClass: string
  accentTextClass: string
  accentSurfaceClass: string
}

type AvailableNarrativeCampaignColumn = NarrativeCampaignColumn & {
  runtime: LabOutlineCompareOutput
}

type EvidenceSelection = {
  ref: LabOutlineEvidenceRef | null
  evidence: LabOutlineEvidence | null
  note: string | null
}

type SharedLeadMatch = {
  leftColumn: AvailableNarrativeCampaignColumn
  rightColumn: AvailableNarrativeCampaignColumn
  leftChange: LabOutlineMaterialChange
  rightChange: LabOutlineMaterialChange
  overlapRatio: number
  sharedTokens: string[]
}

type CompareReadsSummary = {
  headline: string
  divergenceLabel: "substantive" | "stylistic" | "single"
  divergenceText: string
}

type LeadSummary = {
  primaryColumn: AvailableNarrativeCampaignColumn
  primaryChange: LabOutlineMaterialChange
  secondaryColumn: AvailableNarrativeCampaignColumn | null
  secondaryChange: LabOutlineMaterialChange | null
  whatChanged: string
  secondaryNote: string | null
  whyItMatters: string
  caution: string
  prevEvidence: EvidenceSelection
  currEvidence: EvidenceSelection
  isLowDrift: boolean
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

const TITLE_STOP_WORDS = new Set([
  "and",
  "are",
  "for",
  "from",
  "into",
  "more",
  "most",
  "now",
  "risk",
  "risks",
  "that",
  "than",
  "the",
  "their",
  "this",
  "toward",
  "with",
])

function formatClassBadge(changeClass: string) {
  const info = CHANGE_CLASS_DISPLAY[changeClass] ?? {
    label: changeClass,
    color: "text-slate-300 bg-slate-400/10 border-slate-400/20",
  }
  return (
    <span className={`inline-block rounded-full border px-2 py-0.5 text-[11px] font-medium ${info.color}`}>
      {info.label}
    </span>
  )
}

function formatCampaignSurfaceLabel(column: Pick<NarrativeCampaignColumn, "id" | "label">): string {
  const trimmed = column.label.trim()
  if (!trimmed) return `Campaign ${column.id}`
  const simplified = trimmed.split(" (")[0]?.trim()
  return simplified && simplified.length > 0 ? simplified : trimmed
}

function formatEvidenceRef(ref: LabOutlineEvidenceRef): string {
  return `${ref.year} para ${ref.paragraph_idx + 1}`
}

function buildEvidenceRefKey(ref: LabOutlineEvidenceRef): string {
  return `${ref.year}:${ref.paragraph_idx}`
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

function buildColumnEvidenceLookup(column: NarrativeCampaignColumn): Map<string, LabOutlineEvidence> {
  const bank = column.structured?.evidence_bank ?? column.runtime?.evidence_bank ?? []
  return buildEvidenceLookup(bank)
}

function buildDriftScore(output: LabOutlineCompareOutput): { score: number; label: string } {
  const counts = buildAlignmentDistribution(output)
  const total = output.node_alignment.length
  if (total === 0) return { score: 0, label: "No data" }
  const dynamic =
    (counts.get("added") ?? 0) +
    (counts.get("removed") ?? 0) +
    (counts.get("intensified") ?? 0) +
    (counts.get("softened") ?? 0) +
    (counts.get("split") ?? 0) +
    (counts.get("merged") ?? 0)
  const ratio = dynamic / total
  if (ratio >= 0.6) return { score: ratio, label: "High drift" }
  if (ratio >= 0.3) return { score: ratio, label: "Moderate drift" }
  return { score: ratio, label: "Low drift" }
}

function sortMaterialChanges(output: LabOutlineCompareOutput | null): LabOutlineMaterialChange[] {
  if (!output) return []
  return [...output.material_changes].sort((left, right) => right.salience - left.salience)
}

function tokenizeTitle(title: string): string[] {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter((token) => token.length >= 3 && !TITLE_STOP_WORDS.has(token))
}

function compareChangeTitles(left: LabOutlineMaterialChange, right: LabOutlineMaterialChange) {
  const leftTokens = new Set(tokenizeTitle(left.title))
  const rightTokens = new Set(tokenizeTitle(right.title))
  const sharedTokens: string[] = []

  for (const token of leftTokens) {
    if (rightTokens.has(token)) {
      sharedTokens.push(token)
    }
  }

  const unionSize = new Set([...leftTokens, ...rightTokens]).size
  const overlapRatio = unionSize > 0 ? sharedTokens.length / unionSize : 0
  const sameClass = left.change_class === right.change_class
  const isShared = overlapRatio >= 0.3 || (sameClass && overlapRatio >= 0.18)

  return {
    sharedTokens,
    overlapRatio,
    isShared,
  }
}

function countSharedEvidenceRefs(
  leftRefs: LabOutlineEvidenceRef[],
  rightRefs: LabOutlineEvidenceRef[]
): number {
  const rightKeys = new Set(rightRefs.map((ref) => buildEvidenceRefKey(ref)))
  let count = 0
  for (const ref of leftRefs) {
    if (rightKeys.has(buildEvidenceRefKey(ref))) {
      count += 1
    }
  }
  return count
}

function selectBestEvidenceBoundRow<T extends { evidence_refs: LabOutlineEvidenceRef[] }>(
  rows: T[],
  targetRefs: LabOutlineEvidenceRef[]
): T | null {
  if (rows.length === 0) return null
  if (targetRefs.length === 0) return rows[0]

  let bestRow: T | null = null
  let bestScore = -1

  for (const row of rows) {
    const score = countSharedEvidenceRefs(row.evidence_refs, targetRefs)
    if (score > bestScore) {
      bestScore = score
      bestRow = row
    }
  }

  return bestScore > 0 ? bestRow : rows[0]
}

function findEvidenceForRef(
  ref: LabOutlineEvidenceRef,
  evidenceLookup: Map<string, LabOutlineEvidence>
): LabOutlineEvidence | null {
  return evidenceLookup.get(`${ref.year}:${ref.paragraph_idx}`) ?? null
}

function renderEvidenceCard(props: {
  heading: string
  year: number
  ref: LabOutlineEvidenceRef | null
  evidence: LabOutlineEvidence | null
  note?: string | null
}) {
  const { heading, year, ref, evidence, note = null } = props
  return (
    <div className="rounded-[1.1rem] border border-white/10 bg-slate-950/40 p-3.5 sm:p-4">
      <div className="text-[11px] uppercase tracking-wide text-slate-400">{heading}</div>
      {ref && evidence ? (
        <>
          <div className="mt-1.5 text-[11px] text-slate-500">{formatEvidenceRef(ref)}</div>
          <p className="mt-2.5 text-sm leading-6 text-slate-100 text-clamp-5">"{evidence.snippet}"</p>
          <p className="mt-2.5 text-[11px] leading-5 text-slate-400">{evidence.why}</p>
          {note ? <p className="mt-2 text-[11px] leading-5 text-slate-500">{note}</p> : null}
        </>
      ) : ref ? (
        <>
          <div className="mt-1.5 text-[11px] text-slate-500">{formatEvidenceRef(ref)}</div>
          <p className="mt-2.5 text-sm text-slate-400">
            {note ?? "The surfaced reference did not resolve to a stored evidence snippet."}
          </p>
        </>
      ) : (
        <p className="mt-2.5 text-sm text-slate-400">
          {note ?? `No ${year}-year evidence reference was surfaced for this lead change.`}
        </p>
      )}
    </div>
  )
}

function filterAvailableColumns(columns: NarrativeCampaignColumn[]): AvailableNarrativeCampaignColumn[] {
  return columns.filter((column): column is AvailableNarrativeCampaignColumn => Boolean(column.runtime))
}

function buildSharedLeadMatch(columns: NarrativeCampaignColumn[]): SharedLeadMatch | null {
  const available = filterAvailableColumns(columns).slice(0, 2)
  if (available.length < 2) {
    return null
  }

  const leftChanges = sortMaterialChanges(available[0].runtime).slice(0, 3)
  const rightChanges = sortMaterialChanges(available[1].runtime).slice(0, 3)
  let bestMatch: SharedLeadMatch | null = null
  let bestMaxSalience = -1
  let bestTotalSalience = -1

  for (const leftChange of leftChanges) {
    for (const rightChange of rightChanges) {
      const overlap = compareChangeTitles(leftChange, rightChange)
      if (!overlap.isShared) {
        continue
      }

      const maxSalience = Math.max(leftChange.salience, rightChange.salience)
      const totalSalience = leftChange.salience + rightChange.salience
      if (
        maxSalience > bestMaxSalience ||
        (maxSalience === bestMaxSalience && totalSalience > bestTotalSalience)
      ) {
        bestMaxSalience = maxSalience
        bestTotalSalience = totalSalience
        bestMatch = {
          leftColumn: available[0],
          rightColumn: available[1],
          leftChange,
          rightChange,
          overlapRatio: overlap.overlapRatio,
          sharedTokens: overlap.sharedTokens,
        }
      }
    }
  }

  return bestMatch
}

function selectLeadEvidenceForYear(
  year: number,
  primaryColumn: NarrativeCampaignColumn,
  primaryChange: LabOutlineMaterialChange,
  secondaryColumn: NarrativeCampaignColumn | null,
  secondaryChange: LabOutlineMaterialChange | null
): EvidenceSelection {
  const candidates = [
    {
      column: primaryColumn,
      change: primaryChange,
      note: null,
    },
    ...(secondaryColumn && secondaryChange
      ? [
          {
            column: secondaryColumn,
            change: secondaryChange,
            note: `Using ${secondaryColumn.label || `Campaign ${secondaryColumn.id}`} evidence for this year because it is the clearest paired excerpt available.`,
          },
        ]
      : []),
  ]

  let unresolvedSelection: EvidenceSelection | null = null

  for (const candidate of candidates) {
    const ref = candidate.change.evidence_refs.find((item) => item.year === year) ?? null
    if (!ref) {
      continue
    }

    const evidence = findEvidenceForRef(ref, buildColumnEvidenceLookup(candidate.column))
    if (evidence) {
      return {
        ref,
        evidence,
        note: candidate.note,
      }
    }

    if (!unresolvedSelection) {
      unresolvedSelection = {
        ref,
        evidence: null,
        note: "The surfaced reference did not resolve to a stored evidence snippet.",
      }
    }
  }

  return (
    unresolvedSelection ?? {
      ref: null,
      evidence: null,
      note: `No ${year}-year evidence reference was surfaced for this lead change.`,
    }
  )
}

function selectWhyItMattersRow(
  column: NarrativeCampaignColumn,
  change: LabOutlineMaterialChange
): LabOutlineInvestorRelevanceRow | null {
  const rows = column.structured?.investor_relevance ?? []
  return selectBestEvidenceBoundRow(rows, change.evidence_refs)
}

function selectLimitationRow(
  column: NarrativeCampaignColumn,
  change: LabOutlineMaterialChange
): LabOutlineLimitRow | null {
  const rows = column.structured?.uncertainty_and_limits ?? []
  return selectBestEvidenceBoundRow(rows, change.evidence_refs)
}

function buildLeadSummary(
  columns: NarrativeCampaignColumn[],
  yearFrom: number,
  yearTo: number
): LeadSummary | null {
  const available = filterAvailableColumns(columns).slice(0, 2)
  if (available.length === 0) {
    return null
  }

  const sharedMatch = buildSharedLeadMatch(available)
  const isLowDrift = available.every((column) => buildDriftScore(column.runtime).label === "Low drift")

  let primaryColumn: AvailableNarrativeCampaignColumn
  let primaryChange: LabOutlineMaterialChange | null
  let secondaryColumn: AvailableNarrativeCampaignColumn | null = null
  let secondaryChange: LabOutlineMaterialChange | null = null

  if (sharedMatch) {
    const leftIsPrimary = sharedMatch.leftChange.salience >= sharedMatch.rightChange.salience
    primaryColumn = leftIsPrimary ? sharedMatch.leftColumn : sharedMatch.rightColumn
    primaryChange = leftIsPrimary ? sharedMatch.leftChange : sharedMatch.rightChange
    secondaryColumn = leftIsPrimary ? sharedMatch.rightColumn : sharedMatch.leftColumn
    secondaryChange = leftIsPrimary ? sharedMatch.rightChange : sharedMatch.leftChange
  } else {
    primaryColumn = available[0]
    primaryChange = sortMaterialChanges(primaryColumn.runtime)[0] ?? null

    if (available[1]) {
      secondaryColumn = available[1]
      secondaryChange = sortMaterialChanges(secondaryColumn.runtime)[0] ?? null
    }
  }

  if (!primaryChange) {
    return null
  }

  const primaryLabel = formatCampaignSurfaceLabel(primaryColumn)
  const secondaryLabel = secondaryColumn ? formatCampaignSurfaceLabel(secondaryColumn) : ""

  let whatChanged: string
  let secondaryNote: string | null = null

  if (sharedMatch && secondaryChange && secondaryColumn) {
    whatChanged = isLowDrift
      ? `Both visible reads still describe a low-drift filing. The main movement is selective sharpening around ${primaryChange.title}.`
      : `Both visible reads converge on the same filing shift: ${primaryChange.title}.`
    secondaryNote = `${secondaryLabel} frames the same shift as "${secondaryChange.title}".`
  } else if (secondaryChange && secondaryColumn) {
    whatChanged = isLowDrift
      ? `This filing still reads as low drift. The clearest surfaced movement is ${primaryChange.title}.`
      : `${primaryLabel} leads with: ${primaryChange.title}.`
    secondaryNote = `${secondaryLabel} instead leads with "${secondaryChange.title}".`
  } else {
    whatChanged = isLowDrift
      ? `This filing still reads as low drift. The clearest surfaced movement is ${primaryChange.title}.`
      : `The clearest surfaced filing shift is ${primaryChange.title}.`
  }

  const whyItMattersRow =
    selectWhyItMattersRow(primaryColumn, primaryChange) ??
    (secondaryColumn && secondaryChange ? selectWhyItMattersRow(secondaryColumn, secondaryChange) : null)
  const limitationRow =
    selectLimitationRow(primaryColumn, primaryChange) ??
    (secondaryColumn && secondaryChange ? selectLimitationRow(secondaryColumn, secondaryChange) : null)

  const whyItMatters =
    whyItMattersRow?.why_it_matters ??
    "No structured why-it-matters row was surfaced for this lead change."
  const baseCaution = limitationRow?.limitation ?? primaryChange.caveat
  const caution = isLowDrift
    ? `Low drift is part of the signal here. Read this as selective sharpening rather than a wholesale rewrite. ${baseCaution}`
    : baseCaution

  return {
    primaryColumn,
    primaryChange,
    secondaryColumn,
    secondaryChange,
    whatChanged,
    secondaryNote,
    whyItMatters,
    caution,
    prevEvidence: selectLeadEvidenceForYear(
      yearFrom,
      primaryColumn,
      primaryChange,
      secondaryColumn,
      secondaryChange
    ),
    currEvidence: selectLeadEvidenceForYear(
      yearTo,
      primaryColumn,
      primaryChange,
      secondaryColumn,
      secondaryChange
    ),
    isLowDrift,
  }
}

function buildCompareReadsSummary(columns: NarrativeCampaignColumn[]): CompareReadsSummary {
  const available = filterAvailableColumns(columns).slice(0, 2)
  if (available.length < 2) {
    return {
      headline: "One compare read is active.",
      divergenceLabel: "single",
      divergenceText: "Use the audit gateway below if you need the full ranked compare.",
    }
  }

  const sharedMatch = buildSharedLeadMatch(available)
  if (sharedMatch) {
    const leftLabel = formatCampaignSurfaceLabel(sharedMatch.leftColumn)
    const rightLabel = formatCampaignSurfaceLabel(sharedMatch.rightColumn)
    return {
      headline: "Same core shift, different emphasis.",
      divergenceLabel: "stylistic",
      divergenceText: `${leftLabel}: "${compactText(sharedMatch.leftChange.title, 54)}". ${rightLabel}: "${compactText(sharedMatch.rightChange.title, 54)}".`,
    }
  }

  const leftLead = sortMaterialChanges(available[0].runtime)[0]
  const rightLead = sortMaterialChanges(available[1].runtime)[0]
  if (!leftLead || !rightLead) {
    return {
      headline: "Lead-change comparison is unavailable.",
      divergenceLabel: "single",
      divergenceText: "At least one campaign is missing ranked material-change rows.",
    }
  }

  const leftLabel = formatCampaignSurfaceLabel(available[0])
  const rightLabel = formatCampaignSurfaceLabel(available[1])
  return {
    headline: "Different lead reads.",
    divergenceLabel: "substantive",
    divergenceText: `${leftLabel}: "${compactText(leftLead.title, 54)}". ${rightLabel}: "${compactText(rightLead.title, 54)}".`,
  }
}

function renderCompareReadsBadge(divergenceLabel: CompareReadsSummary["divergenceLabel"]) {
  const className =
    divergenceLabel === "substantive"
      ? "border-amber-300/35 bg-amber-400/12 text-amber-100"
      : divergenceLabel === "stylistic"
        ? "border-sky-300/35 bg-sky-400/12 text-sky-100"
        : "border-white/15 bg-white/5 text-slate-200"

  return (
    <span className={`rounded-full border px-2.5 py-1 text-[11px] font-medium ${className}`}>
      {divergenceLabel === "single" ? "Single campaign" : `${divergenceLabel} divergence`}
    </span>
  )
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
  analysisMode = "deep",
}: RiskNarrativeSummaryProps) {
  const columns = useMemo(() => {
    const configured: NarrativeCampaignColumn[] = [
      {
        id: "A",
        label: modelALabel,
        runtime: modelARuntime,
        structured: modelAStructured,
        accentClass: "border-sky-300/40 bg-sky-400/12 text-sky-100",
        accentTextClass: "text-sky-100",
        accentSurfaceClass: "border-sky-300/20 bg-sky-400/8 text-sky-50",
      },
      {
        id: "B",
        label: modelBLabel,
        runtime: modelBRuntime,
        structured: modelBStructured,
        accentClass: "border-emerald-300/35 bg-emerald-400/12 text-emerald-100",
        accentTextClass: "text-emerald-100",
        accentSurfaceClass: "border-emerald-300/20 bg-emerald-400/8 text-emerald-50",
      },
    ]

    return configured.filter((column) => {
      if (column.label.trim().length > 0) return true
      return Boolean(column.runtime || column.structured)
    })
  }, [modelALabel, modelARuntime, modelAStructured, modelBLabel, modelBRuntime, modelBStructured])

  const hasAnyRuntime = columns.some((column) => column.runtime)
  const leadSummary = useMemo(() => buildLeadSummary(columns, yearFrom, yearTo), [columns, yearFrom, yearTo])
  const compareSummary = useMemo(() => buildCompareReadsSummary(columns), [columns])
  const leadSupportItems = useMemo(() => {
    if (!leadSummary) return []
    return [
      {
        label: leadSummary.secondaryNote ? "Compare read" : "Active lane",
        value: compactText(
          leadSummary.secondaryNote ??
            `Lead surfaced by ${formatCampaignSurfaceLabel(leadSummary.primaryColumn)}.`,
          92
        ),
        tone: "neutral" as const,
      },
      {
        label: "Boundary",
        value: compactText(leadSummary.caution, 92),
        tone: "boundary" as const,
      },
    ]
  }, [leadSummary])
  const leadSupportParagraph = useMemo(() => {
    if (!leadSummary) return null
    return compactText(
      `${leadSummary.whatChanged} ${leadSummary.whyItMatters}`,
      leadSummary.isLowDrift ? 228 : 244
    )
  }, [leadSummary])

  if (!hasAnyRuntime) {
    return (
      <section className="rounded-xl border border-slate-600/30 bg-slate-900/40 p-5">
        <h3 className="text-base font-semibold text-slate-200">Risk narrative analysis</h3>
        <p className="mt-2 text-sm text-slate-400">
          Precomputed outline-compare data is not yet available for {ticker}. Deterministic methods below
          still provide quantitative drift signals.
        </p>
      </section>
    )
  }

  return (
    <section
      id="lab-risk-narrative"
      className="space-y-4 rounded-[1.4rem] border border-slate-500/25 bg-linear-to-b from-slate-900/72 via-slate-950/58 to-slate-950/35 p-4 shadow-[0_18px_48px_rgba(2,6,23,0.35)] sm:space-y-5 sm:p-5"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-3xl">
          <p className="text-[11px] uppercase tracking-[0.24em] text-sky-100">Filing answer</p>
          <h2 className="mt-1.5 text-xl font-semibold text-slate-100 sm:text-2xl">
            {ticker} filing answer, {formatFiscalYearLabel(yearFrom)} to {formatFiscalYearLabel(yearTo)}
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
            Claim first, proof directly below it, compare tucked lower. Use the lower layers only when the
            first read needs pressure.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-[11px] text-slate-200">
          <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
            Read mode: {analysisMode === "executive" ? "Quick read" : "Deep review"}
          </span>
          {leadSummary?.isLowDrift ? (
            <span className="rounded-full border border-sky-300/25 bg-sky-400/10 px-2.5 py-1 text-sky-100">
              Low-drift signal
            </span>
          ) : null}
        </div>
      </div>

      {leadSummary ? (
        <>
          <article className="rounded-[1.25rem] border border-white/10 bg-slate-950/44 p-4 shadow-[0_18px_40px_rgba(2,6,23,0.24)] sm:p-5">
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(18rem,0.9fr)] xl:items-start">
              <div className="flex flex-wrap items-center gap-2 xl:col-span-2">
                {formatClassBadge(leadSummary.primaryChange.change_class)}
                <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] text-slate-200">
                  {formatCampaignSurfaceLabel(leadSummary.primaryColumn)}
                </span>
              </div>

              <div className="xl:col-span-2">
                <div className="text-[10px] uppercase tracking-[0.24em] text-slate-300">Lead answer</div>
                <p className="mt-2.5 max-w-4xl text-[1.2rem] font-semibold leading-[1.2] text-slate-50 sm:text-[1.55rem] lg:text-[1.7rem]">
                  {compactText(leadSummary.primaryChange.title, leadSummary.isLowDrift ? 104 : 118)}
                </p>
                <p className="mt-3 max-w-4xl text-sm leading-6 text-slate-200">
                  {leadSupportParagraph}
                </p>
              </div>

              <div className="grid gap-2.5 sm:grid-cols-2 xl:col-span-2">
                {leadSupportItems.map((item) => (
                  <article
                    key={item.label}
                    className={
                      item.tone === "boundary"
                        ? "rounded-[1.05rem] border border-amber-300/20 bg-amber-400/8 p-3"
                        : "rounded-[1.05rem] border border-white/10 bg-slate-900/38 p-3"
                    }
                  >
                    <div
                      className={
                        item.tone === "boundary"
                          ? "text-[10px] uppercase tracking-[0.24em] text-amber-100"
                          : "text-[10px] uppercase tracking-[0.24em] text-slate-300"
                      }
                    >
                      {item.label}
                    </div>
                    <p className="mt-1.5 text-sm leading-5 text-slate-100">{item.value}</p>
                  </article>
                ))}
              </div>

              <div className="xl:col-span-2 border-t border-white/10 pt-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="text-[11px] uppercase tracking-[0.24em] text-slate-300">
                      Paired proof
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-300">
                      Check the two filing excerpts before opening the full compare.
                    </p>
                  </div>
                  <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">
                    Evidence stays adjacent
                  </div>
                </div>
                <div className="mt-4 grid gap-3 lg:grid-cols-2">
                  {renderEvidenceCard({
                    heading: `${formatFiscalYearLabel(yearFrom)} filing evidence`,
                    year: yearFrom,
                    ref: leadSummary.prevEvidence.ref,
                    evidence: leadSummary.prevEvidence.evidence,
                    note: leadSummary.prevEvidence.note,
                  })}
                  {renderEvidenceCard({
                    heading: `${formatFiscalYearLabel(yearTo)} filing evidence`,
                    year: yearTo,
                    ref: leadSummary.currEvidence.ref,
                    evidence: leadSummary.currEvidence.evidence,
                    note: leadSummary.currEvidence.note,
                  })}
                </div>
              </div>
            </div>
          </article>
        </>
      ) : null}

      <details className="rounded-[1.1rem] border border-sky-300/15 bg-slate-950/28 p-2.5 sm:p-3">
        <summary className="list-none cursor-pointer rounded-[0.95rem] border border-white/10 bg-slate-950/38 px-3 py-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="text-[10px] uppercase tracking-[0.24em] text-slate-400">Compare utility</div>
              <div className="mt-1 text-sm font-semibold text-slate-100">Compare reads</div>
              <p className="mt-1 text-[11px] leading-5 text-slate-400">
                Check whether the visible reads land on the same shift before opening the full audit.
              </p>
            </div>
            <div className="flex items-center gap-2">
              {renderCompareReadsBadge(compareSummary.divergenceLabel)}
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] font-medium text-slate-200">
                Open
              </span>
            </div>
          </div>
        </summary>
        <div className="mt-3 space-y-3">
          <div className="rounded-[0.95rem] border border-white/10 bg-slate-950/34 p-3">
            <p className="text-sm font-semibold text-slate-100">{compareSummary.headline}</p>
            <p className="mt-1 text-[11px] leading-5 text-slate-300">
              {compactText(compareSummary.divergenceText, 134)}
            </p>
          </div>

          <div className={`grid gap-2 ${columns.length > 1 ? "sm:grid-cols-2" : "grid-cols-1"}`}>
            {columns.slice(0, 2).map((column) => {
              const runtime = column.runtime
              const lead = runtime ? sortMaterialChanges(runtime)[0] : null
              const drift = runtime ? buildDriftScore(runtime).label : null
              return (
                <article
                  key={`compare-summary-${column.id}`}
                  className="rounded-[0.95rem] border border-white/10 bg-slate-950/26 p-3"
                >
                  <div
                    title={column.label || `Campaign ${column.id}`}
                    className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-medium ${column.accentClass}`}
                  >
                    {formatCampaignSurfaceLabel(column)}
                  </div>
                  {runtime ? (
                    <>
                      <p className="mt-2 text-[13px] font-semibold leading-5 text-slate-100">
                        {compactText(lead?.title ?? "No lead change surfaced.", 58)}
                      </p>
                      <p className="mt-1 text-[10px] text-slate-400">
                        {drift ? `${drift} | ` : ""}
                        {runtime.material_changes.length} ranked changes
                      </p>
                      <p className="mt-1.5 text-[11px] leading-5 text-slate-300 text-clamp-2">
                        {compactText(runtime.lens_divergence.summary, 86)}
                      </p>
                    </>
                  ) : (
                    <p className="mt-2 text-[11px] text-slate-400">
                      No runtime compare artifact loaded for this campaign.
                    </p>
                  )}
                </article>
              )
            })}
          </div>
          <p className="text-[10px] uppercase tracking-[0.18em] text-slate-500">
            Full ranked compare stays in the audit gateway below.
          </p>
        </div>
      </details>
    </section>
  )
}
