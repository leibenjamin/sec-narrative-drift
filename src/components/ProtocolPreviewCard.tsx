import KORestraintStrip from "./KORestraintStrip"
import { compactText } from "../lib/compactText"
import { formatPilotStatusLabel } from "../lib/protocolLabMatrixPresentation.ts"
import type { ProtocolLabPilotMatrixCell } from "../lib/protocolLabMatrixTypes.ts"
import {
  getRouteFamilyConfig,
  type RouteFamilyPreviewSupportStrategy,
} from "../lib/routeFamilyUi"
import type { LabPanelPilotArtifactsState } from "./useLabPanelPilotArtifacts"

type PreviewVariant = "integrated" | "bounded"

type PreviewTile = {
  label: string
  value: string
  tone: "neutral" | "accent" | "boundary"
}

type ProtocolPreviewViewModel = {
  title: string
  subtitle: string
  chips: string[]
  tiles: PreviewTile[]
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

function buildSupportTile(
  pilotArtifacts: LabPanelPilotArtifactsState,
  supportStrategy: RouteFamilyPreviewSupportStrategy,
  scopeNote: string
): PreviewTile {
  const { effortRobustnessBundle, noveltyLedgerArtifact } = pilotArtifacts

  if (supportStrategy === "scope_only") {
    return {
      label: "Pilot scope",
      value: compactText(scopeNote, 118),
      tone: "neutral",
    }
  }

  if (effortRobustnessBundle) {
    return {
      label: "Matched-effort check",
      value: compactText(effortRobustnessBundle.case_artifact.headline, 118),
      tone: "accent",
    }
  }

  if (noveltyLedgerArtifact) {
    return {
      label: "Fresh vs reused",
      value: compactText(noveltyLedgerArtifact.comparison_to_02.why_secondary_only, 118),
      tone: "neutral",
    }
  }

  return {
    label: "Pilot scope",
    value: compactText(scopeNote, 118),
    tone: "neutral",
  }
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
  const { pilotMatrixBundle, effortRobustnessBundle, noveltyLedgerArtifact } = pilotArtifacts
  if (!pilotMatrixBundle) return null

  const familyConfig = getRouteFamilyConfig(ticker)
  const primaryCell = getPrimaryCell(pilotMatrixBundle)
  const subtitleSource = familyConfig?.preview.subtitleSource ?? "card_takeaway"
  const rawSubtitle =
    subtitleSource === "protocol_read"
      ? pilotMatrixBundle.story.protocol_read
      : subtitleSource === "why_case_exists"
        ? pilotMatrixBundle.story.why_this_case_matters
        : primaryCell?.card_takeaway ?? pilotMatrixBundle.story.why_this_case_matters
  const supportTile = buildSupportTile(
    pilotArtifacts,
    familyConfig?.preview.supportStrategy ?? "effort_first",
    pilotMatrixBundle.matrix.pilot_status.note
  )
  const statusLabel = formatPilotStatusLabel(pilotMatrixBundle.matrix.pilot_status.state)
  const chips = [
    primaryCell ? `${renderPublicCellLabel(primaryCell)} first` : null,
    `Scope: ${statusLabel}`,
    noveltyLedgerArtifact && supportTile.label !== "Fresh vs reused"
      ? "Fresh vs reused stays secondary"
      : null,
    effortRobustnessBundle && supportTile.label !== "Matched-effort check"
      ? "Matched-effort check visible"
      : null,
  ].filter((value): value is string => Boolean(value))

  return {
    title:
      variant === "bounded"
        ? familyConfig?.preview.boundedTitle ?? "Why this bounded read stays visible"
        : familyConfig?.preview.integratedTitle ?? "Why this fixture stays visible",
    subtitle: compactText(rawSubtitle, variant === "bounded" ? 126 : 138),
    chips,
    tiles: [
      {
        label: "Case role",
        value: compactText(
          familyConfig?.preview.roleSummary ?? pilotMatrixBundle.story.why_this_case_matters,
          122
        ),
        tone: "neutral",
      },
      {
        label: "Visible reads add",
        value: compactText(pilotMatrixBundle.story.protocol_read, 122),
        tone: "accent",
      },
      {
        label: "Boundary",
        value: compactText(pilotMatrixBundle.story.caveat, 122),
        tone: "boundary",
      },
      supportTile,
    ],
    showDetailDisclosure: variant === "integrated",
    showRestraintStrip: Boolean(familyConfig?.preview.showRestraintStrip),
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
          <p className="text-[11px] uppercase tracking-[0.24em] text-amber-100">Protocol meaning</p>
          <h2 className="mt-1.5 text-lg font-semibold text-slate-50">Protocol layer unavailable</h2>
        </div>
        <p className="text-sm text-slate-100">
          The filing answer is still available above. The protocol layer did not load for this case,
          so deeper pressure-testing should rely on the audit gateway below.
        </p>
        {pilotMatrixError ? <p className="text-sm text-amber-100">{pilotMatrixError}</p> : null}
        {pilotMatrixDebugText ? (
          <p className="break-all text-[11px] text-slate-300">{pilotMatrixDebugText}</p>
        ) : null}
      </section>
    )
  }

  const primaryCell = getPrimaryCell(pilotMatrixBundle)
  const previewModel = buildPreviewModel(pilotArtifacts, ticker, variant)
  if (!previewModel) return null

  const readOrder = pilotMatrixBundle.ordered_cells.map((cell) => renderPublicCellLabel(cell)).join(" -> ")

  return (
    <section id="lab-pilot-matrix" className="space-y-3">
      <article className="rounded-[1.35rem] border border-white/10 bg-linear-to-br from-slate-950/82 via-slate-900/65 to-slate-950/40 p-3.5 shadow-[0_18px_40px_rgba(2,6,23,0.2)] sm:p-4.5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1.5">
            <p className="text-[11px] uppercase tracking-[0.24em] text-sky-100">Protocol meaning</p>
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

        <p className="mt-2.5 text-sm leading-6 text-slate-100 text-clamp-2">{previewModel.subtitle}</p>

        <div className="mt-2.5 flex flex-wrap gap-1.5 text-[11px] text-slate-300">
          {previewModel.chips.map((chip) => (
            <span
              key={chip}
              className="rounded-full border border-white/8 bg-white/4 px-2.5 py-1"
            >
              {chip}
            </span>
          ))}
        </div>

        <div className="mt-2.5 grid gap-2 sm:grid-cols-2">
          {previewModel.tiles.map((tile) => (
            <article
              key={tile.label}
              className={`rounded-2xl border p-2.5 ${getToneClasses(tile.tone)}`}
            >
              <div className="text-[10px] uppercase tracking-[0.24em] text-slate-300">{tile.label}</div>
              <p className="mt-1.5 text-sm leading-5 text-slate-100 text-clamp-3">{tile.value}</p>
            </article>
          ))}
        </div>
      </article>

      {previewModel.showDetailDisclosure ? (
        <details className="rounded-[1.1rem] border border-white/10 bg-slate-950/26 p-2.5 sm:p-3.5">
          <summary className="cursor-pointer list-none text-[13px] font-medium text-slate-100 sm:text-sm">
            Protocol detail
          </summary>
          <p className="mt-1.5 text-[11px] leading-5 text-slate-400">
            Lane roles, scope cues, and protocol-specific support stay discoverable here without taking
            over the default fold.
          </p>

          <div className="mt-2.5 grid gap-2.5 md:grid-cols-3">
            <article className="rounded-lg border border-white/10 bg-slate-950/35 p-2.5">
              <div className="text-[11px] uppercase tracking-wide text-slate-400">Read order</div>
              <p className="mt-2 text-sm text-slate-100">{readOrder}</p>
            </article>
            <article className="rounded-lg border border-white/10 bg-slate-950/35 p-2.5">
              <div className="text-[11px] uppercase tracking-wide text-slate-400">Pilot scope</div>
              <p className="mt-2 text-sm text-slate-100">
                {compactText(pilotMatrixBundle.matrix.pilot_status.note, 180)}
              </p>
            </article>
            <article className="rounded-lg border border-white/10 bg-slate-950/35 p-2.5">
              <div className="text-[11px] uppercase tracking-wide text-slate-400">Primary read</div>
              <p className="mt-2 text-sm text-slate-100">
                {primaryCell ? compactText(primaryCell.why_this_lane_matters, 180) : "Primary read not available."}
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
