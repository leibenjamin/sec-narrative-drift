# SEC Narrative Drift — Codex-Ready Spec (v1.11)
**Project #1 portfolio micro-app**  
**Goal:** A polished, CEO-friendly web app that quantifies and visualizes how a public company’s disclosure language shifts over time, using SEC EDGAR filings (primarily 10‑K Item 1A Risk Factors).

**Design principle:** *Frontend never fetches SEC data directly.* You precompute, cache, and ship static JSON. This avoids SEC rate limits, brittle parsing in-browser, and demo-day failures.

---

## 0) Runbook: exactly what you do (ChatGPT vs VS Code vs Terminal)

This section is written so a **no-web Codex** can succeed with minimal back-and-forth.

### 0.1 Quickstart (recommended order)
1) **VS Code (you):** create repo folder + add steering docs to `docs/`
2) **VS Code (you):** add `AGENTS.md` (Codex rules) + add fixtures
3) **Codex:** implement **UI Tickets 0–8** using placeholder JSON (no SEC work yet)
4) **Codex:** implement **Pipeline Tickets 9–15** using fixtures first, then live SEC fetch
5) **You:** set up GitHub Pages / Cloudflare Pages deployment once `npm run build` is stable

### 0.2 Exactly where/when to do each step

#### Step A — Create the workspace (VS Code + Terminal)
**Where:** VS Code terminal at your chosen parent directory  
**When:** before opening Codex agent

Commands (example):
```bash
mkdir sec-narrative-drift
cd sec-narrative-drift
git init
```

#### Step A2 — GitHub repo (recommended: AFTER first local commit)
**Where:** GitHub.com in your browser  
**When:** after you have the repo folder + docs + `AGENTS.md` in place, and ideally after Ticket 0 or Ticket 3.

**Why later:** it prevents you from pushing half-baked scaffolding and reduces remote churn.

**Do this on GitHub:**
1) Click **New repository**
2) Name: `sec-narrative-drift` (or similar)
3) Choose **Private** while building (optional), make Public when ready
4) Do **NOT** initialize with README (you already have local files)

