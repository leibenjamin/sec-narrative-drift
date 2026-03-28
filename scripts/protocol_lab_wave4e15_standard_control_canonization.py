from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import protocol_lab_validate_desktop_packet_responses as packet_validator

REPO_ROOT = Path(__file__).resolve().parents[1]
BUSINESS_ROOT = REPO_ROOT / "public" / "data" / "business_document_protocol_lab"
PILOT_MATRICES_ROOT = BUSINESS_ROOT / "pilot_matrices"
STANDARD_CONTROLS_ROOT = BUSINESS_ROOT / "standard_controls"
STANDARD_COMPARISONS_ROOT = STANDARD_CONTROLS_ROOT / "comparisons"
REPORTS_ROOT = REPO_ROOT / "reports" / "protocol_lab"

STANDARD_PACKET_ROOT_NAME = "wave4e1_standard_thinking_controls_20260319_0213"
STANDARD_PACKET_ROOT = REPO_ROOT / STANDARD_PACKET_ROOT_NAME
VALIDATION_REPORT_PATH = REPORTS_ROOT / "wave4e15_standard_control_validation_report.json"
CANONIZATION_REPORT_PATH = REPORTS_ROOT / "wave4e15_standard_control_canonization_report.md"
FINDINGS_REPORT_PATH = REPORTS_ROOT / "wave4e15_standard_control_findings.md"
PACKET_PREFIX = "wave4e15_standard_controls_canonized"
ROOT_README_NAME = "README.md"
CHANGED_FILES_MANIFEST_NAME = "changed_files_manifest.md"

BIGGEST_REMAINING_BLOCKER = (
    "Two canonical LLY structured standard-thinking captures still exist only as malformed raw JSON, "
    "so capture integrity remains the main blocker before the next substantive protocol wave."
)

CANONICAL_RUN_IDS = [
    "NVDA_00_b0_unstructured_frontier_baseline_standard",
    "NVDA_02_p1_i2_tagged_packet_standard",
    "NVDA_03_p2_i2_tagged_protocol_standard",
    "LLY_00_b0_unstructured_frontier_baseline_standard",
    "LLY_02_p1_i2_tagged_packet_standard",
    "LLY_03_p2_i2_tagged_protocol_standard",
]

