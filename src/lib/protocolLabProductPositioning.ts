import { withBase } from "./paths"
import { PUBLIC_CASEBOOK_TICKERS } from "./casebookContent"

const PRODUCT_POSITIONING_ROOT = withBase("data/business_document_protocol_lab/product_positioning")
const CURRENT_CASE_MIX_PATH = `${PRODUCT_POSITIONING_ROOT}/current_case_mix_v2.json`
const START_HERE_PATH = `${PRODUCT_POSITIONING_ROOT}/start_here_v1.json`
const DEMO_SHARE_V2_PATH = `${PRODUCT_POSITIONING_ROOT}/demo_share_v2.json`
const DEMO_SHARE_V3_PATH = `${PRODUCT_POSITIONING_ROOT}/demo_share_v3.json`
const EXPECTED_VISIBLE_TICKERS = PUBLIC_CASEBOOK_TICKERS
const EXPECTED_READING_FLOW_STEPS = [
  "filing answer",
  "protocol meaning",
  "audit if needed",
] as const

export type ProtocolLabVisiblePilot = {
  ticker: string
  company_name: string
  year_from: number
  year_to: number
  role: string
  role_label: string
  why_case_exists: string
  best_for: string
}

export type ProtocolLabCurrentCaseMix = {
  artifact_schema_id: "current_case_mix_v2"
  artifact_id: "current_case_mix_v2"
  visible_pilots: ProtocolLabVisiblePilot[]
  product_statement: string
  anti_hype_statement: string
  why_this_mix_matters: string
}

export type ProtocolLabStartHereChoice = {
  ticker: string
  why_pick: string
  what_you_learn: string
}

export type ProtocolLabReadingFlowStep = {
  step: string
  description: string
}

export type ProtocolLabStartHere = {
  artifact_schema_id: "start_here_v1"
  artifact_id: "start_here_v1"
  recommended_first_case: string
  alternative_first_cases: ProtocolLabStartHereChoice[]
  case_guidance: ProtocolLabStartHereChoice[]
  reading_flow: ProtocolLabReadingFlowStep[]
}

type ProtocolLabDemoShareBase = {
  one_line_product_description: string
  short_subhead: string
  current_coverage_statement: string
  three_case_mix_usefulness_statement: string
  where_to_start_statement: string
  external_demo_blurb: string
  readme_blurb: string
  meta_description_candidate: string
  social_share_caption_candidate: string
}

export type ProtocolLabDemoShareV2 = ProtocolLabDemoShareBase & {
  artifact_schema_id: "demo_share_v2"
  artifact_id: "demo_share_v2"
}

export type ProtocolLabDemoShareV3 = ProtocolLabDemoShareBase & {
  artifact_schema_id: "demo_share_v3"
  artifact_id: "demo_share_v3"
  canonical_share_title: string
  canonical_share_description: string
  canonical_external_url: string
  canonical_share_image_path: string
  canonical_share_image_url: string
  canonical_share_image_alt: string
  canonical_favicon_path: string
  canonical_app_icon_path: string
}

export type ProtocolLabVisiblePilotEntry = ProtocolLabVisiblePilot & {
  guidance: ProtocolLabStartHereChoice
  href: string
  is_recommended_first_case: boolean
}

export type ProtocolLabVisiblePilotSystem = {
  currentCaseMix: ProtocolLabCurrentCaseMix
  startHere: ProtocolLabStartHere
  visiblePilots: ProtocolLabVisiblePilotEntry[]
  recommendedPilot: ProtocolLabVisiblePilotEntry
  alternativeFirstPilots: ProtocolLabVisiblePilotEntry[]
}

export type ProtocolLabLandingPositioning = ProtocolLabVisiblePilotSystem

export class ProtocolLabProductPositioningLoadError extends Error {
  readonly url: string
  readonly status?: number

  constructor(message: string, url: string, status?: number) {
    super(message)
    this.name = "ProtocolLabProductPositioningLoadError"
    this.url = url
    this.status = status
  }
}

let currentCaseMixPromise: Promise<ProtocolLabCurrentCaseMix> | null = null
let startHerePromise: Promise<ProtocolLabStartHere> | null = null
let demoShareV2Promise: Promise<ProtocolLabDemoShareV2> | null = null
let demoShareV3Promise: Promise<ProtocolLabDemoShareV3> | null = null
let visiblePilotSystemPromise: Promise<ProtocolLabVisiblePilotSystem> | null = null

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function normalizeTicker(ticker: string): string {
  return ticker.trim().toUpperCase()
}

