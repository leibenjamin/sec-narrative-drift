# Lab Architecture, Goals, and Design Insights

Last updated: 2026-04-16

## What This App Is
Document Protocol Lab is an interactive casebook that compares approaches to business-document reading with frontier LLMs across six public SEC Item 1A cases: three anchor cases (`NVDA`, `LLY`, `KO`) plus three added-pressure cases (`META`, `TSLA`, `WMT`). Each case uses an adjacent-year pair under the company-official fiscal-year convention — FY2024 to FY2025 for most cases, FY2025 to FY2026 for `WMT`.

The visible unit of comparison is the approach, not the company. Three approaches are compared on the same substrate: plain prompt (control), structured contract (typically the primary read), and tagged protocol (comparator). Every multi-cell case renders a side-by-side of the control read and the primary read so the approach verdict is visible without a click.

The public UX is intentionally narrow. Visitors compare approaches across a curated casebook — not a broad issuer gallery, not an upload flow, not a whole-filing research platform. Lower runtime registries and supporting lab artifacts remain broader backstage but do not widen the visible product claim or the three-approach count. In particular, the legacy Core4 runtime registry (`NVDA`/`KO`/`WM`/`GE` under `public/data/sec_narrative_drift_lab/`) is a separate backstage surface from the public casebook data under `public/data/business_document_protocol_lab/`. Both still coexist, but only the latter maps to the shipped six-case public route.

## Two-Level Grammar
The product has two grammars operating at different levels, and they are intentionally distinct:

- **App-level grammar — Read → Compare → Verdict.** This is how the product compares approaches across cases. It appears on Home (the approach-verdict tile, the three-approach signal) and on Methodology (the approach catalog). This is the distinctive claim.
- **Per-case anatomy — filing answer → proof → stop → appendix.** This is how a visitor reads one case after the approach is chosen. It is familiar casebook reading and lives on each company page.

Conflating these two levels was a real risk during the reframe. The `WorkflowAnatomyDiagram` header therefore names itself "Case page anatomy (after an approach is chosen)" to disambiguate from the app-level Read/Compare/Verdict grammar.

## Core Architecture

### Stack
- React + TypeScript + Vite + Tailwind CSS
- Static JSON pipeline with no backend and no runtime LLM or ML calls
- Static-site deployment

### Data Flow
1. SEC filings (10-K HTML) are fetched from EDGAR and extracted into plain text offline by deterministic Python scripts (`sec_extract_item1a.py`). No LLM is involved in extraction.
2. Extracted text is split into paragraphs (`build_lab_outputs.py`) and optionally filtered through the deboilerplated lens (see below). No LLM is involved in these steps.
3. Deterministic detectors produce per-method analysis artifacts (log-odds, JSD, MinHash, winnowing, structure, RBO agreement).
4. The LLM input bundle is assembled from the deterministic paragraph arrays — pair manifests + per-year files with SHA256 integrity metadata. **All LLM inputs are produced entirely by deterministic scripts with no LLM pre-processing.** The LLM being evaluated sees the full filing text (or deboilerplated subset), not a prior model's interpretation of it.
5. Manual model campaigns produce structured outline-compare artifacts offline.
6. Structured artifacts are projected deterministically into runtime compare artifacts.
7. The frontend reads shipped positioning and runtime results from `public/data/...`.

### Cleaning Lenses
- **`raw`**: The full extracted Item 1A text, split into paragraphs. Nothing is removed.
- **`deboilerplated`**: A deterministic sentence-level set-difference filter. Each year's text is split into sentences, normalized (lowercased, whitespace-collapsed), and the intersection (sentences whose normalized form appears identically in both years) is removed. Only sentences unique to each year are retained. This is a conservative exact-match filter — no LLM, no semantic similarity, no ML. It removes recurring legal boilerplate that is copy-pasted year to year, leaving the sentences that actually changed.

The deboilerplated lens is the default because it produces a cleaner first read by removing noise that would trivially inflate apparent similarity between filings. Both lenses are available in the UI for comparison.

### Public Positioning Files
- `public/data/business_document_protocol_lab/product_positioning/current_case_mix_v2.json`: visible fixture mix and public anti-hype framing.
- `public/data/business_document_protocol_lab/product_positioning/start_here_v1.json`: recommended start path and reading order.
- `public/data/business_document_protocol_lab/product_positioning/demo_share_v3.json`: public one-line description and share metadata.

