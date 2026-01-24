import argparse
import json
from pathlib import Path
from typing import Any, Optional, TypedDict, cast

from sec_cache import get_cache_root, filing_meta_path, risk_meta_path


REQUIRED_FILES = [
    "meta.json",
    "filings.json",
    "metrics_10k_item1a.json",
    "similarity_10k_item1a.json",
    "shifts_10k_item1a.json",
    "excerpts_10k_item1a.json",
]
MAX_EXCERPTS_PER_PAIR = 12

ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parent
DATA_DIR = REPO_ROOT / "public" / "data" / "sec_narrative_drift"
# Warnings that indicate likely INCORRECT extraction (surface these as issues):
# - business_heading_inside_slice: extraction includes Item 1 Business, grabbed too much
# - end_not_found: no end marker found, extraction may spill into later sections
# - anchor_low_confidence: (20-F) anchor position unreliable
# - item1a_not_found: extraction failed entirely
# - length_out_of_band: extraction suspiciously short or long
#
# Warnings that are INFORMATIONAL (don't surface as issues):
# - toc_detected, toc_header_repeated: just says TOC exists in document
# - early_position_penalty, toc_like_tail: heuristic penalties, not necessarily wrong
# - toc_range_mismatch: can trigger due to page numbering quirks
# - low_confidence_item1a: redundant with confidence score itself
# - toc_like_head: mostly fixed by strong_head_near check
RISK_WARNING_FLAGS = {
    "anchor_low_confidence",
    "business_heading_inside_slice",
    "end_not_found",
    "item1a_not_found",
    "length_out_of_band",
}
# Gate reasons that are purely informational (don't flag REVIEW status for these)
REVIEW_INFO_REASONS = {"toc_present_in_filing"}


class TickerYearEntry(TypedDict):
    cik: str
    accession: str
    formType: str
    filingDate: str


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def as_str_dict(value: Any) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    out: dict[str, Any] = {}
    for key, item in cast(dict[object, object], value).items():
        if not isinstance(key, str):
            return None
        out[key] = item
    return out


def as_list(value: Any) -> Optional[list[Any]]:
    if not isinstance(value, list):
        return None
    return list(cast(list[Any], value))


def as_str_list(value: Any) -> Optional[list[str]]:
    if not isinstance(value, list):
        return None
    out: list[str] = []
    for item in cast(list[object], value):
        if not isinstance(item, str):
            return None
        out.append(item)
    return out


