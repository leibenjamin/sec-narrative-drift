# LLM Precompute Workflow (Showcase v3)

Status: canonical manual outline-compare workflow for the shipped `full_section_v2` experience.

## Current Shipped Scope
- Active showcase scope is FY2024 -> FY2025 only for `NVDA`, `KO`, `WM`, and `GE`.
- The shipped model-analysis surface is outline compare.
- Runtime-visible compare campaigns are:
  - `openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27`
  - `openai_chatgpt54ext_agent_fullsec_real_2026-03-06`
- Pre-registered but runtime-hidden workspace-aware lane:
  - `anthropic_claudeopus46_claudecode_fullsec_real_2026-03-09`
- Archive-only compatibility lane:
  - `openai_chatgpt52ext_agent_fullsec_real_2026-02-27`

## Canonical Entry Points
- `docs/lab/04_chatgpt_project_setup.md`
- `docs/lab/05_llm_reproducibility_contract.md`
- `docs/lab/07_codex_real_run_profile.md`
- `docs/lab/11_claude_code_real_run_profile.md`
- `docs/lab/09_master_run_troubleshooting_and_sources_of_truth.md`
- `reports/lab_project_instructions_<campaign_id>.txt`
- `reports/lab_llm_master_manifest_<campaign>.json`
- `reports/lab_llm_master_thread_starters_<campaign>.md`
- `reports/lab_llm_master_validation_<campaign>.md`
- `scripts/lab_run_fullsec_campaign_pipeline.py`
- `scripts/lab_build_llm_master_manifest.py`
- `scripts/lab_emit_master_thread_starters.py`
- `scripts/lab_verify_master_input_locks.py`
- `scripts/lab_prompt_consistency_check.py`
- `scripts/lab_validate_llm_master_outputs.py`
- `scripts/lab_audit_master_output_quality.py`
- `scripts/lab_record_master_progress.py`
- `scripts/lab_project_master_v2_to_v1.py`
- `scripts/lab_build_portable_master_run_pack.py`

## Canonical Execution Chain
1. Build or select the active bundle.
2. Publish `public/data/sec_narrative_drift_lab/llm_inputs_v2` from that bundle.
3. Rebuild the campaign master manifest.
4. Emit the matching master thread starters.
5. Verify master input locks against live bundle files and the public input mirror.
6. Run prompt consistency against the generated manifest/starters and canonical docs.
7. Validate outputs, run blocker audit, record batch progress, and refresh campaign/index/readiness metadata.

## Canonical Manual Authoring Unit
- Manual authoring artifact: `llm_outline_compare_structured`
- Deterministic runtime artifact: `llm_outline_compare_runtime`
- Optional experimental sidecar: `llm_outline_compare_insight`

`llm_outline_compare_structured` is the only canonical manual authoring unit for the current shipped compare workflow.

## Output Rule
- LLM outputs are generated offline and committed as static JSON artifacts.
- Operators should save structured JSON directly to the canonical structured output path when the client has workspace access.
- Runtime compare JSON is created later by deterministic projection, not by a second model run.
- Do not normalize low-quality outputs by hand-editing content. Fix prompts, starters, or rerun the job instead.

## Canonical Job Counts
- Current scope per campaign: `4` tickers x `2` lenses = `8` structured jobs.
- Deterministic runtime projection per campaign: `8` runtime outputs.
- Insight artifacts are optional and are not required for shipped compare availability.

## Canonical Paths
- Structured output path:
  `public/data/sec_narrative_drift_lab/<TICKER>/outputs/llm_outline_compare_structured/<track_slug>/lab_llm_outline_compare_structured_10k_item1a_<YEAR_FROM>_<YEAR_TO>_<LENS>_edgar__<track_slug>.json`
- Runtime output path:
  `public/data/sec_narrative_drift_lab/<TICKER>/outputs/llm_outline_compare_runtime/<track_slug>/lab_llm_outline_compare_runtime_10k_item1a_<YEAR_FROM>_<YEAR_TO>_<LENS>_edgar__<track_slug>.json`
- Full-section input mirror:
  - `public/data/sec_narrative_drift_lab/llm_inputs_v2/inputs/pair/...`
  - `public/data/sec_narrative_drift_lab/llm_inputs_v2/inputs/year/...`
- Canonical `provenance.input_file` value:
  `inputs/pair/<TICKER>_<YEAR_FROM>_<YEAR_TO>_10k_item1a_<LENS>_edgar.json`
