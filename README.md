# SEC Narrative Drift Lab

Investor-first, evidence-backed comparison of how SEC 10-K Item 1A risk disclosures change from one fiscal year to the next.

Live: https://benlei.org/sec-narrative-drift/

## What this app does
- Compares adjacent Item 1A filing years for the current Core4 showcase scope: `NVDA`, `KO`, `WM`, and `GE`.
- Starts with deterministic text methods for lexical drift, distribution shift, reuse, structure change, and detector agreement.
- Adds precomputed outline-compare sidecars from Codex and ChatGPT, shown side by side with explicit evidence and provenance.
- Keeps missing artifacts explicit instead of silently falling back.

## Why this matters
Item 1A language often changes before a company has fully translated the shift into cleaner management messaging elsewhere. The useful question is not just whether the filing changed, but whether the company is emphasizing a more important operating, regulatory, or commercial risk channel than it did a year earlier.

This project is built to help investors, competitors, analysts, and technical reviewers answer that question quickly, then audit the evidence in detail.

## Product guarantees
- Runtime reads static JSON only from `public/data/sec_narrative_drift_lab/`.
- No runtime ML or LLM calls.
- SEC text is treated as untrusted and rendered as plain text only.
- Public JSON schemas remain fixed unless explicitly unlocked.
- Model outputs are offline sidecars with deterministic validation and projection.

## Current public scope
- Filing scope: adjacent FY2024 -> FY2025 Item 1A pairs only.
- Active compare-visible campaigns:
  - `openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27`
  - `openai_chatgpt54ext_agent_fullsec_real_2026-03-06`
- Hidden preregistered workspace-aware lane:
  - `anthropic_claudeopus46_claudecode_fullsec_real_2026-03-09`

## How to read one case
1. Start with the risk narrative summary and the paired prior-year/current-year evidence.
2. Check the two core deterministic methods to see whether the filing language really moved.
3. Use the agreement panel to see whether the deterministic methods reinforce the same story.
4. Compare Codex and ChatGPT in the outline-compare view to see whether the divergence is substantive or just framing.

## Local development
```bash
npm install
npm run dev
```

## Required gates
```bash
npm run lint
npm run lab:predeploy
npm run lab:readiness
npm run build
```

## Canonical docs
- `docs/00_DOC_INDEX.md`
- `docs/LAB_REMAINING_WORK_PLAN.md`
- `docs/PRODUCT_STORY.md`
- `docs/SEC_TEXT_SAFETY.md`
- `docs/lab/05_llm_reproducibility_contract.md`
- `docs/lab/10_case_quality_review_log.md`

## Notes
- `bundles/*` are local-only run artifacts for manual LLM jobs.
- `reports/*` are local operator artifacts and remain untracked.
- Archived non-canonical artifacts live under `attic/`.
