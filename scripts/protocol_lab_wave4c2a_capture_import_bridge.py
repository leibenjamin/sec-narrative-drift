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
IMPORT_FILE_TO_CAPTURE_METHOD = {
    ".json": "saved_response_json_file",
    ".txt": "saved_response_text_file",
}
MANUAL_CAPTURE_BLOCKER = "real raw response not yet provided for import into attempt_01"
REQUIRED_RESPONSE_META_FIELDS = (
    "run_request_id",
    "prompt_render_id",
    "attempt_label",
    "runner_binding_id",
    "campaign_id",
    "captured_at",
    "model_name",
    "capture_method",
    "raw_response_filename",
    "raw_response_sha256",
)
REQUIRED_RECEIPT_FIELDS = (
    "capture_receipt_id",
    "run_request_id",
    "prompt_render_id",
    "attempt_label",
    "runner_binding_id",
    "campaign_id",
    "captured_at",
    "model_name",
    "capture_method",
    "raw_response_filename",
    "raw_response_sha256",
    "prompt_body_sha256",
)

CAPTURE_RECEIPT_SCHEMA_PATH = REPORTS_ROOT / "capture_receipt_v1.schema.json"
CAPTURE_VALIDATION_SCHEMA_PATH = REPORTS_ROOT / "capture_validation_report_v1.schema.json"
LOCAL_CAPTURE_CONTRACT_PATH = REPORTS_ROOT / "local_capture_contract_v1.md"
RUNBOOK_PATH = REPORTS_ROOT / "wave4c2a_operator_runbook.md"
BRIDGE_REPORT_PATH = REPORTS_ROOT / "wave4c2a_capture_import_bridge_report.md"
REVIEW_NOTES_PATH = REPORTS_ROOT / "wave4c2a_review_notes.md"


@dataclass
class CaptureImportResult:
    imported: bool
    blockers: list[str]
    raw_response_path: str | None
    raw_response_filename: str | None
    raw_response_sha256: str | None
    capture_method: str | None


@dataclass
class CaptureValidationResult:
    passed: bool
    blockers: list[str]
    raw_response_path: str | None
    raw_response_filename: str | None
    raw_response_sha256: str | None
    capture_receipt_id: str | None


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
    capture_import_bridge_implemented: bool
    real_raw_response_imported: bool
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


def path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def compute_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_mtime_iso(path: Path) -> str:
    """Return the file's modification time as a UTC ISO 8601 string.

    Used as the default captured_at when the operator does not provide an
    explicit timestamp — the moment the response file was last written to
    disk is the most truthful automated proxy for capture time.
    """
    mtime = path.stat().st_mtime
    dt = datetime.fromtimestamp(mtime, tz=timezone.utc).replace(microsecond=0)
    return dt.isoformat().replace("+00:00", "Z")


def is_valid_iso8601(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


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


def rebind_existing_request(existing: dict[str, Any]) -> dict[str, Any]:
    rebound = dict(existing)
    runner_binding_id = maybe_str(rebound.get("runner_binding_id"))
    if runner_binding_id not in {PRIMARY_RUNNER_BINDING_ID, LEGACY_RUNNER_BINDING_ID}:
        raise ValueError(f"Unsupported existing runner binding for this micro-patch: {runner_binding_id}")
    rebound["runner_binding_id"] = PRIMARY_RUNNER_BINDING_ID
    return rebound

def response_meta_template() -> dict[str, Any]:
    return {
        "run_request_id": RUN_REQUEST_ID,
        "prompt_render_id": f"{RUN_REQUEST_ID}__prompt_render_v1",
        "attempt_label": ATTEMPT_LABEL,
        "runner_binding_id": PRIMARY_RUNNER_BINDING_ID,
        "campaign_id": PRIMARY_RUNNER_CAMPAIGN_ID,
        "captured_at": "",
        "model_name": PRIMARY_MODEL_NAME,
        "capture_method": "",
        "raw_response_filename": "",
        "raw_response_sha256": "",
        "notes": ["Confirm or update the truthful Claude Code capture facts before validate/finalize."],
    }


def discover_raw_response_file() -> tuple[Path | None, list[str]]:
    current = attempt_dir()
    if not current.exists():
        return None, []
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


def ensure_capture_receipt_schema() -> None:
    payload = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "reports/protocol_lab/capture_receipt_v1.schema.json",
        "title": "Protocol Lab Local Capture Receipt v1",
        "type": "object",
        "required": [
            "artifact_schema_id",
            "capture_receipt_id",
            "run_request_id",
            "prompt_render_id",
            "attempt_label",
            "runner_binding_id",
            "campaign_id",
            "captured_at",
            "model_name",
            "capture_method",
            "raw_response_filename",
            "raw_response_sha256",
            "prompt_body_sha256",
            "notes",
        ],
        "properties": {
            "artifact_schema_id": {"const": "capture_receipt_v1"},
            "capture_receipt_id": {"type": "string"},
            "run_request_id": {"type": "string"},
            "prompt_render_id": {"type": "string"},
            "attempt_label": {"type": "string"},
            "runner_binding_id": {"type": "string"},
            "campaign_id": {"type": "string"},
            "captured_at": {"type": "string"},
            "model_name": {"type": "string"},
            "capture_method": {"type": "string"},
            "raw_response_filename": {"type": "string"},
            "raw_response_sha256": {"type": "string"},
            "prompt_body_sha256": {"type": "string"},
            "notes": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": False,
    }
    wave4c1.write_json(CAPTURE_RECEIPT_SCHEMA_PATH, payload)


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
            "raw_response_sha256",
            "response_meta_path",
            "capture_receipt_path",
            "capture_receipt_id",
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
            "raw_response_sha256": {"type": ["string", "null"]},
            "response_meta_path": {"type": "string"},
            "capture_receipt_path": {"type": "string"},
            "capture_receipt_id": {"type": ["string", "null"]},
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
        f"- scope: `{RUN_REQUEST_ID}` / `{ATTEMPT_LABEL}` only for Wave 4C2A",
        "",
        "## Accepted Import Sources",
        "",
        "- Saved provider response `.json` file imported as `response.json`",
        "- Saved provider response `.txt` file imported as `response.txt`",
        "- Clipboard import is intentionally out of scope for this wave",
        "",
        "## Required response_meta Fields",
        "",
        "- `run_request_id`",
        "- `prompt_render_id`",
        "- `attempt_label`",
        "- `runner_binding_id`",
        "- `campaign_id`",
        "- `captured_at`",
        "- `model_name`",
        "- `capture_method`",
        "- `raw_response_filename`",
        "- `raw_response_sha256`",
        "- `notes`",
        "",
        "## Required capture_receipt Fields",
        "",
        "- `capture_receipt_id`",
        "- `run_request_id`",
        "- `prompt_render_id`",
        "- `attempt_label`",
        "- `runner_binding_id`",
        "- `campaign_id`",
        "- `captured_at`",
        "- `model_name`",
        "- `capture_method`",
        "- `raw_response_filename`",
        "- `raw_response_sha256`",
        "- `prompt_body_sha256`",
        "- `notes`",
        "",
        "## Validation Rule",
        "",
        "- Validation passes only when the current raw file, `response_meta.json`, and `capture_receipt_v1.json` all bind to the fixed run identity and prompt render.",
        "- Finalize is blocked unless `capture_validation_report_v1.json` reports `overall_result = pass` for `attempt_01`.",
        "- No semantic repair or output coercion is allowed in this wave.",
        "",
    ]
    wave4c1.write_text(LOCAL_CAPTURE_CONTRACT_PATH, "\n".join(lines))


