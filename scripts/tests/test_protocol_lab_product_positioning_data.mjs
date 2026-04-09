import test from "node:test"
import assert from "node:assert/strict"
import { existsSync, readFileSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, "..", "..")

const appSource = readFileSync(path.join(repoRoot, "src", "App.tsx"), "utf8")
const headerSource = readFileSync(path.join(repoRoot, "src", "components", "AppHeader.tsx"), "utf8")
const homeSource = readFileSync(path.join(repoRoot, "src", "pages", "Home.tsx"), "utf8")
const companiesSource = readFileSync(path.join(repoRoot, "src", "pages", "Companies.tsx"), "utf8")
const companySource = readFileSync(path.join(repoRoot, "src", "pages", "Company.tsx"), "utf8")
const methodologySource = readFileSync(
  path.join(repoRoot, "src", "pages", "Methodology.tsx"),
  "utf8"
)
const labPanelSource = readFileSync(
  path.join(repoRoot, "src", "components", "LabPanel.tsx"),
  "utf8"
)
const routeFamilySource = readFileSync(
  path.join(repoRoot, "src", "lib", "routeFamilyUi.ts"),
  "utf8"
)
const casebookContentSource = readFileSync(
  path.join(repoRoot, "src", "lib", "casebookContent.ts"),
  "utf8"
)
const positioningSource = readFileSync(
  path.join(repoRoot, "src", "lib", "protocolLabProductPositioning.ts"),
  "utf8"
)
const pageMetadataSource = readFileSync(
  path.join(repoRoot, "src", "components", "PageMetadata.tsx"),
  "utf8"
)
const readmeSource = readFileSync(path.join(repoRoot, "README.md"), "utf8")
const indexHtmlSource = readFileSync(path.join(repoRoot, "index.html"), "utf8")

function readJson(relativePath) {
  return JSON.parse(readFileSync(path.join(repoRoot, relativePath), "utf8"))
}

function assertPathExists(relativePath) {
  assert.equal(existsSync(path.join(repoRoot, relativePath)), true, `${relativePath} must exist`)
}

function assertNonEmptyString(value, label) {
  assert.equal(typeof value, "string", `${label} must be a string`)
  assert.notEqual(value.trim(), "", `${label} must not be blank`)
}

test("current_case_mix_v2 stays aligned to the six public casebook cases", () => {
  const payload = readJson(
    "public/data/business_document_protocol_lab/product_positioning/current_case_mix_v2.json"
  )

  assert.equal(payload.artifact_schema_id, "current_case_mix_v2")
  assert.equal(payload.artifact_id, "current_case_mix_v2")
  assert.deepEqual(
    payload.visible_pilots.map((item) => item.ticker),
    ["NVDA", "LLY", "KO", "META", "TSLA", "WMT"]
  )
  assert.equal(payload.visible_pilots.some((item) => item.ticker === "GOOGL"), false)
  assert.equal(payload.visible_pilots.some((item) => item.ticker === "UNH"), false)

  for (const item of payload.visible_pilots) {
    assertNonEmptyString(item.company_name, `${item.ticker}.company_name`)
    assert.equal(typeof item.year_from, "number", `${item.ticker}.year_from`)
    assert.equal(typeof item.year_to, "number", `${item.ticker}.year_to`)
    assertNonEmptyString(item.role, `${item.ticker}.role`)
    assertNonEmptyString(item.role_label, `${item.ticker}.role_label`)
    assertNonEmptyString(item.why_case_exists, `${item.ticker}.why_case_exists`)
    assertNonEmptyString(item.best_for, `${item.ticker}.best_for`)
  }

  const wmt = payload.visible_pilots.find((item) => item.ticker === "WMT")
  assert.equal(wmt?.year_from, 2025)
  assert.equal(wmt?.year_to, 2026)
  assert.match(payload.product_statement, /interactive casebook/i)
  assert.match(payload.anti_hype_statement, /not a general document chatbot/i)
  assert.match(payload.why_this_mix_matters, /META, TSLA, and WMT/)
})

