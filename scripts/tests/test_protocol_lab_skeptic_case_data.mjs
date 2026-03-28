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

function resolveSkepticCasePathForTicker(ticker) {
  const normalized = String(ticker ?? "").trim().toUpperCase()
  if (normalized === "KO") {
    return "data/business_document_protocol_lab/skeptic_cases/KO_2024_2025_10k_item1a/ko_canonized_matrix_v1.json"
  }
  return null
}

test("KO pilot_matrix_v1 supports a one-lane skeptic-case matrix", () => {
  const payload = readJson(
    "public/data/business_document_protocol_lab/pilot_matrices/KO_2024_2025_10k_item1a/pilot_matrix_v1.json"
  )

  assert.equal(payload.artifact_schema_id, "pilot_matrix_v1")
  assert.equal(payload.fixture_id, "KO_2024_2025_10k_item1a")
  assert.equal(payload.ordered_cell_ids.length, 1)
  assert.deepEqual(payload.ordered_cell_ids, ["02_p1_i2_tagged_packet"])
  assert.deepEqual(payload.comparison_pairs, [])
  assert.equal(payload.pilot_status.state, "pilot_active_skeptic_case_slice")
})

test("KO skeptic-case canonized matrix stays product-legible", () => {
  const payload = readJson(
    "public/data/business_document_protocol_lab/skeptic_cases/KO_2024_2025_10k_item1a/ko_canonized_matrix_v1.json"
  )

  assert.equal(payload.artifact_schema_id, "skeptic_case_canonized_matrix_v1")
  assert.equal(payload.issuer.ticker, "KO")
  assert.equal(payload.canonical_run_ids.length, 4)
  assert.equal(payload.supports_visible_limited_integration, true)
  assert.equal(payload.agreement_snapshot["02_standard_vs_extended"].broadly_agree, true)
  assert.equal(payload.agreement_snapshot.p4_standard_vs_extended.broadly_agree, true)
  assert.match(payload.framing_note, /Mostly stable, selectively sharpened/i)
  assert.match(payload.product_interpretation, /credible|credibility/i)
})

test("skeptic cross-case summaries and historical current_case_mix_v1 stay bounded", () => {
  const thirdPilot = readJson(
    "public/data/business_document_protocol_lab/skeptic_cases/third_pilot_summary_v1.json"
  )
  const vividVsSkeptic = readJson(
    "public/data/business_document_protocol_lab/skeptic_cases/vivid_vs_skeptic_summary_v1.json"
  )
  const currentCaseMix = readJson(
    "public/data/business_document_protocol_lab/product_positioning/current_case_mix_v1.json"
  )

  assert.equal(thirdPilot.added_issuer, "KO")
  assert.equal(thirdPilot.should_be_visible_in_app, true)
  assert.match(thirdPilot.anti_expansion_note, /gallery|route redesign/i)

  assert.deepEqual(vividVsSkeptic.visible_case_mix.vivid_high_signal, ["NVDA", "LLY"])
  assert.deepEqual(vividVsSkeptic.visible_case_mix.skeptic_low_drift, ["KO"])
  assert.match(vividVsSkeptic.anti_hype_note, /not/i)

  assert.equal(currentCaseMix.artifact_schema_id, "current_case_mix_v1")
  assert.equal(currentCaseMix.visible_pilots.length, 3)
  assert.deepEqual(
    currentCaseMix.visible_pilots.map((item) => item.ticker).sort(),
    ["KO", "LLY", "NVDA"]
  )
  assert.match(
    currentCaseMix.visible_pilots.find((item) => item.ticker === "KO")?.role ?? "",
    /skeptic/i
  )
})

test("skeptic-case loader surfaces stay wired in source", () => {
  assert.match(schemaSource, /export const ProtocolLabSkepticCaseCanonizedMatrixSchema = z\.object\(/)
  assert.match(schemaSource, /export const ProtocolLabSkepticCaseQualityNotesSchema = z\.object\(/)
  assert.match(dataSource, /const SKEPTIC_CASE_PATHS: Record<string, string> = \{/)
  assert.match(
    dataSource,
    /KO:\s*"data\/business_document_protocol_lab\/skeptic_cases\/KO_2024_2025_10k_item1a\/ko_canonized_matrix_v1\.json"/
  )
  assert.equal(
    resolveSkepticCasePathForTicker("ko"),
    "data/business_document_protocol_lab/skeptic_cases/KO_2024_2025_10k_item1a/ko_canonized_matrix_v1.json"
  )
})