ISSUER_CONFIGS: dict[str, dict[str, Any]] = {
    "NVDA_2024_2025_10k_item1a": {
        "run_ids": [
            "NVDA_00_b0_unstructured_frontier_baseline_standard",
            "NVDA_02_p1_i2_tagged_packet_standard",
            "NVDA_03_p2_i2_tagged_protocol_standard",
        ],
        "lane_roles": {
            "02_p1_i2_tagged_packet": "hero",
            "03_p2_i2_tagged_protocol": "main_comparator",
            "00_b0_unstructured_frontier_baseline": "control",
        },
        "ordered_lane_ids": [
            "02_p1_i2_tagged_packet",
            "03_p2_i2_tagged_protocol",
            "00_b0_unstructured_frontier_baseline",
        ],
        "lane_assessments": {
            "02_p1_i2_tagged_packet": {
                "role_label": "Hero lane",
                "assessment": "strongest",
                "rationale": "02 remains the clearest standard-thinking first read on NVDA because it keeps the filing shift legible, structured, and machine-parseable on the tagged packet.",
            },
            "03_p2_i2_tagged_protocol": {
                "role_label": "Main comparator",
                "assessment": "meaningful_comparator",
                "rationale": "03 remains a meaningful comparator on NVDA after the rerun because it still changes the lead story on the same tagged substrate and the current canonical raw file parses cleanly.",
            },
            "00_b0_unstructured_frontier_baseline": {
                "role_label": "Control lane",
                "assessment": "control",
                "rationale": "00 stays readable enough to function as a control, but it remains ad hoc and noncanonical rather than a structured protocol lane.",
            },
        },
        "wave_summary": {
            "summary": "On NVDA, the reduced-reasoning control wave preserves the same practical lane ordering as the extended pilot: 02 is still the default first read, 03 still shifts the narrative in a meaningful way, and 00 remains an honest ad hoc control.",
            "strongest_lane": "02_p1_i2_tagged_packet",
            "weaker_lane": "03_p2_i2_tagged_protocol",
            "control_lane": "00_b0_unstructured_frontier_baseline",
            "bounded_claim": "On this fixed NVDA pair, protocol value still appears visible under standard thinking, but the claim remains a bounded pilot finding rather than a benchmark.",
        },
        "caveats": [
            "This issuer artifact is still a one-issuer, one-pair control summary, not a benchmark.",
            "B0 remains ad hoc and noncanonical even when it is readable.",
            "No whole-filing, novelty-ledger, or external-research overlay is added in this wave.",
        ],
        "provenance_notes": [
            "The current packet-local response.json files are the canonical standard-thinking sources for this wave.",
            "NVDA_03_p2_i2_tagged_protocol_standard was rerun and improved before canonization; the currently present response.json is treated as canonical.",
            "No superseded archived NVDA standard 03 raw response was found in-repo, so no prior-vs-current raw diff is created.",
        ],
        "comparison": {
            "lane_comparisons": {
                "02_p1_i2_tagged_packet": {
                    "stable_points": [
                        "02 remains the strongest default lane on the fixed NVDA pair.",
                        "The filing-first story still centers on a structured tagged-packet read rather than the ad hoc control.",
                    ],
                    "degraded_points": [
                        "The standard wave is still a bounded control packet, so the claim stays narrower than a broader benchmark-style comparison.",
                    ],
                    "lane_order_changed": False,
                    "meaningfulness_note": "02 remains the anchor lane rather than the comparator lane.",
                },
                "03_p2_i2_tagged_protocol": {
                    "stable_points": [
                        "03 still changes the lead story relative to 02 while holding the tagged packet fixed.",
                        "The current rerun-backed canonical raw file remains parseable and structurally valid.",
                    ],
                    "degraded_points": [
                        "03 still trails 02 as the default lane, so reduced reasoning does not reverse the ordering.",
                    ],
                    "lane_order_changed": False,
                    "meaningfulness_note": "03 remains a meaningful comparator after the rerun and under reduced reasoning effort.",
                },
                "00_b0_unstructured_frontier_baseline": {
                    "stable_points": [
                        "00 still functions as a readable control on the same tagged substrate.",
                        "00 remains clearly distinct from the structured lanes and does not replace them.",
                    ],
                    "degraded_points": [
                        "00 stays noncanonical and ad hoc, so it still cannot support a structured-lane claim.",
                    ],
                    "lane_order_changed": False,
                    "meaningfulness_note": "00 is useful only as a control, not as a structured comparator.",
                },
            },
            "issuer_conclusion": "On NVDA, the standard-vs-extended comparison keeps the same product story: 02 remains strongest, 03 remains meaningful, and 00 remains control-only.",
            "caveats": [
                "This remains a bounded pilot comparison for one issuer-year pair.",
                "No score-like benchmark precision is claimed.",
            ],
        },
    },
    "LLY_2024_2025_10k_item1a": {
        "run_ids": [
            "LLY_00_b0_unstructured_frontier_baseline_standard",
            "LLY_02_p1_i2_tagged_packet_standard",
            "LLY_03_p2_i2_tagged_protocol_standard",
        ],
        "lane_roles": {
            "02_p1_i2_tagged_packet": "hero",
            "03_p2_i2_tagged_protocol": "main_comparator",
            "00_b0_unstructured_frontier_baseline": "control",
        },
        "ordered_lane_ids": [
            "02_p1_i2_tagged_packet",
            "03_p2_i2_tagged_protocol",
            "00_b0_unstructured_frontier_baseline",
        ],
        "lane_assessments": {
            "02_p1_i2_tagged_packet": {
                "role_label": "Hero lane",
                "assessment": "strongest",
                "rationale": "02 remains the strongest intended LLY standard-thinking lane, but the current canonical raw file is malformed JSON, so the claim stays bounded by capture integrity.",
            },
            "03_p2_i2_tagged_protocol": {
                "role_label": "Main comparator",
                "assessment": "meaningful_comparator",
                "rationale": "03 remains the intended meaningful LLY comparator after the rerun, but its current canonical raw file is also malformed JSON and therefore carries an explicit capture-integrity caveat.",
            },
            "00_b0_unstructured_frontier_baseline": {
                "role_label": "Control lane",
                "assessment": "control",
                "rationale": "00 stays readable enough to function as a control, but it remains ad hoc and noncanonical rather than a structured protocol lane.",
            },
        },
        "wave_summary": {
            "summary": "On LLY, the reduced-reasoning control wave still points to the same intended lane ordering as the extended pilot, but the structured 02 and 03 canonical raw captures are malformed JSON, so the story is informative yet mechanically fragile.",
            "strongest_lane": "02_p1_i2_tagged_packet",
            "weaker_lane": "03_p2_i2_tagged_protocol",
            "control_lane": "00_b0_unstructured_frontier_baseline",
            "bounded_claim": "On this fixed LLY pair, protocol value still appears directionally visible under standard thinking, but the claim remains pilot-grade and explicitly bounded by capture-integrity failure on the structured lanes.",
        },
        "caveats": [
            "This issuer artifact is still a one-issuer, one-pair control summary, not a benchmark.",
            "LLY_02 and LLY_03 are canonical raw sources but fail JSON parseability in their current saved form.",
            "B0 remains ad hoc and noncanonical even when it is readable.",
        ],
        "provenance_notes": [
            "The current packet-local response.json files are the canonical standard-thinking sources for this wave.",
            "LLY_03_p2_i2_tagged_protocol_standard was rerun and improved before canonization; the currently present response.json is treated as canonical.",
            "No superseded archived LLY standard 03 raw response was found in-repo, so no prior-vs-current raw diff is created.",
        ],
        "comparison": {
            "lane_comparisons": {
                "02_p1_i2_tagged_packet": {
                    "stable_points": [
                        "02 remains the intended strongest first-read lane on the fixed LLY pair.",
                        "The filing-first product story still points to the structured tagged packet as the best bounded lane.",
                    ],
                    "degraded_points": [
                        "The canonical standard raw file is malformed JSON, which weakens machine-audit reliability relative to the extended pilot surface.",
                    ],
                    "lane_order_changed": False,
                    "meaningfulness_note": "02 remains the anchor lane rather than the comparator lane.",
                },
                "03_p2_i2_tagged_protocol": {
                    "stable_points": [
                        "03 still matters as the intended same-substrate comparator to 02 after the rerun-backed canonization step.",
                        "The rerun provenance keeps 03 in play as a truthful comparison lane rather than a discarded artifact.",
                    ],
                    "degraded_points": [
                        "The canonical standard raw file is malformed JSON, which limits machine validation and keeps the reduced-reasoning claim pilot-grade.",
                    ],
                    "lane_order_changed": False,
                    "meaningfulness_note": "03 remains a meaningful comparator after the rerun, but with an explicit capture-integrity caveat.",
                },
                "00_b0_unstructured_frontier_baseline": {
                    "stable_points": [
                        "00 still functions as a readable control on the same tagged substrate.",
                        "00 remains clearly distinct from the structured lanes and does not replace them.",
                    ],
                    "degraded_points": [
                        "00 stays noncanonical and ad hoc, so it still cannot support a structured-lane claim.",
                    ],
                    "lane_order_changed": False,
                    "meaningfulness_note": "00 is useful only as a control, not as a structured comparator.",
                },
            },
            "issuer_conclusion": "On LLY, the standard-vs-extended story remains directionally consistent with 02 strongest, 03 meaningful, and 00 control-only, but the structured standard captures are mechanically weaker because the canonical raw JSON is malformed.",
            "caveats": [
                "This remains a bounded pilot comparison for one issuer-year pair.",
                "LLY structured standard outputs are canonical but malformed, so no benchmark-like precision is claimed.",
            ],
        },
    },
}

