Self-check gate before final output:

1. Schema
- Top-level keys are complete and no extras are present.
- `artifact_id` is `llm_outline_compare_insight`.
- `lab_schema_version` and `artifact_schema_version` are `1.0`.

2. Evidence integrity
- Every `evidence_bank` and `evidence_map` snippet is verbatim and contiguous in mapped paragraph text.
- All refs in `material_changes`, `change_mechanisms`, `uncertainty_and_limits`, `investor_relevance`, and `insight_cards` resolve to valid evidence entries.
- Node evidence indices resolve to the correct year arrays.

3. Alignment integrity
- `node_alignment` never has both node refs null.
- `change_class` only uses allowed taxonomy values.
- No contradictory multi-class tags are emitted for one alignment row.
- `node_alignment` has no duplicate prev/curr pair rows.
- `material_changes` does not use flat salience.

4. Insight integrity
- `insight_cards` contains at least one `difference` and one `similarity`.
- Every `evidence_ref_ids` value resolves to `evidence_map.evidence_id`.
- `ui_contract.default_selected_insight_id` exists in `insight_cards`.
- Every id in `ui_contract.recommended_insight_order` exists in `insight_cards`.
- Every `ui_contract.suggested_clusters[].insight_ids` item exists in `insight_cards`.

5. Provenance and projection
- `provenance.input_file` uses canonical full_section_v2 pair path:
  `inputs/pair/<pair_basename>.json`.
- `provenance.model_provider` and `provenance.model_name` are exact.
- `provenance.run_label` matches `YYYY-MM-DD_<campaign_tag>`.
- `projection_contract.projects_to_artifact_id` is `llm_outline_compare_runtime`.

6. Evidence discipline
- Every snippet length is `<=350` chars.
- Every snippet is contiguous and verbatim.
- Prefer snippet ends at sentence or clause boundaries when possible under the cap.
- Avoid obvious mid-word clipping unless no boundary-preserving contiguous snippet can preserve the same evidence.
- Avoid page-number prefix artifacts at snippet start unless required to preserve evidence meaning.
- Every `material_changes` row has case-specific caveat text.

7. Analytical specificity
- Every `material_changes.title` includes case-specific anchor terms from cited evidence.
- Every `node_alignment.rationale` states a direct year-over-year contrast mechanism.
- Every caveat names a concrete evidence limitation tied to cited references.

If any check fails, revise internally and output only when all checks pass.


