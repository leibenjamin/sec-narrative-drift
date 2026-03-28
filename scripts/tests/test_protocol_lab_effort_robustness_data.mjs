import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import path from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, "..", "..")
const schemaModuleUrl = pathToFileURL(
  path.join(repoRoot, "src", "lib", "protocolLabMatrixSchemas.ts")
).href
const dataModuleUrl = pathToFileURL(
  path.join(repoRoot, "src", "lib", "protocolLabMatrixData.ts")
).href

const {
  ProtocolLabEffortRobustnessCaseSchema,
  ProtocolLabEffortRobustnessSummarySchema,
} = await import(schemaModuleUrl)
const { resolveEffortRobustnessCasePathForTicker } = await import(dataModuleUrl)

function readJson(relativePath) {
  return JSON.parse(readFileSync(path.join(repoRoot, relativePath), "utf8"))
}

test("effort_robustness_case_v1 validates for NVDA and LLY", () => {
  const fixtures = [
    {
      ticker: "NVDA",
      fixtureId: "NVDA_2024_2025_10k_item1a",
      path: "public/data/business_document_protocol_lab/standard_controls/effort_robustness/nvda_effort_robustness_v1.json",
      artifactId: "nvda_effort_robustness_v1",
    },
    {
      ticker: "LLY",
      fixtureId: "LLY_2024_2025_10k_item1a",
      path: "public/data/business_document_protocol_lab/standard_controls/effort_robustness/lly_effort_robustness_v1.json",
      artifactId: "lly_effort_robustness_v1",
    },
  ]

  for (const fixture of fixtures) {
    const payload = readJson(fixture.path)
    const parsed = ProtocolLabEffortRobustnessCaseSchema.parse(payload)

    assert.equal(parsed.artifact_schema_id, "effort_robustness_case_v1")
    assert.equal(parsed.fixture_id, fixture.fixtureId)
    assert.equal(parsed.artifact_id, fixture.artifactId)
    assert.equal(parsed.issuer.ticker, fixture.ticker)
    assert.equal(typeof parsed.lane_robustness["02"], "string")
    assert.equal(typeof parsed.lane_robustness["03"], "string")
    assert.equal(typeof parsed.lane_robustness["00"], "string")
  }
})

test("effort_robustness_summary_v1 validates and covers both issuers", () => {
  const payload = readJson(
    "public/data/business_document_protocol_lab/standard_controls/effort_robustness/effort_robustness_summary_v1.json"
  )
  const parsed = ProtocolLabEffortRobustnessSummarySchema.parse(payload)

  assert.equal(parsed.artifact_schema_id, "effort_robustness_summary_v1")
  assert.deepEqual([...parsed.covered_issuers].sort(), ["LLY", "NVDA"])
  assert.match(parsed.cross_case_pattern_summary, /02 is the most effort-robust lane/i)
})

test("resolveEffortRobustnessCasePathForTicker resolves both visible pilot fixtures", () => {
  assert.equal(
    resolveEffortRobustnessCasePathForTicker("NVDA"),
    "data/business_document_protocol_lab/standard_controls/effort_robustness/nvda_effort_robustness_v1.json"
  )
  assert.equal(
    resolveEffortRobustnessCasePathForTicker("lly"),
    "data/business_document_protocol_lab/standard_controls/effort_robustness/lly_effort_robustness_v1.json"
  )
  assert.equal(resolveEffortRobustnessCasePathForTicker("KO"), null)
})
