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
    "A side-by-side catalog of approaches to business-document comparison, with an honest verdict per case.",
  productStatement:
    "Document Protocol Lab is a side-by-side approach catalog for business-document comparison. It compares plain-prompt, structured-contract, and tagged-protocol reads on six SEC Item 1A pairs, then tells you which approach earned its complexity on each case.",
  home: {
    title: "Document Protocol Lab | Approach Comparison Casebook",
    metaDescription:
      "A side-by-side catalog comparing plain-prompt, structured-contract, and tagged-protocol approaches to business-document comparison across six SEC cases.",
    hook: "Any frontier model can read a 10-K on a plain prompt. The harder question is which approach actually helps.",
    support:
      "Document Protocol Lab compares plain-prompt, structured-contract, and tagged-protocol reads on six SEC Item 1A pairs, and gives an honest verdict about which approach earned its complexity on each case.",
    chooserSummary:
      "Three anchors show where structure earns its weight, where it only sharpens the stop, and when one disciplined read is enough. The rest hold the same comparison under added pressure.",
    whatThisIsTitle: "What this is",
    whatThisIs:
      "A side-by-side approach comparison for business-document analysis: same filings, different approaches, honest verdicts.",
    whatThisIsntTitle: "What this isn't",
    whatThisIsnt:
      "Not a runtime chatbot, a benchmark leaderboard, or a claim that more machinery always wins.",
    whyThisMattersTitle: "Why this matters",
    whyThisMatters: [
      "Better than a single model output when you need to see which approach actually helped.",
      "Better than a benchmark score when you want the evidence beside the verdict.",
      "Better than false certainty when the honest answer is that extra structure did not move the needle.",
    ],
    casebookEntryTitle: "Explore the full casebook",
    casebookEntryBody:
      "The first three teach when structure earns its weight, when it only sharpens the stop, and when one disciplined read is enough. The rest hold the same approach comparison under AI-governance, policy-shock, and calm-interface pressure.",
    compareTeaser:
      "Methodology uses TSLA and META to show what plain prompting catches, what tagging and structured contracts add, and where the extra machinery stops helping.",
    compareTeaserCta: "See the approach comparison",
    casebookEntryCta: "Open the Casebook",
    commonFailureModesTitle: "Common failure modes this lab avoids",
    commonFailureModes: [
      "Mistaking structure for insight",
      "Calling extra machinery a win when it was theater",
      "Treating one case as a universal result",
      "Hiding when plain prompt was already enough",
      "Summarizing without an honest verdict",
    ],
  },
  casebook: {
    title: "Casebook | Document Protocol Lab",
    metaDescription:
      "Six SEC cases, each compared across plain-prompt, structured-contract, and tagged-protocol approaches, with an honest verdict per case.",
    eyebrow: "Casebook",
    heading: "Six approach comparisons on curated filing pairs.",
    intro:
      "Each public case compares plain, structured, and tagged-protocol reads on the same Item 1A pair, then gives an honest verdict about which approach earned its complexity.",
    rosterNoteTitle: "Why this roster",
    rosterNoteLead:
      "Each case earns space by producing a different approach verdict. The first three anchor the outcomes: structure earns its weight, structure only sharpens the stop, one disciplined read is enough. The second three hold the same comparison under AI-governance, policy-shock, and calm-interface pressure.",
    rosterNoteSupport:
      "The roster stays bounded on purpose so each verdict is earned, not padded. Candidates that would overlap or add no fresh verdict stay out.",
    boundednessNote:
      "This is a curated six-case approach catalog, not a filing browser, upload flow, or broad benchmark.",
    comparisonTitle: "Cross-case verdict map",
    comparisonIntro:
      "Use one quick map to compare the first question, approach verdict, stopping boundary, and best fit for each public case.",
  },
  methodology: {
    title: "Methodology | Document Protocol Lab",
    metaDescription:
      "How the lab compares plain-prompt, structured-contract, and tagged-protocol approaches, and how verdicts stay evidence-backed.",
    heading: "Field guide for approach comparison.",
    intro:
      "The lab compares plain-prompt, structured-contract, and tagged-protocol reads on six SEC Item 1A pairs, then gives an honest verdict about whether the extra machinery earned its complexity on each case.",
    whyFrontierTitle: "Why not just ask a frontier model?",
    whyFrontierBody: [
      "A strong frontier model will give you a plausible first read on a plain prompt.",
      "The real question is when adding structure, tagging, or a separate evidence step earns its complexity, and when the extra machinery is theater.",
      "TSLA and META show the difference: the plain-prompt read catches the turn, while the tagged protocol separates ranked specifics from repeated theme language.",
    ],
    compareTitle: "What the tagged protocol actually adds over plain prompt",
    compareIntro:
      "These two cases compare a plain-prompt read and a tagged-protocol read on the same tagged substrate. The verdict is specific: structure helps when ranking novelty over repeated theme language matters.",
    nonClaimsTitle: "What this lab does not claim",
    nonClaims: [
      "Not a benchmark across every model or prompt family.",
      "Not a broad document chatbot or filing browser.",
      "Not a claim that any one approach always wins.",
    ],
    matrixOnlyNote:
      "Some public cases ship honestly with pilot-matrix evidence only. Matrix-first means the approach comparison is sufficient and the bounded public stop is part of the verdict, not a missing feature.",
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
    title: "Anchor approach verdicts",
    description:
      "The first three cases anchor where structure earns its cost (NVDA), where it sharpens the public stop (LLY), and where one disciplined read is honestly enough (KO).",
    tickers: ["NVDA", "LLY", "KO"],
  },
  {
    id: "pressure_cases",
    title: "Approaches under added pressure",
    description:
      "The second three put the same approaches under AI and governance pressure (META), outside policy shock (TSLA), and customer-interface pressure (WMT).",
    tickers: ["META", "TSLA", "WMT"],
  },
] as const

