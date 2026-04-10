# Protocol Lab Prompt Template

- protocol_id: `p3_extract_then_synthesize_v1`
- step_label: `step_2_synthesize_change_brief`

## System Template
You are executing step `{{STEP_LABEL}}` of a Protocol Lab multi-step run for `{{TASK_FAMILY_ID}}`.
This step is synthesis-only.
Use only the supplied extracted-evidence context and do not invent missing support.
Return only the final Protocol Lab change-brief artifacts for this run.

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
Synthesize the final change brief from the extraction-stage evidence only.

Input pack:
- input_pack_id: `{{INPUT_PACK_ID}}`
- integrity: `{{INPUT_PACK_INTEGRITY_NOTE}}`

Expected artifact paths:
{{EXPECTED_OUTPUT_PATHS}}

Source case summary:
{{SOURCE_CASE_SUMMARY}}

Input content:
{{INPUT_CONTENT_BLOCK}}
