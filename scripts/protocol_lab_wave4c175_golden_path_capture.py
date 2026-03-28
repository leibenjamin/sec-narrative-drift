
from __future__ import annotations

import argparse
import hashlib

import re
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import protocol_lab_wave4b_reviewability as wave4b
import protocol_lab_wave4c1_nvda_execution as wave4c1

REPO_ROOT = Path(__file__).resolve().parents[1]
BUSINESS_ROOT = REPO_ROOT / "public" / "data" / "business_document_protocol_lab"
RUNS_ROOT = BUSINESS_ROOT / "runs"
EVALS_ROOT = BUSINESS_ROOT / "evals"
REGISTRIES_ROOT = BUSINESS_ROOT / "registries"
SOURCE_CASES_ROOT = BUSINESS_ROOT / "source_cases"
REPORTS_ROOT = REPO_ROOT / "reports" / "protocol_lab"
RAW_RUNS_ROOT = REPORTS_ROOT / "raw_runs"

FIXTURE_ID = "NVDA_2024_2025_10k_item1a"
RUN_REQUEST_ID = (
    "NVDA_2024_2025_10k_item1a__p1_structured_contract_v1__m_primary_strong_reasoning_v1__i2_tagged_document_packet_v1"
)
PRIMARY_MODEL_PROFILE_ID = "m_primary_strong_reasoning_v1"
PRIMARY_RUNNER_BINDING_ID = "rb_anthropic_claude_code_opus46_real_local_v1"
PRIMARY_RUNNER_CAMPAIGN_ID = "anthropic_claudeopus46_claudecode_fullsec_real_2026-03-09"
PRIMARY_MODEL_NAME = "Claude Opus 4.6 (Thinking, Max)"
LEGACY_RUNNER_BINDING_ID = "rb_openai_gpt53codex_real_local_v1"
LEGACY_RUNNER_CAMPAIGN_ID = "openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27"
ATTEMPT_LABEL = "attempt_01"
ATTEMPT_RE = re.compile(r"^attempt_(\d+)$")
RAW_RESPONSE_FILE_CANDIDATES = ("response.json", "response.txt")
REQUIRED_RESPONSE_META_FIELDS = (
    "captured_at",
    "runner_binding_id",
    "campaign_id",
    "model_name",
    "capture_method",
)

CAPTURE_VALIDATION_SCHEMA_PATH = REPORTS_ROOT / "capture_validation_report_v1.schema.json"
LOCAL_CAPTURE_CONTRACT_PATH = REPORTS_ROOT / "local_capture_contract_v1.md"
HARNESS_REPORT_PATH = REPORTS_ROOT / "wave4c175_capture_harness_report.md"
REVIEW_NOTES_PATH = REPORTS_ROOT / "wave4c175_review_notes.md"


@dataclass
class CaptureValidationResult:
    passed: bool
    blockers: list[str]
    raw_response_path: str | None


@dataclass
class FinalizeResult:
    attempted: bool
    truly_finalized: bool
    blockers: list[str]
    run_state: str
    parse_status: str
    postprocess_status: str
    evidence_item_count: int
    evidence_resolution_result: str
    downstream_artifacts_materialized: bool


@dataclass
class WaveSummary:
    packet_dir: Path
    zip_path: Path
    capture_harness_implemented: bool
    capture_validation_passed: bool
    p1_truly_finalized: bool
    non_empty_evidence_materialized: bool
    biggest_remaining_blocker: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")


def yes_no(flag: bool) -> str:
    return "yes" if flag else "no"


def repo_rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def blocker_note(blockers: list[str], fallback: str) -> str:
    codes = unique([item for item in blockers if item])
    return "; ".join(codes) if codes else fallback


def rebind_existing_request(existing: dict[str, Any]) -> dict[str, Any]:
    rebound = dict(existing)
    runner_binding_id = maybe_str(rebound.get("runner_binding_id"))
    if runner_binding_id not in {PRIMARY_RUNNER_BINDING_ID, LEGACY_RUNNER_BINDING_ID}:
        raise ValueError(f"Unsupported existing runner binding for this micro-patch: {runner_binding_id}")
    rebound["runner_binding_id"] = PRIMARY_RUNNER_BINDING_ID
    return rebound

