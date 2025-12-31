// JSON contract types (see docs/sec_narrative_drift_codex_spec_v1_11.md)

export type Meta = {
  ticker: string;
  cik: string;
  companyName: string;
  lastUpdatedUtc: string;
  formsIncluded: string[];
  sectionsIncluded: string[];
  notes: string[];
  extraction?: MetaExtraction;
};

export type MetaExtraction = {
  section: string;
  method: string;
  confidence: number;
  warnings: string[];
  lengthChars?: number;
  endMarkerUsed?: string | null;
  hasItem1C?: boolean;
};

export type ExtractionInfo = {
  confidence: number;
  method: string;
  errors: string[];
};

export type FilingRow = {
  year: number;
  form: string;
  filingDate: string;
  reportDate: string;
  accessionNumber: string;
  primaryDocument: string;
  secUrl: string;
  extraction: ExtractionInfo;
};

export type Metrics = {
  section: string;
  years: number[];
  drift_vs_prev: Array<number | null>;
  drift_ci_low: Array<number | null>;
  drift_ci_high: Array<number | null>;
  boilerplate_score: Array<number | null>;
};

export type SimilarityMatrix = {
  section: string;
  years: number[];
  cosineSimilarity: number[][];
};

export type ShiftTermItem = {
  term: string;
  score: number;
  // Optional richer stats (present in newer datasets)
  z?: number;
  countPrev?: number;
  countCurr?: number;
  per10kPrev?: number;
  per10kCurr?: number;
  deltaPer10k?: number;
  distinctive?: boolean;
  includes?: string[];
};

export type ShiftTerm = string | ShiftTermItem;

export type ShiftPair = {
  from: number;
  to: number;
  topRisers: ShiftTerm[];
  topFallers: ShiftTerm[];
  summary: string;
  // Optional alternate lens (e.g., TextRank keyphrases)
  topRisersAlt?: ShiftTerm[];
  topFallersAlt?: ShiftTerm[];
  summaryAlt?: string;
};

export type ShiftPairs = {
  section: string;
  yearPairs: ShiftPair[];
};

export type ExcerptParagraph = {
  year: number;
  paragraphIndex: number;
  text: string;
};

export type ExcerptPair = {
  from: number;
  to: number;
  highlightTerms: string[];
  representativeParagraphs: ExcerptParagraph[];
};

export type Excerpts = {
  section: string;
  pairs: ExcerptPair[];
};

export type QualityLevel = "high" | "medium" | "low" | "unknown";

export type CompanyIndexRow = {
  ticker: string;
  companyName: string;
  cik: string;
  sic?: string;
  sicDescription?: string;
  exchange?: string;
  coverage: {
    years: number[];
    count: number;
    minYear: number;
    maxYear: number;
  };
  quality: {
    level: QualityLevel;
    minConfidence?: number;
    medianConfidence?: number;
    notes?: string[];
  };
  metricsSummary?: {
    peakDrift?: { from: number; to: number; value: number };
    latestDrift?: { from: number; to: number; value: number };
  };
  autoPair?: { from: number; to: number };
  featuredCase?: {
    from: number;
    to: number;
    title: string;
    blurb: string;
    tags?: string[];
  };
};

export type CompanyIndex = {
  version: number;
  generatedAtUtc: string;
  section: string;
  lookbackTargetYears: number;
  companyCount: number;
  companies: CompanyIndexRow[];
};

export type FeaturedCase = {
  id: string;
  ticker: string;
  headline: string;
  hook: string;
  defaultPair: { from: number; to: number };
  tags?: string[];
  cta: string;
};

export type FeaturedCases = {
  version: string;
  updatedAt: string;
  cases: FeaturedCase[];
};

export type UniverseEntry = {
  ticker: string;
  theme: string;
  why?: string;
  bestYearPairs?: string[];
  tags?: string[];
};

export type UniverseFeatured = {
  version: string;
  notes: string;
  anchors: UniverseEntry[];
  stories: UniverseEntry[];
};
