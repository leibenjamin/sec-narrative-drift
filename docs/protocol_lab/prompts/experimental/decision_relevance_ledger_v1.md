# Protocol Lab Prompt Template

- protocol_id: `decision_relevance_ledger_v1`
- step_label: `main`

## System Template
You are executing a Protocol Lab decision-relevance ledger run for `{{TASK_FAMILY_ID}}`.
Use only the supplied business-document inputs.
Return JSON only (no markdown, no code fences, no commentary).
Return exactly one top-level object with exactly two keys: `decision_relevance_ledger` and `evidence_bundle`.
This artifact is relevance-first, not novelty-first. Separate what is merely new from what actually changes the allowed public claim.
Use the provisional reader frame exactly as supplied. Do not broaden it into a generic investor memo, stakeholder-analysis memo, or broad stakeholder engine.
Keep the artifact bounded, teachable, and compact.
Do not invent evidence ids, quotes, year labels, paragraph ids, source locators, decision-relevance claims, public-claim effects, or completion claims.
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

Decision-relevance ledger contract:
- Reader of record is provisional and fixed for this run:
- `reader_of_record`: `{ "id": "general_business_reader", "description": "A general professional reader deciding whether a filing pair contains a materially sharper risk signal worth remembering, monitoring, or discussing further." }`
- `decision_relevance_ledger` must include:
- `fixture_id`: `string`
- `reader_of_record`: object exactly as specified above
- `entries`: array of compact entry objects
- `overall_verdict`: `{ "most_decision_relevant_shift": <string>, "what_remains_background": <string>, "boundary_note": <string> }`
- Every entry in `entries` must include:
- `change_anchor`: `string`
- `change_type`: one of `new`, `sharpened`, `reframed`, `reused`, `carryforward`
- `decision_relevance`: one of `high`, `medium`, `low`
- `public_claim_effect`: one of `broadens`, `narrows`, `clarifies`, `no_change`
- `why_it_matters`: `string`
- `why_not_to_overclaim`: `string`
- `evidence_ids`: `string[]`
- Keep the distinction between decision relevance and novelty explicit. A change may be new but still low relevance. A calm carryforward may still matter.
- Use `why_not_to_overclaim` to explain what the evidence does not justify.
- Keep `overall_verdict.boundary_note` honest about why this case does or does not deserve stronger public emphasis.
- Avoid long memo prose and avoid turning the ledger into a catch-all list.
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
