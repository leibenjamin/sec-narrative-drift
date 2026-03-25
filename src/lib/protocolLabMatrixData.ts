import { withBase } from "./paths.ts"
import {
  ProtocolLabEffortRobustnessCaseSchema,
  ProtocolLabEffortRobustnessSummarySchema,
  ProtocolLabNoveltyLedgerCaseSchema,
  ProtocolLabPilotMatrixCellSchema,
  ProtocolLabPilotMatrixRegistrySchema,
  ProtocolLabPilotMatrixReviewSchema,
  ProtocolLabPilotMatrixSchema,
  ProtocolLabPilotMatrixStorySchema,
  ProtocolLabSkepticCaseCanonizedMatrixSchema,
} from "./protocolLabMatrixSchemas.ts"
import type {
  ProtocolLabEffortRobustnessBundle,
  ProtocolLabEffortRobustnessCase,
  ProtocolLabEffortRobustnessSummary,
  ProtocolLabNoveltyLedgerCase,
  ProtocolLabPilotMatrix,
  ProtocolLabPilotMatrixBundle,
  ProtocolLabPilotMatrixCell,
  ProtocolLabPilotMatrixRegistry,
  ProtocolLabPilotMatrixRegistryItem,
  ProtocolLabPilotMatrixReview,
  ProtocolLabPilotMatrixStory,
  ProtocolLabSkepticCaseCanonizedMatrix,
} from "./protocolLabMatrixTypes.ts"
import type { z } from "zod"

const PILOT_MATRIX_REGISTRY_PATH =
  "data/business_document_protocol_lab/registries/pilot_matrices_v1.json"
const EFFORT_ROBUSTNESS_SUMMARY_PATH =
  "data/business_document_protocol_lab/standard_controls/effort_robustness/effort_robustness_summary_v1.json"
const EFFORT_ROBUSTNESS_CASE_PATHS: Record<string, string> = {
  NVDA:
    "data/business_document_protocol_lab/standard_controls/effort_robustness/nvda_effort_robustness_v1.json",
  LLY:
    "data/business_document_protocol_lab/standard_controls/effort_robustness/lly_effort_robustness_v1.json",
}
const NOVELTY_LEDGER_CASE_PATHS: Record<string, string> = {
  NVDA:
    "data/business_document_protocol_lab/novelty_ledger/NVDA_2024_2025_10k_item1a/p4_canonized_matrix_v1.json",
  LLY:
    "data/business_document_protocol_lab/novelty_ledger/LLY_2024_2025_10k_item1a/p4_canonized_matrix_v1.json",
  KO:
    "data/business_document_protocol_lab/novelty_ledger/KO_2024_2025_10k_item1a/p4_canonized_matrix_v1.json",
}
const SKEPTIC_CASE_PATHS: Record<string, string> = {
  KO:
    "data/business_document_protocol_lab/skeptic_cases/KO_2024_2025_10k_item1a/ko_canonized_matrix_v1.json",
}

export class ProtocolLabMatrixLoadError extends Error {
  readonly url: string
  readonly status?: number

  constructor(message: string, url: string, status?: number) {
    super(message)
    this.name = "ProtocolLabMatrixLoadError"
    this.url = url
    this.status = status
  }
}

let pilotMatrixRegistryPromise: Promise<ProtocolLabPilotMatrixRegistry> | null = null
const pilotMatrixBundleCache = new Map<string, Promise<ProtocolLabPilotMatrixBundle>>()
let effortRobustnessSummaryPromise: Promise<ProtocolLabEffortRobustnessSummary> | null = null
const effortRobustnessCaseCache = new Map<string, Promise<ProtocolLabEffortRobustnessCase>>()
const noveltyLedgerCaseCache = new Map<string, Promise<ProtocolLabNoveltyLedgerCase>>()
const skepticCaseCache = new Map<string, Promise<ProtocolLabSkepticCaseCanonizedMatrix>>()

