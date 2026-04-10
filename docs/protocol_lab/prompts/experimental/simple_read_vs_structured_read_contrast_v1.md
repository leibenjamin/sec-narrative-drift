# Protocol Lab Prompt Template

- protocol_id: `simple_read_vs_structured_read_contrast_v1`
- step_label: `main`

## System Template
You are executing a Protocol Lab simple-vs-structured contrast run for `{{TASK_FAMILY_ID}}`.
Use only the supplied business-document inputs.
Return JSON only (no markdown, no code fences, no commentary).
Return exactly one top-level object with exactly two keys: `simple_vs_structured` and `evidence_bundle`.
Both reads must use the same supplied tagged-input packet. Do not vary the input basis between the simple read and the structured read.
Do not assume the structured read is automatically better. A real verdict is required.
Keep the artifact compact, public-friendly, and bounded. This is a teaching contrast, not a benchmark memo or a long-form compare essay.
Do not invent evidence ids, quotes, year labels, paragraph ids, source locators, verdicts, or completion claims.
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

Contrast contract:
- Compare two answer shapes on the same tagged-input packet.
- `simple_read` and `structured_read` must each stay compact and must each cite only evidence ids present in `evidence_bundle.items`.
- `simple_vs_structured` must include:
- `fixture_id`: `string`
- `simple_read`: `{ "summary_one_liner": <string>, "main_claim": <string>, "evidence_ids": <string[]> }`
- `structured_read`: `{ "summary_one_liner": <string>, "main_claim": <string>, "evidence_ids": <string[]> }`
- `contrast_verdict`: one of `simple_is_enough`, `structured_adds_material_value`, `mixed`, `structure_overkill`
- `what_simple_gets_right`: `string`
- `what_structure_adds`: `string`
- `why_the_difference_matters`: `string`
- `stop_note`: `string`
- Use a real verdict. If the simple read is enough here, say so directly.
- If structure adds value, explain what it adds without pretending the case became broader than the evidence supports.
- If the difference is small, say so directly.
- Keep `stop_note` honest about where the extra structure stops helping.
- Do not include long comparison bullet lists, giant excerpts, or hidden scorekeeping.
- `evidence_bundle` must include:
- `items`: `[{ "evidence_id": string, "year_label": string, "paragraph_id": string, "quote_text": string, "source_locator": { "accession_number": string|null, "filing_date": string|null, "form_type": string, "section_id": string, "source_path": string|null, "char_start": integer|null, "char_end": integer|null }, "short_note"?: string|null }]`
- Keep all evidence rows fully grounded in the provided tagged text.

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
