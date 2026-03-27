import ProtocolLabPilotMatrixPanel from "./ProtocolLabPilotMatrixPanel"
import VisibleCaseAnswerSummary from "./VisibleCaseAnswerSummary"
import type { LabPanelPilotArtifactsState } from "./useLabPanelPilotArtifacts"

type LabPanelBoundedVisibleCaseProps = {
  pilotArtifacts: LabPanelPilotArtifactsState
}

export default function LabPanelBoundedVisibleCase({
  pilotArtifacts,
}: LabPanelBoundedVisibleCaseProps) {
  const {
    pilotMatrixBundle,
    isLoadingPilotMatrix,
    pilotMatrixError,
    pilotMatrixDebugText,
    effortRobustnessBundle,
    isLoadingEffortRobustness,
    effortRobustnessError,
    effortRobustnessDebugText,
    noveltyLedgerArtifact,
    isLoadingNoveltyLedger,
    noveltyLedgerError,
    noveltyLedgerDebugText,
    skepticCaseArtifact,
    isLoadingSkepticCase,
    skepticCaseError,
    skepticCaseDebugText,
  } = pilotArtifacts

  return (
    <section className="space-y-6">
      {pilotMatrixBundle ? (
        <VisibleCaseAnswerSummary
          bundle={pilotMatrixBundle}
          noveltyLedger={noveltyLedgerArtifact}
          effortRobustness={effortRobustnessBundle}
        />
      ) : null}

      <ProtocolLabPilotMatrixPanel
        bundle={pilotMatrixBundle}
        isLoading={isLoadingPilotMatrix}
        error={pilotMatrixError}
        debugText={pilotMatrixDebugText}
        effortRobustness={effortRobustnessBundle}
        isLoadingEffortRobustness={isLoadingEffortRobustness}
        effortRobustnessError={effortRobustnessError}
        effortRobustnessDebugText={effortRobustnessDebugText}
        noveltyLedger={noveltyLedgerArtifact}
        isLoadingNoveltyLedger={isLoadingNoveltyLedger}
        noveltyLedgerError={noveltyLedgerError}
        noveltyLedgerDebugText={noveltyLedgerDebugText}
        skepticCase={skepticCaseArtifact}
        isLoadingSkepticCase={isLoadingSkepticCase}
        skepticCaseError={skepticCaseError}
        skepticCaseDebugText={skepticCaseDebugText}
      />

      <section
        id="lab-lower-audit-unavailable"
        className="rounded-[1.25rem] border border-amber-300/20 bg-amber-400/8 p-3 text-sm text-slate-200 sm:p-4"
      >
        <div className="text-[11px] uppercase tracking-[0.24em] text-amber-100">Scope boundary</div>
        <div className="mt-3 grid gap-3 md:grid-cols-3">
          <article className="rounded-lg border border-white/10 bg-slate-950/35 p-3">
            <div className="text-[11px] uppercase tracking-wide text-slate-300">Available here</div>
            <p className="mt-2 text-sm text-slate-100">
              The bounded filing answer, protocol meaning, Fresh vs reused, and the matched-effort
              integrity surface are part of this public LLY slice.
            </p>
          </article>
          <article className="rounded-lg border border-white/10 bg-slate-950/35 p-3">
            <div className="text-[11px] uppercase tracking-wide text-slate-300">
              Intentionally not here
            </div>
            <p className="mt-2 text-sm text-slate-100">
              The full lower-audit runtime stack, broader benchmark-style claims, and the deeper
              multi-panel runtime route are not part of the public LLY surface.
            </p>
          </article>
          <article className="rounded-lg border border-white/10 bg-slate-950/35 p-3">
            <div className="text-[11px] uppercase tracking-wide text-slate-300">
              Why the stop matters
            </div>
            <p className="mt-2 text-sm text-slate-100">
              Stopping here keeps the visible policy-heavy case aligned with what the shipped
              product actually supports instead of implying audit depth that this issuer does not
              currently expose.
            </p>
          </article>
        </div>
      </section>
    </section>
  )
}
