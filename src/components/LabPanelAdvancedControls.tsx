import CleaningLensToggle from "./CleaningLensToggle"
import type { LabCleaningLens, LabLlmCampaign } from "../lib/labTypes"

type DetectorToggleGroup = {
  id: string
  label: string
  detectors: Array<{
    id: string
    label: string
  }>
}

type CaseOption = {
  key: string
  label: string
}

type LabPanelAdvancedControlsProps = {
  isPilotMatrixSelectedCase: boolean
  lens: LabCleaningLens
  lensOptions: Array<{ value: LabCleaningLens; disabled: boolean }>
  onLensChange: (value: LabCleaningLens) => void
  onApplyQuickRead: () => void
  onApplyDeepReview: () => void
  isExecutiveMode: boolean
  isDeepMode: boolean
  presetStatusMessage: string | null
  hasMultipleCases: boolean
  caseOptions: CaseOption[]
  selectedCaseKey: string | null
  onSelectedCaseKeyChange: (value: string) => void
  llmCampaignOptions: LabLlmCampaign[]
  selectedLlmCampaignA: string
  selectedLlmCampaignB: string
  onSelectedLlmCampaignAChange: (value: string) => void
  onSelectedLlmCampaignBChange: (value: string) => void
  detectorGroups: DetectorToggleGroup[]
  availableDetectorSet: Set<string>
  selectedDetectors: string[]
  onToggleDetector: (detectorId: string) => void
  availableDetectorCount: number
  detectorCatalogCount: number
  onExpandAllCards: () => void
  onCollapseAllCards: () => void
  expandedCount: number
  methodCardCount: number
  onReloadOutputs: () => void
  isReloadDisabled: boolean
  showProtocolJump: boolean
  showInsightJump: boolean
  showMethodContextJump: boolean
}

export default function LabPanelAdvancedControls({
  isPilotMatrixSelectedCase,
  lens,
  lensOptions,
  onLensChange,
  onApplyQuickRead,
  onApplyDeepReview,
  isExecutiveMode,
  isDeepMode,
  presetStatusMessage,
  hasMultipleCases,
  caseOptions,
  selectedCaseKey,
  onSelectedCaseKeyChange,
  llmCampaignOptions,
  selectedLlmCampaignA,
  selectedLlmCampaignB,
  onSelectedLlmCampaignAChange,
  onSelectedLlmCampaignBChange,
  detectorGroups,
  availableDetectorSet,
  selectedDetectors,
  onToggleDetector,
  availableDetectorCount,
  detectorCatalogCount,
  onExpandAllCards,
  onCollapseAllCards,
  expandedCount,
  methodCardCount,
  onReloadOutputs,
  isReloadDisabled,
  showProtocolJump,
  showInsightJump,
  showMethodContextJump,
}: LabPanelAdvancedControlsProps) {
  return (
    <div className="space-y-4 text-sm text-slate-200">
      {isPilotMatrixSelectedCase ? (
        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-lg border border-white/10 bg-slate-950/35 p-4">
            <div className="text-xs uppercase tracking-wide text-slate-400">Cleaning lens</div>
            <div className="mt-3">
              <CleaningLensToggle value={lens} options={lensOptions} onChange={onLensChange} />
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
                onClick={onApplyQuickRead}
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
                onClick={onApplyDeepReview}
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
            {presetStatusMessage ? (
              <p className="mt-2 text-xs text-emerald-300">{presetStatusMessage}</p>
            ) : null}
          </div>
        </div>
      ) : null}

      {hasMultipleCases ? (
        <div className="rounded-lg border border-white/10 bg-slate-950/35 p-4">
          <div className="text-xs uppercase tracking-wide text-slate-400">Case override</div>
          <select
            value={selectedCaseKey ?? ""}
            onChange={(event) => onSelectedCaseKeyChange(event.target.value)}
            className="mt-3 w-full rounded-md border border-white/15 bg-slate-950/40 px-3 py-2 text-sm text-slate-100"
          >
            {caseOptions.map((item) => (
              <option key={item.key} value={item.key}>
                {item.label}
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
              onChange={(event) => onSelectedLlmCampaignAChange(event.target.value)}
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
              onChange={(event) => onSelectedLlmCampaignBChange(event.target.value)}
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
            Available outputs: {availableDetectorCount}/{detectorCatalogCount}
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
                        onChange={() => onToggleDetector(detector.id)}
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
              onClick={onExpandAllCards}
              className="rounded-md border border-white/20 bg-slate-900/60 px-2 py-1 text-xs text-slate-100 transition hover:border-white/40"
            >
              Expand all ({expandedCount}/{methodCardCount} expanded)
            </button>
            <button
              type="button"
              onClick={onCollapseAllCards}
              className="rounded-md border border-white/20 bg-slate-900/60 px-2 py-1 text-xs text-slate-100 transition hover:border-white/40"
            >
              Collapse all ({expandedCount}/{methodCardCount} expanded)
            </button>
            <button
              type="button"
              onClick={onReloadOutputs}
              disabled={isReloadDisabled}
              className="rounded-md border border-white/10 bg-slate-950/40 px-2 py-1 text-xs text-slate-300 transition hover:border-white/25 hover:text-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Reload outputs
            </button>
          </div>
          <div className="mt-3 rounded-md border border-white/10 bg-slate-900/35 px-3 py-2 text-xs text-slate-300">
            Working set: {methodCardCount} cards | {expandedCount} expanded
          </div>
        </div>

        <div className="rounded-lg border border-white/10 bg-slate-950/35 p-4">
          <div className="text-xs uppercase tracking-wide text-slate-400">Jump to section</div>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-300">
            {showProtocolJump ? (
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
            {showInsightJump ? (
              <a
                className="underline decoration-white/30 underline-offset-2 hover:text-slate-100"
                href="#lab-insight-lens"
              >
                Insight lens
              </a>
            ) : null}
            {showMethodContextJump ? (
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
  )
}
