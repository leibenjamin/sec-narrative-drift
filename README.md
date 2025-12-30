# SEC Narrative Drift

A portfolio micro-app that quantifies how a public company's Item 1A risk factor language shifts over time using SEC 10-K filings.

Live demo: https://<your-domain>/sec-narrative-drift

## Screenshots
![Home](./assets/screenshot-home.png)
![Company](./assets/screenshot-company.png)

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

## Data provenance and compliance
- Source: SEC EDGAR 10-K filings, primarily Item 1A Risk Factors.
- Pipeline scripts live in `scripts/` and output static JSON to `public/data/sec_narrative_drift/`.
- SEC text is treated as untrusted and never rendered as HTML.
- Descriptive, not causal. This is a reading aid, not investment advice.
- Use a descriptive SEC User-Agent with contact info and respect SEC fair-access limits.

## Getting started
```bash
npm install
npm run dev
npm run build
```

## Build data locally (live SEC)
Set your own SEC User-Agent (SEC policy requirement):
```bash
SEC_USER_AGENT="YOUR NAME <your.email@domain.com>"
```

Regenerate one ticker:
```bash
python scripts/sec_fetch_and_build.py --ticker AAPL --years 10 --out public/data/sec_narrative_drift/AAPL
```

Batch build (anchors and stories):
```bash
python scripts/sec_build_universe.py --only all
```

Validate outputs and rebuild index:
```bash
python scripts/sec_validate_public_data.py
python scripts/sec_build_index.py
```

## Project layout
- `src/` React UI and data loaders
- `public/data/` static JSON datasets used by the app
- `scripts/` data pipeline and fixtures (`scripts/sample_fixtures/`)

## Notes
- The public repo is README-driven; internal planning docs are kept private.
- Replace the live URL and screenshot placeholders when you publish.

## License
No license specified yet.
