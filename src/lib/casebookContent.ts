export const HOME_ANCHOR_TICKERS = ["NVDA", "LLY", "KO"] as const
export const PUBLIC_CASEBOOK_TICKERS = ["NVDA", "LLY", "KO", "META", "TSLA", "WMT"] as const
export const MATRIX_FIRST_PUBLIC_TICKERS = ["LLY", "META", "TSLA", "WMT"] as const
export const RESERVE_CASE_TICKERS = ["GOOGL"] as const
export const HOLD_CASE_TICKERS = ["UNH"] as const

export type HomeAnchorTicker = (typeof HOME_ANCHOR_TICKERS)[number]
export type PublicCasebookTicker = (typeof PUBLIC_CASEBOOK_TICKERS)[number]
export type MatrixFirstPublicTicker = (typeof MATRIX_FIRST_PUBLIC_TICKERS)[number]
export type ReserveCaseTicker = (typeof RESERVE_CASE_TICKERS)[number]
export type HoldCaseTicker = (typeof HOLD_CASE_TICKERS)[number]

export type RouteFamilyPreviewSubtitleSource = "card_takeaway" | "protocol_read" | "why_case_exists"
export type RouteFamilyPreviewSupportStrategy = "effort_first" | "scope_only"
export type PublicCaseSurface = "runtime_full" | "matrix_first"
export type PublicCaseBandId = "anchor_shapes" | "pressure_cases"

export type CaseTeachingLayer = {
  proves: string
  doesntProve: string
  lesson: string
  commonMistake: string
}

export type PublicCasebookEntry = {
  ticker: PublicCasebookTicker
  companyName: string
  sector: string
  yearFrom: number
  yearTo: number
  surface: PublicCaseSurface
  publicRoleLabel: string
  homeCardLabel: string
  chooserCardDescription: string
  chooserBestFor: string
  chooserObjectiveLabel: string
  methodologyDetail: string
  topCue: string
  preview: {
    integratedTitle: string
    boundedTitle: string
    roleSummary: string
    subtitleSource: RouteFamilyPreviewSubtitleSource
    supportStrategy: RouteFamilyPreviewSupportStrategy
    showRestraintStrip?: boolean
  }
  bandId: PublicCaseBandId
  bandLabel: string
  bandSummary: string
  teachingSummary: string
  whyCaseExists: string
  bestUsedWhen: string
  firstQuestion: string
  allowedAnswerShape: string
  routeRefuses: string
  whyCaseMatters: string
  teaching: CaseTeachingLayer
  artifactPolicy: {
    primary: string
    optional: string | null
  }
}

export type CasebookComparisonRow = {
  label: string
  values: Record<PublicCasebookTicker, string>
}

export type CasebookBand = {
  id: PublicCaseBandId
  title: string
  description: string
  tickers: PublicCasebookTicker[]
}

