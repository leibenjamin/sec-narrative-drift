# Master Run Troubleshooting and Sources of Truth

Last updated: 2026-03-09

This is the canonical recovery guide for manual LLM run drift, stale-lock failures, and campaign/source-of-truth confusion.

## What Is Canonical
The active master-run truth chain is:
1. `scripts/lab_output_tracks.py`
2. active bundle under `bundles/showcase_llm_inputs_full_section_v2_*`
3. public mirror `public/data/sec_narrative_drift_lab/llm_inputs_v2/`
4. master manifest in `reports/lab_llm_master_manifest_<campaign>.json`
5. master starters in `reports/lab_llm_master_thread_starters_<campaign>.md`
6. lock report from `scripts/lab_verify_master_input_locks.py`
7. prompt consistency report/checks from `scripts/lab_prompt_consistency_check.py`
8. validator, audit, progress, and public metadata/index refresh scripts

Whole-campaign master validation and quality reports under `reports/` are canonical local operator truth for a campaign checkpoint. One-file `--only` checks should not replace them.

If two layers disagree, trust the earlier canonical layer in that chain and regenerate the later layers.

## Canonical Files by Task
### Campaign metadata
- `scripts/lab_output_tracks.py`
- `public/data/sec_narrative_drift_lab/lab_llm_campaigns_v1.json`
- `public/data/sec_narrative_drift_lab/lab_method_tracks_v1.json`

### Input generation and mirroring
- `scripts/build_showcase_llm_inputs_bundle.py`
- `scripts/lab_publish_llm_inputs_v2.py`
- active bundle root such as `bundles/showcase_llm_inputs_full_section_v2_20260305_2425anchor`
- `public/data/sec_narrative_drift_lab/llm_inputs_v2/inputs_index_pair_v2.json`
- `public/data/sec_narrative_drift_lab/llm_inputs_v2/inputs_index_year_v2.json`

### Master-run prep
- `scripts/lab_run_fullsec_campaign_pipeline.py`
- `scripts/lab_build_llm_master_manifest.py`
- `scripts/lab_emit_master_thread_starters.py`
- `scripts/lab_verify_master_input_locks.py`
- `scripts/lab_prompt_consistency_check.py`

### Validation and projection
- `scripts/lab_validate_llm_master_outputs.py`
- `scripts/lab_audit_master_output_quality.py`
- `scripts/lab_project_master_v2_to_v1.py`
- `scripts/lab_record_master_progress.py`

### Runtime/public metadata refresh
- `scripts/lab_build_llm_campaigns_index.py`
- `scripts/lab_build_method_tracks_index.py`
- `scripts/lab_build_llm_variants_index.py`
- `scripts/lab_runtime_readiness_check.py`

## Canonical vs Compatibility vs Archive-Only
### Canonical
- `docs/00_DOC_INDEX.md`
- `docs/LAB_REMAINING_WORK_PLAN.md`
- `docs/lab/03_llm_precompute_workflow.md`
- `docs/lab/05_llm_reproducibility_contract.md`
- `docs/lab/06_llm_model_comparison_workflow.md`
- current `reports/lab_llm_master_manifest_*`
- current `reports/lab_llm_master_thread_starters_*`

### Compatibility-only
- `reports/lab_llm_run_manifest.*`
- older detector-first checklist/report flows
- archived ChatGPT real identity `openai_chatgpt52ext_agent_fullsec_real_2026-02-27`

### Archive-only or fixture-only
- focuspack-era output lanes not used by shipped runtime
- non-canonical starter variants such as `*_v2.md` or `*_legacy.md`
- historical temporary reports and scratch diagnostics once they are no longer referenced
- `bundles/showcase_llm_inputs_full_section_v2_20260222` remains fixture-only and should be preserved for tests

## March 9, 2026 Stale-Lock Incident
### Symptom
A WM Codex real starter failed immediately with:
- `{"error":"HARD_FAILURE","reason":"preflight input lock mismatch"}`

### Root cause
The starter and master manifest embedded an old pair SHA for the active WM pair manifest, while the live bundle file had changed.

### What was actually stale
- active bundle pair manifest bytes had changed
- public `llm_inputs_v2` pair mirror and/or downstream manifests/starters were still using older locks
- year-file locks still matched, which made the failure look partial and easy to misread

### Residual metadata defect discovered after lock repair
- only two active-bundle focus-signal hints were still invalid after the lock-chain cleanup:
  - WM raw `wm_healthcare_solutions_execution_deterioration`: current hint `97` exceeded the 2025 raw paragraph count of `91`
  - GE raw `ge_leap_services_execution_ramp`: current hint `33` exceeded the 2025 raw paragraph count of `32`