def run_dir() -> Path:
    return RUNS_ROOT / FIXTURE_ID / RUN_REQUEST_ID


def eval_dir() -> Path:
    return EVALS_ROOT / FIXTURE_ID / RUN_REQUEST_ID


def run_request_path() -> Path:
    return run_dir() / "run_request_v1.json"


def prompt_render_path() -> Path:
    return run_dir() / "prompt_render_v1.json"


def execution_trace_path() -> Path:
    return run_dir() / "execution_trace_v1.json"


def change_brief_path() -> Path:
    return run_dir() / "change_brief_output_v1.json"


def evidence_bundle_path() -> Path:
    return run_dir() / "evidence_bundle_v1.json"


def evidence_resolution_path() -> Path:
    return run_dir() / "evidence_resolution_v1.json"


def eval_path() -> Path:
    return eval_dir() / "change_brief_eval_v1.json"


def raw_attempt_root() -> Path:
    return RAW_RUNS_ROOT / FIXTURE_ID / RUN_REQUEST_ID / "main"


def attempt_dir() -> Path:
    return raw_attempt_root() / ATTEMPT_LABEL


def capture_instructions_path() -> Path:
    return attempt_dir() / "CAPTURE_INSTRUCTIONS.md"


def response_meta_path() -> Path:
    return attempt_dir() / "response_meta.json"


def capture_receipt_path() -> Path:
    return attempt_dir() / "capture_receipt_v1.json"


def capture_validation_report_path() -> Path:
    return attempt_dir() / "capture_validation_report_v1.json"


def parse_report_path() -> Path:
    return attempt_dir() / "parse_report_v1.json"


def as_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"Expected object for {label}.")
    return cast("dict[str, Any]", value)


def as_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError(f"Expected array for {label}.")
    return cast("list[Any]", value)


def as_str(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"Expected string for {label}.")
    return value


def maybe_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def list_attempt_labels() -> list[str]:
    root = raw_attempt_root()
    if not root.exists():
        return []
    labels = [path.name for path in root.iterdir() if path.is_dir() and ATTEMPT_RE.fullmatch(path.name)]
    return sorted(labels)


def attempt_policy_blockers() -> list[str]:
    labels = list_attempt_labels()
    return [f"unexpected_attempt_folder_present:{label}" for label in labels if label != ATTEMPT_LABEL]


def prompt_hash(prompt_render: dict[str, Any]) -> str:
    system_text = as_str(prompt_render.get("rendered_system_content"), "rendered_system_content")
    user_text = as_str(prompt_render.get("rendered_user_content"), "rendered_user_content")
    merged = system_text + "\n\n<USER_PROMPT_BOUNDARY>\n\n" + user_text
    return hashlib.sha256(merged.encode("utf-8")).hexdigest()


def discover_raw_response_file() -> tuple[Path | None, list[str]]:
    current = attempt_dir()
    accepted = [current / name for name in RAW_RESPONSE_FILE_CANDIDATES if (current / name).exists()]
    unexpected = [
        path.name
        for path in current.iterdir()
        if path.is_file() and path.name.startswith("response.") and path.name not in RAW_RESPONSE_FILE_CANDIDATES
    ]
    if len(accepted) == 1:
        return accepted[0], unexpected
    if len(accepted) > 1:
        return None, unique(["multiple_raw_response_files", *unexpected])
    return None, unexpected

