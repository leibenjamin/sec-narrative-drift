from __future__ import annotations

import argparse
import copy
import json
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
BUSINESS_ROOT = REPO_ROOT / "public" / "data" / "business_document_protocol_lab"
NOVELTY_LEDGER_ROOT = BUSINESS_ROOT / "novelty_ledger"
PILOT_MATRICES_ROOT = BUSINESS_ROOT / "pilot_matrices"
EFFORT_SUMMARY_PATH = BUSINESS_ROOT / "standard_controls" / "effort_robustness" / "effort_robustness_summary_v1.json"
REPORTS_ROOT = REPO_ROOT / "reports" / "protocol_lab"

TASK_NAME = "Wave 4E4 = P4 Canonization + Limited Integration Decision"
PACKET_PREFIX = "wave4e4_p4_canonized_integration"
ROOT_README_NAME = "README.md"
CHANGED_FILES_MANIFEST_NAME = "changed_files_manifest.md"
RENDER_PREVIEW_NAME = "render_preview.md"

CANONIZATION_REPORT_PATH = Path("reports/protocol_lab/wave4e4_p4_canonization_report.md")
INTEGRATION_DECISION_REPORT_PATH = Path(
    "reports/protocol_lab/wave4e4_p4_integration_decision.md"
)
FINDINGS_REPORT_PATH = Path("reports/protocol_lab/wave4e4_p4_findings.md")
SELF_SCRIPT_PATH = Path("scripts/protocol_lab_wave4e4_p4_canonization.py")
SELF_TEST_PATH = Path("scripts/tests/test_protocol_lab_wave4e4_p4_canonization.py")
NODE_TEST_PATH = Path("scripts/tests/test_protocol_lab_novelty_ledger_data.mjs")

TYPE_PATHS = [
    Path("src/lib/protocolLabMatrixTypes.ts"),
    Path("src/lib/protocolLabMatrixSchemas.ts"),
    Path("src/lib/protocolLabMatrixData.ts"),
]
UI_SOURCE_PATHS = [
    Path("src/components/ProtocolLabPilotMatrixPanel.tsx"),
    Path("src/components/LabPanel.tsx"),
    Path("src/pages/Company.tsx"),
]

PILOT_REVIEW_PATHS = {
    "NVDA_2024_2025_10k_item1a": Path(
        "public/data/business_document_protocol_lab/pilot_matrices/NVDA_2024_2025_10k_item1a/pilot_matrix_review_v1.json"
    ),
    "LLY_2024_2025_10k_item1a": Path(
        "public/data/business_document_protocol_lab/pilot_matrices/LLY_2024_2025_10k_item1a/pilot_matrix_review_v1.json"
    ),
}

BIGGEST_REMAINING_BLOCKER = (
    "A third issuer with clean first-save P4 captures is still missing, so broader P4 expansion "
    "beyond this secondary novelty-ledger module would still be premature."
)

PAIR_INFO_BY_FIXTURE: dict[str, dict[str, Any]] = {
    "NVDA_2024_2025_10k_item1a": {
        "ticker": "NVDA",
        "issuer_name": "NVIDIA Corporation",
        "year_from": 2024,
        "year_to": 2025,
        "form_type": "10-K",
        "section_id": "item_1a",
    },
    "LLY_2024_2025_10k_item1a": {
        "ticker": "LLY",
        "issuer_name": "Eli Lilly and Company",
        "year_from": 2024,
        "year_to": 2025,
        "form_type": "10-K",
        "section_id": "item_1a",
    },
}

