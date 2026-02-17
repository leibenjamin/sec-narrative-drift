import { useEffect, useMemo, useState } from "react"
import AgreementMatrix from "./AgreementMatrix"
import CleaningLensToggle from "./CleaningLensToggle"
import MethodCard from "./MethodCard"
import {
  clearLabOutputCache,
  formatLabLoadDebug,
  listLabCasesForTicker,
  loadLabOutput,
  resolveLabOutputLink,
} from "../lib/labData"
import type { LabCase, LabCleaningLens, LabOutput, LabSourceId } from "../lib/labTypes"

const DETECTOR_CATALOG = [
  {
    id: "det_logodds_terms_v1",
    label: "Log-odds terms",
    description: "Distinctive term shifts from the baseline log-odds detector.",
    defaultSelected: true,
  },
  {
    id: "det_jsd_ngrams_v1",
    label: "JSD n-grams",
    description: "Distributional drift using Jensen-Shannon divergence.",
    defaultSelected: true,
  },
  {
    id: "det_minhash_boilerplate_v1",
    label: "Minhash boilerplate",
    description: "Near-duplicate paragraph reuse estimates.",
    defaultSelected: true,
  },
  {
    id: "det_winnowing_fingerprint_v1",
    label: "Winnowing fingerprints",
    description: "Shared fingerprint spans between years.",
    defaultSelected: false,
  },
  {
    id: "det_structure_artifacts_v1",
    label: "Structure artifacts",
    description: "Heading and length changes across years.",
    defaultSelected: true,
  },
  {
    id: "det_llm_delta_brief_v1",
    label: "LLM delta brief (precomputed)",
    description: "Precomputed narrative summary.",
    defaultSelected: false,
  },
  {
    id: "det_llm_excerpt_picker_v1",
    label: "LLM excerpt picker (precomputed)",
    description: "Precomputed excerpt selection.",
    defaultSelected: false,
  },
]

const DEFAULT_SELECTED = DETECTOR_CATALOG.filter((det) => det.defaultSelected).map(
  (det) => det.id
)
const LENS_PREFERENCE_ORDER: LabCleaningLens[] = [
  "deboilerplated",
  "raw",
  "stage1_clean",
  "structure_aware",
]

