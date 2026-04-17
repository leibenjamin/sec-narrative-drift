# Demo Readiness

## One-sentence product description
Document Protocol Lab is an interactive casebook that puts three approaches to business-document reading (plain prompt, structured contract, tagged protocol) side by side on the same six SEC Item 1A filing pairs so the approach verdict is visible without running any LLM.

## Recommended first-click path
- Start on Home. The approach tile is the anchor: three approaches compared across six cases.
- Open an anchor case (`NVDA` is the most vivid first read) to see the side-by-side approach comparison on a real filing pair.
- Open Methodology to see the approach catalog — input shape, output shape, what each approach earns, and when it is theater.

## What each anchor case demonstrates
- `NVDA` — strongest structural lift: the primary (structured) read surfaces shifts a plain prompt misses or flattens.
- `LLY` — honest stop tightening: the primary read keeps its claim bounded to what the filing supports, where a plain read tends to drift.
- `KO` — useful restraint: the disciplined approach produces one cell rather than five, and the product lets that be enough. The absence of a side-by-side comparison block on `KO` is itself the case.

## Added-pressure cases
- `META` — AI enforcement and platform-liability pressure become a sharper stack under structure.
- `TSLA` — a policy shock and the autonomy-commercialization pivot become visible once the approach earns them.
- `WMT` — a calm retail filing whose customer-interface risk and tariff persistence only surface with structure.

## How to explain the two levels of grammar
- App-level grammar: Read → Compare → Verdict. This is how the product compares approaches across cases.
- Page-level anatomy: filing answer → proof → stop → appendix. This is how a visitor reads one case after the approach is chosen.
- These are not the same thing. The distinctive claim is the app-level grammar; the page-level anatomy is familiar casebook reading.

## How to explain the static runtime
- Static JSON only at runtime.
- Everything in the shipped app loads from `public/data/...`.
- No runtime LLM or ML calls in the shipped app.
- Approach outputs are offline artifacts with explicit provenance and deterministic runtime projection.
- SEC text is treated as untrusted and rendered as plain text only.

## What not to overclaim
- Do not describe the product as a broad issuer gallery, benchmark suite, or whole-filing research platform.
- Do not claim more than three approaches. A fourth (extract-then-synthesize) has templates but no authored cells.
- Do not describe the deterministic detector arm as the product. It is a control arm, under a disclosure.
- Do not conflate the app-level Read / Compare / Verdict grammar with the per-case filing-answer / proof / stop anatomy. They operate at different levels and are both in the UI on purpose.
