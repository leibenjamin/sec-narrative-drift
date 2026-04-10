# Scripts — Document Protocol Lab

This directory holds the Python pipeline that produces every JSON artifact the
shipped app reads at runtime. No LLM or ML call ever happens at runtime; every
JSON under `public/data/` is the output of one of these scripts, or of a manual
LLM campaign whose outputs are deterministically projected into runtime form.

## Two product surfaces live side-by-side

The repository intentionally maintains two separate runtime data trees. Both
are still active, and most scripts target one tree or the other — not both.

1. **Public casebook (active product surface).**
   - Data tree: `public/data/business_document_protocol_lab/`
   - Tickers: `NVDA`, `LLY`, `KO`, `META`, `TSLA`, `WMT`
     (three Home anchor cases + three casebook pressure cases)
   - Canonical ticker lists: `src/lib/casebookContent.ts`
     (`HOME_ANCHOR_TICKERS`, `PUBLIC_CASEBOOK_TICKERS`)
   - Primary generator: `build_casebook_candidate_inputs_bundle.py`
   - Pilot-matrix prompt templates: `docs/protocol_lab/prompts/`
   - Canonical candidate-prep workflow doc: `docs/lab/12_casebook_candidate_workflows.md`

2. **Legacy Core4 backstage runtime (still operational, but narrower).**
   - Data tree: `public/data/sec_narrative_drift_lab/`
   - Tickers: `NVDA`, `KO`, `WM`, `GE` (`CORE4_SHOWCASE_TICKERS` in `lab_output_tracks.py`)
   - Registry: `public/data/sec_narrative_drift_lab/lab_cases_v1.json`
   - Primary generator: `lab_build_cases_registry_v1.py`
   - CI readiness gate: `lab_runtime_readiness_check.py`

The legacy backstage surface is what the required CI gates
(`npm run lab:predeploy`, `npm run lab:readiness`) currently verify. The public
casebook surface is verified by standalone Python and Node tests under
`scripts/tests/` and by manual predeploy spot-checks. When adding a new script,
be explicit about which tree it writes into.

## CI-active surface (required gates)

These are the scripts wired into `.github/workflows/lab_gates.yml` via
`package.json` entries, in the order they run:

- `lab_guard_mojibake.py` — `npm run lab:guard-mojibake`
- `lab_guard_local_only_paths.py` — `npm run lab:guard-local`
- `lab_guard_public_tone.py` — `npm run lab:guard-tone`
- `lab_guard_json_content.py` — `npm run lab:guard-json-content`
- `lab_guard_secrets.py` — `npm run lab:guard-secrets`
- `lab_build_cases_registry_v1.py` — `npm run lab:registry`
- `lab_smoke_check_registry_paths.py` — `npm run lab:smoke`
- `lab_runtime_readiness_check.py` — `npm run lab:readiness`

All of these target the legacy Core4 backstage tree. If you break one of them,
CI fails.

## Central constants module

`lab_output_tracks.py` is the single source of truth for:

- `CORE4_SHOWCASE_TICKERS` — the backstage runtime tickers.
- `LEGACY_FIXED_WINDOW_RUNTIME_CASES` — the preregistered pair window.
- `DETERMINISTIC_DETECTORS` — the deterministic-detector identifier tuple.
- `LLM_CAMPAIGNS` — every LLM outline-compare track, with primary, compare-default,
  and runtime-visibility metadata.
- Canonical filename/path helpers for every artifact kind
  (`canonical_output_relative_path`, `canonical_outline_runtime_relative_path`,
  `canonical_outline_structured_relative_path`, etc.).

Any script that needs a Core4 ticker list, a detector list, or a canonical
artifact path **must** import it from `lab_output_tracks.py`. Do not redefine
these constants locally.

## Canonical candidate-prep path (public casebook)

Use this flow to prepare LLM jobs for any public casebook case or reserve
candidate (`GOOGL`, `UNH`, or a future addition):

```bash
python scripts/build_casebook_candidate_inputs_bundle.py \
  --out-dir bundles/showcase_llm_inputs_casebook_candidates_<label>
python scripts/lab_publish_llm_inputs_v2.py \
  --bundle bundles/showcase_llm_inputs_casebook_candidates_<label>
```

Do **not** use the older `build_showcase_llm_inputs_bundle.py` for candidate
prep. It is still imported by `build_casebook_candidate_inputs_bundle.py` for
input-pack compatibility, but it is not the canonical candidate-case job-prep
path.

See `docs/lab/12_casebook_candidate_workflows.md` for the full candidate job
matrix, fiscal-year policy, archived legacy lanes, and the runs/ operator
convenience layer.

## Core commands

```bash
npm run lab:predeploy   # guards + legacy Core4 registry + smoke
npm run lab:readiness   # legacy Core4 runtime readiness gate
npm run lab:portfolio   # same as lab:readiness
npm run lab:llm-progress  # lab_record_master_progress.py
npm run build           # vite production build (compiles the React app)
```

## Canonical product paths

Legacy Core4 backstage tree:

