import type { EvidenceBlock } from "./labTypes"

type PairScore = {
  highlightOverlapCount: number
  highlightJaccard: number
  whyJaccard: number
  snippetJaccard: number
}

export type EvidencePair = {
  prev: EvidenceBlock
  curr: EvidenceBlock
  prevIndex: number
  currIndex: number
  score: PairScore
  sharedHighlights: string[]
}

export type PairingResult = {
  pairs: EvidencePair[]
  unpairedPrev: EvidenceBlock[]
  unpairedCurr: EvidenceBlock[]
}

const STOPWORDS = new Set([
  "the",
  "and",
  "for",
  "with",
  "that",
  "this",
  "from",
  "are",
  "was",
  "were",
  "will",
  "shall",
  "may",
  "might",
  "could",
  "should",
  "into",
  "over",
  "under",
  "such",
  "their",
  "there",
  "here",
  "have",
  "has",
  "had",
  "our",
  "its",
  "but",
  "not",
  "any",
  "all",
  "can",
  "also",
  "more",
  "than",
  "these",
  "those",
  "including",
  "within",
  "across",
  "about",
  "into",
  "them",
  "they",
  "we",
  "us",
])

function normalizeHighlightTokens(highlights: string[] | undefined): Set<string> {
  const output = new Set<string>()
  if (!highlights) return output
  for (const item of highlights) {
    const trimmed = item.trim().toLowerCase()
    if (!trimmed) continue
    output.add(trimmed)
  }
  return output
}

function tokenize(text: string): Set<string> {
  const tokens = new Set<string>()
  if (!text) return tokens
  const parts = text.toLowerCase().split(/[^a-z0-9]+/g)
  for (const part of parts) {
    const trimmed = part.trim()
    if (!trimmed || trimmed.length < 3) continue
    if (STOPWORDS.has(trimmed)) continue
    tokens.add(trimmed)
  }
  return tokens
}

function buildTrigrams(text: string): Set<string> {
  const output = new Set<string>()
  if (!text) return output
  const cleaned = text.toLowerCase().replace(/\s+/g, " ").trim()
  if (cleaned.length < 3) return output
  for (let idx = 0; idx <= cleaned.length - 3; idx += 1) {
    output.add(cleaned.slice(idx, idx + 3))
  }
  return output
}

function jaccardScore(a: Set<string>, b: Set<string>): number {
  if (!a.size && !b.size) return 0
  let intersection = 0
  for (const item of a) {
    if (b.has(item)) intersection += 1
  }
  const union = a.size + b.size - intersection
  return union > 0 ? intersection / union : 0
}

function scorePair(prev: EvidenceBlock, curr: EvidenceBlock): PairScore {
  const prevHighlights = normalizeHighlightTokens(prev.highlights)
  const currHighlights = normalizeHighlightTokens(curr.highlights)
  let highlightOverlapCount = 0
  for (const token of prevHighlights) {
    if (currHighlights.has(token)) highlightOverlapCount += 1
  }

  const highlightJaccard = jaccardScore(prevHighlights, currHighlights)
  const whyJaccard = jaccardScore(tokenize(prev.why), tokenize(curr.why))
  const snippetJaccard = jaccardScore(buildTrigrams(prev.snippet), buildTrigrams(curr.snippet))

  return {
    highlightOverlapCount,
    highlightJaccard,
    whyJaccard,
    snippetJaccard,
  }
}

function buildSharedHighlights(prev: EvidenceBlock, curr: EvidenceBlock): string[] {
  const shared: string[] = []
  const prevTokens = normalizeHighlightTokens(prev.highlights)
  const currTokens = normalizeHighlightTokens(curr.highlights)
  for (const token of prevTokens) {
    if (currTokens.has(token)) {
      shared.push(token)
    }
  }
  return shared
}

function compareCandidates(
  a: { score: PairScore; prevIndex: number; currIndex: number },
  b: { score: PairScore; prevIndex: number; currIndex: number }
): number {
  if (a.score.highlightOverlapCount !== b.score.highlightOverlapCount) {
    return b.score.highlightOverlapCount - a.score.highlightOverlapCount
  }
  if (a.score.highlightJaccard !== b.score.highlightJaccard) {
    return b.score.highlightJaccard - a.score.highlightJaccard
  }
  if (a.score.whyJaccard !== b.score.whyJaccard) {
    return b.score.whyJaccard - a.score.whyJaccard
  }
  if (a.score.snippetJaccard !== b.score.snippetJaccard) {
    return b.score.snippetJaccard - a.score.snippetJaccard
  }
  if (a.prevIndex !== b.prevIndex) {
    return a.prevIndex - b.prevIndex
  }
  return a.currIndex - b.currIndex
}

export function pairExcerptEvidence(
  prevItems: EvidenceBlock[],
  currItems: EvidenceBlock[],
  options?: { maxPairs?: number }
): PairingResult {
  if (!prevItems.length || !currItems.length) {
    return { pairs: [], unpairedPrev: prevItems, unpairedCurr: currItems }
  }

  const candidates: Array<{
    prevIndex: number
    currIndex: number
    score: PairScore
  }> = []
  for (let i = 0; i < prevItems.length; i += 1) {
    for (let j = 0; j < currItems.length; j += 1) {
      candidates.push({ prevIndex: i, currIndex: j, score: scorePair(prevItems[i], currItems[j]) })
    }
  }

  const highlightCandidates = candidates.filter(
    (candidate) => candidate.score.highlightOverlapCount > 0
  )
  const maxPairs = options?.maxPairs ?? 3
  const targetPairs =
    highlightCandidates.length >= 3
      ? Math.min(maxPairs, 3)
      : highlightCandidates.length >= 2
        ? Math.min(maxPairs, 2)
        : highlightCandidates.length >= 1
          ? 1
          : 0

  if (targetPairs === 0) {
    return { pairs: [], unpairedPrev: prevItems, unpairedCurr: currItems }
  }

  const pool = highlightCandidates.length ? highlightCandidates : candidates
  pool.sort(compareCandidates)

  const usedPrev = new Set<number>()
  const usedCurr = new Set<number>()
  const pairs: EvidencePair[] = []

  for (const candidate of pool) {
    if (pairs.length >= targetPairs) break
    if (usedPrev.has(candidate.prevIndex) || usedCurr.has(candidate.currIndex)) continue
    usedPrev.add(candidate.prevIndex)
    usedCurr.add(candidate.currIndex)
    const prev = prevItems[candidate.prevIndex]
    const curr = currItems[candidate.currIndex]
    pairs.push({
      prev,
      curr,
      prevIndex: candidate.prevIndex,
      currIndex: candidate.currIndex,
      score: candidate.score,
      sharedHighlights: buildSharedHighlights(prev, curr),
    })
  }

  const unpairedPrev = prevItems.filter((_, index) => !usedPrev.has(index))
  const unpairedCurr = currItems.filter((_, index) => !usedCurr.has(index))

  return { pairs, unpairedPrev, unpairedCurr }
}
