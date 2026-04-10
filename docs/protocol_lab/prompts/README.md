# Protocol Lab Prompt Templates

These files are the canonical prompt source for Protocol Lab prompt rendering
and next-generation prototype bundle generation.

Format rules:
- Each file is Markdown.
- Each file must contain exactly one `## System Template` section and one `## User Template` section.
- The renderer replaces `{{PLACEHOLDER}}` tokens directly and fails if any placeholder is left unresolved.
- `main` is the implied step label for single-pass protocols.
- Multi-step protocols use explicit step labels in the filename.

Core committed templates:
- `p0_plain_prompt_v1.md`
- `p1_structured_contract_v1.md`
- `p2_tagged_input_contract_v1.md`
- `p3_extract_then_synthesize_v1__step_1_extract_evidence.md`
- `p3_extract_then_synthesize_v1__step_2_synthesize_change_brief.md`
- `p4_novelty_ledger_contract_v1.md`

Experimental committed templates:
- `experimental/simple_read_vs_structured_read_contrast_v1.md`
- `experimental/decision_relevance_ledger_v1.md`

Notes:
- `config/protocol_lab/protocols_v1.json` and `config/protocol_lab/stacks_v1.json` remain the source of truth for stable protocol ids and bindings.
- The `experimental/` prompt docs are backstage research surfaces only. They define prototype bundles for later Desktop execution and do not imply public-route integration.
