import KORestraintStrip from "./KORestraintStrip"
import { compactText } from "../lib/compactText"
import { getPublicCasebookEntry } from "../lib/casebookContent"
import { formatPilotStatusLabel } from "../lib/protocolLabMatrixPresentation.ts"
import type {
  ProtocolLabPilotMatrixBundle,
  ProtocolLabPilotMatrixCell,
} from "../lib/protocolLabMatrixTypes.ts"
import { getRouteFamilyConfig } from "../lib/routeFamilyUi"
import type { LabPanelPilotArtifactsState } from "./useLabPanelPilotArtifacts"

type PreviewVariant = "integrated" | "bounded"

type PreviewTile = {
  label: string
  value: string
  tone: "neutral" | "accent" | "boundary"
}

type ProtocolPreviewViewModel = {
  title: string
  lead: string
  showLead: boolean
  supportLine: string
  metaLine: string | null
  visibleTiles: PreviewTile[]
  detailTile: PreviewTile
  boundaryTile: PreviewTile
  showDetailDisclosure: boolean
  showRestraintStrip: boolean
}

type ProtocolPreviewCardProps = {
  pilotArtifacts: LabPanelPilotArtifactsState
  ticker?: string
  variant?: PreviewVariant
}

function getPrimaryCell(bundle: LabPanelPilotArtifactsState["pilotMatrixBundle"]): ProtocolLabPilotMatrixCell | null {
  if (!bundle) return null
  return bundle.cells_by_id[bundle.matrix.selected_default_cell_id] ?? bundle.ordered_cells[0] ?? null
}

function renderPublicCellLabel(cell: ProtocolLabPilotMatrixCell): string {
  if (cell.role === "hero") return "Primary read"
  if (cell.role === "main_comparator") return "Comparison read"
  if (cell.role === "secondary_comparator") return "Secondary comparison"
  return "Control read"
}

function renderApproachComparison(bundle: ProtocolLabPilotMatrixBundle) {
  const pair = bundle.matrix.comparison_pairs[0]
  if (!pair) return null

  const left = bundle.cells_by_id[pair.left_cell_id]
  const right = bundle.cells_by_id[pair.right_cell_id]
  if (!left || !right) return null

  const sides: Array<{ cell: ProtocolLabPilotMatrixCell; position: "Left" | "Right" }> = [
    { cell: left, position: "Left" },
    { cell: right, position: "Right" },
  ]

  return (
    <article className="rounded-[1.35rem] border border-sky-300/20 bg-sky-400/6 p-3.5 sm:p-4.5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1.5">
          <p className="text-[11px] uppercase tracking-[0.24em] text-sky-100">
            Approach comparison
          </p>
          <h3 className="text-base font-semibold text-slate-50 sm:text-lg">{pair.label}</h3>
        </div>
        <span className="rounded-full border border-sky-300/20 bg-sky-400/10 px-2.5 py-1 text-[10px] text-sky-100">
          Same substrate
        </span>
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-300">{pair.purpose}</p>
      <div className="mt-3 grid gap-2.5 sm:grid-cols-2">
        {sides.map(({ cell, position }) => (
          <article
            key={cell.cell_id}
            className="rounded-2xl border border-white/10 bg-slate-950/58 p-3"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="rounded-full border border-sky-300/25 bg-sky-400/10 px-2 py-0.5 text-[10px] font-semibold text-sky-100">
                {cell.short_label}
              </span>
              <span className="text-[10px] uppercase tracking-[0.2em] text-slate-400">
                {position} / {renderPublicCellLabel(cell)}
              </span>
            </div>
            <p className="mt-2 text-[11px] text-slate-400">
              {cell.protocol_input_identity.display_text}
            </p>
            <p className="mt-2 text-sm leading-6 text-slate-100">
              {compactText(cell.card_takeaway, 160)}
            </p>
          </article>
        ))}
      </div>
    </article>
  )
}

function getToneClasses(tone: PreviewTile["tone"]): string {
  if (tone === "accent") {
    return "border-sky-300/18 bg-sky-400/8"
  }
  if (tone === "boundary") {
    return "border-amber-300/18 bg-amber-400/7"
  }
  return "border-white/10 bg-slate-950/32"
}

