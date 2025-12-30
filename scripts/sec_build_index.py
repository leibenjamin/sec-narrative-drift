import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence, cast


SECTION_NAME = "10k_item1a"
LOOKBACK_TARGET_YEARS = 10

ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parent
DATA_DIR = REPO_ROOT / "public" / "data" / "sec_narrative_drift"
FEATURED_CASES_PATH = ROOT_DIR / "featured_cases.json"
TICKER_MAP_PATH = ROOT_DIR / "sample_fixtures" / "company_tickers_exchange.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def normalize_text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if text else None


def load_ticker_map(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = read_json(path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        return {}

    mapping: dict[str, dict[str, Any]] = {}

    if "fields" in payload_dict and "data" in payload_dict:
        fields = as_str_list(payload_dict.get("fields"))
        data = as_list(payload_dict.get("data"))
        if fields is None or data is None:
            return mapping

        for row in data:
            if not isinstance(row, Sequence) or isinstance(row, (str, bytes)):
                continue
            row_seq = cast(Sequence[Any], row)
            limit = min(len(fields), len(row_seq))
            record: dict[str, Any] = {}
            for idx in range(limit):
                record[fields[idx]] = row_seq[idx]
            ticker_value = record.get("ticker")
            if not isinstance(ticker_value, str):
                continue
            ticker = ticker_value.upper().strip()
            if not ticker:
                continue
            mapping[ticker] = record
        return mapping

    for entry in payload_dict.values():
        entry_dict = as_str_dict(entry)
        if entry_dict is None:
            continue
        ticker_value = entry_dict.get("ticker")
        if not isinstance(ticker_value, str):
            continue
        ticker = ticker_value.upper().strip()
        if not ticker:
            continue
        mapping[ticker] = entry_dict
    return mapping


def load_featured_cases(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = read_json(path)
    rows = as_list(payload)
    if rows is None:
        return {}

    cases: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_dict = as_str_dict(row)
        if row_dict is None:
            continue
        ticker = normalize_text(row_dict.get("ticker"))
        title = normalize_text(row_dict.get("title"))
        blurb = normalize_text(row_dict.get("blurb"))
        from_year = row_dict.get("from")
        to_year = row_dict.get("to")
        if not ticker or not title or not blurb:
            continue
        if not isinstance(from_year, int) or not isinstance(to_year, int):
            continue
        tags_raw = row_dict.get("tags")
        tags_list: Optional[list[str]] = None
        if isinstance(tags_raw, list):
            tags: list[str] = []
            valid = True
            for tag in cast(list[object], tags_raw):
                if not isinstance(tag, str):
                    valid = False
                    break
                tags.append(tag)
            if valid:
                tags_list = tags
        cases[ticker.upper()] = {
            "from": from_year,
            "to": to_year,
            "title": title,
            "blurb": blurb,
            **({"tags": tags_list} if tags_list else {}),
        }
    return cases


def load_years_from_metrics(path: Path) -> list[int]:
    if not path.exists():
        return []
    payload = read_json(path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        return []
    raw_years = payload_dict.get("years")
    if not isinstance(raw_years, list):
        return []
    years: list[int] = []
    for item in cast(list[object], raw_years):
        if isinstance(item, int):
            years.append(item)
    return sorted(set(years))


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
    return sorted(set(years))


def load_confidences(path: Path) -> list[float]:
    if not path.exists():
        return []
    payload = read_json(path)
    rows = as_list(payload)
    if rows is None:
        return []
    values: list[float] = []
    for row in rows:
        row_dict = as_str_dict(row)
        if row_dict is None:
            continue
        extraction = row_dict.get("extraction")
        extraction_dict = as_str_dict(extraction)
        if extraction_dict is None:
            continue
        confidence = extraction_dict.get("confidence")
        if isinstance(confidence, (int, float)):
            values.append(float(confidence))
    return values


def compute_quality(coverage_count: int, confidences: list[float]) -> dict[str, Any]:
    if not confidences:
        return {"level": "unknown"}
    sorted_values = sorted(confidences)
    min_conf = sorted_values[0]
    mid = len(sorted_values) // 2
    if len(sorted_values) % 2 == 0:
        median = (sorted_values[mid - 1] + sorted_values[mid]) / 2
    else:
        median = sorted_values[mid]
    if coverage_count >= 9 and min_conf >= 0.80:
        level = "high"
    elif coverage_count >= 7 and min_conf >= 0.70:
        level = "medium"
    else:
        level = "low"
    return {
        "level": level,
        "minConfidence": round(min_conf, 4),
        "medianConfidence": round(median, 4),
        "notes": [],
    }


def compute_metrics_summary(metrics_path: Path) -> tuple[Optional[dict[str, Any]], Optional[dict[str, int]]]:
    if not metrics_path.exists():
        return None, None
    payload = read_json(metrics_path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        return None, None
    raw_years = payload_dict.get("years")
    raw_drift = payload_dict.get("drift_vs_prev")
    if not isinstance(raw_years, list) or not isinstance(raw_drift, list):
        return None, None

    years: list[int] = []
    for item in cast(list[object], raw_years):
        if isinstance(item, int):
            years.append(item)
    drift_values: list[Optional[float]] = []
    for item in cast(list[object], raw_drift):
        if isinstance(item, (int, float)):
            drift_values.append(float(item))
        else:
            drift_values.append(None)

    pairs: list[tuple[int, int, float]] = []
    for index in range(1, len(years)):
        if index >= len(drift_values):
            continue
        value = drift_values[index]
        if value is None:
            continue
        pairs.append((years[index - 1], years[index], value))

    if not pairs:
        return None, None

    peak = pairs[0]
    for pair in pairs[1:]:
        if pair[2] > peak[2]:
            peak = pair
    latest = pairs[-1]

    summary = {
        "peakDrift": {"from": peak[0], "to": peak[1], "value": round(peak[2], 4)},
        "latestDrift": {"from": latest[0], "to": latest[1], "value": round(latest[2], 4)},
    }
    auto_pair = {"from": peak[0], "to": peak[1]}
    return summary, auto_pair


def resolve_company_name(
    ticker: str, meta_name: Optional[str], map_entry: Optional[dict[str, Any]]
) -> str:
    if map_entry is not None:
        title = normalize_text(map_entry.get("title"))
        if title:
            return title
        name = normalize_text(map_entry.get("name"))
        if name:
            return name
    if meta_name:
        return meta_name
    return ticker


def build_index(data_dir: Path, featured_cases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ticker_map = load_ticker_map(TICKER_MAP_PATH)
    companies: list[dict[str, Any]] = []

    for entry in sorted(data_dir.iterdir()):
        if not entry.is_dir():
            continue
        meta_path = entry / "meta.json"
        if not meta_path.exists():
            continue

        meta_payload = read_json(meta_path)
        meta_dict = as_str_dict(meta_payload)
        if meta_dict is None:
            continue
        ticker = normalize_text(meta_dict.get("ticker")) or entry.name.upper()
        ticker = ticker.upper()
        cik = normalize_text(meta_dict.get("cik")) or ""
        meta_name = normalize_text(meta_dict.get("companyName"))
        map_entry = ticker_map.get(ticker)
        company_name = resolve_company_name(ticker, meta_name, map_entry)

        metrics_path = entry / "metrics_10k_item1a.json"
        filings_path = entry / "filings.json"

        years = load_years_from_metrics(metrics_path)
        if not years:
            years = load_years_from_filings(filings_path)
        coverage_count = len(years)
        min_year = min(years) if years else None
        max_year = max(years) if years else None

        confidences = load_confidences(filings_path)
        quality = compute_quality(coverage_count, confidences)

        metrics_summary, auto_pair = compute_metrics_summary(metrics_path)

        row: dict[str, Any] = {
            "ticker": ticker,
            "companyName": company_name,
            "cik": cik,
        }
        if map_entry is not None:
            sic_value = map_entry.get("sic")
            if sic_value is not None:
                row["sic"] = str(sic_value)
            sic_desc = normalize_text(map_entry.get("sicDescription"))
            if sic_desc:
                row["sicDescription"] = sic_desc
            exchange = normalize_text(map_entry.get("exchange"))
            if exchange:
                row["exchange"] = exchange

        if years and min_year is not None and max_year is not None:
            row["coverage"] = {
                "years": years,
                "count": coverage_count,
                "minYear": min_year,
                "maxYear": max_year,
            }
        else:
            row["coverage"] = {"years": [], "count": 0, "minYear": 0, "maxYear": 0}

        row["quality"] = quality

        if metrics_summary is not None:
            row["metricsSummary"] = metrics_summary
        if auto_pair is not None:
            row["autoPair"] = auto_pair

        featured_case = featured_cases.get(ticker)
        if featured_case is not None:
            row["featuredCase"] = featured_case

        companies.append(row)

    payload = {
        "version": 1,
        "generatedAtUtc": utc_now(),
        "section": SECTION_NAME,
        "lookbackTargetYears": LOOKBACK_TARGET_YEARS,
        "companyCount": len(companies),
        "companies": companies,
    }
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build index.json from per-company outputs.")
    parser.add_argument(
        "--data-dir",
        default=str(DATA_DIR),
        help="Path to public/data/sec_narrative_drift.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Optional output path for index.json (default: <data-dir>/index.json).",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        raise SystemExit(f"Data dir not found: {data_dir}")

    featured_cases = load_featured_cases(FEATURED_CASES_PATH)
    payload = build_index(data_dir, featured_cases)

    out_path = Path(args.out) if args.out else data_dir / "index.json"
    write_json(out_path, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
