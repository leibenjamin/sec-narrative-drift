# SEC Narrative Drift Lab - Remaining Work Plan (Active)

Last updated: 2026-03-03
Scope: active canonical work only (deterministic runtime + master-v2 manual runs with runtime-v1 projection).

## Decision-Locked Runtime Truth
- Runtime pair scope is fixed to FY2022+ adjacent pairs only:
  - `NVDA`, `KO`, `WM`, `GE` x `2022-2023`, `2023-2024`, `2024-2025`.
- Runtime policy is real-run LLM evidence only:
  - primary runtime-visible campaign: `openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27`
  - compare-default campaign remains hidden pending strict-valid completion: `openai_chatgpt52ext_agent_fullsec_real_2026-02-27`
  - synthetic campaigns (`*_fullsec_2026-02-22`) and focuspack campaigns are audit-only/runtime-hidden.
- Canonical manual authoring unit is `llm_outline_compare_v2` (`24` jobs per campaign: `12` pairs x `2` lenses).
- Runtime compatibility unit remains `llm_outline_compare_v1`, produced by deterministic `v2 -> v1` projection.
- Legacy detector envelopes (`det_llm_delta_brief_v1`, `det_llm_excerpt_picker_v1`) remain deterministic projections from runtime v1 outputs.

## Hard Constraints (Must Hold)
- No runtime LLM/ML calls in shipped app.
- No changes to public JSON schemas or detector envelope keys without explicit governance unlock.
- SEC-derived text is untrusted and must never be rendered as HTML.
- Keep deterministic-first behavior with explicit missing/debug states whenever LLM sidecars are absent.

## Current State Snapshot
- Canonical starter hardening is active (`vscode_autowrite_v4`, JOB_META, strict input hash/path/count lock, forbidden-source policy).
- Prompt-template hardening is campaign-scoped:
  - primary codex template: `prompt_templates_showcase.md`
  - compare chatgpt template: `prompt_templates_showcase__openai-chatgpt52ext-agent-fullsec-real-2026-02-27.md`
- Full-section v2 inputs for all runtime pairs/lenses are available locally.
- Codex real and ChatGPT real master manifests/instructions/starters are generated and maintained with `master_output` (v2) and `projected_master_output_v1` targets.
- Runtime can surface projected outline compare artifacts when present and falls back to explicit deterministic-first missing states when absent.

## Remaining Work (Operational)
1. Complete Codex real manual jobs (`24` total), checkpointing every 6 jobs.
2. Complete ChatGPT real manual jobs (`24` total) and hold runtime visibility until strict-valid coverage is achieved.
3. Run campaign-level validation + blocker quality audits at each checkpoint:
   - `scripts/lab_validate_llm_master_outputs.py`
   - `scripts/lab_audit_master_output_quality.py`
   - `scripts/lab_record_master_progress.py`
4. Keep docs/checkers/tests aligned to canonical starter and campaign truth whenever campaign metadata or run profile changes.
5. Keep `llm_outline_compare_v2` outputs local during active production waves unless explicitly approved for publication.

## Required Gates After Build/Data Logic Changes
- `npm run lab:predeploy`
- `npm run lab:readiness`
- `npm run build`

## Historical Execution Record
Superseded phase narratives and prior one-shot execution prompts were moved to:
- `docs/lab/08_remaining_work_plan_history.md`

That file is archival context only and is not the active execution source of truth.
