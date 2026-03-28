import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, "..", "..")
const schemaSource = readFileSync(
  path.join(repoRoot, "src", "lib", "protocolLabMatrixSchemas.ts"),
  "utf8"
)
const dataSource = readFileSync(
  path.join(repoRoot, "src", "lib", "protocolLabMatrixData.ts"),
  "utf8"
)

function readJson(relativePath) {
  return JSON.parse(readFileSync(path.join(repoRoot, relativePath), "utf8"))
}

function assertStringArray(value, label) {
  assert.ok(Array.isArray(value), `${label} must be an array`)
  assert.ok(value.length >= 1, `${label} must not be empty`)
  for (const entry of value) {
    assert.equal(typeof entry, "string", `${label} entries must be strings`)
    assert.notEqual(entry.trim(), "", `${label} entries must not be blank`)
  }
}

function assertModuleItem(item, label) {
  assert.equal(typeof item.item_id, "string", `${label}.item_id`)
  assert.equal(typeof item.label, "string", `${label}.label`)
  assert.equal(typeof item.text, "string", `${label}.text`)
  assert.match(
    item.support_level,
    /^(both|extended_primary_standard_compatible|standard_primary_extended_compatible)$/,
    `${label}.support_level`
  )
  assert.ok(Array.isArray(item.source_run_ids), `${label}.source_run_ids must be an array`)
  assert.ok(Array.isArray(item.evidence_preview), `${label}.evidence_preview must be an array`)
  assert.ok(item.evidence_preview.length >= 1, `${label}.evidence_preview must not be empty`)
}

function assertCanonizedCase(payload, ticker) {
  assert.equal(payload.artifact_schema_id, "p4_canonized_matrix_v1")
  assert.equal(payload.issuer.ticker, ticker)
  assert.equal(typeof payload.fixture_id, "string")
  assert.equal(typeof payload.p4_role_statement, "string")
  assert.equal(typeof payload.issuer_finding_summary, "string")
  assert.equal(typeof payload.standard_and_extended_broadly_agree, "boolean")
  assert.equal(typeof payload.suitable_for_limited_app_integration, "boolean")
  assertStringArray(payload.canonical_run_ids, "canonical_run_ids")
  assert.ok(Array.isArray(payload.canonized_runs))
  assert.equal(payload.canonized_runs.length, 2)
  for (const run of payload.canonized_runs) {
    assert.equal(typeof run.run_id, "string")
    assert.equal(typeof run.reasoning_variant, "string")
    assert.equal(typeof run.source_response_path, "string")
    assert.equal(typeof run.source_run_manifest_path, "string")
    assert.match(
      run.canonization_status,
      /^(canonized_as_is|canonized_with_transport_repair|canonized_with_evidence_row_correction)$/
    )
    assert.ok(Array.isArray(run.quality_note_ids))
  }
  assert.ok(payload.module_sections)
  assert.ok(Array.isArray(payload.module_sections.fresh_2025_specifics))
  assert.ok(Array.isArray(payload.module_sections.intensified_or_broadened_points))
  assert.ok(Array.isArray(payload.module_sections.reused_framework_language))
  assert.ok(Array.isArray(payload.module_sections.boundary_notes))
  for (const [sectionId, items] of Object.entries(payload.module_sections)) {
    for (const item of items) {
      assertModuleItem(item, `${ticker}.${sectionId}`)
    }
  }
}

function assertQualityArtifact(payload, expectedMinimumCount) {
  assert.equal(payload.artifact_schema_id, "p4_quality_notes_v1")
  assert.ok(Array.isArray(payload.notes))
  assert.ok(payload.notes.length >= expectedMinimumCount)
  for (const note of payload.notes) {
    assert.equal(typeof note.note_id, "string")
    assert.equal(typeof note.issue_type, "string")
    assert.equal(typeof note.affected_run_id, "string")
    assert.match(
      note.issue_family,
      /^(transport\/container|evidence-row integrity|analytical\/content|none)$/
    )
    assert.equal(typeof note.deterministic_repair_allowed, "boolean")
    assert.equal(typeof note.repair_applied_in_canonization, "boolean")
    assert.equal(typeof note.changes_broad_analytical_verdict, "boolean")
    assert.equal(typeof note.review_note, "string")
    assert.equal(typeof note.response_path, "string")
    assert.equal(typeof note.run_manifest_path, "string")
  }
}

