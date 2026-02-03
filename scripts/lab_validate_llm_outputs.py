from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import sys

SCRIPT_VERSION = "lab_validate_llm_outputs.py@v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUTS_DIR = (
    REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab" / "llm_outputs"
)

DEFAULT_REQUIRED_FIELDS = [
    "lab_schema_version",
    "detector_id",
    "cleaning_lens",
    "source_id",
    "ticker",
    "section",
    "year_from",
    "year_to",
    "artifacts",
    "evidence",
    "metrics",
    "provenance",
]

sys.path.append(str(Path(__file__).resolve().parent))
from lab_llm_precompute_utils import (  # type: ignore
    BundlePaths,
    InputIndexEntry,
    as_list,
    as_str_dict,
    get_int,
    get_str,
    load_input_index,
    read_json,
    resolve_bundle_paths,
)


@dataclass(frozen=True)
class FocuspackMeta:
    selected_prev: list[int]
    selected_curr: list[int]
    full_prev_count: Optional[int]
    full_curr_count: Optional[int]


@dataclass(frozen=True)
class ValidationIssue:
    path: Path
    reasons: list[str]


@dataclass(frozen=True)
class ParsedFilename:
    detector_id: str
    year_from: int
    year_to: int
    lens_key: str
    section: str


def load_required_fields(prompt_path: Optional[Path]) -> list[str]:
    if prompt_path is None or not prompt_path.exists():
        return list(DEFAULT_REQUIRED_FIELDS)
    lines = prompt_path.read_text(encoding="utf-8", errors="replace").splitlines()
    for idx, line in enumerate(lines):
        if "Lab detector envelope" not in line:
            continue
        for j in range(idx + 1, len(lines)):
            candidate = lines[j].strip()
            if not candidate:
                continue
            fields: list[str] = []
            for part in candidate.split(","):
                cleaned = part.strip().rstrip(".")
                if cleaned:
                    fields.append(cleaned)
            if fields:
                return fields
            break
    return list(DEFAULT_REQUIRED_FIELDS)


def parse_output_filename(name: str, section: str) -> Optional[ParsedFilename]:
    marker = f"_{section}_"
    if not name.startswith("lab_"):
        return None
    if marker not in name:
        return None
    prefix, rest = name.split(marker, 1)
    detector_id = prefix[len("lab_") :]
    rest_parts = rest.split("_")
    if len(rest_parts) < 3:
        return None
    year_from = None
    year_to = None
    if rest_parts[0].isdigit():
        year_from = int(rest_parts[0])
    if rest_parts[1].isdigit():
        year_to = int(rest_parts[1])
    if year_from is None or year_to is None:
        return None
    lens_key = "_".join(rest_parts[2:])
    if not lens_key:
        return None
    return ParsedFilename(
        detector_id=detector_id,
        year_from=year_from,
        year_to=year_to,
        lens_key=lens_key,
        section=section,
    )


def load_focuspack_meta(path: Path) -> Optional[FocuspackMeta]:
    try:
        payload = read_json(path)
    except json.JSONDecodeError:
        return None
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        return None
    meta_raw = as_str_dict(payload_dict.get("focuspack_meta"))
    if meta_raw is None:
        return None
    selected_prev_raw = as_list(meta_raw.get("selected_prev_indices"))
    selected_curr_raw = as_list(meta_raw.get("selected_curr_indices"))
    if selected_prev_raw is None or selected_curr_raw is None:
        return None
    selected_prev: list[int] = []
    selected_curr: list[int] = []
    for value in selected_prev_raw:
        if isinstance(value, int) and not isinstance(value, bool):
            selected_prev.append(value)
        else:
            return None
    for value in selected_curr_raw:
        if isinstance(value, int) and not isinstance(value, bool):
            selected_curr.append(value)
        else:
            return None
    full_prev_count = get_int(meta_raw.get("full_prev_count"))
    full_curr_count = get_int(meta_raw.get("full_curr_count"))
    return FocuspackMeta(
        selected_prev=selected_prev,
        selected_curr=selected_curr,
        full_prev_count=full_prev_count,
        full_curr_count=full_curr_count,
    )


def load_full_counts(path: Path) -> Optional[tuple[int, int]]:
    try:
        payload = read_json(path)
    except json.JSONDecodeError:
        return None
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        return None
    texts = as_str_dict(payload_dict.get("texts"))
    if texts is None:
        return None
    prev_paras = as_list(texts.get("prev_paragraphs"))
    curr_paras = as_list(texts.get("curr_paragraphs"))
    if prev_paras is None or curr_paras is None:
        return None
    return (len(prev_paras), len(curr_paras))


