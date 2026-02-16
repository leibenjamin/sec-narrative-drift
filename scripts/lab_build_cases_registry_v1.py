from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, cast

SCRIPT_VERSION = "lab_build_cases_registry_v1.py@v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"
REGISTRY_PATH = LAB_ROOT / "lab_cases_v1.json"
REPORTS_ROOT = REPO_ROOT / "reports"
BUILD_REPORT_PATH = REPORTS_ROOT / "lab_cases_registry_build.md"

VALID_LENSES = {"raw", "stage1_clean", "deboilerplated", "structure_aware"}
VALID_SOURCES = {"edgar", "sraf_nd"}
DEFAULT_TICKERS = ["NVDA", "KO", "WM", "GE"]

DETECTOR_ORDER = [
    "det_logodds_terms_v1",
    "det_jsd_ngrams_v1",
    "det_minhash_boilerplate_v1",
    "det_winnowing_fingerprint_v1",
    "det_structure_artifacts_v1",
    "det_rbo_agreement_v1",
    "det_llm_delta_brief_v1",
    "det_llm_excerpt_picker_v1",
]
LENS_ORDER = ["raw", "deboilerplated", "stage1_clean", "structure_aware"]


@dataclass(frozen=True)
class LabOutputRecord:
    abs_path: Path
    rel_path: str
    ticker: str
    section: str
    year_from: int
    year_to: int
    detector_id: str
    cleaning_lens: str
    source_id: str


@dataclass(frozen=True)
class InputRecord:
    abs_path: Path
    rel_path: str
    ticker: str
    section: str
    year_from: int
    year_to: int
    source_id: str
    lens: str


@dataclass(frozen=True)
class OutputLink:
    detector_id: str
    cleaning_lens: str
    source_id: str
    filename: str
    abs_path: Path


@dataclass(frozen=True)
class CaseKey:
    ticker: str
    section: str
    year_from: int
    year_to: int


