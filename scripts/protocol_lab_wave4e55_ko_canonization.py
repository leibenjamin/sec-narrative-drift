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
PILOT_MATRICES_ROOT = BUSINESS_ROOT / "pilot_matrices"
NOVELTY_LEDGER_ROOT = BUSINESS_ROOT / "novelty_ledger"
SKEPTIC_CASES_ROOT = BUSINESS_ROOT / "skeptic_cases"
PRODUCT_POSITIONING_ROOT = BUSINESS_ROOT / "product_positioning"
REGISTRIES_ROOT = BUSINESS_ROOT / "registries"
REPORTS_ROOT = REPO_ROOT / "reports" / "protocol_lab"

TASK_NAME = "Wave 4E5.5 = KO Canonization + Third-Issuer Limited Integration Decision"
PACKET_PREFIX = "wave4e55_ko_canonized_integration"
ROOT_README_NAME = "README.md"
CHANGED_FILES_MANIFEST_NAME = "changed_files_manifest.md"
RENDER_PREVIEW_NAME = "render_preview.md"

CANONIZATION_REPORT_PATH = Path("reports/protocol_lab/wave4e55_ko_canonization_report.md")
INTEGRATION_DECISION_REPORT_PATH = Path(
    "reports/protocol_lab/wave4e55_third_issuer_integration_decision.md"
)
VIVID_VS_SKEPTIC_REPORT_PATH = Path(
    "reports/protocol_lab/wave4e55_vivid_vs_skeptic_findings.md"
)
PRODUCT_FRAMING_REPORT_PATH = Path("reports/protocol_lab/wave4e55_product_framing_note.md")
SELF_SCRIPT_PATH = Path("scripts/protocol_lab_wave4e55_ko_canonization.py")
SELF_TEST_PATH = Path("scripts/tests/test_protocol_lab_wave4e55_ko_canonization.py")
NODE_TEST_PATHS = [
    Path("scripts/tests/test_protocol_lab_matrix_registry.mjs"),
    Path("scripts/tests/test_protocol_lab_matrix_story.mjs"),
    Path("scripts/tests/test_protocol_lab_novelty_ledger_data.mjs"),
    Path("scripts/tests/test_protocol_lab_skeptic_case_data.mjs"),
]

PILOT_REVIEW_PATHS = {
    "NVDA_2024_2025_10k_item1a": Path(
        "public/data/business_document_protocol_lab/pilot_matrices/NVDA_2024_2025_10k_item1a/pilot_matrix_review_v1.json"
    ),
    "LLY_2024_2025_10k_item1a": Path(
        "public/data/business_document_protocol_lab/pilot_matrices/LLY_2024_2025_10k_item1a/pilot_matrix_review_v1.json"
    ),
}
PILOT_REGISTRY_PATH = Path(
    "public/data/business_document_protocol_lab/registries/pilot_matrices_v1.json"
)
P4_SUMMARY_PATH = Path(
    "public/data/business_document_protocol_lab/novelty_ledger/p4_canonized_summary_v1.json"
)
P4_VS_P1_SUMMARY_PATH = Path(
    "public/data/business_document_protocol_lab/novelty_ledger/p4_vs_p1_summary_v1.json"
)
CURRENT_CASE_MIX_PATH = Path(
    "public/data/business_document_protocol_lab/product_positioning/current_case_mix_v1.json"
)

SOURCE_UI_PATHS = [
    Path("src/components/ProtocolLabPilotMatrixPanel.tsx"),
    Path("src/components/LabPanel.tsx"),
    Path("src/pages/Company.tsx"),
    Path("src/pages/Home.tsx"),
    Path("src/pages/Companies.tsx"),
]
SOURCE_DATA_PATHS = [
    Path("src/lib/protocolLabMatrixTypes.ts"),
    Path("src/lib/protocolLabMatrixSchemas.ts"),
    Path("src/lib/protocolLabMatrixData.ts"),
    Path("src/lib/protocolLabMatrixPresentation.ts"),
]

PACKET_ROOT = "wave4e5_third_issuer_skeptic_packet_20260322_0353"
FIXTURE_ID = "KO_2024_2025_10k_item1a"
MATRIX_ID = "KO_2024_2025_10k_item1a__desktop_pilot_matrix_v1"
PAIR_INFO = {
    "ticker": "KO",
    "issuer_name": "The Coca-Cola Company",
    "year_from": 2024,
    "year_to": 2025,
    "form_type": "10-K",
    "section_id": "item_1a",
}
ISSUER = {
    "ticker": "KO",
    "issuer_name": "The Coca-Cola Company",
}

RUN_CONFIGS = [
    {
        "run_id": "KO_02_p1_i2_tagged_packet",
        "lane_family": "02",
        "reasoning_variant": "extended",
        "response_path": Path(
            "wave4e5_third_issuer_skeptic_packet_20260322_0353/KO_02_p1_i2_tagged_packet/response.json"
        ),
        "run_manifest_path": Path(
            "wave4e5_third_issuer_skeptic_packet_20260322_0353/KO_02_p1_i2_tagged_packet/run_manifest.json"
        ),
    },
    {
        "run_id": "KO_02_p1_i2_tagged_packet_standard",
        "lane_family": "02",
        "reasoning_variant": "standard",
        "response_path": Path(
            "wave4e5_third_issuer_skeptic_packet_20260322_0353/KO_02_p1_i2_tagged_packet_standard/response.json"
        ),
        "run_manifest_path": Path(
            "wave4e5_third_issuer_skeptic_packet_20260322_0353/KO_02_p1_i2_tagged_packet_standard/run_manifest.json"
        ),
    },
    {
        "run_id": "KO_04_p4_i2_novelty_ledger_extended_v2",
        "lane_family": "p4",
        "reasoning_variant": "extended",
        "response_path": Path(
            "wave4e5_third_issuer_skeptic_packet_20260322_0353/KO_04_p4_i2_novelty_ledger_extended_v2/response.json"
        ),
        "run_manifest_path": Path(
            "wave4e5_third_issuer_skeptic_packet_20260322_0353/KO_04_p4_i2_novelty_ledger_extended_v2/run_manifest.json"
        ),
    },
    {
        "run_id": "KO_05_p4_i2_novelty_ledger_standard_v2",
        "lane_family": "p4",
        "reasoning_variant": "standard",
        "response_path": Path(
            "wave4e5_third_issuer_skeptic_packet_20260322_0353/KO_05_p4_i2_novelty_ledger_standard_v2/response.json"
        ),
        "run_manifest_path": Path(
            "wave4e5_third_issuer_skeptic_packet_20260322_0353/KO_05_p4_i2_novelty_ledger_standard_v2/run_manifest.json"
        ),
    },
]

KO_STORY = {
    "consensus_findings": [
        "Across the canonized KO runs, FY2025 keeps most of the prior Item 1A architecture and should be read as selective sharpening rather than a dramatic rewrite.",
        "The useful signal clusters around health-policy and demand pressure, product-quality and recall execution, bottler concentration, partner-conduct spillover, and updated Pillar Two detail.",
        "The two 02 runs broadly agree that the hero lane remains useful on a mostly stable filing without forcing significance into routine upkeep.",
        "The two P4 runs broadly agree that freshness stays narrow on KO and that most movement belongs in broadened carryover or boundary buckets.",
    ],
    "disagreement_findings": [
        "02 remains the best first read because it keeps the broader filing shift legible while staying restrained.",
        "P4 adds value by sorting genuinely fresh specifics from reused structure, but it is narrower and more classification-sensitive than 02.",
        "The extra 2025 specifics beyond Pillar Two are not identical across the two P4 runs, which is why KO works as a restraint test rather than a novelty showcase.",
    ],
    "why_this_case_matters": "KO matters because it is the lower-drift skeptic case: the filing is mostly stable, but the useful signal is still visible when the product stays disciplined about selective sharpening rather than hunting for drama.",
    "investor_read": "The investor read is not that Coca-Cola suddenly rewrote its risk map. It is that FY2025 makes a few areas more decision-useful by sharpening health-policy pressure on sweetened beverages, broadening product-quality and recall execution risk, naming bottler concentration more explicitly, and updating Pillar Two developments with dated 2025 to 2026 specifics.",
    "protocol_read": "Methodologically, KO is useful because it shows whether the product can remain helpful when the filing pair is stable. The answer is yes, but only when the hero lane stays restrained and the secondary novelty lens remains narrow about what is actually fresh versus what is better read as broadened carryover or reused structure.",
    "caveat": "This remains a bounded pilot slice. KO improves credibility because it is a lower-drift proof point, but it does not justify broad issuer expansion, whole-filing overlays, or equal-lane promotion of P4.",
}