def get_input_entry(
    index_map: dict[tuple[str, int, int, str, str], InputIndexEntry],
    ticker: str,
    year_from: int,
    year_to: int,
    section: str,
    lens: str,
) -> Optional[InputIndexEntry]:
    return index_map.get((ticker.upper(), year_from, year_to, section, lens))


def validate_outputs(
    outputs_dir: Path,
    bundle_paths: BundlePaths,
    required_fields: list[str],
) -> list[ValidationIssue]:
    if not outputs_dir.exists():
        return [ValidationIssue(outputs_dir, ["outputs directory not found"])]

    focus_index = load_input_index(bundle_paths.focus_index, bundle_paths.bundle_root)
    full_index = load_input_index(bundle_paths.full_index, bundle_paths.bundle_root)

    focus_meta_cache: dict[Path, Optional[FocuspackMeta]] = {}
    full_counts_cache: dict[Path, Optional[tuple[int, int]]] = {}

    issues: list[ValidationIssue] = []

    output_files = sorted(outputs_dir.rglob("*.json"))
    for path in output_files:
        reasons: list[str] = []
        try:
            payload = read_json(path)
        except json.JSONDecodeError as exc:
            issues.append(ValidationIssue(path, [f"invalid JSON: {exc}"]))
            continue
        payload_dict = as_str_dict(payload)
        if payload_dict is None:
            issues.append(ValidationIssue(path, ["JSON root is not an object"]))
            continue

        for field in required_fields:
            if field not in payload_dict:
                reasons.append(f"missing field: {field}")

        section = get_str(payload_dict.get("section")) or "10k_item1a"
        parsed = parse_output_filename(path.stem, section)
        if parsed is None and section != "10k_item1a":
            parsed = parse_output_filename(path.stem, "10k_item1a")
        if parsed is None:
            reasons.append("filename does not match expected pattern")
            issues.append(ValidationIssue(path, reasons))
            continue

        detector_folder = path.parent.parent.name
        ticker_folder = path.parent.name
        if detector_folder and detector_folder != parsed.detector_id:
            reasons.append(
                f"detector folder mismatch: {detector_folder} vs {parsed.detector_id}"
            )

        detector_id = get_str(payload_dict.get("detector_id"))
        if detector_id and detector_id != parsed.detector_id:
            reasons.append(
                f"detector_id mismatch: {detector_id} vs {parsed.detector_id}"
            )
        ticker_value = get_str(payload_dict.get("ticker"))
        if ticker_value and ticker_value.upper() != ticker_folder.upper():
            reasons.append(
                f"ticker mismatch: {ticker_value.upper()} vs {ticker_folder.upper()}"
            )

        year_from = get_int(payload_dict.get("year_from"))
        year_to = get_int(payload_dict.get("year_to"))
        if year_from is None or year_to is None:
            reasons.append("year_from/year_to missing or not integers")
            issues.append(ValidationIssue(path, reasons))
            continue
        if year_from != parsed.year_from or year_to != parsed.year_to:
            reasons.append(
                f"year mismatch: {year_from}-{year_to} vs {parsed.year_from}-{parsed.year_to}"
            )

        cleaning_lens = get_str(payload_dict.get("cleaning_lens"))

        evidence_raw = payload_dict.get("evidence")
        evidence_list = as_list(evidence_raw)
        if evidence_list is None:
            reasons.append("evidence is not a list")
            issues.append(ValidationIssue(path, reasons))
            continue

        lens_key = parsed.lens_key
        lens_name = ""
        is_focuspack = False
        if lens_key.startswith("focuspack_"):
            lens_name = lens_key[len("focuspack_") :]
            is_focuspack = True
        elif lens_key.startswith("full_"):
            lens_name = lens_key[len("full_") :]
        else:
            reasons.append(f"unknown lens key: {lens_key}")

        if cleaning_lens and lens_name and cleaning_lens != lens_name:
            reasons.append(
                f"cleaning_lens mismatch: {cleaning_lens} vs {lens_name}"
            )

        focus_entry = None
        focus_meta = None
        full_entry = None
        full_counts = None

        if lens_name:
            if is_focuspack:
                focus_entry = get_input_entry(
                    focus_index,
                    ticker_folder,
                    year_from,
                    year_to,
                    parsed.section,
                    lens_name,
                )
                if focus_entry is None:
                    reasons.append("missing focuspack input index entry")
                else:
                    cached = focus_meta_cache.get(focus_entry.path)
                    if cached is None:
                        cached = load_focuspack_meta(focus_entry.path)
                        focus_meta_cache[focus_entry.path] = cached
                    focus_meta = cached
                    if focus_meta is None:
                        reasons.append("invalid focuspack_meta in input JSON")

            full_entry = get_input_entry(
                full_index,
                ticker_folder,
                year_from,
                year_to,
                parsed.section,
                lens_name,
            )
            if full_entry is None:
                reasons.append("missing full input index entry")
            else:
                cached_full = full_counts_cache.get(full_entry.path)
                if cached_full is None:
                    cached_full = load_full_counts(full_entry.path)
                    full_counts_cache[full_entry.path] = cached_full
                full_counts = cached_full
                if full_counts is None:
                    reasons.append("invalid full input JSON for paragraph counts")

        for idx, evidence in enumerate(evidence_list):
            evidence_dict = as_str_dict(evidence)
            if evidence_dict is None:
                reasons.append(f"evidence[{idx}] is not an object")
                continue
            paragraph_idx = get_int(evidence_dict.get("paragraph_idx"))
            year_value = get_int(evidence_dict.get("year"))
            if paragraph_idx is None:
                reasons.append(f"evidence[{idx}] paragraph_idx missing or not int")
                continue
            if year_value is None:
                reasons.append(f"evidence[{idx}] year missing or not int")
                continue
            if paragraph_idx < 0:
                reasons.append(f"evidence[{idx}] paragraph_idx negative")
                continue

            if is_focuspack:
                if focus_meta is None:
                    continue
                selected = (
                    focus_meta.selected_prev
                    if year_value == year_from
                    else focus_meta.selected_curr
                    if year_value == year_to
                    else None
                )
                if selected is None:
                    reasons.append(
                        f"evidence[{idx}] year not in pair: {year_value}"
                    )
                    continue
                if paragraph_idx not in selected:
                    reasons.append(
                        f"evidence[{idx}] paragraph_idx not in focuspack mapping"
                    )
                count_prev = (
                    full_counts[0]
                    if full_counts is not None
                    else focus_meta.full_prev_count
                )
                count_curr = (
                    full_counts[1]
                    if full_counts is not None
                    else focus_meta.full_curr_count
                )
                count = count_prev if year_value == year_from else count_curr
                if count is not None and paragraph_idx >= count:
                    reasons.append(
                        f"evidence[{idx}] paragraph_idx out of bounds (count {count})"
                    )
            elif lens_name and full_counts is not None:
                count = full_counts[0] if year_value == year_from else full_counts[1]
                if paragraph_idx >= count:
                    reasons.append(
                        f"evidence[{idx}] paragraph_idx out of bounds (count {count})"
                    )

        if reasons:
            issues.append(ValidationIssue(path, reasons))

    return issues


