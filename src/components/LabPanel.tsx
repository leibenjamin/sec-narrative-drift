import type { ComponentProps } from "react"
import CompanyBriefingShell from "./CompanyBriefingShell"
import { useEffect, useMemo, useRef, useState } from "react"
import LabPanelAuditTrailSection from "./LabPanelAuditTrailSection"
import LabPanelBoundedVisibleCase from "./LabPanelBoundedVisibleCase"
import useLabPanelOutputs from "./useLabPanelOutputs"
import useLabPanelPilotArtifacts, {
  type LabPanelPilotMatrixTarget,
} from "./useLabPanelPilotArtifacts"
import {
  formatLabLoadDebug,
  getDefaultLabLlmCampaignPair,
  loadLabMethodProfilesIndex,
  listLabCasesForTicker,
  loadLabLlmCampaignsIndex,
} from "../lib/labData"
import { formatFiscalYearRange } from "../lib/fiscalYear"
import type {
  LabCase,
  LabCleaningLens,
  LabLlmCampaign,
  LabMethodProfile,
  LabSourceId,
} from "../lib/labTypes"

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
type AnalysisMode = "executive" | "deep"

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

  type LabPanelMode = "registry_case" | "bounded_visible_case" | "empty"

  const panelMode = useMemo<LabPanelMode>(() => {
    if (selectedCase) return "registry_case"
    if (ticker === "LLY") return "bounded_visible_case"
    return "empty"
  }, [selectedCase, ticker])

  const pilotMatrixTarget = useMemo<LabPanelPilotMatrixTarget | null>(() => {
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
    if (panelMode === "bounded_visible_case") {
      return {
        mode: "ticker",
        ticker,
      }
    }
    return null
  }, [panelMode, selectedCase, ticker])

  const isPilotMatrixSelectedCase = pilotMatrixTarget?.mode === "case"
  const isPilotOnlyMatrixView = panelMode === "bounded_visible_case"
  const pilotArtifacts = useLabPanelPilotArtifacts(pilotMatrixTarget)

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
  const outputState = useLabPanelOutputs({
    selectedCase,
    lens,
    selectedDetectors,
    sourceId,
    selectedLlmCampaignA,
    selectedLlmCampaignB,
  })
  const {
    isLoadingOutputs,
    insightOutputs,
    insightDebugPaths,
    insightDebugInfo,
    reloadOutputs,
  } = outputState

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

  const caseOptions = useMemo(
    () =>
      cases.map((item) => ({
        key: buildCaseKey(item),
        label: formatFiscalYearRange(item.year_from, item.year_to),
      })),
    [cases]
  )

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
    reloadOutputs()
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

  const isCardExpanded = (cardKey: string) =>
    expandedCards[buildCardExpansionKey(expansionScopeKey, cardKey)] ?? false

  const advancedControlsProps = {
    isPilotMatrixSelectedCase,
    lens,
    lensOptions,
    onLensChange: setLens,
    onApplyQuickRead: () => handleApplyPreset(EXECUTIVE_READ_PRESET, "deboilerplated", "executive"),
    onApplyDeepReview: () => handleApplyPreset(TECHNICAL_DEEP_DIVE_PRESET, lens, "deep"),
    isExecutiveMode,
    isDeepMode,
    presetStatusMessage: presetStatus?.message ?? null,
    hasMultipleCases,
    caseOptions,
    selectedCaseKey,
    onSelectedCaseKeyChange: setSelectedCaseKey,
    llmCampaignOptions,
    selectedLlmCampaignA,
    selectedLlmCampaignB,
    onSelectedLlmCampaignAChange: setSelectedLlmCampaignA,
    onSelectedLlmCampaignBChange: setSelectedLlmCampaignB,
    detectorGroups,
    availableDetectorSet,
    selectedDetectors,
    onToggleDetector: (detectorId: string) => {
      setSelectedDetectors((previous) => {
        if (previous.includes(detectorId)) {
          return previous.filter((item) => item !== detectorId)
        }
        return [...previous, detectorId]
      })
    },
    availableDetectorCount: availableDetectorIds.length,
    detectorCatalogCount: DETECTOR_CATALOG.length,
    onExpandAllCards: handleExpandAllCards,
    onCollapseAllCards: handleCollapseAllCards,
    expandedCount,
    methodCardCount: methodCards.length,
    onReloadOutputs: handleReloadOutputs,
    isReloadDisabled: !selectedCase || isLoadingOutputs,
    showProtocolJump: isPilotMatrixSelectedCase,
    showInsightJump: hasAnyInsightOutput || compactInsightItems.length > 0,
    showMethodContextJump: isDeepMode,
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
      return <LabPanelBoundedVisibleCase ticker={ticker} pilotArtifacts={pilotArtifacts} />
    }

    return (
      <div className="rounded-lg border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
        No lab cases found for this ticker yet.
      </div>
    )
  }

  const auditTrailProps: ComponentProps<typeof LabPanelAuditTrailSection> = {
    analysisMode,
    advancedControlsProps,
    groupedMethodCards,
    outputState,
    methodProfilesByDetector,
    deepAutoOpenContextKeys,
    isCardExpanded,
    onToggleCardExpanded: handleToggleCardExpanded,
    selectedLlmCampaignA,
    selectedLlmCampaignB,
    selectedCampaignLabelA,
    selectedCampaignLabelB,
    selectedCompareCampaignIds,
    hasAnyInsightOutput,
    compactInsightItems,
  }

  return (
    <section className="space-y-4 sm:space-y-5">
      {selectedCase ? (
        <CompanyBriefingShell
          selectedCase={selectedCase}
          selectedLlmCampaignA={selectedLlmCampaignA}
          selectedLlmCampaignB={selectedLlmCampaignB}
          selectedCampaignLabelA={selectedCampaignLabelA}
          selectedCampaignLabelB={selectedCampaignLabelB}
          analysisMode={analysisMode}
          outputState={outputState}
          pilotArtifacts={pilotArtifacts}
          auditTrailProps={auditTrailProps}
        />
      ) : null}
    </section>
  )
}
