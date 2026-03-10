# Attic Policy



This directory stores non-canonical historical artifacts that are not used by the shipped Lab experience.



## Why this exists

- Keep production runtime paths clear and deterministic.

- Preserve older artifacts for archaeology without leaving them on active fetch paths.

- Reduce confusion for contributors and coding agents.



## Canonical Lab data paths

- Registry: `public/data/sec_narrative_drift_lab/lab_cases_v1.json`

- Deterministic outputs: `public/data/sec_narrative_drift_lab/<TICKER>/outputs/<detector_id>/<track_slug>/lab_<...>__<track_slug>.json`

- LLM outline runtime outputs: `public/data/sec_narrative_drift_lab/<TICKER>/outputs/llm_outline_compare_runtime/<campaign_slug>/lab_<...>__<campaign_slug>.json`

- LLM outline structured outputs: `public/data/sec_narrative_drift_lab/<TICKER>/outputs/llm_outline_compare_structured/<campaign_slug>/lab_<...>__<campaign_slug>.json`



## Typical attic candidates

- Older pair artifacts no longer used by the active shipped product.

- Focuspack-era or synthetic campaign outputs that remain useful for archaeology only.

- Legacy detector-shaped LLM artifacts that were superseded by outline-compare artifacts.

- Historical docs or reports that are intentionally preserved but no longer canonical.



## Safety checks before moving files

- Active runtime indexes no longer reference the files.

- Runtime code paths no longer construct or request those paths.

- Canonical replacement artifacts already exist where the shipped app expects them.



## Production impact

- `attic/` content is not part of production fetch paths.

- The app runtime continues to resolve only canonical static JSON under `public/data/sec_narrative_drift_lab/`.

## Current archived sets

- Legacy `det_llm_delta_brief_v1` and `det_llm_excerpt_picker_v1` public-output trees that are no longer part of the active shipped runtime surface.
- Legacy flat `public/data/sec_narrative_drift_lab/llm_inputs/` and `llm_outputs/` mirrors that were superseded by `llm_inputs_v2` and outline-compare runtime outputs.
- Compatibility scripts may fall back to attic copies when older review-pack or archaeology workflows still reference these files.
- Local project-instruction text assets that were removed from the shipped public runtime surface once thread starters and input files became sufficient for public reruns.