**Then in VS Code terminal (repo root):**
```bash
git add .
git commit -m "chore: initialize project docs and steering"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

#### Step B — Add steering files (VS Code)
**Where:** repo root  
**When:** before asking Codex to implement Ticket 0

Create:
- `docs/sec_narrative_drift_codex_spec_v1_11.md`
- `docs/sec_narrative_drift_codex_implementation_checklist_v1_11.md`
- `AGENTS.md` (Codex “rules of engagement”)
- `scripts/sample_fixtures/` (offline test inputs)

#### Step C — Verify your toolchain once (VS Code + Terminal)
**Where:** VS Code terminal  
**When:** after Ticket 0 (so Node deps exist), before pipeline work

Check:
```bash
node -v
npm -v
python --version
```

#### Step D — “SEC preflight” network sanity check (YOU)
**Where:** VS Code terminal  
**When:** once, before running the full pipeline tickets

Goal: verify your environment can fetch the three critical resources:
- ticker mapping JSON
- submissions JSON
- one primary document HTML

Example (PowerShell on Windows):
```powershell
$ua = "Ben Lei <your-email@example.com>"
Invoke-WebRequest -Headers @{"User-Agent"=$ua} -Uri "https://www.sec.gov/files/company_tickers_exchange.json" | Select-Object -ExpandProperty StatusCode
Invoke-WebRequest -Headers @{"User-Agent"=$ua} -Uri "https://data.sec.gov/submissions/CIK0000320193.json" | Select-Object -ExpandProperty StatusCode
Invoke-WebRequest -Headers @{"User-Agent"=$ua} -Uri "https://www.sec.gov/Archives/edgar/data/320193/000032019324000058/aapl-20240928.htm" | Select-Object -ExpandProperty StatusCode
```

If any fail:
- verify your User-Agent header is present
- retry slowly (SEC can throttle)
- try again later (temporary blocks happen)

#### Step E — Build UI first with placeholder data (Codex)
**Where:** Codex agent inside this repo  
**When:** immediately after steering files exist

Codex should implement Tickets 0–8 without needing any live SEC calls.

#### Step F — Implement pipeline fixtures-first (Codex)
**Where:** Codex agent + terminal  
**When:** after UI works

Codex implements Tickets 9–13 using `scripts/sample_fixtures/` to validate extraction and metrics deterministically.

#### Step G — Generate featured datasets (Codex)
**Where:** terminal  
**When:** once pipeline works on fixtures

Run:
```bash
python scripts/sec_fetch_and_build.py --ticker AAPL --years 10 --out public/data/sec_narrative_drift/AAPL
```
Repeat for NVDA, TSLA.

#### Step H — Ship (YOU)
**Where:** GitHub Pages / Cloudflare Pages pipeline  
**When:** after `npm run build` succeeds and `/public/data/...` exists

---

### 0.3 Non-negotiable constraints (to avoid Codex thrash)
- Frontend is **static**; it only loads **precomputed JSON** from `public/data/...`
- Do **not** rename JSON fields (contracts are strict)
- Implement Ticket 3 (golden sample dataset) before building visuals
- SEC calls must include User-Agent and rate limiting


---

## 1) What the app does

### 1.1 MVP (target: 8–14 hours)
**Scope locked (to keep implementation reliable):**
- **Forms:** 10‑K only
- **Section:** **Item 1A — Risk Factors** only
- **History:** last **8–10** available filings
- **Companies:** precomputed **3 featured** tickers by default (recommended: `AAPL`, `NVDA`, `TSLA`)
- **Visuals:** (1) drift timeline, (2) year×year similarity heatmap, (3) term shift bars, (4) compare pane with highlighted excerpts
- **Quality:** extraction confidence indicator per year

### 1.2 Overkill (target: +6–12 hours)
Add:
- Bootstrap CI bands around drift
- Boilerplate score (% reused sentences)
- Semantic map (paragraph embeddings + UMAP trajectory)
- Lightweight “peer compare” tab (2–5 tickers)

---

## 2) Data sources & constraints (for implementation)
### 2.1 SEC endpoints (free, no API key)
#### A) Ticker ↔ CIK mapping (SEC file)
Use one of:
- `https://www.sec.gov/files/company_tickers_exchange.json`
- `https://www.sec.gov/files/company_tickers.json`

**Note:** SEC says these mappings are periodically updated but not guaranteed complete/accurate; surface that in your UI as a caveat.

#### B) Company submissions history (JSON)
- `https://data.sec.gov/submissions/CIK##########.json`  
Where `##########` is the **CIK padded to 10 digits** with leading zeros.

#### C) Filing document URL (primary document)
Given:
- `cikNoLeadingZeros = str(int(cik_padded_10))`
- `accessionNumber = "0000320193-24-000058"`
- `accNoNoDashes = accessionNumber.replace("-", "")`
- `primaryDocument = "aapl-20240928.htm"`

Construct:
- `https://www.sec.gov/Archives/edgar/data/{cikNoLeadingZeros}/{accNoNoDashes}/{primaryDocument}`

### 2.2 Required request headers + fairness
Every SEC request MUST include:
- `User-Agent: Ben Lei <your-email@example.com>`
- `Accept-Encoding: gzip, deflate, br` (optional, helps)
- `Host: www.sec.gov` or `data.sec.gov` as appropriate

**Rate limiting:** enforce **≤ 10 requests/second** (global) with backoff on 403/429.

---

## 3) Product narrative (what you say to hirers)

### 3.1 Executive framing
**Narrative Drift Index (NDI)**: “How much the company’s risk story changed vs the prior year.”

Use language like:
- “New risk themes emerged”
- “Disclosure stabilized (boilerplate reuse increased)”
- “Shift likely reflects major business or macro changes”

### 3.2 Causality guardrails
The app is **descriptive**, not causal:
- “This tool flags language changes; causal explanations are hypotheses.”
- Provide a “Hypothesis notes” field (saved in localStorage) so a hirer can see you think like a scientist.

---

## 4) UX & flows (demo-safe)

### 4.1 Flow A: Instant demo (default)
Landing → pick one featured company → dashboard loads instantly from `public/data/...` with no network calls.

