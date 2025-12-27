# SEC Narrative Drift — Codex Implementation Checklist (v1.11)
**Use with:** `docs/sec_narrative_drift_codex_spec_v1_11.md` (canonical spec)  
**Purpose:** Turn the spec into small, unambiguous Codex tasks that each end with a runnable, verifiable artifact.

---

## How to use these two docs with Codex
- Treat **the Spec** as the **source of truth** for *what* to build and the JSON contracts.
- Treat **this Checklist** as the **execution order** for *how* to build it.
- In Codex, work ticket-by-ticket. After each ticket, run tests / build / lint, then commit.

---

## Ticket -1 — Workspace prep + steering files (do before Ticket 0)
**Goal:** Make Codex succeed with minimal ambiguity.

**You do this manually (fast):**
- Create `docs/` and place the two canonical docs in it:
  - `docs/sec_narrative_drift_codex_spec_v1_11.md`
  - `docs/sec_narrative_drift_codex_implementation_checklist_v1_11.md`
- Create `AGENTS.md` at repo root (Codex rules of engagement).
- Create `scripts/sample_fixtures/` and add at least one saved 10‑K HTML and one submissions JSON.
- (Recommended) Create the GitHub repo **after the first local commit** and push `main` (keeps the remote clean).

**Acceptance**
- Repo contains `docs/` and `AGENTS.md`
- Codex can open and reference the docs from the workspace
- There is at least one fixture file in `scripts/sample_fixtures/`

---

## Ticket 0 — Repo bootstrap (must be first)
**Goal:** Create a runnable React+TS web app scaffold with one Home page so every later ticket has a stable base.

**Where you run commands:** terminal at the **repo root** (same folder as `package.json`).

### Steps (do in order)

#### 0.1 Put the canonical docs in place
- Create `docs/` and add:
  - `docs/sec_narrative_drift_codex_spec_v1_11.md`
  - `docs/sec_narrative_drift_codex_implementation_checklist_v1_11.md`
  - `docs/sec_narrative_drift_copy_pack_v1_1.md`
  - `docs/sec_narrative_drift_humor_notes_v1_1.md`
- Add `AGENTS.md` at the repo root (instructions for Codex).

#### 0.2 Scaffold the app (Vite + React + TypeScript)
If the repo root is empty enough to host the app, run:

```bash
npm create vite@latest . -- --template react-ts
npm install
npm run dev
```

If you already have files and Vite warns about overwrite, accept only safe prompts. If you prefer to keep the repo root clean, scaffold into a subfolder (e.g., `web/`) and adjust paths accordingly.

#### 0.3 Add Tailwind CSS (2025+ recommended path: Vite plugin)

**Why you hit `npm error could not determine executable to run`:** Tailwind v4 moved the CLI into separate packages and `npx tailwindcss init -p` is no longer the standard workflow.

Use the **official Vite plugin** setup instead (fewer moving parts, no PostCSS config required):

```bash
npm install -D tailwindcss @tailwindcss/vite
```

Update `vite.config.ts`:

```ts
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

export default defineConfig({
  plugins: [react(), tailwindcss()],
})
```

Update `src/index.css` (or keep your file name but ensure it’s imported by `src/main.tsx`):

```css
@import "tailwindcss";
```

Verify Tailwind works by adding a class in `App.tsx`, e.g. `className="p-6"`.

> Optional cleanup: if you previously installed `postcss`/`autoprefixer` just for Tailwind, you can remove them later. They’re not required for the Vite plugin path.
#### 0.4 Add a minimal routing structure (recommended)
```bash
npm install react-router-dom
```

Create:
- `src/pages/Home.tsx` (simple hero + CTA placeholder)
- `src/App.tsx` uses `BrowserRouter` + routes:
  - `/` → `Home`

*(GitHub Pages base-path handling can be added later when you wire deployment.)*

#### 0.5 Add the copy library now (so later tickets don’t hardcode strings)
Create `src/lib/copy.ts` using the latest provided `copy.ts` artifact (single tone, no toggle).

Update `Home.tsx` to import `copy` and render:
- app name, subtitle, one-liner
- the home footnote line (includes one subtle humor line)

### Acceptance
- `npm install` succeeds
- `npm run dev` renders a Home page without console errors
- `npm run build` succeeds
- Repo contains:
  - `package.json`, `vite.config.ts`
  - `src/App.tsx`
  - `src/pages/Home.tsx`
  - `src/lib/copy.ts`
  - `docs/` with the canonical docs
  - `AGENTS.md`

### Commit
- Commit message suggestion: `chore: bootstrap vite app`
- Do **not** push `main` until Ticket 0 passes locally (keeps the remote clean).

