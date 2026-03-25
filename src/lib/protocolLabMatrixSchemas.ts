import { z } from "zod"

const URL_SCHEME_RE = /^[A-Za-z][A-Za-z0-9+.-]*:/

function hasControlChars(value: string): boolean {
  for (let index = 0; index < value.length; index += 1) {
    const codePoint = value.charCodeAt(index)
    if (codePoint <= 0x1f || codePoint === 0x7f) return true
  }
  return false
}

function isRepoPathLike(value: string): boolean {
  const normalized = value.trim().replace(/\\/g, "/").replace(/^\.\/+/, "")
  if (!normalized || hasControlChars(normalized)) return false
  if (URL_SCHEME_RE.test(normalized) || normalized.startsWith("//")) return false
  if (normalized.includes("..")) return false
  return (
    normalized.startsWith("/") ||
    normalized.startsWith("data/") ||
    normalized.startsWith("public/") ||
    normalized.startsWith("wave") ||
    normalized.startsWith("reports/") ||
    normalized.startsWith("docs/") ||
    normalized.startsWith("src/")
  )
}

const RepoPathLikeSchema = z.string().refine(isRepoPathLike, {
  message: "Must be a repo-relative or app-internal path-like value.",
})

const StorySectionIdSchema = z.enum([
  "why_this_case_matters",
  "consensus_findings",
  "investor_read",
  "disagreement_findings",
  "protocol_read",
  "caveat",
])

const REQUIRED_STORY_SECTION_IDS = StorySectionIdSchema.options

export const ProtocolLabPilotMatrixRoleSchema = z.enum([
  "hero",
  "main_comparator",
  "secondary_comparator",
  "control",
])

export const ProtocolLabPilotMatrixLaneCodeSchema = z.enum(["00", "01", "02", "03"])

export const ProtocolLabEffortRobustnessLaneCodeSchema = z.enum(["02", "03", "00"])

export const ProtocolLabPilotMatrixEvidenceRichnessTierSchema = z.enum([
  "baseline",
  "medium",
  "high",
])

export const ProtocolLabPilotMatrixSchema = z.object({
  artifact_schema_id: z.literal("pilot_matrix_v1"),
  matrix_id: z.string().min(1),
  fixture_id: z.string().min(1),
  pair_info: z.object({
    ticker: z.string().min(1),
    issuer_name: z.string().min(1),
    year_from: z.number().int(),
    year_to: z.number().int(),
    form_type: z.string().min(1),
    section_id: z.string().min(1),
  }),
  pilot_status: z.object({
    state: z.string().min(1),
    note: z.string().min(1),
  }),
  lane_roles: z.record(z.string(), ProtocolLabPilotMatrixRoleSchema),
  ordered_cell_ids: z.array(z.string().min(1)).min(1),
  selected_default_cell_id: z.string().min(1),
  comparison_pairs: z
    .array(
      z.object({
        pair_id: z.string().min(1),
        left_cell_id: z.string().min(1),
        right_cell_id: z.string().min(1),
        label: z.string().min(1),
        purpose: z.string().min(1),
      })
    ),
  takeaways: z.array(z.string().min(1)).min(1),
  caveats: z.array(z.string().min(1)).min(1),
  cell_paths: z.record(z.string(), RepoPathLikeSchema),
  review_path: RepoPathLikeSchema,
})

