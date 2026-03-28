from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import protocol_lab_validate_desktop_packet_responses as packet_validator

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CaptureGuardrailSummary:
    packet_root: str
    generated_at: str
    overall_result: str
    proceed: bool
    checked_run_ids: list[str]
    blocking_run_ids: list[str]
    plain_language_summary: str
    run_results: list[packet_validator.RunValidationResult]


def resolve_repo_path(path_value: str) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    return REPO_ROOT / candidate


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_plain_language_summary(report: packet_validator.ValidationReport) -> str:
    blocking_run_ids = [result.run_id for result in report.run_results if result.blocker_codes]
    if not blocking_run_ids:
        return "Proceed. Every checked response.json file exists, is non-empty, parses cleanly, and matches the expected top-level shape."

    blocker_count = len(blocking_run_ids)
    return (
        f"Stop. {blocker_count} checked run"
        + ("" if blocker_count == 1 else "s")
        + " failed capture preflight and should be fixed before canonization or packet zipping."
    )


def build_console_lines(summary: CaptureGuardrailSummary) -> list[str]:
    lines = [
        f"capture_guardrail: {summary.overall_result.upper()}",
        f"packet_root: {summary.packet_root}",
        f"runs_checked: {len(summary.checked_run_ids)}",
        f"blocking_runs: {summary.blocking_run_ids}",
        f"summary: {summary.plain_language_summary}",
    ]

    for result in summary.run_results:
        if not result.blocker_codes:
            continue
        first_note = result.notes[0] if result.notes else "Blocking capture issue."
        lines.append(f"- {result.run_id}: {first_note}")

    return lines


def report_to_payload(summary: CaptureGuardrailSummary) -> dict[str, Any]:
    return {
        "artifact_schema_id": "capture_guardrail_report_v1",
        "packet_root": summary.packet_root,
        "generated_at": summary.generated_at,
        "overall_result": summary.overall_result,
        "proceed": summary.proceed,
        "checked_run_ids": summary.checked_run_ids,
        "blocking_run_ids": summary.blocking_run_ids,
        "plain_language_summary": summary.plain_language_summary,
        "run_results": [
            {
                "run_id": result.run_id,
                "lane_slug": result.lane_slug,
                "expected_top_level_keys": list(result.expected_top_level_keys),
                "response_path": result.response_path,
                "run_manifest_path": result.run_manifest_path,
                "response_exists": result.response_exists,
                "response_non_empty": result.response_non_empty,
                "json_parseable": result.json_parseable,
                "json_object": result.json_object,
                "top_level_shape_valid": result.top_level_shape_valid,
                "actual_top_level_keys": result.actual_top_level_keys,
                "raw_text_expected_key_hints": result.raw_text_expected_key_hints,
                "blocker_codes": result.blocker_codes,
                "notes": result.notes,
            }
            for result in summary.run_results
        ],
    }


def run_guardrail(
    packet_root: Path,
    run_ids: Sequence[str] | None = None,
    report_out: Path | None = None,
) -> CaptureGuardrailSummary:
    validation_report = packet_validator.validate_packet(packet_root, run_ids)
    blocking_run_ids = [
        result.run_id for result in validation_report.run_results if result.blocker_codes
    ]
    summary = CaptureGuardrailSummary(
        packet_root=validation_report.packet_root,
        generated_at=validation_report.generated_at,
        overall_result="proceed" if not blocking_run_ids else "stop",
        proceed=not blocking_run_ids,
        checked_run_ids=[result.run_id for result in validation_report.run_results],
        blocking_run_ids=blocking_run_ids,
        plain_language_summary=build_plain_language_summary(validation_report),
        run_results=validation_report.run_results,
    )

    if report_out is not None:
        write_json(report_out, report_to_payload(summary))

    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Small preflight guardrail for Desktop packet response.json capture quality."
    )
    parser.add_argument("--packet-root", required=True, help="Packet root folder path or repo-relative path.")
    parser.add_argument(
        "--run",
        dest="run_ids",
        action="append",
        default=[],
        help="Optional run id to check. Repeat to limit guardrail scope.",
    )
    parser.add_argument(
        "--report-out",
        help="Optional JSON report path for the guardrail result.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    packet_root = resolve_repo_path(args.packet_root)
    report_out = resolve_repo_path(args.report_out) if args.report_out else None

    summary = run_guardrail(packet_root, args.run_ids, report_out)
    for line in build_console_lines(summary):
        print(line)
    if report_out is not None:
        print(f"report_path: {report_out.resolve()}")
    return 0 if summary.proceed else 1


if __name__ == "__main__":
    raise SystemExit(main())
