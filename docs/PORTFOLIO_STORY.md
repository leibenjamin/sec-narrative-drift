# Portfolio Story: SEC Narrative Drift Lab

## One-line pitch
This Lab shows how risk disclosures change year-over-year using deterministic detectors, then layers offline precomputed LLM campaigns for side-by-side model comparison.

## What to demo first (30 seconds)
1. Open a showcase company page (company pages are now Lab-only).
2. Show a recommended adjacent pair (for example `NVDA 2021-2022`).
3. Explain:
   - deterministic detectors quantify shift/reuse/structure changes,
   - lens toggle compares cleaned vs raw text effects,
   - missing artifacts are explicit with expected paths and copyable debug payloads.

## Key credibility points
- Runtime is deterministic static JSON only.
- No runtime LLM/ML calls.
- SEC text is treated as untrusted and rendered as plain text nodes (no HTML injection APIs).
- Canonical output contract is stable and track-aware: `outputs/<detector_id>/<track_slug>/lab_<...>__<track_slug>.json`.
- LLM layer is reproducible: users can rerun from published focuspack inputs and thread-starter instructions.
- Provenance is campaign-aware (`model_provider`, `model_name`, required day-precise `run_label`) to support future model-vs-model comparisons.
- A/B compare is populated by two complete campaigns (`ChatGPT 5.2-Thinking (Extended Thinking)` and `GPT-5.3-Codex (Extra High Reasoning, Agent Mode)`), both strict-valid (`42/42`).
- Current operational remainder: post-UX incognito screenshot closeout for three A/B compare states.

## Suggested walkthrough sequence
1. Deterministic baseline:
   - Use `det_logodds_terms_v1` and `det_jsd_ngrams_v1` to show lexical/distributional drift.
2. Structure/reuse perspective:
   - Toggle `det_minhash_boilerplate_v1` and `det_structure_artifacts_v1`.
3. Agreement lens:
   - Show `det_rbo_agreement_v1` matrix and explain detector concordance.
4. Optional LLM layer:
   - Turn on `det_llm_delta_brief_v1` / `det_llm_excerpt_picker_v1` and compare `llmA` vs `llmB`.
   - Call out quick-diff strip metrics (confidence, evidence count, citation/evidence overlap behavior).
   - If artifacts are missing, point to explicit path-aware missing state.

## Operational evidence to mention
- `reports/portfolio_readiness_lab.md` (deterministic gate: GO).
- `reports/lab_raw_prereq_audit.md` (RAW eligibility and coverage).
- `reports/lab_llm_run_manifest.md` (complete roster + expected LLM artifact paths).
- `reports/lab_llm_codex_quality_audit.md` (Codex quality-lock gates for diversity/consistency).

## FAQ-ready answers
- Q: "Why deterministic-first?"
  - A: Reproducibility and deploy stability; LLM outputs are precomputed offline and validated.
- Q: "How do you debug missing outputs?"
  - A: UI exposes expected path + requested URL + copyable debug payload; validator reports missing files explicitly.
- Q: "How do you prevent injection risks from filing text?"
  - A: Strict no-HTML rendering policy (`docs/SEC_TEXT_SAFETY.md`), React text-node rendering only.
