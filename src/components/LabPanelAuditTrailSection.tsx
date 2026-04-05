import { useState, type ComponentProps, type ReactNode } from "react"
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

type DisclosureTone = "core" | "utility" | "optional"

type AuditDisclosureRowProps = {
  children: ReactNode
  description: string
  id?: string
  title: string
  tone?: DisclosureTone
}

function disclosureToneClasses(tone: DisclosureTone): string {
  if (tone === "utility") {
    return "border-white/7 bg-slate-950/10"
  }
  if (tone === "optional") {
    return "border-white/6 bg-slate-950/6"
  }
  return "border-white/10 bg-slate-950/16"
}

function disclosureCueToneClasses(tone: DisclosureTone): string {
  if (tone === "utility") {
    return "border-white/10 bg-slate-900/45 text-slate-300"
  }
  if (tone === "optional") {
    return "border-white/8 bg-slate-900/35 text-slate-300"
  }
  return "border-white/15 bg-white/5 text-slate-200"
}

function AuditDisclosureRow({
  children,
  description,
  id,
  title,
  tone = "core",
}: AuditDisclosureRowProps) {
  return (
    <details
      id={id}
      data-tone={tone}
      className={`audit-disclosure rounded-[1.15rem] border px-3 py-3 sm:px-4 ${disclosureToneClasses(tone)}`}
    >
      <summary className="audit-disclosure__summary flex list-none items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="text-[1rem] font-semibold text-slate-100">{title}</div>
          <p className="mt-1 text-sm leading-6 text-slate-400">{description}</p>
        </div>
        <span
          className={`audit-disclosure__cue flex shrink-0 items-center gap-2 rounded-full border px-2.5 py-1.5 text-[11px] font-medium uppercase tracking-[0.18em] ${disclosureCueToneClasses(tone)}`}
        >
          <span className="audit-disclosure__cue-verb audit-disclosure__cue-verb--closed">Open</span>
          <span className="audit-disclosure__cue-verb audit-disclosure__cue-verb--open">Close</span>
          <span className="audit-disclosure__cue-symbol audit-disclosure__cue-symbol--closed">+</span>
          <span className="audit-disclosure__cue-symbol audit-disclosure__cue-symbol--open">-</span>
        </span>
      </summary>
      <div className="audit-disclosure__body mt-4 border-l border-white/10 pl-4 sm:pl-5">
        {children}
      </div>
    </details>
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
  const compareLaneCount = selectedCompareCampaignIds.length || 1
  const modeLabel = analysisMode === "executive" ? "Quick read mode" : "Deep review mode"

  return (
    <section
      id="lab-audit-trail"
      className="space-y-4 rounded-[1.35rem] border border-white/10 bg-slate-950/14 p-4 sm:space-y-5 sm:p-5"
    >
      <div className="space-y-2.5">
        <p className="text-[11px] uppercase tracking-[0.24em] text-slate-300">Audit gateway</p>
        <h2 className="text-xl font-semibold text-slate-100">Pressure-test the briefing</h2>
        <p className="max-w-3xl text-sm leading-6 text-slate-300">
          Open the lower audit only when the filing answer or protocol layer still needs more
          pressure.
        </p>
        <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] uppercase tracking-[0.18em] text-slate-500">
          <span>{totalMethodCards} deterministic cards</span>
          <span className="text-slate-700">/</span>
          <span>{modeLabel}</span>
          <span className="text-slate-700">/</span>
          <span>Compare lanes: {compareLaneCount}</span>
        </p>
      </div>

      <div className="space-y-3">
        <AuditDisclosureRow
          title="Deterministic methods"
          description={`${totalMethodCards} deterministic cards when the filing answer needs method-by-method pressure.`}
        >
          <div id="lab-method-context" className="space-y-6">
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
        </AuditDisclosureRow>

        <AuditDisclosureRow
          id="lab-agreement"
          title="Where methods agree"
          description="Cross-check whether the deterministic methods reinforce the same story or force a slower read."
        >
          <div className="space-y-4">
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
        </AuditDisclosureRow>
      </div>

      {selectedLlmCampaignA || selectedLlmCampaignB ? (
        <div className="pt-2">
          <AuditDisclosureRow
            title="Structure audit"
            description="Compare the ranked outline audit only when the briefing shell still needs proof."
          >
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
          </AuditDisclosureRow>
        </div>
      ) : null}

      {selectedLlmCampaignA || selectedLlmCampaignB ? (
        <>
          <div className="pt-2">
            <AuditDisclosureRow
              title="Advanced controls"
              description="Adjust lanes, method coverage, and diagnostics without reopening the upper shell."
              tone="utility"
            >
              <LabPanelAdvancedControls {...advancedControlsProps} />
            </AuditDisclosureRow>
          </div>
          <div className="pt-3">
            <AuditDisclosureRow
              title="Optional insight lens"
              description="Optional paragraph drilldown once the filing answer and structure audit are already in view."
              tone="optional"
            >
              {selectedCompareCampaignIds.length > 0 && !hasAnyInsightOutput ? (
                <div
                  id="lab-insight-lens"
                  className="rounded-lg border border-white/10 bg-slate-950/18 px-3 py-3 text-sm text-slate-200 sm:px-4"
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
            </AuditDisclosureRow>
          </div>
        </>
      ) : (
        <div className="pt-2">
          <AuditDisclosureRow
            title="Advanced controls"
            description="Adjust lanes, method coverage, and diagnostics without reopening the upper shell."
            tone="utility"
          >
            <LabPanelAdvancedControls {...advancedControlsProps} />
          </AuditDisclosureRow>
        </div>
      )}
    </section>
  )
}