STANDARD_SUMMARY_SUPPORTS = [
    "Across NVDA and LLY, the current two-issuer slice still supports a bounded claim that 02 is the most robust standard-thinking lane.",
    "Across both issuers, 03 remains meaningful enough to act as a comparator lane rather than a discarded artifact.",
    "Across both issuers, 00 remains useful as a readable control that makes the value of structured protocol lanes more explicit.",
]

STANDARD_SUMMARY_DOES_NOT_SUPPORT = [
    "This wave does not establish benchmark-grade rigor or broad multi-company generalization.",
    "This wave does not support whole-filing, external-research, or novelty-ledger claims.",
    "This wave does not erase the capture-integrity caveat created by malformed LLY structured standard raw JSON.",
]

STANDARD_SUMMARY_PATTERNS = [
    "02 stays ranked above 03 and 00 for both issuers, preserving the current product interpretation under reduced reasoning effort.",
    "03 still matters because the same-substrate comparator story survives the rerun-backed canonization step on both issuers.",
    "00 remains useful only as an ad hoc control and not as a structured lane, which keeps the proof boundary honest.",
]

STANDARD_VS_EXTENDED_STABILITY_PATTERNS = [
    "No issuer shows a lane-order reversal: 02 still leads, 03 still follows as the comparator, and 00 stays the control.",
    "The practical protocol story survives on the bounded two-issuer slice: structured tagged-packet lanes remain more valuable than the ad hoc control.",
]

STANDARD_VS_EXTENDED_DEGRADATION_PATTERNS = [
    "The reduced-reasoning wave is still pilot-grade rather than benchmark-grade.",
    "LLY_02 and LLY_03 add a capture-integrity caveat because the canonical structured raw files are malformed JSON.",
]

