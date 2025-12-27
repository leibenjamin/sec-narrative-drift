import { useMemo } from "react"
import { copy } from "../lib/copy"
import { splitForHighlight } from "../lib/textHighlight"
import type { Excerpts } from "../lib/types"

type ComparePaneProps = {
  selectedPair: { from: number; to: number } | null
  excerpts: Excerpts | null
  highlightTerms: string[]
  errorMessage?: string | null
  showLowConfidenceWarning?: boolean
}

export default function ComparePane({
  selectedPair,
  excerpts,
  highlightTerms,
  errorMessage,
  showLowConfidenceWarning,
}: ComparePaneProps) {
  const selectedExcerptPair = useMemo(() => {
    if (!excerpts?.pairs?.length) return null
    if (!selectedPair) return excerpts.pairs[0]
    return (
      excerpts.pairs.find(
        (pair) => pair.from === selectedPair.from && pair.to === selectedPair.to
      ) ?? excerpts.pairs[0]
    )
  }, [excerpts, selectedPair])

  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-xl font-semibold">{copy.comparePane.title}</h2>
        <p className="text-sm opacity-70">{copy.comparePane.helper}</p>
      </div>

      {showLowConfidenceWarning ? (
        <p className="text-xs opacity-70">{copy.comparePane.warnLowConfidence}</p>
      ) : null}

      {errorMessage ? (
        <p className="text-sm opacity-70">{errorMessage}</p>
      ) : selectedExcerptPair ? (
        <div className="space-y-3">
          <div className="text-xs uppercase tracking-wider opacity-70">
            {copy.comparePane.pairLabel}
          </div>
          <div className="text-sm font-semibold">
            {selectedExcerptPair.from}-{selectedExcerptPair.to}
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {selectedExcerptPair.representativeParagraphs.map((para, index) => {
              const segments = splitForHighlight(para.text, highlightTerms)
              return (
                <div
                  key={`${para.year}-${para.paragraphIndex}-${index}`}
                  className="rounded-lg border border-black/10 p-3"
                >
                  <div className="text-xs uppercase tracking-wider opacity-70">
                    {para.year}
                  </div>
                  <p className="mt-2 text-sm leading-relaxed whitespace-pre-line">
                    {segments.length > 0
                      ? segments.map((segment, segmentIndex) =>
                          segment.highlight ? (
                            <mark
                              key={`${para.year}-${para.paragraphIndex}-${segmentIndex}`}
                              className="rounded bg-yellow-200 px-0.5"
                            >
                              {segment.text}
                            </mark>
                          ) : (
                            <span
                              key={`${para.year}-${para.paragraphIndex}-${segmentIndex}`}
                            >
                              {segment.text}
                            </span>
                          )
                        )
                      : para.text}
                  </p>
                </div>
              )
            })}
          </div>
        </div>
      ) : (
        <p className="text-sm opacity-70">{copy.comparePane.emptyNoPair}</p>
      )}
    </section>
  )
}
