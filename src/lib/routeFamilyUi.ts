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
  homeCardDemo: string
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
    homeCardDemo: "See the clearest answer-first shift in the pilot.",
    chooserObjectiveLabel: "Vivid answer",
    methodologyDetail:
      "Shows the workflow at full clarity when the filing shift is vivid and easy to pressure-test.",
    preview: {
      integratedTitle: "Why this fixture stays visible",
      boundedTitle: "Why this read stays visible",
      roleSummary:
        "The vivid-answer route makes the answer-first grammar easiest to read on the clearest pilot pair.",
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
    homeCardDemo: "See where policy pressure makes the public route stop before it overclaims.",
    chooserObjectiveLabel: "Honest stop",
    methodologyDetail:
      "Shows where policy-heavy contrast needs a visible stop before the public surface pretends to broader certainty.",
    preview: {
      integratedTitle: "Why this fixture stays visible",
      boundedTitle: "Why this bounded read stays visible",
      roleSummary:
        "Honest stop keeps the public read visible long enough to show protocol value without pretending to broader certainty.",
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
    homeCardDemo: "See why selective sharpening still matters when the filing barely moves.",
    chooserObjectiveLabel: "Useful restraint",
    methodologyDetail:
      "Shows the same workflow staying useful when the filing barely moves and drama would be misleading.",
    preview: {
      integratedTitle: "Why restraint stays useful",
      boundedTitle: "Why restraint stays useful",
      roleSummary:
        "Useful restraint keeps the workflow credible when the filing is mostly stable and the signal is selective sharpening.",
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
