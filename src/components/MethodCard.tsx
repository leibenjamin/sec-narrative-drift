import { useMemo, useState } from "react"
import EvidenceStack from "./EvidenceStack"
import {
  buildDefaultLlmInputFile,
  buildDefaultLlmYearInputFile,
  buildLlmThreadStarterText,
  isLlmDetector,
} from "../lib/labLlmRepro"
import { withBase } from "../lib/paths"
import { assertSameOriginPathLike } from "../lib/sanitize"
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
    inputFile?: string | null
    yearInputPrev?: string | null
    yearInputCurr?: string | null
    inputFileUrl?: string | null
    yearInputPrevUrl?: string | null
    yearInputCurrUrl?: string | null
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

function formatConfidenceBand(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "-"
  if (value >= 0.75) return `High (${value.toFixed(2)})`
  if (value <= 0.25) return `Low (${value.toFixed(2)})`
  return `Medium (${value.toFixed(2)})`
}

function classifySignal(output: LabOutput | null): SignalSummary {
  if (!output) {
    return {
      tier: "insufficient",
      summary: "Analysis not available.",
      reason: "Output artifact has not been generated for this method/lens combination yet.",
      nextAction: "Review other available methods or check the debug details below.",
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
      summary: "Too little evidence to draw conclusions from this method alone.",
      reason:
        "Key metrics are missing or the evidence base is too thin for reliable interpretation.",
      nextAction: "Cross-reference with at least two other methods before interpreting.",
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
      summary: "Strong evidence of meaningful narrative change detected.",
      reason: "High confidence, broad coverage, and substantial supporting evidence.",
      nextAction: "Check the agreement matrix to see if other methods confirm this finding.",
    }
  }

  if (confidence < 0.45 || coverage < 0.45 || warningsCount >= 2 || evidenceCount < 3) {
    return {
      tier: "low",
      summary: "Weak signal — treat as directional only.",
      reason:
        "Low confidence, limited coverage, or sparse evidence makes this finding unreliable on its own.",
      nextAction: "Use the core drift methods and agreement matrix as the primary reference instead.",
    }
  }

  return {
    tier: "medium",
    summary: "Moderate evidence of narrative change — review supporting excerpts.",
    reason: "Metrics are acceptable but not uniformly strong. Interpret with context from other methods.",
    nextAction: "Compare with the agreement matrix and at least one other method before concluding.",
  }
}

function buildWeaknessReason(output: LabOutput | null): string {
  if (!output) {
    return "No output available for this method."
  }

  const weakness: string[] = []
  const confidence = output.metrics.confidence
  const coverage = output.metrics.coverage
  const warningsCount = output.metrics.warnings.length
  const evidenceCount = output.evidence.length

  if (warningsCount > 0) weakness.push(`${warningsCount} warning${warningsCount > 1 ? "s" : ""}`)
  if (confidence !== null && confidence < 0.6) weakness.push(`low confidence (${confidence.toFixed(2)})`)
  if (coverage !== null && coverage < 0.6) weakness.push(`limited coverage (${coverage.toFixed(2)})`)
  if (evidenceCount < 4) weakness.push(`only ${evidenceCount} evidence excerpt${evidenceCount !== 1 ? "s" : ""}`)

  if (weakness.length === 0) {
    return "Metrics look healthy, but always cross-reference with other methods for a complete picture."
  }
  return `Caveats: ${weakness.join("; ")}.`
}