KO_REVIEW = {
    "supports": [
        "On this fixed KO Item 1A pair, 02 remains useful even when the filing is mostly stable and only selectively sharpened.",
        "KO now serves as a visible third pilot that broadens the product claim beyond vivid cases without expanding into a broad issuer gallery.",
        "P4 is useful on KO as a compact fresh-versus-reused check, especially for keeping selective 2025 specifics inside a disciplined proof boundary.",
        "The current visible pilot mix can now show both vivid high-signal cases and a lower-drift skeptic case while keeping 02 as the hero lane and P4 secondary.",
    ],
    "does_not_yet_support": [
        "This is still a bounded three-case pilot slice rather than a benchmark or broad issuer expansion claim.",
        "It does not yet justify whole-filing context overlays, external research overlays, or a wider route or gallery redesign.",
        "It does not support equal-lane P4 promotion, protocol-zoo expansion, or claims that every low-drift filing will be equally legible.",
    ],
    "why_02_is_hero": "02 is the hero because it gives the clearest restrained first read on KO while still surfacing the selective health-policy, quality, bottler, and tax updates that matter.",
    "why_03_is_main_comparator": "No KO 03 lane is surfaced in this wave. The skeptic-case decision is to keep the visible matrix one-lane rather than invent a comparator that was not canonized for limited integration.",
    "why_00_is_control": "No KO control lane is surfaced in this wave. The product goal here is to test restraint on a low-drift case, not to broaden the visible matrix into another multi-lane panel family.",
    "why_01_is_secondary": "No KO 01 lane is surfaced in this wave. P4 remains the secondary lens on this case, but it stays in the compact novelty-ledger module rather than becoming a visible matrix lane.",
}

KO_P1_VS_P4_SUMMARY = {
    "what_02_does_best": "02 does best on KO when the user needs the broad first-read synthesis of a mostly stable filing without losing the selective sharpened points that actually changed the read.",
    "what_p4_does_best": "P4 does best on KO when the user specifically wants to test what is genuinely fresh, what is broadened or intensified, what is reused structure, and which boundary cases should not be overstated.",
    "why_02_remains_hero": "02 remains the hero because the product still needs one disciplined, investor-readable first lane, and KO confirms that 02 can stay useful even when there is no dramatic rewrite to lead with.",
    "why_p4_remains_secondary": "P4 remains secondary because its value on KO is narrower and more classification-sensitive. It helps keep freshness claims honest, but it does not replace the broader filing-shift read.",
    "why_ko_is_restraint_case": "KO is especially useful as a restraint and credibility case because it proves the product is not only for vivid filings. It can also stay helpful when the right answer is 'mostly stable, selectively sharpened.'",
}

KO_SKEPTIC_CANONIZATION = {
    "finding_summary": "KO's FY2025 Item 1A is mostly stable overall, but it selectively sharpens health-policy and demand language, product-quality and recall execution, bottler concentration, partner-conduct spillover, and Pillar Two updates.",
    "skeptic_case_role_statement": "KO is the lower-drift skeptic case. Its job is to prove that the product can still be useful when a filing changes selectively rather than dramatically.",
    "agreement_snapshot": {
        "02_standard_vs_extended": {
            "broadly_agree": True,
            "note": "Yes. Both 02 runs read KO as mostly stable with selective sharpening in health-policy and demand pressure, product-quality and recall execution, bottler exposure, and Pillar Two detail.",
        },
        "p4_standard_vs_extended": {
            "broadly_agree": True,
            "note": "Yes. Both P4 runs keep freshness narrow, treat most visible movement as broadened carryover, and preserve a disciplined boundary around what should not be overstated.",
        },
    },
    "supports_visible_limited_integration": True,
    "visible_integration_note": "Yes. KO should be visible as a limited third pilot because all four runs were usable and the low-drift verdict is product-legible without requiring new routes or a broader issuer gallery.",
    "known_quality_caveats": [
        "All four KO runs were usable as saved and did not require deterministic transport or evidence-row correction.",
        "The main caveat is analytical restraint: beyond Pillar Two, the two P4 runs do not name exactly the same extra 2025 specifics as fresh, which is why KO should be framed as a skeptic case rather than a novelty showcase.",
    ],
    "product_interpretation": "The product is more credible when it can surface selective sharpening on KO with restraint instead of only reading dramatic filing rewrites like NVDA and LLY.",
    "framing_note": "Mostly stable, selectively sharpened. The point here is disciplined detection, not dramatic novelty hunting.",
    "short_quality_caveat": "All four KO runs were usable as saved. The caution here is overreading, not transport repair.",
}

