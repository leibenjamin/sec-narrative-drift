# Case Quality Review Log

Last updated: 2026-03-10

Purpose: canonical human-review ledger for active Core4 FY2024 -> FY2025 compare artifacts.

Use this file to decide which artifacts are safe to keep, defer, rerun later, or block from demos and screenshots. This ledger is the human-review complement to validator and blocker-audit reports.

Status meanings:
- `keep`: acceptable for the shipped app and normal demos
- `defer`: technically usable, but not preferred for showcase emphasis yet
- `rerun later`: not urgent for the current public surface, but should be revisited
- `blocked`: do not use until rerun or repair

Safe-for-demo meanings:
- `yes`: acceptable for homepage, walkthrough, or screenshots
- `conditional`: usable in the product, but not a preferred demo artifact
- `no`: keep out of default demos and screenshots

## Active Review Ledger
| Ticker | Lens | Campaign | Status | Safe for Demo | Rationale | Evidence Notes | Visible Artifact Risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NVDA | raw | Codex real | defer | conditional | Human review not completed in this pass. | Keep current canonical output unless a new blocker appears. | Needs explicit review before screenshot use. |
| NVDA | deboilerplated | Codex real | defer | conditional | Human review not completed in this pass. | Deterministic and validation gates are green. | Needs explicit review before screenshot use. |
| KO | raw | Codex real | defer | conditional | Human review not completed in this pass. | Deterministic and validation gates are green. | Needs explicit review before screenshot use. |
| KO | deboilerplated | Codex real | defer | conditional | Human review not completed in this pass. | Deterministic and validation gates are green. | Needs explicit review before screenshot use. |
| WM | raw | Codex real | keep | yes | Current rerun is materially improved and now surfaces the Healthcare Solutions / Stericycle deterioration in the lead analysis. | Lead row correctly ties ERP, billing, collection, customer loss, and delayed pricing realization to the acquisition risk story. | Later rows are slightly policy-heavy, but not severe enough to block demos. |
| WM | deboilerplated | Codex real | defer | conditional | No fresh deep review recorded in this pass. | Keep current canonical output unless a new blocker appears. | Needs explicit human salience review before screenshot use. |
| GE | raw | Codex real | keep | yes | Current output leads with the right LEAP / GE9X installed-base and services execution shift. | Strong evidence sits in 2024:19 versus 2025:18, with delivery, durability, time on wing, and repair turnaround surfaced. | Secondary rows still need stylistic vigilance for raw extraction artifacts. |
| GE | deboilerplated | Codex real | defer | no | Source-valid and blocker-clean, but the salience order still underrates the strongest company-specific operational shift. | LEAP installed-base / services execution is only rank 4, behind weaker demo rows. | Misprioritized for public demo use. Revisit later. |
| NVDA | raw | ChatGPT real | defer | conditional | Placeholder until human review is completed. | Validation and audit status are the gating minimum, not the final showcase judgment. | Review before screenshot use. |
| NVDA | deboilerplated | ChatGPT real | defer | conditional | Placeholder until human review is completed. | Validation and audit status are the gating minimum, not the final showcase judgment. | Review before screenshot use. |
| KO | raw | ChatGPT real | defer | conditional | Placeholder until human review is completed. | Validation and audit status are the gating minimum, not the final showcase judgment. | Review before screenshot use. |
| KO | deboilerplated | ChatGPT real | defer | conditional | Placeholder until human review is completed. | Validation and audit status are the gating minimum, not the final showcase judgment. | Review before screenshot use. |
| WM | raw | ChatGPT real | defer | conditional | Placeholder until human review is completed. | Validation and audit status are the gating minimum, not the final showcase judgment. | Review before screenshot use. |
| WM | deboilerplated | ChatGPT real | defer | conditional | Placeholder until human review is completed. | Validation and audit status are the gating minimum, not the final showcase judgment. | Review before screenshot use. |
| GE | raw | ChatGPT real | defer | conditional | Placeholder until human review is completed. | Validation and audit status are the gating minimum, not the final showcase judgment. | Review before screenshot use. |
| GE | deboilerplated | ChatGPT real | defer | conditional | Placeholder until human review is completed. | Validation and audit status are the gating minimum, not the final showcase judgment. | Review before screenshot use. |
| NVDA | raw | Claude real | defer | no | Claude lane is preregistered and hidden until the output set is complete and reviewed. | Do not promote Claude into visible compare flows yet. | Hidden lane. |
| NVDA | deboilerplated | Claude real | defer | no | Claude lane is preregistered and hidden until the output set is complete and reviewed. | Do not promote Claude into visible compare flows yet. | Hidden lane. |
| KO | raw | Claude real | defer | no | Claude lane is preregistered and hidden until the output set is complete and reviewed. | Do not promote Claude into visible compare flows yet. | Hidden lane. |
| KO | deboilerplated | Claude real | defer | no | Claude lane is preregistered and hidden until the output set is complete and reviewed. | Do not promote Claude into visible compare flows yet. | Hidden lane. |
| WM | raw | Claude real | defer | no | Claude lane is preregistered and hidden until the output set is complete and reviewed. | Do not promote Claude into visible compare flows yet. | Hidden lane. |
| WM | deboilerplated | Claude real | defer | no | Claude lane is preregistered and hidden until the output set is complete and reviewed. | Do not promote Claude into visible compare flows yet. | Hidden lane. |
| GE | raw | Claude real | defer | no | Claude lane is preregistered and hidden until the output set is complete and reviewed. | Do not promote Claude into visible compare flows yet. | Hidden lane. |
| GE | deboilerplated | Claude real | defer | no | Claude lane is preregistered and hidden until the output set is complete and reviewed. | Do not promote Claude into visible compare flows yet. | Hidden lane. |

## Current Demo Guidance
- Use `GE raw` and `WM raw` when a live compare example needs strong company-specific operational change.
- Do not use `GE deboilerplated` as the default GE screenshot or homepage narrative until the salience order is rerun and re-reviewed.
- Keep Codex and ChatGPT compare surfaces visible in the app, but only use artifacts marked `yes` or `conditional` for public walkthroughs.
- Add Claude review rows here before any runtime-visibility decision changes.

## Review Workflow
1. Validate and audit the target artifact.
2. Read the cited evidence in the filing inputs, not just the output summary.
3. Record whether the top-ranked change is the right lead story for an experienced investor or analyst.
4. Note any visible extraction-artifact phrasing that is still acceptable, deferred, or blocking.
5. Update this ledger before using the artifact in screenshots, homepage copy, or public walkthroughs.
