import type { Ref } from "react"
import { copy } from "../lib/copy"

export type ExecBriefData = {
  companyName: string
  ticker: string
  startYear: number | null
  endYear: number | null
  largestDriftYear: number | null
  prevYear: number | null
  summary: string
  topRisers: string[]
  topFallers: string[]
  driftValues: Array<number | null>
  provenanceLine: string
}

type ExecBriefCardProps = {
  data: ExecBriefData
  svgRef?: Ref<SVGSVGElement>
}

const WIDTH = 1200
const HEIGHT = 630
const MARGIN = 40
const FONT_FAMILY = "system-ui, -apple-system, Segoe UI, sans-serif"

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

  const summaryLines = wrapText(data.summary, 64).slice(0, 3)
  const sparkWidth = 420
  const sparkHeight = 120
  const sparkPath = buildSparklinePath(data.driftValues, sparkWidth, sparkHeight)

  const risers = data.topRisers.slice(0, 5)
  const fallers = data.topFallers.slice(0, 5)

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
        y={60}
        fontFamily={FONT_FAMILY}
        fontSize={32}
        fontWeight={600}
        fill="#111827"
      >
        {copy.export.title}
      </text>
      <text
        x={MARGIN}
        y={96}
        fontFamily={FONT_FAMILY}
        fontSize={22}
        fill="#111827"
      >
        {copy.export.subtitleLine({ company: data.companyName, ticker: data.ticker })}
      </text>
      {coverageLine ? (
        <text
          x={MARGIN}
          y={124}
          fontFamily={FONT_FAMILY}
          fontSize={16}
          fill="#6b7280"
        >
          {coverageLine}
        </text>
      ) : null}

      <text
        x={MARGIN}
        y={176}
        fontFamily={FONT_FAMILY}
        fontSize={18}
        fontWeight={600}
        fill="#111827"
      >
        {largestDriftLine}
      </text>

      {summaryLines.map((line, index) => (
        <text
          key={`summary-${index}`}
          x={MARGIN}
          y={206 + index * 22}
          fontFamily={FONT_FAMILY}
          fontSize={16}
          fill="#374151"
        >
          {line}
        </text>
      ))}

      <g transform={`translate(${WIDTH - sparkWidth - MARGIN}, 160)`}>
        <rect width={sparkWidth} height={sparkHeight} fill="#f9fafb" stroke="#e5e7eb" />
        {sparkPath ? (
          <path d={sparkPath} fill="none" stroke="#111827" strokeWidth={2} />
        ) : null}
      </g>

      <text
        x={MARGIN}
        y={340}
        fontFamily={FONT_FAMILY}
        fontSize={16}
        fontWeight={600}
        fill="#111827"
      >
        {copy.termShifts.risersLabel}
      </text>
      {risers.map((term, index) => (
        <text
          key={`riser-${term}-${index}`}
          x={MARGIN}
          y={366 + index * 22}
          fontFamily={FONT_FAMILY}
          fontSize={14}
          fill="#374151"
        >
          • {term}
        </text>
      ))}

      <text
        x={WIDTH / 2}
        y={340}
        fontFamily={FONT_FAMILY}
        fontSize={16}
        fontWeight={600}
        fill="#111827"
      >
        {copy.termShifts.fallersLabel}
      </text>
      {fallers.map((term, index) => (
        <text
          key={`faller-${term}-${index}`}
          x={WIDTH / 2}
          y={366 + index * 22}
          fontFamily={FONT_FAMILY}
          fontSize={14}
          fill="#374151"
        >
          • {term}
        </text>
      ))}

      <text
        x={MARGIN}
        y={HEIGHT - 30}
        fontFamily={FONT_FAMILY}
        fontSize={12}
        fill="#6b7280"
      >
        {data.provenanceLine}
      </text>
    </svg>
  )
}
