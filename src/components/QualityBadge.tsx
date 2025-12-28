import { copy } from "../lib/copy"

type QualityLevel = "high" | "medium" | "low" | "unknown"

type QualityBadgeProps = {
  level: QualityLevel
  onClick?: () => void
}

const badgeStyles: Record<QualityLevel, { className: string; label: string }> = {
  high: {
    className: "border-emerald-200 bg-emerald-50 text-emerald-800",
    label: copy.dataQuality.badges.high,
  },
  medium: {
    className: "border-amber-200 bg-amber-50 text-amber-800",
    label: copy.dataQuality.badges.medium,
  },
  low: {
    className: "border-rose-200 bg-rose-50 text-rose-800",
    label: copy.dataQuality.badges.low,
  },
  unknown: {
    className: "border-slate-200 bg-slate-50 text-slate-700",
    label: copy.dataQuality.badges.skipped,
  },
}

export default function QualityBadge({ level, onClick }: QualityBadgeProps) {
  const { className, label } = badgeStyles[level]
  const text = `${copy.dataQuality.title}: ${label}`

  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium ${className}`}
      aria-label={text}
      title={copy.dataQuality.helper}
    >
      {text}
    </button>
  )
}
