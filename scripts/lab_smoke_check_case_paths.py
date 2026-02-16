from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, cast

SCRIPT_VERSION = "lab_smoke_check_case_paths.py@v2"

REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"
DEFAULT_REGISTRY_PATH = LAB_ROOT / "lab_cases_v1.json"
REPORT_PATH = REPO_ROOT / "reports" / "smoke_lab_cases_paths.md"

KO_REQUIRED_CASE = ("KO", 2023, 2024)
KO_REQUIRED_OUTPUTS: list[tuple[str, str, str]] = [
    ("det_logodds_terms_v1", "deboilerplated", "edgar"),
    ("det_jsd_ngrams_v1", "deboilerplated", "edgar"),
    ("det_minhash_boilerplate_v1", "deboilerplated", "edgar"),
    ("det_structure_artifacts_v1", "deboilerplated", "edgar"),
    ("det_llm_delta_brief_v1", "deboilerplated", "edgar"),
    ("det_llm_excerpt_picker_v1", "deboilerplated", "edgar"),
]


@dataclass(frozen=True)
class MissingPathIssue:
    ticker: str
    year_from: int
    year_to: int
    detector_id: str
    filename: str
    reason: str


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


def to_repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except Exception:
        return path.as_posix()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Smoke-check output file paths referenced by lab_cases_v1.json."
    )
    parser.add_argument(
        "--registry",
        default=str(DEFAULT_REGISTRY_PATH),
        help="Path to lab_cases_v1.json",
    )
    parser.add_argument(
        "--ticker",
        default="",
        help="Optional ticker filter (for focused checks).",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    registry_path = Path(args.registry)
    if not registry_path.exists():
        raise SystemExit(f"Registry not found: {registry_path}")

    ticker_filter = args.ticker.strip().upper()
    payload = read_json(registry_path)
    root = as_dict(payload)
    if root is None:
        raise SystemExit("Registry root must be a JSON object.")
    cases_any = as_list(root.get("cases"))
    if cases_any is None:
        raise SystemExit("Registry missing cases[] array.")

    total_cases_checked = 0
    total_outputs_checked = 0
    missing_issues: list[MissingPathIssue] = []
    checked_by_ticker: dict[str, int] = {}
    missing_by_ticker: dict[str, int] = {}
    ko_case_seen = False
    ko_output_keys: set[tuple[str, str, str]] = set()

    for case_any in cases_any:
        case = as_dict(case_any)
        if case is None:
            continue
        ticker = (as_str(case.get("ticker")) or "").upper()
        if not ticker:
            continue
        if ticker_filter and ticker != ticker_filter:
            continue
        year_from = as_int(case.get("year_from")) or -1
        year_to = as_int(case.get("year_to")) or -1
        outputs_any = as_list(case.get("outputs")) or []

        total_cases_checked += 1
        checked_by_ticker[ticker] = checked_by_ticker.get(ticker, 0) + 1
        if ticker not in missing_by_ticker:
            missing_by_ticker[ticker] = 0

        for output_any in outputs_any:
            output = as_dict(output_any)
            if output is None:
                missing_issues.append(
                    MissingPathIssue(
                        ticker=ticker,
                        year_from=year_from,
                        year_to=year_to,
                        detector_id="<unknown>",
                        filename="<invalid>",
                        reason="Output entry is not an object.",
                    )
                )
                missing_by_ticker[ticker] += 1
                continue

            detector_id = as_str(output.get("detector_id")) or "<unknown>"
            cleaning_lens = as_str(output.get("cleaning_lens")) or ""
            source_id = as_str(output.get("source_id")) or ""
            if (
                ticker == KO_REQUIRED_CASE[0]
                and year_from == KO_REQUIRED_CASE[1]
                and year_to == KO_REQUIRED_CASE[2]
                and cleaning_lens
                and source_id
            ):
                ko_case_seen = True
                ko_output_keys.add((detector_id, cleaning_lens, source_id))
            filename_raw = as_str(output.get("filename")) or ""
            normalized_filename = normalize_rel_path(filename_raw)
            if normalized_filename is None:
                missing_issues.append(
                    MissingPathIssue(
                        ticker=ticker,
                        year_from=year_from,
                        year_to=year_to,
                        detector_id=detector_id,
                        filename=filename_raw or "<missing>",
                        reason="Output filename is unsafe or missing.",
                    )
                )
                missing_by_ticker[ticker] += 1
                continue

            total_outputs_checked += 1
            output_path = LAB_ROOT / ticker / normalized_filename
            if not output_path.exists():
                missing_issues.append(
                    MissingPathIssue(
                        ticker=ticker,
                        year_from=year_from,
                        year_to=year_to,
                        detector_id=detector_id,
                        filename=normalized_filename,
                        reason=f"Missing file: {to_repo_rel(output_path)}",
                    )
                )
                missing_by_ticker[ticker] += 1

    ko_assertion_issues: list[str] = []
    if not ticker_filter or ticker_filter == KO_REQUIRED_CASE[0]:
        if not ko_case_seen:
            ko_assertion_issues.append("KO 2023-2024 case is missing from lab_cases_v1.json.")
        else:
            for detector_id, lens, source_id in KO_REQUIRED_OUTPUTS:
                if (detector_id, lens, source_id) not in ko_output_keys:
                    ko_assertion_issues.append(
                        "KO 2023-2024 missing required output link: "
                        + f"detector={detector_id}, lens={lens}, source={source_id}"
                    )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Lab Case Paths Smoke Check")
    lines.append("")
    lines.append(f"- script: {SCRIPT_VERSION}")
    lines.append(f"- registry: {to_repo_rel(registry_path)}")
    lines.append(f"- ticker_filter: {ticker_filter if ticker_filter else '(none)'}")
    lines.append(f"- cases_checked: {total_cases_checked}")
    lines.append(f"- outputs_checked: {total_outputs_checked}")
    lines.append(f"- missing_count: {len(missing_issues)}")
    lines.append(f"- ko_required_assertion_failures: {len(ko_assertion_issues)}")
    lines.append("")

    lines.append("## Ticker Summary")
    if not checked_by_ticker:
        lines.append("- No matching cases were checked.")
    else:
        for ticker in sorted(checked_by_ticker.keys()):
            checked = checked_by_ticker[ticker]
            missing = missing_by_ticker.get(ticker, 0)
            lines.append(f"- {ticker}: cases={checked}, missing_paths={missing}")
    lines.append("")

    lines.append("## KO Required Assertions (2023-2024)")
    if ticker_filter and ticker_filter != KO_REQUIRED_CASE[0]:
        lines.append(
            f"- skipped due to ticker filter `{ticker_filter}` (KO assertions require KO case visibility)."
        )
    elif not ko_assertion_issues:
        lines.append("- KO required detector links are present for deboilerplated lens.")
    else:
        for issue in ko_assertion_issues:
            lines.append(f"- {issue}")
    lines.append("")

    if not missing_issues:
        lines.append("No missing output paths found.")
    else:
        lines.append("## Missing Paths")
        for issue in missing_issues:
            lines.append(
                f"- {issue.ticker} {issue.year_from}-{issue.year_to} "
                + f"detector={issue.detector_id} filename={issue.filename} :: {issue.reason}"
            )

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if missing_issues or ko_assertion_issues:
        print(
            "Lab case path smoke check FAILED: "
            + f"missing_count={len(missing_issues)} "
            + f"ko_required_assertion_failures={len(ko_assertion_issues)} "
            + f"report={to_repo_rel(REPORT_PATH)}"
        )
        return 1

    print(
        "Lab case path smoke check OK: "
        + f"outputs_checked={total_outputs_checked} report={to_repo_rel(REPORT_PATH)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
