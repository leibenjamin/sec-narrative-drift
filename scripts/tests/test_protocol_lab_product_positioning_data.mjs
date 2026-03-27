import test from "node:test"
import assert from "node:assert/strict"
import { existsSync, readFileSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, "..", "..")
const appSource = readFileSync(path.join(repoRoot, "src", "App.tsx"), "utf8")
const homeSource = readFileSync(path.join(repoRoot, "src", "pages", "Home.tsx"), "utf8")
const companiesSource = readFileSync(path.join(repoRoot, "src", "pages", "Companies.tsx"), "utf8")
const companySource = readFileSync(path.join(repoRoot, "src", "pages", "Company.tsx"), "utf8")
const labPanelSource = readFileSync(path.join(repoRoot, "src", "components", "LabPanel.tsx"), "utf8")
const pageMetadataSource = readFileSync(
  path.join(repoRoot, "src", "components", "PageMetadata.tsx"),
  "utf8"
)
const useCaseGuideSource = readFileSync(
  path.join(repoRoot, "src", "components", "ProtocolLabUseCaseGuide.tsx"),
  "utf8"
)
const pilotMatrixPanelSource = readFileSync(
  path.join(repoRoot, "src", "components", "ProtocolLabPilotMatrixPanel.tsx"),
  "utf8"
)
const positioningSource = readFileSync(
  path.join(repoRoot, "src", "lib", "protocolLabProductPositioning.ts"),
  "utf8"
)
const readmeSource = readFileSync(path.join(repoRoot, "README.md"), "utf8")
const indexHtmlSource = readFileSync(path.join(repoRoot, "index.html"), "utf8")

const VISIBLE_STORY_TEXT_PATHS = [
  "README.md",
  "src/pages/Home.tsx",
  "src/pages/Companies.tsx",
  "src/pages/Company.tsx",
  "src/components/LabPanel.tsx",
  "src/components/ProtocolLabUseCaseGuide.tsx",
  "src/components/ProtocolLabPilotMatrixPanel.tsx",
  "public/data/business_document_protocol_lab/product_positioning/current_case_mix_v2.json",
  "public/data/business_document_protocol_lab/product_positioning/start_here_v1.json",
  "public/data/business_document_protocol_lab/product_positioning/demo_share_v3.json",
  "public/data/business_document_protocol_lab/pilot_matrices/NVDA_2024_2025_10k_item1a/pilot_matrix_v1.json",
  "public/data/business_document_protocol_lab/pilot_matrices/LLY_2024_2025_10k_item1a/pilot_matrix_v1.json",
  "public/data/business_document_protocol_lab/pilot_matrices/KO_2024_2025_10k_item1a/pilot_matrix_v1.json",
  "public/data/business_document_protocol_lab/pilot_matrices/NVDA_2024_2025_10k_item1a/pilot_matrix_story_v1.json",
  "public/data/business_document_protocol_lab/pilot_matrices/LLY_2024_2025_10k_item1a/pilot_matrix_story_v1.json",
  "public/data/business_document_protocol_lab/pilot_matrices/KO_2024_2025_10k_item1a/pilot_matrix_story_v1.json",
  "public/data/business_document_protocol_lab/pilot_matrices/NVDA_2024_2025_10k_item1a/pilot_matrix_review_v1.json",
  "public/data/business_document_protocol_lab/pilot_matrices/LLY_2024_2025_10k_item1a/pilot_matrix_review_v1.json",
  "public/data/business_document_protocol_lab/pilot_matrices/KO_2024_2025_10k_item1a/pilot_matrix_review_v1.json",
  "public/data/business_document_protocol_lab/pilot_matrices/NVDA_2024_2025_10k_item1a/cells/02_p1_i2_tagged_packet__pilot_matrix_cell_v1.json",
  "public/data/business_document_protocol_lab/pilot_matrices/LLY_2024_2025_10k_item1a/cells/02_p1_i2_tagged_packet__pilot_matrix_cell_v1.json",
  "public/data/business_document_protocol_lab/pilot_matrices/KO_2024_2025_10k_item1a/cells/02_p1_i2_tagged_packet__pilot_matrix_cell_v1.json",
  "public/data/business_document_protocol_lab/novelty_ledger/NVDA_2024_2025_10k_item1a/p4_canonized_matrix_v1.json",
  "public/data/business_document_protocol_lab/novelty_ledger/LLY_2024_2025_10k_item1a/p4_canonized_matrix_v1.json",
  "public/data/business_document_protocol_lab/novelty_ledger/KO_2024_2025_10k_item1a/p4_canonized_matrix_v1.json",
]

