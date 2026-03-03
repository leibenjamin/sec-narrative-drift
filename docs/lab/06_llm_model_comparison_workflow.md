# LLM Model Comparison Workflow (Lab)

This document defines the canonical multi-model workflow for comparing precomputed LLM sidecars in Lab.

## Scope
- Deterministic detectors remain the baseline.
- LLM sidecars are precomputed offline and loaded from static JSON.
- No runtime LLM calls in shipped app.

## Canonical Campaigns (Current)
Primary real-run campaign (runtime-visible):
- `campaign_id`: `openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27`
- `campaign_slug`: `openai-gpt53codex-xhigh-agent-fullsec-real-2026-02-27`

Compare-lane real-run campaign (runtime-hidden pending strict-valid completion):
- `campaign_id`: `openai_chatgpt52ext_agent_fullsec_real_2026-02-27`
- `campaign_slug`: `openai-chatgpt52ext-agent-fullsec-real-2026-02-27`

Campaign metadata source of truth:
- `scripts/lab_output_tracks.py`
- `public/data/sec_narrative_drift_lab/lab_llm_campaigns_v1.json`

## Runtime Visibility Policy
- Runtime selectors expose only campaigns marked `runtime_visible=true`.
- Real-run compare lane may remain hidden until strict-valid coverage is complete.
- Synthetic/fullsec baseline and focuspack-era campaigns remain on disk for audit only.

## Canonical Output Path
All detector outputs (deterministic and LLM) use track-aware paths:
- `public/data/sec_narrative_drift_lab/<TICKER>/outputs/<detector_id>/<track_slug>/lab_<detector_id>_<section>_<year_from>_<year_to>_<cleaning_lens>_<source_id>__<track_slug>.json`

## Master-First Workflow
1. Build or refresh campaign master manifest and starters.
2. Execute manual master jobs (`llm_outline_compare_v1`) with one starter thread per job.
3. Validate outputs with strict single-target controls.
4. Run blocker-quality audit.
5. Project master artifacts to compatibility detector envelopes.
6. Rebuild runtime indexes and verify compare behavior.

## Provenance Contract
- `provenance.input_file` required.
- `provenance.model_provider` required and campaign-exact.
- `provenance.model_name` required and campaign-exact.
- `provenance.run_label` required with day precision (`YYYY-MM-DD_<campaign_tag>`).

## Validation Commands
Per campaign checkpoint:
- `python scripts/lab_validate_llm_master_outputs.py --manifest <master_manifest.json> --campaign-id <campaign_id> --allow-missing --allow-invalid --report <validation_report.md>`
- `python scripts/lab_audit_master_output_quality.py --manifest <master_manifest.json> --campaign-id <campaign_id> --allow-missing --mode blockers --report <quality_report.md>`
- `python scripts/lab_record_master_progress.py --manifest <master_manifest.json> --campaign-id <campaign_id> --report-md <progress.md> --history-json <progress.json> --label <checkpoint_label>`

## UI Compare Mode
Lab company pages support campaign compare query params:
- `llmA=<campaign_id>`
- `llmB=<campaign_id>`

Behavior:
- LLM cards render side-by-side by campaign.
- Deterministic cards remain unchanged.
- Missing campaign variants show explicit expected paths and debug payload.

## Required Gates
After build/data logic changes:
1. `npm run lab:predeploy`
2. `npm run lab:readiness`
3. `npm run build`

## Legacy Note
Older 2026-02-21 campaign docs and detector-first run-manifest procedures are historical only and non-canonical for current full-section real runs.
