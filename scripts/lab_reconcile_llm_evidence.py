from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, cast

import sys

SCRIPT_VERSION = "lab_reconcile_llm_evidence.py@v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_ROOT = REPO_ROOT / "reports"

FOCUSPACK_WARNING = "Focuspack is a subset; verify in full compare pane."
AUTOFILL_WARNING = "Confidence is moderate; validator autofilled confidence due to missing value."
SELECTED_RECONCILED_WARNING = (
    "Reconciled selected_prev/curr to FULL indices based on evidence."
)
DELTA_BRIEF_MOJIBAKE = "Â¶"
DELTA_BRIEF_PILCROW = "¶"
DELTA_BRIEF_NORMALIZED_WARNING = (
    "Normalized citation symbol from 'Â¶' to '¶' in delta_brief."
)
PROVENANCE_PUBLIC_NORMALIZED_WARNING = (
    "Normalized provenance.input_file to shipped public llm_inputs path."
)
PUBLIC_LLM_INPUTS_ROOT = (
    REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab" / "llm_inputs"
)

sys.path.append(str(Path(__file__).resolve().parent))
from lab_llm_precompute_utils import (  # type: ignore
    as_list,
    as_str_dict,
    get_int,
    get_str,
    read_json,
)
from lab_validate_llm_outputs import (  # type: ignore
    build_paragraph_maps,
    parse_output_filename,
    resolve_input_file,
)


@dataclass(frozen=True)
class FocuspackInputs:
    prev_paragraphs: list[str]
    curr_paragraphs: list[str]
    selected_prev: list[int]
    selected_curr: list[int]


def load_focuspack_inputs(input_payload: dict[str, object]) -> Optional[FocuspackInputs]:
    texts = as_str_dict(input_payload.get("texts"))
    if texts is None:
        return None
    prev_raw = as_list(texts.get("prev_paragraphs"))
    curr_raw = as_list(texts.get("curr_paragraphs"))
    if prev_raw is None or curr_raw is None:
        return None
    prev_paragraphs: list[str] = []
    curr_paragraphs: list[str] = []
    for item in prev_raw:
        if not isinstance(item, str):
            return None
        prev_paragraphs.append(item)
    for item in curr_raw:
        if not isinstance(item, str):
            return None
        curr_paragraphs.append(item)

    meta = as_str_dict(input_payload.get("focuspack_meta"))
    if meta is None:
        return None
    selected_prev_raw = as_list(meta.get("selected_prev_indices"))
    selected_curr_raw = as_list(meta.get("selected_curr_indices"))
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
    if len(selected_prev) != len(prev_paragraphs) or len(selected_curr) != len(curr_paragraphs):
        return None

    return FocuspackInputs(
        prev_paragraphs=prev_paragraphs,
        curr_paragraphs=curr_paragraphs,
        selected_prev=selected_prev,
        selected_curr=selected_curr,
    )


def parse_int_list(value: object) -> Optional[list[int]]:
    values_raw = as_list(value)
    if values_raw is None:
        return None
    values: list[int] = []
    for item in values_raw:
        if isinstance(item, int) and not isinstance(item, bool):
            values.append(item)
        else:
            return None
    return values


def maybe_map_focuspack_local_to_full(
    values: list[int], full_indices: list[int]
) -> tuple[list[int], bool]:
    if not values:
        return values, False
    allowed_full = set(full_indices)
    looks_local = all(0 <= value < len(full_indices) for value in values) and all(
        value not in allowed_full for value in values
    )
    if not looks_local:
        return values, False
    mapped: list[int] = []
    for value in values:
        mapped.append(full_indices[value])
    return mapped, True


def normalize_provenance_to_public_llm_inputs(path_value: str) -> Optional[str]:
    basename = Path(path_value).name
    if not basename or not basename.lower().endswith(".json"):
        return None
    candidate = PUBLIC_LLM_INPUTS_ROOT / basename
    if not candidate.exists() or not candidate.is_file():
        return None
    public_rel = str(candidate.relative_to(REPO_ROOT)).replace("\\", "/")
    current_norm = path_value.replace("\\", "/")
    if current_norm == public_rel:
        return None
    return public_rel


