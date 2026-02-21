import { useEffect, useMemo, useRef, useState } from "react"
import AgreementMatrix from "./AgreementMatrix"
import CleaningLensToggle from "./CleaningLensToggle"
import MethodCard from "./MethodCard"
import {
  LabDataLoadError,
  buildExpectedLabOutputArtifactFromVariant,
  buildExpectedLabOutputArtifact,
  buildLabOutputRepoPath,
  buildLabOutputRequestUrl,
  clearLabOutputCache,
  findLabLlmVariant,
  formatLabLoadDebug,
  getDefaultDeterministicTrackSlug,
  getDefaultLabLlmCampaignPair,
  getLabLlmCampaignById,
  listLabCasesForTicker,
  loadLabLlmCampaignsIndex,
  loadLabOutput,
  resolveLabOutputLink,
} from "../lib/labData"
import { withBase } from "../lib/paths"
import type {
  LabCase,
  LabCleaningLens,
  LabLlmCampaign,
  LabOutput,
  LabSourceId,
} from "../lib/labTypes"

const DETECTOR_CATALOG = [
  {
    id: "det_logodds_terms_v1",
    label: "Log-odds terms",
    description: "Distinctive term shifts from the baseline log-odds detector.",
    group: "core",
    defaultSelected: true,
  },
  {
    id: "det_jsd_ngrams_v1",
    label: "JSD n-grams",
    description: "Distributional drift using Jensen-Shannon divergence.",
    group: "core",
    defaultSelected: true,
  },
  {
    id: "det_minhash_boilerplate_v1",
    label: "Minhash boilerplate",
    description: "Near-duplicate paragraph reuse estimates.",
    group: "structure",
    defaultSelected: true,
  },
  {
    id: "det_winnowing_fingerprint_v1",
    label: "Winnowing fingerprints",
    description: "Shared fingerprint spans between years.",
    group: "structure",
    defaultSelected: false,
  },
  {
    id: "det_structure_artifacts_v1",
    label: "Structure artifacts",
    description: "Heading and length changes across years.",
    group: "structure",
    defaultSelected: true,
  },
  {
    id: "det_llm_delta_brief_v1",
    label: "LLM delta brief (precomputed)",
    description: "Precomputed narrative summary.",
    group: "llm",
    defaultSelected: false,
  },
  {
    id: "det_llm_excerpt_picker_v1",
    label: "LLM excerpt picker (precomputed)",
    description: "Precomputed excerpt selection.",
    group: "llm",
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
  { id: "core", label: "Core drift methods" },
  { id: "structure", label: "Reuse and structure methods" },
  { id: "llm", label: "LLM sidecars (precomputed)" },
] as const
const LENS_PREFERENCE_ORDER: LabCleaningLens[] = [
  "deboilerplated",
  "raw",
  "stage1_clean",
  "structure_aware",
]
const LLM_DETECTOR_IDS = new Set<string>([
  "det_llm_delta_brief_v1",
  "det_llm_excerpt_picker_v1",
])
const DET_TRACK_SLUG = getDefaultDeterministicTrackSlug()

function buildDetectorCardKey(detectorId: string, campaignId?: string): string {
  if (campaignId) return `${detectorId}::${campaignId}`
  return detectorId
}

function countDeltaCitations(output: LabOutput | null): number {
  if (!output || output.detector_id !== "det_llm_delta_brief_v1") return 0
  const raw = output.artifacts.delta_brief
  if (typeof raw !== "string") return 0
  const matches = raw.match(/\b20\d{2}\s+para\s+\d+\b/gi)
  return matches ? matches.length : 0
}

function countEvidence(output: LabOutput | null): number {
  if (!output) return 0
  return Array.isArray(output.evidence) ? output.evidence.length : 0
}

function excerptEvidenceOverlapPercent(a: LabOutput | null, b: LabOutput | null): number | null {
  if (!a || !b) return null
  if (a.detector_id !== "det_llm_excerpt_picker_v1") return null
  if (b.detector_id !== "det_llm_excerpt_picker_v1") return null
  const setA = new Set<string>()
  const setB = new Set<string>()
  for (const block of a.evidence ?? []) {
    setA.add(`${block.year}:${block.paragraph_idx}`)
  }
  for (const block of b.evidence ?? []) {
    setB.add(`${block.year}:${block.paragraph_idx}`)
  }
  if (setA.size === 0 && setB.size === 0) return 100
  const union = new Set<string>([...setA, ...setB])
  let intersection = 0
  for (const key of union) {
    if (setA.has(key) && setB.has(key)) intersection += 1
  }
  return (intersection / union.size) * 100
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
  const [reloadNonce, setReloadNonce] = useState(0)
  const [llmCampaignOptions, setLlmCampaignOptions] = useState<LabLlmCampaign[]>([])
  const [selectedLlmCampaignA, setSelectedLlmCampaignA] = useState<string>("")
  const [selectedLlmCampaignB, setSelectedLlmCampaignB] = useState<string>("")

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
        setLlmCampaignOptions(index.campaigns)
        const defaults = await getDefaultLabLlmCampaignPair()
        if (cancelled) return

        const available = new Set(index.campaigns.map((campaign) => campaign.campaign_id))
        const requestedA =
          requestedLlmCampaignA && available.has(requestedLlmCampaignA)
            ? requestedLlmCampaignA
            : defaults.primaryCampaignId
        const requestedB =
          requestedLlmCampaignB && available.has(requestedLlmCampaignB)
            ? requestedLlmCampaignB
            : defaults.compareCampaignId
        setSelectedLlmCampaignA(requestedA)
        setSelectedLlmCampaignB(requestedB)
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
    if (!onSelectedLlmCampaignsChange) return
    if (!selectedLlmCampaignA || !selectedLlmCampaignB) return
    onSelectedLlmCampaignsChange({
      llmA: selectedLlmCampaignA,
      llmB: selectedLlmCampaignB,
    })
  }, [onSelectedLlmCampaignsChange, selectedLlmCampaignA, selectedLlmCampaignB])

  const selectedCase = useMemo(() => {
    if (!selectedCaseKey) return null
    return cases.find((item) => buildCaseKey(item) === selectedCaseKey) ?? null
  }, [cases, selectedCaseKey])

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

  const recommendedCases = useMemo(
    () => cases.filter((item) => item.tags?.includes("recommended")),
    [cases]
  )

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

      for (const detectorId of selectedDetectors) {
        const isLlm = LLM_DETECTOR_IDS.has(detectorId)
        if (!isLlm) {
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
              errorText: "Missing artifact: detector output is not listed for this case/lens.",
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
          continue
        }

        const llmCampaignIds = [selectedLlmCampaignA, selectedLlmCampaignB].filter(Boolean)
        for (const campaignId of llmCampaignIds) {
          const cardKey = buildDetectorCardKey(detectorId, campaignId)
          const campaign = await getLabLlmCampaignById(campaignId)
          const variant = await findLabLlmVariant(selectedCase, detectorId, lens, campaignId)
          const expectedArtifact = variant
            ? buildExpectedLabOutputArtifactFromVariant(variant)
            : buildExpectedLabOutputArtifact(
                selectedCase,
                detectorId,
                lens,
                sourceId,
                campaign?.campaign_slug ?? campaignId
              )
          const expectedPath = expectedArtifact?.repoPath ?? null
          let requestedUrl = expectedArtifact?.requestUrl ?? null
          if (!variant) {
            nextOutputs[cardKey] = null
            nextOutputDebugPaths[cardKey] = expectedPath
              ? `Missing artifact. Expected path: ${expectedPath}`
              : "Missing artifact."
            nextOutputDebugInfo[cardKey] = {
              ticker: selectedCase.ticker,
              yearFrom: selectedCase.year_from,
              yearTo: selectedCase.year_to,
              lens,
              detectorId,
              campaignId,
              campaignDisplayName: campaign?.display_name ?? campaignId,
              expectedPath,
              requestedUrl,
              errorText: "Missing artifact: campaign variant output is not indexed for this case/lens.",
            }
            continue
          }

          try {
            const output = await loadLabOutput(selectedCase.ticker, variant.filename, {
              signal: controller.signal,
              llmExpectation: {
                campaignId,
                modelProvider: variant.model_provider,
                modelName: variant.model_name,
              },
            })
            nextOutputs[cardKey] = output
            nextOutputDebugPaths[cardKey] = null
            nextOutputDebugInfo[cardKey] = {
              ticker: selectedCase.ticker,
              yearFrom: selectedCase.year_from,
              yearTo: selectedCase.year_to,
              lens,
              detectorId,
              campaignId,
              campaignDisplayName: variant.display_name,
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
              campaignId,
              campaignDisplayName: variant.display_name,
              expectedPath,
              requestedUrl,
              errorText,
            }
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
    const campaignMap = new Map<string, LabLlmCampaign>()
    for (const campaign of llmCampaignOptions) {
      campaignMap.set(campaign.campaign_id, campaign)
    }
    const cards: Array<
      (typeof DETECTOR_CATALOG)[number] & {
        cardKey: string
        campaignId?: string
        campaign?: LabLlmCampaign | null
      }
    > = []
    for (const detector of DETECTOR_CATALOG) {
      if (!selected.has(detector.id)) continue
      if (!LLM_DETECTOR_IDS.has(detector.id)) {
        cards.push({
          ...detector,
          cardKey: buildDetectorCardKey(detector.id),
          campaign: null,
        })
        continue
      }
      const selectedCampaignIds = Array.from(
        new Set([selectedLlmCampaignA, selectedLlmCampaignB].filter(Boolean))
      )
      for (const campaignId of selectedCampaignIds) {
        cards.push({
          ...detector,
          cardKey: buildDetectorCardKey(detector.id, campaignId),
          campaignId,
          campaign: campaignMap.get(campaignId) ?? null,
        })
      }
    }
    return cards
  }, [selectedDetectors, llmCampaignOptions, selectedLlmCampaignA, selectedLlmCampaignB])

  const llmCompareRows = useMemo(() => {
    const rows: Array<{
      detectorId: string
      detectorLabel: string
      confidenceDelta: number | null
      evidenceDelta: number
      citationDelta: number | null
      overlapPercent: number | null
    }> = []
    if (!selectedLlmCampaignA || !selectedLlmCampaignB) return rows
    for (const detector of DETECTOR_CATALOG) {
      if (!LLM_DETECTOR_IDS.has(detector.id)) continue
      if (!selectedDetectors.includes(detector.id)) continue
      const outputA = outputs[buildDetectorCardKey(detector.id, selectedLlmCampaignA)] ?? null
      const outputB = outputs[buildDetectorCardKey(detector.id, selectedLlmCampaignB)] ?? null
      const confidenceA = outputA?.metrics.confidence ?? null
      const confidenceB = outputB?.metrics.confidence ?? null
      const confidenceDelta =
        confidenceA !== null && confidenceB !== null ? confidenceA - confidenceB : null
      const evidenceDelta = countEvidence(outputA) - countEvidence(outputB)
      const citationDelta =
        detector.id === "det_llm_delta_brief_v1"
          ? countDeltaCitations(outputA) - countDeltaCitations(outputB)
          : null
      const overlapPercent =
        detector.id === "det_llm_excerpt_picker_v1"
          ? excerptEvidenceOverlapPercent(outputA, outputB)
          : null
      rows.push({
        detectorId: detector.id,
        detectorLabel: detector.label,
        confidenceDelta,
        evidenceDelta,
        citationDelta,
        overlapPercent,
      })
    }
    return rows
  }, [outputs, selectedLlmCampaignA, selectedLlmCampaignB, selectedDetectors])

  const detectorGroups = useMemo(() => {
    return DETECTOR_GROUP_ORDER.map((group) => ({
      ...group,
      detectors: DETECTOR_CATALOG.filter((detector) => detector.group === group.id),
    }))
  }, [])

  const selectedAvailableDetectorCount = useMemo(() => {
    let count = 0
    for (const detectorId of selectedDetectors) {
      if (availableDetectorSet.has(detectorId)) {
        count += 1
      }
    }
    return count
  }, [availableDetectorSet, selectedDetectors])

  const selectedPairLabel = selectedCase
    ? `${selectedCase.year_from}-${selectedCase.year_to}`
    : "none"

  const handleApplyPreset = (presetDetectorIds: string[], preferredLens: LabCleaningLens) => {
    setSelectedDetectors(presetDetectorIds)
    if (availableLenses.includes(preferredLens)) {
      setLens(preferredLens)
    }
  }

  const handleReloadOutputs = () => {
    clearLabOutputCache()
    setReloadNonce((previous) => previous + 1)
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
    return (
      <div className="rounded-lg border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
        No lab cases found for this ticker yet.
      </div>
    )
  }

  return (
    <section className="space-y-6">
      <div className="rounded-lg border border-white/10 bg-white/5 p-4 text-sm text-slate-200">
        <h3 className="text-sm font-semibold text-slate-100">What am I looking at?</h3>
        <p className="mt-2 text-xs text-slate-300">
          This Lab compares adjacent years of 10-K risk text and surfaces what shifted, what stayed
          similar, and where detectors disagree. Start with the default deboilerplated lens for the
          cleanest signal, then switch lenses to inspect raw wording effects.
        </p>
        <p className="mt-2 text-xs text-slate-400">
          Looking for the method details?{" "}
          <a
            className="text-sky-300 underline decoration-sky-300/60 underline-offset-2"
            href={withBase("methodology")}
          >
            Open methodology
          </a>
          . LLM detector cards also include copy-ready rerun instructions.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-lg border border-white/10 bg-slate-900/50 p-3">
          <div className="text-[11px] uppercase tracking-wide text-slate-400">Selected pair</div>
          <div className="mt-1 text-sm font-semibold text-slate-100">{selectedPairLabel}</div>
        </div>
        <div className="rounded-lg border border-white/10 bg-slate-900/50 p-3">
          <div className="text-[11px] uppercase tracking-wide text-slate-400">Lens</div>
          <div className="mt-1 text-sm font-semibold text-slate-100">{lens}</div>
        </div>
        <div className="rounded-lg border border-white/10 bg-slate-900/50 p-3">
          <div className="text-[11px] uppercase tracking-wide text-slate-400">Methods selected</div>
          <div className="mt-1 text-sm font-semibold text-slate-100">{selectedDetectors.length}</div>
        </div>
        <div className="rounded-lg border border-white/10 bg-slate-900/50 p-3">
          <div className="text-[11px] uppercase tracking-wide text-slate-400">Selected methods available</div>
          <div className="mt-1 text-sm font-semibold text-slate-100">
            {selectedAvailableDetectorCount}/{selectedDetectors.length}
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[2fr,1fr]">
        <div className="space-y-4 rounded-lg border border-white/10 bg-white/5 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-xs uppercase tracking-wide text-slate-400">Case</div>
              <select
                value={selectedCaseKey ?? ""}
                onChange={(event) => setSelectedCaseKey(event.target.value)}
                className="mt-2 w-full rounded-md border border-white/15 bg-slate-950/40 px-3 py-2 text-sm text-slate-100"
              >
                {cases.map((item) => (
                  <option key={buildCaseKey(item)} value={buildCaseKey(item)}>
                    {item.year_from} - {item.year_to}
                  </option>
                ))}
              </select>
            </div>
            <div className="text-xs text-slate-400">
              {selectedCase ? selectedCase.why_interesting : ""}
            </div>
          </div>

          <div>
            <div className="text-xs uppercase tracking-wide text-slate-400">Cleaning lens</div>
            <div className="mt-2">
              <CleaningLensToggle value={lens} options={lensOptions} onChange={setLens} />
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <div className="text-xs uppercase tracking-wide text-slate-400">Model A (LLM)</div>
              <select
                value={selectedLlmCampaignA}
                onChange={(event) => setSelectedLlmCampaignA(event.target.value)}
                className="mt-2 w-full rounded-md border border-white/15 bg-slate-950/40 px-3 py-2 text-xs text-slate-100"
              >
                {llmCampaignOptions.map((campaign) => (
                  <option key={campaign.campaign_id} value={campaign.campaign_id}>
                    {campaign.display_name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-slate-400">Model B (LLM)</div>
              <select
                value={selectedLlmCampaignB}
                onChange={(event) => setSelectedLlmCampaignB(event.target.value)}
                className="mt-2 w-full rounded-md border border-white/15 bg-slate-950/40 px-3 py-2 text-xs text-slate-100"
              >
                {llmCampaignOptions.map((campaign) => (
                  <option key={campaign.campaign_id} value={campaign.campaign_id}>
                    {campaign.display_name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between gap-3">
              <div className="text-xs uppercase tracking-wide text-slate-400">Methods</div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleReloadOutputs}
                  disabled={!selectedCase || isLoadingOutputs}
                  className="rounded-md border border-white/15 bg-slate-900/50 px-2 py-1 text-[11px] text-slate-200 transition hover:border-white/35 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Reload outputs
                </button>
                <div className="text-[11px] text-slate-400">
                  Available outputs: {availableDetectorIds.length}/{DETECTOR_CATALOG.length}
                </div>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => handleApplyPreset(EXECUTIVE_READ_PRESET, "deboilerplated")}
                className="rounded-md border border-sky-300/30 bg-sky-400/10 px-2 py-1 text-[11px] text-sky-100 transition hover:border-sky-200/60"
              >
                30-second executive read
              </button>
              <button
                type="button"
                onClick={() => handleApplyPreset(TECHNICAL_DEEP_DIVE_PRESET, lens)}
                className="rounded-md border border-white/20 bg-slate-900/60 px-2 py-1 text-[11px] text-slate-100 transition hover:border-white/40"
              >
                Technical deep dive
              </button>
            </div>
            <div className="mt-3 space-y-3">
              {detectorGroups.map((group) => (
                <div key={group.id} className="rounded-md border border-white/10 bg-slate-950/30 p-3">
                  <div className="text-[11px] uppercase tracking-wide text-slate-400">{group.label}</div>
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
        </div>

        <div className="rounded-lg border border-white/10 bg-white/5 p-4">
          <div className="text-xs uppercase tracking-wide text-slate-400">Recommended cases</div>
          <div className="mt-3 space-y-2 text-xs text-slate-200">
            {recommendedCases.map((item) => {
              const key = buildCaseKey(item)
              const isActive = key === selectedCaseKey
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => setSelectedCaseKey(key)}
                  className={`w-full rounded-md border px-3 py-2 text-left transition ${
                    isActive
                      ? "border-sky-300/60 bg-sky-400/20 text-sky-100"
                      : "border-white/10 bg-slate-950/40 text-slate-200 hover:border-white/30"
                  }`}
                >
                  {item.ticker} {item.year_from} - {item.year_to}
                  <div className="mt-1 text-[11px] text-slate-400">{item.why_interesting}</div>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-100">Agreement</h3>
          <p className="text-xs text-slate-400">
            Rank-biased overlap across available ranked lists for this case.
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

      {llmCompareRows.length ? (
        <div className="rounded-xl border border-sky-300/25 bg-sky-400/10 p-4">
          <h3 className="text-sm font-semibold text-sky-100">LLM A/B quick diff</h3>
          <p className="mt-1 text-[11px] text-slate-200">
            Deltas are Model A minus Model B for the selected pair/lens.
          </p>
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-left text-[11px] text-slate-100">
              <thead className="text-slate-300">
                <tr>
                  <th className="pr-4">Detector</th>
                  <th className="pr-4">Confidence delta</th>
                  <th className="pr-4">Evidence delta</th>
                  <th className="pr-4">Citation delta</th>
                  <th>Evidence overlap</th>
                </tr>
              </thead>
              <tbody>
                {llmCompareRows.map((row) => (
                  <tr key={row.detectorId} className="border-t border-white/10">
                    <td className="py-1 pr-4">{row.detectorLabel}</td>
                    <td className="py-1 pr-4">
                      {row.confidenceDelta === null ? "-" : row.confidenceDelta.toFixed(2)}
                    </td>
                    <td className="py-1 pr-4">{row.evidenceDelta}</td>
                    <td className="py-1 pr-4">
                      {row.citationDelta === null ? "-" : row.citationDelta}
                    </td>
                    <td className="py-1">
                      {row.overlapPercent === null ? "-" : `${row.overlapPercent.toFixed(0)}%`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      <div className="grid gap-4">
        {methodCards.map((detector) => (
          <MethodCard
            key={detector.cardKey}
            detectorId={detector.id}
            title={
              detector.campaign
                ? `${detector.label} - ${detector.campaign.display_name}`
                : detector.label
            }
            description={detector.description}
            llmCampaign={
              detector.campaign
                ? {
                    campaignId: detector.campaign.campaign_id,
                    campaignDisplayName: detector.campaign.display_name,
                    modelProvider: detector.campaign.model_provider,
                    modelName: detector.campaign.model_name,
                    instructionsAsset: detector.campaign.instructions_asset,
                  }
                : null
            }
            output={outputs[detector.cardKey] ?? null}
            debugPath={outputDebugPaths[detector.cardKey] ?? null}
            debugInfo={outputDebugInfo[detector.cardKey] ?? null}
            isLoading={isLoadingOutputs}
            emptyMessage="No lab output for this detector/lens yet."
          />
        ))}
      </div>
    </section>
  )
}
