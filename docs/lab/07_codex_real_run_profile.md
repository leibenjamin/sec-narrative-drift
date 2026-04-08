# Codex Real Run Profile (8 Master Jobs - FY2024->FY2025 Cohort)

Last updated: 2026-04-06
Scope: `llm_outline_compare_structured` manual Codex jobs generated from
`reports/lab_llm_master_thread_starters_codex_real.md`.

Canonical starter policy:
- `reports/lab_llm_master_thread_starters_codex_real.md` is the single canonical Codex real-run starter file.
- It must be generated with `vscode_autowrite_structured_prod` profile (JOB_META + strict input hash/path/count lock + structured->runtime projection checks).
- Variant files such as `*_v2.md` or `*_legacy.md` are non-canonical and compatibility-only.

Companion canonical docs:
- `docs/lab/03_llm_precompute_workflow.md`
- `docs/lab/05_llm_reproducibility_contract.md`
- `docs/lab/09_master_run_troubleshooting_and_sources_of_truth.md`

Prompt source of truth:
- structured compare prompts live in:
  - `docs/lab/llm_master_compare_structured_system.md`
  - `docs/lab/llm_master_compare_structured_user_template.md`
  - `docs/lab/llm_master_compare_structured_self_check.md`
- casebook candidate prep uses:
  - `docs/lab/12_casebook_candidate_workflows.md`
  - `scripts/build_casebook_candidate_inputs_bundle.py`

Compatibility note:
- `prompt_templates_showcase.md` and `prompt_templates_showcase__<track_slug>.md` are compatibility-only files for older bundle tooling.
- They are not the canonical candidate-case prompt source and should not be used to prep `GOOGL`, `META`, `TSLA`, `UNH`, or `WMT`.

## Anchored Cohort Policy
- Current production cohort is frozen to FY2024->FY2025 for Core4 (`NVDA`, `KO`, `WM`, `GE`).
- Fiscal-year caveat: filings may be submitted in the next calendar year; year pairing follows fiscal years derived from `reportDate`/`filingDate`.
- FY2025->FY2026 remains an optional expansion lane and is not the default showcase cohort in this phase.

## Purpose
- Keep the current one-job-per-thread starter workflow unchanged for active production runs.
- Avoid schema drift and non-deterministic execution behavior.
- Add explicit batch governance so quality is tracked as jobs accumulate.

## Required Execution Profile
- `IDE context`: OFF
- `Plan Mode`: OFF
- model: `gpt-5.3-codex`
- reasoning effort: `xhigh`
- no manual file attachments when starter paths are intact.

## Per-Job Contract (Must Keep)
- Read exactly three inputs (`pair`, `year prev`, `year curr`) from workspace paths in the starter.
- Preflight counts must come from `texts.paragraphs` and must match `JOB_META.expected_prev_paragraphs` and `JOB_META.expected_curr_paragraphs`; mismatches are hard failures.
- Preflight must verify pair/year SHA256 locks and pair manifest linkage (`case`, `lens`, `year_inputs`) before generation.
- Emit exactly one preflight line:
  - `PRECHECK_OK ... prev_paragraphs=<N> curr_paragraphs=<N>`
- Write structured output JSON at canonical structured starter path.
- For large artifact writes on Windows, use a temporary workspace-relative generator script built in small chunks (`Set-Content` + `Add-Content`), execute it, then remove it.
- Project structured output deterministically to canonical runtime path.
- Run exactly three immediate checks:
  - JSON parse check
  - master validator (`--only-mode exact_path`, strict single-target flags) for structured
  - blocker quality audit for structured
  - projection command and runtime parse/validator checks
- Exact-path one-file validation and quality checks now default to scratch `_tmp_*` reports unless `--report` is explicitly set.
- Emit exactly one final status line.
- If a job fails with `preflight input lock mismatch`, check the lock report and troubleshooting doc before rerunning the same starter unchanged.

## Batch Governance Cadence
Run checkpoints every 6 jobs.

Required commands:
```bash
python scripts/lab_validate_llm_master_outputs.py --manifest "reports/lab_llm_master_manifest_codex_real.json" --campaign-id "openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27" --allow-missing --allow-invalid --report "reports/lab_llm_master_validation_codex_real.md"
python scripts/lab_audit_master_output_quality.py --manifest "reports/lab_llm_master_manifest_codex_real.json" --campaign-id "openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27" --allow-missing --mode blockers --strict-depth --report "reports/lab_llm_master_quality_codex_real_structured.md"
python scripts/lab_record_master_progress.py --manifest "reports/lab_llm_master_manifest_codex_real.json" --campaign-id "openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27" --report-md "reports/lab_llm_master_batch_progress_codex_real.md" --history-json "reports/lab_llm_master_batch_progress_codex_real.json" --label "after_job_XX"
python scripts/lab_build_llm_variants_index.py
python scripts/lab_runtime_readiness_check.py
```

Final checkpoint reminder:
- After completing job `8`, run the same progress command with:
  - `--label "after_job_8"`

Track these deltas after each checkpoint:
- `present`
- `invalid`
- `blockers`

## Quality Meaningfulness Policy
- Keep structure-aware 3-level outlines and explicit node alignment.
- Keep case-specific caveats tied to evidence limitations.
- Keep explicit mechanism fields (`driver -> exposure -> impact`, transmission channel, business effect, time horizon).
- For manual review, confirm:
  - top 3 material changes are mechanism-level shifts (not only lexical restatements),
  - at least one material change uses non-opening paragraph evidence from both years when feasible,
  - salience is not flat.

## Config Guidance
Recommended Codex profile for filing-only runs:
```toml
approval_policy = "on-failure"
network_access = "disabled"
web_search = "off"
personality = "pragmatic"
model = "gpt-5.3-codex"
model_reasoning_effort = "xhigh"

[features]
collaboration_modes = true
multi_agent = true
```

Notes:
- `collaboration_modes` may stay enabled globally, but do not turn on Plan Mode for execution threads.
- `multi_agent` may stay enabled globally, but do not use multi-agent inside one starter job thread.

Portable reproducibility export:
- `python scripts/lab_build_portable_master_run_pack.py --manifest reports/lab_llm_master_manifest_codex_real.json --campaign-id openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27 --out-dir bundles/portable_master_run_pack_v1 --clean`

## Non-Blocking Validation Note
During incremental manual production runs, `present_flag_mismatch` can appear when outputs are written but manifest `present` flags are not yet rebuilt. Treat this as non-blocking until manifest regeneration.

## Insight Promotion Criteria
Insight lane remains experimental until all of the following pass for a full campaign:
- `24/24` insight `master_output` artifacts present.
- Zero blocker audits for insight outputs and projected structured outputs.
- Runtime panel smoke checks pass, including explicit missing-state behavior when insight artifacts are absent.
