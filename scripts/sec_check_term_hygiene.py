import argparse
import json
from pathlib import Path
from typing import Any, Optional, cast


ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parent
DEFAULT_DATA_DIR = REPO_ROOT / "public" / "data" / "sec_narrative_drift"


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


def has_repeated_tokens(term: str) -> bool:
    tokens = term.lower().split()
    seen: set[str] = set()
    for token in tokens:
        if not token:
            continue
        if token in seen:
            return True
        seen.add(token)
    return False


def find_duplicate_terms(data_dir: Path) -> list[str]:
    duplicates: list[str] = []
    for entry in sorted(data_dir.iterdir()):
        if not entry.is_dir():
            continue
        shifts_path = entry / "shifts_10k_item1a.json"
        if not shifts_path.exists():
            continue
        payload = read_json(shifts_path)
        payload_dict = as_str_dict(payload)
        if payload_dict is None:
            duplicates.append(f"{entry.name}: shifts.json not an object")
            continue
        year_pairs = as_list(payload_dict.get("yearPairs"))
        if year_pairs is None:
            duplicates.append(f"{entry.name}: shifts.json missing yearPairs")
            continue
        for pair in year_pairs:
            pair_dict = as_str_dict(pair)
            if pair_dict is None:
                continue
            from_year = pair_dict.get("from")
            to_year = pair_dict.get("to")
            year_label = f"{from_year}-{to_year}"
            for key in ("topRisers", "topFallers", "topRisersAlt", "topFallersAlt"):
                items = as_list(pair_dict.get(key))
                if items is None:
                    continue
                for item in items:
                    item_dict = as_str_dict(item)
                    if item_dict is None:
                        continue
                    term = item_dict.get("term")
                    if not isinstance(term, str):
                        continue
                    if has_repeated_tokens(term):
                        duplicates.append(f"{entry.name} {year_label} {key}: {term}")
    return duplicates


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fail if duplicate-token terms appear in shifts JSON."
    )
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help="Path to public/data/sec_narrative_drift.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        raise SystemExit(f"Data dir not found: {data_dir}")

    duplicates = find_duplicate_terms(data_dir)
    if duplicates:
        print("Duplicate-token terms found:")
        for item in duplicates:
            print(f"- {item}")
        return 1

    print("OK: no duplicate-token terms found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
