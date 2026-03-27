import { useEffect, useMemo, useRef, useState } from "react"
import AgreementMatrix from "./AgreementMatrix"
import CleaningLensToggle from "./CleaningLensToggle"
import MethodCard from "./MethodCard"
import InsightLensPanel from "./InsightLensPanel"
import OutlineComparePanel from "./OutlineComparePanel"
import ProtocolLabPilotMatrixPanel from "./ProtocolLabPilotMatrixPanel"
import RiskNarrativeSummary from "./RiskNarrativeSummary"
import VisibleCaseAnswerSummary from "./VisibleCaseAnswerSummary"
import {
  LabDataLoadError,
  buildExpectedLabOutputArtifact,
  buildLabOutputRepoPath,
  buildLabOutputRequestUrl,
  clearLabOutputCache,
  findLabOutlineCompareArtifactForCampaign,
  findLabOutlineCompareStructuredArtifactForCampaign,
  findLabOutlineCompareInsightArtifactForCampaign,
  formatLabLoadDebug,
  getDefaultDeterministicTrackSlug,
  getDefaultLabLlmCampaignPair,
  loadLabOutlineCompareOutput,
  loadLabOutlineCompareStructuredOutput,
  loadLabOutlineCompareInsightOutput,
  loadLabMethodProfilesIndex,
  listLabCasesForTicker,
  loadLabLlmCampaignsIndex,
  loadLabOutput,
  resolveLabOutputLink,
} from "../lib/labData"
import { formatFiscalYearRange } from "../lib/fiscalYear"
import {
  formatProtocolLabMatrixLoadDebug,
  loadEffortRobustnessCaseForTicker,
  loadEffortRobustnessSummary,
  loadNoveltyLedgerCaseForTicker,
  loadPilotMatrixBundleForCase,
  loadPilotMatrixBundleForTicker,
  loadSkepticCaseForTicker,
} from "../lib/protocolLabMatrixData.ts"
import type {
  LabCase,
  LabCleaningLens,
  LabLlmCampaign,
  LabMethodProfile,
  LabOutlineCompareOutput,
  LabOutlineCompareV2Output,
  LabOutlineCompareInsightOutput,
  LabOutput,
  LabSourceId,
} from "../lib/labTypes"
import type {
  ProtocolLabEffortRobustnessBundle,
  ProtocolLabNoveltyLedgerCase,
  ProtocolLabPilotMatrixBundle,
  ProtocolLabSkepticCaseCanonizedMatrix,
} from "../lib/protocolLabMatrixTypes.ts"

const DETECTOR_CATALOG = [
  {
    id: "det_logodds_terms_v1",
    label: "What language moved most?",
    technicalLabel: "Log-odds terms",
    description: "Ranks the specific risk terms that rose or fell most between filing years.",
    group: "core",
    defaultSelected: true,
  },
  {
    id: "det_jsd_ngrams_v1",
    label: "How much did the distribution shift?",
    technicalLabel: "JSD n-grams",
    description: "Measures how far the overall Item 1A language distribution moved year over year.",
    group: "core",
    defaultSelected: true,
  },
  {
    id: "det_minhash_boilerplate_v1",
    label: "How much language was reused?",
    technicalLabel: "Minhash boilerplate",
    description: "Estimates how much of the risk section still behaves like recycled boilerplate.",
    group: "structure",
    defaultSelected: false,
  },
  {
    id: "det_winnowing_fingerprint_v1",
    label: "Which exact spans carried over?",
    technicalLabel: "Winnowing fingerprints",
    description: "Surfaces exact reused spans so continuity is visible instead of inferred.",
    group: "structure",
    defaultSelected: false,
  },
  {
    id: "det_structure_artifacts_v1",
    label: "Where did the structure change?",
    technicalLabel: "Structure artifacts",
    description: "Highlights heading moves and section-shape changes that alter how the filing is organized.",
    group: "structure",
    defaultSelected: false,
  },
]

const DEFAULT_SELECTED = DETECTOR_CATALOG.filter((det) => det.defaultSelected).map(
  (det) => det.id
)
const EXECUTIVE_READ_PRESET = ["det_logodds_terms_v1", "det_jsd_ngrams_v1"]
const TECHNICAL_DEEP_DIVE_PRESET = [
  "det_logodds_terms_v1",
  "det_jsd_ngrams_v1",
  "det_minhash_boilerplate_v1",
  "det_winnowing_fingerprint_v1",
  "det_structure_artifacts_v1",
]
const DETECTOR_GROUP_ORDER = [
  { id: "core", label: "What changed most" },
  { id: "structure", label: "Structure and reuse" },
] as const
const METHOD_GROUP_SECTION_IDS: Record<(typeof DETECTOR_GROUP_ORDER)[number]["id"], string> = {
  core: "lab-core-methods",
  structure: "lab-structure-methods",
}
const LENS_PREFERENCE_ORDER: LabCleaningLens[] = [
  "deboilerplated",
  "raw",
  "stage1_clean",
  "structure_aware",
]
const DET_TRACK_SLUG = getDefaultDeterministicTrackSlug()
type AnalysisMode = "executive" | "deep"

type PilotMatrixTarget =
  | {
      mode: "case"
      ticker: string
      yearFrom: number
      yearTo: number
    }
  | {
      mode: "ticker"
      ticker: string
    }

function buildDetectorCardKey(detectorId: string, campaignId?: string): string {
  if (campaignId) return `${detectorId}::${campaignId}`
  return detectorId
}

function buildCardExpansionKey(scopeKey: string, cardKey: string): string {
  return `${scopeKey}::${cardKey}`
}

function buildCaseKey(caseItem: LabCase): string {
  return `${caseItem.year_from}-${caseItem.year_to}`
}

function findCaseKeyByPair(cases: LabCase[], pair: { from: number; to: number }): string | null {
  const match = cases.find(
    (entry) => entry.year_from === pair.from && entry.year_to === pair.to
  )
  return match ? buildCaseKey(match) : null
}

function normalizeLens(value: LabCleaningLens | string): LabCleaningLens {
  if (value === "deboilerplated" || value === "stage1_clean" || value === "structure_aware") {
    return value
  }
  return "raw"
}

function extractAvailableLenses(caseItem: LabCase, sourceId: LabSourceId): LabCleaningLens[] {
  const lenses: LabCleaningLens[] = []
  for (const output of caseItem.outputs ?? []) {
    if (output.source_id !== sourceId) continue
    const lens = normalizeLens(output.cleaning_lens)
    if (!lenses.includes(lens)) {
      lenses.push(lens)
    }
  }
  return lenses
}

function extractAvailableDetectors(
  caseItem: LabCase,
  sourceId: LabSourceId,
  lens: LabCleaningLens
): string[] {
  const detectors: string[] = []
  for (const output of caseItem.outputs ?? []) {
    if (output.source_id !== sourceId) continue
    if (normalizeLens(output.cleaning_lens) !== lens) continue
    if (!detectors.includes(output.detector_id)) {
      detectors.push(output.detector_id)
    }
  }
  return detectors
}

function pickPreferredAvailableLens(availableLenses: LabCleaningLens[]): LabCleaningLens | null {
  for (const preferred of LENS_PREFERENCE_ORDER) {
    if (availableLenses.includes(preferred)) {
      return preferred
    }
  }
  if (availableLenses.length > 0) {
    return availableLenses[0]
  }
  return null
}

type DetectorDebugInfo = {
  ticker: string
  yearFrom: number
  yearTo: number
  lens: LabCleaningLens
  detectorId: string
  campaignId?: string | null
  campaignDisplayName?: string | null
  expectedPath: string | null
  requestedUrl: string | null
  inputFile?: string | null
  yearInputPrev?: string | null
  yearInputCurr?: string | null
  inputFileUrl?: string | null
  yearInputPrevUrl?: string | null
  yearInputCurrUrl?: string | null
  errorText: string | null
}

type OutlineArtifactDebugInfo = {
  expectedPath: string | null
  requestedUrl: string | null
  errorText: string | null
}

async function copyTextToClipboard(text: string): Promise<boolean> {
  if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // fall through to fallback path
    }
  }
  if (typeof document === "undefined") {
    return false
  }
  const textarea = document.createElement("textarea")
  textarea.value = text
  textarea.setAttribute("readonly", "true")
  textarea.className = "clipboard-staging-textarea"
  document.body.appendChild(textarea)
  textarea.select()
  const copied = document.execCommand("copy")
  document.body.removeChild(textarea)
  return copied
}

type LabPanelProps = {
  ticker: string
  requestedPair?: { from: number; to: number } | null
  onSelectedPairChange?: (pair: { from: number; to: number }) => void
  requestedLlmCampaignA?: string | null
  requestedLlmCampaignB?: string | null
  onSelectedLlmCampaignsChange?: (selection: { llmA: string; llmB: string }) => void
}