export const ProtocolLabPilotMatrixCellSchema = z.object({
  artifact_schema_id: z.literal("pilot_matrix_cell_v1"),
  cell_id: z.string().min(1),
  matrix_id: z.string().min(1),
  fixture_id: z.string().min(1),
  label: z.string().min(1),
  short_label: z.string().min(1),
  role: ProtocolLabPilotMatrixRoleSchema,
  lane_position: z.number().int().nonnegative(),
  protocol_input_identity: z.object({
    protocol_id: z.union([z.string().min(1), z.null()]),
    protocol_label: z.string().min(1),
    input_pack_id: z.string().min(1),
    input_label: z.string().min(1),
    display_text: z.string().min(1),
  }),
  headline: z.string().min(1),
  summary: z.string().min(1),
  card_takeaway: z.string().min(1),
  why_this_lane_matters: z.string().min(1),
  output_shape_info: z.object({
    contract_mode: z.string().min(1),
    display_text: z.string().min(1),
    canonical_structured: z.boolean(),
  }),
  evidence_richness_tier: ProtocolLabPilotMatrixEvidenceRichnessTierSchema,
  evidence_count_total: z.number().int().nonnegative(),
  auditability_note: z.string().min(1),
  strengths: z.array(z.string().min(1)).min(1),
  limitations: z.array(z.string().min(1)).min(1),
  evidence_preview: z.array(
    z.object({
      evidence_id: z.string().min(1),
      year_label: z.string().min(1),
      paragraph_id: z.string(),
      quote_text: z.string().min(1),
      short_note: z.union([z.string(), z.null()]),
    })
  ),
  raw_source_refs: z.object({
    response_path: RepoPathLikeSchema,
    run_manifest_path: RepoPathLikeSchema,
  }),
  normalization_status: z.object({
    kind: z.enum(["canonical_json", "recovered_noncanonical_json"]),
    recovered: z.boolean(),
    source_json_parseable: z.boolean(),
    recovery_boundary: z.union([z.string().min(1), z.null()]),
    required_labels_found: z.array(z.string().min(1)),
    note: z.string().min(1),
  }),
})

export const ProtocolLabPilotMatrixReviewSchema = z.object({
  artifact_schema_id: z.literal("pilot_matrix_review_v1"),
  matrix_id: z.string().min(1),
  supports: z.array(z.string().min(1)).min(1),
  does_not_yet_support: z.array(z.string().min(1)).min(1),
  why_02_is_hero: z.string().min(1),
  why_03_is_main_comparator: z.string().min(1),
  why_00_is_control: z.string().min(1),
  why_01_is_secondary: z.string().min(1),
})

export const ProtocolLabPilotMatrixStorySchema = z.object({
  artifact_schema_id: z.literal("pilot_matrix_story_v1"),
  matrix_id: z.string().min(1),
  fixture_id: z.string().min(1),
  consensus_findings: z.array(z.string().min(1)).min(3).max(5),
  disagreement_findings: z.array(z.string().min(1)).min(2).max(4),
  why_this_case_matters: z.string().min(1),
  investor_read: z.string().min(1),
  protocol_read: z.string().min(1),
  caveat: z.string().min(1),
  display_priority_order: z
    .array(StorySectionIdSchema)
    .length(REQUIRED_STORY_SECTION_IDS.length)
    .superRefine((value, ctx) => {
      const uniqueValues = new Set(value)
      if (uniqueValues.size !== value.length) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "display_priority_order must not repeat section ids.",
        })
      }

      for (const requiredId of REQUIRED_STORY_SECTION_IDS) {
        if (!uniqueValues.has(requiredId)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `display_priority_order is missing required section: ${requiredId}.`,
          })
        }
      }
    }),
})

export const ProtocolLabPilotMatrixRegistryItemSchema = z.object({
  fixture_id: z.string().min(1),
  ticker: z.string().min(1),
  year_from: z.number().int(),
  year_to: z.number().int(),
  matrix_path: RepoPathLikeSchema,
  story_path: RepoPathLikeSchema,
})

export const ProtocolLabPilotMatrixRegistrySchema = z.object({
  artifact_schema_id: z.literal("pilot_matrices_v1"),
  version: z.string().min(1),
  updated_at_utc: z.string().min(1),
  items: z.array(ProtocolLabPilotMatrixRegistryItemSchema).min(1),
})

export const ProtocolLabStandardControlLaneAssessmentKindSchema = z.enum([
  "strongest",
  "meaningful_comparator",
  "control",
])

export const ProtocolLabStandardControlIssuerInfoSchema = z.object({
  ticker: z.string().min(1),
  issuer_name: z.string().min(1),
})

