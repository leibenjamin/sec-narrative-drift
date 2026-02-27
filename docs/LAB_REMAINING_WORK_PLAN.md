# SEC Narrative Drift Lab - Remaining Work Plan (Codex Execution Doc)
Last updated: 2026-02-23 (full-section v2 crash-recovery sync)
Scope: deterministic pipeline + React UI Lab-first product flow
Showcase tickers: NVDA, KO, WM, GE
Core time window: FY2022+ adjacent year pairs (12 runtime pairs: NVDA/KO/WM/GE x 2022-2023, 2023-2024, 2024-2025)

## Hard constraints (DO NOT VIOLATE)
- Deterministic only in the shipped app; no runtime ML/LLM calls.
- No POS taggers.
- Do NOT change baseline public JSON schemas or lab output envelope keys.
- Treat SEC-derived text as untrusted:
  - No HTML rendering of SEC text (no `dangerouslySetInnerHTML`, no raw HTML injection).
  - Highlighting must be done with safe React nodes, not HTML strings.
  - Avoid inserting untrusted text into attribute contexts (id/class/style/href).

## Current status (as reported by operator/Codex)
- Phase 0 complete:
  - deterministic baseline shipped/locked,
  - post-deploy helper added: `scripts/lab_postdeploy_verify.py`,
  - gates passing: `npm run lab:predeploy`, `npm run lab:portfolio`, `npm run build`.
- Phase 1 complete:
  - RAW prerequisite audit added: `scripts/lab_build_raw_prereq_audit.py`,
  - RAW outputs backfilled for all eligible showcase adjacent pairs,
  - audit report added: `reports/lab_raw_prereq_audit.md`.
- Phase 2 complete (full-section v2 baseline):
  - manifest/run-pack generator added: `scripts/lab_build_llm_run_manifest.py`,
  - manifest validator added: `scripts/lab_validate_llm_manifest_outputs.py`,
  - generated artifacts:
    - `reports/lab_llm_run_manifest.md`
    - `reports/lab_llm_run_manifest.json`
    - local-only `bundles/llm_run_pack_<UTCSTAMP>/inputs/*` + `THREAD_STARTERS.md`.
  - current Codex full-section manifest state: `84/84` LLM targets present (`raw` + `deboilerplated`).
- Phase 2 hardening pass complete for baseline ChatGPT campaign:
  - strict zero-touch reproducibility contract and docs refreshed,
  - strict validator enforces citation/evidence, snippet/verbatim, ordering, and provenance constraints,
  - day-precision run labels enforced (`YYYY-MM-DD_...`),
  - ChatGPT baseline strict snapshot is now clean on migrated paths:
    `missing=0`, `invalid=0`, `present_flag_mismatch=0`.
- Phase 3 complete (implementation):
  - Lab explainer added ("What am I looking at?"),
  - explicit missing artifact states with expected path + requested URL + copy-debug payload,
  - SEC text safety doc added: `docs/SEC_TEXT_SAFETY.md`.
- Phase 4 complete (moderate cleanup):
  - stale/non-canonical data moved into `attic/`,
  - canonical docs added: `docs/00_DOC_INDEX.md`, `docs/PORTFOLIO_STORY.md`.
- Phase 5 complete (Lab-first UI pivot):
  - routes kept stable but behavior is now Lab-only (`/company/:ticker` always Lab),
  - `tab=overview` normalized to `tab=lab`,
  - Home/Showcase/Methodology rewritten around Lab narrative and showcase scope,
  - runtime dependencies on legacy `src/lib/data.ts` + pre-Lab overview components removed,
  - retired pre-Lab UI modules archived into `attic/`.
- Phase 6 security and best-practices hardening complete:
  - scheduled workflow moved from direct push to PR flow with pinned action SHAs and no test bypass,
  - Python workflow dependencies pinned in `scripts/requirements.txt`,
  - frontend loader enforces strict detector-aware LLM sidecar contract (provenance/artifacts),
  - ticker/path containment hardening added in frontend loader + strict validator,
  - CSP tightened to remove `style-src 'unsafe-inline'` after style-class refactor,
  - lint scope now excludes local-only archival artifacts (`bundles/**`, `attic/**`, `handoff/**`),
  - hash-aware `SCRIPT_VERSION` applied to active workflow scripts.
