# Remaining Seams

## Lower-runtime-registry seam
- The visible public pilot is fixed to `NVDA`, `LLY`, and `KO`.
- `public/data/sec_narrative_drift_lab/lab_cases_v1.json` and related registries can remain broader backstage for runtime support and audit context.
- That backstage breadth is not the public case list and should not widen the visible product claim.

## Mounted-base local preview caveat
- Local mounted-base preview still has a known caveat under `vite preview`.
- With `VITE_BASE_PATH=/sec-narrative-drift/`, the HTML shell loads at `/sec-narrative-drift/`, but JS assets under `/sec-narrative-drift/assets/...` currently 404 in local preview.
- Use a root-base production preview for local rendered QA until that serving path is fixed.

## Manual follow-up
- The GitHub About sentence remains a manual follow-up outside the repo.
- Repo-side truth should stay aligned so that manual About text can match the current bounded three-fixture pilot without extra interpretation.
