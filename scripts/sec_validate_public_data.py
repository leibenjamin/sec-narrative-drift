import argparse
import json
from pathlib import Path
from typing import Any, Optional, cast


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
        if float(confidence) < 0.55:
            warnings.append("meta extraction low confidence")
    else:
        warnings.append("meta extraction missing confidence")
    length_chars = extraction_dict.get("lengthChars")
    if isinstance(length_chars, int):
        if length_chars < 8000:
            warnings.append("meta extraction short length")


def summarize_ticker(path: Path) -> dict[str, Any]:
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

    summaries: list[dict[str, Any]] = []
    for entry in sorted(data_dir.iterdir()):
        if not entry.is_dir():
            continue
        summaries.append(summarize_ticker(entry))

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