async function fetchJson<T>(url: string, userMessage: string): Promise<T> {
  let response: Response

  try {
    response = await fetch(url, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    })
  } catch {
    throw new ProtocolLabProductPositioningLoadError(userMessage, url)
  }

  if (!response.ok) {
    throw new ProtocolLabProductPositioningLoadError(userMessage, url, response.status)
  }

  try {
    return (await response.json()) as T
  } catch {
    throw new ProtocolLabProductPositioningLoadError(userMessage, url, response.status)
  }
}

function readRequiredString(
  record: Record<string, unknown>,
  key: string,
  label: string,
  url: string
): string {
  const value = record[key]
  if (typeof value !== "string" || value.trim() === "") {
    throw new ProtocolLabProductPositioningLoadError(
      `Invalid ${label} payload (${key} must be a non-empty string).`,
      url
    )
  }
  return value.trim()
}

function readRequiredNumber(
  record: Record<string, unknown>,
  key: string,
  label: string,
  url: string
): number {
  const value = record[key]
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new ProtocolLabProductPositioningLoadError(
      `Invalid ${label} payload (${key} must be a finite number).`,
      url
    )
  }
  return value
}

function readRequiredArray(
  record: Record<string, unknown>,
  key: string,
  label: string,
  url: string
): unknown[] {
  const value = record[key]
  if (!Array.isArray(value)) {
    throw new ProtocolLabProductPositioningLoadError(
      `Invalid ${label} payload (${key} must be an array).`,
      url
    )
  }
  return value
}

function expectExactTickerOrder(
  items: Array<{ ticker: string }>,
  expectedTickers: readonly string[],
  label: string,
  url: string
): void {
  if (items.length !== expectedTickers.length) {
    throw new ProtocolLabProductPositioningLoadError(
      `Invalid ${label} payload (expected ${expectedTickers.length} ticker entries).`,
      url
    )
  }

  for (let index = 0; index < expectedTickers.length; index += 1) {
    if (items[index]?.ticker !== expectedTickers[index]) {
      throw new ProtocolLabProductPositioningLoadError(
        `Invalid ${label} payload (ticker order must be ${expectedTickers.join(", ")}).`,
        url
      )
    }
  }
}

function expectUniqueTickerCoverage(
  items: Array<{ ticker: string }>,
  expectedTickers: readonly string[],
  label: string,
  url: string
): void {
  const expectedSet = new Set(expectedTickers)
  const seen = new Set<string>()

  for (const item of items) {
    if (!expectedSet.has(item.ticker)) {
      throw new ProtocolLabProductPositioningLoadError(
        `Invalid ${label} payload (unexpected ticker ${item.ticker}).`,
        url
      )
    }
    if (seen.has(item.ticker)) {
      throw new ProtocolLabProductPositioningLoadError(
        `Invalid ${label} payload (duplicate ticker ${item.ticker}).`,
        url
      )
    }
    seen.add(item.ticker)
  }

  for (const ticker of expectedTickers) {
    if (!seen.has(ticker)) {
      throw new ProtocolLabProductPositioningLoadError(
        `Invalid ${label} payload (missing ticker ${ticker}).`,
        url
      )
    }
  }
}

function parseVisiblePilotArray(data: unknown, url: string): ProtocolLabVisiblePilot[] {
  if (!Array.isArray(data)) {
    throw new ProtocolLabProductPositioningLoadError(
      "Invalid current_case_mix_v2 payload (visible_pilots must be an array).",
      url
    )
  }

  const pilots: ProtocolLabVisiblePilot[] = []
  for (let index = 0; index < data.length; index += 1) {
    const item = data[index]
    if (!isRecord(item)) {
      throw new ProtocolLabProductPositioningLoadError(
        "Invalid current_case_mix_v2 payload (visible_pilots entries must be objects).",
        url
      )
    }

    pilots.push({
      ticker: normalizeTicker(readRequiredString(item, "ticker", "current_case_mix_v2", url)),
      company_name: readRequiredString(item, "company_name", "current_case_mix_v2", url),
      year_from: readRequiredNumber(item, "year_from", "current_case_mix_v2", url),
      year_to: readRequiredNumber(item, "year_to", "current_case_mix_v2", url),
      role: readRequiredString(item, "role", "current_case_mix_v2", url),
      role_label: readRequiredString(item, "role_label", "current_case_mix_v2", url),
      why_case_exists: readRequiredString(item, "why_case_exists", "current_case_mix_v2", url),
      best_for: readRequiredString(item, "best_for", "current_case_mix_v2", url),
    })
  }

  expectExactTickerOrder(pilots, EXPECTED_VISIBLE_TICKERS, "current_case_mix_v2", url)
  return pilots
}

