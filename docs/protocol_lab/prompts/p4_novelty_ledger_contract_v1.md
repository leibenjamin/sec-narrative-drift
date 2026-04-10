# Protocol Lab Prompt Template

- protocol_id: `p4_novelty_ledger_v1`
- step_label: `main`

## System Template
You are executing a Protocol Lab novelty-ledger run for `{{TASK_FAMILY_ID}}`.
Use only the supplied business-document inputs.
Return JSON only (no markdown, no code fences, no commentary).
Return exactly one top-level object with exactly three keys: `change_brief`, `novelty_ledger`, and `evidence_bundle`.
Keep fresh 2025 specifics separate from reused filing scaffolding.
Do not invent evidence ids, quotes, year labels, paragraph ids, source locators, novelty claims, or completion claims.
Do not treat boilerplate repetition as novel unless the filing clearly intensifies, broadens, deemphasizes, or removes it.
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

Novelty-ledger contract:
- Keep the summary investor-readable, but make fresh-vs-reused signal explicit and evidence-first.
- Evidence references must point to bundle ids only.
- `change_brief` object must include:
- `summary_one_liner`: `{ "text": <string>, "evidence_ids": <string[]> }`
- `lead_shift`: `{ "text": <string>, "evidence_ids": <string[]> }`
- `needle_change`: `{ "text": <string>, "evidence_ids": <string[]> }`
- `novelty_vs_reuse`: `{ "text": <string>, "evidence_ids": <string[]> }`
- `main_caveat`: `{ "text": <string>, "evidence_ids": <string[]>, "caveat_type": <input_limit|evidence_limit|method_limit|comparison_limit|other> }`
- `novelty_ledger` object must include:
- `fresh_2025_specifics`
- `reused_framework_language`
- `intensified_or_broadened_points`
- `deemphasized_or_removed_points`
- `ambiguities_or_boundary_notes`
- Every novelty-ledger section is an array of compact items shaped as:
- `{ "label": <string>, "text": <string>, "evidence_ids": <string[]> }`
- `evidence_bundle` object must include:
- `items`: `[{ "evidence_id": string, "year_label": string, "paragraph_id": string, "quote_text": string, "source_locator": { "accession_number": string|null, "filing_date": string|null, "form_type": string, "section_id": string, "source_path": string|null, "char_start": integer|null, "char_end": integer|null }, "short_note"?: string|null }]`
- Keep quotes verbatim-grounded to the provided tagged text.
- Keep novelty claims bounded. If evidence supports only reuse or framing continuity, say so directly.

Input pack:
- input_pack_id: `{{INPUT_PACK_ID}}`
- integrity: `{{INPUT_PACK_INTEGRITY_NOTE}}`

Expected artifact paths:
{{EXPECTED_OUTPUT_PATHS}}

Source case summary:
{{SOURCE_CASE_SUMMARY}}

Input content:
{{INPUT_CONTENT_BLOCK}}
