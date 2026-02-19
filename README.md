# SEC Narrative Drift Lab

Portfolio-focused, deterministic-first analysis of adjacent SEC 10-K Item 1A risk-factor years.

Live: https://benlei.org/sec-narrative-drift/

## Product direction
- Lab-first UI and UX (Home, Showcase, Company Lab, Methodology).
- Showcase scope: `NVDA`, `KO`, `WM`, `GE`.
- Runtime reads static JSON only from `public/data/sec_narrative_drift_lab/`.
- No runtime ML/LLM calls. LLM outputs are optional precomputed sidecars.

## Key guarantees
- Deterministic detectors and fixed output envelopes.
- SEC text treated as untrusted; rendered as text nodes only.
- Explicit missing-artifact states with expected paths and copyable debug payloads.
- Deep-link compatibility kept for `/company/:ticker?from=YYYY&to=YYYY` (Lab-only behavior).

## Local development
```bash
npm install
npm run dev
```

## Required gates
```bash
npm run lab:predeploy
npm run lab:portfolio
npm run build
```

## Canonical docs
- `docs/00_DOC_INDEX.md`
- `docs/LAB_REMAINING_WORK_PLAN.md`
- `docs/PORTFOLIO_STORY.md`
- `docs/SEC_TEXT_SAFETY.md`
- `docs/lab/05_llm_reproducibility_contract.md`

## Notes
- `bundles/*` are local-only run artifacts for manual LLM jobs.
- Archived non-canonical artifacts live under `attic/`.
