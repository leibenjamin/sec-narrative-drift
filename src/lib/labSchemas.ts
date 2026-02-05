import { z } from "zod"

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
    build_utc: z.string(),
    git_commit: z.string(),
    script_version: z.string(),
    inputs: z.record(z.string(), z.string()),
    notes: z.array(z.string()).optional(),
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
