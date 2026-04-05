import { useEffect, useMemo, useState } from "react"
import {
  LabDataLoadError,
  buildExpectedLabOutputArtifact,
  buildLabOutputRepoPath,
  buildLabOutputRequestUrl,
  clearLabOutputCache,
  findLabOutlineCompareArtifactForCampaign,
  findLabOutlineCompareInsightArtifactForCampaign,
  findLabOutlineCompareStructuredArtifactForCampaign,
  formatLabLoadDebug,
  getDefaultDeterministicTrackSlug,
  loadLabOutlineCompareInsightOutput,
  loadLabOutlineCompareOutput,
  loadLabOutlineCompareStructuredOutput,
  loadLabOutput,
  resolveLabOutputLink,
} from "../lib/labData"
import type {
  LabCase,
  LabCleaningLens,
  LabOutlineCompareInsightOutput,
  LabOutlineCompareOutput,
  LabOutlineCompareV2Output,
  LabOutput,
  LabSourceId,
} from "../lib/labTypes"

const DET_TRACK_SLUG = getDefaultDeterministicTrackSlug()

function buildDetectorCardKey(detectorId: string): string {
  return detectorId
}

function buildOutputRequestKey(props: {
  selectedCase: LabCase | null
  lens: LabCleaningLens
  selectedDetectors: string[]
  selectedLlmCampaignA: string
  selectedLlmCampaignB: string
  reloadNonce: number
}): string | null {
  const { selectedCase, lens, selectedDetectors, selectedLlmCampaignA, selectedLlmCampaignB, reloadNonce } =
    props
  if (!selectedCase) return null
  return `${selectedCase.ticker}|${selectedCase.year_from}-${selectedCase.year_to}|${lens}|${selectedDetectors.join(",")}|${selectedLlmCampaignA}|${selectedLlmCampaignB}|reload:${reloadNonce}`
}

