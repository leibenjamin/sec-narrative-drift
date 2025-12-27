import { copy } from "./copy"
import type {
  Excerpts,
  FilingRow,
  Meta,
  Metrics,
  ShiftPairs,
  SimilarityMatrix,
} from "./types"

const BASE_PATH = "/data/sec_narrative_drift"
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

function buildPath(ticker: string, filename: string): string {
  return `${BASE_PATH}/${ticker.toUpperCase()}/${filename}`
}

async function fetchJson<T>(url: string, userMessage: string): Promise<T> {
  let response: Response

  try {
    response = await fetch(url, { headers: { Accept: "application/json" } })
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

export async function loadCompanyMeta(ticker: string): Promise<Meta> {
  return fetchJson<Meta>(buildPath(ticker, "meta.json"), copy.global.errors.missingDataset)
}

export async function loadCompanyFilings(ticker: string): Promise<FilingRow[]> {
  return fetchJson<FilingRow[]>(
    buildPath(ticker, "filings.json"),
    copy.global.errors.missingDataset
  )
}

export async function loadMetrics(ticker: string): Promise<Metrics> {
  return fetchJson<Metrics>(
    buildPath(ticker, "metrics_10k_item1a.json"),
    copy.global.errors.missingDataset
  )
}

export async function loadSimilarity(ticker: string): Promise<SimilarityMatrix> {
  return fetchJson<SimilarityMatrix>(
    buildPath(ticker, "similarity_10k_item1a.json"),
    copy.global.errors.missingDataset
  )
}

export async function loadShifts(ticker: string): Promise<ShiftPairs> {
  return fetchJson<ShiftPairs>(
    buildPath(ticker, "shifts_10k_item1a.json"),
    copy.global.errors.missingDataset
  )
}

export async function loadExcerpts(ticker: string): Promise<Excerpts> {
  return fetchJson<Excerpts>(
    buildPath(ticker, "excerpts_10k_item1a.json"),
    copy.global.errors.missingExcerpts
  )
}
