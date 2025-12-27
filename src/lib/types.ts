// JSON contract types (see docs/sec_narrative_drift_codex_spec_v1_11.md)

export type Meta = {
  ticker: string;
  cik: string;
  companyName: string;
  lastUpdatedUtc: string;
  formsIncluded: string[];
  sectionsIncluded: string[];
  notes: string[];
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

export type ShiftTerm = {
  term: string;
  score: number;
};

export type ShiftPair = {
  from: number;
  to: number;
  topRisers: ShiftTerm[];
  topFallers: ShiftTerm[];
  summary: string;
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
