import { copy } from "./copy"
import {
  LabCasesRegistrySchema,
  LabLlmCampaignsIndexSchema,
  LabLlmVariantsIndexSchema,
  LabMethodProfilesIndexSchema,
  LabMethodTracksIndexSchema,
  LabOutputSchema,
} from "./labSchemas"
import { withBase } from "./paths"
import type { z } from "zod"
import type {
  LabCase,
  LabCasesRegistry,
  LabCaseOutputLink,
  LabCleaningLens,
  LabLlmCampaign,
  LabLlmCampaignsIndex,
  LabLlmVariant,
  LabLlmVariantsIndex,
  LabMethodProfile,
  LabMethodProfilesIndex,
  LabMethodTracksIndex,
  LabOutput,
  LabSourceId,
} from "./labTypes"

const LAB_BASE_PATH = withBase("data/sec_narrative_drift_lab")
const LAB_CASES_PATH = `${LAB_BASE_PATH}/lab_cases_v1.json`
const LAB_LLM_CAMPAIGNS_PATH = `${LAB_BASE_PATH}/lab_llm_campaigns_v1.json`
const LAB_LLM_VARIANTS_PATH = `${LAB_BASE_PATH}/lab_llm_variants_v1.json`
const LAB_METHOD_TRACKS_PATH = `${LAB_BASE_PATH}/lab_method_tracks_v1.json`
const LAB_METHOD_PROFILES_PATH = `${LAB_BASE_PATH}/lab_method_profiles_v1.json`
export const LAB_SHOWCASE_TICKERS = ["NVDA", "KO", "WM", "GE"] as const
const LLM_DETECTORS = new Set<string>([
  "det_llm_delta_brief_v1",
  "det_llm_excerpt_picker_v1",
])
const LAB_TICKER_RE = /^[A-Z0-9.-]{1,10}$/
const LLM_RUN_LABEL_RE = /^20\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])_[A-Za-z0-9._-]+$/
const LLM_PROVENANCE_KEYS = ["input_file", "model_provider", "model_name", "run_label"] as const
const URL_SCHEME_RE = /^[A-Za-z][A-Za-z0-9+.-]*:/
const DEFAULT_DETERMINISTIC_TRACK_SLUG = "det-baseline-2026-02-21"
const DEFAULT_PRIMARY_CAMPAIGN_ID = "openai_gpt53codex_xhigh_agent_fullsec_2026-02-22"
const DEFAULT_COMPARE_CAMPAIGN_ID = "openai_chatgpt52ext_agent_fullsec_2026-02-22"

function hasControlChars(value: string): boolean {
  for (let index = 0; index < value.length; index += 1) {
    const codePoint = value.charCodeAt(index)
    if (codePoint <= 0x1f || codePoint === 0x7f) return true
  }
  return false
}

export type LabExpectedOutputArtifact = {
  filename: string
  repoPath: string
  requestUrl: string
}

export type LabTickerSummary = {
  ticker: string
  caseCount: number
  recommendedCaseCount: number
  availableLenses: LabCleaningLens[]
  availableDetectors: string[]
  defaultPair: { from: number; to: number } | null
  latestPair: { from: number; to: number } | null
}

export class LabDataLoadError extends Error {
  readonly url: string
  readonly status?: number

  constructor(message: string, url: string, status?: number) {
    super(message)
    this.name = "LabDataLoadError"
    this.url = url
    this.status = status
  }
}

const outputCache = new Map<string, Promise<LabOutput>>()
const inputCache = new Map<string, Promise<unknown>>()
let casesPromise: Promise<LabCasesRegistry> | null = null
let llmCampaignsPromise: Promise<LabLlmCampaignsIndex> | null = null
let llmVariantsPromise: Promise<LabLlmVariantsIndex> | null = null
let methodTracksPromise: Promise<LabMethodTracksIndex> | null = null
let methodProfilesPromise: Promise<LabMethodProfilesIndex> | null = null

export function clearLabOutputCache(): void {
  outputCache.clear()
}

