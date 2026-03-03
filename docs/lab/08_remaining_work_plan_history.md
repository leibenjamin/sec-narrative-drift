# Remaining Work Plan History (Archived)

Status: archive-only context. This file preserves superseded planning narrative that was previously embedded in `docs/LAB_REMAINING_WORK_PLAN.md`.

Use `docs/LAB_REMAINING_WORK_PLAN.md` for current execution.

## Historical Snapshot (Superseded)
- Deterministic baseline hardening, runtime migration, and Lab-first UI pivot phases were tracked here during 2026-02-21 through 2026-02-27.
- Earlier planning included focuspack-era and synthetic full-section campaign milestones that are now runtime-hidden/audit-only.
- Earlier docs referenced legacy detector-first manual run patterns (`reports/lab_llm_run_manifest.*` and detector-by-detector execution) before the canonical master-first pivot.

## Superseded Phase Narrative: PHASE 0 (Deterministic Baseline)
Historical goals included:
- ship deterministic baseline,
- run readiness/build gates,
- deploy and verify registry/output path integrity,
- add post-deploy cache verification guidance.

Historical acceptance criteria included:
- live registry freshness,
- deterministic coverage for required pairs,
- explicit error/missing behavior instead of silent empties.

## Superseded Phase Narrative: PHASE 1 (RAW Backfill)
Historical goals included:
- audit RAW prerequisites,
- generate RAW deterministic outputs for eligible pairs,
- rebuild registry and smoke/readiness checks,
- verify lens-switch behavior in UI.

## Superseded Phase Narrative: PHASE 2 (Legacy Manual LLM Coverage)
Historical goals included:
- detector-level LLM manifest/checklist generation,
- run-pack and thread-starter generation,
- manual ChatGPT detector runs,
- post-run validation and compatibility migration.

This phase narrative is now superseded by canonical master-first execution (`llm_outline_compare_v1`) with deterministic projection to detector envelopes.

## Superseded Phase Narrative: PHASE 3 (Product Polish)
Historical goals included:
- add explainer UX,
- improve explicit missing/debug states,
- perform SEC text safety review,
- refine performance and ergonomics for toggles/load behavior.

## Superseded Phase Narrative: PHASE 4 (Repo Cleanup)
Historical goals included:
- move pre-Lab artifacts into `attic/`,
- reduce script/cache noise,
- establish canonical docs and execution orientation.

## Archived One-Shot Prompt (Superseded)
The historical one-shot prompt instructed Codex to:
1. implement Phase 0 and scaffold Phase 1-4,
2. add helper/report generators,
3. run `lab:predeploy`, `lab:readiness`, `build`,
4. commit and push.

This one-shot execution block is intentionally retired from active docs to avoid stale guidance.

## Why This Archive Exists
- Preserve historical context and rationale for decisions made during the Lab pivot.
- Keep active execution docs concise and decision-locked.
- Avoid reintroducing deprecated workflow patterns into current runs.