def ensure_capture_validation_schema() -> None:
    payload = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "reports/protocol_lab/capture_validation_report_v1.schema.json",
        "title": "Protocol Lab Local Capture Validation Report v1",
        "type": "object",
        "required": [
            "artifact_schema_id",
            "capture_validation_report_id",
            "run_request_id",
            "attempt_label",
            "validated_at",
            "overall_result",
            "blocker_codes",
            "raw_response_path",
            "raw_response_filename",
            "response_meta_path",
            "capture_receipt_path",
            "prompt_render_id",
            "prompt_body_sha256",
            "notes",
        ],
        "properties": {
            "artifact_schema_id": {"const": "capture_validation_report_v1"},
            "capture_validation_report_id": {"type": "string"},
            "run_request_id": {"type": "string"},
            "attempt_label": {"type": "string"},
            "validated_at": {"type": "string"},
            "overall_result": {"type": "string", "enum": ["pass", "fail"]},
            "blocker_codes": {"type": "array", "items": {"type": "string"}},
            "raw_response_path": {"type": ["string", "null"]},
            "raw_response_filename": {"type": ["string", "null"]},
            "response_meta_path": {"type": "string"},
            "capture_receipt_path": {"type": "string"},
            "prompt_render_id": {"type": ["string", "null"]},
            "prompt_body_sha256": {"type": ["string", "null"]},
            "notes": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": False,
    }
    wave4c1.write_json(CAPTURE_VALIDATION_SCHEMA_PATH, payload)


def write_local_capture_contract() -> None:
    lines = [
        "# Local Capture Contract v1",
        "",
        f"- generated_at: `{utc_now_iso()}`",
        "",
        "## Accepted Raw File Names",
        "",
        "- `response.json`",
        "- `response.txt`",
        "",
        "## Required response_meta Fields",
        "",
        "- `captured_at`",
        "- `runner_binding_id`",
        "- `campaign_id`",
        "- `model_name`",
        "- `capture_method`",
        "",
        "## Local Receipt and Validation Artifacts",
        "",
        "- `capture_receipt_v1.json`",
        "- `capture_validation_report_v1.json`",
        "- Finalize is blocked unless validation report `overall_result` is `pass` for `attempt_01`.",
        "",
    ]
    wave4c1.write_text(LOCAL_CAPTURE_CONTRACT_PATH, "\n".join(lines) + "\n")


def build_capture_instructions() -> str:
    return "\n".join(
        [
            "# Wave 4C1.75 Capture Instructions",
            "",
            f"- run_request_id: `{RUN_REQUEST_ID}`",
            f"- attempt_label: `{ATTEMPT_LABEL}`",
            f"- attempt_folder: `{repo_rel(attempt_dir())}`",
            f"- prompt_render_path: `{repo_rel(prompt_render_path())}`",
            "",
            "## Raw Capture",
            "",
            f"- Use Claude Code with runner binding `{PRIMARY_RUNNER_BINDING_ID}` and model `{PRIMARY_MODEL_NAME}`.",
            "- Save unedited provider output as one file: `response.json` or `response.txt`.",
            "- Do not rewrite output semantics before validation/finalize.",
            "",
            "## Required response_meta Fields",
            "",
            "- `captured_at`, `runner_binding_id`, `campaign_id`, `model_name`, `capture_method`",
            "",
            "## Commands",
            "",
            "- `python scripts/protocol_lab_wave4c175_golden_path_capture.py validate`",
            "- `python scripts/protocol_lab_wave4c175_golden_path_capture.py finalize`",
            "",
            "## Wave Rule",
            "",
            "- Do not create `attempt_02` or any other attempt folder in this wave.",
            "",
        ]
    ) + "\n"