function parseStartHereChoiceArray(
  data: unknown,
  label: string,
  url: string
): ProtocolLabStartHereChoice[] {
  if (!Array.isArray(data)) {
    throw new ProtocolLabProductPositioningLoadError(
      `Invalid ${label} payload (entries must be an array).`,
      url
    )
  }

  const choices: ProtocolLabStartHereChoice[] = []
  for (let index = 0; index < data.length; index += 1) {
    const item = data[index]
    if (!isRecord(item)) {
      throw new ProtocolLabProductPositioningLoadError(
        `Invalid ${label} payload (entries must be objects).`,
        url
      )
    }

    choices.push({
      ticker: normalizeTicker(readRequiredString(item, "ticker", label, url)),
      why_pick: readRequiredString(item, "why_pick", label, url),
      what_you_learn: readRequiredString(item, "what_you_learn", label, url),
    })
  }

  return choices
}

function parseReadingFlowArray(data: unknown, url: string): ProtocolLabReadingFlowStep[] {
  if (!Array.isArray(data)) {
    throw new ProtocolLabProductPositioningLoadError(
      "Invalid start_here_v1 payload (reading_flow must be an array).",
      url
    )
  }

  const steps: ProtocolLabReadingFlowStep[] = []
  for (let index = 0; index < data.length; index += 1) {
    const item = data[index]
    if (!isRecord(item)) {
      throw new ProtocolLabProductPositioningLoadError(
        "Invalid start_here_v1 payload (reading_flow entries must be objects).",
        url
      )
    }

    steps.push({
      step: readRequiredString(item, "step", "start_here_v1", url),
      description: readRequiredString(item, "description", "start_here_v1", url),
    })
  }

  if (steps.length !== EXPECTED_READING_FLOW_STEPS.length) {
    throw new ProtocolLabProductPositioningLoadError(
      `Invalid start_here_v1 payload (reading_flow must contain ${EXPECTED_READING_FLOW_STEPS.length} steps).`,
      url
    )
  }

  for (let index = 0; index < EXPECTED_READING_FLOW_STEPS.length; index += 1) {
    if (steps[index]?.step !== EXPECTED_READING_FLOW_STEPS[index]) {
      throw new ProtocolLabProductPositioningLoadError(
        `Invalid start_here_v1 payload (reading_flow step order must be ${EXPECTED_READING_FLOW_STEPS.join(", ")}).`,
        url
      )
    }
  }

  return steps
}

function parseCurrentCaseMix(data: unknown, url: string): ProtocolLabCurrentCaseMix {
  if (!isRecord(data)) {
    throw new ProtocolLabProductPositioningLoadError(
      "Invalid current_case_mix_v2 payload (<root> must be an object).",
      url
    )
  }

  const artifactSchemaId = readRequiredString(data, "artifact_schema_id", "current_case_mix_v2", url)
  const artifactId = readRequiredString(data, "artifact_id", "current_case_mix_v2", url)
  if (artifactSchemaId !== "current_case_mix_v2" || artifactId !== "current_case_mix_v2") {
    throw new ProtocolLabProductPositioningLoadError(
      "Invalid current_case_mix_v2 payload (artifact ids must be current_case_mix_v2).",
      url
    )
  }

  return {
    artifact_schema_id: "current_case_mix_v2",
    artifact_id: "current_case_mix_v2",
    visible_pilots: parseVisiblePilotArray(
      readRequiredArray(data, "visible_pilots", "current_case_mix_v2", url),
      url
    ),
    product_statement: readRequiredString(data, "product_statement", "current_case_mix_v2", url),
    anti_hype_statement: readRequiredString(data, "anti_hype_statement", "current_case_mix_v2", url),
    why_this_mix_matters: readRequiredString(data, "why_this_mix_matters", "current_case_mix_v2", url),
  }
}