def repair_source_file_warning_lines(
    warnings_list: list[Any], provenance_filename: Optional[str]
) -> tuple[list[Any], bool]:
    fixed: list[Any] = []
    changed = False
    replacement = (
        f"Source file: {provenance_filename}" if provenance_filename else None
    )
    for entry in warnings_list:
        if not isinstance(entry, str):
            fixed.append(entry)
            continue
        trimmed = entry.strip()
        is_empty_source_file = (
            trimmed == "Source file:"
            or (
                trimmed.startswith("Source file:")
                and not trimmed[len("Source file:") :].strip()
            )
        )
        if not is_empty_source_file:
            fixed.append(entry)
            continue
        changed = True
        if replacement is None:
            continue
        if replacement not in fixed:
            fixed.append(replacement)
    return fixed, changed


def normalize_warning_strings(warnings_list: list[Any]) -> tuple[list[str], bool]:
    normalized: list[str] = []
    seen: set[str] = set()
    changed = False
    for entry in warnings_list:
        if not isinstance(entry, str):
            changed = True
            continue
        trimmed = entry.strip()
        if trimmed != entry:
            changed = True
        if not trimmed:
            changed = True
            continue
        if trimmed in seen:
            changed = True
            continue
        seen.add(trimmed)
        normalized.append(trimmed)
    return normalized, changed


def trim_snippet(snippet: str, max_chars: int) -> str:
    if len(snippet) <= max_chars:
        return snippet
    candidate = snippet[:max_chars]
    for char in [".", ";", ":", ","]:
        idx = candidate.rfind(char)
        if idx != -1:
            return candidate[: idx + 1].rstrip()
    whitespace_idx = candidate.rfind(" ")
    if whitespace_idx != -1:
        return candidate[:whitespace_idx].rstrip()
    return candidate.rstrip()


def resolve_paths(output_file: Optional[str], output_root: Optional[str]) -> list[Path]:
    if output_file:
        path = Path(output_file)
        if not path.exists():
            raise SystemExit(f"Output file not found: {path}")
        return [path]
    if output_root:
        root = Path(output_root)
        if not root.exists():
            raise SystemExit(f"Output root not found: {root}")
        return sorted(
            path for path in root.rglob("*.json") if not path.name.endswith(".fixed.json")
        )
    raise SystemExit("Provide --output-file or --output-root.")


def build_fixed_path(path: Path) -> Path:
    return path.with_suffix(".fixed.json")


def infer_input_file(path: Path, payload_dict: dict[str, object]) -> Optional[Path]:
    ticker = get_str(payload_dict.get("ticker"))
    section = get_str(payload_dict.get("section")) or "10k_item1a"
    parsed = parse_output_filename(path.stem, section)
    if parsed is None:
        return None
    if ticker is None:
        ticker = path.parent.name
    input_name = f"{ticker}_{parsed.year_from}_{parsed.year_to}_{parsed.lens_key}.json"
    resolution = resolve_input_file(input_name, path)
    return resolution.path


