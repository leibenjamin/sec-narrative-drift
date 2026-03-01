Self-check gate before final output:

1. Schema
- Top-level keys are complete and no extras are present.
- `artifact_id` is `llm_outline_compare_v1`.
- `lab_schema_version` and `artifact_schema_version` are `1.0`.

2. Evidence integrity
- Every `evidence_bank` snippet is verbatim and contiguous in mapped paragraph text.
- All `material_changes.evidence_refs` resolve to valid `evidence_bank` entries.
- Node evidence indices resolve to the correct year arrays.

3. Alignment integrity
- `node_alignment` never has both node refs null.
- `change_class` only uses allowed taxonomy values.
- No contradictory multi-class tags are emitted for one alignment row.
- `node_alignment` has no duplicate prev/curr pair rows.
- `material_changes` does not use flat salience (avoid assigning the same salience to all rows).

4. Provenance
- `provenance.input_file` uses canonical v2 pair path:
  `inputs/pair/<pair_basename>.json`.
- `provenance.model_provider` and `provenance.model_name` are exact.
- `provenance.run_label` matches `YYYY-MM-DD_<campaign_tag>`.

5. Evidence discipline
- Every snippet length is `<=350` chars.
- Every snippet is contiguous and verbatim.
- Prefer snippet ends at sentence or clause boundaries when possible under the length cap.
- Avoid obvious mid-word clipping unless no boundary-preserving contiguous snippet can preserve the same evidence.
- Avoid page-number prefix artifacts at snippet start unless required to preserve evidence meaning.
- Every `material_changes` row has case-specific caveat text.

6. Analytical specificity
- Every `material_changes.title` includes case-specific anchor terms from its cited evidence.
- Every `node_alignment.rationale` states a direct year-over-year contrast mechanism.
- Every caveat names a concrete evidence limitation tied to cited references.

If any check fails, revise internally and output only when all checks pass.
