# SEC Narrative Drift Lab - Remaining Work Plan (Active)

Last updated: 2026-03-10

Scope: active canonical work only (deterministic runtime + structured manual outline-compare runs + deterministic runtime projection).

## Decision-Locked Runtime Truth
- Active showcase scope is FY2024 -> FY2025 only for Core4: `NVDA`, `KO`, `WM`, `GE`.
- Fiscal-year caveat: annual filings may be filed in the next calendar year; pairing follows fiscal years derived from `reportDate` and `filingDate`.
- Primary runtime-visible compare campaign: `openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27`.
- Active compare-visible secondary campaign: `openai_chatgpt54ext_agent_fullsec_real_2026-03-06`.
- Pre-registered hidden workspace-aware campaign: `anthropic_claudeopus46_claudecode_fullsec_real_2026-03-09`.
- Archived compatibility-only ChatGPT real identity: `openai_chatgpt52ext_agent_fullsec_real_2026-02-27`.
- Canonical manual authoring unit is `llm_outline_compare_structured`.
- Runtime compatibility unit is `llm_outline_compare_runtime`, produced deterministically from structured outputs.
- Legacy detector envelopes (`det_llm_delta_brief_v1`, `det_llm_excerpt_picker_v1`) are no longer part of the active shipped product surface. Historical copies may remain only as archive or audit material.
- Focuspack and synthetic campaigns are historical or audit context only, not part of the active shipped runtime surface.

## Hard Constraints (Must Hold)
- No runtime LLM or ML calls in the shipped app.
- No changes to public JSON schemas without explicit governance unlock.
- SEC-derived text is untrusted and must never be rendered as HTML.
- Runtime remains deterministic-first, with explicit missing or degraded states when optional sidecars are unavailable.

## Current State Snapshot
- Active runtime pair gating is already restricted to FY2024 -> FY2025 for Core4.
- Structured outline sidecars are wired into the compare experience.
- Missing insight artifacts collapse to compact notices instead of dominating the page.
- Codex real and ChatGPT real structured outputs exist for the active 8-case scope (`4` tickers x `2` lenses).
- The canonical compare-visible ChatGPT lane is now the truthful `2026-03-06` ChatGPT 5.4 identity; the older `chatgpt52ext` real-lane path is archive-only compatibility.
- The master-run truth chain is bundle -> public `llm_inputs_v2` mirror -> master manifest -> master starters -> lock verifier -> prompt consistency -> validation/audit/progress.
- `docs/lab/09_master_run_troubleshooting_and_sources_of_truth.md` is the canonical recovery guide for stale-lock or multi-source drift incidents.
- `docs/lab/10_case_quality_review_log.md` is the canonical human-review ledger for keep, defer, rerun-later, and demo-safety decisions.

## Remaining Work (Operational)
1. Keep repo gates green after each data or UI change:
   - `npm run lint`
   - `npm run lab:predeploy`
   - `npm run lab:readiness`
   - `npm run build`
2. Regenerate manifests, starters, and public indexes from generators only after the active bundle and public `llm_inputs_v2` mirror are aligned.
3. Keep `scripts/lab_verify_master_input_locks.py` passing for the active Codex real, ChatGPT real, and Codex insight lanes before rerun batches start.
4. Preserve the canonical/compatibility/archive boundary in docs and generated metadata so old `chatgpt52ext` real paths do not appear as the active public truth.
5. Keep the Claude Code real lane preregistered but hidden from runtime selectors until real outputs exist.
6. Record any future manual-run friction in the troubleshooting doc, including the planned post-run formatter/helper for user-supplied self-run outputs.
7. Use the case-quality review log before promoting any artifact into screenshots, homepage storytelling, or launch collateral.

## Required Gates After Build or Data Logic Changes
- `npm run lint`
- `npm run lab:predeploy`
- `npm run lab:readiness`
- `npm run build`

## Historical Execution Record
Superseded phase narratives and prior one-shot execution prompts were moved to:
- `docs/lab/08_remaining_work_plan_history.md`

That file is archival context only and is not the active execution source of truth.
