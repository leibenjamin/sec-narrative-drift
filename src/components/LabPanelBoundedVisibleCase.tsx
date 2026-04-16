import LLYStopStrip from "./LLYStopStrip"
import ProtocolPreviewCard from "./ProtocolPreviewCard"
import VisibleCaseAnswerSummary from "./VisibleCaseAnswerSummary"
import type { LabPanelPilotArtifactsState } from "./useLabPanelPilotArtifacts"

type LabPanelBoundedVisibleCaseProps = {
  ticker: string
  pilotArtifacts: LabPanelPilotArtifactsState
}

export default function LabPanelBoundedVisibleCase({
  ticker,
  pilotArtifacts,
}: LabPanelBoundedVisibleCaseProps) {
  const { pilotMatrixBundle, effortRobustnessBundle, noveltyLedgerArtifact } = pilotArtifacts

  return (
    <section className="space-y-4 sm:space-y-5">
      {pilotMatrixBundle ? (
        <VisibleCaseAnswerSummary ticker={ticker} bundle={pilotMatrixBundle} />
      ) : null}

      {ticker === "LLY" && pilotMatrixBundle ? (
        <LLYStopStrip
          bundle={pilotMatrixBundle}
          noveltyLedger={noveltyLedgerArtifact}
          effortRobustness={effortRobustnessBundle}
        />
      ) : null}

      <ProtocolPreviewCard
        pilotArtifacts={pilotArtifacts}
        ticker={ticker}
        variant="bounded"
      />
    </section>
  )
}
