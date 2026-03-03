# Product Story: SEC Narrative Drift Lab

## One-line pitch
This Lab shows how risk disclosures change year-over-year using deterministic detectors and outline-aware offline LLM artifacts, with side-by-side model comparison and path-level reproducibility.

## Fast walkthrough (30 seconds)
1. Open a showcase company page (company pages are now Lab-only).
2. Show a recommended adjacent pair (for example `NVDA 2023-2024`).
3. Explain:
   - deterministic detectors quantify shift/reuse/structure changes,
   - Outline Compare surfaces structure-aware material changes (added/removed/moved/reworded/intensified/softened),
   - lens toggle compares cleaned vs raw text effects,
   - missing artifacts are explicit with expected paths and copyable debug payloads.

## Core credibility points
- Runtime is deterministic static JSON only.
- No runtime LLM/ML calls.
- SEC text is treated as untrusted and rendered as plain text nodes (no HTML injection APIs).
- Canonical output contract is stable and track-aware: `outputs/<detector_id>/<track_slug>/lab_<...>__<track_slug>.json`.
- LLM layer is reproducible: users can rerun from published full-section v2 pair/year inputs and thread-starter instructions.
- Provenance is campaign-aware (`model_provider`, `model_name`, required day-precise `run_label`) to support future model-vs-model comparisons.
- Runtime policy is real-run only for LLM lanes:
  - synthetic full-section campaigns are hidden from selectors,
  - real manual-run campaigns are the canonical lanes for model evidence,
  - explicit missing/debug states remain visible until real artifacts are generated.
- Active runtime pair scope is FY2022+ adjacent pairs only (12 pairs across NVDA/KO/WM/GE).
- Newly added FY2025 pairs remain visible immediately with deterministic-first defaults when LLM sidecars are unavailable.
- Focuspack-era campaigns are preserved for audit history but hidden from runtime selectors.
- Deep Dive v3 adds persistent mode-state framing, signal-quality tiers, interpretation-first card headers, and sourced method-context drawers (canonical usage, this-app deviation, failure modes, alternatives, origins).
- Current operational remainder: complete real master/manual LLM runs (Codex lane first, ChatGPT lane second), project to legacy detector envelopes, then enable full A/B parity for runtime selectors.

## Suggested walkthrough sequence
1. Deterministic baseline:
   - Use `det_logodds_terms_v1` and `det_jsd_ngrams_v1` to show lexical/distributional drift.
2. Structure/reuse perspective:
   - Toggle `det_minhash_boilerplate_v1` and `det_structure_artifacts_v1`.
3. Agreement lens:
   - Show `det_rbo_agreement_v1` matrix and explain detector concordance.
4. Optional LLM layer:
   - Turn on `det_llm_delta_brief_v1` / `det_llm_excerpt_picker_v1` and compare `llmA` vs `llmB`.
   - Call out quick-diff strip metrics plus the `Read` guidance column (confidence direction, evidence breadth, overlap interpretation).
   - In deep mode, open method context on first cards to explain detector intent and caveats to mixed audiences.
   - If artifacts are missing, point to explicit path-aware missing state.

## Operational evidence to mention
- Local generated reports (`reports/*`, untracked by policy):
  - `reports/lab_runtime_readiness.md` (deterministic gate: GO).
  - `reports/lab_raw_prereq_audit.md` (RAW eligibility and coverage).
  - `reports/lab_llm_master_manifest_codex_real.json` (Codex real-run job roster + canonical output paths).
  - `reports/lab_llm_master_thread_starters_codex_real.md` (canonical Codex starter source).
  - `reports/lab_llm_master_validation_codex_real.md` and `reports/lab_llm_master_quality_codex_real.md` (checkpoint validation and blocker audit).
  - `reports/lab_llm_master_manifest_chatgpt_real.json` (pending compare-lane roster for strict-valid completion).

## FAQ-ready answers
- Q: "Why deterministic-first?"
  - A: Reproducibility and deploy stability; LLM outputs are precomputed offline and validated.
- Q: "How do you debug missing outputs?"
  - A: UI exposes expected path + requested URL + copyable debug payload; validator reports missing files explicitly.
- Q: "How do you prevent injection risks from filing text?"
  - A: Strict no-HTML rendering policy (`docs/SEC_TEXT_SAFETY.md`), React text-node rendering only.