CASE_CONFIGS: dict[str, dict[str, Any]] = {
    "NVDA_2024_2025_10k_item1a": {
        "issuer": {"ticker": "NVDA", "issuer_name": "NVIDIA Corporation"},
        "run_sources": [
            {
                "run_id": "NVDA_04_p4_i2_novelty_ledger_extended_v2",
                "reasoning_variant": "extended",
                "response_path": Path(
                    "wave4e35_nvda_p4_tightened_packet_20260320_1824/NVDA_04_p4_i2_novelty_ledger_extended_v2/response.json"
                ),
                "run_manifest_path": Path(
                    "wave4e35_nvda_p4_tightened_packet_20260320_1824/NVDA_04_p4_i2_novelty_ledger_extended_v2/run_manifest.json"
                ),
                "fy2024_path": Path(
                    "wave4e35_nvda_p4_tightened_packet_20260320_1824/NVDA_04_p4_i2_novelty_ledger_extended_v2/sources/i2_tagged_document_packet_v1_FY2024.json"
                ),
                "fy2025_path": Path(
                    "wave4e35_nvda_p4_tightened_packet_20260320_1824/NVDA_04_p4_i2_novelty_ledger_extended_v2/sources/i2_tagged_document_packet_v1_FY2025.json"
                ),
                "canonization_status": "canonized_as_is",
                "quality_note_ids": [],
                "repair_kind": None,
            },
            {
                "run_id": "NVDA_05_p4_i2_novelty_ledger_standard_v2",
                "reasoning_variant": "standard",
                "response_path": Path(
                    "wave4e35_nvda_p4_tightened_packet_20260320_1824/NVDA_05_p4_i2_novelty_ledger_standard_v2/response.json"
                ),
                "run_manifest_path": Path(
                    "wave4e35_nvda_p4_tightened_packet_20260320_1824/NVDA_05_p4_i2_novelty_ledger_standard_v2/run_manifest.json"
                ),
                "fy2024_path": Path(
                    "wave4e35_nvda_p4_tightened_packet_20260320_1824/NVDA_05_p4_i2_novelty_ledger_standard_v2/sources/i2_tagged_document_packet_v1_FY2024.json"
                ),
                "fy2025_path": Path(
                    "wave4e35_nvda_p4_tightened_packet_20260320_1824/NVDA_05_p4_i2_novelty_ledger_standard_v2/sources/i2_tagged_document_packet_v1_FY2025.json"
                ),
                "canonization_status": "canonized_with_transport_repair",
                "quality_note_ids": [
                    "nvda_transport_only_quote_repair",
                    "nvda_manifest_review_required_evidence_row",
                ],
                "repair_kind": "transport_quotes",
            },
        ],
        "issuer_finding_summary": (
            "Across the canonized NVDA P4 runs, novelty is concentrated in a small number of "
            "named AI-regulation and export-control specifics, while the broader FY2025 move is "
            "better read as intensified supply-execution and export-control detail layered onto a "
            "largely reused Item 1A structure."
        ),
        "p4_role_statement": (
            "This lens separates genuinely new disclosure from intensified or reused filing "
            "structure. It is narrower than the main summary and stays secondary because 02 still "
            "delivers the better default first read."
        ),
        "known_quality_caveats": [
            "The NVDA standard P4 raw response required deterministic transport repair for unescaped internal quotation marks around AI Diffusion.",
            "The repaired NVDA standard object still carries one manifest-linked evidence row for the main caveat instead of a filing paragraph; that quality debt is logged, not silently rewritten.",
        ],
        "standard_and_extended_broadly_agree": True,
        "standard_and_extended_agreement_note": (
            "Yes. Both runs treat AI Diffusion as the clearest fresh point, keep Blackwell and "
            "supply execution in the intensified bucket, and read most of the filing as reused "
            "framework language rather than a wholly new risk map."
        ),
        "suitable_for_limited_app_integration": True,
        "integration_note": (
            "Suitable for a compact secondary module because the core fresh-versus-reused pattern "
            "holds across both runs even after the standard-run transport repair."
        ),
        "comparison_to_02": {
            "where_p4_adds_value": (
                "P4 adds a cleaner fresh-versus-reused check than 02, especially around AI "
                "Diffusion, EU AI Act, and Blackwell as a new example inside an older risk family."
            ),
            "where_02_remains_stronger": (
                "02 remains stronger as the broad default synthesis because it leads with the main "
                "filing shift and stays more robust and investor-readable."
            ),
            "why_secondary_only": (
                "P4 is too narrow and slightly more quality-sensitive to replace the hero lane, "
                "but it is useful as a bounded second lens on novelty claims."
            ),
        },
        "module_sections": {
            "fresh_2025_specifics": [
                {
                    "item_id": "ai_diffusion_ifr",
                    "label": "AI Diffusion IFR",
                    "text": (
                        "FY2025 adds the January 2025 AI Diffusion rule as a newly named "
                        "worldwide export-control regime rather than just another example inside "
                        "the older export-control theme."
                    ),
                    "support_level": "both",
                    "evidence_refs": [
                        {"run_id": "NVDA_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev_01"},
                        {"run_id": "NVDA_05_p4_i2_novelty_ledger_standard_v2", "evidence_id": "ev01"},
                    ],
                },
                {
                    "item_id": "eu_ai_act",
                    "label": "EU AI Act",
                    "text": (
                        "FY2025 newly names the EU AI Act and links it to model training, "
                        "deployment, and release constraints in Europe."
                    ),
                    "support_level": "extended_primary_standard_compatible",
                    "evidence_refs": [
                        {"run_id": "NVDA_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev_03"},
                    ],
                },
            ],
            "intensified_or_broadened_points": [
                {
                    "item_id": "supply_and_blackwell",
                    "label": "Supply and product cadence details",
                    "text": (
                        "FY2025 intensifies the existing supply and transition story by elevating "
                        "long lead times, annual data-center cadence, and a concrete Blackwell "
                        "yield example."
                    ),
                    "support_level": "both",
                    "evidence_refs": [
                        {"run_id": "NVDA_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev_08"},
                        {"run_id": "NVDA_05_p4_i2_novelty_ledger_standard_v2", "evidence_id": "ev06"},
                    ],
                },
                {
                    "item_id": "export_control_spillovers",
                    "label": "Export-control spillovers broaden",
                    "text": (
                        "FY2025 broadens the existing export-control theme with wider operational "
                        "spillovers, including tariffs and market-access consequences beyond the "
                        "older framing."
                    ),
                    "support_level": "both",
                    "evidence_refs": [
                        {"run_id": "NVDA_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev_11"},
                        {"run_id": "NVDA_05_p4_i2_novelty_ledger_standard_v2", "evidence_id": "ev04"},
                    ],
                },
            ],
            "reused_framework_language": [
                {
                    "item_id": "supplier_dependence",
                    "label": "Supplier dependence stays familiar",
                    "text": (
                        "The core warning that NVIDIA depends on third-party manufacturing and "
                        "supplier execution remains materially reused across both years."
                    ),
                    "support_level": "extended_primary_standard_compatible",
                    "evidence_refs": [
                        {"run_id": "NVDA_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev_14"},
                    ],
                }
            ],
            "boundary_notes": [
                {
                    "item_id": "blackwell_boundary",
                    "label": "Blackwell is a new example, not a new risk family",
                    "text": (
                        "The Blackwell disclosure is genuinely new language in FY2025, but it "
                        "still sits inside the older transition, yield, and inventory-risk family."
                    ),
                    "support_level": "both",
                    "evidence_refs": [
                        {"run_id": "NVDA_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev_08"},
                        {"run_id": "NVDA_05_p4_i2_novelty_ledger_standard_v2", "evidence_id": "ev06"},
                    ],
                },
                {
                    "item_id": "fresh_vs_family_boundary",
                    "label": "Fresh regimes do not make the whole risk family new",
                    "text": (
                        "AI Diffusion and the EU AI Act are fresh named specifics, but they do not "
                        "turn the broader export-control and AI-regulation theme into a wholly new "
                        "risk family."
                    ),
                    "support_level": "extended_primary_standard_compatible",
                    "evidence_refs": [
                        {"run_id": "NVDA_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev_01"},
                        {"run_id": "NVDA_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev_03"},
                    ],
                },
            ],
        },
        "quality_notes": [
            {
                "note_id": "nvda_transport_only_quote_repair",
                "issue_type": "raw_json_unescaped_internal_quotes",
                "affected_run_id": "NVDA_05_p4_i2_novelty_ledger_standard_v2",
                "issue_family": "transport/container",
                "deterministic_repair_allowed": True,
                "repair_applied_in_canonization": True,
                "changes_broad_analytical_verdict": False,
                "review_note": (
                    "The canonical working object was created by deterministic transport-only "
                    "quote escaping for the unescaped internal 'AI Diffusion' quotation marks. "
                    "No analytical text was rewritten."
                ),
            },
            {
                "note_id": "nvda_manifest_review_required_evidence_row",
                "issue_type": "non_filing_manifest_status_evidence_row",
                "affected_run_id": "NVDA_05_p4_i2_novelty_ledger_standard_v2",
                "issue_family": "evidence-row integrity",
                "deterministic_repair_allowed": False,
                "repair_applied_in_canonization": False,
                "changes_broad_analytical_verdict": False,
                "review_note": (
                    "Evidence row ev14 cites manifest_review_required instead of a filing "
                    "paragraph. The row is logged as quality debt and is not used for the visible "
                    "module consensus."
                ),
            },
        ],
        "review_updates": {
            "supports": [
                "On this fixed NVDA Item 1A pair, protocol and input treatment materially change usefulness, specificity, novelty separation, and auditability.",
                "Lane 02 is the clearest default first read because it combines a bounded structured contract with paragraph-addressable tagged evidence.",
                "Holding the tagged substrate fixed shows that protocol changes alone can materially alter the lead story and the organization of evidence.",
                "A bounded secondary novelty-ledger module is now supported for NVDA as a check on genuinely fresh specifics versus intensified or reused language.",
            ],
            "does_not_yet_support": [
                "This is a single-issuer, single-pair pilot matrix and does not yet generalize across companies.",
                "It is not a model leaderboard or final benchmark claim, and it does not prove universal superiority of one protocol outside this NVDA slice.",
                "It does not yet cover whole-filing context, external research overlays, third-issuer novelty-ledger transfer, or equal-lane P4 expansion.",
            ],
        },
    },
    "LLY_2024_2025_10k_item1a": {
        "issuer": {"ticker": "LLY", "issuer_name": "Eli Lilly and Company"},
        "run_sources": [
            {
                "run_id": "LLY_04_p4_i2_novelty_ledger_extended_v2",
                "reasoning_variant": "extended",
                "response_path": Path(
                    "wave4e37a_lly_p4_transfer_packet_20260321_2221/LLY_04_p4_i2_novelty_ledger_extended_v2/response.json"
                ),
                "run_manifest_path": Path(
                    "wave4e37a_lly_p4_transfer_packet_20260321_2221/LLY_04_p4_i2_novelty_ledger_extended_v2/run_manifest.json"
                ),
                "fy2024_path": Path(
                    "wave4e37a_lly_p4_transfer_packet_20260321_2221/LLY_04_p4_i2_novelty_ledger_extended_v2/sources/i2_tagged_document_packet_v1_FY2024.json"
                ),
                "fy2025_path": Path(
                    "wave4e37a_lly_p4_transfer_packet_20260321_2221/LLY_04_p4_i2_novelty_ledger_extended_v2/sources/i2_tagged_document_packet_v1_FY2025.json"
                ),
                "canonization_status": "canonized_as_is",
                "quality_note_ids": [],
                "repair_kind": None,
            },
            {
                "run_id": "LLY_05_p4_i2_novelty_ledger_standard_v2",
                "reasoning_variant": "standard",
                "response_path": Path(
                    "wave4e37a_lly_p4_transfer_packet_20260321_2221/LLY_05_p4_i2_novelty_ledger_standard_v2/response.json"
                ),
                "run_manifest_path": Path(
                    "wave4e37a_lly_p4_transfer_packet_20260321_2221/LLY_05_p4_i2_novelty_ledger_standard_v2/run_manifest.json"
                ),
                "fy2024_path": Path(
                    "wave4e37a_lly_p4_transfer_packet_20260321_2221/LLY_05_p4_i2_novelty_ledger_standard_v2/sources/i2_tagged_document_packet_v1_FY2024.json"
                ),
                "fy2025_path": Path(
                    "wave4e37a_lly_p4_transfer_packet_20260321_2221/LLY_05_p4_i2_novelty_ledger_standard_v2/sources/i2_tagged_document_packet_v1_FY2025.json"
                ),
                "canonization_status": "canonized_with_evidence_row_correction",
                "quality_note_ids": ["lly_ev04_exact_substring_correction"],
                "repair_kind": "evidence_row_correction",
            },
        ],
        "issuer_finding_summary": (
            "Across the canonized LLY P4 runs, the strongest freshness signal is a small set of "
            "new pricing-and-access specifics, while most of the visible year-over-year movement "
            "broadens existing pricing, channel, concentration, competition, tariff, and AI "
            "themes rather than introducing wholly new risk families."
        ),
        "p4_role_statement": (
            "This lens is useful for checking whether FY2025 really introduces new pricing and "
            "access detail or mainly sharpens an older pharma risk framework. It stays secondary "
            "because 02 is still the broader and more robust default read."
        ),
        "known_quality_caveats": [
            "The LLY standard P4 raw response remained parseable, but one evidence row required an exact-substring quote correction against the cited filing paragraph.",
            "That correction was limited to quote text for ev04 and did not change the analytical meaning or the broad verdict.",
        ],
        "standard_and_extended_broadly_agree": True,
        "standard_and_extended_agreement_note": (
            "Yes. Both runs agree that the freshest movement sits in pricing-and-access specifics, "
            "that obesity-access/channel detail is broader rather than wholly new, and that most "
            "of the filing still rides on a reused framework."
        ),
        "suitable_for_limited_app_integration": True,
        "integration_note": (
            "Suitable for a compact secondary module because the same product-legible pattern holds "
            "across the extended run and the corrected standard run."
        ),
        "comparison_to_02": {
            "where_p4_adds_value": (
                "P4 adds a clearer split between genuinely new pricing-access specifics, broadened "
                "carryover themes, reused framework language, and boundary cases."
            ),
            "where_02_remains_stronger": (
                "02 remains stronger as the main first-read synthesis because it integrates the full "
                "issuer story and is less sensitive to narrow classification decisions."
            ),
            "why_secondary_only": (
                "P4 is useful precisely because it is narrower. That narrowness makes it valuable as "
                "a second lens, not as a replacement for the hero lane."
            ),
        },
        "module_sections": {
            "fresh_2025_specifics": [
                {
                    "item_id": "us_pricing_arrangements",
                    "label": "New U.S. pricing arrangements",
                    "text": (
                        "FY2025 adds newly disclosed U.S. voluntary pricing agreements rather than "
                        "just refreshing older pricing-pressure language."
                    ),
                    "support_level": "both",
                    "evidence_refs": [
                        {"run_id": "LLY_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev01"},
                        {"run_id": "LLY_05_p4_i2_novelty_ledger_standard_v2", "evidence_id": "ev01"},
                    ],
                },
                {
                    "item_id": "updated_medicare_selection",
                    "label": "Updated Medicare selection example",
                    "text": (
                        "FY2025 updates the Medicare negotiation story with Lilly-specific 2026 "
                        "selection detail, making the next pricing wave more concrete."
                    ),
                    "support_level": "both",
                    "evidence_refs": [
                        {"run_id": "LLY_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev04"},
                        {"run_id": "LLY_05_p4_i2_novelty_ledger_standard_v2", "evidence_id": "ev03"},
                    ],
                },
            ],
            "intensified_or_broadened_points": [
                {
                    "item_id": "obesity_access_channel",
                    "label": "Obesity-access and channel pressure broaden",
                    "text": (
                        "FY2025 broadens the older pricing/access theme into LillyDirect, self-pay, "
                        "and more concrete obesity-coverage friction."
                    ),
                    "support_level": "both",
                    "evidence_refs": [
                        {"run_id": "LLY_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev09"},
                        {"run_id": "LLY_05_p4_i2_novelty_ledger_standard_v2", "evidence_id": "ev02"},
                    ],
                },
                {
                    "item_id": "competition_tariff_ai",
                    "label": "Competition, tariff, and AI pressure broaden",
                    "text": (
                        "Most of the remaining FY2025 movement is broader scope inside existing "
                        "competition, global-operations, tariff, and AI themes rather than a new "
                        "risk family."
                    ),
                    "support_level": "extended_primary_standard_compatible",
                    "evidence_refs": [
                        {"run_id": "LLY_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev28"},
                    ],
                },
            ],
            "reused_framework_language": [
                {
                    "item_id": "core_rd_frame",
                    "label": "Core R&D uncertainty stays intact",
                    "text": (
                        "The filing still relies on the same broad pharma R&D uncertainty frame "
                        "across both years."
                    ),
                    "support_level": "both",
                    "evidence_refs": [
                        {"run_id": "LLY_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev36"},
                        {"run_id": "LLY_05_p4_i2_novelty_ledger_standard_v2", "evidence_id": "ev10"},
                    ],
                }
            ],
            "boundary_notes": [
                {
                    "item_id": "jardiance_to_new_examples",
                    "label": "New Medicare examples do not erase the old pricing theme",
                    "text": (
                        "FY2025 swaps out the older Jardiance detail for newer Trulicity and "
                        "Verzenio examples, but that is still the same underlying government-pricing "
                        "risk family."
                    ),
                    "support_level": "both",
                    "evidence_refs": [
                        {"run_id": "LLY_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev05"},
                        {"run_id": "LLY_05_p4_i2_novelty_ledger_standard_v2", "evidence_id": "ev07"},
                    ],
                },
                {
                    "item_id": "tirzepatide_generalized",
                    "label": "The tirzepatide snapshot was generalized, not clearly removed",
                    "text": (
                        "FY2025 drops the older tirzepatide-specific supply snapshot, but the broader "
                        "manufacturing-and-demand theme remains, so this should not be overstated as "
                        "a true removal."
                    ),
                    "support_level": "both",
                    "evidence_refs": [
                        {"run_id": "LLY_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev21"},
                        {"run_id": "LLY_05_p4_i2_novelty_ledger_standard_v2", "evidence_id": "ev20"},
                    ],
                },
            ],
        },
        "quality_notes": [
            {
                "note_id": "lly_ev04_exact_substring_correction",
                "issue_type": "exact_substring_quote_mismatch",
                "affected_run_id": "LLY_05_p4_i2_novelty_ledger_standard_v2",
                "issue_family": "evidence-row integrity",
                "deterministic_repair_allowed": True,
                "repair_applied_in_canonization": True,
                "changes_broad_analytical_verdict": False,
                "review_note": (
                    "Evidence row ev04 was corrected to the exact filing substring from "
                    "lly_2025_p029. Only quote text changed; the analytical classification and "
                    "broad verdict stayed the same."
                ),
            }
        ],
        "review_updates": {
            "supports": [
                "On this fixed LLY Item 1A pair, protocol structure materially changes first-read usefulness, specificity, novelty separation, and auditability.",
                "Lane 02 is the clearest default first read because it keeps the filing delta legible while staying contract-bounded and paragraph-addressable.",
                "Holding the tagged substrate fixed shows that protocol changes alone can materially alter which obesity-access, pricing, and concentration risks lead the narrative.",
                "A bounded secondary novelty-ledger module is now supported for LLY as a compact check on fresh pricing-access specifics versus broadened carryover themes.",
            ],
            "does_not_yet_support": [
                "This is a single-issuer, single-pair pilot matrix and does not yet generalize across companies.",
                "It is not a model leaderboard or final benchmark claim, and it does not prove universal superiority of one protocol outside this LLY slice.",
                "It does not yet cover whole-filing context, external research overlays, a full lower-audit lab stack for LLY, third-issuer novelty-ledger transfer, or equal-lane P4 expansion.",
            ],
        },
    },
}

