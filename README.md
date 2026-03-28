# Document Protocol Lab

Document Protocol Lab currently ships a bounded SEC Item 1A pilot across three fixtures: NVDA, LLY, and KO.

Document Protocol Lab is a bounded, evidence-first pilot for testing how a document-comparison workflow answers, proves, and stops on real SEC risk disclosures.

**Current public pilot:** SEC Item 1A across three fixtures: `NVDA`, `LLY`, and `KO`.

**Status:** bounded public pilot, not a broad issuer gallery.

Live pilot: `https://benlei.org/sec-narrative-drift/`

## What this repo shows

- A compact public pilot inside Document Protocol Lab.
- Three deliberately chosen fixtures rather than a broad company browser.
- Company pages that surface:
  1. the filing answer,
  2. why the fixture matters to the protocol,
  3. deeper audit only when you want it.
- A static-runtime model: precomputed JSON only, with no runtime ML or LLM calls.

## Why these fixtures

- **`NVDA`** shows the clearest first filing shift.
- **`LLY`** is a policy-heavy bounded contrast case.
- **`KO`** is the restraint check that shows the workflow staying honest on a mostly stable filing.

## Start here

- Start with **`NVDA`** for the fastest read on what the workflow does well.
- Open **`LLY`** to see how the visible product stays useful while stopping honestly.
- Read **`KO`** to understand why low-drift cases matter to the protocol.

## How to read a case

1. Start with the filing answer and paired evidence.
2. Read the protocol layer to see why that fixture is in the lab.
3. Open the deeper audit only when you want more structure, mechanisms, or limits.
4. Treat `Fresh vs reused` as a bounded secondary lens, not the default first read.

## Scope boundaries

This public pilot is intentionally narrow. It uses SEC Item 1A risk sections as a bounded demonstration corpus rather than trying to be a broad issuer gallery or whole-filing research platform.

The visible public fixture set is fixed to `NVDA`, `LLY`, and `KO`.

Internal runtime coverage is broader than the visible public fixture set. That broader backstage coverage does not change the public claim for this shipped pilot.

`LLY` is a deliberately bounded visible case. It ships the first read and protocol layer, but not the full lower-audit runtime stack used by the deeper integrated cases.

## Product discipline

- Static JSON only at runtime.
- No runtime ML or LLM calls.
- SEC text is treated as untrusted and rendered as plain text only.
- Lower runtime coverage can remain broader than the public fixture set without changing the visible product claim.

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
