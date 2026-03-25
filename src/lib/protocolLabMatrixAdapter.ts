import type {
  ProtocolLabPilotMatrixCell,
  ProtocolLabPilotMatrixCellRole,
  ProtocolLabPilotMatrixEvidencePreview,
  ProtocolLabPilotMatrixEvidenceRichnessTier,
  ProtocolLabPilotMatrixLaneCode,
  ProtocolLabPilotMatrixOutputShapeInfo,
  ProtocolLabPilotMatrixProtocolInputIdentity,
} from "./protocolLabMatrixTypes.ts"

const DESKTOP_BASELINE_BOUNDARY = `",
"evidence": [`
const DESKTOP_BASELINE_BRIEF_PREFIX = `"brief_markdown": "`
const REQUIRED_BASELINE_LABELS = [
  "Bottom line:",
  "What changed:",
  "Why it matters:",
  "Caveat:",
] as const
const EVIDENCE_PREVIEW_LIMIT = 3

type StructuredSection = {
  text?: unknown
}

type StructuredEvidenceItem = {
  evidence_id?: unknown
  year_label?: unknown
  paragraph_id?: unknown
  quote_text?: unknown
  short_note?: unknown
}

type StructuredResponseShape = {
  change_brief?: Record<string, StructuredSection | undefined>
  evidence_bundle?: {
    items?: StructuredEvidenceItem[]
  }
}

type PilotMatrixCellBaseOptions = {
  matrix_id: string
  fixture_id: string
  cell_id: string
  label: string
  short_label: string
  role: ProtocolLabPilotMatrixCellRole
  lane_position: number
  protocol_input_identity: ProtocolLabPilotMatrixProtocolInputIdentity
  card_takeaway: string
  why_this_lane_matters: string
  output_shape_info: ProtocolLabPilotMatrixOutputShapeInfo
  evidence_richness_tier: ProtocolLabPilotMatrixEvidenceRichnessTier
  auditability_note: string
  strengths: string[]
  limitations: string[]
  raw_source_refs: {
    response_path: string
    run_manifest_path: string
  }
}

type StructuredPilotMatrixCellOptions = PilotMatrixCellBaseOptions & {
  response: StructuredResponseShape
}

type BaselinePilotMatrixCellOptions = PilotMatrixCellBaseOptions & {
  raw_response_text: string
}

type RecoveredBaselineSections = {
  bottom_line: string
  what_changed: string
  why_it_matters: string
  caveat: string
}

type RecoveredDesktopBaselineResponse = {
  brief_markdown: string
  sections: RecoveredBaselineSections
  evidence: ProtocolLabPilotMatrixEvidencePreview[]
  evidence_count_total: number
  normalization_status: ProtocolLabPilotMatrixCell["normalization_status"]
}

function expectString(value: unknown, label: string): string {
  if (typeof value !== "string") {
    throw new Error(`${label} must be a string.`)
  }
  const trimmed = value.trim()
  if (!trimmed) {
    throw new Error(`${label} must not be empty.`)
  }
  return trimmed
}

function expectStructuredSection(
  container: Record<string, StructuredSection | undefined> | undefined,
  key: string
): string {
  const section = container?.[key]
  if (!section || typeof section !== "object") {
    throw new Error(`change_brief.${key} is missing.`)
  }
  return expectString(section.text, `change_brief.${key}.text`)
}

function decodeJsonLikeString(rawText: string): string {
  let decoded = ""
  let escaping = false

  for (const char of rawText) {
    if (!escaping) {
      if (char === "\\") {
        escaping = true
      } else {
        decoded += char
      }
      continue
    }

    if (char === "n") {
      decoded += "\n"
    } else if (char === "r") {
      decoded += "\r"
    } else if (char === "t") {
      decoded += "\t"
    } else if (char === '"') {
      decoded += '"'
    } else if (char === "\\") {
      decoded += "\\"
    } else {
      decoded += `\\${char}`
    }
    escaping = false
  }

  if (escaping) {
    decoded += "\\"
  }

  return decoded
}

