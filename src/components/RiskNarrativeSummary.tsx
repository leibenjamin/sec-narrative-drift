import { useMemo } from "react"
import { formatFiscalYearLabel } from "../lib/fiscalYear"
import type {
  LabOutlineCompareOutput,
  LabOutlineCompareV2Output,
  LabOutlineEvidence,
  LabOutlineEvidenceRef,
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

function buildLeadComparison(columns: NarrativeCampaignColumn[]): {
  headline: string
  divergenceLabel: "substantive" | "stylistic" | "single"
  divergenceText: string
} {
  const available = columns.filter((column) => sortMaterialChanges(column.runtime)[0])
  if (available.length < 2) {
    return {
      headline: "One compare campaign is active for this filing pair.",
      divergenceLabel: "single",
      divergenceText:
        "Use the deterministic agreement view below to cross-check the lead story until a second campaign is available.",
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

  const leftTokens = new Set(tokenizeTitle(leftLead.title))
  const rightTokens = new Set(tokenizeTitle(rightLead.title))
  const sharedTokens: string[] = []
  for (const token of leftTokens) {
    if (rightTokens.has(token)) {
      sharedTokens.push(token)
    }
  }
  const unionSize = new Set([...leftTokens, ...rightTokens]).size
  const overlapRatio = unionSize > 0 ? sharedTokens.length / unionSize : 0
  const sameClass = leftLead.change_class === rightLead.change_class

  if (overlapRatio >= 0.3 || (sameClass && overlapRatio >= 0.18)) {
    const sharedTheme = sharedTokens.slice(0, 4).join(", ") || "a similar operating-risk channel"
    return {
      headline: `Both campaigns lead with the same core shift: ${sharedTheme}.`,
      divergenceLabel: "stylistic",
      divergenceText: `${available[0].label} frames it as "${leftLead.title}", while ${available[1].label} frames it as "${rightLead.title}". The difference looks more like emphasis and wording than a different lead story.`,
    }
  }

  return {
    headline: `${available[0].label} leads with "${leftLead.title}", while ${available[1].label} leads with "${rightLead.title}".`,
    divergenceLabel: "substantive",
    divergenceText:
      "The two campaigns emphasize different lead mechanisms. Compare the paired evidence before treating them as interchangeable summaries.",
  }
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
}) {
  const { heading, year, ref, evidence } = props
  return (
    <div className="rounded-lg border border-white/10 bg-slate-950/45 p-3">
      <div className="text-[11px] uppercase tracking-wide text-slate-400">{heading}</div>
      {ref && evidence ? (
        <>
          <div className="mt-1 text-[11px] text-slate-500">{formatEvidenceRef(ref)}</div>
          <p className="mt-2 text-xs text-slate-100">"{evidence.snippet}"</p>
          <p className="mt-1 text-[11px] text-slate-400">{evidence.why}</p>
        </>
      ) : (
        <p className="mt-2 text-xs text-slate-400">
          No {year}-year evidence reference was surfaced for this change.
        </p>
      )}
    </div>
  )
}

function renderCampaignNarrativeColumn(props: {
  column: NarrativeCampaignColumn
  analysisMode: AnalysisMode
  yearFrom: number
  yearTo: number
}) {
  const { column, analysisMode, yearFrom, yearTo } = props
  const runtime = column.runtime
  const structured = column.structured
  if (!runtime) {
    return (
      <div className="rounded-2xl border border-amber-300/30 bg-amber-400/10 p-4 text-sm text-slate-200">
        <div className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-medium ${column.accentClass}`}>
          {column.label}
        </div>
        <p className="mt-3 text-sm text-amber-100">Compare artifact not available for this campaign.</p>
        <p className="mt-1 text-xs text-slate-300">
          Deterministic methods below still provide a complete filing-to-filing baseline.
        </p>
      </div>
    )
  }

  const drift = buildDriftScore(runtime)
  const alignmentCounts = buildAlignmentDistribution(runtime)
  const evidenceLookup = structured ? buildEvidenceLookup(structured.evidence_bank) : new Map<string, LabOutlineEvidence>()
  const topChanges = sortMaterialChanges(runtime).slice(0, analysisMode === "executive" ? 3 : 5)
  const investorItems = structured?.investor_relevance.slice(0, analysisMode === "executive" ? 2 : 3) ?? []
  const mechanismItems = structured?.change_mechanisms.slice(0, analysisMode === "executive" ? 2 : 3) ?? []
  const limitItems = structured?.uncertainty_and_limits.slice(0, 2) ?? []

  return (
    <div className="space-y-4 rounded-2xl border border-white/10 bg-slate-950/35 p-4 shadow-[0_18px_40px_rgba(2,6,23,0.25)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-medium ${column.accentClass}`}>
            {column.label}
          </div>
          <p className={`mt-2 text-sm font-semibold ${column.accentTextClass}`}>{drift.label}</p>
          <p className="text-xs text-slate-400">
            {runtime.material_changes.length} material changes | top salience {runtime.material_changes[0]?.salience.toFixed(2) ?? "n/a"}
          </p>
        </div>
        <div className="min-w-40 rounded-xl border border-white/10 bg-slate-900/55 p-3 text-right">
          <div className="text-[11px] uppercase tracking-wide text-slate-400">Structural drift</div>
          <div className="mt-1 text-2xl font-semibold text-slate-100">{(drift.score * 100).toFixed(0)}%</div>
          <div className="mt-1 text-[11px] text-slate-400">
            {(["added", "removed", "intensified", "softened", "split", "stable"] as const)
              .map((changeClass) => {
                const count = alignmentCounts.get(changeClass) ?? 0
                return count > 0 ? `${changeClass}:${count}` : null
              })
              .filter((value) => Boolean(value))
              .join(" | ")}
          </div>
        </div>
      </div>

      <div className={`rounded-xl border px-3 py-2 text-xs ${column.accentSurfaceClass}`}>
        <div className="font-medium text-slate-100">Lead narrative</div>
        <p className="mt-1 text-slate-200">{topChanges[0]?.title ?? "No lead change surfaced."}</p>
        <p className="mt-1 text-slate-400">{runtime.lens_divergence.summary}</p>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-300">Top material changes</h4>
          <span className="text-[11px] text-slate-500">{analysisMode === "executive" ? "Top 3" : "Top 5"}</span>
        </div>
        {topChanges.map((change, index) => {
          const prevRef = change.evidence_refs.find((ref) => ref.year === yearFrom) ?? null
          const currRef = change.evidence_refs.find((ref) => ref.year === yearTo) ?? null
          const prevEvidence = prevRef ? findEvidenceForRef(prevRef, evidenceLookup) : null
          const currEvidence = currRef ? findEvidenceForRef(currRef, evidenceLookup) : null
          return (
            <article key={`${column.id}:${change.id}`} className="rounded-xl border border-white/10 bg-slate-900/45 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-slate-500">Rank {index + 1}</div>
                  <h5 className="mt-1 text-sm font-semibold text-slate-100">{change.title}</h5>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {formatClassBadge(change.change_class)}
                  <span className="text-[11px] text-slate-400">salience {change.salience.toFixed(2)}</span>
                </div>
              </div>
              <p className="mt-2 text-xs text-slate-300">
                <span className="font-medium text-slate-200">Caveat:</span> {change.caveat}
              </p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {change.evidence_refs.map((ref, refIndex) => (
                  <span
                    key={`${column.id}:${change.id}:${refIndex}`}
                    className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] text-slate-200"
                  >
                    {formatEvidenceRef(ref)}
                  </span>
                ))}
              </div>
              {index < 2 ? (
                <div className="mt-3 grid gap-3 xl:grid-cols-2">
                  {renderEvidenceCard({
                    heading: `${formatFiscalYearLabel(yearFrom)} filing evidence`,
                    year: yearFrom,
                    ref: prevRef,
                    evidence: prevEvidence,
                  })}
                  {renderEvidenceCard({
                    heading: `${formatFiscalYearLabel(yearTo)} filing evidence`,
                    year: yearTo,
                    ref: currRef,
                    evidence: currEvidence,
                  })}
                </div>
              ) : null}
            </article>
          )
        })}
      </div>

      <div className="grid gap-3 xl:grid-cols-2">
        <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-300">Why it matters</h4>
          <div className="mt-3 space-y-3 text-xs text-slate-200">
            {investorItems.length > 0 ? (
              investorItems.map((item) => (
                <div key={`${column.id}:${item.id}`} className="rounded-lg border border-white/10 bg-slate-950/40 p-3">
                  <p>{item.why_it_matters}</p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {item.evidence_refs.map((ref, refIndex) => (
                      <span
                        key={`${column.id}:${item.id}:${refIndex}`}
                        className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] text-slate-400"
                      >
                        {formatEvidenceRef(ref)}
                      </span>
                    ))}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-slate-400">Structured investor-relevance rows were not provided for this campaign.</p>
            )}
          </div>
        </div>
        <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-300">Change mechanisms</h4>
          <div className="mt-3 space-y-3 text-xs text-slate-200">
            {mechanismItems.length > 0 ? (
              mechanismItems.map((item) => (
                <div key={`${column.id}:${item.id}`} className="rounded-lg border border-white/10 bg-slate-950/40 p-3">
                  <p className="font-medium text-slate-100">{item.mechanism}</p>
                  <p className="mt-1 text-slate-300">Channel: {item.transmission_channel}</p>
                  <p className="mt-1 text-slate-300">Effect: {item.business_effect}</p>
                  <p className="mt-1 text-slate-400">
                    {item.time_horizon === "near_term"
                      ? "Near term"
                      : item.time_horizon === "medium_term"
                        ? "Medium term"
                        : "Long term"}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-slate-400">Structured mechanism rows were not provided for this campaign.</p>
            )}
          </div>
        </div>
      </div>

      {limitItems.length > 0 ? (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-300">Limitations to keep in mind</h4>
          <div className="grid gap-2 sm:grid-cols-2">
            {limitItems.map((item) => (
              <div key={`${column.id}:${item.id}`} className="rounded-lg border border-amber-300/20 bg-amber-400/8 p-3 text-xs text-slate-300">
                {item.limitation}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
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
  const compareSummary = useMemo(() => buildLeadComparison(columns), [columns])

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
      className="space-y-5 rounded-[1.4rem] border border-slate-500/25 bg-linear-to-b from-slate-900/70 via-slate-950/55 to-slate-950/35 p-5 shadow-[0_18px_48px_rgba(2,6,23,0.35)]"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <p className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Compare-first narrative read</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-100">
            Risk narrative changes: {ticker} {formatFiscalYearLabel(yearFrom)} to {formatFiscalYearLabel(yearTo)}
          </h3>
          <p className="mt-2 text-sm text-slate-300">
            Start here for the lead story, paired filing evidence, and the places where Codex and ChatGPT are
            saying the same thing versus emphasizing different parts of the same filing pair.
          </p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/45 px-4 py-3 text-right">
          <div className="text-[11px] uppercase tracking-wide text-slate-400">Reading mode</div>
          <div className="mt-1 text-sm font-semibold text-slate-100">
            {analysisMode === "executive" ? "Executive" : "Deep"}
          </div>
          <div className="mt-1 text-[11px] text-slate-400">
            {analysisMode === "executive"
              ? "Top three shifts with paired evidence excerpts."
              : "Top five shifts plus investor, mechanism, and limitation context."}
          </div>
        </div>
      </div>

      <div className="grid gap-3 xl:grid-cols-[1.35fr,0.65fr,0.65fr]">
        <div className="rounded-2xl border border-white/10 bg-slate-950/45 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full border px-2.5 py-1 text-[11px] font-medium ${
                compareSummary.divergenceLabel === "substantive"
                  ? "border-amber-300/35 bg-amber-400/12 text-amber-100"
                  : compareSummary.divergenceLabel === "stylistic"
                    ? "border-sky-300/35 bg-sky-400/12 text-sky-100"
                    : "border-white/15 bg-white/5 text-slate-200"
              }`}
            >
              {compareSummary.divergenceLabel === "single"
                ? "Single campaign"
                : `${compareSummary.divergenceLabel} divergence`}
            </span>
          </div>
          <p className="mt-3 text-base font-semibold text-slate-100">{compareSummary.headline}</p>
          <p className="mt-2 text-sm text-slate-300">{compareSummary.divergenceText}</p>
        </div>
        {columns.slice(0, 2).map((column) => {
          const runtime = column.runtime
          const drift = runtime ? buildDriftScore(runtime) : null
          const lead = runtime ? sortMaterialChanges(runtime)[0] : null
          return (
            <div key={`compare-summary-${column.id}`} className="rounded-2xl border border-white/10 bg-slate-950/45 p-4">
              <div className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-medium ${column.accentClass}`}>
                {column.label || `Campaign ${column.id}`}
              </div>
              {runtime && drift ? (
                <>
                  <div className="mt-3 text-xl font-semibold text-slate-100">{(drift.score * 100).toFixed(0)}%</div>
                  <p className="text-xs text-slate-300">{drift.label}</p>
                  <p className="mt-2 text-xs text-slate-400">Lead change: {lead?.title ?? "Unavailable"}</p>
                </>
              ) : (
                <p className="mt-3 text-xs text-slate-400">No runtime compare artifact loaded for this campaign.</p>
              )}
            </div>
          )
        })}
      </div>

      <div className={`grid gap-4 ${columns.length > 1 ? "2xl:grid-cols-2" : "grid-cols-1"}`}>
        {columns.map((column) => (
          <div key={`risk-column-${column.id}`}>
            {renderCampaignNarrativeColumn({
              column,
              analysisMode,
              yearFrom,
              yearTo,
            })}
          </div>
        ))}
      </div>
    </section>
  )
}