export const ProtocolLabStandardControlValidationSnapshotSchema = z.object({
  response_exists: z.boolean(),
  response_non_empty: z.boolean(),
  json_parseable: z.boolean(),
  json_object: z.boolean(),
  top_level_shape_valid: z.boolean(),
  actual_top_level_keys: z.array(z.string().min(1)),
  raw_text_expected_key_hints: z.record(z.string(), z.boolean()),
  blocker_codes: z.array(z.string().min(1)),
  notes: z.array(z.string().min(1)),
})

export const ProtocolLabStandardControlLaneAssessmentSchema = z.object({
  lane_slug: z.string().min(1),
  run_id: z.string().min(1),
  role_label: z.string().min(1),
  assessment: ProtocolLabStandardControlLaneAssessmentKindSchema,
  rationale: z.string().min(1),
})

export const ProtocolLabStandardControlCanonicalSourceSchema = z.object({
  run_id: z.string().min(1),
  lane_slug: z.string().min(1),
  response_path: RepoPathLikeSchema,
  run_manifest_path: RepoPathLikeSchema,
  expected_top_level_keys: z.array(z.string().min(1)).min(1),
  validation_snapshot: ProtocolLabStandardControlValidationSnapshotSchema,
})

export const ProtocolLabStandardControlWaveSummarySchema = z.object({
  summary: z.string().min(1),
  strongest_lane: z.string().min(1),
  weaker_lane: z.string().min(1),
  control_lane: z.string().min(1),
  bounded_claim: z.string().min(1),
})

export const ProtocolLabStandardControlMatrixSchema = z.object({
  artifact_schema_id: z.literal("standard_control_matrix_v1"),
  matrix_id: z.string().min(1),
  fixture_id: z.string().min(1),
  issuer: ProtocolLabStandardControlIssuerInfoSchema,
  pair_info: ProtocolLabPilotMatrixSchema.shape.pair_info,
  packet_root: z.string().min(1),
  reasoning_mode: z.string().min(1),
  canonical_run_ids: z.array(z.string().min(1)).min(1),
  lane_roles: z.record(z.string(), ProtocolLabPilotMatrixRoleSchema),
  ordered_lane_ids: z.array(z.string().min(1)).min(1),
  lane_assessments: z.array(ProtocolLabStandardControlLaneAssessmentSchema).min(1),
  canonical_sources: z.array(ProtocolLabStandardControlCanonicalSourceSchema).min(1),
  wave_summary: ProtocolLabStandardControlWaveSummarySchema,
  caveats: z.array(z.string().min(1)).min(1),
  provenance_notes: z.array(z.string().min(1)).min(1),
})

export const ProtocolLabStandardControlSummaryIssuerRankingSchema = z.object({
  fixture_id: z.string().min(1),
  issuer: ProtocolLabStandardControlIssuerInfoSchema,
  ordered_lane_ids: z.array(z.string().min(1)).min(1),
  ordered_run_ids: z.array(z.string().min(1)).min(1),
  ranking_note: z.string().min(1),
})

export const ProtocolLabStandardControlSummaryValidationOverviewSchema = z.object({
  overall_result: z.string().min(1),
  passed_run_ids: z.array(z.string().min(1)),
  failed_run_ids: z.array(z.string().min(1)),
  failure_note: z.string().min(1),
  validation_report_path: RepoPathLikeSchema,
  raw_hint_note: z.string().min(1),
})

export const ProtocolLabStandardControlSummarySchema = z.object({
  artifact_schema_id: z.literal("standard_control_summary_v1"),
  summary_id: z.string().min(1),
  packet_root: z.string().min(1),
  reasoning_mode: z.string().min(1),
  canonical_run_ids: z.array(z.string().min(1)).min(1),
  by_issuer_ranking: z.array(ProtocolLabStandardControlSummaryIssuerRankingSchema).min(1),
  cross_issuer_pattern_summary: z.array(z.string().min(1)).min(1),
  supports: z.array(z.string().min(1)).min(1),
  does_not_yet_support: z.array(z.string().min(1)).min(1),
  robustness_conclusion: z.object({
    "02": z.string().min(1),
    "03": z.string().min(1),
    "00": z.string().min(1),
  }),
  validation_overview: ProtocolLabStandardControlSummaryValidationOverviewSchema,
  provenance_notes: z.array(z.string().min(1)).min(1),
})

