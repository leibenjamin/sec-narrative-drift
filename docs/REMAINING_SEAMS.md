# Remaining Seams

## Lower-runtime-registry seam
- The public casebook is fixed to six cases (`NVDA`, `LLY`, `KO`, `META`, `TSLA`, `WMT`) comparing three approaches (plain prompt, structured contract, tagged protocol).
- `public/data/sec_narrative_drift_lab/lab_cases_v1.json` and related backstage registries can remain broader for runtime support and audit context.
- That backstage breadth is not the public case list and must not widen the visible six-case claim or inflate the three-approach count.

## Mounted-base local preview caveat
- Local mounted-base preview still has a known caveat under `vite preview`.
- With `VITE_BASE_PATH=/sec-narrative-drift/`, the HTML shell loads at `/sec-narrative-drift/`, but JS assets under `/sec-narrative-drift/assets/...` currently 404 in local preview.
- Use a root-base production preview for local rendered QA until that serving path is fixed.

## Manual follow-ups outside the repo
- The GitHub About sentence remains a manual follow-up. Repo-side truth should stay aligned so the About text can match the current approach-comparison framing without extra interpretation.
- The public URL path remains `/sec-narrative-drift/` for live-link stability; the product identity is "Document Protocol Lab" and does not depend on the path.

## Pedagogic coverage seam
- `PEDAGOGIC_COMPARE_EXAMPLES` in `src/lib/casebookContent.ts` currently names worked approach-verdict breakdowns for `TSLA` and `META`. Extending that coverage to `NVDA`, `LLY`, and `KO` would close a visible asymmetry in the per-case pedagogic layer. The approach comparison block (from `comparison_pairs[0]`) is already live on every multi-cell case; this seam is about the authored worked-example text, not the underlying data.
