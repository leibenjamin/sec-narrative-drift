import { useEffect, useMemo, useState } from "react"
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
  ProtocolLabEffortRobustnessBundle,
  ProtocolLabNoveltyLedgerCase,
  ProtocolLabPilotMatrixBundle,
  ProtocolLabSkepticCaseCanonizedMatrix,
} from "../lib/protocolLabMatrixTypes.ts"

export type LabPanelPilotMatrixTarget =
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

export type LabPanelPilotArtifactsState = {
  pilotMatrixBundle: ProtocolLabPilotMatrixBundle | null
  isLoadingPilotMatrix: boolean
  pilotMatrixError: string | null
  pilotMatrixDebugText: string | null
  effortRobustnessBundle: ProtocolLabEffortRobustnessBundle | null
  isLoadingEffortRobustness: boolean
  effortRobustnessError: string | null
  effortRobustnessDebugText: string | null
  noveltyLedgerArtifact: ProtocolLabNoveltyLedgerCase | null
  isLoadingNoveltyLedger: boolean
  noveltyLedgerError: string | null
  noveltyLedgerDebugText: string | null
  skepticCaseArtifact: ProtocolLabSkepticCaseCanonizedMatrix | null
  isLoadingSkepticCase: boolean
  skepticCaseError: string | null
  skepticCaseDebugText: string | null
}

function buildPilotMatrixRequestKey(target: LabPanelPilotMatrixTarget | null): string | null {
  if (!target) return null
  if (target.mode === "case") {
    return `${target.ticker}:${target.yearFrom}-${target.yearTo}`
  }
  return `${target.ticker}:pilot_only`
}

export default function useLabPanelPilotArtifacts(
  pilotMatrixTarget: LabPanelPilotMatrixTarget | null
): LabPanelPilotArtifactsState {
  const [pilotMatrixBundle, setPilotMatrixBundle] = useState<ProtocolLabPilotMatrixBundle | null>(null)
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
  const requestKey = useMemo(
    () => buildPilotMatrixRequestKey(pilotMatrixTarget),
    [pilotMatrixTarget]
  )
  const [prevRequestKey, setPrevRequestKey] = useState(requestKey)

  if (prevRequestKey !== requestKey) {
    setPrevRequestKey(requestKey)
    if (!requestKey) {
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
    if (!pilotMatrixTarget) return

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
    if (!pilotMatrixTarget) return

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
    if (!pilotMatrixTarget) return

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
    if (!pilotMatrixTarget) return

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

  return {
    pilotMatrixBundle,
    isLoadingPilotMatrix,
    pilotMatrixError,
    pilotMatrixDebugText,
    effortRobustnessBundle,
    isLoadingEffortRobustness,
    effortRobustnessError,
    effortRobustnessDebugText,
    noveltyLedgerArtifact,
    isLoadingNoveltyLedger,
    noveltyLedgerError,
    noveltyLedgerDebugText,
    skepticCaseArtifact,
    isLoadingSkepticCase,
    skepticCaseError,
    skepticCaseDebugText,
  }
}
