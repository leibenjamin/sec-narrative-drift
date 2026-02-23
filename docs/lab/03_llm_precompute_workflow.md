# LLM Precompute Workflow (Showcase v3)

Status: canonical manual rerun workflow for Lab (`full_section_v2`).

## Canonical Entry Points
- `docs/lab/04_chatgpt_project_setup.md`
- `reports/lab_project_instructions_<campaign_id>.txt`
- `reports/lab_llm_run_manifest.json`
- `reports/lab_llm_manual_rerun_checklist.md`
- `scripts/lab_validate_llm_manifest_outputs.py`

## Runtime Truth (Current Push)
- Runtime-visible campaign: `openai_gpt53codex_xhigh_agent_fullsec_2026-02-22` (`84/84` strict-valid).
- Runtime-hidden pending campaign: `openai_chatgpt52ext_agent_fullsec_2026-02-22` (`84` expected missing until second wave).
- `focuspack_v1` campaigns remain on disk for audit history only and are hidden in runtime selectors.

## Zero-Touch Output Rule
- LLM outputs are runtime-static artifacts, generated offline.
- Each output should be directly saveable to canonical path as valid JSON.
- Avoid post-generation patching and reconciliation as a normal step.
- If recurring issues appear, improve prompt blocks and thread starters first.

## Canonical Paths
- Output path:
  `public/data/sec_narrative_drift_lab/<TICKER>/outputs/<detector_id>/<track_slug>/lab_<detector_id>_10k_item1a_<YEAR_FROM>_<YEAR_TO>_<LENS>_edgar__<track_slug>.json`
- Input attachment paths (v2):
  - Pair manifest: `bundles/llm_run_pack_<UTCSTAMP>_<CAMPAIGN_ID>/inputs/pair/<TICKER>_<YEAR_FROM>_<YEAR_TO>_10k_item1a_<LENS>_edgar.json`
  - Year prev: `bundles/llm_run_pack_<UTCSTAMP>_<CAMPAIGN_ID>/inputs/year/<TICKER>_<YEAR_FROM>_10k_item1a_<LENS>_edgar__pair_<YEAR_FROM>_<YEAR_TO>.json`
  - Year curr: `bundles/llm_run_pack_<UTCSTAMP>_<CAMPAIGN_ID>/inputs/year/<TICKER>_<YEAR_TO>_10k_item1a_<LENS>_edgar__pair_<YEAR_FROM>_<YEAR_TO>.json`
- Public mirror for runtime transparency:
  - `public/data/sec_narrative_drift_lab/llm_inputs_v2/inputs/pair/...`
  - `public/data/sec_narrative_drift_lab/llm_inputs_v2/inputs/year/...`
- `provenance.input_file` value:
  `inputs/pair/<TICKER>_<YEAR_FROM>_<YEAR_TO>_10k_item1a_<LENS>_edgar.json`

## Source Canonical Note
- Canonical full-section source for this push is:
  `scripts/_reports/risk_extraction_bundle/sections/<TICKER>_<YEAR>_item_1a.txt`.
- `data/sec_cache` and `scripts/_cache` are audit references, not canonical replacements in this release.
- See `reports/lab_full_section_source_audit.md` for deterministic source/deboiler comparisons.

## Required Provenance for Manual Runs
- `input_file` (required)
- `model_provider` (required)
- `model_name` (required)
- `run_label` (required; must start with `YYYY-MM-DD_`)

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
Legacy `focuspack_v1` inputs remain on disk for audit only and are runtime-hidden.
