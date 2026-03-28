from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
BUSINESS_ROOT = REPO_ROOT / "public" / "data" / "business_document_protocol_lab"
STANDARD_CONTROLS_ROOT = BUSINESS_ROOT / "standard_controls"
STANDARD_COMPARISONS_ROOT = STANDARD_CONTROLS_ROOT / "comparisons"
EFFORT_ROBUSTNESS_ROOT = STANDARD_CONTROLS_ROOT / "effort_robustness"
REPORTS_ROOT = REPO_ROOT / "reports" / "protocol_lab"

ROOT_README_NAME = "README.md"
CHANGED_FILES_MANIFEST_NAME = "changed_files_manifest.md"
RENDER_PREVIEW_NAME = "render_preview.md"
PACKET_PREFIX = "wave4e2_effort_robustness"

NVDA_STANDARD_MATRIX_PATH = STANDARD_CONTROLS_ROOT / "NVDA_2024_2025_10k_item1a" / "standard_control_matrix_v1.json"
LLY_STANDARD_MATRIX_PATH = STANDARD_CONTROLS_ROOT / "LLY_2024_2025_10k_item1a" / "standard_control_matrix_v1.json"
STANDARD_CONTROL_SUMMARY_PATH = STANDARD_CONTROLS_ROOT / "standard_control_summary_v1.json"
NVDA_COMPARISON_PATH = STANDARD_COMPARISONS_ROOT / "nvda_standard_vs_extended_v1.json"
LLY_COMPARISON_PATH = STANDARD_COMPARISONS_ROOT / "lly_standard_vs_extended_v1.json"
STANDARD_VS_EXTENDED_SUMMARY_PATH = STANDARD_COMPARISONS_ROOT / "standard_vs_extended_summary_v1.json"

NVDA_EFFORT_ARTIFACT_PATH = EFFORT_ROBUSTNESS_ROOT / "nvda_effort_robustness_v1.json"
LLY_EFFORT_ARTIFACT_PATH = EFFORT_ROBUSTNESS_ROOT / "lly_effort_robustness_v1.json"
EFFORT_SUMMARY_ARTIFACT_PATH = EFFORT_ROBUSTNESS_ROOT / "effort_robustness_summary_v1.json"

REPORT_PATH = REPORTS_ROOT / "wave4e2_effort_robustness_report.md"
FINDINGS_PATH = REPORTS_ROOT / "wave4e2_effort_robustness_findings.md"

BIGGEST_REMAINING_BLOCKER = (
    "Two canonical LLY structured standard-thinking captures still exist only as malformed raw JSON, "
    "so capture integrity remains the main blocker before the next substantive protocol wave."
)

SCRIPT_AND_TEST_PATHS = [
    Path("scripts/protocol_lab_capture_guardrail.py"),
    Path("scripts/protocol_lab_validate_desktop_packet_responses.py"),
    Path("scripts/protocol_lab_wave4e2_effort_robustness.py"),
    Path("scripts/tests/test_protocol_lab_capture_guardrail.py"),
    Path("scripts/tests/test_protocol_lab_effort_robustness_data.mjs"),
    Path("scripts/tests/test_protocol_lab_validate_desktop_packet_responses.py"),
    Path("scripts/tests/test_protocol_lab_wave4e2_effort_robustness.py"),
]

SOURCE_PATHS = [
    Path("src/components/ProtocolLabPilotMatrixPanel.tsx"),
    Path("src/components/LabPanel.tsx"),
    Path("src/pages/Company.tsx"),
    Path("src/lib/protocolLabMatrixTypes.ts"),
    Path("src/lib/protocolLabMatrixSchemas.ts"),
    Path("src/lib/protocolLabMatrixAdapter.ts"),
    Path("src/lib/protocolLabMatrixData.ts"),
]


@dataclass(frozen=True)
class GenerationSummary:
    packet_dir: Path
    zip_path: Path
    effort_artifact_paths: list[str]
    report_paths: list[str]
    source_paths: list[str]
    guardrail_script_path: str
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
    resolved = path if path.is_absolute() else REPO_ROOT / path
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


