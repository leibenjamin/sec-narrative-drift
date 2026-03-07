import { z } from "zod"

const URL_SCHEME_RE = /^[A-Za-z][A-Za-z0-9+.-]*:/

function hasControlChars(value: string): boolean {
  for (let index = 0; index < value.length; index += 1) {
    const codePoint = value.charCodeAt(index)
    if (codePoint <= 0x1f || codePoint === 0x7f) return true
  }
  return false
}

function isHttpsUrl(value: string): boolean {
  try {
    const parsed = new URL(value)
    return parsed.protocol === "https:"
  } catch {
    return false
  }
}

function isInternalPathLike(value: string): boolean {
  const normalized = value.trim().replace(/\\/g, "/").replace(/^\.\/+/, "")
  if (!normalized || hasControlChars(normalized)) return false
  if (URL_SCHEME_RE.test(normalized) || normalized.startsWith("//")) return false
  if (normalized.includes("..")) return false
  return (
    normalized.startsWith("/") ||
    normalized.startsWith("data/") ||
    normalized.startsWith("public/") ||
    normalized.startsWith("inputs/") ||
    normalized.startsWith("bundles/")
  )
}

const InternalPathLikeSchema = z.string().refine(isInternalPathLike, {
  message: "Must be an internal path-like value.",
})

const OptionalInternalPathLikeSchema = z.union([InternalPathLikeSchema, z.literal("")])

const HttpsUrlSchema = z.string().url().refine(isHttpsUrl, {
  message: "URL must use https.",
})

export const LabCleaningLensSchema = z.enum([
  "raw",
  "stage1_clean",
  "deboilerplated",
  "structure_aware",
])

export const LabSourceIdSchema = z.enum(["edgar", "sraf_nd"])

export const RankedItemSchema = z.object({
  label: z.string(),
  score: z.number(),
  meta: z.record(z.string(), z.unknown()).optional(),
})

export const EvidenceBlockSchema = z.object({
  year: z.number(),
  paragraph_idx: z.number(),
  snippet: z.string(),
  why: z.string(),
  highlights: z.array(z.string()).optional(),
})

export const LabMetricsSchema = z.object({
  drift_score: z.number().nullable(),
  confidence: z.number().nullable(),
  coverage: z.number().nullable(),
  warnings: z.array(z.string()),
})

export const LabProvenanceSchema = z
  .object({
    build_utc: z.string().optional(),
    git_commit: z.string().optional(),
    script_version: z.string().optional(),
    inputs: z.record(z.string(), z.string()).optional(),
    notes: z.array(z.string()).optional(),
    input_file: z.string().optional(),
    input_path: z.string().optional(),
    output_path: z.string().optional(),
    model_provider: z.string().optional(),
    model_name: z.string().optional(),
    run_label: z.string().optional(),
    focuspack_meta: z.record(z.string(), z.unknown()).optional(),
  })
  .passthrough()

export const LabArtifactsSchema = z
  .object({
    ranked_items: z.array(RankedItemSchema).optional(),
    top_risers: z.array(RankedItemSchema).optional(),
    top_fallers: z.array(RankedItemSchema).optional(),
    agreement_matrix: z.record(z.string(), z.number().nullable()).optional(),
    stats: z.record(z.string(), z.unknown()).optional(),
    notes: z.array(z.string()).optional(),
  })
  .passthrough()

export const LabOutputSchema = z.object({
  lab_schema_version: z.literal("1.0"),
  detector_id: z.string(),
  cleaning_lens: LabCleaningLensSchema,
  source_id: LabSourceIdSchema,
  ticker: z.string(),
  section: z.string(),
  year_from: z.number(),
  year_to: z.number(),
  artifacts: LabArtifactsSchema,
  evidence: z.array(EvidenceBlockSchema),
  metrics: LabMetricsSchema,
  provenance: LabProvenanceSchema,
})

const LabCaseOutputLinkSchema = z.object({
  detector_id: z.string(),
  cleaning_lens: LabCleaningLensSchema,
  source_id: LabSourceIdSchema,
  filename: z.string(),
})

