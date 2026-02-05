import type { LabCleaningLens } from "../lib/labTypes"

const LABELS: Record<LabCleaningLens, string> = {
  raw: "Raw",
  stage1_clean: "Stage 1 Clean",
  deboilerplated: "Deboilerplated",
  structure_aware: "Structure Aware",
}

export type CleaningLensOption = {
  value: LabCleaningLens
  disabled?: boolean
}

type CleaningLensToggleProps = {
  value: LabCleaningLens
  options: CleaningLensOption[]
  onChange: (next: LabCleaningLens) => void
}

export default function CleaningLensToggle({
  value,
  options,
  onChange,
}: CleaningLensToggleProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((option) => {
        const isActive = option.value === value
        const isDisabled = option.disabled
        return (
          <button
            key={option.value}
            type="button"
            className={`rounded-full border px-3 py-1 text-xs transition ${
              isActive
                ? "border-sky-300/70 bg-sky-400/20 text-sky-100"
                : "border-white/15 text-slate-300 hover:border-white/30 hover:text-slate-100"
            } ${isDisabled ? "cursor-not-allowed opacity-50" : ""}`}
            onClick={() => {
              if (!isDisabled) {
                onChange(option.value)
              }
            }}
            disabled={isDisabled}
          >
            {LABELS[option.value]}
          </button>
        )
      })}
    </div>
  )
}
