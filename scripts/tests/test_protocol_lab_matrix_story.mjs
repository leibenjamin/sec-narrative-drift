import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, "..", "..")

function readJson(relativePath) {
  return JSON.parse(readFileSync(path.join(repoRoot, relativePath), "utf8"))
}

for (const fixture of [
  {
    fixtureId: "NVDA_2024_2025_10k_item1a",
    matrixId: "NVDA_2024_2025_10k_item1a__desktop_pilot_matrix_v1",
    path: "public/data/business_document_protocol_lab/pilot_matrices/NVDA_2024_2025_10k_item1a/pilot_matrix_story_v1.json",
    consensusCount: 4,
    disagreementCount: 4,
  },
  {
    fixtureId: "LLY_2024_2025_10k_item1a",
    matrixId: "LLY_2024_2025_10k_item1a__desktop_pilot_matrix_v1",
    path: "public/data/business_document_protocol_lab/pilot_matrices/LLY_2024_2025_10k_item1a/pilot_matrix_story_v1.json",
    consensusCount: 4,
    disagreementCount: 3,
  },
  {
    fixtureId: "KO_2024_2025_10k_item1a",
    matrixId: "KO_2024_2025_10k_item1a__desktop_pilot_matrix_v1",
    path: "public/data/business_document_protocol_lab/pilot_matrices/KO_2024_2025_10k_item1a/pilot_matrix_story_v1.json",
    consensusCount: 4,
    disagreementCount: 3,
  },
]) {
  test(`pilot_matrix_story_v1 stays valid and ordered for ${fixture.fixtureId}`, () => {
    const story = readJson(fixture.path)

    assert.equal(story.artifact_schema_id, "pilot_matrix_story_v1")
    assert.equal(story.matrix_id, fixture.matrixId)
    assert.equal(story.fixture_id, fixture.fixtureId)
    assert.equal(story.consensus_findings.length, fixture.consensusCount)
    assert.equal(story.disagreement_findings.length, fixture.disagreementCount)
    assert.deepEqual(story.display_priority_order, [
      "why_this_case_matters",
      "consensus_findings",
      "investor_read",
      "disagreement_findings",
      "protocol_read",
      "caveat",
    ])
    assert.equal(typeof story.why_this_case_matters, "string")
    assert.equal(typeof story.investor_read, "string")
    assert.equal(typeof story.protocol_read, "string")
    assert.equal(typeof story.caveat, "string")
  })
}
