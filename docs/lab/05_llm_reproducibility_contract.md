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
- For focuspack inputs, FULL index mapping must come from `focuspack_meta.selected_prev_indices` and `focuspack_meta.selected_curr_indices`.
- Snippets must be verbatim substrings of mapped paragraphs.
- Snippets must be `<=350` chars.
- `highlights` is required and must be non-empty for every evidence block.

## Metrics Contract
- `metrics.confidence` must be one of `0.25`, `0.50`, `0.75`.
- `metrics.warnings` must include:
  `"Focuspack is a subset; verify in full compare pane."`

## Provenance Contract
`provenance` keys are restricted to:
- `input_file` (required)
- `model_provider` (required)
- `model_name` (required)
- `run_label` (optional)

No extra provenance keys are allowed.

## Citation Contract
For `det_llm_delta_brief_v1`:
- At least two inline citations are required.
- Allowed format only: `YYYY para NN`.
- Disallowed tokens include pilcrow-style citation symbols and mojibake variants.

## Validation Entry Point
- Canonical validator:
  `python scripts/lab_validate_llm_manifest_outputs.py`

Recommended usage:
1. Progress:
   `python scripts/lab_validate_llm_manifest_outputs.py --allow-missing --allow-invalid --report reports/lab_llm_manifest_validation.md`
2. Final strict:
   `python scripts/lab_validate_llm_manifest_outputs.py --report reports/lab_llm_manifest_validation.md`