def write_operator_runbook() -> None:
    lines = [
        "# Wave 4C2A Operator Runbook",
        "",
        "Golden path for one real P1 run only.",
        "",
        "1. Prepare",
        "   - `python scripts/protocol_lab_wave4c2a_capture_import_bridge.py prepare`",
        "2. Locate prompt render",
        f"   - Open `{repo_rel(prompt_render_path())}` and use that exact rendered prompt for the external run.",
        "3. Obtain real output",
        f"   - Use the local Claude Code / Opus 4.6 path bound to `{PRIMARY_RUNNER_BINDING_ID}`.",
        "4. Save raw output",
        "   - Save the Claude Code provider response outside the attempt folder as either `.json` or `.txt` with no semantic edits.",
        "5. Run import",
        "   - Example JSON import:",
        f"     `python scripts/protocol_lab_wave4c2a_capture_import_bridge.py import --source \"C:\\path\\response.json\" --captured-at \"2026-03-15T21:00:00Z\" --model-name \"{PRIMARY_MODEL_NAME}\"`",
        "   - Example text import:",
        f"     `python scripts/protocol_lab_wave4c2a_capture_import_bridge.py import --source \"C:\\path\\response.txt\" --captured-at \"2026-03-15T21:00:00Z\" --model-name \"{PRIMARY_MODEL_NAME}\"`",
        "6. Run validate",
        "   - `python scripts/protocol_lab_wave4c2a_capture_import_bridge.py validate`",
        "7. Run finalize",
        "   - `python scripts/protocol_lab_wave4c2a_capture_import_bridge.py finalize`",
        "",
        "If no real raw response file is available, stop after prepare. The truthful blocker is: `real raw response not yet provided for import into attempt_01`.",
        "",
    ]
    wave4c1.write_text(RUNBOOK_PATH, "\n".join(lines))

def build_capture_instructions() -> str:
    return "\n".join(
        [
            "# Wave 4C2A Capture Instructions",
            "",
            f"- run_request_id: `{RUN_REQUEST_ID}`",
            f"- attempt_label: `{ATTEMPT_LABEL}`",
            f"- attempt_folder: `{repo_rel(attempt_dir())}`",
            f"- prompt_render_path: `{repo_rel(prompt_render_path())}`",
            "",
            "## Golden Path",
            "",
            f"- Use Claude Code with runner binding `{PRIMARY_RUNNER_BINDING_ID}` and model `{PRIMARY_MODEL_NAME}`.",
            "- Save one real raw provider response outside this folder as `.json` or `.txt`.",
            "- Import it with the Wave 4C2A bridge; do not copy-edit the content before import.",
            "- Then run validate and finalize.",
            "",
            "## Commands",
            "",
            "- `python scripts/protocol_lab_wave4c2a_capture_import_bridge.py prepare`",
            "- `python scripts/protocol_lab_wave4c2a_capture_import_bridge.py import --source <path> --captured-at <ISO8601> --model-name <name>`",
            "- `python scripts/protocol_lab_wave4c2a_capture_import_bridge.py validate`",
            "- `python scripts/protocol_lab_wave4c2a_capture_import_bridge.py finalize`",
            "",
            "## Wave Rule",
            "",
            "- Do not create `attempt_02` or broaden scope beyond this single P1+i2 run.",
            "",
        ]
    )


def real_raw_response_imported() -> bool:
    raw_file, blockers = discover_raw_response_file()
    if raw_file is None or blockers:
        return False
    if not response_meta_path().exists() or not capture_receipt_path().exists():
        return False
    try:
        meta = wave4c1.read_json(response_meta_path())
        receipt = wave4c1.read_json(capture_receipt_path())
    except Exception:  # noqa: BLE001
        return False
    actual_sha = compute_sha256(raw_file)
    return (
        maybe_str(meta.get("raw_response_filename")) == raw_file.name
        and maybe_str(meta.get("raw_response_sha256")) == actual_sha
        and maybe_str(receipt.get("raw_response_filename")) == raw_file.name
        and maybe_str(receipt.get("raw_response_sha256")) == actual_sha
        and maybe_str(receipt.get("capture_receipt_id")) is not None
    )


