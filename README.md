# Document Protocol Lab

Document Protocol Lab is an interactive casebook that compares approaches to business-document reading with frontier LLMs across six public SEC Item 1A cases: `NVDA`, `LLY`, `KO`, `META`, `TSLA`, and `WMT`.

The point is not to read one filing the one right way. It is to put three approaches on the same substrate and let a visitor see which one earned the answer and which one was theater.

**Current public casebook:** three anchor cases plus three added-pressure cases, each comparing plain prompt, structured contract, and tagged protocol reads on the same adjacent-year Item 1A pair.

**Status:** curated casebook, not a broad filing browser, general document chatbot, or benchmark-grade model ranking.

Live casebook: `https://benlei.org/sec-narrative-drift/`

## What this repo shows

- **Three approaches compared on the same case**: plain prompt (control), structured contract (typically the primary read), tagged protocol (comparator). Every multi-cell case renders a side-by-side of the control read and the primary read so the approach verdict is visible without clicking a disclosure.
- **An approach catalog** on the Methodology page naming what each approach earns, when it helps, and when it is theater.
- **Per-case anatomy** underneath: filing answer first, proof, stop, appendix. That is a grammar for reading one case — claim, proof, stop — distinct from the approach-comparison verdict the app produces across cases.
- **A static-runtime model**: precomputed JSON only, no runtime ML or LLM calls.

## Why these cases

- **`NVDA`** — strongest structural lift from moving beyond a plain-prompt read.
- **`LLY`** — where a structured approach tightens the stop honestly instead of overclaiming.
- **`KO`** — restraint case; the disciplined read produces one cell, not five, and the product lets that be enough.
- **`META`** — sharper AI enforcement and platform-liability pressure under added structure.
- **`TSLA`** — policy-shock and autonomy-commercialization pivot that a plain read misses.
- **`WMT`** — calm retail filing whose customer-interface risk and tariff persistence only surface once the approach earns them.

## Reading order

1. Start on Home to see the three-approach framing and the approach-verdict tile.
2. Open an anchor case (`NVDA`, `LLY`, or `KO`) to see the control-vs-primary approach comparison on a real filing pair.
3. Read the Methodology page's approach catalog for what each approach earns and when it is theater.
4. Deeper audit (deterministic detector control arm, provenance, methods) remains available under a disclosure and is intentionally not the default surface.

## Scope boundaries

This public product is intentionally narrow. The corpus is bounded to six curated SEC Item 1A adjacent-year pairs rather than a broad issuer gallery, upload flow, or whole-filing research platform. Approaches are limited to the three with authored pilot-matrix data. A fourth approach (extract-then-synthesize) has prompt templates but no cell data and is not claimed as live.

`GOOGL` remains reserve and `UNH` remains hold/internal-only. Some public cases ship with a single pilot-matrix cell rather than multiple; that restraint is an explicit product decision rather than a missing artifact.

## Product discipline

- Static JSON only at runtime.
- No runtime ML or LLM calls in the shipped app.
- SEC text is treated as untrusted and rendered as plain text only.
- The approach catalog names when an approach is theater; the case comparison shows whether structure earned its weight on that filing.

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

## Further reading

- `docs/DEMO_READINESS.md` — walkthrough and speaking notes.
- `docs/LAB_ARCHITECTURE_AND_GOALS.md` — architecture and the two-level grammar (approach comparison vs per-case anatomy).
- `docs/PRODUCT_STORY.md` — public product narrative.
- `docs/protocol_lab/README.md` — approach catalog and prompt-template entrypoint.
- `docs/REMAINING_SEAMS.md` — operational follow-ups.
- `docs/00_DOC_INDEX.md` — full documentation index.
- `public/data/business_document_protocol_lab/product_positioning/demo_share_v3.json` — public one-liner and share metadata.

## Notes

- `bundles/*` are local-only run artifacts for manual LLM jobs (gitignored).
- `reports/*` are local operator artifacts (gitignored).
- Archived non-canonical artifacts live under `attic/` (gitignored).
