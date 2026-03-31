import type { ComponentProps } from "react"
import LabPanelAuditTrailSection from "./LabPanelAuditTrailSection"
import ProtocolPreviewCard from "./ProtocolPreviewCard"
import RiskNarrativeSummary from "./RiskNarrativeSummary"
import type { LabCase } from "../lib/labTypes"
import type { LabPanelOutputsState } from "./useLabPanelOutputs"
import type { LabPanelPilotArtifactsState } from "./useLabPanelPilotArtifacts"

type AnalysisMode = "executive" | "deep"

type CompanyBriefingShellProps = {
  selectedCase: LabCase
  selectedLlmCampaignA: string
  selectedLlmCampaignB: string
  selectedCampaignLabelA: string
  selectedCampaignLabelB: string
  analysisMode: AnalysisMode
  outputState: LabPanelOutputsState
  pilotArtifacts: LabPanelPilotArtifactsState
  auditTrailProps: ComponentProps<typeof LabPanelAuditTrailSection>
}

export default function CompanyBriefingShell({
  selectedCase,
  selectedLlmCampaignA,
  selectedLlmCampaignB,
  selectedCampaignLabelA,
  selectedCampaignLabelB,
  analysisMode,
  outputState,
  pilotArtifacts,
  auditTrailProps,
}: CompanyBriefingShellProps) {
  const { outlineOutputs, structuredOutlineOutputs } = outputState

  return (
    <section className="space-y-4 sm:space-y-5">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.14fr)_minmax(0,0.86fr)] xl:items-start">
        <RiskNarrativeSummary
          ticker={selectedCase.ticker}
          yearFrom={selectedCase.year_from}
          yearTo={selectedCase.year_to}
          modelALabel={selectedCampaignLabelA}
          modelBLabel={selectedCampaignLabelB}
          modelARuntime={selectedLlmCampaignA ? outlineOutputs[selectedLlmCampaignA] ?? null : null}
          modelBRuntime={selectedLlmCampaignB ? outlineOutputs[selectedLlmCampaignB] ?? null : null}
          modelAStructured={
            selectedLlmCampaignA ? structuredOutlineOutputs[selectedLlmCampaignA] ?? null : null
          }
          modelBStructured={
            selectedLlmCampaignB ? structuredOutlineOutputs[selectedLlmCampaignB] ?? null : null
          }
          analysisMode={analysisMode}
        />

        <ProtocolPreviewCard pilotArtifacts={pilotArtifacts} />
      </div>

      <LabPanelAuditTrailSection {...auditTrailProps} />
    </section>
  )
}