def prepare_phase() -> None:
    blockers = attempt_policy_blockers()
    if blockers:
        raise ValueError(blocker_note(blockers, "attempt_policy_blocked"))

    wave4c1.ensure_parse_report_schema()
    ensure_capture_validation_schema()
    write_local_capture_contract()

    existing = rebind_existing_request(wave4c1.read_json(run_request_path()))
    if as_str(existing.get("protocol_id"), "protocol_id") != "p1_structured_contract_v1":
        raise ValueError("Selected run does not use p1_structured_contract_v1.")
    if as_str(existing.get("model_profile_id"), "model_profile_id") != PRIMARY_MODEL_PROFILE_ID:
        raise ValueError("Selected run does not use m_primary_strong_reasoning_v1.")

    bindings = wave4b.ensure_registry_map(REGISTRIES_ROOT / "runner_bindings_local_v1.json", "runner_binding_id")
    source_case = wave4c1.read_json(SOURCE_CASES_ROOT / FIXTURE_ID / "source_case_manifest_v1.json")
    request = wave4c1.build_run_request_payload(existing)
    request["notes"] = [
        "Wave 4C1.75 golden-path capture harness.",
        "Scope: NVDA P1+i2 only, runner binding rb_anthropic_claude_code_opus46_real_local_v1, attempt_01 only.",
        "Prepared for the first real Claude Code / Opus 4.6 Protocol Lab run with local-only raw capture expectations.",
        "Existing scaffold outputs are not proof of current attempt success.",
    ]
    runner_binding = as_dict(bindings[PRIMARY_RUNNER_BINDING_ID], "runner_binding")
    input_pack = wave4b.load_input_pack_payload(FIXTURE_ID, as_str(request.get("input_pack_id"), "input_pack_id"))

    wave4c1.write_json(run_request_path(), request)
    wave4c1.write_json(prompt_render_path(), wave4c1.build_prompt_render(request, source_case, runner_binding, input_pack))
    wave4c1.write_json(execution_trace_path(), wave4c1.build_prepare_trace(request, ATTEMPT_LABEL))

    current_attempt = attempt_dir()
    current_attempt.mkdir(parents=True, exist_ok=True)
    wave4c1.write_text(capture_instructions_path(), build_capture_instructions())
    wave4c1.write_json(
        response_meta_path(),
        {
            "captured_at": "",
            "runner_binding_id": PRIMARY_RUNNER_BINDING_ID,
            "campaign_id": PRIMARY_RUNNER_CAMPAIGN_ID,
            "model_name": PRIMARY_MODEL_NAME,
            "capture_method": "",
            "notes": ["Confirm or update the truthful Claude Code capture facts before validation."],
        },
    )
    for stale in (capture_receipt_path(), capture_validation_report_path(), parse_report_path()):
        if stale.exists():
            stale.unlink()