function normalizeMatrixPath(pathValue: string): string {
  const normalized = pathValue.trim().replace(/\\/g, "/")
  if (normalized.startsWith("public/")) {
    return withBase(normalized.replace(/^public\//, ""))
  }
  if (normalized.startsWith("/")) {
    return withBase(normalized.replace(/^\/+/, ""))
  }
  return withBase(normalized)
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
    throw new ProtocolLabMatrixLoadError(userMessage, url)
  }

  if (!response.ok) {
    throw new ProtocolLabMatrixLoadError(userMessage, url, response.status)
  }

  try {
    return (await response.json()) as T
  } catch {
    throw new ProtocolLabMatrixLoadError(userMessage, url, response.status)
  }
}

function parseMatrixPayload<T>(schema: z.ZodType<T>, data: unknown, label: string, url: string): T {
  const result = schema.safeParse(data)
  if (!result.success) {
    const firstIssue = result.error.issues[0]
    const issuePath =
      firstIssue && firstIssue.path.length > 0 ? firstIssue.path.join(".") : "<root>"
    const issueMessage = firstIssue ? firstIssue.message : "Unknown schema validation issue."
    throw new ProtocolLabMatrixLoadError(
      `Invalid ${label} payload (${issuePath}: ${issueMessage}).`,
      url
    )
  }
  return result.data
}

async function loadPilotMatrixRegistry(): Promise<ProtocolLabPilotMatrixRegistry> {
  if (!pilotMatrixRegistryPromise) {
    const url = withBase(PILOT_MATRIX_REGISTRY_PATH)
    pilotMatrixRegistryPromise = fetchJson<unknown>(
      url,
      "Pilot matrix registry is not available."
    ).then((data) =>
      parseMatrixPayload(ProtocolLabPilotMatrixRegistrySchema, data, "pilot_matrices_v1", url)
    )
  }

  return pilotMatrixRegistryPromise
}

function normalizeTicker(value: string): string {
  return value.trim().toUpperCase()
}

export function resolveEffortRobustnessCasePathForTicker(ticker: string): string | null {
  const normalizedTicker = normalizeTicker(ticker)
  return EFFORT_ROBUSTNESS_CASE_PATHS[normalizedTicker] ?? null
}

export function resolveNoveltyLedgerCasePathForTicker(ticker: string): string | null {
  const normalizedTicker = normalizeTicker(ticker)
  return NOVELTY_LEDGER_CASE_PATHS[normalizedTicker] ?? null
}

export function resolveSkepticCasePathForTicker(ticker: string): string | null {
  const normalizedTicker = normalizeTicker(ticker)
  return SKEPTIC_CASE_PATHS[normalizedTicker] ?? null
}

export function selectPilotMatrixRegistryItem(
  items: ProtocolLabPilotMatrixRegistryItem[],
  options: {
    ticker: string
    yearFrom?: number | null
    yearTo?: number | null
  }
): ProtocolLabPilotMatrixRegistryItem | null {
  const normalizedTicker = normalizeTicker(options.ticker)
  if (!normalizedTicker) return null

  const tickerMatches = items.filter(
    (item) => normalizeTicker(item.ticker) === normalizedTicker
  )

  if (
    typeof options.yearFrom === "number" &&
    typeof options.yearTo === "number"
  ) {
    return (
      tickerMatches.find(
        (item) =>
          item.year_from === options.yearFrom && item.year_to === options.yearTo
      ) ?? null
    )
  }

  return tickerMatches.length === 1 ? tickerMatches[0] : null
}

async function loadMatrixManifest(
  pathValue: string,
  options?: { signal?: AbortSignal }
): Promise<ProtocolLabPilotMatrix> {
  const url = normalizeMatrixPath(pathValue)
  const data = await fetchJson<unknown>(url, "Pilot matrix manifest is not available.", options)
  return parseMatrixPayload(ProtocolLabPilotMatrixSchema, data, "pilot_matrix_v1", url)
}

async function loadMatrixCell(
  pathValue: string,
  options?: { signal?: AbortSignal }
): Promise<ProtocolLabPilotMatrixCell> {
  const url = normalizeMatrixPath(pathValue)
  const data = await fetchJson<unknown>(url, "Pilot matrix cell is not available.", options)
  return parseMatrixPayload(ProtocolLabPilotMatrixCellSchema, data, "pilot_matrix_cell_v1", url)
}

async function loadMatrixReview(
  pathValue: string,
  options?: { signal?: AbortSignal }
): Promise<ProtocolLabPilotMatrixReview> {
  const url = normalizeMatrixPath(pathValue)
  const data = await fetchJson<unknown>(url, "Pilot matrix review is not available.", options)
  return parseMatrixPayload(ProtocolLabPilotMatrixReviewSchema, data, "pilot_matrix_review_v1", url)
}

async function loadMatrixStory(
  pathValue: string,
  options?: { signal?: AbortSignal }
): Promise<ProtocolLabPilotMatrixStory> {
  const url = normalizeMatrixPath(pathValue)
  const data = await fetchJson<unknown>(url, "Pilot matrix story is not available.", options)
  return parseMatrixPayload(ProtocolLabPilotMatrixStorySchema, data, "pilot_matrix_story_v1", url)
}

async function loadEffortRobustnessCase(
  pathValue: string,
  options?: { signal?: AbortSignal }
): Promise<ProtocolLabEffortRobustnessCase> {
  const url = normalizeMatrixPath(pathValue)
  const data = await fetchJson<unknown>(
    url,
    "Effort robustness case artifact is not available.",
    options
  )
  return parseMatrixPayload(
    ProtocolLabEffortRobustnessCaseSchema,
    data,
    "effort_robustness_case_v1",
    url
  )
}

async function loadNoveltyLedgerCase(
  pathValue: string,
  options?: { signal?: AbortSignal }
): Promise<ProtocolLabNoveltyLedgerCase> {
  const url = normalizeMatrixPath(pathValue)
  const data = await fetchJson<unknown>(
    url,
    "Novelty ledger artifact is not available.",
    options
  )
  return parseMatrixPayload(
    ProtocolLabNoveltyLedgerCaseSchema,
    data,
    "p4_canonized_matrix_v1",
    url
  )
}

async function loadSkepticCase(
  pathValue: string,
  options?: { signal?: AbortSignal }
): Promise<ProtocolLabSkepticCaseCanonizedMatrix> {
  const url = normalizeMatrixPath(pathValue)
  const data = await fetchJson<unknown>(
    url,
    "Skeptic case artifact is not available.",
    options
  )
  return parseMatrixPayload(
    ProtocolLabSkepticCaseCanonizedMatrixSchema,
    data,
    "skeptic_case_canonized_matrix_v1",
    url
  )
}

export async function loadEffortRobustnessSummary(options?: {
  signal?: AbortSignal
}): Promise<ProtocolLabEffortRobustnessSummary> {
  if (!effortRobustnessSummaryPromise) {
    const url = normalizeMatrixPath(EFFORT_ROBUSTNESS_SUMMARY_PATH)
    effortRobustnessSummaryPromise = fetchJson<unknown>(
      url,
      "Effort robustness summary artifact is not available.",
      options
    ).then((data) =>
      parseMatrixPayload(
        ProtocolLabEffortRobustnessSummarySchema,
        data,
        "effort_robustness_summary_v1",
        url
      )
    )
  }

  return effortRobustnessSummaryPromise
}

function validateStoryAgainstMatrix(
  matrix: ProtocolLabPilotMatrix,
  story: ProtocolLabPilotMatrixStory,
  storyPath: string
): void {
  const url = normalizeMatrixPath(storyPath)
  if (story.matrix_id !== matrix.matrix_id) {
    throw new ProtocolLabMatrixLoadError(
      "Pilot matrix story matrix_id does not match the matrix manifest.",
      url
    )
  }
  if (story.fixture_id !== matrix.fixture_id) {
    throw new ProtocolLabMatrixLoadError(
      "Pilot matrix story fixture_id does not match the matrix manifest.",
      url
    )
  }
}

export async function resolvePilotMatrixRegistryItem(options: {
  ticker: string
  yearFrom?: number | null
  yearTo?: number | null
}): Promise<ProtocolLabPilotMatrixRegistryItem | null> {
  const registry = await loadPilotMatrixRegistry()
  return selectPilotMatrixRegistryItem(registry.items, options)
}

async function loadMatrixBundleFromRegistryItem(
  item: ProtocolLabPilotMatrixRegistryItem
): Promise<ProtocolLabPilotMatrixBundle> {
  const cacheKey = item.fixture_id
  const cached = pilotMatrixBundleCache.get(cacheKey)
  if (cached) {
    return cached
  }

  const promise = loadMatrixManifest(item.matrix_path)
    .then(async (matrix) => {
      const orderedCells = await Promise.all(
        matrix.ordered_cell_ids.map(async (cellId) => {
          const cellPath = matrix.cell_paths[cellId]
          if (!cellPath) {
            throw new ProtocolLabMatrixLoadError(
              `Pilot matrix cell path missing for ${cellId}.`,
              normalizeMatrixPath(item.matrix_path)
            )
          }
          return loadMatrixCell(cellPath)
        })
      )
      const cellsById: Record<string, ProtocolLabPilotMatrixCell> = {}
      for (const cell of orderedCells) {
        cellsById[cell.cell_id] = cell
      }
      const [review, story] = await Promise.all([
        loadMatrixReview(matrix.review_path),
        loadMatrixStory(item.story_path),
      ])
      validateStoryAgainstMatrix(matrix, story, item.story_path)
      return {
        matrix,
        ordered_cells: orderedCells,
        cells_by_id: cellsById,
        review,
        story,
      }
    })
    .catch((error) => {
      pilotMatrixBundleCache.delete(cacheKey)
      throw error
    })

  pilotMatrixBundleCache.set(cacheKey, promise)
  return promise
}

export async function loadPilotMatrixBundleForCase(options: {
  ticker: string
  yearFrom?: number | null
  yearTo?: number | null
  signal?: AbortSignal
}): Promise<ProtocolLabPilotMatrixBundle | null> {
  if (options.signal?.aborted) {
    throw new DOMException("The operation was aborted.", "AbortError")
  }

  const item = await resolvePilotMatrixRegistryItem({
    ticker: options.ticker,
    yearFrom: options.yearFrom,
    yearTo: options.yearTo,
  })

  if (options.signal?.aborted) {
    throw new DOMException("The operation was aborted.", "AbortError")
  }

  if (!item) return null
  return loadMatrixBundleFromRegistryItem(item)
}

export async function loadPilotMatrixBundleForTicker(options: {
  ticker: string
  signal?: AbortSignal
}): Promise<ProtocolLabPilotMatrixBundle | null> {
  return loadPilotMatrixBundleForCase({
    ticker: options.ticker,
    signal: options.signal,
  })
}

export async function loadEffortRobustnessCaseForTicker(options: {
  ticker: string
  signal?: AbortSignal
}): Promise<ProtocolLabEffortRobustnessCase | null> {
  const pathValue = resolveEffortRobustnessCasePathForTicker(options.ticker)
  if (!pathValue) return null

  const cacheKey = normalizeTicker(options.ticker)
  const cached = effortRobustnessCaseCache.get(cacheKey)
  if (cached) {
    return cached
  }

  const promise = loadEffortRobustnessCase(pathValue, {
    signal: options.signal,
  }).catch((error) => {
    effortRobustnessCaseCache.delete(cacheKey)
    throw error
  })
  effortRobustnessCaseCache.set(cacheKey, promise)
  return promise
}

export async function loadNoveltyLedgerCaseForTicker(options: {
  ticker: string
  signal?: AbortSignal
}): Promise<ProtocolLabNoveltyLedgerCase | null> {
  const pathValue = resolveNoveltyLedgerCasePathForTicker(options.ticker)
  if (!pathValue) return null

  const cacheKey = normalizeTicker(options.ticker)
  const cached = noveltyLedgerCaseCache.get(cacheKey)
  if (cached) {
    return cached
  }

  const promise = loadNoveltyLedgerCase(pathValue, {
    signal: options.signal,
  }).catch((error) => {
    noveltyLedgerCaseCache.delete(cacheKey)
    throw error
  })
  noveltyLedgerCaseCache.set(cacheKey, promise)
  return promise
}

export async function loadSkepticCaseForTicker(options: {
  ticker: string
  signal?: AbortSignal
}): Promise<ProtocolLabSkepticCaseCanonizedMatrix | null> {
  const pathValue = resolveSkepticCasePathForTicker(options.ticker)
  if (!pathValue) return null

  const cacheKey = normalizeTicker(options.ticker)
  const cached = skepticCaseCache.get(cacheKey)
  if (cached) {
    return cached
  }

  const promise = loadSkepticCase(pathValue, {
    signal: options.signal,
  }).catch((error) => {
    skepticCaseCache.delete(cacheKey)
    throw error
  })
  skepticCaseCache.set(cacheKey, promise)
  return promise
}

export async function loadEffortRobustnessBundleForTicker(options: {
  ticker: string
  signal?: AbortSignal
}): Promise<ProtocolLabEffortRobustnessBundle | null> {
  const caseArtifact = await loadEffortRobustnessCaseForTicker(options)
  if (!caseArtifact) return null

  const summaryArtifact = await loadEffortRobustnessSummary(options)
  return {
    case_artifact: caseArtifact,
    summary_artifact: summaryArtifact,
  }
}

export function clearProtocolLabMatrixCache(): void {
  pilotMatrixRegistryPromise = null
  pilotMatrixBundleCache.clear()
  effortRobustnessSummaryPromise = null
  effortRobustnessCaseCache.clear()
  noveltyLedgerCaseCache.clear()
  skepticCaseCache.clear()
}

export function formatProtocolLabMatrixLoadDebug(error: unknown): string | null {
  if (error instanceof ProtocolLabMatrixLoadError) {
    const statusText = typeof error.status === "number" ? ` (status ${error.status})` : ""
    return `${error.message} Requested path: ${error.url}${statusText}`
  }
  if (error instanceof Error) {
    return `Protocol lab matrix error: ${error.message}`
  }
  return "Protocol lab matrix error: unknown failure."
}
