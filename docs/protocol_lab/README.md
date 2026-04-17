# Protocol Lab Namespace

## What this namespace is
This is the active authoring and runtime namespace for Document Protocol Lab, the interactive casebook that compares approaches to business-document reading with frontier LLMs. Product-level framing lives in `docs/PRODUCT_STORY.md` and architecture in `docs/LAB_ARCHITECTURE_AND_GOALS.md`; this document is the internal reference for namespace, registry, and artifact-contract rules.

`config/protocol_lab/*.json` is the authoring truth for Protocol Lab registry content.
`public/data/business_document_protocol_lab/registries/*.json` is the runtime mirror and should stay aligned with the source registries.

## Approach catalog (live vs authored)
Three approaches are live across the public casebook, each with authored pilot-matrix cells:
- `p0_plain_prompt_v1` — plain-prompt baseline (control).
- `p1_structured_contract_v1` — structured contract (typically the primary read).
- `p2_tagged_input_contract_v1` — tagged input contract (comparator).

`p4_novelty_ledger_contract_v1` is available on a subset of cases as a deeper structural comparison.

`p3_extract_then_synthesize_v1` has a prompt template and is referenced by artifact contracts below, but has no authored cell data in any public case. It is not claimed as a live approach on the product surface. Artifact-contract rules that reference `p3` apply only if a run is eventually executed; they do not imply the approach is shipped.

Prompt templates live in `docs/protocol_lab/prompts/`.

## Control-plane and artifact-contract rules

Wave 4A / 4A.5 control-plane rules:
- `artifact_status` is artifact lifecycle and scaffold state only. It is not a readiness field.
- Canonical readiness is split into `availability_status`, `extraction_quality_status`, and `analysis_readiness_status`.
- `availability_status` answers whether required source paths exist.
- `extraction_quality_status` answers whether the extracted section is trustworthy enough to analyze.
- `analysis_readiness_status` answers whether the source case can participate in substrate review, pilot ablations, or matrix work.
- Legacy combined `status` fields are compatibility-only derived shims and must not be treated as canonical readiness.
- Fixture registry items may also carry `fixture_role` so sentinel or roster intent is not collapsed back into readiness.
- Protocols own `default_input_pack_id` only. Experiment cells and run requests may select an effective input pack without changing the protocol design itself.
- Stacks remain protocol-plus-model only. Concrete pack selection lives at the experiment-cell and run-request layers.
- Model profiles are stable product-level identities. Concrete local campaign bindings live in `runner_bindings_local_v1`.
- `input_pack_v1` may either inline `rendered_inputs` or reference an external payload with `rendered_inputs_path` when the payload is too large to keep inside the manifest.
- `run_request_v1.execution_status` remains a coarse compatibility field in Wave 4B. Canonical detailed run-state now lives in `execution_trace_v1.run_state`.

Wave 4A.5 readiness and QC rules:
- Allowed `availability_status` values: `missing`, `partial`, `available`.
- Allowed `extraction_quality_status` values: `not_assessed`, `failed`, `review_required`, `acceptable`.
- Allowed `analysis_readiness_status` values: `blocked`, `substrate_only`, `pilot_ready`, `matrix_ready`.
- `source_case_manifest_v1` now carries `qc_summary` both at the top level and inside each `years[]` entry.
- `qc_summary` captures `quality_gate_result`, `confidence_band`, `paragraph_count_plausibility`, `severe_warning_flags`, and `readiness_derivation_note`.
- `analysis_readiness_status = matrix_ready` is intentionally strict: it requires pilot readiness plus deterministic support for the topology-specific `i3_extractive_evidence_packet_v1` lane.
- `i3_extractive_evidence_packet_v1` is not a universal prerequisite. It is required only for `p3_extract_then_synthesize_v1` and experiments that intentionally test extractive topology.
- ASML-style hard-fail signals such as `quality_gate_failed`, `risk_too_short`, implausibly low paragraph counts, or very low extraction confidence must block analysis readiness even when raw source files exist.

Wave 4A.5 comparison rules:
- Canonical NVDA comparison geometry now lives in four ablation sets: `nvda_ablation_contract_v1`, `nvda_ablation_filtering_v1`, `nvda_ablation_tag_awareness_v1`, and `nvda_ablation_topology_v1`.
- Legacy `pilot_matrix_a_nvda_protocols_v1` and `pilot_matrix_b_nvda_interaction_v1` remain as deprecated compatibility-only surfaces.
- `comparison_view_v1` now requires explicit `comparison_purpose`, `comparison_verdict`, and `delta_ledger` fields so the future UI can render comparisons directly without inferring deltas from notes.
- `pairwise_findings` should point at explicit `delta_ids` rather than relying on prose-only interpretation.

Section naming rules:
- `item_1a` is the canonical internal section id for 10-K Risk Factors.
- `item_3d` is the canonical internal section id for 20-F Risk Factors.
- Pair folder ids may keep `item1a` or `item3d` in the fixture slug for stable external naming, but internal `section_id` stays underscored.
- Current sentinel helper exports may still emit legacy `10k_item1a`-named local report files even when the underlying cache extraction is `20-F/item_3d`; treat those helper exports as reference-only.

Strict new-only run rule:
- A Protocol Lab run only counts as real when it is executed and captured inside the `business_document_protocol_lab` namespace.
- Legacy `sec_narrative_drift_lab` outputs can be cited in notes or review materials, but they do not become Protocol Lab outputs by copy or relabeling.

Wave 4B lineage and reviewability rules:
- Prompt source-of-truth now lives under `docs/protocol_lab/prompts/`.
- `prompt_render_v1` is the canonical rendered-prompt artifact. It records the exact system and user prompt bodies generated for a run or step.
- `execution_trace_v1` is the canonical detailed execution-state artifact. Wave 4C1.5 active generation now uses `awaiting_capture`, `capture_missing`, `captured`, `parse_failed`, `validated`, and `reviewed`; legacy values such as `scaffolded`, `rendered`, `submitted`, `completed`, and `postprocess_failed` remain schema-accepted for historical compatibility only.
- `artifact_status` continues to mean artifact completeness or scaffold state only. It is not execution state and it is not readiness.
- Raw model responses are local-only audit material under `reports/protocol_lab/raw_runs/...` even when lineage metadata lives under `public/data/business_document_protocol_lab/runs/...`.
- `evidence_resolution_v1` is a deterministic audit artifact for evidence-id resolution and locator or quote checks. It is separate from `change_brief_eval_v1` in Wave 4B.
- Multi-step lineage is step-scoped. `p3_extract_then_synthesize_v1` stores prompt renders and execution traces under `runs/<fixture>/<run_id>/steps/<step_label>/`.

Stage 3 and Wave 4A scope:
- Control plane and artifact contracts only.
- No app-shell redesign.
- No legacy page refactor.
- No broad fixture backfills.
- No silent mutation of unrelated legacy surfaces.

Wave 4C1.75 local-only capture note:
- `capture_receipt_v1.json` and `capture_validation_report_v1.json` under `reports/protocol_lab/raw_runs/...` are local audit artifacts only and are never runtime-public dependencies.
