# Lab Architecture, Goals, and Design Insights

Last updated: 2026-03-27

## What This App Is
Document Protocol Lab currently ships a bounded visible SEC Item 1A pilot across `NVDA`, `LLY`, and `KO`, each with one active FY2024 to FY2025 fixture.

The public UX is intentionally simple. Users choose a fixture, not a broad issuer gallery, and land in one default reading order: filing answer first, protocol meaning second, deeper audit third.

The lower runtime registry and supporting lab artifacts can remain broader backstage. That backstage breadth supports audit and future work, but it does not widen the visible product claim.

## Core Architecture

### Stack
- React + TypeScript + Vite + Tailwind CSS
- Static JSON pipeline with no backend and no runtime LLM or ML calls
- Static-site deployment

### Data Flow
1. SEC filings are fetched and cleaned offline.
2. Deterministic detectors produce per-method analysis artifacts.
3. Manual model campaigns produce structured outline-compare artifacts offline.
4. Structured artifacts are projected deterministically into runtime compare artifacts.
5. The frontend reads shipped positioning and runtime results from `public/data/...`.

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

Archived legacy lanes such as `det_llm_delta_brief_v1` and `det_llm_excerpt_picker_v1` are no longer part of the active shipped product surface.

## Outline Compare Pipeline
Each campaign and lens can produce three artifact tiers:
1. `llm_outline_compare_structured`: canonical manual authoring unit with alignment, evidence, mechanisms, relevance, and limits.
2. `llm_outline_compare_runtime`: deterministic projection used by the shipped compare UI.
3. `llm_outline_compare_insight`: optional insight layer, not required for the core public flow.

## Public Visible Scope
- Visible pilot only: `NVDA`, `LLY`, and `KO`
- One active FY2024 to FY2025 Item 1A fixture per visible company
- `NVDA`: strongest first signal
- `LLY`: policy-heavy bounded contrast with an explicit stop before full lower-audit runtime depth
- `KO`: restraint / low-drift honesty check with narrower visible comparisons by design

## Backstage Runtime Scope
- Lower runtime registries may still include additional cases, lanes, and supporting artifacts.
- Backstage breadth does not change the visible three-fixture product claim.
- Hidden preregistered lanes remain out of public flow until they earn exposure.

## Public Page Flow
1. **Filing Answer**: the answer and nearby evidence come first.
2. **Protocol Meaning**: the fixture role and comparison geometry come second.
3. **Deeper Audit**: methods, agreement, compare detail, and provenance stay lower on the page.
4. **Optional Insight**: only shown when the sidecar exists.

## UX Defaults
- Quick read is the default mode.
- The default lens is `deboilerplated` because it removes recurring filing boilerplate for a cleaner first read.
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
- Keep public docs, labels, and UX aligned with the visible three-fixture pilot while leaving backstage runtime breadth explicit but secondary.
- Preserve advanced audit controls without letting them dominate the default reading path.
- Continue treating Insight Lens as optional enrichment rather than required surface area.
