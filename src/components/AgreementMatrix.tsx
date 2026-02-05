import type { LabOutput } from "../lib/labTypes"

type AgreementMatrixProps = {
  output: LabOutput | null
}

export default function AgreementMatrix({ output }: AgreementMatrixProps) {
  const detectors = Array.isArray(output?.artifacts?.detectors)
    ? (output?.artifacts.detectors as string[])
    : []
  const matrix = Array.isArray(output?.artifacts?.matrix)
    ? (output?.artifacts.matrix as Array<Array<number | null>>)
    : []

  if (!output) {
    return (
      <div className="rounded-lg border border-white/10 bg-white/5 p-4 text-xs text-slate-300">
        No agreement matrix available.
      </div>
    )
  }

  if (!detectors.length || !matrix.length) {
    return (
      <div className="rounded-lg border border-white/10 bg-white/5 p-4 text-xs text-slate-300">
        Agreement matrix requires at least two ranked lists.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-white/10 bg-white/5">
      <table className="min-w-full text-left text-xs text-slate-200">
        <thead className="bg-white/5 text-[11px] uppercase tracking-wide text-slate-400">
          <tr>
            <th className="px-3 py-2">Detector</th>
            {detectors.map((det) => (
              <th key={det} className="px-3 py-2">
                {det}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, rowIdx) => (
            <tr key={detectors[rowIdx] ?? rowIdx} className="border-t border-white/10">
              <td className="px-3 py-2 text-slate-300">{detectors[rowIdx]}</td>
              {row.map((cell, colIdx) => (
                <td key={`${rowIdx}-${colIdx}`} className="px-3 py-2">
                  {cell === null || cell === undefined ? "-" : cell.toFixed(3)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
