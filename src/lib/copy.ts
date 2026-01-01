// src/lib/copy.ts
/**
 * SEC Narrative Drift — Copy System (Single public tone)
 *
 * Portfolio guidance: ship ONE public tone. Keep humor understated and embedded in a few
 * high-traffic helpers/footnotes. Some people gave feedback that I should edit down my tone for professional credibility.
 *
 * Usage:
 *   import { copy, t } from "@/lib/copy";
 */

export function t(template: string, params?: Record<string, string | number | null | undefined>): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (_, key: string) => {
    const v = params[key];
    return v === null || v === undefined ? "" : String(v);
  });
}

export const copy = {
  global: {
    appName: "SEC Narrative Drift",
    subtitle: "How 10‑K “Risk Factors” language changes over time (Item 1A)",
    oneLiner: "A fast, auditable way to spot when the risk story changed — and read the exact paragraphs.",
    sourceLine: "Source: SEC EDGAR (10‑K and 20-Ffilings).",
    caveatLine: "Descriptive, not causal. Use drift as a reading prompt, not a conclusion.",
    disclaimerLine: "Not investment advice. For informational analysis of public filings.",
    loading: {
      base: "Loading…",
      filings: "Loading filings…",
      charts: "Rendering charts…",
    },
    errors: {
      missingDataset:
        "We couldn’t load this dataset. Try a featured company — those are precomputed and demo‑safe.",
      missingExcerpts: "We have metrics for this pair, but no excerpt set yet.",
      noShifts: "No clear “top movers” for this year pair (which is itself a result).",
      lowConfidenceYear:
        "This year’s Item 1A extraction is low confidence. Treat metrics with caution and use the “View on SEC” link to verify.",
    },
  },

  nav: {
    home: "Home",
    companies: "Companies",
    company: "Company",
    methodology: "Methodology",
    dataQuality: "Data Quality",
  },

  buttons: {
    exploreFeatured: "Explore a featured company",
    browseCompanies: "Browse list of companies",
    startTour: "Start tour",
    resetSelection: "Reset selection",
    details: "Details",
    exportExecBrief: "Export Exec Brief",
    export: "Export",
  },

  home: {
    heroTitle: "Narrative Drift, by the numbers — and by the paragraph",
    heroBody:
      "Pick a company and see how its 10‑K Risk Factors language changes year‑to‑year, where the biggest shifts happen, and the terms that move the most.",
    // High-traffic understated humor: most users see this.
    heroFootnote: "Featured companies are precomputed, because live demos are a form of optimism.",
    featuredHeading: "Featured companies",
    featuredHelper: "Three precomputed datasets. Click one to start.",
    howToReadTitle: "How to read this",
    howToReadSteps: {
      drift: "Drift timeline: spot the year the wording changes most.",
      similarity: "Similarity heatmap: pick two years to compare.",
      evidence: "Evidence excerpts: read the paragraphs that moved.",
    },
    exampleLabel: "Example insight",
    exampleText:
      "NVDA: a 2021 spike pairs with pandemic-era terms in Item 1A. Use it as a prompt to read, not a verdict.",
    exampleLink: "Open NVDA",
  },

  companies: {
    title: "Company directory",
    coverageLine: "{n} companies, up to {target} years each.",
    searchPlaceholder: "Search ticker or name",
    searchAria: "Search companies",
    coverageFilterAria: "Filter by coverage",
    storyFilterAria: "Filter by story companies",
    exchangeFilterAria: "Filter by exchange",
    qualityFilterAria: "Filter by data quality",
    sortAria: "Sort companies",
    filters: {
      coverageAll: "Coverage: all",
      coverageGe8: "Coverage: 8+ years",
      storyAll: "Story: all",
      storyOnly: "Story: only",
      exchangeAll: "Exchange: all",
      qualityAll: "Quality: all",
      qualityHigh: "Quality: high",
      qualityHighMed: "Quality: high + medium",
    },
    sort: {
      featured: "Sort: featured",
      az: "Sort: A-Z",
      peakDrift: "Sort: peak drift",
      coverage: "Sort: coverage",
    },
    featuredTitle: "Featured cases",
    featuredChip: "Featured",
    storyChip: "Story",
    compareYearsLabel: "Compare {from}-{to}",
    resultsCount: "{n} results",
    peakDriftLabel: "Peak drift {from}-{to}: {v}",
    jumpBiggestShift: "Jump to biggest shift",
    latestYearLabel: "Latest",
    latestYearUnknown: "Latest: -",
  },

  company: {
    labels: {
      company: "Company",
      section: "Section",
      years: "Years",
    },
    sectionValueMvp: "10‑K Item 1A — Risk Factors",
    topButtons: {
      allCompanies: "All companies",
      methodology: "Methodology",
      dataQuality: "Data Quality",
      startTour: "Start tour",
      exportExecBrief: "Export Exec Brief",
    },
    callouts: {
      largestDrift: {
        label: "Largest drift year",
        tooltip: "Highest drift vs prior year (1 − cosine similarity).",
      },
      mostStable: {
        label: "Most stable year",
        tooltip: "Lowest drift vs prior year (excluding null).",
      },
      // Understated Barry-ish corporate-speak humor; still clear.
      highestBoilerplate: {
        label: "Most templated year",
        tooltip: "Approx. reuse rate of sentences across years.",
      },
    },
    executiveSummary: {
      title: "Executive summary",
      helper: "Largest drift year, confidence band, and the terms that moved most.",
      largestDriftLine: ({
        year,
        prevYear,
      }: {
        year: number | string
        prevYear: number | string
      }) => t("Largest drift year: {year} (vs {prevYear})", { year, prevYear }),
      driftCiLine: ({
        drift,
        low,
        high,
      }: {
        drift: string
        low: string
        high: string
      }) => t("Drift: {drift} | 95% CI: {low}-{high}", { drift, low, high }),
      jumpButton: "Jump to largest drift pair",
      noTerms: "No clear movers for this pair.",
      empty: "Not enough data to compute a largest drift year.",
      subtleLine: "If the line spikes, the filing got a rewrite.",
    },
    selectedPairCallout: {
      label: "Selected pair",
      title: ({
        fromYear,
        toYear,
      }: {
        fromYear: number | string
        toYear: number | string
      }) => t("Comparing {fromYear} vs {toYear}", { fromYear, toYear }),
      driftLine: ({ drift }: { drift: string }) =>
        t("Drift vs prior year: {drift}", { drift }),
      driftWithCi: ({
        drift,
        low,
        high,
      }: {
        drift: string
        low: string
        high: string
      }) => t("Drift vs prior year: {drift} (95% CI {low}-{high})", {
        drift,
        low,
        high,
      }),
      driftUnavailable: "Drift vs prior year: -",
      jumpToEvidence: "Jump to evidence",
      openFiling: ({ year }: { year: number | string }) => t("Open SEC filing ({year})", { year }),
    },
  },

  driftTimeline: {
    title: "Narrative drift vs prior year",
    // High-traffic: appears above the fold in the default dashboard layout.
    helper: "Higher means the wording changed more from the previous year. Not a verdict — just where to read.",
    tooltip: {
      title: ({ year }: { year: number | string }) => t("{year}", { year }),
      driftLine: ({ prevYear, drift }: { prevYear: number | string; drift: string }) =>
        t("Drift vs {prevYear}: {drift}", { prevYear, drift }),
      ciLine: ({ low, high }: { low: string; high: string }) => t("CI: {low}–{high}", { low, high }),
      boilerplateLine: ({ boilerplatePct }: { boilerplatePct: string }) => t("Boilerplate: {boilerplatePct}", { boilerplatePct }),
      confidenceLine: ({ confidencePct }: { confidencePct: string }) => t("Extraction confidence: {confidencePct}", { confidencePct }),
    },
  },

  heatmap: {
    title: "Similarity across years",
    // High-traffic line for most flows: small + dry + functional.
    helper: "Darker cells are more similar. Click a cell to compare years. It will not file a 10‑K for you.",
    microcopy: "Click a cell to compare those years.",
    legendMin: ({ value }: { value: string }) => t("Low ({value})", { value }),
    legendMax: ({ value }: { value: string }) => t("High ({value})", { value }),
    selectedLabel: ({
      fromYear,
      toYear,
    }: {
      fromYear: number | string
      toYear: number | string
    }) => t("Selected: {fromYear} vs {toYear}", { fromYear, toYear }),
    clickHint: ({
      fromYear,
      toYear,
    }: {
      fromYear: number | string
      toYear: number | string
    }) => t("Click to compare {fromYear} vs {toYear}", { fromYear, toYear }),
    ariaLabel: ({
      fromYear,
      toYear,
      value,
    }: {
      fromYear: number | string
      toYear: number | string
      value: string
    }) => t("Compare {fromYear} vs {toYear}. Similarity {value}.", {
      fromYear,
      toYear,
      value,
    }),
    naLabel: "not available",
    hoverTitle: ({ fromYear, toYear }: { fromYear: number | string; toYear: number | string }) =>
      t("{fromYear} ↔ {toYear}", { fromYear, toYear }),
    cosineLine: ({ value }: { value: string }) => t("Cosine similarity: {value}", { value }),
    driftLine: ({ drift }: { drift: string }) => t("Drift: {drift}", { drift }),
  },

  termShifts: {
    title: "Distinctive terms (log-odds)",
    helper:
      "Words and phrases that shifted the most between years (descriptive, not causal). Click a term to highlight it below.",
    risersLabel: "More emphasized",
    fallersLabel: "Less emphasized",
    scoreTooltip:
      "Smoothed log-odds shift. Higher magnitude = larger relative change. Some datasets also include an approximate z-score and per-10k frequency deltas.",
    lensLabel: "Phrase lens",
    lensPrimary: "PMI phrases",
    lensAlt: "TextRank keyphrases",
    lensPrimaryHelp:
      "PMI bigrams + a small curated phrase list. Tends to be more stable and auditable.",
    lensAltHelp:
      "TextRank-style keyphrases derived from each year's text. Can surface more \"topic-like\" phrases, but may be noisier.",
    distinctiveBadge: "Notable",
    distinctiveTooltip:
      "Heuristic: this term's shift looks less likely to be a tokenization artifact (uses z-score + frequency filters when available).",
  },

  terms: {
    header: "Distinctive terms (log-odds)",
    subnote:
      "Grouped by canonical term to reduce duplicate variants (e.g., \"covid\", \"covid-19\", \"coronavirus\").",
    includesLabel: "Includes",
    includesTooltipTitle: "Includes variants found in this year-pair",
    includesTooltipCountsNote:
      "Counts shown use the canonical group (not each variant separately).",
    includesTooltipTip: "Tip: open Evidence to see each variant in context.",
    whyGroupTitle: "Why group terms?",
    whyGroupBody1:
      "Risk factors reuse boilerplate and vary in phrasing. Grouping collapses obvious lexical variants so lists stay readable.",
    whyGroupBody2: "We avoid broad semantic merges unless explicitly mapped.",
    dryAside: "Boilerplate is a renewable resource.",
  },

  comparePane: {
    title: "Read the evidence",
    helper: "Representative paragraphs for the selected year pair. The receipts — curated, not comprehensive.",
    pairLabel: "Comparing",
    loading: "Loading excerpts...",
    highlightLabel: "Highlight",
    highlightOptions: {
      topShifts: "Top shifts",
      selectedTerm: "Selected term",
      none: "None",
    },
    viewOnSec: "View filing on SEC",
    emptyNoPair: "Select a year pair from the heatmap to compare.",
    warnLowConfidence: "This excerpt set includes at least one low-confidence extraction year.",
  },

  methodology: {
    pageTitle: "Methodology",
    headings: {
      whatMeasures: "What this measures",
      whatNot: "What it does not measure",
      extraction: "How extraction works (high level)",
      drift: "How drift is computed (high level)",
      sanityCheck: "How to sanity‑check a spike",
      relatedWork: "Related work (and how this differs)",
      securityPrivacy: "Security & privacy",
      credits: "Credits",
    },
    paragraphs: {
      whatMeasures:
        "We compare the text of Item 1A across years and compute how similar each year is to the previous year. A large change suggests the risk narrative was rewritten or restructured.",
      whatNot:
        "A drift spike is not proof of a real-world event. It’s a prompt to read the filing and form hypotheses. Treat this as descriptive analysis, not causality.",
      extraction:
        "We download the filing HTML, isolate Item 1A using section heuristics, and split the result into paragraphs. We record an extraction confidence score for each year.",
      secAccess:
        "Always include a descriptive User-Agent with contact info and respect SEC fair-access limits (<= 10 requests/sec).",
      drift:
        "We vectorize text and compute cosine similarity across years. Drift is defined as 1 − similarity. Term shifts are computed as a smoothed log‑odds difference.",
      sanityCheck:
        "Click the spike year → click the heatmap cell → skim term shifts → read the highlighted paragraphs → open the SEC link if anything looks off.",
      relatedWorkLead:
        "There are plenty of ways to download and extract SEC sections. This project's obsession is narrower: turn those sections into an auditable, evidence-first \"what changed?\" reading workflow - with uncertainty, quality flags, and direct links back to the filing.",
      relatedWorkDisclaimer:
        "We're not affiliated with the tools below. They're good references; this is a different product decision.",
      securityPrivacy:
        "No login, no user accounts, and no server-side tracking. SEC text is treated as untrusted and rendered as plain text with highlights. Notes (if used) are stored locally in your browser (localStorage) and never uploaded. Security headers like CSP and frame-ancestors are set.",
      credits:
        "See docs for research, attributions, and inspirations.",
    },
    relatedWork: {
      // Keep this list short: it's a credibility stamp, not an academic appendix.
      items: [
        {
          label: "EDGAR-CRAWLER (WWW 2025): download + structured JSON extraction",
          href: "https://github.com/lefterisloukas/edgar-crawler",
          note: "Great for building corpora. SEC Narrative Drift starts after extraction: change metrics + evidence UX.",
        },
        {
          label: "itemseg: 10-K item segmentation tool (incl. LLM/PLM approaches)",
          href: "https://pypi.org/project/itemseg/",
          note: "A stronger segmenter can be swapped into the pipeline. Our UI/metrics don't depend on any one parser.",
        },
        {
          label: "Harvard Forum (2024): boilerplate & \"stickiness\" definitions for risk factors",
          href: "https://corpgov.law.harvard.edu/2024/03/26/covid-19-risk-factors-and-boilerplate-disclosure/",
          note: "Frames why drift is useful: it helps locate where disclosures did (or didn't) update with circumstances.",
        },
        {
          label: "Dyer et al. (JAE 2017): disclosure growth, boilerplate, and stickiness trends",
          href: "https://msbfile03.usc.edu/digitalmeasures/sticelaw/intellcont/Dyer%20et%20al.%202017-1.pdf",
          note: "A classic reference for how risk-factor text expands and repeats over time - and why measuring change is non-trivial.",
        },
        {
          label: "Nature HSSC (2024): risk disclosures become more specific (less boilerplate) during crises",
          href: "https://www.nature.com/articles/s41599-024-04169-w",
          note: "Empirical support for what you often see visually: crisis years produce genuinely different risk language.",
        },
      ],
    },
  },

  dataQuality: {
    title: "Data quality",
    helper:
      "Extraction confidence reflects how reliably we isolated Item 1A in the filing HTML. Low confidence years are where HTML and reality briefly disagree.",
    badges: {
      high: "High confidence",
      medium: "Medium confidence",
      low: "Low confidence",
      skipped: "Skipped (no reliable extract)",
    },
    guidance:
      "If confidence is low, drift may reflect parsing noise. Use the “View on SEC” link to verify boundaries.",
  },
  sectionCapture: {
    label: "Section capture",
    tooltipTitle: "Section capture confidence",
    levels: {
      high: "Clean boundaries. The section start/end markers look like the real Item 1A.",
      medium:
        "Probably right, but the filing structure is quirky. Use the evidence panel to sanity-check.",
      low: "This might be a TOC or cross-reference. Treat highlights as a starting point, not a verdict.",
    },
    footer: "If anything looks odd, open the filing on EDGAR.",
    dryLine: "Some filings are well-structured. Others are enthusiastic.",
  },

  tour: {
    steps: {
      drift: "Start here: spikes show years where wording changed most vs the prior year.",
      heatmap: "Click any cell to pick two years to compare.",
      shifts: "These are the biggest movers for that year pair. Click one to highlight it.",
      compare: "Read the paragraphs side‑by‑side. This is why drift is auditable.",
    },
  },

  export: {
    title: "SEC Narrative Drift — Exec Brief",
    subtitleLine: ({ company, ticker }: { company: string; ticker: string }) => t("{company} ({ticker})", { company, ticker }),
    coverageLine: ({ startYear, endYear }: { startYear: number | string; endYear: number | string }) =>
      t("Coverage: {startYear}–{endYear}", { startYear, endYear }),
    driftLine: ({ drift }: { drift: string }) => t("Drift: {drift}", { drift }),
    driftLineWithCi: ({ drift, low, high }: { drift: string; low: string; high: string }) =>
      t("Drift: {drift} (95% CI {low}-{high})", { drift, low, high }),
    keyChangesTitle: "Key changes",
    qualityLabel: "Data quality",
    sparklineLabel: "Drift trend",
    bullets: {
      largestDrift: ({ year, prev }: { year: number | string; prev: number | string }) =>
        t("Largest drift year: {year} (vs {prev})", { year, prev }),
      mostStable: ({ year }: { year: number | string }) => t("Most stable year: {year}", { year }),
      topRisers: ({ t1, t2, t3 }: { t1: string; t2: string; t3: string }) => t("Top risers: {t1}, {t2}, {t3}", { t1, t2, t3 }),
      topFallers: ({ t1, t2, t3 }: { t1: string; t2: string; t3: string }) =>
        t("Top fallers: {t1}, {t2}, {t3}", { t1, t2, t3 }),
    },
    footer: ({ lastUpdatedUtc }: { lastUpdatedUtc: string }) =>
      t("Source: SEC EDGAR | Item 1A (10‑K) or Item 3.D (20-F) | Generated: {lastUpdatedUtc}", { lastUpdatedUtc }),
  },
} as const;
