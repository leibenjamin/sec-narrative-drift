from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_ROOT = REPO_ROOT / "reports" / "protocol_lab"
DEFAULT_REPORT_PATH = REPORTS_ROOT / "wave4e15_standard_control_validation_report.json"


@dataclass(frozen=True)
class RunValidationResult:
    run_id: str
    lane_slug: str
    expected_top_level_keys: tuple[str, ...]
    response_path: str
    run_manifest_path: str
    response_exists: bool
    response_non_empty: bool
    json_parseable: bool
    json_object: bool
    top_level_shape_valid: bool
    actual_top_level_keys: list[str]
    raw_text_expected_key_hints: dict[str, bool]
    blocker_codes: list[str]
    notes: list[str]
    sidecars_written: list[str]


@dataclass(frozen=True)
class ValidationReport:
    packet_root: str
    generated_at: str
    overall_result: str
    run_results: list[RunValidationResult]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_repo_path(path_value: str) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    return REPO_ROOT / candidate


def repo_rel_or_abs(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def derive_lane_slug(run_id: str) -> str:
    base = run_id.removesuffix("_standard")
    parts = base.split("_", 1)
    if len(parts) != 2:
        raise ValueError(f"Unable to derive lane slug from run id: {run_id}")
    return parts[1]


def run_manifest_payload(run_manifest_path: Path) -> dict[str, object] | None:
    if not run_manifest_path.exists():
        return None
    try:
        payload = json.loads(run_manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return cast(dict[str, object], payload)


def derive_lane_slug_from_run_manifest(run_manifest_path: Path) -> str | None:
    manifest = run_manifest_payload(run_manifest_path)
    if manifest is None:
        return None
    run_identity = manifest.get("run_identity")
    if isinstance(run_identity, dict):
        identity = cast(dict[str, object], run_identity)
        family_id = identity.get("family_id")
        if isinstance(family_id, str) and family_id:
            return family_id
        lane_slug = identity.get("lane_slug")
        if isinstance(lane_slug, str) and lane_slug:
            return lane_slug
    output_contract = manifest.get("output_contract")
    if isinstance(output_contract, dict):
        contract = cast(dict[str, object], output_contract)
        primary_artifact_key = contract.get("primary_artifact_key")
        if isinstance(primary_artifact_key, str) and primary_artifact_key:
            return primary_artifact_key
    return None


def expected_top_level_keys_for_lane_slug(lane_slug: str) -> tuple[str, ...]:
    if lane_slug.startswith("00_"):
        return ("brief_markdown", "evidence")
    if lane_slug.startswith("01_") or lane_slug.startswith("02_") or lane_slug.startswith("03_"):
        return ("change_brief", "evidence_bundle")
    raise ValueError(f"Unsupported lane family for validator: {lane_slug}")


def expected_top_level_keys_from_run_manifest(run_manifest_path: Path) -> tuple[str, ...] | None:
    manifest = run_manifest_payload(run_manifest_path)
    if manifest is None:
        return None
    output_contract = manifest.get("output_contract")
    if not isinstance(output_contract, dict):
        return None
    contract = cast(dict[str, object], output_contract)
    top_level_keys = contract.get("top_level_keys")
    if not isinstance(top_level_keys, list) or not top_level_keys:
        return None

    resolved_keys: list[str] = []
    for value in cast(list[object], top_level_keys):
        if not isinstance(value, str) or not value:
            return None
        resolved_keys.append(value)
    return tuple(resolved_keys)


def expected_top_level_keys_for_run(run_id: str, run_manifest_path: Path) -> tuple[str, ...]:
    manifest_keys = expected_top_level_keys_from_run_manifest(run_manifest_path)
    if manifest_keys is not None:
        return manifest_keys
    lane_slug = derive_lane_slug(run_id)
    return expected_top_level_keys_for_lane_slug(lane_slug)


def sidecar_outputs_from_run_manifest(run_manifest_path: Path) -> list[dict[str, str]]:
    manifest = run_manifest_payload(run_manifest_path)
    if manifest is None:
        return []
    output_contract = manifest.get("output_contract")
    if not isinstance(output_contract, dict):
        return []
    contract = cast(dict[str, object], output_contract)
    raw_outputs = contract.get("sidecar_outputs")
    if not isinstance(raw_outputs, list):
        return []

    outputs: list[dict[str, str]] = []
    for item in cast(list[object], raw_outputs):
        if not isinstance(item, dict):
            continue
        output = cast(dict[str, object], item)
        response_key = output.get("response_key")
        relative_path = output.get("relative_path")
        if isinstance(response_key, str) and response_key and isinstance(relative_path, str) and relative_path:
            outputs.append({"response_key": response_key, "relative_path": relative_path})
    return outputs


def write_sidecars_from_response(parsed: dict[str, object], run_manifest_path: Path) -> list[str]:
    written_paths: list[str] = []
    for sidecar in sidecar_outputs_from_run_manifest(run_manifest_path):
        response_key = sidecar["response_key"]
        if response_key not in parsed:
            continue
        value = parsed[response_key]
        if not isinstance(value, dict):
            continue
        destination = resolve_repo_path(sidecar["relative_path"])
        write_json(destination, cast(dict[str, Any], value))
        written_paths.append(repo_rel_or_abs(destination))
    return written_paths


def detect_expected_key_hints(raw_text: str, expected_keys: Sequence[str]) -> dict[str, bool]:
    return {key: f'"{key}"' in raw_text for key in expected_keys}


def validate_run(packet_root: Path, run_id: str, *, write_sidecars: bool = False) -> RunValidationResult:
    response_path = packet_root / run_id / "response.json"
    run_manifest_path = packet_root / run_id / "run_manifest.json"
    lane_slug = derive_lane_slug_from_run_manifest(run_manifest_path) or run_id
    expected_keys = expected_top_level_keys_for_run(run_id, run_manifest_path)
    blocker_codes: list[str] = []
    notes: list[str] = []
    actual_top_level_keys: list[str] = []
    raw_text_expected_key_hints = {key: False for key in expected_keys}
    sidecars_written: list[str] = []
    response_exists = response_path.exists()
    response_non_empty = False
    json_parseable = False
    json_object = False
    top_level_shape_valid = False

    if not response_exists:
        blocker_codes.append("response_missing")
        notes.append("response.json is missing.")
        return RunValidationResult(
            run_id=run_id,
            lane_slug=lane_slug,
            expected_top_level_keys=expected_keys,
            response_path=repo_rel_or_abs(response_path),
            run_manifest_path=repo_rel_or_abs(run_manifest_path),
            response_exists=response_exists,
            response_non_empty=response_non_empty,
            json_parseable=json_parseable,
            json_object=json_object,
            top_level_shape_valid=top_level_shape_valid,
            actual_top_level_keys=actual_top_level_keys,
            raw_text_expected_key_hints=raw_text_expected_key_hints,
            blocker_codes=blocker_codes,
            notes=notes,
            sidecars_written=sidecars_written,
        )

    raw_text = response_path.read_text(encoding="utf-8-sig")
    response_non_empty = len(raw_text.strip()) > 0
    if not response_non_empty:
        blocker_codes.append("response_empty")
        notes.append("response.json exists but is empty after trimming whitespace.")
        raw_text_expected_key_hints = detect_expected_key_hints(raw_text, expected_keys)
        return RunValidationResult(
            run_id=run_id,
            lane_slug=lane_slug,
            expected_top_level_keys=expected_keys,
            response_path=repo_rel_or_abs(response_path),
            run_manifest_path=repo_rel_or_abs(run_manifest_path),
            response_exists=response_exists,
            response_non_empty=response_non_empty,
            json_parseable=json_parseable,
            json_object=json_object,
            top_level_shape_valid=top_level_shape_valid,
            actual_top_level_keys=actual_top_level_keys,
            raw_text_expected_key_hints=raw_text_expected_key_hints,
            blocker_codes=blocker_codes,
            notes=notes,
            sidecars_written=sidecars_written,
        )

    try:
        parsed = json.loads(raw_text)
        json_parseable = True
    except json.JSONDecodeError as exc:
        blocker_codes.append("json_parse_failed")
        raw_text_expected_key_hints = detect_expected_key_hints(raw_text, expected_keys)
        notes.append(f"JSON parse failed: {exc.msg} at line {exc.lineno}, column {exc.colno}.")
        if all(raw_text_expected_key_hints.values()):
            notes.append("Expected top-level key tokens are still present in the raw text.")
        else:
            missing = [key for key, present in raw_text_expected_key_hints.items() if not present]
            notes.append(
                "Expected top-level key tokens missing from raw text: "
                + ", ".join(missing)
                + "."
            )
        return RunValidationResult(
            run_id=run_id,
            lane_slug=lane_slug,
            expected_top_level_keys=expected_keys,
            response_path=repo_rel_or_abs(response_path),
            run_manifest_path=repo_rel_or_abs(run_manifest_path),
            response_exists=response_exists,
            response_non_empty=response_non_empty,
            json_parseable=json_parseable,
            json_object=json_object,
            top_level_shape_valid=top_level_shape_valid,
            actual_top_level_keys=actual_top_level_keys,
            raw_text_expected_key_hints=raw_text_expected_key_hints,
            blocker_codes=blocker_codes,
            notes=notes,
            sidecars_written=sidecars_written,
        )

    if not isinstance(parsed, dict):
        blocker_codes.append("json_top_level_not_object")
        notes.append("JSON parsed successfully but the top level is not an object.")
        return RunValidationResult(
            run_id=run_id,
            lane_slug=lane_slug,
            expected_top_level_keys=expected_keys,
            response_path=repo_rel_or_abs(response_path),
            run_manifest_path=repo_rel_or_abs(run_manifest_path),
            response_exists=response_exists,
            response_non_empty=response_non_empty,
            json_parseable=json_parseable,
            json_object=json_object,
            top_level_shape_valid=top_level_shape_valid,
            actual_top_level_keys=actual_top_level_keys,
            raw_text_expected_key_hints=raw_text_expected_key_hints,
            blocker_codes=blocker_codes,
            notes=notes,
            sidecars_written=sidecars_written,
        )

    json_object = True
    checked_parsed = cast(dict[str, object], parsed)
    actual_top_level_keys = list(checked_parsed.keys())
    raw_text_expected_key_hints = detect_expected_key_hints(raw_text, expected_keys)
    top_level_shape_valid = actual_top_level_keys == list(expected_keys)

    if not top_level_shape_valid:
        blocker_codes.append("top_level_keys_mismatch")
        notes.append(
            "Top-level keys do not match the expected lane-family shape: "
            f"expected {list(expected_keys)}, got {actual_top_level_keys}."
        )
    else:
        notes.append("response.json matches the expected lane-family top-level keys.")
        if write_sidecars:
            sidecars_written = write_sidecars_from_response(checked_parsed, run_manifest_path)
            if sidecars_written:
                notes.append("Wrote sidecar artifacts from the validated response.")

    return RunValidationResult(
        run_id=run_id,
        lane_slug=lane_slug,
        expected_top_level_keys=expected_keys,
        response_path=repo_rel_or_abs(response_path),
        run_manifest_path=repo_rel_or_abs(run_manifest_path),
        response_exists=response_exists,
        response_non_empty=response_non_empty,
        json_parseable=json_parseable,
        json_object=json_object,
        top_level_shape_valid=top_level_shape_valid,
        actual_top_level_keys=actual_top_level_keys,
        raw_text_expected_key_hints=raw_text_expected_key_hints,
        blocker_codes=blocker_codes,
        notes=notes,
        sidecars_written=sidecars_written,
    )


def discover_run_ids(packet_root: Path) -> list[str]:
    run_ids: list[str] = []
    for path in sorted(packet_root.iterdir()):
        if not path.is_dir():
            continue
        if path.name == "reports" or path.name == "scripts" or path.name == "src":
            continue
        if not (path / "run_manifest.json").exists():
            continue
        run_ids.append(path.name)
    return run_ids


def validate_packet(
    packet_root: Path,
    run_ids: Sequence[str] | None = None,
    *,
    write_sidecars: bool = False,
) -> ValidationReport:
    effective_run_ids = list(run_ids) if run_ids else discover_run_ids(packet_root)
    results = [validate_run(packet_root, run_id, write_sidecars=write_sidecars) for run_id in effective_run_ids]
    overall_result = "pass" if results and all(not result.blocker_codes for result in results) else "fail"
    return ValidationReport(
        packet_root=repo_rel_or_abs(packet_root),
        generated_at=utc_now_iso(),
        overall_result=overall_result,
        run_results=results,
    )


def report_to_payload(report: ValidationReport) -> dict[str, Any]:
    return {
        "artifact_schema_id": "standard_control_validation_report_v1",
        "packet_root": report.packet_root,
        "generated_at": report.generated_at,
        "overall_result": report.overall_result,
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
                "sidecars_written": result.sidecars_written,
            }
            for result in report.run_results
        ],
    }