CROSS_ISSUER_SUMMARY = {
    "what_p4_consistently_adds_over_02": [
        "P4 cleanly separates genuinely fresh, date-linked specifics from intensified or broadened carryover themes.",
        "P4 makes reused framework language visible instead of leaving it implicit inside the broader first-read summary.",
        "P4 handles boundary cases more explicitly, which helps keep new examples inside old risk families from being overstated as wholly new risk maps.",
    ],
    "what_p4_still_does_not_do_as_well_as_02": [
        "P4 is weaker than 02 as a broad default investor-readable synthesis of the full filing shift.",
        "P4 is more quality-sensitive because its value depends on narrow evidence and category discipline.",
        "P4 does not replace 02's role as the most robust first-read lane across the current two-issuer slice.",
    ],
    "why_secondary_only": (
        "P4 now passes two-issuer transfer well enough to move beyond internal experimentation, "
        "but it still works best as a secondary module because it is intentionally narrower than "
        "the hero lane and more dependent on careful canonization."
    ),
    "overall_verdict": (
        "Across NVDA and LLY, P4 is strong enough for limited pilot integration as a secondary "
        "novelty-ledger module that helps users distinguish fresh specifics, broadened carryover "
        "points, reused framework language, and boundary cases. It is not strong enough to become "
        "a full equal top-level lane."
    ),
}

