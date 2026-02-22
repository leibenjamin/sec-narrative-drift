import { useEffect, useMemo, useState } from "react"
import EvidenceStack from "./EvidenceStack"
import LabExcerptPickerPanel from "./LabExcerptPickerPanel"
import {
  buildDefaultLlmInputFile,
  buildLlmThreadStarterText,
  isLlmDetector,
  loadLlmProjectInstructionsText,
} from "../lib/labLlmRepro"
import { withBase } from "../lib/paths"
import type {
  LabCleaningLens,
  LabMethodProfile,
  LabOutput,
  RankedItem,
} from "../lib/labTypes"

const EMPTY_ITEMS: RankedItem[] = []

type AnalysisMode = "executive" | "deep"
type SignalTier = "high" | "medium" | "low" | "insufficient"

type SignalSummary = {
  tier: SignalTier
  summary: string
  reason: string
  nextAction: string
}

type MethodCardProps = {
  detectorId: string
  title: string
  description?: string
  output: LabOutput | null
  llmCampaign?: {
    campaignId: string
    campaignDisplayName: string
    modelProvider: string
    modelName: string
    instructionsAsset?: string
  } | null
  methodProfile?: LabMethodProfile | null
  analysisMode?: AnalysisMode
  autoOpenContext?: boolean
  isLoading?: boolean
  isExpanded?: boolean
  onToggleExpanded?: () => void
  emptyMessage?: string
  debugPath?: string | null
  debugInfo?: {
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
  } | null
}

function normalizeRankedList(raw: unknown): RankedItem[] {
  if (!Array.isArray(raw)) return EMPTY_ITEMS
  const items: RankedItem[] = []
  for (const entry of raw) {
    if (!entry || typeof entry !== "object") continue
    const record = entry as RankedItem
    if (typeof record.label === "string" && typeof record.score === "number") {
      items.push(record)
    }
  }
  return items
}

function formatMetric(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "-"
  return value.toFixed(3)
}

function classifySignal(output: LabOutput | null): SignalSummary {
  if (!output) {
    return {
      tier: "insufficient",
      summary: "No detector payload loaded.",
      reason: "This card has no output artifact yet.",
      nextAction: "Use the expected path and debug payload to recover the missing artifact first.",
    }
  }

  const evidenceCount = output.evidence.length
  const warningsCount = output.metrics.warnings.length
  const confidence = output.metrics.confidence
  const coverage = output.metrics.coverage
  const drift = output.metrics.drift_score

  if (evidenceCount < 2 || confidence === null || coverage === null || drift === null) {
    return {
      tier: "insufficient",
      summary: "Signal is insufficient for strong interpretation.",
      reason:
        "One or more core diagnostics are missing or too thin (evidence, confidence, coverage, or drift).",
      nextAction: "Cross-check agreement plus at least two core deterministic cards before concluding.",
    }
  }

  if (
    confidence >= 0.75 &&
    coverage >= 0.75 &&
    warningsCount === 0 &&
    evidenceCount >= 4 &&
    drift >= 0.2
  ) {
    return {
      tier: "high",
      summary: "Signal looks strong for this detector.",
      reason: "Confidence, coverage, evidence volume, and warning profile are all supportive.",
      nextAction: "Validate with agreement and one orthogonal method before final interpretation.",
    }
  }

  if (confidence < 0.45 || coverage < 0.45 || warningsCount >= 2 || evidenceCount < 3) {
    return {
      tier: "low",
      summary: "Signal is weak and easy to over-read.",
      reason:
        "At least one quality indicator is weak (confidence, coverage, warning load, or sparse evidence).",
      nextAction: "Treat as directional only and prioritize JSD/log-odds plus agreement cross-checks.",
    }
  }

  return {
    tier: "medium",
    summary: "Signal is usable with caveats.",
    reason: "Metrics are acceptable but not uniformly strong across all quality checks.",
    nextAction: "Use this card with structure/reuse context before drawing a durable conclusion.",
  }
}