export const ProtocolLabStandardVsExtendedLaneComparisonSchema = z.object({
  lane_slug: z.string().min(1),
  stable_points: z.array(z.string().min(1)).min(1),
  degraded_points: z.array(z.string().min(1)).min(1),
  lane_order_changed: z.boolean(),
  meaningfulness_note: z.string().min(1),
})

export const ProtocolLabStandardVsExtendedComparisonSchema = z.object({
  artifact_schema_id: z.literal("standard_vs_extended_comparison_v1"),
  comparison_id: z.string().min(1),
  fixture_id: z.string().min(1),
  issuer: ProtocolLabStandardControlIssuerInfoSchema,
  standard_matrix_id: z.string().min(1),
  standard_matrix_path: RepoPathLikeSchema,
  extended_matrix_id: z.string().min(1),
  extended_matrix_path: RepoPathLikeSchema,
  lane_comparisons: z.array(ProtocolLabStandardVsExtendedLaneComparisonSchema).min(1),
  issuer_conclusion: z.string().min(1),
  caveats: z.array(z.string().min(1)).min(1),
})

export const ProtocolLabStandardVsExtendedSummarySchema = z.object({
  artifact_schema_id: z.literal("standard_vs_extended_summary_v1"),
  summary_id: z.string().min(1),
  packet_root: z.string().min(1),
  reasoning_mode: z.string().min(1),
  issuer_comparison_paths: z.array(RepoPathLikeSchema).min(1),
  cross_issuer_stability_patterns: z.array(z.string().min(1)).min(1),
  cross_issuer_degradation_patterns: z.array(z.string().min(1)).min(1),
  lane_order_change_summary: z.string().min(1),
  protocol_value_under_reduced_reasoning: z.string().min(1),
  does_not_yet_support: z.array(z.string().min(1)).min(1),
})

export const ProtocolLabEffortRobustnessCaseSchema = z.object({
  artifact_schema_id: z.literal("effort_robustness_case_v1"),
  artifact_id: z.string().min(1),
  fixture_id: z.string().min(1),
  issuer: ProtocolLabStandardControlIssuerInfoSchema,
  pair_info: ProtocolLabPilotMatrixSchema.shape.pair_info,
  headline: z.string().min(1),
  stable_findings: z.array(z.string().min(1)).min(1),
  weakened_under_standard: z.array(z.string().min(1)).min(1),
  lane_robustness: z.object({
    "02": z.string().min(1),
    "03": z.string().min(1),
    "00": z.string().min(1),
  }),
  winner_stayed_same: z.boolean(),
  comparator_remained_meaningful: z.boolean(),
  control_remained_useful: z.boolean(),
  lane_order_materially_changed: z.boolean(),
  integrity_note: z.string().min(1),
  caveat: z.string().min(1),
})

export const ProtocolLabEffortRobustnessSummarySchema = z.object({
  artifact_schema_id: z.literal("effort_robustness_summary_v1"),
  artifact_id: z.string().min(1),
  covered_issuers: z.array(z.string().min(1)).length(2),
  cross_case_pattern_summary: z.string().min(1),
  protocol_value_under_lower_effort: z.string().min(1),
  still_should_not_claim: z.string().min(1),
  integrity_note: z.string().min(1),
})

export const ProtocolLabSkepticCaseIssueFamilySchema = z.enum([
  "transport/container",
  "evidence-row integrity",
  "analytical/content",
  "none",
])

export const ProtocolLabSkepticCaseRunQualityNoteSchema = z.object({
  run_id: z.string().min(1),
  lane_family: z.enum(["02", "p4"]),
  reasoning_variant: z.string().min(1),
  status: z.string().min(1),
  issue_family: ProtocolLabSkepticCaseIssueFamilySchema,
  issue_type: z.string().min(1),
  correction_needed: z.boolean(),
  changes_broad_analytical_verdict: z.boolean(),
  review_note: z.string().min(1),
  response_path: RepoPathLikeSchema,
  run_manifest_path: RepoPathLikeSchema,
})