function buildPreviewModel(
  pilotArtifacts: LabPanelPilotArtifactsState,
  ticker: string | undefined,
  variant: PreviewVariant
): ProtocolPreviewViewModel | null {
  const { pilotMatrixBundle } = pilotArtifacts
  if (!pilotMatrixBundle) return null

  const familyConfig = getRouteFamilyConfig(ticker)
  const casebookEntry = getPublicCasebookEntry(ticker)
  const primaryCell = getPrimaryCell(pilotMatrixBundle)
  const showRestraintStrip = Boolean(familyConfig?.preview.showRestraintStrip)
  const subtitleSource = familyConfig?.preview.subtitleSource ?? "card_takeaway"
  const rawSubtitle =
    subtitleSource === "protocol_read"
      ? pilotMatrixBundle.story.protocol_read
      : subtitleSource === "why_case_exists"
        ? pilotMatrixBundle.story.why_this_case_matters
        : primaryCell?.card_takeaway ?? pilotMatrixBundle.story.why_this_case_matters
  const proofBasisTile = {
    label: "Proof basis",
    value: compactText(
      casebookEntry?.proofBasis ?? pilotMatrixBundle.matrix.pilot_status.note,
      showRestraintStrip ? 98 : 118
    ),
    tone: "accent" as const,
  }
  const boundaryTile = {
    label: "Stop boundary",
    value: compactText(
      casebookEntry?.stopBoundary ?? pilotMatrixBundle.story.caveat,
      showRestraintStrip ? 96 : 104
    ),
    tone: "boundary" as const,
  }
  const statusLabel = formatPilotStatusLabel(pilotMatrixBundle.matrix.pilot_status.state)
  const routeLabel =
    casebookEntry?.surface === "matrix_first" ? "Matrix-led case" : "Full compare case"
  const showLead = !showRestraintStrip
  const metaLine = `${routeLabel} · Scope: ${statusLabel}`
  const visibleTiles = showRestraintStrip ? [proofBasisTile] : [proofBasisTile, boundaryTile]

  return {
    title:
      variant === "bounded"
        ? familyConfig?.preview.boundedTitle ?? "Why this read is here"
        : familyConfig?.preview.integratedTitle ?? "Why this case is here",
    lead: compactText(
      variant === "bounded" ? casebookEntry?.publicClaim ?? rawSubtitle : rawSubtitle,
      showRestraintStrip ? 0 : variant === "bounded" ? 132 : 128
    ),
    showLead,
    supportLine: compactText(
      familyConfig?.preview.roleSummary ?? pilotMatrixBundle.story.why_this_case_matters,
      showRestraintStrip ? 92 : 108
    ),
    metaLine,
    visibleTiles,
    detailTile: proofBasisTile,
    boundaryTile,
    showDetailDisclosure: variant === "integrated",
    showRestraintStrip,
  }
}