KO_NOVELTY_CASE = {
    "issuer_finding_summary": "Across the canonized KO P4 runs, the freshest movement is narrow and concentrated in dated Pillar Two updates plus a small number of sharper 2025 specifics, while most of the filing remains a reused framework with broadened examples inside older risk families.",
    "p4_role_statement": "This lens is useful on KO because it keeps freshness claims disciplined. It stays secondary because the hero lane still gives the better broad first read on a mostly stable filing.",
    "known_quality_caveats": [
        "Both KO P4 runs were parseable and usable as saved; no transport or evidence-row correction was required during canonization.",
        "The standard and extended P4 runs differ slightly on which extra 2025 specifics beyond Pillar Two deserve the 'fresh' label, but both keep freshness narrow and do not change the broad verdict.",
    ],
    "standard_and_extended_broadly_agree": True,
    "standard_and_extended_agreement_note": "Yes. Both runs agree that KO is mostly reused structure with a narrow set of fresh specifics, that supplier-cost tariffs and health-policy pressure are broadened carryover themes, and that boundary cases should not be overstated.",
    "suitable_for_limited_app_integration": True,
    "integration_note": "Suitable for the existing compact secondary module because the freshness verdict stays narrow and disciplined across both runs.",
    "comparison_to_02": {
        "where_p4_adds_value": "P4 adds a cleaner fresh-versus-reused check than 02, especially for separating dated Pillar Two updates from broadened carryover themes like tariff pass-through, health-policy pressure, recall execution, and privacy compliance.",
        "where_02_remains_stronger": "02 remains stronger as the broad default synthesis because it integrates the full filing shift instead of focusing only on freshness classification.",
        "why_secondary_only": "P4 is useful on KO precisely because it is narrower and more disciplined about freshness. That makes it a compact second lens, not a replacement for the hero lane.",
    },
    "module_sections": {
        "fresh_2025_specifics": [
            {
                "item_id": "pillar_two_side_by_side_framework",
                "label": "Pillar Two side-by-side framework update",
                "text": "FY2025 newly adds dated Pillar Two side-by-side disclosures tied to the June 2025 G7 understanding and January 2026 OECD guidance.",
                "support_level": "both",
                "evidence_refs": [
                    {"run_id": "KO_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev20"},
                    {"run_id": "KO_05_p4_i2_novelty_ledger_standard_v2", "evidence_id": "ev08"},
                ],
            },
            {
                "item_id": "bottler_concentration_and_partner_conduct",
                "label": "Bottler concentration and partner-conduct spillover",
                "text": "FY2025 newly discloses that one bottler represented 10% of net operating revenues and newly makes bottling-partner conduct a more explicit reputational and execution spillover channel.",
                "support_level": "extended_primary_standard_compatible",
                "evidence_refs": [
                    {"run_id": "KO_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev17"},
                    {"run_id": "KO_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev18"},
                ],
            },
        ],
        "intensified_or_broadened_points": [
            {
                "item_id": "tariff_supplier_cost_pass_through",
                "label": "Tariff risk widened to supplier sourcing costs",
                "text": "The tariff theme already existed in FY2024, but FY2025 broadens it by explicitly adding supplier-cost pass-through.",
                "support_level": "both",
                "evidence_refs": [
                    {"run_id": "KO_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev05"},
                    {"run_id": "KO_05_p4_i2_novelty_ledger_standard_v2", "evidence_id": "ev11"},
                ],
            },
            {
                "item_id": "health_policy_and_snap_pressure",
                "label": "Sweetened-beverage demand risk broadened with childhood-disease and SNAP examples",
                "text": "FY2025 keeps the existing sweetened-beverage demand theme but sharpens it with childhood chronic disease initiatives and benefit-program restrictions such as SNAP.",
                "support_level": "both",
                "evidence_refs": [
                    {"run_id": "KO_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev08"},
                    {"run_id": "KO_05_p4_i2_novelty_ledger_standard_v2", "evidence_id": "ev03"},
                ],
            },
            {
                "item_id": "quality_and_recall_execution",
                "label": "Product-quality execution broadened to contract manufacturers and remediation consequences",
                "text": "The quality and recall theme persists, but FY2025 widens the operational perimeter to contract manufacturers, more specific triggers, and remediation-driven production effects.",
                "support_level": "both",
                "evidence_refs": [
                    {"run_id": "KO_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev14"},
                    {"run_id": "KO_05_p4_i2_novelty_ledger_standard_v2", "evidence_id": "ev14"},
                ],
            },
        ],
        "reused_framework_language": [
            {
                "item_id": "macro_affordability_and_inflation",
                "label": "Macro affordability and inflation frame remains",
                "text": "Both years keep the same basic warning that inflation and weaker economic conditions can pressure beverage affordability and consumer demand.",
                "support_level": "extended_primary_standard_compatible",
                "evidence_refs": [
                    {"run_id": "KO_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev01"},
                    {"run_id": "KO_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev02"},
                ],
            },
            {
                "item_id": "supply_chain_input_volatility",
                "label": "Supply-chain input volatility framework remains",
                "text": "The broad warning that raw materials and other inputs face volatility and availability pressure remains materially reused across the two filings.",
                "support_level": "extended_primary_standard_compatible",
                "evidence_refs": [
                    {"run_id": "KO_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev03"},
                    {"run_id": "KO_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev04"},
                ],
            },
            {
                "item_id": "ai_regulatory_perimeter",
                "label": "AI and sustainability stay inside recurring compliance scaffolds",
                "text": "AI, sustainability reporting, and climate-related obligations remain recurring compliance families rather than wholly new FY2025 risk maps.",
                "support_level": "standard_primary_extended_compatible",
                "evidence_refs": [
                    {"run_id": "KO_05_p4_i2_novelty_ledger_standard_v2", "evidence_id": "ev23"},
                    {"run_id": "KO_05_p4_i2_novelty_ledger_standard_v2", "evidence_id": "ev25"},
                ],
            },
        ],
        "boundary_notes": [
            {
                "item_id": "named_conflicts_generalized",
                "label": "Named geopolitical conflicts disappear, but the broader theme remains",
                "text": "FY2024 named Russia-Ukraine and Middle East conflicts directly, while FY2025 generalizes the language. That looks more like example swapping than a disappearance of geopolitical risk.",
                "support_level": "both",
                "evidence_refs": [
                    {"run_id": "KO_04_p4_i2_novelty_ledger_extended_v2", "evidence_id": "ev28"},
                    {"run_id": "KO_05_p4_i2_novelty_ledger_standard_v2", "evidence_id": "ev19"},
                ],
            },
            {
                "item_id": "named_product_examples_generalized",
                "label": "Named nontraditional beverage examples were generalized, not clearly removed",
                "text": "FY2025 drops the prior named value-added dairy and plant-based beverage examples, but the underlying product-expansion and safety complexity theme remains.",
                "support_level": "standard_primary_extended_compatible",
                "evidence_refs": [
                    {"run_id": "KO_05_p4_i2_novelty_ledger_standard_v2", "evidence_id": "ev20"},
                    {"run_id": "KO_05_p4_i2_novelty_ledger_standard_v2", "evidence_id": "ev21"},
                ],
            },
        ],
    },
}

NVDA_REVIEW_UPDATES = {
    "supports": [
        "On this fixed NVDA Item 1A pair, protocol and input treatment materially change usefulness, specificity, novelty separation, and auditability.",
        "Lane 02 is the clearest default first read because it combines a bounded structured contract with paragraph-addressable tagged evidence.",
        "Holding the tagged substrate fixed shows that protocol changes alone can materially alter the lead story and the organization of evidence.",
        "A bounded secondary novelty-ledger module now transfers across vivid and skeptic pilots without promoting P4 to an equal lane.",
    ],
    "does_not_yet_support": [
        "This is a bounded pilot slice and does not yet generalize across companies or establish a benchmark-grade leaderboard.",
        "It is not a final proof of universal superiority of one protocol outside the fixed filing pair and current visible pilot mix.",
        "It does not yet cover whole-filing context, external research overlays, broad issuer expansion, or equal-lane P4 promotion.",
    ],
}

LLY_REVIEW_UPDATES = {
    "supports": [
        "On this fixed LLY Item 1A pair, protocol structure materially changes first-read usefulness, specificity, novelty separation, and auditability.",
        "Lane 02 is the clearest default first read because it keeps the filing delta legible while staying contract-bounded and paragraph-addressable.",
        "Holding the tagged substrate fixed shows that protocol changes alone can materially alter which obesity-access, pricing, and concentration risks lead the narrative.",
        "A bounded secondary novelty-ledger module now transfers across vivid and skeptic pilots without promoting P4 to an equal lane.",
    ],
    "does_not_yet_support": [
        "This is a bounded pilot slice and does not yet generalize across companies or establish a benchmark-grade leaderboard.",
        "It is not a final proof of universal superiority of one protocol outside the fixed filing pair and the current limited visible pilot mix.",
        "It does not yet cover whole-filing context, external research overlays, a full lower-audit lab stack for every pilot, or equal-lane P4 promotion.",
    ],
}

BIGGEST_REMAINING_BLOCKER = (
    "Landing-level framing is still not done, so broader public claims remain bounded to the "
    "current three-case pilot slice."
)


@dataclass(frozen=True)
class ResolvedRun:
    run_id: str
    lane_family: str
    reasoning_variant: str
    response: dict[str, Any]
    run_manifest: dict[str, Any]
    response_path: Path
    run_manifest_path: Path


@dataclass(frozen=True)
class GenerationSummary:
    packet_dir: Path
    zip_path: Path
    ko_artifact_paths: list[str]
    cross_case_paths: list[str]
    source_paths: list[str]
    ko_visible_integration: bool
    app_visible_framing_updated: bool
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
        "Files created or modified by Wave 4E5.5:",
        "",
    ]
    for path in paths:
        lines.append(f"- `{path.as_posix()}`")
    return "\n".join(lines) + "\n"


def build_render_preview() -> str:
    lines = [
        "# Wave 4E5.5 Render Preview",
        "",
        "Deterministic text preview of the visible KO insertion and current case-mix framing changes.",
        "",
        "## KO Pilot Slice",
        "",
        "- single visible matrix lane: `02` hero only",
        "- top copy: skeptic-case framing instead of multi-lane comparison language",
        "- in-flow note: `Mostly stable, selectively sharpened. The point here is disciplined detection, not dramatic novelty hunting.`",
        "- matched-effort block: compact skeptic-case section with 02 agreement, P4 agreement, visible-third-pilot verdict, and short quality caveat",
        "- P4 novelty-ledger module: present below the skeptic block and still secondary",
        "- lower audit surfaces: remain available below because KO already has the broader lab stack",
        "",
        "## App Framing Touches",
        "",
        "- company page: KO visible-lane and default-read copy now frame the issuer as the low-drift skeptic proof point",
        "- home and companies cards: KO description now signals the low-drift proof-point role without changing the surrounding layout",
        "",
        "## Artifact Layer",
        "",
        "- current case mix artifact: NVDA and LLY as vivid high-signal pilots, KO as the skeptic low-drift pilot",
        "- cross-case summaries: third-pilot decision and vivid-vs-skeptic framing added for later landing-level copy work",
    ]
    return "\n".join(lines) + "\n"


