# LLM Model Comparison Workflow (Lab)

This document defines the canonical multi-model workflow for comparing precomputed LLM sidecars in Lab.

## Scope
- Deterministic detectors remain primary baseline.
- LLM sidecars are precomputed offline and loaded from static JSON only.
- No runtime LLM calls in the shipped app.

## Campaigns
- ChatGPT baseline:
  - `campaign_id`: `openai_chatgpt52ext_agent_2026-02-21`
  - `campaign_slug`: `openai-chatgpt52ext-agent-2026-02-21`
- Codex campaign:
  - `campaign_id`: `openai_gpt53codex_xhigh_agent_2026-02-21`
  - `campaign_slug`: `openai-gpt53codex-xhigh-agent-2026-02-21`

Campaign metadata source of truth:
- `scripts/lab_output_tracks.py`
- `public/data/sec_narrative_drift_lab/lab_llm_campaigns_v1.json`

## Canonical Output Path
All detector outputs (deterministic and LLM) use track-aware paths:
- `public/data/sec_narrative_drift_lab/<TICKER>/outputs/<detector_id>/<track_slug>/lab_<detector_id>_<section>_<year_from>_<year_to>_<cleaning_lens>_<source_id>__<track_slug>.json`

## Provenance Contract
- `provenance.input_file` required.
- `provenance.model_provider` required and campaign-exact.
- `provenance.model_name` required and campaign-exact.
- `provenance.run_label` required with day precision:
  - `YYYY-MM-DD_<campaign_tag>`

## Run Artifacts
Generate campaign-specific artifacts:
1. Instructions:
   - `python scripts/lab_write_chatgpt_project_instructions.py --campaign-id <campaign_id>`
2. Prompt templates:
   - `python scripts/lab_write_prompt_templates.py --bundle bundles/showcase_llm_inputs_20260207_182343 --campaign-id <campaign_id>`
3. Manifest + run pack:
   - `python scripts/lab_build_llm_run_manifest.py --campaign-id <campaign_id> --bundle bundles/showcase_llm_inputs_20260207_182343 --out-md <report.md> --out-json <report.json>`
4. Checklist:
   - `python scripts/lab_build_manual_llm_rerun_checklist.py --manifest <report.json> --out <checklist.md>`

## Validation
Per campaign:
- Progress:
  - `python scripts/lab_validate_llm_manifest_outputs.py --manifest <manifest.json> --campaign-id <campaign_id> --allow-missing --allow-invalid --report <report.md>`
- Final strict:
  - `python scripts/lab_validate_llm_manifest_outputs.py --manifest <manifest.json> --campaign-id <campaign_id> --report <report.md>`

Index-level matrix:
- `python scripts/lab_build_llm_variants_index.py`

## UI Compare Mode
Lab company page exposes:
- `llmA=<campaign_id>`
- `llmB=<campaign_id>`

UX behavior:
- LLM cards render side-by-side by campaign for each LLM detector.
- Deterministic cards remain unchanged.
- Missing variants show explicit expected path and debug payload.

## Required Gates
After build/data logic changes:
1. `npm run lab:predeploy`
2. `npm run lab:readiness`
3. `npm run build`
