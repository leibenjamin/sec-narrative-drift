import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import path from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, "..", "..")
const adapterModuleUrl = pathToFileURL(
  path.join(repoRoot, "src", "lib", "protocolLabMatrixAdapter.ts")
).href
const {
  normalizeBaselinePilotMatrixCell,
  normalizeStructuredPilotMatrixCell,
  recoverDesktopBaselineResponse,
  isRecoveredNoncanonicalControlCell,
} = await import(adapterModuleUrl)

function readJson(relativePath) {
  return JSON.parse(readFileSync(path.join(repoRoot, relativePath), "utf8"))
}

function readText(relativePath) {
  return readFileSync(path.join(repoRoot, relativePath), "utf8")
}

function buildStructuredOptions(
  cellId,
  shortLabel,
  role,
  lanePosition,
  responsePath,
  runManifestPath,
  matrixId = "NVDA_2024_2025_10k_item1a__desktop_pilot_matrix_v1",
  fixtureId = "NVDA_2024_2025_10k_item1a"
) {
  const response = readJson(responsePath)
  const manifest = readJson(runManifestPath)
  return {
    matrix_id: matrixId,
    fixture_id: fixtureId,
    cell_id: cellId,
    label: manifest.run_identity.run_name,
    short_label: shortLabel,
    role,
    lane_position: lanePosition,
    protocol_input_identity: {
      protocol_id: manifest.protocol_basis.canonical_protocol_id ?? null,
      protocol_label: manifest.protocol_basis.canonical_protocol_id ?? "Unstructured baseline",
      input_pack_id: manifest.input_basis.input_pack_id,
      input_label: manifest.input_basis.input_pack_id,
      display_text: `${shortLabel}`,
    },
    response,
    card_takeaway: `${shortLabel} card takeaway`,
    why_this_lane_matters: `${shortLabel} why this lane matters`,
    output_shape_info: {
      contract_mode: manifest.output_contract.contract_mode,
      display_text: manifest.output_contract.contract_mode,
      canonical_structured: true,
    },
    evidence_richness_tier: shortLabel === "P1+i1" ? "medium" : "high",
    auditability_note: `${shortLabel} auditability`,
    strengths: [`${shortLabel} strength`],
    limitations: [`${shortLabel} limitation`],
    raw_source_refs: {
      response_path: responsePath.replace(/\\/g, "/"),
      run_manifest_path: runManifestPath.replace(/\\/g, "/"),
    },
  }
}

test("normalizeStructuredPilotMatrixCell normalizes canonical lane 01", () => {
  const cell = normalizeStructuredPilotMatrixCell(
    buildStructuredOptions(
      "01_p1_i1_reuse_filtered",
      "P1+i1",
      "secondary_comparator",
      3,
      "wave4c3a6_split_default_flip_20260317_1702/01_p1_i1_reuse_filtered/response.json",
      "wave4c3a6_split_default_flip_20260317_1702/01_p1_i1_reuse_filtered/run_manifest.json"
    )
  )
  assert.equal(cell.normalization_status.kind, "canonical_json")
  assert.equal(cell.evidence_richness_tier, "medium")
  assert.equal(cell.evidence_count_total, 10)
  assert.match(cell.headline, /FY2025 reframes NVDA/i)
})

test("normalizeStructuredPilotMatrixCell normalizes canonical lane 02", () => {
  const cell = normalizeStructuredPilotMatrixCell(
    buildStructuredOptions(
      "02_p1_i2_tagged_packet",
      "P1+i2",
      "hero",
      1,
      "wave4c3a6_split_default_flip_20260317_1702/02_p1_i2_tagged_packet/response.json",
      "wave4c3a6_split_default_flip_20260317_1702/02_p1_i2_tagged_packet/run_manifest.json"
    )
  )
  assert.equal(cell.normalization_status.kind, "canonical_json")
  assert.equal(cell.evidence_richness_tier, "high")
  assert.equal(cell.evidence_count_total, 18)
  assert.match(cell.summary, /biggest lead shift is regulatory/i)
})