- Local bundle pair manifests may include optional `analysis_expectations.focus_signals` metadata for hard manual-run cases.
- That metadata is for starter/audit hardening only and does not change shipped compare artifact schemas.
- `analysis_expectations.paragraph_hints` are fail-fast canonical inputs: if a hint falls outside the linked year arrays, fix the source expectations first and regenerate downstream artifacts.
- Raw-lens reruns may lightly normalize only non-evidence display titles/labels when correcting obvious extraction artifacts; do not hand-edit committed output JSON.

## Rerun By Venue
- ChatGPT Desktop campaigns run directly from the thread starter plus the three attached input files.
- Workspace-aware Codex and Claude Code campaigns run from declared workspace paths and may write artifacts locally.
- Use `docs/lab/07_codex_real_run_profile.md` for Codex threads and `docs/lab/11_claude_code_real_run_profile.md` for Claude Code threads.
- If starter/input files are reused outside the original workspace, users must update workspace-relative file paths before rerun.
- End-user formatting for self-run outputs is a planned follow-up helper and is not part of the current canonical pipeline.

## Validation Loop
1. Validate structured outputs against the campaign manifest.
2. Run blocker quality audit, including `--strict-depth` when required.
3. Project structured outputs to runtime via `scripts/lab_project_master_v2_to_v1.py`.
4. Validate runtime outputs.
5. Refresh campaign progress, variants, and readiness metadata.
6. Run deterministic repo gates:
   - `npm run lab:predeploy`
   - `npm run lab:readiness`
   - `npm run build`

## Prompt Consistency Commands
- Codex real:
  - `python scripts/lab_prompt_consistency_check.py --bundle bundles/showcase_llm_inputs_full_section_v2_20260305_2425anchor --campaign-id openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27`
- ChatGPT real:
  - `python scripts/lab_prompt_consistency_check.py --bundle bundles/showcase_llm_inputs_full_section_v2_20260305_2425anchor --campaign-id openai_chatgpt54ext_agent_fullsec_real_2026-03-06 --master-starters reports/lab_llm_master_thread_starters_chatgpt_real.md --master-manifest reports/lab_llm_master_manifest_chatgpt_real.json`
- Codex insight:
  - `python scripts/lab_prompt_consistency_check.py --bundle bundles/showcase_llm_inputs_full_section_v2_20260305_2425anchor --campaign-id openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27 --master-starters reports/lab_llm_master_thread_starters_codex_real_insight.md --master-manifest reports/lab_llm_master_manifest_codex_real_insight.json`

## Lock Verification Commands
- Codex real:
  - `python scripts/lab_verify_master_input_locks.py --bundle bundles/showcase_llm_inputs_full_section_v2_20260305_2425anchor --campaign-id openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27 --master-manifest reports/lab_llm_master_manifest_codex_real.json --master-starters reports/lab_llm_master_thread_starters_codex_real.md`
- ChatGPT real:
  - `python scripts/lab_verify_master_input_locks.py --bundle bundles/showcase_llm_inputs_full_section_v2_20260305_2425anchor --campaign-id openai_chatgpt54ext_agent_fullsec_real_2026-03-06 --master-manifest reports/lab_llm_master_manifest_chatgpt_real.json --master-starters reports/lab_llm_master_thread_starters_chatgpt_real.md`
- Codex insight:
  - `python scripts/lab_verify_master_input_locks.py --bundle bundles/showcase_llm_inputs_full_section_v2_20260305_2425anchor --campaign-id openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27 --master-manifest reports/lab_llm_master_manifest_codex_real_insight.json --master-starters reports/lab_llm_master_thread_starters_codex_real_insight.md`

## Recommended Orchestrated Runs
- Codex real-manual lane:
  - `python scripts/lab_run_fullsec_campaign_pipeline.py --campaign-id openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27 --run-day YYYY-MM-DD --skip-generate --allow-missing --allow-invalid`
- ChatGPT real-manual lane:
  - `python scripts/lab_run_fullsec_campaign_pipeline.py --campaign-id openai_chatgpt54ext_agent_fullsec_real_2026-03-06 --run-day YYYY-MM-DD --skip-generate --allow-missing --allow-invalid`
- Claude Code real-manual lane:
  - `python scripts/lab_run_fullsec_campaign_pipeline.py --campaign-id anthropic_claudeopus46_claudecode_fullsec_real_2026-03-09 --run-day YYYY-MM-DD --skip-generate --allow-missing --allow-invalid`

## Legacy Note
- Older `focuspack_v1` campaigns remain on disk for archive and audit only.
- Older detector-shaped LLM artifacts (`det_llm_delta_brief_v1`, `det_llm_excerpt_picker_v1`) are archive-only and are not part of the active shipped runtime surface.
- Detector-first validator flows remain compatibility-only and should not drive the current showcase workflow.
