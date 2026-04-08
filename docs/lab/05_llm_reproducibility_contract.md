# LLM Reproducibility Contract (Lab)

This contract defines the canonical manual LLM run standard for SEC Narrative Drift Lab.

## Objectives
- Reproducible manual runs across operators and threads.
- Save-ready JSON with deterministic validation and projection.
- Clear provenance for model-versus-model comparison.

## Canonical Manual Authoring Unit
- Canonical manual authoring artifact: `llm_outline_compare_structured`
- Deterministic runtime projection artifact: `llm_outline_compare_runtime`
- Experimental optional artifact: `llm_outline_compare_insight`

`llm_outline_compare_structured` is the only canonical manual authoring unit for the current shipped compare experience.

## Active Scope
- Active shipped scope is FY2024 -> FY2025 only for `NVDA`, `KO`, `WM`, and `GE`.
- Campaign identity and output paths remain track-aware and stable.
- Active compare-visible ChatGPT campaign is `openai_chatgpt54ext_agent_fullsec_real_2026-03-06`.
- Archived compatibility-only ChatGPT real identity is `openai_chatgpt52ext_agent_fullsec_real_2026-02-27`.
- Pre-registered hidden workspace-aware Claude lane is `anthropic_claudeopus46_claudecode_fullsec_real_2026-03-09`.

## Manual Input Contract

### Input provenance
All three input files attached to each LLM job are produced entirely by deterministic Python scripts with no LLM involvement:
- **Extraction**: `sec_extract_item1a.py` parses 10-K HTML from SEC EDGAR into plain text (rule-based HTML parsing).
- **Paragraph splitting**: `build_lab_outputs.py` splits on double-newline boundaries and merges short fragments.
- **Deboilerplated lens**: `build_deboilerplated_pair()` removes sentences shared verbatim between both years via normalized exact-match set-difference. No semantic similarity or ML.
- **Bundle assembly**: pair manifests and year files are written with SHA256 integrity metadata.

The LLM being evaluated receives the full filing text (or its deterministic deboilerplated subset), never a prior model's interpretation.

### Input file contract
Each outline-compare job uses exactly three input JSON files:
- pair manifest
- year prev input
- year curr input

The pair manifest is the canonical `provenance.input_file` target:
- `inputs/pair/<TICKER>_<YEAR_FROM>_<YEAR_TO>_10k_item1a_<LENS>_edgar.json`

The pair manifest must resolve its year files through:
- `year_inputs.prev`
- `year_inputs.curr`

Optional local-only pair-manifest metadata may also be present for hard cases:
- `analysis_expectations.focus_signals`

This field is for manual run hardening and audit enforcement only. It is not part of any shipped compare artifact schema.

Each focus signal may declare:
- stable `id`
- `priority`
- `paragraph_hints`
- `anchor_groups`
- `surface_requirements`

## Output Handling by Venue

### Workspace-Aware Agents
If the model has direct workspace access, it may write the structured artifact directly to its canonical output path and then run deterministic validation and projection.

Workspace-aware campaigns include Codex and Claude Code lanes that read starter-declared workspace paths.

If operators export those starter/input files outside the original workspace, they must update the workspace-relative file paths before rerun.

### ChatGPT Desktop or Non-Workspace Clients
If the model does not have direct workspace access, it must not claim to write files itself.

It must instead:
- return the final JSON object in-chat, or
- return a downloadable JSON file when the client supports file output.

The operator then saves that JSON to the canonical structured output path before running local validation and projection.

## Structured Artifact Contract (`llm_outline_compare_structured`)
Required top-level keys:
- `lab_schema_version`
- `artifact_schema_version`
- `artifact_id`
- `ticker`
- `section`
- `source_id`
- `cleaning_lens`
- `year_from`
- `year_to`
- `outline_prev`
- `outline_curr`
- `node_alignment`
- `material_changes`
- `evidence_bank`
- `lens_divergence`
- `risk_graph_prev`
- `risk_graph_curr`
- `change_mechanisms`
- `uncertainty_and_limits`
- `investor_relevance`
- `projection_contract`
- `provenance`

Hard requirements:
- `artifact_id` must be exactly `llm_outline_compare_structured`.
- `lab_schema_version` and `artifact_schema_version` must be `1.0`.
- `node_alignment.change_class` must be one of:
  - `added`, `removed`, `moved`, `split`, `merged`, `reworded`, `intensified`, `softened`, `stable`
- `projection_contract.projects_to_artifact_id` must be `llm_outline_compare_runtime`.
- `risk_graph_prev` and `risk_graph_curr` must encode explicit `driver -> exposure -> impact` rows.
- Every `change_mechanisms` row must include `mechanism`, `transmission_channel`, `business_effect`, and `time_horizon`.
- Every evidence reference used in material changes, change mechanisms, limits, or investor relevance must resolve to an `evidence_bank` entry.

## Runtime Projection Contract (`llm_outline_compare_runtime`)
- Runtime compare artifacts are deterministic projections of structured artifacts.
- Runtime fields shared with structured must match their structured source exactly.
- Any runtime artifact without a resolvable structured source is invalid.
- Runtime projection is deterministic post-processing; it is not a second model run.

## Evidence Contract
- All paragraph indices are full-year paragraph indices.
- For `full_section_v2`, `paragraph_idx` is the direct full index from the year input arrays.
- Evidence snippets must be contiguous verbatim substrings of the mapped paragraph text.
- Evidence snippets must be `<=350` chars.
- If the mapped paragraph is longer than `350` chars, the snippet must be a contiguous trimmed substring that preserves the mechanism under discussion.
- Synthetic ellipses or edited snippets are not allowed.
- Evidence blocks must be sorted by `(year, paragraph_idx)` ascending.
- Duplicate evidence blocks with the same `(year, paragraph_idx)` are not allowed.
- Avoid page-number prefix artifacts at snippet starts unless required for fidelity.
- For raw-lens outputs, only `material_changes.title` and outline `label` fields may lightly normalize obvious extraction artifacts; evidence text and evidence-bearing prose remain verbatim-grounded only.

## Analytical Depth Gate (`--strict-depth`)
Strict-depth blockers for `llm_outline_compare_structured`:
- `material_changes` must have at least `4` rows.
- Use distinct evidence coverage across years when paragraph counts are high enough to support it.
- Include at least one top-ranked non-opening-paragraph material change when available.
- Avoid shallow opening-paragraph concentration.

## Focus-Signal Gate
When the pair manifest provides `analysis_expectations.focus_signals`:
- Required signal surfacing is evaluated on surfaced analytical sections, not evidence-bank presence alone.
- Surfacing must satisfy any required rank or section constraints declared in the focus signal.
- Signals are starter/audit hardening inputs only; they do not create new shipped schema fields.
- `analysis_expectations.paragraph_hints` must stay in range for the linked prev/curr year files; canonical bundle, starter, and lock-verification flows now fail fast when they do not.

## Provenance Contract
- `provenance.input_file` must match the canonical pair-manifest path.
- `provenance.model_provider` and `provenance.model_name` must match the selected campaign exactly.
- `provenance.run_label` must start with `YYYY-MM-DD_`.
- Day precision is mandatory for truthful public run history and campaign comparison.

## Source-of-Truth Reminder
If a rerun unexpectedly fails preflight on counts or SHA locks, treat that as a source-of-truth problem first, not a model-quality problem first. Use `scripts/lab_verify_master_input_locks.py` and `docs/lab/09_master_run_troubleshooting_and_sources_of_truth.md` before rerunning the same starter unchanged.