const LabCaseSchema = z.object({
  ticker: z.string(),
  year_from: z.number(),
  year_to: z.number(),
  section: z.string(),
  why_interesting: z.string(),
  expected_detectors: z.array(z.string()),
  tags: z.array(z.string()).optional(),
  outputs: z.array(LabCaseOutputLinkSchema),
})

export const LabCasesRegistrySchema = z.object({
  version: z.string(),
  updated_at: z.string(),
  notes: z.array(z.string()).optional(),
  cases: z.array(LabCaseSchema),
  provenance: LabProvenanceSchema.optional(),
})

export const LabLlmCampaignSchema = z.object({
  campaign_id: z.string(),
  campaign_slug: z.string(),
  display_name: z.string(),
  input_mode: z.enum(["focuspack_v1", "full_section_v2"]).optional(),
  model_provider: z.string(),
  model_name: z.string(),
  run_label_prefix_template: z.string().optional(),
  instructions_asset: z.string().optional(),
  primary_for_runtime: z.boolean().optional(),
  compare_default: z.boolean().optional(),
  runtime_visible: z.boolean().optional(),
})

export const LabLlmCampaignsIndexSchema = z.object({
  version: z.string(),
  updated_at: z.string(),
  primary_campaign_id: z.string(),
  compare_default_campaign_id: z.string(),
  campaigns: z.array(LabLlmCampaignSchema),
  provenance: LabProvenanceSchema.optional(),
})

export const LabLlmVariantSchema = z.object({
  ticker: z.string(),
  section: z.string(),
  year_from: z.number(),
  year_to: z.number(),
  lens: LabCleaningLensSchema,
  source_id: LabSourceIdSchema,
  detector_id: z.string(),
  campaign_id: z.string(),
  campaign_slug: z.string(),
  display_name: z.string(),
  input_mode: z.enum(["focuspack_v1", "full_section_v2"]).optional(),
  runtime_visible: z.boolean().optional(),
  model_provider: z.string(),
  model_name: z.string(),
  filename: z.string(),
  expected_repo_path: z.string(),
  request_url: InternalPathLikeSchema,
  present: z.boolean(),
  valid: z.boolean(),
  run_label: z.string(),
  input_file: OptionalInternalPathLikeSchema.optional(),
  year_input_prev: OptionalInternalPathLikeSchema.optional(),
  year_input_curr: OptionalInternalPathLikeSchema.optional(),
  outline_compare_present: z.boolean().optional(),
  outline_compare_valid: z.boolean().optional(),
  outline_compare_expected_repo_path: OptionalInternalPathLikeSchema.optional(),
  outline_compare_request_url: OptionalInternalPathLikeSchema.optional(),
  outline_compare_insight_present: z.boolean().optional(),
  outline_compare_insight_valid: z.boolean().optional(),
  outline_compare_insight_expected_repo_path: OptionalInternalPathLikeSchema.optional(),
  outline_compare_insight_request_url: OptionalInternalPathLikeSchema.optional(),
  outline_research_present: z.boolean().optional(),
  outline_research_valid: z.boolean().optional(),
  outline_research_expected_repo_path: OptionalInternalPathLikeSchema.optional(),
  outline_research_request_url: OptionalInternalPathLikeSchema.optional(),
  validation_reasons: z.array(z.string()).optional(),
})

export const LabLlmVariantsIndexSchema = z.object({
  version: z.string(),
  updated_at: z.string(),
  variants: z.array(LabLlmVariantSchema),
  provenance: LabProvenanceSchema.optional(),
})

export const LabMethodTrackSchema = z.object({
  track_id: z.string(),
  track_slug: z.string(),
  kind: z.enum(["deterministic", "llm"]),
  display_name: z.string(),
  detector_ids: z.array(z.string()),
  model_provider: z.string().optional(),
  model_name: z.string().optional(),
  input_mode: z.enum(["focuspack_v1", "full_section_v2", "deterministic"]).optional(),
  primary_for_runtime: z.boolean().optional(),
  compare_default: z.boolean().optional(),
  runtime_visible: z.boolean().optional(),
})

export const LabMethodTracksIndexSchema = z.object({
  version: z.string(),
  updated_at: z.string(),
  tracks: z.array(LabMethodTrackSchema),
  provenance: LabProvenanceSchema.optional(),
})

