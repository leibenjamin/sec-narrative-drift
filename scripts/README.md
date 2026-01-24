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

### Live Website vs Local Development

| Aspect | Live Website | Local Development |
|--------|--------------|-------------------|
| **Data Source** | Pre-built JSON in `public/data/` | Built from cache or live SEC |
| **Updates** | Manual rebuild + deploy | On-demand rebuild |
| **Cache** | Not needed at runtime | Required for efficient iteration |
| **SEC API** | Not needed at runtime | Only for initial fetch or updates |

---

## Directory Structure

```
sec-narrative-drift/
├── data/
│   └── sec_cache/                    # Primary data cache (git-ignored)
│       ├── filings/{CIK}/{ACCESSION}/
│       │   ├── filing.txt.gz         # Normalized full filing text
│       │   ├── filing.html.gz        # Original HTML (optional)
│       │   ├── filing_meta.json      # Filing metadata
│       │   └── risk/
│       │       ├── item_1a.txt.gz    # Extracted risk section
│       │       └── rf_meta.json      # Extraction metadata + debug
│       ├── indexes/
│       │   ├── ticker_year_index.json    # Global ticker-year mapping
│       │   └── extraction_version.json   # Version tracking
│       └── reports/
│           └── cache_usage.json      # Cache statistics
│
├── public/data/sec_narrative_drift/  # Website output (committed)
│   ├── {TICKER}/
│   │   ├── meta.json                 # Company info
│   │   ├── filings.json              # Filing list with extraction status
│   │   ├── metrics_10k_item1a.json   # Drift scores, similarity
│   │   ├── similarity_10k_item1a.json # Cosine similarity matrix
│   │   ├── shifts_10k_item1a.json    # Year-over-year term shifts
│   │   └── excerpts_10k_item1a.json  # Representative text excerpts
│   └── index.json                    # Global ticker index
│
├── scripts/
│   ├── _cache/                       # Working cache (git-ignored)
│   │   ├── submissions.zip           # Bulk SEC submissions archive
│   │   ├── build_universe.log        # Build execution log
│   │   └── {TICKER}/                 # Raw HTML files (optional)
│   ├── sample_fixtures/              # Test fixtures
│   ├── resources/                    # Config files (git-ignored)
│   └── *.py                          # Pipeline scripts
```

---

## Common Workflows

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

### 3. Initial Build (From Live SEC)

Use when: First time setup, no cache exists.

```bash
# Download bulk submissions archive first (saves many API calls)
python sec_build_universe.py --download-submissions-zip

# Build all tickers
python sec_build_universe.py --submissions-zip _cache/submissions.zip
python sec_build_index.py
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

# Check public output consistency
python sec_validate_public_data.py

# Build manual review checklist
python build_risk_manual_checklist.py
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
| `sec_build_index.py` | Build global index.json | (none) |

### Cache Management Scripts

| Script | Purpose | Typical Flags |
|--------|---------|---------------|
| `sec_cache.py` | Cache utilities (library) | N/A (imported) |
| `refresh_risk_cache_from_html.py` | Re-extract from cached HTML | `--tickers AAPL,MSFT` |
| `rebuild_ticker_year_index_from_cache.py` | Rebuild index from cache | (none) |
| `fetch_missing_html_cache.py` | Download missing HTML | `--only AAPL --limit 10` |

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
| `build_canonical_terms.py` | Term normalization mapping |

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
--allow-sample-fixtures   Use test fixtures instead of live data
```

### sec_build_universe.py

```
--submissions-zip PATH        Use cached submissions archive
--download-submissions-zip    Download latest archive first
--only [anchors|stories|all]  Which ticker subset
--start-at TICKER             Resume from specific ticker
--max-count N                 Stop after N tickers
--include-20f                 Include 20-F filings
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
     │
     ├──────────────────────────────────────────────────────────┐
     │                                                          │
     v                                                          v
submissions.zip ──────────> sec_fetch_and_build.py <─── filing HTML/TXT
     │                              │
     │                              v
     │                    sec_extract_item1a.py
     │                              │
     │                              v
     │                 ┌────────────────────────┐
     │                 │   data/sec_cache/      │
     │                 │   - filing.txt.gz      │
     │                 │   - filing_meta.json   │
     │                 │   - risk/item_1a.txt.gz│
     │                 │   - risk/rf_meta.json  │
     │                 └────────────────────────┘
     │                              │
     │                              v
     │                    sec_metrics.py
     │                    sec_quality.py
     │                              │
     │                              v
     │                 ┌────────────────────────┐
     │                 │ public/data/.../       │
     │                 │   - meta.json          │
     │                 │   - filings.json       │
     │                 │   - metrics_*.json     │
     │                 │   - similarity_*.json  │
     │                 │   - shifts_*.json      │
     │                 │   - excerpts_*.json    │
     │                 └────────────────────────┘
     │                              │
     │                              v
     │                    sec_build_index.py
     │                              │
     │                              v
     │                       index.json
     │
     v
refresh_risk_cache_from_html.py ←── (re-extract without SEC API)
rebuild_ticker_year_index_from_cache.py ←── (rebuild index from cache)
```

---

## External Dependencies

- `requests` - HTTP client
- `beautifulsoup4` - HTML parsing
- `scikit-learn` - TF-IDF, cosine similarity
- `pyyaml` - Config parsing

Install all: `pip install -r requirements.txt`