- Phase 7 complete (multi-LLM path/campaign refactor + full-section v2 hard-cut):
  - single source-of-truth track/campaign registry added: `scripts/lab_output_tracks.py`,
  - hard-cut output migration complete to canonical track-aware paths:
    `.../outputs/<detector_id>/<track_slug>/lab_<...>__<track_slug>.json`,
  - migration integrity reports emitted:
    - `reports/lab_pre_migration_inventory.md`
    - `reports/lab_pre_migration_hashes_chatgpt52ext_42.json`
    - `reports/lab_post_migration_hashes_chatgpt52ext_42.json` (mismatch=0),
  - additive public indexes generated:
    - `public/data/sec_narrative_drift_lab/lab_llm_campaigns_v1.json`
    - `public/data/sec_narrative_drift_lab/lab_llm_variants_v1.json`
    - `public/data/sec_narrative_drift_lab/lab_method_tracks_v1.json`,
  - Lab UI now supports campaign-aware LLM selectors with query params (`llmA`, `llmB`), campaign metadata, and quick diff strip.
  - runtime hard-cut now shows runtime-visible `full_section_v2` campaigns only (`focuspack_v1` hidden),
  - Codex full-section campaign artifacts regenerated across both lenses (`84` targets) via `scripts/lab_generate_codex_campaign_outputs.py`,
  - strict Codex validation clean: `targets=84`, `missing=0`, `invalid=0`, `present_flag_mismatch=0`,
  - ChatGPT full-section campaign intentionally pending for second wave: `targets=84`, `missing=84`, `invalid=0`, `present_flag_mismatch=0` (allow-missing validation),
  - variants index now reflects runtime truth: `targets=252`, `present=168`, `valid=168`, `missing=84`,
  - source/deboiler audit report added: `reports/lab_full_section_source_audit.md` (canonical source remains `sections/*.txt`, sec_cache used for audit comparison),
  - non-blocking quality audit added and passing:
    - `reports/lab_llm_codex_quality_audit.md`
    - delta template uniqueness: `20/21`
    - evidence-why uniqueness ratio: `0.464`
    - confidence levels present: `0.50`, `0.75`.
- Post-rewrite closeout hardening complete:
  - local-only recurrence guard added: `scripts/lab_guard_local_only_paths.py`,
  - `lab:predeploy` now runs `lab:guard-local` before registry/smoke,
  - CI gate workflow added: `.github/workflows/lab_gates.yml`,
  - full-section pipeline orchestrator added: `scripts/lab_run_fullsec_campaign_pipeline.py`.

Remaining human/manual work (post-hardening):
- publish screenshot verification for deployed Deep Dive v3 states (incognito),
- complete ChatGPT full-section second wave (`84` outputs) before re-enabling full A/B compare defaults,
- optional editorial fine-tuning passes for Codex prose style (not contract-blocking).
- continue LLM-first pivot: master outline compare artifacts as canonical unit with deterministic projection to legacy LLM detector envelopes.
- deterministic-first runtime behavior for pairs where LLM sidecars are not yet available (explicit missing/debug payloads remain required).

Repository policy note:
- `reports/*`, `bundles/*`, `scripts/_reports/*`, `scripts/_cache/*`, and `analysis_exports/*` are local-only and intentionally untracked.

---

# PHASE 0 - Ship and lock the deterministic baseline (DEBOILERPLATED)
Goal: Get the GO deterministic Lab state deployed and verifiably live.

## 0.1 Make git state clean and reproducible
1) `git status` must be clean after committing any generated outputs/registry/reports that are meant to ship.
2) Commit message convention:
   - `lab: backfill deterministic outputs 2019-2024`
   - `lab: rebuild registry + gates`
   - `lab: UI reload button / cache fixes` (if applicable)

## 0.2 Run the predeploy gates locally (must pass)
- `npm run lab:predeploy`  (registry + smoke; portfolio gate may be separate depending on current package.json)
- `npm run lab:portfolio`  (must be GO for the deterministic baseline)
- `npm run build`

## 0.3 Deploy
- Push to `origin/main`.
- Trigger the hosting build (Cloudflare Pages or whatever pipeline currently publishes `dist/`).

## 0.4 Post-deploy verification (fast, no guesswork)
Open these in an incognito window:
1) `/sec-narrative-drift/data/sec_narrative_drift_lab/lab_cases_v1.json`
   - confirm `updated_at` matches your latest commit build time.
2) For each ticker, open ONE deterministic output file referenced by the registry (deboilerplated):
   - e.g. `.../NVDA/outputs/det_logodds_terms_v1/<file>.json`
   - e.g. `.../KO/outputs/det_jsd_ngrams_v1/<file>.json`
3) Load the site:
   - NVDA Lab tab
   - KO Lab tab
Confirm:
- "Available outputs" counts look correct for the selected case/lens.
- No silent empties caused by 404/schema errors. If something fails, the UI should show a debug path/error (not blank).

## 0.5 Only if needed: address CDN caching safely
If the JSON URLs in (0.4) already show the newest content, DO NOTHING.
If they show stale content after deploy:
- Prefer a targeted purge (purge-by-URL) for:
  - `/sec-narrative-drift/data/sec_narrative_drift_lab/lab_cases_v1.json`
  - and any specific missing output JSON paths.