test("normalizeStructuredPilotMatrixCell normalizes canonical lane 03", () => {
  const cell = normalizeStructuredPilotMatrixCell(
    buildStructuredOptions(
      "03_p2_i2_tagged_protocol",
      "P2+i2",
      "main_comparator",
      2,
      "wave4c3a6_split_default_flip_20260317_1702/03_p2_i2_tagged_protocol/response.json",
      "wave4c3a6_split_default_flip_20260317_1702/03_p2_i2_tagged_protocol/run_manifest.json"
    )
  )
  assert.equal(cell.normalization_status.kind, "canonical_json")
  assert.equal(cell.evidence_richness_tier, "high")
  assert.equal(cell.evidence_count_total, 13)
  assert.match(cell.headline, /FY2025 keeps NVDA's core Item 1A risk architecture/i)
})

test("normalizeStructuredPilotMatrixCell normalizes LLY canonical lane 02", () => {
  const cell = normalizeStructuredPilotMatrixCell(
    buildStructuredOptions(
      "02_p1_i2_tagged_packet",
      "P1+i2",
      "hero",
      1,
      "wave4d2_lly_desktop_packet_20260318_1851/02_p1_i2_tagged_packet/response.json",
      "wave4d2_lly_desktop_packet_20260318_1851/02_p1_i2_tagged_packet/run_manifest.json",
      "LLY_2024_2025_10k_item1a__desktop_pilot_matrix_v1",
      "LLY_2024_2025_10k_item1a"
    )
  )
  assert.equal(cell.normalization_status.kind, "canonical_json")
  assert.equal(cell.evidence_count_total, 18)
  assert.match(cell.headline, /FY2025 leaves Lilly's Item 1A structure largely intact/i)
})

test("normalizeStructuredPilotMatrixCell normalizes LLY canonical lane 03", () => {
  const cell = normalizeStructuredPilotMatrixCell(
    buildStructuredOptions(
      "03_p2_i2_tagged_protocol",
      "P2+i2",
      "main_comparator",
      2,
      "wave4d2_lly_desktop_packet_20260318_1851/03_p2_i2_tagged_protocol/response.json",
      "wave4d2_lly_desktop_packet_20260318_1851/03_p2_i2_tagged_protocol/run_manifest.json",
      "LLY_2024_2025_10k_item1a__desktop_pilot_matrix_v1",
      "LLY_2024_2025_10k_item1a"
    )
  )
  assert.equal(cell.normalization_status.kind, "canonical_json")
  assert.equal(cell.evidence_count_total, 12)
  assert.match(cell.summary, /more company-specific obesity-access risk/i)
})

test("recoverDesktopBaselineResponse deterministically recovers B0 brief and evidence", () => {
  const raw = readText(
    "wave4c3a6_split_default_flip_20260317_1702/00_b0_unstructured_frontier_baseline/response.json"
  )
  const recovered = recoverDesktopBaselineResponse(raw)
  assert.equal(recovered.normalization_status.kind, "recovered_noncanonical_json")
  assert.equal(recovered.normalization_status.recovered, true)
  assert.equal(recovered.evidence_count_total, 11)
  assert.match(recovered.sections.bottom_line, /FY2025 Item 1A keeps the same broad risk map/i)
  assert.match(recovered.sections.caveat, /sharpening of emphasis and specificity/i)
})

test("normalizeBaselinePilotMatrixCell marks B0 as recovered control output", () => {
  const raw = readText(
    "wave4c3a6_split_default_flip_20260317_1702/00_b0_unstructured_frontier_baseline/response.json"
  )
  const cell = normalizeBaselinePilotMatrixCell({
    matrix_id: "NVDA_2024_2025_10k_item1a__desktop_pilot_matrix_v1",
    fixture_id: "NVDA_2024_2025_10k_item1a",
    cell_id: "00_b0_unstructured_frontier_baseline",
    label: "00_b0_unstructured_frontier_baseline",
    short_label: "B0",
    role: "control",
    lane_position: 4,
    protocol_input_identity: {
      protocol_id: null,
      protocol_label: "Unstructured Desktop baseline",
      input_pack_id: "i2_tagged_document_packet_v1",
      input_label: "Tagged document packet",
      display_text: "No canonical protocol + i2 tagged packet",
    },
    raw_response_text: raw,
    card_takeaway: "B0 takeaway",
    why_this_lane_matters: "B0 why lane matters",
    output_shape_info: {
      contract_mode: "desktop_packet_baseline_json",
      display_text: "Ad hoc Desktop baseline packet",
      canonical_structured: false,
    },
    evidence_richness_tier: "baseline",
    auditability_note: "Recovered baseline",
    strengths: ["Same tagged substrate as 02"],
    limitations: ["Noncanonical response envelope"],
    raw_source_refs: {
      response_path:
        "wave4c3a6_split_default_flip_20260317_1702/00_b0_unstructured_frontier_baseline/response.json",
      run_manifest_path:
        "wave4c3a6_split_default_flip_20260317_1702/00_b0_unstructured_frontier_baseline/run_manifest.json",
    },
  })
  assert.equal(cell.normalization_status.kind, "recovered_noncanonical_json")
  assert.equal(cell.output_shape_info.canonical_structured, false)
  assert.equal(cell.evidence_count_total, 11)
  assert.match(cell.summary, /In FY2024, the supply narrative centered on demand-estimation errors/i)
})

test("normalizeBaselinePilotMatrixCell marks LLY B0 as recovered control output", () => {
  const raw = readText(
    "wave4d2_lly_desktop_packet_20260318_1851/00_b0_unstructured_frontier_baseline/response.json"
  )
  const cell = normalizeBaselinePilotMatrixCell({
    matrix_id: "LLY_2024_2025_10k_item1a__desktop_pilot_matrix_v1",
    fixture_id: "LLY_2024_2025_10k_item1a",
    cell_id: "00_b0_unstructured_frontier_baseline",
    label: "B0 unstructured frontier baseline",
    short_label: "B0",
    role: "control",
    lane_position: 3,
    protocol_input_identity: {
      protocol_id: null,
      protocol_label: "Unstructured Desktop baseline",
      input_pack_id: "i2_tagged_document_packet_v1",
      input_label: "Tagged document packet",
      display_text: "No canonical protocol + i2 tagged packet",
    },
    raw_response_text: raw,
    card_takeaway: "B0 takeaway",
    why_this_lane_matters: "B0 why lane matters",
    output_shape_info: {
      contract_mode: "desktop_packet_baseline_json",
      display_text: "Recovered ad hoc brief plus evidence array",
      canonical_structured: false,
    },
    evidence_richness_tier: "baseline",
    auditability_note: "Recovered baseline",
    strengths: ["Same tagged substrate as 02"],
    limitations: ["Noncanonical response envelope"],
    raw_source_refs: {
      response_path:
        "wave4d2_lly_desktop_packet_20260318_1851/00_b0_unstructured_frontier_baseline/response.json",
      run_manifest_path:
        "wave4d2_lly_desktop_packet_20260318_1851/00_b0_unstructured_frontier_baseline/run_manifest.json",
    },
  })
  assert.equal(cell.normalization_status.kind, "recovered_noncanonical_json")
  assert.equal(cell.evidence_count_total, 17)
  assert.match(cell.summary, /LillyDirect\/self-pay obesity access channel risk/i)
})

test("isRecoveredNoncanonicalControlCell only returns true for recovered control lanes", () => {
  const recoveredControl = {
    role: "control",
    normalization_status: {
      kind: "recovered_noncanonical_json",
      recovered: true,
    },
  }
  const canonicalHero = {
    role: "hero",
    normalization_status: {
      kind: "canonical_json",
      recovered: false,
    },
  }
  const canonicalControl = {
    role: "control",
    normalization_status: {
      kind: "canonical_json",
      recovered: false,
    },
  }

  assert.equal(isRecoveredNoncanonicalControlCell(recoveredControl), true)
  assert.equal(isRecoveredNoncanonicalControlCell(canonicalHero), false)
  assert.equal(isRecoveredNoncanonicalControlCell(canonicalControl), false)
})

test("recoverDesktopBaselineResponse fails closed when the brief/evidence boundary is missing", () => {
  assert.throws(
    () => recoverDesktopBaselineResponse('{"brief_markdown": "Bottom line: x"}'),
    /literal brief\/evidence boundary/
  )
})
