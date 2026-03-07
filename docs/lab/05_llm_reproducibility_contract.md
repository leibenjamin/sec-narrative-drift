# LLM Reproducibility Contract (Lab)

This contract defines the current canonical manual LLM run standard for showcase Lab outputs.

## Objectives
- Reproducible manual runs across threads and operators.
- Save-ready output JSON with zero post-processing.
- Transparent provenance for future model-versus-model comparisons.

## Canonical Authoring Artifact (Current)
- Canonical manual authoring artifact is now `llm_outline_compare_structured`.
- Runtime-compatible artifact remains `llm_outline_compare_runtime`, generated deterministically from structured outputs.
- Runtime UI continues to read `llm_outline_compare_runtime` during this phase.
- Validation now covers:
  - structured schema/evidence integrity
  - structured -> runtime projection equivalence for runtime files

## Output Contract
Top-level keys are fixed:
- `lab_schema_version`
- `detector_id`
- `cleaning_lens`
- `source_id`
- `ticker`
- `section`
- `year_from`
- `year_to`
- `artifacts`
- `evidence`
- `metrics`
- `provenance`

No extra top-level keys are allowed.

## Master Artifact Contract (`llm_outline_compare_structured`)
This is the canonical manual LLM output unit for current anchored showcase runs (FY2024->FY2025 across Core4).
- Fiscal-year caveat: annual filings may be filed in the next calendar year; `year_from`/`year_to` reflect fiscal years derived from `reportDate`/`filingDate`.
- Expansion path: FY2025->FY2026 can be added as an explicit additional lane when released coverage is broad enough.

Required top-level keys:
- `lab_schema_version`
- `artifact_schema_version`
- `artifact_id`
- `ticker`
- `section`
- `source_id`
- `cleaning_lens`
- `year_from`
- `year_to`
- `outline_prev`
- `outline_curr`
- `node_alignment`
- `material_changes`
- `evidence_bank`
- `lens_divergence`
- `risk_graph_prev`
- `risk_graph_curr`
- `change_mechanisms`
- `uncertainty_and_limits`
- `investor_relevance`
- `projection_contract`
- `provenance`

Hard requirements:
- `artifact_id` must be `llm_outline_compare_structured`.
- `node_alignment.change_class` must be one of:
  - `added`, `removed`, `moved`, `split`, `merged`, `reworded`, `intensified`, `softened`, `stable`.
- All paragraph indices must resolve against full-year paragraph arrays referenced by `provenance.input_file`.
- Evidence snippets must remain verbatim substrings and obey `<=350` char limit.
- `risk_graph_prev/risk_graph_curr` must encode explicit `driver -> exposure -> impact`.
- Each `change_mechanisms` row must include `mechanism`, `transmission_channel`, `business_effect`, `time_horizon`.
- `projection_contract.projects_to_artifact_id` must be `llm_outline_compare_runtime`.

## Runtime Projection Contract (`llm_outline_compare_runtime`)
- Runtime-visible `llm_outline_compare_runtime` artifacts are deterministic projections of structured outputs.
- v1 fields `outline_prev`, `outline_curr`, `node_alignment`, `material_changes`, `evidence_bank`, and `lens_divergence` must match their structured source exactly.
- Any runtime file without a resolvable corresponding structured source is invalid under current policy.

## Manual Job-Pass Contract
Each one-paste manual job must satisfy all of the following:
- Exactly one `PRECHECK_OK` line is printed.
- structured output JSON is written to the expected canonical path.
- structured output is projected to runtime path deterministically.
- Shell-safe parse check succeeds (no shell-specific redirection assumptions).
- Master validator runs with strict single-target controls:
  - `--only-mode exact_path`
  - `--expect-target-count 1`
  - `--fail-if-target-count-mismatch`
- Job status line from validator is present:
  - `JOB_VALIDATE targets=<n> missing=<n> invalid=<n> mismatch=<n> present_mismatch=<n> status=<PASS|FAIL>`
- Quality blocker audit passes for the output:
  - `python scripts/lab_audit_master_output_quality.py --output "<path>" --mode blockers --strict-depth ...`
- Exactly one final status line is printed for the job thread.

Strict-depth blockers (`--strict-depth`, `llm_outline_compare_structured`):
- `material_changes` must have at least 4 rows.
- Material-change evidence refs must cover each year with unique refs:
  - if year paragraph count >= 50: at least 4 unique refs
  - otherwise: at least 3 unique refs
- Among top-3 material changes by salience, at least one row must reference both years with non-opening paragraphs in each year.
- For each year with paragraph count >= 30, material refs must span at least two section terciles.
- Shallow-reference patterns are blockers in strict mode:
  - opening paragraph ratio > 0.35
  - evidence ref concentration > 0.50
  - unique-ref ratio < 0.50

## Portable Run-Pack Contract (Script-Free Reproduction)
Portable run packs must include:
- `job/job_meta.json`
- `inputs/pair.json`
- `inputs/year_prev.json`
- `inputs/year_curr.json`
- `checksums/sha256_manifest.json`
- `starter/THREAD_STARTER.txt`
- `README_PORTABLE.md`

Portable starters:
- must use only local relative file paths from the pack root
- must not require workspace-only scripts or repo-specific paths
- must include local Python preflight/hash checks and JSON parse checks

## Detector Artifact Contract
- `det_llm_delta_brief_v1`: `artifacts` must contain only `delta_brief`.
- `det_llm_excerpt_picker_v1`: `artifacts` must contain only `selected_prev`, `selected_curr`.