- Avoid "purge everything" unless you truly need it.

Additionally, add cache headers for lab data to reduce confusion:
- Patch `public/_headers` (or equivalent) to include `/data/sec_narrative_drift_lab/*.json`
  - either short max-age or conservative caching while you iterate.

Acceptance criteria for Phase 0:
- Live registry `updated_at` matches latest deploy.
- Live site shows deterministic outputs for all required runtime pairs (FY2022+ adjacents) under deboilerplated.
- No "empty card" that is actually caused by missing file/path/schema.

---

# PHASE 1 - Fill RAW lens deterministically (for all available pairs)
User question: "Can raw be filled in now for all these year-pairs?"
Answer: YES **if** raw source texts exist for each (ticker, year) pair.

Important: RAW is not required for shipping, but lab pages would look emptier without RAW.

## 1.1 Determine whether "raw" source sections exist
We need raw Item 1A text for each ticker+year.
Common locations (verify actual paths in repo):
- `scripts/_reports/risk_extraction_bundle/sections/<TICKER>_<YEAR>_item_1a.txt`
- raw/edgar variants may exist depending on your extraction pipeline naming.

Codex task:
- Implement a script or add a mode to existing scripts to print a matrix:
  - rows: ticker-year
  - cols: raw exists? deboilerplated exists?
- Output: `reports/lab_raw_prereq_audit.md`

## 1.2 Generate raw outputs (deterministic detectors only)
If raw texts exist:
- Run `build_lab_outputs.py` with `--lenses raw` for:
  - all tickers NVDA, KO, WM, GE
  - all adjacent pairs in FY2022+ runtime scope (2022-2023, 2023-2024, 2024-2025)
  - detectors: the same 6 deterministic detectors

Example shape (adjust to your CLI):
- `python scripts/build_lab_outputs.py --tickers KO --pairs 2019-2020,... --lenses raw --detectors <6detectors>`

## 1.3 Rebuild registry + gates
- `npm run lab:registry`
- `npm run lab:smoke`
- `npm run lab:portfolio` should remain GO (it should not require raw unless you explicitly add that requirement)
- `npm run build`

## 1.4 UI sanity check
- Lab should default to deboilerplated (already preferred).
- When switching to RAW, it should show outputs for the same case if raw was generated.

Acceptance criteria for Phase 1:
- Raw lens is available in UI for all pairs where raw prerequisites exist.
- Switching lenses never yields "silent empty" when files exist.

---

# PHASE 2 - Fill LLM precompute outputs for ALL pairs (your ChatGPT runs)
This is the "fully fleshed out" goal.

Key rule: LLM runs do NOT happen at runtime.
They are offline precompute artifacts stored as JSON.

## 2.1 Decide the required LLM coverage
For a portfolio-ready experience, recommended:
- For every required adjacent pair (2019-2024) for each showcase ticker:
  - LLM delta brief (precomputed)
  - LLM excerpt picker (precomputed)
- Lens: deboilerplated (recommended as default).

## 2.2 Create an LLM run manifest (Codex-generated)
Codex should generate:
- `reports/lab_llm_run_manifest.md`
- `reports/lab_llm_run_manifest.json` (machine-friendly)
Each entry includes:
- ticker
- year_from, year_to
- lens (deboilerplated)
- expected output paths:
  - `public/data/sec_narrative_drift_lab/<TICKER>/outputs/det_llm_delta_brief_v1/<filename>.json`
  - `public/data/sec_narrative_drift_lab/<TICKER>/outputs/det_llm_excerpt_picker_v1/<filename>.json`
- input bundle path(s) you will attach to ChatGPT threads

## 2.3 Generate all LLM input bundles (Codex)
Codex should generate full-section v2 run-pack inputs for every manifest line:
- Pair manifest under:
  - `bundles/llm_run_pack_<UTCSTAMP>_<CAMPAIGN_ID>/inputs/pair/<TICKER>_<YFROM>_<YTO>_10k_item1a_<LENS>_edgar.json`
- Year files under:
  - `bundles/llm_run_pack_<UTCSTAMP>_<CAMPAIGN_ID>/inputs/year/<TICKER>_<YEAR>_10k_item1a_<LENS>_edgar__pair_<YFROM>_<YTO>.json`

Also generate:
- `bundles/.../THREAD_STARTERS.md` that contains copy/paste ready prompts per pair.

## 2.4 You run ChatGPT (manual)
You do the runs, paste JSON-only outputs, save them to the expected output paths.

## 2.5 Validate + migrate + gate
After you drop in the outputs:
- run the migration/compat script (if needed):
  - `python scripts/lab_migrate_llm_outputs_section_id.py`