export default function ProtocolPreviewCard({
  pilotArtifacts,
  ticker,
  variant = "integrated",
}: ProtocolPreviewCardProps) {
  const {
    pilotMatrixBundle,
    isLoadingPilotMatrix,
    pilotMatrixError,
    pilotMatrixDebugText,
    skepticCaseArtifact,
  } = pilotArtifacts

  if (isLoadingPilotMatrix && !pilotMatrixBundle) {
    return (
      <section
        id="lab-pilot-matrix"
        className="rounded-[1.35rem] border border-white/10 bg-white/5 p-4 text-sm text-slate-200 shadow-[0_18px_40px_rgba(2,6,23,0.2)] sm:p-5"
      >
        Loading protocol preview...
      </section>
    )
  }

  if (!pilotMatrixBundle) {
    return (
      <section
        id="lab-pilot-matrix"
        className="space-y-3 rounded-[1.35rem] border border-amber-300/20 bg-amber-400/10 p-4 text-sm text-slate-200 shadow-[0_18px_40px_rgba(2,6,23,0.2)] sm:p-5"
      >
        <div>
          <p className="text-[11px] uppercase tracking-[0.24em] text-amber-100">Why this read matters</p>
          <h2 className="mt-1.5 text-lg font-semibold text-slate-50">Second layer unavailable</h2>
        </div>
        <p className="text-sm text-slate-100">
          The filing answer is still available above. The second layer did not load for this case,
          so deeper pressure-testing should rely on the audit gateway below.
        </p>
        {pilotMatrixError ? <p className="text-sm text-amber-100">{pilotMatrixError}</p> : null}
        {pilotMatrixDebugText ? (
          <p className="break-all text-[11px] text-slate-300">{pilotMatrixDebugText}</p>
        ) : null}
      </section>
    )
  }

  const previewModel = buildPreviewModel(pilotArtifacts, ticker, variant)
  if (!previewModel) return null

  const readOrder = pilotMatrixBundle.ordered_cells.map((cell) => renderPublicCellLabel(cell)).join(" -> ")

  return (
    <section id="lab-pilot-matrix" className="space-y-3">
      <article className="rounded-[1.35rem] border border-white/10 bg-linear-to-br from-slate-950/82 via-slate-900/65 to-slate-950/40 p-3.5 shadow-[0_18px_40px_rgba(2,6,23,0.2)] sm:p-4.5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1.5">
            <p className="text-[11px] uppercase tracking-[0.24em] text-sky-100">Why this read matters</p>
            <h2 className="text-lg font-semibold text-slate-50 sm:text-xl">{previewModel.title}</h2>
          </div>
          <span className="rounded-full border border-sky-300/20 bg-sky-400/10 px-2.5 py-1 text-[10px] text-sky-100">
            Second layer
          </span>
        </div>

        {previewModel.showRestraintStrip && skepticCaseArtifact ? (
          <div className="mt-2.5">
            <KORestraintStrip bundle={pilotMatrixBundle} skepticCase={skepticCaseArtifact} />
          </div>
        ) : null}

        {previewModel.showLead ? (
          <p className="mt-3 text-lg font-semibold leading-7 text-slate-100 sm:text-[1.1rem]">
            {previewModel.lead}
          </p>
        ) : null}
        <p className={`${previewModel.showLead ? "mt-2" : "mt-3"} text-sm leading-6 text-slate-300`}>
          {previewModel.supportLine}
        </p>

        {previewModel.metaLine ? (
          <p className="mt-2 text-[11px] uppercase tracking-[0.2em] text-slate-400">
            {previewModel.metaLine}
          </p>
        ) : null}

        <div className={`mt-3 grid gap-2.5 ${previewModel.visibleTiles.length > 1 ? "sm:grid-cols-2" : ""}`}>
          {previewModel.visibleTiles.map((tile) => (
            <article
              key={tile.label}
              className={`rounded-2xl border p-3 ${getToneClasses(tile.tone)}`}
            >
              <div className="text-[10px] uppercase tracking-[0.24em] text-slate-300">{tile.label}</div>
              <p className="mt-1.5 text-sm leading-5 text-slate-100">{tile.value}</p>
            </article>
          ))}
        </div>
      </article>

      {renderApproachComparison(pilotMatrixBundle)}

      {previewModel.showDetailDisclosure ? (
        <details className="rounded-[1.1rem] border border-white/10 bg-slate-950/26 p-2.5 sm:p-3.5">
          <summary className="cursor-pointer list-none text-[13px] font-medium text-slate-100 sm:text-sm">
            More detail
          </summary>
          <p className="mt-1.5 text-[11px] leading-5 text-slate-400">
            Lane roles, scope cues, and supporting notes stay discoverable here without taking
            over the default fold.
          </p>

          <div className="mt-2.5 grid gap-2.5 md:grid-cols-3">
            <article className="rounded-lg border border-white/10 bg-slate-950/35 p-2.5">
              <div className="text-[11px] uppercase tracking-wide text-slate-400">Read order</div>
              <p className="mt-2 text-sm text-slate-100">{readOrder}</p>
            </article>
            <article className="rounded-lg border border-white/10 bg-slate-950/35 p-2.5">
              <div className="text-[11px] uppercase tracking-wide text-slate-400">
                {previewModel.detailTile.label}
              </div>
              <p className="mt-2 text-sm text-slate-100">{compactText(previewModel.detailTile.value, 180)}</p>
            </article>
            <article className="rounded-lg border border-white/10 bg-slate-950/35 p-2.5">
              <div className="text-[11px] uppercase tracking-wide text-slate-400">
                {previewModel.boundaryTile.label}
              </div>
              <p className="mt-2 text-sm text-slate-100">
                {compactText(previewModel.boundaryTile.value, 180)}
              </p>
            </article>
          </div>

          <div className="mt-2.5 grid gap-2.5">
            {pilotMatrixBundle.ordered_cells.map((cell) => (
              <article
                key={cell.cell_id}
                className="rounded-lg border border-white/10 bg-slate-950/35 p-2.5"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] text-slate-200">
                    {renderPublicCellLabel(cell)}
                  </span>
                  <span className="text-[11px] text-slate-400">{cell.protocol_input_identity.display_text}</span>
                </div>
                <p className="mt-2 text-sm font-medium text-slate-100">{cell.label}</p>
                <p className="mt-1 text-sm leading-6 text-slate-300 text-clamp-3">{cell.card_takeaway}</p>
                <p className="mt-2 text-xs text-slate-500">{cell.auditability_note}</p>
              </article>
            ))}
          </div>
        </details>
      ) : null}
    </section>
  )
}
