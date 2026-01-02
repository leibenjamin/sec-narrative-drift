const COMMON_SHORT_WORDS = new Set([
  "a",
  "an",
  "and",
  "are",
  "as",
  "at",
  "be",
  "but",
  "by",
  "can",
  "did",
  "do",
  "for",
  "had",
  "has",
  "i",
  "if",
  "in",
  "is",
  "it",
  "its",
  "may",
  "not",
  "nor",
  "of",
  "on",
  "or",
  "our",
  "per",
  "the",
  "to",
  "us",
  "we",
  "who",
  "why",
  "you",
])

const SUFFIX_FRAGMENTS = [
  "mation",
  "mations",
  "tion",
  "tions",
  "sion",
  "sions",
  "ment",
  "ments",
  "ness",
  "less",
  "ance",
  "ances",
  "ence",
  "ences",
  "ing",
  "ings",
  "ity",
  "ities",
  "ative",
  "atives",
  "able",
  "ably",
  "ization",
  "izations",
  "tory",
  "tories",
]

const BULLET_TOKEN = "__BULLET_BREAK__"
const BULLET_SYMBOL = "\u2022"
const BULLET_PATTERN = /\n\s*(?:\u2022|\u00b7|\*|\u2013|\u2014|-)\s+/g

function startsWithAny(value: string, fragments: string[]): boolean {
  for (const fragment of fragments) {
    if (value.startsWith(fragment)) {
      return true
    }
  }
  return false
}

export function normalizeExcerptText(text: string): string {
  if (!text) return ""
  let normalized = text
    .replace(/\u00a0/g, " ")
    .replace(/[\u0091\u0092]/g, "'")
    .replace(/[\u0093\u0094]/g, '"')
    .replace(/\u0096/g, "\u2013")
    .replace(/\u0097/g, "\u2014")
    .replace(/\r\n?/g, "\n")

  normalized = normalized.replace(/([A-Za-z])-\n([A-Za-z])/g, "$1$2")
  normalized = normalized.replace(BULLET_PATTERN, `${BULLET_TOKEN}${BULLET_SYMBOL} `)

  normalized = normalized.replace(
    /\b([A-Za-z]{1,3})\s*\n\s*([a-z][A-Za-z]+)/g,
    (_match, left: string, right: string) => {
      void _match
      const lower = left.toLowerCase()
      const rightLower = right.toLowerCase()
      if (COMMON_SHORT_WORDS.has(lower) || COMMON_SHORT_WORDS.has(rightLower)) {
        return `${left} ${right}`
      }
      return `${left}${right}`
    }
  )

  normalized = normalized.replace(
    /\b([A-Za-z]{3,})\s*\n\s*([a-z]{1,2})\b/g,
    (_match, left: string, right: string) => {
      void _match
      const leftLower = left.toLowerCase()
      const rightLower = right.toLowerCase()
      if (COMMON_SHORT_WORDS.has(leftLower) || COMMON_SHORT_WORDS.has(rightLower)) {
        return `${left} ${right}`
      }
      return `${left}${right}`
    }
  )

  normalized = normalized.replace(
    /\b([A-Za-z]{3,})\s*\n\s*([a-z]{2,})/g,
    (_match, left: string, right: string) => {
      void _match
      const rightLower = right.toLowerCase()
      if (startsWithAny(rightLower, SUFFIX_FRAGMENTS)) {
        return `${left}${right}`
      }
      return `${left} ${right}`
    }
  )

  normalized = normalized.replace(/\s*\n+\s*/g, " ")
  normalized = normalized.replace(
    /([A-Za-z])\s+(\u00ae|\u2122|\u2120)/g,
    "$1$2"
  )
  normalized = normalized.replace(
    /(\u00ae|\u2122|\u2120)\s+([A-Za-z])/g,
    "$1 $2"
  )
  normalized = normalized.replace(/\u201c\s+/g, "\u201c")
  normalized = normalized.replace(/\s+\u201d/g, "\u201d")
  normalized = normalized.replace(new RegExp(BULLET_TOKEN, "g"), "\n")
  normalized = normalized.replace(/\s{2,}/g, " ").trim()

  return normalized
}