### Lower Runtime Registries
- `lab_cases_v1.json`: lower backstage ticker and case coverage used by runtime loaders.
- `lab_llm_campaigns_v1.json`: active compare-visible model campaigns.
- `lab_llm_variants_v1.json`: runtime compare variant coverage per campaign, ticker, case, and lens.
- `lab_method_tracks_v1.json`: deterministic and model track mapping to shipped artifacts.
- `lab_method_profiles_v1.json`: canonical usage, failure modes, and references for active deterministic methods.

## Deterministic Detectors
- `det_logodds_terms_v1`: ranks distinctive word shifts.
- `det_jsd_ngrams_v1`: measures distribution drift across n-grams.
- `det_minhash_boilerplate_v1`: estimates near-duplicate paragraph reuse.
- `det_winnowing_fingerprint_v1`: surfaces exact reused spans.
- `det_structure_artifacts_v1`: tracks heading and section-shape changes.
- `det_rbo_agreement_v1`: summarizes cross-method agreement.

### Archived legacy LLM lanes (DO NOT USE for new cases)
- `det_llm_delta_brief_v1`: flat delta brief (Change/Drivers/Caveat) — **ARCHIVED**.
- `det_llm_excerpt_picker_v1`: paragraph excerpt selection — **ARCHIVED**.

These legacy lanes are no longer part of the active shipped product surface.
The build script `scripts/lab_prompt_blocks.py` still generates templates for these
lanes in `prompt_templates_showcase.md`, but those templates must NOT be used for
casebook expansion or any new LLM jobs. Use the outline compare structured workflow
(below) and Protocol Lab pilot matrix prompts (in `docs/protocol_lab/prompts/`) instead.

## Outline Compare Pipeline (active shipped workflow)
Each campaign and lens can produce three artifact tiers:
1. `llm_outline_compare_structured`: canonical manual authoring unit with alignment, evidence, mechanisms, relevance, and limits.
2. `llm_outline_compare_runtime`: deterministic projection used by the shipped compare UI.
3. `llm_outline_compare_insight`: optional insight layer, not required for the core public flow.

## Protocol Lab Pilot Matrix (core product experiment)
The pilot matrix is the core product experiment. Each case has cells representing different approach reads on the same filing pair, and the comparison between cells is what the product surfaces on the case page. The primary surface is the `ProtocolPreviewCard` component, which renders `comparison_pairs[0]` (control read vs primary read) as a side-by-side block visible without a disclosure click. Data lives in `public/data/business_document_protocol_lab/`.

Prompt templates in `docs/protocol_lab/prompts/`:
- `p0_plain_prompt_v1.md`: unstructured plain-prompt baseline (control).
- `p1_structured_contract_v1.md`: structured contract (typically the primary read).
- `p2_tagged_input_contract_v1.md`: tagged input contract (comparator).
- `p4_novelty_ledger_contract_v1.md`: novelty ledger (available on a subset of cases for deeper structural comparison).

A fourth approach (`p3_extract_then_synthesize`) has prompt templates in the same folder but no authored cell data in any case. It is not claimed as live, and Home's three-approach signal excludes it deliberately.

Each cell produces `change_brief` + `evidence_bundle` (+ `novelty_ledger` for p4 where authored).

### Casebook LLM job bundles
For preparing ChatGPT Desktop LLM jobs for new casebook cases, use:
- `scripts/build_casebook_candidate_inputs_bundle.py`
- `bundles/.../prompt_templates_casebook.md`
- `docs/lab/12_casebook_candidate_workflows.md`

Do **not** use:
- `prompt_templates_showcase.md`
- `det_llm_delta_brief_v1`
- `det_llm_excerpt_picker_v1`
- legacy focuspack / pilot-pack helpers as candidate-prep sources of truth

Candidate-prep fiscal-year policy also follows the official company fiscal-year convention.
That means `WMT` remains `FY2025 vs FY2026`, consistent with `NVDA`. A later switch to a
“bulk of 12 months” convention would be a repo-wide relabeling decision, not a one-off fix.

