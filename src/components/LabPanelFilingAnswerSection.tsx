import RiskNarrativeSummary from "./RiskNarrativeSummary"
import type { LabCase } from "../lib/labTypes"
import type { LabPanelOutputsState } from "./useLabPanelOutputs"

type AnalysisMode = "executive" | "deep"

type LabPanelFilingAnswerSectionProps = {
  selectedCase: LabCase
  selectedLlmCampaignA: string
  selectedLlmCampaignB: string
  selectedCampaignLabelA: string
  selectedCampaignLabelB: string
  analysisMode: AnalysisMode
  outputState: LabPanelOutputsState
}

export default function LabPanelFilingAnswerSection({
  selectedCase,
  selectedLlmCampaignA,
  selectedLlmCampaignB,
  selectedCampaignLabelA,
  selectedCampaignLabelB,
  analysisMode,
  outputState,
}: LabPanelFilingAnswerSectionProps) {
  const { outlineOutputs, structuredOutlineOutputs } = outputState

  if (!selectedLlmCampaignA && !selectedLlmCampaignB) {
    return null
  }

  return (
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
  )
}