function readJson(relativePath) {
  return JSON.parse(readFileSync(path.join(repoRoot, relativePath), "utf8"))
}

function readText(relativePath) {
  return readFileSync(path.join(repoRoot, relativePath), "utf8")
}

function assertPathExists(relativePath) {
  assert.equal(existsSync(path.join(repoRoot, relativePath)), true, `${relativePath} must exist`)
}

function assertNonEmptyString(value, label) {
  assert.equal(typeof value, "string", `${label} must be a string`)
  assert.notEqual(value.trim(), "", `${label} must not be blank`)
}

function assertNoStaleVisibleCatalogTerms(value, label) {
  assert.equal(/\bWM\b/.test(value), false, `${label} must not mention WM`)
  assert.equal(/\bGE\b/.test(value), false, `${label} must not mention GE`)
  assert.equal(/\bCore4\b/i.test(value), false, `${label} must not mention Core4`)
}

function assertNoStalePublicShorthand(value, label) {
  for (const phrase of [
    "02 default read",
    "P4 fresh-vs-reused check",
    "03 comparison read",
    "00 recovered control",
    "proof-point",
    "visible pilot system",
    "pilot-first",
  ]) {
    assert.equal(value.includes(phrase), false, `${label} must not include stale phrase: ${phrase}`)
  }
}

test("current_case_mix_v2 stays aligned to the three visible pilots", () => {
  const payload = readJson(
    "public/data/business_document_protocol_lab/product_positioning/current_case_mix_v2.json"
  )

  assert.equal(payload.artifact_schema_id, "current_case_mix_v2")
  assert.equal(payload.artifact_id, "current_case_mix_v2")
  assert.deepEqual(
    payload.visible_pilots.map((item) => item.ticker),
    ["NVDA", "LLY", "KO"]
  )

  for (const item of payload.visible_pilots) {
    assertNonEmptyString(item.company_name, `${item.ticker}.company_name`)
    assert.equal(typeof item.year_from, "number", `${item.ticker}.year_from`)
    assert.equal(typeof item.year_to, "number", `${item.ticker}.year_to`)
    assertNonEmptyString(item.role, `${item.ticker}.role`)
    assertNonEmptyString(item.role_label, `${item.ticker}.role_label`)
    assertNonEmptyString(item.why_case_exists, `${item.ticker}.why_case_exists`)
    assertNonEmptyString(item.best_for, `${item.ticker}.best_for`)
  }

  assertNonEmptyString(payload.product_statement, "product_statement")
  assertNonEmptyString(payload.anti_hype_statement, "anti_hype_statement")
  assertNonEmptyString(payload.why_this_mix_matters, "why_this_mix_matters")

  const serialized = JSON.stringify(payload)
  assertNoStaleVisibleCatalogTerms(serialized, "current_case_mix_v2")
})

