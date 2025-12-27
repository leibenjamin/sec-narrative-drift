export type HighlightSegment = {
  text: string
  highlight: boolean
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
}

function normalizeTerms(terms: string[]): string[] {
  const seen = new Set<string>()
  const normalized: string[] = []

  terms.forEach((term) => {
    const trimmed = term.trim()
    if (!trimmed) return
    const key = trimmed.toLowerCase()
    if (seen.has(key)) return
    seen.add(key)
    normalized.push(trimmed)
  })

  return normalized.sort((a, b) => b.length - a.length)
}

function buildRegex(terms: string[]): RegExp | null {
  if (terms.length === 0) return null
  const pattern = terms.map((term) => `\\b${escapeRegExp(term)}\\b`).join("|")
  if (!pattern) return null
  return new RegExp(pattern, "gi")
}

export function splitForHighlight(text: string, terms: string[]): HighlightSegment[] {
  if (!text) return []
  const normalizedTerms = normalizeTerms(terms)
  const regex = buildRegex(normalizedTerms)
  if (!regex) return [{ text, highlight: false }]

  const segments: HighlightSegment[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = regex.exec(text)) !== null) {
    const start = match.index ?? 0
    if (start > lastIndex) {
      segments.push({ text: text.slice(lastIndex, start), highlight: false })
    }
    const matchText = match[0]
    segments.push({ text: matchText, highlight: true })
    lastIndex = start + matchText.length
  }

  if (lastIndex < text.length) {
    segments.push({ text: text.slice(lastIndex), highlight: false })
  }

  if (segments.length === 0) {
    return [{ text, highlight: false }]
  }

  return segments
}