function buildDecisionSentence(signalSummary: SignalSummary): string {
  return signalSummary.summary
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

function resolveInputHref(pathValue: string | null | undefined): string | null {
  if (!pathValue) return null
  try {
    return assertSameOriginPathLike(pathValue)
  } catch {
    return null
  }
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
  const [copyAttachmentsState, setCopyAttachmentsState] = useState<"idle" | "copied" | "failed">(
    "idle"
  )
  const [copyClaimUrlState, setCopyClaimUrlState] = useState<"idle" | "copied" | "failed">(
    "idle"
  )
  const [copiedClaimUrl, setCopiedClaimUrl] = useState<string | null>(null)
  const [contextPreference, setContextPreference] = useState<"auto" | "open" | "closed">("auto")
  const [diagnosticsPreference, setDiagnosticsPreference] = useState<"auto" | "open" | "closed">(
    "auto"
  )

  const warnings = output?.metrics.warnings ?? []
  const rankedItems = normalizeRankedList(output?.artifacts.ranked_items)
  const topRisers = normalizeRankedList(output?.artifacts.top_risers)
  const topFallers = normalizeRankedList(output?.artifacts.top_fallers)
  const llmCard = isLlmDetector(detectorId)
  const signalSummary = useMemo(() => classifySignal(output), [output])
  const weaknessReason = useMemo(() => buildWeaknessReason(output), [output])
  const decisionSentence = useMemo(() => buildDecisionSentence(signalSummary), [signalSummary])

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
  const pairInputFileForRerun = debugInfo?.inputFile ?? inputFileForRerun
  const yearPrevInputFileForRerun =
    debugInfo?.yearInputPrev ??
    (debugInfo
      ? buildDefaultLlmYearInputFile(
          debugInfo.ticker,
          debugInfo.yearFrom,
          debugInfo.yearFrom,
          debugInfo.yearTo,
          debugInfo.lens,
          output?.section ?? "10k_item1a",
          output?.source_id ?? "edgar"
        )
      : null)
  const yearCurrInputFileForRerun =
    debugInfo?.yearInputCurr ??
    (debugInfo
      ? buildDefaultLlmYearInputFile(
          debugInfo.ticker,
          debugInfo.yearTo,
          debugInfo.yearFrom,
          debugInfo.yearTo,
          debugInfo.lens,
          output?.section ?? "10k_item1a",
          output?.source_id ?? "edgar"
        )
      : null)
  const pairInputUrl = resolveInputHref(debugInfo?.inputFileUrl ?? pairInputFileForRerun)
  const yearPrevInputUrl = resolveInputHref(
    debugInfo?.yearInputPrevUrl ?? yearPrevInputFileForRerun
  )
  const yearCurrInputUrl = resolveInputHref(
    debugInfo?.yearInputCurrUrl ?? yearCurrInputFileForRerun
  )
  const threadStarterText = useMemo(() => {
    if (!llmCard || !debugInfo || !pairInputFileForRerun || !llmCampaign) return null
    return buildLlmThreadStarterText({
      ticker: debugInfo.ticker,
      yearFrom: debugInfo.yearFrom,
      yearTo: debugInfo.yearTo,
      detectorId: debugInfo.detectorId || detectorId,
      lens: debugInfo.lens,
      sectionId: output?.section ?? "10k_item1a",
      campaignId: llmCampaign.campaignId,
      campaignDisplayName: llmCampaign.campaignDisplayName,
      modelProvider: llmCampaign.modelProvider,
      modelName: llmCampaign.modelName,
      inputFile: pairInputFileForRerun,
      expectedOutputPath: debugInfo.expectedPath ?? null,
      runLabelTemplate: "YYYY-MM-DD_<campaign_tag>",
      sourceId: output?.source_id ?? "edgar",
    })
  }, [
    llmCard,
    debugInfo,
    pairInputFileForRerun,
    llmCampaign,
    detectorId,
    output?.section,
    output?.source_id,
  ])


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
      input_file: pairInputFileForRerun ?? null,
      year_input_prev: yearPrevInputFileForRerun ?? null,
      year_input_curr: yearCurrInputFileForRerun ?? null,
      input_file_url: pairInputUrl ?? null,
      year_input_prev_url: yearPrevInputUrl ?? null,
      year_input_curr_url: yearCurrInputUrl ?? null,
      error: debugInfo.errorText,
      schema_issue_or_debug: debugPath ?? null,
    }
    const didCopy = await copyTextToClipboard(JSON.stringify(payload, null, 2))
    setCopyState(didCopy ? "copied" : "failed")
  }

  const handleCopyAttachmentPaths = async () => {
    const lines: string[] = []
    if (pairInputFileForRerun) lines.push(`Pair manifest: ${pairInputFileForRerun}`)
    if (yearPrevInputFileForRerun) lines.push(`Year prev: ${yearPrevInputFileForRerun}`)
    if (yearCurrInputFileForRerun) lines.push(`Year curr: ${yearCurrInputFileForRerun}`)
    if (lines.length === 0) return
    const didCopy = await copyTextToClipboard(lines.join("\n"))
    setCopyAttachmentsState(didCopy ? "copied" : "failed")
  }

  const handleCopyThreadStarter = async () => {
    if (!threadStarterText) return
    const didCopy = await copyTextToClipboard(threadStarterText)
    setCopyStarterState(didCopy ? "copied" : "failed")
  }


  const handleCopyClaimUrl = async (url: string) => {
    const didCopy = await copyTextToClipboard(url)
    setCopiedClaimUrl(url)
    setCopyClaimUrlState(didCopy ? "copied" : "failed")
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
  const diagnosticsToneClass =
    signalSummary.tier === "high" || signalSummary.tier === "medium"
      ? "border-white/5 bg-slate-900/25"
      : "border-white/10 bg-slate-900/35"

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
          <span title="Magnitude of year-over-year narrative change detected">Drift: {formatMetric(output?.metrics.drift_score)}</span>
          <span className="text-slate-500">|</span>
          <span
            title="Heuristic confidence band (Low / Medium / High) — not a calibrated probability"
          >
            Confidence: {formatConfidenceBand(output?.metrics.confidence)}
          </span>
          <span className="text-slate-500">|</span>
          <span title="Proportion of the risk section covered by this method's analysis">Coverage: {formatMetric(output?.metrics.coverage)}</span>
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
              <p className="text-xs font-semibold text-amber-100">Analysis not available</p>
              <p className="text-xs text-slate-200">{emptyMessage ?? "No output available for this configuration."}</p>
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
                        {methodProfile.origin_claims.map((claim) => {
                          const internalClaimHref = resolveInputHref(claim.url)
                          return (
                            <li key={`${claim.title}:${claim.year}`}>
                            <div className="font-medium text-slate-200">
                              {claim.title} ({claim.year})
                            </div>
                            <div>{claim.author_or_org}</div>
                            {internalClaimHref ? (
                              <a
                                href={internalClaimHref}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sky-300 underline decoration-sky-300/60 underline-offset-2"
                              >
                                Source
                              </a>
                            ) : (
                              <div className="mt-1 flex flex-wrap items-center gap-2">
                                <span className="text-amber-200">
                                  External URL blocked by same-origin policy.
                                </span>
                                <button
                                  type="button"
                                  onClick={() => handleCopyClaimUrl(claim.url)}
                                  className="rounded-md border border-white/20 bg-slate-900/60 px-2 py-1 text-xs text-slate-100 transition hover:border-white/40"
                                >
                                  Copy URL
                                </button>
                                {copiedClaimUrl === claim.url && copyClaimUrlState === "copied" ? (
                                  <span className="text-emerald-300">Copied.</span>
                                ) : null}
                                {copiedClaimUrl === claim.url && copyClaimUrlState === "failed" ? (
                                  <span className="text-rose-300">Copy failed.</span>
                                ) : null}
                              </div>
                            )}
                            {!internalClaimHref ? (
                              <div className="break-all text-[11px] text-slate-400">{claim.url}</div>
                            ) : null}
                          </li>
                          )
                        })}
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
            <details className="mt-3 rounded-md border border-sky-300/30 bg-sky-400/10 p-3 text-xs text-slate-100">
              <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-sky-200">
                Reproducibility — run this analysis yourself
              </summary>
              <p className="mt-2 text-xs text-slate-200">
                This analysis was precomputed offline. You can reproduce it using the same
                inputs and model configuration below.
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
                  Pair manifest:{" "}
                  <span className="text-slate-100">
                    {pairInputFileForRerun ?? "not available"}
                  </span>
                  {pairInputUrl ? (
                    <>
                      {" "}
                      <a
                        href={pairInputUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sky-300 underline decoration-sky-300/60 underline-offset-2"
                      >
                        open
                      </a>
                    </>
                  ) : null}
                </div>
                <div className="break-all">
                  Year prev input:{" "}
                  <span className="text-slate-100">
                    {yearPrevInputFileForRerun ?? "not available"}
                  </span>
                  {yearPrevInputUrl ? (
                    <>
                      {" "}
                      <a
                        href={yearPrevInputUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sky-300 underline decoration-sky-300/60 underline-offset-2"
                      >
                        open
                      </a>
                    </>
                  ) : null}
                </div>
                <div className="break-all">
                  Year curr input:{" "}
                  <span className="text-slate-100">
                    {yearCurrInputFileForRerun ?? "not available"}
                  </span>
                  {yearCurrInputUrl ? (
                    <>
                      {" "}
                      <a
                        href={yearCurrInputUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sky-300 underline decoration-sky-300/60 underline-offset-2"
                      >
                        open
                      </a>
                    </>
                  ) : null}
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
                  onClick={handleCopyAttachmentPaths}
                  disabled={
                    !pairInputFileForRerun && !yearPrevInputFileForRerun && !yearCurrInputFileForRerun
                  }
                  className="rounded-md border border-white/20 bg-slate-900/60 px-2 py-1 text-xs text-slate-100 transition hover:border-white/40 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Copy all attachment paths
                </button>
                {copyStarterState === "copied" ? (
                  <span className="text-xs text-emerald-300">Starter copied.</span>
                ) : null}
                {copyStarterState === "failed" ? (
                  <span className="text-xs text-rose-300">Starter copy failed.</span>
                ) : null}
                {copyAttachmentsState === "copied" ? (
                  <span className="text-xs text-emerald-300">Attachment paths copied.</span>
                ) : null}
                {copyAttachmentsState === "failed" ? (
                  <span className="text-xs text-rose-300">Attachment copy failed.</span>
                ) : null}
              </div>
              <p className="mt-2 text-xs text-slate-400">The thread starter already carries the required output contract. Pair and year input files are the only public attachments needed for reruns.</p>
            </details>
          ) : null}

          {output ? (
            <div className="mt-4 space-y-4">
              {shouldShowSignalBanner ? (
                <div className={`rounded-md border p-3 text-xs ${signalTierClasses(signalSummary.tier)}`}>
                  <div className="font-semibold">
                    Evidence strength: {signalSummary.tier === "high" ? "Strong" : signalSummary.tier === "medium" ? "Moderate" : signalSummary.tier === "low" ? "Weak" : "Insufficient"}
                  </div>
                  <p className="mt-1">{signalSummary.reason}</p>
                  <p className="mt-1 text-slate-100">{weaknessReason}</p>
                  <p className="mt-1 text-slate-100">
                    <span className="font-semibold">Suggested next step:</span> {signalSummary.nextAction}
                  </p>
                </div>
              ) : null}

              {warnings.length || rankedItems.length || topRisers.length || topFallers.length ? (
                <div className={`rounded-md border p-3 ${diagnosticsToneClass}`}>
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
                  <EvidenceStack
                    evidence={output.evidence ?? []}
                    fallbackMessage="No evidence blocks for this detector yet."
                  />
                </div>
              </div>
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  )
}