def build_packet_readme(
    packet_dir: Path,
    ko_artifact_paths: list[Path],
    cross_case_paths: list[Path],
    report_paths: list[Path],
    source_paths: list[Path],
    loader_paths: list[Path],
) -> str:
    lines = [
        f"# {packet_dir.name}",
        "",
        "This packet contains the Wave 4E5.5 KO canonized artifacts, cross-case summaries, reports, modified source files, loader/type/schema changes, and deterministic render preview.",
        "",
        "## Included",
        "",
        "- KO pilot-matrix files plus KO skeptic-case and novelty-ledger canonized artifacts",
        "- cross-case skeptic summaries, novelty-ledger summaries, and current case-mix positioning artifact",
        "- Wave 4E5.5 reports and product framing note",
        "- modified React source files plus minimal loader/type/schema files",
        "- generator script, targeted tests, changed-file manifest, and render preview",
        "",
        "## KO Canonized Artifacts",
        "",
    ]
    for path in ko_artifact_paths:
        lines.append(f"- `{repo_rel(path)}`")
    lines.extend(["", "## Cross-Case Artifacts", ""])
    for path in cross_case_paths:
        lines.append(f"- `{repo_rel(path)}`")
    lines.extend(["", "## Reports", ""])
    for path in report_paths:
        lines.append(f"- `{repo_rel(path)}`")
    lines.extend(["", "## Modified Source Files", ""])
    for path in source_paths:
        lines.append(f"- `{path.as_posix()}`")
    lines.extend(["", "## Loader / Type / Schema Files", ""])
    for path in loader_paths:
        lines.append(f"- `{path.as_posix()}`")
    return "\n".join(lines) + "\n"


def build_evidence_preview(
    response: dict[str, Any], evidence_refs: list[dict[str, str]] | None = None
) -> list[dict[str, Any]]:
    evidence_bundle = response.get("evidence_bundle")
    if not isinstance(evidence_bundle, dict):
        raise TypeError("Response is missing evidence_bundle.")
    evidence_bundle = cast(dict[str, Any], evidence_bundle)
    items = evidence_bundle.get("items")
    if not isinstance(items, list):
        raise TypeError("Response is missing evidence_bundle.items.")
    evidence_items = cast(list[dict[str, Any]], items)

    if evidence_refs is None:
        selected_items = evidence_items[:3]
    else:
        selected_items: list[dict[str, Any]] = []
        for evidence_ref in evidence_refs:
            match = next(
                (
                    item
                    for item in evidence_items
                    if item.get("evidence_id") == evidence_ref["evidence_id"]
                ),
                None,
            )
            if match is None:
                raise KeyError(
                    f"Missing evidence {evidence_ref['evidence_id']} in response."
                )
            selected_items.append(match)

    preview: list[dict[str, Any]] = []
    for item in selected_items:
        preview.append(
            {
                "evidence_id": cast(str, item["evidence_id"]),
                "year_label": cast(str, item["year_label"]),
                "paragraph_id": cast(str, item["paragraph_id"]),
                "quote_text": cast(str, item["quote_text"]),
                "short_note": item.get("short_note") if isinstance(item.get("short_note"), str) else None,
            }
        )
    return preview


def validate_run_manifest(run_manifest: dict[str, Any], expected_run_id: str) -> None:
    run_identity = run_manifest.get("run_identity")
    if not isinstance(run_identity, dict):
        raise TypeError(f"{expected_run_id} run_manifest is missing run_identity.")
    run_identity = cast(dict[str, Any], run_identity)
    run_name = run_identity.get("run_name")
    if run_name != expected_run_id:
        raise ValueError(f"Run manifest identity mismatch: expected {expected_run_id}, got {run_name!r}.")


def resolve_runs() -> dict[str, ResolvedRun]:
    resolved: dict[str, ResolvedRun] = {}
    for config in RUN_CONFIGS:
        response_path = REPO_ROOT / cast(Path, config["response_path"])
        run_manifest_path = REPO_ROOT / cast(Path, config["run_manifest_path"])
        response = read_json(response_path)
        run_manifest = read_json(run_manifest_path)
        validate_run_manifest(run_manifest, cast(str, config["run_id"]))
        resolved[cast(str, config["run_id"])] = ResolvedRun(
            run_id=cast(str, config["run_id"]),
            lane_family=cast(str, config["lane_family"]),
            reasoning_variant=cast(str, config["reasoning_variant"]),
            response=response,
            run_manifest=run_manifest,
            response_path=response_path,
            run_manifest_path=run_manifest_path,
        )
    return resolved


def build_ko_pilot_cell(run: ResolvedRun) -> dict[str, Any]:
    change_brief = cast(dict[str, Any], run.response["change_brief"])
    evidence_bundle = cast(dict[str, Any], run.response["evidence_bundle"])
    evidence_items = cast(list[dict[str, Any]], evidence_bundle["items"])
    return {
        "artifact_schema_id": "pilot_matrix_cell_v1",
        "cell_id": "02_p1_i2_tagged_packet",
        "matrix_id": MATRIX_ID,
        "fixture_id": FIXTURE_ID,
        "label": "P1 + i2 tagged packet",
        "short_label": "P1+i2",
        "role": "hero",
        "lane_position": 1,
        "protocol_input_identity": {
            "protocol_id": "p1_structured_contract_v1",
            "protocol_label": "P1 structured contract",
            "input_pack_id": "i2_tagged_document_packet_v1",
            "input_label": "i2 tagged document packet",
            "display_text": "P1 structured contract + i2 tagged document packet",
        },
        "headline": cast(dict[str, Any], change_brief["summary_one_liner"])["text"],
        "summary": cast(dict[str, Any], change_brief["lead_shift"])["text"],
        "card_takeaway": "Best first read on the low-drift KO case: useful, specific, and restrained without forcing drama into a mostly stable filing.",
        "why_this_lane_matters": "This is the hero lane because it gives the clearest broad filing shift on KO while keeping the proof boundary compact and the emphasis disciplined.",
        "output_shape_info": {
            "contract_mode": "canonical_protocol_json",
            "display_text": "Canonical change brief plus evidence bundle",
            "canonical_structured": True,
        },
        "evidence_richness_tier": "high",
        "evidence_count_total": len(evidence_items),
        "auditability_note": "High auditability: tagged evidence and paragraph ids keep the selective-sharpening read grounded in the saved packet.",
        "strengths": [
            "Keeps the filing shift legible without overstating a low-drift case as a dramatic rewrite.",
            "Tagged paragraph evidence makes it straightforward to audit the specific sharpened points that do matter.",
        ],
        "limitations": [
            "This remains a single-company, single-pair pilot slice rather than a benchmark result.",
            "Much of KO's Item 1A remains reused structure, so the product value comes from restraint as much as novelty detection.",
        ],
        "evidence_preview": build_evidence_preview(run.response),
        "raw_source_refs": {
            "response_path": repo_rel(run.response_path),
            "run_manifest_path": repo_rel(run.run_manifest_path),
        },
        "normalization_status": {
            "kind": "canonical_json",
            "recovered": False,
            "source_json_parseable": True,
            "recovery_boundary": None,
            "required_labels_found": [],
            "note": "Parsed directly from the canonical structured Desktop response JSON.",
        },
    }


def build_ko_pilot_matrix(cell_path: Path, review_path: Path) -> dict[str, Any]:
    return {
        "artifact_schema_id": "pilot_matrix_v1",
        "matrix_id": MATRIX_ID,
        "fixture_id": FIXTURE_ID,
        "pair_info": copy.deepcopy(PAIR_INFO),
        "pilot_status": {
            "state": "pilot_active_skeptic_case_slice",
            "note": "KO is the lower-drift skeptic proof point inside the bounded pilot slice. The visible matrix intentionally stays one-lane so the app can show restraint rather than fabricate extra compare lanes.",
        },
        "lane_roles": {
            "02_p1_i2_tagged_packet": "hero",
        },
        "ordered_cell_ids": [
            "02_p1_i2_tagged_packet",
        ],
        "selected_default_cell_id": "02_p1_i2_tagged_packet",
        "comparison_pairs": [],
        "takeaways": [
            "KO shows that the product can still surface useful filing signal when the pair is mostly stable and selectively sharpened.",
            "Keeping the visible matrix to the 02 hero lane avoids panel sprawl and keeps the skeptic case legible.",
            "P4 remains available below as a secondary novelty-ledger check rather than becoming a peer lane in the matrix.",
        ],
        "caveats": [
            "This is a bounded single-issuer, single-pair skeptic-case pilot slice, not a benchmark.",
            "The absence of visible 03, 01, and 00 lanes is intentional and should be read as product discipline, not missing hidden winners.",
            "Claims here improve credibility beyond vivid cases, but they do not justify broad issuer expansion, overlays, or equal-lane P4 promotion.",
        ],
        "cell_paths": {
            "02_p1_i2_tagged_packet": public_data_rel(cell_path),
        },
        "review_path": public_data_rel(review_path),
    }


