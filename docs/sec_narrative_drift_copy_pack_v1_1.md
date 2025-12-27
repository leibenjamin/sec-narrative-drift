# SEC Narrative Drift — Copy Pack (Single Tone) (v1.1)

**Purpose:** Provide copy text, labels, tooltips, and microcopy *ahead of implementation* so **no‑web Codex** doesn’t invent generic phrasing.

**Tone:** Single public tone (Ferris‑dry / Eggers / Max Barry energy).  
**Humor style:** understated, workplace‑satire microcopy — never insulting, never profane, never “lol random”.

> Implementation note: Put these strings in `src/lib/copy.ts` as a single `copy` object. **Do not implement any tone toggle.**

---

## 0) Global strings

- **App name:** `SEC Narrative Drift`
- **Subtitle:** `How 10‑K “Risk Factors” language changes over time (Item 1A)`
- **One‑liner (home hero):** `A fast, auditable way to spot when the risk story changed — and read the exact paragraphs.`
- **Source line:** `Source: SEC EDGAR (10‑K filings).`
- **Caveat line (always visible, small):** `Descriptive, not causal. Use drift as a reading prompt, not a conclusion.`

---

## 1) Home page copy (high traffic)

- Title: `Narrative Drift, by the numbers — and by the paragraph`
- Body: `Pick a company and see how its 10‑K Risk Factors language changes year‑to‑year, where the biggest shifts happen, and the terms that move the most.`
- Footnote (humor, high‑traffic): `Featured companies are precomputed, because live demos are a form of optimism.`

Featured block:
- Heading: `Featured companies`
- Helper: `Three precomputed datasets. Click one to start.`

---

## 2) Company page copy (top bar + callouts)

Top bar:
- Company: `Company`
- Section: `Section` → `10‑K Item 1A — Risk Factors`
- Years: `Years`
- Buttons: `Methodology`, `Data Quality`, `Start tour`, `Export Exec Brief`

Callout chips:
- `Largest drift year` (tooltip: `Highest drift vs prior year (1 − cosine similarity).`)
- `Most stable year` (tooltip: `Lowest drift vs prior year (excluding null).`)
- `Most templated year` (tooltip: `Approx. reuse rate of sentences across years.`)

---

## 3) DriftTimeline component copy (high traffic)

- Title: `Narrative drift vs prior year`
- Helper (humor, high‑traffic): `Higher means the wording changed more from the previous year. Not a verdict — just where to read.`

Tooltip lines:
- `Drift vs {prevYear}: {drift}`
- `CI: {low}–{high}` (only if present)
- `Boilerplate: {boilerplatePct}` (if present)
- `Extraction confidence: {confidencePct}`

---

## 4) SimilarityHeatmap component copy (high traffic)

- Title: `Similarity across years`
- Helper (humor, likely encountered): `Darker cells are more similar. Click a cell to compare years. It will not file a 10‑K for you.`

Hover tooltip:
- `{fromYear} ↔ {toYear}`
- `Cosine similarity: {value}`
- `Drift: {drift}` (optional)

---

## 5) TermShiftBars component copy

- Title: `Term shifts (what moved most)`
- Helper: `Left: terms emphasized more. Right: terms emphasized less (vs prior year).`
- Labels: `Risers`, `Fallers`
- Score tooltip: `Log‑odds shift score (with smoothing). Higher magnitude = larger relative change.`

---

## 6) ComparePane component copy

- Title: `Read the evidence`
- Helper (humor, likely encountered): `Representative paragraphs for the selected year pair. The receipts — curated, not comprehensive.`

Controls:
- Pair label: `Comparing`
- Highlight label: `Highlight` → `Top shifts`, `Selected term`, `None`
- Link label: `View filing on SEC`

Empty states:
- `Select a year pair from the heatmap to compare.`
- `This excerpt set includes at least one low-confidence extraction year.`

---

## 7) Data Quality drawer copy

- Title: `Data quality`
- Helper (humor): `Extraction confidence reflects how reliably we isolated Item 1A in the filing HTML. Low confidence years are where HTML and reality briefly disagree.`
- Badges: `High confidence`, `Medium confidence`, `Low confidence`, `Skipped (no reliable extract)`
- Guidance: `If confidence is low, drift may reflect parsing noise. Use the “View on SEC” link to verify boundaries.`

---

## 8) Methodology page copy

Headings:
- `What this measures`
- `What it does not measure`
- `How extraction works (high level)`
- `How drift is computed (high level)`
- `How to sanity‑check a spike`
- `Credits`

Core paragraphs (starter):
- Measures: `We compare the text of Item 1A across years and compute how similar each year is to the previous year. A large change suggests the risk narrative was rewritten or restructured.`
- Not causal: `A drift spike is not proof of a real-world event. It’s a prompt to read the filing and form hypotheses.`
- Sanity check: `Click the spike year → click the heatmap cell → skim term shifts → read the highlighted paragraphs → open the SEC link if anything looks off.`

---

## 9) Unused copy text (reserve, do not ship yet)

Use these sparingly and only where they *add clarity*. Keep them out of finance/investment claims.

### Reserve helpers / tooltips (original lines)
- `The metric is descriptive. Your interpretation is the product.`
- `If this looks suspicious, you’re doing it right: click through and read.`
- `We measure text. Reality is outside the scope of this dashboard.`
- `Compliance language changes. So do the reasons. This app only sees the first part.`
- `If you’re looking for causality, you want a different app.`
- `A chart is not a thesis.`
- `This is the fastest way to get from “something changed” to “show me the paragraph.”`
- `All numbers here are invitations to read, not substitutes for reading.`
- `This is not a scandal detector. It’s a change detector.`
- `If the story didn’t change, that’s also a story.`
- `If the story changed, the reason might be boring. That’s still useful.`
- `High drift can mean: new risks, reorganized prose, or a new template.`
- `Low drift can mean: stability, inertia, or very committed templates.`

### Reserve epigraphs (short, credit in Methodology if used)
Keep epigraphs to ≤ 1 sentence and avoid anything that reads cynical about the SEC or compliance.

- Joshua Ferris (*Then We Came to the End*): `In fact there was no such thing as a rumor. There was fact, and there was what did not come up in conversation.`
- Dave Eggers (*The Every*): `Think of how much more genuine and authentic our friendships could be, if we just apply the right metrics to them.`
- Max Barry (*Company*): `That's the thing you learn about values: they're what people make up to justify what they did.`