function parseStartHere(data: unknown, url: string): ProtocolLabStartHere {
  if (!isRecord(data)) {
    throw new ProtocolLabProductPositioningLoadError(
      "Invalid start_here_v1 payload (<root> must be an object).",
      url
    )
  }

  const artifactSchemaId = readRequiredString(data, "artifact_schema_id", "start_here_v1", url)
  const artifactId = readRequiredString(data, "artifact_id", "start_here_v1", url)
  if (artifactSchemaId !== "start_here_v1" || artifactId !== "start_here_v1") {
    throw new ProtocolLabProductPositioningLoadError(
      "Invalid start_here_v1 payload (artifact ids must be start_here_v1).",
      url
    )
  }

  const recommendedFirstCase = normalizeTicker(
    readRequiredString(data, "recommended_first_case", "start_here_v1", url)
  )
  if (!EXPECTED_VISIBLE_TICKERS.includes(recommendedFirstCase as (typeof EXPECTED_VISIBLE_TICKERS)[number])) {
    throw new ProtocolLabProductPositioningLoadError(
      `Invalid start_here_v1 payload (recommended_first_case must be one of ${EXPECTED_VISIBLE_TICKERS.join(", ")}).`,
      url
    )
  }

  const alternativeFirstCases = parseStartHereChoiceArray(
    readRequiredArray(data, "alternative_first_cases", "start_here_v1", url),
    "start_here_v1",
    url
  )
  const expectedAlternatives = EXPECTED_VISIBLE_TICKERS.filter(
    (ticker) => ticker !== recommendedFirstCase
  )
  expectUniqueTickerCoverage(alternativeFirstCases, expectedAlternatives, "start_here_v1", url)

  const caseGuidance = parseStartHereChoiceArray(
    readRequiredArray(data, "case_guidance", "start_here_v1", url),
    "start_here_v1",
    url
  )
  expectUniqueTickerCoverage(caseGuidance, EXPECTED_VISIBLE_TICKERS, "start_here_v1", url)

  return {
    artifact_schema_id: "start_here_v1",
    artifact_id: "start_here_v1",
    recommended_first_case: recommendedFirstCase,
    alternative_first_cases: alternativeFirstCases,
    case_guidance: caseGuidance,
    reading_flow: parseReadingFlowArray(
      readRequiredArray(data, "reading_flow", "start_here_v1", url),
      url
    ),
  }
}

function parseDemoShareV2(data: unknown, url: string): ProtocolLabDemoShareV2 {
  if (!isRecord(data)) {
    throw new ProtocolLabProductPositioningLoadError(
      "Invalid demo_share_v2 payload (<root> must be an object).",
      url
    )
  }

  const artifactSchemaId = readRequiredString(data, "artifact_schema_id", "demo_share_v2", url)
  const artifactId = readRequiredString(data, "artifact_id", "demo_share_v2", url)
  if (artifactSchemaId !== "demo_share_v2" || artifactId !== "demo_share_v2") {
    throw new ProtocolLabProductPositioningLoadError(
      "Invalid demo_share_v2 payload (artifact ids must be demo_share_v2).",
      url
    )
  }

  return {
    artifact_schema_id: "demo_share_v2",
    artifact_id: "demo_share_v2",
    ...readDemoShareBaseFields(data, "demo_share_v2", url),
  }
}

function readDemoShareBaseFields(
  data: Record<string, unknown>,
  label: "demo_share_v2" | "demo_share_v3",
  url: string
): ProtocolLabDemoShareBase {
  return {
    one_line_product_description: readRequiredString(
      data,
      "one_line_product_description",
      label,
      url
    ),
    short_subhead: readRequiredString(data, "short_subhead", label, url),
    current_coverage_statement: readRequiredString(data, "current_coverage_statement", label, url),
    three_case_mix_usefulness_statement: readRequiredString(
      data,
      "three_case_mix_usefulness_statement",
      label,
      url
    ),
    where_to_start_statement: readRequiredString(data, "where_to_start_statement", label, url),
    external_demo_blurb: readRequiredString(data, "external_demo_blurb", label, url),
    readme_blurb: readRequiredString(data, "readme_blurb", label, url),
    meta_description_candidate: readRequiredString(data, "meta_description_candidate", label, url),
    social_share_caption_candidate: readRequiredString(
      data,
      "social_share_caption_candidate",
      label,
      url
    ),
  }
}

