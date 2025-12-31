# SEC Narrative Drift

A small portfolio app that turns 10-K **Item 1A (Risk Factors)** into an auditable "what changed?" workflow:
- **Drift timeline** (where the narrative shifts most year-to-year)
- **Similarity heatmap** (pick a year pair)
- **Term shifts** (distinctive terms; smoothed log-odds)
- **Evidence-first compare** (representative excerpts + "View on SEC")

Live: https://benlei.org/sec-narrative-drift/

## What this is (and isn't)

This is **descriptive**, not causal. Drift is a reading prompt, not a conclusion.

It also does **not** ship full filing text. The demo stores short excerpts only and links back to EDGAR for verification.

## Data source

- SEC EDGAR 10-K filings (public).
- Section: Item 1A "Risk Factors".

## Local dev

```bash
npm install
npm run dev
```

## Build & deploy

```bash
npm run build
npm run preview
```

Static hosting (e.g., Cloudflare Pages / GitHub Pages) works well.

## Scripts (data build)

See `scripts/README.md` for batch builds and how we fetch filings responsibly (User-Agent, rate limits, caching).

## Related work (and how this differs)

There are many ways to download/extract SEC sections. This project's focus is narrower: **auditable change signals + evidence UX**.

- EDGAR-CRAWLER (WWW 2025): https://github.com/lefterisloukas/edgar-crawler  
  Great for corpora; SEC Narrative Drift starts after extraction: change metrics + evidence UX.

- itemseg (10-K item segmentation): https://pypi.org/project/itemseg/  
  A stronger segmenter can be swapped in; the UI/metrics aren't married to one parser.

- Boilerplate & stickiness framing (Harvard Forum, 2024):  
  https://corpgov.law.harvard.edu/2024/03/26/covid-19-risk-factors-and-boilerplate-disclosure/

- Disclosure evolution & stickiness (Dyer et al., JAE 2017):  
  https://msbfile03.usc.edu/digitalmeasures/sticelaw/intellcont/Dyer%20et%20al.%202017-1.pdf

- Crisis years reduce boilerplate (Nature HSSC, 2024):  
  https://www.nature.com/articles/s41599-024-04169-w

_Not affiliated with the above tools/papers._