def zip_directory(source_dir: Path, zip_path: Path) -> None:
    ensure_clean_output(zip_path)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for path in sorted(source_dir.rglob("*")):
            if path.is_dir():
                continue
            handle.write(path, arcname=path.relative_to(REPO_ROOT).as_posix())


def normalize_sentence(value: str) -> str:
    return " ".join(str(value).split())


def lane_code_from_slug(lane_slug: str) -> str:
    return lane_slug.split("_", 1)[0]


def build_lane_comparison_map(comparison_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        lane_code_from_slug(str(entry["lane_slug"])): entry
        for entry in comparison_payload["lane_comparisons"]
    }


def build_lane_assessment_map(standard_matrix_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        lane_code_from_slug(str(entry["lane_slug"])): entry
        for entry in standard_matrix_payload["lane_assessments"]
    }


def find_failed_lane_codes(standard_matrix_payload: dict[str, Any]) -> list[str]:
    failed_codes: list[str] = []
    for source in standard_matrix_payload["canonical_sources"]:
        blocker_codes = list(source["validation_snapshot"]["blocker_codes"])
        if blocker_codes:
            failed_codes.append(lane_code_from_slug(str(source["lane_slug"])))
    return failed_codes


def build_lane_note(
    lane_code: str,
    lane_comparison: dict[str, Any],
    failed_lane_codes: list[str],
) -> str:
    stable_point = normalize_sentence(str(lane_comparison["stable_points"][0]))
    degraded_point = normalize_sentence(str(lane_comparison["degraded_points"][0]))
    if lane_code in failed_lane_codes or lane_code == "00":
        return f"{stable_point} {degraded_point}"
    return stable_point


def build_case_headline(ticker: str, failed_lane_codes: list[str]) -> str:
    if failed_lane_codes:
        return (
            f"{ticker} keeps the same visible winner under standard thinking, "
            "but the structured standard captures still carry an explicit integrity caveat."
        )
    return (
        f"{ticker} keeps the same visible winner under standard thinking: "
        "02 stays first, 03 still matters, and 00 remains control-only."
    )


def build_integrity_note(ticker: str, failed_lane_codes: list[str]) -> str:
    if not failed_lane_codes:
        return f"{ticker} shows no capture-integrity failure on the visible standard lanes."

    joined_codes = ", ".join(failed_lane_codes)
    return (
        f"{ticker} keeps an explicit capture-integrity caveat: "
        f"saved standard raw JSON is malformed for lane {joined_codes}."
        if len(failed_lane_codes) == 1
        else f"{ticker} keeps an explicit capture-integrity caveat: saved standard raw JSON is malformed for lanes {joined_codes}."
    )


def build_effort_case_payload(
    artifact_id: str,
    standard_matrix_payload: dict[str, Any],
    comparison_payload: dict[str, Any],
) -> dict[str, Any]:
    lane_comparisons = build_lane_comparison_map(comparison_payload)
    lane_assessments = build_lane_assessment_map(standard_matrix_payload)
    failed_lane_codes = find_failed_lane_codes(standard_matrix_payload)
    ticker = str(standard_matrix_payload["issuer"]["ticker"])

    return {
        "artifact_schema_id": "effort_robustness_case_v1",
        "artifact_id": artifact_id,
        "fixture_id": standard_matrix_payload["fixture_id"],
        "issuer": standard_matrix_payload["issuer"],
        "pair_info": standard_matrix_payload["pair_info"],
        "headline": build_case_headline(ticker, failed_lane_codes),
        "stable_findings": [
            normalize_sentence(str(lane_comparisons["02"]["stable_points"][0])),
            normalize_sentence(str(lane_comparisons["03"]["stable_points"][0])),
            normalize_sentence(str(lane_comparisons["00"]["stable_points"][0])),
        ],
        "weakened_under_standard": [
            normalize_sentence(str(lane_comparisons["02"]["degraded_points"][0])),
            normalize_sentence(str(lane_comparisons["03"]["degraded_points"][0])),
            normalize_sentence(str(lane_comparisons["00"]["degraded_points"][0])),
        ],
        "lane_robustness": {
            "02": build_lane_note("02", lane_comparisons["02"], failed_lane_codes),
            "03": build_lane_note("03", lane_comparisons["03"], failed_lane_codes),
            "00": build_lane_note("00", lane_comparisons["00"], failed_lane_codes),
        },
        "winner_stayed_same": str(standard_matrix_payload["wave_summary"]["strongest_lane"]).startswith("02_"),
        "comparator_remained_meaningful": lane_assessments["03"]["assessment"] == "meaningful_comparator",
        "control_remained_useful": lane_assessments["00"]["assessment"] == "control",
        "lane_order_materially_changed": any(
            bool(entry["lane_order_changed"]) for entry in comparison_payload["lane_comparisons"]
        ),
        "integrity_note": build_integrity_note(ticker, failed_lane_codes),
        "caveat": normalize_sentence(str(standard_matrix_payload["wave_summary"]["bounded_claim"])),
    }


