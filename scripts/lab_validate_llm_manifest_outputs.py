from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import sys

SCRIPT_VERSION = "lab_validate_llm_manifest_outputs.py@v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "reports" / "lab_llm_run_manifest.json"
DEFAULT_REPORT_PATH = REPO_ROOT / "reports" / "lab_llm_manifest_validation.md"

REQUIRED_TOP_LEVEL_FIELDS = [
    "lab_schema_version",
    "detector_id",
    "cleaning_lens",
    "source_id",
    "ticker",
    "section",
    "year_from",
    "year_to",
    "artifacts",
    "evidence",
    "metrics",
    "provenance",
]

sys.path.append(str(Path(__file__).resolve().parent))
from lab_llm_precompute_utils import (  # type: ignore
    as_list,
    as_str_dict,
    get_int,
    get_str,
    read_json,
)


@dataclass(frozen=True)
class ManifestTarget:
    ticker: str
    year_from: int
    year_to: int
    section: str
    lens: str
    detector_id: str
    expected_output_path: str
    manifest_present_flag: Optional[bool]


@dataclass(frozen=True)
class ValidationIssue:
    issue_type: str
    expected_output_path: str
    ticker: str
    year_from: int
    year_to: int
    detector_id: str
    reasons: list[str]


def write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")


def load_manifest_targets(manifest_path: Path) -> list[ManifestTarget]:
    payload = read_json(manifest_path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        raise SystemExit(f"Manifest root is not an object: {manifest_path}")

    entries_raw = as_list(payload_dict.get("entries"))
    if entries_raw is None:
        raise SystemExit(f"Manifest missing list field 'entries': {manifest_path}")

    targets: list[ManifestTarget] = []
    for entry in entries_raw:
        entry_dict = as_str_dict(entry)
        if entry_dict is None:
            continue
        ticker = get_str(entry_dict.get("ticker"))
        year_from = get_int(entry_dict.get("year_from"))
        year_to = get_int(entry_dict.get("year_to"))
        section = get_str(entry_dict.get("section"))
        lens = get_str(entry_dict.get("lens"))
        detectors_raw = as_list(entry_dict.get("detectors"))
        if (
            ticker is None
            or year_from is None
            or year_to is None
            or section is None
            or lens is None
            or detectors_raw is None
        ):
            continue
        for detector in detectors_raw:
            detector_dict = as_str_dict(detector)
            if detector_dict is None:
                continue
            detector_id = get_str(detector_dict.get("detector_id"))
            expected_path = get_str(detector_dict.get("expected_output_path"))
            present_flag_raw = detector_dict.get("present")
            present_flag: Optional[bool] = None
            if isinstance(present_flag_raw, bool):
                present_flag = present_flag_raw
            if detector_id is None or expected_path is None:
                continue
            targets.append(
                ManifestTarget(
                    ticker=ticker,
                    year_from=year_from,
                    year_to=year_to,
                    section=section,
                    lens=lens,
                    detector_id=detector_id,
                    expected_output_path=expected_path,
                    manifest_present_flag=present_flag,
                )
            )
    return targets


def validate_output_json(target: ManifestTarget, output_path: Path) -> list[str]:
    reasons: list[str] = []
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        reasons.append(f"invalid JSON: {exc}")
        return reasons

    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        reasons.append("JSON root is not an object")
        return reasons

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in payload_dict:
            reasons.append(f"missing top-level field: {field}")

    detector_id = get_str(payload_dict.get("detector_id"))
    if detector_id != target.detector_id:
        reasons.append(
            f"detector_id mismatch: got {detector_id!r}, expected {target.detector_id!r}"
        )

    cleaning_lens = get_str(payload_dict.get("cleaning_lens"))
    if cleaning_lens != target.lens:
        reasons.append(
            f"cleaning_lens mismatch: got {cleaning_lens!r}, expected {target.lens!r}"
        )

    ticker = get_str(payload_dict.get("ticker"))
    if ticker is None or ticker.upper() != target.ticker.upper():
        reasons.append(f"ticker mismatch: got {ticker!r}, expected {target.ticker!r}")

    section = get_str(payload_dict.get("section"))
    if section != target.section:
        reasons.append(f"section mismatch: got {section!r}, expected {target.section!r}")

    year_from = get_int(payload_dict.get("year_from"))
    year_to = get_int(payload_dict.get("year_to"))
    if year_from != target.year_from:
        reasons.append(
            f"year_from mismatch: got {year_from!r}, expected {target.year_from!r}"
        )
    if year_to != target.year_to:
        reasons.append(f"year_to mismatch: got {year_to!r}, expected {target.year_to!r}")

    artifacts = as_str_dict(payload_dict.get("artifacts"))
    if artifacts is None:
        reasons.append("artifacts must be an object")

    evidence = as_list(payload_dict.get("evidence"))
    if evidence is None:
        reasons.append("evidence must be a list")

    metrics = as_str_dict(payload_dict.get("metrics"))
    if metrics is None:
        reasons.append("metrics must be an object")

    provenance = as_str_dict(payload_dict.get("provenance"))
    if provenance is None:
        reasons.append("provenance must be an object")

    return reasons


def validate_targets(targets: list[ManifestTarget]) -> tuple[list[ValidationIssue], list[ValidationIssue], list[ValidationIssue]]:
    missing: list[ValidationIssue] = []
    invalid: list[ValidationIssue] = []
    manifest_mismatch: list[ValidationIssue] = []

    for target in targets:
        expected_abs = REPO_ROOT / Path(target.expected_output_path)
        exists_now = expected_abs.exists()

        if target.manifest_present_flag is not None and target.manifest_present_flag != exists_now:
            manifest_mismatch.append(
                ValidationIssue(
                    issue_type="manifest_present_mismatch",
                    expected_output_path=target.expected_output_path,
                    ticker=target.ticker,
                    year_from=target.year_from,
                    year_to=target.year_to,
                    detector_id=target.detector_id,
                    reasons=[
                        "manifest 'present' flag does not match filesystem state",
                        f"manifest_present={target.manifest_present_flag}, filesystem_present={exists_now}",
                    ],
                )
            )

        if not exists_now:
            missing.append(
                ValidationIssue(
                    issue_type="missing",
                    expected_output_path=target.expected_output_path,
                    ticker=target.ticker,
                    year_from=target.year_from,
                    year_to=target.year_to,
                    detector_id=target.detector_id,
                    reasons=["file not found"],
                )
            )
            continue

        reasons = validate_output_json(target, expected_abs)
        if reasons:
            invalid.append(
                ValidationIssue(
                    issue_type="invalid",
                    expected_output_path=target.expected_output_path,
                    ticker=target.ticker,
                    year_from=target.year_from,
                    year_to=target.year_to,
                    detector_id=target.detector_id,
                    reasons=reasons,
                )
            )

    return missing, invalid, manifest_mismatch


def issue_lines(issues: list[ValidationIssue]) -> list[str]:
    lines: list[str] = []
    for issue in issues:
        pair_label = f"{issue.year_from}-{issue.year_to}"
        lines.append(
            f"- {issue.ticker} {pair_label} {issue.detector_id}: {issue.expected_output_path}"
        )
        for reason in issue.reasons:
            lines.append(f"  - {reason}")
    if not lines:
        lines.append("- none")
    return lines


def build_report(
    manifest_path: Path,
    target_count: int,
    missing: list[ValidationIssue],
    invalid: list[ValidationIssue],
    manifest_mismatch: list[ValidationIssue],
) -> list[str]:
    lines: list[str] = []
    lines.append("# LLM Manifest Validation")
    lines.append("")
    lines.append(f"Manifest: {manifest_path.as_posix()}")
    lines.append(f"Script: {SCRIPT_VERSION}")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| Targets | {target_count} |")
    lines.append(f"| Missing files | {len(missing)} |")
    lines.append(f"| Invalid files | {len(invalid)} |")
    lines.append(f"| Present-flag mismatches | {len(manifest_mismatch)} |")
    lines.append("")
    lines.append("## Missing Outputs")
    lines.extend(issue_lines(missing))
    lines.append("")
    lines.append("## Invalid Outputs")
    lines.extend(issue_lines(invalid))
    lines.append("")
    lines.append("## Manifest Present-Flag Mismatches")
    lines.extend(issue_lines(manifest_mismatch))
    return lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate LLM outputs referenced by reports/lab_llm_run_manifest.json."
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST_PATH),
        help="Path to reports/lab_llm_run_manifest.json",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT_PATH),
        help="Write markdown validation report to this path.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Return success even when manifest targets are missing.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")

    targets = load_manifest_targets(manifest_path)
    missing, invalid, manifest_mismatch = validate_targets(targets)

    report_lines = build_report(
        manifest_path=manifest_path,
        target_count=len(targets),
        missing=missing,
        invalid=invalid,
        manifest_mismatch=manifest_mismatch,
    )
    write_text(Path(args.report), report_lines)

    print(
        "Manifest validation summary: "
        + f"targets={len(targets)}, missing={len(missing)}, "
        + f"invalid={len(invalid)}, present_flag_mismatch={len(manifest_mismatch)}"
    )
    if missing:
        print("Missing outputs:")
        for line in issue_lines(missing):
            print(line)
    if invalid:
        print("Invalid outputs:")
        for line in issue_lines(invalid):
            print(line)
    if manifest_mismatch:
        print("Manifest present-flag mismatches:")
        for line in issue_lines(manifest_mismatch):
            print(line)
    print(f"Wrote validation report: {args.report}")

    if invalid:
        return 1
    if missing and not args.allow_missing:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
