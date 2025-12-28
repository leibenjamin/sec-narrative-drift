import { useMemo } from "react"
import { copy } from "../lib/copy"

type ActiveCell = {
  row: number
  col: number
}

type SimilarityHeatmapProps = {
  years: number[]
  cosineSimilarity: number[][]
  onSelectPair: (fromYear: number, toYear: number) => void
  activeCell?: ActiveCell | null
}

function formatValue(value: number): string {
  return value.toFixed(2)
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

export default function SimilarityHeatmap({
  years,
  cosineSimilarity,
  onSelectPair,
  activeCell,
}: SimilarityHeatmapProps) {
  const cellSize = years.length > 12 ? 20 : 26
  const leftLabelWidth = 48
  const topLabelHeight = 22
  const gridSize = years.length * cellSize
  const width = leftLabelWidth + gridSize + 8
  const height = topLabelHeight + gridSize + 8

  const cells = useMemo(
    () =>
      years.flatMap((rowYear, rowIndex) =>
        years.map((colYear, colIndex) => {
          const rawValue = cosineSimilarity?.[rowIndex]?.[colIndex]
          const value = typeof rawValue === "number" ? rawValue : null
          const isDiagonal = rowIndex === colIndex
          const normalized = value === null ? 0 : clamp(value, 0, 1)
          const shade = Math.round(235 - normalized * 120)
          const fill = isDiagonal
            ? "#e5e7eb"
            : value === null
              ? "#f3f4f6"
              : `rgb(${shade}, ${shade}, ${shade})`

          return {
            rowYear,
            colYear,
            rowIndex,
            colIndex,
            value,
            fill,
            isDiagonal,
            x: leftLabelWidth + colIndex * cellSize,
            y: topLabelHeight + rowIndex * cellSize,
          }
        })
      ),
    [years, cosineSimilarity, cellSize, leftLabelWidth, topLabelHeight]
  )

  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full min-w-130"
        role="img"
        aria-label={copy.heatmap.title}
      >
        {years.map((year, index) => (
          <text
            key={`col-${year}`}
            x={leftLabelWidth + index * cellSize + cellSize / 2}
            y={topLabelHeight - 6}
            textAnchor="middle"
            fontSize={11}
            fill="#6b7280"
          >
            {year}
          </text>
        ))}

        {years.map((year, index) => (
          <text
            key={`row-${year}`}
            x={leftLabelWidth - 6}
            y={topLabelHeight + index * cellSize + cellSize / 2 + 4}
            textAnchor="end"
            fontSize={11}
            fill="#6b7280"
          >
            {year}
          </text>
        ))}

        {cells.map((cell) => {
          const isActive =
            activeCell?.row === cell.rowIndex && activeCell?.col === cell.colIndex
          const stroke = isActive
            ? "#111827"
            : cell.isDiagonal
              ? "#9ca3af"
              : "#f9fafb"
          const strokeWidth = isActive ? 2 : 1
          const tooltipLines = [
            copy.heatmap.hoverTitle({
              fromYear: cell.rowYear,
              toYear: cell.colYear,
            }),
            cell.value !== null
              ? copy.heatmap.cosineLine({ value: formatValue(cell.value) })
              : null,
            cell.value !== null
              ? copy.heatmap.driftLine({
                  drift: formatValue(1 - cell.value),
                })
              : null,
          ]
            .filter(Boolean)
            .join("\n")

          return (
            <g key={`cell-${cell.rowYear}-${cell.colYear}`}>
              <title>{tooltipLines}</title>
              <rect
                x={cell.x}
                y={cell.y}
                width={cellSize}
                height={cellSize}
                fill={cell.fill}
                stroke={stroke}
                strokeWidth={strokeWidth}
                className="cursor-pointer"
                onClick={() => {
                  onSelectPair(cell.rowYear, cell.colYear)
                }}
              />
            </g>
          )
        })}
      </svg>
    </div>
  )
}
