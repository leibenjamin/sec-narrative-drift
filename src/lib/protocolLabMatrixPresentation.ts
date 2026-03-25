import type { ProtocolLabPilotMatrixComparisonPair } from "./protocolLabMatrixTypes.ts"

const PILOT_STATUS_LABELS: Record<string, string> = {
  pilot_active_two_case_slice: "Bounded case view",
  pilot_active_skeptic_case_slice: "Bounded restraint view",
  loading: "Loading",
  unavailable: "Unavailable",
}

function titleCaseFromSnake(value: string): string {
  return value
    .split("_")
    .filter((part) => part.length > 0)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ")
}

export function formatPilotStatusLabel(state: string | null | undefined): string {
  if (!state) return PILOT_STATUS_LABELS.unavailable
  return PILOT_STATUS_LABELS[state] ?? titleCaseFromSnake(state)
}

export function formatPilotComparisonPurpose(pair: ProtocolLabPilotMatrixComparisonPair): string {
  if (pair.pair_id === "00_to_02_control_vs_hero") {
    return "Tests structure versus the control on the same tagged packet."
  }
  if (pair.pair_id === "01_to_02_input_treatment") {
    return "Tests filtered reuse versus the tagged packet under P1."
  }
  if (pair.pair_id === "02_to_03_protocol_shift") {
    return "Tests whether P2 changes the read on the same tagged packet."
  }
  return pair.purpose
}
