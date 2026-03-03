# Documentation Index (Lab Canonical)

## Start Here
- `docs/00_DOC_INDEX.md` - this file.
- `docs/LAB_REMAINING_WORK_PLAN.md` - active execution status and remaining work.
- `docs/PRODUCT_STORY.md` - public product narrative and walkthrough order.
- `docs/PUBLIC_TONE_POLICY.md` - public-facing language policy and banned framing.
- `docs/SEC_TEXT_SAFETY.md` - SEC text trust model and rendering safety rules.
- `docs/lab/03_llm_precompute_workflow.md` - canonical precompute workflow (`full_section_v2`, master-first).
- `docs/lab/05_llm_reproducibility_contract.md` - strict manual LLM output contract.
- `docs/lab/06_llm_model_comparison_workflow.md` - campaign-aware model comparison workflow.
- `docs/lab/07_codex_real_run_profile.md` - Codex real-run operating profile.
- `docs/lab/08_remaining_work_plan_history.md` - archived/superseded execution narrative.

## Archived Legacy References (Reference Only)
Legacy contract/docs remain available under archive paths and are not canonical execution sources:
- `docs/_archive/legacy_context_20260302/00_README_doc_index.md`
- `docs/_archive/legacy_context_20260302/sec_narrative_drift_codex_spec_v1_13.md`
- `docs/_archive/legacy_context_20260302/sec_narrative_drift_codex_implementation_checklist_v1_13.md`

## Canonical Manual LLM Run Artifacts (Local)
`reports/*` stays local/untracked by policy. Typical active artifacts:
- `reports/lab_llm_master_manifest_codex_real.json`
- `reports/lab_llm_master_manifest_chatgpt_real.json`
- `reports/lab_llm_master_thread_starters_codex_real.md`
- `reports/lab_llm_master_thread_starters_chatgpt_real.md`
- `reports/lab_llm_master_validation_codex_real.md`
- `reports/lab_llm_master_validation_chatgpt_real.md`
- `reports/lab_llm_master_quality_codex_real.md`
- `reports/lab_llm_master_quality_<campaign>.md` (generated during checkpoint audits)

Compatibility-only artifacts may still appear locally (`reports/lab_llm_run_manifest.*`, legacy checklist docs) but are not canonical for real-run master execution.

## Canonical Runtime Data Paths
- Registry: `public/data/sec_narrative_drift_lab/lab_cases_v1.json`
- Detector/master outputs: `public/data/sec_narrative_drift_lab/<TICKER>/outputs/<detector_id>/<track_slug>/lab_<...>__<track_slug>.json`
- LLM campaigns index: `public/data/sec_narrative_drift_lab/lab_llm_campaigns_v1.json`
- LLM variants index: `public/data/sec_narrative_drift_lab/lab_llm_variants_v1.json`
- Method tracks index: `public/data/sec_narrative_drift_lab/lab_method_tracks_v1.json`
- Method profiles index: `public/data/sec_narrative_drift_lab/lab_method_profiles_v1.json`

## Local-Only Artifact Policy
- `reports/*` - validation/checkpoint outputs (untracked local workflow files).
- `bundles/*` - run-pack inputs and handoff artifacts (untracked local files).
- `scripts/_cache/*` and `scripts/_reports/*` - local caches/intermediate reports.
- `attic/*` - archived historical artifacts not used by production runtime.
