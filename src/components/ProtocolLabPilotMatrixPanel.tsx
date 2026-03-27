import { useEffect, useMemo, useState } from "react"
import {
  getProtocolLabLaneCode,
  isRecoveredNoncanonicalControlCell,
} from "../lib/protocolLabMatrixAdapter.ts"
import {
  formatPilotComparisonPurpose,
  formatPilotStatusLabel,
} from "../lib/protocolLabMatrixPresentation.ts"
import type {
  ProtocolLabEffortRobustnessBundle,
  ProtocolLabEffortRobustnessLaneCode,
  ProtocolLabNoveltyLedgerCase,
  ProtocolLabNoveltyLedgerModuleItem,
  ProtocolLabPilotMatrixBundle,
  ProtocolLabPilotMatrixCell,
  ProtocolLabPilotMatrixCellRole,
  ProtocolLabSkepticCaseCanonizedMatrix,
} from "../lib/protocolLabMatrixTypes.ts"

type ProtocolLabPilotMatrixPanelProps = {
  bundle: ProtocolLabPilotMatrixBundle | null
  isLoading: boolean
  error: string | null
  debugText?: string | null
  effortRobustness: ProtocolLabEffortRobustnessBundle | null
  isLoadingEffortRobustness: boolean
  effortRobustnessError: string | null
  effortRobustnessDebugText?: string | null
  noveltyLedger: ProtocolLabNoveltyLedgerCase | null
  isLoadingNoveltyLedger: boolean
  noveltyLedgerError: string | null
  noveltyLedgerDebugText?: string | null
  skepticCase: ProtocolLabSkepticCaseCanonizedMatrix | null
  isLoadingSkepticCase: boolean
  skepticCaseError: string | null
  skepticCaseDebugText?: string | null
}

type LaneTag = {
  label: string
  className: string
}

type EffortAnswerTile = {
  label: string
  value: string
  className: string
}

type SkepticAnswerTile = {
  label: string
  value: string
  className: string
}

type NoveltyGroupConfig = {
  sectionId:
    | "fresh_2025_specifics"
    | "intensified_or_broadened_points"
    | "reused_framework_language"
    | "boundary_notes"
  label: string
  className: string
  chipClassName: string
}

const ROLE_STYLES: Record<
  ProtocolLabPilotMatrixCellRole,
  {
    badge: string
    card: string
    activeCard: string
    chip: string
  }
> = {
  hero: {
    badge: "Primary read",
    card: "border-sky-300/30 bg-sky-400/10",
    activeCard: "border-sky-200/80 bg-sky-400/20 shadow-[0_0_0_1px_rgba(125,211,252,0.25)]",
    chip: "border-sky-300/30 bg-sky-400/15 text-sky-100",
  },
  main_comparator: {
    badge: "Comparison read",
    card: "border-amber-300/25 bg-amber-400/10",
    activeCard: "border-amber-200/70 bg-amber-400/18 shadow-[0_0_0_1px_rgba(251,191,36,0.22)]",
    chip: "border-amber-300/30 bg-amber-400/15 text-amber-100",
  },
  secondary_comparator: {
    badge: "Secondary comparison",
    card: "border-white/10 bg-slate-900/45",
    activeCard: "border-white/30 bg-white/10 shadow-[0_0_0_1px_rgba(255,255,255,0.08)]",
    chip: "border-white/15 bg-white/8 text-slate-100",
  },
  control: {
    badge: "Control read",
    card: "border-rose-300/25 bg-rose-400/10",
    activeCard: "border-rose-200/70 bg-rose-400/18 shadow-[0_0_0_1px_rgba(251,113,133,0.2)]",
    chip: "border-rose-300/30 bg-rose-400/15 text-rose-100",
  },
}

const NOVELTY_GROUPS: NoveltyGroupConfig[] = [
  {
    sectionId: "fresh_2025_specifics",
    label: "Fresh 2025 specifics",
    className: "border-sky-300/20 bg-slate-950/35",
    chipClassName: "border-sky-300/25 bg-sky-400/10 text-sky-100",
  },
  {
    sectionId: "intensified_or_broadened_points",
    label: "Intensified / broadened points",
    className: "border-amber-300/20 bg-slate-950/35",
    chipClassName: "border-amber-300/25 bg-amber-400/10 text-amber-100",
  },
  {
    sectionId: "reused_framework_language",
    label: "Reused framework language",
    className: "border-white/10 bg-slate-950/35",
    chipClassName: "border-white/10 bg-white/5 text-slate-200",
  },
  {
    sectionId: "boundary_notes",
    label: "Boundary notes",
    className: "border-rose-300/20 bg-slate-950/35",
    chipClassName: "border-rose-300/25 bg-rose-400/10 text-rose-100",
  },
]

function renderRoleBadge(role: ProtocolLabPilotMatrixCellRole): string {
  return ROLE_STYLES[role].badge
}

