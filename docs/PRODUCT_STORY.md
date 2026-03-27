# Product Story: Document Protocol Lab

## One-line pitch
Document Protocol Lab currently ships a bounded SEC Item 1A pilot across NVDA, LLY, and KO, showing how an evidence-first workflow answers first, explains protocol meaning second, and keeps deeper audit third.

## What makes the product distinctive
- Users choose one of three visible fixtures, not a broad issuer gallery.
- The default reading path starts with the filing answer and nearby evidence instead of raw metrics.
- The protocol layer stays visible as the second read so each fixture has an explicit reason to exist.
- Deeper audit remains available, but it does not lead the page.
- Deterministic methods remain the reproducible baseline underneath any model sidecars.
- Missing artifacts stay explicit instead of being silently hidden.

## Fast walkthrough
1. Open Home or Cases.
2. Start with NVDA unless you specifically want the bounded LLY contrast or the KO restraint case.
3. Read the filing answer first.
4. Use the protocol layer to understand why that fixture is in the lab.
5. Open deeper audit only when you want more structure, methods, or provenance.

## Core credibility points
- Runtime is static JSON only.
- No runtime LLM or ML calls.
- SEC text is treated as untrusted and rendered as plain text only.
- Public output paths and campaign metadata remain stable.
- Model outputs are offline sidecars with deterministic validation and runtime projection.
- The visible public pilot is fixed to `NVDA`, `LLY`, and `KO` for FY2024 to FY2025.
- `LLY` remains explicitly bounded and does not imply the full lower-audit runtime stack.
- Lower runtime registries can remain broader backstage without changing the visible pilot claim.

## Public walkthrough sequence
1. Start with the filing answer and paired evidence.
2. Read the protocol meaning second so the fixture role is explicit.
3. Open deeper audit and provenance only when you need more structure or pressure-testing.
4. Mention optional insight only when the sidecar is actually present.

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
Local validation artifacts and broader runtime registries can exist backstage, but they are not the public case list and should not widen the visible three-fixture claim.

## FAQ-ready answers
- Q: Why only three visible fixtures?
  A: Because the current product claim is intentionally narrow. NVDA gives the strongest first signal, LLY pressure-tests the protocol in a bounded policy-heavy case, and KO checks whether the same workflow stays honest on a mostly stable filing.
- Q: Why deterministic-first?
  A: Because the deploy surface stays reproducible and path-auditable. Model outputs are offline sidecars, not runtime inference.
- Q: How should LLY be described honestly?
  A: As a bounded visible case. The filing answer and protocol meaning are public, but the full lower-audit runtime stack is intentionally not implied for that issuer.
- Q: How do you prevent injection risks from filing text?
  A: The app follows `docs/SEC_TEXT_SAFETY.md`: no HTML rendering, only safe text-node rendering and controlled `<mark>` spans.
