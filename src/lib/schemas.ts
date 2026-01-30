// Runtime schema validation using Zod
// These schemas match the TypeScript types in types.ts

import { z } from "zod"

// Quality level enum
const QualityLevelSchema = z.enum(["high", "medium", "low", "unknown"])

// Meta extraction info
const MetaExtractionSchema = z.object({
  section: z.string(),
  method: z.string(),
  confidence: z.number(),
  warnings: z.array(z.string()),
  lengthChars: z.number().optional(),
  endMarkerUsed: z.string().nullable().optional(),
  hasItem1C: z.boolean().optional(),
})

// Company metadata
export const MetaSchema = z.object({
  ticker: z.string(),
  cik: z.string(),
  companyName: z.string(),
  lastUpdatedUtc: z.string(),
  formsIncluded: z.array(z.string()),
  sectionsIncluded: z.array(z.string()),
  notes: z.array(z.string()),
  extraction: MetaExtractionSchema.optional(),
})

// Extraction info for filings
const ExtractionInfoSchema = z.object({
  confidence: z.number(),
  method: z.string(),
  errors: z.array(z.string()),
})

// Filing row
const FilingRowSchema = z.object({
  year: z.number(),
  form: z.string(),
  filingDate: z.string(),
  reportDate: z.string(),
  accessionNumber: z.string(),
  primaryDocument: z.string(),
  secUrl: z.string(),
  extraction: ExtractionInfoSchema,
})

export const FilingRowsSchema = z.array(FilingRowSchema)

// Metrics
export const MetricsSchema = z.object({
  section: z.string(),
  years: z.array(z.number()),
  drift_vs_prev: z.array(z.number().nullable()),
  drift_ci_low: z.array(z.number().nullable()),
  drift_ci_high: z.array(z.number().nullable()),
  boilerplate_score: z.array(z.number().nullable()),
})

// Similarity matrix
export const SimilarityMatrixSchema = z.object({
  section: z.string(),
  years: z.array(z.number()),
  cosineSimilarity: z.array(z.array(z.number())),
})

// Shift term (can be string or detailed object)
const ShiftTermItemSchema = z.object({
  term: z.string(),
  score: z.number(),
  z: z.number().optional(),
  countPrev: z.number().optional(),
  countCurr: z.number().optional(),
  per10kPrev: z.number().optional(),
  per10kCurr: z.number().optional(),
  deltaPer10k: z.number().optional(),
  distinctive: z.boolean().optional(),
  includes: z.array(z.string()).optional(),
})

const ShiftTermSchema = z.union([z.string(), ShiftTermItemSchema])

// Shift pair
const ShiftPairSchema = z.object({
  from: z.number(),
  to: z.number(),
  topRisers: z.array(ShiftTermSchema),
  topFallers: z.array(ShiftTermSchema),
  summary: z.string(),
  topRisersAlt: z.array(ShiftTermSchema).optional(),
  topFallersAlt: z.array(ShiftTermSchema).optional(),
  summaryAlt: z.string().optional(),
})

export const ShiftPairsSchema = z.object({
  section: z.string(),
  yearPairs: z.array(ShiftPairSchema),
})

// Excerpt paragraph
const ExcerptParagraphSchema = z.object({
  year: z.number(),
  paragraphIndex: z.number(),
  text: z.string(),
})

// Excerpt pair
const ExcerptPairSchema = z.object({
  from: z.number(),
  to: z.number(),
  highlightTerms: z.array(z.string()),
  representativeParagraphs: z.array(ExcerptParagraphSchema),
})

export const ExcerptsSchema = z.object({
  section: z.string(),
  pairs: z.array(ExcerptPairSchema),
})

// Company index row
const CompanyIndexRowSchema = z.object({
  ticker: z.string(),
  companyName: z.string(),
  cik: z.string(),
  sic: z.string().optional(),
  sicDescription: z.string().optional(),
  exchange: z.string().optional(),
  coverage: z.object({
    years: z.array(z.number()),
    count: z.number(),
    minYear: z.number(),
    maxYear: z.number(),
  }),
  quality: z.object({
    level: QualityLevelSchema,
    minConfidence: z.number().optional(),
    medianConfidence: z.number().optional(),
    notes: z.array(z.string()).optional(),
  }),
  metricsSummary: z.object({
    peakDrift: z.object({ from: z.number(), to: z.number(), value: z.number() }).optional(),
    latestDrift: z.object({ from: z.number(), to: z.number(), value: z.number() }).optional(),
  }).optional(),
  autoPair: z.object({ from: z.number(), to: z.number() }).optional(),
  featuredCase: z.object({
    from: z.number(),
    to: z.number(),
    title: z.string(),
    blurb: z.string(),
    tags: z.array(z.string()).optional(),
  }).optional(),
})

export const CompanyIndexSchema = z.object({
  version: z.number(),
  generatedAtUtc: z.string(),
  section: z.string(),
  lookbackTargetYears: z.number(),
  companyCount: z.number(),
  companies: z.array(CompanyIndexRowSchema),
})

// Featured case
const FeaturedCaseSchema = z.object({
  id: z.string(),
  ticker: z.string(),
  headline: z.string(),
  hook: z.string(),
  defaultPair: z.object({ from: z.number(), to: z.number() }),
  tags: z.array(z.string()).optional(),
  cta: z.string(),
})

export const FeaturedCasesSchema = z.object({
  version: z.string(),
  updatedAt: z.string(),
  cases: z.array(FeaturedCaseSchema),
})

// Universe entry
const UniverseEntrySchema = z.object({
  ticker: z.string(),
  theme: z.string(),
  why: z.string().optional(),
  bestYearPairs: z.array(z.string()).optional(),
  tags: z.array(z.string()).optional(),
})

export const UniverseFeaturedSchema = z.object({
  version: z.string(),
  notes: z.string(),
  anchors: z.array(UniverseEntrySchema),
  stories: z.array(UniverseEntrySchema),
})

// Validation helper with error logging
export function parseWithSchema<T>(
  schema: z.ZodSchema<T>,
  data: unknown,
  context: string
): T {
  const result = schema.safeParse(data)
  if (!result.success) {
    console.warn(`Schema validation warning for ${context}:`, result.error.issues)
    // Return data as-is if validation fails (graceful degradation)
    // This allows the app to continue working with legacy data
    return data as T
  }
  return result.data
}
