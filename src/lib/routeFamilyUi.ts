import {
  HOME_ANCHOR_TICKERS,
  PUBLIC_CASEBOOK_CASES,
  PUBLIC_CASEBOOK_TICKERS,
  getPublicCasebookEntry,
  type HomeAnchorTicker,
  type PublicCasebookTicker,
  type RouteFamilyPreviewSubtitleSource,
  type RouteFamilyPreviewSupportStrategy,
} from "./casebookContent"

export { HOME_ANCHOR_TICKERS, PUBLIC_CASEBOOK_TICKERS }
export type {
  HomeAnchorTicker,
  PublicCasebookTicker,
  RouteFamilyPreviewSubtitleSource,
  RouteFamilyPreviewSupportStrategy,
}

export type RouteFamilyCaseConfig = {
  ticker: PublicCasebookTicker
  companyName: string
  sector: string
  publicRoleLabel: string
  topCue: string
  homeCardLabel: string
  chooserCardDescription: string
  chooserBestFor: string
  chooserObjectiveLabel: string
  methodologyDetail: string
  preview: {
    integratedTitle: string
    boundedTitle: string
    roleSummary: string
    subtitleSource: RouteFamilyPreviewSubtitleSource
    supportStrategy: RouteFamilyPreviewSupportStrategy
    showRestraintStrip?: boolean
  }
}

const ROUTE_FAMILY_CASE_CONFIG = PUBLIC_CASEBOOK_TICKERS.reduce<
  Record<PublicCasebookTicker, RouteFamilyCaseConfig>
>((accumulator, ticker) => {
  const entry = PUBLIC_CASEBOOK_CASES[ticker]
  accumulator[ticker] = {
    ticker,
    companyName: entry.companyName,
    sector: entry.sector,
    publicRoleLabel: entry.publicRoleLabel,
    topCue: entry.topCue,
    homeCardLabel: entry.homeCardLabel,
    chooserCardDescription: entry.chooserCardDescription,
    chooserBestFor: entry.chooserBestFor,
    chooserObjectiveLabel: entry.chooserObjectiveLabel,
    methodologyDetail: entry.methodologyDetail,
    preview: entry.preview,
  }
  return accumulator
}, {} as Record<PublicCasebookTicker, RouteFamilyCaseConfig>)

export function isPublicCasebookTicker(value: string): value is PublicCasebookTicker {
  return PUBLIC_CASEBOOK_TICKERS.includes(value as PublicCasebookTicker)
}

export function isHomeAnchorTicker(value: string): value is HomeAnchorTicker {
  return HOME_ANCHOR_TICKERS.includes(value as HomeAnchorTicker)
}

export function getRouteFamilyConfig(ticker: string | null | undefined): RouteFamilyCaseConfig | null {
  const entry = getPublicCasebookEntry(ticker)
  if (!entry) return null
  return ROUTE_FAMILY_CASE_CONFIG[entry.ticker]
}

export function listRouteFamilyConfigs(): RouteFamilyCaseConfig[] {
  return PUBLIC_CASEBOOK_TICKERS.map((ticker) => ROUTE_FAMILY_CASE_CONFIG[ticker])
}