test("start_here_v1 stays aligned to the six-case public roster", () => {
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
  assert.deepEqual(alternativeTickers, expectedAlternativeTickers)
  assert.deepEqual(guidanceTickers, visibleTickers)
  assert.deepEqual(
    payload.reading_flow.map((item) => item.step),
    ["filing answer", "protocol meaning", "audit if needed"]
  )

  for (const item of payload.case_guidance) {
    assertNonEmptyString(item.why_pick, `${item.ticker}.why_pick`)
    assertNonEmptyString(item.what_you_learn, `${item.ticker}.what_you_learn`)
  }

  for (const item of currentCaseMix.visible_pilots) {
    const expectedHref = `/company/${item.ticker}?tab=lab&from=${item.year_from}&to=${item.year_to}`
    assert.match(
      expectedHref,
      /^\/company\/[A-Z0-9.-]+\?tab=lab&from=\d{4}&to=\d{4}$/,
      `${item.ticker} route must stay valid`
    )
  }
})

test("demo_share_v3 stays aligned with the current casebook metadata and share assets", () => {
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

  assert.match(demoShare.one_line_product_description, /interactive casebook/i)
  assert.match(demoShare.current_coverage_statement, /NVDA, LLY, KO, META, TSLA, and WMT/)
  assert.match(demoShare.canonical_share_title, /Interactive Casebook/)
  assert.equal(demoShare.canonical_external_url, "https://benlei.org/sec-narrative-drift/")
  assert.equal(
    demoShare.canonical_share_image_url.endsWith(demoShare.canonical_share_image_path),
    true
  )

  assertPathExists(`public/${demoShare.canonical_share_image_path}`)
  assertPathExists(`public/${demoShare.canonical_favicon_path}`)
  assertPathExists(`public/${demoShare.canonical_app_icon_path}`)
})

test("app sources stay aligned to Home, Casebook, and Methodology routing", () => {
  assert.match(appSource, /<Route path="\/companies" element={<Companies \/>} \/>/)
  assert.match(appSource, /<Route path="\/company\/:ticker" element={<Company \/>} \/>/)
  assert.match(headerSource, /{ to: "\/companies", label: "Casebook" }/)

  assert.match(casebookContentSource, /HOME_ANCHOR_TICKERS = \["NVDA", "LLY", "KO"\]/)
  assert.match(casebookContentSource, /PUBLIC_CASEBOOK_TICKERS = \["NVDA", "LLY", "KO", "META", "TSLA", "WMT"\]/)
  assert.match(routeFamilySource, /export \{ HOME_ANCHOR_TICKERS, PUBLIC_CASEBOOK_TICKERS \}/)
  assert.match(positioningSource, /EXPECTED_VISIBLE_TICKERS = PUBLIC_CASEBOOK_TICKERS/)
  assert.match(positioningSource, /buildProtocolLabCaseHref/)

  assert.match(homeSource, /HOME_ANCHOR_TICKERS/)
  assert.match(homeSource, /loadProtocolLabVisiblePilotSystem/)
  assert.match(homeSource, /ProtocolStageMap/)
  assert.match(homeSource, /casebookFraming\.home\.casebookEntryCta/)

  assert.match(companiesSource, /CASEBOOK_BANDS/)
  assert.match(companiesSource, /CasebookComparisonTable/)
  assert.match(companiesSource, /loadProtocolLabVisiblePilotSystem/)

  assert.match(companySource, /CaseTeachingLayer/)
  assert.match(companySource, /Back to Casebook/)

  assert.match(methodologySource, /casebookFraming\.methodology\.whyFrontierTitle/)
  assert.match(methodologySource, /casebookFraming\.methodology\.nonClaimsTitle/)
  assert.match(labPanelSource, /isMatrixFirstPublicTicker/)
})

test("README and static metadata stay aligned to the casebook framing", () => {
  const demoShare = readJson(
    "public/data/business_document_protocol_lab/product_positioning/demo_share_v3.json"
  )

  assert.match(readmeSource, /interactive casebook/i)
  assert.match(readmeSource, /six public SEC Item 1A cases/i)
  assert.match(readmeSource, /`GOOGL` remains reserve and `UNH` remains hold/i)

  assert.match(indexHtmlSource, /Document Protocol Lab \| Interactive Casebook/)
  assert.equal(indexHtmlSource.includes(demoShare.canonical_share_title), true)
  assert.equal(indexHtmlSource.includes(demoShare.canonical_share_description), true)
  assert.equal(indexHtmlSource.includes(demoShare.canonical_external_url), true)
  assert.equal(indexHtmlSource.includes(demoShare.canonical_share_image_url), true)
  assert.equal(indexHtmlSource.includes(demoShare.canonical_share_image_alt), true)

  assert.match(pageMetadataSource, /document\.title = title/)
  assert.match(pageMetadataSource, /meta\.setAttribute\("content", description\)/)
})