## Evidence Contract
- `paragraph_idx` values must be FULL indices.
- For `full_section_v2`, `paragraph_idx` is a direct FULL index from referenced year input arrays.
- Pair manifests reference year files under `year_inputs.prev` and `year_inputs.curr`; `provenance.input_file` points to the pair-manifest path.
- Snippets must be verbatim substrings of mapped paragraphs.
- Snippets must be `<=350` chars.
- `<=350` is a campaign reproducibility/UX constraint so outputs remain comparable across operators and runs.
- If mapped paragraph length is `>350`, snippet must be a contiguous verbatim trimmed substring (recommended `220-320` chars, hard cap `350`).
- Synthetic ellipses or edited snippets are not allowed.
- Evidence blocks must be sorted by `(year, paragraph_idx)` ascending.
- Duplicate evidence blocks with the same `(year, paragraph_idx)` are not allowed.
- `highlights` is required for every evidence block with `1-3` non-empty values.

## Metrics Contract
- `metrics.confidence` must be one of `0.25`, `0.50`, `0.75`.
- `metrics.confidence` is an ordinal heuristic confidence band, not a calibrated probability or confidence interval.
- `metrics.warnings` should include concise caveats when signal or coverage is limited.
- `metrics.warnings` entries must be complete statements; placeholder tails like `Input file citation:`, `Source:`, `Input source:` are invalid.

## Provenance Contract
`provenance` keys are restricted to:
- `input_file` (required)
- `model_provider` (required, exact campaign provider)
- `model_name` (required, exact campaign model name)
- `run_label` (required, must start with `YYYY-MM-DD_`)

Canonical `provenance.input_file` pattern for structured:
- `inputs/pair/<TICKER>_<YEAR_FROM>_<YEAR_TO>_10k_item1a_<LENS>_edgar.json`

No extra provenance keys are allowed.

## Runtime Security Presentation Rules
- JSON-derived metadata links are same-origin-only in runtime UI.
- Internal input/output paths may be opened directly when they resolve under `public/data/...`.
- External metadata URLs are displayed as plain text with copy actions (non-clickable by policy).

## Citation Contract
For `det_llm_delta_brief_v1`:
- At least two inline citations are required.
- Allowed format only: `YYYY para NN`.
- Disallowed tokens include pilcrow-style citation symbols and mojibake variants.
- Every citation must map to an evidence block with matching year and `paragraph_idx = NN - 1`.

## Mandatory Pre-Output Quality Gate
Before final JSON output in each manual thread:
- Every `snippet` must be a contiguous verbatim substring of the mapped FULL-index paragraph.
- Every `snippet` must be `<=350` chars.
- For mapped paragraphs `>350` chars, snippet must be a strict contiguous trimmed substring `<=350` (recommended `220-320` chars).
- Evidence blocks are sorted by `(year, paragraph_idx)` ascending with no duplicates.
- Every evidence block includes `highlights` with `1-3` non-empty values.
- For excerpt picker, `selected_prev/selected_curr` must exactly equal deduped evidence indices per year (no extras) and be sorted ascending.
- For delta brief, evidence count must be `4-8` total with `>=2` per year.
- For excerpt picker, evidence count must be `6-10` total with `>=3` per year.
- Delta brief must include non-empty sections in order: `Change:`, `Drivers:`, `Caveat:`.
- Prefer snippet boundaries at sentence/clause ends when possible under the 350-char cap.
- Avoid obvious mid-word snippet clipping when avoidable.
- Avoid page-number prefix artifacts in snippet starts unless required for evidence fidelity.
- If any check fails, revise in-thread before final output.

## Schema-Unlock Governance Gate (Required Before Structured Cutover)
Baseline policy remains locked for shipped runtime contracts:
- Do not change public JSON schemas or detector envelope keys unless explicitly unlocked.

Before implementing `llm_outline_compare_structured`:
1. Record explicit unlock approval in canonical docs.
2. Define migration and rollback plan for runtime compatibility.
3. Keep `llm_outline_compare_runtime` available during migration.
4. Provide deterministic structured->runtime projection for legacy detector envelopes and existing UI paths.

## Validation Entry Point
- Canonical validator:
  `python scripts/lab_validate_llm_master_outputs.py`

Recommended usage:
1. Progress:
   `python scripts/lab_validate_llm_master_outputs.py --manifest reports/lab_llm_master_manifest_<campaign>.json --campaign-id <campaign_id> --allow-missing --allow-invalid --report reports/lab_llm_master_validation_<campaign>.md`
2. Final strict:
   `python scripts/lab_validate_llm_master_outputs.py --manifest reports/lab_llm_master_manifest_<campaign>.json --campaign-id <campaign_id> --report reports/lab_llm_master_validation_<campaign>.md`

Compatibility note:
- `scripts/lab_validate_llm_manifest_outputs.py` remains legacy-only for detector-manifest workflows and is non-canonical for master-manifest production runs.



## Rename Governance Unlock (Approved)
- Approved: schema/envelope artifact-id rename from numeric version labels to role-based labels:
  - `llm_outline_compare_v1` -> `llm_outline_compare_runtime`
  - `llm_outline_compare_v2` -> `llm_outline_compare_structured`
  - `llm_outline_compare_v3` -> `llm_outline_compare_insight`
- Approved: manifest target-field rename:
  - `projected_master_output_v1` -> `projected_master_output_runtime`
  - `projected_master_output_v2` -> `projected_master_output_structured`
- Rollback plan: migration script can re-map ids/fields deterministically in reverse before publication.
