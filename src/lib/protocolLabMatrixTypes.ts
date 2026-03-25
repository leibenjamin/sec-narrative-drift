export type ProtocolLabPilotMatrixCellRole =
  | "hero"
  | "main_comparator"
  | "secondary_comparator"
  | "control"

export type ProtocolLabPilotMatrixLaneCode = "00" | "01" | "02" | "03"

export type ProtocolLabEffortRobustnessLaneCode = "02" | "03" | "00"

export type ProtocolLabPilotMatrixStorySectionId =
  | "why_this_case_matters"
  | "consensus_findings"
  | "investor_read"
  | "disagreement_findings"
  | "protocol_read"
  | "caveat"

export type ProtocolLabPilotMatrixEvidenceRichnessTier = "baseline" | "medium" | "high"

export type ProtocolLabPilotMatrixNormalizationKind =
  | "canonical_json"
  | "recovered_noncanonical_json"

export type ProtocolLabPilotMatrixPairInfo = {
  ticker: string
  issuer_name: string
  year_from: number
  year_to: number
  form_type: string
  section_id: string
}

export type ProtocolLabPilotMatrixPilotStatus = {
  state: string
  note: string
}

export type ProtocolLabPilotMatrixComparisonPair = {
  pair_id: string
  left_cell_id: string
  right_cell_id: string
  label: string
  purpose: string
}

export type ProtocolLabPilotMatrix = {
  artifact_schema_id: "pilot_matrix_v1"
  matrix_id: string
  fixture_id: string
  pair_info: ProtocolLabPilotMatrixPairInfo
  pilot_status: ProtocolLabPilotMatrixPilotStatus
  lane_roles: Record<string, ProtocolLabPilotMatrixCellRole>
  ordered_cell_ids: string[]
  selected_default_cell_id: string
  comparison_pairs: ProtocolLabPilotMatrixComparisonPair[]
  takeaways: string[]
  caveats: string[]
  cell_paths: Record<string, string>
  review_path: string
}

export type ProtocolLabPilotMatrixEvidencePreview = {
  evidence_id: string
  year_label: string
  paragraph_id: string
  quote_text: string
  short_note: string | null
}

export type ProtocolLabPilotMatrixOutputShapeInfo = {
  contract_mode: string
  display_text: string
  canonical_structured: boolean
}

export type ProtocolLabPilotMatrixProtocolInputIdentity = {
  protocol_id: string | null
  protocol_label: string
  input_pack_id: string
  input_label: string
  display_text: string
}

export type ProtocolLabPilotMatrixNormalizationStatus = {
  kind: ProtocolLabPilotMatrixNormalizationKind
  recovered: boolean
  source_json_parseable: boolean
  recovery_boundary: string | null
  required_labels_found: string[]
  note: string
}

export type ProtocolLabPilotMatrixRawSourceRefs = {
  response_path: string
  run_manifest_path: string
}

export type ProtocolLabPilotMatrixCell = {
  artifact_schema_id: "pilot_matrix_cell_v1"
  cell_id: string
  matrix_id: string
  fixture_id: string
  label: string
  short_label: string
  role: ProtocolLabPilotMatrixCellRole
  lane_position: number
  protocol_input_identity: ProtocolLabPilotMatrixProtocolInputIdentity
  headline: string
  summary: string
  card_takeaway: string
  why_this_lane_matters: string
  output_shape_info: ProtocolLabPilotMatrixOutputShapeInfo
  evidence_richness_tier: ProtocolLabPilotMatrixEvidenceRichnessTier
  evidence_count_total: number
  auditability_note: string
  strengths: string[]
  limitations: string[]
  evidence_preview: ProtocolLabPilotMatrixEvidencePreview[]
  raw_source_refs: ProtocolLabPilotMatrixRawSourceRefs
  normalization_status: ProtocolLabPilotMatrixNormalizationStatus
}

export type ProtocolLabPilotMatrixReview = {
  artifact_schema_id: "pilot_matrix_review_v1"
  matrix_id: string
  supports: string[]
  does_not_yet_support: string[]
  why_02_is_hero: string
  why_03_is_main_comparator: string
  why_00_is_control: string
  why_01_is_secondary: string
}

