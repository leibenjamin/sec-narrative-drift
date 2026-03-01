# Documentation Index (Lab Canonical)

## Start here
- `docs/00_DOC_INDEX.md` - this file.
- `docs/LAB_REMAINING_WORK_PLAN.md` - execution status and remaining work.
- `docs/PRODUCT_STORY.md` - public product narrative and walkthrough order.
- `docs/PUBLIC_TONE_POLICY.md` - public-facing language policy and banned framing.
- `docs/SEC_TEXT_SAFETY.md` - SEC text trust model and rendering safety rules.
- `docs/lab/05_llm_reproducibility_contract.md` - strict manual LLM rerun contract and validation requirements.
- `docs/lab/06_llm_model_comparison_workflow.md` - multi-campaign model-comparison workflow.
- `docs/lab/07_codex_real_run_profile.md` - operational profile for 24-job Codex real master runs and batch governance cadence.
- CI security gates include runtime dependency audit and forbidden HTML API scan via `.github/workflows/lab_gates.yml`.

## Product and contract docs
- `docs/sec_narrative_drift_codex_spec_v1_13.md` - product/data contract baseline.
- `docs/sec_narrative_drift_codex_implementation_checklist_v1_13.md` - ticketed implementation checklist.
- `docs/00_README_doc_index.md` - historical canonical index retained for compatibility.

## Local generated reports (not committed)
- `reports/*` are generated locally for validation and operator workflows, then kept untracked by policy.
- Typical local artifacts:
  - `reports/lab_runtime_readiness.md` - deterministic readiness gate.
  - `reports/lab_raw_prereq_audit.md` - RAW prerequisite and coverage audit.
  - `reports/lab_llm_run_manifest.md` - LLM run manifest (human-readable).
  - `reports/lab_llm_run_manifest.json` - LLM run manifest (machine-readable).
  - `reports/lab_execution_checklist.md` - phase execution tracker.

## Canonical runtime data paths
- Registry: `public/data/sec_narrative_drift_lab/lab_cases_v1.json`
- Output files: `public/data/sec_narrative_drift_lab/<TICKER>/outputs/<detector_id>/<track_slug>/lab_<...>__<track_slug>.json`
- LLM campaigns index: `public/data/sec_narrative_drift_lab/lab_llm_campaigns_v1.json`
- LLM variants index: `public/data/sec_narrative_drift_lab/lab_llm_variants_v1.json`
- Method tracks index: `public/data/sec_narrative_drift_lab/lab_method_tracks_v1.json`
- Method profiles index: `public/data/sec_narrative_drift_lab/lab_method_profiles_v1.json`

## Local-only artifacts
- `reports/*` - local validation/checklist outputs (never committed).
- `bundles/*` - local run packs and handoff artifacts (kept uncommitted by policy).
- `attic/*` - archived historical artifacts, not used by production runtime.
  - `attic/legacy_ui_pre_lab_20260219.md` documents the hard Lab-first UI archive mapping.