### 4.2 Flow B: Explore any ticker (optional later)
Either:
- Disabled (MVP): show “Coming soon” + link to featured companies.
- Enabled (Overkill): trigger a backend refresh job (not recommended for a static site demo).

### 4.3 Dashboard layout
**Top bar:** Company selector, section selector (only Item 1A in MVP), years, “Methodology”, “Data Quality”.

**Row 1:** Drift timeline + callouts (“largest drift year”, “most stable year”)  
**Row 2:** Similarity heatmap (year×year) — click cell to compare those two years  
**Row 3:** Term shift (riser/faller bars) — click term to highlight in compare pane  
**Row 4:** Compare pane — representative paragraphs with highlighted terms

---

## 4.4 Hire-mode: how the app should “read” to skeptical reviewers
Assume the viewer believes this was largely AI-assisted. Your goal is to show *judgment, rigor, and constraints*.

### What to emphasize on the page (above the fold)
- **One-sentence claim:** “Quantifies how a company’s Risk Factors language changes year-to-year.”
- **Data provenance:** “Source: SEC EDGAR 10‑K, Item 1A.”
- **Reliability cues:** “Precomputed datasets; extraction confidence per year; descriptive (not causal).”
- **Actionability cues:** “Largest drift year”, “Most stable year”, “Top new terms”.

### What to hide behind drawers (progressive disclosure)
- TF‑IDF details, tokenization, smoothing constants
- any CI/permutation test math
- extraction heuristics and regex details

### “Answer scripts” for common skeptical questions
- **Q: Did you build the NLP model yourself?**  
  A: “The app is intentionally lightweight (TF‑IDF + robust extraction) because the value is the reproducible pipeline and the executive-readable storytelling. Overkill mode adds embeddings/UMAP, but I prioritized reliability.”
- **Q: Is this causal / does drift mean trouble?**  
  A: “No. It’s descriptive. Drift is a prompt to ask *why* language changed, not an answer.”
- **Q: How do you know extraction is correct?**  
  A: “I score extraction confidence and surface low-confidence years. The pipeline is fixture-tested; the compare pane lets you verify by reading the source text.”

### Add a “1-minute tour” mode (recommended)
A small guided overlay that highlights:
1) what drift means, 2) how to click the heatmap, 3) what term shifts mean, 4) how to sanity-check in compare pane.



**Copy pack:** Use `docs/sec_narrative_drift_copy_pack_v1_1.md` for all labels/tooltips.

**Tone guidance:** Ship a single public tone. Humor should be sparse and functional (microcopy), not a feature.


---

## 5) Repo structure (recommended)
```
sec-narrative-drift/
  README.md
  package.json
  vite.config.ts
  src/
    App.tsx
    pages/
      Home.tsx
      Company.tsx
      Methodology.tsx
    components/
      DriftTimeline.tsx
      SimilarityHeatmap.tsx
      TermShiftBars.tsx
      ComparePane.tsx
      QualityBadge.tsx
      DataProvenanceDrawer.tsx
    lib/
      data.ts
      types.ts
      textHighlight.ts
  public/
    data/
      sec_narrative_drift/
        AAPL/
          meta.json
          filings.json
          metrics_10k_item1a.json
          similarity_10k_item1a.json
          shifts_10k_item1a.json
          excerpts_10k_item1a.json
        NVDA/...
        TSLA/...
  scripts/
    requirements.txt
    sec_fetch_and_build.py
    sec_extract_item1a.py
    sec_metrics.py
    sec_quality.py
    sample_fixtures/
      company_tickers_exchange.json
      CIK0000320193.json
      aapl-20240928.htm
  .github/workflows/
    refresh_featured.yml
```

---

## 6) Data pipeline — step-by-step (no ambiguity)

### 6.1 Step 0: fixtures (Codex-proofing)
Include `scripts/sample_fixtures/` with:
- one mapping file
- one submissions JSON
- one 10‑K HTML file
This allows Codex to develop extraction logic offline and run tests deterministically.

### 6.2 Step 1: ticker → CIK
Parse mapping JSON into dict:
- key: tickerUpper
- value: `{ cik, name, exchange }`

Normalize:
- uppercase ticker
- trim whitespace

