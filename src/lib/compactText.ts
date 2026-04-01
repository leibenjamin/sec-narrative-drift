export function normalizeText(text: string): string {
  return text.replace(/\s+/g, " ").trim()
}

export function compactText(text: string, maxLength = 160): string {
  const normalized = normalizeText(text)
  if (normalized.length <= maxLength) return normalized
  const clipped = normalized.slice(0, maxLength).trimEnd()
  const lastSpace = clipped.lastIndexOf(" ")
  return `${(lastSpace > 0 ? clipped.slice(0, lastSpace) : clipped).trimEnd()}...`
}
