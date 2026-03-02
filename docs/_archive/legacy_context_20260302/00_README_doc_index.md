# SEC Narrative Drift - Docs Index (Canonical)

This folder contains planning/spec docs for the SEC Narrative Drift portfolio app.

Canonical rule: Treat this file (`docs/00_README_doc_index.md`) as the only canonical index.
If anything conflicts, patch the docs instead of improvising.

Status (2026-01-29): Canonical index. Updated to reflect security/performance best practices implementation.

## Canonical sources and versioning
- `docs/sec_narrative_drift_codex_spec_v1_13.md` (source of truth: product + data contract)
- `docs/sec_narrative_drift_codex_implementation_checklist_v1_13.md` (ticket order + acceptance criteria)
- `docs/sec_narrative_drift_copy_pack_v1_1.md` (UI strings)
- `docs/sec_narrative_drift_humor_notes_v1_1.md` (optional tone guidance)
- `docs/sec_risk_extraction_upgrade_codex_pack_v2.md` (canonical for extraction algorithm details + triage/testing; does not change public JSON schemas; supersedes v1)
- `docs/lab/00_LAB_CANONICAL_SPEC.md` (canonical for Narrative Drift Lab pivot)
- `docs/lab/01_METHODS_SCORECARD.md` (Lab methods quick reference)

## Read order for Codex (day-to-day)

### 0) **Codex Analysis: Risk Extraction Hardening (Tickets 8-11)** *
Deep analysis of 12 critical failures in 79 filings. Complete implementation plan for risk extraction fix. Start here if implementing Tickets 8-11 (or if you're new and want comprehensive context).

- [CODEX_START_HERE.md](CODEX_START_HERE.md) -- Quick orientation + document index (10 min)
- [CODEX_COMPREHENSIVE_ANALYSIS_SUMMARY.md](CODEX_COMPREHENSIVE_ANALYSIS_SUMMARY.md) -- Executive overview (15 min)
- [CODEX_MASTER_IMPLEMENTATION_GUIDE_8_11.md](CODEX_MASTER_IMPLEMENTATION_GUIDE_8_11.md) -- Complete cookbook (primary reference)
- [CODEX_TICKET_PLAN_8_11.md](CODEX_TICKET_PLAN_8_11.md) -- Detailed ticket specs (reference)
- [CODEX_HISTORICAL_ANALYSIS_AND_INTEGRATION.md](CODEX_HISTORICAL_ANALYSIS_AND_INTEGRATION.md) -- Why we're here + context
- [CODEX_DELIVERABLES_MANIFEST.md](CODEX_DELIVERABLES_MANIFEST.md) -- What was delivered
- [chatgpt_bundle_manifest_template.md](chatgpt_bundle_manifest_template.md) -- Template manifest for ChatGPT export bundles
- [normalize_doc_ascii.md](normalize_doc_ascii.md) -- Utility: normalize docs to ASCII to avoid mojibake

1) **Spec (canonical)**
- `docs/sec_narrative_drift_codex_spec_v1_13.md`

2) **Implementation checklist (canonical tickets)**
- `docs/sec_narrative_drift_codex_implementation_checklist_v1_13.md`

3) **Extraction upgrade (active, canonical for extraction details + testing)**
- `docs/sec_risk_extraction_upgrade_codex_pack_v2.md`

4) **Copy pack (UI strings)**
- `docs/sec_narrative_drift_copy_pack_v1_1.md`
- `docs/sec_narrative_drift_humor_notes_v1_1.md` (optional; only if touching copy)

5) **Extraction hardening + canonical terms (applied in repo; reference only)**
- `docs/sec_narrative_drift_item1a_extraction_hardening_patch_pack_v1_0.md` (legacy; superseded by risk extraction upgrade)
- `docs/sec_narrative_drift_canonical_terms_builder_patch_pack_v1_0.md`
- `docs/sec_narrative_drift_canonical_terms_ui_includes_patch_pack_v1_0.md`

6) **Accuracy / signal upgrades (applied in repo; reference only)**
- `docs/sec_narrative_drift_accuracy_signal_patch_pack_v1_0.md` (patch-style diffs already applied)
- `docs/sec_narrative_drift_accuracy_signal_upgrade_v1_1.md` (background + rationale)
- `docs/sec_narrative_drift_accuracy_upgrade_codex_pack_v1_3.md` (optional expansion plan)

7) **Universe + directory expansion (applied in repo; reference only)**
- `docs/sec_narrative_drift_company_directory_patch_pack_v1_1.md`
- `docs/sec_narrative_drift_universe_and_featured_stories_codex_pack_v1_0.md`

