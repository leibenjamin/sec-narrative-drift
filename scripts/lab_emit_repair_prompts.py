from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Optional

from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v3")


def extract_errors(log_text: str) -> dict[str, list[str]]:
    issues: dict[str, list[str]] = {}
    current: Optional[str] = None
    for line in log_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") and ": " in stripped and ".json" in stripped:
            item = stripped[2:].strip()
            path_part = item.split(": ", 1)[1].strip() if ": " in item else item
            if path_part:
                current = path_part
                if current not in issues:
                    issues[current] = []
            continue
        if line.startswith("  - ") and current:
            issues[current].append(line[4:].strip())
    return issues


def match_issue_keys(keys: list[str], target: Path) -> list[str]:
    target_str = str(target)
    target_name = target.name
    target_norm = target_str.replace("\\", "/")
    matches: list[str] = []
    for key in keys:
        key_norm = key.replace("\\", "/")
        if key == target_str or key.endswith(target_str) or key_norm.endswith(target_norm):
            matches.append(key)
            continue
        if key.endswith(target_name):
            matches.append(key)
    return matches


def infer_focus_keys(reasons: list[str]) -> list[str]:
    focus: list[str] = []
    for reason in reasons:
        lower = reason.lower()
        if "top-level" in lower:
            for candidate in (
                "lab_schema_version",
                "artifact_schema_version",
                "artifact_id",
                "outline_prev",
                "outline_curr",
                "node_alignment",
                "material_changes",
                "evidence_bank",
                "lens_divergence",
                "provenance",
            ):
                if candidate not in focus:
                    focus.append(candidate)
        for candidate in (
            "outline_prev",
            "outline_curr",
            "node_alignment",
            "material_changes",
            "evidence_bank",
            "lens_divergence",
            "provenance",
            "ticker",
            "section",
            "source_id",
            "cleaning_lens",
            "year_from",
            "year_to",
            "artifact_id",
            "lab_schema_version",
            "artifact_schema_version",
        ):
            if candidate in reason and candidate not in focus:
                focus.append(candidate)
        if "snippet" in lower or "paragraph_idx" in lower:
            if "evidence_bank" not in focus:
                focus.append("evidence_bank")
        if "change_class" in lower or "rationale" in lower or "salience" in lower:
            if "node_alignment" not in focus:
                focus.append("node_alignment")
            if "material_changes" not in focus:
                focus.append("material_changes")
        if "model_provider" in lower or "model_name" in lower or "run_label" in lower or "input_file" in lower:
            if "provenance" not in focus:
                focus.append("provenance")
    return focus


def extract_index_hints(reasons: list[str]) -> dict[str, set[int]]:
    hints: dict[str, set[int]] = {}
    for reason in reasons:
        for match in re.finditer(
            r"(outline_prev|outline_curr|node_alignment|material_changes|evidence_bank)\[(\d+)\]",
            reason,
        ):
            key = match.group(1)
            idx = int(match.group(2))
            if key not in hints:
                hints[key] = set()
            hints[key].add(idx)
    return hints


def build_focused_payload(
    payload: dict[str, object],
    focus_keys: list[str],
    index_hints: dict[str, set[int]],
) -> dict[str, object]:
    focused: dict[str, object] = {}
    if not focus_keys:
        return focused
    for key in focus_keys:
        if key not in payload:
            continue
        value = payload[key]
        if isinstance(value, list) and key in index_hints:
            selected: list[object] = []
            for idx in sorted(index_hints[key]):
                if 0 <= idx < len(value):
                    selected.append(value[idx])
            focused[f"{key}__indexed_focus"] = selected
        focused[key] = value
    return focused


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Emit a repair prompt for a failed LLM output.")
    parser.add_argument("--error-log", required=True, help="Validator error log text file")
    parser.add_argument("--json", required=True, help="Path to the offending JSON file")
    parser.add_argument(
        "--out",
        default="",
        help="Write prompt to this file (defaults to stdout)",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    log_path = Path(args.error_log)
    json_path = Path(args.json)
    if not log_path.exists():
        raise SystemExit(f"Error log not found: {log_path}")
    if not json_path.exists():
        raise SystemExit(f"JSON file not found: {json_path}")

    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    issues = extract_errors(log_text)
    matches = match_issue_keys(list(issues.keys()), json_path)
    reasons: list[str] = []
    for key in matches:
        reasons.extend(issues.get(key, []))

    json_text = json_path.read_text(encoding="utf-8", errors="replace").strip()
    try:
        payload_raw = json.loads(json_text)
    except json.JSONDecodeError:
        payload_raw = {}
    payload = payload_raw if isinstance(payload_raw, dict) else {}

    artifact_id = ""
    detector_id = ""
    if isinstance(payload, dict):
        artifact_id = str(payload.get("artifact_id") or "")
        detector_id = str(payload.get("detector_id") or "")
    provenance = payload.get("provenance") if isinstance(payload, dict) else None
    provenance_dict = provenance if isinstance(provenance, dict) else {}
    model_provider = str(provenance_dict.get("model_provider") or "")
    model_name = str(provenance_dict.get("model_name") or "")
    run_label = str(provenance_dict.get("run_label") or "")

    focus_keys = infer_focus_keys(reasons)
    index_hints = extract_index_hints(reasons)
    focused_payload = build_focused_payload(payload if isinstance(payload, dict) else {}, focus_keys, index_hints)

    lines: list[str] = []
    lines.append("You are repairing a validation failure in one Lab LLM output JSON file.")
    lines.append("Return corrected JSON only. No markdown. No backticks. No commentary.")
    lines.append("Do not add or remove top-level keys.")
    lines.append("Preserve existing content unless a change is required to fix listed validator errors.")
    if artifact_id == "llm_outline_compare_v1":
        lines.append("This is a master artifact repair (`llm_outline_compare_v1`).")
        lines.append("Maintain top-level key set and required master sections exactly.")
        lines.append("Keep all evidence snippets verbatim contiguous substrings from mapped input paragraphs.")
    elif detector_id in {"det_llm_delta_brief_v1", "det_llm_excerpt_picker_v1"}:
        lines.append(f"This is a detector artifact repair (`{detector_id}`).")
    lines.append("Keep provenance keys restricted to input_file, model_provider, model_name, run_label.")
    if model_provider:
        lines.append(f'Keep provenance.model_provider exactly "{model_provider}".')
    if model_name:
        lines.append(f'Keep provenance.model_name exactly "{model_name}".')
    if run_label:
        lines.append(f'Keep provenance.run_label exactly "{run_label}" unless validator requires change.')
    else:
        lines.append("Keep provenance.run_label present and formatted as YYYY-MM-DD_<campaign_tag>.")
    lines.append('Keep citations in ASCII format "YYYY para NN" when citation text exists.')
    lines.append("")
    lines.append("Validation errors to fix:")
    if reasons:
        for reason in reasons:
            lines.append(f"- {reason}")
    else:
        lines.append("- No specific errors found in log. Review JSON for schema and index issues.")
    if focus_keys:
        lines.append("")
        lines.append("Likely failing fields (focus first):")
        for key in focus_keys:
            lines.append(f"- {key}")
    if focused_payload:
        lines.append("")
        lines.append("Focused payload slice (from failing fields / hinted indices):")
        lines.append(json.dumps(focused_payload, indent=2, ensure_ascii=False))
    lines.append("")
    lines.append("Original JSON:")
    lines.append(json_text)

    output_text = "\n".join(lines)
    if args.out:
        Path(args.out).write_text(output_text, encoding="utf-8")
    else:
        print(output_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