export type LabPanelDetectorDebugInfo = {
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

export type LabPanelOutlineArtifactDebugInfo = {
  expectedPath: string | null
  requestedUrl: string | null
  errorText: string | null
}

export type LabPanelOutputsState = {
  outputs: Record<string, LabOutput | null>
  outputDebugPaths: Record<string, string | null>
  outputDebugInfo: Record<string, LabPanelDetectorDebugInfo>
  agreementOutput: LabOutput | null
  agreementDebugPath: string | null
  agreementDebugInfo: LabPanelDetectorDebugInfo | null
  isLoadingOutputs: boolean
  outlineOutputs: Record<string, LabOutlineCompareOutput | null>
  outlineDebugPaths: Record<string, string | null>
  outlineDebugInfo: Record<string, LabPanelOutlineArtifactDebugInfo>
  structuredOutlineOutputs: Record<string, LabOutlineCompareV2Output | null>
  structuredOutlineDebugPaths: Record<string, string | null>
  structuredOutlineDebugInfo: Record<string, LabPanelOutlineArtifactDebugInfo>
  insightOutputs: Record<string, LabOutlineCompareInsightOutput | null>
  insightDebugPaths: Record<string, string | null>
  insightDebugInfo: Record<string, LabPanelOutlineArtifactDebugInfo>
  reloadOutputs: () => void
}

type UseLabPanelOutputsProps = {
  selectedCase: LabCase | null
  lens: LabCleaningLens
  selectedDetectors: string[]
  sourceId: LabSourceId
  selectedLlmCampaignA: string
  selectedLlmCampaignB: string
}

export default function useLabPanelOutputs(
  props: UseLabPanelOutputsProps
): LabPanelOutputsState {
  const { selectedCase, lens, selectedDetectors, sourceId, selectedLlmCampaignA, selectedLlmCampaignB } =
    props
  const [outputs, setOutputs] = useState<Record<string, LabOutput | null>>({})
  const [outputDebugPaths, setOutputDebugPaths] = useState<Record<string, string | null>>({})
  const [outputDebugInfo, setOutputDebugInfo] = useState<Record<string, LabPanelDetectorDebugInfo>>({})
  const [agreementOutput, setAgreementOutput] = useState<LabOutput | null>(null)
  const [agreementDebugPath, setAgreementDebugPath] = useState<string | null>(null)
  const [agreementDebugInfo, setAgreementDebugInfo] = useState<LabPanelDetectorDebugInfo | null>(null)
  const [isLoadingOutputs, setIsLoadingOutputs] = useState(false)
  const [outlineOutputs, setOutlineOutputs] = useState<Record<string, LabOutlineCompareOutput | null>>({})
  const [outlineDebugPaths, setOutlineDebugPaths] = useState<Record<string, string | null>>({})
  const [outlineDebugInfo, setOutlineDebugInfo] = useState<Record<string, LabPanelOutlineArtifactDebugInfo>>(
    {}
  )
  const [structuredOutlineOutputs, setStructuredOutlineOutputs] = useState<
    Record<string, LabOutlineCompareV2Output | null>
  >({})
  const [structuredOutlineDebugPaths, setStructuredOutlineDebugPaths] = useState<
    Record<string, string | null>
  >({})
  const [structuredOutlineDebugInfo, setStructuredOutlineDebugInfo] = useState<
    Record<string, LabPanelOutlineArtifactDebugInfo>
  >({})
  const [insightOutputs, setInsightOutputs] = useState<Record<string, LabOutlineCompareInsightOutput | null>>(
    {}
  )
  const [insightDebugPaths, setInsightDebugPaths] = useState<Record<string, string | null>>({})
  const [insightDebugInfo, setInsightDebugInfo] = useState<Record<string, LabPanelOutlineArtifactDebugInfo>>(
    {}
  )
  const [reloadNonce, setReloadNonce] = useState(0)
  const outputRequestKey = useMemo(
    () =>
      buildOutputRequestKey({
        selectedCase,
        lens,
        selectedDetectors,
        selectedLlmCampaignA,
        selectedLlmCampaignB,
        reloadNonce,
      }),
    [lens, reloadNonce, selectedCase, selectedDetectors, selectedLlmCampaignA, selectedLlmCampaignB]
  )
  const [prevOutputRequestKey, setPrevOutputRequestKey] = useState(outputRequestKey)

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
      setIsLoadingOutputs(false)
    } else {
      setIsLoadingOutputs(true)
    }
  }

  useEffect(() => {
    if (!selectedCase) return

    let cancelled = false
    const controller = new AbortController()

    const load = async () => {
      const nextOutputs: Record<string, LabOutput | null> = {}
      const nextOutputDebugPaths: Record<string, string | null> = {}
      const nextOutputDebugInfo: Record<string, LabPanelDetectorDebugInfo> = {}
      const nextOutlineOutputs: Record<string, LabOutlineCompareOutput | null> = {}
      const nextOutlineDebugPaths: Record<string, string | null> = {}
      const nextOutlineDebugInfo: Record<string, LabPanelOutlineArtifactDebugInfo> = {}
      const nextStructuredOutlineOutputs: Record<string, LabOutlineCompareV2Output | null> = {}
      const nextStructuredOutlineDebugPaths: Record<string, string | null> = {}
      const nextStructuredOutlineDebugInfo: Record<string, LabPanelOutlineArtifactDebugInfo> = {}
      const nextInsightOutputs: Record<string, LabOutlineCompareInsightOutput | null> = {}
      const nextInsightDebugPaths: Record<string, string | null> = {}
      const nextInsightDebugInfo: Record<string, LabPanelOutlineArtifactDebugInfo> = {}

      for (const detectorId of selectedDetectors) {
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
            "Optional insight sidecar is not published for this compare lane."
          nextInsightDebugInfo[campaignId] = {
            expectedPath: null,
            requestedUrl: null,
            errorText: "Optional insight sidecar not available for this case/lens/campaign.",
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
      const agreementLink = resolveLabOutputLink(selectedCase, "det_rbo_agreement_v1", lens, sourceId)
      let nextAgreementOutput: LabOutput | null = null
      let nextAgreementDebugPath: string | null = null
      let nextAgreementDebugInfo: LabPanelDetectorDebugInfo | null = null

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
          nextAgreementOutput = await loadLabOutput(selectedCase.ticker, agreementLink.filename, {
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
          nextAgreementOutput = null
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
        nextAgreementOutput = null
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
        setAgreementOutput(nextAgreementOutput)
        setAgreementDebugPath(nextAgreementDebugPath)
        setAgreementDebugInfo(nextAgreementDebugInfo)
        setIsLoadingOutputs(false)
      }
    }

    void load()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [
    lens,
    outputRequestKey,
    selectedCase,
    selectedDetectors,
    selectedLlmCampaignA,
    selectedLlmCampaignB,
    sourceId,
  ])

  return {
    outputs,
    outputDebugPaths,
    outputDebugInfo,
    agreementOutput,
    agreementDebugPath,
    agreementDebugInfo,
    isLoadingOutputs,
    outlineOutputs,
    outlineDebugPaths,
    outlineDebugInfo,
    structuredOutlineOutputs,
    structuredOutlineDebugPaths,
    structuredOutlineDebugInfo,
    insightOutputs,
    insightDebugPaths,
    insightDebugInfo,
    reloadOutputs: () => {
      clearLabOutputCache()
      setReloadNonce((previous) => previous + 1)
    },
  }
}
