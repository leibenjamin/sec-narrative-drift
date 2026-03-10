# Product Story: SEC Narrative Drift Lab

## One-line pitch
This Lab shows how Item 1A risk disclosures change from one fiscal year to the next using deterministic detectors plus precomputed outline-compare artifacts with explicit evidence and provenance.

## What makes the product distinctive
- Deterministic methods come first, so the baseline stays reproducible and auditable.
- Codex and ChatGPT are visible side by side, not hidden behind a single-model toggle.
- Evidence is path-level and filing-backed rather than abstract model prose.
- Missing artifacts stay explicit instead of being quietly papered over.

## Fast walkthrough (30 seconds)
1. Open a showcase company page.
2. Start with the active adjacent pair for FY2024 -> FY2025.
3. Read the risk narrative summary first:
   - lead material change
   - paired prior-year versus current-year evidence
   - whether model divergence looks substantive or stylistic
4. Check the deterministic methods and agreement panel.
5. Open outline compare for mechanisms, investor relevance, limitations, and structure.

## Core credibility points
- Runtime is static JSON only.
- No runtime LLM or ML calls.
- SEC text is treated as untrusted and rendered as plain text only.
- Public output paths and campaign metadata remain stable.
- Model outputs are offline sidecars with deterministic validation and runtime projection.
- Current shipped scope is Core4 only: `NVDA`, `KO`, `WM`, `GE` across FY2024 -> FY2025.
- Visible compare lanes are the truthful Codex real and ChatGPT 5.4 real campaigns; Claude remains hidden until it earns public exposure.

## Suggested public walkthrough sequence
1. Lead narrative:
   - show the risk narrative summary and the paired evidence excerpt.
2. Deterministic support:
   - use log-odds and JSD to confirm whether the language shift is real.
3. Agreement:
   - explain whether the deterministic methods are converging or disagreeing.
4. Side-by-side model read:
   - keep Codex and ChatGPT on screen together and point out salience or framing differences.
5. Deep audit:
   - open outline compare and walk through mechanisms, investor relevance, limits, and outline structure.

## Public case-study framing
- Problem:
  - risk-factor sections are long, repetitive, and hard to compare by eye.
- Insight:
  - the meaningful question is whether a company is emphasizing a more important operating or regulatory risk channel than it did a year earlier.
- Design choice:
  - deterministic-first methods provide the hard baseline; model sidecars only sit on top of that baseline.
- Product value:
  - users can move from headline interpretation to filing evidence without changing tools.

## Operational evidence to mention
Local generated reports (`reports/*`, untracked by policy):
- `reports/lab_runtime_readiness.md`
- `reports/lab_llm_master_manifest_codex_real.json`
- `reports/lab_llm_master_manifest_chatgpt_real.json`
- `reports/lab_llm_master_validation_codex_real.md`
- `reports/lab_llm_master_validation_chatgpt_real.md`
- `reports/lab_llm_master_quality_codex_real_structured.md`
- `reports/lab_llm_master_quality_chatgpt_real_structured.md`

## FAQ-ready answers
- Q: Why deterministic-first?
  - A: Because the deploy surface stays reproducible and path-auditable. Model outputs are offline sidecars, not runtime inference.
- Q: What does model comparison add?
  - A: It shows whether two strong model lanes agree on the lead story, or whether the filing supports multiple plausible emphases.
- Q: How do you prevent injection risks from filing text?
  - A: The app follows `docs/SEC_TEXT_SAFETY.md`: no HTML rendering, only safe text-node rendering and controlled `<mark>` spans.
