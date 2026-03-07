Build `llm_outline_compare_insight` for the attached case.

Required sections:
1. `outline_prev`
2. `outline_curr`
3. `node_alignment`
4. `material_changes`
5. `evidence_bank`
6. `lens_divergence`
7. `risk_graph_prev`
8. `risk_graph_curr`
9. `change_mechanisms`
10. `uncertainty_and_limits`
11. `investor_relevance`
12. `executive_digest`
13. `insight_cards`
14. `evidence_map`
15. `insight_coverage`
16. `ui_contract`
17. `projection_contract`
18. `provenance`

Modeling requirements:
- Keep all filing-only constraints from v2 fields (no external claims).
- Create a 3-level outline for each year with stable `node_id` values.
- Keep outline nodes structure-aware: do not flatten everything into topic bullets.
- Use change taxonomy only from:
  `added`, `removed`, `moved`, `split`, `merged`, `reworded`, `intensified`, `softened`, `stable`.
- Minimize false novelty; if content is mainly relocated/reordered, prefer `moved`/`stable`.
- In `material_changes`, rank by salience (0-1), prioritize meaning shifts, and include concrete case-specific caveats.
- `executive_digest.summary_text` must be concise, filing-faithful, and useful for investor/analyst review.
- `insight_cards` must include both `difference` and `similarity` insight types.
- Each insight must include direct evidence links for both years where applicable:
  - `evidence_refs_prev`, `evidence_refs_curr`, and `evidence_ref_ids`.
- Every `evidence_ref_ids` item must resolve to an `evidence_map.evidence_id`.
- `evidence_map` snippets must be verbatim contiguous substrings from mapped paragraphs.
- `ui_contract` must provide deterministic consumption order and grouping:
  - `default_selected_insight_id`
  - `recommended_insight_order`
  - `suggested_clusters`.
- `risk_graph_prev` and `risk_graph_curr` must encode explicit `driver -> exposure -> impact`.
- Every `change_mechanisms` row must include `mechanism`, `transmission_channel`, `business_effect`, and `time_horizon`.
- Include at least one top-ranked material change that cites non-opening paragraphs for both years when available.

