# Documentation Index (Lab Canonical)

## Start here
- `docs/00_DOC_INDEX.md` - this file.
- `docs/LAB_REMAINING_WORK_PLAN.md` - execution status and remaining work.
- `docs/PORTFOLIO_STORY.md` - demo narrative for interviews and portfolio walkthroughs.
- `docs/SEC_TEXT_SAFETY.md` - SEC text trust model and rendering safety rules.

## Product and contract docs
- `docs/sec_narrative_drift_codex_spec_v1_13.md` - product/data contract baseline.
- `docs/sec_narrative_drift_codex_implementation_checklist_v1_13.md` - ticketed implementation checklist.
- `docs/00_README_doc_index.md` - historical canonical index retained for compatibility.

## Operational reports
- `reports/portfolio_readiness_lab.md` - deterministic readiness gate.
- `reports/lab_raw_prereq_audit.md` - RAW prerequisite and coverage audit.
- `reports/lab_llm_run_manifest.md` - LLM run manifest (human-readable).
- `reports/lab_llm_run_manifest.json` - LLM run manifest (machine-readable).
- `reports/lab_execution_checklist.md` - phase execution tracker.

## Canonical runtime data paths
- Registry: `public/data/sec_narrative_drift_lab/lab_cases_v1.json`
- Output files: `public/data/sec_narrative_drift_lab/<TICKER>/outputs/<detector_id>/<filename>.json`
- LLM canonical outputs follow the same `outputs/<detector_id>/...` pattern.

## Local-only artifacts
- `bundles/*` - local run packs and handoff artifacts (kept uncommitted by policy).
- `attic/*` - archived historical artifacts, not used by production runtime.
