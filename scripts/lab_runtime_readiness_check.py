from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, cast

from lab_output_tracks import (
    CORE4_SHOWCASE_TICKERS,
    LEGACY_FIXED_WINDOW_RUNTIME_CASES,
    pick_latest_adjacent_pair,
)

SCRIPT_VERSION = "lab_runtime_readiness_check.py@v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"
REGISTRY_PATH = LAB_ROOT / "lab_cases_v1.json"
REPORT_PATH = REPO_ROOT / "reports" / "lab_runtime_readiness.md"

REQUIRED_TICKERS = list(CORE4_SHOWCASE_TICKERS)
REQUIRED_DETECTORS = [
    "det_logodds_terms_v1",
    "det_jsd_ngrams_v1",
    "det_minhash_boilerplate_v1",
    "det_winnowing_fingerprint_v1",
    "det_structure_artifacts_v1",
    "det_rbo_agreement_v1",
]
OPTIONAL_LLM_DETECTORS = ["det_llm_delta_brief_v1", "det_llm_excerpt_picker_v1"]
PAIR_POLICY_LATEST_TWO = "latest_two"
PAIR_POLICY_FIXED_WINDOW = "fixed_window"
LEGACY_REQUIRED_ADJACENT_PAIRS = list(
    LEGACY_FIXED_WINDOW_RUNTIME_CASES.get("NVDA", ((2022, 2023), (2023, 2024), (2024, 2025)))
)


@dataclass(frozen=True)
class PairCoverage:
    ticker: str
    year_from: int
    year_to: int
    required_expected: int
    required_present: int
    required_missing: list[str]
    optional_present: list[str]
    optional_missing: list[str]
    optional_broken: list[str]


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


def parse_registry(
    registry_path: Path,
) -> tuple[
    dict[str, dict[tuple[int, int], dict[tuple[str, str, str], str]]],
    dict[str, set[tuple[int, int]]],
    list[str],
]:
    payload = read_json(registry_path)
    root = as_dict(payload)
    if root is None:
        raise SystemExit("Registry JSON root is not an object.")

    cases_any = as_list(root.get("cases"))
    if cases_any is None:
        raise SystemExit("Registry missing cases[] array.")

    outputs_by_ticker: dict[str, dict[tuple[int, int], dict[tuple[str, str, str], str]]] = {}
    adjacent_pairs_by_ticker: dict[str, set[tuple[int, int]]] = {}
    parse_issues: list[str] = []

    for case_any in cases_any:
        case = as_dict(case_any)
        if case is None:
            parse_issues.append("Case entry is not an object.")
            continue

        ticker_raw = as_str(case.get("ticker"))
        year_from = as_int(case.get("year_from"))
        year_to = as_int(case.get("year_to"))
        if ticker_raw is None or year_from is None or year_to is None:
            parse_issues.append("Case entry has invalid ticker/year fields.")
            continue

        ticker = ticker_raw.upper()
        if ticker not in REQUIRED_TICKERS:
            continue

        pair = (year_from, year_to)
        if year_to - year_from == 1:
            if ticker not in adjacent_pairs_by_ticker:
                adjacent_pairs_by_ticker[ticker] = set()
            adjacent_pairs_by_ticker[ticker].add(pair)

        if ticker not in outputs_by_ticker:
            outputs_by_ticker[ticker] = {}
        if pair not in outputs_by_ticker[ticker]:
            outputs_by_ticker[ticker][pair] = {}
        output_index = outputs_by_ticker[ticker][pair]

        outputs_any = as_list(case.get("outputs")) or []
        for output_any in outputs_any:
            output = as_dict(output_any)
            if output is None:
                parse_issues.append(f"{ticker} {year_from}-{year_to}: output entry is not an object.")
                continue

            detector_id = as_str(output.get("detector_id"))
            cleaning_lens = as_str(output.get("cleaning_lens"))
            source_id = as_str(output.get("source_id"))
            filename = as_str(output.get("filename"))
            if detector_id is None or cleaning_lens is None or source_id is None or filename is None:
                parse_issues.append(
                    f"{ticker} {year_from}-{year_to}: output link has invalid detector/lens/source/filename."
                )
                continue

            key = (detector_id, cleaning_lens, source_id)
            if key not in output_index:
                output_index[key] = filename

    return outputs_by_ticker, adjacent_pairs_by_ticker, parse_issues


def resolve_ticker_output_path(ticker: str, filename: str) -> Optional[Path]:
    safe_rel = normalize_rel_path(filename)
    if safe_rel is None:
        return None
    return LAB_ROOT / ticker / safe_rel


def csv(items: list[str]) -> str:
    if not items:
        return "none"
    return ", ".join(items)