function toEvidencePreviewItem(item: StructuredEvidenceItem, index: number): ProtocolLabPilotMatrixEvidencePreview {
  const evidenceId = expectString(item.evidence_id, `evidence[${index}].evidence_id`)
  const yearLabel = expectString(item.year_label, `evidence[${index}].year_label`)
  const quoteText = expectString(item.quote_text, `evidence[${index}].quote_text`)
  const paragraphIdRaw = item.paragraph_id
  const shortNoteRaw = item.short_note

  return {
    evidence_id: evidenceId,
    year_label: yearLabel,
    paragraph_id: typeof paragraphIdRaw === "string" ? paragraphIdRaw : "",
    quote_text: quoteText,
    short_note: typeof shortNoteRaw === "string" && shortNoteRaw.trim() ? shortNoteRaw.trim() : null,
  }
}

function buildStructuredEvidencePreview(items: StructuredEvidenceItem[] | undefined): {
  evidence_count_total: number
  evidence_preview: ProtocolLabPilotMatrixEvidencePreview[]
} {
  const evidenceItems = Array.isArray(items) ? items : []
  if (evidenceItems.length === 0) {
    throw new Error("evidence_bundle.items must contain at least one evidence item.")
  }

  return {
    evidence_count_total: evidenceItems.length,
    evidence_preview: evidenceItems.slice(0, EVIDENCE_PREVIEW_LIMIT).map(toEvidencePreviewItem),
  }
}

function buildCell(
  options: PilotMatrixCellBaseOptions & {
    headline: string
    summary: string
    evidence_count_total: number
    evidence_preview: ProtocolLabPilotMatrixEvidencePreview[]
    normalization_status: ProtocolLabPilotMatrixCell["normalization_status"]
  }
): ProtocolLabPilotMatrixCell {
  return {
    artifact_schema_id: "pilot_matrix_cell_v1",
    cell_id: options.cell_id,
    matrix_id: options.matrix_id,
    fixture_id: options.fixture_id,
    label: options.label,
    short_label: options.short_label,
    role: options.role,
    lane_position: options.lane_position,
    protocol_input_identity: options.protocol_input_identity,
    headline: options.headline,
    summary: options.summary,
    card_takeaway: options.card_takeaway,
    why_this_lane_matters: options.why_this_lane_matters,
    output_shape_info: options.output_shape_info,
    evidence_richness_tier: options.evidence_richness_tier,
    evidence_count_total: options.evidence_count_total,
    auditability_note: options.auditability_note,
    strengths: options.strengths,
    limitations: options.limitations,
    evidence_preview: options.evidence_preview,
    raw_source_refs: options.raw_source_refs,
    normalization_status: options.normalization_status,
  }
}