test("start_here_v1 stays aligned to the current three-case mix", () => {
  const currentCaseMix = readJson(
    "public/data/business_document_protocol_lab/product_positioning/current_case_mix_v2.json"
  )
  const payload = readJson(
    "public/data/business_document_protocol_lab/product_positioning/start_here_v1.json"
  )
  const visibleTickers = currentCaseMix.visible_pilots.map((item) => item.ticker)
  const alternativeTickers = payload.alternative_first_cases.map((item) => item.ticker)
  const guidanceTickers = payload.case_guidance.map((item) => item.ticker)
  const expectedAlternativeTickers = visibleTickers.filter(
    (ticker) => ticker !== payload.recommended_first_case
  )

  assert.equal(payload.artifact_schema_id, "start_here_v1")
  assert.equal(payload.artifact_id, "start_here_v1")
  assert.equal(payload.recommended_first_case, "NVDA")
  assert.equal(visibleTickers.includes(payload.recommended_first_case), true)
  assert.deepEqual([...alternativeTickers].sort(), [...expectedAlternativeTickers].sort())
  assert.deepEqual([...guidanceTickers].sort(), [...visibleTickers].sort())
  assert.deepEqual(
    payload.reading_flow.map((item) => item.step),
    ["filing answer", "protocol meaning", "audit if needed"]
  )

  for (const item of payload.alternative_first_cases) {
    assertNonEmptyString(item.why_pick, `${item.ticker}.why_pick`)
    assertNonEmptyString(item.what_you_learn, `${item.ticker}.what_you_learn`)
  }

  for (const item of payload.case_guidance) {
    assertNonEmptyString(item.why_pick, `${item.ticker}.why_pick`)
    assertNonEmptyString(item.what_you_learn, `${item.ticker}.what_you_learn`)
  }

  for (const item of currentCaseMix.visible_pilots) {
    const guidance = payload.case_guidance.find((entry) => entry.ticker === item.ticker)
    assert.ok(guidance, `${item.ticker} must have case guidance`)
    const expectedHref = `/company/${item.ticker}?tab=lab&from=${item.year_from}&to=${item.year_to}`
    assert.match(
      expectedHref,
      /^\/company\/[A-Z0-9.-]+\?tab=lab&from=\d{4}&to=\d{4}$/,
      `${item.ticker} route must stay valid`
    )
  }

  const serialized = JSON.stringify(payload)
  assertNoStaleVisibleCatalogTerms(serialized, "start_here_v1")
})

test("demo_share_v3 stays aligned with the current three-case mix and share assets", () => {
  const currentCaseMix = readJson(
    "public/data/business_document_protocol_lab/product_positioning/current_case_mix_v2.json"
  )
  const demoShare = readJson(
    "public/data/business_document_protocol_lab/product_positioning/demo_share_v3.json"
  )

  assert.equal(demoShare.artifact_schema_id, "demo_share_v3")
  assert.equal(demoShare.artifact_id, "demo_share_v3")

  for (const key of [
    "one_line_product_description",
    "short_subhead",
    "current_coverage_statement",
    "three_case_mix_usefulness_statement",
    "where_to_start_statement",
    "external_demo_blurb",
    "readme_blurb",
    "meta_description_candidate",
    "social_share_caption_candidate",
    "canonical_share_title",
    "canonical_share_description",
    "canonical_external_url",
    "canonical_share_image_path",
    "canonical_share_image_url",
    "canonical_share_image_alt",
    "canonical_favicon_path",
    "canonical_app_icon_path",
  ]) {
    assertNonEmptyString(demoShare[key], `demo_share_v3.${key}`)
  }

  for (const ticker of currentCaseMix.visible_pilots.map((item) => item.ticker)) {
    assert.equal(
      demoShare.current_coverage_statement.includes(ticker) ||
        demoShare.where_to_start_statement.includes(ticker),
      true,
      `demo_share_v3 must stay aligned with visible ticker ${ticker}`
    )
  }

  assert.equal(demoShare.canonical_share_description, demoShare.meta_description_candidate)
  assert.equal(demoShare.canonical_external_url, "https://benlei.org/sec-narrative-drift/")
  assert.equal(
    demoShare.canonical_share_image_url.endsWith(demoShare.canonical_share_image_path),
    true
  )

  assertPathExists(`public/${demoShare.canonical_share_image_path}`)
  assertPathExists(`public/${demoShare.canonical_favicon_path}`)
  assertPathExists(`public/${demoShare.canonical_app_icon_path}`)
  assertPathExists("public/social/sec-narrative-drift-lab-icon-512.png")

  assertNoStaleVisibleCatalogTerms(JSON.stringify(demoShare), "demo_share_v3")
  assertNoStalePublicShorthand(JSON.stringify(demoShare), "demo_share_v3")
})

