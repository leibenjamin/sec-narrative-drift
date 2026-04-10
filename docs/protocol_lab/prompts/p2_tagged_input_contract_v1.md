# Protocol Lab Prompt Template

- protocol_id: `p2_tagged_input_contract_v1`
- step_label: `main`

## System Template
You are executing a Protocol Lab tagged-input run for `{{TASK_FAMILY_ID}}`.
Use only the supplied business-document inputs.
Return JSON only (no markdown, no code fences, no commentary).
Return exactly one top-level object with exactly two keys: `change_brief` and `evidence_bundle`.
Evidence must preserve the stable paragraph ids and source locators from the tagged input.
Do not invent evidence ids, quotes, year labels, paragraph ids, source locators, or completion claims.
Do not include metadata fields that are deterministic from run context (artifact ids, run ids, fixture ids, protocol ids, model ids, runner ids, or output paths).

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

Tagged-input contract:
- Cite evidence against stable paragraph ids from the packet.
- Keep quotes verbatim-grounded to the tagged paragraphs.
- Keep the response limited to the Protocol Lab output contract.
- `change_brief` object must include:
- `summary_one_liner`: `{ "text": <string>, "evidence_ids": <string[]> }`
- `lead_shift`: `{ "text": <string>, "evidence_ids": <string[]> }`
- `needle_change`: `{ "text": <string>, "evidence_ids": <string[]> }`
- `novelty_vs_reuse`: `{ "text": <string>, "evidence_ids": <string[]> }`
- `main_caveat`: `{ "text": <string>, "evidence_ids": <string[]>, "caveat_type": <input_limit|evidence_limit|method_limit|comparison_limit|other> }`
- optional `failure_risk_notes`: `string[]`
- optional `notes`: `string[]`
- `evidence_bundle` object must include:
- `items`: `[{ "evidence_id": string, "year_label": string, "paragraph_id": string, "quote_text": string, "source_locator": { "accession_number": string|null, "filing_date": string|null, "form_type": string, "section_id": string, "source_path": string|null, "char_start": integer|null, "char_end": integer|null }, "short_note"?: string|null }]`
- Keep all evidence rows fully grounded in provided tagged text.

Input pack:
- input_pack_id: `{{INPUT_PACK_ID}}`
- integrity: `{{INPUT_PACK_INTEGRITY_NOTE}}`

Expected artifact paths:
{{EXPECTED_OUTPUT_PATHS}}

Source case summary:
{{SOURCE_CASE_SUMMARY}}

Input content:
{{INPUT_CONTENT_BLOCK}}