def get_str(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    return None


def get_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    return None


def load_years_from_filings(path: Path) -> list[int]:
    if not path.exists():
        return []
    payload = read_json(path)
    rows = as_list(payload)
    if rows is None:
        return []
    years: list[int] = []
    for row in rows:
        row_dict = as_str_dict(row)
        if row_dict is None:
            continue
        year = row_dict.get("year")
        if isinstance(year, int):
            years.append(year)
    return years


def validate_filings_years(years: list[int], warnings: list[str]) -> list[int]:
    if not years:
        return []
    unique_years = sorted(set(years))
    if years != unique_years:
        warnings.append("filings years not sorted or not unique")
    return unique_years


def validate_metrics(path: Path, warnings: list[str]) -> None:
    if not path.exists():
        return
    payload = read_json(path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        warnings.append("metrics.json structure unexpected")
        return
    raw_years = as_list(payload_dict.get("years"))
    raw_drift = as_list(payload_dict.get("drift_vs_prev"))
    if raw_years is None or raw_drift is None:
        warnings.append("metrics.json missing years or drift_vs_prev")
        return
    if len(raw_years) != len(raw_drift):
        warnings.append("metrics years/drift length mismatch")


def validate_shifts(path: Path, warnings: list[str]) -> None:
    if not path.exists():
        return
    payload = read_json(path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        warnings.append("shifts.json structure unexpected")
        return
    year_pairs = payload_dict.get("yearPairs")
    if not isinstance(year_pairs, list):
        warnings.append("shifts.json missing yearPairs")
        return
    for pair in cast(list[object], year_pairs):
        pair_dict = as_str_dict(pair)
        if pair_dict is None:
            warnings.append("shifts yearPair not an object")
            continue
        from_year = pair_dict.get("from")
        to_year = pair_dict.get("to")
        if not isinstance(from_year, int) or not isinstance(to_year, int):
            warnings.append("shifts yearPair missing from/to")
            continue
        top_risers = pair_dict.get("topRisers")
        top_fallers = pair_dict.get("topFallers")
        if not isinstance(top_risers, list) or not isinstance(top_fallers, list):
            warnings.append("shifts yearPair missing risers/fallers")


def validate_excerpts(path: Path, warnings: list[str]) -> None:
    if not path.exists():
        return
    payload = read_json(path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        warnings.append("excerpts.json structure unexpected")
        return
    pairs = payload_dict.get("pairs")
    if not isinstance(pairs, list):
        warnings.append("excerpts.json missing pairs")
        return
    for pair in cast(list[object], pairs):
        pair_dict = as_str_dict(pair)
        if pair_dict is None:
            warnings.append("excerpt pair not an object")
            continue
        paragraphs = as_list(pair_dict.get("representativeParagraphs"))
        if paragraphs is None:
            warnings.append("excerpt pair missing representativeParagraphs")
            continue
        if len(paragraphs) > MAX_EXCERPTS_PER_PAIR:
            warnings.append("excerpt pair exceeds cap")
            break


def validate_meta_extraction(path: Path, warnings: list[str]) -> None:
    if not path.exists():
        return
    payload = read_json(path)
    meta_dict = as_str_dict(payload)
    if meta_dict is None:
        warnings.append("meta.json structure unexpected")
        return
    extraction = meta_dict.get("extraction")
    extraction_dict = as_str_dict(extraction)
    if extraction_dict is None:
        warnings.append("meta extraction missing")
        return
    confidence = extraction_dict.get("confidence")
    if isinstance(confidence, (int, float)):
        if float(confidence) < 0.5:
            warnings.append("meta extraction low confidence")
    else:
        warnings.append("meta extraction missing confidence")
    length_chars = extraction_dict.get("lengthChars")
    if isinstance(length_chars, int):
        if length_chars < 8000:
            warnings.append("meta extraction short length")


def load_cache_index(cache_root: Path) -> dict[str, dict[int, TickerYearEntry]]:
    index_path = cache_root / "indexes" / "ticker_year_index.json"
    if not index_path.exists():
        return {}
    payload = read_json(index_path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        return {}
    output: dict[str, dict[int, TickerYearEntry]] = {}
    for ticker_key, value in payload_dict.items():
        year_map = as_str_dict(value)
        if year_map is None:
            continue
        parsed_years: dict[int, TickerYearEntry] = {}
        for year_key, entry_value in year_map.items():
            entry = as_str_dict(entry_value)
            if entry is None:
                continue
            year_value = None
            if year_key.isdigit():
                year_value = int(year_key)
            if year_value is None:
                continue
            cik = get_str(entry.get("cik"))
            accession = get_str(entry.get("accession"))
            form_type = get_str(entry.get("formType"))
            filing_date = get_str(entry.get("filingDate"))
            if not cik or not accession or not form_type or not filing_date:
                continue
            parsed_years[year_value] = {
                "cik": cik,
                "accession": accession,
                "formType": form_type,
                "filingDate": filing_date,
            }
        if parsed_years:
            output[ticker_key.upper()] = parsed_years
    return output


def add_warning(warnings: list[str], value: str) -> None:
    if value not in warnings:
        warnings.append(value)


def add_cache_warnings(
    ticker: str,
    latest_year: Optional[int],
    cache_index: Optional[dict[str, dict[int, TickerYearEntry]]],
    warnings: list[str],
) -> None:
    if latest_year is None or cache_index is None:
        return
    year_map = cache_index.get(ticker.upper())
    if year_map is None:
        return
    entry = year_map.get(latest_year)
    if entry is None:
        add_warning(warnings, "cache missing latest year")
        return
    risk_meta = as_str_dict(read_json(risk_meta_path(entry["cik"], entry["accession"])))
    if risk_meta is None:
        add_warning(warnings, "cache missing latest rf_meta")
        return
    risk_warnings = as_str_list(risk_meta.get("warnings")) or []
    flagged: list[str] = []
    for warning in risk_warnings:
        if warning in RISK_WARNING_FLAGS:
            flagged.append(warning)
    status = get_str(risk_meta.get("status"))
    gate_reasons = as_str_list(risk_meta.get("gateReasons")) or []
    if status == "FAIL":
        flagged.append("status_fail")
        if gate_reasons:
            flagged.append(f"gate:{','.join(gate_reasons)}")
    elif status == "REVIEW":
        significant = [reason for reason in gate_reasons if reason not in REVIEW_INFO_REASONS]
        if significant:
            flagged.append("status_review")
            flagged.append(f"gate:{','.join(significant)}")
    quality_gate_failed = get_bool(risk_meta.get("qualityGateFailed"))
    if quality_gate_failed and "quality_gate_failed" not in flagged:
        flagged.append("quality_gate_failed")
    if flagged:
        add_warning(warnings, f"latest cache warnings: {','.join(flagged)}")
    filing_meta = as_str_dict(
        read_json(filing_meta_path(entry["cik"], entry["accession"]))
    )
    if filing_meta is None:
        return
    decode_warnings = as_str_list(filing_meta.get("decodeWarnings"))
    if decode_warnings:
        add_warning(warnings, "latest decode warnings")


def summarize_ticker(
    path: Path,
    cache_index: Optional[dict[str, dict[int, TickerYearEntry]]],
) -> dict[str, Any]:
    missing: list[str] = []
    warnings: list[str] = []
    for name in REQUIRED_FILES:
        if not (path / name).exists():
            missing.append(name)

    years = validate_filings_years(load_years_from_filings(path / "filings.json"), warnings)
    latest_year = max(years) if years else None

    validate_meta_extraction(path / "meta.json", warnings)
    validate_metrics(path / "metrics_10k_item1a.json", warnings)
    validate_shifts(path / "shifts_10k_item1a.json", warnings)
    validate_excerpts(path / "excerpts_10k_item1a.json", warnings)
    add_cache_warnings(path.name, latest_year, cache_index, warnings)

    return {
        "ticker": path.name,
        "years_count": len(years),
        "latest_year": latest_year,
        "missing": missing,
        "warnings": warnings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate public data outputs.")
    parser.add_argument(
        "--data-dir",
        default=str(DATA_DIR),
        help="Path to public/data/sec_narrative_drift.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        raise SystemExit(f"Data dir not found: {data_dir}")

    cache_index = load_cache_index(get_cache_root())

    summaries: list[dict[str, Any]] = []
    for entry in sorted(data_dir.iterdir()):
        if not entry.is_dir():
            continue
        summaries.append(summarize_ticker(entry, cache_index))

    header = "ticker\tyears\tlatest\tmissing_files\twarnings"
    print(header)
    for summary in summaries:
        missing = ",".join(summary["missing"]) if summary["missing"] else "-"
        warnings = "; ".join(summary["warnings"]) if summary["warnings"] else "-"
        latest = summary["latest_year"] if summary["latest_year"] is not None else "-"
        print(
            f"{summary['ticker']}\t{summary['years_count']}\t{latest}\t{missing}\t{warnings}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