function parseDemoShareV3(data: unknown, url: string): ProtocolLabDemoShareV3 {
  if (!isRecord(data)) {
    throw new ProtocolLabProductPositioningLoadError(
      "Invalid demo_share_v3 payload (<root> must be an object).",
      url
    )
  }

  const artifactSchemaId = readRequiredString(data, "artifact_schema_id", "demo_share_v3", url)
  const artifactId = readRequiredString(data, "artifact_id", "demo_share_v3", url)
  if (artifactSchemaId !== "demo_share_v3" || artifactId !== "demo_share_v3") {
    throw new ProtocolLabProductPositioningLoadError(
      "Invalid demo_share_v3 payload (artifact ids must be demo_share_v3).",
      url
    )
  }

  return {
    artifact_schema_id: "demo_share_v3",
    artifact_id: "demo_share_v3",
    ...readDemoShareBaseFields(data, "demo_share_v3", url),
    canonical_share_title: readRequiredString(data, "canonical_share_title", "demo_share_v3", url),
    canonical_share_description: readRequiredString(
      data,
      "canonical_share_description",
      "demo_share_v3",
      url
    ),
    canonical_external_url: readRequiredString(
      data,
      "canonical_external_url",
      "demo_share_v3",
      url
    ),
    canonical_share_image_path: readRequiredString(
      data,
      "canonical_share_image_path",
      "demo_share_v3",
      url
    ),
    canonical_share_image_url: readRequiredString(
      data,
      "canonical_share_image_url",
      "demo_share_v3",
      url
    ),
    canonical_share_image_alt: readRequiredString(
      data,
      "canonical_share_image_alt",
      "demo_share_v3",
      url
    ),
    canonical_favicon_path: readRequiredString(
      data,
      "canonical_favicon_path",
      "demo_share_v3",
      url
    ),
    canonical_app_icon_path: readRequiredString(
      data,
      "canonical_app_icon_path",
      "demo_share_v3",
      url
    ),
  }
}

export function buildProtocolLabCaseHref(
  ticker: string,
  yearFrom: number,
  yearTo: number
): string {
  return `/company/${normalizeTicker(ticker)}?tab=lab&from=${yearFrom}&to=${yearTo}`
}

function buildVisiblePilotSystem(
  currentCaseMix: ProtocolLabCurrentCaseMix,
  startHere: ProtocolLabStartHere
): ProtocolLabVisiblePilotSystem {
  const guidanceByTicker = new Map<string, ProtocolLabStartHereChoice>()
  for (const choice of startHere.case_guidance) {
    guidanceByTicker.set(choice.ticker, choice)
  }

  const alternativeByTicker = new Map<string, ProtocolLabStartHereChoice>()
  for (const choice of startHere.alternative_first_cases) {
    alternativeByTicker.set(choice.ticker, choice)
  }

  const visiblePilots = currentCaseMix.visible_pilots.map((pilot) => {
    const guidance = guidanceByTicker.get(pilot.ticker)
    if (!guidance) {
      throw new ProtocolLabProductPositioningLoadError(
        `Invalid visible pilot system payload (missing case guidance for ${pilot.ticker}).`,
        START_HERE_PATH
      )
    }

    return {
      ...pilot,
      guidance,
      href: buildProtocolLabCaseHref(pilot.ticker, pilot.year_from, pilot.year_to),
      is_recommended_first_case: pilot.ticker === startHere.recommended_first_case,
    }
  })

  const recommendedPilot = visiblePilots.find(
    (pilot) => pilot.ticker === startHere.recommended_first_case
  )
  if (!recommendedPilot) {
    throw new ProtocolLabProductPositioningLoadError(
      "Invalid visible pilot system payload (recommended first case is not a visible pilot).",
      START_HERE_PATH
    )
  }

  const alternativeFirstPilots = visiblePilots.filter(
    (pilot) => pilot.ticker !== recommendedPilot.ticker
  )
  for (const pilot of alternativeFirstPilots) {
    if (!alternativeByTicker.has(pilot.ticker)) {
      throw new ProtocolLabProductPositioningLoadError(
        `Invalid visible pilot system payload (missing alternate first-case guidance for ${pilot.ticker}).`,
        START_HERE_PATH
      )
    }
  }

  return {
    currentCaseMix,
    startHere,
    visiblePilots,
    recommendedPilot,
    alternativeFirstPilots,
  }
}