def valid_response_meta(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    for key in REQUIRED_RESPONSE_META_FIELDS:
        if not isinstance(payload.get(key), str) or not cast(str, payload[key]).strip():
            blockers.append("response_meta_incomplete")
            return False, blockers
    if maybe_str(payload.get("runner_binding_id")) != PRIMARY_RUNNER_BINDING_ID:
        blockers.append("runner_binding_id_mismatch")
    if maybe_str(payload.get("campaign_id")) != PRIMARY_RUNNER_CAMPAIGN_ID:
        blockers.append("campaign_id_mismatch")
    model_name = (maybe_str(payload.get("model_name")) or "").lower()
    if "claude opus 4.6" not in model_name:
        blockers.append("model_name_mismatch")
    return (len(blockers) == 0), blockers


def build_receipt(meta: dict[str, Any], render: dict[str, Any], raw_file: Path, render_hash: str) -> dict[str, Any]:
    return {
        "artifact_schema_id": "capture_receipt_v1",
        "run_request_id": RUN_REQUEST_ID,
        "prompt_render_id": as_str(render.get("prompt_render_id"), "prompt_render_id"),
        "prompt_body_sha256": render_hash,
        "attempt_label": ATTEMPT_LABEL,
        "runner_binding_id": as_str(meta.get("runner_binding_id"), "runner_binding_id"),
        "campaign_id": as_str(meta.get("campaign_id"), "campaign_id"),
        "captured_at": as_str(meta.get("captured_at"), "captured_at"),
        "model_name": as_str(meta.get("model_name"), "model_name"),
        "capture_method": as_str(meta.get("capture_method"), "capture_method"),
        "raw_response_filename": raw_file.name,
        "raw_response_sha256": hashlib.sha256(raw_file.read_bytes()).hexdigest(),
        "validated_at": utc_now_iso(),
    }


def update_capture_gate_state(validation_passed: bool, blockers: list[str]) -> None:
    trace = wave4c1.read_json(execution_trace_path())
    request = wave4c1.read_json(run_request_path())
    if validation_passed:
        trace["run_state"] = "captured"
        trace["error_note"] = None
        request = wave4c1.update_request_status(request, "submitted", "Wave 4C1.75 capture validation passed for attempt_01.")
    else:
        trace["run_state"] = "capture_missing"
        trace["error_note"] = blocker_note(blockers, "capture_missing")
        request = wave4c1.update_request_status(
            request,
            "blocked",
            f"Wave 4C1.75 capture validation failed for attempt_01: {blocker_note(blockers, 'capture_missing')}",
        )
    trace["parse_status"] = "not_run"
    trace["postprocess_status"] = "not_run"
    trace["raw_response_path"] = None
    trace["finished_at"] = utc_now_iso()
    wave4c1.write_json(execution_trace_path(), trace)
    wave4c1.write_json(run_request_path(), request)


def validate_phase() -> CaptureValidationResult:
    blockers = attempt_policy_blockers()

    if not prompt_render_path().exists():
        blockers.append("prompt_render_missing")
        render = None
        render_hash = None
    else:
        render = wave4c1.read_json(prompt_render_path())
        render_hash = prompt_hash(render)

    raw_file, raw_discovery_blockers = discover_raw_response_file()
    blockers.extend(raw_discovery_blockers)
    if raw_file is None:
        blockers.append("raw_response_missing")

    if not response_meta_path().exists():
        blockers.append("response_meta_missing")
        meta = None
    else:
        meta = wave4c1.read_json(response_meta_path())
        ok, meta_blockers = valid_response_meta(meta)
        if not ok:
            blockers.extend(meta_blockers)

    if not blockers and render is not None and render_hash is not None and raw_file is not None and meta is not None:
        receipt = build_receipt(meta, render, raw_file, render_hash)
        wave4c1.write_json(capture_receipt_path(), receipt)
        if receipt["run_request_id"] != RUN_REQUEST_ID or receipt["attempt_label"] != ATTEMPT_LABEL:
            blockers.append("capture_receipt_mismatch")
    elif capture_receipt_path().exists():
        capture_receipt_path().unlink()

    blockers = unique(blockers)
    passed = len(blockers) == 0
    raw_response_rel: str | None = repo_rel(raw_file) if raw_file is not None else None
    report = {
        "artifact_schema_id": "capture_validation_report_v1",
        "capture_validation_report_id": f"{RUN_REQUEST_ID}__{ATTEMPT_LABEL}__capture_validation_report_v1",
        "run_request_id": RUN_REQUEST_ID,
        "attempt_label": ATTEMPT_LABEL,
        "validated_at": utc_now_iso(),
        "overall_result": "pass" if passed else "fail",
        "blocker_codes": blockers,
        "raw_response_path": raw_response_rel,
        "raw_response_filename": raw_file.name if raw_file is not None else None,
        "response_meta_path": repo_rel(response_meta_path()),
        "capture_receipt_path": repo_rel(capture_receipt_path()),
        "prompt_render_id": maybe_str(render.get("prompt_render_id")) if render is not None else None,
        "prompt_body_sha256": render_hash,
        "notes": ["Wave 4C1.75 capture-integrity gate only; no semantic eval in this phase."],
    }
    wave4c1.write_json(capture_validation_report_path(), report)
    update_capture_gate_state(passed, blockers)
    return CaptureValidationResult(passed=passed, blockers=blockers, raw_response_path=raw_response_rel)

def load_validation_gate() -> tuple[bool, list[str]]:
    if not capture_validation_report_path().exists():
        return False, ["capture_validation_report_missing"]
    report = wave4c1.read_json(capture_validation_report_path())
    blockers: list[str] = []
    if as_str(report.get("run_request_id"), "run_request_id") != RUN_REQUEST_ID:
        blockers.append("capture_validation_run_request_mismatch")
    if as_str(report.get("attempt_label"), "attempt_label") != ATTEMPT_LABEL:
        blockers.append("capture_validation_attempt_mismatch")
    if as_str(report.get("overall_result"), "overall_result") != "pass":
        blockers.append("capture_validation_not_passed")
    return len(blockers) == 0, blockers


def finalize_phase() -> FinalizeResult:
    gate_ok, gate_blockers = load_validation_gate()
    blockers = unique(gate_blockers + attempt_policy_blockers())
    if not gate_ok or blockers:
        return FinalizeResult(False, False, blockers or ["capture_validation_required"], "capture_missing", "not_run", "not_run", 0, "not_run", False)

    parse = wave4c1.parse_raw_response(RUN_REQUEST_ID, ATTEMPT_LABEL)
    wave4c1.write_json(parse_report_path(), wave4c1.build_parse_report(RUN_REQUEST_ID, ATTEMPT_LABEL, parse))

    if not parse.parse_succeeded:
        blockers = ["parse_failed"]
        trace = wave4c1.read_json(execution_trace_path())
        trace = wave4c1.update_trace(trace, "parse_failed", "failed", "not_run", parse.raw_response_path, repo_rel(parse_report_path()), ATTEMPT_LABEL, parse, blockers, 0)
        request = wave4c1.update_request_status(wave4c1.read_json(run_request_path()), "failed", "Wave 4C1.75 parse failed for attempt_01.")
        wave4c1.write_json(execution_trace_path(), trace)
        wave4c1.write_json(run_request_path(), request)
        return FinalizeResult(True, False, blockers, "parse_failed", "failed", "not_run", 0, "not_run", False)

    if not parse.schema_validation_succeeded:
        blockers = ["schema_validation_failed"]
        trace = wave4c1.read_json(execution_trace_path())
        trace = wave4c1.update_trace(trace, "parse_failed", "failed", "not_run", parse.raw_response_path, repo_rel(parse_report_path()), ATTEMPT_LABEL, parse, blockers, 0)
        request = wave4c1.update_request_status(wave4c1.read_json(run_request_path()), "failed", "Wave 4C1.75 schema validation failed for attempt_01.")
        wave4c1.write_json(execution_trace_path(), trace)
        wave4c1.write_json(run_request_path(), request)
        return FinalizeResult(True, False, blockers, "parse_failed", "failed", "not_run", 0, "not_run", False)

    request = wave4c1.read_json(run_request_path())
    input_pack = wave4b.load_input_pack_payload(FIXTURE_ID, as_str(request.get("input_pack_id"), "input_pack_id"))
    envelope = as_dict(parse.envelope, "parse.envelope")
    brief = wave4c1.build_change_brief(request, envelope)
    bundle = wave4c1.build_evidence_bundle(request, envelope)
    resolution = wave4b.build_evidence_resolution_payload(request, brief, bundle, input_pack)
    human = wave4c1.load_human_eval()
    rubric, failure_tags, reviewer_notes, human_present = wave4c1.sanitize_human_entry(human["runs"].get(RUN_REQUEST_ID))
    hard_checks = wave4c1.build_hard_checks(brief, bundle, resolution)
    eval_payload = wave4c1.build_eval(
        RUN_REQUEST_ID,
        hard_checks,
        rubric,
        failure_tags,
        reviewer_notes,
        as_str(brief.get("change_brief_output_id"), "change_brief_output_id"),
        as_str(bundle.get("evidence_bundle_id"), "evidence_bundle_id"),
        human_present,
    )

    wave4c1.write_json(change_brief_path(), brief)
    wave4c1.write_json(evidence_bundle_path(), bundle)
    wave4c1.write_json(evidence_resolution_path(), resolution)
    wave4c1.write_json(eval_path(), eval_payload)

    evidence_items = as_list(bundle.get("items"), "evidence_bundle.items")
    evidence_count = len(evidence_items)
    resolution_result = as_str(as_dict(resolution.get("resolution_summary"), "resolution_summary").get("overall_result"), "overall_result")

    blockers: list[str] = []
    if evidence_count == 0:
        blockers.append("evidence_bundle_empty")
    if resolution_result != "pass":
        blockers.append("evidence_resolution_not_pass")
    if not all(value == "pass" for value in hard_checks.values()):
        blockers.append("hard_checks_failed")
    blockers = unique(blockers)

    run_state = "reviewed" if (not blockers and human_present) else ("validated" if not blockers else "captured")
    postprocess_status = "passed" if not blockers else "failed"
    trace = wave4c1.read_json(execution_trace_path())
    trace = wave4c1.update_trace(trace, run_state, "passed", postprocess_status, parse.raw_response_path, repo_rel(parse_report_path()), ATTEMPT_LABEL, parse, blockers, evidence_count)
    request_status = "completed" if not blockers else "failed"
    request_note = f"Wave 4C1.75 {run_state} for attempt_01." if not blockers else f"Wave 4C1.75 blocked for attempt_01: {blocker_note(blockers, 'postprocess_failed')}"
    request = wave4c1.update_request_status(wave4c1.read_json(run_request_path()), request_status, request_note)
    wave4c1.write_json(execution_trace_path(), trace)
    wave4c1.write_json(run_request_path(), request)

    truly_finalized = run_state in {"validated", "reviewed"} and evidence_count > 0
    return FinalizeResult(True, truly_finalized, blockers, run_state, "passed", postprocess_status, evidence_count, resolution_result, True)


def packet_paths_for_stamp(stamp: str) -> tuple[Path, Path]:
    name = f"wave4c175_golden_path_capture_{stamp}"
    return REPO_ROOT / name, REPO_ROOT / f"{name}.zip"


def build_packet(validation: CaptureValidationResult, finalize: FinalizeResult | None, biggest_blocker: str) -> tuple[Path, Path]:
    packet_dir, zip_path = packet_paths_for_stamp(utc_stamp())
    if packet_dir.exists():
        shutil.rmtree(packet_dir)
    if zip_path.exists():
        zip_path.unlink()

    files: list[Path] = [
        Path("scripts/protocol_lab_wave4c175_golden_path_capture.py"),
        Path("scripts/tests/test_protocol_lab_wave4c175_golden_path_capture.py"),
        Path("docs/protocol_lab/README.md"),
        Path(repo_rel(LOCAL_CAPTURE_CONTRACT_PATH)),
        Path(repo_rel(CAPTURE_VALIDATION_SCHEMA_PATH)),
        Path(repo_rel(wave4c1.PARSE_REPORT_SCHEMA_PATH)),
        Path(repo_rel(HARNESS_REPORT_PATH)),
        Path(repo_rel(REVIEW_NOTES_PATH)),
        Path(repo_rel(run_request_path())),
        Path(repo_rel(prompt_render_path())),
        Path(repo_rel(execution_trace_path())),
        Path(repo_rel(capture_instructions_path())),
        Path(repo_rel(response_meta_path())),
        Path(repo_rel(capture_validation_report_path())),
    ]
    if capture_receipt_path().exists():
        files.append(Path(repo_rel(capture_receipt_path())))
    if parse_report_path().exists():
        files.append(Path(repo_rel(parse_report_path())))
    for name in RAW_RESPONSE_FILE_CANDIDATES:
        raw_path = attempt_dir() / name
        if raw_path.exists():
            files.append(Path(repo_rel(raw_path)))
    if finalize is not None and finalize.downstream_artifacts_materialized:
        files.extend([
            Path(repo_rel(change_brief_path())),
            Path(repo_rel(evidence_bundle_path())),
            Path(repo_rel(evidence_resolution_path())),
            Path(repo_rel(eval_path())),
        ])

    files = list(dict.fromkeys([f for f in files if (REPO_ROOT / f).exists()]))
    for rel in files:
        source = REPO_ROOT / rel
        dest = packet_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)

    readme = "\n".join([
        f"# {packet_dir.name}",
        "",
        "Wave 4C1.75 golden-path capture packet.",
        "",
        "## Summary",
        f"- capture_validation_passed: {validation.passed}",
        f"- finalize_attempted: {finalize.attempted if finalize is not None else False}",
        f"- p1_truly_finalized: {finalize.truly_finalized if finalize is not None else False}",
        f"- biggest_remaining_blocker: {biggest_blocker}",
        "",
    ])
    manifest = "# Relevant Files Manifest\n\n" + "\n".join(f"- {path.as_posix()}" for path in files) + "\n"
    wave4c1.write_text(packet_dir / "README.md", readme)
    wave4c1.write_text(packet_dir / "relevant_files_manifest.md", manifest)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for file_path in packet_dir.rglob("*"):
            if file_path.is_file():
                handle.write(file_path, file_path.relative_to(REPO_ROOT).as_posix())
    return packet_dir, zip_path


