from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from lab_output_tracks import CORE4_SHOWCASE_TICKERS


SCRIPT_VERSION = "lab_build_raw_prereq_audit.py@v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
SECTIONS_ROOT = REPO_ROOT / "scripts" / "_reports" / "risk_extraction_bundle" / "sections"
CACHE_ROOT = REPO_ROOT / "scripts" / "_cache"
LAB_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"
DEFAULT_REPORT = REPO_ROOT / "reports" / "lab_raw_prereq_audit.md"

# Legacy Core4 backstage runtime tickers (NVDA/KO/WM/GE). Public casebook
# tickers (NVDA/LLY/KO/META/TSLA/WMT) live in business_document_protocol_lab/
# and are not covered by this raw-prereq audit.
SHOWCASE_TICKERS = CORE4_SHOWCASE_TICKERS
RAW_DETECTORS = (
    "det_logodds_terms_v1",
    "det_jsd_ngrams_v1",
    "det_minhash_boilerplate_v1",
    "det_winnowing_fingerprint_v1",
    "det_structure_artifacts_v1",
    "det_rbo_agreement_v1",
)
SECTION = "10k_item1a"
SOURCE = "edgar"


@dataclass(frozen=True)
class YearPrereq:
    ticker: str
    year: int
    section_exists: bool
    cache_html_exists: bool
    raw_prereq_ready: bool


@dataclass(frozen=True)
class PairCoverage:
    ticker: str
    year_from: int
    year_to: int
    pair_prereq_ready: bool
    expected: int
    present: int
    missing: list[str]


def parse_tickers(raw: str) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for piece in raw.split(","):
        candidate = piece.strip().upper()
        if not candidate:
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        output.append(candidate)
    return output


def find_section_file(ticker: str, year: int) -> Path:
    return SECTIONS_ROOT / f"{ticker}_{year}_item_1a.txt"


def has_cache_html_for_year(ticker: str, year: int) -> bool:
    ticker_cache = CACHE_ROOT / ticker
    if not ticker_cache.exists() or not ticker_cache.is_dir():
        return False
    year_token = str(year)
    for entry in ticker_cache.iterdir():
        if not entry.is_file():
            continue
        lower_name = entry.name.lower()
        if year_token not in lower_name:
            continue
        if ".htm" in lower_name:
            return True
    return False


def build_raw_output_filename(
    year_from: int,
    year_to: int,
    detector_id: str,
) -> str:
    return f"lab_{SECTION}_{year_from}_{year_to}_{detector_id}_raw_{SOURCE}.json"


def has_raw_output(
    ticker: str,
    year_from: int,
    year_to: int,
    detector_id: str,
) -> bool:
    output_path = (
        LAB_ROOT
        / ticker
        / "outputs"
        / detector_id
        / build_raw_output_filename(year_from, year_to, detector_id)
    )
    return output_path.exists()


def build_year_rows(
    tickers: list[str],
    year_min: int,
    year_max: int,
) -> tuple[list[YearPrereq], dict[tuple[str, int], YearPrereq]]:
    rows: list[YearPrereq] = []
    by_key: dict[tuple[str, int], YearPrereq] = {}
    for ticker in tickers:
        for year in range(year_min, year_max + 1):
            section_exists = find_section_file(ticker, year).exists()
            cache_html_exists = has_cache_html_for_year(ticker, year)
            row = YearPrereq(
                ticker=ticker,
                year=year,
                section_exists=section_exists,
                cache_html_exists=cache_html_exists,
                raw_prereq_ready=section_exists or cache_html_exists,
            )
            rows.append(row)
            by_key[(ticker, year)] = row
    return rows, by_key


def build_pair_rows(
    tickers: list[str],
    year_min: int,
    year_max: int,
    year_index: dict[tuple[str, int], YearPrereq],
) -> list[PairCoverage]:
    rows: list[PairCoverage] = []
    for ticker in tickers:
        for year_from in range(year_min, year_max):
            year_to = year_from + 1
            left = year_index.get((ticker, year_from))
            right = year_index.get((ticker, year_to))
            pair_prereq_ready = bool(
                left is not None
                and right is not None
                and left.raw_prereq_ready
                and right.raw_prereq_ready
            )

            missing: list[str] = []
            present = 0
            for detector_id in RAW_DETECTORS:
                if has_raw_output(ticker, year_from, year_to, detector_id):
                    present += 1
                else:
                    missing.append(detector_id)

            rows.append(
                PairCoverage(
                    ticker=ticker,
                    year_from=year_from,
                    year_to=year_to,
                    pair_prereq_ready=pair_prereq_ready,
                    expected=len(RAW_DETECTORS),
                    present=present,
                    missing=missing,
                )
            )
    return rows