SCRIPT_AND_TEST_PATHS = [
    Path("scripts/protocol_lab_validate_desktop_packet_responses.py"),
    Path("scripts/protocol_lab_wave4e15_standard_control_canonization.py"),
    Path("scripts/tests/test_protocol_lab_validate_desktop_packet_responses.py"),
    Path("scripts/tests/test_protocol_lab_wave4e15_standard_control_canonization.py"),
]

SOURCE_SUPPORT_PATHS = [
    Path("eslint.config.js"),
    Path("src/lib/protocolLabMatrixTypes.ts"),
    Path("src/lib/protocolLabMatrixSchemas.ts"),
]


@dataclass(frozen=True)
class GenerationSummary:
    packet_dir: Path
    zip_path: Path
    standard_artifact_paths: list[str]
    comparison_artifact_paths: list[str]
    script_and_test_paths: list[str]
    validation_passed: bool
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
    resolved = path if path.is_absolute() else (REPO_ROOT / path)
    return resolved.relative_to(REPO_ROOT).as_posix()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected JSON object at {path}.")
    return cast(dict[str, Any], payload)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ensure_clean_output(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def lane_slug_for_run(run_id: str) -> str:
    return packet_validator.derive_lane_slug(run_id)


def standard_matrix_artifact_path(fixture_id: str) -> Path:
    return STANDARD_CONTROLS_ROOT / fixture_id / "standard_control_matrix_v1.json"


def comparison_artifact_path(ticker: str) -> Path:
    return STANDARD_COMPARISONS_ROOT / f"{ticker.lower()}_standard_vs_extended_v1.json"


def load_pair_info(fixture_id: str) -> dict[str, Any]:
    matrix_path = PILOT_MATRICES_ROOT / fixture_id / "pilot_matrix_v1.json"
    matrix_payload = read_json(matrix_path)
    pair_info = matrix_payload.get("pair_info")
    if not isinstance(pair_info, dict):
        raise TypeError(f"pilot_matrix_v1.json missing pair_info for {fixture_id}.")
    return cast(dict[str, Any], pair_info)


def build_validation_result_map(
    report: packet_validator.ValidationReport,
) -> dict[str, packet_validator.RunValidationResult]:
    return {result.run_id: result for result in report.run_results}


def build_validation_snapshot(result: packet_validator.RunValidationResult) -> dict[str, Any]:
    return {
        "response_exists": result.response_exists,
        "response_non_empty": result.response_non_empty,
        "json_parseable": result.json_parseable,
        "json_object": result.json_object,
        "top_level_shape_valid": result.top_level_shape_valid,
        "actual_top_level_keys": result.actual_top_level_keys,
        "raw_text_expected_key_hints": result.raw_text_expected_key_hints,
        "blocker_codes": result.blocker_codes,
        "notes": result.notes,
    }


def build_standard_control_matrix_payload(
    fixture_id: str,
    config: dict[str, Any],
    validation_map: dict[str, packet_validator.RunValidationResult],
) -> dict[str, Any]:
    pair_info = load_pair_info(fixture_id)
    issuer = {
        "ticker": pair_info["ticker"],
        "issuer_name": pair_info["issuer_name"],
    }
    run_ids = cast(list[str], config["run_ids"])
    lane_assessments: list[dict[str, Any]] = []
    canonical_sources: list[dict[str, Any]] = []

    for run_id in run_ids:
        lane_slug = lane_slug_for_run(run_id)
        assessment = cast(dict[str, Any], config["lane_assessments"][lane_slug])
        validation = validation_map[run_id]
        lane_assessments.append(
            {
                "lane_slug": lane_slug,
                "run_id": run_id,
                "role_label": assessment["role_label"],
                "assessment": assessment["assessment"],
                "rationale": assessment["rationale"],
            }
        )
        canonical_sources.append(
            {
                "run_id": run_id,
                "lane_slug": lane_slug,
                "response_path": repo_rel(STANDARD_PACKET_ROOT / run_id / "response.json"),
                "run_manifest_path": repo_rel(STANDARD_PACKET_ROOT / run_id / "run_manifest.json"),
                "expected_top_level_keys": list(validation.expected_top_level_keys),
                "validation_snapshot": build_validation_snapshot(validation),
            }
        )

    return {
        "artifact_schema_id": "standard_control_matrix_v1",
        "matrix_id": f"{fixture_id}__standard_control_matrix_v1",
        "fixture_id": fixture_id,
        "issuer": issuer,
        "pair_info": pair_info,
        "packet_root": STANDARD_PACKET_ROOT_NAME,
        "reasoning_mode": "standard_thinking",
        "canonical_run_ids": run_ids,
        "lane_roles": config["lane_roles"],
        "ordered_lane_ids": config["ordered_lane_ids"],
        "lane_assessments": lane_assessments,
        "canonical_sources": canonical_sources,
        "wave_summary": config["wave_summary"],
        "caveats": config["caveats"],
        "provenance_notes": config["provenance_notes"],
    }


def build_standard_vs_extended_payload(
    fixture_id: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    pair_info = load_pair_info(fixture_id)
    comparison_config = cast(dict[str, Any], config["comparison"])
    lane_comparisons_payload: list[dict[str, Any]] = []
    for lane_slug in cast(list[str], config["ordered_lane_ids"]):
        lane_comparison = cast(dict[str, Any], comparison_config["lane_comparisons"][lane_slug])
        lane_comparisons_payload.append(
            {
                "lane_slug": lane_slug,
                "stable_points": lane_comparison["stable_points"],
                "degraded_points": lane_comparison["degraded_points"],
                "lane_order_changed": lane_comparison["lane_order_changed"],
                "meaningfulness_note": lane_comparison["meaningfulness_note"],
            }
        )

    ticker = cast(str, pair_info["ticker"])
    return {
        "artifact_schema_id": "standard_vs_extended_comparison_v1",
        "comparison_id": f"{fixture_id}__standard_vs_extended_v1",
        "fixture_id": fixture_id,
        "issuer": {
            "ticker": ticker,
            "issuer_name": pair_info["issuer_name"],
        },
        "standard_matrix_id": f"{fixture_id}__standard_control_matrix_v1",
        "standard_matrix_path": repo_rel(standard_matrix_artifact_path(fixture_id)),
        "extended_matrix_id": f"{fixture_id}__desktop_pilot_matrix_v1",
        "extended_matrix_path": repo_rel(
            PILOT_MATRICES_ROOT / fixture_id / "pilot_matrix_v1.json"
        ),
        "lane_comparisons": lane_comparisons_payload,
        "issuer_conclusion": comparison_config["issuer_conclusion"],
        "caveats": comparison_config["caveats"],
    }


def build_standard_control_summary_payload(
    validation_report: packet_validator.ValidationReport,
) -> dict[str, Any]:
    passed_run_ids = [
        result.run_id for result in validation_report.run_results if not result.blocker_codes
    ]
    failed_run_ids = [
        result.run_id for result in validation_report.run_results if result.blocker_codes
    ]

    by_issuer_ranking: list[dict[str, Any]] = []
    for fixture_id, config in ISSUER_CONFIGS.items():
        pair_info = load_pair_info(fixture_id)
        ordered_lane_ids = cast(list[str], config["ordered_lane_ids"])
        lane_to_run_id = {
            lane_slug_for_run(run_id): run_id for run_id in cast(list[str], config["run_ids"])
        }
        by_issuer_ranking.append(
            {
                "fixture_id": fixture_id,
                "issuer": {
                    "ticker": pair_info["ticker"],
                    "issuer_name": pair_info["issuer_name"],
                },
                "ordered_lane_ids": ordered_lane_ids,
                "ordered_run_ids": [lane_to_run_id[lane_slug] for lane_slug in ordered_lane_ids],
                "ranking_note": "02 remains strongest, 03 remains the meaningful comparator, and 00 remains the control.",
            }
        )

    failure_note = (
        "LLY_02_p1_i2_tagged_packet_standard and LLY_03_p2_i2_tagged_protocol_standard fail JSON parseability in their current canonical raw form; the other four runs pass the bounded validator."
        if failed_run_ids
        else "All six standard-thinking runs pass the bounded validator."
    )

    provenance_notes = [
        "The current packet-local response.json files are the canonical standard-thinking sources for all six runs.",
        "NVDA_03_p2_i2_tagged_protocol_standard and LLY_03_p2_i2_tagged_protocol_standard were rerun and improved before canonization; the current response.json files are treated as canonical.",
        "No superseded archived standard 03 raw outputs were found in-repo, so no prior-vs-current raw diff is created.",
    ]

    return {
        "artifact_schema_id": "standard_control_summary_v1",
        "summary_id": "standard_control_summary_v1",
        "packet_root": STANDARD_PACKET_ROOT_NAME,
        "reasoning_mode": "standard_thinking",
        "canonical_run_ids": CANONICAL_RUN_IDS,
        "by_issuer_ranking": by_issuer_ranking,
        "cross_issuer_pattern_summary": STANDARD_SUMMARY_PATTERNS,
        "supports": STANDARD_SUMMARY_SUPPORTS,
        "does_not_yet_support": STANDARD_SUMMARY_DOES_NOT_SUPPORT,
        "robustness_conclusion": {
            "02": "02 remains the most robust lane across both issuers and is still the strongest bounded product lane under standard thinking.",
            "03": "03 remains meaningful across both issuers, but the reduced-reasoning claim stays bounded by the rerun provenance and the malformed LLY structured raw captures.",
            "00": "00 remains useful only as a readable ad hoc control and not as a structured lane.",
        },
        "validation_overview": {
            "overall_result": validation_report.overall_result,
            "passed_run_ids": passed_run_ids,
            "failed_run_ids": failed_run_ids,
            "failure_note": failure_note,
            "validation_report_path": repo_rel(VALIDATION_REPORT_PATH),
            "raw_hint_note": "When JSON parsing fails, raw-text key hints are recorded for review but never used to repair or coerce the canonical raw file.",
        },
        "provenance_notes": provenance_notes,
    }


def build_standard_vs_extended_summary_payload() -> dict[str, Any]:
    issuer_comparison_paths = [
        repo_rel(comparison_artifact_path("NVDA")),
        repo_rel(comparison_artifact_path("LLY")),
    ]
    return {
        "artifact_schema_id": "standard_vs_extended_summary_v1",
        "summary_id": "standard_vs_extended_summary_v1",
        "packet_root": STANDARD_PACKET_ROOT_NAME,
        "reasoning_mode": "standard_thinking",
        "issuer_comparison_paths": issuer_comparison_paths,
        "cross_issuer_stability_patterns": STANDARD_VS_EXTENDED_STABILITY_PATTERNS,
        "cross_issuer_degradation_patterns": STANDARD_VS_EXTENDED_DEGRADATION_PATTERNS,
        "lane_order_change_summary": "No issuer shows a lane-order reversal. 02 stays ahead of 03, and 00 stays the control for both NVDA and LLY.",
        "protocol_value_under_reduced_reasoning": "The current two-issuer slice still supports a bounded claim that protocol structure adds value under reduced reasoning effort, but the claim remains pilot-grade and explicitly limited by the malformed LLY structured standard raw files.",
        "does_not_yet_support": [
            "No benchmark-grade claim about universal lane superiority.",
            "No third issuer or broader multi-company expansion claim.",
            "No whole-filing, external-research, or novelty-ledger claim.",
        ],
    }


def build_canonization_report(
    validation_report: packet_validator.ValidationReport,
    standard_artifact_paths: list[Path],
    comparison_paths: list[Path],
) -> str:
    failed_run_ids = [
        result.run_id for result in validation_report.run_results if result.blocker_codes
    ]
    lines = [
        "# Wave 4E1.5 Standard Control Canonization Report",
        "",
        f"- generated_at: `{utc_now_iso()}`",
        f"- packet_root: `{STANDARD_PACKET_ROOT_NAME}`",
        "",
        "## What Was Canonized",
        "",
        "- Canonized the six standard-thinking ChatGPT Desktop runs in `wave4e1_standard_thinking_controls_20260319_0213` as the current standard-thinking control wave for NVDA and LLY.",
        "- Kept the current packet-local `response.json` files as the only canonical standard-thinking sources for this wave.",
        "- Did not resurrect, repair, or fabricate superseded standard `03` raw outputs.",
        "",
        "## Canonical Packet Sources",
        "",
        "Canonical response files treated as source of truth:",
    ]
    for run_id in CANONICAL_RUN_IDS:
        lines.append(f"- `{repo_rel(STANDARD_PACKET_ROOT / run_id / 'response.json')}`")
    lines.extend(
        [
            "",
            "## Rerun Provenance",
            "",
            "- `NVDA_03_p2_i2_tagged_protocol_standard` and `LLY_03_p2_i2_tagged_protocol_standard` were rerun and improved before canonization.",
            "- The currently present `response.json` files for those runs are treated as canonical.",
            "- No superseded archived standard `03` raw outputs were found in-repo, so no prior-vs-current raw diff artifact was created.",
            "",
            "## New Public Artifacts",
            "",
        ]
    )
    for artifact_path in standard_artifact_paths:
        lines.append(f"- `{repo_rel(artifact_path)}`")
    for artifact_path in comparison_paths:
        lines.append(f"- `{repo_rel(artifact_path)}`")
    lines.extend(
        [
            "",
            "## Light Reliability Hardening",
            "",
            "- Added `scripts/protocol_lab_validate_desktop_packet_responses.py` as a small reusable validator for packet-local `response.json` capture review.",
            "- The validator checks existence, non-empty files, JSON parseability, lane-family top-level keys, and raw-text expected-key hints when parsing fails.",
            f"- Wrote the reviewable validation report to `{repo_rel(VALIDATION_REPORT_PATH)}`.",
            "",
            "## Product Claim Now Supported",
            "",
            "- The current two-issuer control wave still supports a bounded product claim that protocol value remains visible under reduced reasoning effort.",
            "- `02` remains the strongest and most robust lane, `03` remains a meaningful comparator after the reruns, and `00` remains a readable ad hoc control.",
            "- The claim remains explicitly pilot-grade rather than benchmark-grade.",
            "",
            "## Validation Outcome",
            "",
            f"- overall_result: `{validation_report.overall_result}`",
            f"- failed_runs: `{failed_run_ids}`",
            "- The malformed structured captures are preserved as canonical raw sources and surfaced as an explicit capture-integrity caveat rather than silently normalized.",
            "",
            "## Biggest Remaining Blocker",
            "",
            f"- {BIGGEST_REMAINING_BLOCKER}",
        ]
    )
    return "\n".join(lines) + "\n"


def build_findings_report(validation_report: packet_validator.ValidationReport) -> str:
    failed_run_ids = [
        result.run_id for result in validation_report.run_results if result.blocker_codes
    ]
    lines = [
        "# Wave 4E1.5 Standard Control Findings",
        "",
        "- strongest lane across the six standard-thinking runs: `02_p1_i2_tagged_packet`",
        "- `03` remains a valid comparator after reruns: yes, but bounded by the malformed LLY structured raw captures.",
        "- `00` as a control: readable enough to stay useful, but still ad hoc and noncanonical.",
        "- what changed from the initial first-pass interpretation: the main interpretation holds, but the standard wave now carries an explicit capture-integrity caveat because `LLY_02` and `LLY_03` are canonical-but-malformed raw JSON.",
        "- validator failures in this repo state: "
        + (", ".join(f"`{run_id}`" for run_id in failed_run_ids) if failed_run_ids else "`none`"),
        "- recommended next protocol-lab wave: tighten first-save capture integrity for structured standard runs before any broader protocol expansion.",
    ]
    return "\n".join(lines) + "\n"


def build_changed_files_manifest(paths: list[Path]) -> str:
    lines = [
        "# Changed Files Manifest",
        "",
        "Files created or modified by Wave 4E1.5:",
        "",
    ]
    for path in paths:
        lines.append(f"- `{path.as_posix()}`")
    return "\n".join(lines) + "\n"


def build_packet_readme(
    packet_dir: Path,
    standard_artifact_paths: list[Path],
    comparison_paths: list[Path],
    validation_report: packet_validator.ValidationReport,
) -> str:
    lines = [
        f"# {packet_dir.name}",
        "",
        "This packet contains the additive standard-control canonization artifacts for Wave 4E1.5.",
        "",
        "## Included",
        "",
        "- public standard-control artifacts",
        "- standard-vs-extended comparison artifacts",
        "- canonization and findings reports",
        "- validation report for the six canonical standard-thinking runs",
        "- new validator and wave scripts plus targeted tests",
        "- touched protocolLabMatrix type/schema support files",
        "",
        "## Standard-Control Artifacts",
        "",
    ]
    for path in standard_artifact_paths:
        lines.append(f"- `{repo_rel(path)}`")
    lines.extend(["", "## Comparison Artifacts", ""])
    for path in comparison_paths:
        lines.append(f"- `{repo_rel(path)}`")
    lines.extend(
        [
            "",
            "## Validation Status",
            "",
            f"- overall_result: `{validation_report.overall_result}`",
            "- The canonical LLY structured standard raw files remain malformed JSON and are preserved without repair.",
            "",
            "## Biggest Remaining Blocker",
            "",
            f"- {BIGGEST_REMAINING_BLOCKER}",
        ]
    )
    return "\n".join(lines) + "\n"


def build_repo_paths_for_packet(
    standard_artifact_paths: list[Path],
    comparison_paths: list[Path],
) -> list[Path]:
    paths = [
        *standard_artifact_paths,
        *comparison_paths,
        VALIDATION_REPORT_PATH,
        CANONIZATION_REPORT_PATH,
        FINDINGS_REPORT_PATH,
        *SCRIPT_AND_TEST_PATHS,
        *SOURCE_SUPPORT_PATHS,
    ]
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = path.as_posix()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def copy_repo_paths_into_packet(packet_dir: Path, repo_paths: list[Path]) -> None:
    for path in repo_paths:
        source = REPO_ROOT / path if not path.is_absolute() else path
        copy_file(source, packet_dir / repo_rel(path))


def zip_directory(source_dir: Path, zip_path: Path) -> None:
    ensure_clean_output(zip_path)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for path in sorted(source_dir.rglob("*")):
            if path.is_dir():
                continue
            handle.write(path, arcname=path.relative_to(REPO_ROOT).as_posix())


def generate_wave(stamp: str | None = None) -> GenerationSummary:
    validation_report = packet_validator.validate_packet(STANDARD_PACKET_ROOT, CANONICAL_RUN_IDS)
    packet_validator.write_validation_report(validation_report, VALIDATION_REPORT_PATH)
    validation_map = build_validation_result_map(validation_report)

    standard_artifact_paths = [
        standard_matrix_artifact_path("NVDA_2024_2025_10k_item1a"),
        standard_matrix_artifact_path("LLY_2024_2025_10k_item1a"),
        STANDARD_CONTROLS_ROOT / "standard_control_summary_v1.json",
    ]
    comparison_paths = [
        comparison_artifact_path("NVDA"),
        comparison_artifact_path("LLY"),
        STANDARD_COMPARISONS_ROOT / "standard_vs_extended_summary_v1.json",
    ]

    write_json(
        standard_artifact_paths[0],
        build_standard_control_matrix_payload(
            "NVDA_2024_2025_10k_item1a",
            ISSUER_CONFIGS["NVDA_2024_2025_10k_item1a"],
            validation_map,
        ),
    )
    write_json(
        standard_artifact_paths[1],
        build_standard_control_matrix_payload(
            "LLY_2024_2025_10k_item1a",
            ISSUER_CONFIGS["LLY_2024_2025_10k_item1a"],
            validation_map,
        ),
    )
    write_json(standard_artifact_paths[2], build_standard_control_summary_payload(validation_report))
    write_json(
        comparison_paths[0],
        build_standard_vs_extended_payload(
            "NVDA_2024_2025_10k_item1a",
            ISSUER_CONFIGS["NVDA_2024_2025_10k_item1a"],
        ),
    )
    write_json(
        comparison_paths[1],
        build_standard_vs_extended_payload(
            "LLY_2024_2025_10k_item1a",
            ISSUER_CONFIGS["LLY_2024_2025_10k_item1a"],
        ),
    )
    write_json(comparison_paths[2], build_standard_vs_extended_summary_payload())

    write_text(
        CANONIZATION_REPORT_PATH,
        build_canonization_report(validation_report, standard_artifact_paths, comparison_paths),
    )
    write_text(FINDINGS_REPORT_PATH, build_findings_report(validation_report))

    effective_stamp = stamp or utc_stamp()
    packet_dir, zip_path = packet_paths_for_stamp(effective_stamp)
    ensure_clean_output(packet_dir)
    ensure_clean_output(zip_path)
    packet_dir.mkdir(parents=True, exist_ok=True)

    repo_paths = build_repo_paths_for_packet(standard_artifact_paths, comparison_paths)
    copy_repo_paths_into_packet(packet_dir, repo_paths)

    changed_paths = [Path(repo_rel(path)) for path in repo_paths]
    write_text(packet_dir / CHANGED_FILES_MANIFEST_NAME, build_changed_files_manifest(changed_paths))
    write_text(
        packet_dir / ROOT_README_NAME,
        build_packet_readme(packet_dir, standard_artifact_paths, comparison_paths, validation_report),
    )
    zip_directory(packet_dir, zip_path)

    validation_passed = validation_report.overall_result == "pass"
    console_summary_lines = [
        f"packet folder path: {packet_dir.resolve()}",
        f"zip path: {zip_path.resolve()}",
        "canonical standard-thinking artifact paths:",
        *(f"- {path.resolve()}" for path in standard_artifact_paths),
        "comparison artifact paths:",
        *(f"- {path.resolve()}" for path in comparison_paths),
        "scripts/helpers/tests added or modified:",
        *(f"- {(REPO_ROOT / path).resolve()}" for path in SCRIPT_AND_TEST_PATHS),
        f"whether the six standard-thinking runs validated successfully: {'yes' if validation_passed else 'no'}",
        f"biggest remaining blocker before the next substantive protocol wave: {BIGGEST_REMAINING_BLOCKER}",
    ]

    for line in console_summary_lines:
        print(line)

    return GenerationSummary(
        packet_dir=packet_dir,
        zip_path=zip_path,
        standard_artifact_paths=[repo_rel(path) for path in standard_artifact_paths],
        comparison_artifact_paths=[repo_rel(path) for path in comparison_paths],
        script_and_test_paths=[path.as_posix() for path in SCRIPT_AND_TEST_PATHS],
        validation_passed=validation_passed,
        biggest_remaining_blocker=BIGGEST_REMAINING_BLOCKER,
        console_summary_lines=console_summary_lines,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Wave 4E1.5 standard-control canonization and reliability hardening."
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