def reconcile_file(
    path: Path,
    mode: str,
    max_chars: int,
) -> dict[str, object]:
    result: dict[str, object] = {
        "path": str(path),
        "fixed_path": None,
        "paragraph_idx_corrected": 0,
        "snippets_trimmed": 0,
        "confidence_filled": 0,
        "warnings_filled": 0,
        "unresolved_snippet_matches": 0,
        "input_file_inferred": 0,
        "errors": [],
    }

    try:
        payload = read_json(path)
    except json.JSONDecodeError as exc:
        result["errors"] = [f"invalid JSON: {exc}"]
        return result

    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        result["errors"] = ["JSON root is not an object"]
        return result

    provenance = as_str_dict(payload_dict.get("provenance")) or {}
    input_file_value = get_str(provenance.get("input_file"))
    if input_file_value is not None and not input_file_value.strip():
        input_file_value = None
    input_path: Optional[Path] = None
    resolution_error: Optional[str] = None
    provenance_public_normalized = False
    if input_file_value is None:
        inferred = infer_input_file(path, payload_dict)
        if inferred is None:
            result["errors"] = ["provenance.input_file missing"]
            return result
        input_path = inferred
        provenance["input_file"] = str(input_path.relative_to(REPO_ROOT))
        payload_dict["provenance"] = provenance
        input_file_value = get_str(provenance.get("input_file"))
        result["input_file_inferred"] = 1
    else:
        resolution = resolve_input_file(input_file_value, path)
        input_path = resolution.path
        resolution_error = resolution.error

    current_input_file_value = get_str(provenance.get("input_file"))
    if current_input_file_value is not None:
        normalized_public = normalize_provenance_to_public_llm_inputs(
            current_input_file_value
        )
        if normalized_public is not None:
            provenance["input_file"] = normalized_public
            payload_dict["provenance"] = provenance
            input_file_value = normalized_public
            resolution = resolve_input_file(normalized_public, path)
            input_path = resolution.path
            resolution_error = resolution.error
            provenance_public_normalized = True

    if input_path is None or not input_path.exists():
        if input_file_value is None:
            result["errors"] = ["provenance.input_file not found"]
        else:
            result["errors"] = [
                resolution_error or f"provenance.input_file not found: {input_file_value}"
            ]
        return result

    input_payload = as_str_dict(read_json(input_path))
    if input_payload is None:
        result["errors"] = ["provenance.input_file JSON invalid"]
        return result

    maps = build_paragraph_maps(input_payload)
    focuspack_inputs = load_focuspack_inputs(input_payload)
    if maps is None or focuspack_inputs is None:
        result["errors"] = ["provenance.input_file missing focuspack texts/meta"]
        return result

    year_from = get_int(payload_dict.get("year_from"))
    year_to = get_int(payload_dict.get("year_to"))
    if year_from is None or year_to is None:
        result["errors"] = ["year_from/year_to missing or invalid"]
        return result

    evidence_list = as_list(payload_dict.get("evidence"))
    if evidence_list is None:
        result["errors"] = ["evidence is not a list"]
        return result

    detector_id = get_str(payload_dict.get("detector_id")) or ""
    is_excerpt_picker = detector_id == "det_llm_excerpt_picker_v1"
    selected_reconciled = False
    delta_brief_normalized = False

    artifacts = as_str_dict(payload_dict.get("artifacts"))
    if artifacts is None:
        artifacts = {}
        payload_dict["artifacts"] = artifacts

    if detector_id == "det_llm_delta_brief_v1":
        delta_brief = get_str(artifacts.get("delta_brief"))
        if delta_brief is not None and DELTA_BRIEF_MOJIBAKE in delta_brief:
            artifacts["delta_brief"] = delta_brief.replace(
                DELTA_BRIEF_MOJIBAKE, DELTA_BRIEF_PILCROW
            )
            payload_dict["artifacts"] = artifacts
            delta_brief_normalized = True

    selected_prev_original = parse_int_list(artifacts.get("selected_prev")) if is_excerpt_picker else None
    selected_curr_original = parse_int_list(artifacts.get("selected_curr")) if is_excerpt_picker else None
    selected_prev_mapped = selected_prev_original or []
    selected_curr_mapped = selected_curr_original or []
    if is_excerpt_picker:
        selected_prev_mapped, prev_was_local = maybe_map_focuspack_local_to_full(
            selected_prev_mapped, focuspack_inputs.selected_prev
        )
        selected_curr_mapped, curr_was_local = maybe_map_focuspack_local_to_full(
            selected_curr_mapped, focuspack_inputs.selected_curr
        )
        if prev_was_local or curr_was_local:
            selected_reconciled = True

    evidence_prev_indices: list[int] = []
    evidence_curr_indices: list[int] = []
    seen_prev_indices: set[int] = set()
    seen_curr_indices: set[int] = set()
    for idx, entry in enumerate(evidence_list):
        entry_dict = as_str_dict(entry)
        if entry_dict is None:
            continue
        snippet = get_str(entry_dict.get("snippet"))
        paragraph_idx = get_int(entry_dict.get("paragraph_idx"))
        year_value = get_int(entry_dict.get("year"))
        if snippet is None or paragraph_idx is None or year_value is None:
            continue

        if year_value == year_from:
            mapped_text = maps.prev_map.get(paragraph_idx)
            focus_paras = focuspack_inputs.prev_paragraphs
            focus_indices = focuspack_inputs.selected_prev
        elif year_value == year_to:
            mapped_text = maps.curr_map.get(paragraph_idx)
            focus_paras = focuspack_inputs.curr_paragraphs
            focus_indices = focuspack_inputs.selected_curr
        else:
            continue

        if year_value == year_from and paragraph_idx not in seen_prev_indices:
            seen_prev_indices.add(paragraph_idx)
            evidence_prev_indices.append(paragraph_idx)
        if year_value == year_to and paragraph_idx not in seen_curr_indices:
            seen_curr_indices.add(paragraph_idx)
            evidence_curr_indices.append(paragraph_idx)

        if mapped_text is None or snippet not in mapped_text:
            matches: list[int] = []
            for pos, paragraph in enumerate(focus_paras):
                if snippet in paragraph:
                    matches.append(pos)
            if len(matches) == 1:
                new_full_idx = focus_indices[matches[0]]
                entry_dict["paragraph_idx"] = new_full_idx
                result["paragraph_idx_corrected"] = cast(int, result["paragraph_idx_corrected"]) + 1
            else:
                result["unresolved_snippet_matches"] = cast(int, result["unresolved_snippet_matches"]) + 1

        if len(snippet) > max_chars:
            trimmed = trim_snippet(snippet, max_chars)
            entry_dict["snippet"] = trimmed
            result["snippets_trimmed"] = cast(int, result["snippets_trimmed"]) + 1

        evidence_list[idx] = entry_dict

    payload_dict["evidence"] = evidence_list

    if is_excerpt_picker:
        rebuilt_prev = evidence_prev_indices
        rebuilt_curr = evidence_curr_indices
        if selected_prev_mapped != rebuilt_prev or selected_curr_mapped != rebuilt_curr:
            selected_reconciled = True
        artifacts["selected_prev"] = rebuilt_prev
        artifacts["selected_curr"] = rebuilt_curr
        payload_dict["artifacts"] = artifacts

    metrics = payload_dict.get("metrics")
    metrics_dict = as_str_dict(metrics) if metrics is not None else None
    if metrics_dict is None:
        metrics_dict = {}

    confidence = metrics_dict.get("confidence")
    if confidence is None:
        metrics_dict["confidence"] = 0.50
        result["confidence_filled"] = cast(int, result["confidence_filled"]) + 1
        autofilled_conf = True
    else:
        autofilled_conf = False

    warnings = metrics_dict.get("warnings")
    warnings_list = as_list(warnings) if warnings is not None else None
    if warnings_list is None:
        warnings_list = []

    provenance_filename: Optional[str] = None
    current_provenance_file = get_str(provenance.get("input_file"))
    if current_provenance_file is not None:
        filename = Path(current_provenance_file).name
        if filename:
            provenance_filename = filename
    warnings_list, source_warning_fixed = repair_source_file_warning_lines(
        warnings_list, provenance_filename
    )
    if source_warning_fixed:
        result["warnings_filled"] = cast(int, result["warnings_filled"]) + 1

    if not warnings_list:
        warnings_list.append(FOCUSPACK_WARNING)
        if autofilled_conf:
            warnings_list.append(AUTOFILL_WARNING)
        result["warnings_filled"] = cast(int, result["warnings_filled"]) + 1
    else:
        if FOCUSPACK_WARNING not in warnings_list:
            warnings_list.append(FOCUSPACK_WARNING)
            if autofilled_conf:
                warnings_list.append(AUTOFILL_WARNING)
            result["warnings_filled"] = cast(int, result["warnings_filled"]) + 1
    if selected_reconciled and SELECTED_RECONCILED_WARNING not in warnings_list:
        warnings_list.append(SELECTED_RECONCILED_WARNING)
        result["warnings_filled"] = cast(int, result["warnings_filled"]) + 1
    if (
        delta_brief_normalized
        and DELTA_BRIEF_NORMALIZED_WARNING not in warnings_list
    ):
        warnings_list.append(DELTA_BRIEF_NORMALIZED_WARNING)
        result["warnings_filled"] = cast(int, result["warnings_filled"]) + 1
    if (
        provenance_public_normalized
        and PROVENANCE_PUBLIC_NORMALIZED_WARNING not in warnings_list
    ):
        warnings_list.append(PROVENANCE_PUBLIC_NORMALIZED_WARNING)
        result["warnings_filled"] = cast(int, result["warnings_filled"]) + 1
    warnings_list, warnings_normalized = normalize_warning_strings(warnings_list)
    if warnings_normalized:
        result["warnings_filled"] = cast(int, result["warnings_filled"]) + 1
    metrics_dict["warnings"] = warnings_list

    payload_dict["metrics"] = metrics_dict

    if mode == "report_only":
        return result

    if mode == "write_fixed_sibling":
        fixed_path = build_fixed_path(path)
        fixed_path.write_text(json.dumps(payload_dict, indent=2) + "\n", encoding="utf-8")
        result["fixed_path"] = str(fixed_path)
        return result

    if mode == "in_place":
        path.write_text(json.dumps(payload_dict, indent=2) + "\n", encoding="utf-8")
        result["fixed_path"] = str(path)
        return result

    result["errors"] = [f"unknown mode: {mode}"]
    return result


