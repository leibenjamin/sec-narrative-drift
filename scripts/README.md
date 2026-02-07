# Scripts - SEC Narrative Drift Pipeline

This directory contains the data processing pipeline for extracting, analyzing, and building SEC 10-K Risk Factors (Item 1A) data.

## Quick Start

### Setup
```bash
cd scripts
python -m venv ../.venv
../.venv/Scripts/activate  # Windows
# or: source ../.venv/bin/activate  # Unix
pip install -r requirements.txt
```

### Environment Variables
```bash
# Required for live SEC API requests:
export SEC_USER_AGENT="Your Name your@email.com"

# Optional overrides:
export SEC_CACHE_ROOT="/path/to/cache"  # Default: data/sec_cache
export SEC_CACHE_MAX_GB="10"            # Cache pruning limit
```

---

## Pipeline Overview

### Two Execution Modes

| Mode | When to Use | SEC API Needed? | Speed |
|------|-------------|-----------------|-------|
| **From Cache** | Local dev, testing, rebuilding after algorithm changes | No | Fast |
| **From Live** | Initial build, adding new tickers, updating latest filings | Yes | Slow (rate limited) |

**Note:** Sample fixtures are **opt-in only**. The pipeline will not use
`scripts/sample_fixtures/` unless `--allow-sample-fixtures` is explicitly set.

### Live Website vs Local Development

| Aspect | Live Website | Local Development |
|--------|--------------|-------------------|
| **Data Source** | Pre-built JSON in `public/data/` | Built from cache or live SEC |
| **Updates** | Manual rebuild + deploy | On-demand rebuild |
| **Cache** | Not needed at runtime | Required for efficient iteration |
| **SEC API** | Not needed at runtime | Only for initial fetch or updates |

---

### Algorithm Notes (short)

- **Drift:** TF-IDF cosine similarity between adjacent years; drift = 1 - similarity.
- **Term shifts:** Smoothed log-odds with a Dirichlet prior. Rank score applies a document-frequency penalty to downweight boilerplate. Phrases come from PMI bigrams + an allowlist; the alternate lens uses TextRank keyphrases.
- **Boilerplate:** Approximate sentence reuse score (see `sec_metrics.py`).
- **Determinism:** No LLMs or opaque models in the core metrics; outputs are reproducible from inputs + parameters.

---

## Directory Structure

```
sec-narrative-drift/
|-- data/
|   `-- sec_cache/                    # Primary data cache (git-ignored)
|       |-- filings/{CIK}/{ACCESSION}/
|       |   |-- filing.txt.gz         # Normalized full filing text
|       |   |-- filing.html.gz        # Original HTML (optional)
|       |   |-- filing_meta.json      # Filing metadata
|       |   `-- risk/
|       |       |-- item_1a.txt.gz             # Extracted risk section
|       |       |-- term_counts_primary.json.gz # Canonical term counts (per filing)
|       |       `-- rf_meta.json               # Extraction metadata + debug
|       |-- indexes/
|       |   |-- ticker_year_index.json    # Global ticker-year mapping
|       |   `-- extraction_version.json   # Version tracking
|       `-- reports/
|           `-- cache_usage.json      # Cache statistics
|
|-- public/data/sec_narrative_drift/  # Website output (committed)
|   |-- {TICKER}/
|   |   |-- meta.json                 # Company info
|   |   |-- filings.json              # Filing list with extraction status
|   |   |-- metrics_10k_item1a.json   # Drift scores, similarity
|   |   |-- similarity_10k_item1a.json # Cosine similarity matrix
|   |   |-- shifts_10k_item1a.json    # Year-over-year term shifts
|   |   `-- excerpts_10k_item1a.json  # Representative text excerpts
|   `-- index.json                    # Global ticker index
|
|-- public/data/sec_narrative_drift_metrics/  # Optional sidecar metrics (committed)
|   |-- {TICKER}/
|   |   `-- deboilerplated_drift_10k_item1a.json
|
|-- scripts/
|   |-- _cache/                       # Working cache (git-ignored)
|   |   |-- submissions.zip           # Bulk SEC submissions archive
|   |   |-- build_universe.log        # Build execution log
|   |   `-- {TICKER}/                 # Raw HTML files (optional)
|   |-- sample_fixtures/              # Test fixtures
|   |-- resources/                    # Config files (git-ignored)
|   `-- *.py                          # Pipeline scripts
```

---

## Common Workflows

### Build per-filing term counts cache (optional, improves audits)
```bash
python scripts/build_risk_term_counts_cache.py
```
This writes `risk/term_counts_primary.json.gz` for each filing, using the same
tokenization + canonicalization as term shifts. Re-run after refreshing risk
extractions or changing tokenization logic.

### 1. Full Rebuild (From Existing Cache)

Use when: Extraction algorithm changed, need fresh metrics.

```bash
cd scripts

