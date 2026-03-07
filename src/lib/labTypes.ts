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
  input_mode?: "focuspack_v1" | "full_section_v2"
  model_provider: string
  model_name: string
  run_label_prefix_template?: string
  instructions_asset?: string
  primary_for_runtime?: boolean
  compare_default?: boolean
  runtime_visible?: boolean
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
  input_mode?: "focuspack_v1" | "full_section_v2"
  runtime_visible?: boolean
  model_provider: string
  model_name: string
  filename: string
  expected_repo_path: string
  request_url: string
  present: boolean
  valid: boolean
  run_label: string
  input_file?: string
  year_input_prev?: string
  year_input_curr?: string
  outline_compare_present?: boolean
  outline_compare_valid?: boolean
  outline_compare_expected_repo_path?: string
  outline_compare_request_url?: string
  outline_compare_insight_present?: boolean
  outline_compare_insight_valid?: boolean
  outline_compare_insight_expected_repo_path?: string
  outline_compare_insight_request_url?: string
  outline_research_present?: boolean
  outline_research_valid?: boolean
  outline_research_expected_repo_path?: string
  outline_research_request_url?: string
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
  input_mode?: "focuspack_v1" | "full_section_v2" | "deterministic"
  primary_for_runtime?: boolean
  compare_default?: boolean
  runtime_visible?: boolean
}

export type LabMethodTracksIndex = {
  version: string
  updated_at: string
  tracks: LabMethodTrack[]
  provenance?: LabProvenance
}

export type LabMethodProfileOriginClaim = {
  title: string
  author_or_org: string
  year: number
  url: string
}

export type LabMethodProfile = {
  detector_id: string
  short_purpose: string
  canonical_usage: string
  this_app_deviation: string
  when_it_works_well: string
  failure_modes: string[]
  why_included_here: string
  alternatives_not_chosen: string[]
  current_industry_usage: string
  origin_claims: LabMethodProfileOriginClaim[]
}