def write_validation_report(report: ValidationReport, report_path: Path) -> None:
    write_json(report_path, report_to_payload(report))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate Desktop packet response.json files for bounded protocol-lab capture review."
    )
    parser.add_argument("--packet-root", required=True, help="Packet root folder path or repo-relative path.")
    parser.add_argument(
        "--run",
        dest="run_ids",
        action="append",
        default=[],
        help="Optional run id to validate. Repeat to validate multiple runs.",
    )
    parser.add_argument(
        "--report-out",
        default=str(DEFAULT_REPORT_PATH),
        help="Path for the JSON validation report. Defaults to reports/protocol_lab/wave4e15_standard_control_validation_report.json.",
    )
    parser.add_argument(
        "--write-sidecars",
        action="store_true",
        help="Write configured sidecar artifacts from valid response.json files after validation.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    packet_root = resolve_repo_path(args.packet_root)
    report_path = resolve_repo_path(args.report_out)

    report = validate_packet(packet_root, args.run_ids, write_sidecars=args.write_sidecars)
    write_validation_report(report, report_path)

    passed_runs = [result.run_id for result in report.run_results if not result.blocker_codes]
    failed_runs = [result.run_id for result in report.run_results if result.blocker_codes]
    print(f"packet_root: {packet_root.resolve()}")
    print(f"overall_result: {report.overall_result}")
    print(f"report_path: {report_path.resolve()}")
    print(f"passed_runs: {passed_runs}")
    print(f"failed_runs: {failed_runs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