function renderEvidenceTierLabel(cell: ProtocolLabPilotMatrixCell): string {
  if (cell.evidence_richness_tier === "high") return "High evidence richness"
  if (cell.evidence_richness_tier === "medium") return "Medium evidence richness"
  return "Baseline evidence richness"
}

function buildLaneTags(cell: ProtocolLabPilotMatrixCell): LaneTag[] {
  if (!isRecoveredNoncanonicalControlCell(cell)) return []

  return [
    {
      label: "Ad hoc",
      className: "border-rose-300/30 bg-rose-400/12 text-rose-100",
    },
    {
      label: "Recovered",
      className: "border-rose-300/30 bg-rose-400/12 text-rose-100",
    },
    {
      label: "Noncanonical",
      className: "border-rose-300/30 bg-rose-400/12 text-rose-100",
    },
  ]
}

function renderBulletList(items: string[], toneClassName: string) {
  return (
    <ul className={`list-disc space-y-2 pl-5 text-sm marker:text-slate-400 ${toneClassName}`}>
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  )
}

function formatSectionLabel(sectionId: string): string {
  return sectionId
    .split("_")
    .map((part) => {
      if (/^\d+[a-z]?$/i.test(part)) return part.toUpperCase()
      return part.charAt(0).toUpperCase() + part.slice(1)
    })
    .join(" ")
}

function buildRoleRationaleItems(bundle: ProtocolLabPilotMatrixBundle): Array<{ label: string; text: string }> {
  const hasMainComparator = bundle.ordered_cells.some((cell) => cell.role === "main_comparator")
  const items = [
    {
      label: "Primary read",
      text: bundle.review.why_02_is_hero,
    },
    {
      label: hasMainComparator ? "Comparison read" : "Comparison note",
      text: bundle.review.why_03_is_main_comparator,
    },
  ]

  const hasSecondaryComparator = bundle.ordered_cells.some(
    (cell) => cell.role === "secondary_comparator"
  )
  if (hasSecondaryComparator) {
    items.push({
      label: "Secondary comparison",
      text: bundle.review.why_01_is_secondary,
    })
  } else {
    items.push({
      label: "Secondary note",
      text: bundle.review.why_01_is_secondary,
    })
  }

  const hasControlLane = bundle.ordered_cells.some((cell) => cell.role === "control")
  items.push({
    label: hasControlLane ? "Control read" : "Control note",
    text: bundle.review.why_00_is_control,
  })

  return items
}

function getLaneGridClassName(laneCount: number): string {
  if (laneCount >= 4) return "xl:grid-cols-4"
  if (laneCount === 3) return "xl:grid-cols-3"
  if (laneCount === 2) return "xl:grid-cols-2"
  return ""
}

function formatBooleanAnswer(value: boolean): string {
  return value ? "Yes" : "No"
}

function renderPublicLaneCodeLabel(value: string): string {
  if (value === "02") return "Primary read"
  if (value === "03") return "Comparison read"
  if (value === "01") return "Secondary comparison"
  if (value === "00") return "Control read"
  if (value === "P4") return "Fresh vs reused"
  return value
}

function renderPublicLaneText(value: string): string {
  return value
    .replace(/\bP4\b/g, "Fresh vs reused")
    .replace(/\b02\b/g, "Primary read")
    .replace(/\b03\b/g, "Comparison read")
    .replace(/\b01\b/g, "Secondary comparison")
    .replace(/\b00\b/g, "Control read")
}

function renderPublicCellLabel(cell: ProtocolLabPilotMatrixCell): string {
  if (cell.role === "hero") return "Primary read"
  if (cell.role === "main_comparator") return "Comparison read"
  if (cell.role === "secondary_comparator") return "Secondary comparison"
  return "Control read"
}

function buildEffortAnswerTiles(
  effortBundle: ProtocolLabEffortRobustnessBundle
): EffortAnswerTile[] {
  const effortCase = effortBundle.case_artifact
  return [
    {
      label: "Winner stayed the same",
      value: formatBooleanAnswer(effortCase.winner_stayed_same),
      className: "border-emerald-300/25 bg-emerald-400/10 text-emerald-50",
    },
    {
      label: "Comparator still meaningful",
      value: formatBooleanAnswer(effortCase.comparator_remained_meaningful),
      className: "border-amber-300/25 bg-amber-400/10 text-amber-50",
    },
    {
      label: "Control still useful",
      value: formatBooleanAnswer(effortCase.control_remained_useful),
      className: "border-rose-300/25 bg-rose-400/10 text-rose-50",
    },
    {
      label: "Integrity note",
      value: effortCase.integrity_note,
      className: "border-white/10 bg-white/5 text-slate-100",
    },
  ]
}

