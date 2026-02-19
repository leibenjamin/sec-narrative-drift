import { copy } from "../lib/copy"

type CaptureLevel = "high" | "medium" | "low"

type SectionCaptureBadgeProps = {
  confidence?: number | null
}

const badgeStyles: Record<CaptureLevel, { className: string; label: string }> = {
  high: {
    className: "border-emerald-400/40 bg-emerald-400/15 text-emerald-100",
    label: "High",
  },
  medium: {
    className: "border-amber-400/40 bg-amber-400/15 text-amber-100",
    label: "Medium",
  },
  low: {
    className: "border-rose-400/40 bg-rose-400/15 text-rose-100",
    label: "Low",
  },
}

function resolveLevel(confidence: number): CaptureLevel {
  if (confidence >= 0.8) return "high"
  if (confidence >= 0.55) return "medium"
  return "low"
}

export default function SectionCaptureBadge({ confidence }: SectionCaptureBadgeProps) {
  if (typeof confidence !== "number") return null
  const level = resolveLevel(confidence)
  const { className, label } = badgeStyles[level]
  const text = `${copy.sectionCapture.label}: ${label}`
  const tooltipLines = [
    copy.sectionCapture.tooltipTitle,
    copy.sectionCapture.levels[level],
    copy.sectionCapture.footer,
    copy.sectionCapture.dryLine,
  ].filter(Boolean)

  return (
    <span
      className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium ${className}`}
      aria-label={text}
      title={tooltipLines.join("\n")}
    >
      {text}
    </span>
  )
}