export default function LabPanel({
  ticker,
  requestedPair = null,
  onSelectedPairChange,
  requestedLlmCampaignA = null,
  requestedLlmCampaignB = null,
  onSelectedLlmCampaignsChange,
}: LabPanelProps) {
  const syncedPairKeyRef = useRef<string | null>(null)
  const [cases, setCases] = useState<LabCase[]>([])
  const [isLoadingCases, setIsLoadingCases] = useState(true)
  const [caseError, setCaseError] = useState<string | null>(null)
  const [caseDebugPath, setCaseDebugPath] = useState<string | null>(null)
  const [selectedCaseKey, setSelectedCaseKey] = useState<string | null>(null)
  const [prevRequestedCaseKey, setPrevRequestedCaseKey] = useState<string | null>(null)
  const [lens, setLens] = useState<LabCleaningLens>("deboilerplated")
  const [selectedDetectors, setSelectedDetectors] = useState<string[]>(DEFAULT_SELECTED)
  const [outputs, setOutputs] = useState<Record<string, LabOutput | null>>({})
  const [outputDebugPaths, setOutputDebugPaths] = useState<Record<string, string | null>>({})
  const [outputDebugInfo, setOutputDebugInfo] = useState<Record<string, DetectorDebugInfo>>({})
  const [agreementOutput, setAgreementOutput] = useState<LabOutput | null>(null)
  const [agreementDebugPath, setAgreementDebugPath] = useState<string | null>(null)
  const [agreementDebugInfo, setAgreementDebugInfo] = useState<DetectorDebugInfo | null>(null)
  const [agreementCopyState, setAgreementCopyState] = useState<"idle" | "copied" | "failed">(
    "idle"
  )
  const [isLoadingOutputs, setIsLoadingOutputs] = useState(false)
  const [outlineOutputs, setOutlineOutputs] = useState<Record<string, LabOutlineCompareOutput | null>>(
    {}
  )
  const [outlineDebugPaths, setOutlineDebugPaths] = useState<Record<string, string | null>>({})
  const [outlineDebugInfo, setOutlineDebugInfo] = useState<Record<string, OutlineArtifactDebugInfo>>(
    {}
  )
  const [structuredOutlineOutputs, setStructuredOutlineOutputs] = useState<
    Record<string, LabOutlineCompareV2Output | null>
  >({})
  const [structuredOutlineDebugPaths, setStructuredOutlineDebugPaths] = useState<
    Record<string, string | null>
  >({})
  const [structuredOutlineDebugInfo, setStructuredOutlineDebugInfo] = useState<
    Record<string, OutlineArtifactDebugInfo>
  >({})
  const [insightOutputs, setInsightOutputs] = useState<Record<string, LabOutlineCompareInsightOutput | null>>(
    {}
  )
  const [insightDebugPaths, setInsightDebugPaths] = useState<Record<string, string | null>>({})
  const [insightDebugInfo, setInsightDebugInfo] = useState<Record<string, OutlineArtifactDebugInfo>>(
    {}
  )
  const [reloadNonce, setReloadNonce] = useState(0)
  const [llmCampaignOptions, setLlmCampaignOptions] = useState<LabLlmCampaign[]>([])
  const [selectedLlmCampaignA, setSelectedLlmCampaignA] = useState<string>("")
  const [selectedLlmCampaignB, setSelectedLlmCampaignB] = useState<string>("")
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>("executive")
  const [presetStatus, setPresetStatus] = useState<{ message: string; token: number } | null>(
    null
  )
  const [expandedCards, setExpandedCards] = useState<Record<string, boolean>>({})
  const [methodProfilesByDetector, setMethodProfilesByDetector] = useState<
    Record<string, LabMethodProfile>
  >({})
  const [pilotMatrixBundle, setPilotMatrixBundle] = useState<ProtocolLabPilotMatrixBundle | null>(
    null
  )
  const [isLoadingPilotMatrix, setIsLoadingPilotMatrix] = useState(false)
  const [pilotMatrixError, setPilotMatrixError] = useState<string | null>(null)
  const [pilotMatrixDebugText, setPilotMatrixDebugText] = useState<string | null>(null)
  const [effortRobustnessBundle, setEffortRobustnessBundle] =
    useState<ProtocolLabEffortRobustnessBundle | null>(null)
  const [isLoadingEffortRobustness, setIsLoadingEffortRobustness] = useState(false)
  const [effortRobustnessError, setEffortRobustnessError] = useState<string | null>(null)
  const [effortRobustnessDebugText, setEffortRobustnessDebugText] = useState<string | null>(null)
  const [noveltyLedgerArtifact, setNoveltyLedgerArtifact] =
    useState<ProtocolLabNoveltyLedgerCase | null>(null)
  const [isLoadingNoveltyLedger, setIsLoadingNoveltyLedger] = useState(false)
  const [noveltyLedgerError, setNoveltyLedgerError] = useState<string | null>(null)
  const [noveltyLedgerDebugText, setNoveltyLedgerDebugText] = useState<string | null>(null)
  const [skepticCaseArtifact, setSkepticCaseArtifact] =
    useState<ProtocolLabSkepticCaseCanonizedMatrix | null>(null)
  const [isLoadingSkepticCase, setIsLoadingSkepticCase] = useState(false)
  const [skepticCaseError, setSkepticCaseError] = useState<string | null>(null)
  const [skepticCaseDebugText, setSkepticCaseDebugText] = useState<string | null>(null)

  // Track previous values for render-time state adjustments (React recommended pattern)
  const [prevTicker, setPrevTicker] = useState(ticker)

  const sourceId: LabSourceId = "edgar"

  // Adjust state during render when ticker changes to avoid sync setState in effect
  if (prevTicker !== ticker) {
    setPrevTicker(ticker)
    setIsLoadingCases(true)
    setCaseError(null)
    setCaseDebugPath(null)
    setCases([])
    setSelectedCaseKey(null)
    setExpandedCards({})
    setLens("deboilerplated")
    setSelectedDetectors(DEFAULT_SELECTED)
    setAnalysisMode("executive")
    setPilotMatrixBundle(null)
    setIsLoadingPilotMatrix(false)
    setPilotMatrixError(null)
    setPilotMatrixDebugText(null)
    setEffortRobustnessBundle(null)
    setIsLoadingEffortRobustness(false)
    setEffortRobustnessError(null)
    setEffortRobustnessDebugText(null)
    setNoveltyLedgerArtifact(null)
    setIsLoadingNoveltyLedger(false)
    setNoveltyLedgerError(null)
    setNoveltyLedgerDebugText(null)
    setSkepticCaseArtifact(null)
    setIsLoadingSkepticCase(false)
    setSkepticCaseError(null)
    setSkepticCaseDebugText(null)
  }

  useEffect(() => {
    let cancelled = false

    listLabCasesForTicker(ticker)
      .then((result) => {
        if (cancelled) return
        setCases(result)
        const recommended = result.find((item) => item.tags?.includes("recommended"))
        const initial = recommended ?? result[0]
        setSelectedCaseKey(initial ? buildCaseKey(initial) : null)
      })
      .catch((error) => {
        if (cancelled) return
        setCaseError(error instanceof Error ? error.message : "Failed to load lab cases.")
        setCaseDebugPath(formatLabLoadDebug(error))
      })
      .finally(() => {
        if (!cancelled) setIsLoadingCases(false)
      })

    return () => {
      cancelled = true
    }
  }, [ticker])

  useEffect(() => {
    let cancelled = false
    loadLabLlmCampaignsIndex()
      .then(async (index) => {
        if (cancelled) return
        const runtimeCampaigns = index.campaigns.filter(
          (campaign) =>
            campaign.runtime_visible !== false && campaign.input_mode !== "focuspack_v1"
        )
        const options = runtimeCampaigns.length > 0 ? runtimeCampaigns : index.campaigns
        setLlmCampaignOptions(options)
        const defaults = await getDefaultLabLlmCampaignPair()
        if (cancelled) return

        const available = new Set(options.map((campaign) => campaign.campaign_id))
        const requestedA =
          requestedLlmCampaignA && available.has(requestedLlmCampaignA)
            ? requestedLlmCampaignA
            : defaults.primaryCampaignId
        const requestedB =
          requestedLlmCampaignB && available.has(requestedLlmCampaignB)
            ? requestedLlmCampaignB
            : defaults.compareCampaignId
        setSelectedLlmCampaignA(requestedA)
        if (options.length <= 1) {
          setSelectedLlmCampaignB(requestedA)
        } else {
          setSelectedLlmCampaignB(requestedB === requestedA ? options[1]?.campaign_id ?? requestedA : requestedB)
        }
      })
      .catch(() => {
        if (cancelled) return
        setLlmCampaignOptions([])
      })
    return () => {
      cancelled = true
    }
  }, [requestedLlmCampaignA, requestedLlmCampaignB])

  useEffect(() => {
    let cancelled = false
    loadLabMethodProfilesIndex()
      .then((index) => {
        if (cancelled) return
        const next: Record<string, LabMethodProfile> = {}
        for (const profile of index.profiles) {
          next[profile.detector_id] = profile
        }
        setMethodProfilesByDetector(next)
      })
      .catch(() => {
        if (cancelled) return
        setMethodProfilesByDetector({})
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!onSelectedLlmCampaignsChange) return
    if (!selectedLlmCampaignA || !selectedLlmCampaignB) return
    onSelectedLlmCampaignsChange({
      llmA: selectedLlmCampaignA,
      llmB: selectedLlmCampaignB,
    })
  }, [onSelectedLlmCampaignsChange, selectedLlmCampaignA, selectedLlmCampaignB])

  useEffect(() => {
    if (!presetStatus) return
    const timeoutId = window.setTimeout(() => {
      setPresetStatus(null)
    }, 2500)
    return () => {
      window.clearTimeout(timeoutId)
    }
  }, [presetStatus])

  const selectedCase = useMemo(() => {
    if (!selectedCaseKey) return null
    return cases.find((item) => buildCaseKey(item) === selectedCaseKey) ?? null
  }, [cases, selectedCaseKey])

  const pilotMatrixTarget = useMemo<PilotMatrixTarget | null>(() => {
    if (
      selectedCase &&
      (selectedCase.ticker === "NVDA" || selectedCase.ticker === "KO") &&
      selectedCase.year_from === 2024 &&
      selectedCase.year_to === 2025
    ) {
      return {
        mode: "case",
        ticker: selectedCase.ticker,
        yearFrom: selectedCase.year_from,
        yearTo: selectedCase.year_to,
      }
    }
    if (!selectedCase && ticker === "LLY") {
      return {
        mode: "ticker",
        ticker,
      }
    }
    return null
  }, [selectedCase, ticker])

  const isPilotMatrixSelectedCase = pilotMatrixTarget?.mode === "case"
  const isPilotOnlyMatrixView = pilotMatrixTarget?.mode === "ticker"

  const pilotMatrixRequestKey = useMemo(() => {
    if (!pilotMatrixTarget) return null
    if (pilotMatrixTarget.mode === "case") {
      return `${pilotMatrixTarget.ticker}:${pilotMatrixTarget.yearFrom}-${pilotMatrixTarget.yearTo}`
    }
    return `${pilotMatrixTarget.ticker}:pilot_only`
  }, [pilotMatrixTarget])
  const [prevPilotMatrixRequestKey, setPrevPilotMatrixRequestKey] = useState(pilotMatrixRequestKey)

  if (prevPilotMatrixRequestKey !== pilotMatrixRequestKey) {
    setPrevPilotMatrixRequestKey(pilotMatrixRequestKey)
    if (!pilotMatrixRequestKey) {
      setPilotMatrixBundle(null)
      setIsLoadingPilotMatrix(false)
      setPilotMatrixError(null)
      setPilotMatrixDebugText(null)
      setEffortRobustnessBundle(null)
      setIsLoadingEffortRobustness(false)
      setEffortRobustnessError(null)
      setEffortRobustnessDebugText(null)
      setNoveltyLedgerArtifact(null)
      setIsLoadingNoveltyLedger(false)
      setNoveltyLedgerError(null)
      setNoveltyLedgerDebugText(null)
      setSkepticCaseArtifact(null)
      setIsLoadingSkepticCase(false)
      setSkepticCaseError(null)
      setSkepticCaseDebugText(null)
    } else {
      setIsLoadingPilotMatrix(true)
      setPilotMatrixError(null)
      setPilotMatrixDebugText(null)
      setIsLoadingEffortRobustness(true)
      setEffortRobustnessError(null)
      setEffortRobustnessDebugText(null)
      setIsLoadingNoveltyLedger(true)
      setNoveltyLedgerError(null)
      setNoveltyLedgerDebugText(null)
      setIsLoadingSkepticCase(true)
      setSkepticCaseError(null)
      setSkepticCaseDebugText(null)
    }
  }

  useEffect(() => {
    if (!pilotMatrixTarget) {
      return
    }

    let cancelled = false
    const controller = new AbortController()

    const loadPromise =
      pilotMatrixTarget.mode === "case"
        ? loadPilotMatrixBundleForCase({
            ticker: pilotMatrixTarget.ticker,
            yearFrom: pilotMatrixTarget.yearFrom,
            yearTo: pilotMatrixTarget.yearTo,
            signal: controller.signal,
          })
        : loadPilotMatrixBundleForTicker({
            ticker: pilotMatrixTarget.ticker,
            signal: controller.signal,
          })

    loadPromise
      .then((bundle) => {
        if (cancelled) return
        if (!bundle) {
          setPilotMatrixBundle(null)
          setPilotMatrixError("Integrated case-comparison registry entry is not available for this view.")
          setPilotMatrixDebugText(null)
          return
        }
        setPilotMatrixBundle(bundle)
        setPilotMatrixError(null)
        setPilotMatrixDebugText(null)
      })
      .catch((error) => {
        if (cancelled) return
        setPilotMatrixBundle(null)
        setPilotMatrixError(
          error instanceof Error ? error.message : "Failed to load integrated case comparison."
        )
        setPilotMatrixDebugText(formatProtocolLabMatrixLoadDebug(error))
      })
      .finally(() => {
        if (!cancelled) setIsLoadingPilotMatrix(false)
      })

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [pilotMatrixTarget])

  useEffect(() => {
    if (!pilotMatrixTarget) {
      return
    }

    let cancelled = false
    const controller = new AbortController()

    loadSkepticCaseForTicker({
      ticker: pilotMatrixTarget.ticker,
      signal: controller.signal,
    })
      .then((artifact) => {
        if (cancelled) return
        if (!artifact) {
          setSkepticCaseArtifact(null)
          setSkepticCaseError("Restraint-case artifact is not available for this bounded case view.")
          setSkepticCaseDebugText(null)
          return
        }
        setSkepticCaseArtifact(artifact)
        setSkepticCaseError(null)
        setSkepticCaseDebugText(null)
      })
      .catch((error) => {
        if (cancelled) return
        setSkepticCaseArtifact(null)
        setSkepticCaseError(
          error instanceof Error ? error.message : "Failed to load restraint-case artifact."
        )
        setSkepticCaseDebugText(formatProtocolLabMatrixLoadDebug(error))
      })
      .finally(() => {
        if (!cancelled) setIsLoadingSkepticCase(false)
      })

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [pilotMatrixTarget])

  useEffect(() => {
    if (!pilotMatrixTarget) {
      return
    }

    let cancelled = false
    const controller = new AbortController()

    loadNoveltyLedgerCaseForTicker({
      ticker: pilotMatrixTarget.ticker,
      signal: controller.signal,
    })
      .then((artifact) => {
        if (cancelled) return
        if (!artifact) {
          setNoveltyLedgerArtifact(null)
          setNoveltyLedgerError("Fresh-vs-reused artifact is not available for this bounded case view.")
          setNoveltyLedgerDebugText(null)
          return
        }
        setNoveltyLedgerArtifact(artifact)
        setNoveltyLedgerError(null)
        setNoveltyLedgerDebugText(null)
      })
      .catch((error) => {
        if (cancelled) return
        setNoveltyLedgerArtifact(null)
        setNoveltyLedgerError(
          error instanceof Error ? error.message : "Failed to load novelty ledger."
        )
        setNoveltyLedgerDebugText(formatProtocolLabMatrixLoadDebug(error))
      })
      .finally(() => {
        if (!cancelled) setIsLoadingNoveltyLedger(false)
      })

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [pilotMatrixTarget])

  useEffect(() => {
    if (!pilotMatrixTarget) {
      return
    }

    let cancelled = false

    Promise.allSettled([
      loadEffortRobustnessCaseForTicker({
        ticker: pilotMatrixTarget.ticker,
      }),
      loadEffortRobustnessSummary(),
    ])
      .then(([caseResult, summaryResult]) => {
        if (cancelled) return

        if (caseResult.status === "rejected") {
          setEffortRobustnessBundle(null)
          setEffortRobustnessError(
            caseResult.reason instanceof Error
              ? caseResult.reason.message
              : "Failed to load effort robustness."
          )
          setEffortRobustnessDebugText(formatProtocolLabMatrixLoadDebug(caseResult.reason))
          return
        }

        if (!caseResult.value) {
          setEffortRobustnessBundle(null)
          setEffortRobustnessError("Effort-robustness artifact is not available for this bounded case view.")
          setEffortRobustnessDebugText(null)
          return
        }

        setEffortRobustnessBundle({
          case_artifact: caseResult.value,
          summary_artifact: summaryResult.status === "fulfilled" ? summaryResult.value : null,
        })

        if (summaryResult.status === "rejected") {
          setEffortRobustnessError(
            summaryResult.reason instanceof Error
              ? summaryResult.reason.message
              : "Failed to load effort robustness summary."
          )
          setEffortRobustnessDebugText(formatProtocolLabMatrixLoadDebug(summaryResult.reason))
          return
        }

        setEffortRobustnessError(null)
        setEffortRobustnessDebugText(null)
      })
      .finally(() => {
        if (!cancelled) setIsLoadingEffortRobustness(false)
      })

    return () => {
      cancelled = true
    }
  }, [pilotMatrixTarget])

  const requestedCaseKey = useMemo(() => {
    if (!requestedPair || cases.length === 0) return null
    return findCaseKeyByPair(cases, requestedPair)
  }, [cases, requestedPair])

  if (requestedCaseKey !== prevRequestedCaseKey) {
    setPrevRequestedCaseKey(requestedCaseKey)
    if (requestedCaseKey && requestedCaseKey !== selectedCaseKey) {
      setSelectedCaseKey(requestedCaseKey)
    }
  }

  useEffect(() => {
    if (!selectedCase || !onSelectedPairChange) return
    const pairKey = `${selectedCase.ticker}:${selectedCase.year_from}-${selectedCase.year_to}`
    if (syncedPairKeyRef.current === pairKey) return
    syncedPairKeyRef.current = pairKey
    onSelectedPairChange({ from: selectedCase.year_from, to: selectedCase.year_to })
  }, [onSelectedPairChange, selectedCase])

  const availableLenses = useMemo(() => {
    if (!selectedCase) return []
    const lenses = extractAvailableLenses(selectedCase, sourceId)
    return lenses.length ? lenses : (["raw"] as LabCleaningLens[])
  }, [selectedCase, sourceId])

  const availableDetectorIds = useMemo(() => {
    if (!selectedCase) return []
    return extractAvailableDetectors(selectedCase, sourceId, lens)
  }, [selectedCase, sourceId, lens])
  const availableDetectorSet = useMemo(
    () => new Set<string>(availableDetectorIds),
    [availableDetectorIds]
  )

  // Adjust lens during render when available lenses change (avoids sync setState in effect)
  if (availableLenses.length && !availableLenses.includes(lens)) {
    const nextLens = pickPreferredAvailableLens(availableLenses)
    if (nextLens) {
      setLens(nextLens)
    }
  }

  // Build a key to track when output-loading dependencies change
  const outputRequestKey = selectedCase
    ? `${buildCaseKey(selectedCase)}|${lens}|${selectedDetectors.join(",")}|${selectedLlmCampaignA}|${selectedLlmCampaignB}|reload:${reloadNonce}`
    : null
  const [prevOutputRequestKey, setPrevOutputRequestKey] = useState(outputRequestKey)

  // Adjust outputs state during render when dependencies change (avoids sync setState in effect)
  if (prevOutputRequestKey !== outputRequestKey) {
    setPrevOutputRequestKey(outputRequestKey)
    if (!outputRequestKey) {
      setOutputs({})
      setOutputDebugPaths({})
      setOutputDebugInfo({})
      setOutlineOutputs({})
      setOutlineDebugPaths({})
      setOutlineDebugInfo({})
      setStructuredOutlineOutputs({})
      setStructuredOutlineDebugPaths({})
      setStructuredOutlineDebugInfo({})
      setInsightOutputs({})
      setInsightDebugPaths({})
      setInsightDebugInfo({})
      setAgreementOutput(null)
      setAgreementDebugPath(null)
      setAgreementDebugInfo(null)
      setAgreementCopyState("idle")
      setIsLoadingOutputs(false)
    } else {
      setIsLoadingOutputs(true)
    }
  }

  useEffect(() => {
    if (!selectedCase) {
      return
    }

    let cancelled = false
    const controller = new AbortController()

    const load = async () => {
      const nextOutputs: Record<string, LabOutput | null> = {}
      const nextOutputDebugPaths: Record<string, string | null> = {}
      const nextOutputDebugInfo: Record<string, DetectorDebugInfo> = {}
      const nextOutlineOutputs: Record<string, LabOutlineCompareOutput | null> = {}
      const nextOutlineDebugPaths: Record<string, string | null> = {}
      const nextOutlineDebugInfo: Record<string, OutlineArtifactDebugInfo> = {}
      const nextStructuredOutlineOutputs: Record<string, LabOutlineCompareV2Output | null> = {}
      const nextStructuredOutlineDebugPaths: Record<string, string | null> = {}
      const nextStructuredOutlineDebugInfo: Record<string, OutlineArtifactDebugInfo> = {}
      const nextInsightOutputs: Record<string, LabOutlineCompareInsightOutput | null> = {}
      const nextInsightDebugPaths: Record<string, string | null> = {}
      const nextInsightDebugInfo: Record<string, OutlineArtifactDebugInfo> = {}

      for (const detectorId of selectedDetectors) {
        {
          const expectedArtifact = buildExpectedLabOutputArtifact(
            selectedCase,
            detectorId,
            lens,
            sourceId,
            DET_TRACK_SLUG
          )
          const link = resolveLabOutputLink(selectedCase, detectorId, lens, sourceId)
          const fallbackExpectedPath = expectedArtifact?.repoPath ?? null
          const fallbackRequestedUrl = expectedArtifact?.requestUrl ?? null
          let requestedUrl = fallbackRequestedUrl
          let expectedPath = fallbackExpectedPath
          const cardKey = buildDetectorCardKey(detectorId)
          if (!link) {
            nextOutputs[cardKey] = null
            nextOutputDebugPaths[cardKey] = fallbackExpectedPath
              ? `Missing artifact. Expected path: ${fallbackExpectedPath}`
              : "Missing artifact."
            nextOutputDebugInfo[cardKey] = {
              ticker: selectedCase.ticker,
              yearFrom: selectedCase.year_from,
              yearTo: selectedCase.year_to,
              lens,
              detectorId,
              expectedPath: fallbackExpectedPath,
              requestedUrl: fallbackRequestedUrl,
              errorText: "No precomputed output exists for this method and cleaning lens combination.",
            }
            continue
          }
          requestedUrl =
            buildLabOutputRequestUrl(selectedCase.ticker, link.filename) ?? fallbackRequestedUrl
          expectedPath =
            buildLabOutputRepoPath(selectedCase.ticker, link.filename) ?? fallbackExpectedPath
          try {
            const output = await loadLabOutput(selectedCase.ticker, link.filename, {
              signal: controller.signal,
            })
            nextOutputs[cardKey] = output
            nextOutputDebugPaths[cardKey] = null
            nextOutputDebugInfo[cardKey] = {
              ticker: selectedCase.ticker,
              yearFrom: selectedCase.year_from,
              yearTo: selectedCase.year_to,
              lens,
              detectorId,
              expectedPath,
              requestedUrl,
              errorText: null,
            }
          } catch (error) {
            nextOutputs[cardKey] = null
            nextOutputDebugPaths[cardKey] = formatLabLoadDebug(error)
            let errorText = "Failed to load detector output."
            if (error instanceof LabDataLoadError) {
              const statusText = typeof error.status === "number" ? ` (status ${error.status})` : ""
              errorText = `${error.message}${statusText}`
              requestedUrl = error.url
            } else if (error instanceof Error) {
              errorText = error.message
            }
            nextOutputDebugInfo[cardKey] = {
              ticker: selectedCase.ticker,
              yearFrom: selectedCase.year_from,
              yearTo: selectedCase.year_to,
              lens,
              detectorId,
              expectedPath,
              requestedUrl,
              errorText,
            }
          }
        }
      }

      const selectedCampaignIds = Array.from(
        new Set([selectedLlmCampaignA, selectedLlmCampaignB].filter(Boolean))
      )
      for (const campaignId of selectedCampaignIds) {
        const artifact = await findLabOutlineCompareArtifactForCampaign(selectedCase, lens, campaignId)
        if (!artifact) {
          nextOutlineOutputs[campaignId] = null
          nextOutlineDebugPaths[campaignId] = "Missing outline compare artifact metadata."
          nextOutlineDebugInfo[campaignId] = {
            expectedPath: null,
            requestedUrl: null,
            errorText: "Outline artifact metadata is not indexed for this case/lens/campaign.",
          }
          continue
        }
        let requestedUrl = artifact.requestUrl
        try {
          const output = await loadLabOutlineCompareOutput(selectedCase.ticker, artifact.filename, {
            signal: controller.signal,
          })
          nextOutlineOutputs[campaignId] = output
          nextOutlineDebugPaths[campaignId] = null
          nextOutlineDebugInfo[campaignId] = {
            expectedPath: artifact.repoPath,
            requestedUrl,
            errorText: null,
          }
        } catch (error) {
          nextOutlineOutputs[campaignId] = null
          nextOutlineDebugPaths[campaignId] = formatLabLoadDebug(error)
          let errorText = "Failed to load outline compare output."
          if (error instanceof LabDataLoadError) {
            const statusText = typeof error.status === "number" ? ` (status ${error.status})` : ""
            errorText = `${error.message}${statusText}`
            requestedUrl = error.url
          } else if (error instanceof Error) {
            errorText = error.message
          }
          nextOutlineDebugInfo[campaignId] = {
            expectedPath: artifact.repoPath,
            requestedUrl,
            errorText,
          }
        }
      }

      for (const campaignId of selectedCampaignIds) {
        const artifact = await findLabOutlineCompareStructuredArtifactForCampaign(selectedCase, lens, campaignId)
        if (!artifact) {
          nextStructuredOutlineOutputs[campaignId] = null
          nextStructuredOutlineDebugPaths[campaignId] = "Missing structured outline artifact metadata."
          nextStructuredOutlineDebugInfo[campaignId] = {
            expectedPath: null,
            requestedUrl: null,
            errorText: "Structured outline artifact metadata is not indexed for this case/lens/campaign.",
          }
          continue
        }
        let requestedUrl = artifact.requestUrl
        try {
          const output = await loadLabOutlineCompareStructuredOutput(selectedCase.ticker, artifact.filename, {
            signal: controller.signal,
          })
          nextStructuredOutlineOutputs[campaignId] = output
          nextStructuredOutlineDebugPaths[campaignId] = null
          nextStructuredOutlineDebugInfo[campaignId] = {
            expectedPath: artifact.repoPath,
            requestedUrl,
            errorText: null,
          }
        } catch (error) {
          nextStructuredOutlineOutputs[campaignId] = null
          nextStructuredOutlineDebugPaths[campaignId] = formatLabLoadDebug(error)
          let errorText = "Failed to load structured outline output."
          if (error instanceof LabDataLoadError) {
            const statusText = typeof error.status === "number" ? ` (status ${error.status})` : ""
            errorText = `${error.message}${statusText}`
            requestedUrl = error.url
          } else if (error instanceof Error) {
            errorText = error.message
          }
          nextStructuredOutlineDebugInfo[campaignId] = {
            expectedPath: artifact.repoPath,
            requestedUrl,
            errorText,
          }
        }
      }

      for (const campaignId of selectedCampaignIds) {
        const artifact = await findLabOutlineCompareInsightArtifactForCampaign(selectedCase, lens, campaignId)
        if (!artifact) {
          nextInsightOutputs[campaignId] = null
          nextInsightDebugPaths[campaignId] =
            "Optional insight lens sidecar is not published for this compare lane."
          nextInsightDebugInfo[campaignId] = {
            expectedPath: null,
            requestedUrl: null,
            errorText: "Optional insight lens sidecar not available for this case/lens/campaign.",
          }
          continue
        }
        let requestedUrl = artifact.requestUrl
        try {
          const output = await loadLabOutlineCompareInsightOutput(selectedCase.ticker, artifact.filename, {
            signal: controller.signal,
          })
          nextInsightOutputs[campaignId] = output
          nextInsightDebugPaths[campaignId] = null
          nextInsightDebugInfo[campaignId] = {
            expectedPath: artifact.repoPath,
            requestedUrl,
            errorText: null,
          }
        } catch (error) {
          nextInsightOutputs[campaignId] = null
          nextInsightDebugPaths[campaignId] = formatLabLoadDebug(error)
          let errorText = "Failed to load insight lens output."
          if (error instanceof LabDataLoadError) {
            const statusText = typeof error.status === "number" ? ` (status ${error.status})` : ""
            errorText = `${error.message}${statusText}`
            requestedUrl = error.url
          } else if (error instanceof Error) {
            errorText = error.message
          }
          nextInsightDebugInfo[campaignId] = {
            expectedPath: artifact.repoPath,
            requestedUrl,
            errorText,
          }
        }
      }

      const agreementExpectedArtifact = buildExpectedLabOutputArtifact(
        selectedCase,
        "det_rbo_agreement_v1",
        lens,
        sourceId,
        DET_TRACK_SLUG
      )
      const agreementLink = resolveLabOutputLink(
        selectedCase,
        "det_rbo_agreement_v1",
        lens,
        sourceId
      )
      let agreement: LabOutput | null = null
      let nextAgreementDebugPath: string | null = null
      let nextAgreementDebugInfo: DetectorDebugInfo | null = null
      if (agreementLink) {
        const expectedPath =
          buildLabOutputRepoPath(selectedCase.ticker, agreementLink.filename) ??
          agreementExpectedArtifact?.repoPath ??
          null
        let requestedUrl =
          buildLabOutputRequestUrl(selectedCase.ticker, agreementLink.filename) ??
          agreementExpectedArtifact?.requestUrl ??
          null
        try {
          agreement = await loadLabOutput(selectedCase.ticker, agreementLink.filename, {
            signal: controller.signal,
          })
          nextAgreementDebugPath = null
          nextAgreementDebugInfo = {
            ticker: selectedCase.ticker,
            yearFrom: selectedCase.year_from,
            yearTo: selectedCase.year_to,
            lens,
            detectorId: "det_rbo_agreement_v1",
            expectedPath,
            requestedUrl,
            errorText: null,
          }
        } catch (error) {
          agreement = null
          nextAgreementDebugPath = formatLabLoadDebug(error)
          let errorText = "Failed to load agreement output."
          if (error instanceof LabDataLoadError) {
            const statusText = typeof error.status === "number" ? ` (status ${error.status})` : ""
            errorText = `${error.message}${statusText}`
            requestedUrl = error.url
          } else if (error instanceof Error) {
            errorText = error.message
          }
          nextAgreementDebugInfo = {
            ticker: selectedCase.ticker,
            yearFrom: selectedCase.year_from,
            yearTo: selectedCase.year_to,
            lens,
            detectorId: "det_rbo_agreement_v1",
            expectedPath,
            requestedUrl,
            errorText,
          }
        }
      } else {
        agreement = null
        nextAgreementDebugPath = agreementExpectedArtifact?.repoPath
          ? `Missing artifact. Expected path: ${agreementExpectedArtifact.repoPath}`
          : "Missing artifact."
        nextAgreementDebugInfo = {
          ticker: selectedCase.ticker,
          yearFrom: selectedCase.year_from,
          yearTo: selectedCase.year_to,
          lens,
          detectorId: "det_rbo_agreement_v1",
          expectedPath: agreementExpectedArtifact?.repoPath ?? null,
          requestedUrl: agreementExpectedArtifact?.requestUrl ?? null,
          errorText: "Missing artifact: agreement output is not listed for this case/lens.",
        }
      }

      if (!cancelled) {
        setOutputs(nextOutputs)
        setOutputDebugPaths(nextOutputDebugPaths)
        setOutputDebugInfo(nextOutputDebugInfo)
        setOutlineOutputs(nextOutlineOutputs)
        setOutlineDebugPaths(nextOutlineDebugPaths)
        setOutlineDebugInfo(nextOutlineDebugInfo)
        setStructuredOutlineOutputs(nextStructuredOutlineOutputs)
        setStructuredOutlineDebugPaths(nextStructuredOutlineDebugPaths)
        setStructuredOutlineDebugInfo(nextStructuredOutlineDebugInfo)
        setInsightOutputs(nextInsightOutputs)
        setInsightDebugPaths(nextInsightDebugPaths)
        setInsightDebugInfo(nextInsightDebugInfo)
        setAgreementOutput(agreement)
        setAgreementDebugPath(nextAgreementDebugPath)
        setAgreementDebugInfo(nextAgreementDebugInfo)
        setAgreementCopyState("idle")
        setIsLoadingOutputs(false)
      }
    }

    void load()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [
    selectedCase,
    lens,
    selectedDetectors,
    sourceId,
    selectedLlmCampaignA,
    selectedLlmCampaignB,
    reloadNonce,
  ])

  const lensOptions = useMemo(() => {
    const base: LabCleaningLens[] = ["raw", "deboilerplated", "stage1_clean", "structure_aware"]
    return base.map((value) => ({
      value,
      disabled: !availableLenses.includes(value),
    }))
  }, [availableLenses])

  const methodCards = useMemo(() => {
    const selected = new Set(selectedDetectors)
    return DETECTOR_CATALOG.filter((det) => selected.has(det.id)).map((det) => ({
      ...det,
      cardKey: buildDetectorCardKey(det.id),
    }))
  }, [selectedDetectors])

  const expansionScopeKey = selectedCase
    ? `${selectedCase.ticker}:${selectedCase.year_from}-${selectedCase.year_to}`
    : `${ticker}:none`
  const methodCardsKey = `${expansionScopeKey}|mode:${analysisMode}|${methodCards
    .map((card) => card.cardKey)
    .join("|")}`
  const [prevMethodCardsKey, setPrevMethodCardsKey] = useState(methodCardsKey)
  if (prevMethodCardsKey !== methodCardsKey) {
    setPrevMethodCardsKey(methodCardsKey)
    setExpandedCards((previous) => {
      const next: Record<string, boolean> = { ...previous }
      const scopePrefix = `${expansionScopeKey}::`

      // Reset scoped expansion defaults on mode/case/ticker changes.
      for (const existingKey of Object.keys(next)) {
        if (existingKey.startsWith(scopePrefix)) {
          delete next[existingKey]
        }
      }

      for (const card of methodCards) {
        const scopedKey = buildCardExpansionKey(expansionScopeKey, card.cardKey)
        const defaultExpanded = false
        next[scopedKey] = defaultExpanded
      }

      return next
    })
  }

  const methodCoverageSummary = useMemo(() => {
    let selected = 0
    let available = 0
    for (const card of methodCards) {
      selected += 1
      if (outputs[card.cardKey]) available += 1
    }
    return `Method coverage ${available}/${selected}`
  }, [methodCards, outputs])

  const selectedCompareCampaignIds = useMemo(
    () => Array.from(new Set([selectedLlmCampaignA, selectedLlmCampaignB].filter(Boolean))),
    [selectedLlmCampaignA, selectedLlmCampaignB]
  )

  const hasAnyInsightOutput = useMemo(
    () => selectedCompareCampaignIds.some((campaignId) => Boolean(insightOutputs[campaignId] ?? null)),
    [insightOutputs, selectedCompareCampaignIds]
  )

  const compactInsightItems = useMemo(
    () =>
      selectedCompareCampaignIds.map((campaignId) => ({
        campaignId,
        label:
          (llmCampaignOptions.find((campaign) => campaign.campaign_id === campaignId)?.display_name ??
            campaignId),
        debug: insightDebugInfo[campaignId] ?? null,
        debugPath: insightDebugPaths[campaignId] ?? null,
      })),
    [insightDebugInfo, insightDebugPaths, llmCampaignOptions, selectedCompareCampaignIds]
  )

  const selectedCampaignA = useMemo(
    () => llmCampaignOptions.find((campaign) => campaign.campaign_id === selectedLlmCampaignA) ?? null,
    [llmCampaignOptions, selectedLlmCampaignA]
  )

  const selectedCampaignB = useMemo(
    () => llmCampaignOptions.find((campaign) => campaign.campaign_id === selectedLlmCampaignB) ?? null,
    [llmCampaignOptions, selectedLlmCampaignB]
  )

  const selectedCampaignLabelA = selectedCampaignA?.display_name ?? selectedLlmCampaignA ?? ""
  const selectedCampaignLabelB = selectedCampaignB?.display_name ?? selectedLlmCampaignB ?? ""

  const detectorGroups = useMemo(() => {
    return DETECTOR_GROUP_ORDER.map((group) => ({
      ...group,
      detectors: DETECTOR_CATALOG.filter((detector) => detector.group === group.id),
    }))
  }, [])

  const groupedMethodCards = useMemo(() => {
    return DETECTOR_GROUP_ORDER.map((group) => ({
      ...group,
      sectionId: METHOD_GROUP_SECTION_IDS[group.id],
      cards: methodCards.filter((card) => card.group === group.id),
    })).filter((group) => group.cards.length > 0)
  }, [methodCards])

  const deepAutoOpenContextKeys = useMemo(() => {
    return new Set(methodCards.slice(0, 2).map((card) => card.cardKey))
  }, [methodCards])

  const expandedCount = useMemo(() => {
    let count = 0
    for (const card of methodCards) {
      const scopedKey = buildCardExpansionKey(expansionScopeKey, card.cardKey)
      if (expandedCards[scopedKey]) {
        count += 1
      }
    }
    return count
  }, [expandedCards, expansionScopeKey, methodCards])

  const isExecutiveMode = analysisMode === "executive"
  const isDeepMode = analysisMode === "deep"
  const hasMultipleCases = cases.length > 1

  const handleApplyPreset = (
    presetDetectorIds: string[],
    preferredLens: LabCleaningLens,
    mode: AnalysisMode
  ) => {
    const nextDetectors = [...new Set(presetDetectorIds)]
    setAnalysisMode(mode)
    setSelectedDetectors([...nextDetectors])
    let nextLens = preferredLens
    if (mode === "executive") {
      if (availableLenses.includes("deboilerplated")) {
        nextLens = "deboilerplated"
      } else {
        const fallbackLens = pickPreferredAvailableLens(availableLenses)
        if (fallbackLens) {
          nextLens = fallbackLens
        }
      }
      setLens(nextLens)
      setPresetStatus({
        message: `Applied quick read: ${nextDetectors.length} methods, lens=${nextLens}`,
        token: Date.now(),
      })
      return
    }
    if (!availableLenses.includes(nextLens)) {
      const fallbackLens = pickPreferredAvailableLens(availableLenses)
      if (fallbackLens) {
        nextLens = fallbackLens
        setLens(nextLens)
      }
    }
    setPresetStatus({
      message: `Applied deep review: ${nextDetectors.length} methods, lens=${nextLens}`,
      token: Date.now(),
    })
  }

  const handleReloadOutputs = () => {
    clearLabOutputCache()
    setReloadNonce((previous) => previous + 1)
  }

  const handleExpandAllCards = () => {
    setExpandedCards((previous) => {
      const next: Record<string, boolean> = { ...previous }
      for (const card of methodCards) {
        next[buildCardExpansionKey(expansionScopeKey, card.cardKey)] = true
      }
      return next
    })
  }

  const handleCollapseAllCards = () => {
    setExpandedCards((previous) => {
      const next: Record<string, boolean> = { ...previous }
      for (const card of methodCards) {
        next[buildCardExpansionKey(expansionScopeKey, card.cardKey)] = false
      }
      return next
    })
  }

  const handleToggleCardExpanded = (cardKey: string) => {
    const scopedKey = buildCardExpansionKey(expansionScopeKey, cardKey)
    setExpandedCards((previous) => ({
      ...previous,
      [scopedKey]: !previous[scopedKey],
    }))
  }

  const buildDebugPayload = (
    info: DetectorDebugInfo,
    debugText: string | null
  ): string => {
    return JSON.stringify(
      {
        ticker: info.ticker,
        pair: `${info.yearFrom}-${info.yearTo}`,
        lens: info.lens,
        detector: info.detectorId,
        campaign_id: info.campaignId ?? null,
        campaign_display_name: info.campaignDisplayName ?? null,
        expected_path: info.expectedPath,
        requested_url: info.requestedUrl,
        error: info.errorText,
        schema_issue_or_debug: debugText,
      },
      null,
      2
    )
  }

  const handleCopyAgreementDebug = async () => {
    if (!agreementDebugInfo) return
    const payload = buildDebugPayload(agreementDebugInfo, agreementDebugPath)
    const didCopy = await copyTextToClipboard(payload)
    setAgreementCopyState(didCopy ? "copied" : "failed")
  }

  if (isLoadingCases) {
    return <p className="text-sm text-slate-300">Loading lab cases...</p>
  }

  if (caseError) {
    return (
      <div className="space-y-1">
        <p className="text-sm text-amber-200">{caseError}</p>
        {caseDebugPath ? <p className="break-all text-[11px] text-slate-400">{caseDebugPath}</p> : null}
      </div>
    )
  }

  if (!cases.length) {
    if (isPilotOnlyMatrixView) {
      return (
        <section className="space-y-6">
          {pilotMatrixBundle ? (
            <VisibleCaseAnswerSummary
              bundle={pilotMatrixBundle}
              noveltyLedger={noveltyLedgerArtifact}
              effortRobustness={effortRobustnessBundle}
            />
          ) : null}

          <ProtocolLabPilotMatrixPanel
            bundle={pilotMatrixBundle}
            isLoading={isLoadingPilotMatrix}
            error={pilotMatrixError}
            debugText={pilotMatrixDebugText}
            effortRobustness={effortRobustnessBundle}
            isLoadingEffortRobustness={isLoadingEffortRobustness}
            effortRobustnessError={effortRobustnessError}
            effortRobustnessDebugText={effortRobustnessDebugText}
            noveltyLedger={noveltyLedgerArtifact}
            isLoadingNoveltyLedger={isLoadingNoveltyLedger}
            noveltyLedgerError={noveltyLedgerError}
            noveltyLedgerDebugText={noveltyLedgerDebugText}
            skepticCase={skepticCaseArtifact}
            isLoadingSkepticCase={isLoadingSkepticCase}
            skepticCaseError={skepticCaseError}
            skepticCaseDebugText={skepticCaseDebugText}
          />

          <section
            id="lab-lower-audit-unavailable"
            className="rounded-[1.25rem] border border-amber-300/20 bg-amber-400/10 p-4 text-sm text-slate-200"
          >
            <div className="text-xs uppercase tracking-wide text-amber-100">Scope boundary</div>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              <article className="rounded-lg border border-white/10 bg-slate-950/35 p-3">
                <div className="text-[11px] uppercase tracking-wide text-slate-300">
                  Available here
                </div>
                <p className="mt-2 text-sm text-slate-100">
                  The bounded filing answer, protocol meaning, Fresh vs reused, and the matched-effort
                  integrity surface are part of this public LLY slice.
                </p>
              </article>
              <article className="rounded-lg border border-white/10 bg-slate-950/35 p-3">
                <div className="text-[11px] uppercase tracking-wide text-slate-300">
                  Intentionally not here
                </div>
                <p className="mt-2 text-sm text-slate-100">
                  The full lower-audit runtime stack, broader benchmark-style claims, and the deeper
                  multi-panel runtime route are not part of the public LLY surface.
                </p>
              </article>
              <article className="rounded-lg border border-white/10 bg-slate-950/35 p-3">
                <div className="text-[11px] uppercase tracking-wide text-slate-300">
                  Why the stop matters
                </div>
                <p className="mt-2 text-sm text-slate-100">
                  Stopping here keeps the visible policy-heavy case aligned with what the shipped
                  product actually supports instead of implying audit depth that this issuer does not
                  currently expose.
                </p>
              </article>
            </div>
          </section>
        </section>
      )
    }

    return (
      <div className="rounded-lg border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
        No lab cases found for this ticker yet.
      </div>
    )
  }

  return (
    <section className="space-y-6">
      {selectedCase && (selectedLlmCampaignA || selectedLlmCampaignB) ? (
        <RiskNarrativeSummary
          ticker={ticker}
          yearFrom={selectedCase.year_from}
          yearTo={selectedCase.year_to}
          modelALabel={selectedCampaignLabelA}
          modelBLabel={selectedCampaignLabelB}
          modelARuntime={selectedLlmCampaignA ? outlineOutputs[selectedLlmCampaignA] ?? null : null}
          modelBRuntime={selectedLlmCampaignB ? outlineOutputs[selectedLlmCampaignB] ?? null : null}
          modelAStructured={selectedLlmCampaignA ? structuredOutlineOutputs[selectedLlmCampaignA] ?? null : null}
          modelBStructured={selectedLlmCampaignB ? structuredOutlineOutputs[selectedLlmCampaignB] ?? null : null}
          analysisMode={analysisMode}
        />
      ) : null}

      {isPilotMatrixSelectedCase ? (
        <ProtocolLabPilotMatrixPanel
          bundle={pilotMatrixBundle}
          isLoading={isLoadingPilotMatrix}
          error={pilotMatrixError}
          debugText={pilotMatrixDebugText}
          effortRobustness={effortRobustnessBundle}
          isLoadingEffortRobustness={isLoadingEffortRobustness}
          effortRobustnessError={effortRobustnessError}
          effortRobustnessDebugText={effortRobustnessDebugText}
          noveltyLedger={noveltyLedgerArtifact}
          isLoadingNoveltyLedger={isLoadingNoveltyLedger}
          noveltyLedgerError={noveltyLedgerError}
          noveltyLedgerDebugText={noveltyLedgerDebugText}
          skepticCase={skepticCaseArtifact}
          isLoadingSkepticCase={isLoadingSkepticCase}
          skepticCaseError={skepticCaseError}
          skepticCaseDebugText={skepticCaseDebugText}
        />
      ) : null}

      <section
        id="lab-audit-trail"
        className="space-y-6 rounded-[1.4rem] border border-white/10 bg-slate-950/18 p-5"
      >
        <div className="max-w-3xl">
          <p className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Audit trail</p>
          <h2 className="mt-2 text-xl font-semibold text-slate-100">How we checked the filing answer</h2>
          <p className="mt-2 text-sm text-slate-300">
            This lower layer is for pressure-testing the answer above. Start with the filing answer,
            then the protocol meaning, and only then use controls, methods, and deeper compare surfaces.
          </p>
        </div>

        <details className="rounded-[1.1rem] border border-white/10 bg-slate-950/22 p-4">
          <summary className="cursor-pointer list-none text-sm font-semibold text-slate-100">
            Advanced controls
          </summary>
          <p className="mt-3 max-w-3xl text-xs text-slate-400">
            Power-user controls for changing lanes, methods, and diagnostics. They stay below the answer
            and protocol layers on purpose.
          </p>
          <div className="mt-4 space-y-4 text-sm text-slate-200">
            {isPilotMatrixSelectedCase ? (
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-lg border border-white/10 bg-slate-950/35 p-4">
                  <div className="text-xs uppercase tracking-wide text-slate-400">Cleaning lens</div>
                  <div className="mt-3">
                    <CleaningLensToggle value={lens} options={lensOptions} onChange={setLens} />
                  </div>
                  <p className="mt-3 text-xs text-slate-400">
                    {lens === "deboilerplated"
                      ? "Deboilerplated remains the default filing-cleaning view for a cleaner deterministic read below the matrix."
                      : "Switch lenses to compare the default cleaned view with the raw filing text and other preprocessing variants."}
                  </p>
                </div>
                <div className="rounded-lg border border-white/10 bg-slate-950/35 p-4">
                  <div className="text-xs uppercase tracking-wide text-slate-400">Reading mode</div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => handleApplyPreset(EXECUTIVE_READ_PRESET, "deboilerplated", "executive")}
                      className={`rounded-md border px-3 py-1.5 text-sm transition ${
                        isExecutiveMode
                          ? "border-sky-200/80 bg-sky-400/25 text-sky-50 shadow-[0_0_0_1px_rgba(125,211,252,0.25)]"
                          : "border-white/15 bg-slate-900/45 text-slate-300 hover:border-white/30 hover:text-slate-100"
                      }`}
                    >
                      Quick read
                    </button>
                    <button
                      type="button"
                      onClick={() => handleApplyPreset(TECHNICAL_DEEP_DIVE_PRESET, lens, "deep")}
                      className={`rounded-md border px-3 py-1.5 text-sm transition ${
                        isDeepMode
                          ? "border-emerald-200/80 bg-emerald-400/25 text-emerald-50 shadow-[0_0_0_1px_rgba(110,231,183,0.25)]"
                          : "border-white/15 bg-slate-900/45 text-slate-300 hover:border-white/30 hover:text-slate-100"
                      }`}
                    >
                      Deep review
                    </button>
                  </div>
                  <p className="mt-3 text-xs text-slate-400">
                    {isExecutiveMode
                      ? "Quick read keeps the two core deterministic methods in view first."
                      : "Deep review restores the full deterministic set and richer method context."}
                  </p>
                  {presetStatus ? <p className="mt-2 text-xs text-emerald-300">{presetStatus.message}</p> : null}
                </div>
              </div>
            ) : null}

            {hasMultipleCases ? (
              <div className="rounded-lg border border-white/10 bg-slate-950/35 p-4">
                <div className="text-xs uppercase tracking-wide text-slate-400">Case override</div>
                <select
                  value={selectedCaseKey ?? ""}
                  onChange={(event) => setSelectedCaseKey(event.target.value)}
                  className="mt-3 w-full rounded-md border border-white/15 bg-slate-950/40 px-3 py-2 text-sm text-slate-100"
                >
                  {cases.map((item) => (
                    <option key={buildCaseKey(item)} value={buildCaseKey(item)}>
                      {formatFiscalYearRange(item.year_from, item.year_to)}
                    </option>
                  ))}
                </select>
              </div>
            ) : null}

            {llmCampaignOptions.length > 1 ? (
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-lg border border-white/10 bg-slate-950/35 p-4">
                  <div className="text-xs uppercase tracking-wide text-slate-400">Compare campaign A</div>
                  <select
                    value={selectedLlmCampaignA}
                    onChange={(event) => setSelectedLlmCampaignA(event.target.value)}
                    className="mt-3 w-full rounded-md border border-white/15 bg-slate-950/40 px-3 py-2 text-sm text-slate-100"
                  >
                    {llmCampaignOptions.map((campaign) => (
                      <option key={campaign.campaign_id} value={campaign.campaign_id}>
                        {campaign.display_name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="rounded-lg border border-white/10 bg-slate-950/35 p-4">
                  <div className="text-xs uppercase tracking-wide text-slate-400">Compare campaign B</div>
                  <select
                    value={selectedLlmCampaignB}
                    onChange={(event) => setSelectedLlmCampaignB(event.target.value)}
                    disabled={llmCampaignOptions.length <= 1}
                    className="mt-3 w-full rounded-md border border-white/15 bg-slate-950/40 px-3 py-2 text-sm text-slate-100"
                  >
                    {llmCampaignOptions.map((campaign) => (
                      <option key={campaign.campaign_id} value={campaign.campaign_id}>
                        {campaign.display_name}
                      </option>
                    ))}
                  </select>
                  {llmCampaignOptions.length <= 1 ? (
                    <div className="mt-2 text-xs text-slate-400">Second full-section campaign pending.</div>
                  ) : null}
                </div>
              </div>
            ) : null}

            <div className="rounded-lg border border-white/10 bg-slate-950/35 p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="text-xs uppercase tracking-wide text-slate-400">Deterministic methods</div>
                <div className="text-xs text-slate-500">
                  Available outputs: {availableDetectorIds.length}/{DETECTOR_CATALOG.length}
                </div>
              </div>
              <div className="mt-3 space-y-3">
                {detectorGroups.map((group) => (
                  <div key={group.id} className="rounded-md border border-white/10 bg-slate-900/35 p-3">
                    <div className="text-xs uppercase tracking-wide text-slate-400">{group.label}</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {group.detectors.map((detector) => {
                        const isAvailable = availableDetectorSet.has(detector.id)
                        const isSelected = selectedDetectors.includes(detector.id)
                        return (
                          <label
                            key={detector.id}
                            className={`flex items-center gap-2 rounded-full border px-3 py-1 text-xs ${
                              isAvailable
                                ? "border-white/10 bg-white/5 text-slate-200"
                                : "border-amber-300/30 bg-amber-400/10 text-amber-100"
                            }`}
                          >
                            <input
                              type="checkbox"
                              className="h-3 w-3"
                              checked={isSelected}
                              onChange={() => {
                                setSelectedDetectors((prev) => {
                                  if (prev.includes(detector.id)) {
                                    return prev.filter((item) => item !== detector.id)
                                  }
                                  return [...prev, detector.id]
                                })
                              }}
                            />
                            <span>
                              {detector.label}
                              {!isAvailable ? " (missing artifact)" : ""}
                            </span>
                          </label>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid gap-3 lg:grid-cols-[1fr,0.8fr]">
              <div className="rounded-lg border border-white/10 bg-slate-950/35 p-4">
                <div className="text-xs uppercase tracking-wide text-slate-400">Utilities</div>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={handleExpandAllCards}
                    className="rounded-md border border-white/20 bg-slate-900/60 px-2 py-1 text-xs text-slate-100 transition hover:border-white/40"
                  >
                    Expand all ({expandedCount}/{methodCards.length} expanded)
                  </button>
                  <button
                    type="button"
                    onClick={handleCollapseAllCards}
                    className="rounded-md border border-white/20 bg-slate-900/60 px-2 py-1 text-xs text-slate-100 transition hover:border-white/40"
                  >
                    Collapse all ({expandedCount}/{methodCards.length} expanded)
                  </button>
                  <button
                    type="button"
                    onClick={handleReloadOutputs}
                    disabled={!selectedCase || isLoadingOutputs}
                    className="rounded-md border border-white/10 bg-slate-950/40 px-2 py-1 text-xs text-slate-300 transition hover:border-white/25 hover:text-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Reload outputs
                  </button>
                </div>
                <div className="mt-3 rounded-md border border-white/10 bg-slate-900/35 px-3 py-2 text-xs text-slate-300">
                  {methodCoverageSummary}
                </div>
              </div>

              <div className="rounded-lg border border-white/10 bg-slate-950/35 p-4">
                <div className="text-xs uppercase tracking-wide text-slate-400">Jump to section</div>
                <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-300">
                  {isPilotMatrixSelectedCase ? (
                    <a
                      className="underline decoration-white/30 underline-offset-2 hover:text-slate-100"
                      href="#lab-pilot-matrix"
                    >
                      Protocol
                    </a>
                  ) : null}
                  <a
                    className="underline decoration-white/30 underline-offset-2 hover:text-slate-100"
                    href="#lab-risk-narrative"
                  >
                    Filing answer
                  </a>
                  <a
                    className="underline decoration-white/30 underline-offset-2 hover:text-slate-100"
                    href="#lab-core-methods"
                  >
                    Core methods
                  </a>
                  <a
                    className="underline decoration-white/30 underline-offset-2 hover:text-slate-100"
                    href="#lab-structure-methods"
                  >
                    Structure methods
                  </a>
                  <a
                    className="underline decoration-white/30 underline-offset-2 hover:text-slate-100"
                    href="#lab-agreement"
                  >
                    Agreement
                  </a>
                  <a
                    className="underline decoration-white/30 underline-offset-2 hover:text-slate-100"
                    href="#lab-outline-compare"
                  >
                    Structure audit
                  </a>
                  {(hasAnyInsightOutput || compactInsightItems.length > 0) ? (
                    <a
                      className="underline decoration-white/30 underline-offset-2 hover:text-slate-100"
                      href="#lab-insight-lens"
                    >
                      Insight lens
                    </a>
                  ) : null}
                  {isDeepMode ? (
                    <a
                      className="underline decoration-white/30 underline-offset-2 hover:text-slate-100"
                      href="#lab-method-context"
                    >
                      Method context
                    </a>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        </details>

        <div id="lab-method-context" className="space-y-6">
          {groupedMethodCards.map((group) => (
            <section key={group.id} id={group.sectionId} className="space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-300">
                {group.label}
              </h3>
              <div className="grid gap-4">
                {group.cards.map((detector) => (
                  <MethodCard
                    key={detector.cardKey}
                    detectorId={detector.id}
                    title={detector.label}
                    description={`${detector.technicalLabel}. ${detector.description}`}
                    llmCampaign={null}
                    output={outputs[detector.cardKey] ?? null}
                    debugPath={outputDebugPaths[detector.cardKey] ?? null}
                    debugInfo={outputDebugInfo[detector.cardKey] ?? null}
                    isLoading={isLoadingOutputs}
                    analysisMode={analysisMode}
                    methodProfile={methodProfilesByDetector[detector.id] ?? null}
                    autoOpenContext={isDeepMode && deepAutoOpenContextKeys.has(detector.cardKey)}
                    isExpanded={
                      expandedCards[buildCardExpansionKey(expansionScopeKey, detector.cardKey)] ??
                      false
                    }
                    onToggleExpanded={() => handleToggleCardExpanded(detector.cardKey)}
                    emptyMessage="No output available for this method, lens, and model combination. Try the deboilerplated lens or a different ticker for available results."
                  />
                ))}
              </div>
            </section>
          ))}
        </div>

        <div id="lab-agreement" className="space-y-4">
          <div>
            <h3 className="text-lg font-semibold text-slate-100">Where methods agree</h3>
            <p className="text-xs text-slate-400">
              Cross-check how much the deterministic methods reinforce the same ranked risk themes before
              leaning on any single audit surface.
            </p>
          </div>
          <AgreementMatrix output={agreementOutput} />
          {!agreementOutput ? (
            <div className="space-y-2 rounded-md border border-amber-400/30 bg-amber-400/10 p-3 text-xs text-slate-200">
              <p className="font-semibold text-amber-100">Missing artifact</p>
              {agreementDebugInfo?.expectedPath ? (
                <p className="break-all text-[11px] text-slate-100">
                  Expected path: {agreementDebugInfo.expectedPath}
                </p>
              ) : null}
              {agreementDebugInfo?.requestedUrl ? (
                <p className="break-all text-[11px] text-slate-300">
                  Requested URL: {agreementDebugInfo.requestedUrl}
                </p>
              ) : null}
              {agreementDebugInfo?.errorText ? (
                <p className="text-[11px] text-amber-100">{agreementDebugInfo.errorText}</p>
              ) : null}
              {agreementDebugPath ? (
                <p className="break-all text-[11px] text-slate-300">{agreementDebugPath}</p>
              ) : null}
              {agreementDebugInfo ? (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleCopyAgreementDebug}
                    className="rounded-md border border-white/20 bg-slate-900/60 px-2 py-1 text-[11px] text-slate-100 transition hover:border-white/40"
                  >
                    Copy debug info
                  </button>
                  {agreementCopyState === "copied" ? (
                    <span className="text-[11px] text-emerald-300">Copied.</span>
                  ) : null}
                  {agreementCopyState === "failed" ? (
                    <span className="text-[11px] text-rose-300">Copy failed.</span>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>

        {selectedLlmCampaignA || selectedLlmCampaignB ? (
          <OutlineComparePanel
            modelALabel={selectedCampaignLabelA}
            modelBLabel={selectedCampaignLabelB}
            modelAOutput={
              selectedLlmCampaignA ? outlineOutputs[selectedLlmCampaignA] ?? null : null
            }
            modelBOutput={
              selectedLlmCampaignB ? outlineOutputs[selectedLlmCampaignB] ?? null : null
            }
            modelADebug={
              selectedLlmCampaignA ? outlineDebugInfo[selectedLlmCampaignA] ?? null : null
            }
            modelBDebug={
              selectedLlmCampaignB ? outlineDebugInfo[selectedLlmCampaignB] ?? null : null
            }
            modelADebugPath={
              selectedLlmCampaignA ? outlineDebugPaths[selectedLlmCampaignA] ?? null : null
            }
            modelBDebugPath={
              selectedLlmCampaignB ? outlineDebugPaths[selectedLlmCampaignB] ?? null : null
            }
            modelAStructuredOutput={
              selectedLlmCampaignA ? structuredOutlineOutputs[selectedLlmCampaignA] ?? null : null
            }
            modelBStructuredOutput={
              selectedLlmCampaignB ? structuredOutlineOutputs[selectedLlmCampaignB] ?? null : null
            }
            modelAStructuredDebug={
              selectedLlmCampaignA ? structuredOutlineDebugInfo[selectedLlmCampaignA] ?? null : null
            }
            modelBStructuredDebug={
              selectedLlmCampaignB ? structuredOutlineDebugInfo[selectedLlmCampaignB] ?? null : null
            }
            modelAStructuredDebugPath={
              selectedLlmCampaignA ? structuredOutlineDebugPaths[selectedLlmCampaignA] ?? null : null
            }
            modelBStructuredDebugPath={
              selectedLlmCampaignB ? structuredOutlineDebugPaths[selectedLlmCampaignB] ?? null : null
            }
            analysisMode={analysisMode}
          />
        ) : null}

        {selectedLlmCampaignA || selectedLlmCampaignB ? (
          selectedCompareCampaignIds.length > 0 && !hasAnyInsightOutput ? (
            <div
              id="lab-insight-lens"
              className="rounded-lg border border-white/10 bg-slate-950/24 px-4 py-3 text-sm text-slate-200"
            >
              <div className="text-xs uppercase tracking-wide text-slate-400">Optional insight lens</div>
              <p className="mt-2 text-sm text-slate-200">
                No optional insight sidecar is published for the selected compare lanes. Runtime and
                structured outline artifacts above remain the shipped compare path.
              </p>
              <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-300">
                {compactInsightItems.map((item) => (
                  <span
                    key={item.campaignId}
                    className="rounded-full border border-white/10 bg-slate-900/35 px-2 py-1"
                  >
                    {item.label}: {item.debug?.errorText ?? "No insight sidecar present."}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <InsightLensPanel
              modelALabel={selectedCampaignLabelA}
              modelBLabel={selectedCampaignLabelB}
              modelAOutput={selectedLlmCampaignA ? insightOutputs[selectedLlmCampaignA] ?? null : null}
              modelBOutput={selectedLlmCampaignB ? insightOutputs[selectedLlmCampaignB] ?? null : null}
              modelADebug={selectedLlmCampaignA ? insightDebugInfo[selectedLlmCampaignA] ?? null : null}
              modelBDebug={selectedLlmCampaignB ? insightDebugInfo[selectedLlmCampaignB] ?? null : null}
              modelADebugPath={selectedLlmCampaignA ? insightDebugPaths[selectedLlmCampaignA] ?? null : null}
              modelBDebugPath={selectedLlmCampaignB ? insightDebugPaths[selectedLlmCampaignB] ?? null : null}
            />
          )
        ) : null}
      </section>
    </section>
  )
}
