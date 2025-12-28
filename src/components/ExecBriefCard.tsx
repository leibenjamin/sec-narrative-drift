import type { Ref } from "react"
import { copy } from "../lib/copy"

type QualityLevel = "high" | "medium" | "low" | "unknown"

export type ExecBriefData = {
  companyName: string
  ticker: string
  startYear: number | null
  endYear: number | null
  largestDriftYear: number | null
  prevYear: number | null
  largestDriftValue: number | null
  largestDriftCiLow: number | null
  largestDriftCiHigh: number | null
  summary: string
  topRisers: string[]
  topFallers: string[]
  driftValues: Array<number | null>
  provenanceLine: string
  dataQualityLevel: QualityLevel
}

type ExecBriefCardProps = {
  data: ExecBriefData
  svgRef?: Ref<SVGSVGElement>
}

const WIDTH = 1200
const HEIGHT = 630
const MARGIN = 40
const FONT_FAMILY = "system-ui, -apple-system, Segoe UI, sans-serif"

function formatValue(value: number | null): string {
  if (value === null || Number.isNaN(value)) return "-"
  return value.toFixed(2)
}

function wrapText(text: string, maxChars: number): string[] {
  const words = text.split(/\s+/).filter(Boolean)
  if (words.length === 0) return []

  const lines: string[] = []
  let current = words[0]

  words.slice(1).forEach((word) => {
    if ((current + " " + word).length <= maxChars) {
      current += ` ${word}`
    } else {
      lines.push(current)
      current = word
    }
  })

  lines.push(current)
  return lines
}

function buildSparklinePath(values: Array<number | null>, width: number, height: number): string {
  const numericValues = values.filter((value): value is number => value !== null)
  if (numericValues.length === 0) return ""

  const minValue = Math.min(...numericValues)
  const maxValue = Math.max(...numericValues)
  const range = Math.max(maxValue - minValue, 0.01)
  const padding = 8
  const step = values.length > 1 ? (width - padding * 2) / (values.length - 1) : 0

  let path = ""
  let started = false

  values.forEach((value, index) => {
    if (value === null) {
      started = false
      return
    }
    const x = padding + step * index
    const y = padding + (1 - (value - minValue) / range) * (height - padding * 2)
    path += `${started ? " L" : "M"} ${x.toFixed(2)} ${y.toFixed(2)}`
    started = true
  })

  return path
}

function getQualityBadge(level: QualityLevel): {
  label: string
  fill: string
  stroke: string
  text: string
} {
  switch (level) {
    case "high":
      return {
        label: copy.dataQuality.badges.high,
        fill: "#ecfdf3",
        stroke: "#a7f3d0",
        text: "#047857",
      }
    case "medium":
      return {
        label: copy.dataQuality.badges.medium,
        fill: "#fffbeb",
        stroke: "#fcd34d",
        text: "#92400e",
      }
    case "low":
      return {
        label: copy.dataQuality.badges.low,
        fill: "#fff1f2",
        stroke: "#fecdd3",
        text: "#be123c",
      }
    default:
      return {
        label: copy.dataQuality.badges.skipped,
        fill: "#f8fafc",
        stroke: "#e2e8f0",
        text: "#475569",
      }
  }
}

