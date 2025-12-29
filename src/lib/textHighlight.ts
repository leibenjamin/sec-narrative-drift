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

  // Longer phrases first so we don't highlight "chain" inside "supply chain".
  return normalized.sort((a, b) => b.length - a.length)
}

function termToPattern(term: string): string {
  const trimmed = term.trim()
  if (!trimmed) return ""
  const hasSpace = /\s/.test(trimmed)
  const escaped = escapeRegExp(trimmed)

  // Treat spaces and hyphens as roughly equivalent in prose.
  const hyphenClass = "[\\u2010\\u2011\\u2012\\u2013\\u2014\\u2212-]"
  if (hasSpace) {
    const parts = trimmed.split(/\s+/).map((part) => escapeRegExp(part))
    const joiner = `(?:\\s+|${hyphenClass}\\s*)`
    return `\\b${parts.join(joiner)}\\b`
  }

  return `\\b${escaped}\\b`
}

function buildRegex(terms: string[]): RegExp | null {
  if (terms.length === 0) return null
  const patterns = terms.map(termToPattern).filter(Boolean)
  if (patterns.length === 0) return null
  const pattern = patterns.join("|")
  return new RegExp(pattern, "gi")
}

export function splitForHighlight(
  text: string,
  terms: string[],
  options?: { maxMatches?: number }
): HighlightSegment[] {
  if (!text) return []
  const normalizedTerms = normalizeTerms(terms)
  const regex = buildRegex(normalizedTerms)
  if (!regex) return [{ text, highlight: false }]

  const maxMatches = options?.maxMatches ?? 14
  const segments: HighlightSegment[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null
  let matchCount = 0

  while ((match = regex.exec(text)) !== null) {
    if (!match[0]) break
    matchCount += 1
    if (matchCount > maxMatches) {
      break
    }
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