def prepare_phase() -> None:
    blockers = attempt_policy_blockers()
    if blockers:
        raise ValueError(blocker_note(blockers, "attempt_policy_blocked"))
    wave4c1.ensure_parse_report_schema()
    ensure_capture_receipt_schema()
    ensure_capture_validation_schema()
    write_local_capture_contract()
    write_operator_runbook()

    existing = rebind_existing_request(wave4c1.read_json(run_request_path()))
    if as_str(existing.get("protocol_id"), "protocol_id") != "p1_structured_contract_v1":
        raise ValueError("Selected run does not use p1_structured_contract_v1.")
    if as_str(existing.get("model_profile_id"), "model_profile_id") != PRIMARY_MODEL_PROFILE_ID:
        raise ValueError("Selected run does not use m_primary_strong_reasoning_v1.")

    bindings = wave4b.ensure_registry_map(REGISTRIES_ROOT / "runner_bindings_local_v1.json", "runner_binding_id")
    source_case = wave4c1.read_json(SOURCE_CASES_ROOT / FIXTURE_ID / "source_case_manifest_v1.json")
    request = wave4c1.build_run_request_payload(existing)
    request["notes"] = [
        "Wave 4C2A capture import bridge.",
        "Scope: NVDA P1+i2 only, runner binding rb_anthropic_claude_code_opus46_real_local_v1, attempt_01 only.",
        "Prepared for the first real Claude Code / Opus 4.6 Protocol Lab run with local-only raw capture expectations.",
        "Existing scaffold outputs are historical placeholders until this exact attempt finalizes.",
    ]
    runner_binding = as_dict(bindings[PRIMARY_RUNNER_BINDING_ID], "runner_binding")
    input_pack = wave4b.load_input_pack_payload(FIXTURE_ID, as_str(request.get("input_pack_id"), "input_pack_id"))

    wave4c1.write_json(run_request_path(), request)
    wave4c1.write_json(prompt_render_path(), wave4c1.build_prompt_render(request, source_case, runner_binding, input_pack))
    wave4c1.write_json(execution_trace_path(), wave4c1.build_prepare_trace(request, ATTEMPT_LABEL))

    current_attempt = attempt_dir()
    current_attempt.mkdir(parents=True, exist_ok=True)
    wave4c1.write_text(capture_instructions_path(), build_capture_instructions())
    if not real_raw_response_imported():
        wave4c1.write_json(response_meta_path(), response_meta_template())


def import_phase(source: str, captured_at: str | None, model_name: str | None, notes: list[str]) -> CaptureImportResult:
    prepare_phase()
    blockers = attempt_policy_blockers()
    if blockers:
        return CaptureImportResult(False, blockers, None, None, None, None)

    source_path = Path(source).expanduser()
    if not source_path.is_absolute():
        source_path = Path.cwd() / source_path
    source_path = source_path.resolve()
    if not source_path.exists() or not source_path.is_file():
        return CaptureImportResult(False, ["import_source_missing"], None, None, None, None)
    if path_is_relative_to(source_path, attempt_dir()):
        return CaptureImportResult(False, ["import_source_must_be_external"], None, None, None, None)

    suffix = source_path.suffix.lower()
    if suffix not in IMPORT_FILE_TO_CAPTURE_METHOD:
        return CaptureImportResult(False, ["unsupported_import_source_type"], None, None, None, None)
    if not captured_at:
        captured_at = file_mtime_iso(source_path)
    if not captured_at.strip() or not is_valid_iso8601(captured_at):
        return CaptureImportResult(False, ["captured_at_invalid"], None, None, None, None)
    if not model_name:
        model_name = PRIMARY_MODEL_NAME
    if not model_name.strip():
        return CaptureImportResult(False, ["model_name_missing"], None, None, None, None)

    destination = attempt_dir() / ("response.json" if suffix == ".json" else "response.txt")
    destination.parent.mkdir(parents=True, exist_ok=True)
    for candidate in RAW_RESPONSE_FILE_CANDIDATES:
        candidate_path = attempt_dir() / candidate
        if candidate_path != destination and candidate_path.exists():
            candidate_path.unlink()
    shutil.copyfile(source_path, destination)

    render = wave4c1.read_json(prompt_render_path())
    render_id = as_str(render.get("prompt_render_id"), "prompt_render_id")
    render_hash = prompt_hash(render)
    raw_sha = compute_sha256(destination)
    capture_method = IMPORT_FILE_TO_CAPTURE_METHOD[suffix]
    response_meta = {
        "run_request_id": RUN_REQUEST_ID,
        "prompt_render_id": render_id,
        "attempt_label": ATTEMPT_LABEL,
        "runner_binding_id": PRIMARY_RUNNER_BINDING_ID,
        "campaign_id": PRIMARY_RUNNER_CAMPAIGN_ID,
        "captured_at": captured_at,
        "model_name": model_name,
        "capture_method": capture_method,
        "raw_response_filename": destination.name,
        "raw_response_sha256": raw_sha,
        "notes": notes,
    }
    receipt = {
        "artifact_schema_id": "capture_receipt_v1",
        "capture_receipt_id": f"{RUN_REQUEST_ID}__{ATTEMPT_LABEL}__capture_receipt_v1",
        "run_request_id": RUN_REQUEST_ID,
        "prompt_render_id": render_id,
        "attempt_label": ATTEMPT_LABEL,
        "runner_binding_id": PRIMARY_RUNNER_BINDING_ID,
        "campaign_id": PRIMARY_RUNNER_CAMPAIGN_ID,
        "captured_at": captured_at,
        "model_name": model_name,
        "capture_method": capture_method,
        "raw_response_filename": destination.name,
        "raw_response_sha256": raw_sha,
        "prompt_body_sha256": render_hash,
        "notes": notes,
    }
    wave4c1.write_json(response_meta_path(), response_meta)
    wave4c1.write_json(capture_receipt_path(), receipt)
    for stale in (capture_validation_report_path(), parse_report_path()):
        if stale.exists():
            stale.unlink()
    return CaptureImportResult(True, [], repo_rel(destination), destination.name, raw_sha, capture_method)


