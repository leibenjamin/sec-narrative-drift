# AGENTS.md — Instructions for Codex (SEC Narrative Drift)

You are Codex working in this repository.

## Canonical docs (MUST follow)
1) `docs/sec_narrative_drift_codex_spec_v1_11.md` — canonical product + data contract
2) `docs/sec_narrative_drift_codex_implementation_checklist_v1_11.md` — ticket order + acceptance criteria

If anything conflicts, the spec is the source of truth. Do not invent endpoints or rename JSON fields.

## Workflow rules
- Work **ticket-by-ticket** in checklist order.
- Make the **smallest change** that satisfies the ticket acceptance criteria.
- After each ticket:
  - run `npm run build` (UI tickets) or the script command (pipeline tickets)
  - fix errors
  - do not proceed until acceptance criteria are met
- Prefer deterministic fixtures in `scripts/sample_fixtures/` before live SEC calls.

## Hard constraints (do not violate)
- Frontend loads **only** static JSON from `public/data/...` (no direct SEC calls).
- Do not change JSON schemas (field names and shapes are strict).
- Always include SEC headers (User-Agent) and enforce throttling for pipeline fetches.

## Implementation preferences
- Keep components small and readable.
- For heatmap, SVG grid is acceptable and often simplest.
- For highlighting terms, avoid `dangerouslySetInnerHTML` unless you guarantee escaping.
- Pylance strict typing: when parsing JSON, use explicit type guards/helpers and explicit loops to build typed lists/dicts; avoid comprehensions over unknown data and `all(...)` on unknown keys.


## Security / privacy guardrails (MUST follow)
- Treat all SEC-derived text as **untrusted**. Do not render it as HTML.
- Prefer highlighting by splitting into React text nodes + `<mark>` spans.
- **Do not use** `dangerouslySetInnerHTML`. If you absolutely must, you must escape then sanitize (e.g., DOMPurify) and document why.
- External links (SEC URLs) must use: `target="_blank"` + `rel="noopener noreferrer"`.
- Do not introduce analytics, trackers, or third-party CDNs by default.
- Any user notes stored locally must be clearly labeled “stored in your browser (localStorage)” and should not include sensitive info.