def build_ko_pilot_story() -> dict[str, Any]:
    return {
        "artifact_schema_id": "pilot_matrix_story_v1",
        "matrix_id": MATRIX_ID,
        "fixture_id": FIXTURE_ID,
        **copy.deepcopy(KO_STORY),
        "display_priority_order": [
            "why_this_case_matters",
            "consensus_findings",
            "investor_read",
            "disagreement_findings",
            "protocol_read",
            "caveat",
        ],
    }


def build_ko_pilot_review() -> dict[str, Any]:
    return {
        "artifact_schema_id": "pilot_matrix_review_v1",
        "matrix_id": MATRIX_ID,
        **copy.deepcopy(KO_REVIEW),
    }


def build_run_preview(resolved_runs: dict[str, ResolvedRun], evidence_refs: list[dict[str, str]]) -> list[dict[str, Any]]:
    preview: list[dict[str, Any]] = []
    for evidence_ref in evidence_refs:
        run = resolved_runs[evidence_ref["run_id"]]
        for item in build_evidence_preview(run.response, [evidence_ref]):
            item["run_id"] = evidence_ref["run_id"]
            preview.append(item)
    return preview


def build_ko_p4_case(resolved_runs: dict[str, ResolvedRun], quality_note_path: Path) -> dict[str, Any]:
    module_sections: dict[str, list[dict[str, Any]]] = {}
    for section_id, items in cast(dict[str, list[dict[str, Any]]], KO_NOVELTY_CASE["module_sections"]).items():
        section_items: list[dict[str, Any]] = []
        for item in items:
            section_items.append(
                {
                    "item_id": item["item_id"],
                    "label": item["label"],
                    "text": item["text"],
                    "support_level": item["support_level"],
                    "source_run_ids": list(dict.fromkeys(ref["run_id"] for ref in item["evidence_refs"])),
                    "evidence_preview": build_run_preview(resolved_runs, item["evidence_refs"]),
                }
            )
        module_sections[section_id] = section_items

    canonized_runs: list[dict[str, Any]] = []
    for run_id in [
        "KO_04_p4_i2_novelty_ledger_extended_v2",
        "KO_05_p4_i2_novelty_ledger_standard_v2",
    ]:
        run = resolved_runs[run_id]
        canonized_runs.append(
            {
                "run_id": run.run_id,
                "reasoning_variant": run.reasoning_variant,
                "source_response_path": repo_rel(run.response_path),
                "source_run_manifest_path": repo_rel(run.run_manifest_path),
                "canonization_status": "canonized_as_is",
                "quality_note_ids": [f"{run.run_id.lower()}__no_blocking_issue_observed"],
                "repair_summary": None,
            }
        )

    return {
        "artifact_schema_id": "p4_canonized_matrix_v1",
        "artifact_id": f"{FIXTURE_ID}__p4_canonized_matrix_v1",
        "fixture_id": FIXTURE_ID,
        "issuer": copy.deepcopy(ISSUER),
        "pair_info": copy.deepcopy(PAIR_INFO),
        "canonical_run_ids": [
            "KO_04_p4_i2_novelty_ledger_extended_v2",
            "KO_05_p4_i2_novelty_ledger_standard_v2",
        ],
        "canonized_runs": canonized_runs,
        "issuer_finding_summary": KO_NOVELTY_CASE["issuer_finding_summary"],
        "p4_role_statement": KO_NOVELTY_CASE["p4_role_statement"],
        "known_quality_caveats": copy.deepcopy(KO_NOVELTY_CASE["known_quality_caveats"]),
        "standard_and_extended_broadly_agree": KO_NOVELTY_CASE["standard_and_extended_broadly_agree"],
        "standard_and_extended_agreement_note": KO_NOVELTY_CASE["standard_and_extended_agreement_note"],
        "suitable_for_limited_app_integration": KO_NOVELTY_CASE["suitable_for_limited_app_integration"],
        "integration_note": KO_NOVELTY_CASE["integration_note"],
        "comparison_to_02": copy.deepcopy(KO_NOVELTY_CASE["comparison_to_02"]),
        "module_sections": module_sections,
        "quality_note_path": public_data_rel(quality_note_path),
    }


def build_ko_p4_quality_notes(resolved_runs: dict[str, ResolvedRun]) -> dict[str, Any]:
    notes: list[dict[str, Any]] = []
    for run_id in [
        "KO_04_p4_i2_novelty_ledger_extended_v2",
        "KO_05_p4_i2_novelty_ledger_standard_v2",
    ]:
        run = resolved_runs[run_id]
        notes.append(
            {
                "note_id": f"{run.run_id.lower()}__no_blocking_issue_observed",
                "issue_type": "no_blocking_issue_observed",
                "affected_run_id": run.run_id,
                "issue_family": "none",
                "deterministic_repair_allowed": False,
                "repair_applied_in_canonization": False,
                "changes_broad_analytical_verdict": False,
                "review_note": "Parsed cleanly and remained usable as saved. The main review requirement on KO is analytical restraint rather than repair.",
                "response_path": repo_rel(run.response_path),
                "run_manifest_path": repo_rel(run.run_manifest_path),
            }
        )
    return {
        "artifact_schema_id": "p4_quality_notes_v1",
        "artifact_id": "ko_p4_quality_notes_v1",
        "fixture_id": FIXTURE_ID,
        "issuer": copy.deepcopy(ISSUER),
        "notes": notes,
    }


def build_ko_skeptic_quality_notes(resolved_runs: dict[str, ResolvedRun]) -> dict[str, Any]:
    run_notes: list[dict[str, Any]] = []
    for run_id in [
        "KO_02_p1_i2_tagged_packet",
        "KO_02_p1_i2_tagged_packet_standard",
        "KO_04_p4_i2_novelty_ledger_extended_v2",
        "KO_05_p4_i2_novelty_ledger_standard_v2",
    ]:
        run = resolved_runs[run_id]
        status = "usable_as_saved"
        note = (
            "Parsed cleanly and stayed usable without correction. The broad verdict held."
            if run.lane_family == "p4"
            else "Parsed cleanly and stayed usable without correction. The restrained low-drift read held."
        )
        run_notes.append(
            {
                "run_id": run.run_id,
                "lane_family": run.lane_family,
                "reasoning_variant": run.reasoning_variant,
                "status": status,
                "issue_family": "none",
                "issue_type": "no_blocking_issue_observed",
                "correction_needed": False,
                "changes_broad_analytical_verdict": False,
                "review_note": note,
                "response_path": repo_rel(run.response_path),
                "run_manifest_path": repo_rel(run.run_manifest_path),
            }
        )
    return {
        "artifact_schema_id": "skeptic_case_quality_notes_v1",
        "artifact_id": "ko_quality_notes_v1",
        "fixture_id": FIXTURE_ID,
        "issuer": copy.deepcopy(ISSUER),
        "run_notes": run_notes,
    }


def build_ko_skeptic_canonized_matrix(
    skeptic_quality_path: Path, p1_vs_p4_summary_path: Path
) -> dict[str, Any]:
    return {
        "artifact_schema_id": "skeptic_case_canonized_matrix_v1",
        "artifact_id": f"{FIXTURE_ID}__ko_canonized_matrix_v1",
        "fixture_id": FIXTURE_ID,
        "issuer": copy.deepcopy(ISSUER),
        "pair_info": copy.deepcopy(PAIR_INFO),
        "canonical_run_ids": [
            "KO_02_p1_i2_tagged_packet",
            "KO_02_p1_i2_tagged_packet_standard",
            "KO_04_p4_i2_novelty_ledger_extended_v2",
            "KO_05_p4_i2_novelty_ledger_standard_v2",
        ],
        "finding_summary": KO_SKEPTIC_CANONIZATION["finding_summary"],
        "skeptic_case_role_statement": KO_SKEPTIC_CANONIZATION["skeptic_case_role_statement"],
        "agreement_snapshot": copy.deepcopy(KO_SKEPTIC_CANONIZATION["agreement_snapshot"]),
        "supports_visible_limited_integration": KO_SKEPTIC_CANONIZATION["supports_visible_limited_integration"],
        "visible_integration_note": KO_SKEPTIC_CANONIZATION["visible_integration_note"],
        "known_quality_caveats": copy.deepcopy(KO_SKEPTIC_CANONIZATION["known_quality_caveats"]),
        "product_interpretation": KO_SKEPTIC_CANONIZATION["product_interpretation"],
        "framing_note": KO_SKEPTIC_CANONIZATION["framing_note"],
        "short_quality_caveat": KO_SKEPTIC_CANONIZATION["short_quality_caveat"],
        "quality_note_path": public_data_rel(skeptic_quality_path),
        "p1_vs_p4_summary_path": public_data_rel(p1_vs_p4_summary_path),
    }


