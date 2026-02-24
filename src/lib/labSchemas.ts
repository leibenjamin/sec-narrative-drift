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
