import { useMemo } from "react"
import { copy } from "../lib/copy"

type DriftTimelineProps = {
  years: number[]
  drift_vs_prev: Array<number | null>
  drift_ci_low?: Array<number | null>
  drift_ci_high?: Array<number | null>
  boilerplate_score?: Array<number | null>
}

type DriftPoint = {
  year: number
  index: number
  value: number | null
  ciLow: number | null
  ciHigh: number | null
  boilerplate: number | null
  prevYear?: number
  x: number
  y: number
}

function formatValue(value: number): string {
  return value.toFixed(2)
}

export default function DriftTimeline({
  years,
  drift_vs_prev,
  drift_ci_low,
  drift_ci_high,
  boilerplate_score,
}: DriftTimelineProps) {
  const width = 720
  const height = 200
  const paddingX = 36
  const paddingTop = 20
  const paddingBottom = 32
  const chartWidth = width - paddingX * 2
  const chartHeight = height - paddingTop - paddingBottom
  const baselineY = paddingTop + chartHeight

  const points = useMemo<DriftPoint[]>(() => {
    const values = drift_vs_prev
      .slice(0, years.length)
      .filter((value): value is number => value !== null)
    const maxValue = values.length > 0 ? Math.max(...values) : 1
    const minValue = 0
    const range = Math.max(maxValue - minValue, 0.1)

    return years.map((year, index) => {
      const value = drift_vs_prev[index] ?? null
      const ciLow = drift_ci_low?.[index] ?? null
      const ciHigh = drift_ci_high?.[index] ?? null
      const boilerplate = boilerplate_score?.[index] ?? null
      const prevYear = index > 0 ? years[index - 1] : undefined
      const x =
        years.length > 1
          ? paddingX + (index / (years.length - 1)) * chartWidth
          : paddingX + chartWidth / 2
      const y =
        value === null
          ? baselineY
          : paddingTop + ((maxValue - value) / range) * chartHeight

      return {
        year,
        index,
        value,
        ciLow,
        ciHigh,
        boilerplate,
        prevYear,
        x,
        y,
      }
    })
  }, [
    years,
    drift_vs_prev,
    drift_ci_low,
    drift_ci_high,
    boilerplate_score,
    chartWidth,
    chartHeight,
    baselineY,
    paddingTop,
    paddingX,
  ])

  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full min-w-130"
        role="img"
        aria-label={copy.driftTimeline.title}
      >
        <line
          x1={paddingX}
          y1={baselineY}
          x2={width - paddingX}
          y2={baselineY}
          stroke="#e5e7eb"
          strokeWidth={1}
        />

        {points.slice(1).map((point, index) => {
          const prev = points[index]
          if (prev.value === null || point.value === null) return null
          return (
            <line
              key={`segment-${prev.year}-${point.year}`}
              x1={prev.x}
              y1={prev.y}
              x2={point.x}
              y2={point.y}
              stroke="#111827"
              strokeWidth={2}
            />
          )
        })}

        {points.map((point) => {
          const tooltipLines = [
            copy.driftTimeline.tooltip.title({ year: point.year }),
            point.value !== null && point.prevYear !== undefined
              ? copy.driftTimeline.tooltip.driftLine({
                  prevYear: point.prevYear,
                  drift: formatValue(point.value),
                })
              : null,
            point.ciLow !== null && point.ciHigh !== null
              ? copy.driftTimeline.tooltip.ciLine({
                  low: formatValue(point.ciLow),
                  high: formatValue(point.ciHigh),
                })
              : null,
            point.boilerplate !== null
              ? copy.driftTimeline.tooltip.boilerplateLine({
                  boilerplatePct: formatValue(point.boilerplate),
                })
              : null,
          ]
            .filter(Boolean)
            .join("\n")

          return (
            <g key={`point-${point.year}`}>
              <title>{tooltipLines}</title>
              <circle
                cx={point.x}
                cy={point.y}
                r={point.value === null ? 5 : 6}
                fill={point.value === null ? "#9ca3af" : "#111827"}
              />
            </g>
          )
        })}

        {points.map((point) => (
          <text
            key={`label-${point.year}`}
            x={point.x}
            y={height - 10}
            textAnchor="middle"
            fontSize={11}
            fill="#6b7280"
          >
            {point.year}
          </text>
        ))}
      </svg>
    </div>
  )
}