export const ProtocolLabSkepticCaseQualityNotesSchema = z.object({
  artifact_schema_id: z.literal("skeptic_case_quality_notes_v1"),
  artifact_id: z.string().min(1),
  fixture_id: z.string().min(1),
  issuer: ProtocolLabStandardControlIssuerInfoSchema,
  run_notes: z.array(ProtocolLabSkepticCaseRunQualityNoteSchema).min(1),
})

export const ProtocolLabSkepticCaseAgreementCheckSchema = z.object({
  broadly_agree: z.boolean(),
  note: z.string().min(1),
})

export const ProtocolLabSkepticCaseCanonizedMatrixSchema = z.object({
  artifact_schema_id: z.literal("skeptic_case_canonized_matrix_v1"),
  artifact_id: z.string().min(1),
  fixture_id: z.string().min(1),
  issuer: ProtocolLabStandardControlIssuerInfoSchema,
  pair_info: ProtocolLabPilotMatrixSchema.shape.pair_info,
  canonical_run_ids: z.array(z.string().min(1)).length(4),
  finding_summary: z.string().min(1),
  skeptic_case_role_statement: z.string().min(1),
  agreement_snapshot: z.object({
    "02_standard_vs_extended": ProtocolLabSkepticCaseAgreementCheckSchema,
    p4_standard_vs_extended: ProtocolLabSkepticCaseAgreementCheckSchema,
  }),
  supports_visible_limited_integration: z.boolean(),
  visible_integration_note: z.string().min(1),
  known_quality_caveats: z.array(z.string().min(1)).min(1),
  product_interpretation: z.string().min(1),
  framing_note: z.string().min(1),
  short_quality_caveat: z.string().min(1),
  quality_note_path: RepoPathLikeSchema,
  p1_vs_p4_summary_path: RepoPathLikeSchema,
})

export const ProtocolLabNoveltyLedgerCanonizationStatusSchema = z.enum([
  "canonized_as_is",
  "canonized_with_transport_repair",
  "canonized_with_evidence_row_correction",
])

export const ProtocolLabNoveltyLedgerSupportLevelSchema = z.enum([
  "both",
  "extended_primary_standard_compatible",
  "standard_primary_extended_compatible",
])

export const ProtocolLabNoveltyLedgerEvidencePreviewSchema = z.object({
  run_id: z.string().min(1),
  evidence_id: z.string().min(1),
  year_label: z.string().min(1),
  paragraph_id: z.string().min(1),
  quote_text: z.string().min(1),
  short_note: z.union([z.string().min(1), z.null()]),
})

export const ProtocolLabNoveltyLedgerModuleItemSchema = z.object({
  item_id: z.string().min(1),
  label: z.string().min(1),
  text: z.string().min(1),
  support_level: ProtocolLabNoveltyLedgerSupportLevelSchema,
  source_run_ids: z.array(z.string().min(1)).min(1),
  evidence_preview: z.array(ProtocolLabNoveltyLedgerEvidencePreviewSchema).min(1),
})

export const ProtocolLabNoveltyLedgerModuleSectionsSchema = z.object({
  fresh_2025_specifics: z.array(ProtocolLabNoveltyLedgerModuleItemSchema),
  intensified_or_broadened_points: z.array(ProtocolLabNoveltyLedgerModuleItemSchema),
  reused_framework_language: z.array(ProtocolLabNoveltyLedgerModuleItemSchema),
  boundary_notes: z.array(ProtocolLabNoveltyLedgerModuleItemSchema),
})

export const ProtocolLabNoveltyLedgerComparisonTo02Schema = z.object({
  where_p4_adds_value: z.string().min(1),
  where_02_remains_stronger: z.string().min(1),
  why_secondary_only: z.string().min(1),
})