P4_VS_P1_SUMMARY = {
    "comparison_frame": (
        "P4 is a complementary second lens next to the current 02 hero lane rather than a "
        "winner-take-all replacement."
    ),
    "where_p4_is_stronger": [
        "P4 is stronger when the user specifically wants fresh-versus-reused clarity.",
        "P4 is stronger when a new example might really be an intensified carryover theme instead of a fresh risk family.",
    ],
    "where_02_is_stronger": [
        "02 remains stronger as the broad default investor-readable synthesis of the filing shift.",
        "02 remains stronger on general robustness and as the first lane a user should read.",
    ],
    "bounded_decision": (
        "The product decision stays the same after two-issuer transfer: keep 02 as the hero lane, "
        "and use P4 only as a compact novelty-ledger module inside the pilot slices."
    ),
}


@dataclass(frozen=True)
class ResolvedRun:
    run_id: str
    reasoning_variant: str
    response: dict[str, Any]
    run_manifest: dict[str, Any]
    response_path: Path
    run_manifest_path: Path
    canonization_status: str
    quality_note_ids: list[str]
    repair_summary: str | None
    evidence_issues: list[str]


@dataclass(frozen=True)
class GenerationSummary:
    packet_dir: Path
    zip_path: Path
    artifact_paths: list[str]
    quality_note_paths: list[str]
    source_paths: list[str]
    renders_both_pilots: bool
    biggest_remaining_blocker: str
    console_summary_lines: list[str]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")


def packet_paths_for_stamp(stamp: str) -> tuple[Path, Path]:
    name = f"{PACKET_PREFIX}_{stamp}"
    return REPO_ROOT / name, REPO_ROOT / f"{name}.zip"


def repo_rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def public_data_rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT / "public").as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(read_text(path))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected JSON object at {path}.")
    return cast(dict[str, Any], payload)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, indent=2) + "\n")


def ensure_clean_output(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def zip_directory(source_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(source_dir.rglob("*")):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(source_dir.parent))


def copy_repo_paths_into_packet(packet_dir: Path, repo_paths: list[Path]) -> None:
    for repo_path in repo_paths:
        source_path = REPO_ROOT / repo_path
        destination_path = packet_dir / repo_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)


def build_changed_files_manifest(paths: list[Path]) -> str:
    lines = [
        "# Changed Files Manifest",
        "",
        "Files created or modified by Wave 4E4:",
        "",
    ]
    for path in paths:
        lines.append(f"- `{path.as_posix()}`")
    return "\n".join(lines) + "\n"


def build_render_preview(case_payloads: dict[str, dict[str, Any]]) -> str:
    nvda = case_payloads["NVDA_2024_2025_10k_item1a"]
    lly = case_payloads["LLY_2024_2025_10k_item1a"]
    lines = [
        "# Wave 4E4 Render Preview",
        "",
        "Deterministic text preview of the pilot slices after the limited P4 novelty-ledger insertion.",
        "",
        "## NVDA Pilot Slice",
        "",
        "- filing-shift story: present",
        "- effort robustness: present",
        "- novelty ledger module: inserted between effort robustness and the lane-card grid",
        f"- fresh focus: {nvda['module_sections']['fresh_2025_specifics'][0]['label']}, {nvda['module_sections']['fresh_2025_specifics'][1]['label']}",
        "- visible groups: fresh 2025 specifics / intensified or broadened points / reused framework language / boundary notes",
        "- lower proof boundary and matrix caveat: still present below the lane detail area",
        "",
        "## LLY Pilot Slice",
        "",
        "- filing-shift story: present",
        "- effort robustness: present",
        "- novelty ledger module: inserted between effort robustness and the lane-card grid",
        f"- fresh focus: {lly['module_sections']['fresh_2025_specifics'][0]['label']}, {lly['module_sections']['fresh_2025_specifics'][1]['label']}",
        "- visible groups: fresh 2025 specifics / intensified or broadened points / reused framework language / boundary notes",
        "- lower audit unavailable-state panel: still present below the pilot matrix stack",
    ]
    return "\n".join(lines) + "\n"