def run_all() -> WaveSummary:
    prepare_phase()
    validation = validate_phase()
    finalize: FinalizeResult | None = None
    if validation.passed:
        finalize = finalize_phase()

    if not validation.passed:
        biggest = blocker_note(validation.blockers, "capture_validation_failed")
    elif finalize is not None and not finalize.truly_finalized:
        biggest = blocker_note(finalize.blockers, "finalize_blocked")
    else:
        biggest = "none"

    harness_report = "\n".join([
        "# Wave 4C1.75 Capture Harness Report",
        "",
        f"- generated_at: `{utc_now_iso()}`",
        f"- run_request_id: `{RUN_REQUEST_ID}`",
        f"- attempt_label: `{ATTEMPT_LABEL}`",
        f"- capture_validation_passed: `{validation.passed}`",
        f"- validation_blockers: `{validation.blockers}`",
        f"- raw_response_path: `{validation.raw_response_path}`",
        f"- finalize_attempted: `{finalize.attempted if finalize is not None else False}`",
        f"- truly_finalized: `{finalize.truly_finalized if finalize is not None else False}`",
        f"- biggest_remaining_blocker: `{biggest}`",
        "",
    ])
    review_notes = "\n".join([
        "# Wave 4C1.75 Review Notes",
        "",
        f"- generated_at: `{utc_now_iso()}`",
        f"- capture_validation_passed: `{validation.passed}`",
        f"- validation_blockers: `{validation.blockers}`",
        f"- finalize_status: `{finalize.run_state if finalize is not None else 'not_attempted'}`",
        f"- finalize_blockers: `{finalize.blockers if finalize is not None else []}`",
        f"- biggest_remaining_blocker: `{biggest}`",
        "",
    ])
    wave4c1.write_text(HARNESS_REPORT_PATH, harness_report)
    wave4c1.write_text(REVIEW_NOTES_PATH, review_notes)

    packet_dir, zip_path = build_packet(validation, finalize, biggest)
    return WaveSummary(
        packet_dir=packet_dir,
        zip_path=zip_path,
        capture_harness_implemented=True,
        capture_validation_passed=validation.passed,
        p1_truly_finalized=bool(finalize and finalize.truly_finalized),
        non_empty_evidence_materialized=bool(finalize and finalize.downstream_artifacts_materialized and finalize.evidence_item_count > 0),
        biggest_remaining_blocker=biggest,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Wave4C1.75 golden-path capture harness")
    parser.add_argument("phase", nargs="?", choices=["prepare", "validate", "finalize", "all"], default="all")
    args = parser.parse_args()

    if args.phase == "prepare":
        prepare_phase()
        print("Wave4C1.75 prepare complete.")
        return 0

    if args.phase == "validate":
        result = validate_phase()
        print(f"capture validation passed: {yes_no(result.passed)}")
        print(f"capture validation blockers: {result.blockers}")
        return 0 if result.passed else 1

    if args.phase == "finalize":
        result = finalize_phase()
        if not result.attempted:
            print(f"finalize refused: {result.blockers}")
            return 1
        print(f"p1 run truly finalized: {yes_no(result.truly_finalized)}")
        print(f"finalize blockers: {result.blockers}")
        return 0 if result.truly_finalized else 1

    summary = run_all()
    print(f"packet folder path: {summary.packet_dir.resolve()}")
    print(f"zip path: {summary.zip_path.resolve()}")
    print(f"whether capture harness was implemented: {yes_no(summary.capture_harness_implemented)}")
    print(f"whether capture validation passed: {yes_no(summary.capture_validation_passed)}")
    print(f"whether the P1 run was truly finalized: {yes_no(summary.p1_truly_finalized)}")
    print(f"whether non-empty evidence bundles were materialized: {yes_no(summary.non_empty_evidence_materialized)}")
    print(f"biggest remaining blocker after Wave 4C1.75: {summary.biggest_remaining_blocker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
