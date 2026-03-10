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

Compare-lane real-run campaign (runtime-visible):
- `campaign_id`: `openai_chatgpt54ext_agent_fullsec_real_2026-03-06`
- `campaign_slug`: `openai-chatgpt54ext-agent-fullsec-real-2026-03-06`
- Active model for this manual compare campaign is `ChatGPT 5.4-Thinking (Extended Thinking)`.
- This campaign is the truthful public replacement for the older compatibility-only `chatgpt52ext` real-lane identity.

Pre-registered workspace-aware campaign (runtime-hidden until outputs exist):
- `campaign_id`: `anthropic_claudeopus46_claudecode_fullsec_real_2026-03-09`
- `campaign_slug`: `anthropic-claudeopus46-claudecode-fullsec-real-2026-03-09`
- Model: `Claude Opus 4.6 (Thinking, Max)`
- Execution venue: `vscode_agent`
- Runtime status: `runtime_visible=false`

Archive-only compatibility lane:
- `campaign_id`: `openai_chatgpt52ext_agent_fullsec_real_2026-02-27`
- `campaign_slug`: `openai-chatgpt52ext-agent-fullsec-real-2026-02-27`
- Use only for archival path continuity or historical recovery, not for active public truth.

Campaign metadata source of truth:
- `scripts/lab_output_tracks.py`
- `public/data/sec_narrative_drift_lab/lab_llm_campaigns_v1.json`
- `docs/lab/09_master_run_troubleshooting_and_sources_of_truth.md`

## Runtime Visibility Policy
- Runtime selectors expose only campaigns marked `runtime_visible=true`.
- Primary and compare-visible campaigns are both exposed only when `runtime_visible=true` in the generated campaign index.
- Synthetic/fullsec baseline, archive-only compatibility lanes, and preregistered workspace lanes remain on disk or in metadata for audit/prep only.

## Canonical Output Paths
Deterministic outputs use detector-aware paths:
- `public/data/sec_narrative_drift_lab/<TICKER>/outputs/<detector_id>/<track_slug>/lab_<detector_id>_<section>_<year_from>_<year_to>_<cleaning_lens>_<source_id>__<track_slug>.json`

LLM outline compare artifacts use artifact-aware campaign paths:
- structured: `public/data/sec_narrative_drift_lab/<TICKER>/outputs/llm_outline_compare_structured/<campaign_slug>/lab_llm_outline_compare_structured_<section>_<year_from>_<year_to>_<cleaning_lens>_<source_id>__<campaign_slug>.json`
- runtime: `public/data/sec_narrative_drift_lab/<TICKER>/outputs/llm_outline_compare_runtime/<campaign_slug>/lab_llm_outline_compare_runtime_<section>_<year_from>_<year_to>_<cleaning_lens>_<source_id>__<campaign_slug>.json`

## Master-First Workflow
1. Build or refresh the active bundle.
2. Publish the public `llm_inputs_v2` mirror.
3. Build the campaign master manifest.
4. Emit matching master thread starters.
5. Run `scripts/lab_verify_master_input_locks.py`.
6. Run `scripts/lab_prompt_consistency_check.py`.
7. Execute manual master jobs (`llm_outline_compare_structured`) with one starter thread per job.
8. Validate outputs with strict single-target controls.
9. Run blocker-quality audit.
10. Project structured artifacts deterministically to `llm_outline_compare_runtime`.
11. Rebuild runtime indexes and verify compare behavior.

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
1. `npm run lint`
2. `npm run lab:predeploy`
3. `npm run lab:readiness`
4. `npm run build`

## Legacy Note
Older 2026-02-21 campaign docs and detector-first run-manifest procedures are historical only and non-canonical for current full-section real runs.