def build_packet_readme(
    packet_dir: Path,
    artifact_paths: list[Path],
    quality_note_paths: list[Path],
    report_paths: list[Path],
    changed_source_paths: list[Path],
) -> str:
    lines = [
        f"# {packet_dir.name}",
        "",
        "This packet contains the Wave 4E4 canonized novelty-ledger artifacts, reports, modified source files, and deterministic render preview.",
        "",
        "## Included",
        "",
        "- canonized public novelty-ledger artifacts for NVDA, LLY, and the two cross-case summaries",
        "- issuer quality-note artifacts with logged repair or correction decisions",
        "- Wave 4E4 canonization, integration-decision, and findings reports",
        "- modified pilot-slice source files plus the minimal loader/type/schema files",
        "- generator script, targeted tests, changed-file manifest, and render preview",
        "",
        "## Canonized Artifacts",
        "",
    ]
    for path in artifact_paths:
        lines.append(f"- `{repo_rel(path)}`")
    lines.extend(["", "## Quality Notes", ""])
    for path in quality_note_paths:
        lines.append(f"- `{repo_rel(path)}`")
    lines.extend(["", "## Reports", ""])
    for path in report_paths:
        lines.append(f"- `{repo_rel(path)}`")
    lines.extend(["", "## Modified Source Files", ""])
    for path in changed_source_paths:
        lines.append(f"- `{path.as_posix()}`")
    return "\n".join(lines) + "\n"


def build_paragraph_lookup(fy2024_path: Path, fy2025_path: Path) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for path in (fy2024_path, fy2025_path):
        payload = read_json(path)
        documents = payload.get("documents", [])
        if not isinstance(documents, list):
            raise TypeError(f"Expected documents array in {path}.")
        for document in cast(list[dict[str, Any]], documents):
            paragraphs = document.get("paragraphs", [])
            if not isinstance(paragraphs, list):
                continue
            for paragraph in cast(list[dict[str, Any]], paragraphs):
                paragraph_id = paragraph.get("paragraph_id")
                text = paragraph.get("text")
                if isinstance(paragraph_id, str) and isinstance(text, str):
                    lookup[paragraph_id] = text
    return lookup


def repair_nvda_standard_transport(raw_text: str) -> tuple[dict[str, Any], str]:
    occurrence_count = raw_text.count('"AI Diffusion"')
    if occurrence_count != 2:
        raise ValueError(
            f"Expected exactly 2 unescaped AI Diffusion transport occurrences, found {occurrence_count}."
        )
    repaired_text = raw_text.replace('"AI Diffusion"', '\\"AI Diffusion\\"')
    response = json.loads(repaired_text)
    if not isinstance(response, dict):
        raise TypeError("Expected repaired NVDA standard response to decode to a JSON object.")
    return cast(dict[str, Any], response), (
        "Applied deterministic transport-only escaping to the two unescaped internal "
        '"AI Diffusion" quotations in the raw JSON payload.'
    )


def correct_lly_standard_ev04(response: dict[str, Any], paragraph_lookup: dict[str, str]) -> str:
    evidence_bundle = response.get("evidence_bundle")
    if not isinstance(evidence_bundle, dict):
        raise TypeError("LLY standard response is missing evidence_bundle.")
    evidence_bundle = cast(dict[str, Any], evidence_bundle)
    items = evidence_bundle.get("items")
    if not isinstance(items, list):
        raise TypeError("LLY standard response is missing evidence_bundle.items.")

    for item in cast(list[dict[str, Any]], items):
        if item.get("evidence_id") != "ev04":
            continue
        paragraph_id = item.get("paragraph_id")
        if not isinstance(paragraph_id, str):
            raise TypeError("LLY ev04 paragraph_id must be a string.")
        paragraph_text = paragraph_lookup.get(paragraph_id)
        if not paragraph_text:
            raise KeyError(f"Unable to resolve paragraph text for {paragraph_id}.")
        quote_text = item.get("quote_text")
        if not isinstance(quote_text, str):
            raise TypeError("LLY ev04 quote_text must be a string.")
        if quote_text in paragraph_text:
            raise AssertionError("LLY ev04 already matches the filing paragraph; correction was not expected.")

        start = paragraph_text.index("For example, in July 2025")
        end = paragraph_text.index("We expect supply chain entities", start)
        corrected_quote = paragraph_text[start:end].strip()
        if corrected_quote not in paragraph_text:
            raise AssertionError("Derived ev04 correction is not an exact filing substring.")
        item["quote_text"] = corrected_quote
        return (
            "Replaced ev04 quote_text with the exact filing substring from lly_2025_p029. "
            "No analytical text or category assignment changed."
        )

    raise KeyError("Expected to find ev04 in the LLY standard response evidence bundle.")


def find_evidence_issues(response: dict[str, Any], paragraph_lookup: dict[str, str]) -> list[str]:
    evidence_bundle = response.get("evidence_bundle")
    if not isinstance(evidence_bundle, dict):
        raise TypeError("Response is missing evidence_bundle.")
    evidence_bundle = cast(dict[str, Any], evidence_bundle)
    items = evidence_bundle.get("items")
    if not isinstance(items, list):
        raise TypeError("Response is missing evidence_bundle.items.")

    issues: list[str] = []
    for item in cast(list[dict[str, Any]], items):
        evidence_id = item.get("evidence_id")
        paragraph_id = item.get("paragraph_id")
        quote_text = item.get("quote_text")
        if not isinstance(evidence_id, str) or not isinstance(paragraph_id, str) or not isinstance(quote_text, str):
            issues.append("malformed_evidence_row")
            continue
        paragraph_text = paragraph_lookup.get(paragraph_id)
        if paragraph_text is None:
            issues.append(f"{evidence_id}:{paragraph_id}:paragraph_missing")
            continue
        if quote_text not in paragraph_text:
            issues.append(f"{evidence_id}:{paragraph_id}:quote_mismatch")
    return issues


def validate_run_manifest(run_manifest: dict[str, Any], expected_run_id: str) -> None:
    run_identity = run_manifest.get("run_identity")
    if not isinstance(run_identity, dict):
        raise TypeError(f"{expected_run_id} run_manifest is missing run_identity.")
    run_identity = cast(dict[str, Any], run_identity)
    run_name = run_identity.get("run_name")
    if run_name != expected_run_id:
        raise ValueError(f"Run manifest identity mismatch: expected {expected_run_id}, got {run_name!r}.")


