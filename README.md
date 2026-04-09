# Document Protocol Lab

Document Protocol Lab ships as an interactive casebook for bounded document-comparison judgment across six public SEC Item 1A cases: `NVDA`, `LLY`, `KO`, `META`, `TSLA`, and `WMT`.

The product exists to show what a workflow should claim, how it should prove it, and where it should stop.

**Current public casebook:** three anchor cases plus three added pressure cases.

**Status:** curated casebook, not a broad issuer browser, general document chatbot, or benchmark-grade product comparison.

Live casebook: `https://benlei.org/sec-narrative-drift/`

## What this repo shows

- A compact interactive casebook inside Document Protocol Lab.
- Three anchor answer shapes on Home: vivid answer, honest stop, and useful restraint.
- Three added pressure cases in the Casebook: sharper AI enforcement, policy shock, and calm retail-interface shift.
- Company pages that surface:
  1. the filing answer,
  2. what the case proves and does not prove,
  3. deeper audit only when you want it.
- A static-runtime model: precomputed JSON only, with no runtime ML or LLM calls.

## Why these cases

- **`NVDA`** shows the clearest answer-first route.
- **`LLY`** is the honest-stop public route.
- **`KO`** is the restraint check that shows the workflow staying useful on a mostly stable filing.
- **`META`** sharpens a repeated AI theme into a more decision-useful enforcement and liability stack.
- **`TSLA`** turns an execution story into a policy-shock and autonomy-commercialization pivot.
- **`WMT`** shows how a calm retail case can still matter once customer-interface risk and tariff persistence sharpen.

## Start here

- Start with **`NVDA`** for the clearest answer-first read.
- Open **`LLY`** to see how the visible product stays useful while stopping honestly.
- Read **`KO`** to understand why low-drift restraint is a product strength.
- Use the full **Casebook** for `META`, `TSLA`, and `WMT` when you want added pressure types without widening the public claim.

## How to read a case

1. Start with the filing answer and paired evidence.
2. Read the case layer to see what the workflow is allowed to claim and where it should stop.
3. Open the deeper audit only when you want more structure, mechanism detail, or provenance.
4. Treat lower comparison lanes as supporting pedagogy, not as the default first read.

## Scope boundaries

This public product is intentionally narrow. It uses SEC Item 1A risk sections as a bounded demonstration corpus rather than trying to be a broad issuer gallery, upload flow, or whole-filing research platform.

The public casebook roster is fixed to `NVDA`, `LLY`, `KO`, `META`, `TSLA`, and `WMT`.

`GOOGL` remains reserve and `UNH` remains hold/internal-only.

Some public cases ship with pilot-matrix artifacts only. That bounded stop is an explicit product decision rather than a hidden fallback.

## Product discipline

- Static JSON only at runtime.
- No runtime ML or LLM calls.
- SEC text is treated as untrusted and rendered as plain text only.
- Public answer shape, proof, and stop stay visible.

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

- `docs/DEMO_READINESS.md`
- `docs/REMAINING_SEAMS.md`
- `docs/LAB_ARCHITECTURE_AND_GOALS.md`
- `docs/00_DOC_INDEX.md`
- `public/data/business_document_protocol_lab/product_positioning/demo_share_v3.json`

## Notes

- `bundles/*` are local-only run artifacts for manual LLM jobs.
- `reports/*` are local operator artifacts and remain untracked.
- Archived non-canonical artifacts live under `attic/`.