## Public Visible Scope
- Public casebook: `NVDA`, `LLY`, `KO`, `META`, `TSLA`, and `WMT`.
- Home anchor cases: `NVDA`, `LLY`, `KO`.
- Added-pressure cases surfaced inside the Casebook: `META`, `TSLA`, `WMT`.
- Adjacent-year Item 1A pair per case, using the company-official fiscal-year convention (FY2024 to FY2025 for most; FY2025 to FY2026 for `WMT`).
- Three approaches compared: plain prompt, structured contract, tagged protocol. A fourth (extract-then-synthesize) has templates but no authored cells and is not claimed as live.
- `NVDA`: strongest structural lift from moving beyond a plain-prompt read.
- `LLY`: honest stop tightening under structure.
- `KO`: useful restraint — one cell by design, and the product lets that be enough.
- `META`: sharper AI enforcement and platform-liability pressure under structure.
- `TSLA`: policy shock and autonomy-commercialization pivot.
- `WMT`: calm retail case whose customer-interface risk and tariff persistence only surface once the approach earns them.
- `GOOGL` remains reserve and `UNH` remains hold/internal-only.
- Canonical public-casebook ticker lists live in `src/lib/casebookContent.ts` (`HOME_ANCHOR_TICKERS` and `PUBLIC_CASEBOOK_TICKERS`).

## Backstage Runtime Scope
- The legacy Core4 lab runtime registry (`public/data/sec_narrative_drift_lab/lab_cases_v1.json`) still covers `NVDA`, `KO`, `WM`, and `GE` with deterministic detector outputs and LLM outline-compare artifacts. It powers the older outline-compare runtime surfaces but is not the source of truth for the public casebook's six-case route.
- The active public casebook is served from `public/data/business_document_protocol_lab/` and is sourced from the casebook-candidate bundle builder (`scripts/build_casebook_candidate_inputs_bundle.py`) plus the protocol-lab pilot-matrix cells.
- Backstage Core4 breadth does not change the six-case public product claim.
- Hidden preregistered lanes remain out of public flow until they earn exposure.

## App-Level Surface: Approach Comparison
1. **Home** surfaces the approach tile (three approaches compared across six cases) and the approach-verdict framing.
2. **Methodology** surfaces the approach catalog (input shape, output shape, what each approach earns, when it helps, when it is theater) and a worked-comparison example block.
3. **Case page** surfaces the side-by-side approach comparison (`comparison_pairs[0]`: control read vs primary read) as the top disclosure-free block, then the per-case anatomy below it.
4. **Deterministic detector arm** is preserved on Methodology under a `<details>` disclosure labelled as a control arm, not as the product.

## Per-Case Page Anatomy (after an approach is chosen)
1. **Filing answer**: the answer and nearby evidence come first.
2. **Proof**: the structured evidence the approach produced.
3. **Stop**: what the approach explicitly does not claim, and why.
4. **Appendix / optional insight**: methods, agreement, compare detail, and provenance stay lower on the page.

## UX Defaults
- Quick read is the default mode.
- The default lens is `deboilerplated` because it removes recurring filing boilerplate (sentences shared verbatim between both years) for a cleaner first read. See the "Cleaning Lenses" section above for the exact mechanism.
- Single-case company pages do not foreground case-picking UI.
- Campaign overrides, detector checkboxes, utilities, and jump links live under `Advanced controls`.
- Existing `/company/:ticker` deep links and `from`, `to`, `llmA`, and `llmB` query params remain supported.

## Design Principles

### Deterministic-First
Every public analysis starts from reproducible, auditable methods. Precomputed model artifacts enrich the interpretation; they do not replace the deterministic baseline or introduce runtime inference.

### Evidence-Backed Trust
Users can trace claims back to filing text through snippets, paragraph indices, and structured evidence groupings.

### Explicit Absence
Missing artifacts should remain visible and path-explicit. The app should not silently imply coverage that does not exist.

### Filing-First Tone
Copy should speak to people interested in how the filing changed, not to evaluators of a demo or showcase artifact.

## Current Improvement Focus
- Keep public docs, labels, and UX aligned with the approach-comparison framing across the six-case public casebook. The backstage Core4 runtime remains explicit but secondary.
- Preserve the disambiguation between the app-level Read/Compare/Verdict grammar and the per-case filing-answer/proof/stop anatomy. Both appear in the UI on purpose; conflating them was the main staleness risk during the reframe.
- Extend `PEDAGOGIC_COMPARE_EXAMPLES` in `src/lib/casebookContent.ts` to cover the three anchor cases (`NVDA`, `LLY`, `KO`) in addition to the existing `TSLA` and `META` breakdowns. The side-by-side approach comparison block is already live on every multi-cell case; the gap is in the authored worked-example text.
- Keep the deterministic detector arm under a disclosure as a control arm rather than letting it dominate the default reading path.
- Keep the approach count honest. Three approaches are live; a fourth (extract-then-synthesize) has templates but no authored cells and is not claimed.
