# SEC Narrative Drift Lab - Remaining Work Plan (Active)

Last updated: 2026-03-05
Scope: active canonical work only (deterministic runtime + master-structured manual runs with runtime projection).

## Decision-Locked Runtime Truth
- Runtime pair scope is anchored to FY2024->FY2025 for Core4 (`NVDA`, `KO`, `WM`, `GE`) in the current showcase cohort.
- Fiscal-year caveat: annual filings may be filed in the next calendar year; pairing follows fiscal years derived from `reportDate`/`filingDate`.
- Expansion path: FY2025->FY2026 can be added as an explicit additional cohort when released coverage is broad enough.
- Runtime policy is real-run LLM evidence only:
  - primary runtime-visible campaign: `openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27`
  - compare-default campaign remains hidden pending strict-valid completion: `openai_chatgpt52ext_agent_fullsec_real_2026-02-27`
  - compare-lane lineage note: campaign id token stays `chatgpt52ext` for path continuity; active manual model is `ChatGPT 5.4-Thinking (Extended Thinking)` and new run labels use `chatgpt54ext`.
  - synthetic campaigns (`*_fullsec_2026-02-22`) and focuspack campaigns are audit-only/runtime-hidden.
- Canonical manual authoring unit is `llm_outline_compare_structured` (`8` jobs per campaign in current Core4 FY2024->FY2025 anchored scope: `4` pairs x `2` lenses).
- Runtime compatibility unit remains `llm_outline_compare_runtime`, produced by deterministic `structured -> runtime` projection.
- Legacy detector envelopes (`det_llm_delta_brief_v1`, `det_llm_excerpt_picker_v1`) remain deterministic projections from runtime outputs.

## Hard Constraints (Must Hold)
- No runtime LLM/ML calls in shipped app.
- No changes to public JSON schemas or detector envelope keys without explicit governance unlock.
- SEC-derived text is untrusted and must never be rendered as HTML.
- Keep deterministic-first behavior with explicit missing/debug states whenever LLM sidecars are absent.

## Current State Snapshot
- Canonical starter hardening is active (`vscode_autowrite_structured_prod`, JOB_META, strict input hash/path/count lock, forbidden-source policy).
- Prompt-template hardening is campaign-scoped:
  - primary codex template: `prompt_templates_showcase.md`
  - compare chatgpt template: `prompt_templates_showcase__openai-chatgpt52ext-agent-fullsec-real-2026-02-27.md`
- Full-section v2 inputs for all runtime pairs/lenses are available locally.
- Codex real and ChatGPT real master manifests/instructions/starters are generated and maintained with `master_output` (`llm_outline_compare_structured` in production lane) and `projected_master_output_runtime` targets.
- Runtime can surface projected outline compare artifacts when present and falls back to explicit deterministic-first missing states when absent.

## Remaining Work (Operational)
1. Complete Codex real manual jobs (`8` total in current Core4 FY2024->FY2025 anchored scope), checkpointing every 6 jobs.
2. Complete ChatGPT real manual jobs (`8` total in current Core4 FY2024->FY2025 anchored scope) and hold runtime visibility until strict-valid coverage is achieved.
3. Run campaign-level validation + blocker quality audits at each checkpoint:
   - `scripts/lab_validate_llm_master_outputs.py`
   - `scripts/lab_audit_master_output_quality.py`
   - `scripts/lab_record_master_progress.py`
4. Keep docs/checkers/tests aligned to canonical starter and campaign truth whenever campaign metadata or run profile changes.
5. Keep `llm_outline_compare_structured` outputs local during active production waves unless explicitly approved for publication.

## Required Gates After Build/Data Logic Changes
- `npm run lab:predeploy`
- `npm run lab:readiness`
- `npm run build`

## Historical Execution Record
Superseded phase narratives and prior one-shot execution prompts were moved to:
- `docs/lab/08_remaining_work_plan_history.md`

That file is archival context only and is not the active execution source of truth.



## Rename Governance Unlock (Approved)
- Big-bang role-based naming cutover is approved for this wave.
- Production lane remains structured (llm_outline_compare_structured -> llm_outline_compare_runtime).
- Insight lane (llm_outline_compare_insight) remains experimental until explicit promotion criteria are met.



## Insight Lane Promotion Criteria
- Promotion candidate remains `llm_outline_compare_insight` (experimental lane only until all checks pass).
- Required objective gate before production promotion:
  - `24/24` insight `master_output` artifacts present for the campaign,
  - zero blocker audits for both insight outputs and projected structured outputs,
  - runtime UI smoke validation passes with deterministic missing-state behavior when insight artifacts are absent.