### 6.3 Step 2: fetch submissions JSON
URL: `https://data.sec.gov/submissions/CIK{cik10}.json`

The `filings.recent` content is “columnar arrays” (parallel arrays).  
Convert to row objects by zipping arrays using shared indices.

Minimum fields to extract:
- `form`
- `filingDate`
- `reportDate` (if present)
- `accessionNumber`
- `primaryDocument`

Filter to `form == "10-K"` (ignore amendments for MVP unless you want them).

Take last N (8–10) by filingDate.

### 6.4 Step 3: download primary document HTML
Construct URL using the formula in §2.1C.

Store raw HTML to disk for reproducibility.

### 6.5 Step 4: HTML → cleaned text
Rules:
- remove `<script>`, `<style>`, `<noscript>`
- drop or heavily downweight `<table>` content (tables create noise)
- convert block tags to newlines (`p`, `div`, `br`, `li`, headings)
- normalize whitespace (collapse 3+ newlines to 2)

### 6.6 Step 5: extract Item 1A Risk Factors
**Two-pass extraction** (robust, implementable)

Pass A (regex heading boundaries):
- Find start index by matching any of:
  - `(?i)\bitem\s+1a\b`
  - `(?i)\brisk\s+factors\b` (near “item 1a”)
- Find end index by matching next item heading:
  - `(?i)\bitem\s+1b\b`
  - else `(?i)\bitem\s+2\b`

Pass B (fallback):
- If Pass A fails:
  - locate “RISK FACTORS” heading and take the next X characters (e.g., 80k) or until a strong “ITEM 1B/2” pattern appears
- If still fails:
  - mark extraction as low confidence and store an empty string + error for that year

### 6.7 Step 6: segment into paragraphs
Split on blank lines, keep paragraphs with length ≥ 200 chars.

Store:
- full section text
- paragraph list

---

## 7) Metrics (MVP + deterministic)

### 7.1 TF-IDF drift (primary)
For each year:
- build TF-IDF vectors over paragraphs (or whole section)
- compute cosine similarity between year t and year t−1
- define drift as `1 - similarity`

### 7.2 Year×year similarity matrix
Compute cosine similarity for all pairs of years.

### 7.3 Term shift (log-odds with smoothing)
Compare year t vs t−1:
- tokenize to terms (lowercase, alpha terms, remove stopwords)
- compute log-odds ratio with Dirichlet prior
- output top 15 risers and top 15 fallers

### 7.4 Boilerplate score (recommended even in MVP)
Compute approximate reuse rate:
- split into sentences
- compute minhash or shingled Jaccard similarity between sentence sets
- `boilerplate_score = reused_sentences / total_sentences`

---

## 8) Significance checks (optional but impressive)
Pick ONE (doable):
### Option A: bootstrap CI for drift
- sample paragraphs with replacement within each year (200–500 iterations)
- recompute drift each iteration
- report 5th/95th percentile as CI

### Option B: permutation test
- pool paragraphs from both years
- random split into two pseudo-years repeatedly
- compute drift distribution under “no structured difference”

UI shows “drift vs noise floor”.

---

## 9) Frontend JSON contracts (strict)
### 9.1 meta.json
```json
{
  "ticker": "AAPL",
  "cik": "0000320193",
  "companyName": "Apple Inc.",
  "lastUpdatedUtc": "2025-12-25T18:30:00Z",
  "formsIncluded": ["10-K"],
  "sectionsIncluded": ["10k_item1a"],
  "notes": [
    "Ticker/CIK mapping is SEC-provided and may be incomplete or outdated.",
    "Narrative Drift is descriptive; causal explanations are hypotheses."
  ]
}
```

### 9.2 filings.json
```json
[
  {
    "year": 2024,
    "form": "10-K",
    "filingDate": "2024-11-01",
    "reportDate": "2024-09-28",
    "accessionNumber": "0000320193-24-000058",
    "primaryDocument": "aapl-20240928.htm",
    "secUrl": "https://www.sec.gov/Archives/edgar/data/320193/000032019324000058/aapl-20240928.htm",
    "extraction": { "confidence": 0.9, "method": "regex_item1a_to_item1b", "errors": [] }
  }
]
```

