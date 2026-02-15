# LLM Outputs (Lab Sidecar)

This folder stores precomputed LLM detector outputs for the Narrative Drift Lab.

Output naming:
`public/data/sec_narrative_drift_lab/llm_outputs/{detector_id}/{ticker}/lab_{detector_id}_10k_item1a_{year_from}_{year_to}_{lens}.json`

Lens values:
- `focuspack_deboilerplated`
- `focuspack_raw`
- `full_deboilerplated`
- `full_raw`

Use `scripts/lab_make_llm_precompute_queue.py` to build the job list and
`scripts/lab_validate_llm_outputs.py` to validate outputs before sharing.