8) **Post-launch roadmaps (active backlog; many tickets completed)**
- `docs/sec_narrative_drift_postlaunch_roadmap_and_ticket_pack_v1_2.md`

9) **Portfolio polish (optional, not canonical; archived)**
- `docs/_archive/sec_narrative_drift_portfolio_eval_and_trust_tickets_v1_0.md`
- `docs/_archive/sec-narrative-drift_next-roadmap_and_prior-art_audit.md`

10) **Context memos (non-canonical; may be stale)**
- `docs/sec_narrative_drift_current_state_and_sec_access_obstacles.md`
- `docs/sec_narrative_drift_sec_edgar_api_context.md`

11) **Pipeline map (living)**
- `docs/sec_pipeline_map_v1.md`

## Implementation status snapshot (2026-01-29)
- BlockDoc extraction upgrade applied (TOC scoring, candidate selection, cleanup, quality gates); see `docs/sec_risk_extraction_upgrade_codex_pack_v2.md`.
- Item 1A extraction hardening patch pack applied (legacy reference).
- Canonical terms builder + report in `scripts/resources` and `scripts/_reports`; `sec_metrics.py` emits `includes`.
- Term shifts UI includes "Includes" variants + "Why group terms" tooltip on Company page.
- Featured tickers are configured in `scripts/universe_featured.json` (no special pipeline; fixtures are opt-in only).
- Universe + directory expansion in place: `universe_featured.json`, `featured_cases.json`, `index.json`, and company directory UI.
- Postlaunch tickets 17-26 applied: Executive Summary, heatmap legend/affordance, SelectedPairCallout, CI band, QualityBadge, lazy-loaded excerpts, `_headers`, README.
- Golden snapshot for review: `scripts/_cache/metrics_demo` (metrics, similarity, shifts, excerpts).
- Local SEC cache + validator added: `scripts/sec_cache.py`, `scripts/sec_validate_cache.py`, and `data/sec_cache/` (git-ignored).
- **Security hardening (2026-01-29)**: CSP headers in `public/_headers`, source maps disabled in production, React ErrorBoundary for crash recovery.
- **Runtime validation (2026-01-29)**: Zod schemas in `src/lib/schemas.ts` for all JSON data types with graceful degradation.
- **Performance optimizations (2026-01-29)**: Bootstrap iterations reduced (200->100), canonical terms caching, Vite code splitting, `--fast` flag for builds.
- **Pipeline improvements (2026-01-29)**: Structured logging via `scripts/sec_logging.py`, `--cache-only` and `--incremental` flags, `sec_rebuild_local.py` for parallel rebuilds.

## Config sources (current decisions)
- `scripts/universe_featured.json` is the source of truth; `public/data/sec_narrative_drift/universe_featured.json` mirrors it for the frontend.
- `public/data/sec_narrative_drift/featured_cases.json` powers Home; `scripts/featured_cases.json` feeds `index.json` featuredCase entries.
- `scripts/resources/canonical_terms.yml` is the source of truth; `canonical_terms.json` is generated.
- SEC cache root defaults to `data/sec_cache/` and can be overridden with `SEC_CACHE_ROOT`.

