import {
  formatPilotStatusLabel,
} from "../lib/protocolLabMatrixPresentation.ts"
import type {
  ProtocolLabPilotMatrixCell,
} from "../lib/protocolLabMatrixTypes.ts"
import type { LabPanelPilotArtifactsState } from "./useLabPanelPilotArtifacts"

type PreviewTile = {
  label: string
  value: string
  tone: "neutral" | "accent" | "boundary"
}

function normalizeText(text: string): string {
  return text.replace(/\s+/g, " ").trim()
}

function compactText(text: string, maxLength = 200): string {
  const normalized = normalizeText(text)
  if (normalized.length <= maxLength) return normalized
  const clipped = normalized.slice(0, maxLength).trimEnd()
  const lastSpace = clipped.lastIndexOf(" ")
  return `${(lastSpace > 0 ? clipped.slice(0, lastSpace) : clipped).trimEnd()}...`
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

function buildSupportTile(pilotArtifacts: LabPanelPilotArtifactsState): PreviewTile | null {
  const { effortRobustnessBundle, skepticCaseArtifact, noveltyLedgerArtifact } = pilotArtifacts

  if (effortRobustnessBundle) {
    return {
      label: "Matched-effort check",
      value: compactText(effortRobustnessBundle.case_artifact.headline, 180),
      tone: "accent",
    }
  }

  if (skepticCaseArtifact) {
    return {
      label: "Matched-effort check",
      value: compactText(skepticCaseArtifact.finding_summary, 180),
      tone: "accent",
    }
  }

  if (noveltyLedgerArtifact) {
    return {
      label: "Fresh vs reused",
      value: compactText(noveltyLedgerArtifact.comparison_to_02.why_secondary_only, 180),
      tone: "neutral",
    }
  }

  return null
}

function getToneClasses(tone: PreviewTile["tone"]): string {
  if (tone === "accent") {
    return "border-sky-300/20 bg-sky-400/10"
  }
  if (tone === "boundary") {
    return "border-amber-300/20 bg-amber-400/8"
  }
  return "border-white/10 bg-slate-950/35"
}

export default function ProtocolPreviewCard({
  pilotArtifacts,
}: {
  pilotArtifacts: LabPanelPilotArtifactsState
}) {
  const {
    pilotMatrixBundle,
    isLoadingPilotMatrix,
    pilotMatrixError,
    pilotMatrixDebugText,
    effortRobustnessBundle,
    noveltyLedgerArtifact,
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
          <p className="text-[11px] uppercase tracking-[0.24em] text-amber-100">Protocol preview</p>
          <h2 className="mt-1.5 text-lg font-semibold text-slate-50">Protocol layer unavailable</h2>
        </div>
        <p className="text-sm text-slate-100">
          The filing answer is still available above. The protocol layer did not load for this case, so
          deeper pressure-testing should rely on the audit gateway below.
        </p>
        {pilotMatrixError ? <p className="text-sm text-amber-100">{pilotMatrixError}</p> : null}
        {pilotMatrixDebugText ? (
          <p className="break-all text-[11px] text-slate-300">{pilotMatrixDebugText}</p>
        ) : null}
      </section>
    )
  }

  const primaryCell = getPrimaryCell(pilotMatrixBundle)
  const supportTile = buildSupportTile(pilotArtifacts)
  const statusLabel = formatPilotStatusLabel(pilotMatrixBundle.matrix.pilot_status.state)
  const readOrder = pilotMatrixBundle.ordered_cells.map((cell) => renderPublicCellLabel(cell)).join(" -> ")
  const detailTiles: PreviewTile[] = [
    {
      label: "Why this fixture matters",
      value: compactText(pilotMatrixBundle.story.why_this_case_matters),
      tone: "neutral",
    },
    {
      label: "Visible reads add",
      value: compactText(pilotMatrixBundle.story.protocol_read),
      tone: "accent",
    },
    {
      label: "Stop / boundary",
      value: compactText(pilotMatrixBundle.story.caveat),
      tone: "boundary",
    },
  ]
  if (supportTile) {
    detailTiles.push(supportTile)
  }

  const chips = [
    primaryCell ? `${renderPublicCellLabel(primaryCell)} first` : null,
    `Scope: ${statusLabel}`,
    noveltyLedgerArtifact ? "Fresh vs reused stays secondary" : null,
    effortRobustnessBundle || skepticCaseArtifact ? "Matched-effort check visible" : null,
  ].filter((value): value is string => Boolean(value))

  return (
    <section id="lab-pilot-matrix" className="space-y-3">
      <article className="rounded-[1.35rem] border border-white/10 bg-linear-to-br from-slate-950/82 via-slate-900/65 to-slate-950/40 p-4 shadow-[0_18px_40px_rgba(2,6,23,0.2)] sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <p className="text-[11px] uppercase tracking-[0.24em] text-sky-100">Protocol preview</p>
            <h2 className="text-lg font-semibold text-slate-50 sm:text-xl">
              Why this fixture stays visible
            </h2>
          </div>
          <span className="rounded-full border border-sky-300/20 bg-sky-400/10 px-2.5 py-1 text-[11px] text-sky-100">
            Second layer
          </span>
        </div>

        <p className="mt-3 text-sm leading-6 text-slate-100 text-clamp-4">
          {primaryCell?.card_takeaway
            ? compactText(primaryCell.card_takeaway, 220)
            : compactText(pilotMatrixBundle.story.why_this_case_matters, 220)}
        </p>

        <div className="mt-3 flex flex-wrap gap-1.5 text-[11px] text-slate-200">
          {chips.map((chip) => (
            <span
              key={chip}
              className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1"
            >
              {chip}
            </span>
          ))}
        </div>
      </article>

      <div className="grid gap-2.5 sm:grid-cols-2">
        {detailTiles.map((tile) => (
          <article
            key={tile.label}
            className={`rounded-[1.05rem] border p-3 ${getToneClasses(tile.tone)}`}
          >
            <div className="text-[10px] uppercase tracking-[0.24em] text-slate-300">{tile.label}</div>
            <p className="mt-2 text-sm leading-6 text-slate-100 text-clamp-3">{tile.value}</p>
          </article>
        ))}
      </div>

      <details className="rounded-[1.1rem] border border-white/10 bg-slate-950/28 p-3 sm:p-4">
        <summary className="cursor-pointer list-none text-sm font-medium text-slate-100">
          Protocol detail
        </summary>
        <p className="mt-2 text-xs text-slate-400">
          Lane roles, scope cues, and protocol-specific support stay discoverable here without taking
          over the default fold.
        </p>

        <div className="mt-3 grid gap-3 md:grid-cols-3">
          <article className="rounded-lg border border-white/10 bg-slate-950/35 p-3">
            <div className="text-[11px] uppercase tracking-wide text-slate-400">Read order</div>
            <p className="mt-2 text-sm text-slate-100">{readOrder}</p>
          </article>
          <article className="rounded-lg border border-white/10 bg-slate-950/35 p-3">
            <div className="text-[11px] uppercase tracking-wide text-slate-400">Pilot scope</div>
            <p className="mt-2 text-sm text-slate-100">
              {compactText(pilotMatrixBundle.matrix.pilot_status.note, 180)}
            </p>
          </article>
          <article className="rounded-lg border border-white/10 bg-slate-950/35 p-3">
            <div className="text-[11px] uppercase tracking-wide text-slate-400">Primary read</div>
            <p className="mt-2 text-sm text-slate-100">
              {primaryCell ? compactText(primaryCell.why_this_lane_matters, 180) : "Primary read not available."}
            </p>
          </article>
        </div>

        <div className="mt-3 grid gap-3">
          {pilotMatrixBundle.ordered_cells.map((cell) => (
            <article
              key={cell.cell_id}
              className="rounded-lg border border-white/10 bg-slate-950/35 p-3"
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
    </section>
  )
}