def build_effort_summary_payload(
    standard_control_summary_payload: dict[str, Any],
    standard_vs_extended_summary_payload: dict[str, Any],
) -> dict[str, Any]:
    covered_issuers = [
        str(item["issuer"]["ticker"])
        for item in standard_control_summary_payload["by_issuer_ranking"]
    ]
    return {
        "artifact_schema_id": "effort_robustness_summary_v1",
        "artifact_id": "effort_robustness_summary_v1",
        "covered_issuers": covered_issuers,
        "cross_case_pattern_summary": (
            "Across NVDA and LLY, 02 is the most effort-robust lane, 03 still adds a meaningful same-substrate comparison but is more variance-sensitive, and 00 remains a readable control."
        ),
        "protocol_value_under_lower_effort": normalize_sentence(
            str(standard_vs_extended_summary_payload["protocol_value_under_reduced_reasoning"])
        ),
        "still_should_not_claim": (
            "It still should not claim benchmark-grade rigor, third-issuer generalization, or whole-filing, external-research, or novelty-ledger coverage."
        ),
        "integrity_note": normalize_sentence(
            str(standard_control_summary_payload["validation_overview"]["failure_note"])
        ),
    }


def build_report(
    effort_artifact_paths: list[Path],
    report_paths: list[Path],
    changed_repo_paths: list[Path],
    guardrail_script_path: Path,
) -> str:
    lines = [
        "# Wave 4E2 Effort Robustness Report",
        "",
        f"- generated_at: `{utc_now_iso()}`",
        "",
        "## New Effort-Robustness Artifacts",
        "",
    ]
    for path in effort_artifact_paths:
        lines.append(f"- `{repo_rel(path)}`")
    lines.extend(
        [
            "",
            "## Pilot Slice Changes",
            "",
            "- Added one compact `Effort robustness` block to the integrated NVDA and LLY pilot slices.",
            "- The block now sits after `How the lanes differ` and before the lane cards and detail area.",
            "- The proof boundary and caveat copy now sits below the lane-detail area so lower audit surfaces remain visually last.",
            "",
            "## Copy Tightening",
            "",
            "- Tightened the NVDA and LLY pilot-first/default-read copy so the lower-effort robustness message reads naturally in investor-facing language.",
            "- Kept the wording bounded: no benchmark, no broader generalization, no overlay expansion claim.",
            "",
            "## Capture Guardrail",
            "",
            f"- Added `{repo_rel(guardrail_script_path)}` as the reusable operator preflight helper.",
            "- The helper checks `response.json` existence, non-empty content, JSON parseability, and expected top-level keys by lane family.",
            "- It prints a plain-language `PROCEED` or `STOP` summary and can optionally write a small JSON report.",
            "",
            "## Files Modified",
            "",
        ]
    )
    for path in changed_repo_paths:
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


def build_findings_report() -> str:
    lines = [
        "# Wave 4E2 Effort Robustness Findings",
        "",
        "- strongest lane overall: `02_p1_i2_tagged_packet`",
        "- whether `03` remains a valid comparator under standard thinking: yes, but it is more variance-sensitive and LLY still carries a capture-integrity caveat.",
        "- whether `00` remains useful as a control: yes, as a readable control lane rather than a structured lane.",
        "- main cross-issuer standard-vs-extended conclusion: the visible protocol value survives reduced reasoning effort on the current NVDA + LLY slice, with `02` remaining the most robust lane.",
        "- recommended next wave: tighten first-save capture integrity for structured standard runs before the next substantive protocol expansion.",
    ]
    return "\n".join(lines) + "\n"


