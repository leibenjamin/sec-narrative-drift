import { useState } from "react"
import { splitForHighlight } from "../lib/textHighlight"
import type { EvidenceBlock } from "../lib/labTypes"

type EvidenceStackProps = {
  evidence: EvidenceBlock[]
  fallbackMessage?: string
  defaultHighlights?: string[]
}

const DEFAULT_VISIBLE_BLOCKS = 4
const LONG_SNIPPET_THRESHOLD = 320

export default function EvidenceStack({
  evidence,
  fallbackMessage,
  defaultHighlights,
}: EvidenceStackProps) {
  const [showAll, setShowAll] = useState(false)
  const [expandedSnippets, setExpandedSnippets] = useState<Record<string, boolean>>({})

  if (!evidence.length) {
    return (
      <div className="rounded-md border border-white/10 bg-white/5 p-3 text-xs text-slate-300">
        {fallbackMessage ?? "No evidence blocks available."}
      </div>
    )
  }

  const visibleEvidence = showAll ? evidence : evidence.slice(0, DEFAULT_VISIBLE_BLOCKS)

  return (
    <div className="space-y-3">
      {visibleEvidence.map((block, idx) => {
        const highlights = block.highlights?.length
          ? block.highlights
          : defaultHighlights ?? []
        const segments = splitForHighlight(block.snippet, highlights, { maxMatches: 18 })
        const blockKey = `${block.year}-${block.paragraph_idx}-${idx}`
        const isExpanded = Boolean(expandedSnippets[blockKey])
        const isLongSnippet = block.snippet.length > LONG_SNIPPET_THRESHOLD
        const clampStyle =
          !isExpanded && isLongSnippet
            ? {
                display: "-webkit-box",
                WebkitLineClamp: 4,
                WebkitBoxOrient: "vertical" as const,
                overflow: "hidden",
              }
            : undefined

        return (
          <div
            key={`${block.year}-${idx}`}
            className="rounded-md border border-white/10 bg-white/5 p-3"
          >
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-300">
              <span>
                {block.year} para {block.paragraph_idx + 1}
              </span>
              <span className="text-slate-400">{block.why}</span>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-slate-100" style={clampStyle}>
              {segments.map((segment, segIdx) =>
                segment.highlight ? (
                  <mark
                    key={segIdx}
                    className="rounded-sm bg-amber-200/20 px-1 text-amber-100"
                  >
                    {segment.text}
                  </mark>
                ) : (
                  <span key={segIdx}>{segment.text}</span>
                )
              )}
            </p>
            {isLongSnippet ? (
              <button
                type="button"
                onClick={() =>
                  setExpandedSnippets((previous) => ({
                    ...previous,
                    [blockKey]: !previous[blockKey],
                  }))
                }
                className="mt-2 text-[11px] text-slate-300 underline decoration-dotted underline-offset-4"
              >
                {isExpanded ? "Show less" : "Show more"}
              </button>
            ) : null}
          </div>
        )
      })}
      {evidence.length > DEFAULT_VISIBLE_BLOCKS ? (
        <button
          type="button"
          onClick={() => setShowAll((previous) => !previous)}
          className="rounded-md border border-white/20 bg-slate-900/60 px-3 py-1.5 text-xs text-slate-100 transition hover:border-white/40"
        >
          {showAll
            ? `Show first ${DEFAULT_VISIBLE_BLOCKS} evidence blocks`
            : `Show all ${evidence.length} evidence blocks`}
        </button>
      ) : null}
    </div>
  )
}
