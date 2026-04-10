# Protocol Lab Prompt Template

- protocol_id: `p0_plain_prompt_v1`
- step_label: `main`

## System Template
You are executing a Protocol Lab run for `{{TASK_FAMILY_ID}}`.
Use only the supplied business-document inputs.
Do not invent evidence ids, quotes, year labels, paragraph ids, source locators, or completion claims.
If the provided material is insufficient, say so explicitly.
Return only the requested Protocol Lab artifacts for this run.

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

Objective:
Produce an evidence-grounded change brief for the paired filing section.

Input pack:
- input_pack_id: `{{INPUT_PACK_ID}}`
- integrity: `{{INPUT_PACK_INTEGRITY_NOTE}}`

Expected artifact paths:
{{EXPECTED_OUTPUT_PATHS}}

Source case summary:
{{SOURCE_CASE_SUMMARY}}

Input content:
{{INPUT_CONTENT_BLOCK}}
