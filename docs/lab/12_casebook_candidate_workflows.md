# Casebook Candidate Workflows

Last updated: 2026-04-06

## Purpose

This document is the canonical source of truth for candidate-case LLM job preparation.
Use it when preparing `GOOGL`, `META`, `TSLA`, `UNH`, `WMT`, or future casebook candidates.

It exists to prevent one specific confusion:
- candidate-case prep must follow the active Business Document Protocol Lab workflows
- candidate-case prep must not drift back to archived SEC Narrative Drift legacy lanes

## Active Workflow Families

### 1. Outline Compare Structured

Active artifact chain:
- manual authoring artifact: `llm_outline_compare_structured`
- deterministic projection target: `llm_outline_compare_runtime`

Canonical prompt sources:
- `docs/lab/llm_master_compare_structured_system.md`
- `docs/lab/llm_master_compare_structured_user_template.md`
- `docs/lab/llm_master_compare_structured_self_check.md`

Canonical candidate bundle surface:
- `scripts/build_casebook_candidate_inputs_bundle.py`
- `bundles/showcase_llm_inputs_casebook_candidates_*/prompt_templates_casebook.md`

### 2. Protocol Lab Pilot Matrix

Active pedagogical cells:
- `p0`
- `p1`
- `p2`
- optional `p4`

Canonical prompt sources:
- `docs/protocol_lab/prompts/p0_plain_prompt_v1.md`
- `docs/protocol_lab/prompts/p1_structured_contract_v1.md`
- `docs/protocol_lab/prompts/p2_tagged_input_contract_v1.md`
- `docs/protocol_lab/prompts/p4_novelty_ledger_contract_v1.md`

Canonical runtime roots:
- `public/data/business_document_protocol_lab/pilot_matrices/<FIXTURE_ID>/`
- optional `public/data/business_document_protocol_lab/novelty_ledger/<FIXTURE_ID>/`

## Archived Workflow Families

These are archived and must not be treated as candidate-prep targets:
- `det_llm_delta_brief_v1`
- `det_llm_excerpt_picker_v1`

Archive-only helper surfaces that still exist for compatibility:
- `scripts/lab_make_llm_precompute_queue.py`
- `scripts/lab_make_pilot_pack.py`
- `scripts/lab_ingest_llm_outputs.py`
- `scripts/lab_validate_llm_outputs.py`
- `scripts/lab_validate_pilot_and_report.py`
- `scripts/lab_write_prompt_templates.py`
- `prompt_templates_showcase.md`

Those scripts now carry archive-facing warnings, but they still exist to support old detector-shaped flows. They are not the active path for casebook candidate prep.

## Component To Artifact Map

### `RiskNarrativeSummary`

Required:
- `llm_outline_compare_runtime`

Optional enrichers:
- `llm_outline_compare_structured` sidecar fields such as `evidence_bank`, `investor_relevance`, and `uncertainty_and_limits`

Meaning:
- no runtime artifact means no active filing-answer compare surface
- structured artifacts enrich the surface but do not replace runtime

### `OutlineComparePanel`

Required:
- `llm_outline_compare_runtime`

Optional enrichers:
- `llm_outline_compare_structured` sidecars for richer mechanism, risk-graph, investor-relevance, and limits views

Meaning:
- runtime compare is the hard dependency
- structured sidecars improve depth but are not the minimum render contract

### `ProtocolPreviewCard`

Required:
- Protocol Lab pilot matrix bundle under `public/data/business_document_protocol_lab/pilot_matrices/<FIXTURE_ID>/`

Optional support layers:
- novelty ledger
- effort robustness
- skeptic case

Meaning:
- the pilot matrix is the minimum second-layer protocol surface
- support layers deepen the read but are not the base requirement

## Current Visible Reference Cases

### `NVDA`

Uses:
- deterministic detector outputs
- `llm_outline_compare_structured`
- `llm_outline_compare_runtime`
- pilot matrix
- novelty ledger
- effort robustness