export const LabMethodProfileOriginClaimSchema = z.object({
  title: z.string(),
  author_or_org: z.string(),
  year: z.number(),
  url: HttpsUrlSchema,
})

export const LabMethodProfileSchema = z.object({
  detector_id: z.string(),
  short_purpose: z.string(),
  canonical_usage: z.string(),
  this_app_deviation: z.string(),
  when_it_works_well: z.string(),
  failure_modes: z.array(z.string()),
  why_included_here: z.string(),
  alternatives_not_chosen: z.array(z.string()),
  current_industry_usage: z.string(),
  origin_claims: z.array(LabMethodProfileOriginClaimSchema),
})

export const LabMethodProfilesIndexSchema = z.object({
  version: z.string(),
  updated_at: z.string(),
  profiles: z.array(LabMethodProfileSchema),
  provenance: LabProvenanceSchema.optional(),
})

const OutlineChangeClassSchema = z.enum([
  "added",
  "removed",
  "moved",
  "split",
  "merged",
  "reworded",
  "intensified",
  "softened",
  "stable",
])

const LabOutlineNodeSchema = z.object({
  node_id: z.string(),
  parent_id: z.string().nullable(),
  level: z.union([z.literal(1), z.literal(2), z.literal(3)]),
  order: z.number().int().nonnegative(),
  label: z.string(),
  risk_thesis: z.string(),
  evidence_paragraph_idx: z.array(z.number().int().nonnegative()),
})

const LabOutlineAlignmentSchema = z.object({
  prev_node_id: z.string().nullable(),
  curr_node_id: z.string().nullable(),
  change_class: OutlineChangeClassSchema,
  rationale: z.string(),
  salience: z.number().min(0).max(1),
})

const LabOutlineEvidenceRefSchema = z.object({
  year: z.number().int(),
  paragraph_idx: z.number().int().nonnegative(),
})

const LabOutlineMaterialChangeSchema = z.object({
  id: z.string(),
  title: z.string(),
  change_class: z.enum([
    "added",
    "removed",
    "moved",
    "split",
    "merged",
    "reworded",
    "intensified",
    "softened",
  ]),
  salience: z.number().min(0).max(1),
  caveat: z.string(),
  evidence_refs: z.array(LabOutlineEvidenceRefSchema),
})

const LabOutlineEvidenceSchema = z.object({
  year: z.number().int(),
  paragraph_idx: z.number().int().nonnegative(),
  snippet: z.string(),
  why: z.string(),
  node_ids: z.array(z.string()),
})

const LabOutlineRiskGraphRowSchema = z.object({
  id: z.string(),
  driver: z.string(),
  exposure: z.string(),
  impact: z.string(),
  evidence_paragraph_idx: z.array(z.number().int().nonnegative()),
})

const LabOutlineChangeMechanismRowSchema = z.object({
  id: z.string(),
  mechanism: z.string(),
  transmission_channel: z.string(),
  business_effect: z.string(),
  time_horizon: z.enum(["near_term", "medium_term", "long_term"]),
  evidence_refs: z.array(LabOutlineEvidenceRefSchema),
})

const LabOutlineLimitRowSchema = z.object({
  id: z.string(),
  limitation: z.string(),
  evidence_refs: z.array(LabOutlineEvidenceRefSchema),
})

const LabOutlineInvestorRelevanceRowSchema = z.object({
  id: z.string(),
  why_it_matters: z.string(),
  evidence_refs: z.array(LabOutlineEvidenceRefSchema),
})

const LabOutlineProjectionContractSchema = z.object({
  projects_to_artifact_id: z.literal("llm_outline_compare_runtime"),
  projection_version: z.string(),
})

const LabOutlineCompareBaseSchema = z.object({
  lab_schema_version: z.literal("1.0"),
  artifact_schema_version: z.literal("1.0"),
  ticker: z.string(),
  section: z.string(),
  source_id: LabSourceIdSchema,
  cleaning_lens: LabCleaningLensSchema,
  year_from: z.number().int(),
  year_to: z.number().int(),
  outline_prev: z.array(LabOutlineNodeSchema),
  outline_curr: z.array(LabOutlineNodeSchema),
  node_alignment: z.array(LabOutlineAlignmentSchema),
  material_changes: z.array(LabOutlineMaterialChangeSchema),
  evidence_bank: z.array(LabOutlineEvidenceSchema),
  lens_divergence: z.object({
    materially_different: z.boolean(),
    summary: z.string(),
  }),
  provenance: LabProvenanceSchema,
})

