# LLM Precompute Queue (Legacy Pointer)

Status: legacy and non-canonical for current Lab manual reruns.

This file is intentionally minimal and exists only to redirect older queue/checklist references.

## Use These Canonical Docs Instead
- `docs/lab/03_llm_precompute_workflow.md`
- `docs/lab/05_llm_reproducibility_contract.md`
- `docs/lab/07_codex_real_run_profile.md`

## Canonical Local Artifacts (Master-First)
- `reports/lab_llm_master_manifest_codex_real.json`
- `reports/lab_llm_master_manifest_chatgpt_real.json`
- `reports/lab_llm_master_thread_starters_codex_real.md`
- `reports/lab_llm_master_thread_starters_chatgpt_real.md`
- `reports/lab_llm_master_validation_codex_real.md`
- `reports/lab_llm_master_validation_chatgpt_real.md`

## Why This Queue Doc Is Legacy
- Earlier queue docs centered detector-first run-manifest flow.
- Current canonical flow is master-first (`llm_outline_compare_v1`) with deterministic projection for legacy detector envelopes.
- Starter hardening and strict exact-path single-target validation are now enforced at job level.

## Legacy Scripts (Archive/Archaeology)
- `scripts/lab_make_llm_precompute_queue.py`
- `scripts/lab_validate_llm_outputs.py`
- `scripts/lab_ingest_llm_outputs.py`
- `scripts/lab_ingest_manual_llm_outputs.py`