---

## Ticket 1 — Define TypeScript types matching the JSON contracts
**Goal:** Prevent UI/pipeline mismatches by enforcing a strict data model.

**Steps**
- Create `src/lib/types.ts` with types for:
  - `Meta`
  - `FilingRow` (including `extraction`)
  - `Metrics`
  - `SimilarityMatrix`
  - `ShiftPairs`
  - `Excerpts`

**Acceptance**
- TypeScript compiles without errors
- Types match the spec exactly (field names, shapes)

**Files**
- `src/lib/types.ts`

---

## Ticket 2 — Static data loader + graceful missing-data behavior
**Goal:** UI can load precomputed JSON from `public/data/...` and never crashes on missing/null fields.

**Steps**
- Implement `src/lib/data.ts`:
  - `listFeaturedTickers(): string[]`
  - `loadCompanyMeta(ticker)`
  - `loadCompanyFilings(ticker)`
  - `loadMetrics(ticker)`
  - `loadSimilarity(ticker)`
  - `loadShifts(ticker)`
  - `loadExcerpts(ticker)`
- All functions:
  - Use `fetch("/data/sec_narrative_drift/...")`
  - Throw controlled errors with user-friendly message
  - Support partial datasets (e.g., missing excerpts)

**Acceptance**
- With placeholder JSON (Ticket 3), the Company page renders
- If a JSON file is missing, UI shows a friendly message, not a stack trace

**Files**
- `src/lib/data.ts`
- `src/pages/Company.tsx`

---

## Ticket 3 — Create a minimal “golden” sample dataset (handmade)
**Goal:** Unblock UI work before pipeline exists.

**Steps**
- Create `public/data/sec_narrative_drift/AAPL/`
- Add the 6 required JSON files per spec:
  - `meta.json`
  - `filings.json`
  - `metrics_10k_item1a.json`
  - `similarity_10k_item1a.json`
  - `shifts_10k_item1a.json`
  - `excerpts_10k_item1a.json`
- Use 3 years only (e.g., 2022–2024) with plausible values.

**Acceptance**
- Company page loads and renders charts + compare pane
- Heatmap click switches selected year-pair
- Term click highlights in compare pane

**Files**
- `public/data/sec_narrative_drift/AAPL/*.json`

---

## Ticket 4 — Build the DriftTimeline component
**Goal:** Timeline chart that can show drift and (optionally) CI bands.

**Steps**
- Create `src/components/DriftTimeline.tsx`
- Inputs:
  - years[]
  - drift_vs_prev[]
  - optional drift_ci_low/high[]
- Behavior:
  - drift null → show gap/gray marker
  - hover tooltip: year, drift, CI, boilerplate score (if available)

**Acceptance**
- Renders with placeholder dataset
- No warnings or layout jitter

**Files**
- `src/components/DriftTimeline.tsx`

---

## Ticket 5 — Build the SimilarityHeatmap component
**Goal:** Year×year heatmap with click selection.

**Steps**
- Create `src/components/SimilarityHeatmap.tsx`
- Inputs:
  - years[]
  - cosineSimilarity[][] (square)
  - onSelectPair(fromYear, toYear)
- Behavior:
  - show value on hover
  - diagonal visually distinct
  - click cell sets active pair and highlights that cell

**Acceptance**
- Click changes compare pane selection
- Handles small matrices (3×3) and larger (10×10)

**Files**
- `src/components/SimilarityHeatmap.tsx`

---

## Ticket 6 — Build TermShiftBars component
**Goal:** Diverging bars (risers vs fallers) for selected year-pair.

**Steps**
- Create `src/components/TermShiftBars.tsx`
- Inputs:
  - selectedPair (from,to)
  - topRisers[], topFallers[]
  - onClickTerm(term)

**Acceptance**
- Clicking a term highlights it in compare pane
- Handles empty shifts gracefully

**Files**
- `src/components/TermShiftBars.tsx`

---

## Ticket 7 — Build ComparePane with deterministic rules
**Goal:** Show representative paragraphs with highlights and term filtering.

**Steps**
- Create `src/components/ComparePane.tsx`
- Inputs:
  - selectedPair
  - excerpts payload (from `excerpts_10k_item1a.json`)
  - highlightTerms (from shifts union or user selection)
- Implement `src/lib/textHighlight.ts`:
  - case-insensitive whole-word highlight with safe HTML escaping

**Acceptance**
- Highlights are correct and do not break punctuation
- No XSS risk: ensure escaping before injecting HTML (or use React fragments)

**Files**
- `src/components/ComparePane.tsx`
- `src/lib/textHighlight.ts`