export type ProtocolLabPilotMatrixStory = {
  artifact_schema_id: "pilot_matrix_story_v1"
  matrix_id: string
  fixture_id: string
  consensus_findings: string[]
  disagreement_findings: string[]
  why_this_case_matters: string
  investor_read: string
  protocol_read: string
  caveat: string
  display_priority_order: ProtocolLabPilotMatrixStorySectionId[]
}

export type ProtocolLabPilotMatrixBundle = {
  matrix: ProtocolLabPilotMatrix
  ordered_cells: ProtocolLabPilotMatrixCell[]
  cells_by_id: Record<string, ProtocolLabPilotMatrixCell>
  review: ProtocolLabPilotMatrixReview
  story: ProtocolLabPilotMatrixStory
}

export type ProtocolLabPilotMatrixRegistryItem = {
  fixture_id: string
  ticker: string
  year_from: number
  year_to: number
  matrix_path: string
  story_path: string
}

export type ProtocolLabPilotMatrixRegistry = {
  artifact_schema_id: "pilot_matrices_v1"
  version: string
  updated_at_utc: string
  items: ProtocolLabPilotMatrixRegistryItem[]
}

export type ProtocolLabStandardControlLaneAssessmentKind =
  | "strongest"
  | "meaningful_comparator"
  | "control"

export type ProtocolLabStandardControlIssuerInfo = {
  ticker: string
  issuer_name: string
}

export type ProtocolLabStandardControlValidationSnapshot = {
  response_exists: boolean
  response_non_empty: boolean
  json_parseable: boolean
  json_object: boolean
  top_level_shape_valid: boolean
  actual_top_level_keys: string[]
  raw_text_expected_key_hints: Record<string, boolean>
  blocker_codes: string[]
  notes: string[]
}

export type ProtocolLabStandardControlLaneAssessment = {
  lane_slug: string
  run_id: string
  role_label: string
  assessment: ProtocolLabStandardControlLaneAssessmentKind
  rationale: string
}

export type ProtocolLabStandardControlCanonicalSource = {
  run_id: string
  lane_slug: string
  response_path: string
  run_manifest_path: string
  expected_top_level_keys: string[]
  validation_snapshot: ProtocolLabStandardControlValidationSnapshot
}

export type ProtocolLabStandardControlWaveSummary = {
  summary: string
  strongest_lane: string
  weaker_lane: string
  control_lane: string
  bounded_claim: string
}

export type ProtocolLabStandardControlMatrix = {
  artifact_schema_id: "standard_control_matrix_v1"
  matrix_id: string
  fixture_id: string
  issuer: ProtocolLabStandardControlIssuerInfo
  pair_info: ProtocolLabPilotMatrixPairInfo
  packet_root: string
  reasoning_mode: string
  canonical_run_ids: string[]
  lane_roles: Record<string, ProtocolLabPilotMatrixCellRole>
  ordered_lane_ids: string[]
  lane_assessments: ProtocolLabStandardControlLaneAssessment[]
  canonical_sources: ProtocolLabStandardControlCanonicalSource[]
  wave_summary: ProtocolLabStandardControlWaveSummary
  caveats: string[]
  provenance_notes: string[]
}

export type ProtocolLabStandardControlSummaryIssuerRanking = {
  fixture_id: string
  issuer: ProtocolLabStandardControlIssuerInfo
  ordered_lane_ids: string[]
  ordered_run_ids: string[]
  ranking_note: string
}

export type ProtocolLabStandardControlSummaryValidationOverview = {
  overall_result: string
  passed_run_ids: string[]
  failed_run_ids: string[]
  failure_note: string
  validation_report_path: string
  raw_hint_note: string
}

export type ProtocolLabStandardControlSummary = {
  artifact_schema_id: "standard_control_summary_v1"
  summary_id: string
  packet_root: string
  reasoning_mode: string
  canonical_run_ids: string[]
  by_issuer_ranking: ProtocolLabStandardControlSummaryIssuerRanking[]
  cross_issuer_pattern_summary: string[]
  supports: string[]
  does_not_yet_support: string[]
  robustness_conclusion: {
    "02": string
    "03": string
    "00": string
  }
  validation_overview: ProtocolLabStandardControlSummaryValidationOverview
  provenance_notes: string[]
}