function buildSkepticAnswerTiles(
  skepticCase: ProtocolLabSkepticCaseCanonizedMatrix
): SkepticAnswerTile[] {
  return [
    {
      label: "Primary read broad agreement",
      value: skepticCase.agreement_snapshot["02_standard_vs_extended"].note,
      className: "border-emerald-300/25 bg-emerald-400/10 text-emerald-50",
    },
    {
      label: "Fresh vs reused broad agreement",
      value: skepticCase.agreement_snapshot.p4_standard_vs_extended.note,
      className: "border-sky-300/25 bg-sky-400/10 text-sky-50",
    },
    {
      label: "Visible third case verdict",
      value: skepticCase.visible_integration_note,
      className: "border-amber-300/25 bg-amber-400/10 text-amber-50",
    },
    {
      label: "Quality caveat",
      value: skepticCase.short_quality_caveat,
      className: "border-white/10 bg-white/5 text-slate-100",
    },
  ]
}

function isEffortLaneCode(
  value: string | null
): value is ProtocolLabEffortRobustnessLaneCode {
  return value === "02" || value === "03" || value === "00"
}

function buildOrderedEffortLaneNotes(
  bundle: ProtocolLabPilotMatrixBundle,
  effortBundle: ProtocolLabEffortRobustnessBundle
): Array<{ laneCode: ProtocolLabEffortRobustnessLaneCode; note: string }> {
  const orderedCodes = bundle.ordered_cells
    .map((cell) => getProtocolLabLaneCode(cell.cell_id))
    .filter(isEffortLaneCode)
  const uniqueCodes = [...new Set(orderedCodes)]
  return uniqueCodes.map((laneCode) => ({
    laneCode,
    note: effortBundle.case_artifact.lane_robustness[laneCode],
  }))
}

function renderNoveltySupportLabel(item: ProtocolLabNoveltyLedgerModuleItem): string {
  if (item.support_level === "both") return "Both runs"
  if (item.support_level === "extended_primary_standard_compatible") {
    return "Extended-led"
  }
  return "Standard-led"
}

function renderNoveltyItem(
  item: ProtocolLabNoveltyLedgerModuleItem,
  chipClassName: string
) {
  return (
    <article key={item.item_id} className="rounded-lg border border-white/10 bg-white/5 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <h4 className="text-sm font-semibold text-slate-50">{item.label}</h4>
        <span className={`rounded-full border px-2 py-0.5 text-[11px] ${chipClassName}`}>
          {renderNoveltySupportLabel(item)}
        </span>
      </div>
      <p className="mt-2 text-sm text-slate-100">{item.text}</p>
    </article>
  )
}

function buildOverflowNoveltyGroups(noveltyLedger: ProtocolLabNoveltyLedgerCase) {
  return NOVELTY_GROUPS.map((group) => ({
    ...group,
    items: noveltyLedger.module_sections[group.sectionId].slice(2),
  })).filter((group) => group.items.length > 0)
}

