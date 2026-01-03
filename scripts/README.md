# Scripts

Setup:
1) python -m venv .venv
2) .venv\\Scripts\\activate
3) pip install -r scripts/requirements.txt

Usage:
- python scripts/sec_fetch_and_build.py --help
- python scripts/sec_validate_cache.py --help

Type checking (optional):
- Install pyright if you want CLI checks.
- `pyright` (uses `pyrightconfig.json` at the repo root).

Notes:
- Pipeline tickets will add SEC fetching and fixture-first extraction.
- Prefer fixtures in scripts/sample_fixtures/ before live SEC calls.
- The pipeline caches normalized filings + extracted risk sections under `data/sec_cache/` (git-ignored). Set `SEC_CACHE_ROOT` to override the cache location.