# 1. Re-extract risk sections from cached HTML
python refresh_risk_cache_from_html.py

# 2. Build public JSONs for all tickers (using cached submissions)
python sec_build_universe.py --submissions-zip _cache/submissions.zip

# 3. Build global index
python sec_build_index.py
```

### 2. Single Ticker Rebuild

Use when: Testing changes on one company.

```bash
python sec_fetch_and_build.py --ticker AAPL --submissions-zip _cache/submissions.zip
```
Note: partial runs now *merge* year entries into `ticker_year_index.json` and
preserve existing years outside the current run.

To run against deterministic fixtures instead of live/cached SEC data:
See **Testing / Debug (fixtures)** below.

### 3. Initial Build (From Live SEC)

Use when: First time setup, no cache exists.

```bash
# Download bulk submissions archive first (saves many API calls)
python sec_build_universe.py --download-submissions-zip

# Build all tickers
python sec_build_universe.py --submissions-zip _cache/submissions.zip
python sec_build_index.py
# If you want to reuse prior index metadata:
# python sec_build_index.py --existing-index public/data/sec_narrative_drift/index.json
```

### 4. Add New Ticker

```bash
# Add ticker to scripts/universe_featured.json, then:
python sec_fetch_and_build.py --ticker NEWTICKER --submissions-zip _cache/submissions.zip
python sec_build_index.py
```

### 5. Validate Data Quality

```bash
# Check cache integrity
python sec_validate_cache.py

# Require risk slice/raw/segments caches
python sec_validate_cache.py --require-risk-exports

# Check public output consistency
python sec_validate_public_data.py

# Build manual review checklist
python build_risk_manual_checklist.py
```
`build_risk_manual_checklist.py` uses `public/data/sec_narrative_drift/index.json`
for company names and does not fall back to fixtures.

### 5.1 Build Deboilerplated Drift Report (optional)

```bash
python build_deboilerplated_drift_report.py
```
Writes:
- `reports/term_shift_deboilerplate/deboilerplated_drift_pairs.csv`
- `reports/term_shift_deboilerplate/deboilerplated_drift_pairs.jsonl`

### 5.2 Promote Lab LLM Inputs To Public (optional)

Use this when you want stable shipped `provenance.input_file` targets under
`public/data/sec_narrative_drift_lab/llm_inputs/`.

```bash
# Promote all input files referenced by a pilot pack:
python scripts/lab_promote_llm_inputs_to_public.py --from-pilot-pack bundles/llm_pilot_pack_20260204_145010

# Or promote from a showcase bundle:
python scripts/lab_promote_llm_inputs_to_public.py --from-bundle bundles/showcase_llm_inputs_20260205_171321

