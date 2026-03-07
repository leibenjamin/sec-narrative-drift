import type { LabOutput } from "../lib/labTypes"

type AgreementMatrixProps = {
  output: LabOutput | null
}

const DETECTOR_DISPLAY_NAMES: Record<string, string> = {
  det_logodds_terms_v1: "Log-odds terms",
  det_jsd_ngrams_v1: "JSD n-grams",
  det_minhash_boilerplate_v1: "Minhash boilerplate",
  det_winnowing_fingerprint_v1: "Winnowing fingerprints",
  det_structure_artifacts_v1: "Structure artifacts",
  det_llm_delta_brief_v1: "AI delta brief",
  det_llm_excerpt_picker_v1: "AI excerpt picker",
  det_rbo_agreement_v1: "Agreement (RBO)",
}

function formatDetectorName(raw: string): string {
  return DETECTOR_DISPLAY_NAMES[raw] ?? raw.replace(/^det_/, "").replace(/_v\d+$/, "").replace(/_/g, " ")
}

function cellColorClass(value: number | null | undefined, isDiagonal: boolean): string {
  if (isDiagonal) return "text-slate-500"
  if (value === null || value === undefined) return ""
  if (value >= 0.7) return "text-emerald-300"
  if (value <= 0.3) return "text-amber-300"
  return ""
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
        Agreement matrix not available for this filing pair and lens combination.
      </div>
    )
  }

  if (!detectors.length || !matrix.length) {
    return (
      <div className="rounded-lg border border-white/10 bg-white/5 p-4 text-xs text-slate-300">
        Agreement matrix requires results from at least two methods.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-white/10 bg-white/5">
      <table className="min-w-full text-left text-xs text-slate-200">
        <thead className="bg-white/5 text-[11px] uppercase tracking-wide text-slate-400">
          <tr>
            <th className="px-3 py-2">Method</th>
            {detectors.map((det) => (
              <th key={det} className="px-3 py-2" title={det}>
                {formatDetectorName(det)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, rowIdx) => (
            <tr key={detectors[rowIdx] ?? rowIdx} className="border-t border-white/10">
              <td className="px-3 py-2 font-medium text-slate-300" title={detectors[rowIdx]}>
                {formatDetectorName(detectors[rowIdx] ?? "")}
              </td>
              {row.map((cell, colIdx) => (
                <td key={`${rowIdx}-${colIdx}`} className={`px-3 py-2 ${cellColorClass(cell, rowIdx === colIdx)}`}>
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