- Runtime registry: `public/data/sec_narrative_drift_lab/lab_cases_v1.json`
- Deterministic outputs: `public/data/sec_narrative_drift_lab/<TICKER>/outputs/<detector_id>/<track_slug>/...`
- LLM runtime outputs: `public/data/sec_narrative_drift_lab/<TICKER>/outputs/llm_outline_compare_runtime/<campaign_slug>/...`
- LLM structured sidecars: `public/data/sec_narrative_drift_lab/<TICKER>/outputs/llm_outline_compare_structured/<campaign_slug>/...`
- Public LLM input mirror: `public/data/sec_narrative_drift_lab/llm_inputs_v2/`

Public casebook tree:

- Pilot-matrix cells: `public/data/business_document_protocol_lab/pilot_matrices/<FIXTURE_ID>/`
- Optional deeper layers: `public/data/business_document_protocol_lab/novelty_ledger/`, `.../effort_robustness/`, `.../skeptic_case/`
- Product positioning: `public/data/business_document_protocol_lab/product_positioning/`

## Canonical docs

Prefer these for manual data work rather than reading the scripts directly:

- `docs/00_DOC_INDEX.md`
- `docs/LAB_ARCHITECTURE_AND_GOALS.md`
- `docs/LAB_REMAINING_WORK_PLAN.md`
- `docs/lab/03_llm_precompute_workflow.md`
- `docs/lab/12_casebook_candidate_workflows.md`
- `docs/lab/05_llm_reproducibility_contract.md`
- `docs/lab/09_master_run_troubleshooting_and_sources_of_truth.md`

## Script categories (all non-CI surfaces)

Scripts outside the CI-active set generally fall into one of these groups. Any
script that does not match a group below is likely a one-off utility that can
be reviewed for archival on the next cleanup pass.

- **SEC cache/extraction helpers** (`sec_cache.py`, `sec_extract_item1a.py`,
  `sec_fetch_and_build.py`, `sec_segments.py`, `sec_metrics.py`,
  `sec_phrases.py`, `sec_quality.py`, `sec_scan_recent_annuals.py`,
  `sec_validate_cache.py`, `sec_logging.py`): offline-only utilities used by
  `build_lab_outputs.py` and manual SEC corpus work. They do not hit the
  network at build time and do not ship any runtime data.
- **Deterministic output builder** (`build_lab_outputs.py`): emits the
  deterministic detector JSON for both the legacy Core4 tree and any fixture
  passed explicitly.
- **Candidate bundle builders** (`build_casebook_candidate_inputs_bundle.py`,
  `build_showcase_llm_inputs_bundle.py`, `build_canonical_terms.py`,
  `build_showcase_roster_continuity.py`, `select_showcase_hero_pairs.py`):
  assemble manual-LLM input bundles with SHA256 integrity metadata.
- **LLM campaign manifest / projection scripts**
  (`lab_build_llm_master_manifest.py`, `lab_build_llm_run_manifest.py`,
  `lab_build_llm_campaigns_index.py`, `lab_build_llm_variants_index.py`,
  `lab_project_master_to_detectors.py`, `lab_project_master_v*_to_v*.py`,
  `lab_emit_master_thread_starters.py`,
  `lab_prompt_consistency_check.py`,
  `lab_verify_master_input_locks.py`,
  `lab_run_fullsec_campaign_pipeline.py`): drive the manual outline-compare
  campaign pipeline from bundle to runtime artifact.
- **Archive-facing helpers** (`lab_make_llm_precompute_queue.py`,
  `lab_make_pilot_pack.py`, `lab_ingest_llm_outputs.py`,
  `lab_validate_llm_outputs.py`, `lab_validate_pilot_and_report.py`,
  `lab_write_prompt_templates.py`, `lab_prompt_blocks.py`): still exist to
  support archived `det_llm_delta_brief_v1` and `det_llm_excerpt_picker_v1`
  lanes. **Must not** be used for new casebook or candidate-prep work.
- **Protocol-lab wave captures** (`protocol_lab_wave*.py` and their matching
  test files under `scripts/tests/`): one-time historical packet-capture
  scripts. They were run once to produce the pilot-matrix, novelty-ledger,
  effort-robustness, and skeptic-case bundles that now live under
  `public/data/business_document_protocol_lab/`. They are retained for
  reproducibility and for regression testing, not as active daily tools.
- **One-off migrations** (`lab_migrate_*.py`,
  `lab_rewrite_llm_run_labels_day_precision.py`): ran once against previous
  layouts and are kept in-repo only so prior runs can be replayed if
  necessary.

## Retired surface

The pre-Lab featured/universe dataset surface is gone from the shipped repo:

- removed workflow: `refresh_featured.yml`
- removed public trees: `public/data/sec_narrative_drift/**` and
  `public/data/sec_narrative_drift_metrics/**`
- removed maintenance/orchestration scripts that only served that surface

Those artifacts remain available through Git history if historical archaeology
is needed.

## SEC fetch note

`sec_fetch_and_build.py` remains in-repo as an offline/local utility for
cache-driven or live SEC builds. It no longer represents the shipped website
data surface, and its default output path is local under
`data/legacy_sec_narrative_drift/`.