Role:
- vivid answer / strongest first signal

### `KO`

Uses:
- deterministic detector outputs
- `llm_outline_compare_structured`
- `llm_outline_compare_runtime`
- pilot matrix
- novelty ledger
- skeptic case

Role:
- useful restraint / low-drift honesty check

### `LLY`

Uses:
- deterministic detector outputs
- pilot matrix
- no integrated outline-compare runtime requirement on the bounded visible route

Role:
- policy-heavy honest-stop / bounded contrast

Meaning:
- Protocol Lab Pilot Matrix is enough for a minimum viable public case when the route is intentionally bounded and pedagogically honest.
- `llm_outline_compare_structured` is not mandatory for every public case.

## Minimum Viable Case Vs Full Case

### Minimum viable public case

Required:
- deterministic detector support
- casebook content and route framing
- Protocol Lab Pilot Matrix

Optional:
- outline compare structured/runtime

Use when:
- the case has a clear bounded teaching role
- the honest public route is protocol-first or boundary-first

### Full integrated public case

Required:
- deterministic detector support
- casebook content and route framing
- `llm_outline_compare_structured`
- deterministic projection to `llm_outline_compare_runtime`
- Protocol Lab Pilot Matrix

Use when:
- the case is strong enough to support both answer-first compare and protocol-layer teaching

## Input Provenance Guarantee

All LLM input files (pair manifests + year files) are produced entirely by deterministic Python scripts with no LLM pre-processing:

1. **Extraction**: `sec_extract_item1a.py` parses 10-K HTML from SEC EDGAR into plain text using rule-based HTML parsing. No LLM involved.
2. **Paragraph splitting**: `build_lab_outputs.py` splits text on double-newline boundaries and merges short fragments. Pure string operations.
3. **Deboilerplated lens**: `build_lab_outputs.py:build_deboilerplated_pair()` — a sentence-level exact-match set-difference between adjacent years. Each year's text is sentence-split, normalized (lowercased, whitespace-collapsed), and the shared set is removed. Only sentences unique to each year are retained. No LLM, no semantic similarity, no ML.
4. **Bundle assembly**: `build_casebook_candidate_inputs_bundle.py` writes pair manifests and year files with SHA256 integrity metadata. No content transformation.

This guarantee is critical to the Protocol Lab's validity: the LLM being evaluated sees the full filing text (or its deterministic deboilerplated subset), not a prior model's summary, outline, or interpretation. If a future pipeline step introduces any LLM pre-processing of inputs, it must be explicitly documented and the Protocol Lab's claims adjusted accordingly.

## Fiscal-Year Policy

Current standard:
- use the company-official fiscal-year designation derived from the filing/report-date convention already used in the app

Why this standard stays in force here:
- it is already how `NVDA` is labeled in the shipped product
- `WMT` is internally consistent when labeled `FY2025 vs FY2026`
- a switch to a “bulk of 12 months” convention would require repo-wide relabeling, not a quiet one-off exception

Affected candidate tickers:
- `GOOGL`: `FY2024 vs FY2025`
- `META`: `FY2024 vs FY2025`
- `TSLA`: `FY2024 vs FY2025`
- `UNH`: `FY2024 vs FY2025`
- `WMT`: `FY2025 vs FY2026`
- `NVDA`: `FY2024 vs FY2025`

Important current seam:
- candidate inputs for `WMT` are already corrected to `FY2025 vs FY2026`
- some older deterministic output filenames under `public/data/sec_narrative_drift_lab/WMT/outputs/` still use `2024_2025`
- that mismatch is documented and surfaced here; it is not silently normalized in this pass

If the project later adopts a “bulk of 12 months” convention, the migration would need:
- bundle filename relabeling
- pair-manifest relabeling
- deterministic output relabeling for January-fiscal companies
- doc and route-copy updates
- registry and report consistency checks across `NVDA`, `WMT`, and any other January fiscal-year issuers

## Candidate Job Matrix

