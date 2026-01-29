import argparse
import json
from pathlib import Path
from typing import Any, Optional, TypedDict, cast

from sec_cache import (
    filing_html_path,
    filing_text_path,
    get_cache_root,
    load_gz_text,
    load_json,
    risk_meta_path,
    ticker_year_index_path,
)
from sec_extract_item1a import extract_item1a_from_html, extract_item1a_from_text


class TickerYearEntry(TypedDict):
    cik: str
    accession: str
    formType: str
    filingDate: str


class CacheRecord(TypedDict):
    cik: str
    accession: str
    ticker: str
    year: int
    confidence: float
    warnings: list[str]
    qualityGateFailed: bool
    method: str


ROOT_DIR = Path(__file__).resolve().parent
UNIVERSE_PATH = ROOT_DIR / "universe_featured.json"


def as_str_dict(value: Any) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    out: dict[str, Any] = {}
    for key, item in cast(dict[object, object], value).items():
        if not isinstance(key, str):
            return None
        out[key] = item
    return out


def as_str(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    return None


def as_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    return None


def as_float(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def as_str_list(value: Any) -> Optional[list[str]]:
    if not isinstance(value, list):
        return None
    out: list[str] = []
    for item in cast(list[object], value):
        if not isinstance(item, str):
            return None
        out.append(item)
    return out


def parse_ticker_year_index(raw: Any) -> dict[str, dict[int, TickerYearEntry]]:
    payload = as_str_dict(raw)
    if payload is None:
        return {}
    output: dict[str, dict[int, TickerYearEntry]] = {}
    for ticker_key, value in payload.items():
        year_map = as_str_dict(value)
        if year_map is None:
            continue
        parsed_years: dict[int, TickerYearEntry] = {}
        for year_key, entry_value in year_map.items():
            entry = as_str_dict(entry_value)
            if entry is None:
                continue
            cik = as_str(entry.get("cik"))
            accession = as_str(entry.get("accession"))
            form_type = as_str(entry.get("formType"))
            filing_date = as_str(entry.get("filingDate"))
            if cik is None or accession is None or form_type is None or filing_date is None:
                continue
            try:
                year_int = int(year_key)
            except ValueError:
                continue
            parsed_years[year_int] = {
                "cik": cik,
                "accession": accession,
                "formType": form_type,
                "filingDate": filing_date,
            }
        if parsed_years:
            output[ticker_key] = parsed_years
    return output


def build_accession_map(
    index_payload: dict[str, dict[int, TickerYearEntry]]
) -> dict[tuple[str, str], tuple[str, int]]:
    mapping: dict[tuple[str, str], tuple[str, int]] = {}
    for ticker, year_map in index_payload.items():
        for year, entry in year_map.items():
            key = (entry["cik"], entry["accession"])
            mapping[key] = (ticker, year)
    return mapping


def load_featured_tickers(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    output: list[str] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        ticker = item.get("ticker")
        if isinstance(ticker, str):
            output.append(ticker.upper())
    return output


def parse_case(arg: str) -> Optional[tuple[str, str, int]]:
    parts = arg.split(":")
    if len(parts) == 2:
        ticker_raw, year_raw = parts
        label = f"{ticker_raw}_{year_raw}"
    elif len(parts) == 3:
        label, ticker_raw, year_raw = parts
    else:
        return None
    try:
        year = int(year_raw)
    except ValueError:
        return None
    ticker = ticker_raw.upper()
    return label, ticker, year


def build_default_cases(
    index_payload: dict[str, dict[int, TickerYearEntry]], limit: int
) -> list[tuple[str, str, int]]:
    tickers = load_featured_tickers(UNIVERSE_PATH)
    if not tickers:
        tickers = sorted(index_payload.keys())
    cases: list[tuple[str, str, int]] = []
    for ticker in tickers:
        year_map = index_payload.get(ticker)
        if not year_map:
            continue
        latest_year = max(year_map.keys())
        cases.append((f"{ticker}_{latest_year}", ticker, latest_year))
        if len(cases) >= limit:
            break
    return cases


def load_cached_filing(cik: str, accession: str) -> tuple[Optional[str], Optional[str]]:
    html = load_gz_text(filing_html_path(cik, accession))
    if html is not None:
        return html, None
    text = load_gz_text(filing_text_path(cik, accession))
    return None, text


def run_extraction(
    cik: str, accession: str
) -> tuple[str, float, str, list[str], dict[str, Any]]:
    html, text = load_cached_filing(cik, accession)
    if html is not None:
        return extract_item1a_from_html(html)
    if text is not None:
        return extract_item1a_from_text(text)
    return "", 0.0, "missing", ["missing_cache_input"], {}


def load_cached_risk_meta(cik: str, accession: str) -> Optional[CacheRecord]:
    raw = load_json(risk_meta_path(cik, accession))
    payload = as_str_dict(raw)
    if payload is None:
        return None
    confidence = as_float(payload.get("confidence"))
    method = as_str(payload.get("method"))
    warnings = as_str_list(payload.get("warnings"))
    quality_gate_failed = as_bool(payload.get("qualityGateFailed"))
    if confidence is None or method is None or warnings is None or quality_gate_failed is None:
        return None
    return {
        "cik": cik,
        "accession": accession,
        "ticker": "unknown",
        "year": 0,
        "confidence": confidence,
        "warnings": warnings,
        "qualityGateFailed": quality_gate_failed,
        "method": method,
    }


def bucket_confidence(confidence: float) -> str:
    if confidence < 0.25:
        return "0.00-0.24"
    if confidence < 0.5:
        return "0.25-0.49"
    if confidence < 0.75:
        return "0.50-0.74"
    if confidence < 0.9:
        return "0.75-0.89"
    return "0.90-1.00"


def format_bool(value: Optional[bool]) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "unknown"


def evaluate_case(
    label: str, section: str, warnings: list[str], debug: dict[str, Any]
) -> list[str]:
    notes: list[str] = []
    debug_info = as_str_dict(debug.get("debug"))
    toc_score = as_str_dict(debug_info.get("tocScoreSliceHead")) if debug_info else None
    toc_like = as_bool(toc_score.get("tocLike")) if toc_score else None
    head = section[:400].lower()

    if label == "MS_2017":
        if toc_like is True:
            notes.append("fail: toc_like_head true")
        if "risk factors" not in head:
            notes.append("fail: risk factors missing near head")
        if "item 1a" not in head:
            notes.append("warn: item 1a missing near head")
    if label == "UNH_2018":
        if "start_crossref_suspected" in warnings:
            notes.append("fail: start_crossref_suspected")
        if "table of contents" in head:
            notes.append("fail: toc header in head")
    if label == "WMT_2017":
        idx_item1a = head.find("item 1a")
        idx_item1biz = head.find("item 1. business")
        if idx_item1biz != -1 and idx_item1a != -1 and idx_item1biz < idx_item1a:
            notes.append("fail: item 1 business before item 1a")
    if label == "COST_2024":
        toc_hits = section.lower().count("table of contents")
        if toc_hits >= 3:
            notes.append(f"fail: toc repeats {toc_hits}")
    if label == "PFE_2025":
        end_marker = as_str(debug.get("endMarkerUsed"))
        if end_marker is None and "end_fallback_used" not in warnings:
            notes.append("fail: no end marker and no fallback warning")

    if toc_like is not None:
        notes.append(f"toc_like_head={format_bool(toc_like)}")
    return notes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Risk extraction cache report.")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of cached filings to scan (0 = all).",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Use cached risk_meta.json for summary instead of re-extracting every filing.",
    )
    parser.add_argument(
        "--cases",
        nargs="+",
        default=None,
        help="Override sanity cases (TICKER:YEAR or LABEL:TICKER:YEAR).",
    )
    parser.add_argument(
        "--case-limit",
        type=int,
        default=6,
        help="Number of default sanity cases when --cases is not provided.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    index_payload = parse_ticker_year_index(load_json(ticker_year_index_path()))
    accession_map = build_accession_map(index_payload)

    cases: list[tuple[str, str, int]] = []
    if args.cases:
        for raw_case in args.cases:
            parsed = parse_case(raw_case)
            if parsed is None:
                print(f"warning: skipping invalid case '{raw_case}'")
                continue
            cases.append(parsed)
    if not cases:
        cases = build_default_cases(index_payload, args.case_limit)

    print("sanity_checks:")
    for label, ticker, year in cases:
        year_map = index_payload.get(ticker)
        entry = year_map.get(year) if year_map else None
        if entry is None:
            print(f"  {label}: missing cache entry")
            continue
        section, confidence, method, warnings, debug = run_extraction(
            entry["cik"], entry["accession"]
        )
        notes = evaluate_case(label, section, warnings, debug)
        note_text = "; ".join(notes) if notes else "ok"
        print(
            f"  {label}: conf={confidence:.2f} method={method} warnings={len(warnings)} {note_text}"
        )

    print("\nsummary_report:")
    cache_root = get_cache_root()
    filings_root = cache_root / "filings"
    warning_counts: dict[str, int] = {}
    gate_fails = 0
    confidence_bins: dict[str, int] = {}
    worst_cases: list[CacheRecord] = []
    scanned = 0

    if filings_root.exists():
        for cik_dir in filings_root.iterdir():
            if not cik_dir.is_dir():
                continue
            cik = cik_dir.name
            for acc_dir in cik_dir.iterdir():
                if not acc_dir.is_dir():
                    continue
                accession = acc_dir.name
                confidence = 0.0
                method = "missing"
                warn_list: list[str] = []
                debug_gate_failed: Optional[bool] = None
                if args.fast:
                    cached_meta = load_cached_risk_meta(cik, accession)
                    if cached_meta is not None:
                        confidence = cached_meta["confidence"]
                        method = cached_meta["method"]
                        warn_list = cached_meta["warnings"]
                        debug_gate_failed = cached_meta["qualityGateFailed"]
                    else:
                        _section, confidence, method, warnings, debug = run_extraction(
                            cik, accession
                        )
                        warn_list = as_str_list(warnings) or []
                        debug_gate_failed = as_bool(debug.get("qualityGateFailed"))
                else:
                    _section, confidence, method, warnings, debug = run_extraction(cik, accession)
                    warn_list = as_str_list(warnings) or []
                    debug_gate_failed = as_bool(debug.get("qualityGateFailed"))

                for warn in warn_list:
                    warning_counts[warn] = warning_counts.get(warn, 0) + 1
                if debug_gate_failed:
                    gate_fails += 1
                bucket = bucket_confidence(confidence)
                confidence_bins[bucket] = confidence_bins.get(bucket, 0) + 1

                ticker = "unknown"
                year = 0
                mapped = accession_map.get((cik, accession))
                if mapped is not None:
                    ticker, year = mapped

                worst_cases.append(
                    {
                        "cik": cik,
                        "accession": accession,
                        "ticker": ticker,
                        "year": year,
                        "confidence": confidence,
                        "warnings": warn_list,
                        "qualityGateFailed": bool(debug_gate_failed),
                        "method": method,
                    }
                )
                scanned += 1
                if args.limit and scanned >= args.limit:
                    break
            if args.limit and scanned >= args.limit:
                break

    print(f"  filings_scanned: {scanned}")
    print(f"  gate_fails: {gate_fails}")
    for bucket in sorted(confidence_bins.keys()):
        print(f"  confidence_{bucket}: {confidence_bins[bucket]}")

    print("  warnings_by_type:")
    for key in sorted(warning_counts.keys()):
        print(f"    {key}: {warning_counts[key]}")

    worst_cases.sort(key=lambda item: item["confidence"])
    print("  worst_cases:")
    for item in worst_cases[:10]:
        warn_preview = ", ".join(item["warnings"][:4])
        print(
            f"    {item['ticker']} {item['year']} {item['accession']} "
            f"conf={item['confidence']:.2f} gate={item['qualityGateFailed']} "
            f"warnings={warn_preview}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