def print_issues(issues: list[ValidationIssue]) -> None:
    print(f"Validation failed: {len(issues)} invalid file(s)")
    for issue in issues:
        print(f"- {issue.path}")
        for reason in issue.reasons:
            print(f"  - {reason}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate LLM outputs in the lab sidecar.")
    parser.add_argument(
        "--outputs-dir",
        default=str(DEFAULT_OUTPUTS_DIR),
        help="Path to public/data/sec_narrative_drift_lab/llm_outputs",
    )
    parser.add_argument(
        "--bundle",
        default="",
        help="LLM input bundle root (defaults to latest bundles/showcase_llm_inputs_*)",
    )
    parser.add_argument(
        "--inputs-index-focuspack",
        default="",
        help="Override path to inputs_index_focuspack.json",
    )
    parser.add_argument(
        "--inputs-index-full",
        default="",
        help="Override path to inputs_index_full.json",
    )
    parser.add_argument(
        "--prompt-templates",
        default="",
        help="Override path to prompt_templates_showcase.md",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    bundle_paths = resolve_bundle_paths(
        args.bundle or None,
        args.inputs_index_focuspack or None,
        args.inputs_index_full or None,
        args.prompt_templates or None,
    )
    outputs_dir = Path(args.outputs_dir)
    required_fields = load_required_fields(bundle_paths.prompt_templates)

    issues = validate_outputs(outputs_dir, bundle_paths, required_fields)
    if issues:
        print_issues(issues)
        return 1

    file_count = len(list(outputs_dir.rglob("*.json"))) if outputs_dir.exists() else 0
    print(f"Validated {file_count} output file(s) OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
