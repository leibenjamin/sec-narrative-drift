# LLM Precompute Workflow (Showcase v3)

Status: canonical manual rerun workflow for Lab.

## Canonical Entry Points
- `docs/lab/04_chatgpt_project_setup.md`
- `reports/lab_chatgpt_project_instructions.txt`
- `reports/lab_llm_run_manifest.json`
- `reports/lab_llm_manual_rerun_checklist.md`
- `scripts/lab_validate_llm_manifest_outputs.py`

## Zero-Touch Output Rule
- LLM outputs are runtime-static artifacts, generated offline.
- Each output should be directly saveable to canonical path as valid JSON.
- Avoid post-generation patching and reconciliation as a normal step.
- If recurring issues appear, improve prompt blocks and thread starters first.

## Canonical Paths
- Output path:
  `public/data/sec_narrative_drift_lab/<TICKER>/outputs/<detector_id>/lab_<detector_id>_10k_item1a_<YEAR_FROM>_<YEAR_TO>_focuspack_deboilerplated.json`
- Input attachment path:
  `bundles/llm_run_pack_<UTCSTAMP>/inputs/<TICKER>_<YEAR_FROM>_<YEAR_TO>_focuspack_deboilerplated.json`
- `provenance.input_file` value:
  `inputs/<TICKER>_<YEAR_FROM>_<YEAR_TO>_focuspack_deboilerplated.json`

## Required Provenance for Manual Runs
- `input_file` (required)
- `model_provider` (required)
- `model_name` (required)
- `run_label` (optional, recommended)

## Canonical Validation Loop
1. Wave progress:
   `python scripts/lab_validate_llm_manifest_outputs.py --allow-missing --allow-invalid --report reports/lab_llm_manifest_validation.md`
2. Final strict:
   `python scripts/lab_validate_llm_manifest_outputs.py --report reports/lab_llm_manifest_validation.md`
3. Deterministic gates:
   `npm run lab:predeploy`
   `npm run lab:portfolio`
   `npm run build`

## Legacy Notice
Older queue and ingest flow docs remain for history and compatibility checks only.
They are non-canonical for current showcase manual reruns.