function buildCaseKey(caseItem: LabCase): string {
  return `${caseItem.year_from}-${caseItem.year_to}`
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

export default function LabPanel({ ticker }: { ticker: string }) {
  const [cases, setCases] = useState<LabCase[]>([])
  const [isLoadingCases, setIsLoadingCases] = useState(true)
  const [caseError, setCaseError] = useState<string | null>(null)
  const [caseDebugPath, setCaseDebugPath] = useState<string | null>(null)
  const [selectedCaseKey, setSelectedCaseKey] = useState<string | null>(null)
  const [lens, setLens] = useState<LabCleaningLens>("deboilerplated")
  const [selectedDetectors, setSelectedDetectors] = useState<string[]>(DEFAULT_SELECTED)
  const [outputs, setOutputs] = useState<Record<string, LabOutput | null>>({})
  const [outputDebugPaths, setOutputDebugPaths] = useState<Record<string, string | null>>({})
  const [agreementOutput, setAgreementOutput] = useState<LabOutput | null>(null)
  const [agreementDebugPath, setAgreementDebugPath] = useState<string | null>(null)
  const [isLoadingOutputs, setIsLoadingOutputs] = useState(false)
  const [reloadNonce, setReloadNonce] = useState(0)

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

  const selectedCase = useMemo(() => {
    if (!selectedCaseKey) return null
    return cases.find((item) => buildCaseKey(item) === selectedCaseKey) ?? null
  }, [cases, selectedCaseKey])

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

  // Keep selected detectors in sync when case/lens availability changes.
  const detectorSyncKey = selectedCase
    ? `${buildCaseKey(selectedCase)}|${lens}|${availableDetectorIds.join(",")}`
    : null
  const [prevDetectorSyncKey, setPrevDetectorSyncKey] = useState(detectorSyncKey)
  if (prevDetectorSyncKey !== detectorSyncKey) {
    setPrevDetectorSyncKey(detectorSyncKey)
    if (selectedCase) {
      setSelectedDetectors((prev) => {
        const filtered = prev.filter((detectorId) => availableDetectorSet.has(detectorId))
        const defaults = DEFAULT_SELECTED.filter((detectorId) =>
          availableDetectorSet.has(detectorId)
        )
        const next = filtered.length ? filtered : defaults
        if (next.length === prev.length && next.every((item, idx) => item === prev[idx])) {
          return prev
        }
        return next
      })
    }
  }

  // Adjust lens during render when available lenses change (avoids sync setState in effect)
  if (availableLenses.length && !availableLenses.includes(lens)) {
    const nextLens = pickPreferredAvailableLens(availableLenses)
    if (nextLens) {
      setLens(nextLens)
    }
  }

  // Build a key to track when output-loading dependencies change
  const outputRequestKey = selectedCase
    ? `${buildCaseKey(selectedCase)}|${lens}|${selectedDetectors.join(",")}|reload:${reloadNonce}`
    : null
  const [prevOutputRequestKey, setPrevOutputRequestKey] = useState(outputRequestKey)

  // Adjust outputs state during render when dependencies change (avoids sync setState in effect)
  if (prevOutputRequestKey !== outputRequestKey) {
    setPrevOutputRequestKey(outputRequestKey)
    if (!outputRequestKey) {
      setOutputs({})
      setOutputDebugPaths({})
      setAgreementOutput(null)
      setAgreementDebugPath(null)
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

      for (const detectorId of selectedDetectors) {
        const link = resolveLabOutputLink(selectedCase, detectorId, lens, sourceId)
        if (!link) {
          nextOutputs[detectorId] = null
          nextOutputDebugPaths[detectorId] = null
          continue
        }
        try {
          const output = await loadLabOutput(selectedCase.ticker, link.filename, {
            signal: controller.signal,
          })
          nextOutputs[detectorId] = output
          nextOutputDebugPaths[detectorId] = null
        } catch (error) {
          nextOutputs[detectorId] = null
          nextOutputDebugPaths[detectorId] = formatLabLoadDebug(error)
        }
      }

      const agreementLink = resolveLabOutputLink(
        selectedCase,
        "det_rbo_agreement_v1",
        lens,
        sourceId
      )
      let agreement: LabOutput | null = null
      let nextAgreementDebugPath: string | null = null
      if (agreementLink) {
        try {
          agreement = await loadLabOutput(selectedCase.ticker, agreementLink.filename, {
            signal: controller.signal,
          })
          nextAgreementDebugPath = null
        } catch (error) {
          agreement = null
          nextAgreementDebugPath = formatLabLoadDebug(error)
        }
      }

      if (!cancelled) {
        setOutputs(nextOutputs)
        setOutputDebugPaths(nextOutputDebugPaths)
        setAgreementOutput(agreement)
        setAgreementDebugPath(nextAgreementDebugPath)
        setIsLoadingOutputs(false)
      }
    }

    void load()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [selectedCase, lens, selectedDetectors, sourceId])

  const lensOptions = useMemo(() => {
    const base: LabCleaningLens[] = ["raw", "deboilerplated", "stage1_clean", "structure_aware"]
    return base.map((value) => ({
      value,
      disabled: !availableLenses.includes(value),
    }))
  }, [availableLenses])

  const methodCards = useMemo(() => {
    const selected = new Set(selectedDetectors)
    return DETECTOR_CATALOG.filter((det) => selected.has(det.id))
  }, [selectedDetectors])

  const handleReloadOutputs = () => {
    clearLabOutputCache()
    setReloadNonce((previous) => previous + 1)
  }

  if (isLoadingCases) {
    return <p className="text-sm text-slate-300">Loading lab cases?</p>
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
            <div className="mt-2 flex flex-wrap gap-3">
              {DETECTOR_CATALOG.map((detector) => {
                const isAvailable = availableDetectorSet.has(detector.id)
                const isSelected = isAvailable && selectedDetectors.includes(detector.id)
                return (
                  <label
                    key={detector.id}
                    className={`flex items-center gap-2 rounded-full border px-3 py-1 text-xs ${
                      isAvailable
                        ? "border-white/10 bg-white/5 text-slate-200"
                        : "cursor-not-allowed border-white/10 bg-slate-900/40 text-slate-500"
                    }`}
                  >
                    <input
                      type="checkbox"
                      className="h-3 w-3"
                      disabled={!isAvailable}
                      checked={isSelected}
                      onChange={() => {
                        if (!isAvailable) return
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
                      {!isAvailable ? " (not available for this case)" : ""}
                    </span>
                  </label>
                )
              })}
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
        {!agreementOutput && agreementDebugPath ? (
          <p className="break-all text-[11px] text-slate-500">{agreementDebugPath}</p>
        ) : null}
      </div>

      <div className="grid gap-4">
        {methodCards.map((detector) => (
          <MethodCard
            key={detector.id}
            title={detector.label}
            description={detector.description}
            output={outputs[detector.id] ?? null}
            debugPath={outputDebugPaths[detector.id] ?? null}
            isLoading={isLoadingOutputs}
            emptyMessage="No lab output for this detector/lens yet."
          />
        ))}
      </div>
    </section>
  )
}