export const PEDAGOGIC_COMPARE_EXAMPLES: PedagogicCompareExample[] = [
  {
    ticker: "TSLA",
    simpleRead:
      "A plain prompt lists autonomy, tariffs, and roadmap pressure side by side, without showing how they actually pressure the story.",
    structuredRead:
      "The tagged protocol keeps a mechanism chain visible: outside policy shock into cost and demand pressure into commercialization dependence, with proof tied to each step.",
    whyItMatters:
      "This is where a structured approach turns a flat list into an auditable mechanism story, instead of flattening into generic EV or AI commentary.",
  },
  {
    ticker: "META",
    simpleRead:
      "A plain prompt flags AI and regulation as sharper, but it blurs repeated scaffolding together with the newly decision-useful items.",
    structuredRead:
      "The tagged protocol separates the ongoing AI and privacy scaffold from the 2025 stack: named decisions, liability shifts, and AI-specific execution risk.",
    whyItMatters:
      "This is where a structured approach earns its cost: it stops repeated theme language from masquerading as genuinely new risk.",
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
    publicRoleLabel: "Structure earns its weight",
    publicClaim:
      "The FY2024 to FY2025 shift is vivid enough that plain prompting catches the turn; the structured tagged read materially lifts specificity, ranking, and auditability on the same evidence.",
    proofBasis:
      "Integrated runtime compare on the official FY2024 to FY2025 pair, with a four-cell pilot matrix (control, reuse-filtered input, tagged packet, tagged protocol) on the same substrate.",
    stopBoundary:
      "It does not prove that structure always wins or that this single-case lift generalizes across issuers.",
    homeCardLabel: "Structure earns its weight",
    chooserCardDescription:
      "The case where moving from a plain baseline to a structured tagged read materially lifts specificity, ranking, and auditability on the same evidence.",
    chooserBestFor: "Where structure clearly pays off",
    chooserObjectiveLabel: "Structure earns its weight",
    methodologyDetail:
      "Shows how moving from a plain baseline to a structured tagged read materially lifts specificity, ranking, and auditability on the same evidence substrate.",
    topCue:
      "Approach verdict: plain prompt catches the turn, but the structured tagged read materially lifts specificity and auditability on NVDA.",
    preview: {
      integratedTitle: "Why this case matters",
      boundedTitle: "Why this read matters",
      roleSummary: "A strong answer-first read can stay specific without pretending to be a universal benchmark.",
      subtitleSource: "card_takeaway",
    },
    bandId: "anchor_shapes",
    bandLabel: "Anchor approach verdict",
    bandSummary: "The clearest case where structure materially lifts the read.",
    teachingSummary:
      "Shows how a vivid filing shift still benefits from structure: more ranked, more auditable, and more specific than a plain baseline.",
    whyCaseExists:
      "The vivid FY2024 to FY2025 shift is the cleanest place to see what a structured tagged read adds over a plain baseline on the same evidence.",
    bestUsedWhen: "You want the cleanest case for structure earning its complexity.",
    firstQuestion: "Does the structured read materially beat the plain baseline here?",
    allowedAnswerShape: "Answer-first claim with visible lift from structure.",
    routeRefuses: "It refuses to turn a single-case lift into a universal benchmark result.",
    whyCaseMatters:
      "It proves that extra structure can be worth its cost, without pretending every case has the same lift.",
    teaching: {
      commonMistake:
        "Assuming a clear structural lift on one case means structure always earns its cost on every other case.",
    },
    artifactPolicy: {
      primary: "Runtime compare plus four-cell pilot matrix.",
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
    publicRoleLabel: "Structure sharpens the stop",
    publicClaim:
      "All three approaches converge on obesity-access, pricing, and concentration as the center; the structured tagged read only sharpens where the bounded public read should stop.",
    proofBasis:
      "Matrix-first read on the official FY2024 to FY2025 paragraph packet. A three-cell pilot matrix (control, tagged packet, tagged protocol) shows structure sharpening the stop without extending it.",
    stopBoundary:
      "It does not prove that more structure buys more certainty beyond the bounded public read, or justify a full lower-audit stack on the public route.",
    homeCardLabel: "Structure sharpens the stop",
    chooserCardDescription:
      "The bounded case where every approach converges on the same public read. Structure sharpens the stop; it does not extend it.",
    chooserBestFor: "Where structure cannot buy more truth",
    chooserObjectiveLabel: "Structure sharpens the stop",
    methodologyDetail:
      "Shows how a bounded case stays bounded even when more structure is available: the approach can sharpen the stop, not move it.",
    topCue:
      "Approach verdict: all three reads converge on the same bounded public read; tagged protocol only sharpens where LLY should stop.",
    preview: {
      integratedTitle: "Why this case matters",
      boundedTitle: "Why this read stops here",
      roleSummary: "The value is not maximal coverage. The value is a public route that stops honestly before pretending to broader certainty.",
      subtitleSource: "card_takeaway",
    },
    bandId: "anchor_shapes",
    bandLabel: "Anchor approach verdict",
    bandSummary: "The case where structure clarifies the stop but cannot extend it.",
    teachingSummary:
      "Shows how a bounded case stays bounded even when more approaches are applied: structure sharpens where to stop, not how far to reach.",
    whyCaseExists:
      "Policy, pricing, and concentration pressure make a bounded public read clearly correct, and the approach comparison only sharpens where it ends.",
    bestUsedWhen: "You need to see an approach that earns its discipline by stopping honestly.",
    firstQuestion: "Does added structure buy more truth on a bounded case?",
    allowedAnswerShape: "Bounded public read with the stop sharpened by structure.",
    routeRefuses: "It refuses to pretend that more approach machinery buys more certainty.",
    whyCaseMatters:
      "It teaches that approach sophistication can sharpen a stop without being able to move it, and that honest stopping is itself a verdict.",
    teaching: {
      commonMistake:
        "Assuming more approach layers will extend a bounded read, rather than just sharpen where it should stop.",
    },
    artifactPolicy: {
      primary: "Three-cell pilot matrix (control, tagged packet, tagged protocol).",
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
    publicRoleLabel: "One disciplined read is enough",
    publicClaim:
      "On a calm filing, one restrained primary read already surfaces the selective sharpening; layering a narrower novelty ledger adds only situational lift.",
    proofBasis:
      "Integrated runtime compare on the official FY2024 to FY2025 pair, with a single disciplined primary-read cell plus a narrower novelty-ledger cross-check.",
    stopBoundary:
      "It does not prove a dramatic rewrite, broad issuer expansion, or that layering more approaches helps on low-drift cases.",
    homeCardLabel: "One disciplined read is enough",
    chooserCardDescription:
      "The calm case where one restrained primary read stays useful and extra approach layers add only situational lift.",
    chooserBestFor: "Where layering more approaches stops helping",
    chooserObjectiveLabel: "One disciplined read is enough",
    methodologyDetail:
      "Shows how a single disciplined approach stays honest on a mostly stable filing, and why adding a narrower novelty layer gives only classification-sensitive lift.",
    topCue:
      "Approach verdict: on a low-drift filing, one restrained primary read already captures the selective shift; extra approach layers add only narrower, situational lift.",
    preview: {
      integratedTitle: "Why restraint helps here",
      boundedTitle: "Why restraint helps here",
      roleSummary: "Mostly stable filing; the workflow earns trust by staying selective instead of forcing drama.",
      subtitleSource: "card_takeaway",
      showRestraintStrip: true,
    },
    bandId: "anchor_shapes",
    bandLabel: "Anchor approach verdict",
    bandSummary: "The calm case where one disciplined read beats layered machinery.",
    teachingSummary:
      "Shows that on a mostly stable filing, one restrained primary read captures the real signal; extra approach layers add only narrower classification lift.",
    whyCaseExists:
      "The filing barely moves, which turns the approach question into 'which layer is worth keeping' rather than 'which approach wins.'",
    bestUsedWhen: "You want to see where layering more approaches stops helping.",
    firstQuestion: "Does layering more approaches add truth on a low-drift filing?",
    allowedAnswerShape: "Selective sharpening delivered by a single disciplined read.",
    routeRefuses: "It refuses to force drama by stacking approaches that the case does not reward.",
    whyCaseMatters:
      "It proves that 'which approach helps' sometimes answers with 'the simplest disciplined one already does.'",
    teaching: {
      commonMistake:
        "Stacking more approach layers on a low-drift case in the hope of manufacturing novelty.",
    },
    artifactPolicy: {
      primary: "Runtime compare plus primary-read pilot matrix cell.",
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
    publicRoleLabel: "Tagged protocol ranks the novelty",
    publicClaim:
      "The tagged protocol read most clearly ranks 2025-specific decisions above repeated AI/privacy scaffold; the plain and structured reads catch the turn but leave the ranking blurred.",
    proofBasis:
      "Matrix-first read on the official FY2024 to FY2025 paragraph packet. A three-cell pilot matrix (plain prompt, structured contract, tagged protocol) on the same tagged substrate.",
    stopBoundary:
      "It does not prove a full novelty map, a benchmark result, or that every repeated AI theme line is automatically new.",
    homeCardLabel: "Tagged protocol ranks the novelty",
    chooserCardDescription:
      "The case where the tagged protocol best ranks named 2025 decisions above repeated theme language; looser approaches catch the turn but leave the ranking blurred.",
    chooserBestFor: "Where tagging separates sharpening from repetition",
    chooserObjectiveLabel: "Tagged protocol ranks the novelty",
    methodologyDetail:
      "Shows how a tagged protocol separates a genuinely sharper 2025 decision stack from repeated theme language when the filing adds specifics without rewriting.",
    topCue:
      "Approach verdict: on META, tagged protocol best ranks 2025-specific decisions; structured contract stays useful but broader; plain prompt loses ranking discipline.",
    preview: {
      integratedTitle: "Why this case matters",
      boundedTitle: "Why this read matters",
      roleSummary:
        "The theme already existed. The teaching value is in how named decisions, governance pressure, and AI-specific vulnerabilities make it more decision-useful.",
      subtitleSource: "card_takeaway",
    },
    bandId: "pressure_cases",
    bandLabel: "Pressure approach verdict",
    bandSummary: "The case where tagged protocol pays off in novelty ranking.",
    teachingSummary:
      "Shows how a tagged protocol separates a genuinely sharper decision stack from repeated theme language, where looser approaches leave that distinction blurred.",
    whyCaseExists:
      "The filing adds named 2025 decisions on top of a familiar AI theme, so the approach question becomes whether structure can separate sharpening from repetition.",
    bestUsedWhen: "You want to see where tagging beats plain prompting on novelty ranking.",
    firstQuestion: "Can a tagged protocol separate a sharper stack from repeated theme language?",
    allowedAnswerShape: "Ranked 2025 decision stack with repeated theme held separately.",
    routeRefuses: "It refuses to treat every repeated AI theme line as a fresh category.",
    whyCaseMatters:
      "It teaches where structure adds decision-usefulness by ranking novelty, not by summarizing more.",
    teaching: {
      commonMistake:
        "Confusing broader AI vocabulary with a genuinely sharper or more decision-useful risk stack.",
    },
    artifactPolicy: {
      primary: "Three-cell pilot matrix (plain prompt, structured contract, tagged protocol).",
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
    publicRoleLabel: "Structure exposes the mechanism",
    publicClaim:
      "The tagged protocol read best exposes the policy shock to cost to commercialization mechanism chain; plain and structured reads catch the pivot but blur the chain.",
    proofBasis:
      "Matrix-first read on the official FY2024 to FY2025 paragraph packet. A three-cell pilot matrix (plain prompt, structured contract, tagged protocol) on the same tagged substrate.",
    stopBoundary:
      "It does not prove a full-filing benchmark result or justify turning a vivid pivot into a totalizing thesis.",
    homeCardLabel: "Structure exposes the mechanism",
    chooserCardDescription:
      "The case where tagged protocol best exposes the policy shock to cost to commercialization chain; looser approaches flatten it into generic EV commentary.",
    chooserBestFor: "Where structure preserves a mechanism chain",
    chooserObjectiveLabel: "Structure exposes the mechanism",
    methodologyDetail:
      "Shows how protocol framing makes a mechanism chain visible under external pressure, keeping the pivot specific instead of flattening it into a generic demand story.",
    topCue:
      "Approach verdict: on TSLA, tagged protocol best exposes the mechanism chain; structured contract stays useful but broader; plain prompt is less disciplined about policy and commercialization specifics.",
    preview: {
      integratedTitle: "Why this case matters",
      boundedTitle: "Why this read matters",
      roleSummary:
        "The case becomes public because outside pressure turns a familiar manufacturing story into a sharper autonomy, policy, and commercialization read.",
      subtitleSource: "card_takeaway",
    },
    bandId: "pressure_cases",
    bandLabel: "Pressure approach verdict",
    bandSummary: "The case where tagged protocol preserves the mechanism chain.",
    teachingSummary:
      "Shows how protocol framing keeps a policy-shock mechanism chain visible where looser approaches flatten it into generic EV commentary.",
    whyCaseExists:
      "Outside pressure re-centers the filing around autonomy, tariffs, and commercialization, so the approach question becomes whether structure can preserve the mechanism chain.",
    bestUsedWhen: "You want to see where structure beats plain prompting on mechanism preservation.",
    firstQuestion: "Can a tagged protocol preserve a mechanism chain under policy shock?",
    allowedAnswerShape: "Ranked pivot with the policy to commercialization chain kept visible.",
    routeRefuses: "It refuses to reduce the change to generic EV-demand or CEO narrative.",
    whyCaseMatters:
      "It teaches that structure can earn its weight by preserving mechanism specificity, not by adding more bullet points.",
    teaching: {
      commonMistake:
        "Collapsing a specific autonomy and tariff pivot into a generic EV-demand read that a plainer approach can also produce.",
    },
    artifactPolicy: {
      primary: "Three-cell pilot matrix (plain prompt, structured contract, tagged protocol).",
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
    publicRoleLabel: "Structure prevents overreading",
    publicClaim:
      "The tagged protocol read best preserves the calm selective-shift boundary; plain and structured reads catch the same movement but risk turning refreshed examples into false novelty.",
    proofBasis:
      "Matrix-first read on the official FY2025 to FY2026 paragraph packet. A three-cell pilot matrix (plain prompt, structured contract, tagged protocol) on the same tagged substrate.",
    stopBoundary:
      "It does not prove a rewritten risk map or justify treating a calm case like a dramatic overhaul.",
    homeCardLabel: "Structure prevents overreading",
    chooserCardDescription:
      "The calm case where tagged protocol best preserves the selective-shift boundary; looser approaches risk turning refreshed examples into false novelty.",
    chooserBestFor: "Where structure bounds an overread",
    chooserObjectiveLabel: "Structure prevents overreading",
    methodologyDetail:
      "Shows how protocol framing keeps a calm retail shift bounded, where looser approaches inflate refreshed examples into novelty.",
    topCue:
      "Approach verdict: on WMT, tagged protocol keeps the calm boundary; structured contract stays useful but broader; plain prompt risks overreading refreshed specifics.",
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
    label: "Approaches in play",
    values: {
      NVDA: "Plain baseline, reuse-filtered input, tagged packet, tagged protocol",
      LLY: "Tagged packet versus tagged protocol on the same pair",
      KO: "One disciplined structured read (no second approach needed)",
      META: "Plain prompt, structured contract, tagged protocol",
      TSLA: "Plain prompt, structured contract, tagged protocol",
      WMT: "Structured contract versus tagged protocol on the same pair",
    },
  },
  {
    label: "Approach verdict",
    values: {
      NVDA: "Plain prompt catches the turn; structure materially lifts specificity and auditability.",
      LLY: "Structure sharpens the public stop without letting the read overrun the evidence.",
      KO: "One disciplined read is enough; extra approaches would add noise, not signal.",
      META: "Tagged protocol ranks newly decision-useful items above repeated theme language.",
      TSLA: "Tagged protocol exposes a mechanism chain that a plain list cannot hold together.",
      WMT: "Structured approaches prevent a calm case from being overread into false drama.",
    },
  },
  {
    label: "Stop boundary",
    values: {
      NVDA: "A one-case lift does not turn structure into a universal benchmark win.",
      LLY: "The sharper stop is still a stop; public reads stay bounded by proof.",
      KO: "One strong read here is not proof that plain prompting always suffices.",
      META: "A sharper stack is not the same as automatic novelty or decision-readiness.",
      TSLA: "A mechanism chain is not a full-filing thesis or a forecast.",
      WMT: "Selective pressure is not a rewritten strategic map.",
    },
  },
  {
    label: "Best used for",
    values: {
      NVDA: "Showing where structure clearly earns its cost.",
      LLY: "Watching structure tighten a bounded public stop.",
      KO: "Teaching restraint — resisting the urge to add more approaches.",
      META: "Separating recycled scaffolding from genuinely new risk.",
      TSLA: "Turning a flat list into an auditable mechanism story.",
      WMT: "Holding a calm case to selective structural pressure.",
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