def now_utc_iso() -> str:
    return (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def as_dict(value: Any) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    output: dict[str, Any] = {}
    for key, item in cast(dict[Any, Any], value).items():
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


def normalize_rel_path(value: str) -> Optional[str]:
    normalized = value.replace("\\", "/").strip()
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
        if part == "" or part == ".":
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


def get_git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return "unknown"
    if result.returncode != 0:
        return "unknown"
    output = result.stdout.strip()
    if output:
        return output
    return "unknown"


def parse_tickers(raw_items: list[str]) -> list[str]:
    parsed: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        for piece in item.split(","):
            candidate = piece.strip().upper()
            if not candidate:
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            parsed.append(candidate)
    return parsed


def parse_lab_output(path: Path) -> Optional[LabOutputRecord]:
    payload = read_json(path)
    root = as_dict(payload)
    if root is None:
        return None
    if as_str(root.get("lab_schema_version")) != "1.0":
        return None

    detector_id = as_str(root.get("detector_id"))
    cleaning_lens = as_str(root.get("cleaning_lens"))
    source_id = as_str(root.get("source_id"))
    ticker = as_str(root.get("ticker"))
    section = as_str(root.get("section"))
    year_from = as_int(root.get("year_from"))
    year_to = as_int(root.get("year_to"))

    if (
        detector_id is None
        or cleaning_lens is None
        or source_id is None
        or ticker is None
        or section is None
        or year_from is None
        or year_to is None
    ):
        return None
    if cleaning_lens not in VALID_LENSES:
        return None
    if source_id not in VALID_SOURCES:
        return None

    yf = min(year_from, year_to)
    yt = max(year_from, year_to)

    rel_path = path.relative_to(LAB_ROOT).as_posix()
    return LabOutputRecord(
        abs_path=path,
        rel_path=rel_path,
        ticker=ticker.upper(),
        section=section,
        year_from=yf,
        year_to=yt,
        detector_id=detector_id,
        cleaning_lens=cleaning_lens,
        source_id=source_id,
    )


def parse_input_record(path: Path) -> Optional[InputRecord]:
    rel_path = path.relative_to(LAB_ROOT).as_posix()
    if not rel_path.startswith("llm_inputs/"):
        return None

    payload = read_json(path)
    root = as_dict(payload)
    if root is None:
        return None

    case = as_dict(root.get("case"))
    lens = as_dict(root.get("lens"))
    if case is None or lens is None:
        return None

    ticker = as_str(case.get("ticker"))
    section = as_str(case.get("section"))
    source_id = as_str(case.get("source_id")) or "edgar"
    lens_name = as_str(lens.get("name"))
    year_from = as_int(case.get("year_from"))
    year_to = as_int(case.get("year_to"))
    if (
        ticker is None
        or section is None
        or lens_name is None
        or year_from is None
        or year_to is None
    ):
        return None

    return InputRecord(
        abs_path=path,
        rel_path=rel_path,
        ticker=ticker.upper(),
        section=section,
        year_from=min(year_from, year_to),
        year_to=max(year_from, year_to),
        source_id=source_id,
        lens=lens_name,
    )


def source_priority(rel_path: str, ticker: str) -> tuple[int, str]:
    if rel_path.startswith(f"{ticker}/outputs/"):
        return (0, rel_path)
    if rel_path.startswith(f"{ticker}/"):
        return (1, rel_path)
    if rel_path.startswith("llm_outputs/"):
        return (2, rel_path)
    return (3, rel_path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def sync_file_deterministic(source: Path, destination: Path) -> bool:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        src_hash = sha256_file(source)
        dst_hash = sha256_file(destination)
        if src_hash == dst_hash:
            return False
    shutil.copy2(source, destination)
    return True


def build_candidate_pairs(
    year_min: int, year_max: int, adjacent_only: bool, include_most_recent_always: bool
) -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []
    if adjacent_only:
        for year in range(year_min, year_max):
            pairs.append((year, year + 1))
    else:
        for left in range(year_min, year_max + 1):
            for right in range(left + 1, year_max + 1):
                pairs.append((left, right))

    if include_most_recent_always:
        most_recent = (2024, 2025)
        if year_min <= 2024 and year_max >= 2025 and most_recent not in pairs:
            pairs.append(most_recent)

    pairs.sort(key=lambda item: (item[0], item[1]))
    return pairs


def load_hero_pairs() -> dict[str, dict[tuple[int, int], list[str]]]:
    hero_path = LAB_ROOT / "lab_showcase_hero_pairs_v2.json"
    output: dict[str, dict[tuple[int, int], list[str]]] = {}
    if not hero_path.exists():
        return output

    payload = read_json(hero_path)
    root = as_dict(payload)
    if root is None:
        return output
    hero_map = as_dict(root.get("hero_pairs_per_ticker"))
    if hero_map is None:
        return output

    for ticker, raw_pairs in hero_map.items():
        ticker_upper = ticker.upper()
        rows = as_list(raw_pairs)
        if rows is None:
            continue
        pair_map: dict[tuple[int, int], list[str]] = {}
        for row in rows:
            row_dict = as_dict(row)
            if row_dict is None:
                continue
            year_from = as_int(row_dict.get("year_from"))
            year_to = as_int(row_dict.get("year_to"))
            tags_any = as_list(row_dict.get("tags"))
            if year_from is None or year_to is None:
                continue
            tags: list[str] = []
            if tags_any is not None:
                for entry in tags_any:
                    if isinstance(entry, str):
                        cleaned = entry.strip()
                        if cleaned and cleaned not in tags:
                            tags.append(cleaned)
            pair_key = (min(year_from, year_to), max(year_from, year_to))
            pair_map[pair_key] = tags
        output[ticker_upper] = pair_map
    return output


def get_detector_rank(detector_id: str) -> tuple[int, str]:
    if detector_id in DETECTOR_ORDER:
        return (DETECTOR_ORDER.index(detector_id), detector_id)
    return (999, detector_id)


def get_lens_rank(lens: str) -> tuple[int, str]:
    if lens in LENS_ORDER:
        return (LENS_ORDER.index(lens), lens)
    return (999, lens)


def build_tags(hero_tags: list[str], is_featured: bool) -> Optional[list[str]]:
    tags: list[str] = []
    if is_featured:
        tags.append("recommended")
    for tag in hero_tags:
        if tag == "recommended":
            continue
        if tag not in tags:
            tags.append(tag)
    if tags:
        return tags
    return None


def build_why_interesting(tags: Optional[list[str]]) -> str:
    if tags is None:
        return "Adjacent pair with precomputed lab outputs."
    if "most_recent" in tags:
        return "Most recent adjacent pair with precomputed lab outputs."
    if "meaningful" in tags:
        return "Hero pair with stronger drift and term-signal proxy scores."
    if "structure" in tags:
        return "Hero pair selected for structure-shift proxy signals."
    if "boilerplate" in tags:
        return "Hero pair selected for boilerplate-reuse proxy signal."
    return "Featured adjacent pair from the showcase hero roster."


def normalize_input_url(path_value: str) -> Optional[str]:
    normalized = normalize_rel_path(path_value)
    if normalized is None:
        return None

    if normalized.startswith("data/"):
        return normalized
    if normalized.startswith("public/"):
        return normalized[len("public/") :]
    if normalized.startswith("bundles/"):
        basename = normalized.split("/")[-1]
        if not basename:
            return None
        return f"data/sec_narrative_drift_lab/llm_inputs/{basename}"
    if normalized.startswith("inputs/"):
        basename = normalized.split("/")[-1]
        if not basename:
            return None
        return f"data/sec_narrative_drift_lab/llm_inputs/{basename}"
    if "/" not in normalized:
        return f"data/sec_narrative_drift_lab/llm_inputs/{normalized}"
    return f"data/sec_narrative_drift_lab/{normalized}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build deterministic lab_cases_v1 registry.")
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=DEFAULT_TICKERS,
        help="Tickers to include (space-separated and/or comma-separated).",
    )
    parser.add_argument("--year-min", type=int, default=2019)
    parser.add_argument("--year-max", type=int, default=2025)
    parser.add_argument(
        "--include-most-recent-always",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Always include 2024-2025 pair if files exist.",
    )
    parser.add_argument(
        "--adjacent-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include only adjacent year pairs.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    tickers = parse_tickers(args.tickers)
    if not tickers:
        raise SystemExit("No tickers provided.")
    if args.year_min > args.year_max:
        raise SystemExit("--year-min must be <= --year-max.")

    candidate_pairs = build_candidate_pairs(
        year_min=args.year_min,
        year_max=args.year_max,
        adjacent_only=bool(args.adjacent_only),
        include_most_recent_always=bool(args.include_most_recent_always),
    )
    hero_pairs = load_hero_pairs()

    all_inputs: list[InputRecord] = []
    output_candidates: dict[
        tuple[str, str, int, int, str, str, str], list[LabOutputRecord]
    ] = {}

    for path in sorted(LAB_ROOT.rglob("*.json"), key=lambda item: str(item).lower()):
        rel_str = path.relative_to(LAB_ROOT).as_posix()
        if rel_str == "lab_cases_v1.json":
            continue
        try:
            parsed_input = parse_input_record(path)
        except Exception:
            parsed_input = None
        if parsed_input is not None:
            all_inputs.append(parsed_input)

        try:
            parsed_output = parse_lab_output(path)
        except Exception:
            parsed_output = None
        if parsed_output is None:
            continue
        if parsed_output.ticker not in tickers:
            continue
        if parsed_output.year_from < args.year_min or parsed_output.year_to > args.year_max:
            continue
        if args.adjacent_only and parsed_output.year_to != parsed_output.year_from + 1:
            continue
        key = (
            parsed_output.ticker,
            parsed_output.section,
            parsed_output.year_from,
            parsed_output.year_to,
            parsed_output.detector_id,
            parsed_output.cleaning_lens,
            parsed_output.source_id,
        )
        bucket = output_candidates.setdefault(key, [])
        bucket.append(parsed_output)

    normalized_links_by_case: dict[CaseKey, list[OutputLink]] = {}
    normalized_files: list[str] = []
    copied_count = 0
    synced_count = 0

    for key in sorted(output_candidates.keys()):
        candidates = output_candidates[key]
        if not candidates:
            continue
        selected = sorted(
            candidates, key=lambda item: source_priority(item.rel_path, item.ticker)
        )[0]

        ticker = selected.ticker
        target_rel = f"{ticker}/outputs/{selected.detector_id}/{selected.abs_path.name}"
        target_abs = LAB_ROOT / target_rel
        filename = f"outputs/{selected.detector_id}/{selected.abs_path.name}"

        same_target = False
        try:
            same_target = selected.abs_path.resolve() == target_abs.resolve()
        except Exception:
            same_target = selected.abs_path == target_abs

        if not same_target:
            did_copy = sync_file_deterministic(selected.abs_path, target_abs)
            if did_copy:
                copied_count += 1
            else:
                synced_count += 1
            normalized_files.append(f"{selected.rel_path} -> {target_rel}")

        safe_filename = normalize_rel_path(filename)
        if safe_filename is None:
            raise SystemExit(f"Unsafe ticker-relative filename generated: {filename}")

        case_key = CaseKey(
            ticker=selected.ticker,
            section=selected.section,
            year_from=selected.year_from,
            year_to=selected.year_to,
        )
        case_bucket = normalized_links_by_case.setdefault(case_key, [])
        case_bucket.append(
            OutputLink(
                detector_id=selected.detector_id,
                cleaning_lens=selected.cleaning_lens,
                source_id=selected.source_id,
                filename=safe_filename,
                abs_path=target_abs,
            )
        )

    cases_payload: list[dict[str, Any]] = []
    missing_pairs_by_ticker: dict[str, list[tuple[int, int]]] = {}
    featured_pairs_by_ticker: dict[str, list[tuple[int, int]]] = {}
    included_pairs_by_ticker: dict[str, list[tuple[int, int]]] = {}
    output_count_by_ticker: dict[str, int] = {}

    for ticker in tickers:
        missing_pairs_by_ticker[ticker] = []
        featured_pairs_by_ticker[ticker] = []
        included_pairs_by_ticker[ticker] = []
        output_count_by_ticker[ticker] = 0

        for year_from, year_to in candidate_pairs:
            case_key = CaseKey(
                ticker=ticker,
                section="10k_item1a",
                year_from=year_from,
                year_to=year_to,
            )
            links = normalized_links_by_case.get(case_key, [])
            if not links:
                missing_pairs_by_ticker[ticker].append((year_from, year_to))
                continue

            sorted_links = sorted(
                links,
                key=lambda item: (
                    get_detector_rank(item.detector_id),
                    get_lens_rank(item.cleaning_lens),
                    item.source_id,
                    item.filename,
                ),
            )

            expected_detectors: list[str] = []
            for link in sorted_links:
                if link.detector_id not in expected_detectors:
                    expected_detectors.append(link.detector_id)

            hero_tags = hero_pairs.get(ticker, {}).get((year_from, year_to), [])
            is_featured = len(hero_tags) > 0
            tags = build_tags(hero_tags, is_featured)
            if is_featured:
                featured_pairs_by_ticker[ticker].append((year_from, year_to))

            why_interesting = build_why_interesting(tags)
            case_payload: dict[str, Any] = {
                "ticker": ticker,
                "year_from": year_from,
                "year_to": year_to,
                "section": "10k_item1a",
                "why_interesting": why_interesting,
                "expected_detectors": expected_detectors,
                "outputs": [
                    {
                        "detector_id": link.detector_id,
                        "cleaning_lens": link.cleaning_lens,
                        "source_id": link.source_id,
                        "filename": link.filename,
                    }
                    for link in sorted_links
                ],
            }
            if tags is not None:
                case_payload["tags"] = tags

            cases_payload.append(case_payload)
            included_pairs_by_ticker[ticker].append((year_from, year_to))
            output_count_by_ticker[ticker] += len(sorted_links)

    cases_payload.sort(
        key=lambda item: (
            tickers.index(item["ticker"]) if item["ticker"] in tickers else 999,
            item["section"],
            item["year_from"],
            item["year_to"],
        )
    )

    build_utc = now_utc_iso()
    provenance_inputs = {
        "tickers": ",".join(tickers),
        "year_min": str(args.year_min),
        "year_max": str(args.year_max),
        "adjacent_only": str(bool(args.adjacent_only)).lower(),
        "include_most_recent_always": str(bool(args.include_most_recent_always)).lower(),
    }
    registry_payload = {
        "version": "1.0",
        "updated_at": build_utc,
        "notes": [
            "Generated deterministically from scanned lab outputs.",
            "Output links are canonicalized to ticker-local outputs/<detector_id>/<filename> paths.",
        ],
        "cases": cases_payload,
        "provenance": {
            "build_utc": build_utc,
            "git_commit": get_git_commit(),
            "script_version": SCRIPT_VERSION,
            "inputs": provenance_inputs,
            "notes": [
                "Selected outputs are synced into ticker-local outputs/<detector_id>/ paths when needed."
            ],
        },
    }
    write_json(REGISTRY_PATH, registry_payload)

    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Lab Cases Registry Build")
    lines.append("")
    lines.append(f"- build_utc: {build_utc}")
    lines.append(f"- script: {SCRIPT_VERSION}")
    lines.append(f"- tickers: {', '.join(tickers)}")
    lines.append(
        f"- options: year_min={args.year_min}, year_max={args.year_max}, "
        + f"adjacent_only={bool(args.adjacent_only)}, include_most_recent_always={bool(args.include_most_recent_always)}"
    )
    lines.append(f"- cases_written: {len(cases_payload)}")
    lines.append(f"- normalized_output_paths: {len(normalized_files)}")
    lines.append(f"- copied_new_files: {copied_count}")
    lines.append(f"- already_synced_files: {synced_count}")
    lines.append(f"- llm_inputs_detected: {len(all_inputs)}")
    lines.append("")

    lines.append("## Counts By Ticker")
    for ticker in tickers:
        included = len(included_pairs_by_ticker[ticker])
        featured = len(featured_pairs_by_ticker[ticker])
        outputs = output_count_by_ticker[ticker]
        missing = len(missing_pairs_by_ticker[ticker])
        lines.append(
            f"- {ticker}: pairs_included={included}, featured_pairs={featured}, outputs={outputs}, missing_pairs={missing}"
        )
    lines.append("")

    lines.append("## Missing Pairs (Required Files Absent)")
    for ticker in tickers:
        missing_pairs = missing_pairs_by_ticker[ticker]
        if not missing_pairs:
            lines.append(f"- {ticker}: none")
            continue
        rendered = ", ".join(f"{left}-{right}" for left, right in missing_pairs)
        lines.append(f"- {ticker}: {rendered}")
    lines.append("")

    cases_by_ticker: dict[str, list[dict[str, Any]]] = {}
    for case in cases_payload:
        ticker = str(case["ticker"])
        bucket = cases_by_ticker.setdefault(ticker, [])
        bucket.append(case)

    lines.append("## Detectors Per Case")
    for ticker in tickers:
        ticker_cases = cases_by_ticker.get(ticker, [])
        if not ticker_cases:
            lines.append(f"- {ticker}: none")
            continue
        for case in ticker_cases:
            year_from = int(case["year_from"])
            year_to = int(case["year_to"])
            outputs_any = as_list(case.get("outputs")) or []
            present_detectors: list[str] = []
            for output_any in outputs_any:
                output = as_dict(output_any)
                if output is None:
                    continue
                detector_id = as_str(output.get("detector_id"))
                if detector_id is None:
                    continue
                if detector_id not in present_detectors:
                    present_detectors.append(detector_id)
            if present_detectors:
                lines.append(f"- {ticker} {year_from}-{year_to}: {', '.join(present_detectors)}")
            else:
                lines.append(f"- {ticker} {year_from}-{year_to}: none")
    lines.append("")

    lines.append("## Missing Outputs By Case (vs Detector Roster)")
    for ticker in tickers:
        ticker_cases = cases_by_ticker.get(ticker, [])
        if not ticker_cases:
            lines.append(f"- {ticker}: no included cases")
            continue
        for case in ticker_cases:
            year_from = int(case["year_from"])
            year_to = int(case["year_to"])
            outputs_any = as_list(case.get("outputs")) or []
            present_detectors: list[str] = []
            for output_any in outputs_any:
                output = as_dict(output_any)
                if output is None:
                    continue
                detector_id = as_str(output.get("detector_id"))
                if detector_id is None:
                    continue
                if detector_id not in present_detectors:
                    present_detectors.append(detector_id)
            missing_detectors = [det for det in DETECTOR_ORDER if det not in present_detectors]
            if missing_detectors:
                lines.append(
                    f"- {ticker} {year_from}-{year_to}: missing {', '.join(missing_detectors)}"
                )
            else:
                lines.append(f"- {ticker} {year_from}-{year_to}: none")
    lines.append("")

    lines.append("## UI Fetch Samples")
    lines.append("- Registry URL: `data/sec_narrative_drift_lab/lab_cases_v1.json`")

    for ticker in tickers:
        lines.append("")
        lines.append(f"### {ticker}")
        ticker_cases = cases_by_ticker.get(ticker, [])
        if not ticker_cases:
            lines.append("- No included cases for this ticker.")
            continue

        sample_cases = ticker_cases[:2]
        for case in sample_cases:
            year_from = int(case["year_from"])
            year_to = int(case["year_to"])
            lines.append(f"- Case `{year_from}-{year_to}`")
            outputs_any = as_list(case.get("outputs")) or []
            if not outputs_any:
                lines.append("  - No output links in this case.")
                continue
            first_output = as_dict(outputs_any[0])
            if first_output is None:
                lines.append("  - First output link is malformed.")
                continue
            filename = as_str(first_output.get("filename"))
            if filename is None:
                lines.append("  - First output filename missing.")
                continue

            output_url = f"data/sec_narrative_drift_lab/{ticker}/{filename}"
            lines.append(f"  - Lab output URL: `{output_url}`")
            output_abs = LAB_ROOT / ticker / filename
            if output_abs.exists():
                try:
                    output_payload = read_json(output_abs)
                    output_root = as_dict(output_payload)
                except Exception:
                    output_root = None
                if output_root is not None:
                    provenance = as_dict(output_root.get("provenance")) or {}
                    input_file = as_str(provenance.get("input_file"))
                    if input_file:
                        input_url = normalize_input_url(input_file)
                        if input_url is not None:
                            lines.append(f"  - Input URL from provenance.input_file: `{input_url}`")

    if normalized_files:
        lines.append("")
        lines.append("## Output Path Normalization")
        for item in sorted(normalized_files):
            lines.append(f"- `{item}`")

    BUILD_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(
        "Lab registry build complete: "
        + f"cases={len(cases_payload)} "
        + f"registry={to_repo_rel(REGISTRY_PATH)} "
        + f"report={to_repo_rel(BUILD_REPORT_PATH)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