### 9.3 metrics_10k_item1a.json
```json
{
  "section": "10k_item1a",
  "years": [2016,2017,2018,2019,2020,2021,2022,2023,2024],
  "drift_vs_prev": [null,0.12,0.09,0.15,0.33,0.18,0.11,0.14,0.10],
  "drift_ci_low": [null,0.08,0.05,0.10,0.27,0.12,0.07,0.09,0.06],
  "drift_ci_high":[null,0.16,0.13,0.20,0.40,0.24,0.15,0.19,0.14],
  "boilerplate_score": [null,0.62,0.70,0.64,0.48,0.55,0.60,0.58,0.63]
}
```

### 9.4 similarity_10k_item1a.json

**Note:** `cosineSimilarity` is an N×N square matrix aligned to `years` (same order).
```json
{
  "section":"10k_item1a",
  "years":[2022,2023,2024],
  "cosineSimilarity":[
    [1.0,0.88,0.86],
    [0.88,1.0,0.89],
    [0.86,0.89,1.0]
  ]
}
```

### 9.5 shifts_10k_item1a.json
```json
{
  "section":"10k_item1a",
  "yearPairs":[
    {
      "from": 2019,
      "to": 2020,
      "topRisers":[{"term":"pandemic","score":5.2},{"term":"supply chain","score":4.8}],
      "topFallers":[{"term":"tablet","score":-3.1},{"term":"ipod","score":-2.7}],
      "summary":"2020 adds health/supply-chain terms; older product-line risks fade."
    }
  ]
}
```

### 9.6 excerpts_10k_item1a.json (deterministic compare pane)
```json
{
  "section":"10k_item1a",
  "pairs":[
    {
      "from": 2019,
      "to": 2020,
      "highlightTerms":["pandemic","supply chain","remote","inventory"],
      "representativeParagraphs": [
        {
          "year": 2020,
          "paragraphIndex": 12,
          "text": "..."
        },
        {
          "year": 2019,
          "paragraphIndex": 8,
          "text": "..."
        }
      ]
    }
  ]
}
```

---

## 10) Compare pane highlight rules (locked for MVP)
When user selects a year-pair:
1) highlight the union of top **15 risers + 15 fallers**
2) pick “representative paragraphs” by score:
   - `paragraph_score = count(riser_terms) - count(faller_terms)`
3) show top 3 paragraphs from each year, with highlighted terms

This is deterministic and easy for Codex.

---

## 11) QA & failure handling
### 11.1 Pipeline QA
- If extraction confidence < 0.5, still write JSON, but:
  - set `errors: ["low_confidence_item1a"]`
  - use an empty section string and skip metrics for that year (set nulls)
- Always ensure:
  - similarity diagonal is exactly 1.0
  - drift_vs_prev[0] is null

### 11.2 Frontend QA
- UI must never crash if some years have null drift (skip or gray out)
- Heatmap click must degrade gracefully if excerpt data missing

---

## 12) Deployment & refresh (safe)
### 12.1 Recommended: scheduled refresh with GitHub Actions
Workflow:
- weekly cron
- run Python scripts
- commit `public/data/...` updates
- redeploy

### 12.2 Demo safety
The production site should remain functional even if SEC endpoints are down because the user experience uses precomputed JSON.


## 13) Performance, security, and privacy
This app is designed to be **static + precomputed** (no server-side user sessions). That already eliminates most privacy and attack-surface concerns, but there are still a few best-practice guardrails.

### 13.1 Performance best practices
- Keep shipped JSON small and intentional:
  - Do **not** ship full filing text; ship only the excerpts needed for the compare pane.
  - Prefer short, representative paragraphs over long blocks.
- Load data **on demand** (lazy fetch):
  - Company page fetches `meta.json`/`filings.json`/`metrics...` first.
  - Fetch `excerpts...` only after a year-pair is selected (or after initial render).
- Keep the initial JS bundle lean:
  - Use route-based code splitting (Home vs Company vs Methodology).
  - Avoid heavyweight chart libraries unless needed; simple SVG is fine.
- Host should serve gzip/brotli; static assets are cacheable.

