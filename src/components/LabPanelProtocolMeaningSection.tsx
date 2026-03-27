import ProtocolLabPilotMatrixPanel from "./ProtocolLabPilotMatrixPanel"
import type { LabPanelPilotArtifactsState } from "./useLabPanelPilotArtifacts"

type LabPanelProtocolMeaningSectionProps = {
  pilotArtifacts: LabPanelPilotArtifactsState
}

export default function LabPanelProtocolMeaningSection({
  pilotArtifacts,
}: LabPanelProtocolMeaningSectionProps) {
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
  )
}