| Case | Fiscal-year label | Outline Compare Structured | Protocol Lab Pilot Matrix | Deterministic detectors | Casebook content | Estimated pedagogic role | Candidate strength | Recommendation | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `NVDA` | `FY2024 vs FY2025` | existing reference | existing reference | complete shipped reference | present | vivid answer reference | reference anchor | no new jobs; use as calibration check | Already demonstrates the full integrated path and anchors fiscal-label consistency. |
| `GOOGL` | `FY2024 vs FY2025` | optional | required | present; signal is medium and partially thin | missing | policy-heavy restraint / governance-pressure candidate | medium | run pilot matrix first | No outline compare or pilot matrix exists yet, casebook copy is missing, and deterministic term signal is thinner than META/TSLA. Use pilot-matrix results to decide whether a fuller compare route is justified. |
| `META` | `FY2024 vs FY2025` | required | required | present; strong enough to justify full read | present | AI-governance / platform-risk full case | strong | run full outline compare + pilot matrix | Already has casebook framing, deterministic support is solid, and it is one of the strongest candidates for a full answer-plus-audit route. |
| `TSLA` | `FY2024 vs FY2025` | required | required | present; strong enough to justify full read | present | external-shock / execution-risk full case | strong | run full outline compare + pilot matrix | Existing content plus distinctive signal make this the other strong full-case candidate. |
| `UNH` | `FY2024 vs FY2025` | skip | skip | present but weak; low-confidence RBO and no distinctive terms | missing | hold / weak candidate | weak | hold until later | This is the weakest candidate in current deterministic evidence and has no casebook framing yet. It does not justify immediate LLM spend. |
| `WMT` | `FY2025 vs FY2026` | optional | required | present but filename labels are inconsistent | missing | tariff / retail-shock bounded candidate | medium | run pilot matrix first after label-aware review | Candidate inputs are corrected to official fiscal years, but the repo still has older `2024_2025` deterministic filenames. Pilot matrix first is the safest way to test whether the case earns a fuller route. |

Cases ready to evaluate after jobs:
- `META` after full outline compare + pilot matrix
- `TSLA` after full outline compare + pilot matrix
- `GOOGL` after pilot matrix first, then only full compare if the role becomes clear
- `WMT` after pilot matrix first and explicit fiscal-label consistency review

Not ready for immediate job spend:
- `UNH`

## Canonical Generation Path

Use this path for future candidate bundles:

```bash
python scripts/build_casebook_candidate_inputs_bundle.py --out-dir bundles/showcase_llm_inputs_casebook_candidates_<label>
python scripts/lab_publish_llm_inputs_v2.py --bundle bundles/showcase_llm_inputs_casebook_candidates_<label>
```

Do not use this path for candidate prep:

```bash
python scripts/build_showcase_llm_inputs_bundle.py
```

That older script remains in repo because other full-section pipeline steps still call it for input-pack compatibility, but it is not the canonical candidate-case job-prep path.

## Generated Manual Runs Layer

The candidate bundle generator now also emits:

- `bundles/showcase_llm_inputs_casebook_candidates_*/runs/`

Purpose:

- make manual ChatGPT Desktop execution easier for the next human
- group runs by case and by workflow
- provide one starter prompt and one attachment checklist per run
- provide one reusable tagged protocol packet per case

What it is:

- an operator convenience layer generated from the bundle inputs and canonical prompt docs

What it is not:

- not the canonical workflow definition
- not the final artifact schema
- not a hand-maintained packet that should drift independently

Use it when:

- you are manually running candidate jobs from a specific generated bundle in ChatGPT Desktop

Do not use it as the source of truth when:

- deciding what the active workflows are
- deciding what artifacts the app consumes
- changing fiscal-year policy
- changing job requirements or bundle composition

If `runs/` appears stale:

- regenerate the candidate bundle with `scripts/build_casebook_candidate_inputs_bundle.py`
- do not patch the run folders by hand unless you are only adding temporary operator notes outside version control
