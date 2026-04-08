# Scripts - SEC Narrative Drift Lab

This directory documents the active Lab pipeline only.

## Active surface

The shipped app reads static JSON only from `public/data/sec_narrative_drift_lab/`.
The active build and validation flow centers on:

- `build_lab_outputs.py`
- `build_casebook_candidate_inputs_bundle.py` for active candidate-case job prep
- `lab_build_cases_registry_v1.py`
- `lab_runtime_readiness_check.py`
- `lab_run_fullsec_campaign_pipeline.py`
- the `lab_*` validation, projection, and campaign scripts
- lower-level SEC cache/extraction helpers such as `sec_fetch_and_build.py`, `sec_extract_item1a.py`, `sec_cache.py`, `sec_segments.py`, `sec_metrics.py`, and `sec_quality.py`

## Canonical product paths

- Runtime registry: `public/data/sec_narrative_drift_lab/lab_cases_v1.json`
- Deterministic outputs: `public/data/sec_narrative_drift_lab/<TICKER>/outputs/<detector_id>/<track_slug>/...`
- LLM runtime outputs: `public/data/sec_narrative_drift_lab/<TICKER>/outputs/llm_outline_compare_runtime/<campaign_slug>/...`
- LLM structured sidecars: `public/data/sec_narrative_drift_lab/<TICKER>/outputs/llm_outline_compare_structured/<campaign_slug>/...`
- Public LLM input mirror: `public/data/sec_narrative_drift_lab/llm_inputs_v2/`

## Core commands

```bash
npm run lab:predeploy
npm run lab:portfolio
npm run build
```

Prefer the canonical Lab docs for manual data work:

- `docs/00_DOC_INDEX.md`
- `docs/LAB_REMAINING_WORK_PLAN.md`
- `docs/lab/03_llm_precompute_workflow.md`
- `docs/lab/12_casebook_candidate_workflows.md`
- `docs/lab/05_llm_reproducibility_contract.md`
- `docs/lab/09_master_run_troubleshooting_and_sources_of_truth.md`

## Retired surface

The pre-Lab featured/universe dataset surface has been retired from the shipped repo:

- removed workflow: `refresh_featured.yml`
- removed public trees: `public/data/sec_narrative_drift/**` and `public/data/sec_narrative_drift_metrics/**`
- removed maintenance/orchestration scripts that only served that surface

Those artifacts remain available through Git history if historical archaeology is needed.

## SEC fetch note

`sec_fetch_and_build.py` remains in-repo as an offline/local utility for cache-driven or live SEC builds. It no longer represents the shipped website data surface, and its default output path is local under `data/legacy_sec_narrative_drift/`.