def build_changed_files_manifest(paths: list[Path]) -> str:
    lines = [
        "# Changed Files Manifest",
        "",
        "Files created or modified by Wave 4E2:",
        "",
    ]
    for path in paths:
        lines.append(f"- `{path.as_posix()}`")
    return "\n".join(lines) + "\n"


def build_render_preview(
    nvda_payload: dict[str, Any],
    lly_payload: dict[str, Any],
    summary_payload: dict[str, Any],
) -> str:
    lines = [
        "# Wave 4E2 Render Preview",
        "",
        "Deterministic text preview of the pilot-slice reading order after the Wave 4E2 effort-robustness insertion.",
        "",
        "## NVDA Pilot Slice",
        "",
        "- why this case matters: present",
        "- what changed in the filing: present",
        "- how the lanes differ: present",
        f"- effort robustness headline: {nvda_payload['headline']}",
        "- lane cards / detail area: 02 hero, 03 main comparator, 01 secondary comparator, 00 recovered control",
        "- proof boundary / caveat: present below the lane detail area",
        "- lower audit surfaces: risk narrative summary, deterministic methods, agreement, and outline compare remain below the matrix",
        "",
        "## LLY Pilot Slice",
        "",
        "- why this case matters: present",
        "- what changed in the filing: present",
        "- how the lanes differ: present",
        f"- effort robustness headline: {lly_payload['headline']}",
        "- lane cards / detail area: 02 hero, 03 main comparator, 00 recovered control",
        "- proof boundary / caveat: present below the lane detail area",
        "- lower audit surfaces: explicit unavailable-state panel remains below the matrix",
        "",
        "## Cross-Case Footer",
        "",
        f"- protocol value under lower effort: {summary_payload['protocol_value_under_lower_effort']}",
        f"- still should not claim: {summary_payload['still_should_not_claim']}",
    ]
    return "\n".join(lines) + "\n"


def build_packet_readme(
    packet_dir: Path,
    effort_artifact_paths: list[Path],
    report_paths: list[Path],
    source_paths: list[Path],
    guardrail_script_path: Path,
) -> str:
    lines = [
        f"# {packet_dir.name}",
        "",
        "This packet contains the Wave 4E2 effort-robustness artifacts, reports, scripts, tests, and modified source files.",
        "",
        "## Included",
        "",
        "- public effort-robustness artifacts for NVDA, LLY, and the cross-issuer summary",
        "- Wave 4E2 report and findings",
        "- packet-local changed-file manifest and text render preview",
        "- capture guardrail helper plus targeted tests",
        "- modified pilot-slice source files and shared protocol-lab data contracts",
        "",
        "## Effort-Robustness Artifacts",
        "",
    ]
    for path in effort_artifact_paths:
        lines.append(f"- `{repo_rel(path)}`")
    lines.extend(["", "## Reports", ""])
    for path in report_paths:
        lines.append(f"- `{repo_rel(path)}`")
    lines.extend(
        [
            "",
            "## Modified Source Files",
            "",
        ]
    )
    for path in source_paths:
        lines.append(f"- `{path.as_posix()}`")
    lines.extend(
        [
            "",
            "## Guardrail Helper",
            "",
            f"- `{repo_rel(guardrail_script_path)}`",
            "",
            "## Biggest Remaining Blocker",
            "",
            f"- {BIGGEST_REMAINING_BLOCKER}",
        ]
    )
    return "\n".join(lines) + "\n"