export function recoverDesktopBaselineResponse(
  rawResponseText: string
): RecoveredDesktopBaselineResponse {
  const normalizedResponseText = rawResponseText.replace(/\r\n/g, "\n")

  const briefPrefixIndex = normalizedResponseText.indexOf(DESKTOP_BASELINE_BRIEF_PREFIX)
  if (briefPrefixIndex < 0) {
    throw new Error("Baseline response is missing the brief_markdown prefix.")
  }

  const briefStart = briefPrefixIndex + DESKTOP_BASELINE_BRIEF_PREFIX.length
  const boundaryIndex = normalizedResponseText.indexOf(DESKTOP_BASELINE_BOUNDARY, briefStart)
  if (boundaryIndex < 0) {
    throw new Error("Baseline response is missing the literal brief/evidence boundary.")
  }

  const rawBriefSegment = normalizedResponseText.slice(briefStart, boundaryIndex)
  const decodedBrief = decodeJsonLikeString(rawBriefSegment).trim()
  if (!decodedBrief) {
    throw new Error("Recovered baseline brief_markdown is empty.")
  }

  const labelPositions = REQUIRED_BASELINE_LABELS.map((label) => {
    const index = decodedBrief.indexOf(label)
    if (index < 0) {
      throw new Error(`Baseline response is missing required label: ${label}`)
    }
    return { label, index }
  }).sort((left, right) => left.index - right.index)

  const sections = labelPositions.reduce<RecoveredBaselineSections>((accumulator, entry, index) => {
    const nextIndex = index + 1 < labelPositions.length ? labelPositions[index + 1].index : decodedBrief.length
    const sectionText = decodedBrief.slice(entry.index + entry.label.length, nextIndex).trim()
    if (!sectionText) {
      throw new Error(`Baseline response section is empty: ${entry.label}`)
    }
    if (entry.label === "Bottom line:") {
      accumulator.bottom_line = sectionText
    } else if (entry.label === "What changed:") {
      accumulator.what_changed = sectionText
    } else if (entry.label === "Why it matters:") {
      accumulator.why_it_matters = sectionText
    } else if (entry.label === "Caveat:") {
      accumulator.caveat = sectionText
    }
    return accumulator
  }, {
    bottom_line: "",
    what_changed: "",
    why_it_matters: "",
    caveat: "",
  })

  const evidenceStart = normalizedResponseText.indexOf("[", boundaryIndex)
  const evidenceEnd = normalizedResponseText.lastIndexOf("]")
  if (evidenceStart < 0 || evidenceEnd < evidenceStart) {
    throw new Error("Baseline response evidence array is missing or malformed.")
  }

  let evidenceRaw: unknown
  try {
    evidenceRaw = JSON.parse(normalizedResponseText.slice(evidenceStart, evidenceEnd + 1))
  } catch {
    throw new Error("Baseline response evidence array is not valid JSON.")
  }

  if (!Array.isArray(evidenceRaw) || evidenceRaw.length === 0) {
    throw new Error("Baseline response evidence array must be a non-empty array.")
  }

  const evidencePreview = evidenceRaw.slice(0, EVIDENCE_PREVIEW_LIMIT).map((item, index) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) {
      throw new Error(`Baseline evidence item ${index} is not an object.`)
    }
    return toEvidencePreviewItem(item as StructuredEvidenceItem, index)
  })

  return {
    brief_markdown: decodedBrief,
    sections,
    evidence: evidencePreview,
    evidence_count_total: evidenceRaw.length,
    normalization_status: {
      kind: "recovered_noncanonical_json",
      recovered: true,
      source_json_parseable: false,
      recovery_boundary: DESKTOP_BASELINE_BOUNDARY,
      required_labels_found: [...REQUIRED_BASELINE_LABELS],
      note:
        "Recovered deterministically from a noncanonical Desktop baseline file by slicing the literal brief/evidence boundary and parsing the valid evidence array directly.",
    },
  }
}

export function normalizeStructuredPilotMatrixCell(
  options: StructuredPilotMatrixCellOptions
): ProtocolLabPilotMatrixCell {
  const headline = expectStructuredSection(options.response.change_brief, "summary_one_liner")
  const summary = expectStructuredSection(options.response.change_brief, "lead_shift")
  const { evidence_count_total, evidence_preview } = buildStructuredEvidencePreview(
    options.response.evidence_bundle?.items
  )

  return buildCell({
    ...options,
    headline,
    summary,
    evidence_count_total,
    evidence_preview,
    normalization_status: {
      kind: "canonical_json",
      recovered: false,
      source_json_parseable: true,
      recovery_boundary: null,
      required_labels_found: [],
      note: "Parsed directly from the canonical structured Desktop response JSON.",
    },
  })
}

export function normalizeBaselinePilotMatrixCell(
  options: BaselinePilotMatrixCellOptions
): ProtocolLabPilotMatrixCell {
  const recovered = recoverDesktopBaselineResponse(options.raw_response_text)

  return buildCell({
    ...options,
    headline: recovered.sections.bottom_line,
    summary: recovered.sections.what_changed,
    evidence_count_total: recovered.evidence_count_total,
    evidence_preview: recovered.evidence,
    normalization_status: recovered.normalization_status,
  })
}

export function isRecoveredNoncanonicalControlCell(
  cell: Pick<ProtocolLabPilotMatrixCell, "role" | "normalization_status">
): boolean {
  return (
    cell.role === "control" &&
    cell.normalization_status.kind === "recovered_noncanonical_json" &&
    cell.normalization_status.recovered
  )
}

export function getProtocolLabLaneCode(value: string): ProtocolLabPilotMatrixLaneCode | null {
  const match = value.trim().match(/^(\d{2})_/)
  if (!match) return null

  const laneCode = match[1]
  if (laneCode === "00" || laneCode === "01" || laneCode === "02" || laneCode === "03") {
    return laneCode
  }

  return null
}
