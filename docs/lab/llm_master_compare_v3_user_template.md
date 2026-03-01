Build `llm_outline_compare_v1` for the attached case.

Required sections:
1. `outline_prev`
2. `outline_curr`
3. `node_alignment`
4. `material_changes`
5. `evidence_bank`
6. `lens_divergence`
7. `provenance`

Modeling requirements:
- Create a 3-level outline for each year with stable `node_id` values.
- Keep outline nodes structure-aware: do not flatten everything into topic bullets.
- Use change taxonomy only from:
  `added`, `removed`, `moved`, `split`, `merged`, `reworded`, `intensified`, `softened`, `stable`.
- Minimize false novelty:
  - if content is mainly relocated/reordered, prefer `moved`/`stable` over `added`/`removed`.
- In `material_changes`, rank by salience (0-1) and include explicit caveat text.
- In `material_changes`, prioritize substantive meaning shifts over lexical restatements.
- Use case-specific caveats tied to evidence quality/coverage (no generic caveats).
- Each `material_changes.title` must include case-specific anchor language that appears in cited evidence snippets.
- Each `node_alignment.rationale` must describe a direct contrast mechanism between years, not tone-only restatement.
- Each caveat must state a concrete evidence-quality limitation (coverage, boundary, mapping, or specificity constraint).
- Ensure every `material_changes.evidence_refs` item resolves to an `evidence_bank` entry.
- For change classes other than `added`/`removed`, ensure evidence coverage references both years.
- Keep filing-only claims in this artifact (no external web claims here).