export type ProtocolLabStandardVsExtendedLaneComparison = {
  lane_slug: string
  stable_points: string[]
  degraded_points: string[]
  lane_order_changed: boolean
  meaningfulness_note: string
}

export type ProtocolLabStandardVsExtendedComparison = {
  artifact_schema_id: "standard_vs_extended_comparison_v1"
  comparison_id: string
  fixture_id: string
  issuer: ProtocolLabStandardControlIssuerInfo
  standard_matrix_id: string
  standard_matrix_path: string
  extended_matrix_id: string
  extended_matrix_path: string
  lane_comparisons: ProtocolLabStandardVsExtendedLaneComparison[]
  issuer_conclusion: string
  caveats: string[]
}

export type ProtocolLabStandardVsExtendedSummary = {
  artifact_schema_id: "standard_vs_extended_summary_v1"
  summary_id: string
  packet_root: string
  reasoning_mode: string
  issuer_comparison_paths: string[]
  cross_issuer_stability_patterns: string[]
  cross_issuer_degradation_patterns: string[]
  lane_order_change_summary: string
  protocol_value_under_reduced_reasoning: string
  does_not_yet_support: string[]
}

export type ProtocolLabEffortRobustnessCase = {
  artifact_schema_id: "effort_robustness_case_v1"
  artifact_id: string
  fixture_id: string
  issuer: ProtocolLabStandardControlIssuerInfo
  pair_info: ProtocolLabPilotMatrixPairInfo
  headline: string
  stable_findings: string[]
  weakened_under_standard: string[]
  lane_robustness: Record<ProtocolLabEffortRobustnessLaneCode, string>
  winner_stayed_same: boolean
  comparator_remained_meaningful: boolean
  control_remained_useful: boolean
  lane_order_materially_changed: boolean
  integrity_note: string
  caveat: string
}

export type ProtocolLabEffortRobustnessSummary = {
  artifact_schema_id: "effort_robustness_summary_v1"
  artifact_id: string
  covered_issuers: string[]
  cross_case_pattern_summary: string
  protocol_value_under_lower_effort: string
  still_should_not_claim: string
  integrity_note: string
}

export type ProtocolLabEffortRobustnessBundle = {
  case_artifact: ProtocolLabEffortRobustnessCase
  summary_artifact: ProtocolLabEffortRobustnessSummary | null
}

export type ProtocolLabSkepticCaseIssueFamily =
  | "transport/container"
  | "evidence-row integrity"
  | "analytical/content"
  | "none"

export type ProtocolLabSkepticCaseRunQualityNote = {
  run_id: string
  lane_family: "02" | "p4"
  reasoning_variant: string
  status: string
  issue_family: ProtocolLabSkepticCaseIssueFamily
  issue_type: string
  correction_needed: boolean
  changes_broad_analytical_verdict: boolean
  review_note: string
  response_path: string
  run_manifest_path: string
}

export type ProtocolLabSkepticCaseQualityNotes = {
  artifact_schema_id: "skeptic_case_quality_notes_v1"
  artifact_id: string
  fixture_id: string
  issuer: ProtocolLabStandardControlIssuerInfo
  run_notes: ProtocolLabSkepticCaseRunQualityNote[]
}

export type ProtocolLabSkepticCaseAgreementCheck = {
  broadly_agree: boolean
  note: string
}

export type ProtocolLabSkepticCaseCanonizedMatrix = {
  artifact_schema_id: "skeptic_case_canonized_matrix_v1"
  artifact_id: string
  fixture_id: string
  issuer: ProtocolLabStandardControlIssuerInfo
  pair_info: ProtocolLabPilotMatrixPairInfo
  canonical_run_ids: string[]
  finding_summary: string
  skeptic_case_role_statement: string
  agreement_snapshot: {
    "02_standard_vs_extended": ProtocolLabSkepticCaseAgreementCheck
    p4_standard_vs_extended: ProtocolLabSkepticCaseAgreementCheck
  }
  supports_visible_limited_integration: boolean
  visible_integration_note: string
  known_quality_caveats: string[]
  product_interpretation: string
  framing_note: string
  short_quality_caveat: string
  quality_note_path: string
  p1_vs_p4_summary_path: string
}