function normalizeTickerSymbol(ticker: string): string | null {
  const normalized = ticker.trim().toUpperCase()
  if (!LAB_TICKER_RE.test(normalized)) return null
  return normalized
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

type LlmExpectation = {
  campaignId?: string
  modelProvider?: string
  modelName?: string
}

function validateLlmStrictPayload(
  payload: LabOutput,
  label: string,
  url: string,
  expectation?: LlmExpectation
): void {
  if (!LLM_DETECTORS.has(payload.detector_id)) return

  const provenance = asRecord(payload.provenance)
  if (!provenance) {
    throw new LabDataLoadError(`Invalid ${label} payload (provenance must be an object).`, url)
  }
  const provenanceKeys = Object.keys(provenance).sort()
  const expectedProvenanceKeys = [...LLM_PROVENANCE_KEYS].sort()
  if (
    provenanceKeys.length !== expectedProvenanceKeys.length ||
    provenanceKeys.some((key, index) => key !== expectedProvenanceKeys[index])
  ) {
    throw new LabDataLoadError(
      `Invalid ${label} payload (LLM provenance keys must be exactly: ${expectedProvenanceKeys.join(", ")}).`,
      url
    )
  }

  const inputFile = provenance.input_file
  if (typeof inputFile !== "string" || inputFile.trim().length === 0) {
    throw new LabDataLoadError(
      `Invalid ${label} payload (provenance.input_file must be a non-empty string).`,
      url
    )
  }
  const modelProvider = provenance.model_provider
  if (typeof modelProvider !== "string" || modelProvider.trim().length === 0) {
    throw new LabDataLoadError(
      `Invalid ${label} payload (provenance.model_provider must be a non-empty string).`,
      url
    )
  }
  if (expectation?.modelProvider && modelProvider !== expectation.modelProvider) {
    throw new LabDataLoadError(
      `Invalid ${label} payload (provenance.model_provider must be "${expectation.modelProvider}").`,
      url
    )
  }
  const modelName = provenance.model_name
  if (typeof modelName !== "string" || modelName.trim().length === 0) {
    throw new LabDataLoadError(
      `Invalid ${label} payload (provenance.model_name must be a non-empty string).`,
      url
    )
  }
  if (expectation?.modelName && modelName !== expectation.modelName) {
    throw new LabDataLoadError(
      `Invalid ${label} payload (provenance.model_name must be "${expectation.modelName}").`,
      url
    )
  }
  const runLabel = provenance.run_label
  if (typeof runLabel !== "string" || LLM_RUN_LABEL_RE.test(runLabel) === false) {
    throw new LabDataLoadError(
      `Invalid ${label} payload (provenance.run_label must match YYYY-MM-DD_<campaign_tag>).`,
      url
    )
  }

  const artifacts = asRecord(payload.artifacts)
  if (!artifacts) {
    throw new LabDataLoadError(`Invalid ${label} payload (artifacts must be an object).`, url)
  }
  const artifactKeys = Object.keys(artifacts).sort()
  if (payload.detector_id === "det_llm_delta_brief_v1") {
    if (artifactKeys.length !== 1 || artifactKeys[0] !== "delta_brief") {
      throw new LabDataLoadError(
        `Invalid ${label} payload (artifacts must contain only delta_brief).`,
        url
      )
    }
    const deltaBrief = artifacts.delta_brief
    if (typeof deltaBrief !== "string" || deltaBrief.trim().length === 0) {
      throw new LabDataLoadError(
        `Invalid ${label} payload (artifacts.delta_brief must be a non-empty string).`,
        url
      )
    }
    return
  }

  if (
    artifactKeys.length !== 2 ||
    artifactKeys[0] !== "selected_curr" ||
    artifactKeys[1] !== "selected_prev"
  ) {
    throw new LabDataLoadError(
      `Invalid ${label} payload (artifacts must contain only selected_prev and selected_curr).`,
      url
    )
  }
  const selectedPrev = artifacts.selected_prev
  const selectedCurr = artifacts.selected_curr
  if (!Array.isArray(selectedPrev) || !Array.isArray(selectedCurr)) {
    throw new LabDataLoadError(
      `Invalid ${label} payload (selected_prev and selected_curr must be arrays).`,
      url
    )
  }
  const seenPrev = new Set<number>()
  for (const value of selectedPrev) {
    if (!Number.isInteger(value) || value < 0 || seenPrev.has(value)) {
      throw new LabDataLoadError(
        `Invalid ${label} payload (selected_prev must be deduped non-negative integers).`,
        url
      )
    }
    seenPrev.add(value)
  }
  const seenCurr = new Set<number>()
  for (const value of selectedCurr) {
    if (!Number.isInteger(value) || value < 0 || seenCurr.has(value)) {
      throw new LabDataLoadError(
        `Invalid ${label} payload (selected_curr must be deduped non-negative integers).`,
        url
      )
    }
    seenCurr.add(value)
  }
}

function normalizeOutputFilename(pathValue: string): string | null {
  const normalized = pathValue.replace(/\\/g, "/").replace(/^\.\/+/, "")
  if (!normalized || normalized.includes("..")) return null
  if (!normalized.startsWith("outputs/")) return null
  return normalized
}

function buildLabPath(ticker: string, filename: string): string | null {
  const normalizedTicker = normalizeTickerSymbol(ticker)
  if (!normalizedTicker) return null
  const normalized = normalizeOutputFilename(filename)
  if (!normalized) return null
  return `${LAB_BASE_PATH}/${normalizedTicker}/${normalized}`
}

export function buildLabOutputRequestUrl(ticker: string, filename: string): string | null {
  return buildLabPath(ticker, filename)
}

export function buildLabOutputRepoPath(ticker: string, filename: string): string | null {
  const normalizedTicker = normalizeTickerSymbol(ticker)
  if (!normalizedTicker) return null
  const normalized = normalizeOutputFilename(filename)
  if (!normalized) return null
  return `public/data/sec_narrative_drift_lab/${normalizedTicker}/${normalized}`
}

function normalizeInputPath(pathValue: string): string | null {
  const normalized = pathValue.trim().replace(/\\/g, "/").replace(/^\.\/+/, "")
  if (!normalized || normalized.includes("..")) return null
  if (hasControlChars(normalized)) return null
  if (URL_SCHEME_RE.test(normalized) || normalized.startsWith("//")) return null

  if (normalized.startsWith("data/")) {
    return withBase(normalized)
  }
  if (normalized.startsWith("public/")) {
    return withBase(normalized.replace(/^public\//, ""))
  }
  if (normalized.startsWith("bundles/")) {
    const bundleTail = normalized.replace(/^bundles\/[^/]+\/?/, "")
    if (!bundleTail) return null
    if (bundleTail.startsWith("inputs/")) {
      return withBase(`data/sec_narrative_drift_lab/llm_inputs_v2/${bundleTail}`)
    }
    const filename = bundleTail.split("/").pop()
    if (!filename) return null
    return withBase(`data/sec_narrative_drift_lab/llm_inputs/${filename}`)
  }
  if (normalized.startsWith("inputs/")) {
    return withBase(`data/sec_narrative_drift_lab/llm_inputs_v2/${normalized}`)
  }
  if (!normalized.includes("/")) {
    return withBase(`data/sec_narrative_drift_lab/llm_inputs/${normalized}`)
  }
  return withBase(`data/sec_narrative_drift_lab/${normalized}`)
}

export function buildLabInputRequestUrl(inputPath: string): string | null {
  return normalizeInputPath(inputPath)
}

if (import.meta.env.DEV) {
  const smokeActual = normalizeInputPath("inputs/NVDA/foo.json")
  const smokeExpected = `${LAB_BASE_PATH}/llm_inputs_v2/inputs/NVDA/foo.json`
  console.assert(
    smokeActual === smokeExpected,
    `normalizeInputPath smoke failed: expected ${smokeExpected}, got ${String(smokeActual)}`
  )
}

async function fetchJson<T>(
  url: string,
  userMessage: string,
  options?: { signal?: AbortSignal }
): Promise<T> {
  let response: Response

  try {
    response = await fetch(url, {
      headers: { Accept: "application/json" },
      cache: "no-store",
      signal: options?.signal,
    })
  } catch {
    throw new LabDataLoadError(userMessage, url)
  }

  if (!response.ok) {
    throw new LabDataLoadError(userMessage, url, response.status)
  }

  try {
    return (await response.json()) as T
  } catch {
    throw new LabDataLoadError(userMessage, url, response.status)
  }
}

function parseLabPayload<T>(
  schema: z.ZodType<T>,
  data: unknown,
  label: string,
  url: string
): T {
  const result = schema.safeParse(data)
  if (!result.success) {
    const firstIssue = result.error.issues[0]
    const issuePath =
      firstIssue && firstIssue.path.length > 0 ? firstIssue.path.join(".") : "<root>"
    const issueMessage = firstIssue ? firstIssue.message : "Unknown schema validation issue."
    throw new LabDataLoadError(
      `Invalid ${label} payload (${issuePath}: ${issueMessage}).`,
      url
    )
  }
  return result.data
}

function normalizeLabOutputPayload(data: unknown): unknown {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    return data
  }
  const record = data as Record<string, unknown>
  if ("section_id" in record) {
    return data
  }
  const section = record.section
  if (typeof section !== "string") {
    return data
  }
  return { ...record, section_id: section }
}

export async function loadLabCasesRegistry(): Promise<LabCasesRegistry> {
  if (!casesPromise) {
    casesPromise = fetchJson<unknown>(LAB_CASES_PATH, copy.global.errors.missingDataset).then(
      (data) => parseLabPayload(LabCasesRegistrySchema, data, "LabCasesRegistry", LAB_CASES_PATH)
    )
  }
  return casesPromise!
}

export async function loadLabLlmCampaignsIndex(): Promise<LabLlmCampaignsIndex> {
  if (!llmCampaignsPromise) {
    llmCampaignsPromise = fetchJson<unknown>(
      LAB_LLM_CAMPAIGNS_PATH,
      "LLM campaigns index is not available."
    ).then((data) =>
      parseLabPayload(
        LabLlmCampaignsIndexSchema,
        data,
        "LabLlmCampaignsIndex",
        LAB_LLM_CAMPAIGNS_PATH
      )
    )
  }
  return llmCampaignsPromise
}

export async function loadLabLlmVariantsIndex(): Promise<LabLlmVariantsIndex> {
  if (!llmVariantsPromise) {
    llmVariantsPromise = fetchJson<unknown>(
      LAB_LLM_VARIANTS_PATH,
      "LLM variants index is not available."
    ).then((data) =>
      parseLabPayload(
        LabLlmVariantsIndexSchema,
        data,
        "LabLlmVariantsIndex",
        LAB_LLM_VARIANTS_PATH
      )
    )
  }
  return llmVariantsPromise
}

export async function loadLabMethodTracksIndex(): Promise<LabMethodTracksIndex> {
  if (!methodTracksPromise) {
    methodTracksPromise = fetchJson<unknown>(
      LAB_METHOD_TRACKS_PATH,
      "Method tracks index is not available."
    ).then((data) =>
      parseLabPayload(
        LabMethodTracksIndexSchema,
        data,
        "LabMethodTracksIndex",
        LAB_METHOD_TRACKS_PATH
      )
    )
  }
  return methodTracksPromise
}

export async function loadLabMethodProfilesIndex(): Promise<LabMethodProfilesIndex> {
  if (!methodProfilesPromise) {
    methodProfilesPromise = fetchJson<unknown>(
      LAB_METHOD_PROFILES_PATH,
      "Method profiles index is not available."
    ).then((data) =>
      parseLabPayload(
        LabMethodProfilesIndexSchema,
        data,
        "LabMethodProfilesIndex",
        LAB_METHOD_PROFILES_PATH
      )
    )
  }
  return methodProfilesPromise
}

export async function listLabMethodProfiles(): Promise<LabMethodProfile[]> {
  const index = await loadLabMethodProfilesIndex()
  return index.profiles
}

export async function getLabMethodProfileByDetectorId(
  detectorId: string
): Promise<LabMethodProfile | null> {
  const index = await loadLabMethodProfilesIndex()
  for (const profile of index.profiles) {
    if (profile.detector_id === detectorId) {
      return profile
    }
  }
  return null
}

export async function listLabLlmCampaigns(): Promise<LabLlmCampaign[]> {
  const index = await loadLabLlmCampaignsIndex()
  const runtimeCampaigns = index.campaigns.filter(
    (campaign) =>
      campaign.runtime_visible !== false && campaign.input_mode !== "focuspack_v1"
  )
  return runtimeCampaigns.length > 0 ? runtimeCampaigns : index.campaigns
}

export async function getDefaultLabLlmCampaignPair(): Promise<{
  primaryCampaignId: string
  compareCampaignId: string
}> {
  const campaigns = await listLabLlmCampaigns()
  const index = await loadLabLlmCampaignsIndex()
  const primaryExists = campaigns.some(
    (campaign) => campaign.campaign_id === index.primary_campaign_id
  )
  const compareExists = campaigns.some(
    (campaign) => campaign.campaign_id === index.compare_default_campaign_id
  )
  return {
    primaryCampaignId: primaryExists
      ? index.primary_campaign_id
      : (campaigns[0]?.campaign_id ?? DEFAULT_PRIMARY_CAMPAIGN_ID),
    compareCampaignId: compareExists
      ? index.compare_default_campaign_id
      : (campaigns[1]?.campaign_id ??
        campaigns[0]?.campaign_id ??
        DEFAULT_COMPARE_CAMPAIGN_ID),
  }
}

export async function findLabLlmVariant(
  entry: Pick<LabCase, "ticker" | "section" | "year_from" | "year_to">,
  detectorId: string,
  lens: LabCleaningLens,
  campaignId: string
): Promise<LabLlmVariant | null> {
  const index = await loadLabLlmVariantsIndex()
  for (const variant of index.variants) {
    if (variant.ticker.toUpperCase() !== entry.ticker.toUpperCase()) continue
    if (variant.section !== entry.section) continue
    if (variant.year_from !== entry.year_from || variant.year_to !== entry.year_to) continue
    if (variant.detector_id !== detectorId) continue
    if (variant.lens !== lens) continue
    if (variant.campaign_id !== campaignId) continue
    return variant
  }
  return null
}

export async function getLabLlmCampaignById(campaignId: string): Promise<LabLlmCampaign | null> {
  const index = await loadLabLlmCampaignsIndex()
  for (const campaign of index.campaigns) {
    if (campaign.campaign_id === campaignId) {
      return campaign
    }
  }
  return null
}

export function getDefaultDeterministicTrackSlug(): string {
  return DEFAULT_DETERMINISTIC_TRACK_SLUG
}

export async function listLabCasesForTicker(ticker: string): Promise<LabCase[]> {
  const normalizedTicker = normalizeTickerSymbol(ticker)
  if (!normalizedTicker) return []
  const registry = await loadLabCasesRegistry()
  const filtered: LabCase[] = []
  for (const entry of registry.cases ?? []) {
    if (entry.ticker.toUpperCase() === normalizedTicker) {
      filtered.push(entry)
    }
  }
  return filtered
}

export function listLabShowcaseTickers(): string[] {
  return [...LAB_SHOWCASE_TICKERS]
}

export function isLabShowcaseTicker(ticker: string): boolean {
  const normalizedTicker = normalizeTickerSymbol(ticker)
  if (!normalizedTicker) return false
  return LAB_SHOWCASE_TICKERS.includes(
    normalizedTicker as (typeof LAB_SHOWCASE_TICKERS)[number]
  )
}

function compareCaseOrder(
  left: Pick<LabCase, "year_from" | "year_to">,
  right: Pick<LabCase, "year_from" | "year_to">
): number {
  if (left.year_to !== right.year_to) return left.year_to - right.year_to
  return left.year_from - right.year_from
}

function pickDefaultCase(entries: LabCase[]): LabCase | null {
  if (entries.length === 0) return null
  const sorted = [...entries].sort(compareCaseOrder)
  const recommended = sorted.filter((entry) => entry.tags?.includes("recommended"))
  if (recommended.length > 0) {
    return recommended[recommended.length - 1]
  }
  return sorted[sorted.length - 1]
}

function pickLatestCase(entries: LabCase[]): LabCase | null {
  if (entries.length === 0) return null
  const sorted = [...entries].sort(compareCaseOrder)
  return sorted[sorted.length - 1]
}

function pushUniqueLens(list: LabCleaningLens[], lens: LabCleaningLens): void {
  if (!list.includes(lens)) list.push(lens)
}

function pushUniqueDetector(list: string[], detectorId: string): void {
  if (!list.includes(detectorId)) list.push(detectorId)
}

type TickerBucket = {
  ticker: string
  entries: LabCase[]
}

export async function listLabTickerSummaries(options?: {
  showcaseOnly?: boolean
}): Promise<LabTickerSummary[]> {
  const registry = await loadLabCasesRegistry()
  const buckets = new Map<string, TickerBucket>()

  for (const entry of registry.cases ?? []) {
    const ticker = entry.ticker.toUpperCase()
    if (options?.showcaseOnly && !isLabShowcaseTicker(ticker)) continue
    const existing = buckets.get(ticker)
    if (existing) {
      existing.entries.push(entry)
    } else {
      buckets.set(ticker, { ticker, entries: [entry] })
    }
  }

  const summaries: LabTickerSummary[] = []
  for (const bucket of buckets.values()) {
    const defaultCase = pickDefaultCase(bucket.entries)
    const latestCase = pickLatestCase(bucket.entries)
    const availableLenses: LabCleaningLens[] = []
    const availableDetectors: string[] = []
    let recommendedCaseCount = 0

    for (const entry of bucket.entries) {
      if (entry.tags?.includes("recommended")) {
        recommendedCaseCount += 1
      }
      for (const output of entry.outputs ?? []) {
        pushUniqueLens(availableLenses, output.cleaning_lens)
        pushUniqueDetector(availableDetectors, output.detector_id)
      }
    }

    summaries.push({
      ticker: bucket.ticker,
      caseCount: bucket.entries.length,
      recommendedCaseCount,
      availableLenses,
      availableDetectors,
      defaultPair: defaultCase
        ? { from: defaultCase.year_from, to: defaultCase.year_to }
        : null,
      latestPair: latestCase ? { from: latestCase.year_from, to: latestCase.year_to } : null,
    })
  }

  const showcaseOrder = new Map<string, number>()
  LAB_SHOWCASE_TICKERS.forEach((ticker, index) => {
    showcaseOrder.set(ticker, index)
  })

  summaries.sort((left, right) => {
    const leftShowcaseRank = showcaseOrder.get(left.ticker)
    const rightShowcaseRank = showcaseOrder.get(right.ticker)
    if (leftShowcaseRank !== undefined && rightShowcaseRank !== undefined) {
      return leftShowcaseRank - rightShowcaseRank
    }
    if (leftShowcaseRank !== undefined) return -1
    if (rightShowcaseRank !== undefined) return 1
    return left.ticker.localeCompare(right.ticker)
  })

  return summaries
}

export function resolveLabOutputLink(
  entry: LabCase,
  detectorId: string,
  lens: LabCleaningLens,
  sourceId: LabSourceId
): LabCaseOutputLink | null {
  for (const output of entry.outputs ?? []) {
    if (
      output.detector_id === detectorId &&
      output.cleaning_lens === lens &&
      output.source_id === sourceId &&
      normalizeOutputFilename(output.filename)
    ) {
      return output
    }
  }
  return null
}

function buildCanonicalLabOutputFilename(
  entry: Pick<LabCase, "section" | "year_from" | "year_to">,
  detectorId: string,
  lens: LabCleaningLens,
  sourceId: LabSourceId,
  trackSlug: string
): string {
  const section = entry.section
  const yearFrom = entry.year_from
  const yearTo = entry.year_to
  const filename = `lab_${detectorId}_${section}_${yearFrom}_${yearTo}_${lens}_${sourceId}__${trackSlug}.json`
  return `outputs/${detectorId}/${trackSlug}/${filename}`
}

export function buildExpectedLabOutputArtifact(
  entry: Pick<LabCase, "ticker" | "section" | "year_from" | "year_to">,
  detectorId: string,
  lens: LabCleaningLens,
  sourceId: LabSourceId,
  trackSlug: string
): LabExpectedOutputArtifact | null {
  const filename = buildCanonicalLabOutputFilename(
    entry,
    detectorId,
    lens,
    sourceId,
    trackSlug
  )
  const requestUrl = buildLabOutputRequestUrl(entry.ticker, filename)
  const repoPath = buildLabOutputRepoPath(entry.ticker, filename)
  if (!requestUrl || !repoPath) return null
  return { filename, repoPath, requestUrl }
}

export function buildExpectedLabOutputArtifactFromVariant(
  variant: Pick<LabLlmVariant, "filename" | "expected_repo_path" | "request_url">
): LabExpectedOutputArtifact {
  return {
    filename: variant.filename,
    repoPath: variant.expected_repo_path,
    requestUrl: withBase(variant.request_url),
  }
}

export async function loadLabOutput(
  ticker: string,
  filename: string,
  options?: { signal?: AbortSignal; llmExpectation?: LlmExpectation }
): Promise<LabOutput> {
  const normalizedTicker = normalizeTickerSymbol(ticker)
  if (!normalizedTicker) {
    throw new LabDataLoadError("Ticker format is invalid for Lab output paths.", ticker)
  }
  const normalizedFilename = normalizeOutputFilename(filename)
  if (!normalizedFilename) {
    throw new LabDataLoadError("Output file path is not canonical.", filename)
  }
  const url = buildLabPath(normalizedTicker, filename)
  if (!url) {
    throw new LabDataLoadError("Output file path is not usable.", filename)
  }
  const expectationKey = options?.llmExpectation
    ? `|${options.llmExpectation.modelProvider ?? ""}|${options.llmExpectation.modelName ?? ""}`
    : ""
  const cacheKey = `${url}${expectationKey}`
  if (!outputCache.has(cacheKey)) {
    const promise = fetchJson<unknown>(url, copy.global.errors.missingDataset, options)
      .then((data) => {
        const output = parseLabPayload(
          LabOutputSchema,
          normalizeLabOutputPayload(data),
          `LabOutput:${normalizedFilename}`,
          url
        )
        validateLlmStrictPayload(
          output,
          `LabOutput:${normalizedFilename}`,
          url,
          options?.llmExpectation
        )
        return output
      })
      .catch((error) => {
        // Retry smoke (manual):
        // 1) First call rejects (404/invalid JSON) and evicts this URL from cache.
        // 2) After file/path is fixed, the next call re-fetches instead of reusing a stale rejection.
        outputCache.delete(cacheKey)
        throw error
      })
    outputCache.set(cacheKey, promise)
  }
  return outputCache.get(cacheKey)!
}

export async function loadLabInputFile(
  inputFile: string,
  options?: { signal?: AbortSignal }
): Promise<unknown> {
  const url = normalizeInputPath(inputFile)
  if (!url) {
    throw new LabDataLoadError("Input file path is not usable.", inputFile)
  }
  if (!inputCache.has(url)) {
    const promise = fetchJson<unknown>(url, "Input file not available.", options)
    inputCache.set(url, promise)
  }
  return inputCache.get(url)!
}

export function formatLabLoadDebug(error: unknown): string | null {
  if (error instanceof LabDataLoadError) {
    const statusText = typeof error.status === "number" ? ` (status ${error.status})` : ""
    return `${error.message} Requested path: ${error.url}${statusText}`
  }
  if (error instanceof Error) {
    return `Lab data error: ${error.message}`
  }
  return "Lab data error: unknown failure."
}