## Directory tree snapshot (pruned, 2026-01-29)
```text
sec-narrative-drift
+-- AGENTS.md
+-- README.md
+-- .github
|   +-- workflows
|   |   +-- refresh_featured.yml
+-- docs
|   +-- 00_README_doc_index.md
|   +-- sec_narrative_drift_codex_spec_v1_13.md
|   +-- sec_narrative_drift_codex_implementation_checklist_v1_13.md
|   +-- sec_narrative_drift_copy_pack_v1_1.md
|   +-- sec_narrative_drift_humor_notes_v1_1.md
|   +-- sec_narrative_drift_item1a_extraction_hardening_patch_pack_v1_0.md
|   +-- sec_narrative_drift_canonical_terms_builder_patch_pack_v1_0.md
|   +-- sec_narrative_drift_canonical_terms_ui_includes_patch_pack_v1_0.md
|   +-- sec_narrative_drift_company_directory_patch_pack_v1_1.md
|   +-- sec_narrative_drift_universe_and_featured_stories_codex_pack_v1_0.md
|   +-- sec_narrative_drift_accuracy_signal_patch_pack_v1_0.md
|   +-- sec_narrative_drift_postlaunch_roadmap_and_ticket_pack_v1_2.md
|   +-- sec_risk_extraction_upgrade_codex_pack_v1.md
|   +-- sec_risk_extraction_upgrade_codex_pack_v2.md
|   +-- sec_risk_extraction_upgrade_v1.md
|   +-- _archive/
|   |   +-- sec_narrative_drift_accuracy_signal_upgrade_v1_1.md
|   |   +-- sec_narrative_drift_accuracy_upgrade_codex_pack_v1_3.md
|   |   +-- sec_narrative_drift_portfolio_eval_and_trust_tickets_v1_0.md
|   |   +-- sec-narrative-drift_next-roadmap_and_prior-art_audit.md
|   +-- screenshots/
+-- public
|   +-- data
|   |   +-- sec_narrative_drift
|   |   |   +-- index.json
|   |   |   +-- featured_cases.json
|   |   |   +-- universe_featured.json
|   |   |   +-- AAPL
|   |   |   +-- NVDA
|   |   |   +-- TSLA
|   |   |   +-- <many more tickers>
|   +-- _headers
|   +-- _redirects
|   +-- vite.svg
+-- data
|   +-- sec_cache (local only; git-ignored)
+-- scripts
|   +-- _cache
|   |   +-- metrics_demo
|   |   |   +-- excerpts_10k_item1a.json
|   |   |   +-- metrics_10k_item1a.json
|   |   |   +-- shifts_10k_item1a.json
|   |   |   +-- similarity_10k_item1a.json
|   +-- _reports
|   |   +-- canonical_terms_report.md
|   +-- resources
|   |   +-- canonical_terms.yml
|   |   +-- canonical_terms.json
|   +-- sample_fixtures
|   |   +-- aapl-20230930.htm
|   |   +-- aapl-20240928.htm
|   |   +-- nvda-20230129.htm
|   |   +-- tsla-20221231.htm
|   |   +-- tsm-2024-20f.htm
|   |   +-- CIK0000320193.json
|   |   +-- company_tickers_exchange.json
|   +-- README.md
|   +-- requirements.txt
|   +-- build_canonical_terms.py
|   +-- sec_build_index.py
|   +-- sec_build_universe.py
|   +-- sec_cache.py
|   +-- sec_extract_item1a.py
|   +-- sec_fetch_and_build.py
|   +-- sec_logging.py
|   +-- sec_metrics.py
|   +-- sec_phrases.py
|   +-- sec_quality.py
|   +-- sec_rebuild_local.py
|   +-- sec_validate_cache.py
|   +-- sec_validate_public_data.py
|   +-- universe_featured.json
|   +-- featured_cases.json
|   +-- tests
|   |   +-- test_canonical_terms.py
|   |   +-- test_extract_item1a.py
|   |   +-- test_sec_cache.py
|   |   +-- fixtures/
+-- src
|   +-- assets
|   |   +-- react.svg
|   +-- components
|   |   +-- ComparePane.tsx
|   |   +-- DataProvenanceDrawer.tsx
|   |   +-- DriftTimeline.tsx
|   |   +-- ErrorBoundary.tsx
|   |   +-- ExecBriefCard.tsx
|   |   +-- ExecutiveSummary.tsx
|   |   +-- InlinePopover.tsx
|   |   +-- QualityBadge.tsx
|   |   +-- SectionCaptureBadge.tsx
|   |   +-- SelectedPairCallout.tsx
|   |   +-- SimilarityHeatmap.tsx
|   |   +-- TermShiftBars.tsx
|   |   +-- Tour.tsx
|   +-- lib
|   |   +-- copy.ts
|   |   +-- data.ts
|   |   +-- exportPng.ts
|   |   +-- sanitize.ts
|   |   +-- schemas.ts
|   |   +-- shiftTerms.ts
|   |   +-- textHighlight.ts
|   |   +-- types.ts
|   +-- pages
|   |   +-- Company.tsx
|   |   +-- Companies.tsx
|   |   +-- Home.tsx
|   |   +-- Methodology.tsx
|   +-- App.css
|   +-- App.tsx
|   +-- index.css
|   +-- main.tsx
+-- .gitignore
+-- eslint.config.js
+-- index.html
+-- package-lock.json
+-- package.json
+-- pyrightconfig.json
+-- tsconfig.app.json
+-- tsconfig.json
+-- tsconfig.node.json
+-- vite.config.ts
```

## Archive
Older versions and one-off integrity notes live in `docs/_archive/`.
Codex should not treat archive docs as authoritative unless explicitly told.