export type ProtocolLabNoveltyLedgerCanonizationStatus =
  | "canonized_as_is"
  | "canonized_with_transport_repair"
  | "canonized_with_evidence_row_correction"

export type ProtocolLabNoveltyLedgerSupportLevel =
  | "both"
  | "extended_primary_standard_compatible"
  | "standard_primary_extended_compatible"

export type ProtocolLabNoveltyLedgerEvidencePreview = {
  run_id: string
  evidence_id: string
  year_label: string
  paragraph_id: string
  quote_text: string
  short_note: string | null
}

export type ProtocolLabNoveltyLedgerModuleItem = {
  item_id: string
  label: string
  text: string
  support_level: ProtocolLabNoveltyLedgerSupportLevel
  source_run_ids: string[]
  evidence_preview: ProtocolLabNoveltyLedgerEvidencePreview[]
}

export type ProtocolLabNoveltyLedgerModuleSections = {
  fresh_2025_specifics: ProtocolLabNoveltyLedgerModuleItem[]
  intensified_or_broadened_points: ProtocolLabNoveltyLedgerModuleItem[]
  reused_framework_language: ProtocolLabNoveltyLedgerModuleItem[]
  boundary_notes: ProtocolLabNoveltyLedgerModuleItem[]
}

export type ProtocolLabNoveltyLedgerComparisonTo02 = {
  where_p4_adds_value: string
  where_02_remains_stronger: string
  why_secondary_only: string
}

export type ProtocolLabNoveltyLedgerCanonizedRun = {
  run_id: string
  reasoning_variant: string
  source_response_path: string
  source_run_manifest_path: string
  canonization_status: ProtocolLabNoveltyLedgerCanonizationStatus
  quality_note_ids: string[]
  repair_summary: string | null
}

export type ProtocolLabNoveltyLedgerCase = {
  artifact_schema_id: "p4_canonized_matrix_v1"
  artifact_id: string
  fixture_id: string
  issuer: ProtocolLabStandardControlIssuerInfo
  pair_info: ProtocolLabPilotMatrixPairInfo
  canonical_run_ids: string[]
  canonized_runs: ProtocolLabNoveltyLedgerCanonizedRun[]
  issuer_finding_summary: string
  p4_role_statement: string
  known_quality_caveats: string[]
  standard_and_extended_broadly_agree: boolean
  standard_and_extended_agreement_note: string
  suitable_for_limited_app_integration: boolean
  integration_note: string
  comparison_to_02: ProtocolLabNoveltyLedgerComparisonTo02
  module_sections: ProtocolLabNoveltyLedgerModuleSections
  quality_note_path: string
}

export type ProtocolLabNoveltyLedgerQualityNoteFamily =
  | "transport/container"
  | "evidence-row integrity"
  | "analytical/content"
  | "none"

export type ProtocolLabNoveltyLedgerQualityNote = {
  note_id: string
  issue_type: string
  affected_run_id: string
  issue_family: ProtocolLabNoveltyLedgerQualityNoteFamily
  deterministic_repair_allowed: boolean
  repair_applied_in_canonization: boolean
  changes_broad_analytical_verdict: boolean
  review_note: string
  response_path: string
  run_manifest_path: string
}

export type ProtocolLabNoveltyLedgerQualityArtifact = {
  artifact_schema_id: "p4_quality_notes_v1"
  artifact_id: string
  fixture_id: string
  issuer: ProtocolLabStandardControlIssuerInfo
  notes: ProtocolLabNoveltyLedgerQualityNote[]
}

export type ProtocolLabNoveltyLedgerSummary = {
  artifact_schema_id: "p4_canonized_summary_v1"
  artifact_id: string
  covered_issuers: string[]
  issuer_artifact_paths: string[]
  quality_note_paths: string[]
  what_p4_consistently_adds_over_02: string[]
  what_p4_still_does_not_do_as_well_as_02: string[]
  why_secondary_only: string
  overall_verdict: string
}

export type ProtocolLabNoveltyLedgerVsP1Summary = {
  artifact_schema_id: "p4_vs_p1_summary_v1"
  artifact_id: string
  covered_issuers: string[]
  hero_lane_family: string
  comparison_frame: string
  where_p4_is_stronger: string[]
  where_02_is_stronger: string[]
  bounded_decision: string
}
