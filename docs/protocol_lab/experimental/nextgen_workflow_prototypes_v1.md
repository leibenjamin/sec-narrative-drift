# Next-Generation Workflow Prototypes v1

Status note:
- This file documents the original v1 experimental surface.
- The current run-ready prototype bundle defaults to `config/protocol_lab/experimental/nextgen_workflow_prototypes_v1_1.json`.
- Use the shared builder with `--manifest` when you need to rebuild the historical v1 packet deliberately.

This experimental surface defines the first two next-generation workflow families for Business Document Protocol Lab:

- `simple_read_vs_structured_read_contrast_v1`
- `decision_relevance_ledger_v1`

Shared implementation anchors:
- Program manifest: `config/protocol_lab/experimental/nextgen_workflow_prototypes_v1.json`
- Shared builder: `scripts/build_nextgen_workflow_prototypes_bundle.py`
- Prompt templates: `docs/protocol_lab/prompts/experimental/`
- Response schemas: `schemas/protocol_lab/experimental/`

Scope rules:
- Experimental only.
- No public route or runtime integration in this pass.
- Uses already materialized local tagged-input packets and emits a bundle for later Desktop execution and review.