function buildWeaknessReason(output: LabOutput | null): string {
  if (!output) {
    return "No output is loaded, so no evidence-level interpretation is possible."
  }

  const weakness: string[] = []
  const confidence = output.metrics.confidence
  const coverage = output.metrics.coverage
  const warningsCount = output.metrics.warnings.length
  const evidenceCount = output.evidence.length

  if (warningsCount > 0) weakness.push(`warnings present (${warningsCount})`)
  if (confidence !== null && confidence < 0.6) weakness.push(`confidence is ${confidence.toFixed(2)}`)
  if (coverage !== null && coverage < 0.6) weakness.push(`coverage is ${coverage.toFixed(2)}`)
  if (evidenceCount < 4) weakness.push(`limited evidence blocks (${evidenceCount})`)

  if (weakness.length === 0) {
    return "Even strong detector metrics can miss cross-method disagreement or structure-driven artifacts."
  }
  return `${weakness.join("; ")}.`
}

function buildDecisionSentence(signalSummary: SignalSummary): string {
  return `Interpretation: ${signalSummary.summary} ${signalSummary.nextAction}`
}

function signalTierClasses(tier: SignalTier): string {
  if (tier === "high") return "border-emerald-300/25 bg-emerald-400/10 text-emerald-100"
  if (tier === "medium") return "border-sky-300/25 bg-sky-400/10 text-sky-100"
  if (tier === "low") return "border-amber-300/30 bg-amber-400/10 text-amber-100"
  return "border-rose-300/35 bg-rose-400/10 text-rose-100"
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

export default function MethodCard({
  detectorId,
  title,
  description,
  output,
  llmCampaign = null,
  methodProfile = null,
  analysisMode = "executive",
  autoOpenContext = false,
  isLoading,
  isExpanded = true,
  onToggleExpanded,
  emptyMessage,
  debugPath,
  debugInfo,
}: MethodCardProps) {
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle")
  const [copyStarterState, setCopyStarterState] = useState<"idle" | "copied" | "failed">("idle")
  const [copyInstructionsState, setCopyInstructionsState] = useState<"idle" | "copied" | "failed">(
    "idle"
  )
  const [projectInstructions, setProjectInstructions] = useState<string>("")
  const [projectInstructionsError, setProjectInstructionsError] = useState<string | null>(null)
  const [contextPreference, setContextPreference] = useState<"auto" | "open" | "closed">("auto")
  const [diagnosticsPreference, setDiagnosticsPreference] = useState<"auto" | "open" | "closed">(
    "auto"
  )

  const warnings = output?.metrics.warnings ?? []
  const rankedItems = normalizeRankedList(output?.artifacts.ranked_items)
  const topRisers = normalizeRankedList(output?.artifacts.top_risers)
  const topFallers = normalizeRankedList(output?.artifacts.top_fallers)
  const llmCard = isLlmDetector(detectorId)
  const isExcerptPicker = output?.detector_id === "det_llm_excerpt_picker_v1"
  const isDeltaBrief = output?.detector_id === "det_llm_delta_brief_v1"
  const signalSummary = useMemo(() => classifySignal(output), [output])
  const weaknessReason = useMemo(() => buildWeaknessReason(output), [output])
  const decisionSentence = useMemo(() => buildDecisionSentence(signalSummary), [signalSummary])

  const deltaBriefRaw = isDeltaBrief ? output?.artifacts.delta_brief : null
  const deltaBriefText =
    typeof deltaBriefRaw === "string"
      ? deltaBriefRaw.trim()
      : deltaBriefRaw
        ? JSON.stringify(deltaBriefRaw, null, 2)
        : ""
  const provenance = output?.provenance as Record<string, unknown> | undefined
  const modelProvider =
    typeof provenance?.model_provider === "string" ? provenance.model_provider : null
  const modelName = typeof provenance?.model_name === "string" ? provenance.model_name : null
  const runLabel = typeof provenance?.run_label === "string" ? provenance.run_label : null
  const runDate =
    runLabel && /^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])_/.test(runLabel)
      ? runLabel.slice(0, 10)
      : null
  const fallbackInputFile = debugInfo
    ? buildDefaultLlmInputFile(
        debugInfo.ticker,
        debugInfo.yearFrom,
        debugInfo.yearTo,
        debugInfo.lens
      )
    : null
  const inputFileForRerun =
    typeof provenance?.input_file === "string" && provenance.input_file
      ? provenance.input_file
      : fallbackInputFile
  const threadStarterText = useMemo(() => {
    if (!llmCard || !debugInfo || !inputFileForRerun || !llmCampaign) return null
    return buildLlmThreadStarterText({
      ticker: debugInfo.ticker,
      yearFrom: debugInfo.yearFrom,
      yearTo: debugInfo.yearTo,
      detectorId: debugInfo.detectorId || detectorId,
      lens: debugInfo.lens,
      campaignId: llmCampaign.campaignId,
      campaignDisplayName: llmCampaign.campaignDisplayName,
      modelProvider: llmCampaign.modelProvider,
      modelName: llmCampaign.modelName,
      inputFile: inputFileForRerun,
      expectedOutputPath: debugInfo.expectedPath ?? null,
      runLabelTemplate: "YYYY-MM-DD_<campaign_tag>",
      sourceId: output?.source_id ?? "edgar",
    })
  }, [llmCard, debugInfo, inputFileForRerun, llmCampaign, detectorId, output?.source_id])

  useEffect(() => {
    if (!llmCard) return
    let cancelled = false
    loadLlmProjectInstructionsText(llmCampaign?.instructionsAsset)
      .then((text) => {
        if (!cancelled) {
          setProjectInstructions(text)
          setProjectInstructionsError(null)
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setProjectInstructions("")
          setProjectInstructionsError(error instanceof Error ? error.message : "Failed to load.")
        }
      })
    return () => {
      cancelled = true
    }
  }, [llmCard, llmCampaign?.instructionsAsset])

  const handleCopyDebug = async () => {
    if (!debugInfo) return
    const payload = {
      ticker: debugInfo.ticker,
      pair: `${debugInfo.yearFrom}-${debugInfo.yearTo}`,
      lens: debugInfo.lens,
      detector: debugInfo.detectorId || detectorId,
      campaign_id: debugInfo.campaignId ?? null,
      campaign_display_name: debugInfo.campaignDisplayName ?? null,
      expected_path: debugInfo.expectedPath,
      requested_url: debugInfo.requestedUrl,
      error: debugInfo.errorText,
      schema_issue_or_debug: debugPath ?? null,
    }
    const didCopy = await copyTextToClipboard(JSON.stringify(payload, null, 2))
    setCopyState(didCopy ? "copied" : "failed")
  }

  const handleCopyThreadStarter = async () => {
    if (!threadStarterText) return
    const didCopy = await copyTextToClipboard(threadStarterText)
    setCopyStarterState(didCopy ? "copied" : "failed")
  }

  const handleCopyProjectInstructions = async () => {
    if (!projectInstructions) return
    const didCopy = await copyTextToClipboard(projectInstructions)
    setCopyInstructionsState(didCopy ? "copied" : "failed")
  }

  const shouldShowSignalBanner =
    !!output && (analysisMode === "deep" || signalSummary.tier === "low" || signalSummary.tier === "insufficient")
  const isContextOpen =
    contextPreference === "open" ||
    (contextPreference === "auto" && analysisMode === "deep" && autoOpenContext)
  const defaultDiagnosticsOpen =
    analysisMode !== "deep" ||
    signalSummary.tier === "low" ||
    signalSummary.tier === "insufficient"
  const isDiagnosticsOpen =
    diagnosticsPreference === "auto"
      ? defaultDiagnosticsOpen
      : diagnosticsPreference === "open"

  const handleToggleContext = () => {
    if (isContextOpen) {
      setContextPreference("closed")
    } else {
      setContextPreference("open")
    }
  }

  const handleToggleDiagnostics = () => {
    if (isDiagnosticsOpen) {
      setDiagnosticsPreference("closed")
    } else {
      setDiagnosticsPreference("open")
    }
  }

  return (
    <section className="rounded-xl border border-white/10 bg-slate-950/40 p-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-100">{title}</h3>
          {description ? <p className="text-sm text-slate-300">{description}</p> : null}
          <p className="mt-2 text-sm text-slate-200">{decisionSentence}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm text-slate-300">
          <span>drift {formatMetric(output?.metrics.drift_score)}</span>
          <span>confidence {formatMetric(output?.metrics.confidence)}</span>
          <span>coverage {formatMetric(output?.metrics.coverage)}</span>
          <button
            type="button"
            onClick={handleToggleContext}
            className="rounded-md border border-white/20 bg-slate-900/60 px-2 py-1 text-xs text-slate-100 transition hover:border-white/40"
          >
            {isContextOpen ? "Hide method context" : "Method context"}
          </button>
          {onToggleExpanded ? (
            <button
              type="button"
              onClick={onToggleExpanded}
              className="rounded-md border border-white/20 bg-slate-900/60 px-2 py-1 text-xs text-slate-100 transition hover:border-white/40"
            >
              {isExpanded ? "Collapse" : "Expand"}
            </button>
          ) : null}
        </div>
      </header>

      {!isExpanded ? (
        <div className="mt-3 rounded-md border border-white/10 bg-slate-900/35 p-3">
          {isLoading ? (
            <p className="text-xs text-slate-300">Loading detector output...</p>
          ) : !output ? (
            <p className="text-xs text-amber-200">
              Missing artifact. Expand for expected path, requested URL, and copyable debug details.
            </p>
          ) : (
            <p className="text-xs text-slate-300">
              Collapsed. Signal: {signalSummary.summary} Expand to inspect evidence, caveats, and context.
            </p>
          )}
        </div>
      ) : null}

      {isExpanded ? (
        <>
          {isLoading ? (
            <p className="mt-3 text-xs text-slate-400">Loading detector output...</p>
          ) : null}

          {!isLoading && !output ? (
            <div className="mt-3 space-y-2 rounded-md border border-amber-400/30 bg-amber-400/10 p-3">
              <p className="text-xs font-semibold text-amber-100">Missing artifact</p>
              <p className="text-xs text-slate-200">{emptyMessage ?? "No lab output yet."}</p>
              {debugInfo?.expectedPath ? (
                <p className="break-all text-xs text-slate-200">
                  Expected path: <span className="text-slate-100">{debugInfo.expectedPath}</span>
                </p>
              ) : null}
              {debugInfo?.requestedUrl ? (
                <p className="break-all text-xs text-slate-300">
                  Requested URL: <span className="text-slate-100">{debugInfo.requestedUrl}</span>
                </p>
              ) : null}
              {debugInfo?.errorText ? (
                <p className="text-xs text-amber-100">{debugInfo.errorText}</p>
              ) : null}
              {debugPath ? <p className="break-all text-xs text-slate-300">{debugPath}</p> : null}
              {debugInfo ? (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleCopyDebug}
                    className="rounded-md border border-white/20 bg-slate-900/60 px-2 py-1 text-xs text-slate-100 transition hover:border-white/40"
                  >
                    Copy debug info
                  </button>
                  {copyState === "copied" ? (
                    <span className="text-xs text-emerald-300">Copied.</span>
                  ) : null}
                  {copyState === "failed" ? (
                    <span className="text-xs text-rose-300">Copy failed.</span>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}

          <div id={`method-context-${detectorId}`} className="mt-3 rounded-md border border-white/10 bg-slate-900/35 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-200">
                Method context
              </h4>
              <a
                href={withBase(`methodology#detector-${detectorId}`)}
                className="text-xs text-sky-300 underline decoration-sky-300/60 underline-offset-2"
              >
                Methodology anchor
              </a>
            </div>
            {isContextOpen ? (
              methodProfile ? (
                <div className="mt-3 space-y-3 text-xs text-slate-200">
                  <div>
                    <div className="font-semibold text-slate-100">What this method is</div>
                    <p className="mt-1 text-slate-300">{methodProfile.short_purpose}</p>
                  </div>
                  <div>
                    <div className="font-semibold text-slate-100">How this lab implements it</div>
                    <p className="mt-1 text-slate-300">{methodProfile.this_app_deviation}</p>
                  </div>
                  <div>
                    <div className="font-semibold text-slate-100">When it works well</div>
                    <p className="mt-1 text-slate-300">{methodProfile.when_it_works_well}</p>
                  </div>
                  <div>
                    <div className="font-semibold text-slate-100">Typical failure modes</div>
                    <ul className="mt-1 list-disc space-y-1 pl-4 text-slate-300">
                      {methodProfile.failure_modes.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <div className="font-semibold text-slate-100">Why this method is included</div>
                    <p className="mt-1 text-slate-300">{methodProfile.why_included_here}</p>
                  </div>
                  <div>
                    <div className="font-semibold text-slate-100">Alternatives considered</div>
                    <ul className="mt-1 list-disc space-y-1 pl-4 text-slate-300">
                      {methodProfile.alternatives_not_chosen.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <div className="font-semibold text-slate-100">Current industry usage</div>
                    <p className="mt-1 text-slate-300">{methodProfile.current_industry_usage}</p>
                  </div>
                  {methodProfile.origin_claims.length ? (
                    <div>
                      <div className="font-semibold text-slate-100">Origins and references</div>
                      <ul className="mt-1 space-y-2 text-slate-300">
                        {methodProfile.origin_claims.map((claim) => (
                          <li key={`${claim.title}:${claim.year}`}>
                            <div className="font-medium text-slate-200">
                              {claim.title} ({claim.year})
                            </div>
                            <div>{claim.author_or_org}</div>
                            <a
                              href={claim.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-sky-300 underline decoration-sky-300/60 underline-offset-2"
                            >
                              Source
                            </a>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              ) : (
                <p className="mt-2 text-xs text-slate-300">
                  Method profile metadata is not available for this detector yet.
                </p>
              )
            ) : (
              <p className="mt-2 text-xs text-slate-300">
                Expand this drawer for canonical usage, deviations, caveats, and sourced origins.
              </p>
            )}
          </div>

          {llmCard ? (
            <div className="mt-3 rounded-md border border-sky-300/30 bg-sky-400/10 p-3 text-xs text-slate-100">
              <div className="text-xs font-semibold uppercase tracking-wide text-sky-200">
                Run this output yourself
              </div>
              <p className="mt-1 text-xs text-slate-200">
                This detector is precomputed offline. Use the same input and starter text to rerun in
                ChatGPT Desktop for reproducible outputs.
              </p>
              <div className="mt-2 space-y-1 text-xs text-slate-200">
                <div>
                  Model:{" "}
                  <span className="text-slate-100">
                    {modelProvider && modelName
                      ? `${modelProvider} / ${modelName}`
                      : llmCampaign
                        ? `${llmCampaign.modelProvider} / ${llmCampaign.modelName}`
                        : "not set"}
                  </span>
                </div>
                {llmCampaign ? (
                  <div>
                    Campaign: <span className="text-slate-100">{llmCampaign.campaignDisplayName}</span>
                  </div>
                ) : null}
                {runLabel ? (
                  <div>
                    Run label: <span className="text-slate-100">{runLabel}</span>
                  </div>
                ) : null}
                {runDate ? (
                  <div>
                    Run date: <span className="text-slate-100">{runDate}</span>
                  </div>
                ) : null}
                <div className="break-all">
                  Input file:{" "}
                  <span className="text-slate-100">{inputFileForRerun ?? "not available"}</span>
                </div>
                <div className="break-all">
                  Expected output path:{" "}
                  <span className="text-slate-100">{debugInfo?.expectedPath ?? "not available"}</span>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={handleCopyThreadStarter}
                  disabled={!threadStarterText}
                  className="rounded-md border border-white/20 bg-slate-900/60 px-2 py-1 text-xs text-slate-100 transition hover:border-white/40 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Copy thread starter
                </button>
                <button
                  type="button"
                  onClick={handleCopyProjectInstructions}
                  disabled={!projectInstructions}
                  className="rounded-md border border-white/20 bg-slate-900/60 px-2 py-1 text-xs text-slate-100 transition hover:border-white/40 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Copy project instructions
                </button>
                {copyStarterState === "copied" ? (
                  <span className="text-xs text-emerald-300">Starter copied.</span>
                ) : null}
                {copyStarterState === "failed" ? (
                  <span className="text-xs text-rose-300">Starter copy failed.</span>
                ) : null}
                {copyInstructionsState === "copied" ? (
                  <span className="text-xs text-emerald-300">Instructions copied.</span>
                ) : null}
                {copyInstructionsState === "failed" ? (
                  <span className="text-xs text-rose-300">Instructions copy failed.</span>
                ) : null}
              </div>
              {projectInstructionsError ? (
                <div className="mt-2 text-xs text-amber-100">
                  Instruction text fallback in use: {projectInstructionsError}
                </div>
              ) : null}
            </div>
          ) : null}

          {output ? (
            <div className="mt-4 space-y-4">
              {shouldShowSignalBanner ? (
                <div className={`rounded-md border p-3 text-xs ${signalTierClasses(signalSummary.tier)}`}>
                  <div className="font-semibold">Signal quality: {signalSummary.tier.toUpperCase()}</div>
                  <p className="mt-1">{signalSummary.summary}</p>
                  <p className="mt-1 text-slate-100">{signalSummary.reason}</p>
                  <p className="mt-1 text-slate-100">
                    <span className="font-semibold">
                      {analysisMode === "deep" ? "Why signal may be weak:" : "Interpretation note:"}
                    </span>{" "}
                    {weaknessReason}
                  </p>
                  <p className="mt-1 text-slate-100">
                    <span className="font-semibold">Next best action:</span> {signalSummary.nextAction}
                  </p>
                </div>
              ) : null}

              {warnings.length || rankedItems.length || topRisers.length || topFallers.length ? (
                <div className="rounded-md border border-white/10 bg-slate-900/35 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-xs font-semibold uppercase tracking-wide text-slate-200">
                        Diagnostic details
                      </div>
                      <p className="mt-1 text-xs text-slate-400">
                        Warnings, ranked terms, and riser/faller context.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={handleToggleDiagnostics}
                      className="rounded-md border border-white/20 bg-slate-900/60 px-2 py-1 text-xs text-slate-100 transition hover:border-white/40"
                    >
                      {isDiagnosticsOpen ? "Hide diagnostics" : "Show diagnostics"}
                    </button>
                  </div>

                  {isDiagnosticsOpen ? (
                    <div className="mt-3 space-y-4">
                      {warnings.length ? (
                        <div className="rounded-md border border-amber-400/30 bg-amber-400/10 p-3 text-xs text-amber-100">
                          Warnings: {warnings.join(", ")}
                        </div>
                      ) : null}

                      {rankedItems.length ? (
                        <div>
                          <div className="text-xs uppercase tracking-wide text-slate-400">Top ranked</div>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {rankedItems.slice(0, 8).map((item) => (
                              <span
                                key={item.label}
                                className="rounded-full border border-white/10 bg-white/5 px-2 py-1 text-xs text-slate-200"
                              >
                                {item.label} | {item.score.toFixed(2)}
                              </span>
                            ))}
                          </div>
                        </div>
                      ) : null}

                      {topRisers.length || topFallers.length ? (
                        <div className="grid gap-3 md:grid-cols-2">
                          <div>
                            <div className="text-xs uppercase tracking-wide text-slate-400">Risers</div>
                            <ul className="mt-2 space-y-1 text-xs text-slate-200">
                              {topRisers.slice(0, 6).map((item) => (
                                <li key={item.label}>{item.label}</li>
                              ))}
                            </ul>
                          </div>
                          <div>
                            <div className="text-xs uppercase tracking-wide text-slate-400">Fallers</div>
                            <ul className="mt-2 space-y-1 text-xs text-slate-200">
                              {topFallers.slice(0, 6).map((item) => (
                                <li key={item.label}>{item.label}</li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ) : null}

              <div>
                <div className="text-xs uppercase tracking-wide text-slate-400">Evidence</div>
                <div className="mt-2">
                  {isDeltaBrief && deltaBriefText ? (
                    <div>
                      <div className="text-xs uppercase tracking-wide text-slate-400">Delta brief</div>
                      <div className="mt-2 whitespace-pre-wrap rounded-md border border-white/10 bg-white/5 p-3 text-xs text-slate-200">
                        {deltaBriefText}
                      </div>
                    </div>
                  ) : null}

                  {isExcerptPicker ? (
                    <LabExcerptPickerPanel output={output} />
                  ) : (
                    <EvidenceStack
                      evidence={output.evidence ?? []}
                      fallbackMessage="No evidence blocks for this detector yet."
                    />
                  )}
                </div>
              </div>
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  )
}