def build_ko_p1_vs_p4_summary() -> dict[str, Any]:
    return {
        "artifact_schema_id": "skeptic_case_p1_vs_p4_summary_v1",
        "artifact_id": "ko_p1_vs_p4_summary_v1",
        "fixture_id": FIXTURE_ID,
        "issuer": copy.deepcopy(ISSUER),
        **copy.deepcopy(KO_P1_VS_P4_SUMMARY),
    }


def build_third_pilot_summary() -> dict[str, Any]:
    return {
        "artifact_schema_id": "third_pilot_summary_v1",
        "artifact_id": "third_pilot_summary_v1",
        "added_issuer": "KO",
        "why_ko_was_added": "KO was added because NVDA and LLY alone could prove the product on vivid, high-signal cases, but they could not prove that the same compact flow stays useful when the filing is lower drift and restraint matters more than drama.",
        "what_ko_proves_beyond_nvda_and_lly": [
            "The product can still be useful when the filing pair is mostly stable and selectively sharpened.",
            "02 remains a credible hero lane even when there is no dramatic rewrite to lead with.",
            "P4 can stay narrow and disciplined on freshness instead of turning routine maintenance into fake novelty.",
        ],
        "should_be_visible_in_app": True,
        "visible_role": "KO should now be visible as the limited third pilot and skeptic low-drift proof point inside the current compact pilot slice.",
        "anti_expansion_note": "This is a third-pilot integration decision, not a reason to open a broad issuer gallery or route redesign.",
    }


def build_vivid_vs_skeptic_summary() -> dict[str, Any]:
    return {
        "artifact_schema_id": "vivid_vs_skeptic_summary_v1",
        "artifact_id": "vivid_vs_skeptic_summary_v1",
        "visible_case_mix": {
            "vivid_high_signal": ["NVDA", "LLY"],
            "skeptic_low_drift": ["KO"],
        },
        "why_both_matter": [
            "NVDA and LLY show that the product can stay useful when the filing shift is vivid and the named specifics are unusually high signal.",
            "KO shows that the product can also stay useful when the filing is mostly stable and the right read depends on selective sharpening plus disciplined restraint.",
            "Keeping both case types visible makes the app look less like a dramatic-case demo and more like a compact comparison-first product.",
        ],
        "product_value_statement": "The combination is stronger because it proves usefulness across both vivid and skeptic conditions without claiming broad coverage or benchmark completeness.",
        "anti_hype_note": "The point is not that every filing will produce dramatic novelty. The point is that the app can stay useful whether the filing is vivid or lower drift.",
    }


def build_current_case_mix() -> dict[str, Any]:
    return {
        "artifact_schema_id": "current_case_mix_v1",
        "artifact_id": "current_case_mix_v1",
        "visible_pilots": [
            {
                "ticker": "NVDA",
                "role": "vivid/high-signal",
                "note": "Fast-moving export-control, supply, and AI-regulation case.",
            },
            {
                "ticker": "LLY",
                "role": "vivid/high-signal",
                "note": "High-signal but different policy, pricing, and industry geometry.",
            },
            {
                "ticker": "KO",
                "role": "skeptic/low-drift restraint case",
                "note": "Mostly stable, selectively sharpened proof point.",
            },
        ],
        "product_statement": "This mix matters because the product can now credibly show usefulness on both vivid filings and a lower-drift skeptic case without widening into a broad issuer gallery.",
    }


def build_registry_payload() -> dict[str, Any]:
    return {
        "artifact_schema_id": "pilot_matrices_v1",
        "version": "1.0",
        "updated_at_utc": utc_now_iso(),
        "items": [
            {
                "fixture_id": "NVDA_2024_2025_10k_item1a",
                "ticker": "NVDA",
                "year_from": 2024,
                "year_to": 2025,
                "matrix_path": "data/business_document_protocol_lab/pilot_matrices/NVDA_2024_2025_10k_item1a/pilot_matrix_v1.json",
                "story_path": "data/business_document_protocol_lab/pilot_matrices/NVDA_2024_2025_10k_item1a/pilot_matrix_story_v1.json",
            },
            {
                "fixture_id": "LLY_2024_2025_10k_item1a",
                "ticker": "LLY",
                "year_from": 2024,
                "year_to": 2025,
                "matrix_path": "data/business_document_protocol_lab/pilot_matrices/LLY_2024_2025_10k_item1a/pilot_matrix_v1.json",
                "story_path": "data/business_document_protocol_lab/pilot_matrices/LLY_2024_2025_10k_item1a/pilot_matrix_story_v1.json",
            },
            {
                "fixture_id": FIXTURE_ID,
                "ticker": "KO",
                "year_from": 2024,
                "year_to": 2025,
                "matrix_path": f"data/business_document_protocol_lab/pilot_matrices/{FIXTURE_ID}/pilot_matrix_v1.json",
                "story_path": f"data/business_document_protocol_lab/pilot_matrices/{FIXTURE_ID}/pilot_matrix_story_v1.json",
            },
        ],
    }


def build_cross_p4_summary(issuer_artifact_paths: list[Path], quality_note_paths: list[Path]) -> dict[str, Any]:
    return {
        "artifact_schema_id": "p4_canonized_summary_v1",
        "artifact_id": "p4_canonized_summary_v1",
        "covered_issuers": ["NVDA", "LLY", "KO"],
        "issuer_artifact_paths": [public_data_rel(path) for path in issuer_artifact_paths],
        "quality_note_paths": [public_data_rel(path) for path in quality_note_paths],
        "what_p4_consistently_adds_over_02": [
            "P4 cleanly separates genuinely fresh, date-linked specifics from intensified or broadened carryover themes.",
            "P4 makes reused framework language explicit instead of leaving it implicit inside the broader first-read summary.",
            "P4 helps the product stay disciplined on lower-drift cases like KO by surfacing what should remain a boundary note instead of fake novelty.",
        ],
        "what_p4_still_does_not_do_as_well_as_02": [
            "P4 remains weaker than 02 as the broad default investor-readable synthesis of the filing shift.",
            "P4 remains more quality-sensitive because its value depends on narrow evidence and careful category discipline.",
            "P4 still does not justify becoming an equal top-level lane across the current pilot mix.",
        ],
        "why_secondary_only": "Across NVDA, LLY, and KO, P4 is strong enough for limited visible use as a compact secondary module, but it remains intentionally narrower than the hero lane and more dependent on classification discipline.",
        "overall_verdict": "Across the vivid high-signal cases and the KO skeptic case, P4 is now credible as a limited secondary novelty-ledger module. The product decision stays the same: keep 02 as the hero lane and keep P4 compact and secondary.",
    }


def build_p4_vs_p1_summary() -> dict[str, Any]:
    return {
        "artifact_schema_id": "p4_vs_p1_summary_v1",
        "artifact_id": "p4_vs_p1_summary_v1",
        "covered_issuers": ["NVDA", "LLY", "KO"],
        "hero_lane_family": "02_p1_i2_tagged_packet",
        "comparison_frame": "P4 is a complementary second lens next to the current 02 hero lane rather than a winner-take-all replacement.",
        "where_p4_is_stronger": [
            "P4 is stronger when the user specifically wants fresh-versus-reused clarity.",
            "P4 is stronger when a named 2025 example might really be a broadened carryover theme rather than a wholly new risk family.",
            "P4 is stronger on skeptic cases like KO when boundary discipline matters as much as novelty itself.",
        ],
        "where_02_is_stronger": [
            "02 remains stronger as the broad default investor-readable synthesis of the filing shift.",
            "02 remains stronger on overall product robustness and as the first lane a user should read.",
            "02 remains stronger when the user needs one compact filing-first summary before opening narrower secondary modules.",
        ],
        "bounded_decision": "Across NVDA, LLY, and KO, keep 02 as the hero lane and use P4 only as a compact secondary novelty-ledger module inside the current pilot slices.",
    }


