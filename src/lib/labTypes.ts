export type LabCleaningLens = "raw" | "stage1_clean" | "deboilerplated" | "structure_aware"

export type LabSourceId = "edgar" | "sraf_nd"

export type RankedItem = {
  label: string
  score: number
  meta?: Record<string, unknown>
}

export type EvidenceBlock = {
  year: number
  paragraph_idx: number
  snippet: string
  why: string
  highlights?: string[]
}

export type LabMetrics = {
  drift_score: number | null
  confidence: number | null
  coverage: number | null
  warnings: string[]
}

export type LabProvenance = {
  build_utc?: string
  git_commit?: string
  script_version?: string
  inputs?: Record<string, string>
  notes?: string[]
  input_file?: string
  input_path?: string
  output_path?: string
  model_provider?: string
  model_name?: string
  run_label?: string
  focuspack_meta?: Record<string, unknown>
}

export type LabLlmCampaign = {
  campaign_id: string
  campaign_slug: string
  display_name: string
  model_provider: string
  model_name: string
  run_label_prefix_template?: string
  instructions_asset?: string
  primary_for_runtime?: boolean
  compare_default?: boolean
}

export type LabLlmCampaignsIndex = {
  version: string
  updated_at: string
  primary_campaign_id: string
  compare_default_campaign_id: string
  campaigns: LabLlmCampaign[]
  provenance?: LabProvenance
}

export type LabLlmVariant = {
  ticker: string
  section: string
  year_from: number
  year_to: number
  lens: LabCleaningLens
  source_id: LabSourceId
  detector_id: string
  campaign_id: string
  campaign_slug: string
  display_name: string
  model_provider: string
  model_name: string
  filename: string
  expected_repo_path: string
  request_url: string
  present: boolean
  valid: boolean
  run_label: string
  validation_reasons?: string[]
}

export type LabLlmVariantsIndex = {
  version: string
  updated_at: string
  variants: LabLlmVariant[]
  provenance?: LabProvenance
}

export type LabMethodTrack = {
  track_id: string
  track_slug: string
  kind: "deterministic" | "llm"
  display_name: string
  detector_ids: string[]
  model_provider?: string
  model_name?: string
  primary_for_runtime?: boolean
  compare_default?: boolean
}

export type LabMethodTracksIndex = {
  version: string
  updated_at: string
  tracks: LabMethodTrack[]
  provenance?: LabProvenance
}

export type LabArtifacts = {
  ranked_items?: RankedItem[]
  top_risers?: RankedItem[]
  top_fallers?: RankedItem[]
  agreement_matrix?: Record<string, number | null>
  stats?: Record<string, unknown>
  notes?: string[]
  [key: string]: unknown
}

export type LabOutput = {
  lab_schema_version: "1.0"
  detector_id: string
  cleaning_lens: LabCleaningLens
  source_id: LabSourceId
  ticker: string
  section: string
  year_from: number
  year_to: number
  artifacts: LabArtifacts
  evidence: EvidenceBlock[]
  metrics: LabMetrics
  provenance: LabProvenance
}

export type LabCaseOutputLink = {
  detector_id: string
  cleaning_lens: LabCleaningLens
  source_id: LabSourceId
  filename: string
}

export type LabCase = {
  ticker: string
  year_from: number
  year_to: number
  section: string
  why_interesting: string
  expected_detectors: string[]
  tags?: string[]
  outputs: LabCaseOutputLink[]
}

export type LabCasesRegistry = {
  version: string
  updated_at: string
  notes?: string[]
  cases: LabCase[]
  provenance?: LabProvenance
}
