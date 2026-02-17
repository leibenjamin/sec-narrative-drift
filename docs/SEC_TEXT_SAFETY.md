# SEC Text Safety

## Scope
- All SEC-derived text is treated as untrusted input.
- This includes filing paragraphs, headings, snippets, and any LLM precompute fields derived from filings.

## Rendering Rules
- SEC-derived text is rendered as plain text nodes in React.
- Highlighting uses safe React nodes (for example, `<mark>` around text spans), not HTML strings.
- Forbidden APIs:
  - `dangerouslySetInnerHTML`
  - `innerHTML`
  - `insertAdjacentHTML`

## URL and Path Handling
- Lab output files are fetched as static JSON only.
- Output paths are normalized to canonical `outputs/<detector>/<filename>.json` forms.
- Debug views may show expected paths and request URLs as plain text for troubleshooting.

## Why This Matters
- Filing text can contain arbitrary strings and must never be trusted as executable markup.
- Relying on React escaping plus strict no-HTML injection rules prevents XSS through filing content.

## Verification Checklist
- Search source for forbidden HTML injection APIs before release.
- Confirm detector cards and agreement states render missing/debug data as plain text.
- Keep runtime deterministic (no runtime ML/LLM execution in app code).