def reconcile_outputs(
    paths: list[Path],
    mode: str,
    max_chars: int,
) -> dict[str, object]:
    results: list[dict[str, object]] = []
    for path in paths:
        results.append(reconcile_file(path, mode, max_chars))

    summary = {
        "mode": mode,
        "files": len(results),
        "paragraph_idx_corrected": sum(cast(int, r["paragraph_idx_corrected"]) for r in results),
        "snippets_trimmed": sum(cast(int, r["snippets_trimmed"]) for r in results),
        "confidence_filled": sum(cast(int, r["confidence_filled"]) for r in results),
        "warnings_filled": sum(cast(int, r["warnings_filled"]) for r in results),
        "unresolved_snippet_matches": sum(cast(int, r["unresolved_snippet_matches"]) for r in results),
        "input_file_inferred": sum(cast(int, r["input_file_inferred"]) for r in results),
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_ROOT / f"llm_reconcile_log_{timestamp}.json"
    md_path = REPORTS_ROOT / f"llm_reconcile_log_{timestamp}.md"

    log_payload = {"summary": summary, "results": results, "script": SCRIPT_VERSION}
    json_path.write_text(json.dumps(log_payload, indent=2) + "\n", encoding="utf-8")

    md_lines: list[str] = []
    md_lines.append("# LLM Reconcile Log")
    md_lines.append("")
    md_lines.append(f"Created: {timestamp}")
    md_lines.append(f"Script: {SCRIPT_VERSION}")
    md_lines.append("")
    md_lines.append("## Summary")
    md_lines.append(f"- mode: {summary['mode']}")
    md_lines.append(f"- files: {summary['files']}")
    md_lines.append(f"- paragraph_idx_corrected: {summary['paragraph_idx_corrected']}")
    md_lines.append(f"- snippets_trimmed: {summary['snippets_trimmed']}")
    md_lines.append(f"- confidence_filled: {summary['confidence_filled']}")
    md_lines.append(f"- warnings_filled: {summary['warnings_filled']}")
    md_lines.append(
        f"- unresolved_snippet_matches: {summary['unresolved_snippet_matches']}"
    )
    md_lines.append(f"- input_file_inferred: {summary['input_file_inferred']}")
    md_lines.append("")
    md_lines.append("## Details")
    for entry in results:
        md_lines.append(f"- {entry['path']}")
        if entry.get("fixed_path"):
            md_lines.append(f"  - fixed_path: {entry['fixed_path']}")
        if entry.get("errors"):
            md_lines.append("  - errors:")
            for error in cast(list[str], entry["errors"]):
                md_lines.append(f"    - {error}")
        md_lines.append(
            "  - paragraph_idx_corrected: "
            + str(entry["paragraph_idx_corrected"])
        )
        md_lines.append("  - snippets_trimmed: " + str(entry["snippets_trimmed"]))
        md_lines.append("  - confidence_filled: " + str(entry["confidence_filled"]))
        md_lines.append("  - warnings_filled: " + str(entry["warnings_filled"]))
        md_lines.append(
            "  - unresolved_snippet_matches: "
            + str(entry["unresolved_snippet_matches"])
        )
        md_lines.append("  - input_file_inferred: " + str(entry["input_file_inferred"]))

    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return {
        "summary": summary,
        "json_log": str(json_path),
        "md_log": str(md_path),
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reconcile LLM evidence indices and snippets.")
    parser.add_argument("--output-file", default="", help="Single output JSON file to reconcile.")
    parser.add_argument(
        "--output-root",
        "--root",
        dest="output_root",
        default="",
        help="Directory containing output JSON files to reconcile.",
    )
    parser.add_argument(
        "--mode",
        choices=["report_only", "write_fixed_sibling", "in_place"],
        default="report_only",
        help="Reconcile mode (default report_only).",
    )
    parser.add_argument(
        "--max-snippet-chars",
        type=int,
        default=350,
        help="Max snippet length (default 350).",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    paths = resolve_paths(args.output_file or None, args.output_root or None)
    output = reconcile_outputs(paths, args.mode, args.max_snippet_chars)
    print(f"Wrote reconcile log to {output['md_log']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
