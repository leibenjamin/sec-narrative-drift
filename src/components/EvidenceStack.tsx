import { splitForHighlight } from "../lib/textHighlight"
import type { EvidenceBlock } from "../lib/labTypes"

type EvidenceStackProps = {
  evidence: EvidenceBlock[]
  fallbackMessage?: string
  defaultHighlights?: string[]
}

export default function EvidenceStack({
  evidence,
  fallbackMessage,
  defaultHighlights,
}: EvidenceStackProps) {
  if (!evidence.length) {
    return (
      <div className="rounded-md border border-white/10 bg-white/5 p-3 text-xs text-slate-300">
        {fallbackMessage ?? "No evidence blocks available."}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {evidence.map((block, idx) => {
        const highlights = block.highlights?.length
          ? block.highlights
          : defaultHighlights ?? []
        const segments = splitForHighlight(block.snippet, highlights, { maxMatches: 18 })
        return (
          <div key={`${block.year}-${idx}`} className="rounded-md border border-white/10 bg-white/5 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-300">
              <span>
                {block.year} ? paragraph {block.paragraph_idx + 1}
              </span>
              <span className="text-slate-400">{block.why}</span>
            </div>
            <p className="mt-2 text-sm text-slate-100">
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
          </div>
        )
      })}
    </div>
  )
}
