# LLM Precompute Queue (Legacy)

Status: legacy and non-canonical for current showcase manual reruns.

Use this file only for historical context around earlier queue and ingest experiments.

## Canonical Manual Rerun Flow
Use these instead:
- `docs/lab/04_chatgpt_project_setup.md`
- `reports/lab_chatgpt_project_instructions.txt`
- `reports/lab_llm_run_manifest.json`
- `reports/lab_llm_manual_rerun_checklist.md`
- `scripts/lab_validate_llm_manifest_outputs.py`

## Why this is legacy
- This queue doc references older `llm_outputs/...` layouts and older validation steps.
- Current canonical flow writes directly to `<TICKER>/outputs/<detector_id>/...` and validates against manifest targets.
- Current reproducibility contract requires standardized model metadata in output provenance.

## Legacy Scripts (for archaeology only)
- `scripts/lab_make_llm_precompute_queue.py`
- `scripts/lab_validate_llm_outputs.py`
- `scripts/lab_ingest_llm_outputs.py`
- `scripts/lab_ingest_manual_llm_outputs.py`