---

## Ticket 8 — Methodology + Data Quality drawers (hire-facing polish)
**Goal:** Simple but credible explanation + caveats.

**Steps**
- Create `DataProvenanceDrawer` and `Methodology` page:
  - Data source (SEC EDGAR)
  - User-Agent + rate limit adherence
  - “Descriptive not causal”
  - Extraction confidence meaning

**Acceptance**
- Accessible from Company page
- Copy is concise and non-jargony by default

**Files**
- `src/components/DataProvenanceDrawer.tsx`
- `src/pages/Methodology.tsx`

---

## Ticket 8B — “Hire-mode” guided tour + executive callouts (recommended)
**Goal:** Make the app self-explanatory in <60 seconds to non-technical viewers.

**Steps**
- Add an optional “Start tour” button on the Company page.
- Implement 3–4 tour steps (simple overlay) that point to:
  - Drift chart
  - Heatmap
  - Term shifts
  - Compare pane
- Add 3 callout chips above the drift chart:
  - Largest drift year (exclude null)
  - Most stable year
  - Lowest boilerplate (or highest, depending on framing)

**Acceptance**
- Tour can be dismissed and never blocks interaction
- Callouts render correctly even when some years are null

**Files**
- `src/components/Tour.tsx` (or `src/lib/tour.ts`)
- `src/pages/Company.tsx`

---

## Ticket 8C — “Exec Brief” export card (optional, high-impact)
**Goal:** One-click shareable artifact (PNG/SVG) for a hiring manager.

**Steps**
- Create an “Export Exec Brief” button that generates a simple summary card:
  - Company + years
  - Largest drift year + one-sentence summary
  - Top 5 risers + top 5 fallers
  - Small sparkline of drift
  - Data provenance line (SEC EDGAR + filing dates)
- Export as PNG using a client-side approach (e.g., HTML → canvas). Keep it lightweight.

**Acceptance**
- Clicking export downloads a PNG without errors
- Output looks presentable and includes data provenance line

**Files**
- `src/components/ExecBriefCard.tsx`
- `src/lib/exportPng.ts`



---

## Ticket 8D — Copy pack integration (strongly recommended)
**Goal:** Ensure copy is consistently high-quality without Codex inventing phrasing.

**Steps**
- Add `src/lib/copy.ts` containing:
  - a single `copy` object (single tone)
  - a `copy` object keyed by page/component (Home, Company, DriftTimeline, etc.)
  - defaults from `docs/sec_narrative_drift_copy_pack_v1_1.md`
- Replace hard-coded strings across UI with `copy[...]` lookups.

**Acceptance**
- All major UI strings come from `src/lib/copy.ts`
- No missing-string fallbacks in console

**Files**
- `src/lib/copy.ts`
- `src/lib/storage.ts` (optional)
- Updated components/pages



## Ticket 8E — Security + privacy hardening (recommended)
**Goal:** Make the static site resilient against common web risks (especially XSS) and tighten deployment hygiene.

**Steps**
- Add link hygiene everywhere you render SEC URLs:
  - `target="_blank"` and `rel="noopener noreferrer"`
- Add a tiny `src/lib/sanitize.ts` (or similar) with:
  - `escapeHtml(text: string): string` (for any fallback rendering path)
  - `assertSafeExternalUrl(url: string): string` (allowlist `https://www.sec.gov/` only)
- Add a short “Security & privacy” paragraph to the Methodology page:
  - No login, no user accounts, no server-side tracking
  - SEC text treated as untrusted; rendered as plain text with highlights
  - Any notes are stored locally (localStorage) and never uploaded
- Deployment hardening (document-only unless you use Cloudflare):
  - If fronted by Cloudflare, set security headers (CSP, frame-ancestors, Referrer-Policy).
  - If using GitHub Pages alone, note that custom headers are limited; prefer Cloudflare in front if you want CSP.

**Acceptance**
- No place in the UI uses `dangerouslySetInnerHTML`
- External links cannot be replaced with non-SEC domains
- Methodology page includes the Security & privacy paragraph

**Files**
- `src/lib/sanitize.ts` (if needed)
- `src/pages/Methodology.tsx` (copy)


# Pipeline tickets (Python)

## Ticket 9 — Python environment + dependencies
**Goal:** Scripts runnable locally and in GitHub Actions.

**Steps**
- Add `scripts/requirements.txt` with:
  - `requests`
  - `beautifulsoup4`
  - `lxml`
  - `scikit-learn`
  - (optional) `nltk` (only if you need; avoid if not)
- Add `scripts/README.md` describing usage