test("p4_canonized_matrix_v1 payloads stay valid for NVDA, LLY, and KO", () => {
  const nvda = readJson(
    "public/data/business_document_protocol_lab/novelty_ledger/NVDA_2024_2025_10k_item1a/p4_canonized_matrix_v1.json"
  )
  const lly = readJson(
    "public/data/business_document_protocol_lab/novelty_ledger/LLY_2024_2025_10k_item1a/p4_canonized_matrix_v1.json"
  )
  const ko = readJson(
    "public/data/business_document_protocol_lab/novelty_ledger/KO_2024_2025_10k_item1a/p4_canonized_matrix_v1.json"
  )

  assertCanonizedCase(nvda, "NVDA")
  assertCanonizedCase(lly, "LLY")
  assertCanonizedCase(ko, "KO")
  assert.match(nvda.module_sections.fresh_2025_specifics[0]?.label ?? "", /AI Diffusion/i)
  assert.match(lly.module_sections.fresh_2025_specifics[0]?.label ?? "", /pricing arrangements/i)
  assert.match(ko.module_sections.fresh_2025_specifics[0]?.label ?? "", /Pillar Two/i)
})

test("p4_quality_notes_v1 payloads stay valid for NVDA, LLY, and KO", () => {
  const nvda = readJson(
    "public/data/business_document_protocol_lab/novelty_ledger/nvda_p4_quality_notes_v1.json"
  )
  const lly = readJson(
    "public/data/business_document_protocol_lab/novelty_ledger/lly_p4_quality_notes_v1.json"
  )
  const ko = readJson(
    "public/data/business_document_protocol_lab/novelty_ledger/ko_p4_quality_notes_v1.json"
  )

  assertQualityArtifact(nvda, 2)
  assertQualityArtifact(lly, 1)
  assertQualityArtifact(ko, 2)
  assert.match(nvda.notes[0]?.issue_type ?? "", /quotes/i)
  assert.match(lly.notes[0]?.issue_type ?? "", /substring/i)
  assert.match(ko.notes[0]?.issue_type ?? "", /no_blocking/i)
})

test("cross-case novelty-ledger summaries stay product-legible", () => {
  const canonizedSummary = readJson(
    "public/data/business_document_protocol_lab/novelty_ledger/p4_canonized_summary_v1.json"
  )
  const p4VsP1Summary = readJson(
    "public/data/business_document_protocol_lab/novelty_ledger/p4_vs_p1_summary_v1.json"
  )

  assert.equal(canonizedSummary.artifact_schema_id, "p4_canonized_summary_v1")
  assert.deepEqual([...canonizedSummary.covered_issuers].sort(), ["KO", "LLY", "NVDA"])
  assertStringArray(
    canonizedSummary.what_p4_consistently_adds_over_02,
    "what_p4_consistently_adds_over_02"
  )
  assertStringArray(
    canonizedSummary.what_p4_still_does_not_do_as_well_as_02,
    "what_p4_still_does_not_do_as_well_as_02"
  )
  assert.match(canonizedSummary.overall_verdict, /secondary/i)

  assert.equal(p4VsP1Summary.artifact_schema_id, "p4_vs_p1_summary_v1")
  assert.equal(p4VsP1Summary.hero_lane_family, "02_p1_i2_tagged_packet")
  assert.deepEqual([...p4VsP1Summary.covered_issuers].sort(), ["KO", "LLY", "NVDA"])
  assertStringArray(p4VsP1Summary.where_p4_is_stronger, "where_p4_is_stronger")
  assertStringArray(p4VsP1Summary.where_02_is_stronger, "where_02_is_stronger")
  assert.match(p4VsP1Summary.bounded_decision, /02/)
})

test("novelty-ledger schema and path surfaces stay wired in source", () => {
  assert.match(schemaSource, /export const ProtocolLabNoveltyLedgerCaseSchema = z\.object\(/)
  assert.match(
    schemaSource,
    /export const ProtocolLabNoveltyLedgerQualityArtifactSchema = z\.object\(/
  )
  assert.match(schemaSource, /export const ProtocolLabNoveltyLedgerSummarySchema = z\.object\(/)
  assert.match(
    schemaSource,
    /export const ProtocolLabNoveltyLedgerVsP1SummarySchema = z\.object\(/
  )

  assert.match(dataSource, /const NOVELTY_LEDGER_CASE_PATHS: Record<string, string> = \{/)
  assert.match(
    dataSource,
    /NVDA:\s*"data\/business_document_protocol_lab\/novelty_ledger\/NVDA_2024_2025_10k_item1a\/p4_canonized_matrix_v1\.json"/
  )
  assert.match(
    dataSource,
    /LLY:\s*"data\/business_document_protocol_lab\/novelty_ledger\/LLY_2024_2025_10k_item1a\/p4_canonized_matrix_v1\.json"/
  )
  assert.match(
    dataSource,
    /KO:\s*"data\/business_document_protocol_lab\/novelty_ledger\/KO_2024_2025_10k_item1a\/p4_canonized_matrix_v1\.json"/
  )
  assert.match(dataSource, /export function resolveNoveltyLedgerCasePathForTicker\(ticker: string\)/)
})
