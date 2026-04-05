export const VISIBLE_FAMILY_TICKERS = ["NVDA", "LLY", "KO"] as const

export type VisibleFamilyTicker = (typeof VISIBLE_FAMILY_TICKERS)[number]

export type RouteFamilyPreviewSubtitleSource = "card_takeaway" | "protocol_read" | "why_case_exists"

export type RouteFamilyPreviewSupportStrategy = "effort_first" | "scope_only"

export type RouteFamilyCaseConfig = {
  ticker: VisibleFamilyTicker
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

const ROUTE_FAMILY_CASE_CONFIG = {
  NVDA: {
    ticker: "NVDA",
    companyName: "NVIDIA",
    sector: "Semiconductors / AI Infrastructure",
    publicRoleLabel: "Vivid answer",
    topCue:
      "Vivid answer: read the filing answer first, then use the protocol and audit layers only to pressure-test it.",
    homeCardLabel: "Vivid answer",
    chooserCardDescription: "The clearest answer-first shift in the pilot.",
    chooserBestFor: "Strongest first signal",
    chooserObjectiveLabel: "Vivid answer",
    methodologyDetail:
      "Shows the workflow at full clarity when the filing shift is vivid and easy to pressure-test.",
    preview: {
      integratedTitle: "Why this fixture stays visible",
      boundedTitle: "Why this read stays visible",
      roleSummary: "Answer-first is clearest here; the support layers only pressure-test it.",
      subtitleSource: "card_takeaway",
      supportStrategy: "effort_first",
    },
  },
  LLY: {
    ticker: "LLY",
    companyName: "Eli Lilly and Company",
    sector: "Pharmaceuticals / Cardiometabolic and Obesity",
    publicRoleLabel: "Honest stop",
    topCue:
      "Honest stop: read the filing answer, check the compact protocol layer, then stop at the explicit boundary.",
    homeCardLabel: "Honest stop",
    chooserCardDescription: "Policy pressure makes the stop boundary visible.",
    chooserBestFor: "Policy-heavy contrast",
    chooserObjectiveLabel: "Honest stop",
    methodologyDetail:
      "Shows where policy-heavy contrast needs a visible stop before the public surface pretends to broader certainty.",
    preview: {
      integratedTitle: "Why this fixture stays visible",
      boundedTitle: "Why this bounded read stays visible",
      roleSummary: "Show the visible read, then stop at the boundary.",
      subtitleSource: "card_takeaway",
      supportStrategy: "effort_first",
    },
  },
  KO: {
    ticker: "KO",
    companyName: "Coca-Cola",
    sector: "Consumer Staples / Beverages",
    publicRoleLabel: "Useful restraint",
    topCue:
      "Useful restraint: read the filing answer, then use the protocol layer to selectively sharpen a mostly stable filing.",
    homeCardLabel: "Useful restraint",
    chooserCardDescription: "Selective sharpening matters when the filing barely moves.",
    chooserBestFor: "Low-drift restraint",
    chooserObjectiveLabel: "Useful restraint",
    methodologyDetail:
      "Shows the same workflow staying useful when the filing barely moves and drama would be misleading.",
    preview: {
      integratedTitle: "Why restraint stays useful",
      boundedTitle: "Why restraint stays useful",
      roleSummary: "Mostly stable filing; the protocol only sharpens the few places that moved.",
      subtitleSource: "card_takeaway",
      supportStrategy: "scope_only",
      showRestraintStrip: true,
    },
  },
} satisfies Record<VisibleFamilyTicker, RouteFamilyCaseConfig>

export function isVisibleFamilyTicker(value: string): value is VisibleFamilyTicker {
  return VISIBLE_FAMILY_TICKERS.includes(value as VisibleFamilyTicker)
}

export function getRouteFamilyConfig(ticker: string | null | undefined): RouteFamilyCaseConfig | null {
  if (!ticker) return null
  const normalizedTicker = ticker.trim().toUpperCase()
  if (!isVisibleFamilyTicker(normalizedTicker)) return null
  return ROUTE_FAMILY_CASE_CONFIG[normalizedTicker]
}

export function listRouteFamilyConfigs(): RouteFamilyCaseConfig[] {
  return VISIBLE_FAMILY_TICKERS.map((ticker) => ROUTE_FAMILY_CASE_CONFIG[ticker])
}
