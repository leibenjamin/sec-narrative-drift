# Product Story: Document Protocol Lab

## One-line pitch
Document Protocol Lab is an interactive casebook that compares three approaches to business-document reading — plain prompt, structured contract, and tagged protocol — on the same six SEC Item 1A filing pairs, so a visitor can see which approach earned the answer and which was theater.

## What makes the product distinctive
- The visible unit of comparison is the approach, not the company. Every multi-cell case renders a side-by-side of the control read (plain prompt) and the primary read (structured contract) on the same filing pair.
- The Methodology page names each approach explicitly: input shape, output shape, what it earns, when it helps, when it is theater.
- Per-case anatomy underneath — filing answer, proof, stop, appendix — is a grammar for reading one case (claim, proof, stop), distinct from the approach-comparison verdict the app produces across cases.
- The deterministic detector arm is preserved as a control arm under a disclosure, not presented as the product.
- The approach count is honest: three approaches, not five. A fourth approach has prompt templates but no authored cell data and is not claimed as live.
- Missing artifacts stay explicit rather than silently hidden.

## Fast walkthrough
1. Open Home. Read the three-approach signal and the approach-verdict tile.
2. Open an anchor case (`NVDA`, `LLY`, or `KO`). The approach comparison block is visible without a click.
3. Open the Methodology page's approach catalog for when each approach helps and when it is theater.
4. Open the deterministic-control-arm disclosure only if you want the detector perspective.

## Core credibility points
- Runtime is static JSON only.
- No runtime ML or LLM calls.
- SEC text is treated as untrusted and rendered as plain text only.
- Public approach identifiers and campaign metadata remain stable.
- Approach outputs are offline artifacts with deterministic validation and runtime projection.
- The public casebook is fixed to six cases: `NVDA`, `LLY`, `KO`, `META`, `TSLA`, `WMT`.
- `KO` ships with a single cell by design; that restraint is part of what the case demonstrates.

## Public case framing
- Problem:
  risk-factor sections are long and repetitive, and it is tempting to believe that simply asking a frontier LLM is enough.
- Insight:
  the approach matters. A plain prompt, a structured contract, and a tagged protocol produce meaningfully different reads on the same filing pair, and the difference becomes visible once the reads sit side by side on the same substrate.
- Design choice:
  the comparison is the product. Per-case depth sits underneath it, and deterministic detectors sit further underneath as a control arm.
- Product value:
  visitors can see the approach verdict (plain vs structured) without running any LLM themselves, and they can form their own judgment about which approach would survive a skeptical read.

## Operator note
Local validation artifacts and broader runtime registries can exist backstage, but they are not the public case list and should not widen the visible six-case claim or inflate the three-approach count.

## FAQ-ready answers
- Q: Why not more approaches?
  A: Three approaches have authored cell data across the public casebook. A fourth (extract-then-synthesize) has prompt templates but no cells. Claiming more than is live would be the kind of overclaim the product is built to avoid.
- Q: Why these six cases?
  A: Three anchor cases (`NVDA`, `LLY`, `KO`) span vivid answer, honest stop, and useful restraint. Three added-pressure cases (`META`, `TSLA`, `WMT`) add sharper AI enforcement, a policy shock, and a calm retail filing whose risk only surfaces once structure earns it.
- Q: Static runtime, so what does the product actually compute at view time?
  A: Nothing. All approach outputs are precomputed offline. The runtime projects static JSON. This is deliberate: the comparison visitors see is the same comparison a skeptic can audit from the published artifacts.
- Q: What about filing-text injection risk?
  A: The app follows `docs/SEC_TEXT_SAFETY.md`: no HTML rendering of SEC text, only safe text-node rendering and controlled `<mark>` spans.