def update_review_file(path: Path, supports: list[str], does_not_yet_support: list[str]) -> None:
    payload = read_json(path)
    payload["supports"] = supports
    payload["does_not_yet_support"] = does_not_yet_support
    write_json(path, payload)


def build_canonization_report(
    ko_artifact_paths: list[Path],
    cross_case_paths: list[Path],
    source_paths: list[Path],
    loader_paths: list[Path],
) -> str:
    lines = [
        "# Wave 4E5.5 KO Canonization Report",
        "",
        "## What KO Artifacts Were Canonized",
        "",
        "- KO pilot matrix bundle with one visible `02` hero lane",
        "- KO skeptic-case canonized matrix, quality notes, and `02` versus P4 summary",
        "- KO P4 canonized matrix and KO P4 quality notes",
        "- Cross-case skeptic summaries, current case mix artifact, pilot registry update, and refreshed P4 cross-case summaries",
        "",
        "## Run Outputs Used",
        "",
        "- `KO_02_p1_i2_tagged_packet`",
        "- `KO_02_p1_i2_tagged_packet_standard`",
        "- `KO_04_p4_i2_novelty_ledger_extended_v2`",
        "- `KO_05_p4_i2_novelty_ledger_standard_v2`",
        "",
        "## Quality Notes Recorded",
        "",
        "- All four KO runs were usable as saved and did not require unchanged reruns.",
        "- No transport/container, evidence-row integrity, or analytical/content repair was needed in canonization.",
        "- The main logged caution is analytical restraint: some extra P4 freshness classification differs slightly beyond Pillar Two, but the broad verdict does not change.",
        "",
        "## Public Artifacts Created Or Updated",
        "",
    ]
    for path in [*ko_artifact_paths, *cross_case_paths]:
        lines.append(f"- `{repo_rel(path)}`")
    lines.extend(["", "## Source Files Modified", ""])
    for path in [*source_paths, *loader_paths]:
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
        "# Wave 4E5.5 Third-Issuer Integration Decision",
        "",
        "## Decision",
        "",
        "- KO is now integrated visibly as the limited third pilot.",
        "- KO is framed as the skeptic case: mostly stable, selectively sharpened, and useful precisely because it tests restraint.",
        "- 02 remains the hero lane. P4 remains a compact secondary novelty-ledger module.",
        "",
        "## Why KO Is The Right Third Pilot",
        "",
        "- NVDA and LLY already prove the product on vivid, high-signal cases. KO proves usefulness on a lower-drift filing where overreading is the real risk.",
        "- KO is not a boring filler case. It is the case that tells you whether the app can still be useful when the right answer is disciplined sharpening instead of dramatic novelty.",
        "- All four KO runs were usable, which makes the visible integration decision honest rather than speculative.",
        "",
        "## Why This Does Not Justify Broad Expansion Yet",
        "",
        "- A visible third pilot is enough to improve product credibility, but it is not enough to justify a broad issuer gallery, route redesign, or protocol-zoo expansion.",
        "- The product still lacks landing-level framing work and still defers whole-filing and external-research overlays.",
        "",
        "## App Role",
        "",
        "- KO now appears as the low-drift skeptic proof point inside the existing compact pilot-slice flow.",
        "- The KO pilot slice keeps a single 02 hero lane, inserts a short skeptic-case framing note, and adds a compact matched-effort read where effort robustness would normally sit.",
        "- P4 remains secondary and compact, answering what is actually fresh, what is broadened or intensified, what is reused structure, and what should remain a boundary case.",
        "",
        "## Brief Forward Look",
        "",
        "- A later landing-level line can now honestly say that the product is useful on vivid filings and on a lower-drift skeptic case.",
        "- KO should likely remain visible as the skeptic pilot unless a cleaner or even more legible restraint case later displaces it.",
        "- The current three-case mix is enough before adding future overlays.",
    ]
    return "\n".join(lines) + "\n"


def build_vivid_vs_skeptic_report() -> str:
    lines = [
        "# Wave 4E5.5 Vivid Vs Skeptic Findings",
        "",
        "## What NVDA And LLY Prove",
        "",
        "- NVDA proves the product can stay useful when a filing carries vivid, named, high-signal changes around export controls, AI regulation, and supply execution.",
        "- LLY proves the product can stay useful in a different industry and policy geometry where pricing access, concentration, and policy-channel detail move to the center.",
        "",
        "## What KO Proves",
        "",
        "- KO proves the product can still be useful when the filing is mostly stable and selectively sharpened.",
        "- KO proves that restraint is a product feature, not a weakness: the app can stay helpful without pretending every change is dramatic.",
        "",
        "## Why The Combination Is Stronger",
        "",
        "- Together, the vivid cases and the skeptic case make the product look less like a dramatic-case demo and more like a disciplined comparison-first reading tool.",
        "- Investors and analysts get evidence that the app can help on both vivid and lower-drift disclosures.",
        "- Managers and hiring readers get a clearer product story: the system is not just a novelty detector, it is a bounded tool for reading filing change honestly.",
        "- Data scientists get a better signal about failure modes, because KO shows where restraint and boundary control matter as much as recall.",
        "",
        "## Implication",
        "",
        "- The credible claim is now stronger: useful on vivid high-signal cases and on a lower-drift skeptic case.",
        "- The claim still should not drift into benchmark or broad-market coverage language.",
        "",
        "## Brief Forward Look",
        "",
        "- A landing-level framing line can now center disciplined usefulness across vivid and skeptic cases.",
        "- KO should likely remain the permanent skeptic pilot unless a later case offers the same restraint value more cleanly.",
        "- The current three-case mix is enough before future overlay work.",
    ]
    return "\n".join(lines) + "\n"


def build_product_framing_report() -> str:
    lines = [
        "# Wave 4E5.5 Product Framing Note",
        "",
        "## What The App Can Now Credibly Claim",
        "",
        "- The app is useful on vivid, high-signal filings like NVDA and LLY.",
        "- The app is also useful on a lower-drift skeptic case like KO when the filing is mostly stable and selectively sharpened.",
        "- The compact flow remains comparison-first, disciplined, and bounded: 02 hero lane first, P4 secondary only.",
        "",
        "## What The App Still Should Not Claim",
        "",
        "- It should not claim broad issuer coverage, benchmark completeness, or universal superiority of one protocol family.",
        "- It should not claim whole-filing context, external-research overlays, or equal-lane P4 parity.",
        "",
        "## Ready For A Later Landing Pass",
        "",
        "- Yes. The factual foundation is now strong enough for a later landing-level framing pass.",
        "- That later pass should stay bounded to the current visible three-case pilot slice until broader work actually ships.",
        "",
        "## Brief Forward Look",
        "",
        "- A later landing line could honestly say: compare vivid filings and a lower-drift skeptic case in one compact, filing-first workflow.",
        "- KO should likely stay visible as the skeptic pilot for now.",
        "- The current three-case mix is enough before adding overlays or broader issuer surfaces.",
    ]
    return "\n".join(lines) + "\n"


def build_repo_paths_for_packet(
    ko_artifact_paths: list[Path], cross_case_paths: list[Path], report_paths: list[Path]
) -> list[Path]:
    repo_paths = [path.relative_to(REPO_ROOT) for path in [*ko_artifact_paths, *cross_case_paths]]
    repo_paths.extend(path.relative_to(REPO_ROOT) for path in report_paths)
    repo_paths.extend(
        [
            PILOT_REGISTRY_PATH,
            P4_SUMMARY_PATH,
            P4_VS_P1_SUMMARY_PATH,
            *PILOT_REVIEW_PATHS.values(),
            *SOURCE_UI_PATHS,
            *SOURCE_DATA_PATHS,
            SELF_SCRIPT_PATH,
            SELF_TEST_PATH,
            *NODE_TEST_PATHS,
        ]
    )
    return repo_paths