### 13.2 Security best practices (static site)
**Primary risk: XSS via untrusted SEC-derived text.**
- Treat all extracted text as **untrusted**:
  - Render as plain text in React nodes.
  - Highlight by splitting into spans; avoid injecting HTML.
  - Avoid `dangerouslySetInnerHTML`. If you must use it, escape then sanitize and lock down CSP.
- External links:
  - `target="_blank"` + `rel="noopener noreferrer"`.
  - Do not allow arbitrary domains; the SEC link should be from the pipeline (or allowlisted).
- Recommended headers (best via Cloudflare or a proxy in front of GitHub Pages):
  - `Content-Security-Policy` (CSP) (start strict, relax only if needed)
  - `Referrer-Policy: no-referrer` (or `strict-origin-when-cross-origin`)
  - `X-Content-Type-Options: nosniff`
  - `Permissions-Policy` (disable unused sensors)
  - `Cross-Origin-Opener-Policy: same-origin` (optional; test before enabling)
  - `frame-ancestors 'none'` in CSP to block clickjacking

### 13.3 Privacy best practices
- No accounts, no login, no user PII collection.
- If you add a “Hypothesis notes” field stored in localStorage:
  - Label it explicitly: “Stored locally in your browser; never uploaded.”
  - Provide a “Clear notes” button.
- Avoid third-party analytics/CDNs by default; if you add analytics, disclose it.

### 13.4 Pipeline security + fairness (SEC)
- Always include a descriptive `User-Agent` with contact info and respect SEC fair-access limits (≤10 requests/sec).
- Use timeouts and backoff on 403/429.
- Cache raw downloads locally and in CI to reduce repeated requests.

---

# Appendix A — Codex 5.2 Thinking audit (3 iterations)

## A1) Iteration 1: “No-web Codex risk” scan
**Top failure risks:**
- brittle Item 1A extraction
- misunderstanding SEC submissions JSON shape (parallel arrays)
- rate limiting and User-Agent omitted

**Patches included in v1.1:**
- fixtures folder for offline development
- explicit “zip arrays into rows”
- hard-coded header requirements + throttle rules
- fallback extraction pass + confidence scoring

## A2) Iteration 2: “Implementation minimalism” scan
**Risk:** Too broad scope overwhelms the build.
**Patch:** locked MVP scope to **10‑K Item 1A only** and **3 featured companies**.

## A3) Iteration 3: “Data contract clarity” scan
**Risk:** frontend/pipeline mismatch causes thrash.
**Patch:** strict JSON schemas + deterministic compare-pane rules + required files listed.

---

# Appendix B — Hirer/coworker UX evaluation (5 personas)

## B1) CEO / GM
Wants: “Tell me what changed and why I should care.”
✅ Timeline + callouts + one-sentence summaries per spike.  
⚠️ Must hide NLP jargon by default (keep in Methodology drawer).  
**Add:** “Exec Brief” export button (PNG + bullets).

## B2) Product leader
Wants: “How do risks shift with product lines and launches?”
✅ Term shift + compare paragraphs gives narrative evidence.  
**Add:** optional “Tag as product risk / legal / supply chain” labeling.

## B3) Sales exec
Wants: “Are customer / pricing / channel risks changing?”
✅ Can filter terms by category (supply chain, competition, pricing).  
**Add:** term-category facet (simple keyword-based mapping).

## B4) Data science lead
Wants: “Is this reproducible, robust, and honest?”
✅ Data provenance, extraction confidence, bootstrap/permutation option.  
**Add:** show “noise floor” or CI bands when enabled.

## B5) Engineer / analytics engineer
Wants: “Is this maintainable and not a pile of magic?”
✅ pipeline scripts + fixtures + strict contracts.  
**Add:** unit tests for extraction patterns on fixtures.

---

# Appendix C — Release checklist (MVP)
- [ ] UI works with precomputed AAPL/NVDA/TSLA JSON
- [ ] Pipeline runs end-to-end for 1 ticker producing all required files
- [ ] Extraction confidence is shown per year
- [ ] Heatmap click opens compare pane
- [ ] Term click highlights in compare pane
- [ ] Methodology drawer clearly states “descriptive, not causal”
