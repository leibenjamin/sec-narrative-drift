# LLM Precompute Workflow (Showcase v3)

Status: canonical manual rerun workflow for Lab (`full_section_v2`, master-first).

## Canonical Entry Points
- `docs/lab/04_chatgpt_project_setup.md`
- `docs/lab/07_codex_real_run_profile.md`
- `reports/lab_project_instructions_<campaign_id>.txt`
- `reports/lab_llm_master_manifest_<campaign>.json`
- `reports/lab_llm_master_thread_starters_<campaign>.md`
- `reports/lab_llm_master_validation_<campaign>.md`
- `reports/lab_llm_manual_rerun_checklist.md` (legacy detector checklist; compatibility only)
- `scripts/lab_run_fullsec_campaign_pipeline.py` (single-command orchestrator for full_section_v2 flow)
- `scripts/lab_build_llm_master_manifest.py`
- `scripts/lab_emit_master_thread_starters.py`
- `scripts/lab_validate_llm_master_outputs.py`
- `scripts/lab_record_master_progress.py`
- `scripts/lab_project_master_to_detectors.py`

## Canonical Starter File (Codex Real Runs)
- Single-source starter file:
  - `reports/lab_llm_master_thread_starters_codex_real.md`
- Canonical generation profile:
  - `scripts/lab_emit_master_thread_starters.py --format vscode_autowrite_v3`
- Non-canonical compatibility artifacts:
  - `reports/lab_llm_master_thread_starters_codex_real_v2.md`
  - `reports/lab_llm_master_thread_starters_codex_real_legacy.md`

## Runtime Truth (Current Push)
- Runtime policy is real-run LLM evidence only.
- Runtime-visible campaign: `openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27` (manual lane; artifacts may be missing until jobs are completed).
- Runtime-hidden pending campaign: `openai_chatgpt52ext_agent_fullsec_real_2026-02-27` (enable only after strict-valid coverage).
- Synthetic full-section campaigns (`*_fullsec_2026-02-22`) remain on disk for audit history only and are hidden in runtime selectors.
- `focuspack_v1` campaigns remain on disk for audit history only and are hidden in runtime selectors.
- Runtime case scope is FY2022+ adjacent pairs only (`NVDA/KO/WM/GE` x `2022-2023`, `2023-2024`, `2024-2025`).
- For pairs without LLM sidecars, runtime remains deterministic-first with explicit LLM missing/debug states.

## Zero-Touch Output Rule
- LLM outputs are runtime-static artifacts, generated offline.
- Each output should be directly saveable to canonical path as valid JSON.
- Avoid post-generation patching and reconciliation as a normal step.
- If recurring issues appear, improve prompt blocks and thread starters first.

## Job-Pass Contract (One-Paste Hardened)
Each manual master job is considered PASS only when all of the following are true:
- Exactly one `PRECHECK_OK ...` line is printed.
- Output JSON write succeeds at the canonical path.
- Shell-safe parse check succeeds (`JSON_OK` expected).
- `scripts/lab_validate_llm_master_outputs.py` runs with strict single-target controls:
  - `--only-mode exact_path`
  - `--expect-target-count 1`
  - `--fail-if-target-count-mismatch`
- Master quality blocker audit passes:
  - `python scripts/lab_audit_master_output_quality.py --output "<path>" --mode blockers ...`
- Exactly one final status line is printed:
  - success: `WRITE_OK JSON_OK VALIDATION_OK`
  - failure: `FAILED: ...`

## Canonical Job Counts
- Master jobs per campaign: `12 pairs x 2 lenses = 24`.
- Projection outputs per campaign (legacy detector compatibility): `24 x 2 detectors = 48`.
- Prefer master-first execution; do not run detector-by-detector manual jobs as primary workflow.

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
1. Wave progress (Codex real):
   `python scripts/lab_validate_llm_master_outputs.py --manifest reports/lab_llm_master_manifest_codex_real.json --campaign-id openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27 --allow-missing --allow-invalid --report reports/lab_llm_master_validation_codex_real.md`
2. Wave progress (ChatGPT real):
   `python scripts/lab_validate_llm_master_outputs.py --manifest reports/lab_llm_master_manifest_chatgpt_real.json --campaign-id openai_chatgpt52ext_agent_fullsec_real_2026-02-27 --allow-missing --allow-invalid --report reports/lab_llm_master_validation_chatgpt_real.md`
3. Master quality audit (blockers):
   `python scripts/lab_audit_master_output_quality.py --manifest reports/lab_llm_master_manifest_<campaign>.json --campaign-id <campaign_id> --allow-missing --mode blockers --report reports/lab_llm_master_quality_<campaign>.md`
4. Checkpoint progress capture:
   `python scripts/lab_record_master_progress.py --manifest reports/lab_llm_master_manifest_<campaign>.json --campaign-id <campaign_id> --report-md reports/lab_llm_master_batch_progress_<campaign>.md --history-json reports/lab_llm_master_batch_progress_<campaign>.json --label after_job_XX`
5. Deterministic gates:
   `npm run lab:predeploy`
   `npm run lab:readiness`
   `npm run build`

## Orchestrated Pipeline (Recommended)
- Codex full-section real-manual lane:
  - `python scripts/lab_run_fullsec_campaign_pipeline.py --campaign-id openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27 --run-day YYYY-MM-DD --skip-generate --allow-missing --allow-invalid`
- ChatGPT full-section real-manual lane:
  - `python scripts/lab_run_fullsec_campaign_pipeline.py --campaign-id openai_chatgpt52ext_agent_fullsec_real_2026-02-27 --run-day YYYY-MM-DD --skip-generate --allow-missing --allow-invalid`
- Publish step behavior:
  - `scripts/lab_publish_llm_inputs_v2.py` now cleans stale mirror files by default.
  - Pass `--no-clean` only when explicitly preserving existing mirror files.

## Legacy Notice
Older queue and ingest flow docs remain for history and compatibility checks only.
They are non-canonical for current showcase manual reruns.
Legacy `focuspack_v1` inputs remain on disk for audit only and are runtime-hidden.
Detector-first validator flow via `scripts/lab_validate_llm_manifest_outputs.py` remains compatibility-only.
