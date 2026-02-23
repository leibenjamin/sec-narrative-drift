from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, cast

SCRIPT_VERSION = "lab_smoke_check_registry_paths.py@v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"
REGISTRY_PATH = LAB_ROOT / "lab_cases_v1.json"
REPORTS_ROOT = REPO_ROOT / "reports"
REPORT_PATH = REPORTS_ROOT / "lab_smoke_check_registry_paths.md"


@dataclass(frozen=True)
class CheckIssue:
    severity: str
    ticker: str
    year_from: int
    year_to: int
    message: str


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def as_dict(value: Any) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    raw = cast(dict[Any, Any], value)
    output: dict[str, Any] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            return None
        output[key] = item
    return output


def as_list(value: Any) -> Optional[list[Any]]:
    if isinstance(value, list):
        return cast(list[Any], value)
    return None


def as_str(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    return None


def as_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def normalize_rel_path(path_value: str) -> Optional[str]:
    normalized = path_value.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        return None
    if normalized.startswith("/"):
        return None
    if len(normalized) >= 2 and normalized[1] == ":":
        return None
    parts = normalized.split("/")
    cleaned: list[str] = []
    for part in parts:
        if part in {"", "."}:
            continue
        if part == "..":
            return None
        cleaned.append(part)
    if not cleaned:
        return None
    return "/".join(cleaned)


def resolve_input_path_like_ui(input_file: str) -> Optional[Path]:
    normalized = normalize_rel_path(input_file)
    if normalized is None:
        return None

    if normalized.startswith("data/"):
        return REPO_ROOT / "public" / normalized[len("data/") :]
    if normalized.startswith("public/"):
        return REPO_ROOT / normalized
    if normalized.startswith("bundles/"):
        marker = "/inputs/"
        marker_idx = normalized.find(marker)
        if marker_idx >= 0:
            tail = normalized[marker_idx + 1 :]
            return LAB_ROOT / "llm_inputs_v2" / tail
        basename = normalized.split("/")[-1]
        if not basename:
            return None
        return LAB_ROOT / "llm_inputs" / basename
    if normalized.startswith("inputs/"):
        if normalized.startswith("inputs/pair/") or normalized.startswith("inputs/year/"):
            return LAB_ROOT / "llm_inputs_v2" / normalized
        basename = normalized.split("/")[-1]
        if not basename:
            return None
        return LAB_ROOT / "llm_inputs" / basename
    if "/" not in normalized:
        return LAB_ROOT / "llm_inputs" / normalized
    return LAB_ROOT / normalized


def to_repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except Exception:
        return path.as_posix()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Smoke-check lab_cases_v1 output and provenance input paths."
    )
    parser.add_argument(
        "--registry",
        default=str(REGISTRY_PATH),
        help="Path to lab_cases_v1.json",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    registry_path = Path(args.registry)
    if not registry_path.exists():
        raise SystemExit(f"Registry not found: {registry_path}")

    payload = read_json(registry_path)
    root = as_dict(payload)
    if root is None:
        raise SystemExit("Registry JSON root is not an object.")
    cases_any = as_list(root.get("cases"))
    if cases_any is None:
        raise SystemExit("Registry missing cases[] array.")

    issues: list[CheckIssue] = []
    checked_cases = 0
    checked_outputs = 0

    for case_any in cases_any:
        case = as_dict(case_any)
        if case is None:
            continue
        ticker = (as_str(case.get("ticker")) or "").upper()
        year_from = as_int(case.get("year_from")) or -1
        year_to = as_int(case.get("year_to")) or -1
        tags_any = as_list(case.get("tags")) or []
        tags: list[str] = []
        for tag in tags_any:
            if isinstance(tag, str):
                tags.append(tag)
        is_featured = "recommended" in tags
        severity = "HARD_FAIL" if is_featured else "WARN"

        if not ticker or year_from < 0 or year_to < 0:
            issues.append(
                CheckIssue(
                    severity=severity,
                    ticker=ticker or "<unknown>",
                    year_from=year_from,
                    year_to=year_to,
                    message="Case metadata invalid (ticker/year fields).",
                )
            )
            continue

        checked_cases += 1
        outputs_any = as_list(case.get("outputs")) or []

        for output_any in outputs_any:
            output = as_dict(output_any)
            if output is None:
                issues.append(
                    CheckIssue(
                        severity=severity,
                        ticker=ticker,
                        year_from=year_from,
                        year_to=year_to,
                        message="Output entry is not an object.",
                    )
                )
                continue
            filename = as_str(output.get("filename"))
            detector_id = as_str(output.get("detector_id")) or "<unknown>"
            if filename is None:
                issues.append(
                    CheckIssue(
                        severity=severity,
                        ticker=ticker,
                        year_from=year_from,
                        year_to=year_to,
                        message=f"Output link missing filename (detector={detector_id}).",
                    )
                )
                continue

            safe_filename = normalize_rel_path(filename)
            if safe_filename is None:
                issues.append(
                    CheckIssue(
                        severity=severity,
                        ticker=ticker,
                        year_from=year_from,
                        year_to=year_to,
                        message=f"Unsafe output filename '{filename}' (detector={detector_id}).",
                    )
                )
                continue

            output_path = LAB_ROOT / ticker / safe_filename
            checked_outputs += 1
            if not output_path.exists():
                issues.append(
                    CheckIssue(
                        severity=severity,
                        ticker=ticker,
                        year_from=year_from,
                        year_to=year_to,
                        message=(
                            "Missing output file for UI path: "
                            + f"{to_repo_rel(output_path)} (detector={detector_id})"
                        ),
                    )
                )
                continue

            output_payload = read_json(output_path)
            output_root = as_dict(output_payload)
            if output_root is None:
                issues.append(
                    CheckIssue(
                        severity=severity,
                        ticker=ticker,
                        year_from=year_from,
                        year_to=year_to,
                        message=f"Output JSON root invalid: {to_repo_rel(output_path)}",
                    )
                )
                continue

            provenance = as_dict(output_root.get("provenance")) or {}
            input_file = as_str(provenance.get("input_file"))
            if input_file is None or not input_file.strip():
                continue

            resolved_input = resolve_input_path_like_ui(input_file)
            if resolved_input is None:
                issues.append(
                    CheckIssue(
                        severity=severity,
                        ticker=ticker,
                        year_from=year_from,
                        year_to=year_to,
                        message=(
                            "provenance.input_file is unsafe/unusable: "
                            + f"'{input_file}' in {to_repo_rel(output_path)}"
                        ),
                    )
                )
                continue
            if not resolved_input.exists():
                issues.append(
                    CheckIssue(
                        severity=severity,
                        ticker=ticker,
                        year_from=year_from,
                        year_to=year_to,
                        message=(
                            "provenance.input_file missing on disk: "
                            + f"'{input_file}' -> {to_repo_rel(resolved_input)} "
                            + f"(output={to_repo_rel(output_path)})"
                        ),
                    )
                )

    hard_fail_count = 0
    warn_count = 0
    for issue in issues:
        if issue.severity == "HARD_FAIL":
            hard_fail_count += 1
        else:
            warn_count += 1

    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Lab Registry Path Smoke Check")
    lines.append("")
    lines.append(f"- script: {SCRIPT_VERSION}")
    lines.append(f"- registry: {to_repo_rel(registry_path)}")
    lines.append(f"- cases_checked: {checked_cases}")
    lines.append(f"- outputs_checked: {checked_outputs}")
    lines.append(f"- hard_fail_count: {hard_fail_count}")
    lines.append(f"- warn_count: {warn_count}")
    lines.append("")
    if not issues:
        lines.append("No path issues found.")
    else:
        lines.append("## Issues")
        for issue in issues:
            lines.append(
                f"- [{issue.severity}] {issue.ticker} {issue.year_from}-{issue.year_to}: {issue.message}"
            )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if hard_fail_count > 0:
        print(
            "Registry path smoke check FAILED: "
            + f"hard_fail_count={hard_fail_count}, warn_count={warn_count}, "
            + f"report={to_repo_rel(REPORT_PATH)}"
        )
        return 1

    print(
        "Registry path smoke check OK: "
        + f"warn_count={warn_count}, report={to_repo_rel(REPORT_PATH)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
