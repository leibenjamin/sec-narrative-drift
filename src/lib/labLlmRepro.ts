import { withBase } from "./paths"
import type { LabCleaningLens } from "./labTypes"

const LLM_DETECTORS = new Set<string>([
  "det_llm_delta_brief_v1",
  "det_llm_excerpt_picker_v1",
])

const PROJECT_INSTRUCTIONS_PATH = withBase(
  "data/sec_narrative_drift_lab/llm_project_instructions_v1.txt"
)

let projectInstructionsPromise: Promise<string> | null = null

const FALLBACK_PROJECT_INSTRUCTIONS = [
  "Output must be JSON only (no markdown, no backticks, no commentary).",
  "Output exactly one top-level JSON object.",
  "No extra top-level keys.",
  "Never output section_id.",
  "Use only attached input file and thread starter prompt.",
  "provenance.input_file must match attached input path exactly.",
  "provenance.model_provider and provenance.model_name are required.",
  'Delta citations must use ASCII format: "YYYY para NN".',
].join("\n")

type LlmThreadStarterContext = {
  ticker: string
  yearFrom: number
  yearTo: number
  detectorId: string
  lens: LabCleaningLens
  inputFile: string
  expectedOutputPath: string | null
  sourceId?: string
}

function normalizeInputFile(inputFile: string): string {
  const trimmed = inputFile.trim().replace(/\\/g, "/")
  if (!trimmed) return inputFile
  if (trimmed.startsWith("inputs/")) return trimmed
  const filename = trimmed.split("/").pop()
  if (!filename) return trimmed
  return `inputs/${filename}`
}

export function isLlmDetector(detectorId: string): boolean {
  return LLM_DETECTORS.has(detectorId)
}

export function buildDefaultLlmInputFile(
  ticker: string,
  yearFrom: number,
  yearTo: number,
  lens: LabCleaningLens
): string {
  return `inputs/${ticker.toUpperCase()}_${yearFrom}_${yearTo}_focuspack_${lens}.json`
}

export function buildLlmThreadStarterText(context: LlmThreadStarterContext): string {
  const inputFile = normalizeInputFile(context.inputFile)
  const sourceId = context.sourceId ?? "edgar"
  const lines: string[] = []
  lines.push(
    `Thread Title: ${context.ticker.toUpperCase()} ${context.yearFrom}-${context.yearTo} ${context.detectorId} (focuspack_${context.lens})`
  )
  lines.push("")
  lines.push(`Attach this input file: ${inputFile}`)
  if (context.expectedOutputPath) {
    lines.push(`Save output to: ${context.expectedOutputPath}`)
  }
  lines.push("")
  lines.push("STRICT OUTPUT RULES")
  lines.push("- JSON ONLY.")
  lines.push("- Output exactly one top-level JSON object.")
  lines.push("- Top-level keys must be exactly the lab envelope keys.")
  lines.push("- No extra top-level keys.")
  lines.push("- Never output section_id.")
  lines.push("- Numeric fields must remain numeric (no quoted numbers).")
  lines.push("- provenance.input_file must match attached input path exactly.")
  lines.push("- provenance.model_provider is required.")
  lines.push("- provenance.model_name is required.")
  lines.push("- provenance.run_label is optional.")
  lines.push("- No extra provenance keys beyond input_file, model_provider, model_name, run_label.")
  lines.push("- paragraph_idx must be FULL index via focuspack_meta mappings.")
  lines.push("- Snippets must be verbatim and <= 350 chars.")
  lines.push("- highlights must be present and non-empty.")
  lines.push('- Delta citations must be ASCII-only format "YYYY para NN".')
  lines.push('- Never use pilcrow-style citation symbols; use "YYYY para NN" only.')
  lines.push("")
  lines.push("JSON SKELETON")
  lines.push("{")
  lines.push('  "lab_schema_version": "1.0",')
  lines.push(`  "detector_id": "${context.detectorId}",`)
  lines.push(`  "cleaning_lens": "${context.lens}",`)
  lines.push(`  "source_id": "${sourceId}",`)
  lines.push(`  "ticker": "${context.ticker.toUpperCase()}",`)
  lines.push('  "section": "10k_item1a",')
  lines.push(`  "year_from": ${context.yearFrom},`)
  lines.push(`  "year_to": ${context.yearTo},`)
  if (context.detectorId === "det_llm_delta_brief_v1") {
    lines.push('  "artifacts": { "delta_brief": "<summary>" },')
  } else {
    lines.push('  "artifacts": { "selected_prev": [], "selected_curr": [] },')
  }
  lines.push('  "evidence": [],')
  lines.push('  "metrics": {')
  lines.push('    "drift_score": null,')
  lines.push('    "confidence": 0.50,')
  lines.push('    "coverage": null,')
  lines.push('    "warnings": ["Focuspack is a subset; verify in full compare pane."]')
  lines.push("  },")
  lines.push('  "provenance": {')
  lines.push(`    "input_file": "${inputFile}",`)
  lines.push('    "model_provider": "<provider>",')
  lines.push('    "model_name": "<model>",')
  lines.push('    "run_label": "<optional-run-label>"')
  lines.push("  }")
  lines.push("}")
  return lines.join("\n")
}

export async function loadLlmProjectInstructionsText(): Promise<string> {
  if (!projectInstructionsPromise) {
    projectInstructionsPromise = fetch(PROJECT_INSTRUCTIONS_PATH, {
      cache: "no-store",
      headers: { Accept: "text/plain" },
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`instructions fetch failed: ${response.status}`)
        }
        return response.text()
      })
      .then((text) => {
        const trimmed = text.trim()
        return trimmed || FALLBACK_PROJECT_INSTRUCTIONS
      })
      .catch(() => FALLBACK_PROJECT_INSTRUCTIONS)
  }
  return projectInstructionsPromise
}