def generate_wave(stamp: str | None = None) -> GenerationSummary:
    resolved_runs = resolve_runs()

    ko_matrix_dir = PILOT_MATRICES_ROOT / FIXTURE_ID
    ko_cell_path = ko_matrix_dir / "cells" / "02_p1_i2_tagged_packet__pilot_matrix_cell_v1.json"
    ko_story_path = ko_matrix_dir / "pilot_matrix_story_v1.json"
    ko_review_path = ko_matrix_dir / "pilot_matrix_review_v1.json"
    ko_matrix_path = ko_matrix_dir / "pilot_matrix_v1.json"

    ko_skeptic_dir = SKEPTIC_CASES_ROOT / FIXTURE_ID
    ko_skeptic_matrix_path = ko_skeptic_dir / "ko_canonized_matrix_v1.json"
    ko_skeptic_quality_path = ko_skeptic_dir / "ko_quality_notes_v1.json"
    ko_p1_vs_p4_summary_path = ko_skeptic_dir / "ko_p1_vs_p4_summary_v1.json"
    third_pilot_summary_path = SKEPTIC_CASES_ROOT / "third_pilot_summary_v1.json"
    vivid_vs_skeptic_summary_path = SKEPTIC_CASES_ROOT / "vivid_vs_skeptic_summary_v1.json"

    ko_p4_dir = NOVELTY_LEDGER_ROOT / FIXTURE_ID
    ko_p4_case_path = ko_p4_dir / "p4_canonized_matrix_v1.json"
    ko_p4_quality_path = NOVELTY_LEDGER_ROOT / "ko_p4_quality_notes_v1.json"

    current_case_mix_path = REPO_ROOT / CURRENT_CASE_MIX_PATH

    write_json(ko_cell_path, build_ko_pilot_cell(resolved_runs["KO_02_p1_i2_tagged_packet"]))
    write_json(ko_story_path, build_ko_pilot_story())
    write_json(ko_review_path, build_ko_pilot_review())
    write_json(ko_matrix_path, build_ko_pilot_matrix(ko_cell_path, ko_review_path))
    write_json(REPO_ROOT / PILOT_REGISTRY_PATH, build_registry_payload())

    write_json(ko_skeptic_quality_path, build_ko_skeptic_quality_notes(resolved_runs))
    write_json(ko_p1_vs_p4_summary_path, build_ko_p1_vs_p4_summary())
    write_json(
        ko_skeptic_matrix_path,
        build_ko_skeptic_canonized_matrix(ko_skeptic_quality_path, ko_p1_vs_p4_summary_path),
    )
    write_json(third_pilot_summary_path, build_third_pilot_summary())
    write_json(vivid_vs_skeptic_summary_path, build_vivid_vs_skeptic_summary())
    write_json(current_case_mix_path, build_current_case_mix())

    write_json(ko_p4_quality_path, build_ko_p4_quality_notes(resolved_runs))
    write_json(ko_p4_case_path, build_ko_p4_case(resolved_runs, ko_p4_quality_path))

    issuer_artifact_paths = [
        REPO_ROOT
        / "public/data/business_document_protocol_lab/novelty_ledger/NVDA_2024_2025_10k_item1a/p4_canonized_matrix_v1.json",
        REPO_ROOT
        / "public/data/business_document_protocol_lab/novelty_ledger/LLY_2024_2025_10k_item1a/p4_canonized_matrix_v1.json",
        ko_p4_case_path,
    ]
    quality_note_paths = [
        REPO_ROOT
        / "public/data/business_document_protocol_lab/novelty_ledger/nvda_p4_quality_notes_v1.json",
        REPO_ROOT
        / "public/data/business_document_protocol_lab/novelty_ledger/lly_p4_quality_notes_v1.json",
        ko_p4_quality_path,
    ]
    write_json(REPO_ROOT / P4_SUMMARY_PATH, build_cross_p4_summary(issuer_artifact_paths, quality_note_paths))
    write_json(REPO_ROOT / P4_VS_P1_SUMMARY_PATH, build_p4_vs_p1_summary())

    update_review_file(
        REPO_ROOT / PILOT_REVIEW_PATHS["NVDA_2024_2025_10k_item1a"],
        NVDA_REVIEW_UPDATES["supports"],
        NVDA_REVIEW_UPDATES["does_not_yet_support"],
    )
    update_review_file(
        REPO_ROOT / PILOT_REVIEW_PATHS["LLY_2024_2025_10k_item1a"],
        LLY_REVIEW_UPDATES["supports"],
        LLY_REVIEW_UPDATES["does_not_yet_support"],
    )

    report_paths = [
        REPO_ROOT / CANONIZATION_REPORT_PATH,
        REPO_ROOT / INTEGRATION_DECISION_REPORT_PATH,
        REPO_ROOT / VIVID_VS_SKEPTIC_REPORT_PATH,
        REPO_ROOT / PRODUCT_FRAMING_REPORT_PATH,
    ]

    ko_artifact_paths = [
        ko_matrix_path,
        ko_story_path,
        ko_review_path,
        ko_cell_path,
        ko_skeptic_matrix_path,
        ko_skeptic_quality_path,
        ko_p1_vs_p4_summary_path,
        ko_p4_case_path,
        ko_p4_quality_path,
    ]
    cross_case_paths = [
        REPO_ROOT / PILOT_REGISTRY_PATH,
        REPO_ROOT / P4_SUMMARY_PATH,
        REPO_ROOT / P4_VS_P1_SUMMARY_PATH,
        third_pilot_summary_path,
        vivid_vs_skeptic_summary_path,
        current_case_mix_path,
        REPO_ROOT / PILOT_REVIEW_PATHS["NVDA_2024_2025_10k_item1a"],
        REPO_ROOT / PILOT_REVIEW_PATHS["LLY_2024_2025_10k_item1a"],
    ]

    write_text(
        report_paths[0],
        build_canonization_report(
            ko_artifact_paths,
            cross_case_paths,
            SOURCE_UI_PATHS,
            SOURCE_DATA_PATHS,
        ),
    )
    write_text(report_paths[1], build_integration_decision_report())
    write_text(report_paths[2], build_vivid_vs_skeptic_report())
    write_text(report_paths[3], build_product_framing_report())

    stamp_value = stamp or utc_stamp()
    packet_dir, zip_path = packet_paths_for_stamp(stamp_value)
    ensure_clean_output(packet_dir)
    ensure_clean_output(zip_path)
    packet_dir.mkdir(parents=True, exist_ok=True)

    repo_paths = build_repo_paths_for_packet(ko_artifact_paths, cross_case_paths, report_paths)
    copy_repo_paths_into_packet(packet_dir, repo_paths)

    changed_repo_paths = [
        *(path.relative_to(REPO_ROOT) for path in [*ko_artifact_paths, *cross_case_paths, *report_paths]),
        *SOURCE_UI_PATHS,
        *SOURCE_DATA_PATHS,
        SELF_SCRIPT_PATH,
        SELF_TEST_PATH,
        *NODE_TEST_PATHS,
    ]
    write_text(packet_dir / CHANGED_FILES_MANIFEST_NAME, build_changed_files_manifest(changed_repo_paths))
    write_text(
        packet_dir / ROOT_README_NAME,
        build_packet_readme(
            packet_dir,
            ko_artifact_paths,
            cross_case_paths,
            report_paths,
            SOURCE_UI_PATHS,
            SOURCE_DATA_PATHS,
        ),
    )
    write_text(packet_dir / RENDER_PREVIEW_NAME, build_render_preview())
    zip_directory(packet_dir, zip_path)

    console_summary_lines = [
        f"packet folder path: {packet_dir.resolve()}",
        f"zip path: {zip_path.resolve()}",
        "KO canonized artifact paths:",
        *(f"- {path.resolve()}" for path in ko_artifact_paths),
        "cross-case summary artifact paths:",
        *(f"- {path.resolve()}" for path in cross_case_paths),
        "which source files were modified:",
        *(f"- {(REPO_ROOT / path).resolve()}" for path in [*SOURCE_UI_PATHS, *SOURCE_DATA_PATHS]),
        "whether KO is now visibly integrated as the third pilot: yes",
        "whether any app-visible framing was updated: yes",
        f"biggest remaining blocker after this wave: {BIGGEST_REMAINING_BLOCKER}",
    ]
    for line in console_summary_lines:
        print(line)

    return GenerationSummary(
        packet_dir=packet_dir,
        zip_path=zip_path,
        ko_artifact_paths=[repo_rel(path) for path in ko_artifact_paths],
        cross_case_paths=[repo_rel(path) for path in cross_case_paths],
        source_paths=[path.as_posix() for path in [*SOURCE_UI_PATHS, *SOURCE_DATA_PATHS]],
        ko_visible_integration=True,
        app_visible_framing_updated=True,
        biggest_remaining_blocker=BIGGEST_REMAINING_BLOCKER,
        console_summary_lines=console_summary_lines,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--stamp", default=None, help="Optional UTC timestamp override.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    generate_wave(stamp=args.stamp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
