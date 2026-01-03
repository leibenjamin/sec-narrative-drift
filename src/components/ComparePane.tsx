import { copy } from "../lib/copy"
import { normalizeExcerptText } from "../lib/normalizeExcerpt"
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
  const fromParagraphs = selectedExcerptPair
    ? selectedExcerptPair.representativeParagraphs.filter(
        (para) => para.year === selectedExcerptPair.from
      )
    : []
  const toParagraphs = selectedExcerptPair
    ? selectedExcerptPair.representativeParagraphs.filter(
        (para) => para.year === selectedExcerptPair.to
      )
    : []
  const sortedFrom = [...fromParagraphs].sort((a, b) => a.paragraphIndex - b.paragraphIndex)
  const sortedTo = [...toParagraphs].sort((a, b) => a.paragraphIndex - b.paragraphIndex)
  const hasBothSides = sortedFrom.length > 0 && sortedTo.length > 0
  const rowCount = Math.max(sortedFrom.length, sortedTo.length)
  const pairedRows = hasBothSides
    ? Array.from({ length: rowCount }, (_, index) => ({
        left: sortedFrom[index] ?? null,
        right: sortedTo[index] ?? null,
      }))
    : []

  const renderParagraph = (
    para: ExcerptPair["representativeParagraphs"][number],
    index: number
  ) => {
    const normalizedText = normalizeExcerptText(para.text)
    const segments = splitForHighlight(normalizedText, highlightTerms)
    return (
      <div
        key={`${para.year}-${para.paragraphIndex}-${index}`}
        className="rounded-lg border border-white/10 bg-slate-900/40 p-3"
      >
        <p className="text-sm leading-relaxed whitespace-pre-line">
          {segments.length > 0
            ? segments.map((segment, segmentIndex) =>
                segment.highlight ? (
                  <mark
                    key={`${para.year}-${para.paragraphIndex}-${segmentIndex}`}
                    className="rounded bg-amber-400/25 px-0.5 text-amber-100"
                  >
                    {segment.text}
                  </mark>
                ) : (
                  <span key={`${para.year}-${para.paragraphIndex}-${segmentIndex}`}>
                    {segment.text}
                  </span>
                )
              )
            : normalizedText}
        </p>
      </div>
    )
  }

  const renderEmptyCell = (key: string) => (
    <div
      key={key}
      className="rounded-lg border border-dashed border-white/10 bg-slate-900/30 p-3 text-xs text-slate-400"
    >
      {copy.comparePane.emptyCell}
    </div>
  )

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
          {hasBothSides ? (
            <div className="rounded-lg border border-white/10 bg-slate-900/40 p-4 space-y-3">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="flex items-baseline justify-between">
                  <div className="text-xs uppercase tracking-wider text-slate-300">
                    {copy.comparePane.fromLabel} {selectedExcerptPair.from}
                  </div>
                  <div className="text-xs text-slate-400">
                    {copy.comparePane.excerptCount({ n: fromParagraphs.length })}
                  </div>
                </div>
                <div className="flex items-baseline justify-between">
                  <div className="text-xs uppercase tracking-wider text-slate-300">
                    {copy.comparePane.toLabel} {selectedExcerptPair.to}
                  </div>
                  <div className="text-xs text-slate-400">
                    {copy.comparePane.excerptCount({ n: toParagraphs.length })}
                  </div>
                </div>
              </div>
              {pairedRows.map((row, rowIndex) => (
                <div key={`row-${rowIndex}`} className="grid gap-3 md:grid-cols-2">
                  {row.left
                    ? renderParagraph(row.left, rowIndex)
                    : renderEmptyCell(`left-${rowIndex}`)}
                  {row.right
                    ? renderParagraph(row.right, rowIndex)
                    : renderEmptyCell(`right-${rowIndex}`)}
                </div>
              ))}
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-3 rounded-lg border border-white/10 bg-slate-900/40 p-4">
                <div className="flex items-baseline justify-between">
                  <div className="text-xs uppercase tracking-wider text-slate-300">
                    {copy.comparePane.fromLabel} {selectedExcerptPair.from}
                  </div>
                  <div className="text-xs text-slate-400">
                    {copy.comparePane.excerptCount({ n: fromParagraphs.length })}
                  </div>
                </div>
                {fromParagraphs.length
                  ? fromParagraphs.map((para, index) => renderParagraph(para, index))
                  : (
                      <p className="text-xs text-slate-400">
                        {copy.comparePane.emptyYear}
                      </p>
                    )}
              </div>
              <div className="space-y-3 rounded-lg border border-white/10 bg-slate-900/40 p-4">
                <div className="flex items-baseline justify-between">
                  <div className="text-xs uppercase tracking-wider text-slate-300">
                    {copy.comparePane.toLabel} {selectedExcerptPair.to}
                  </div>
                  <div className="text-xs text-slate-400">
                    {copy.comparePane.excerptCount({ n: toParagraphs.length })}
                  </div>
                </div>
                {toParagraphs.length
                  ? toParagraphs.map((para, index) => renderParagraph(para, index))
                  : (
                      <p className="text-xs text-slate-400">
                        {copy.comparePane.emptyYear}
                      </p>
                    )}
              </div>
            </div>
          )}
        </div>
      ) : (
        <p className="text-sm text-slate-300">{copy.comparePane.emptyNoPair}</p>
      )}
    </section>
  )
}
