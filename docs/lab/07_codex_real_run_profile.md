# Codex Real Run Profile (24 Master Jobs)

Last updated: 2026-03-02
Scope: `llm_outline_compare_v1` manual Codex jobs generated from
`reports/lab_llm_master_thread_starters_codex_real.md`.

Canonical starter policy:
- `reports/lab_llm_master_thread_starters_codex_real.md` is the single canonical Codex real-run starter file.
- It must be generated with `vscode_autowrite_v3` profile (JOB_META + strict preflight count lock).
- Variant files such as `*_v2.md` or `*_legacy.md` are non-canonical and compatibility-only.

Companion canonical docs:
- `docs/lab/03_llm_precompute_workflow.md`
- `docs/lab/05_llm_reproducibility_contract.md`

Prompt template pairing (full_section_v2 bundle):
- Primary Codex: `prompt_templates_showcase.md`
- Compare ChatGPT: `prompt_templates_showcase__openai-chatgpt52ext-agent-fullsec-real-2026-02-27.md`

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
- Preflight counts must come from `year_payload.texts.paragraphs` and must match `JOB_META.expected_prev_paragraphs` and `JOB_META.expected_curr_paragraphs`; mismatches are hard failures.
- Emit exactly one preflight line:
  - `PRECHECK_OK ... prev_paragraphs=<N> curr_paragraphs=<N>`
- Write exactly one output JSON at the canonical starter path.
- Run exactly three immediate checks:
  - JSON parse check
  - master validator (`--only-mode exact_path`, strict single-target flags)
  - blocker quality audit
- Emit exactly one final status line.

## Batch Governance Cadence
Run checkpoints every 6 jobs.

Required commands:
```bash
python scripts/lab_validate_llm_master_outputs.py --manifest "reports/lab_llm_master_manifest_codex_real.json" --campaign-id "openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27" --allow-missing --allow-invalid --report "reports/lab_llm_master_validation_codex_real.md"
python scripts/lab_audit_master_output_quality.py --manifest "reports/lab_llm_master_manifest_codex_real.json" --campaign-id "openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27" --allow-missing --mode blockers --report "reports/lab_llm_master_quality_codex_real.md"
python scripts/lab_record_master_progress.py --manifest "reports/lab_llm_master_manifest_codex_real.json" --campaign-id "openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27" --report-md "reports/lab_llm_master_batch_progress_codex_real.md" --history-json "reports/lab_llm_master_batch_progress_codex_real.json" --label "after_job_XX"
```

Final checkpoint reminder:
- After completing job `24`, run the same progress command with:
  - `--label "after_job_24"`

Track these deltas after each checkpoint:
- `present`
- `invalid`
- `blockers`

## Quality Meaningfulness Policy
- Keep structure-aware 3-level outlines and explicit node alignment.
- Keep case-specific caveats tied to evidence limitations.
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

## Non-Blocking Validation Note
During incremental manual production runs, `present_flag_mismatch` can appear when outputs are written but manifest `present` flags are not yet rebuilt. Treat this as non-blocking until manifest regeneration.