export const ProtocolLabNoveltyLedgerCanonizedRunSchema = z.object({
  run_id: z.string().min(1),
  reasoning_variant: z.string().min(1),
  source_response_path: RepoPathLikeSchema,
  source_run_manifest_path: RepoPathLikeSchema,
  canonization_status: ProtocolLabNoveltyLedgerCanonizationStatusSchema,
  quality_note_ids: z.array(z.string().min(1)),
  repair_summary: z.union([z.string().min(1), z.null()]),
})

export const ProtocolLabNoveltyLedgerCaseSchema = z.object({
  artifact_schema_id: z.literal("p4_canonized_matrix_v1"),
  artifact_id: z.string().min(1),
  fixture_id: z.string().min(1),
  issuer: ProtocolLabStandardControlIssuerInfoSchema,
  pair_info: ProtocolLabPilotMatrixSchema.shape.pair_info,
  canonical_run_ids: z.array(z.string().min(1)).length(2),
  canonized_runs: z.array(ProtocolLabNoveltyLedgerCanonizedRunSchema).length(2),
  issuer_finding_summary: z.string().min(1),
  p4_role_statement: z.string().min(1),
  known_quality_caveats: z.array(z.string().min(1)).min(1),
  standard_and_extended_broadly_agree: z.boolean(),
  standard_and_extended_agreement_note: z.string().min(1),
  suitable_for_limited_app_integration: z.boolean(),
  integration_note: z.string().min(1),
  comparison_to_02: ProtocolLabNoveltyLedgerComparisonTo02Schema,
  module_sections: ProtocolLabNoveltyLedgerModuleSectionsSchema,
  quality_note_path: RepoPathLikeSchema,
})

export const ProtocolLabNoveltyLedgerQualityNoteFamilySchema = z.enum([
  "transport/container",
  "evidence-row integrity",
  "analytical/content",
  "none",
])

export const ProtocolLabNoveltyLedgerQualityNoteSchema = z.object({
  note_id: z.string().min(1),
  issue_type: z.string().min(1),
  affected_run_id: z.string().min(1),
  issue_family: ProtocolLabNoveltyLedgerQualityNoteFamilySchema,
  deterministic_repair_allowed: z.boolean(),
  repair_applied_in_canonization: z.boolean(),
  changes_broad_analytical_verdict: z.boolean(),
  review_note: z.string().min(1),
  response_path: RepoPathLikeSchema,
  run_manifest_path: RepoPathLikeSchema,
})

export const ProtocolLabNoveltyLedgerQualityArtifactSchema = z.object({
  artifact_schema_id: z.literal("p4_quality_notes_v1"),
  artifact_id: z.string().min(1),
  fixture_id: z.string().min(1),
  issuer: ProtocolLabStandardControlIssuerInfoSchema,
  notes: z.array(ProtocolLabNoveltyLedgerQualityNoteSchema).min(1),
})

export const ProtocolLabNoveltyLedgerSummarySchema = z.object({
  artifact_schema_id: z.literal("p4_canonized_summary_v1"),
  artifact_id: z.string().min(1),
  covered_issuers: z.array(z.string().min(1)).min(1),
  issuer_artifact_paths: z.array(RepoPathLikeSchema).min(1),
  quality_note_paths: z.array(RepoPathLikeSchema).min(1),
  what_p4_consistently_adds_over_02: z.array(z.string().min(1)).min(1),
  what_p4_still_does_not_do_as_well_as_02: z.array(z.string().min(1)).min(1),
  why_secondary_only: z.string().min(1),
  overall_verdict: z.string().min(1),
})

export const ProtocolLabNoveltyLedgerVsP1SummarySchema = z.object({
  artifact_schema_id: z.literal("p4_vs_p1_summary_v1"),
  artifact_id: z.string().min(1),
  covered_issuers: z.array(z.string().min(1)).min(1),
  hero_lane_family: z.string().min(1),
  comparison_frame: z.string().min(1),
  where_p4_is_stronger: z.array(z.string().min(1)).min(1),
  where_02_is_stronger: z.array(z.string().min(1)).min(1),
  bounded_decision: z.string().min(1),
})
