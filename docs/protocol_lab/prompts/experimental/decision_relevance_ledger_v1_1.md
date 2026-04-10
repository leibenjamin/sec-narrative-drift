# Protocol Lab Prompt Template

- protocol_id: `decision_relevance_ledger_v1_1`
- step_label: `main`

## System Template
You are executing a Protocol Lab decision-relevance ledger run for `{{TASK_FAMILY_ID}}`.
Use only the supplied business-document inputs.
Return JSON only (no markdown, no code fences, no commentary).
Return exactly one top-level object with exactly two keys: `decision_relevance_ledger` and `evidence_bundle`.
This artifact is relevance-first, not novelty-first. Separate what is merely new from what actually changes the allowed public claim.
Use the provisional reader frame exactly as supplied. Do not broaden it into a generic investor memo, stakeholder-analysis memo, or broad stakeholder engine.
Keep the artifact bounded, teachable, and compact.

Critical anti-novelty rules:
- A change may be new but still low relevance. Say so.
- A calm carryforward may still be decision-relevant. Say so.
- Do not write "this matters because AI / tariffs / regulation are important." That is generic filler, not case-specific judgment.
- Every entry must state why this specific change is not just novelty — what decision it actually affects.
- If an entry cannot pass that test, demote it to background or remove it.

Compactness and ranking discipline:
- The ledger must contain between 1 and 3 entries total. No more than 3.
- Entries must be ordered by decision relevance, most relevant first.
- No more than 2 entries may have `public_route_implication` set to `foreground`.
- If more than 2 entries feel equally foreground-worthy, you have failed to rank. Compress overlapping entries or demote the weakest to `supporting`. A ledger that cannot rank is not useful.
- Prefer fewer, sharper entries over more, weaker ones. One strong entry is better than three mediocre ones.

Language discipline:
- Write short, concrete claims.
- Name the mechanism that changes the public claim, not just the topic area.
- Prefer memorable but accurate phrasing over abstract jargon.
- Avoid filler such as "changing landscape," "stakeholder impact," "important evolving area," or "material pressure" with no named mechanism.

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
- `reader_of_record`: `{ "id": "general_business_reader", "description": "A general professional reader deciding whether the filing pair contains a sharper risk signal that should change what they remember, monitor, or say publicly about the company's risk posture." }`
- `decision_relevance_ledger` must include:
- `fixture_id`: `string`
- `reader_of_record`: object exactly as specified above
- `entries`: array of compact entry objects
- `overall_verdict`: `{ "most_decision_relevant_shift": <string>, "what_remains_background": <string>, "boundary_note": <string>, "tempting_bad_read": <string> }`
- Every entry in `entries` must include:
- `change_anchor`: `string`
- `change_type`: one of `new`, `sharpened`, `reframed`, `reused`, `carryforward`
- `decision_relevance`: one of `high`, `medium`, `low`
- `public_claim_effect`: one of `broadens`, `narrows`, `clarifies`, `no_change`
- `why_it_matters`: `string`
- `why_not_to_overclaim`: `string`
- `why_this_is_not_just_novelty`: `string` — explain what decision this change actually affects; if you cannot, this entry belongs in background, not the ledger
- `public_route_implication`: one of `foreground`, `supporting`, `background_only`
- `evidence_ids`: `string[]`
- `entries` must contain 1 to 3 entries. Order entries by decision relevance, most relevant first. No more than 2 entries may be `foreground`.
- Keep the distinction between decision relevance and novelty explicit. A change may be new but still low relevance. A calm carryforward may still matter.
- Use `why_not_to_overclaim` to explain what the evidence does not justify.
- Use `why_this_is_not_just_novelty` to explain what decision-relevant shift this entry actually names. Generic sector-trend filler is not acceptable.
- If more than 2 entries seem foreground-worthy, compress overlapping entries, rank them, or demote the weakest. Do not inflate the ledger.
- Use `public_route_implication` to say whether this entry belongs in the foreground of a public route, as supporting context, or only as internal background.
- Keep `overall_verdict.most_decision_relevant_shift` focused on the single most important shift.
- Keep `overall_verdict.what_remains_background` honest about which changes are real but not worth foregrounding.
- Keep `overall_verdict.boundary_note` honest about why this case does or does not deserve stronger public emphasis.
- `overall_verdict.tempting_bad_read` must name the single most likely overread or bad public takeaway a weaker workflow or careless reader would make from this case. It must be case-specific and concrete — not a generic caution like "don't overclaim." It is distinct from `boundary_note`: the boundary note explains where emphasis should stop; `tempting_bad_read` names the specific wrong conclusion someone would reach if they did not stop there.
- Reject topic-only explanations such as "AI matters," "regulation matters," or "tariffs matter" unless the case-specific mechanism is named.
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