- run schema validation (Codex should ensure you have a validator; if not, add one):
  - `python scripts/lab_validate_outputs.py --llm` (or equivalent)
- rebuild registry:
  - `npm run lab:registry`
- smoke check:
  - `npm run lab:smoke`
- build:
  - `npm run build`

Acceptance criteria for Phase 2:
- For each pair, LLM cards render with content (not "precomputed but not available").
- Any missing LLM output is displayed as an explicit "missing artifact" state with the expected path shown.

---

# PHASE 3 - Portfolio polish (make it obvious, credible, and safe)
Goal: Hiring managers should "get it" in 30 seconds, and experts shouldn't cringe.

## 3.1 UX: reduce confusion, increase trust
- Add a small "What am I looking at?" explainer at top of Lab:
  - deterministic-only
  - what each detector measures
  - what "coverage/confidence/drift" mean (plain English + link to methodology)
- Improve empty/missing states:
  - show: "Missing artifact" + expected file path + suggestion: "run lab:predeploy"
- Add "Copy debug info" button for errors:
  - includes ticker, pair, lens, detector, requested URL, and any schema issue.

## 3.2 Security audit: prevent XSS/injection from SEC text
Codex must:
- Search for unsafe APIs:
  - `dangerouslySetInnerHTML`, `innerHTML`, `insertAdjacentHTML`
- Ensure all SEC-derived text is rendered only as text nodes.
- Ensure highlight logic does not generate HTML strings.

Add a short `docs/SEC_TEXT_SAFETY.md` explaining:
- SEC text is untrusted
- React escaping is relied on
- unsafe HTML APIs are forbidden
- (optional) CSP policy if supported by hosting

## 3.3 Performance and ergonomics
- Ensure output fetches don't permanently cache failures:
  - rejected promises must be evicted (already done)
  - provide a "Reload outputs" control (already done)
- Consider adding a tiny debounce for rapid lens/method toggles.
- Keep payload sizes reasonable (cap evidence blocks, lazy-render long paragraphs).

Acceptance criteria for Phase 3:
- No blank confusing states: every absence is explained.
- No unsafe rendering paths exist.
- Lab feels "productized", not "debug UI".

---

# PHASE 4 - Repo cleanup (remove pre-Lab clutter without breaking archaeology)
Goal: reduce Codex confusion and improve portfolio impression.

## 4.1 Create an /attic (or /archive) policy
- Move old bundles/scripts/docs that are not part of the shipped product into:
  - `attic/` (kept, but clearly non-shipping)
- Add `attic/README.md` explaining:
  - why it exists
  - what's in there
  - "not used by production build"

## 4.2 Reduce noise
- Ensure `scripts/_cache/` remains gitignored.
- Remove outdated one-off scripts that duplicate the new Lab pipeline:
  - but only after verifying nothing imports them.

## 4.3 Canonical docs
Create/update:
- `docs/00_DOC_INDEX.md` (single source of truth)
- `docs/LAB_REMAINING_WORK_PLAN.md` (this doc)
- `docs/PORTFOLIO_STORY.md` (how to demo the app in an interview)

Acceptance criteria for Phase 4:
- Repo tree reads clean and intentional.
- New contributors (or hiring managers) can find the "main path" fast.
- Codex Agent Mode is less likely to latch onto dead code.

---

# CODEx: One-shot Agent Prompt (surgical execution)
You are GPT-5.3-Codex in Agent mode (Extra High reasoning).
Implement Phase 0 completely and prepare Phase 1-4 scaffolding without blocking deploy.

Do:
1) Create `docs/LAB_REMAINING_WORK_PLAN.md` from the latest version in chat (edit for repo specifics).
2) Add post-deploy verification helper script:
   - `scripts/lab_postdeploy_verify.py`
   - It should print the 3 URLs to open and what values to confirm (updated_at, etc.).
3) Add `reports/lab_raw_prereq_audit.md` generator:
   - prints which ticker-years have raw text available vs deboilerplated.
4) Add `reports/lab_llm_run_manifest.{md,json}` generator:
   - lists every required adjacent pair (2019-2024) for NVDA/KO/WM/GE and the expected LLM output paths.
5) Run:
   - `npm run lab:predeploy`
   - `npm run lab:portfolio`
   - `npm run build`
6) If all pass, commit with a single clean commit:
   - `lab: ship deterministic baseline + manifests`
7) Push to origin/main.

Do NOT:
- change any JSON schemas or envelope keys.
- add runtime LLM/ML.
- add POS tagging.
- introduce any unsafe rendering of SEC text.

Output:
- A short summary of what you changed
- Exact commands you ran
- Any files you moved into `attic/`
- Any remaining TODOs for the human (LLM runs)
