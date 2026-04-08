# Documentation Index

## Start Here
- `docs/00_DOC_INDEX.md` - this file.
- `docs/LAB_REMAINING_WORK_PLAN.md` - active execution status and remaining work.
- `docs/LAB_ARCHITECTURE_AND_GOALS.md` - canonical product/runtime architecture, design goals, and shipped-surface principles.
- `docs/PRODUCT_STORY.md` - public product narrative and walkthrough order.
- `docs/DEMO_READINESS.md` - compact walkthrough and speaking notes for the current public pilot.
- `docs/REMAINING_SEAMS.md` - brief note on the remaining public/runtime seams and manual follow-ups.
- `docs/PUBLIC_TONE_POLICY.md` - public-facing language policy and banned framing.
- `docs/SEC_TEXT_SAFETY.md` - SEC text trust model and rendering safety rules.
- `docs/lab/03_llm_precompute_workflow.md` - canonical precompute workflow (`full_section_v2`, master-first).
- `docs/lab/05_llm_reproducibility_contract.md` - strict manual LLM output contract for outline-compare runs.
- `docs/lab/06_llm_model_comparison_workflow.md` - campaign-aware model comparison workflow.
- `docs/lab/07_codex_real_run_profile.md` - Codex real-run operating profile.
- `docs/lab/12_casebook_candidate_workflows.md` - canonical active-vs-archived workflow map and candidate-case job-prep guide.
- `docs/lab/11_claude_code_real_run_profile.md` - Claude Code real-run operating profile.
- `docs/lab/09_master_run_troubleshooting_and_sources_of_truth.md` - canonical source-of-truth and recovery guide for bundle -> mirror -> manifest -> starter drift.
- `docs/lab/10_case_quality_review_log.md` - canonical human-review ledger for keep/defer/rerun decisions on active case artifacts.
- `docs/lab/08_remaining_work_plan_history.md` - archived and superseded execution narrative.

## Archived Legacy References (Reference Only)
Legacy contract/docs remain available under archive paths and are not canonical execution sources:
- `docs/_archive/legacy_context_20260302/00_README_doc_index.md`
- `docs/_archive/legacy_context_20260302/sec_narrative_drift_codex_spec_v1_13.md`
- `docs/_archive/legacy_context_20260302/sec_narrative_drift_codex_implementation_checklist_v1_13.md`

## Canonical Manual LLM Run Artifacts (Local)
`reports/*` stays local and untracked by policy. Typical active artifacts:
- `reports/lab_llm_master_manifest_codex_real.json`
- `reports/lab_llm_master_manifest_chatgpt_real.json`
- `reports/lab_llm_master_thread_starters_codex_real.md`
- `reports/lab_llm_master_thread_starters_chatgpt_real.md`
- `reports/lab_llm_master_validation_codex_real.md`
- `reports/lab_llm_master_validation_chatgpt_real.md`
- `reports/lab_llm_master_quality_codex_real_structured.md`
- `reports/lab_llm_master_quality_<campaign>_structured.md`
- `reports/lab_llm_master_input_locks_<campaign>_<artifact>.md`

Compatibility-only artifacts may still appear locally (`reports/lab_llm_run_manifest.*`, older checklist docs, archived starter variants), but they are not canonical for current real-run master execution.

## Canonical Runtime Data Paths
- Registry: `public/data/sec_narrative_drift_lab/lab_cases_v1.json`
- Deterministic outputs: `public/data/sec_narrative_drift_lab/<TICKER>/outputs/<detector_id>/<track_slug>/lab_<...>__<track_slug>.json`
- LLM outline runtime outputs: `public/data/sec_narrative_drift_lab/<TICKER>/outputs/llm_outline_compare_runtime/<campaign_slug>/lab_<...>__<campaign_slug>.json`
- LLM outline structured sidecars: `public/data/sec_narrative_drift_lab/<TICKER>/outputs/llm_outline_compare_structured/<campaign_slug>/lab_<...>__<campaign_slug>.json`
- LLM inputs mirror: `public/data/sec_narrative_drift_lab/llm_inputs_v2/`
- LLM campaigns index: `public/data/sec_narrative_drift_lab/lab_llm_campaigns_v1.json`
- LLM variants index: `public/data/sec_narrative_drift_lab/lab_llm_variants_v1.json`
- Method tracks index: `public/data/sec_narrative_drift_lab/lab_method_tracks_v1.json`
- Method profiles index: `public/data/sec_narrative_drift_lab/lab_method_profiles_v1.json`

## Local-Only Artifact Policy
- `reports/*` - validation and checkpoint outputs for local workflow.
- `bundles/*` - run-pack inputs and handoff artifacts.
- `scripts/_cache/*` and `scripts/_reports/*` - local caches and intermediate reports.
- `attic/*` - archived historical artifacts not used by production runtime.
