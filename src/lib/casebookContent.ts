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
export type PublicCaseSurface = "runtime_full" | "matrix_first"
export type PublicCaseBandId = "anchor_shapes" | "pressure_cases"

export type CaseTeachingLayer = {
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
  publicClaim: string
  proofBasis: string
  stopBoundary: string
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

export type PedagogicCompareExample = {
  ticker: Extract<PublicCasebookTicker, "META" | "TSLA">
  simpleRead: string
  structuredRead: string
  whyItMatters: string
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
      "Start with the three anchor answer shapes. The full Casebook keeps the same claim, proof, and stop grammar under added pressure.",
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
      "The first three teach vivid answer, honest stop, and useful restraint. The full Casebook keeps the same bounded grammar under added pressure.",
    compareTeaser:
      "Methodology uses TSLA and META to show what a simpler read gets right, what structure adds, and why the public route still stays bounded.",
    compareTeaserCta: "See the compare",
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
      "Each public case earns space by teaching a different first question, answer shape, and stopping boundary for the same comparison task.",
    rosterNoteTitle: "Why this roster",
    rosterNoteLead:
      "Each public case earns space by teaching a different kind of judgment. The first three anchor the answer shapes. The second three keep the same grammar under added pressure without promising full depth everywhere.",
    rosterNoteSupport:
      "The roster stays bounded on purpose so the casebook stays curated, not noisy. Some valid candidates stay out when they overlap too much or add too little teaching contrast.",
    boundednessNote:
      "This is a curated six-case roster, not a filing browser, upload flow, or broad benchmark.",
    comparisonTitle: "Cross-case map",
    comparisonIntro:
      "Use one quick map to compare the first question, answer shape, stopping boundary, and best fit for each public case.",
  },
  methodology: {
    title: "Methodology | Document Protocol Lab",
    metaDescription:
      "How the casebook makes bounded document-comparison claims, keeps proof visible, and stops before overclaiming.",
    heading: "Field guide for claim, proof, and stop.",
    intro:
      "The public lab is not trying to answer every document question. It exists to show how a bounded workflow should make a claim, prove it with visible evidence, and stop before the public route overclaims.",
    whyFrontierTitle: "Why not just ask a frontier model?",
    whyFrontierBody: [
      "A strong frontier model can often give you a plausible first read.",
      "This casebook is for when you care about answer shape, proof beside the answer, and where the workflow should stop.",
      "TSLA and META show the difference: the simpler read catches the theme, while the structured read makes the mechanism, ranking, and stopping boundary clearer.",
    ],
    compareTitle: "What the structured read adds",
    compareIntro:
      "These two cases show what a simpler read gets right, what the structured read adds, and why the stronger public route still needs an explicit stop.",
    nonClaimsTitle: "What this lab does not claim",
    nonClaims: [
      "It is not a benchmark of every model or prompt family.",
      "It is not a broad market screener or issuer browser.",
      "It is not proof that every document set needs the same answer shape.",
    ],
    matrixOnlyNote:
      "Some public cases can ship honestly with pilot-matrix evidence only. Matrix-first here means the proof basis is sufficient and the bounded public stop is part of the lesson, not a missing feature.",
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
      "The first three public cases teach the anchor answer shapes: vivid answer, honest stop, and useful restraint.",
    tickers: ["NVDA", "LLY", "KO"],
  },
  {
    id: "pressure_cases",
    title: "Added pressure cases",
    description:
      "The second three show those same judgment habits under AI and regulation, policy shock, and interface pressure.",
    tickers: ["META", "TSLA", "WMT"],
  },
] as const

