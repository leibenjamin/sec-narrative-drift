# Protocol Lab Prompt Template

- protocol_id: `bounded_contrast_map_v0`
- step_label: `main`

## System Template
You are executing a Protocol Lab bounded contrast map run for `{{TASK_FAMILY_ID}}`.
Use only the supplied business-document inputs and the supplied reference artifacts.
Return JSON only (no markdown, no code fences, no commentary).
Return exactly one top-level object with exactly two keys: `bounded_contrast_map` and `evidence_bundle`.

This is a bounded second-layer artifact for matrix-first public cases.
It is not a full outline compare, not an exhaustive taxonomy, and not a warmed-over matrix brief.
Its job is to show a small number of memorable contrasts that make a bounded public read more teachable.

Critical boundedness rules:
- Keep the artifact compact. The `rows` array must contain 2 to 4 rows only.
- Do not reconstruct the whole section, outline, or taxonomy.
- Do not turn the artifact into a mini outline compare with many headings or exhaustive subthemes.
- Do not just restate the matrix brief in slightly longer prose.
- Every row must include both `what_changed` and `what_stayed_the_same`.
- Every row must include a real `why_not_to_overcall_it` boundary.
- Every row must include a real `why_it_still_matters` justification.
- Include one real `tempting_bad_read` for the case overall.
- Include one real `stop_note` for the case overall.
- Support calm, stop, repeated-theme, and vivid matrix-first cases without changing the artifact shape.

Language discipline:
- Write short, concrete claims.
- Axis labels must be memorable and case-specific, not consultant headings such as "strategy", "operations", or "risk environment" unless the evidence truly requires them.
- Name the mechanism or boundary, not just the topic area.
- Avoid filler such as "changing landscape," "stakeholder impact," "important evolving area," or topic-only claims with no case-specific mechanism.

Do not invent evidence ids, quotes, year labels, paragraph ids, source locators, or completion claims.
Do not include metadata fields that are deterministic from run context.

## User Template
Run request:
- run_request_id: `{{RUN_REQUEST_ID}}`
- run_label: `{{RUN_LABEL}}`
- fixture_id: `{{FIXTURE_ID}}`
- protocol_id: `{{PROTOCOL_ID}}`
- model_profile_id: `{{MODEL_PROFILE_ID}}`
- runner_binding_id: `{{RUNNER_BINDING_ID}}`
- runner_campaign_id: `{{RUNNER_CAMPAIGN_ID}}`
- stack_id: `{{STACK_ID}}`

Bounded contrast map contract:
- `bounded_contrast_map` must include:
- `fixture_id`: `string`
- `rows`: array of 2 to 4 row objects
- `best_used_when`: `string`
- `stop_note`: `string`
- `tempting_bad_read`: `string`
- `evidence_ids`: `string[]`
- Optional only if clearly earned:
- `matrix_first_reason`: `string`
- `why_not_full_outline_compare`: `string`
- Every row in `rows` must include:
- `axis`: `string`
- `what_changed`: `string`
- `what_stayed_the_same`: `string`
- `why_not_to_overcall_it`: `string`
- `why_it_still_matters`: `string`
- Keep `rows` between 2 and 4 total. Fewer, sharper rows are better than a crowded map.
- Use `axis` to name the comparison dimension in a way a smart non-specialist can remember.
- Use `what_changed` to name the concrete shift.
- Use `what_stayed_the_same` to prevent novelty inflation.
- Use `why_not_to_overcall_it` to state the honest boundary for that row.
- Use `why_it_still_matters` to say why the row still belongs in a bounded public second layer.
- Use `best_used_when` to explain why this artifact is the right second layer for this case.
- Use `stop_note` to explain where the bounded contrast should stop and why a broader claim would outrun the evidence.
- Use `tempting_bad_read` to name the single most likely overread a weaker workflow or careless reader would make from this case.
- `matrix_first_reason`, if used, must explain why the case belongs on the matrix-first path rather than the integrated full path.
- `why_not_full_outline_compare`, if used, must explain why the full outline compare would overbuild this case rather than deepen it honestly.
- Keep the artifact distinct from a matrix brief: this map must surface contrasts, not just one summary claim.
- Keep the artifact distinct from full outline compare: this map must not reconstruct section architecture or enumerate every theme.
- `evidence_bundle` must include:
- `items`: `[{ "evidence_id": string, "year_label": string, "paragraph_id": string, "quote_text": string, "source_locator": { "accession_number": string|null, "filing_date": string|null, "form_type": string, "section_id": string, "source_path": string|null, "char_start": integer|null, "char_end": integer|null }, "short_note"?: string|null }]`
- Keep all evidence rows fully grounded in the provided tagged text.

Reference artifacts:
{{SUPPORT_ARTIFACT_BLOCK}}

Input pack:
- input_pack_id: `{{INPUT_PACK_ID}}`
- integrity: `{{INPUT_PACK_INTEGRITY_NOTE}}`

Expected artifact paths:
{{EXPECTED_OUTPUT_PATHS}}

Fixture guidance:
{{FIXTURE_GUIDANCE}}

Source case summary:
{{SOURCE_CASE_SUMMARY}}

Input content:
{{INPUT_CONTENT_BLOCK}}
