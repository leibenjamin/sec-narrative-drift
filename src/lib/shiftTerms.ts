import type { ShiftTerm, ShiftTermItem } from "./types"

export function isShiftTermItem(term: ShiftTerm): term is ShiftTermItem {
  return typeof term === "object" && term !== null && "term" in term
}

export function getShiftTermLabel(term: ShiftTerm): string {
  return typeof term === "string" ? term : term.term
}

export function getShiftTermIncludes(term: ShiftTerm): string[] {
  if (!isShiftTermItem(term)) return []
  if (!Array.isArray(term.includes)) return []
  const output: string[] = []
  term.includes.forEach((entry) => {
    if (typeof entry === "string") {
      output.push(entry)
    }
  })
  return output
}
