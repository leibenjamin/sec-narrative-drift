import { withBase } from "./paths"
import type { LabCleaningLens } from "./labTypes"

const LLM_DETECTORS = new Set<string>([
  "det_llm_delta_brief_v1",
  "det_llm_excerpt_picker_v1",
])

const DEFAULT_INSTRUCTIONS_ASSET =
  "llm_project_instructions_openai_gpt53codex_xhigh_agent_fullsec_2026-02-22.txt"
const DEFAULT_PROJECT_INSTRUCTIONS_PATH = withBase(
  `data/sec_narrative_drift_lab/${DEFAULT_INSTRUCTIONS_ASSET}`
)
const RUN_LABEL_TEMPLATE = "YYYY-MM-DD_<campaign_tag>"

const projectInstructionsPromiseByPath = new Map<string, Promise<string>>()

const FALLBACK_PROJECT_INSTRUCTIONS = [
  "Output must be JSON only (no markdown, no backticks, no commentary).",
  "Output exactly one top-level JSON object.",
  "Top-level keys must match the Lab envelope exactly.",
  "No extra top-level keys.",
  "Never output section_id.",
  "Use only attached input file and thread starter prompt.",
  "provenance.input_file must match attached input path exactly.",
  `provenance.model_provider must be exactly "<campaign model_provider>".`,
  `provenance.model_name must be exactly "<campaign model_name>".`,
  `provenance.run_label is required and must start with YYYY-MM-DD_ (example: "${RUN_LABEL_TEMPLATE}").`,
  "No extra provenance keys beyond input_file, model_provider, model_name, run_label.",
  "Attach pair manifest plus both year input files for each job.",
  "paragraph_idx must be direct FULL indices from the referenced year input arrays.",
  "Snippets must be verbatim substrings and <= 350 chars.",
  "highlights must be present and non-empty for every evidence block.",
  'Delta citations must use ASCII format: "YYYY para NN".',
  "If any quality check fails, revise before output.",
].join("\n")

type LlmThreadStarterContext = {
  ticker: string
  yearFrom: number
  yearTo: number
  detectorId: string
  lens: LabCleaningLens
  sectionId?: string
  campaignId: string
  campaignDisplayName: string
  modelProvider: string
  modelName: string
  inputFile: string
  expectedOutputPath: string | null
  runLabelTemplate: string
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
  lens: LabCleaningLens,
  section = "10k_item1a",
  sourceId = "edgar"
): string {
  return `inputs/pair/${ticker.toUpperCase()}_${yearFrom}_${yearTo}_${section}_${lens}_${sourceId}.json`
}

export function buildDefaultLlmYearInputFile(
  ticker: string,
  year: number,
  pairYearFrom: number,
  pairYearTo: number,
  lens: LabCleaningLens,
  section = "10k_item1a",
  sourceId = "edgar"
): string {
  return `inputs/year/${ticker.toUpperCase()}_${year}_${section}_${lens}_${sourceId}__pair_${pairYearFrom}_${pairYearTo}.json`
}

export function buildLlmThreadStarterText(context: LlmThreadStarterContext): string {
  const inputFile = normalizeInputFile(context.inputFile)
  const sourceId = context.sourceId ?? "edgar"
  const sectionId = context.sectionId ?? "10k_item1a"
  const lines: string[] = []
  lines.push(
    `Thread Title: ${context.ticker.toUpperCase()} ${context.yearFrom}-${context.yearTo} ${context.detectorId} (${context.lens}) [${context.campaignDisplayName}]`
  )
  lines.push("")
  lines.push(`Attach this input file: ${inputFile}`)
  if (inputFile.startsWith("inputs/pair/")) {
    lines.push(
      `Attach this input file: ${buildDefaultLlmYearInputFile(
        context.ticker,
        context.yearFrom,
        context.yearFrom,
        context.yearTo,
        context.lens,
        sectionId,
        sourceId
      )}`
    )
    lines.push(
      `Attach this input file: ${buildDefaultLlmYearInputFile(
        context.ticker,
        context.yearTo,
        context.yearFrom,
        context.yearTo,
        context.lens,
        sectionId,
        sourceId
      )}`
    )
  }
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
  lines.push(`- provenance.model_provider must be exactly "${context.modelProvider}".`)
  lines.push(`- provenance.model_name must be exactly "${context.modelName}".`)
  lines.push(
    `- provenance.run_label is required and must start with YYYY-MM-DD_ (example: "${context.runLabelTemplate}").`
  )
  lines.push("- No extra provenance keys beyond input_file, model_provider, model_name, run_label.")
  lines.push("- Attach pair manifest + both year input files for this job.")
  lines.push("- paragraph_idx must be direct FULL indices from year inputs.")
  lines.push("- Snippets must be verbatim and <= 350 chars.")
  lines.push("- highlights must be present and non-empty.")
  lines.push('- Delta citations must be ASCII-only format "YYYY para NN".')
  lines.push('- Never use pilcrow-style citation symbols; use "YYYY para NN" only.')
  lines.push("- If any quality check fails, revise before output.")
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
  lines.push('    "warnings": ["Precomputed model output; validate against deterministic evidence and full paragraph context."]')
  lines.push("  },")
  lines.push('  "provenance": {')
  lines.push(`    "input_file": "${inputFile}",`)
  lines.push(`    "model_provider": "${context.modelProvider}",`)
  lines.push(`    "model_name": "${context.modelName}",`)
  lines.push(`    "run_label": "${context.runLabelTemplate}"`)
  lines.push("  }")
  lines.push("}")
  return lines.join("\n")
}

function resolveInstructionPath(assetName?: string): string {
  if (assetName && assetName.trim().length > 0) {
    return withBase(`data/sec_narrative_drift_lab/${assetName}`)
  }
  return DEFAULT_PROJECT_INSTRUCTIONS_PATH
}

export async function loadLlmProjectInstructionsText(assetName?: string): Promise<string> {
  const path = resolveInstructionPath(assetName)
  if (!projectInstructionsPromiseByPath.has(path)) {
    const promise = fetch(path, {
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
    projectInstructionsPromiseByPath.set(path, promise)
  }
  return projectInstructionsPromiseByPath.get(path)!
}