def csv(values: list[str]) -> str:
    if not values:
        return "none"
    return ", ".join(values)


def write_report(
    path: Path,
    year_rows: list[YearPrereq],
    pair_rows: list[PairCoverage],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    missing_prereq_years = 0
    for row in year_rows:
        if not row.raw_prereq_ready:
            missing_prereq_years += 1

    eligible_pairs = 0
    complete_raw_pairs = 0
    for row in pair_rows:
        if row.pair_prereq_ready:
            eligible_pairs += 1
        if row.present == row.expected:
            complete_raw_pairs += 1

    lines: list[str] = []
    lines.append("# Lab RAW Prerequisite Audit")
    lines.append("")
    lines.append(f"- script: {SCRIPT_VERSION}")
    lines.append(f"- sections_root: {SECTIONS_ROOT}")
    lines.append(f"- cache_root: {CACHE_ROOT}")
    lines.append(f"- lab_root: {LAB_ROOT}")
    lines.append(f"- years_audited: {year_rows[0].year}-{year_rows[-1].year}" if year_rows else "- years_audited: n/a")
    lines.append(f"- ticker_count: {len(set(row.ticker for row in year_rows))}")
    lines.append(f"- ticker_year_rows: {len(year_rows)}")
    lines.append(f"- ticker_year_missing_prereq_count: {missing_prereq_years}")
    lines.append(f"- pair_rows: {len(pair_rows)}")
    lines.append(f"- pair_prereq_ready_count: {eligible_pairs}")
    lines.append(f"- pair_full_raw_coverage_count: {complete_raw_pairs}")
    lines.append("")

    lines.append("## Ticker-Year Matrix")
    lines.append("| ticker | year | section_exists | cache_html_exists | raw_prereq_ready |")
    lines.append("| --- | --- | --- | --- | --- |")
    for row in year_rows:
        lines.append(
            f"| {row.ticker} | {row.year} | "
            + f"{'yes' if row.section_exists else 'no'} | "
            + f"{'yes' if row.cache_html_exists else 'no'} | "
            + f"{'yes' if row.raw_prereq_ready else 'no'} |"
        )
    lines.append("")

    lines.append("## Pair-Level RAW Eligibility and Coverage")
    lines.append("| ticker | pair | prereq_ready | raw_coverage | missing_detectors |")
    lines.append("| --- | --- | --- | --- | --- |")
    for row in pair_rows:
        pair = f"{row.year_from}-{row.year_to}"
        lines.append(
            f"| {row.ticker} | {pair} | "
            + f"{'yes' if row.pair_prereq_ready else 'no'} | "
            + f"{row.present}/{row.expected} | "
            + f"{csv(row.missing)} |"
        )
    lines.append("")

    lines.append("## Missing Prereq Years")
    missing_lines = 0
    for row in year_rows:
        if row.raw_prereq_ready:
            continue
        missing_lines += 1
        lines.append(
            f"- {row.ticker} {row.year}: "
            + "missing section text and cache html prerequisite"
        )
    if missing_lines == 0:
        lines.append("- none")
    lines.append("")

    lines.append("## Eligible Pairs Missing RAW Coverage")
    missing_pair_lines = 0
    for row in pair_rows:
        if not row.pair_prereq_ready:
            continue
        if row.present == row.expected:
            continue
        missing_pair_lines += 1
        pair = f"{row.year_from}-{row.year_to}"
        lines.append(
            f"- {row.ticker} {pair}: missing {csv(row.missing)}"
        )
    if missing_pair_lines == 0:
        lines.append("- none")
    lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit RAW prerequisite availability and RAW detector coverage for Lab showcase pairs."
    )
    parser.add_argument(
        "--tickers",
        default=",".join(SHOWCASE_TICKERS),
        help="Comma-separated tickers.",
    )
    parser.add_argument("--year-min", type=int, default=2019)
    parser.add_argument("--year-max", type=int, default=2025)
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT),
        help="Output markdown report path.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.year_min > args.year_max:
        raise SystemExit("--year-min must be <= --year-max")

    tickers = parse_tickers(args.tickers)
    if not tickers:
        raise SystemExit("No tickers provided.")

    year_rows, year_index = build_year_rows(tickers, args.year_min, args.year_max)
    pair_rows = build_pair_rows(tickers, args.year_min, args.year_max, year_index)

    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = REPO_ROOT / report_path
    write_report(report_path, year_rows, pair_rows)
    print(f"Wrote RAW prerequisite audit report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