test("Home, Companies, and Company share the normalized visible pilot source", () => {
  assert.match(positioningSource, /export type ProtocolLabVisiblePilotSystem = \{/)
  assert.match(positioningSource, /export type ProtocolLabDemoShareV3 = /)
  assert.match(positioningSource, /export async function loadProtocolLabDemoShareV3\(\)/)
  assert.match(positioningSource, /export async function loadProtocolLabVisiblePilotSystem\(\)/)
  assert.match(positioningSource, /export function buildProtocolLabCaseHref\(/)
  assert.match(appSource, /<Route path="\/company" element={<Company \/>} \/>/)
  assert.match(appSource, /<Route path="\/company\/:ticker" element={<Company \/>} \/>/)

  assert.match(homeSource, /PageMetadata/)
  assert.match(homeSource, /loadProtocolLabDemoShareV3/)
  assert.match(homeSource, /loadProtocolLabVisiblePilotSystem/)
  assert.match(homeSource, /getProtocolLabRecommendedPilot/)
  assert.match(homeSource, /listProtocolLabVisiblePilots/)
  assert.equal(homeSource.includes('/company/NVDA?tab=lab&from=2024&to=2025'), false)

  assert.match(companiesSource, /PageMetadata/)
  assert.match(companiesSource, /loadProtocolLabVisiblePilotSystem/)
  assert.match(companiesSource, /getProtocolLabRecommendedPilot/)
  assert.match(companiesSource, /listProtocolLabVisiblePilots/)
  assert.equal(companiesSource.includes('/company/NVDA?tab=lab&from=2024&to=2025'), false)

  assert.match(companySource, /PageMetadata/)
  assert.match(companySource, /loadProtocolLabVisiblePilotSystem/)
  assert.match(companySource, /findProtocolLabVisiblePilotEntry/)
  assert.equal(companySource.includes("listLabShowcaseTickers"), false)
})

test("visible story copy stays aligned to the softened public wording", () => {
  const combinedText = VISIBLE_STORY_TEXT_PATHS.map((relativePath) => readText(relativePath)).join("\n")

  for (const phrase of [
    "hero lane",
    "pilot-first lower boundary",
    "pilot-first slice",
    "pilot matrix",
    "Novelty ledger",
  ]) {
    assert.equal(
      combinedText.includes(phrase),
      false,
      `visible story copy must not include stale phrase: ${phrase}`
    )
  }

  assertNoStalePublicShorthand(combinedText, "visible story copy")

  assert.match(homeSource, /Document Protocol Lab/)
  assert.match(homeSource, /Open the NVDA fixture/)
  assert.match(homeSource, /Recommended start/)
  assert.match(homeSource, /Why these three fixtures/)
  assert.match(homeSource, /Default reading order/)
  assert.equal(homeSource.includes("Current pilot fixtures"), false)
  assert.equal(homeSource.includes("ProtocolLabUseCaseGuide"), false)
  assert.match(companiesSource, /Document Protocol Lab/)
  assert.match(companiesSource, /Open the NVDA fixture/)
  assert.match(companiesSource, /Choose the fixture that matches your goal\./)
  assert.match(companiesSource, /Choose by goal/)
  assert.match(companiesSource, /Back to Home thesis/)
  assert.match(companiesSource, /Why the chooser stays fixed/)
  assert.equal(companiesSource.includes("Current pilot fixtures"), false)
  assert.match(companySource, /Current pilot case/)
  assert.match(companySource, /Fixture role:/)
  assert.match(companySource, /Bounded SEC Item 1A pilot/)
  assert.match(companySource, /Read the filing answer first/)
  assert.match(companySource, /Back to 3 fixtures/)
  assert.match(useCaseGuideSource, /objective: "Strongest first signal"/)
  assert.match(useCaseGuideSource, /ticker: "NVDA"/)
  assert.match(useCaseGuideSource, /objective: "Policy-heavy bounded contrast"/)
  assert.match(useCaseGuideSource, /ticker: "LLY"/)
  assert.match(useCaseGuideSource, /objective: "Restraint \/ low-drift honesty check"/)
  assert.match(useCaseGuideSource, /ticker: "KO"/)
  assert.match(useCaseGuideSource, /What this fixture proves/)
  assert.match(labPanelSource, /Where methods agree/)
  assert.match(labPanelSource, /Scope boundary/)
  assert.match(labPanelSource, /Optional insight layer/)
  assert.match(pilotMatrixPanelSource, /Fresh vs reused/)
  assert.match(pilotMatrixPanelSource, /Primary read broad agreement/)
  assert.match(
    readmeSource,
    /Document Protocol Lab currently ships a bounded SEC Item 1A pilot across three fixtures: NVDA, LLY, and KO\./
  )

  for (const phrase of [
    "Choose a case",
    "Open case",
    "Start here if...",
    "Browse companies",
    "Visible reads",
  ]) {
    assert.equal(
      combinedText.includes(phrase),
      false,
      `visible story copy must not include stale phrase: ${phrase}`
    )
  }
})

test("README top blurb stays aligned with demo_share_v3", () => {
  const demoShare = readJson(
    "public/data/business_document_protocol_lab/product_positioning/demo_share_v3.json"
  )

  assert.equal(readmeSource.includes(demoShare.readme_blurb), true)
  assert.equal(readmeSource.includes("demo_share_v3.json"), true)
  assertNoStalePublicShorthand(readmeSource, "README")
})

test("page metadata stays coherent with the share artifact, static social tags, and asset links", () => {
  const demoShare = readJson(
    "public/data/business_document_protocol_lab/product_positioning/demo_share_v3.json"
  )

  assert.match(indexHtmlSource, /<title>Document Protocol Lab \| SEC Item 1A pilot<\/title>/)
  assert.match(indexHtmlSource, /meta\s+name="description"/)
  assert.match(indexHtmlSource, /property="og:title"/)
  assert.match(indexHtmlSource, /property="og:description"/)
  assert.match(indexHtmlSource, /property="og:type"/)
  assert.match(indexHtmlSource, /property="og:url"/)
  assert.match(indexHtmlSource, /property="og:image"/)
  assert.match(indexHtmlSource, /property="og:image:alt"/)
  assert.match(indexHtmlSource, /name="twitter:card"/)
  assert.match(indexHtmlSource, /name="twitter:title"/)
  assert.match(indexHtmlSource, /name="twitter:description"/)
  assert.match(indexHtmlSource, /name="twitter:image"/)
  assert.match(indexHtmlSource, /name="twitter:image:alt"/)
  assert.match(indexHtmlSource, /href="\.\/favicon\.svg"/)
  assert.match(indexHtmlSource, /href="\.\/apple-touch-icon\.png"/)
  assert.equal(indexHtmlSource.includes("vite.svg"), false)
  assert.equal(indexHtmlSource.includes(demoShare.canonical_share_title), true)
  assert.equal(indexHtmlSource.includes(demoShare.canonical_share_description), true)
  assert.equal(indexHtmlSource.includes(demoShare.canonical_external_url), true)
  assert.equal(indexHtmlSource.includes(demoShare.canonical_share_image_url), true)
  assert.equal(indexHtmlSource.includes(demoShare.canonical_share_image_alt), true)

  assert.match(pageMetadataSource, /document\.title = title/)
  assert.match(pageMetadataSource, /meta\.setAttribute\("content", description\)/)

  assert.match(homeSource, /Document Protocol Lab \| SEC Item 1A pilot/)
  assert.match(companiesSource, /Pilot Cases \| Document Protocol Lab/)
  assert.match(companySource, /\| Document Protocol Lab/)
  assert.match(homeSource, /PageMetadata/)
  assert.match(companiesSource, /PageMetadata/)
  assert.match(companySource, /PageMetadata/)
})

test("lab_cases_v1 separates visible pilot integration from legacy background cases", () => {
  const registry = readJson("public/data/sec_narrative_drift_lab/lab_cases_v1.json")

  assert.equal(Array.isArray(registry.notes), true)
  assert.equal(
    registry.notes.some((item) => String(item).includes("current_case_mix_v2.json")),
    true
  )
  assert.equal(
    registry.notes.some((item) => String(item).includes("start_here_v1.json")),
    true
  )
  assert.equal(registry.provenance.inputs.visible_pilot_tickers, "NVDA,LLY,KO")
  assert.equal(registry.provenance.inputs.visible_pilot_integrated_runtime_cases, "NVDA,KO")
  assert.equal(registry.provenance.inputs.visible_pilot_bounded_non_registry_cases, "LLY")

  const tickers = registry.cases.map((item) => item.ticker)
  assert.equal(tickers.includes("LLY"), false)

  const casesByTicker = new Map(registry.cases.map((item) => [item.ticker, item]))
  assert.ok(casesByTicker.get("NVDA")?.tags?.includes("visible_pilot_integrated"))
  assert.ok(casesByTicker.get("KO")?.tags?.includes("visible_pilot_integrated"))
  assert.ok(casesByTicker.get("WM")?.tags?.includes("legacy_background_case"))
  assert.ok(casesByTicker.get("GE")?.tags?.includes("legacy_background_case"))
})