# Add --overwrite to replace existing public llm_inputs files.
```

### 6. Fix Year Index Issues

```bash
# Rebuild ticker-year index from cache (fixes year mapping issues)
python rebuild_ticker_year_index_from_cache.py
```

---

## Script Reference

### Core Pipeline Scripts

| Script | Purpose | Typical Flags |
|--------|---------|---------------|
| `sec_fetch_and_build.py` | Build data for one ticker | `--ticker AAPL --submissions-zip _cache/submissions.zip` |
| `sec_build_universe.py` | Batch build all tickers | `--submissions-zip _cache/submissions.zip` |
| `sec_build_index.py` | Build global index.json | `--existing-index ...` (tests only: `--allow-sample-fixtures`) |

### Canonical entrypoints
- `sec_fetch_and_build.py` (single ticker, live or cached submissions)
- `refresh_risk_cache_from_html.py` (refresh risk caches from local HTML)
- `sec_build_universe.py` (batch build all tickers)
- `sec_build_index.py` (global index)

### Cache Management Scripts

| Script | Purpose | Typical Flags |
|--------|---------|---------------|
| `sec_cache.py` | Cache utilities (library) | N/A (imported) |
| `refresh_risk_cache_from_html.py` | Re-extract from cached HTML | `--tickers AAPL,MSFT` |
| `rebuild_ticker_year_index_from_cache.py` | Rebuild index from cache | (tests only: `--allow-sample-fixtures`) |
| `fetch_missing_html_cache.py` | Download missing HTML | `--only AAPL --limit 10` |
| `export_risk_sections.py` | Export cached risk sections | `--tickers AAPL,MSFT --years 2022,2023` |

### Validation Scripts

| Script | Purpose | Typical Flags |
|--------|---------|---------------|
| `sec_validate_cache.py` | Check cache integrity | `--hash-sample 5` |
| `sec_validate_public_data.py` | Check output consistency | (none) |
| `build_risk_manual_checklist.py` | Generate review checklist | (none) |

### Analysis Scripts

| Script | Purpose |
|--------|---------|
| `sec_extract_item1a.py` | Risk section extraction (library) |
| `sec_metrics.py` | TF-IDF similarity, term shifts |
| `sec_quality.py` | Excerpt selection |
| `build_deboilerplated_drift_report.py` | Aggregate deboilerplated drift sidecar outputs |
| `build_canonical_terms.py` | Term normalization mapping |
| `export_risk_sections.py` | Export cached risk files to a zip bundle |

### Non-canonical / auxiliary scripts
These are useful for audits or one-off analysis but are not required for routine
builds:
- `sec_risk_extraction_report.py`
- `sec_risk_extraction_audit.py`
- `analyze_term_shift_snr.py`
- `sweep_term_shift_prior.py`

Notes:
- `sec_risk_extraction_report.py` uses featured tickers by default; override with
  `--cases TICKER:YEAR` or `--cases LABEL:TICKER:YEAR`.
- `sweep_term_shift_prior.py` defaults to `scripts/universe_featured.json` tickers
  when `--tickers` is not provided.

### Debug Scripts (Internal)

| Script | Purpose |
|--------|---------|
| `debug_start_in_toc.py` | Debug TOC detection |
| `sec_risk_extraction_audit.py` | Audit extraction quality |

---

## Key Flags Reference

### sec_fetch_and_build.py

```
--ticker TICKER           Required: Stock ticker (e.g., AAPL)
--submissions-zip PATH    Use cached submissions archive (recommended)
--years N                 Number of years to process
--start-year YYYY         Minimum fiscal year (default: 2015)
--out PATH                Output directory
--include-20f             Include 20-F filings (international companies)
--cache-debug-html        Store HTML for debugging
--force-html-cache        Re-fetch HTML even if cached
--force-live-submissions  Ignore submissions fixtures (also disables fixture HTML)
--allow-sample-fixtures   Use test fixtures instead of live data
--cache-only              Rebuild from local cache only (no SEC API calls)
--incremental             Only process filings newer than cached
--fast                    Skip bootstrap CI computation (faster builds)
--use-ticker-map-cache    Use cached ticker map if fresh (default: True)
--no-ticker-map-cache     Always fetch fresh ticker map
```

### sec_build_universe.py

```
--submissions-zip PATH        Use cached submissions archive
--download-submissions-zip    Download latest archive first
--only [anchors|stories|all]  Which ticker subset
--start-at TICKER             Resume from specific ticker
--max-count N                 Stop after N tickers
--include-20f                 Include 20-F filings
--cache-only                  Rebuild all tickers from local cache (no SEC API)
--incremental                 Only fetch new filings for each ticker
--refresh-ticker-map          Force refresh ticker map before batch
```

### sec_rebuild_local.py

Convenience script for local cache rebuilds (no SEC API calls):

```
--ticker TICKER     Single ticker to rebuild (default: all universe tickers)
--workers N         Number of parallel workers (default: 1)
--list-only         List processable tickers without rebuilding
```

Example: Rebuild all tickers from cache with 4 workers:
```bash
python sec_rebuild_local.py --workers 4
```

---

## Testing / Debug (fixtures)

Fixtures are **tests-only** and must be explicitly enabled. All fixture-enabled
scripts print a warning banner when fixtures are in use.

```bash
# Deterministic single-ticker run using fixtures
python sec_fetch_and_build.py --ticker AAPL --allow-sample-fixtures

