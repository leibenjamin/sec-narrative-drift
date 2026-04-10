# P4 Novelty Ledger Contract v2

- contract_id: `p4_novelty_ledger_contract_v2`
- protocol_family_id: `p4_novelty_ledger_v1`
- status: `packet-local tightening for Wave 4E3.5`

## Scope

- Use only the supplied business-document inputs.
- Treat this as a narrow, evidence-first, filing-only comparison protocol.
- Keep the result investor-readable. Do not turn the ledger into a large taxonomy.
- Return JSON only. No markdown, no prose outside the JSON object.
- Do not invent evidence ids, quotes, year labels, paragraph ids, source locators, novelty claims, or completion claims.

## Required Output Shape

Return exactly one top-level object with exactly three keys:

- `change_brief`
- `novelty_ledger`
- `evidence_bundle`

The `change_brief` object must include:

- `summary_one_liner`
- `lead_shift`
- `needle_change`
- `novelty_vs_reuse`
- `main_caveat`

Each section except `main_caveat` must be shaped as:

```json
{ "text": "string", "evidence_ids": ["string"] }
```

`main_caveat` must be shaped as:

```json
{
  "text": "string",
  "evidence_ids": ["string"],
  "caveat_type": "input_limit|evidence_limit|method_limit|comparison_limit|other"
}
```

The `novelty_ledger` object must include all five sections below, each as an array. Use an empty array if a section has no supported items.

- `fresh_2025_specifics`
- `reused_framework_language`
- `intensified_or_broadened_points`
- `deemphasized_or_removed_points`
- `ambiguities_or_boundary_notes`

Every novelty-ledger item must be shaped as:

```json
{ "label": "string", "text": "string", "evidence_ids": ["string"] }
```

The `evidence_bundle` object must include:

```json
{
  "items": [
    {
      "evidence_id": "string",
      "year_label": "string",
      "paragraph_id": "string",
      "quote_text": "string",
      "source_locator": {
        "accession_number": "string|null",
        "filing_date": "string|null",
        "form_type": "string",
        "section_id": "string",
        "source_path": "string|null",
        "char_start": "integer|null",
        "char_end": "integer|null"
      },
      "short_note": "string|null"
    }
  ]
}
```

## Change-Brief Rules

- Keep each section compact and filing-grounded.
- Make the fresh-vs-reused distinction explicit in `novelty_vs_reuse`.
- Use `main_caveat` for real method or comparison limits, not for hedging away supported claims.

## Category-Boundary Rules

### `fresh_2025_specifics`

Use only for items that are clearly newly introduced in FY2025.

These usually include:

- newly named rules or regimes
- newly named products, examples, or incidents
- newly introduced bullets or examples
- newly introduced concrete disclosures
- newly introduced specific numeric or date-linked examples

Rules:

- If the theme already materially exists in FY2024, default to not fresh.
- The item text must explicitly say what is newly introduced in FY2025.
- Added detail under an old theme is not enough by itself.
- If the best argument for freshness is only that FY2025 is more specific, default to `intensified_or_broadened_points` instead.

### `reused_framework_language`

Use for recurring structural or thematic language that is materially present across both years without a meaningful change in scope or specificity.

Rules:

- This bucket is not for "boring language." It is for stable filing scaffolding or persistent theme framing.
- Use it when the core warning, framing, and practical meaning are substantially unchanged across years.
- Minor wording cleanup or light trimming does not make an item fresh.

### `intensified_or_broadened_points`

Use when the theme already exists in FY2024 but FY2025 does one or more of the following:

- expands scope
- adds a new example under an existing theme
- increases specificity
- elevates prominence
- widens operational consequences

Rules:

- If there is any reasonable argument that an item is "fresh" only because it adds detail to an old theme, default here instead of `fresh_2025_specifics`.
- New examples inside an already existing risk family usually belong here.
- Standard-thinking runs should prefer this bucket over over-claiming novelty.

### `deemphasized_or_removed_points`

Use only with extra caution.

Include an item only if FY2024 contained a concrete example, framing, or emphasis that FY2025 clearly omits, generalizes, or downplays.

Rules:

- Do not equate loss of a named example with disappearance of the underlying theme.
- The item text must explicitly say whether the apparent removal looks like:
  - likely true omission or deemphasis
  - or only a boundary or interpretation question
- If the evidence does not clearly support true deemphasis, move the item to `ambiguities_or_boundary_notes`.

### `ambiguities_or_boundary_notes`

Use for any item where:

- fresh versus intensified is unclear
- a named-example omission may be mistaken for theme removal
- the evidence does not support a confident category assignment

Rules:

- This is the safety bucket for boundary uncertainty.
- Standard-thinking runs should use this bucket rather than overstating novelty.
- If classification confidence is meaningfully limited, say so directly.

## Evidence Discipline

- Every `evidence_bundle.items[].quote_text` value must be a verbatim substring of the mapped paragraph text.
- Evidence ids must map cleanly to the cited `paragraph_id` and `source_locator` from the tagged inputs.
- Do not paraphrase quote text in `evidence_bundle`.
- If unsure, shorten the quote rather than paraphrasing.
- Every evidence id cited in `change_brief` or `novelty_ledger` must resolve to an `evidence_bundle` item.
- Keep quotes contiguous and filing-grounded.

## Boundary Guidance

- A new FY2025 export-control example under a theme already present in FY2024 usually belongs in `intensified_or_broadened_points`, not `fresh_2025_specifics`.
- A newly named FY2025 rule or regime with its own date-linked disclosure usually belongs in `fresh_2025_specifics`.
- A FY2024 named product example that disappears in FY2025, while the broader demand-risk theme remains, usually belongs in `ambiguities_or_boundary_notes` unless the filing clearly downplays that example category.
- A stable recurring paragraph or risk frame present in both years with only wording cleanup belongs in `reused_framework_language`.
- A FY2025 paragraph that keeps the old theme but adds operational consequences, wider geography, or a broader affected-product set usually belongs in `intensified_or_broadened_points`.
- A FY2025 omission should go to `deemphasized_or_removed_points` only when the evidence supports real deemphasis of the concrete example or framing, not just drafting consolidation.

## Practical Defaults

- Default to narrower claims.
- Default borderline fresh claims to `intensified_or_broadened_points` or `ambiguities_or_boundary_notes`.
- Keep the ledger compact, reviewable, and evidence-first.
