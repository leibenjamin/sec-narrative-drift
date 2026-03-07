from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, cast


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DATA_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift"
CACHE_ROOT = REPO_ROOT / "scripts" / "_cache"
INDEX_PATH = REPO_ROOT / "data" / "sec_cache" / "indexes" / "ticker_year_index.json"

YEAR_RE = re.compile(r"(?:19|20)\d{2}")
PAIR_POLICY_LATEST_TWO = "latest_two"
PAIR_POLICY_FIXED_WINDOW = "fixed_window"


@dataclass(frozen=True)
class AvailabilityResult:
    years: list[int]
    source: str
    warnings: list[str]


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def as_list(value: Any) -> Optional[list[Any]]:
    if isinstance(value, list):
        return cast(list[Any], value)
    return None


def as_str_dict(value: Any) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    output: dict[str, Any] = {}
    for key, item in cast(dict[Any, Any], value).items():
        if not isinstance(key, str):
            return None
        output[key] = item
    return output


def extract_years_from_metrics(path: Path) -> list[int]:
    if not path.exists():
        return []
    payload = read_json(path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        return []
    years_raw = as_list(payload_dict.get("years"))
    if years_raw is None:
        return []
    years: list[int] = []
    for entry in years_raw:
        if isinstance(entry, int):
            years.append(entry)
    return sorted(set(years))


def extract_years_from_pairs(path: Path) -> list[int]:
    if not path.exists():
        return []
    payload = read_json(path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        return []
    candidates: list[dict[str, Any]] = []
    for key in ("yearPairs", "pairs"):
        raw = as_list(payload_dict.get(key))
        if raw is None:
            continue
        for entry in raw:
            entry_dict = as_str_dict(entry)
            if entry_dict is None:
                continue
            candidates.append(entry_dict)
    years: set[int] = set()
    for entry in candidates:
        value_from = entry.get("from")
        value_to = entry.get("to")
        if isinstance(value_from, int):
            years.add(value_from)
        if isinstance(value_to, int):
            years.add(value_to)
    return sorted(years)


def extract_years_from_cache(ticker: str) -> list[int]:
    cache_dir = CACHE_ROOT / ticker.upper()
    if not cache_dir.exists():
        return []
    years: set[int] = set()
    for path in cache_dir.glob("*.htm*"):
        for match in YEAR_RE.findall(path.name):
            try:
                value = int(match)
            except ValueError:
                continue
            if 1990 <= value <= 2035:
                years.add(value)
    return sorted(years)


def load_years_from_index(ticker: str, index_payload: dict[str, Any]) -> list[int]:
    entry = index_payload.get(ticker.upper())
    if not isinstance(entry, dict):
        return []
    entry_dict = cast(dict[str, Any], entry)
    years: list[int] = []
    for key in entry_dict.keys():
        if key.isdigit():
            years.append(int(key))
    return sorted(set(years))

def resolve_availability(ticker: str, section: str, index_payload: dict[str, Any]) -> AvailabilityResult:
    warnings: list[str] = []
    ticker_dir = PUBLIC_DATA_ROOT / ticker.upper()
    metrics_path = ticker_dir / f"metrics_{section}.json"
    shifts_path = ticker_dir / f"shifts_{section}.json"
    excerpts_path = ticker_dir / f"excerpts_{section}.json"

    source_years: dict[str, list[int]] = {}
    metrics_years = extract_years_from_metrics(metrics_path)
    if metrics_years:
        source_years[str(metrics_path)] = metrics_years

    shifts_years = extract_years_from_pairs(shifts_path)
    if shifts_years:
        source_years[str(shifts_path)] = shifts_years

    excerpts_years = extract_years_from_pairs(excerpts_path)
    if excerpts_years:
        source_years[str(excerpts_path)] = excerpts_years

    cache_years = extract_years_from_cache(ticker)
    if cache_years:
        source_years[str(CACHE_ROOT / ticker.upper())] = cache_years

    index_years = load_years_from_index(ticker, index_payload)
    if index_years:
        source_years[str(INDEX_PATH)] = index_years

    if not source_years:
        warnings.append("no_years_found")
        return AvailabilityResult(years=[], source="none", warnings=warnings)

    merged_years: set[int] = set()
    for values in source_years.values():
        merged_years.update(values)
    years = sorted(merged_years)

    if metrics_years and index_years and max(index_years) > max(metrics_years):
        warnings.append("public_metrics_stale_vs_cache_index")
    if shifts_years and index_years and max(index_years) > max(shifts_years):
        warnings.append("public_shifts_stale_vs_cache_index")
    if excerpts_years and index_years and max(index_years) > max(excerpts_years):
        warnings.append("public_excerpts_stale_vs_cache_index")

    source = "merged:" + ",".join(sorted(source_years.keys()))
    return AvailabilityResult(years=years, source=source, warnings=warnings)



def build_adjacent_pairs(years: list[int], year_min: int, year_max: int) -> list[dict[str, int]]:
    years_filtered = sorted({year for year in years if year_min <= year <= year_max})
    pairs: list[dict[str, int]] = []
    for idx in range(len(years_filtered) - 1):
        current_year = years_filtered[idx]
        next_year = years_filtered[idx + 1]
        if next_year == current_year + 1:
            pairs.append({"year_from": current_year, "year_to": next_year})
    return pairs


def build_latest_two_pair(years: list[int], year_min: int) -> list[dict[str, int]]:
    years_filtered = sorted({year for year in years if year >= year_min})
    if len(years_filtered) < 2:
        return []
    latest_from: Optional[int] = None
    latest_to: Optional[int] = None
    for idx in range(len(years_filtered) - 1):
        current_year = years_filtered[idx]
        next_year = years_filtered[idx + 1]
        if next_year != current_year + 1:
            continue
        latest_from = current_year
        latest_to = next_year
    if latest_from is None or latest_to is None:
        return []
    return [{"year_from": latest_from, "year_to": latest_to}]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build continuity roster for Narrative Drift Lab showcase.")
    parser.add_argument("--tickers", required=True, help="Comma-separated tickers")
    parser.add_argument("--section", default="10k_item1a")
    parser.add_argument("--year_min", type=int, default=2019)
    parser.add_argument("--year_max", type=int, default=2025)
    parser.add_argument("--also_try_year", type=int, default=2026)
    parser.add_argument(
        "--pair-policy",
        choices=(PAIR_POLICY_LATEST_TWO, PAIR_POLICY_FIXED_WINDOW),
        default=PAIR_POLICY_LATEST_TWO,
        help=(
            "Pair selection policy. latest_two picks only the latest adjacent pair per ticker. "
            "fixed_window preserves year_min/year_max plus optional also_try_year logic."
        ),
    )
    parser.add_argument(
        "--out",
        default=str(REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab" / "lab_showcase_roster_v2.json"),
        help="Output roster JSON path",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    tickers = [item.strip().upper() for item in args.tickers.split(",") if item.strip()]
    if not tickers:
        raise SystemExit("No tickers provided.")

    index_payload: dict[str, Any] = {}
    if INDEX_PATH.exists():
        payload = read_json(INDEX_PATH)
        payload_dict = as_str_dict(payload)
        if payload_dict is not None:
            index_payload = payload_dict

    available_years_per_ticker: dict[str, list[int]] = {}
    pairs_per_ticker: dict[str, list[dict[str, int]]] = {}
    availability_sources: dict[str, str] = {}
    availability_warnings: dict[str, list[str]] = {}

    for ticker in tickers:
        availability = resolve_availability(ticker, args.section, index_payload)
        years = availability.years
        available_years_per_ticker[ticker] = years
        availability_sources[ticker] = availability.source
        availability_warnings[ticker] = availability.warnings

        if args.pair_policy == PAIR_POLICY_LATEST_TWO:
            pairs = build_latest_two_pair(years, args.year_min)
        else:
            pairs = build_adjacent_pairs(years, args.year_min, args.year_max)
            if args.also_try_year in years and args.year_max in years:
                extra_pair = {"year_from": args.year_max, "year_to": args.also_try_year}
                if extra_pair not in pairs:
                    pairs.append(extra_pair)

        pairs_per_ticker[ticker] = pairs

    roster_payload = {
        "version": "2.0",
        "updated_at": now_utc_iso(),
        "tickers": tickers,
        "section": args.section,
        "source_id": "edgar",
        "pair_policy": args.pair_policy,
        "available_years_per_ticker": available_years_per_ticker,
        "pairs_per_ticker": pairs_per_ticker,
        "hero_selection_targets": ["boilerplate", "structure", "meaningful", "most_recent"],
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(roster_payload, indent=2), encoding="utf-8")

    report_path = REPO_ROOT / "reports" / "showcase_filing_availability.md"
    report_lines: list[str] = []
    report_lines.append("# Showcase Filing Availability")
    report_lines.append("")
    report_lines.append(f"Generated: {now_utc_iso()}")
    report_lines.append(f"Section: {args.section}")
    report_lines.append(f"Pair policy: {args.pair_policy}")
    report_lines.append(f"Year range: {args.year_min}-{args.year_max}")
    if args.pair_policy == PAIR_POLICY_FIXED_WINDOW:
        report_lines.append(f"Also try year: {args.also_try_year}")
    report_lines.append("")

    for ticker in tickers:
        years = available_years_per_ticker.get(ticker, [])
        missing = [
            year
            for year in range(args.year_min, args.year_max + 1)
            if year not in set(years)
        ]
        selected_pairs = pairs_per_ticker.get(ticker, [])

        report_lines.append(f"## {ticker}")
        report_lines.append("")
        report_lines.append(f"- years found: {', '.join(str(y) for y in years) if years else 'none'}")
        report_lines.append(
            f"- missing years ({args.year_min}-{args.year_max}): {', '.join(str(y) for y in missing) if missing else 'none'}"
        )
        if selected_pairs:
            rendered_pairs = ", ".join(
                f"{pair['year_from']}-{pair['year_to']}" for pair in selected_pairs
            )
            report_lines.append(f"- selected pair(s): {rendered_pairs}")
        else:
            report_lines.append("- selected pair(s): none")

        if args.pair_policy == PAIR_POLICY_FIXED_WINDOW:
            has_window_year = args.year_max in years
            has_extra = args.also_try_year in years
            include_extra = has_window_year and has_extra
            extra_reason = (
                f"year {args.also_try_year} present"
                if has_extra
                else f"year {args.also_try_year} missing"
            )
            report_lines.append(
                f"- fixed-window extra pair included: {'yes' if include_extra else 'no'} (reason: {extra_reason})"
            )
        report_lines.append(f"- availability source: {availability_sources.get(ticker, 'unknown')}")
        warnings = availability_warnings.get(ticker, [])
        report_lines.append(
            f"- warnings: {', '.join(warnings) if warnings else 'none'}"
        )
        report_lines.append("")

    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Wrote roster to {out_path}")
    print(f"Wrote availability report to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
