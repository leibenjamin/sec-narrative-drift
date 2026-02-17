# Attic Policy

This directory stores non-canonical historical artifacts that are not used by the shipped Lab experience.

## Why this exists
- Keep portfolio/runtime paths clear and deterministic.
- Preserve older artifacts for archaeology without deleting history.
- Reduce confusion for contributors and coding agents.

## Canonical Lab data paths
- Registry: `public/data/sec_narrative_drift_lab/lab_cases_v1.json`
- Canonical outputs: `public/data/sec_narrative_drift_lab/<TICKER>/outputs/<detector_id>/<filename>.json`
- LLM canonical outputs (same pattern): `public/data/sec_narrative_drift_lab/<TICKER>/outputs/det_llm_*/*`

## Moved in this cleanup
- Entire stale ticker roots:
  - `public/data/sec_narrative_drift_lab/AAPL/*`
  - `public/data/sec_narrative_drift_lab/TSLA/*`
- Flat duplicate files (legacy root-level copies):
  - `public/data/sec_narrative_drift_lab/NVDA/lab_10k_item1a_*`
  - `public/data/sec_narrative_drift_lab/KO/lab_10k_item1a_*`
  - `public/data/sec_narrative_drift_lab/WM/lab_10k_item1a_*`
  - `public/data/sec_narrative_drift_lab/GE/lab_10k_item1a_*`

## Safety checks used before moving
- `lab_cases_v1.json` has no AAPL/TSLA case references.
- `lab_cases_v1.json` output links are canonical `outputs/...` paths (no root-level `lab_10k_item1a_*` references).
- No runtime code path references `sec_narrative_drift_lab/AAPL` or `sec_narrative_drift_lab/TSLA`.
- Canonical `outputs/<detector>/...` files remain in place.

## Production impact
- `attic/` content is not part of production fetch paths.
- App runtime still resolves Lab outputs through registry canonical links and deterministic static JSON.
