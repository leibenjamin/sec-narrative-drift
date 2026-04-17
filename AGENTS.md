# AGENTS.md — Instructions for Codex (Document Protocol Lab)

You are Codex working in this repository. The product is Document Protocol Lab, an interactive casebook that compares approaches to business-document reading with frontier LLMs across six SEC Item 1A cases. The public URL path remains `/sec-narrative-drift/` for live-link stability; the product identity is "Document Protocol Lab".

## Canonical docs (must follow)
1) `docs/00_DOC_INDEX.md` — canonical doc index.
2) `docs/LAB_ARCHITECTURE_AND_GOALS.md` — architecture and the two-level grammar (app-level approach comparison vs per-case anatomy).
3) `docs/protocol_lab/README.md` — Protocol Lab namespace rules, approach catalog, prompt-template entrypoint.
4) `docs/lab/05_llm_reproducibility_contract.md` — strict manual LLM output contract.
5) `docs/SEC_TEXT_SAFETY.md` — SEC text trust model and rendering guardrails.
6) `docs/PUBLIC_TONE_POLICY.md` — public-facing language policy and banned framing.
7) `docs/LAB_REMAINING_WORK_PLAN.md` — execution plan and phase status. May trail the shipped state; check the code before relying on it.

Legacy references (reference-only, not execution source of truth):
- `docs/_archive/legacy_context_20260302/00_README_doc_index.md`
- `docs/_archive/legacy_context_20260302/sec_narrative_drift_codex_spec_v1_13.md`
- `docs/_archive/legacy_context_20260302/sec_narrative_drift_codex_implementation_checklist_v1_13.md`

If anything conflicts, follow the Lab canonical docs above. Do not invent endpoints or rename JSON fields.

## Workflow rules
- Execute work phase-by-phase using `docs/LAB_REMAINING_WORK_PLAN.md`.
- Make the smallest change that satisfies each phase acceptance criterion.
- After any build/data logic change, run:
  - `npm run lab:predeploy`
  - `npm run lab:portfolio`
  - `npm run build`
- Keep `bundles/*` local-only unless explicitly requested.

## Hard constraints (do not violate)
- Frontend loads only static JSON from `public/data/...` (no direct SEC calls at runtime).
- Do not change public JSON schemas or detector envelope keys.
- No runtime LLM/ML calls in the shipped app.
- No POS tagging.
- SEC live fetches (if any) must include `SEC_USER_AGENT="Ben Lei <contact@benlei.org>"` and throttling.

## Implementation preferences
- Keep components small and readable.
- Favor deterministic, path-explicit error states over silent fallback.
- Pylance strict typing: use explicit type guards/helpers and explicit loops when parsing unknown JSON.

## Security / privacy guardrails (must follow)
- Treat all SEC-derived text as untrusted. Do not render it as HTML.
- Prefer highlighting by splitting React text nodes plus safe `<mark>` spans.
- Do not use `dangerouslySetInnerHTML` or innerHTML APIs.
- External links must use: `target="_blank"` plus `rel="noopener noreferrer"`.
- Do not add analytics, trackers, or third-party CDNs by default.
