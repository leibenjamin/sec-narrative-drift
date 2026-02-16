from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, cast

SCRIPT_VERSION = "lab_build_cases_health_reports.py@v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"
DEFAULT_REGISTRY_PATH = LAB_ROOT / "lab_cases_v1.json"
DEFAULT_HEALTH_REPORT_PATH = REPO_ROOT / "reports" / "lab_cases_health.md"
DEFAULT_SUMMARY_REPORT_PATH = REPO_ROOT / "reports" / "lab_cases_summary.md"


@dataclass(frozen=True)
class HealthRow:
    ticker: str
    year_from: int
    year_to: int
    lens: str
    detector: str
    filename: str
    exists: bool
    expected_path: str
    issue: str


@dataclass
class TickerCounts:
    case_count: int = 0
    output_count: int = 0
    missing_count: int = 0


@dataclass
class DetectorCounts:
    output_count: int = 0
    missing_count: int = 0


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


def parse_ticker_list(raw_values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for raw_value in raw_values:
        for piece in raw_value.split(","):
            candidate = piece.strip().upper()
            if not candidate:
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            output.append(candidate)
    return output


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


def to_repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except Exception:
        return path.as_posix()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build deterministic Lab dataset health/summary markdown reports."
    )
    parser.add_argument(
        "--registry",
        default=str(DEFAULT_REGISTRY_PATH),
        help="Path to lab_cases_v1.json",
    )
    parser.add_argument(
        "--health-report",
        default=str(DEFAULT_HEALTH_REPORT_PATH),
        help="Output path for lab_cases_health.md",
    )
    parser.add_argument(
        "--summary-report",
        default=str(DEFAULT_SUMMARY_REPORT_PATH),
        help="Output path for lab_cases_summary.md",
    )
    parser.add_argument(
        "--tickers",
        nargs="*",
        default=[],
        help="Optional ticker filter (space and/or comma-separated).",
    )
    parser.add_argument(
        "--fail-on-missing",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Return non-zero if any missing outputs are detected.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    registry_path = Path(args.registry)
    if not registry_path.exists():
        raise SystemExit(f"Registry not found: {registry_path}")

    health_report_path = Path(args.health_report)
    summary_report_path = Path(args.summary_report)
    ticker_filter = parse_ticker_list(args.tickers)
    ticker_filter_set = set(ticker_filter)

    payload = read_json(registry_path)
    root = as_dict(payload)
    if root is None:
        raise SystemExit("Registry JSON root must be an object.")
    cases_any = as_list(root.get("cases"))
    if cases_any is None:
        raise SystemExit("Registry missing cases[] array.")

    rows: list[HealthRow] = []
    ticker_counts: dict[str, TickerCounts] = {}
    detector_counts: dict[str, DetectorCounts] = {}

    for case_any in cases_any:
        case = as_dict(case_any)
        if case is None:
            continue

        ticker = (as_str(case.get("ticker")) or "").upper()
        year_from = as_int(case.get("year_from"))
        year_to = as_int(case.get("year_to"))
        if not ticker or year_from is None or year_to is None:
            continue
        if ticker_filter_set and ticker not in ticker_filter_set:
            continue

        counts = ticker_counts.get(ticker)
        if counts is None:
            counts = TickerCounts()
            ticker_counts[ticker] = counts
        counts.case_count += 1

        outputs_any = as_list(case.get("outputs")) or []
        for output_any in outputs_any:
            output = as_dict(output_any)
            if output is None:
                continue

            detector = as_str(output.get("detector_id")) or "<invalid>"
            lens = as_str(output.get("cleaning_lens")) or "<invalid>"
            filename_raw = as_str(output.get("filename")) or ""
            normalized = normalize_rel_path(filename_raw)

            expected_path = ""
            exists = False
            issue = ""
            if normalized is None:
                issue = "unsafe or missing filename"
            else:
                expected_abs = LAB_ROOT / ticker / normalized
                expected_path = to_repo_rel(expected_abs)
                exists = expected_abs.exists()
                if not exists:
                    issue = "missing file"

            row = HealthRow(
                ticker=ticker,
                year_from=year_from,
                year_to=year_to,
                lens=lens,
                detector=detector,
                filename=normalized if normalized is not None else filename_raw or "<missing>",
                exists=exists,
                expected_path=expected_path,
                issue=issue,
            )
            rows.append(row)

            counts.output_count += 1
            det_counts = detector_counts.get(detector)
            if det_counts is None:
                det_counts = DetectorCounts()
                detector_counts[detector] = det_counts
            det_counts.output_count += 1

            if not exists:
                counts.missing_count += 1
                det_counts.missing_count += 1

    rows.sort(
        key=lambda item: (
            item.ticker,
            item.year_from,
            item.year_to,
            item.lens,
            item.detector,
            item.filename,
        )
    )

    missing_rows: list[HealthRow] = []
    for row in rows:
        if not row.exists:
            missing_rows.append(row)

    total_cases = 0
    total_outputs = 0
    for counts in ticker_counts.values():
        total_cases += counts.case_count
        total_outputs += counts.output_count

    health_lines: list[str] = []
    health_lines.append("# Lab Cases Health")
    health_lines.append("")
    health_lines.append(f"- script: {SCRIPT_VERSION}")
    health_lines.append(f"- registry: {to_repo_rel(registry_path)}")
    health_lines.append(
        f"- ticker_filter: {', '.join(ticker_filter) if ticker_filter else '(none)'}"
    )
    health_lines.append(f"- cases_checked: {total_cases}")
    health_lines.append(f"- outputs_checked: {total_outputs}")
    health_lines.append(f"- missing_count: {len(missing_rows)}")
    health_lines.append("")
    health_lines.append("| ticker | year_from-year_to | lens | detector | filename | exists? |")
    health_lines.append("| --- | --- | --- | --- | --- | --- |")
    if rows:
        for row in rows:
            pair = f"{row.year_from}-{row.year_to}"
            exists_text = "yes" if row.exists else "no"
            health_lines.append(
                f"| {row.ticker} | {pair} | {row.lens} | {row.detector} | {row.filename} | {exists_text} |"
            )
    else:
        health_lines.append("| - | - | - | - | - | - |")
    health_lines.append("")

    summary_lines: list[str] = []
    summary_lines.append("# Lab Cases Summary")
    summary_lines.append("")
    summary_lines.append(f"- script: {SCRIPT_VERSION}")
    summary_lines.append(f"- registry: {to_repo_rel(registry_path)}")
    summary_lines.append(
        f"- ticker_filter: {', '.join(ticker_filter) if ticker_filter else '(none)'}"
    )
    summary_lines.append(f"- cases_checked: {total_cases}")
    summary_lines.append(f"- outputs_checked: {total_outputs}")
    summary_lines.append(f"- missing_count: {len(missing_rows)}")
    summary_lines.append("")

    summary_lines.append("## Counts Per Ticker")
    summary_lines.append("| ticker | cases | outputs | missing |")
    summary_lines.append("| --- | --- | --- | --- |")
    if ticker_counts:
        for ticker in sorted(ticker_counts.keys()):
            counts = ticker_counts[ticker]
            summary_lines.append(
                f"| {ticker} | {counts.case_count} | {counts.output_count} | {counts.missing_count} |"
            )
    else:
        summary_lines.append("| - | 0 | 0 | 0 |")
    summary_lines.append("")

    summary_lines.append("## Counts Per Detector")
    summary_lines.append("| detector | outputs | missing |")
    summary_lines.append("| --- | --- | --- |")
    if detector_counts:
        for detector in sorted(detector_counts.keys()):
            counts = detector_counts[detector]
            summary_lines.append(
                f"| {detector} | {counts.output_count} | {counts.missing_count} |"
            )
    else:
        summary_lines.append("| - | 0 | 0 |")
    summary_lines.append("")

    summary_lines.append("## Missing Outputs")
    if missing_rows:
        for row in missing_rows:
            pair = f"{row.year_from}-{row.year_to}"
            path_text = row.expected_path if row.expected_path else "<invalid path>"
            issue_text = row.issue if row.issue else "missing file"
            summary_lines.append(
                f"- {row.ticker} {pair} lens={row.lens} detector={row.detector} "
                + f"filename={row.filename} expected={path_text} issue={issue_text}"
            )
    else:
        summary_lines.append("- none")
    summary_lines.append("")

    write_text(health_report_path, "\n".join(health_lines) + "\n")
    write_text(summary_report_path, "\n".join(summary_lines) + "\n")

    print(
        "Lab health reports written: "
        + f"health={to_repo_rel(health_report_path)} "
        + f"summary={to_repo_rel(summary_report_path)} "
        + f"missing_count={len(missing_rows)}"
    )

    if bool(args.fail_on_missing) and missing_rows:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
