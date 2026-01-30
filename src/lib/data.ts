import { copy } from "./copy"
import {
  CompanyIndexSchema,
  ExcerptsSchema,
  FeaturedCasesSchema,
  FilingRowsSchema,
  MetaSchema,
  MetricsSchema,
  parseWithSchema,
  ShiftPairsSchema,
  SimilarityMatrixSchema,
  UniverseFeaturedSchema,
} from "./schemas"
import type {
  Excerpts,
  FeaturedCases,
  UniverseFeatured,
  CompanyIndex,
  CompanyIndexRow,
  FilingRow,
  Meta,
  Metrics,
  ShiftPairs,
  SimilarityMatrix,
} from "./types"

const BASE_PATH = `${import.meta.env.BASE_URL}data/sec_narrative_drift`
const INDEX_PATH = `${BASE_PATH}/index.json`
const FEATURED_CASES_PATH = `${BASE_PATH}/featured_cases.json`
const UNIVERSE_PATH = `${BASE_PATH}/universe_featured.json`
const FEATURED_TICKERS = ["AAPL", "NVDA", "TSLA"]

export class DataLoadError extends Error {
  readonly url: string
  readonly status?: number

  constructor(message: string, url: string, status?: number) {
    super(message)
    this.name = "DataLoadError"
    this.url = url
    this.status = status
  }
}

function buildFallbackIndex(): CompanyIndex {
  const companies: CompanyIndexRow[] = FEATURED_TICKERS.map((ticker) => ({
    ticker,
    companyName: ticker,
    cik: "",
    coverage: { years: [], count: 0, minYear: 0, maxYear: 0 },
    quality: { level: "unknown" },
  }))
  return {
    version: 1,
    generatedAtUtc: "fallback",
    section: "10k_item1a",
    lookbackTargetYears: 10,
    companyCount: companies.length,
    companies,
  }
}

function buildPath(ticker: string, filename: string): string {
  return `${BASE_PATH}/${ticker.toUpperCase()}/${filename}`
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
      signal: options?.signal,
    })
  } catch {
    throw new DataLoadError(userMessage, url)
  }

  if (!response.ok) {
    throw new DataLoadError(userMessage, url, response.status)
  }

  try {
    return (await response.json()) as T
  } catch {
    throw new DataLoadError(userMessage, url, response.status)
  }
}

export function listFeaturedTickers(): string[] {
  return [...FEATURED_TICKERS]
}

export function listFeaturedTickersFromIndex(index: CompanyIndex): string[] {
  const featured = index.companies
    .filter((company) => !!company.featuredCase)
    .map((company) => company.ticker)
  return featured.length ? featured.slice(0, 12) : [...FEATURED_TICKERS]
}

export async function loadCompanyIndex(): Promise<CompanyIndex> {
  try {
    const data = await fetchJson<unknown>(INDEX_PATH, copy.global.errors.missingDataset)
    return parseWithSchema(CompanyIndexSchema, data, "CompanyIndex")
  } catch (error) {
    if (import.meta.env.DEV) {
      console.warn("Index missing or unreadable; using fallback tickers.", error)
    }
    return buildFallbackIndex()
  }
}

export async function loadFeaturedCases(): Promise<FeaturedCases> {
  const data = await fetchJson<unknown>(FEATURED_CASES_PATH, copy.global.errors.missingDataset)
  return parseWithSchema(FeaturedCasesSchema, data, "FeaturedCases")
}

export async function loadUniverseFeatured(): Promise<UniverseFeatured> {
  const data = await fetchJson<unknown>(UNIVERSE_PATH, copy.global.errors.missingDataset)
  return parseWithSchema(UniverseFeaturedSchema, data, "UniverseFeatured")
}

export function resolveDefaultPair(
  availableYears: number[],
  desiredFrom?: number | null,
  desiredTo?: number | null
): { from: number; to: number } | null {
  const years = [...new Set(availableYears)]
    .filter((year) => Number.isFinite(year))
    .sort((a, b) => a - b)

  if (years.length < 2) return null

  let targetFrom = typeof desiredFrom === "number" ? desiredFrom : years[years.length - 2]
  let targetTo = typeof desiredTo === "number" ? desiredTo : years[years.length - 1]

  if (targetFrom > targetTo) {
    const tmp = targetFrom
    targetFrom = targetTo
    targetTo = tmp
  }
  if (targetFrom === targetTo) {
    targetFrom = years[years.length - 2]
    targetTo = years[years.length - 1]
  }

  let best = { from: years[0], to: years[1] }
  let bestScore = Number.POSITIVE_INFINITY

  for (let i = 1; i < years.length; i += 1) {
    const from = years[i - 1]
    const to = years[i]
    const score = Math.abs(from - targetFrom) + Math.abs(to - targetTo)
    if (score < bestScore) {
      bestScore = score
      best = { from, to }
    }
  }

  return best
}

export async function loadCompanyMeta(ticker: string): Promise<Meta> {
  const data = await fetchJson<unknown>(buildPath(ticker, "meta.json"), copy.global.errors.missingDataset)
  return parseWithSchema(MetaSchema, data, `Meta:${ticker}`)
}

export async function loadCompanyFilings(ticker: string): Promise<FilingRow[]> {
  const data = await fetchJson<unknown>(
    buildPath(ticker, "filings.json"),
    copy.global.errors.missingDataset
  )
  return parseWithSchema(FilingRowsSchema, data, `FilingRows:${ticker}`)
}

export async function loadMetrics(ticker: string): Promise<Metrics> {
  const data = await fetchJson<unknown>(
    buildPath(ticker, "metrics_10k_item1a.json"),
    copy.global.errors.missingDataset
  )
  return parseWithSchema(MetricsSchema, data, `Metrics:${ticker}`)
}

export async function loadSimilarity(ticker: string): Promise<SimilarityMatrix> {
  const data = await fetchJson<unknown>(
    buildPath(ticker, "similarity_10k_item1a.json"),
    copy.global.errors.missingDataset
  )
  return parseWithSchema(SimilarityMatrixSchema, data, `SimilarityMatrix:${ticker}`)
}

export async function loadShifts(ticker: string): Promise<ShiftPairs> {
  const data = await fetchJson<unknown>(
    buildPath(ticker, "shifts_10k_item1a.json"),
    copy.global.errors.missingDataset
  )
  return parseWithSchema(ShiftPairsSchema, data, `ShiftPairs:${ticker}`)
}

export async function loadExcerpts(
  ticker: string,
  signal?: AbortSignal
): Promise<Excerpts> {
  const data = await fetchJson<unknown>(
    buildPath(ticker, "excerpts_10k_item1a.json"),
    copy.global.errors.missingExcerpts,
    { signal }
  )
  return parseWithSchema(ExcerptsSchema, data, `Excerpts:${ticker}`)
}