export default function ExecBriefCard({ data, svgRef }: ExecBriefCardProps) {
  const coverageLine =
    data.startYear && data.endYear
      ? copy.export.coverageLine({ startYear: data.startYear, endYear: data.endYear })
      : ""

  const largestDriftLine =
    data.largestDriftYear && data.prevYear
      ? copy.export.bullets.largestDrift({
          year: data.largestDriftYear,
          prev: data.prevYear,
        })
      : `${copy.company.callouts.largestDrift.label}: -`

  const driftValueLine =
    data.largestDriftValue !== null
      ? data.largestDriftCiLow !== null && data.largestDriftCiHigh !== null
        ? copy.export.driftLineWithCi({
            drift: formatValue(data.largestDriftValue),
            low: formatValue(data.largestDriftCiLow),
            high: formatValue(data.largestDriftCiHigh),
          })
        : copy.export.driftLine({ drift: formatValue(data.largestDriftValue) })
      : copy.export.driftLine({ drift: "-" })

  const summaryLines = wrapText(data.summary, 62).slice(0, 2)
  const sparkWidth = 420
  const sparkHeight = 130
  const sparkPath = buildSparklinePath(data.driftValues, sparkWidth, sparkHeight)

  const risers = data.topRisers.slice(0, 3)
  const fallers = data.topFallers.slice(0, 3)

  const quality = getQualityBadge(data.dataQualityLevel)
  const qualityText = `${copy.export.qualityLabel}: ${quality.label}`
  const qualityWidth = 260
  const qualityHeight = 28
  const qualityX = WIDTH - MARGIN - qualityWidth
  const qualityY = 36

  const keyBoxX = MARGIN
  const keyBoxY = 250
  const keyBoxWidth = 640
  const keyBoxHeight = 210
  const keyBoxPadding = 18
  const columnGap = 24
  const columnWidth = (keyBoxWidth - keyBoxPadding * 2 - columnGap) / 2
  const leftColumnX = keyBoxX + keyBoxPadding
  const rightColumnX = leftColumnX + columnWidth + columnGap

  return (
    <svg
      ref={svgRef}
      width={WIDTH}
      height={HEIGHT}
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label={copy.export.title}
    >
      <rect width={WIDTH} height={HEIGHT} fill="#ffffff" />

      <text
        x={MARGIN}
        y={54}
        fontFamily={FONT_FAMILY}
        fontSize={30}
        fontWeight={600}
        fill="#111827"
      >
        {copy.export.title}
      </text>
      <text
        x={MARGIN}
        y={88}
        fontFamily={FONT_FAMILY}
        fontSize={20}
        fill="#111827"
      >
        {copy.export.subtitleLine({ company: data.companyName, ticker: data.ticker })}
      </text>
      {coverageLine ? (
        <text
          x={MARGIN}
          y={114}
          fontFamily={FONT_FAMILY}
          fontSize={14}
          fill="#6b7280"
        >
          {coverageLine}
        </text>
      ) : null}

      <rect
        x={qualityX}
        y={qualityY}
        width={qualityWidth}
        height={qualityHeight}
        rx={qualityHeight / 2}
        fill={quality.fill}
        stroke={quality.stroke}
      />
      <text
        x={qualityX + 12}
        y={qualityY + 19}
        fontFamily={FONT_FAMILY}
        fontSize={12}
        fontWeight={600}
        fill={quality.text}
      >
        {qualityText}
      </text>

      <text
        x={MARGIN}
        y={154}
        fontFamily={FONT_FAMILY}
        fontSize={18}
        fontWeight={600}
        fill="#111827"
      >
        {largestDriftLine}
      </text>
      <text
        x={MARGIN}
        y={178}
        fontFamily={FONT_FAMILY}
        fontSize={14}
        fill="#374151"
      >
        {driftValueLine}
      </text>

      {summaryLines.map((line, index) => (
        <text
          key={`summary-${index}`}
          x={MARGIN}
          y={206 + index * 20}
          fontFamily={FONT_FAMILY}
          fontSize={14}
          fill="#4b5563"
        >
          {line}
        </text>
      ))}

      <text
        x={WIDTH - sparkWidth - MARGIN}
        y={140}
        fontFamily={FONT_FAMILY}
        fontSize={12}
        fill="#6b7280"
      >
        {copy.export.sparklineLabel}
      </text>
      <g transform={`translate(${WIDTH - sparkWidth - MARGIN}, 150)`}>
        <rect width={sparkWidth} height={sparkHeight} fill="#f8fafc" stroke="#e5e7eb" />
        {sparkPath ? (
          <path d={sparkPath} fill="none" stroke="#111827" strokeWidth={2} />
        ) : null}
      </g>

      <rect
        x={keyBoxX}
        y={keyBoxY}
        width={keyBoxWidth}
        height={keyBoxHeight}
        rx={16}
        fill="#f8fafc"
        stroke="#e5e7eb"
      />
      <text
        x={keyBoxX + keyBoxPadding}
        y={keyBoxY + 28}
        fontFamily={FONT_FAMILY}
        fontSize={14}
        fontWeight={600}
        fill="#111827"
      >
        {copy.export.keyChangesTitle}
      </text>
      <text
        x={leftColumnX}
        y={keyBoxY + 56}
        fontFamily={FONT_FAMILY}
        fontSize={12}
        fontWeight={600}
        fill="#111827"
      >
        {copy.termShifts.risersLabel}
      </text>
      {risers.map((term, index) => (
        <text
          key={`riser-${term}-${index}`}
          x={leftColumnX}
          y={keyBoxY + 80 + index * 20}
          fontFamily={FONT_FAMILY}
          fontSize={12}
          fill="#374151"
        >
          - {term}
        </text>
      ))}
      <text
        x={rightColumnX}
        y={keyBoxY + 56}
        fontFamily={FONT_FAMILY}
        fontSize={12}
        fontWeight={600}
        fill="#111827"
      >
        {copy.termShifts.fallersLabel}
      </text>
      {fallers.map((term, index) => (
        <text
          key={`faller-${term}-${index}`}
          x={rightColumnX}
          y={keyBoxY + 80 + index * 20}
          fontFamily={FONT_FAMILY}
          fontSize={12}
          fill="#374151"
        >
          - {term}
        </text>
      ))}

      <text
        x={MARGIN}
        y={HEIGHT - 58}
        fontFamily={FONT_FAMILY}
        fontSize={12}
        fill="#6b7280"
      >
        {copy.global.caveatLine}
      </text>
      <text
        x={MARGIN}
        y={HEIGHT - 40}
        fontFamily={FONT_FAMILY}
        fontSize={12}
        fill="#6b7280"
      >
        {copy.global.disclaimerLine}
      </text>
      <text
        x={MARGIN}
        y={HEIGHT - 20}
        fontFamily={FONT_FAMILY}
        fontSize={12}
        fill="#6b7280"
      >
        {data.provenanceLine}
      </text>
    </svg>
  )
}
