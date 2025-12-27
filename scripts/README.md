# Scripts

Setup:
1) python -m venv .venv
2) .venv\\Scripts\\activate
3) pip install -r scripts/requirements.txt

Usage:
- python scripts/sec_fetch_and_build.py --help

Notes:
- Pipeline tickets will add SEC fetching and fixture-first extraction.
- Prefer fixtures in scripts/sample_fixtures/ before live SEC calls.
