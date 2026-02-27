# Public Tone Policy

## Purpose
Public UI text, public repository prose, and authored comments must remain audience-neutral and product-focused.

## Required rules
1. Do not frame the app or repository as an employment-targeted artifact.
2. Do not frame the app or repository as machine-authored output.
3. Keep copy directed at public users of the product, not at the creator.
4. Keep reproducibility and model identifiers when operationally required.
5. Keep SEC corpus text and filing excerpts unchanged; this policy applies to authored text.

## Enforcement
1. `scripts/lab_guard_public_tone.py` scans `src/`, `docs/`, `README.md`, `.github/workflows/`, and `package.json`.
2. The guard runs via:
   - `npm run lab:guard-tone`
   - `npm run lab:predeploy`
3. CI runs the same guard through the lab gates workflow.
