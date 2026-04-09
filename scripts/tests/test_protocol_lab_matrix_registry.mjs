import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, "..", "..")
const dataSource = readFileSync(
  path.join(repoRoot, "src", "lib", "protocolLabMatrixData.ts"),
  "utf8"
)
const schemaSource = readFileSync(
  path.join(repoRoot, "src", "lib", "protocolLabMatrixSchemas.ts"),
  "utf8"
)

function readJson(relativePath) {
  return JSON.parse(readFileSync(path.join(repoRoot, relativePath), "utf8"))
}

function selectPilotMatrixRegistryItem(items, options) {
  const normalizedTicker = String(options.ticker ?? "").trim().toUpperCase()
  if (!normalizedTicker) return null

  const tickerMatches = items.filter((item) => String(item.ticker).trim().toUpperCase() === normalizedTicker)
  if (typeof options.yearFrom === "number" && typeof options.yearTo === "number") {
    return (
      tickerMatches.find(
        (item) => item.year_from === options.yearFrom && item.year_to === options.yearTo
      ) ?? null
    )
  }
  return tickerMatches.length === 1 ? tickerMatches[0] : null
}

test("pilot_matrices_v1 registry stays valid for the six public casebook cases", () => {
  const registry = readJson(
    "public/data/business_document_protocol_lab/registries/pilot_matrices_v1.json"
  )

  assert.equal(registry.artifact_schema_id, "pilot_matrices_v1")
  assert.equal(registry.version, "1.0")
  assert.equal(Array.isArray(registry.items), true)
  assert.equal(registry.items.length, 6)
  assert.deepEqual(
    registry.items.map((item) => item.ticker),
    ["NVDA", "LLY", "KO", "META", "TSLA", "WMT"]
  )

  const uniquePairs = new Set(
    registry.items.map((item) => `${item.ticker}:${item.year_from}-${item.year_to}`)
  )
  assert.equal(uniquePairs.size, registry.items.length)
})

test("selectPilotMatrixRegistryItem resolves exact public casebook cases", () => {
  const registry = readJson(
    "public/data/business_document_protocol_lab/registries/pilot_matrices_v1.json"
  )

  assert.equal(
    selectPilotMatrixRegistryItem(registry.items, {
      ticker: "NVDA",
      yearFrom: 2024,
      yearTo: 2025,
    })?.fixture_id,
    "NVDA_2024_2025_10k_item1a"
  )
  assert.equal(
    selectPilotMatrixRegistryItem(registry.items, {
      ticker: "LLY",
      yearFrom: 2024,
      yearTo: 2025,
    })?.fixture_id,
    "LLY_2024_2025_10k_item1a"
  )
  assert.equal(
    selectPilotMatrixRegistryItem(registry.items, {
      ticker: "KO",
      yearFrom: 2024,
      yearTo: 2025,
    })?.fixture_id,
    "KO_2024_2025_10k_item1a"
  )
  assert.equal(
    selectPilotMatrixRegistryItem(registry.items, {
      ticker: "META",
      yearFrom: 2024,
      yearTo: 2025,
    })?.fixture_id,
    "META_2024_2025_10k_item1a"
  )
  assert.equal(
    selectPilotMatrixRegistryItem(registry.items, {
      ticker: "TSLA",
      yearFrom: 2024,
      yearTo: 2025,
    })?.fixture_id,
    "TSLA_2024_2025_10k_item1a"
  )
  assert.equal(
    selectPilotMatrixRegistryItem(registry.items, {
      ticker: "WMT",
      yearFrom: 2025,
      yearTo: 2026,
    })?.fixture_id,
    "WMT_2025_2026_10k_item1a"
  )
})

test("selectPilotMatrixRegistryItem resolves public casebook entries by ticker when unique", () => {
  const registry = readJson(
    "public/data/business_document_protocol_lab/registries/pilot_matrices_v1.json"
  )

  for (const ticker of ["NVDA", "LLY", "KO", "META", "TSLA", "WMT"]) {
    assert.equal(selectPilotMatrixRegistryItem(registry.items, { ticker })?.ticker, ticker)
  }

  assert.equal(selectPilotMatrixRegistryItem(registry.items, { ticker: "GOOGL" }), null)
  assert.equal(selectPilotMatrixRegistryItem(registry.items, { ticker: "UNH" }), null)
})

test("registry source surfaces still wire bounded public matrix support", () => {
  assert.match(schemaSource, /comparison_pairs:\s*z\s*\.array\(/)
  assert.match(schemaSource, /normalized\.startsWith\("bundles\/"\)/)
  assert.match(dataSource, /export function resolveNoveltyLedgerCasePathForTicker\(ticker: string\)/)
  assert.match(dataSource, /export function resolveSkepticCasePathForTicker\(ticker: string\)/)
  assert.match(dataSource, /loadPilotMatrixBundleForTicker/)
})

test("candidate-backed public matrix cells can keep bundles-backed raw source refs", () => {
  for (const relativePath of [
    "public/data/business_document_protocol_lab/pilot_matrices/META_2024_2025_10k_item1a/cells/00_p0_i2_tagged_plain_prompt__pilot_matrix_cell_v1.json",
    "public/data/business_document_protocol_lab/pilot_matrices/META_2024_2025_10k_item1a/cells/02_p2_i2_tagged_protocol__pilot_matrix_cell_v1.json",
    "public/data/business_document_protocol_lab/pilot_matrices/TSLA_2024_2025_10k_item1a/cells/00_p0_i2_tagged_plain_prompt__pilot_matrix_cell_v1.json",
    "public/data/business_document_protocol_lab/pilot_matrices/TSLA_2024_2025_10k_item1a/cells/02_p2_i2_tagged_protocol__pilot_matrix_cell_v1.json",
    "public/data/business_document_protocol_lab/pilot_matrices/WMT_2025_2026_10k_item1a/cells/02_p2_i2_tagged_protocol__pilot_matrix_cell_v1.json",
  ]) {
    const payload = readJson(relativePath)
    assert.equal(payload.artifact_schema_id, "pilot_matrix_cell_v1")
    assert.match(payload.raw_source_refs.response_path, /^bundles\//)
    assert.match(payload.raw_source_refs.run_manifest_path, /^bundles\//)
  }
})