export async function loadProtocolLabCurrentCaseMix(): Promise<ProtocolLabCurrentCaseMix> {
  if (!currentCaseMixPromise) {
    currentCaseMixPromise = fetchJson<unknown>(
      CURRENT_CASE_MIX_PATH,
      "Current case mix artifact is not available."
    ).then((data) => parseCurrentCaseMix(data, CURRENT_CASE_MIX_PATH))
  }

  return currentCaseMixPromise
}

export async function loadProtocolLabStartHere(): Promise<ProtocolLabStartHere> {
  if (!startHerePromise) {
    startHerePromise = fetchJson<unknown>(
      START_HERE_PATH,
      "Start-here artifact is not available."
    ).then((data) => parseStartHere(data, START_HERE_PATH))
  }

  return startHerePromise
}

export async function loadProtocolLabDemoShareV2(): Promise<ProtocolLabDemoShareV2> {
  if (!demoShareV2Promise) {
    demoShareV2Promise = fetchJson<unknown>(
      DEMO_SHARE_V2_PATH,
      "Demo/share metadata is not available."
    ).then((data) => parseDemoShareV2(data, DEMO_SHARE_V2_PATH))
  }

  return demoShareV2Promise
}

export async function loadProtocolLabDemoShareV3(): Promise<ProtocolLabDemoShareV3> {
  if (!demoShareV3Promise) {
    demoShareV3Promise = fetchJson<unknown>(
      DEMO_SHARE_V3_PATH,
      "Demo/share metadata is not available."
    ).then((data) => parseDemoShareV3(data, DEMO_SHARE_V3_PATH))
  }

  return demoShareV3Promise
}

export async function loadProtocolLabVisiblePilotSystem(): Promise<ProtocolLabVisiblePilotSystem> {
  if (!visiblePilotSystemPromise) {
    visiblePilotSystemPromise = Promise.all([
      loadProtocolLabCurrentCaseMix(),
      loadProtocolLabStartHere(),
    ]).then(([currentCaseMix, startHere]) => buildVisiblePilotSystem(currentCaseMix, startHere))
  }

  return visiblePilotSystemPromise
}

export async function loadProtocolLabLandingPositioning(): Promise<ProtocolLabLandingPositioning> {
  return loadProtocolLabVisiblePilotSystem()
}

export function findProtocolLabVisiblePilot(
  currentCaseMix: ProtocolLabCurrentCaseMix,
  ticker: string
): ProtocolLabVisiblePilot | null {
  const normalizedTicker = normalizeTicker(ticker)
  for (const pilot of currentCaseMix.visible_pilots) {
    if (pilot.ticker === normalizedTicker) return pilot
  }
  return null
}

export function findProtocolLabStartHereChoice(
  startHere: ProtocolLabStartHere,
  ticker: string
): ProtocolLabStartHereChoice | null {
  const normalizedTicker = normalizeTicker(ticker)
  for (const choice of startHere.case_guidance) {
    if (choice.ticker === normalizedTicker) return choice
  }
  return null
}

export function findProtocolLabVisiblePilotEntry(
  visiblePilotSystem: ProtocolLabVisiblePilotSystem,
  ticker: string
): ProtocolLabVisiblePilotEntry | null {
  const normalizedTicker = normalizeTicker(ticker)
  for (const pilot of visiblePilotSystem.visiblePilots) {
    if (pilot.ticker === normalizedTicker) return pilot
  }
  return null
}

export function listProtocolLabVisiblePilots(
  visiblePilotSystem: ProtocolLabVisiblePilotSystem
): ProtocolLabVisiblePilotEntry[] {
  return visiblePilotSystem.visiblePilots
}

export function getProtocolLabRecommendedPilot(
  visiblePilotSystem: ProtocolLabVisiblePilotSystem
): ProtocolLabVisiblePilotEntry {
  return visiblePilotSystem.recommendedPilot
}