export const casebookFraming = {
  appName: "Document Protocol Lab",
  casebookOneLiner:
    "An interactive casebook for how document-comparison workflows should claim, prove, and stop.",
  productStatement:
    "Document Protocol Lab is an interactive casebook for bounded document-comparison judgment. It shows what a workflow should claim, how it should prove it, and where it should stop.",
  home: {
    title: "Document Protocol Lab | Interactive Casebook",
    metaDescription:
      "Document Protocol Lab is an interactive casebook for bounded document-comparison judgment across six public cases.",
    hook: "How do you show what changed in a document without overstating what you know?",
    support:
      "An interactive casebook for how document-comparison workflows should claim, prove, and stop.",
    chooserSummary:
      "Start with the three anchor answer shapes, then use the Casebook to compare the added pressure cases.",
    whatThisIsTitle: "What this is",
    whatThisIs: "An interactive casebook for bounded document-comparison judgment.",
    whatThisIsntTitle: "What this isn't",
    whatThisIsnt: "A general document chatbot or a broad filing browser.",
    whyThisMattersTitle: "Why this matters",
    whyThisMatters: [
      "Better than a summary when the shape of the claim matters.",
      "Better than a one-off answer when you want proof beside the answer.",
      "Better than false certainty when the honest move is to stop.",
    ],
    casebookEntryTitle: "Explore the full casebook",
    casebookEntryBody:
      "Three anchor cases teach the cleanest answer shapes. Three added cases show how pressure type changes the read without widening the claim.",
    casebookEntryCta: "Open the Casebook",
    commonFailureModesTitle: "Common failure modes this lab avoids",
    commonFailureModes: [
      "Mistaking reordering for novelty",
      "Treating added examples as new themes",
      "Summarizing without proof",
      "Refusing to stop",
      "Overcalling weak change",
    ],
  },
  casebook: {
    title: "Casebook | Document Protocol Lab",
    metaDescription:
      "Six public cases show how document-comparison workflows should claim, prove, and stop.",
    eyebrow: "Casebook",
    heading: "A curated set of worked document-comparison cases.",
    intro:
      "Each case demonstrates a different allowed answer shape or pressure type for the same kind of comparison task.",
    boundednessNote:
      "This is a curated six-case roster, not a filing browser, upload flow, or broad benchmark.",
    comparisonTitle: "Cross-case comparison",
    comparisonIntro:
      "Use one matrix to see why these cases belong together and where each route should stop.",
  },
  methodology: {
    title: "Methodology | Document Protocol Lab",
    metaDescription:
      "How the casebook makes bounded document-comparison claims, keeps proof visible, and stops before overclaiming.",
    heading: "Field guide for claim, proof, and stop.",
    intro:
      "The public lab is not trying to answer every document question. It exists to show how a bounded workflow should make a claim, prove it with visible evidence, and stop where the public route should stop.",
    whyFrontierTitle: "Why not just ask a frontier model?",
    whyFrontierBody: [
      "A strong model can often produce a plausible answer.",
      "This lab is for when you care about the answer shape, the proof beside it, and the point where the workflow should stop.",
      "The value here is visible judgment, not just output.",
    ],
    nonClaimsTitle: "What this lab does not claim",
    nonClaims: [
      "It is not a benchmark of every model or prompt family.",
      "It is not a broad market screener or issuer browser.",
      "It is not proof that every document set needs the same answer shape.",
    ],
    matrixOnlyNote:
      "Some public cases can ship honestly with pilot-matrix artifacts only. LLY already proves that the visible route does not need outline compare everywhere to be useful.",
  },
  reserveHold: {
    reserveTitle: "Reserve",
    reserveCase: "GOOGL",
    reserveRationale:
      "Valid output, but too overlapping with META in the current public roster.",
    holdTitle: "Hold",
    holdCase: "UNH",
    holdRationale:
      "Valid output, but not vivid or distinct enough to earn public casebook space.",
    reconsideration:
      "Reconsider only if a current public case drops out or if a later run produces clearly stronger pedagogic distinctiveness.",
  },
} as const

export const CASEBOOK_BANDS: CasebookBand[] = [
  {
    id: "anchor_shapes",
    title: "Anchor answer shapes",
    description:
      "Start here when you need the cleanest examples of answer-first, honest stop, and useful restraint.",
    tickers: ["NVDA", "LLY", "KO"],
  },
  {
    id: "pressure_cases",
    title: "Added pressure cases",
    description:
      "Use these when the same comparison task needs sharper pressure around regulation, policy shock, or interface risk.",
    tickers: ["META", "TSLA", "WMT"],
  },
] as const

