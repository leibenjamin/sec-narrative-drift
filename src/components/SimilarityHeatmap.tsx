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

  const legendRange = useMemo(() => {
    let minValue = Infinity
    let maxValue = -Infinity

    for (const cell of cells) {
      if (typeof cell.value !== "number") continue
      minValue = Math.min(minValue, cell.value)
      maxValue = Math.max(maxValue, cell.value)
    }

    if (!Number.isFinite(minValue) || !Number.isFinite(maxValue)) {
      return { min: 0, max: 1 }
    }

    return { min: minValue, max: maxValue }
  }, [cells])

  const selectedLabel = useMemo(() => {
    if (!activeCell) return null
    const fromYear = years[activeCell.row]
    const toYear = years[activeCell.col]
    if (fromYear === undefined || toYear === undefined) return null
    return copy.heatmap.selectedLabel({ fromYear, toYear })
  }, [activeCell, years])

  const legendGradient = "linear-gradient(90deg, #f3f4f6 0%, #6b7280 100%)"

  return (
    <div className="space-y-3 rounded-lg border border-white/10 bg-slate-900/40 p-3">
      <div className="space-y-2 text-xs text-slate-300">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span>{copy.heatmap.microcopy}</span>
          {selectedLabel ? (
            <span className="rounded-full border border-sky-400/40 bg-sky-400/10 px-2 py-0.5 text-sky-100">
              {selectedLabel}
            </span>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-slate-400">
            {copy.heatmap.legendMin({ value: formatValue(legendRange.min) })}
          </span>
          <span
            className="h-2 w-28 rounded-sm border border-slate-500/40"
            style={{ background: legendGradient }}
          />
          <span className="text-slate-400">
            {copy.heatmap.legendMax({ value: formatValue(legendRange.max) })}
          </span>
        </div>
      </div>

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
            const borderColor = isActive
              ? "#38bdf8"
              : cell.isDiagonal
                ? "#94a3b8"
                : "#e2e8f0"
            const borderWidth = isActive ? 2 : 1
            const isSelectable = !cell.isDiagonal && cell.value !== null
            const primaryHint = cell.isDiagonal
              ? copy.heatmap.sameYearHint
              : cell.value === null
                ? copy.heatmap.noDataHint
                : copy.heatmap.clickHint({
                    fromYear: cell.rowYear,
                    toYear: cell.colYear,
                  })
            const tooltipLines = [
              primaryHint,
              cell.value !== null && !cell.isDiagonal
                ? copy.heatmap.cosineLine({ value: formatValue(cell.value) })
                : null,
              cell.value !== null && !cell.isDiagonal
                ? copy.heatmap.driftLine({
                    drift: formatValue(1 - cell.value),
                  })
                : null,
            ]
              .filter(Boolean)
              .join("\n")

            const ariaLabel = cell.isDiagonal
              ? copy.heatmap.sameYearAria({ year: cell.rowYear })
              : copy.heatmap.ariaLabel({
                  fromYear: cell.rowYear,
                  toYear: cell.colYear,
                  value:
                    cell.value !== null ? formatValue(cell.value) : copy.heatmap.naLabel,
                })

            return (
              <foreignObject
                key={`cell-${cell.rowYear}-${cell.colYear}`}
                x={cell.x}
                y={cell.y}
                width={cellSize}
                height={cellSize}
              >
                <button
                  type="button"
                  title={tooltipLines}
                  aria-label={ariaLabel}
                  aria-disabled={!isSelectable}
                  tabIndex={isSelectable ? 0 : -1}
                  onClick={() => {
                    if (!isSelectable) return
                    onSelectPair(cell.rowYear, cell.colYear)
                  }}
                  style={{
                    width: "100%",
                    height: "100%",
                    padding: 0,
                    margin: 0,
                    borderRadius: 0,
                    border: `${borderWidth}px solid ${borderColor}`,
                    backgroundColor: cell.fill,
                    cursor: isSelectable ? "pointer" : "not-allowed",
                    boxShadow: isActive ? "0 0 0 1px #111827" : "none",
                  }}
                />
              </foreignObject>
            )
          })}
        </svg>
      </div>
    </div>
  )
}
