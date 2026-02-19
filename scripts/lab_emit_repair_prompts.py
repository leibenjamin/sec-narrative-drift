from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

SCRIPT_VERSION = "lab_emit_repair_prompts.py@v2"


def extract_errors(log_text: str) -> dict[str, list[str]]:
    issues: dict[str, list[str]] = {}
    current: Optional[str] = None
    for line in log_text.splitlines():
        if line.startswith("- ") and "det_llm_" in line and ": " in line:
            current = line[2:].strip()
            if current:
                issues[current] = []
            continue
        if line.startswith("  - ") and current:
            issues[current].append(line[4:].strip())
    return issues


def match_issue_keys(keys: list[str], target: Path) -> list[str]:
    target_str = str(target)
    matches: list[str] = []
    for key in keys:
        if key == target_str or key.endswith(target_str):
            matches.append(key)
            continue
        if key.endswith(target.name):
            matches.append(key)
    return matches


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

    lines: list[str] = []
    lines.append("You are repairing a validation failure in one Lab LLM output JSON.")
    lines.append("Return corrected JSON only. No markdown. No backticks. No commentary.")
    lines.append("Do not add or remove top-level keys.")
    lines.append("Preserve existing content unless a change is required to fix listed validator errors.")
    lines.append(
        "Keep provenance keys restricted to input_file, model_provider, model_name, run_label."
    )
    lines.append("Keep delta citations in ASCII format only: YYYY para NN.")
    lines.append("")
    lines.append("Validation errors to fix:")
    if reasons:
        for reason in reasons:
            lines.append(f"- {reason}")
    else:
        lines.append("- No specific errors found in log. Review JSON for schema and index issues.")
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
