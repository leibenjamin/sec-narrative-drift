import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, TypedDict, cast

from sec_cache import (
    EXTRACTOR_VERSION,
    NORMALIZER_VERSION,
    atomic_write_json,
    cache_size_report,
    cache_usage_path,
    filing_meta_path,
    filing_text_path,
    get_cache_root,
    load_gz_text,
    load_json,
    risk_meta_path,
    risk_text_path,
    ticker_year_index_path,
    compute_sha256_text,
)


class TickerYearEntry(TypedDict):
    cik: str
    accession: str
    formType: str
    filingDate: str


class TopFiling(TypedDict):
    cik: str
    accession: str
    bytes: int


def as_str_dict(value: Any) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    out: dict[str, Any] = {}
    for key, item in cast(dict[object, object], value).items():
        if not isinstance(key, str):
            return None
        out[key] = item
    return out


def get_str(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    return None


def get_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def parse_ticker_year_index(raw: Any) -> dict[str, dict[str, TickerYearEntry]]:
    payload = as_str_dict(raw)
    if payload is None:
        return {}
    output: dict[str, dict[str, TickerYearEntry]] = {}
    for ticker_key, value in payload.items():
        year_map = as_str_dict(value)
        if year_map is None:
            continue
        parsed_years: dict[str, TickerYearEntry] = {}
        for year_key, entry_value in year_map.items():
            entry = as_str_dict(entry_value)
            if entry is None:
                continue
            cik = get_str(entry.get("cik"))
            accession = get_str(entry.get("accession"))
            form_type = get_str(entry.get("formType"))
            filing_date = get_str(entry.get("filingDate"))
            if cik is None or accession is None or form_type is None or filing_date is None:
                continue
            parsed_years[year_key] = {
                "cik": cik,
                "accession": accession,
                "formType": form_type,
                "filingDate": filing_date,
            }
        if parsed_years:
            output[ticker_key] = parsed_years
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate local SEC cache contents.")
    parser.add_argument(
        "--hash-sample",
        type=int,
        default=5,
        help="Number of ticker-years to verify sha256 hashes for (default: 5).",
    )
    parser.add_argument(
        "--hash-all",
        action="store_true",
        help="Verify sha256 hashes for all cached filings.",
    )
    return parser


def _dir_size(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    cache_root = get_cache_root()
    index_payload = parse_ticker_year_index(load_json(ticker_year_index_path()))

    issues: list[str] = []
    hash_checks = args.hash_sample if not args.hash_all else 10**9
    checked = 0

    for ticker in sorted(index_payload.keys()):
        year_map = index_payload[ticker]
        for year_key in sorted(year_map.keys()):
            entry = year_map[year_key]
            cik = entry["cik"]
            accession = entry["accession"]
            form_type = entry["formType"]

            filing_meta = load_json(filing_meta_path(cik, accession))
            filing_meta_dict: Optional[dict[str, Any]] = None
            filing_text = filing_text_path(cik, accession)
            if not filing_text.exists():
                issues.append(f"{ticker} {year_key}: missing filing.txt.gz")
            if not isinstance(filing_meta, dict):
                issues.append(f"{ticker} {year_key}: missing filing_meta.json")
            else:
                filing_meta_dict = cast(dict[str, Any], filing_meta)
                if get_str(filing_meta_dict.get("normalizerVersion")) != NORMALIZER_VERSION:
                    issues.append(f"{ticker} {year_key}: normalizer version mismatch")
                if get_str(filing_meta_dict.get("extractorVersion")) != EXTRACTOR_VERSION:
                    issues.append(f"{ticker} {year_key}: extractor version mismatch (filing)")

            risk_meta = load_json(risk_meta_path(cik, accession))
            risk_meta_dict: Optional[dict[str, Any]] = None
            risk_text = risk_text_path(cik, accession, form_type)
            if not risk_text.exists():
                issues.append(f"{ticker} {year_key}: missing risk text")
            if not isinstance(risk_meta, dict):
                issues.append(f"{ticker} {year_key}: missing rf_meta.json")
            else:
                risk_meta_dict = cast(dict[str, Any], risk_meta)
                if get_str(risk_meta_dict.get("extractorVersion")) != EXTRACTOR_VERSION:
                    issues.append(f"{ticker} {year_key}: extractor version mismatch (risk)")
                if get_str(risk_meta_dict.get("normalizerVersion")) != NORMALIZER_VERSION:
                    issues.append(f"{ticker} {year_key}: normalizer version mismatch (risk)")

            if checked < hash_checks and filing_meta_dict is not None and filing_text.exists():
                text = load_gz_text(filing_text)
                expected = get_str(filing_meta_dict.get("sha256FilingText"))
                if isinstance(text, str) and isinstance(expected, str) and expected:
                    actual = compute_sha256_text(text)
                    if actual != expected:
                        issues.append(f"{ticker} {year_key}: filing text hash mismatch")
                checked += 1

            if checked < hash_checks and risk_meta_dict is not None and risk_text.exists():
                text = load_gz_text(risk_text)
                expected = get_str(risk_meta_dict.get("sha256RiskText"))
                if isinstance(text, str) and isinstance(expected, str) and expected:
                    actual = compute_sha256_text(text)
                    if actual != expected:
                        issues.append(f"{ticker} {year_key}: risk text hash mismatch")
                checked += 1

    size_report = cache_size_report()
    total_bytes_value = get_int(size_report.get("totalBytes"))
    total_bytes = total_bytes_value if total_bytes_value is not None else 0
    total_gb = total_bytes / (1024 * 1024 * 1024)

    filings_root = cache_root / "filings"
    top_filings: list[TopFiling] = []
    if filings_root.exists():
        for cik_dir in filings_root.iterdir():
            if not cik_dir.is_dir():
                continue
            for acc_dir in cik_dir.iterdir():
                if not acc_dir.is_dir():
                    continue
                size = _dir_size(acc_dir)
                top_filings.append(
                    {"cik": cik_dir.name, "accession": acc_dir.name, "bytes": size}
                )
    top_filings.sort(key=lambda item: item["bytes"], reverse=True)
    top_filings = top_filings[:10]

    per_cik_value = size_report.get("perCik")
    per_cik: dict[str, Any] = {}
    if isinstance(per_cik_value, dict):
        for key, value in cast(dict[object, object], per_cik_value).items():
            if isinstance(key, str):
                per_cik[key] = value
    report_payload: dict[str, Any] = {
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        ),
        "totalBytes": total_bytes,
        "totalGB": round(total_gb, 4),
        "perCik": per_cik,
        "topFilings": top_filings,
        "issues": issues,
    }
    atomic_write_json(cache_usage_path(), report_payload)

    print(f"cache size: {total_gb:.2f} GB")
    if top_filings:
        print("top cached filings:")
        for entry in top_filings:
            mb = entry["bytes"] / (1024 * 1024)
            print(f"  {entry['cik']} {entry['accession']} - {mb:.2f} MB")
    if issues:
        print(f"issues found: {len(issues)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
