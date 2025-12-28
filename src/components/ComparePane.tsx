import { copy } from "../lib/copy"
import { splitForHighlight } from "../lib/textHighlight"
import type { ExcerptPair } from "../lib/types"

type ComparePaneProps = {
  excerptPair: ExcerptPair | null
  highlightTerms: string[]
  secLinks?: Array<{ year: number; url: string }>
  errorMessage?: string | null
  isLoading?: boolean
  showLowConfidenceWarning?: boolean
}

export default function ComparePane({
  excerptPair,
  highlightTerms,
  secLinks,
  errorMessage,
  isLoading,
  showLowConfidenceWarning,
}: ComparePaneProps) {
  const selectedExcerptPair = excerptPair
  const showLoading = Boolean(isLoading && !selectedExcerptPair && !errorMessage)

  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-xl font-semibold">{copy.comparePane.title}</h2>
        <p className="text-sm text-slate-300">{copy.comparePane.helper}</p>
      </div>

      {showLowConfidenceWarning ? (
        <p className="text-xs text-slate-300">{copy.comparePane.warnLowConfidence}</p>
      ) : null}

      {errorMessage ? (
        <p className="text-sm text-slate-300">{errorMessage}</p>
      ) : showLoading ? (
        <p className="text-sm text-slate-300">{copy.comparePane.loading}</p>
      ) : selectedExcerptPair ? (
        <div className="space-y-3">
          <div className="text-xs uppercase tracking-wider text-slate-300">
            {copy.comparePane.pairLabel}
          </div>
          <div className="text-sm font-semibold">
            {selectedExcerptPair.from}-{selectedExcerptPair.to}
          </div>
          {secLinks && secLinks.length > 0 ? (
            <div className="flex flex-wrap gap-3 text-xs">
              {secLinks.map((link) => (
                <a
                  key={`sec-${link.year}`}
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline"
                >
                  {copy.comparePane.viewOnSec} {link.year}
                </a>
              ))}
            </div>
          ) : null}
          <div className="grid gap-3 md:grid-cols-2">
            {selectedExcerptPair.representativeParagraphs.map((para, index) => {
              const segments = splitForHighlight(para.text, highlightTerms)
              return (
                <div
                  key={`${para.year}-${para.paragraphIndex}-${index}`}
                  className="rounded-lg border border-black/10 p-3"
                >
                  <div className="text-xs uppercase tracking-wider text-slate-300">
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
        <p className="text-sm text-slate-300">{copy.comparePane.emptyNoPair}</p>
      )}
    </section>
  )
}
