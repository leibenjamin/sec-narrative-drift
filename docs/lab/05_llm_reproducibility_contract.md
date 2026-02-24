# LLM Reproducibility Contract (Lab)

This contract defines the current canonical manual LLM run standard for showcase Lab outputs.

## Objectives
- Reproducible manual runs across threads and operators.
- Save-ready output JSON with zero post-processing.
- Transparent provenance for future model-versus-model comparisons.

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

Canonical `provenance.input_file` pattern for v2:
- `inputs/pair/<TICKER>_<YEAR_FROM>_<YEAR_TO>_10k_item1a_<LENS>_edgar.json`

No extra provenance keys are allowed.

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
- If any check fails, revise in-thread before final output.

## Validation Entry Point
- Canonical validator:
  `python scripts/lab_validate_llm_manifest_outputs.py`

Recommended usage:
1. Progress:
   `python scripts/lab_validate_llm_manifest_outputs.py --allow-missing --allow-invalid --report reports/lab_llm_manifest_validation.md`
2. Final strict:
   `python scripts/lab_validate_llm_manifest_outputs.py --report reports/lab_llm_manifest_validation.md`