def model_name_matches(value: str | None) -> bool:
    lowered = (value or "").lower()
    return "claude opus 4.6" in lowered or lowered == PRIMARY_MODEL_NAME.lower()


def require_non_empty_string(payload: dict[str, Any], key: str, blocker: str) -> list[str]:
    value = payload.get(key)
    return [] if isinstance(value, str) and value.strip() else [blocker]


def response_meta_blockers(payload: dict[str, Any], raw_file: Path, render: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for key in REQUIRED_RESPONSE_META_FIELDS:
        blockers.extend(require_non_empty_string(payload, key, "response_meta_incomplete"))
    notes = payload.get("notes")
    if notes is not None and not isinstance(notes, list):
        blockers.append("response_meta_notes_invalid")
    if maybe_str(payload.get("run_request_id")) != RUN_REQUEST_ID:
        blockers.append("response_meta_run_request_mismatch")
    if maybe_str(payload.get("prompt_render_id")) != as_str(render.get("prompt_render_id"), "prompt_render_id"):
        blockers.append("response_meta_prompt_render_mismatch")
    if maybe_str(payload.get("attempt_label")) != ATTEMPT_LABEL:
        blockers.append("response_meta_attempt_mismatch")
    if maybe_str(payload.get("runner_binding_id")) != PRIMARY_RUNNER_BINDING_ID:
        blockers.append("runner_binding_id_mismatch")
    if maybe_str(payload.get("campaign_id")) != PRIMARY_RUNNER_CAMPAIGN_ID:
        blockers.append("campaign_id_mismatch")
    if not model_name_matches(maybe_str(payload.get("model_name"))):
        blockers.append("model_name_mismatch")
    if not is_valid_iso8601(maybe_str(payload.get("captured_at")) or ""):
        blockers.append("captured_at_invalid")
    if maybe_str(payload.get("capture_method")) not in IMPORT_FILE_TO_CAPTURE_METHOD.values():
        blockers.append("capture_method_invalid")
    if maybe_str(payload.get("raw_response_filename")) != raw_file.name:
        blockers.append("response_meta_raw_response_filename_mismatch")
    if maybe_str(payload.get("raw_response_sha256")) != compute_sha256(raw_file):
        blockers.append("response_meta_raw_response_sha256_mismatch")
    return unique(blockers)


def capture_receipt_blockers(payload: dict[str, Any], raw_file: Path, render: dict[str, Any], meta: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if maybe_str(payload.get("artifact_schema_id")) != "capture_receipt_v1":
        blockers.append("capture_receipt_schema_mismatch")
    for key in REQUIRED_RECEIPT_FIELDS:
        blockers.extend(require_non_empty_string(payload, key, "capture_receipt_incomplete"))
    notes = payload.get("notes")
    if notes is not None and not isinstance(notes, list):
        blockers.append("capture_receipt_notes_invalid")
    if maybe_str(payload.get("run_request_id")) != RUN_REQUEST_ID:
        blockers.append("capture_receipt_run_request_mismatch")
    if maybe_str(payload.get("prompt_render_id")) != as_str(render.get("prompt_render_id"), "prompt_render_id"):
        blockers.append("capture_receipt_prompt_render_mismatch")
    if maybe_str(payload.get("attempt_label")) != ATTEMPT_LABEL:
        blockers.append("capture_receipt_attempt_mismatch")
    if maybe_str(payload.get("runner_binding_id")) != PRIMARY_RUNNER_BINDING_ID:
        blockers.append("capture_receipt_runner_binding_mismatch")
    if maybe_str(payload.get("campaign_id")) != PRIMARY_RUNNER_CAMPAIGN_ID:
        blockers.append("capture_receipt_campaign_mismatch")
    if not model_name_matches(maybe_str(payload.get("model_name"))):
        blockers.append("capture_receipt_model_name_mismatch")
    if maybe_str(payload.get("capture_method")) != maybe_str(meta.get("capture_method")):
        blockers.append("capture_receipt_capture_method_mismatch")
    if maybe_str(payload.get("captured_at")) != maybe_str(meta.get("captured_at")):
        blockers.append("capture_receipt_captured_at_mismatch")
    if maybe_str(payload.get("raw_response_filename")) != raw_file.name:
        blockers.append("capture_receipt_raw_response_filename_mismatch")
    actual_sha = compute_sha256(raw_file)
    if maybe_str(payload.get("raw_response_sha256")) != actual_sha:
        blockers.append("capture_receipt_raw_response_sha256_mismatch")
    if maybe_str(payload.get("prompt_body_sha256")) != prompt_hash(render):
        blockers.append("capture_receipt_prompt_body_sha256_mismatch")
    return unique(blockers)

def update_capture_gate_state(validation_passed: bool, blockers: list[str]) -> None:
    trace = wave4c1.read_json(execution_trace_path())
    request = wave4c1.read_json(run_request_path())
    if validation_passed:
        trace["run_state"] = "captured"
        trace["error_note"] = None
        request = wave4c1.update_request_status(request, "submitted", "Wave 4C2A capture validation passed for attempt_01.")
    else:
        trace["run_state"] = "capture_missing"
        trace["error_note"] = blocker_note(blockers, "capture_missing")
        request = wave4c1.update_request_status(
            request,
            "blocked",
            f"Wave 4C2A capture validation failed for attempt_01: {blocker_note(blockers, 'capture_missing')}",
        )
    trace["parse_status"] = "not_run"
    trace["postprocess_status"] = "not_run"
    trace["raw_response_path"] = None
    trace["finished_at"] = utc_now_iso()
    wave4c1.write_json(execution_trace_path(), trace)
    wave4c1.write_json(run_request_path(), request)


def validate_phase() -> CaptureValidationResult:
    blockers = attempt_policy_blockers()
    render: dict[str, Any] | None = None
    render_hash: str | None = None
    if not prompt_render_path().exists():
        blockers.append("prompt_render_missing")
    else:
        render = wave4c1.read_json(prompt_render_path())
        render_hash = prompt_hash(render)

    raw_file, raw_discovery_blockers = discover_raw_response_file()
    blockers.extend(raw_discovery_blockers)
    raw_sha: str | None = None
    if raw_file is None:
        blockers.append("raw_response_missing")
    else:
        raw_sha = compute_sha256(raw_file)

    meta: dict[str, Any] | None = None
    if not response_meta_path().exists():
        blockers.append("response_meta_missing")
    else:
        meta = wave4c1.read_json(response_meta_path())
        if raw_file is None or render is None:
            blockers.append("response_meta_not_verifiable")
        else:
            blockers.extend(response_meta_blockers(meta, raw_file, render))

    receipt: dict[str, Any] | None = None
    if not capture_receipt_path().exists():
        blockers.append("capture_receipt_missing")
    else:
        receipt = wave4c1.read_json(capture_receipt_path())
        if raw_file is None or render is None or meta is None:
            blockers.append("capture_receipt_not_verifiable")
        else:
            blockers.extend(capture_receipt_blockers(receipt, raw_file, render, meta))

    blockers = unique(blockers)
    passed = len(blockers) == 0
    val_raw_path: str | None = repo_rel(raw_file) if raw_file is not None else None
    val_raw_filename: str | None = raw_file.name if raw_file is not None else None
    val_receipt_id: str | None = maybe_str(receipt.get("capture_receipt_id")) if receipt is not None else None
    report = {
        "artifact_schema_id": "capture_validation_report_v1",
        "capture_validation_report_id": f"{RUN_REQUEST_ID}__{ATTEMPT_LABEL}__capture_validation_report_v1",
        "run_request_id": RUN_REQUEST_ID,
        "attempt_label": ATTEMPT_LABEL,
        "validated_at": utc_now_iso(),
        "overall_result": "pass" if passed else "fail",
        "blocker_codes": blockers,
        "raw_response_path": val_raw_path,
        "raw_response_filename": val_raw_filename,
        "raw_response_sha256": raw_sha,
        "response_meta_path": repo_rel(response_meta_path()),
        "capture_receipt_path": repo_rel(capture_receipt_path()),
        "capture_receipt_id": val_receipt_id,
        "prompt_render_id": maybe_str(render.get("prompt_render_id")) if render is not None else None,
        "prompt_body_sha256": render_hash,
        "notes": ["Wave 4C2A capture-integrity gate only; no semantic eval in this phase."],
    }
    wave4c1.write_json(capture_validation_report_path(), report)
    update_capture_gate_state(passed, blockers)
    return CaptureValidationResult(
        passed=passed,
        blockers=blockers,
        raw_response_path=val_raw_path,
        raw_response_filename=val_raw_filename,
        raw_response_sha256=raw_sha,
        capture_receipt_id=val_receipt_id,
    )


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
        request = wave4c1.update_request_status(wave4c1.read_json(run_request_path()), "failed", "Wave 4C2A parse failed for attempt_01.")
        wave4c1.write_json(execution_trace_path(), trace)
        wave4c1.write_json(run_request_path(), request)
        return FinalizeResult(True, False, blockers, "parse_failed", "failed", "not_run", 0, "not_run", False)

    if not parse.schema_validation_succeeded:
        blockers = ["schema_validation_failed"]
        trace = wave4c1.read_json(execution_trace_path())
        trace = wave4c1.update_trace(trace, "parse_failed", "failed", "not_run", parse.raw_response_path, repo_rel(parse_report_path()), ATTEMPT_LABEL, parse, blockers, 0)
        request = wave4c1.update_request_status(wave4c1.read_json(run_request_path()), "failed", "Wave 4C2A schema validation failed for attempt_01.")
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
    request_note = f"Wave 4C2A {run_state} for attempt_01." if not blockers else f"Wave 4C2A blocked for attempt_01: {blocker_note(blockers, 'postprocess_failed')}"
    request = wave4c1.update_request_status(wave4c1.read_json(run_request_path()), request_status, request_note)
    wave4c1.write_json(execution_trace_path(), trace)
    wave4c1.write_json(run_request_path(), request)

    truly_finalized = run_state in {"validated", "reviewed"} and evidence_count > 0
    return FinalizeResult(True, truly_finalized, blockers, run_state, "passed", postprocess_status, evidence_count, resolution_result, True)


def current_parse_report_payload() -> dict[str, Any]:
    if parse_report_path().exists():
        return wave4c1.read_json(parse_report_path())
    outcome = wave4c1.parse_raw_response(RUN_REQUEST_ID, ATTEMPT_LABEL)
    return wave4c1.build_parse_report(RUN_REQUEST_ID, ATTEMPT_LABEL, outcome)


def current_trace_payload() -> dict[str, Any]:
    if execution_trace_path().exists():
        return wave4c1.read_json(execution_trace_path())
    return {
        "run_state": "awaiting_capture",
        "parse_status": "not_run",
        "postprocess_status": "not_run",
        "error_note": MANUAL_CAPTURE_BLOCKER,
    }

def load_real_public_artifacts() -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    brief = wave4c1.read_json(change_brief_path()) if change_brief_path().exists() else None
    bundle = wave4c1.read_json(evidence_bundle_path()) if evidence_bundle_path().exists() else None
    resolution = wave4c1.read_json(evidence_resolution_path()) if evidence_resolution_path().exists() else None
    eval_payload = wave4c1.read_json(eval_path()) if eval_path().exists() else None
    if brief is not None and maybe_str(brief.get("artifact_status")) != "complete":
        brief = None
    if bundle is not None:
        items = bundle.get("items")
        if maybe_str(bundle.get("artifact_status")) != "complete" or not isinstance(items, list) or len(cast("list[Any]", items)) == 0:
            bundle = None
    if resolution is not None:
        summary = resolution.get("resolution_summary")
        if not isinstance(summary, dict) or cast("dict[str, Any]", summary).get("overall_result") != "pass":
            resolution = None
    if eval_payload is not None and maybe_str(eval_payload.get("artifact_status")) not in {"complete", "pending"}:
        eval_payload = None
    return brief, bundle, resolution, eval_payload


def current_truly_finalized() -> bool:
    trace = current_trace_payload()
    brief, bundle, resolution, _ = load_real_public_artifacts()
    return maybe_str(trace.get("run_state")) in {"validated", "reviewed"} and brief is not None and bundle is not None and resolution is not None


def current_non_empty_evidence_materialized() -> bool:
    _, bundle, resolution, _ = load_real_public_artifacts()
    return bundle is not None and resolution is not None


def current_biggest_remaining_blocker(validation: CaptureValidationResult, finalize: FinalizeResult) -> str:
    if not real_raw_response_imported():
        return MANUAL_CAPTURE_BLOCKER
    if not validation.passed:
        return blocker_note(validation.blockers, "capture_validation_failed")
    if not finalize.truly_finalized:
        return blocker_note(finalize.blockers, "finalize_blocked")
    return "none"


def build_review_notes(validation: CaptureValidationResult, finalize: FinalizeResult, biggest_blocker: str) -> str:
    run_request = wave4c1.read_json(run_request_path())
    prompt_render = wave4c1.read_json(prompt_render_path())
    parse_report = current_parse_report_payload()
    trace = current_trace_payload()
    brief, bundle, resolution, eval_payload = load_real_public_artifacts()

    summary_text = "[not_available]"
    lead_text = "[not_available]"
    needle_text = "[not_available]"
    novelty_text = "[not_available]"
    caveat_text = "[not_available]"
    caveat_type = "[not_available]"
    evidence_rows: list[str] = ["- [none]"]
    resolution_lines = [
        "- overall_result: `[not_available]`",
        "- total_evidence_items: `[not_available]`",
        "- failed_item_count: `[not_available]`",
    ]
    if brief is not None:
        summary_text = maybe_str(as_dict(brief.get("summary_one_liner"), "summary_one_liner").get("text")) or "[not_available]"
        lead_text = maybe_str(as_dict(brief.get("lead_shift"), "lead_shift").get("text")) or "[not_available]"
        needle_text = maybe_str(as_dict(brief.get("needle_change"), "needle_change").get("text")) or "[not_available]"
        novelty_text = maybe_str(as_dict(brief.get("novelty_vs_reuse"), "novelty_vs_reuse").get("text")) or "[not_available]"
        main_caveat = as_dict(brief.get("main_caveat"), "main_caveat")
        caveat_text = maybe_str(main_caveat.get("text")) or "[not_available]"
        caveat_type = maybe_str(main_caveat.get("caveat_type")) or "[not_available]"
    if bundle is not None:
        evidence_rows = []
        for item in as_list(bundle.get("items"), "evidence_bundle.items")[:6]:
            evidence = as_dict(item, "evidence_item")
            evidence_rows.append(
                "- "
                + f"{evidence.get('evidence_id')} | {evidence.get('year_label')} | {evidence.get('paragraph_id')} | "
                + (maybe_str(evidence.get("quote_text")) or "[not_available]")
            )
    if resolution is not None:
        summary = as_dict(resolution.get("resolution_summary"), "resolution_summary")
        resolution_lines = [
            f"- overall_result: `{summary.get('overall_result')}`",
            f"- total_evidence_items: `{summary.get('total_evidence_items')}`",
            f"- failed_item_count: `{summary.get('failed_item_count')}`",
        ]

    lines = [
        "# Wave 4C2A Review Notes",
        "",
        f"- generated_at: `{utc_now_iso()}`",
        f"- run_request_id: `{RUN_REQUEST_ID}`",
        f"- attempt_label: `{ATTEMPT_LABEL}`",
        f"- biggest_remaining_blocker: `{biggest_blocker}`",
    ]
    if not real_raw_response_imported():
        lines.append(f"- manual_blocker: `{MANUAL_CAPTURE_BLOCKER}`")
    lines.extend(
        [
            "",
            "Prompt metadata:",
            f"- protocol_id: `{run_request.get('protocol_id')}`",
            f"- input_pack_id: `{run_request.get('input_pack_id')}`",
            f"- model_profile_id: `{run_request.get('model_profile_id')}`",
            f"- runner_binding_id: `{run_request.get('runner_binding_id')}`",
            f"- prompt_render_id: `{prompt_render.get('prompt_render_id')}`",
            f"- prompt_body_sha256: `{prompt_hash(prompt_render)}`",
            "",
            "Parser summary:",
            f"- raw_response_exists: `{parse_report.get('raw_response_exists')}`",
            f"- raw_response_path: `{parse_report.get('raw_response_path')}`",
            f"- raw_response_format: `{parse_report.get('raw_response_format')}`",
            f"- parse_succeeded: `{parse_report.get('parse_succeeded')}`",
            f"- schema_validation_succeeded: `{parse_report.get('schema_validation_succeeded')}`",
            f"- normalizations_applied: `{parse_report.get('normalizations_applied')}`",
            f"- parse_warnings: `{parse_report.get('parse_warnings')}`",
            f"- parser_error_note: `{parse_report.get('parser_error_note')}`",
            "",
            "Run trace summary:",
            f"- run_state: `{trace.get('run_state')}`",
            f"- parse_status: `{trace.get('parse_status')}`",
            f"- postprocess_status: `{trace.get('postprocess_status')}`",
            f"- blocker_summary: `{trace.get('error_note') or biggest_blocker}`",
            "",
            f"- summary_one_liner: `{summary_text}`",
            f"- lead_shift: `{lead_text}`",
            f"- needle_change: `{needle_text}`",
            f"- novelty_vs_reuse: `{novelty_text}`",
            f"- main_caveat: `{caveat_text}`",
            f"- main_caveat_type: `{caveat_type}`",
            "",
            "Evidence rows:",
        ]
    )
    lines.extend(evidence_rows)
    lines.extend(["", "Evidence-resolution result:"])
    lines.extend(resolution_lines)
    if eval_payload is not None:
        lines.extend(["", "Eval summary:", f"- artifact_status: `{eval_payload.get('artifact_status')}`", f"- hard_checks: `{eval_payload.get('hard_checks')}`"])
    if validation.capture_receipt_id is not None:
        lines.extend(["", f"- capture_receipt_id: `{validation.capture_receipt_id}`"])
    if finalize.attempted:
        lines.extend([f"- finalize_run_state: `{finalize.run_state}`", f"- finalize_blockers: `{finalize.blockers}`"])
    lines.append("")
    return "\n".join(lines)


def packet_paths_for_stamp(stamp: str) -> tuple[Path, Path]:
    name = f"wave4c2a_first_real_p1_{stamp}"
    return REPO_ROOT / name, REPO_ROOT / f"{name}.zip"


def build_packet_readme(summary: WaveSummary) -> str:
    lines = [
        f"# {summary.packet_dir.name}",
        "",
        "Wave 4C2A capture import bridge packet.",
        "",
        "## Summary",
        f"- capture_import_bridge_implemented: `{summary.capture_import_bridge_implemented}`",
        f"- real_raw_response_imported: `{summary.real_raw_response_imported}`",
        f"- capture_validation_passed: `{summary.capture_validation_passed}`",
        f"- p1_truly_finalized: `{summary.p1_truly_finalized}`",
        f"- non_empty_evidence_materialized: `{summary.non_empty_evidence_materialized}`",
        f"- biggest_remaining_blocker: `{summary.biggest_remaining_blocker}`",
        "",
    ]
    return "\n".join(lines)


def build_packet(summary: WaveSummary) -> tuple[Path, Path]:
    packet_dir, zip_path = summary.packet_dir, summary.zip_path
    if packet_dir.exists():
        shutil.rmtree(packet_dir)
    if zip_path.exists():
        zip_path.unlink()
    files: list[Path] = [
        Path("scripts/protocol_lab_wave4c2a_capture_import_bridge.py"),
        Path("scripts/tests/test_protocol_lab_wave4c2a_capture_import_bridge.py"),
        Path(repo_rel(CAPTURE_RECEIPT_SCHEMA_PATH)),
        Path(repo_rel(CAPTURE_VALIDATION_SCHEMA_PATH)),
        Path(repo_rel(wave4c1.PARSE_REPORT_SCHEMA_PATH)),
        Path(repo_rel(LOCAL_CAPTURE_CONTRACT_PATH)),
        Path(repo_rel(RUNBOOK_PATH)),
        Path(repo_rel(BRIDGE_REPORT_PATH)),
        Path(repo_rel(REVIEW_NOTES_PATH)),
        Path(repo_rel(run_request_path())),
        Path(repo_rel(prompt_render_path())),
        Path(repo_rel(execution_trace_path())),
        Path(repo_rel(capture_instructions_path())),
        Path(repo_rel(response_meta_path())),
    ]
    for local_artifact in (capture_receipt_path(), capture_validation_report_path(), parse_report_path()):
        if local_artifact.exists():
            files.append(Path(repo_rel(local_artifact)))
    for name in RAW_RESPONSE_FILE_CANDIDATES:
        raw_path = attempt_dir() / name
        if raw_path.exists():
            files.append(Path(repo_rel(raw_path)))
    if summary.p1_truly_finalized:
        for public_artifact in (change_brief_path(), evidence_bundle_path(), evidence_resolution_path(), eval_path()):
            if public_artifact.exists():
                files.append(Path(repo_rel(public_artifact)))
    files = list(dict.fromkeys([path for path in files if (REPO_ROOT / path).exists()]))
    for rel in files:
        source = REPO_ROOT / rel
        destination = packet_dir / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    manifest = "# Relevant Files Manifest\n\n" + "\n".join(f"- {path.as_posix()}" for path in files) + "\n"
    wave4c1.write_text(packet_dir / "README.md", build_packet_readme(summary))
    wave4c1.write_text(packet_dir / "relevant_files_manifest.md", manifest)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for file_path in packet_dir.rglob("*"):
            if file_path.is_file():
                handle.write(file_path, file_path.relative_to(REPO_ROOT).as_posix())
    return packet_dir, zip_path

def write_reports_and_packet(validation: CaptureValidationResult, finalize: FinalizeResult) -> WaveSummary:
    packet_dir, zip_path = packet_paths_for_stamp(utc_stamp())
    summary = WaveSummary(
        packet_dir=packet_dir,
        zip_path=zip_path,
        capture_import_bridge_implemented=True,
        real_raw_response_imported=real_raw_response_imported(),
        capture_validation_passed=validation.passed,
        p1_truly_finalized=current_truly_finalized(),
        non_empty_evidence_materialized=current_non_empty_evidence_materialized(),
        biggest_remaining_blocker=current_biggest_remaining_blocker(validation, finalize),
    )

    bridge_report = "\n".join(
        [
            "# Wave 4C2A Capture Import Bridge Report",
            "",
            f"- generated_at: `{utc_now_iso()}`",
            f"- run_request_id: `{RUN_REQUEST_ID}`",
            f"- attempt_label: `{ATTEMPT_LABEL}`",
            f"- capture_import_bridge_implemented: `{summary.capture_import_bridge_implemented}`",
            f"- real_raw_response_imported: `{summary.real_raw_response_imported}`",
            f"- capture_validation_passed: `{summary.capture_validation_passed}`",
            f"- validation_blockers: `{validation.blockers}`",
            f"- finalize_attempted: `{finalize.attempted}`",
            f"- p1_truly_finalized: `{summary.p1_truly_finalized}`",
            f"- non_empty_evidence_materialized: `{summary.non_empty_evidence_materialized}`",
            f"- packet_folder_path: `{repo_rel(summary.packet_dir)}`",
            f"- zip_path: `{repo_rel(summary.zip_path)}`",
            f"- biggest_remaining_blocker: `{summary.biggest_remaining_blocker}`",
            "",
        ]
    )
    wave4c1.write_text(BRIDGE_REPORT_PATH, bridge_report)
    wave4c1.write_text(REVIEW_NOTES_PATH, build_review_notes(validation, finalize, summary.biggest_remaining_blocker))
    build_packet(summary)
    return summary


def print_summary(summary: WaveSummary) -> None:
    print(f"packet folder path: {summary.packet_dir.resolve()}")
    print(f"zip path: {summary.zip_path.resolve()}")
    print(f"whether the capture import bridge was implemented: {yes_no(summary.capture_import_bridge_implemented)}")
    print(f"whether a real raw response was imported: {yes_no(summary.real_raw_response_imported)}")
    print(f"whether capture validation passed: {yes_no(summary.capture_validation_passed)}")
    print(f"whether the P1 run was truly finalized: {yes_no(summary.p1_truly_finalized)}")
    print(f"whether non-empty evidence bundles were materialized: {yes_no(summary.non_empty_evidence_materialized)}")
    print(f"biggest remaining blocker after Wave 4C2A: {summary.biggest_remaining_blocker}")


def run_all() -> WaveSummary:
    prepare_phase()
    validation = validate_phase()
    finalize = finalize_phase()
    return write_reports_and_packet(validation, finalize)


def load_existing_validation_result() -> CaptureValidationResult:
    report = wave4c1.read_json(capture_validation_report_path())
    return CaptureValidationResult(
        passed=report.get("overall_result") == "pass",
        blockers=[item for item in report.get("blocker_codes", []) if isinstance(item, str)],
        raw_response_path=maybe_str(report.get("raw_response_path")),
        raw_response_filename=maybe_str(report.get("raw_response_filename")),
        raw_response_sha256=maybe_str(report.get("raw_response_sha256")),
        capture_receipt_id=maybe_str(report.get("capture_receipt_id")),
    )


def run_finalize_command() -> WaveSummary:
    validation = validate_phase() if not capture_validation_report_path().exists() else load_existing_validation_result()
    finalize = finalize_phase()
    return write_reports_and_packet(validation, finalize)


def main() -> int:
    parser = argparse.ArgumentParser(description="Wave 4C2A capture import bridge")
    parser.add_argument("phase", nargs="?", choices=["prepare", "import", "validate", "finalize", "all"], default="all")
    parser.add_argument("--source", dest="source")
    parser.add_argument("--captured-at", dest="captured_at")
    parser.add_argument("--model-name", dest="model_name")
    parser.add_argument("--note", dest="notes", action="append", default=[])
    args = parser.parse_args()

    if args.phase == "prepare":
        prepare_phase()
        print("Wave 4C2A prepare complete.")
        return 0

    if args.phase == "import":
        if not args.source:
            print("import requires --source (--captured-at and --model-name are optional; defaults: source file mtime, PRIMARY_MODEL_NAME)")
            return 1
        result = import_phase(args.source, args.captured_at, args.model_name, cast("list[str]", args.notes))
        if not result.imported:
            print(f"real raw response imported: {yes_no(result.imported)}")
            print(f"import blockers: {result.blockers}")
            return 1
        print(f"real raw response imported: {yes_no(result.imported)}")
        print(f"raw_response_path: {result.raw_response_path}")
        print(f"raw_response_sha256: {result.raw_response_sha256}")
        return 0

    if args.phase == "validate":
        result = validate_phase()
        print(f"capture validation passed: {yes_no(result.passed)}")
        print(f"capture validation blockers: {result.blockers}")
        return 0 if result.passed else 1

    if args.phase == "finalize":
        summary = run_finalize_command()
        print_summary(summary)
        return 0 if summary.p1_truly_finalized else 1

    summary = run_all()
    print_summary(summary)
    return 0 if summary.p1_truly_finalized else 1


if __name__ == "__main__":
    raise SystemExit(main())
