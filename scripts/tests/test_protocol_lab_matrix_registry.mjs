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

test("pilot_matrices_v1 registry stays valid for the three integrated pilot cases", () => {
  const registry = readJson(
    "public/data/business_document_protocol_lab/registries/pilot_matrices_v1.json"
  )

  assert.equal(registry.artifact_schema_id, "pilot_matrices_v1")
  assert.equal(registry.version, "1.0")
  assert.equal(Array.isArray(registry.items), true)
  assert.equal(registry.items.length, 3)
  assert.deepEqual(
    registry.items.map((item) => item.ticker).sort(),
    ["KO", "LLY", "NVDA"]
  )

  const uniquePairs = new Set(
    registry.items.map((item) => `${item.ticker}:${item.year_from}-${item.year_to}`)
  )
  assert.equal(uniquePairs.size, registry.items.length)
})

test("selectPilotMatrixRegistryItem resolves exact NVDA, LLY, and KO cases", () => {
  const registry = readJson(
    "public/data/business_document_protocol_lab/registries/pilot_matrices_v1.json"
  )

  const nvda = selectPilotMatrixRegistryItem(registry.items, {
    ticker: "NVDA",
    yearFrom: 2024,
    yearTo: 2025,
  })
  const lly = selectPilotMatrixRegistryItem(registry.items, {
    ticker: "LLY",
    yearFrom: 2024,
    yearTo: 2025,
  })
  const ko = selectPilotMatrixRegistryItem(registry.items, {
    ticker: "KO",
    yearFrom: 2024,
    yearTo: 2025,
  })

  assert.equal(nvda?.fixture_id, "NVDA_2024_2025_10k_item1a")
  assert.equal(lly?.fixture_id, "LLY_2024_2025_10k_item1a")
  assert.equal(ko?.fixture_id, "KO_2024_2025_10k_item1a")
})

test("selectPilotMatrixRegistryItem resolves by ticker when only one integrated case exists", () => {
  const registry = readJson(
    "public/data/business_document_protocol_lab/registries/pilot_matrices_v1.json"
  )

  assert.equal(
    selectPilotMatrixRegistryItem(registry.items, { ticker: "nvda" })?.fixture_id,
    "NVDA_2024_2025_10k_item1a"
  )
  assert.equal(
    selectPilotMatrixRegistryItem(registry.items, { ticker: "LLY" })?.fixture_id,
    "LLY_2024_2025_10k_item1a"
  )
  assert.equal(
    selectPilotMatrixRegistryItem(registry.items, { ticker: "KO" })?.fixture_id,
    "KO_2024_2025_10k_item1a"
  )
  assert.equal(selectPilotMatrixRegistryItem(registry.items, { ticker: "WM" }), null)
})

test("registry source surfaces still wire KO and one-lane matrix support", () => {
  assert.match(schemaSource, /comparison_pairs:\s*z\s*\.array\(/)
  assert.match(schemaSource, /pilot_active_skeptic_case_slice|ProtocolLabSkepticCaseCanonizedMatrixSchema/)
  assert.match(dataSource, /export function resolveNoveltyLedgerCasePathForTicker\(ticker: string\)/)
  assert.match(dataSource, /export function resolveSkepticCasePathForTicker\(ticker: string\)/)
})