def pair_sort_key(pair: tuple[str, int, int]) -> tuple[int, int, int]:
    ticker = pair[0]
    order_index = len(REQUIRED_TICKERS)
    idx = 0
    while idx < len(REQUIRED_TICKERS):
        if REQUIRED_TICKERS[idx] == ticker:
            order_index = idx
            break
        idx += 1
    return (order_index, pair[1], pair[2])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit deterministic lab runtime readiness across NVDA/KO/WM/GE. "
            "Fails when required deboilerplated outputs are missing."
        )
    )
    parser.add_argument(
        "--registry",
        default=str(REGISTRY_PATH),
        help="Path to lab_cases_v1.json",
    )
    parser.add_argument(
        "--report",
        default=str(REPORT_PATH),
        help="Output markdown report path",
    )
    parser.add_argument(
        "--pair-policy",
        choices=(PAIR_POLICY_LATEST_TWO, PAIR_POLICY_FIXED_WINDOW),
        default=PAIR_POLICY_LATEST_TWO,
        help=(
            "Pair policy for required runtime coverage. latest_two checks the latest adjacent "
            "pair per ticker; fixed_window preserves the legacy 2022-2025 adjacent set."
        ),
    )
    parser.add_argument(
        "--verbose-progress",
        action="store_true",
        help="Emit progress lines while evaluating ticker/pair coverage.",
    )
    parser.add_argument(
        "--progress-interval-sec",
        type=int,
        default=300,
        help="Heartbeat interval in seconds for long-running operations.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    started = time.monotonic()
    args = build_parser().parse_args(argv)
    registry_path = Path(args.registry)
    report_path = Path(args.report)

    if not registry_path.exists():
        raise SystemExit(f"Registry not found: {registry_path}")

    outputs_by_ticker, adjacent_pairs_by_ticker, parse_issues = parse_registry(registry_path)

    coverage_rows: list[PairCoverage] = []
    required_failures: list[str] = []
    required_missing_pairs: set[tuple[str, int, int]] = set()
    latest_pairs: dict[str, Optional[tuple[int, int]]] = {}
    progress_interval_sec = max(1, int(args.progress_interval_sec))
    last_heartbeat = started

    for ticker_index, ticker in enumerate(REQUIRED_TICKERS, start=1):
        now = time.monotonic()
        if args.verbose_progress or now - last_heartbeat >= progress_interval_sec:
            elapsed = int(now - started)
            print(
                "[progress] runtime_readiness "
                + f"tickers={ticker_index}/{len(REQUIRED_TICKERS)} "
                + f"coverage_rows={len(coverage_rows)} required_failures={len(required_failures)} "
                + f"elapsed={elapsed}s",
                flush=True,
            )
            last_heartbeat = now
        ticker_adjacent_pairs = adjacent_pairs_by_ticker.get(ticker, set())
        latest_pair = pick_latest_adjacent_pair(ticker_adjacent_pairs)
        latest_pairs[ticker] = latest_pair

        required_pairs: list[tuple[int, int]] = []
        if args.pair_policy == PAIR_POLICY_LATEST_TWO:
            if latest_pair is not None:
                required_pairs.append(latest_pair)
        else:
            required_pairs.extend(LEGACY_REQUIRED_ADJACENT_PAIRS)
            if latest_pair is not None and latest_pair not in required_pairs:
                required_pairs.append(latest_pair)

        ticker_outputs = outputs_by_ticker.get(ticker, {})

        for year_from, year_to in required_pairs:
            pair_outputs = ticker_outputs.get((year_from, year_to), {})
            required_missing: list[str] = []
            optional_present: list[str] = []
            optional_missing: list[str] = []
            optional_broken: list[str] = []
            required_present = 0

            for detector_id in REQUIRED_DETECTORS:
                key = (detector_id, "deboilerplated", "edgar")
                filename = pair_outputs.get(key)
                if filename is None:
                    required_missing.append(f"{detector_id} (registry link missing)")
                    continue

                output_path = resolve_ticker_output_path(ticker, filename)
                if output_path is None:
                    required_missing.append(f"{detector_id} (unsafe filename '{filename}')")
                    continue
                if not output_path.exists():
                    required_missing.append(
                        f"{detector_id} (file missing: {to_repo_rel(output_path)})"
                    )
                    continue

                required_present += 1

            for detector_id in OPTIONAL_LLM_DETECTORS:
                key = (detector_id, "deboilerplated", "edgar")
                filename = pair_outputs.get(key)
                if filename is None:
                    optional_missing.append(f"{detector_id} (not linked)")
                    continue

                output_path = resolve_ticker_output_path(ticker, filename)
                if output_path is None:
                    optional_broken.append(f"{detector_id} (unsafe filename '{filename}')")
                    continue
                if not output_path.exists():
                    optional_broken.append(
                        f"{detector_id} (file missing: {to_repo_rel(output_path)})"
                    )
                    continue

                optional_present.append(detector_id)

            if required_missing:
                required_missing_pairs.add((ticker, year_from, year_to))
                for issue in required_missing:
                    required_failures.append(f"{ticker} {year_from}-{year_to}: {issue}")

            coverage_rows.append(
                PairCoverage(
                    ticker=ticker,
                    year_from=year_from,
                    year_to=year_to,
                    required_expected=len(REQUIRED_DETECTORS),
                    required_present=required_present,
                    required_missing=required_missing,
                    optional_present=optional_present,
                    optional_missing=optional_missing,
                    optional_broken=optional_broken,
                )
            )

    optional_missing_count = 0
    optional_broken_count = 0
    for row in coverage_rows:
        optional_missing_count += len(row.optional_missing)
        optional_broken_count += len(row.optional_broken)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Lab Runtime Readiness Check")
    lines.append("")
    lines.append(f"- script: {SCRIPT_VERSION}")
    lines.append(f"- registry: {to_repo_rel(registry_path)}")
    lines.append(f"- tickers: {', '.join(REQUIRED_TICKERS)}")
    lines.append("- required_lens: deboilerplated")
    lines.append("- required_source: edgar")
    lines.append(f"- required_detectors: {', '.join(REQUIRED_DETECTORS)}")
    lines.append(f"- optional_llm_detectors: {', '.join(OPTIONAL_LLM_DETECTORS)}")
    lines.append(f"- pair_policy: {args.pair_policy}")
    if args.pair_policy == PAIR_POLICY_FIXED_WINDOW:
        lines.append(
            "- required_pairs: "
            + ", ".join(f"{year_from}-{year_to}" for year_from, year_to in LEGACY_REQUIRED_ADJACENT_PAIRS)
            + " (+ latest pair when outside fixed window)"
        )
    else:
        lines.append("- required_pairs: latest adjacent pair per ticker from registry")
    lines.append(f"- rows_checked: {len(coverage_rows)}")
    lines.append(f"- required_failure_count: {len(required_failures)}")
    lines.append(f"- missing_required_pairs_count: {len(required_missing_pairs)}")
    lines.append(f"- optional_missing_count: {optional_missing_count}")
    lines.append(f"- optional_broken_count: {optional_broken_count}")
    lines.append("")
    lines.append("## Most Recent Adjacent Pair By Ticker")
    for ticker in REQUIRED_TICKERS:
        latest_pair = latest_pairs.get(ticker)
        if latest_pair is None:
            lines.append(f"- {ticker}: none found in registry")
        else:
            lines.append(f"- {ticker}: {latest_pair[0]}-{latest_pair[1]}")
    lines.append("")
    if parse_issues:
        lines.append("## Registry Parse Issues")
        for issue in parse_issues:
            lines.append(f"- {issue}")
        lines.append("")
    lines.append("## Coverage Table")
    lines.append(
        "| Ticker | Pair | Required Coverage | Missing Required | Optional Present | Optional Missing | Optional Broken |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for row in coverage_rows:
        pair_label = f"{row.year_from}-{row.year_to}"
        required_coverage = f"{row.required_present}/{row.required_expected}"
        lines.append(
            f"| {row.ticker} | {pair_label} | {required_coverage} | "
            + f"{csv(row.required_missing)} | {csv(row.optional_present)} | "
            + f"{csv(row.optional_missing)} | {csv(row.optional_broken)} |"
        )
    lines.append("")
    lines.append("## Missing Required Pairs (for batch generation)")
    if not required_missing_pairs:
        lines.append("None.")
    else:
        sorted_pairs = sorted(required_missing_pairs, key=pair_sort_key)
        for ticker, year_from, year_to in sorted_pairs:
            lines.append(f"- {ticker},{year_from},{year_to}")
    lines.append("")
    lines.append("## Required Failures")
    if not required_failures:
        lines.append("None.")
    else:
        for failure in required_failures:
            lines.append(f"- {failure}")
    lines.append("")
    lines.append("## Verdict")
    if required_failures:
        lines.append("NO-GO (required deterministic coverage is incomplete).")
    else:
        lines.append("GO (required deterministic coverage is complete).")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    elapsed = int(time.monotonic() - started)
    if required_failures:
        print(
            "Runtime readiness check FAILED: "
            + f"required_failure_count={len(required_failures)}, "
            + f"optional_missing_count={optional_missing_count}, "
            + f"optional_broken_count={optional_broken_count}, "
            + f"report={to_repo_rel(report_path)}, elapsed={elapsed}s"
        )
        return 1

    print(
        "Runtime readiness check OK: "
        + f"optional_missing_count={optional_missing_count}, "
        + f"optional_broken_count={optional_broken_count}, "
        + f"report={to_repo_rel(report_path)}, elapsed={elapsed}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
