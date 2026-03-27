# Document Protocol Lab

Document Protocol Lab currently ships a bounded SEC Item 1A pilot across three fixtures: NVDA, LLY, and KO.

Document Protocol Lab is a bounded, evidence-first SEC Item 1A pilot for testing how a document workflow answers, proves, and stops on real filings.

Live pilot: https://benlei.org/sec-narrative-drift/

## What currently ships
- The public app is a compact SEC Item 1A pilot inside Document Protocol Lab.
- The visible fixture system is intentionally fixed to `NVDA`, `LLY`, and `KO`.
- `NVDA` is the clearest first signal, `LLY` is the policy-heavy bounded contrast case, and `KO` is the restraint / low-drift honesty check.
- Company pages are intended to land the filing answer first, explain why the fixture matters to the protocol second, and keep deeper audit surfaces third.
- `Fresh vs reused` remains a bounded secondary lens rather than the default first read.
- Missing artifacts stay explicit instead of silently falling back.

## Current pilot framing
- Current pilot/workstream name: `SEC Narrative Drift`.
- Mounted public entry remains `https://benlei.org/sec-narrative-drift/`.
- The current pilot is deliberately narrow; it is not a broad issuer gallery, benchmark suite, or whole-filing research platform.
- `lab_cases_v1.json` remains the lower backstage runtime registry, not the public case list.

## Start with
- `NVDA` for the strongest first filing shift.
- `LLY` for policy, pricing, and industry-geometry contrast.
- `KO` for the restraint check that shows the workflow staying honest on a mostly stable filing.

## Product discipline
- Static JSON only at runtime.
- No runtime ML or LLM calls.
- SEC text is treated as untrusted and rendered as plain text only.
- Top-level public positioning is defined by `current_case_mix_v2.json`, `start_here_v1.json`, and `demo_share_v3.json`.
- Lower runtime coverage can remain broader than the public fixture set without changing the visible product claim.

## Current runtime notes
- `NVDA` and `KO` retain lower backstage runtime-registry integration.
- `LLY` is a bounded visible case and does not yet ship the full lower-audit runtime stack surfaced through `lab_cases_v1.json`.
- The lower runtime registry can remain broader backstage without widening the visible three-fixture claim.

## How to read one case
1. Start with the filing answer and paired evidence.
2. Read the protocol layer to see why that fixture is in the lab and what the comparison geometry adds.
3. Use deterministic methods and the deeper audit only when you want more structure, mechanisms, and limits.
4. Treat `Fresh vs reused` as a bounded secondary lens, not the default first read.

## Local development
```bash
npm install
npm run dev
```

## Required gates
```bash
npm run lint
npm run build
npm run lab:predeploy
npm run lab:readiness
```

## Canonical docs
- `docs/00_DOC_INDEX.md`
- `docs/LAB_REMAINING_WORK_PLAN.md`
- `docs/LAB_ARCHITECTURE_AND_GOALS.md`
- `docs/PRODUCT_STORY.md`
- `docs/DEMO_READINESS.md`
- `docs/REMAINING_SEAMS.md`
- `docs/SEC_TEXT_SAFETY.md`
- `docs/lab/05_llm_reproducibility_contract.md`
- `docs/lab/10_case_quality_review_log.md`

## Notes
- `bundles/*` are local-only run artifacts for manual LLM jobs.
- `reports/*` are local operator artifacts and remain untracked.
- Archived non-canonical artifacts live under `attic/`.
