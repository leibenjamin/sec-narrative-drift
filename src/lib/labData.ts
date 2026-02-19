import { copy } from "./copy"
import { LabCasesRegistrySchema, LabOutputSchema } from "./labSchemas"
import { withBase } from "./paths"
import type { z } from "zod"
import type {
  LabCase,
  LabCasesRegistry,
  LabCaseOutputLink,
  LabCleaningLens,
  LabOutput,
  LabSourceId,
} from "./labTypes"

const LAB_BASE_PATH = withBase("data/sec_narrative_drift_lab")
const LAB_CASES_PATH = `${LAB_BASE_PATH}/lab_cases_v1.json`
export const LAB_SHOWCASE_TICKERS = ["NVDA", "KO", "WM", "GE"] as const
const LLM_DETECTORS = new Set<string>([
  "det_llm_delta_brief_v1",
  "det_llm_excerpt_picker_v1",
])

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

export function clearLabOutputCache(): void {
  outputCache.clear()
}

function normalizeOutputFilename(pathValue: string): string | null {
  const normalized = pathValue.replace(/\\/g, "/").replace(/^\.\/+/, "")
  if (!normalized || normalized.includes("..")) return null
  if (!normalized.startsWith("outputs/")) return null
  return normalized
}

function buildLabPath(ticker: string, filename: string): string | null {
  const normalized = normalizeOutputFilename(filename)
  if (!normalized) return null
  return `${LAB_BASE_PATH}/${ticker.toUpperCase()}/${normalized}`
}

export function buildLabOutputRequestUrl(ticker: string, filename: string): string | null {
  return buildLabPath(ticker, filename)
}

export function buildLabOutputRepoPath(ticker: string, filename: string): string | null {
  const normalized = normalizeOutputFilename(filename)
  if (!normalized) return null
  return `public/data/sec_narrative_drift_lab/${ticker.toUpperCase()}/${normalized}`
}

function normalizeInputPath(pathValue: string): string | null {
  const normalized = pathValue.replace(/\\/g, "/").replace(/^\.\/+/, "")
  if (!normalized || normalized.includes("..")) return null

  if (normalized.startsWith("data/")) {
    return withBase(normalized)
  }
  if (normalized.startsWith("public/")) {
    return withBase(normalized.replace(/^public\//, ""))
  }
  if (normalized.startsWith("bundles/")) {
    const filename = normalized.split("/").pop()
    if (!filename) return null
    return withBase(`data/sec_narrative_drift_lab/llm_inputs/${filename}`)
  }
  if (normalized.startsWith("inputs/")) {
    const filename = normalized.split("/").pop()
    if (!filename) return null
    return withBase(`data/sec_narrative_drift_lab/llm_inputs/${filename}`)
  }
  if (!normalized.includes("/")) {
    return withBase(`data/sec_narrative_drift_lab/llm_inputs/${normalized}`)
  }
  return withBase(`data/sec_narrative_drift_lab/${normalized}`)
}

if (import.meta.env.DEV) {
  const smokeActual = normalizeInputPath("inputs/NVDA/foo.json")
  const smokeExpected = `${LAB_BASE_PATH}/llm_inputs/foo.json`
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

export async function listLabCasesForTicker(ticker: string): Promise<LabCase[]> {
  const registry = await loadLabCasesRegistry()
  const filtered: LabCase[] = []
  for (const entry of registry.cases ?? []) {
    if (entry.ticker.toUpperCase() === ticker.toUpperCase()) {
      filtered.push(entry)
    }
  }
  return filtered
}

export function listLabShowcaseTickers(): string[] {
  return [...LAB_SHOWCASE_TICKERS]
}

export function isLabShowcaseTicker(ticker: string): boolean {
  return LAB_SHOWCASE_TICKERS.includes(ticker.toUpperCase() as (typeof LAB_SHOWCASE_TICKERS)[number])
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
  sourceId: LabSourceId
): string {
  const section = entry.section
  const yearFrom = entry.year_from
  const yearTo = entry.year_to
  if (LLM_DETECTORS.has(detectorId)) {
    return `outputs/${detectorId}/lab_${detectorId}_${section}_${yearFrom}_${yearTo}_focuspack_${lens}.json`
  }
  return `outputs/${detectorId}/lab_${section}_${yearFrom}_${yearTo}_${detectorId}_${lens}_${sourceId}.json`
}

export function buildExpectedLabOutputArtifact(
  entry: Pick<LabCase, "ticker" | "section" | "year_from" | "year_to">,
  detectorId: string,
  lens: LabCleaningLens,
  sourceId: LabSourceId
): LabExpectedOutputArtifact | null {
  const filename = buildCanonicalLabOutputFilename(entry, detectorId, lens, sourceId)
  const requestUrl = buildLabOutputRequestUrl(entry.ticker, filename)
  const repoPath = buildLabOutputRepoPath(entry.ticker, filename)
  if (!requestUrl || !repoPath) return null
  return { filename, repoPath, requestUrl }
}

export async function loadLabOutput(
  ticker: string,
  filename: string,
  options?: { signal?: AbortSignal }
): Promise<LabOutput> {
  const normalizedFilename = normalizeOutputFilename(filename)
  if (!normalizedFilename) {
    throw new LabDataLoadError("Output file path is not canonical.", filename)
  }
  const url = buildLabPath(ticker, filename)
  if (!url) {
    throw new LabDataLoadError("Output file path is not usable.", filename)
  }
  if (!outputCache.has(url)) {
    const promise = fetchJson<unknown>(url, copy.global.errors.missingDataset, options)
      .then((data) =>
        parseLabPayload(
          LabOutputSchema,
          normalizeLabOutputPayload(data),
          `LabOutput:${normalizedFilename}`,
          url
        )
      )
      .catch((error) => {
        // Retry smoke (manual):
        // 1) First call rejects (404/invalid JSON) and evicts this URL from cache.
        // 2) After file/path is fixed, the next call re-fetches instead of reusing a stale rejection.
        outputCache.delete(url)
        throw error
      })
    outputCache.set(url, promise)
  }
  return outputCache.get(url)!
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