export const PEDAGOGIC_COMPARE_EXAMPLES: PedagogicCompareExample[] = [
  {
    ticker: "TSLA",
    simpleRead:
      "You quickly see autonomy, tariffs, and roadmap pressure moving closer to the center.",
    structuredRead:
      "P2 keeps the mechanism chain visible: policy shock to cost and demand pressure to commercialization dependence, with proof beside the claim and a clearer stop.",
    whyItMatters:
      "That keeps the case from flattening into generic EV or AI commentary.",
  },
  {
    ticker: "META",
    simpleRead:
      "You quickly see AI and regulation sharpening.",
    structuredRead:
      "P2 separates the repeated AI and privacy scaffold from the newly decision-useful 2025 stack: named decisions, liability shifts, and AI-specific execution risk.",
    whyItMatters:
      "That keeps repeated theme language from masquerading as genuinely new risk.",
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
    publicClaim:
      "FY2025 is vivid enough to support a specific first claim about regulatory and AI-infrastructure execution pressure.",
    proofBasis:
      "Integrated runtime compare on the official FY2024 to FY2025 pair, with the pilot matrix kept nearby as a compact cross-check.",
    stopBoundary:
      "It does not prove a universal benchmark winner or that every filing deserves the same answer-first confidence.",
    homeCardLabel: "Vivid answer",
    chooserCardDescription:
      "The clearest answer-first case when the filing shift is vivid and evidence-adjacent.",
    chooserBestFor: "Strongest answer-first case",
    chooserObjectiveLabel: "Vivid answer",
    methodologyDetail:
      "Shows the workflow at full clarity when the filing shift is vivid enough to support a specific first read.",
    topCue:
      "Vivid answer: make the claim up front, keep proof beside it, and stop before the extra machinery takes over.",
    preview: {
      integratedTitle: "Why this case matters",
      boundedTitle: "Why this read matters",
      roleSummary: "A strong answer-first read can stay specific without pretending to be a universal benchmark.",
      subtitleSource: "card_takeaway",
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
    publicClaim:
      "FY2025 brings obesity-access, pricing, and concentration pressure closer to the center, and the honest public move is to stop there.",
    proofBasis:
      "Matrix-first read on the official FY2024 to FY2025 paragraph packet. The pilot matrix keeps the evidence nearby without implying a full lower public stack.",
    stopBoundary:
      "It does not prove a full lower-audit public route or broader certainty beyond the bounded public read.",
    homeCardLabel: "Honest stop",
    chooserCardDescription:
      "The bounded public route that teaches where to stop before overclaiming.",
    chooserBestFor: "Bounded public route",
    chooserObjectiveLabel: "Honest stop",
    methodologyDetail:
      "Shows why a public case can ship honestly with a matrix-first route when the boundary is part of the lesson.",
    topCue:
      "Honest stop: make the visible claim, inspect the proof, then stop before the public route starts bluffing.",
    preview: {
      integratedTitle: "Why this case matters",
      boundedTitle: "Why this read stops here",
      roleSummary: "The value is not maximal coverage. The value is a public route that stops honestly before pretending to broader certainty.",
      subtitleSource: "card_takeaway",
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
    publicClaim:
      "FY2025 is mostly stable, but a few policy, quality, and concentration details become selectively sharper.",
    proofBasis:
      "Integrated runtime compare on the official FY2024 to FY2025 pair, with the matrix story keeping the calm shift explicit.",
    stopBoundary:
      "It does not prove a dramatic rewrite, broad issuer expansion, or equal weight for every lower layer.",
    homeCardLabel: "Useful restraint",
    chooserCardDescription:
      "The calm low-drift case that proves selective sharpening is still a real answer.",
    chooserBestFor: "Low-drift restraint",
    chooserObjectiveLabel: "Useful restraint",
    methodologyDetail:
      "Shows the workflow staying useful when the filing barely moves and drama would be misleading.",
    topCue:
      "Useful restraint: let the filing stay mostly stable, prove the selective shift, and stop before calm change turns into fake drama.",
    preview: {
      integratedTitle: "Why restraint helps here",
      boundedTitle: "Why restraint helps here",
      roleSummary: "Mostly stable filing; the workflow earns trust by staying selective instead of forcing drama.",
      subtitleSource: "card_takeaway",
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
    publicClaim:
      "FY2025 turns a familiar AI and governance theme into a sharper decision stack once named decisions, liability, and AI-specific vulnerabilities land.",
    proofBasis:
      "Matrix-first read on the official FY2024 to FY2025 paragraph packet. The pilot matrix keeps P2 as the default read and P1 as the compact check.",
    stopBoundary:
      "It does not prove a full novelty map, a benchmark result, or that repeated AI language is automatically new.",
    homeCardLabel: "Risk-stack sharpening",
    chooserCardDescription:
      "A familiar AI theme becomes decision-useful once enforcement and governance specifics land.",
    chooserBestFor: "Sharpened AI risk stack",
    chooserObjectiveLabel: "Risk-stack sharpening",
    methodologyDetail:
      "Shows a persistent theme becoming sharper and more decision-useful when named decisions, obligations, and AI-specific risk arrive.",
    topCue:
      "Risk-stack sharpening: claim only the sharper 2025 stack, prove it on the packet, and stop before repeated theme language turns into false novelty.",
    preview: {
      integratedTitle: "Why this case matters",
      boundedTitle: "Why this read matters",
      roleSummary:
        "The theme already existed. The teaching value is in how named decisions, governance pressure, and AI-specific vulnerabilities make it more decision-useful.",
      subtitleSource: "card_takeaway",
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
    publicClaim:
      "FY2025 re-centers the filing around autonomy commercialization plus tariff and incentive pressure, not just generic EV execution.",
    proofBasis:
      "Matrix-first read on the official FY2024 to FY2025 paragraph packet. The pilot matrix keeps P2 as the default read and P1 as the compact check.",
    stopBoundary:
      "It does not prove a full-filing benchmark result or justify turning a vivid pivot into a totalizing thesis.",
    homeCardLabel: "Policy-shock pivot",
    chooserCardDescription:
      "External pressure turns an EV-manufacturing story into an autonomy, tariffs, and commercialization pivot.",
    chooserBestFor: "Policy shock and platform pivot",
    chooserObjectiveLabel: "Policy-shock pivot",
    methodologyDetail:
      "Shows how external policy shock and platform-roadmap dependence can re-center the filing read.",
    topCue:
      "Policy-shock pivot: claim the re-centering, prove the mechanism chain, and stop before it turns into a full-filing thesis.",
    preview: {
      integratedTitle: "Why this case matters",
      boundedTitle: "Why this read matters",
      roleSummary:
        "The case becomes public because outside pressure turns a familiar manufacturing story into a sharper autonomy, policy, and commercialization read.",
      subtitleSource: "card_takeaway",
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
    publicClaim:
      "FY2026 keeps the broad retail scaffold but makes customer-interface AI, cyber, and tariff persistence materially sharper.",
    proofBasis:
      "Matrix-first read on the official FY2025 to FY2026 paragraph packet. The pilot matrix keeps the selective shift visible without turning the case into a full compare.",
    stopBoundary:
      "It does not prove a rewritten risk map or justify treating a calm case like a dramatic overhaul.",
    homeCardLabel: "Calm operating shift",
    chooserCardDescription:
      "A calm retail case becomes meaningful once agentic commerce, customer-interface risk, and tariff persistence sharpen.",
    chooserBestFor: "Retail interface and tariff persistence",
    chooserObjectiveLabel: "Calm operating shift",
    methodologyDetail:
      "Shows how a calmer operating case can still earn public space when interface control and tariff pressure become specific.",
    topCue:
      "Calm operating shift: claim only the selective sharpening, prove it on the official FY2025 to FY2026 packet, and stop before calm change becomes fake drama.",
    preview: {
      integratedTitle: "Why this case matters",
      boundedTitle: "Why this read matters",
      roleSummary:
        "The case earns public space because a calm retail story still becomes meaningfully sharper once customer-interface and tariff mechanics are explicit.",
      subtitleSource: "card_takeaway",
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
      NVDA: "Strong enough to answer first?",
      LLY: "Where should the public read stop?",
      KO: "Mostly stable, or selectively sharper?",
      META: "Sharper stack, or repeated theme?",
      TSLA: "Did outside pressure re-center the story?",
      WMT: "Calm story, sharper pressure points?",
    },
  },
  {
    label: "Allowed answer",
    values: {
      NVDA: "Answer first, then test",
      LLY: "Bounded public stop",
      KO: "Selective sharpening",
      META: "Sharpened risk stack",
      TSLA: "Policy-shock pivot",
      WMT: "Calm operating shift",
    },
  },
  {
    label: "Stop boundary",
    values: {
      NVDA: "Strong first read, not a universal benchmark",
      LLY: "Stop before public certainty outruns proof",
      KO: "Stay calm; do not force drama",
      META: "Sharper stack, not automatic novelty",
      TSLA: "Mechanism chain, not a full-filing thesis",
      WMT: "Selective sharpening, not a rewritten map",
    },
  },
  {
    label: "Best used for",
    values: {
      NVDA: "Clean answer-first route",
      LLY: "Visible stopping boundary",
      KO: "Low-drift honesty check",
      META: "AI and governance stack",
      TSLA: "Policy-shock pivot",
      WMT: "Retail interface pressure",
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
