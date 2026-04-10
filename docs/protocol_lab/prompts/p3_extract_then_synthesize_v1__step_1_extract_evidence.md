# Protocol Lab Prompt Template

- protocol_id: `p3_extract_then_synthesize_v1`
- step_label: `step_1_extract_evidence`

## System Template
You are executing step `{{STEP_LABEL}}` of a Protocol Lab multi-step run for `{{TASK_FAMILY_ID}}`.
This step is extraction-only.
Identify and preserve candidate evidence without synthesizing the final change brief.
Do not invent evidence ids, quotes, year labels, paragraph ids, source locators, or completion claims.

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
- step_label: `{{STEP_LABEL}}`

Multi-step objective:
Extract candidate evidence for a later synthesis step while keeping the extraction stage auditable.

Input pack:
- input_pack_id: `{{INPUT_PACK_ID}}`
- integrity: `{{INPUT_PACK_INTEGRITY_NOTE}}`

Expected artifact paths:
{{EXPECTED_OUTPUT_PATHS}}

Source case summary:
{{SOURCE_CASE_SUMMARY}}

Input content:
{{INPUT_CONTENT_BLOCK}}