export const PUBLIC_CASEBOOK_CASES: Record<PublicCasebookTicker, PublicCasebookEntry> = {
  NVDA: {
    ticker: "NVDA",
    companyName: "NVIDIA",
    sector: "Semiconductors / AI Infrastructure",
    yearFrom: 2024,
    yearTo: 2025,
    surface: "runtime_full",
    publicRoleLabel: "Vivid answer",
    homeCardLabel: "Vivid answer",
    chooserCardDescription:
      "The clearest answer-first case when the filing shift is vivid and evidence-adjacent.",
    chooserBestFor: "Strongest answer-first case",
    chooserObjectiveLabel: "Vivid answer",
    methodologyDetail:
      "Shows the workflow at full clarity when the filing shift is vivid enough to support a specific first read.",
    topCue:
      "Vivid answer: start with the filing claim, keep proof beside it, and stop before the extra machinery takes over.",
    preview: {
      integratedTitle: "Why this case matters",
      boundedTitle: "Why this read matters",
      roleSummary: "A strong answer-first read can stay specific without pretending to be a universal benchmark.",
      subtitleSource: "card_takeaway",
      supportStrategy: "effort_first",
    },
    bandId: "anchor_shapes",
    bandLabel: "Anchor answer shape",
    bandSummary: "The cleanest answer-first read in the public roster.",
    teachingSummary:
      "Shows how a vivid filing shift can stay specific, evidence-adjacent, and bounded.",
    whyCaseExists:
      "The filing change is vivid enough to make the answer-first route legible on first contact.",
    bestUsedWhen: "You want the clearest answer-first route.",
    firstQuestion: "Is the shift strong enough to claim clearly up front?",
    allowedAnswerShape: "Answer first, then pressure-test.",
    routeRefuses: "It refuses to turn vividness into a universal benchmark.",
    whyCaseMatters:
      "It proves the workflow can be decisive without losing auditability or boundaries.",
    teaching: {
      proves: "A strong answer-first read can stay specific and evidence-adjacent.",
      doesntProve: "It does not prove the same answer-first shape belongs on every filing pair.",
      lesson: "When the shift is vivid, the workflow should claim clearly without dragging the reader through every lower layer first.",
      commonMistake:
        "Mistaking a vivid case for permission to overclaim on weaker or lower-drift cases.",
    },
    artifactPolicy: {
      primary: "Runtime compare plus pilot matrix.",
      optional: "Novelty ledger and effort-robustness stay secondary.",
    },
  },
  LLY: {
    ticker: "LLY",
    companyName: "Eli Lilly and Company",
    sector: "Pharmaceuticals / Cardiometabolic and Obesity",
    yearFrom: 2024,
    yearTo: 2025,
    surface: "matrix_first",
    publicRoleLabel: "Honest stop",
    homeCardLabel: "Honest stop",
    chooserCardDescription:
      "The bounded public route that teaches where to stop before overclaiming.",
    chooserBestFor: "Bounded public route",
    chooserObjectiveLabel: "Honest stop",
    methodologyDetail:
      "Shows why a public case can ship honestly with a matrix-first route when the boundary is part of the lesson.",
    topCue:
      "Honest stop: read the visible claim, inspect the proof, then stop where the public route should stop.",
    preview: {
      integratedTitle: "Why this case matters",
      boundedTitle: "Why this read stops here",
      roleSummary: "The value is not maximal coverage. The value is a public route that stops honestly before pretending to broader certainty.",
      subtitleSource: "card_takeaway",
      supportStrategy: "effort_first",
    },
    bandId: "anchor_shapes",
    bandLabel: "Anchor answer shape",
    bandSummary: "The clearest bounded public route in the roster.",
    teachingSummary:
      "Shows how a public case can be useful precisely because it stops where the evidence stops.",
    whyCaseExists:
      "Policy, pricing, and concentration pressure make the public stop boundary easy to see and teach.",
    bestUsedWhen: "You need a public route that stays visibly bounded.",
    firstQuestion: "Where should the public route stop before it starts bluffing?",
    allowedAnswerShape: "Bounded public read with an explicit stop.",
    routeRefuses: "It refuses to pretend bounded evidence equals full certainty.",
    whyCaseMatters:
      "It teaches that honesty about stopping is part of the product, not a fallback.",
    teaching: {
      proves: "A public route can stop honestly without pretending to completeness.",
      doesntProve: "It does not prove every public case should stop at the same depth.",
      lesson: "Boundedness should be visible when the right move is to stop before a broader claim.",
      commonMistake:
        "Confusing a useful bounded route with an incomplete route that needs to hide its limits.",
    },
    artifactPolicy: {
      primary: "Pilot matrix only.",
      optional: "Existing novelty and robustness checks remain secondary.",
    },
  },
  KO: {
    ticker: "KO",
    companyName: "Coca-Cola",
    sector: "Consumer Staples / Beverages",
    yearFrom: 2024,
    yearTo: 2025,
    surface: "runtime_full",
    publicRoleLabel: "Useful restraint",
    homeCardLabel: "Useful restraint",
    chooserCardDescription:
      "The calm low-drift case that proves selective sharpening is still a real answer.",
    chooserBestFor: "Low-drift restraint",
    chooserObjectiveLabel: "Useful restraint",
    methodologyDetail:
      "Shows the workflow staying useful when the filing barely moves and drama would be misleading.",
    topCue:
      "Useful restraint: let the filing stay mostly stable, then sharpen only the parts that truly moved.",
    preview: {
      integratedTitle: "Why restraint helps here",
      boundedTitle: "Why restraint helps here",
      roleSummary: "Mostly stable filing; the workflow earns trust by staying selective instead of forcing drama.",
      subtitleSource: "card_takeaway",
      supportStrategy: "scope_only",
      showRestraintStrip: true,
    },
    bandId: "anchor_shapes",
    bandLabel: "Anchor answer shape",
    bandSummary: "The calm selective-shift case.",
    teachingSummary:
      "Shows how low drift can still justify a real answer when the workflow stays selective.",
    whyCaseExists:
      "The filing barely moves, which makes restraint itself part of the lesson.",
    bestUsedWhen: "You need the cleanest low-drift honesty check.",
    firstQuestion: "Is the right answer a calm selective shift rather than a dramatic rewrite?",
    allowedAnswerShape: "Selective sharpening on a mostly stable filing.",
    routeRefuses: "It refuses to force drama into a low-drift case.",
    whyCaseMatters:
      "It proves that useful restraint is a product strength rather than a weak result.",
    teaching: {
      proves: "A calm selective shift can still be the right result.",
      doesntProve: "It does not prove every low-drift case deserves public space.",
      lesson: "Selective sharpening is the honest answer when the filing stays mostly stable.",
      commonMistake:
        "Overcalling weak change just because the workflow feels obligated to produce drama.",
    },
    artifactPolicy: {
      primary: "Runtime compare plus pilot matrix.",
      optional: "Novelty ledger and skeptic-case material stay secondary.",
    },
  },
  META: {
    ticker: "META",
    companyName: "Meta Platforms",
    sector: "Platforms / Advertising / AI",
    yearFrom: 2024,
    yearTo: 2025,
    surface: "matrix_first",
    publicRoleLabel: "Risk-stack sharpening",
    homeCardLabel: "Risk-stack sharpening",
    chooserCardDescription:
      "A familiar AI theme becomes decision-useful once enforcement and governance specifics land.",
    chooserBestFor: "Sharpened AI risk stack",
    chooserObjectiveLabel: "Risk-stack sharpening",
    methodologyDetail:
      "Shows a persistent theme becoming sharper and more decision-useful when named decisions, obligations, and AI-specific risk arrive.",
    topCue:
      "Risk-stack sharpening: read how a familiar AI and governance theme becomes materially sharper once concrete decisions and obligations land.",
    preview: {
      integratedTitle: "Why this case matters",
      boundedTitle: "Why this read matters",
      roleSummary:
        "The theme already existed. The teaching value is in how named decisions, governance pressure, and AI-specific vulnerabilities make it more decision-useful.",
      subtitleSource: "card_takeaway",
      supportStrategy: "scope_only",
    },
    bandId: "pressure_cases",
    bandLabel: "Added pressure case",
    bandSummary: "AI risk stack under regulatory-decision pressure.",
    teachingSummary:
      "Shows how a persistent theme becomes decision-useful when risk specifics sharpen and regulatory decisions bite.",
    whyCaseExists:
      "The filing sharpens AI, enforcement, youth-safety, and platform-liability risk into a denser decision stack rather than just repeating the old theme.",
    bestUsedWhen: "You need the sharper AI, governance, and enforcement stack.",
    firstQuestion: "Did a familiar theme become materially sharper, or just broader?",
    allowedAnswerShape: "Sharpened risk stack with explicit limits.",
    routeRefuses: "It refuses to treat every repeated AI theme as a new category.",
    whyCaseMatters:
      "It teaches when new decisions and obligations matter more than broad topical overlap.",
    teaching: {
      proves:
        "A familiar theme can become newly decision-useful when specific enforcement, platform-liability, and AI-security details sharpen it.",
      doesntProve: "It does not prove every AI-heavy filing update is genuinely new.",
      lesson: "Look for named decisions, obligations, and mechanisms before claiming novelty.",
      commonMistake:
        "Confusing broader AI vocabulary with a genuinely sharper or more useful risk read.",
    },
    artifactPolicy: {
      primary: "Pilot matrix with P2 as default and P1 as comparator.",
      optional: "Outline compare stays deferred pending manual review.",
    },
  },
  TSLA: {
    ticker: "TSLA",
    companyName: "Tesla",
    sector: "Autos / Autonomy / Energy",
    yearFrom: 2024,
    yearTo: 2025,
    surface: "matrix_first",
    publicRoleLabel: "Policy-shock pivot",
    homeCardLabel: "Policy-shock pivot",
    chooserCardDescription:
      "External pressure turns an EV-manufacturing story into an autonomy, tariffs, and commercialization pivot.",
    chooserBestFor: "Policy shock and platform pivot",
    chooserObjectiveLabel: "Policy-shock pivot",
    methodologyDetail:
      "Shows how external policy shock and platform-roadmap dependence can re-center the filing read.",
    topCue:
      "Policy-shock pivot: read how tariffs, incentives, and autonomy commercialization shift the center of the filing.",
    preview: {
      integratedTitle: "Why this case matters",
      boundedTitle: "Why this read matters",
      roleSummary:
        "The case becomes public because outside pressure turns a familiar manufacturing story into a sharper autonomy, policy, and commercialization read.",
      subtitleSource: "card_takeaway",
      supportStrategy: "scope_only",
    },
    bandId: "pressure_cases",
    bandLabel: "Added pressure case",
    bandSummary: "External shock plus platform-roadmap pivot.",
    teachingSummary:
      "Shows how a filing can pivot from manufacturing execution into autonomy commercialization and policy-shock pressure.",
    whyCaseExists:
      "The filing re-centers around autonomy, Robotaxi, Bots, tariffs, and incentive rollback in a way that changes the first question.",
    bestUsedWhen: "You need the clearest policy-shock and roadmap pivot case.",
    firstQuestion: "Did external pressure change the center of the business-risk story?",
    allowedAnswerShape: "Vivid pivot with explicit mechanism chain.",
    routeRefuses: "It refuses to reduce the change to generic EV-demand commentary.",
    whyCaseMatters:
      "It teaches how policy shock and commercialization dependence can make an external-pressure case vivid without widening the claim.",
    teaching: {
      proves:
        "A filing can pivot from product and manufacturing execution into platform-roadmap and policy-shock risk.",
      doesntProve: "It does not prove every autonomy mention is equally material or public-ready.",
      lesson: "Follow the mechanism chain from policy change to cost, demand, and commercialization dependence.",
      commonMistake:
        "Collapsing a specific autonomy and tariff pivot into generic EV-demand or CEO narrative.",
    },
    artifactPolicy: {
      primary: "Pilot matrix with P2 as default and P1 as comparator.",
      optional: "Outline compare stays deferred pending manual review.",
    },
  },
  WMT: {
    ticker: "WMT",
    companyName: "Walmart",
    sector: "Retail / Omnichannel / Payments",
    yearFrom: 2025,
    yearTo: 2026,
    surface: "matrix_first",
    publicRoleLabel: "Calm operating shift",
    homeCardLabel: "Calm operating shift",
    chooserCardDescription:
      "A calm retail case becomes meaningful once agentic commerce, customer-interface risk, and tariff persistence sharpen.",
    chooserBestFor: "Retail interface and tariff persistence",
    chooserObjectiveLabel: "Calm operating shift",
    methodologyDetail:
      "Shows how a calmer operating case can still earn public space when interface control and tariff pressure become specific.",
    topCue:
      "Calm operating shift: read how agentic commerce, tariff persistence, and customer-interface risk sharpen a seemingly stable retail story.",
    preview: {
      integratedTitle: "Why this case matters",
      boundedTitle: "Why this read matters",
      roleSummary:
        "The case earns public space because a calm retail story still becomes meaningfully sharper once customer-interface and tariff mechanics are explicit.",
      subtitleSource: "card_takeaway",
      supportStrategy: "scope_only",
    },
    bandId: "pressure_cases",
    bandLabel: "Added pressure case",
    bandSummary: "Retail interface and tariff persistence under calm surface movement.",
    teachingSummary:
      "Shows how a calm retail case can still reveal meaningful shifts in customer interface and tariff exposure.",
    whyCaseExists:
      "It adds a retail and agentic-commerce case whose value comes from selective sharpening rather than dramatic rewrite.",
    bestUsedWhen: "You need the calmer retail-interface and tariff case.",
    firstQuestion: "Did a calm operating story become meaningfully sharper in the right places?",
    allowedAnswerShape: "Selective operating shift with a sharper interface read.",
    routeRefuses: "It refuses to treat every refreshed example as a reordered enterprise-risk map.",
    whyCaseMatters:
      "It teaches that a calm public case can still be distinctive when the shift changes customer-interface and pricing pressure.",
    teaching: {
      proves:
        "A seemingly calm retail case can still show meaningful shifts in customer-interface and tariff exposure.",
      doesntProve: "It does not prove the filing was broadly rewritten or re-prioritized end to end.",
      lesson: "Calm cases still matter when the sharpened examples change how the business meets customers and absorbs cost pressure.",
      commonMistake:
        "Dismissing a calm case as weak just because the strongest movement is selective rather than dramatic.",
    },
    artifactPolicy: {
      primary: "Pilot matrix with P2 as default and P1 as comparator.",
      optional: "Outline compare stays deferred pending manual review.",
    },
  },
}