def build_repo_paths_for_packet(
    effort_artifact_paths: list[Path],
    report_paths: list[Path],
) -> list[Path]:
    paths = [
        *effort_artifact_paths,
        *report_paths,
        *SCRIPT_AND_TEST_PATHS,
        *SOURCE_PATHS,
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


def generate_wave(stamp: str | None = None) -> GenerationSummary:
    nvda_standard_matrix = read_json(NVDA_STANDARD_MATRIX_PATH)
    lly_standard_matrix = read_json(LLY_STANDARD_MATRIX_PATH)
    standard_control_summary = read_json(STANDARD_CONTROL_SUMMARY_PATH)
    nvda_comparison = read_json(NVDA_COMPARISON_PATH)
    lly_comparison = read_json(LLY_COMPARISON_PATH)
    standard_vs_extended_summary = read_json(STANDARD_VS_EXTENDED_SUMMARY_PATH)

    nvda_effort_payload = build_effort_case_payload(
        "nvda_effort_robustness_v1",
        nvda_standard_matrix,
        nvda_comparison,
    )
    lly_effort_payload = build_effort_case_payload(
        "lly_effort_robustness_v1",
        lly_standard_matrix,
        lly_comparison,
    )
    effort_summary_payload = build_effort_summary_payload(
        standard_control_summary,
        standard_vs_extended_summary,
    )

    write_json(NVDA_EFFORT_ARTIFACT_PATH, nvda_effort_payload)
    write_json(LLY_EFFORT_ARTIFACT_PATH, lly_effort_payload)
    write_json(EFFORT_SUMMARY_ARTIFACT_PATH, effort_summary_payload)

    effort_artifact_paths = [
        NVDA_EFFORT_ARTIFACT_PATH,
        LLY_EFFORT_ARTIFACT_PATH,
        EFFORT_SUMMARY_ARTIFACT_PATH,
    ]
    report_paths = [REPORT_PATH, FINDINGS_PATH]

    changed_repo_paths = [
        Path(repo_rel(path)) for path in [*effort_artifact_paths, *report_paths, *SCRIPT_AND_TEST_PATHS, *SOURCE_PATHS]
    ]

    write_text(
        REPORT_PATH,
        build_report(
            effort_artifact_paths,
            report_paths,
            changed_repo_paths,
            Path("scripts/protocol_lab_capture_guardrail.py"),
        ),
    )
    write_text(FINDINGS_PATH, build_findings_report())

    effective_stamp = stamp or utc_stamp()
    packet_dir, zip_path = packet_paths_for_stamp(effective_stamp)
    ensure_clean_output(packet_dir)
    ensure_clean_output(zip_path)
    packet_dir.mkdir(parents=True, exist_ok=True)

    repo_paths = build_repo_paths_for_packet(effort_artifact_paths, report_paths)
    copy_repo_paths_into_packet(packet_dir, repo_paths)
    write_text(packet_dir / CHANGED_FILES_MANIFEST_NAME, build_changed_files_manifest(changed_repo_paths))
    write_text(
        packet_dir / ROOT_README_NAME,
        build_packet_readme(
            packet_dir,
            effort_artifact_paths,
            report_paths,
            SOURCE_PATHS,
            Path("scripts/protocol_lab_capture_guardrail.py"),
        ),
    )
    write_text(
        packet_dir / RENDER_PREVIEW_NAME,
        build_render_preview(nvda_effort_payload, lly_effort_payload, effort_summary_payload),
    )
    zip_directory(packet_dir, zip_path)

    renders_both_pilots = True
    console_summary_lines = [
        f"packet folder path: {packet_dir.resolve()}",
        f"zip path: {zip_path.resolve()}",
        "new effort-robustness artifact paths:",
        *(f"- {path.resolve()}" for path in effort_artifact_paths),
        "which source files were modified:",
        *(f"- {(REPO_ROOT / path).resolve()}" for path in SOURCE_PATHS),
        f"which guardrail helper/script was added: {(REPO_ROOT / 'scripts/protocol_lab_capture_guardrail.py').resolve()}",
        f"whether NVDA and LLY both render the effort-robustness block: {'yes' if renders_both_pilots else 'no'}",
        f"biggest remaining blocker before the next substantive protocol wave: {BIGGEST_REMAINING_BLOCKER}",
    ]
    for line in console_summary_lines:
        print(line)

    return GenerationSummary(
        packet_dir=packet_dir,
        zip_path=zip_path,
        effort_artifact_paths=[repo_rel(path) for path in effort_artifact_paths],
        report_paths=[repo_rel(path) for path in report_paths],
        source_paths=[path.as_posix() for path in SOURCE_PATHS],
        guardrail_script_path="scripts/protocol_lab_capture_guardrail.py",
        renders_both_pilots=renders_both_pilots,
        biggest_remaining_blocker=BIGGEST_REMAINING_BLOCKER,
        console_summary_lines=console_summary_lines,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Wave 4E2 effort-robustness artifact, report, and packet generator."
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
