from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import sys

SCRIPT_VERSION = "lab_validate_pilot_and_report.py@v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO_ROOT / "reports" / "llm_pilot_quality_report.md"
BUNDLES_ROOT = REPO_ROOT / "bundles"

sys.path.append(str(Path(__file__).resolve().parent))
from lab_llm_precompute_utils import (  # type: ignore
    as_list,
    as_str_dict,
    get_int,
    get_str,
    resolve_bundle_paths,
)
from lab_validate_llm_outputs import (  # type: ignore
    load_required_fields,
    validate_outputs,
)
from lab_reconcile_llm_evidence import (  # type: ignore
    build_fixed_path,
    reconcile_outputs,
)


@dataclass(frozen=True)
class PilotJob:
    job_id: str
    ticker: str
    year_from: int
    year_to: int
    detector_id: str
    input_lens: str
    output_path: Path


def read_json_lines(path: Path) -> list[Any]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    payloads: list[Any] = []
    for line in lines:
        if not line.strip():
            continue
        payloads.append(json.loads(line))
    return payloads


def find_latest_pilot_pack(root: Path) -> Optional[Path]:
    if not root.exists():
        return None
    candidates: list[Path] = []
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        if not entry.name.startswith("llm_pilot_pack_"):
            continue
        if (entry / "pilot_jobs.jsonl").exists():
            candidates.append(entry)
    if not candidates:
        return None
    return sorted(candidates, key=lambda path: path.name)[-1]


def load_jobs(path: Path) -> list[PilotJob]:
    jobs_payloads = read_json_lines(path)
    jobs: list[PilotJob] = []
    for payload in jobs_payloads:
        payload_dict = as_str_dict(payload)
        if payload_dict is None:
            raise SystemExit(f"Invalid job entry in {path}")
        job_id = get_str(payload_dict.get("job_id"))
        ticker = get_str(payload_dict.get("ticker"))
        year_from = get_int(payload_dict.get("year_from"))
        year_to = get_int(payload_dict.get("year_to"))
        detector_id = get_str(payload_dict.get("detector_id"))
        input_lens = get_str(payload_dict.get("input_lens"))
        output_path = get_str(payload_dict.get("output_path"))
        if (
            job_id is None
            or ticker is None
            or year_from is None
            or year_to is None
            or detector_id is None
            or input_lens is None
            or output_path is None
        ):
            raise SystemExit(f"Job entry missing fields in {path}")
        jobs.append(
            PilotJob(
                job_id=job_id,
                ticker=ticker,
                year_from=year_from,
                year_to=year_to,
                detector_id=detector_id,
                input_lens=input_lens,
                output_path=REPO_ROOT / output_path,
            )
        )
    return jobs


def count_evidence_blocks(payload: dict[str, Any]) -> int:
    evidence_list = as_list(payload.get("evidence"))
    if evidence_list is None:
        return 0
    return len(evidence_list)


