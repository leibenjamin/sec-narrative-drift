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
