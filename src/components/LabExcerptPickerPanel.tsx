import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { loadLabInputFile } from "../lib/labData"
import { pairExcerptEvidence } from "../lib/labExcerptPairing"
import { splitForHighlight, type HighlightSegment } from "../lib/textHighlight"
import type { EvidenceBlock, LabOutput } from "../lib/labTypes"

type ParagraphLookup = {
  prevMap: Map<number, string>
  currMap: Map<number, string>
}

type ParagraphStatus = {
  lookup: ParagraphLookup | null
  error: string | null
  isLoading: boolean
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

function asStringArray(value: unknown): string[] | null {
  if (!Array.isArray(value)) return null
  const output: string[] = []
  for (const entry of value) {
    if (typeof entry !== "string") return null
    output.push(entry)
  }
  return output
}

function asNumberArray(value: unknown): number[] | null {
  if (!Array.isArray(value)) return null
  const output: number[] = []
  for (const entry of value) {
    if (typeof entry !== "number" || Number.isNaN(entry)) return null
    output.push(entry)
  }
  return output
}

function buildLegacyParagraphLookup(root: Record<string, unknown>): ParagraphLookup | null {
  const texts = asRecord(root.texts)
  if (!texts) return null
  const prevParagraphs = asStringArray(texts.prev_paragraphs)
  const currParagraphs = asStringArray(texts.curr_paragraphs)
  if (!prevParagraphs || !currParagraphs) return null

  const focusMeta = asRecord(root.focuspack_meta)
  const selectedPrev = focusMeta ? asNumberArray(focusMeta.selected_prev_indices) : null
  const selectedCurr = focusMeta ? asNumberArray(focusMeta.selected_curr_indices) : null

  const prevMap = new Map<number, string>()
  const currMap = new Map<number, string>()

  if (selectedPrev && selectedPrev.length === prevParagraphs.length) {
    selectedPrev.forEach((fullIdx, idx) => {
      prevMap.set(fullIdx, prevParagraphs[idx])
    })
  } else {
    prevParagraphs.forEach((para, idx) => {
      prevMap.set(idx, para)
    })
  }

  if (selectedCurr && selectedCurr.length === currParagraphs.length) {
    selectedCurr.forEach((fullIdx, idx) => {
      currMap.set(fullIdx, currParagraphs[idx])
    })
  } else {
    currParagraphs.forEach((para, idx) => {
      currMap.set(idx, para)
    })
  }
  return { prevMap, currMap }
}

function parseYearParagraphMap(payload: unknown): Map<number, string> | null {
  const root = asRecord(payload)
  if (!root) return null
  const texts = asRecord(root.texts)
  if (!texts) return null
  const paragraphs = asStringArray(texts.paragraphs)
  if (!paragraphs) return null
  const output = new Map<number, string>()
  paragraphs.forEach((paragraph, idx) => {
    output.set(idx, paragraph)
  })
  return output
}

async function buildParagraphLookup(payload: unknown): Promise<ParagraphLookup | null> {
  const root = asRecord(payload)
  if (!root) return null
  const yearInputs = asRecord(root.year_inputs)
  if (!yearInputs) {
    return buildLegacyParagraphLookup(root)
  }
  const prevRef = typeof yearInputs.prev === "string" ? yearInputs.prev : ""
  const currRef = typeof yearInputs.curr === "string" ? yearInputs.curr : ""
  if (!prevRef || !currRef) return null
  const [prevPayload, currPayload] = await Promise.all([
    loadLabInputFile(prevRef),
    loadLabInputFile(currRef),
  ])
  const prevMap = parseYearParagraphMap(prevPayload)
  const currMap = parseYearParagraphMap(currPayload)
  if (!prevMap || !currMap) return null
  return { prevMap, currMap }
}

function titleCase(text: string): string {
  return text.replace(/\b\w/g, (match) => match.toUpperCase())
}

function buildEvidenceTitle(block: EvidenceBlock): string {
  if (block.highlights && block.highlights.length > 0) {
    return block.highlights.slice(0, 3).map((item) => titleCase(item)).join(" / ")
  }
  const clause = block.why.split(/[.;:]/)[0]?.trim()
  if (!clause) return "Excerpt"
  if (clause.length <= 80) return clause
  return `${clause.slice(0, 77)}...`
}

function splitBySnippet(
  paragraph: string,
  snippet: string,
  fallbackTerms: string[]
): HighlightSegment[] {
  if (!snippet) {
    return splitForHighlight(paragraph, fallbackTerms, { maxMatches: 18 })
  }
  const idx = paragraph.indexOf(snippet)
  if (idx < 0) {
    return splitForHighlight(paragraph, fallbackTerms, { maxMatches: 18 })
  }
  const segments: HighlightSegment[] = []
  if (idx > 0) {
    segments.push({ text: paragraph.slice(0, idx), highlight: false })
  }
  segments.push({ text: snippet, highlight: true })
  const tailStart = idx + snippet.length
  if (tailStart < paragraph.length) {
    segments.push({ text: paragraph.slice(tailStart), highlight: false })
  }
  return segments
}

function formatCoverage(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "-"
  return value.toFixed(3)
}

function extractInputFile(output: LabOutput): string | null {
  const provenance = output.provenance as { input_file?: string; input_path?: string }
  if (typeof provenance.input_file === "string" && provenance.input_file) {
    return provenance.input_file
  }
  if (typeof provenance.input_path === "string" && provenance.input_path) {
    return provenance.input_path
  }
  return null
}

type ExcerptCardProps = {
  block: EvidenceBlock
  paragraphText: string | null
  title: string
  isExpanded: boolean
  onToggle: () => void
  compareUrl: string
}

function ExcerptCard({
  block,
  paragraphText,
  title,
  isExpanded,
  onToggle,
  compareUrl,
}: ExcerptCardProps) {
  const displayText = paragraphText ?? block.snippet
  const segments = splitBySnippet(displayText, block.snippet, block.highlights ?? [])
  const excerptClass = isExpanded ? "" : "text-clamp-4"

  return (
    <div className="rounded-lg border border-white/10 bg-slate-900/40 p-4 space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-xs uppercase tracking-wide text-slate-300">{title}</div>
        <div className="text-[11px] text-slate-400">
          {block.year} para {block.paragraph_idx + 1}
        </div>
      </div>
      <div className="text-[11px] text-slate-400">{block.why}</div>
      <p className={`text-sm leading-relaxed text-slate-100 ${excerptClass}`.trim()}>
        {segments.map((segment, idx) =>
          segment.highlight ? (
            <mark
              key={idx}
              className="rounded-sm bg-amber-200/20 px-1 text-amber-100"
            >
              {segment.text}
            </mark>
          ) : (
            <span key={idx}>{segment.text}</span>
          )
        )}
      </p>
      {paragraphText ? null : (
        <div className="text-[11px] text-amber-200/80">
          Full paragraph unavailable (using snippet only).
        </div>
      )}
      <div className="flex flex-wrap items-center gap-3 text-xs text-slate-300">
        <button
          type="button"
          onClick={onToggle}
          className="underline decoration-dotted underline-offset-4"
        >
          {isExpanded ? "Show less" : "Show more"}
        </button>
        <Link
          to={compareUrl}
          className="underline decoration-dotted underline-offset-4"
        >
          Jump to Compare Pane
        </Link>
      </div>
    </div>
  )
}

export default function LabExcerptPickerPanel({ output }: { output: LabOutput }) {
  const inputFile = extractInputFile(output)

  const [paragraphStatus, setParagraphStatus] = useState<ParagraphStatus>({
    lookup: null,
    error: null,
    isLoading: !!inputFile,
  })
  const [expandedKeys, setExpandedKeys] = useState<Record<string, boolean>>({})
  const [prevInputFile, setPrevInputFile] = useState(inputFile)
  if (prevInputFile !== inputFile) {
    setPrevInputFile(inputFile)
    setParagraphStatus({ lookup: null, error: null, isLoading: !!inputFile })
  }

  useEffect(() => {
    let cancelled = false

    if (!inputFile) {
      return () => {
        cancelled = true
      }
    }

    loadLabInputFile(inputFile)
      .then(async (payload) => {
        if (cancelled) return
        const lookup = await buildParagraphLookup(payload)
        if (cancelled) return
        if (!lookup) {
          setParagraphStatus({
            lookup: null,
            error: "Input file missing paragraph data.",
            isLoading: false,
          })
          return
        }
        setParagraphStatus({ lookup, error: null, isLoading: false })
      })
      .catch(() => {
        if (cancelled) return
        setParagraphStatus({
          lookup: null,
          error: "Input file could not be loaded.",
          isLoading: false,
        })
      })

    return () => {
      cancelled = true
    }
  }, [inputFile])

  const effectiveStatus: ParagraphStatus = !inputFile
    ? { lookup: null, error: "Input file not linked.", isLoading: false }
    : paragraphStatus

  const yearFrom = output.year_from
  const yearTo = output.year_to
  const evidence = useMemo(() => output.evidence ?? [], [output.evidence])

  const prevEvidence = useMemo(
    () => evidence.filter((block) => block.year === yearFrom),
    [evidence, yearFrom]
  )
  const currEvidence = useMemo(
    () => evidence.filter((block) => block.year === yearTo),
    [evidence, yearTo]
  )

  const pairing = useMemo(
    () => pairExcerptEvidence(prevEvidence, currEvidence, { maxPairs: 3 }),
    [prevEvidence, currEvidence]
  )

  const missingParagraphs = useMemo(() => {
    if (!effectiveStatus.lookup) return evidence.length
    let missing = 0
    for (const block of evidence) {
      const map = block.year === yearFrom ? effectiveStatus.lookup.prevMap : effectiveStatus.lookup.currMap
      if (!map.has(block.paragraph_idx)) {
        missing += 1
      }
    }
    return missing
  }, [effectiveStatus.lookup, evidence, yearFrom])

  const coverage = output.metrics.coverage
  const coverageLabel = `${formatCoverage(coverage)}${coverage !== null && coverage < 0.99 ? " (subset)" : ""}`
  const isLowCoverage = coverage !== null && coverage < 0.4
  const isDeboiler = output.cleaning_lens === "deboilerplated"

  const compareUrl = `/company/${output.ticker}?tab=lab&from=${yearFrom}&to=${yearTo}`

  const toggleKey = (key: string) => {
    setExpandedKeys((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const paragraphLookup = effectiveStatus.lookup

  const buildParagraphText = (block: EvidenceBlock): string | null => {
    if (!paragraphLookup) return null
    const map = block.year === yearFrom ? paragraphLookup.prevMap : paragraphLookup.currMap
    return map.get(block.paragraph_idx) ?? null
  }

  const buildCardKey = (block: EvidenceBlock, index: number): string =>
    `${block.year}-${block.paragraph_idx}-${index}`

  return (
    <div className="space-y-5">
      <div className="rounded-md border border-white/10 bg-white/5 p-3 text-xs text-slate-200">
        <div className="flex flex-wrap items-center gap-3">
          <span className="font-semibold">Coverage: {coverageLabel}</span>
          {output.metrics.warnings?.length ? (
            <span className="text-slate-300">Warnings: {output.metrics.warnings.join(", ")}</span>
          ) : null}
        </div>
        {isDeboiler && isLowCoverage ? (
          <div className="mt-2 text-[11px] text-slate-300">
            Low coverage is common for the deboilerplated lens. Use the Compare pane to confirm
            full context.
          </div>
        ) : null}
        {isLowCoverage && missingParagraphs > 0 ? (
          <div className="mt-1 text-[11px] text-slate-300">
            Low coverage may also reflect missing paragraph lookups; check filing availability.
          </div>
        ) : null}
        {effectiveStatus.error ? (
          <div className="mt-2 text-[11px] text-amber-200/80">{effectiveStatus.error}</div>
        ) : null}
        {effectiveStatus.isLoading ? (
          <div className="mt-2 text-[11px] text-slate-400">Loading full paragraphs...</div>
        ) : null}
      </div>

      <div className="space-y-3">
        <div>
          <div className="text-xs uppercase tracking-wide text-slate-400">Paired changes</div>
          <p className="text-xs text-slate-300">
            Paired changes are matched by shared highlight tags and wording overlap; verify in
            Compare pane.
          </p>
        </div>
        {pairing.pairs.length ? (
          <div className="space-y-4">
            {pairing.pairs.map((pair, index) => {
              const shared = pair.sharedHighlights.map((item) => titleCase(item))
              const prevKey = buildCardKey(pair.prev, pair.prevIndex)
              const currKey = buildCardKey(pair.curr, pair.currIndex)
              return (
                <div key={`pair-${index}`} className="rounded-lg border border-white/10 bg-white/5 p-4 space-y-3">
                  {shared.length ? (
                    <div className="flex flex-wrap items-center gap-2 text-[11px] text-amber-200">
                      {shared.map((token) => (
                        <span
                          key={token}
                          className="rounded-full border border-amber-200/30 bg-amber-200/10 px-2 py-0.5"
                        >
                          {token}
                        </span>
                      ))}
                    </div>
                  ) : null}
                  <div className="grid gap-3 md:grid-cols-2">
                    <ExcerptCard
                      block={pair.prev}
                      paragraphText={buildParagraphText(pair.prev)}
                      title={buildEvidenceTitle(pair.prev)}
                      isExpanded={Boolean(expandedKeys[prevKey])}
                      onToggle={() => toggleKey(prevKey)}
                      compareUrl={compareUrl}
                    />
                    <ExcerptCard
                      block={pair.curr}
                      paragraphText={buildParagraphText(pair.curr)}
                      title={buildEvidenceTitle(pair.curr)}
                      isExpanded={Boolean(expandedKeys[currKey])}
                      onToggle={() => toggleKey(currKey)}
                      compareUrl={compareUrl}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="rounded-md border border-white/10 bg-white/5 p-3 text-xs text-slate-300">
            No paired changes found for this output.
          </div>
        )}
      </div>

      <div className="space-y-3">
        <div className="text-xs uppercase tracking-wide text-slate-400">Other notable excerpts</div>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-3">
            <div className="text-xs uppercase tracking-wide text-slate-300">
              {yearFrom}
            </div>
            {pairing.unpairedPrev.length ? (
              pairing.unpairedPrev.map((block, index) => {
                const key = buildCardKey(block, index)
                return (
                  <ExcerptCard
                    key={key}
                    block={block}
                    paragraphText={buildParagraphText(block)}
                    title={buildEvidenceTitle(block)}
                    isExpanded={Boolean(expandedKeys[key])}
                    onToggle={() => toggleKey(key)}
                    compareUrl={compareUrl}
                  />
                )
              })
            ) : (
              <div className="rounded-md border border-white/10 bg-white/5 p-3 text-xs text-slate-300">
                No additional excerpts for {yearFrom}.
              </div>
            )}
          </div>
          <div className="space-y-3">
            <div className="text-xs uppercase tracking-wide text-slate-300">
              {yearTo}
            </div>
            {pairing.unpairedCurr.length ? (
              pairing.unpairedCurr.map((block, index) => {
                const key = buildCardKey(block, index)
                return (
                  <ExcerptCard
                    key={key}
                    block={block}
                    paragraphText={buildParagraphText(block)}
                    title={buildEvidenceTitle(block)}
                    isExpanded={Boolean(expandedKeys[key])}
                    onToggle={() => toggleKey(key)}
                    compareUrl={compareUrl}
                  />
                )
              })
            ) : (
              <div className="rounded-md border border-white/10 bg-white/5 p-3 text-xs text-slate-300">
                No additional excerpts for {yearTo}.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