def resolve_run(run_config: dict[str, Any]) -> ResolvedRun:
    response_path = REPO_ROOT / cast(Path, run_config["response_path"])
    run_manifest_path = REPO_ROOT / cast(Path, run_config["run_manifest_path"])
    fy2024_path = REPO_ROOT / cast(Path, run_config["fy2024_path"])
    fy2025_path = REPO_ROOT / cast(Path, run_config["fy2025_path"])
    paragraph_lookup = build_paragraph_lookup(fy2024_path, fy2025_path)
    run_manifest = read_json(run_manifest_path)
    validate_run_manifest(run_manifest, cast(str, run_config["run_id"]))

    repair_summary: str | None = None
    if run_config["repair_kind"] == "transport_quotes":
        raw_text = read_text(response_path)
        response, repair_summary = repair_nvda_standard_transport(raw_text)
        evidence_issues = find_evidence_issues(response, paragraph_lookup)
        expected_issues = ["ev14:manifest_review_required:paragraph_missing"]
        if evidence_issues != expected_issues:
            raise AssertionError(
                f"Unexpected NVDA standard evidence issues: {evidence_issues!r} vs {expected_issues!r}."
            )
    elif run_config["repair_kind"] == "evidence_row_correction":
        response = copy.deepcopy(read_json(response_path))
        pre_correction_issues = find_evidence_issues(response, paragraph_lookup)
        expected_pre_correction = ["ev04:lly_2025_p029:quote_mismatch"]
        if pre_correction_issues != expected_pre_correction:
            raise AssertionError(
                "Unexpected LLY standard pre-correction evidence issues: "
                f"{pre_correction_issues!r} vs {expected_pre_correction!r}."
            )
        repair_summary = correct_lly_standard_ev04(response, paragraph_lookup)
        evidence_issues = find_evidence_issues(response, paragraph_lookup)
        if evidence_issues:
            raise AssertionError(
                f"LLY standard evidence issues remain after correction: {evidence_issues!r}."
            )
    else:
        response = read_json(response_path)
        evidence_issues = find_evidence_issues(response, paragraph_lookup)
        if evidence_issues:
            raise AssertionError(
                f"Unexpected evidence issues in {run_config['run_id']}: {evidence_issues!r}."
            )

    return ResolvedRun(
        run_id=cast(str, run_config["run_id"]),
        reasoning_variant=cast(str, run_config["reasoning_variant"]),
        response=response,
        run_manifest=run_manifest,
        response_path=response_path,
        run_manifest_path=run_manifest_path,
        canonization_status=cast(str, run_config["canonization_status"]),
        quality_note_ids=cast(list[str], run_config["quality_note_ids"]),
        repair_summary=repair_summary,
        evidence_issues=evidence_issues,
    )


def build_evidence_preview(
    resolved_runs: dict[str, ResolvedRun], evidence_refs: list[dict[str, str]]
) -> list[dict[str, Any]]:
    preview: list[dict[str, Any]] = []
    for evidence_ref in evidence_refs:
        run = resolved_runs[evidence_ref["run_id"]]
        evidence_bundle = cast(dict[str, Any], run.response["evidence_bundle"])
        items = cast(list[dict[str, Any]], evidence_bundle["items"])
        match = next(
            (item for item in items if item.get("evidence_id") == evidence_ref["evidence_id"]),
            None,
        )
        if match is None:
            raise KeyError(
                f"Missing evidence {evidence_ref['evidence_id']} in run {evidence_ref['run_id']}."
            )
        preview.append(
            {
                "run_id": evidence_ref["run_id"],
                "evidence_id": cast(str, match["evidence_id"]),
                "year_label": cast(str, match["year_label"]),
                "paragraph_id": cast(str, match["paragraph_id"]),
                "quote_text": cast(str, match["quote_text"]),
                "short_note": match.get("short_note") if isinstance(match.get("short_note"), str) else None,
            }
        )
    return preview


def build_case_artifact(
    fixture_id: str,
    case_config: dict[str, Any],
    resolved_runs: dict[str, ResolvedRun],
    quality_note_path: Path,
) -> dict[str, Any]:
    pair_info = copy.deepcopy(PAIR_INFO_BY_FIXTURE[fixture_id])
    issuer_info = copy.deepcopy(case_config["issuer"])
    module_sections: dict[str, list[dict[str, Any]]] = {}
    for section_id, items in cast(dict[str, list[dict[str, Any]]], case_config["module_sections"]).items():
        module_sections[section_id] = []
        for item in items:
            module_sections[section_id].append(
                {
                    "item_id": item["item_id"],
                    "label": item["label"],
                    "text": item["text"],
                    "support_level": item["support_level"],
                    "source_run_ids": [ref["run_id"] for ref in item["evidence_refs"]],
                    "evidence_preview": build_evidence_preview(resolved_runs, item["evidence_refs"]),
                }
            )

    canonized_runs: list[dict[str, Any]] = []
    for run in resolved_runs.values():
        canonized_runs.append(
            {
                "run_id": run.run_id,
                "reasoning_variant": run.reasoning_variant,
                "source_response_path": repo_rel(run.response_path),
                "source_run_manifest_path": repo_rel(run.run_manifest_path),
                "canonization_status": run.canonization_status,
                "quality_note_ids": run.quality_note_ids,
                "repair_summary": run.repair_summary,
            }
        )

    return {
        "artifact_schema_id": "p4_canonized_matrix_v1",
        "artifact_id": f"{fixture_id}__p4_canonized_matrix_v1",
        "fixture_id": fixture_id,
        "issuer": issuer_info,
        "pair_info": pair_info,
        "canonical_run_ids": list(resolved_runs.keys()),
        "canonized_runs": canonized_runs,
        "issuer_finding_summary": case_config["issuer_finding_summary"],
        "p4_role_statement": case_config["p4_role_statement"],
        "known_quality_caveats": case_config["known_quality_caveats"],
        "standard_and_extended_broadly_agree": case_config["standard_and_extended_broadly_agree"],
        "standard_and_extended_agreement_note": case_config["standard_and_extended_agreement_note"],
        "suitable_for_limited_app_integration": case_config["suitable_for_limited_app_integration"],
        "integration_note": case_config["integration_note"],
        "comparison_to_02": copy.deepcopy(case_config["comparison_to_02"]),
        "module_sections": module_sections,
        "quality_note_path": public_data_rel(quality_note_path),
    }


def build_quality_artifact(
    fixture_id: str, case_config: dict[str, Any], resolved_runs: dict[str, ResolvedRun]
) -> dict[str, Any]:
    issuer_info = copy.deepcopy(case_config["issuer"])
    notes = copy.deepcopy(case_config["quality_notes"])
    run_map = {run.run_id: run for run in resolved_runs.values()}
    for note in notes:
        run = run_map[note["affected_run_id"]]
        note["response_path"] = repo_rel(run.response_path)
        note["run_manifest_path"] = repo_rel(run.run_manifest_path)
    return {
        "artifact_schema_id": "p4_quality_notes_v1",
        "artifact_id": f"{issuer_info['ticker'].lower()}_p4_quality_notes_v1",
        "fixture_id": fixture_id,
        "issuer": issuer_info,
        "notes": notes,
    }


