# SEC Narrative Drift Lab

Investor-first, evidence-backed comparison of how SEC 10-K Item 1A risk disclosures change from one fiscal year to the next.

Live: https://benlei.org/sec-narrative-drift/

## What this app does
- Covers the current Core4 scope only: `NVDA`, `KO`, `WM`, and `GE`.
- Opens one active FY2024 to FY2025 Item 1A case per company.
- Starts with a compare-first risk narrative summary, then confirms the filing signal with deterministic methods and agreement.
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
- One active FY2024 to FY2025 Item 1A case per company.
- Active compare-visible campaigns:
  - `openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27`
  - `openai_chatgpt54ext_agent_fullsec_real_2026-03-06`
- Hidden preregistered workspace-aware lane:
  - `anthropic_claudeopus46_claudecode_fullsec_real_2026-03-09`

## How to read one case
1. Start with the risk narrative summary and the paired prior-year versus current-year evidence.
2. Check the two core deterministic methods to see whether the filing language really moved.
3. Use the agreement panel to see whether the deterministic methods reinforce the same story.
4. Open outline compare to inspect mechanisms, investor relevance, limits, and side-by-side framing.
5. Treat Insight Lens as optional when it is available, not as part of the default flow.

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