export type LabMethodProfilesIndex = {
  version: string
  updated_at: string
  profiles: LabMethodProfile[]
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

export type OutlineChangeClass =
  | "added"
  | "removed"
  | "moved"
  | "split"
  | "merged"
  | "reworded"
  | "intensified"
  | "softened"
  | "stable"

export type LabOutlineNode = {
  node_id: string
  parent_id: string | null
  level: 1 | 2 | 3
  order: number
  label: string
  risk_thesis: string
  evidence_paragraph_idx: number[]
}

export type LabOutlineAlignment = {
  prev_node_id: string | null
  curr_node_id: string | null
  change_class: OutlineChangeClass
  rationale: string
  salience: number
}

export type LabOutlineEvidenceRef = {
  year: number
  paragraph_idx: number
}

export type LabOutlineMaterialChange = {
  id: string
  title: string
  change_class: Exclude<OutlineChangeClass, "stable">
  salience: number
  caveat: string
  evidence_refs: LabOutlineEvidenceRef[]
}

export type LabOutlineEvidence = {
  year: number
  paragraph_idx: number
  snippet: string
  why: string
  node_ids: string[]
}

export type LabOutlineRiskGraphRow = {
  id: string
  driver: string
  exposure: string
  impact: string
  evidence_paragraph_idx: number[]
}

export type LabOutlineChangeMechanismRow = {
  id: string
  mechanism: string
  transmission_channel: string
  business_effect: string
  time_horizon: "near_term" | "medium_term" | "long_term"
  evidence_refs: LabOutlineEvidenceRef[]
}

export type LabOutlineLimitRow = {
  id: string
  limitation: string
  evidence_refs: LabOutlineEvidenceRef[]
}

export type LabOutlineInvestorRelevanceRow = {
  id: string
  why_it_matters: string
  evidence_refs: LabOutlineEvidenceRef[]
}

export type LabOutlineCompareOutput = {
  lab_schema_version: "1.0"
  artifact_schema_version: "1.0"
  artifact_id: "llm_outline_compare_runtime"
  ticker: string
  section: string
  source_id: LabSourceId
  cleaning_lens: LabCleaningLens
  year_from: number
  year_to: number
  outline_prev: LabOutlineNode[]
  outline_curr: LabOutlineNode[]
  node_alignment: LabOutlineAlignment[]
  material_changes: LabOutlineMaterialChange[]
  evidence_bank: LabOutlineEvidence[]
  lens_divergence: {
    materially_different: boolean
    summary: string
  }
  provenance: LabProvenance
}

export type LabOutlineCompareV2Output = {
  lab_schema_version: "1.0"
  artifact_schema_version: "1.0"
  artifact_id: "llm_outline_compare_structured"
  ticker: string
  section: string
  source_id: LabSourceId
  cleaning_lens: LabCleaningLens
  year_from: number
  year_to: number
  outline_prev: LabOutlineNode[]
  outline_curr: LabOutlineNode[]
  node_alignment: LabOutlineAlignment[]
  material_changes: LabOutlineMaterialChange[]
  evidence_bank: LabOutlineEvidence[]
  lens_divergence: {
    materially_different: boolean
    summary: string
  }
  risk_graph_prev: LabOutlineRiskGraphRow[]
  risk_graph_curr: LabOutlineRiskGraphRow[]
  change_mechanisms: LabOutlineChangeMechanismRow[]
  uncertainty_and_limits: LabOutlineLimitRow[]
  investor_relevance: LabOutlineInvestorRelevanceRow[]
  projection_contract: {
    projects_to_artifact_id: "llm_outline_compare_runtime"
    projection_version: string
  }
  provenance: LabProvenance
}

export type LabOutlineInsightExecutiveDigest = {
  summary_text: string
  audience: "investor_analyst"
  reading_time_sec_estimate: number
}

export type LabOutlineInsightType = "difference" | "similarity"

export type LabOutlineInsightCard = {
  id: string
  insight_type: LabOutlineInsightType
  title: string
  claim: string
  why_it_matters: string
  salience: number
  confidence_band: string
  evidence_refs_prev: LabOutlineEvidenceRef[]
  evidence_refs_curr: LabOutlineEvidenceRef[]
  evidence_ref_ids: string[]
  counterpoint_or_limit: string
}

export type LabOutlineInsightEvidenceMapEntry = {
  evidence_id: string
  year: number
  paragraph_idx: number
  snippet: string
  char_start?: number | null
  char_end?: number | null
  insight_ids: string[]
}

export type LabOutlineInsightCoverage = {
  difference_count: number
  similarity_count: number
  per_year_evidence_spread: Record<string, number>
}

export type LabOutlineInsightUiCluster = {
  cluster_id: string
  label: string
  insight_ids: string[]
}

export type LabOutlineInsightUiContract = {
  default_selected_insight_id: string
  recommended_insight_order: string[]
  suggested_clusters: LabOutlineInsightUiCluster[]
}

export type LabOutlineCompareInsightOutput = Omit<LabOutlineCompareV2Output, "artifact_id"> & {
  artifact_id: "llm_outline_compare_insight"
  executive_digest: LabOutlineInsightExecutiveDigest
  insight_cards: LabOutlineInsightCard[]
  evidence_map: LabOutlineInsightEvidenceMapEntry[]
  insight_coverage: LabOutlineInsightCoverage
  ui_contract: LabOutlineInsightUiContract
}

export type LabOutlineResearchClaim = {
  claim: string
  source_url: string
  source_date: string
  support_label: "support" | "contradict" | "unclear"
  note: string
}

export type LabOutlineResearchOutput = {
  lab_schema_version: "1.0"
  artifact_schema_version: "1.0"
  artifact_id: "llm_outline_research_v1"
  ticker: string
  section: string
  source_id: LabSourceId
  cleaning_lens: LabCleaningLens
  year_from: number
  year_to: number
  trigger_reasons: string[]
  claims: LabOutlineResearchClaim[]
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