export const LabOutlineCompareOutputSchema = LabOutlineCompareBaseSchema.extend({
  artifact_id: z.literal("llm_outline_compare_runtime"),
})

export const LabOutlineCompareV2OutputSchema = LabOutlineCompareBaseSchema.extend({
  artifact_id: z.literal("llm_outline_compare_structured"),
  risk_graph_prev: z.array(LabOutlineRiskGraphRowSchema),
  risk_graph_curr: z.array(LabOutlineRiskGraphRowSchema),
  change_mechanisms: z.array(LabOutlineChangeMechanismRowSchema),
  uncertainty_and_limits: z.array(LabOutlineLimitRowSchema),
  investor_relevance: z.array(LabOutlineInvestorRelevanceRowSchema),
  projection_contract: LabOutlineProjectionContractSchema,
})

const LabOutlineInsightExecutiveDigestSchema = z.object({
  summary_text: z.string(),
  audience: z.literal("investor_analyst"),
  reading_time_sec_estimate: z.number().int().positive(),
})

const LabOutlineInsightCardSchema = z.object({
  id: z.string(),
  insight_type: z.enum(["difference", "similarity"]),
  title: z.string(),
  claim: z.string(),
  why_it_matters: z.string(),
  salience: z.number().min(0).max(1),
  confidence_band: z.string(),
  evidence_refs_prev: z.array(LabOutlineEvidenceRefSchema),
  evidence_refs_curr: z.array(LabOutlineEvidenceRefSchema),
  evidence_ref_ids: z.array(z.string()),
  counterpoint_or_limit: z.string(),
})

const LabOutlineInsightEvidenceMapSchema = z.object({
  evidence_id: z.string(),
  year: z.number().int(),
  paragraph_idx: z.number().int().nonnegative(),
  snippet: z.string(),
  char_start: z.number().int().nonnegative().nullable().optional(),
  char_end: z.number().int().nonnegative().nullable().optional(),
  insight_ids: z.array(z.string()),
})

const LabOutlineInsightCoverageSchema = z.object({
  difference_count: z.number().int().nonnegative(),
  similarity_count: z.number().int().nonnegative(),
  per_year_evidence_spread: z.record(z.string(), z.number()).optional().default({}),
})

const LabOutlineInsightUiContractSchema = z.object({
  default_selected_insight_id: z.string(),
  recommended_insight_order: z.array(z.string()),
  suggested_clusters: z.array(
    z.object({
      cluster_id: z.string(),
      label: z.string(),
      insight_ids: z.array(z.string()),
    })
  ),
})

export const LabOutlineCompareInsightOutputSchema = LabOutlineCompareV2OutputSchema.extend({
  artifact_id: z.literal("llm_outline_compare_insight"),
  executive_digest: LabOutlineInsightExecutiveDigestSchema,
  insight_cards: z.array(LabOutlineInsightCardSchema),
  evidence_map: z.array(LabOutlineInsightEvidenceMapSchema),
  insight_coverage: LabOutlineInsightCoverageSchema,
  ui_contract: LabOutlineInsightUiContractSchema,
})

const LabOutlineResearchClaimSchema = z.object({
  claim: z.string(),
  source_url: HttpsUrlSchema,
  source_date: z.string(),
  support_label: z.enum(["support", "contradict", "unclear"]),
  note: z.string(),
})

export const LabOutlineResearchOutputSchema = z.object({
  lab_schema_version: z.literal("1.0"),
  artifact_schema_version: z.literal("1.0"),
  artifact_id: z.literal("llm_outline_research_v1"),
  ticker: z.string(),
  section: z.string(),
  source_id: LabSourceIdSchema,
  cleaning_lens: LabCleaningLensSchema,
  year_from: z.number().int(),
  year_to: z.number().int(),
  trigger_reasons: z.array(z.string()),
  claims: z.array(LabOutlineResearchClaimSchema),
  provenance: LabProvenanceSchema,
})