**Acceptance**
- `python -m venv .venv && pip install -r scripts/requirements.txt` works
- `python scripts/sec_fetch_and_build.py --help` works

**Files**
- `scripts/requirements.txt`
- `scripts/sec_fetch_and_build.py`
- `scripts/README.md`

---

## Ticket 10 — Fixture-first extraction harness
**Goal:** Make extraction logic testable without network.

**Steps**
- Add `scripts/sample_fixtures/` files (from the spec)
- Implement `scripts/sec_extract_item1a.py`:
  - `clean_html_to_text(html: str) -> str`
  - `extract_item_1a(text: str) -> (section_text, confidence, method, errors)`
  - paragraph splitter

**Acceptance**
- Running `python scripts/sec_extract_item1a.py --fixture scripts/sample_fixtures/aapl-20240928.htm` prints:
  - confidence score
  - extracted length
  - first 300 chars preview

**Files**
- `scripts/sec_extract_item1a.py`
- `scripts/sample_fixtures/*`

---

## Ticket 11 — SEC fetch utilities with rate limit + headers
**Goal:** Deterministic, polite SEC requests.

**Steps**
- Implement `scripts/sec_fetch_and_build.py` utilities:
  - `load_ticker_cik_map()`
  - `fetch_submissions_json(cik10)`
  - `iter_recent_filings(submissions) -> list[rows]` (zip arrays into rows)
  - `build_primary_doc_url(cik10, accession, primaryDoc)`
  - `download(url) -> bytes`
- Add:
  - global throttle (<=10 req/sec)
  - backoff on 403/429
  - required `User-Agent` header

**Acceptance**
- Running `--ticker AAPL --limit 1` downloads a 10‑K HTML successfully
- Writes raw HTML into `scripts/_cache/...` (or similar)

**Files**
- `scripts/sec_fetch_and_build.py`

---

## Ticket 12 — Metrics computation (TF-IDF drift + similarity + term shift)
**Goal:** Create the JSON artifacts the UI expects.

**Steps**
- Implement `scripts/sec_metrics.py`:
  - tokenize + stopword removal
  - TF-IDF cosine similarity
  - drift vs prev
  - year×year similarity matrix
  - log-odds term shift w/ smoothing

**Acceptance**
- Given 3 extracted year texts, script outputs:
  - `metrics_10k_item1a.json`
  - `similarity_10k_item1a.json`
  - `shifts_10k_item1a.json`

**Files**
- `scripts/sec_metrics.py`

---

## Ticket 13 — Excerpts builder (deterministic compare pane)
**Goal:** Generate `excerpts_10k_item1a.json` using locked rules.

**Steps**
- Implement excerpt generation:
  - highlightTerms = top 15 risers + top 15 fallers for each year-pair
  - paragraph_score = count(risers) - count(fallers)
  - select top 3 paragraphs per year for each pair

**Acceptance**
- UI compare pane works end-to-end without manual excerpt editing

**Files**
- `scripts/sec_quality.py` (or integrate into build script)

---

## Ticket 14 — Full build script: produce public/data for one ticker
**Goal:** `python scripts/sec_fetch_and_build.py --ticker AAPL --years 10 --out public/data/...`

**Steps**
- Integrate fetch + extract + metrics + excerpts
- Write all required JSON files + section text cache (optional)

**Acceptance**
- Running the script generates a complete folder for AAPL
- UI renders using newly generated data

---

## Ticket 15 — Generate featured datasets (AAPL, NVDA, TSLA)
**Goal:** Refresh three featured companies.

**Steps**
- Run build for each ticker
- Commit generated JSON to repo

**Acceptance**
- Home page lists all featured companies
- Company pages load instantly and consistently

---

## Ticket 16 — GitHub Actions weekly refresh (optional)
**Goal:** Auto-refresh featured company datasets.

**Steps**
- Add workflow to:
  - set up python
  - install requirements
  - run build script for tickers
  - commit changes (using bot token)

**Acceptance**
- Workflow runs on schedule without errors
- Site updates with new filings when available

---

# “Codex prompt templates” (copy/paste per ticket)
Use short prompts; avoid asking for long preambles.

## Prompt template
**Task:** Implement Ticket X from `docs/sec_narrative_drift_codex_implementation_checklist_v1_11.md`.  
**Constraints:** Follow the canonical spec `docs/sec_narrative_drift_codex_spec_v1_11.md`. Don’t change JSON field names.  
**Output:** Make the smallest set of file edits to satisfy acceptance criteria.

Then run one of:
- UI tickets: `npm run build`
- Pipeline tickets: the relevant `python ...` command

Fix errors before moving on.

