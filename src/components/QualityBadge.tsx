import { copy } from "../lib/copy"

type QualityLevel = "high" | "medium" | "low" | "unknown"

type QualityBadgeProps = {
  level: QualityLevel
  onClick?: () => void
}

const badgeStyles: Record<QualityLevel, { className: string; label: string }> = {
  high: {
    className: "border-emerald-400/40 bg-emerald-400/15 text-emerald-100",
    label: copy.dataQuality.badges.high,
  },
  medium: {
    className: "border-amber-400/40 bg-amber-400/15 text-amber-100",
    label: copy.dataQuality.badges.medium,
  },
  low: {
    className: "border-rose-400/40 bg-rose-400/15 text-rose-100",
    label: copy.dataQuality.badges.low,
  },
  unknown: {
    className: "border-slate-400/30 bg-white/5 text-slate-200",
    label: copy.dataQuality.badges.skipped,
  },
}

export default function QualityBadge({ level, onClick }: QualityBadgeProps) {
  const { className, label } = badgeStyles[level]
  const text = `${copy.dataQuality.title}: ${label}`

  if (!onClick) {
    return (
      <span
        className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium ${className}`}
        aria-label={text}
        title={copy.dataQuality.helper}
      >
        {text}
      </span>
    )
  }

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