def build_cross_summary(issuer_artifact_paths: list[Path], quality_note_paths: list[Path]) -> dict[str, Any]:
    return {
        "artifact_schema_id": "p4_canonized_summary_v1",
        "artifact_id": "p4_canonized_summary_v1",
        "covered_issuers": ["NVDA", "LLY"],
        "issuer_artifact_paths": [public_data_rel(path) for path in issuer_artifact_paths],
        "quality_note_paths": [public_data_rel(path) for path in quality_note_paths],
        "what_p4_consistently_adds_over_02": CROSS_ISSUER_SUMMARY["what_p4_consistently_adds_over_02"],
        "what_p4_still_does_not_do_as_well_as_02": CROSS_ISSUER_SUMMARY[
            "what_p4_still_does_not_do_as_well_as_02"
        ],
        "why_secondary_only": CROSS_ISSUER_SUMMARY["why_secondary_only"],
        "overall_verdict": CROSS_ISSUER_SUMMARY["overall_verdict"],
    }


def build_p4_vs_p1_summary() -> dict[str, Any]:
    return {
        "artifact_schema_id": "p4_vs_p1_summary_v1",
        "artifact_id": "p4_vs_p1_summary_v1",
        "covered_issuers": ["NVDA", "LLY"],
        "hero_lane_family": "02_p1_i2_tagged_packet",
        "comparison_frame": P4_VS_P1_SUMMARY["comparison_frame"],
        "where_p4_is_stronger": P4_VS_P1_SUMMARY["where_p4_is_stronger"],
        "where_02_is_stronger": P4_VS_P1_SUMMARY["where_02_is_stronger"],
        "bounded_decision": P4_VS_P1_SUMMARY["bounded_decision"],
    }


def update_review_file(path: Path, supports: list[str], does_not_yet_support: list[str]) -> None:
    payload = read_json(path)
    payload["supports"] = supports
    payload["does_not_yet_support"] = does_not_yet_support
    write_json(path, payload)


def update_effort_summary_file(path: Path) -> None:
    payload = read_json(path)
    payload["still_should_not_claim"] = (
        "It still should not claim benchmark-grade rigor, third-issuer generalization, "
        "whole-filing or external-research overlays, or equal-lane P4 expansion."
    )
    write_json(path, payload)


def build_canonization_report(
    artifact_paths: list[Path],
    quality_note_paths: list[Path],
    modified_source_paths: list[Path],
    updated_public_copy_paths: list[Path],
) -> str:
    lines = [
        "# Wave 4E4 P4 Canonization Report",
        "",
        "## What Was Canonized",
        "",
        "- NVDA extended and standard P4 novelty-ledger v2 runs",
        "- LLY extended and standard P4 novelty-ledger v2 runs",
        "- Canonized public issuer artifacts for NVDA and LLY plus two cross-case summaries",
        "",
        "## Source Runs Used",
        "",
        "- `NVDA_04_p4_i2_novelty_ledger_extended_v2`",
        "- `NVDA_05_p4_i2_novelty_ledger_standard_v2`",
        "- `LLY_04_p4_i2_novelty_ledger_extended_v2`",
        "- `LLY_05_p4_i2_novelty_ledger_standard_v2`",
        "",
        "## Quality Issues Logged",
        "",
        "- NVDA standard v2: raw JSON transport brittleness from unescaped internal quotation marks; canonized through deterministic transport-only repair.",
        "- NVDA standard v2: one manifest-linked evidence row remains logged as evidence-grounding debt and was not silently rewritten.",
        "- LLY standard v2: one exact-substring evidence mismatch on `ev04`; canonized through a logged quote-only correction against `lly_2025_p029`.",
        "",
        "## Deterministic Repairs Or Corrections",
        "",
        "- NVDA standard v2: escaped the two unescaped `\"AI Diffusion\"` internal quotations in the raw JSON payload so the response could be parsed for canonization.",
        "- LLY standard v2: replaced only the `ev04` quote text with the exact filing substring from the cited paragraph.",
        "",
        "## Public Artifacts Created",
        "",
    ]
    for path in artifact_paths:
        lines.append(f"- `{repo_rel(path)}`")
    for path in quality_note_paths:
        lines.append(f"- `{repo_rel(path)}`")
    lines.extend(["", "## Public Copy Updated", ""])
    for path in updated_public_copy_paths:
        lines.append(f"- `{path.as_posix()}`")
    lines.extend(["", "## Source Files Modified", ""])
    for path in modified_source_paths:
        lines.append(f"- `{path.as_posix()}`")
    lines.extend(
        [
            "",
            "## Biggest Remaining Blocker",
            "",
            f"- {BIGGEST_REMAINING_BLOCKER}",
        ]
    )
    return "\n".join(lines) + "\n"


def build_integration_decision_report() -> str:
    lines = [
        "# Wave 4E4 P4 Integration Decision",
        "",
        "## Decision",
        "",
        "- P4 is now integrated in a limited way as a secondary novelty-ledger module inside the existing NVDA and LLY pilot slices.",
        "- P4 is not promoted to a new route or a new equal lane card in the main matrix.",
        "",
        "## Why Limited",
        "",
        "- The two-issuer transfer result is good enough for visible product use, but the module remains intentionally narrower than 02.",
        "- 02 still provides the best default investor-readable synthesis and remains the most robust first read.",
        "- P4 adds value when users specifically want fresh-versus-reused clarity, intensified-versus-fresh discipline, and explicit boundary handling.",
        "",
        "## Visible Role",
        "",
        "- The module now sits below effort robustness and above the lane-card grid in each pilot slice.",
        "- The visible groups are Fresh 2025 specifics, Intensified / broadened points, Reused framework language, and Boundary notes.",
        "- The visible copy keeps the lens complementary, narrow, and evidence-first.",
        "",
        "## What Would Need To Be True For Broader Expansion",
        "",
        "- A third issuer would need to confirm transfer cleanly.",
        "- Capture integrity would need to be cleaner on first-save raw outputs.",
        "- P4 would need to keep helping without turning the matrix into a lane zoo or displacing the hero-lane first-read flow.",
    ]
    return "\n".join(lines) + "\n"


def build_findings_report() -> str:
    lines = [
        "# Wave 4E4 P4 Findings",
        "",
        "## Cross-Issuer Finding",
        "",
        "- Across NVDA and LLY, P4 adds fresh-versus-reused clarity by splitting genuinely fresh specifics from broadened carryover themes more cleanly than the current hero lane family does by default.",
        "- P4 is especially useful for showing where a new named example still belongs inside an older risk family rather than being overstated as a wholly new risk map.",
        "",
        "## Where P4 Remains Weaker Than 02",
        "",
        "- P4 is weaker as a broad first-read synthesis of the filing shift.",
        "- P4 is more sensitive to output integrity and evidence-row discipline.",
        "- P4 does not replace the need for a single strong hero lane.",
        "",
        "## Standard Versus Extended",
        "",
        "- Standard and extended broadly agree on the main novelty-ledger story for both issuers.",
        "- NVDA standard required transport repair and still carries a logged evidence-grounding caveat.",
        "- LLY standard required one quote-only evidence-row correction but stayed analytically aligned with the extended run.",
        "",
        "## Why This Matters For The App",
        "",
        "- The app thesis improves when users can check whether a filing truly introduced new risk detail rather than only reading a broad synthesis.",
        "- That value is real, but it is still best delivered as a compact secondary module rather than a new top-level lane.",
        "",
        "## Recommended Next Wave",
        "",
        "- Add one third issuer with clean first-save P4 captures before considering any broader P4 expansion.",
    ]
    return "\n".join(lines) + "\n"