export const CASEBOOK_COMPARISON_ROWS: CasebookComparisonRow[] = [
  {
    label: "First question",
    values: {
      NVDA: PUBLIC_CASEBOOK_CASES.NVDA.firstQuestion,
      LLY: PUBLIC_CASEBOOK_CASES.LLY.firstQuestion,
      KO: PUBLIC_CASEBOOK_CASES.KO.firstQuestion,
      META: PUBLIC_CASEBOOK_CASES.META.firstQuestion,
      TSLA: PUBLIC_CASEBOOK_CASES.TSLA.firstQuestion,
      WMT: PUBLIC_CASEBOOK_CASES.WMT.firstQuestion,
    },
  },
  {
    label: "Allowed answer shape",
    values: {
      NVDA: PUBLIC_CASEBOOK_CASES.NVDA.allowedAnswerShape,
      LLY: PUBLIC_CASEBOOK_CASES.LLY.allowedAnswerShape,
      KO: PUBLIC_CASEBOOK_CASES.KO.allowedAnswerShape,
      META: PUBLIC_CASEBOOK_CASES.META.allowedAnswerShape,
      TSLA: PUBLIC_CASEBOOK_CASES.TSLA.allowedAnswerShape,
      WMT: PUBLIC_CASEBOOK_CASES.WMT.allowedAnswerShape,
    },
  },
  {
    label: "What the route refuses",
    values: {
      NVDA: PUBLIC_CASEBOOK_CASES.NVDA.routeRefuses,
      LLY: PUBLIC_CASEBOOK_CASES.LLY.routeRefuses,
      KO: PUBLIC_CASEBOOK_CASES.KO.routeRefuses,
      META: PUBLIC_CASEBOOK_CASES.META.routeRefuses,
      TSLA: PUBLIC_CASEBOOK_CASES.TSLA.routeRefuses,
      WMT: PUBLIC_CASEBOOK_CASES.WMT.routeRefuses,
    },
  },
  {
    label: "Why this case matters",
    values: {
      NVDA: PUBLIC_CASEBOOK_CASES.NVDA.whyCaseMatters,
      LLY: PUBLIC_CASEBOOK_CASES.LLY.whyCaseMatters,
      KO: PUBLIC_CASEBOOK_CASES.KO.whyCaseMatters,
      META: PUBLIC_CASEBOOK_CASES.META.whyCaseMatters,
      TSLA: PUBLIC_CASEBOOK_CASES.TSLA.whyCaseMatters,
      WMT: PUBLIC_CASEBOOK_CASES.WMT.whyCaseMatters,
    },
  },
  {
    label: "Best used when",
    values: {
      NVDA: PUBLIC_CASEBOOK_CASES.NVDA.bestUsedWhen,
      LLY: PUBLIC_CASEBOOK_CASES.LLY.bestUsedWhen,
      KO: PUBLIC_CASEBOOK_CASES.KO.bestUsedWhen,
      META: PUBLIC_CASEBOOK_CASES.META.bestUsedWhen,
      TSLA: PUBLIC_CASEBOOK_CASES.TSLA.bestUsedWhen,
      WMT: PUBLIC_CASEBOOK_CASES.WMT.bestUsedWhen,
    },
  },
] as const

export function isPublicCasebookTicker(value: string): value is PublicCasebookTicker {
  return PUBLIC_CASEBOOK_TICKERS.includes(value as PublicCasebookTicker)
}

export function isHomeAnchorTicker(value: string): value is HomeAnchorTicker {
  return HOME_ANCHOR_TICKERS.includes(value as HomeAnchorTicker)
}

export function isMatrixFirstPublicTicker(value: string): value is MatrixFirstPublicTicker {
  return MATRIX_FIRST_PUBLIC_TICKERS.includes(value as MatrixFirstPublicTicker)
}

export function getPublicCasebookEntry(
  ticker: string | null | undefined
): PublicCasebookEntry | null {
  if (!ticker) return null
  const normalizedTicker = ticker.trim().toUpperCase()
  if (!isPublicCasebookTicker(normalizedTicker)) return null
  return PUBLIC_CASEBOOK_CASES[normalizedTicker]
}
