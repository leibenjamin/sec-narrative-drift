import { useState, type ComponentProps } from "react"
import AgreementMatrix from "./AgreementMatrix"
import InsightLensPanel from "./InsightLensPanel"
import LabPanelAdvancedControls from "./LabPanelAdvancedControls"
import MethodCard from "./MethodCard"
import OutlineComparePanel from "./OutlineComparePanel"
import type { LabMethodProfile } from "../lib/labTypes"
import type {
  LabPanelDetectorDebugInfo,
  LabPanelOutlineArtifactDebugInfo,
  LabPanelOutputsState,
} from "./useLabPanelOutputs"

type AnalysisMode = "executive" | "deep"

type MethodCardDescriptor = {
  id: string
  label: string
  technicalLabel: string
  description: string
  cardKey: string
}

type MethodCardGroup = {
  id: string
  label: string
  sectionId: string
  cards: MethodCardDescriptor[]
}

type CompactInsightItem = {
  campaignId: string
  label: string
  debug: LabPanelOutlineArtifactDebugInfo | null
  debugPath: string | null
}

type LabPanelAuditTrailSectionProps = {
  analysisMode: AnalysisMode
  advancedControlsProps: ComponentProps<typeof LabPanelAdvancedControls>
  groupedMethodCards: MethodCardGroup[]
  outputState: LabPanelOutputsState
  methodProfilesByDetector: Record<string, LabMethodProfile>
  deepAutoOpenContextKeys: Set<string>
  isCardExpanded: (cardKey: string) => boolean
  onToggleCardExpanded: (cardKey: string) => void
  selectedLlmCampaignA: string
  selectedLlmCampaignB: string
  selectedCampaignLabelA: string
  selectedCampaignLabelB: string
  selectedCompareCampaignIds: string[]
  hasAnyInsightOutput: boolean
  compactInsightItems: CompactInsightItem[]
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

function buildDebugPayload(
  info: LabPanelDetectorDebugInfo,
  debugText: string | null
): string {
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

type DisclosureSummaryProps = {
  title: string
  description: string
  badge: string
}

function DisclosureSummary({ title, description, badge }: DisclosureSummaryProps) {
  return (
    <summary className="flex cursor-pointer list-none items-start justify-between gap-3 rounded-[0.95rem] border border-white/10 bg-slate-950/36 px-3 py-3">
      <div>
        <div className="text-sm font-semibold text-slate-100">{title}</div>
        <p className="mt-1 text-xs leading-5 text-slate-400">{description}</p>
      </div>
      <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] font-medium text-slate-200">
        {badge}
      </span>
    </summary>
  )
}

export default function LabPanelAuditTrailSection({
  analysisMode,
  advancedControlsProps,
  groupedMethodCards,
  outputState,
  methodProfilesByDetector,
  deepAutoOpenContextKeys,
  isCardExpanded,
  onToggleCardExpanded,
  selectedLlmCampaignA,
  selectedLlmCampaignB,
  selectedCampaignLabelA,
  selectedCampaignLabelB,
  selectedCompareCampaignIds,
  hasAnyInsightOutput,
  compactInsightItems,
}: LabPanelAuditTrailSectionProps) {
  const {
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
  } = outputState
  const [agreementCopyState, setAgreementCopyState] = useState<"idle" | "copied" | "failed">("idle")
  const agreementCopyResetKey = `${agreementDebugInfo?.expectedPath ?? ""}|${agreementDebugInfo?.requestedUrl ?? ""}|${agreementDebugPath ?? ""}|${agreementDebugInfo?.errorText ?? ""}`
  const [prevAgreementCopyResetKey, setPrevAgreementCopyResetKey] = useState(agreementCopyResetKey)

  if (prevAgreementCopyResetKey !== agreementCopyResetKey) {
    setPrevAgreementCopyResetKey(agreementCopyResetKey)
    setAgreementCopyState("idle")
  }

  const handleCopyAgreementDebug = async () => {
    if (!agreementDebugInfo) return
    const payload = buildDebugPayload(agreementDebugInfo, agreementDebugPath)
    const didCopy = await copyTextToClipboard(payload)
    setAgreementCopyState(didCopy ? "copied" : "failed")
  }

  const totalMethodCards = groupedMethodCards.reduce((count, group) => count + group.cards.length, 0)

  return (
    <section
      id="lab-audit-trail"
      className="space-y-4 rounded-[1.35rem] border border-white/10 bg-slate-950/14 p-4 sm:space-y-5 sm:p-5"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-3xl">
          <p className="text-[11px] uppercase tracking-[0.24em] text-slate-300">Audit gateway</p>
          <h2 className="mt-1.5 text-xl font-semibold text-slate-100">Pressure-test the briefing</h2>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            Controls, methods, agreement checks, and structure audit stay collapsed until you need
            them. The shell above keeps the first read compact on purpose.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-[11px] text-slate-200">
          <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
            {advancedControlsProps.methodCoverageSummary}
          </span>
          <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
            {analysisMode === "executive" ? "Quick read mode" : "Deep review mode"}
          </span>
          <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
            Compare lanes: {selectedCompareCampaignIds.length || 1}
          </span>
        </div>
      </div>

      <div className="grid gap-2.5 md:grid-cols-3">
        <article className="rounded-2xl border border-sky-300/14 bg-slate-950/28 p-3">
          <div className="text-[10px] uppercase tracking-[0.24em] text-slate-400">Controls</div>
          <p className="mt-2 text-xs leading-5 text-slate-100">
            Case override, compare-lane selection, and method toggles stay tucked into the first
            collapsed panel.
          </p>
        </article>
        <article className="rounded-2xl border border-emerald-300/14 bg-slate-950/28 p-3">
          <div className="text-[10px] uppercase tracking-[0.24em] text-slate-400">Methods</div>
          <p className="mt-2 text-xs leading-5 text-slate-100">
            {totalMethodCards} deterministic cards remain available, but they no longer dominate the
            default company view.
          </p>
        </article>
        <article className="rounded-2xl border border-amber-300/14 bg-slate-950/28 p-3">
          <div className="text-[10px] uppercase tracking-[0.24em] text-slate-400">Structure audit</div>
          <p className="mt-2 text-xs leading-5 text-slate-100">
            Full ranked compare, outline structure, and optional insight stay below this gateway and
            open only on demand.
          </p>
        </article>
      </div>

      <LabPanelAdvancedControls {...advancedControlsProps} />

      <details className="rounded-[1.1rem] border border-emerald-300/16 bg-slate-950/22 p-3 sm:p-4">
        <DisclosureSummary
          title="Deterministic methods"
          description="Open this only when the filing answer needs method-by-method pressure."
          badge={`${totalMethodCards} cards`}
        />
        <p className="mt-3 text-xs text-slate-400">
          Expand only when the filing answer needs method-by-method pressure. Each card still keeps
          its own evidence, caveats, and method context.
        </p>

        <div id="lab-method-context" className="mt-4 space-y-6">
          {groupedMethodCards.map((group) => (
            <section key={group.id} id={group.sectionId} className="space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-300">
                {group.label}
              </h3>
              <div className="grid gap-3 sm:gap-4">
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
                    autoOpenContext={analysisMode === "deep" && deepAutoOpenContextKeys.has(detector.cardKey)}
                    isExpanded={isCardExpanded(detector.cardKey)}
                    onToggleExpanded={() => onToggleCardExpanded(detector.cardKey)}
                    emptyMessage="No output available for this method, lens, and model combination. Try the deboilerplated lens or a different ticker for available results."
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      </details>

      <details
        id="lab-agreement"
        className="rounded-[1.1rem] border border-sky-300/16 bg-slate-950/22 p-3 sm:p-4"
      >
        <DisclosureSummary
          title="Where methods agree"
          description="Use this table only when you want to test whether the deterministic methods reinforce the same story."
          badge="Cross-check"
        />
        <p className="mt-3 text-xs text-slate-400">
          Use this table only when you want to test whether the deterministic methods reinforce the
          same story or pull you into a slower read.
        </p>
        <div className="mt-4 space-y-4">
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
      </details>

      {selectedLlmCampaignA || selectedLlmCampaignB ? (
        <details className="rounded-[1.1rem] border border-amber-300/16 bg-slate-950/22 p-3 sm:p-4">
          <DisclosureSummary
            title="Structure audit"
            description="Open this only when you want the full ranked compare and outline structure behind the briefing shell."
            badge="Full compare"
          />
          <p className="mt-3 text-xs text-slate-400">
            Open this only when you want the full ranked compare, outline structure, mechanisms, and
            limitations that sit behind the briefing shell.
          </p>
          <div className="mt-4">
            <OutlineComparePanel
              modelALabel={selectedCampaignLabelA}
              modelBLabel={selectedCampaignLabelB}
              modelAOutput={selectedLlmCampaignA ? outlineOutputs[selectedLlmCampaignA] ?? null : null}
              modelBOutput={selectedLlmCampaignB ? outlineOutputs[selectedLlmCampaignB] ?? null : null}
              modelADebug={selectedLlmCampaignA ? outlineDebugInfo[selectedLlmCampaignA] ?? null : null}
              modelBDebug={selectedLlmCampaignB ? outlineDebugInfo[selectedLlmCampaignB] ?? null : null}
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
          </div>
        </details>
      ) : null}

      {selectedLlmCampaignA || selectedLlmCampaignB ? (
        <details className="rounded-[1.1rem] border border-white/10 bg-slate-950/22 p-3 sm:p-4">
          <DisclosureSummary
            title="Optional insight lens"
            description="Insight sidecars stay explicitly secondary and only matter once the filing answer and structure audit are already in view."
            badge="Optional"
          />
          <p className="mt-3 text-xs text-slate-400">
            Insight sidecars stay explicitly secondary and only matter once the filing answer and
            structure audit are already in view.
          </p>
          <div className="mt-4">
            {selectedCompareCampaignIds.length > 0 && !hasAnyInsightOutput ? (
              <div
                id="lab-insight-lens"
                className="rounded-lg border border-white/10 bg-slate-950/20 px-3 py-3 text-sm text-slate-200 sm:px-4"
              >
                <p className="text-sm text-slate-200">
                  Optional insight sidecars are not published for these compare lanes. The shipped compare
                  path remains the filing answer plus the outline audit above.
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
                modelADebugPath={
                  selectedLlmCampaignA ? insightDebugPaths[selectedLlmCampaignA] ?? null : null
                }
                modelBDebugPath={
                  selectedLlmCampaignB ? insightDebugPaths[selectedLlmCampaignB] ?? null : null
                }
              />
            )}
          </div>
        </details>
      ) : null}
    </section>
  )
}