export default function ProtocolLabPilotMatrixPanel({
  bundle,
  isLoading,
  error,
  debugText = null,
  effortRobustness,
  isLoadingEffortRobustness,
  effortRobustnessError,
  effortRobustnessDebugText = null,
  noveltyLedger,
  isLoadingNoveltyLedger,
  noveltyLedgerError,
  noveltyLedgerDebugText = null,
  skepticCase,
  isLoadingSkepticCase,
  skepticCaseError,
  skepticCaseDebugText = null,
}: ProtocolLabPilotMatrixPanelProps) {
  const defaultSelectedCellId = bundle?.matrix.selected_default_cell_id ?? null
  const [selectedCellId, setSelectedCellId] = useState<string | null>(defaultSelectedCellId)

  useEffect(() => {
    setSelectedCellId(defaultSelectedCellId)
  }, [defaultSelectedCellId])

  const selectedCell = useMemo(() => {
    if (!bundle) return null
    const fallback =
      bundle.cells_by_id[bundle.matrix.selected_default_cell_id] ?? bundle.ordered_cells[0] ?? null
    if (!selectedCellId) return fallback
    return bundle.cells_by_id[selectedCellId] ?? fallback
  }, [bundle, selectedCellId])

  if (isLoading && !bundle) {
    return (
      <section
        id="lab-pilot-matrix"
        className="rounded-[1.35rem] border border-white/10 bg-white/5 p-5 text-sm text-slate-200"
      >
        Loading case comparison...
      </section>
    )
  }

  if (!bundle) {
    return (
    <section
      id="lab-pilot-matrix"
      className="rounded-[1.35rem] border border-amber-300/20 bg-amber-400/10 p-5 text-sm text-slate-200"
    >
        <div className="text-xs uppercase tracking-wide text-amber-100">Case comparison unavailable</div>
        <p className="mt-2 text-sm text-slate-100">
          The comparison-first case view did not load. Existing deeper audit surfaces remain
          available below when present.
        </p>
        {error ? <p className="mt-3 text-xs text-amber-100">{error}</p> : null}
        {debugText ? <p className="mt-2 break-all text-[11px] text-slate-300">{debugText}</p> : null}
      </section>
    )
  }

  const story = bundle.story
  const pairInfo = bundle.matrix.pair_info
  const issuerLabel = pairInfo.issuer_name || pairInfo.ticker
  const fixtureLabel = `${pairInfo.ticker} ${pairInfo.year_from} to ${pairInfo.year_to}`
  const sectionLabel = `${pairInfo.form_type} ${formatSectionLabel(pairInfo.section_id)}`
  const laneGridClassName = getLaneGridClassName(bundle.ordered_cells.length)
  const roleRationaleItems = buildRoleRationaleItems(bundle)
  const pilotStatusLabel = formatPilotStatusLabel(bundle.matrix.pilot_status.state)
  const effortAnswerTiles = effortRobustness ? buildEffortAnswerTiles(effortRobustness) : []
  const skepticAnswerTiles = skepticCase ? buildSkepticAnswerTiles(skepticCase) : []
  const orderedEffortLaneNotes =
    effortRobustness ? buildOrderedEffortLaneNotes(bundle, effortRobustness) : []
  const noveltyOverflowGroups = noveltyLedger ? buildOverflowNoveltyGroups(noveltyLedger) : []
  const isSkepticMode = bundle.matrix.comparison_pairs.length === 0
  const isLoadingMatchedEffort = isLoadingEffortRobustness || isLoadingSkepticCase
  const matchedEffortError = skepticCaseError ?? effortRobustnessError
  const matchedEffortDebugText = skepticCaseDebugText ?? effortRobustnessDebugText

  return (
    <section
      id="lab-pilot-matrix"
      className="space-y-4 rounded-[1.35rem] border border-white/10 bg-linear-to-br from-slate-950/75 via-slate-900/65 to-slate-950/40 p-4 shadow-[0_18px_40px_rgba(2,6,23,0.2)] sm:space-y-5 sm:p-5"
    >
      <div className="grid gap-3 sm:gap-4 lg:grid-cols-[1.15fr,0.85fr]">
        <div className="space-y-3 sm:space-y-4">
          <div>
            <div className="text-[11px] uppercase tracking-[0.24em] text-sky-100">
              Protocol meaning
            </div>
            <h2 className="mt-1.5 text-lg font-semibold text-slate-50 sm:mt-2 sm:text-xl">
              {isSkepticMode
                ? "How the restraint read fits this filing pair"
                : "How the visible reads frame this filing pair"}
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-200">
              {isSkepticMode
                ? "Second layer after the filing answer: why the restraint case stays visible, what the visible reads add, and where the protocol boundary sits."
                : "Second layer after the filing answer: why this fixture is in the lab, what the visible reads add, and where the protocol boundary sits."}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-lg border border-white/10 bg-slate-900/42 p-3">
              <div className="text-[10px] uppercase tracking-[0.22em] text-slate-400">Fixture</div>
              <div className="mt-1 text-sm font-semibold text-slate-100">{fixtureLabel}</div>
              <div className="mt-1 text-xs text-slate-400">{sectionLabel}</div>
            </div>
            <div className="rounded-lg border border-white/10 bg-slate-900/42 p-3">
              <div className="text-[10px] uppercase tracking-[0.22em] text-slate-400">Primary read</div>
              <div className="mt-1 text-sm font-semibold text-slate-100">
                {bundle.cells_by_id[bundle.matrix.selected_default_cell_id]
                  ? renderPublicCellLabel(bundle.cells_by_id[bundle.matrix.selected_default_cell_id])
                  : renderPublicLaneText(bundle.matrix.selected_default_cell_id)}
              </div>
            </div>
            <div className="rounded-lg border border-white/10 bg-slate-900/42 p-3">
              <div className="text-[10px] uppercase tracking-[0.22em] text-slate-400">Scope</div>
              <div className="mt-1 text-sm font-semibold text-slate-100">{pilotStatusLabel}</div>
            </div>
            <div className="rounded-lg border border-white/10 bg-slate-900/42 p-3">
              <div className="text-[10px] uppercase tracking-[0.22em] text-slate-400">Read order</div>
              <div className="mt-1 text-sm font-semibold text-slate-100">
                {bundle.ordered_cells.map((cell) => renderPublicCellLabel(cell)).join(" -> ")}
              </div>
            </div>
          </div>

          {bundle.matrix.comparison_pairs.length > 0 ? (
            <div className="flex flex-wrap gap-1.5 text-[11px] text-slate-200 sm:gap-2 sm:text-xs">
              {bundle.matrix.comparison_pairs.map((pair) => (
                <span
                  key={pair.pair_id}
                  className="rounded-full border border-white/10 bg-slate-900/38 px-2.5 py-1 sm:px-3 sm:py-1.5"
                  title={pair.purpose}
                >
                  {renderPublicLaneText(pair.label)}: {formatPilotComparisonPurpose(pair)}
                </span>
              ))}
            </div>
          ) : null}
        </div>

        <div className="space-y-2.5 rounded-[1.1rem] border border-sky-300/20 bg-sky-400/8 p-3 sm:p-4">
          <div className="text-[10px] uppercase tracking-[0.24em] text-sky-100">
            Why this fixture is in the lab
          </div>
          <p className="text-sm text-slate-100">{story.why_this_case_matters}</p>
          <div className="pt-1.5 text-[10px] uppercase tracking-[0.24em] text-slate-300">Pilot scope</div>
          <p className="text-sm text-slate-200">{bundle.matrix.pilot_status.note}</p>
        </div>
      </div>

      <div className="grid gap-3 sm:gap-4 lg:grid-cols-2">
        <article className="space-y-3 rounded-[1.1rem] border border-sky-300/20 bg-slate-950/35 p-3 sm:p-4">
          <div>
            <div className="text-[10px] uppercase tracking-[0.24em] text-sky-100">
              {isSkepticMode ? "What the visible checks add" : "What the visible reads add"}
            </div>
            <p className="mt-2 text-sm text-slate-200">{story.protocol_read}</p>
          </div>
          {renderBulletList(bundle.matrix.takeaways, "text-slate-100")}
        </article>

        <article className="space-y-3 rounded-[1.1rem] border border-amber-300/20 bg-slate-950/35 p-3 sm:p-4">
          <div>
            <div className="text-[10px] uppercase tracking-[0.24em] text-amber-100">
              Protocol boundary
            </div>
            <p className="mt-2 text-sm text-slate-200">{story.caveat}</p>
          </div>
          {renderBulletList(bundle.matrix.caveats, "text-slate-100")}
        </article>
      </div>

      {skepticCase ? (
        <section className="rounded-[1.1rem] border border-sky-300/20 bg-sky-400/8 p-3 sm:p-4">
          <div className="text-[10px] uppercase tracking-[0.24em] text-sky-100">Restraint case</div>
          <p className="mt-2 text-sm text-slate-100">{skepticCase.framing_note}</p>
        </section>
      ) : null}

      {effortRobustness ? (
        <section className="space-y-3 sm:space-y-4 rounded-[1.1rem] border border-emerald-300/20 bg-emerald-400/8 p-3 sm:p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="text-[10px] uppercase tracking-[0.24em] text-emerald-100">
                Effort robustness
              </div>
              <p className="mt-2 max-w-3xl text-sm text-slate-100">
                {effortRobustness.case_artifact.headline}
              </p>
            </div>
            <span className="rounded-full border border-white/10 bg-slate-950/35 px-3 py-1 text-[11px] text-slate-200">
              Read order {effortRobustness.case_artifact.lane_order_materially_changed ? "changed" : "held"}
            </span>
          </div>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {effortAnswerTiles.map((tile) => (
              <article key={tile.label} className={`rounded-lg border p-3 ${tile.className}`}>
                <div className="text-[11px] uppercase tracking-wide text-slate-300">{tile.label}</div>
                <p className="mt-2 text-sm">{tile.value}</p>
              </article>
            ))}
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            {orderedEffortLaneNotes.map((item) => (
              <article
                key={item.laneCode}
                className="rounded-lg border border-white/10 bg-slate-950/35 p-3"
              >
                <div className="text-[11px] uppercase tracking-wide text-slate-300">
                  {renderPublicLaneCodeLabel(item.laneCode)}
                </div>
                <p className="mt-2 text-sm text-slate-100">{item.note}</p>
              </article>
            ))}
          </div>

          <div className="grid gap-3 lg:grid-cols-2">
            <div className="rounded-lg border border-white/10 bg-slate-950/35 p-3">
              <div className="text-[11px] uppercase tracking-wide text-slate-300">
                What held up
              </div>
              {renderBulletList(effortRobustness.case_artifact.stable_findings, "mt-2 text-slate-100")}
            </div>
            <div className="rounded-lg border border-white/10 bg-slate-950/35 p-3">
              <div className="text-[11px] uppercase tracking-wide text-slate-300">
                What weakened under standard
              </div>
              {renderBulletList(
                effortRobustness.case_artifact.weakened_under_standard,
                "mt-2 text-slate-100"
              )}
            </div>
          </div>

          {effortRobustness.summary_artifact ? (
            <div className="rounded-lg border border-white/10 bg-slate-950/35 p-3">
              <div className="text-[11px] uppercase tracking-wide text-slate-300">
                Cross-case read
              </div>
              <p className="mt-2 text-sm text-slate-100">
                {effortRobustness.summary_artifact.protocol_value_under_lower_effort}
              </p>
              <p className="mt-3 text-xs text-slate-300">
                {effortRobustness.summary_artifact.still_should_not_claim}
              </p>
            </div>
          ) : null}

          {effortRobustnessError && !effortRobustness.summary_artifact ? (
            <div className="rounded-lg border border-amber-300/25 bg-amber-400/10 p-3">
              <div className="text-[11px] uppercase tracking-wide text-amber-100">
                Cross-case footer unavailable
              </div>
              <p className="mt-2 text-sm text-slate-100">{effortRobustnessError}</p>
              {effortRobustnessDebugText ? (
                <p className="mt-2 break-all text-[11px] text-slate-300">
                  {effortRobustnessDebugText}
                </p>
              ) : null}
            </div>
          ) : null}
        </section>
      ) : null}

      {!effortRobustness && skepticCase ? (
        <section className="space-y-3 sm:space-y-4 rounded-[1.1rem] border border-emerald-300/20 bg-emerald-400/8 p-3 sm:p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="text-[10px] uppercase tracking-[0.24em] text-emerald-100">
                Matched-effort restraint check
              </div>
              <p className="mt-2 max-w-3xl text-sm text-slate-100">{skepticCase.finding_summary}</p>
            </div>
            <span className="rounded-full border border-white/10 bg-slate-950/35 px-3 py-1 text-[11px] text-slate-200">
              {skepticCase.supports_visible_limited_integration ? "Visible third case" : "Review only"}
            </span>
          </div>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {skepticAnswerTiles.map((tile) => (
              <article key={tile.label} className={`rounded-lg border p-3 ${tile.className}`}>
                <div className="text-[11px] uppercase tracking-wide text-slate-300">{tile.label}</div>
                <p className="mt-2 text-sm">{tile.value}</p>
              </article>
            ))}
          </div>

          <div className="rounded-lg border border-white/10 bg-slate-950/35 p-3">
            <div className="text-[11px] uppercase tracking-wide text-slate-300">
              Why this case matters for the product
            </div>
            <p className="mt-2 text-sm text-slate-100">{skepticCase.product_interpretation}</p>
          </div>
        </section>
      ) : null}

      {!effortRobustness && !skepticCase && isLoadingMatchedEffort ? (
        <section className="rounded-[1.1rem] border border-white/10 bg-white/5 p-4 text-sm text-slate-200">
          Loading matched-effort read...
        </section>
      ) : null}

      {!effortRobustness && !skepticCase && !isLoadingMatchedEffort && matchedEffortError ? (
        <section className="rounded-[1.1rem] border border-amber-300/20 bg-amber-400/10 p-4 text-sm text-slate-200">
          <div className="text-xs uppercase tracking-wide text-amber-100">
            Matched-effort read unavailable
          </div>
          <p className="mt-2 text-sm text-slate-100">{matchedEffortError}</p>
          {matchedEffortDebugText ? (
            <p className="mt-2 break-all text-[11px] text-slate-300">{matchedEffortDebugText}</p>
          ) : null}
        </section>
      ) : null}

      {noveltyLedger ? (
        <section className="space-y-3 sm:space-y-4 rounded-[1.1rem] border border-sky-300/20 bg-sky-400/8 p-3 sm:p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="text-[10px] uppercase tracking-[0.24em] text-sky-100">Fresh vs reused</div>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-100">
                This view separates new disclosure from reused filing structure. It is narrower
                than the main summary, but useful for checking whether the filing truly introduced
                new risk detail.
              </p>
            </div>
            <span className="rounded-full border border-white/10 bg-slate-950/35 px-3 py-1 text-[11px] text-slate-200">
              Second lens
            </span>
          </div>

          <div className="rounded-lg border border-white/10 bg-slate-950/35 p-3">
            <p className="text-sm text-slate-100">{noveltyLedger.issuer_finding_summary}</p>
            <p className="mt-3 text-xs text-slate-300">
              {noveltyLedger.comparison_to_02.why_secondary_only}
            </p>
          </div>

          <div className="grid gap-3 lg:grid-cols-2">
            {NOVELTY_GROUPS.map((group) => {
              const items = noveltyLedger.module_sections[group.sectionId]
              const visibleItems = items.slice(0, 2)

              return (
                <article key={group.sectionId} className={`rounded-lg border p-3 ${group.className}`}>
                  <div className="text-[11px] uppercase tracking-wide text-slate-300">
                    {group.label}
                  </div>
                  <div className="mt-3 space-y-3">
                    {visibleItems.length > 0 ? (
                      visibleItems.map((item) => renderNoveltyItem(item, group.chipClassName))
                    ) : (
                      <p className="text-sm text-slate-300">
                        No canonized items surfaced for this issuer in this bucket.
                      </p>
                    )}
                  </div>
                </article>
              )
            })}
          </div>

          {noveltyOverflowGroups.length > 0 ? (
            <details className="rounded-lg border border-white/10 bg-slate-950/35 p-3">
              <summary className="cursor-pointer text-xs uppercase tracking-wide text-slate-300">
                Show more items
              </summary>
              <div className="mt-3 space-y-4">
                {noveltyOverflowGroups.map((group) => (
                  <div key={`overflow-${group.sectionId}`} className="space-y-3">
                    <div className="text-[11px] uppercase tracking-wide text-slate-400">
                      {group.label}
                    </div>
                    <div className="space-y-3">
                      {group.items.map((item) => renderNoveltyItem(item, group.chipClassName))}
                    </div>
                  </div>
                ))}
              </div>
            </details>
          ) : null}

          <div className="rounded-lg border border-white/10 bg-slate-950/35 p-3">
            <div className="text-[11px] uppercase tracking-wide text-slate-300">
              Agreement note
            </div>
            <p className="mt-2 text-sm text-slate-100">
              {noveltyLedger.standard_and_extended_agreement_note}
            </p>
            <p className="mt-3 text-xs text-slate-300">
              Canonized from the standard and extended Fresh vs reused runs. Logged quality caveats stay
              audit-side instead of being silently ignored.
            </p>
          </div>
        </section>
      ) : null}

      {!noveltyLedger && isLoadingNoveltyLedger ? (
        <section className="rounded-[1.1rem] border border-white/10 bg-white/5 p-4 text-sm text-slate-200">
          Loading fresh-vs-reused view...
        </section>
      ) : null}

      {!noveltyLedger && !isLoadingNoveltyLedger && noveltyLedgerError ? (
        <section className="rounded-[1.1rem] border border-amber-300/20 bg-amber-400/10 p-4 text-sm text-slate-200">
          <div className="text-xs uppercase tracking-wide text-amber-100">
            Fresh vs reused unavailable
          </div>
          <p className="mt-2 text-sm text-slate-100">{noveltyLedgerError}</p>
          {noveltyLedgerDebugText ? (
            <p className="mt-2 break-all text-[11px] text-slate-300">{noveltyLedgerDebugText}</p>
          ) : null}
        </section>
      ) : null}

      <div className={`grid gap-3 md:grid-cols-2 ${laneGridClassName}`}>
        {bundle.ordered_cells.map((cell) => {
          const isSelected = selectedCell?.cell_id === cell.cell_id
          const roleStyle = ROLE_STYLES[cell.role]
          const laneTags = buildLaneTags(cell)

          return (
            <button
              key={cell.cell_id}
              type="button"
              onClick={() => setSelectedCellId(cell.cell_id)}
              className={`rounded-2xl border p-4 text-left transition hover:border-white/30 ${roleStyle.card} ${isSelected ? roleStyle.activeCard : ""}`}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-300">
                    {renderPublicCellLabel(cell)}
                  </div>
                  <div className="mt-1 text-sm font-semibold text-slate-50">{cell.label}</div>
                </div>
                <span className={`rounded-full border px-2 py-1 text-[11px] ${roleStyle.chip}`}>
                  {renderRoleBadge(cell.role)}
                </span>
              </div>

              {laneTags.length > 0 ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {laneTags.map((tag) => (
                    <span
                      key={`${cell.cell_id}-${tag.label}`}
                      className={`rounded-full border px-2 py-1 text-[11px] ${tag.className}`}
                    >
                      {tag.label}
                    </span>
                  ))}
                </div>
              ) : null}

              <div className="mt-3 text-sm text-slate-200">{cell.protocol_input_identity.display_text}</div>
              <p className="mt-3 text-sm text-slate-100">{cell.card_takeaway}</p>
              {isRecoveredNoncanonicalControlCell(cell) ? (
                <p className="mt-3 rounded-md border border-rose-300/25 bg-rose-400/10 px-3 py-2 text-xs text-rose-100">
                  Recovered control. Same tagged substrate, but not a fully structured read.
                </p>
              ) : null}
              <div className="mt-3 text-xs text-slate-300">{cell.auditability_note}</div>
            </button>
          )
        })}
      </div>

      {selectedCell ? (
        <>
          <div className="grid gap-4 lg:grid-cols-[1.25fr,0.75fr]">
            <div className="space-y-4 rounded-[1.1rem] border border-white/10 bg-slate-950/35 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full border px-2 py-1 text-[11px] ${ROLE_STYLES[selectedCell.role].chip}`}>
                  {renderRoleBadge(selectedCell.role)}
                </span>
                {buildLaneTags(selectedCell).map((tag) => (
                  <span
                    key={`${selectedCell.cell_id}-selected-${tag.label}`}
                    className={`rounded-full border px-2 py-1 text-[11px] ${tag.className}`}
                  >
                    {tag.label}
                  </span>
                ))}
                <span className="rounded-full border border-white/10 bg-white/5 px-2 py-1 text-[11px] text-slate-300">
                  {renderEvidenceTierLabel(selectedCell)}
                </span>
                <span className="rounded-full border border-white/10 bg-white/5 px-2 py-1 text-[11px] text-slate-300">
                  {selectedCell.output_shape_info.display_text}
                </span>
              </div>

              {isRecoveredNoncanonicalControlCell(selectedCell) ? (
                <div className="rounded-lg border border-rose-300/25 bg-rose-400/10 p-3">
                  <div className="text-xs uppercase tracking-wide text-rose-100">Recovered control warning</div>
                  <p className="mt-2 text-sm text-rose-50">
                    The ad hoc control was recovered for comparison, but it is not a canonical
                    structured comparison output.
                  </p>
                </div>
              ) : null}

              <div>
                <h3 className="text-lg font-semibold text-slate-50">{selectedCell.headline}</h3>
                <p className="mt-3 whitespace-pre-line text-sm text-slate-200">{selectedCell.summary}</p>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-lg border border-white/10 bg-white/5 p-3">
                  <div className="text-xs uppercase tracking-wide text-slate-400">Why this read matters</div>
                  <p className="mt-2 text-sm text-slate-100">{selectedCell.why_this_lane_matters}</p>
                </div>
                <div className="rounded-lg border border-white/10 bg-white/5 p-3">
                  <div className="text-xs uppercase tracking-wide text-slate-400">Normalization status</div>
                  <p className="mt-2 text-sm text-slate-100">{selectedCell.normalization_status.note}</p>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-lg border border-white/10 bg-white/5 p-3">
                  <div className="text-xs uppercase tracking-wide text-slate-400">Strengths</div>
                  {renderBulletList(selectedCell.strengths, "mt-2 text-slate-100")}
                </div>
                <div className="rounded-lg border border-white/10 bg-white/5 p-3">
                  <div className="text-xs uppercase tracking-wide text-slate-400">Limitations</div>
                  {renderBulletList(selectedCell.limitations, "mt-2 text-slate-100")}
                </div>
              </div>

              <div className="space-y-3">
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-400">Evidence preview</div>
                  <p className="mt-1 text-xs text-slate-400">
                    Showing {selectedCell.evidence_preview.length} of {selectedCell.evidence_count_total} cited evidence items.
                  </p>
                </div>
                <div className="grid gap-3">
                  {selectedCell.evidence_preview.map((item) => (
                    <article key={item.evidence_id} className="rounded-lg border border-white/10 bg-white/5 p-3">
                      <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-300">
                        <span>{item.evidence_id}</span>
                        <span>{item.year_label}</span>
                        {item.paragraph_id ? <span>{item.paragraph_id}</span> : <span>paragraph id unavailable</span>}
                      </div>
                      <p className="mt-2 text-sm text-slate-100">{item.quote_text}</p>
                      {item.short_note ? <p className="mt-2 text-xs text-slate-300">{item.short_note}</p> : null}
                    </article>
                  ))}
                </div>
              </div>
            </div>

            <aside className="space-y-4 rounded-[1.1rem] border border-white/10 bg-slate-950/35 p-4">
              <details className="rounded-lg border border-white/10 bg-white/5 p-3">
                <summary className="cursor-pointer text-xs uppercase tracking-wide text-slate-400">
                  Read rationale
                </summary>
                <p className="mt-2 text-xs text-slate-400">
                  Secondary context for why each visible read keeps its current role in this case comparison.
                </p>
                <div className="mt-3 space-y-3 text-sm text-slate-100">
                  {roleRationaleItems.map((item) => (
                    <div key={item.label}>
                      <div className="text-[11px] uppercase tracking-wide text-slate-400">{item.label}</div>
                      <p className="mt-1">{item.text}</p>
                    </div>
                  ))}
                </div>
              </details>

              <div className="rounded-lg border border-white/10 bg-white/5 p-3">
                <div className="text-xs uppercase tracking-wide text-slate-400">Raw source refs</div>
                <p className="mt-2 break-all text-[11px] text-slate-300">
                  response: {selectedCell.raw_source_refs.response_path}
                </p>
                <p className="mt-2 break-all text-[11px] text-slate-300">
                  manifest: {selectedCell.raw_source_refs.run_manifest_path}
                </p>
              </div>

              <div className="rounded-lg border border-white/10 bg-white/5 p-3">
                <div className="text-xs uppercase tracking-wide text-slate-400">Scope boundary</div>
                <p className="mt-2 text-sm text-slate-100">
                  {issuerLabel} remains a bounded visible pilot view. Claims are filing-first and
                  bounded to this fixed year pair.
                </p>
              </div>
            </aside>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <article className="rounded-[1.1rem] border border-white/10 bg-slate-950/35 p-4">
              <div className="text-xs uppercase tracking-wide text-slate-400">
                What this supports vs not yet
              </div>
              {renderBulletList(bundle.review.supports, "mt-2 text-slate-100")}
              {renderBulletList(bundle.review.does_not_yet_support, "mt-3 text-slate-300")}
            </article>

            <article className="space-y-4 rounded-[1.1rem] border border-amber-300/20 bg-amber-400/10 p-4">
              <div>
                <div className="text-xs uppercase tracking-wide text-amber-100">Scope boundary</div>
                <p className="mt-2 text-sm text-slate-100">{story.caveat}</p>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-slate-300">Comparison caveats</div>
                {renderBulletList(bundle.matrix.caveats, "mt-2 text-slate-100")}
              </div>
            </article>
          </div>
        </>
      ) : null}
    </section>
  )
}