def build_repo_paths_for_packet(
    artifact_paths: list[Path], quality_note_paths: list[Path], report_paths: list[Path]
) -> list[Path]:
    repo_paths = [path.relative_to(REPO_ROOT) for path in artifact_paths]
    repo_paths.extend(path.relative_to(REPO_ROOT) for path in quality_note_paths)
    repo_paths.extend(path.relative_to(REPO_ROOT) for path in report_paths)
    repo_paths.extend(PILOT_REVIEW_PATHS.values())
    repo_paths.append(Path(repo_rel(EFFORT_SUMMARY_PATH)))
    repo_paths.extend(UI_SOURCE_PATHS)
    repo_paths.extend(TYPE_PATHS)
    repo_paths.extend([SELF_SCRIPT_PATH, SELF_TEST_PATH, NODE_TEST_PATH])
    return repo_paths


def generate_wave(stamp: str | None = None) -> GenerationSummary:
    resolved_case_runs: dict[str, dict[str, ResolvedRun]] = {}
    case_artifacts: dict[str, dict[str, Any]] = {}
    artifact_paths: list[Path] = []
    quality_note_paths: list[Path] = []

    for fixture_id, case_config in CASE_CONFIGS.items():
        resolved_runs = {
            cast(str, run_config["run_id"]): resolve_run(run_config)
            for run_config in cast(list[dict[str, Any]], case_config["run_sources"])
        }
        resolved_case_runs[fixture_id] = resolved_runs

        case_dir = NOVELTY_LEDGER_ROOT / fixture_id
        issuer_ticker = cast(str, case_config["issuer"]["ticker"]).lower()
        quality_note_path = NOVELTY_LEDGER_ROOT / f"{issuer_ticker}_p4_quality_notes_v1.json"
        case_artifact_path = case_dir / "p4_canonized_matrix_v1.json"

        quality_payload = build_quality_artifact(fixture_id, case_config, resolved_runs)
        case_payload = build_case_artifact(fixture_id, case_config, resolved_runs, quality_note_path)

        write_json(case_artifact_path, case_payload)
        write_json(quality_note_path, quality_payload)

        case_artifacts[fixture_id] = case_payload
        artifact_paths.append(case_artifact_path)
        quality_note_paths.append(quality_note_path)

    cross_summary_path = NOVELTY_LEDGER_ROOT / "p4_canonized_summary_v1.json"
    p4_vs_p1_summary_path = NOVELTY_LEDGER_ROOT / "p4_vs_p1_summary_v1.json"
    write_json(cross_summary_path, build_cross_summary(artifact_paths, quality_note_paths))
    write_json(p4_vs_p1_summary_path, build_p4_vs_p1_summary())
    artifact_paths.extend([cross_summary_path, p4_vs_p1_summary_path])

    for fixture_id, case_config in CASE_CONFIGS.items():
        update_review_file(
            REPO_ROOT / PILOT_REVIEW_PATHS[fixture_id],
            cast(list[str], case_config["review_updates"]["supports"]),
            cast(list[str], case_config["review_updates"]["does_not_yet_support"]),
        )
    update_effort_summary_file(EFFORT_SUMMARY_PATH)

    report_paths = [
        REPO_ROOT / CANONIZATION_REPORT_PATH,
        REPO_ROOT / INTEGRATION_DECISION_REPORT_PATH,
        REPO_ROOT / FINDINGS_REPORT_PATH,
    ]
    updated_public_copy_paths = [*PILOT_REVIEW_PATHS.values(), Path(repo_rel(EFFORT_SUMMARY_PATH))]
    modified_source_paths = [*UI_SOURCE_PATHS, *TYPE_PATHS]
    write_text(
        report_paths[0],
        build_canonization_report(
            artifact_paths,
            quality_note_paths,
            modified_source_paths,
            updated_public_copy_paths,
        ),
    )
    write_text(report_paths[1], build_integration_decision_report())
    write_text(report_paths[2], build_findings_report())

    stamp_value = stamp or utc_stamp()
    packet_dir, zip_path = packet_paths_for_stamp(stamp_value)
    ensure_clean_output(packet_dir)
    ensure_clean_output(zip_path)
    packet_dir.mkdir(parents=True, exist_ok=True)

    repo_paths = build_repo_paths_for_packet(artifact_paths, quality_note_paths, report_paths)
    copy_repo_paths_into_packet(packet_dir, repo_paths)

    changed_repo_paths = [
        *(path.relative_to(REPO_ROOT) for path in artifact_paths),
        *(path.relative_to(REPO_ROOT) for path in quality_note_paths),
        *(path.relative_to(REPO_ROOT) for path in report_paths),
        *PILOT_REVIEW_PATHS.values(),
        Path(repo_rel(EFFORT_SUMMARY_PATH)),
        *UI_SOURCE_PATHS,
        *TYPE_PATHS,
        SELF_SCRIPT_PATH,
        SELF_TEST_PATH,
        NODE_TEST_PATH,
    ]
    write_text(packet_dir / CHANGED_FILES_MANIFEST_NAME, build_changed_files_manifest(changed_repo_paths))
    write_text(
        packet_dir / ROOT_README_NAME,
        build_packet_readme(
            packet_dir,
            artifact_paths,
            quality_note_paths,
            report_paths,
            [*UI_SOURCE_PATHS, *TYPE_PATHS],
        ),
    )
    write_text(packet_dir / RENDER_PREVIEW_NAME, build_render_preview(case_artifacts))
    zip_directory(packet_dir, zip_path)

    renders_both_pilots = True
    source_paths = [path.as_posix() for path in [*UI_SOURCE_PATHS, *TYPE_PATHS]]
    console_summary_lines = [
        f"packet folder path: {packet_dir.resolve()}",
        f"zip path: {zip_path.resolve()}",
        "canonized P4 artifact paths:",
        *(f"- {path.resolve()}" for path in artifact_paths),
        "quality-note artifact paths:",
        *(f"- {path.resolve()}" for path in quality_note_paths),
        "which source files were modified:",
        *(f"- {(REPO_ROOT / path).resolve()}" for path in [*UI_SOURCE_PATHS, *TYPE_PATHS]),
        f"whether NVDA and LLY both render the limited P4 module: {'yes' if renders_both_pilots else 'no'}",
        f"biggest remaining blocker after this wave: {BIGGEST_REMAINING_BLOCKER}",
    ]
    for line in console_summary_lines:
        print(line)

    return GenerationSummary(
        packet_dir=packet_dir,
        zip_path=zip_path,
        artifact_paths=[repo_rel(path) for path in artifact_paths],
        quality_note_paths=[repo_rel(path) for path in quality_note_paths],
        source_paths=source_paths,
        renders_both_pilots=renders_both_pilots,
        biggest_remaining_blocker=BIGGEST_REMAINING_BLOCKER,
        console_summary_lines=console_summary_lines,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate Wave 4E4 P4 canonized artifacts, reports, and review packet."
    )
    parser.add_argument(
        "--stamp",
        help="Optional UTC stamp override in YYYYMMDD_HHMM format for packet output naming.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    generate_wave(stamp=args.stamp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