# Build index with fixture metadata (tests only)
python sec_build_index.py --allow-sample-fixtures

# Rebuild ticker-year index using fixture ticker map (tests only)
python rebuild_ticker_year_index_from_cache.py --allow-sample-fixtures
```
---

## Version Tracking

The pipeline tracks algorithm versions to enable cache invalidation:

| Version | Location | Current |
|---------|----------|---------|
| Extractor | `sec_cache.EXTRACTOR_VERSION` | 1.25 |
| Normalizer | `sec_cache.NORMALIZER_VERSION` | 1.0 |

When these change, the pipeline will re-extract rather than use cached data.

---

## Quality Gates

Extractions are validated against these thresholds:

| Gate | Threshold | Warning |
|------|-----------|---------|
| Minimum tokens | 400 | `risk_too_short` |
| Minimum unique tokens | 150 | `risk_low_unique` |
| Confidence threshold | 0.5 | `low_confidence_item1a` |
| Quality gate failed | - | `quality_gate_failed` |

Years failing quality gates are excluded from similarity matrices.

---

## Troubleshooting

### "SEC_USER_AGENT env var is required"

Set the environment variable:
```bash
export SEC_USER_AGENT="Your Name your@email.com"
```

Or use cached submissions:
```bash
python sec_build_universe.py --submissions-zip _cache/submissions.zip
```

### Missing years in similarity heatmap

Years with confidence < 0.5 are excluded. Check:
1. `public/data/sec_narrative_drift/{TICKER}/filings.json` - look for `confidence` values
2. Re-run extraction: `python refresh_risk_cache_from_html.py --tickers TICKER`
3. Rebuild: `python sec_fetch_and_build.py --ticker TICKER --submissions-zip _cache/submissions.zip`

### Cache out of sync

```bash
python rebuild_ticker_year_index_from_cache.py
python refresh_risk_cache_from_html.py
python sec_build_universe.py --submissions-zip _cache/submissions.zip
```

### Type checking

```bash
pip install pyright
pyright  # Uses pyrightconfig.json at repo root
```

---

## Data Flow Diagram

```
SEC EDGAR API
     |
     |----------------------------------------------------------+
     |                                                          |
     v                                                          v
submissions.zip ----------> sec_fetch_and_build.py <--- filing HTML/TXT
     |                              |
     |                              v
     |                    sec_extract_item1a.py
     |                              |
     |                              v
     |                 +------------------------+
     |                 |   data/sec_cache/      |
     |                 |   - filing.txt.gz      |
     |                 |   - filing_meta.json   |
     |                 |   - risk/item_1a.txt.gz|
     |                 |   - risk/rf_meta.json  |
     |                 `------------------------+
     |                              |
     |                              v
     |                    sec_metrics.py
     |                    sec_quality.py
     |                              |
     |                              v
     |                 +------------------------+
     |                 | public/data/.../       |
     |                 |   - meta.json          |
     |                 |   - filings.json       |
     |                 |   - metrics_*.json     |
     |                 |   - similarity_*.json  |
     |                 |   - shifts_*.json      |
     |                 |   - excerpts_*.json    |
     |                 `------------------------+
     |                              |
     |                              v
     |                    sec_build_index.py
     |                              |
     |                              v
     |                       index.json
     |
     v
refresh_risk_cache_from_html.py <--- (re-extract without SEC API)
rebuild_ticker_year_index_from_cache.py <--- (rebuild index from cache)
```

---

## Logging

Pipeline scripts use structured logging via `sec_logging.py`:

```python
from sec_logging import get_logger
logger = get_logger(__name__)
logger.info("Processing ticker %s", ticker)
```

Set log level via environment variable:
```bash
export SEC_LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

---

## External Dependencies

- `requests` - HTTP client
- `beautifulsoup4` - HTML parsing
- `scikit-learn` - TF-IDF, cosine similarity
- `pyyaml` - Config parsing

Install all: `pip install -r requirements.txt`