def check_snippets(payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    evidence_list = as_list(payload.get("evidence"))
    if evidence_list is None:
        return issues
    for idx, entry in enumerate(evidence_list):
        entry_dict = as_str_dict(entry)
        if entry_dict is None:
            continue
        snippet = get_str(entry_dict.get("snippet"))
        if snippet is None:
            continue
        if len(snippet) > 350:
            issues.append(f"snippet too long at evidence[{idx}] ({len(snippet)} chars)")
    return issues


def warnings_needed(payload: dict[str, Any]) -> bool:
    metrics = as_str_dict(payload.get("metrics"))
    if metrics is None:
        return False
    confidence = metrics.get("confidence")
    if confidence is None:
        return True
    if isinstance(confidence, (int, float)):
        return float(confidence) < 0.6
    return True


def warnings_present(payload: dict[str, Any]) -> bool:
    metrics = as_str_dict(payload.get("metrics"))
    if metrics is None:
        return False
    warnings_list = as_list(metrics.get("warnings"))
    if warnings_list is None:
        return False
    return len(warnings_list) > 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate pilot outputs and write a quality report.")
    parser.add_argument(
        "--pilot-pack",
        default="",
        help="Pilot pack directory (bundles/llm_pilot_pack_*)",
    )
    parser.add_argument(
        "--jobs",
        default="",
        help="Path to pilot_jobs.jsonl (overrides --pilot-pack)",
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
    parser.add_argument(
        "--report",
        default=str(REPORT_PATH),
        help="Output report path",
    )
    parser.add_argument(
        "--reconcile",
        choices=["off", "sibling", "in_place"],
        default="off",
        help="Run evidence reconcile before scoring (off, sibling, in_place).",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    pilot_pack = Path(args.pilot_pack) if args.pilot_pack else None
    jobs_path = Path(args.jobs) if args.jobs else None
    if jobs_path is None:
        if pilot_pack is None:
            pilot_pack = find_latest_pilot_pack(BUNDLES_ROOT)
        if pilot_pack is None:
            raise SystemExit("Pilot pack not found. Provide --pilot-pack or --jobs.")
        jobs_path = pilot_pack / "pilot_jobs.jsonl"
    if not jobs_path.exists():
        raise SystemExit(f"pilot_jobs.jsonl not found: {jobs_path}")

    jobs = load_jobs(jobs_path)

    bundle_paths = resolve_bundle_paths(
        args.bundle or None,
        args.inputs_index_focuspack or None,
        args.inputs_index_full or None,
        args.prompt_templates or None,
    )
    required_fields = load_required_fields(bundle_paths.prompt_templates)
    outputs_dir = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab" / "llm_outputs"

    reconcile_summary: Optional[dict[str, Any]] = None
    if args.reconcile != "off":
        mode = "write_fixed_sibling" if args.reconcile == "sibling" else "in_place"
        reconcile_summary = reconcile_outputs([job.output_path for job in jobs], mode, 350)

    validation_issues = validate_outputs(outputs_dir, bundle_paths, required_fields)
    issue_map: dict[str, list[str]] = {}
    for issue in validation_issues:
        issue_map[str(issue.path)] = issue.reasons

    report_lines: list[str] = []
    report_lines.append("# LLM Pilot Quality Report")
    report_lines.append("")
    report_lines.append(f"Jobs file: {jobs_path}")
    report_lines.append(f"Script: {SCRIPT_VERSION}")
    report_lines.append("")
    if reconcile_summary:
        summary = reconcile_summary.get("summary", {})
        report_lines.append("## Reconcile Summary")
        report_lines.append(f"- mode: {summary.get('mode')}")
        report_lines.append(f"- paragraph_idx_corrected: {summary.get('paragraph_idx_corrected')}")
        report_lines.append(f"- snippets_trimmed: {summary.get('snippets_trimmed')}")
        report_lines.append(f"- confidence_filled: {summary.get('confidence_filled')}")
        report_lines.append(f"- warnings_filled: {summary.get('warnings_filled')}")
        report_lines.append(f"- unresolved_snippet_matches: {summary.get('unresolved_snippet_matches')}")
        report_lines.append(f"- input_file_inferred: {summary.get('input_file_inferred')}")
        report_lines.append(f"- reconcile_log: {reconcile_summary.get('md_log')}")
        report_lines.append("")

    missing_outputs: list[str] = []
    invalid_outputs: list[str] = []
    schema_issues_by_job: dict[str, list[str]] = {}
    validator_warnings_by_job: dict[str, list[str]] = {}
    snippet_issues: dict[str, list[str]] = {}
    warning_missing: list[str] = []
    evidence_counts: dict[str, int] = {}

    for job in jobs:
        output_path = (
            build_fixed_path(job.output_path)
            if args.reconcile == "sibling"
            else job.output_path
        )
        key = str(output_path)
        if not output_path.exists():
            missing_outputs.append(job.job_id)
            continue

        try:
            payload = json.loads(output_path.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError as exc:
            invalid_outputs.append(job.job_id)
            schema_issues_by_job[job.job_id] = [f"invalid JSON: {exc}"]
            evidence_counts[job.job_id] = 0
            continue

        payload_dict = as_str_dict(payload) or {}
        evidence_counts[job.job_id] = count_evidence_blocks(payload_dict)

        reasons = issue_map.get(key, [])
        error_reasons = [reason for reason in reasons if not reason.startswith("WARN:")]
        warn_reasons = [reason for reason in reasons if reason.startswith("WARN:")]
        if error_reasons:
            invalid_outputs.append(job.job_id)
            schema_issues_by_job[job.job_id] = reasons
        elif warn_reasons:
            validator_warnings_by_job[job.job_id] = warn_reasons

        snippet_problems = check_snippets(payload_dict)
        if snippet_problems:
            snippet_issues[job.job_id] = snippet_problems

        if warnings_needed(payload_dict) and not warnings_present(payload_dict):
            warning_missing.append(job.job_id)

    report_lines.append("## Status By Output")
    report_lines.append("| Job ID | Exists | Schema Valid | Evidence Blocks | Snippet Issues | Warnings Needed | Validator Warnings |")
    report_lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for job in jobs:
        exists = "yes" if job.job_id not in missing_outputs else "no"
        schema_valid = "yes" if job.job_id not in invalid_outputs and exists == "yes" else "no"
        evidence_count = evidence_counts.get(job.job_id, 0)
        snippet_issue = "yes" if job.job_id in snippet_issues else "no"
        warnings_needed_flag = "missing" if job.job_id in warning_missing else "-"
        validator_warn_flag = "yes" if job.job_id in validator_warnings_by_job else "-"
        report_lines.append(
            f"| {job.job_id} | {exists} | {schema_valid} | {evidence_count} | {snippet_issue} | {warnings_needed_flag} | {validator_warn_flag} |"
        )

    report_lines.append("")
    report_lines.append("## Missing Outputs")
    if missing_outputs:
        for job_id in missing_outputs:
            report_lines.append(f"- {job_id}")
    else:
        report_lines.append("- None")

    report_lines.append("")
    report_lines.append("## Schema Issues")
    if schema_issues_by_job:
        for job_id in invalid_outputs:
            report_lines.append(f"- {job_id}")
            for reason in schema_issues_by_job.get(job_id, []):
                report_lines.append(f"  - {reason}")
    else:
        report_lines.append("- None")

    report_lines.append("")
    report_lines.append("## Validator Warnings")
    if validator_warnings_by_job:
        for job_id, reasons in validator_warnings_by_job.items():
            report_lines.append(f"- {job_id}")
            for reason in reasons:
                report_lines.append(f"  - {reason}")
    else:
        report_lines.append("- None")

    report_lines.append("")
    report_lines.append("## Snippet Length Issues")
    if snippet_issues:
        for job_id, issues in snippet_issues.items():
            report_lines.append(f"- {job_id}")
            for issue in issues:
                report_lines.append(f"  - {issue}")
    else:
        report_lines.append("- None")

    report_lines.append("")
    report_lines.append("## Warning Coverage Check")
    if warning_missing:
        report_lines.append("Warnings were expected due to low/unknown confidence.")
        for job_id in warning_missing:
            report_lines.append(f"- {job_id}")
    else:
        report_lines.append("- None")

    hard_fail = bool(missing_outputs or invalid_outputs or snippet_issues)
    summary = "NO-GO" if hard_fail else "GO"
    report_lines.append("")
    report_lines.append("## Go / No-Go Summary")
    report_lines.append(f"**{summary}**")
    if hard_fail:
        report_lines.append("Missing outputs or validation issues detected. Resolve before scaling.")
    else:
        report_lines.append("Pilot outputs look good. Safe to scale.")

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Wrote report to {report_path}")
    if hard_fail:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
