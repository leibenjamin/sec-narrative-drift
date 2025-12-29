# SEC Narrative Drift

A portfolio micro-app that quantifies how a public company's Item 1A risk factor language shifts over time using SEC 10-K filings.

Live demo: (add link)

## What it does
- Compares year-to-year Item 1A disclosures and surfaces rising/falling terms.
- Highlights term shifts in context with excerpted paragraphs.
- Shows similarity patterns across years with a compact heatmap view.
- Keeps all SEC data precomputed as static JSON for reliability and compliance.

## Why it is useful
Risk factor language changes can signal evolving exposure, strategy, or regulatory pressure. This app turns dense filings into a concise narrative drift view that is easy to scan and explain.

## Features
- Phrase-aware term shifts (unigrams + vetted SEC phrases; supports multiword signals).
- Optional alternate lens (TextRank keyphrases) when available in data.
- Highlighted excerpts and side-by-side comparisons for context.
- Static data delivery (no in-browser SEC calls).

## Tech stack
- React + TypeScript + Vite
- Tailwind CSS
- Python data pipeline for extraction and metrics

## Data and methodology
- Source: SEC EDGAR 10-K filings, primarily Item 1A Risk Factors.
- Pipeline scripts: `scripts/` (fetch, extract, score, and generate JSON outputs).
- Outputs: `public/data/sec_narrative_drift/<TICKER>/*.json` consumed by the frontend.
- Security: SEC text is treated as untrusted and never rendered as HTML.

## Getting started
```bash
npm install
npm run dev
npm run build
```

## Regenerate data (live SEC)
Set your own SEC User-Agent with contact info (SEC policy requirement):
```bash
SEC_USER_AGENT="YOUR NAME <your.email@domain.com>"
```

Regenerate one ticker:
```bash
python scripts/sec_fetch_and_build.py --ticker AAPL --years 10 --out public/data/sec_narrative_drift/AAPL
```

## Project layout
- `src/` React UI and data loaders
- `public/data/` static JSON datasets used by the app
- `scripts/` data pipeline and fixtures (`scripts/sample_fixtures/`)

## Notes
- The public repo is README-driven; internal planning docs are kept private.
- If you publish a live demo, add the link and a screenshot at the top.

## License
No license specified yet.
