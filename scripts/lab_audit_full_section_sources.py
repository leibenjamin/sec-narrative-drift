from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional, cast

import build_lab_outputs as blo  # type: ignore
from lab_output_tracks import CORE4_SHOWCASE_TICKERS
from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab" / "lab_cases_v1.json"
DEFAULT_CACHE_INDEX = REPO_ROOT / "data" / "sec_cache" / "indexes" / "ticker_year_index.json"
DEFAULT_REPORT = REPO_ROOT / "reports" / "lab_full_section_source_audit.md"
SECTIONS_ROOT = REPO_ROOT / "scripts" / "_reports" / "risk_extraction_bundle" / "sections"
HTML_CACHE_ROOT = REPO_ROOT / "scripts" / "_cache"
SEC_CACHE_FILINGS_ROOT = REPO_ROOT / "data" / "sec_cache" / "filings"
# Legacy Core4 backstage runtime tickers audited for full-section source parity.
SHOWCASE_TICKERS = CORE4_SHOWCASE_TICKERS
SECTION = "10k_item1a"

WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class SourceRow:
    ticker: str
    year: int
    canonical_exists: bool
    canonical_path: Optional[str]
    canonical_chars: Optional[int]
    canonical_paragraphs: Optional[int]
    canonical_sha256: Optional[str]
    sec_cache_exists: bool
    sec_cache_path: Optional[str]
    sec_cache_chars: Optional[int]
    sec_cache_paragraphs: Optional[int]
    sec_cache_sha256: Optional[str]
    overlap_ratio: Optional[float]
    html_candidate_count: int
    html_sample: list[str]
    flags: list[str]


@dataclass(frozen=True)
class PairRow:
    ticker: str
    year_from: int
    year_to: int
    prev_found: bool
    curr_found: bool
    coverage: Optional[float]
    warnings: list[str]
    prev_sentence_count: Optional[int]
    curr_sentence_count: Optional[int]
    shared_sentence_count: Optional[int]
    prev_retained_count: Optional[int]
    curr_retained_count: Optional[int]
    flags: list[str]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def as_dict(value: Any) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    raw = cast(dict[Any, Any], value)
    out: dict[str, Any] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            return None
        out[key] = item
    return out


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


def to_repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except Exception:
        return path.as_posix()


