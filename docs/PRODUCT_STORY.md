# Product Story: SEC Narrative Drift Lab

## One-line pitch
This Lab shows where a company's Item 1A risk story changed from FY2024 to FY2025 using deterministic detectors plus precomputed compare artifacts with explicit evidence and provenance.

## What makes the product distinctive
- Users choose a company, not a year pair.
- The default reading path starts with a compare-first risk narrative summary instead of raw metrics.
- Codex and ChatGPT stay visible side by side as the public compare lanes.
- Deterministic methods remain the reproducible baseline underneath the model sidecars.
- Missing artifacts stay explicit instead of being silently hidden.

## Fast walkthrough
1. Open a company page.
2. Land on that company's one active FY2024 to FY2025 case.
3. Read the risk narrative summary first.
4. Check the two core deterministic methods and the agreement panel.
5. Open outline compare for mechanisms, investor relevance, limits, and side-by-side framing.
6. Treat Insight Lens as optional when it is present.

## Core credibility points
- Runtime is static JSON only.
- No runtime LLM or ML calls.
- SEC text is treated as untrusted and rendered as plain text only.
- Public output paths and campaign metadata remain stable.
- Model outputs are offline sidecars with deterministic validation and runtime projection.
- Current shipped scope is Core4 only: `NVDA`, `KO`, `WM`, and `GE` across FY2024 to FY2025.
- Visible compare lanes are the truthful Codex real and ChatGPT 5.4 real campaigns.

## Public walkthrough sequence
1. Start with the risk narrative summary and paired filing evidence.
2. Confirm the signal with the two core deterministic methods.
3. Use agreement to see whether the deterministic methods reinforce the same story.
4. Open outline compare for the deeper structural audit.
5. Mention Insight Lens only when the sidecar is actually present.

## Public case-study framing
- Problem:
  risk-factor sections are long, repetitive, and hard to compare by eye.
- Insight:
  the useful question is whether a company is emphasizing a more important operating, regulatory, or commercial risk channel than it did a year earlier.
- Design choice:
  deterministic methods provide the hard baseline; model sidecars sit on top of that baseline without replacing it.
- Product value:
  users can move from headline interpretation to filing evidence without changing tools.

## Operator note
Local validation artifacts exist for operators, but they are not part of the shipped UX or the public product story.

## FAQ-ready answers
- Q: Why deterministic-first?
  A: Because the deploy surface stays reproducible and path-auditable. Model outputs are offline sidecars, not runtime inference.
- Q: What does model comparison add?
  A: It shows whether two strong model lanes agree on the lead story, or whether the filing supports multiple plausible emphases.
- Q: How do you prevent injection risks from filing text?
  A: The app follows `docs/SEC_TEXT_SAFETY.md`: no HTML rendering, only safe text-node rendering and controlled `<mark>` spans.