- those hints now fail fast during bundle generation, starter emission, and master lock verification.

### Why rerunning the same starter was unproductive
The failure was deterministic. No model retry could fix a stale `JOB_META.expected_pair_sha256` value.

## Recovery Sequence
When you see stale-lock behavior, run this order:
1. Confirm the active bundle root you actually intend to use.
2. Publish `llm_inputs_v2` from that bundle:
   - `python scripts/lab_publish_llm_inputs_v2.py --bundle <bundle_root>`
3. Regenerate the campaign manifest and starters through the canonical pipeline:
   - `python scripts/lab_run_fullsec_campaign_pipeline.py --campaign-id <campaign_id> --bundle <bundle_root> --skip-generate --allow-missing --allow-invalid`
4. Run the lock verifier directly if needed:
   - `python scripts/lab_verify_master_input_locks.py --bundle <bundle_root> --campaign-id <campaign_id> --master-manifest <manifest.json> --master-starters <starters.md>`
5. Run prompt consistency.
6. Only then rerun manual jobs.
7. If the rerun issue is only an ugly raw-text extraction artifact in a non-evidence title/label, fix the prompt/starter policy and rerun the affected job; do not hand-edit committed output JSON.
8. If a temporary direct output edit was used for triage, replace it with a clean rerun before treating the artifact as canonical.

## How to Read a Failure
### `preflight input lock mismatch`
- starter lock/count metadata does not match the live files or manifest
- fix source-of-truth drift first

### `master input lock verification failed`
- bundle, public mirror, manifest, or starters disagree
- inspect the first reported layer and regenerate downstream artifacts from that point

### one-file validation or audit check
- filtered `--only` validator runs now default to scratch `_tmp_*` reports when `--report` is omitted
- filtered quality-audit runs now do the same for both `--only` and `--output` one-file checks when `--report` is omitted
- if a canonical full-campaign report was overwritten during investigation, restoring it from a full-campaign rerun was the correct recovery action
- the March 9 GE raw non-evidence title cleanup was temporary triage only and has now been superseded by rerun-based recovery

### prompt consistency failure with lock details
- docs or prompt assets may be fine, but manifest/starter/live-file coherence is broken
- do not treat this as a model-instructions issue until lock verification passes

## Venue-Specific Rerun Rules
### ChatGPT Desktop
- Thread starter plus three attached inputs is enough to rerun in a fresh chat.
- ChatGPT cannot write local workspace files directly.
- Operators save the returned JSON locally and run local validation/projection.

### Codex and Claude Code workspace-aware lanes
- The starter assumes direct workspace paths.
- If users download those starters outside the original workspace, they must edit workspace-relative paths before rerun.
- The same is true for local validation/projection commands when folder layout differs.

## Raw-Lens Title Policy
- Evidence snippets remain strictly verbatim and contiguous.
- For raw-lens outputs, only `material_changes.title` and outline `label` fields may lightly normalize obvious extraction artifacts.
- Those non-evidence display fields must still preserve filing meaning and keep anchor language grounded in cited evidence.

## Archive Cleanup Map
### Archived to `attic/`
- legacy `public/data/sec_narrative_drift_lab/*/outputs/det_llm_delta_brief_v1/**` trees
- legacy `public/data/sec_narrative_drift_lab/*/outputs/det_llm_excerpt_picker_v1/**` trees
- legacy flat `public/data/sec_narrative_drift_lab/llm_inputs/**` and `llm_outputs/**` mirrors
- historical `public/data/sec_narrative_drift_lab/lab_build_complete.json`

### Compatibility paths still allowed
- script-level review-pack or archaeology workflows may fall back to `attic/` when they still mention archived detector outputs
- active runtime and public indexes must not fetch from `attic/`

### What remains canonical after cleanup
- `public/data/sec_narrative_drift_lab/llm_inputs_v2/**`
- active `llm_outline_compare_structured` and `llm_outline_compare_runtime` outputs for FY2024->FY2025
- current campaign indexes and runtime metadata under `public/data/sec_narrative_drift_lab/`

## Future Campaign Onboarding Checklist
1. Add the campaign to `scripts/lab_output_tracks.py` with truthful id, slug, model name, execution venue, and runtime visibility.
2. Regenerate public campaign/method/variant indexes.
3. Generate project instructions.
4. Build the master manifest.
5. Emit master starters.
6. Run the lock verifier.
7. Run prompt consistency.
8. Only then begin manual runs or publish outputs.

## Deferred Follow-Up
A helper for formatting/parsing end-user self-run campaign outputs outside the app is still planned. Do not treat that as part of the current canonical master-run pipeline.