def parse_tickers(raw: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for token in raw.split(","):
        ticker = token.strip().upper()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        out.append(ticker)
    return out


def section_file_path(ticker: str, year: int, section: str) -> Path:
    suffix = blo.section_suffix(section)
    return SECTIONS_ROOT / f"{ticker}_{year}_{suffix}.txt"


def normalize_text(text: str) -> str:
    return WS_RE.sub(" ", text.strip().lower())


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_gzip_text(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return gzip.decompress(path.read_bytes()).decode("utf-8", errors="replace")


def risk_basename_for_form(form_type: str) -> str:
    if form_type.upper().startswith("20-F"):
        return "item_3d"
    return "item_1a"


def get_html_candidates(ticker: str, year: int) -> tuple[int, list[str]]:
    cache_dir = HTML_CACHE_ROOT / ticker.upper()
    if not cache_dir.exists() or not cache_dir.is_dir():
        return 0, []
    sample: list[str] = []
    count = 0
    year_token = str(year)
    for entry in sorted(cache_dir.iterdir(), key=lambda p: p.name):
        if not entry.is_file():
            continue
        lower_name = entry.name.lower()
        if year_token not in lower_name:
            continue
        if ".htm" not in lower_name:
            continue
        count += 1
        if len(sample) < 3:
            sample.append(entry.name)
    return count, sample


def load_cache_index(path: Path) -> dict[str, dict[str, dict[str, Any]]]:
    if not path.exists():
        return {}
    payload = read_json(path)
    root = as_dict(payload)
    if root is None:
        return {}
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for ticker, years_raw in root.items():
        ticker_name = ticker.upper()
        years_map = as_dict(years_raw)
        if years_map is None:
            continue
        year_entries: dict[str, dict[str, Any]] = {}
        for year_key, entry_raw in years_map.items():
            entry = as_dict(entry_raw)
            if entry is None:
                continue
            year_entries[year_key] = entry
        out[ticker_name] = year_entries
    return out


def load_pairs_from_registry(registry_path: Path, tickers: list[str], section: str) -> dict[str, list[tuple[int, int]]]:
    payload = read_json(registry_path)
    root = as_dict(payload)
    if root is None:
        raise SystemExit(f"Registry root is not an object: {registry_path}")
    cases = as_list(root.get("cases"))
    if cases is None:
        raise SystemExit(f"Registry missing cases[]: {registry_path}")
    out: dict[str, set[tuple[int, int]]] = {ticker: set() for ticker in tickers}
    for case_raw in cases:
        case = as_dict(case_raw)
        if case is None:
            continue
        ticker = (as_str(case.get("ticker")) or "").upper()
        if ticker not in out:
            continue
        case_section = as_str(case.get("section")) or ""
        if case_section != section:
            continue
        year_from = as_int(case.get("year_from"))
        year_to = as_int(case.get("year_to"))
        if year_from is None or year_to is None:
            continue
        out[ticker].add((year_from, year_to))
    ordered: dict[str, list[tuple[int, int]]] = {}
    for ticker in tickers:
        ordered[ticker] = sorted(out.get(ticker, set()), key=lambda pair: (pair[0], pair[1]))
    return ordered


def collect_years_by_ticker(pairs_by_ticker: dict[str, list[tuple[int, int]]]) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for ticker, pairs in pairs_by_ticker.items():
        years: set[int] = set()
        for year_from, year_to in pairs:
            years.add(year_from)
            years.add(year_to)
        out[ticker] = sorted(years)
    return out


def build_source_rows(
    section: str,
    tickers: list[str],
    years_by_ticker: dict[str, list[int]],
    cache_index: dict[str, dict[str, dict[str, Any]]],
    overlap_threshold: float,
) -> list[SourceRow]:
    rows: list[SourceRow] = []
    for ticker in tickers:
        for year in years_by_ticker.get(ticker, []):
            flags: list[str] = []
            canonical_path = section_file_path(ticker, year, section)
            canonical_exists = canonical_path.exists()
            canonical_text: Optional[str] = None
            canonical_chars: Optional[int] = None
            canonical_paragraphs: Optional[int] = None
            canonical_sha: Optional[str] = None
            if canonical_exists:
                canonical_text = canonical_path.read_text(encoding="utf-8", errors="replace")
                canonical_chars = len(canonical_text)
                canonical_paragraphs = len(blo.build_paragraphs(canonical_text, min_chars=200))
                canonical_sha = sha256_text(canonical_text)
            else:
                flags.append("missing_canonical")

            ticker_index = cache_index.get(ticker, {})
            year_entry = ticker_index.get(str(year))
            sec_cache_exists = False
            sec_cache_path: Optional[Path] = None
            sec_cache_text: Optional[str] = None
            if year_entry is None:
                flags.append("missing_sec_cache_index")
            else:
                cik = as_str(year_entry.get("cik"))
                accession = as_str(year_entry.get("accession"))
                form_type = as_str(year_entry.get("formType")) or "10-K"
                if cik and accession:
                    basename = risk_basename_for_form(form_type)
                    candidate = SEC_CACHE_FILINGS_ROOT / cik / accession / "risk" / f"{basename}.txt.gz"
                    sec_cache_text = read_gzip_text(candidate)
                    if sec_cache_text is not None:
                        sec_cache_exists = True
                        sec_cache_path = candidate
                    else:
                        flags.append("missing_sec_cache_text")
                else:
                    flags.append("missing_sec_cache_meta")

            sec_cache_chars: Optional[int] = None
            sec_cache_paragraphs: Optional[int] = None
            sec_cache_sha: Optional[str] = None
            if sec_cache_text is not None:
                sec_cache_chars = len(sec_cache_text)
                sec_cache_paragraphs = len(blo.build_paragraphs(sec_cache_text, min_chars=200))
                sec_cache_sha = sha256_text(sec_cache_text)

            overlap_ratio: Optional[float] = None
            if canonical_text is not None and sec_cache_text is not None:
                canonical_norm = normalize_text(canonical_text)
                sec_cache_norm = normalize_text(sec_cache_text)
                overlap_ratio = SequenceMatcher(None, canonical_norm, sec_cache_norm).ratio()
                if overlap_ratio < overlap_threshold:
                    flags.append("overlap_low")

            html_count, html_sample = get_html_candidates(ticker, year)
            if html_count == 0:
                flags.append("missing_html_cache")

            rows.append(
                SourceRow(
                    ticker=ticker,
                    year=year,
                    canonical_exists=canonical_exists,
                    canonical_path=to_repo_rel(canonical_path) if canonical_exists else None,
                    canonical_chars=canonical_chars,
                    canonical_paragraphs=canonical_paragraphs,
                    canonical_sha256=canonical_sha,
                    sec_cache_exists=sec_cache_exists,
                    sec_cache_path=to_repo_rel(sec_cache_path) if sec_cache_path is not None else None,
                    sec_cache_chars=sec_cache_chars,
                    sec_cache_paragraphs=sec_cache_paragraphs,
                    sec_cache_sha256=sec_cache_sha,
                    overlap_ratio=overlap_ratio,
                    html_candidate_count=html_count,
                    html_sample=html_sample,
                    flags=flags,
                )
            )
    return rows


def build_pair_rows(
    section: str,
    tickers: list[str],
    pairs_by_ticker: dict[str, list[tuple[int, int]]],
    coverage_threshold: float,
) -> list[PairRow]:
    rows: list[PairRow] = []
    for ticker in tickers:
        for year_from, year_to in pairs_by_ticker.get(ticker, []):
            flags: list[str] = []
            prev = blo.load_section_text(ticker, year_from, section, "edgar", REPO_ROOT)
            curr = blo.load_section_text(ticker, year_to, section, "edgar", REPO_ROOT)
            prev_found = prev is not None
            curr_found = curr is not None
            if not prev_found:
                flags.append("missing_prev_source")
            if not curr_found:
                flags.append("missing_curr_source")
            if prev is None or curr is None:
                rows.append(
                    PairRow(
                        ticker=ticker,
                        year_from=year_from,
                        year_to=year_to,
                        prev_found=prev_found,
                        curr_found=curr_found,
                        coverage=None,
                        warnings=[],
                        prev_sentence_count=None,
                        curr_sentence_count=None,
                        shared_sentence_count=None,
                        prev_retained_count=None,
                        curr_retained_count=None,
                        flags=flags,
                    )
                )
                continue

            lens_pair = blo.build_lens_pair(prev, curr, "deboilerplated")
            _, _, stats = blo.build_deboilerplated_pair(prev.text, curr.text)
            warnings = list(lens_pair.warnings)
            coverage = lens_pair.coverage
            if coverage is not None and coverage < coverage_threshold:
                flags.append("coverage_low")
            if "fallback_to_raw" in warnings:
                flags.append("fallback_to_raw")
            if "low_retained_text" in warnings:
                flags.append("low_retained_text")

            rows.append(
                PairRow(
                    ticker=ticker,
                    year_from=year_from,
                    year_to=year_to,
                    prev_found=prev_found,
                    curr_found=curr_found,
                    coverage=coverage,
                    warnings=warnings,
                    prev_sentence_count=stats.get("prev_sentence_count"),
                    curr_sentence_count=stats.get("curr_sentence_count"),
                    shared_sentence_count=stats.get("shared_sentence_count"),
                    prev_retained_count=stats.get("prev_retained_count"),
                    curr_retained_count=stats.get("curr_retained_count"),
                    flags=flags,
                )
            )
    return rows


def render_report(
    path: Path,
    tickers: list[str],
    section: str,
    overlap_threshold: float,
    coverage_threshold: float,
    source_rows: list[SourceRow],
    pair_rows: list[PairRow],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    source_anomaly_count = 0
    for row in source_rows:
        if row.flags:
            source_anomaly_count += 1
    pair_anomaly_count = 0
    for row in pair_rows:
        if row.flags:
            pair_anomaly_count += 1

    lines: list[str] = []
    lines.append("# Full-Section Source + Deboiler Audit")
    lines.append("")
    lines.append(f"- script: `{SCRIPT_VERSION}`")
    lines.append(f"- tickers: `{', '.join(tickers)}`")
    lines.append(f"- section: `{section}`")
    lines.append(f"- overlap_threshold: `{overlap_threshold:.2f}`")
    lines.append(f"- coverage_threshold: `{coverage_threshold:.2f}`")
    lines.append(f"- source_rows: `{len(source_rows)}`")
    lines.append(f"- source_rows_with_flags: `{source_anomaly_count}`")
    lines.append(f"- pair_rows: `{len(pair_rows)}`")
    lines.append(f"- pair_rows_with_flags: `{pair_anomaly_count}`")
    lines.append("")
    lines.append("## Source Coverage and Comparison")
    lines.append(
        "| ticker | year | canonical | sec_cache | html_candidates | canonical_chars | sec_cache_chars | canonical_paras | sec_cache_paras | overlap | flags |"
    )
    lines.append(
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    )
    for row in source_rows:
        canonical_status = "yes" if row.canonical_exists else "no"
        cache_status = "yes" if row.sec_cache_exists else "no"
        overlap_text = f"{row.overlap_ratio:.3f}" if row.overlap_ratio is not None else "-"
        flags_text = ", ".join(row.flags) if row.flags else "none"
        lines.append(
            "| "
            + " | ".join(
                [
                    row.ticker,
                    str(row.year),
                    canonical_status,
                    cache_status,
                    str(row.html_candidate_count),
                    str(row.canonical_chars if row.canonical_chars is not None else "-"),
                    str(row.sec_cache_chars if row.sec_cache_chars is not None else "-"),
                    str(row.canonical_paragraphs if row.canonical_paragraphs is not None else "-"),
                    str(row.sec_cache_paragraphs if row.sec_cache_paragraphs is not None else "-"),
                    overlap_text,
                    flags_text,
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("## Deboiler Pair Diagnostics")
    lines.append(
        "| ticker | pair | prev_found | curr_found | coverage | warnings | prev_sent | curr_sent | shared | prev_retained | curr_retained | flags |"
    )
    lines.append(
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    )
    for row in pair_rows:
        coverage_text = f"{row.coverage:.3f}" if row.coverage is not None else "-"
        warnings_text = ", ".join(row.warnings) if row.warnings else "none"
        flags_text = ", ".join(row.flags) if row.flags else "none"
        lines.append(
            "| "
            + " | ".join(
                [
                    row.ticker,
                    f"{row.year_from}-{row.year_to}",
                    "yes" if row.prev_found else "no",
                    "yes" if row.curr_found else "no",
                    coverage_text,
                    warnings_text,
                    str(row.prev_sentence_count if row.prev_sentence_count is not None else "-"),
                    str(row.curr_sentence_count if row.curr_sentence_count is not None else "-"),
                    str(row.shared_sentence_count if row.shared_sentence_count is not None else "-"),
                    str(row.prev_retained_count if row.prev_retained_count is not None else "-"),
                    str(row.curr_retained_count if row.curr_retained_count is not None else "-"),
                    flags_text,
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("## Flagged Source Rows")
    flagged_source = [row for row in source_rows if row.flags]
    if not flagged_source:
        lines.append("- none")
    else:
        for row in flagged_source:
            lines.append(
                f"- {row.ticker} {row.year}: flags={', '.join(row.flags)} "
                + f"(canonical={row.canonical_path or 'missing'}, sec_cache={row.sec_cache_path or 'missing'}, html_sample={row.html_sample})"
            )
    lines.append("")
    lines.append("## Flagged Deboiler Pairs")
    flagged_pairs = [row for row in pair_rows if row.flags]
    if not flagged_pairs:
        lines.append("- none")
    else:
        for row in flagged_pairs:
            lines.append(
                f"- {row.ticker} {row.year_from}-{row.year_to}: flags={', '.join(row.flags)} "
                + f"(coverage={row.coverage}, warnings={row.warnings})"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit full-section source consistency and deboiler quality for showcase cases."
    )
    parser.add_argument(
        "--registry",
        default=str(DEFAULT_REGISTRY),
        help="Path to lab_cases_v1.json",
    )
    parser.add_argument(
        "--cache-index",
        default=str(DEFAULT_CACHE_INDEX),
        help="Path to data/sec_cache/indexes/ticker_year_index.json",
    )
    parser.add_argument(
        "--tickers",
        default=",".join(SHOWCASE_TICKERS),
        help="Comma-separated tickers to audit.",
    )
    parser.add_argument(
        "--section",
        default=SECTION,
        help="Section identifier to audit.",
    )
    parser.add_argument(
        "--overlap-threshold",
        type=float,
        default=0.95,
        help="Flag source rows where normalized overlap falls below this value.",
    )
    parser.add_argument(
        "--coverage-threshold",
        type=float,
        default=0.55,
        help="Flag deboiler pair rows where coverage falls below this value.",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT),
        help="Markdown report output path.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    registry_path = Path(args.registry)
    if not registry_path.is_absolute():
        registry_path = REPO_ROOT / registry_path
    cache_index_path = Path(args.cache_index)
    if not cache_index_path.is_absolute():
        cache_index_path = REPO_ROOT / cache_index_path
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = REPO_ROOT / report_path

    tickers = parse_tickers(args.tickers)
    if not tickers:
        raise SystemExit("No tickers parsed from --tickers.")

    pairs_by_ticker = load_pairs_from_registry(
        registry_path=registry_path,
        tickers=tickers,
        section=args.section,
    )
    years_by_ticker = collect_years_by_ticker(pairs_by_ticker)
    cache_index = load_cache_index(cache_index_path)

    source_rows = build_source_rows(
        section=args.section,
        tickers=tickers,
        years_by_ticker=years_by_ticker,
        cache_index=cache_index,
        overlap_threshold=args.overlap_threshold,
    )
    pair_rows = build_pair_rows(
        section=args.section,
        tickers=tickers,
        pairs_by_ticker=pairs_by_ticker,
        coverage_threshold=args.coverage_threshold,
    )
    render_report(
        path=report_path,
        tickers=tickers,
        section=args.section,
        overlap_threshold=args.overlap_threshold,
        coverage_threshold=args.coverage_threshold,
        source_rows=source_rows,
        pair_rows=pair_rows,
    )

    source_flagged = sum(1 for row in source_rows if row.flags)
    pair_flagged = sum(1 for row in pair_rows if row.flags)
    print(
        "Full-section audit complete: "
        + f"source_rows={len(source_rows)}, source_flagged={source_flagged}, "
        + f"pair_rows={len(pair_rows)}, pair_flagged={pair_flagged}, "
        + f"report={to_repo_rel(report_path)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
