from __future__ import annotations

import argparse
import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import protocol_lab_wave4b_reviewability as wave4b

REPO_ROOT = Path(__file__).resolve().parents[1]
BUSINESS_ROOT = REPO_ROOT / "public" / "data" / "business_document_protocol_lab"
RUNS_ROOT = BUSINESS_ROOT / "runs"
EVALS_ROOT = BUSINESS_ROOT / "evals"
REGISTRIES_ROOT = BUSINESS_ROOT / "registries"
SOURCE_CASES_ROOT = BUSINESS_ROOT / "source_cases"
REPORTS_ROOT = REPO_ROOT / "reports" / "protocol_lab"
RAW_RUNS_ROOT = REPORTS_ROOT / "raw_runs"

FIXTURE_ID = "NVDA_2024_2025_10k_item1a"
TARGET_RUN_IDS = [
    "NVDA_2024_2025_10k_item1a__p1_structured_contract_v1__m_primary_strong_reasoning_v1__i2_tagged_document_packet_v1",
    "NVDA_2024_2025_10k_item1a__p2_tagged_input_contract_v1__m_primary_strong_reasoning_v1",
]
PRIMARY_MODEL_PROFILE_ID = "m_primary_strong_reasoning_v1"
PRIMARY_RUNNER_BINDING_ID = "rb_openai_gpt53codex_real_local_v1"
PRIMARY_RUNNER_CAMPAIGN_ID = "openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27"
COMPARISON_VIEW_PATH = (
    BUSINESS_ROOT
    / "comparisons"
    / FIXTURE_ID
    / "nvda_ablation_tag_awareness_v1"
    / "comparison_view_v1.json"
)
PARSE_REPORT_SCHEMA_PATH = REPORTS_ROOT / "parse_report_v1.schema.json"
HUMAN_EVAL_INPUT_PATH = REPORTS_ROOT / "wave4c1_nvda_human_eval_input.json"
EXECUTION_REPORT_PATH = REPORTS_ROOT / "wave4c15_capture_boundary_execution_report.md"
REVIEW_NOTES_PATH = REPORTS_ROOT / "wave4c15_capture_boundary_review_notes.md"
REVIEW_PACKET_MD_PATH = REPORTS_ROOT / "wave4c15_capture_boundary_review_packet.md"
RED_TEAM_BRIEF_PATH = REPORTS_ROOT / "wave4c1_nvda_desktop_red_team_brief.md"
BOUNDARY_CLEANUP_NOTES_PATH = REPORTS_ROOT / "wave4c15_boundary_cleanup_notes.md"
RUN_STATE_MODEL_UPDATE_PATH = REPORTS_ROOT / "run_state_model_wave4c15.md"
LOCAL_CAPTURE_CONTRACT_PATH = REPORTS_ROOT / "local_capture_contract_v1.md"
SMOKE_REPORT_PATH = REPORTS_ROOT / "wave4c15_smoke_run_report.md"
SMOKE_ROOT = REPORTS_ROOT / "wave4c15_smoke"
SMOKE_RUN_ID = f"{FIXTURE_ID}__wave4c15_capture_handshake_v1__{PRIMARY_MODEL_PROFILE_ID}"
SMOKE_PROMPT_RENDER_PATH = SMOKE_ROOT / "smoke_prompt_render_v1.json"
SMOKE_EXECUTION_TRACE_PATH = SMOKE_ROOT / "smoke_execution_trace_v1.json"
SMOKE_CAPTURE_ROOT = RAW_RUNS_ROOT / FIXTURE_ID / SMOKE_RUN_ID / "main" / "attempt_01"

RAW_RESPONSE_FILE_CANDIDATES = ("response.json", "response.txt")
REQUIRED_RESPONSE_META_FIELDS = ("captured_at", "runner_binding_id", "campaign_id", "model_name", "capture_method")
ALLOWED_NORMALIZATIONS = ["utf8_bom_trim", "outer_whitespace_trim", "single_fenced_wrapper_trim"]
ALLOWED_CAVEAT_TYPES = {"input_limit", "evidence_limit", "method_limit", "comparison_limit", "other"}
BAND_SCORES = {"strong": 3, "fair": 2, "weak": 1}
RUBRIC_KEYS = ["evidence_grounding", "novelty_separation", "specificity", "caveat_honesty", "overall_usefulness"]
SECTION_LABELS = {
    "summary_one_liner": "Summary One-Liner",
    "lead_shift": "Lead Shift",
    "needle_change": "Needle Change",
    "novelty_vs_reuse": "Novelty vs Reuse",
    "main_caveat": "Main Caveat",
}
FENCED_JSON_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)
ATTEMPT_LABEL_RE = re.compile(r"^attempt_(\d+)$")


@dataclass
class ParseOutcome:
    raw_response_path: str | None
    raw_response_exists: bool
    raw_response_format: str | None
    parse_succeeded: bool
    schema_validation_succeeded: bool
    coercion_or_repair_applied: bool
    parse_warnings: list[str]
    parser_error_note: str | None
    normalizations_applied: list[str]
    envelope: dict[str, Any] | None


@dataclass
class ResponseMetaOutcome:
    response_meta_path: str
    response_meta_exists: bool
    response_meta_valid: bool
    validation_errors: list[str]
    payload: dict[str, Any] | None


@dataclass
class SmokeSummary:
    smoke_passed: bool
    run_state: str
    parse_status: str
    blocker_codes: list[str]
    raw_response_path: str | None
    response_meta_path: str
    parse_report_path: str


@dataclass
class RunFinalizeResult:
    run_request_id: str
    run_succeeded: bool
    run_state: str
    parse_status: str
    postprocess_status: str
    raw_response_path: str | None
    parse_report_path: str
    evidence_item_count: int
    evidence_resolution_overall_result: str
    human_eval_present: bool
    blocker_notes: list[str]
    attempt_label: str | None = None
    downstream_artifacts_materialized: bool = False


@dataclass
class Wave4c15Summary:
    packet_dir: Path
    zip_path: Path
    boundary_cleanup_completed: bool
    run_state_semantics_updated: bool
    smoke_passed: bool
    nvda_rerun_attempted: bool
    real_non_empty_evidence_materialized: bool
    biggest_remaining_blocker: str
    takeaway: str
    run_results: list[RunFinalizeResult]
    smoke_result: SmokeSummary


@dataclass
class FinalizeArtifacts:
    results: list[RunFinalizeResult]
    comparison: dict[str, Any]
    comparison_is_real: bool
    takeaway: str
    run_requests: dict[str, dict[str, Any]]
    traces: dict[str, dict[str, Any]]
    parse_reports: dict[str, dict[str, Any]]
    evidence_bundles: dict[str, dict[str, Any]]
    briefs: dict[str, dict[str, Any]]
    resolutions: dict[str, dict[str, Any]]
    evals: dict[str, dict[str, Any]]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected JSON object at {path}.")
    return cast("dict[str, Any]", payload)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def repo_rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


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


def run_dir(run_request_id: str) -> Path:
    return RUNS_ROOT / FIXTURE_ID / run_request_id


def run_request_path(run_request_id: str) -> Path:
    return run_dir(run_request_id) / "run_request_v1.json"


def prompt_render_path(run_request_id: str) -> Path:
    return run_dir(run_request_id) / "prompt_render_v1.json"


def execution_trace_path(run_request_id: str) -> Path:
    return run_dir(run_request_id) / "execution_trace_v1.json"


def change_brief_path(run_request_id: str) -> Path:
    return run_dir(run_request_id) / "change_brief_output_v1.json"


def evidence_bundle_path(run_request_id: str) -> Path:
    return run_dir(run_request_id) / "evidence_bundle_v1.json"


def evidence_resolution_path(run_request_id: str) -> Path:
    return run_dir(run_request_id) / "evidence_resolution_v1.json"


def eval_path(run_request_id: str) -> Path:
    return EVALS_ROOT / FIXTURE_ID / run_request_id / "change_brief_eval_v1.json"


def raw_attempt_root(run_request_id: str) -> Path:
    return RAW_RUNS_ROOT / FIXTURE_ID / run_request_id / "main"


def validate_attempt_label(attempt_label: str) -> str:
    if ATTEMPT_LABEL_RE.fullmatch(attempt_label) is None:
        raise ValueError(f"Invalid attempt label: {attempt_label}")
    return attempt_label


def attempt_sort_key(attempt_label: str) -> int:
    match = ATTEMPT_LABEL_RE.fullmatch(validate_attempt_label(attempt_label))
    assert match is not None
    return int(match.group(1))


def attempt_dir(run_request_id: str, attempt_label: str) -> Path:
    return raw_attempt_root(run_request_id) / validate_attempt_label(attempt_label)


def parse_report_path(run_request_id: str, attempt_label: str) -> Path:
    return attempt_dir(run_request_id, attempt_label) / "parse_report_v1.json"


def capture_instructions_path(run_request_id: str, attempt_label: str) -> Path:
    return attempt_dir(run_request_id, attempt_label) / "CAPTURE_INSTRUCTIONS.md"


def response_meta_path(run_request_id: str, attempt_label: str) -> Path:
    return attempt_dir(run_request_id, attempt_label) / "response_meta.json"


def require_non_empty_string(value: Any, label: str) -> list[str]:
    return [] if isinstance(value, str) and value.strip() else [f"{label} must be a non-empty string."]


def inspect_response_meta(run_request_id: str, attempt_label: str) -> ResponseMetaOutcome:
    meta_path = response_meta_path(run_request_id, attempt_label)
    if not meta_path.exists():
        return ResponseMetaOutcome(repo_rel(meta_path), False, False, ["response_meta_missing"], None)
    try:
        payload = read_json(meta_path)
    except Exception:  # noqa: BLE001
        return ResponseMetaOutcome(repo_rel(meta_path), True, False, ["response_meta_unreadable"], None)

    validation_errors: list[str] = []
    for field_name in REQUIRED_RESPONSE_META_FIELDS:
        validation_errors.extend(require_non_empty_string(payload.get(field_name), f"response_meta.{field_name}"))
    if validation_errors:
        return ResponseMetaOutcome(repo_rel(meta_path), True, False, ["response_meta_incomplete"], payload)
    return ResponseMetaOutcome(repo_rel(meta_path), True, True, [], payload)


def list_attempt_labels(run_request_id: str) -> list[str]:
    root = raw_attempt_root(run_request_id)
    if not root.exists():
        return []
    labels = [path.name for path in root.iterdir() if path.is_dir() and ATTEMPT_LABEL_RE.fullmatch(path.name)]
    return sorted(labels, key=attempt_sort_key)


def latest_attempt_label(run_request_id: str) -> str | None:
    labels = list_attempt_labels(run_request_id)
    return labels[-1] if labels else None


def selected_or_latest_attempt_label(run_request_id: str, requested_attempt_label: str | None = None) -> str:
    if requested_attempt_label is not None:
        return validate_attempt_label(requested_attempt_label)
    latest = latest_attempt_label(run_request_id)
    return latest if latest is not None else "attempt_01"


def ensure_prepare_attempt_label(run_request_id: str, requested_attempt_label: str | None = None) -> str:
    selected = selected_or_latest_attempt_label(run_request_id, requested_attempt_label)
    attempt_dir(run_request_id, selected).mkdir(parents=True, exist_ok=True)
    return selected


def canonical_expected_artifact_paths(run_request_id: str) -> dict[str, str]:
    return {
        "change_brief_output_path": repo_rel(change_brief_path(run_request_id)),
        "evidence_bundle_path": repo_rel(evidence_bundle_path(run_request_id)),
        "change_brief_eval_path": repo_rel(eval_path(run_request_id)),
    }


def unique_codes(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def public_blocker_note(blockers: list[str], fallback: str) -> str:
    codes = [code for code in unique_codes(blockers) if code]
    return "; ".join(codes) if codes else fallback


def yes_no(flag: bool) -> str:
    return "yes" if flag else "no"


def ensure_parse_report_schema() -> None:
    payload = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "reports/protocol_lab/parse_report_v1.schema.json",
        "title": "Protocol Lab Local Parse Report v1",
        "type": "object",
        "required": [
            "artifact_schema_id",
            "parse_report_id",
            "run_request_id",
            "step_label",
            "attempt_label",
            "generated_at",
            "raw_response_path",
            "raw_response_exists",
            "raw_response_format",
            "parse_succeeded",
            "schema_validation_succeeded",
            "coercion_or_repair_applied",
            "parse_warnings",
            "parser_error_note",
            "normalizations_applied",
            "allowed_normalizations",
        ],
        "properties": {
            "artifact_schema_id": {"const": "parse_report_v1"},
            "parse_report_id": {"type": "string"},
            "run_request_id": {"type": "string"},
            "step_label": {"type": ["string", "null"]},
            "attempt_label": {"type": "string"},
            "generated_at": {"type": "string"},
            "raw_response_path": {"type": ["string", "null"]},
            "raw_response_exists": {"type": "boolean"},
            "raw_response_format": {"type": ["string", "null"]},
            "parse_succeeded": {"type": "boolean"},
            "schema_validation_succeeded": {"type": "boolean"},
            "coercion_or_repair_applied": {"const": False},
            "parse_warnings": {"type": "array", "items": {"type": "string"}},
            "parser_error_note": {"type": ["string", "null"]},
            "normalizations_applied": {"type": "array", "items": {"type": "string"}},
            "allowed_normalizations": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": False,
    }
    write_json(PARSE_REPORT_SCHEMA_PATH, payload)


def discover_raw_response_file(run_request_id: str, attempt_label: str) -> tuple[Path | None, str | None]:
    attempt_path = attempt_dir(run_request_id, attempt_label)
    for candidate in RAW_RESPONSE_FILE_CANDIDATES:
        candidate_path = attempt_path / candidate
        if candidate_path.exists():
            raw_format = "json" if candidate.endswith(".json") else "text"
            return candidate_path, raw_format
    return None, None


def normalize_transport_text(raw_text: str) -> tuple[str, list[str], list[str]]:
    text = raw_text
    normalizations: list[str] = []
    warnings: list[str] = []
    if text.startswith("\ufeff"):
        text = text[1:]
        normalizations.append("utf8_bom_trim")
    trimmed = text.strip()
    if trimmed != text:
        text = trimmed
        normalizations.append("outer_whitespace_trim")
    fence = FENCED_JSON_RE.match(text)
    if fence is not None:
        text = fence.group(1).strip()
        normalizations.append("single_fenced_wrapper_trim")
    if "```" in text:
        warnings.append("fence_marker_present_after_normalization")
    return text, normalizations, warnings


def require_string(value: Any, label: str) -> list[str]:
    return [] if isinstance(value, str) else [f"{label} must be a string."]


def require_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        return [f"{label} must be an array of strings."]
    items = cast("list[Any]", value)
    return [f"{label}[{idx}] must be a string." for idx, entry in enumerate(items) if not isinstance(entry, str)]


def validate_section_payload(payload: Any, label: str, require_caveat_type: bool) -> list[str]:
    if not isinstance(payload, dict):
        return [f"change_brief.{label} must be an object."]
    d = cast("dict[str, Any]", payload)
    expected: set[str] = {"text", "evidence_ids"} | ({"caveat_type"} if require_caveat_type else set[str]())
    errors: list[str] = []
    if set(d.keys()) != expected:
        errors.append(f"change_brief.{label} keys must be exactly {sorted(expected)}.")
    errors.extend(require_string(d.get("text"), f"change_brief.{label}.text"))
    errors.extend(require_string_list(d.get("evidence_ids"), f"change_brief.{label}.evidence_ids"))
    if require_caveat_type:
        caveat = d.get("caveat_type")
        if not isinstance(caveat, str) or caveat not in ALLOWED_CAVEAT_TYPES:
            errors.append("change_brief.main_caveat.caveat_type is invalid.")
    return errors


def validate_source_locator(payload: Any, label: str) -> list[str]:
    if not isinstance(payload, dict):
        return [f"{label} must be an object."]
    d = cast("dict[str, Any]", payload)
    expected = {
        "accession_number",
        "filing_date",
        "form_type",
        "section_id",
        "source_path",
        "char_start",
        "char_end",
    }
    errors: list[str] = []
    if set(d.keys()) != expected:
        errors.append(f"{label} keys must be exactly {sorted(expected)}.")
    for key in ("accession_number", "filing_date", "source_path"):
        value = d.get(key)
        if value is not None and not isinstance(value, str):
            errors.append(f"{label}.{key} must be string|null.")
    for key in ("form_type", "section_id"):
        if not isinstance(d.get(key), str):
            errors.append(f"{label}.{key} must be string.")
    for key in ("char_start", "char_end"):
        value = d.get(key)
        if value is not None and not isinstance(value, int):
            errors.append(f"{label}.{key} must be integer|null.")
    return errors


def validate_semantic_envelope(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["Top-level payload must be an object."]
    top = cast("dict[str, Any]", payload)
    errors: list[str] = []
    if set(top.keys()) != {"change_brief", "evidence_bundle"}:
        errors.append("Top-level keys must be exactly `change_brief` and `evidence_bundle`.")

    raw_change_brief = top.get("change_brief")
    if not isinstance(raw_change_brief, dict):
        errors.append("change_brief must be an object.")
    else:
        cb = cast("dict[str, Any]", raw_change_brief)
        allowed_keys = {
            "summary_one_liner",
            "lead_shift",
            "needle_change",
            "novelty_vs_reuse",
            "main_caveat",
            "failure_risk_notes",
            "notes",
        }
        unknown_keys: list[str] = sorted(set(cb.keys()) - allowed_keys)
        if unknown_keys:
            errors.append(f"change_brief includes unsupported keys: {unknown_keys}.")
        errors.extend(validate_section_payload(cb.get("summary_one_liner"), "summary_one_liner", False))
        errors.extend(validate_section_payload(cb.get("lead_shift"), "lead_shift", False))
        errors.extend(validate_section_payload(cb.get("needle_change"), "needle_change", False))
        errors.extend(validate_section_payload(cb.get("novelty_vs_reuse"), "novelty_vs_reuse", False))
        errors.extend(validate_section_payload(cb.get("main_caveat"), "main_caveat", True))
        if "failure_risk_notes" in cb:
            errors.extend(require_string_list(cb.get("failure_risk_notes"), "change_brief.failure_risk_notes"))
        if "notes" in cb:
            errors.extend(require_string_list(cb.get("notes"), "change_brief.notes"))

    raw_evidence_bundle = top.get("evidence_bundle")
    if not isinstance(raw_evidence_bundle, dict):
        errors.append("evidence_bundle must be an object.")
    else:
        eb = cast("dict[str, Any]", raw_evidence_bundle)
        if set(eb.keys()) != {"items"}:
            errors.append("evidence_bundle keys must be exactly ['items'].")
        raw_items = eb.get("items")
        if not isinstance(raw_items, list):
            errors.append("evidence_bundle.items must be an array.")
        else:
            item_list = cast("list[Any]", raw_items)
            for idx, raw_item in enumerate(item_list):
                item_label = f"evidence_bundle.items[{idx}]"
                if not isinstance(raw_item, dict):
                    errors.append(f"{item_label} must be an object.")
                    continue
                item = cast("dict[str, Any]", raw_item)
                allowed_item_keys = {"evidence_id", "year_label", "paragraph_id", "quote_text", "source_locator", "short_note"}
                unknown_item_keys: list[str] = sorted(set(item.keys()) - allowed_item_keys)
                if unknown_item_keys:
                    errors.append(f"{item_label} includes unsupported keys: {unknown_item_keys}.")
                for key in ("evidence_id", "year_label", "paragraph_id", "quote_text"):
                    errors.extend(require_string(item.get(key), f"{item_label}.{key}"))
                errors.extend(validate_source_locator(item.get("source_locator"), f"{item_label}.source_locator"))
                short_note = item.get("short_note")
                if short_note is not None and not isinstance(short_note, str):
                    errors.append(f"{item_label}.short_note must be string|null.")
    return errors


def parse_model_envelope_text(raw_text: str, raw_response_path: str | None, raw_format: str | None) -> ParseOutcome:
    normalized, normalizations, warnings = normalize_transport_text(raw_text)
    parse_ok = False
    schema_ok = False
    parser_error_note: str | None = None
    envelope: dict[str, Any] | None = None
    try:
        parsed = json.loads(normalized)
        parse_ok = True
    except json.JSONDecodeError as exc:
        parsed = None
        parser_error_note = f"JSON parse error: {exc.msg} (line {exc.lineno}, col {exc.colno})."
    if parse_ok:
        if not isinstance(parsed, dict):
            parser_error_note = "Parsed payload must be an object."
        else:
            semantic_errors = validate_semantic_envelope(parsed)
            if semantic_errors:
                parser_error_note = " ; ".join(semantic_errors)
            else:
                schema_ok = True
                envelope = cast("dict[str, Any]", parsed)
    return ParseOutcome(
        raw_response_path=raw_response_path,
        raw_response_exists=raw_response_path is not None,
        raw_response_format=raw_format,
        parse_succeeded=parse_ok,
        schema_validation_succeeded=schema_ok,
        coercion_or_repair_applied=False,
        parse_warnings=warnings,
        parser_error_note=parser_error_note,
        normalizations_applied=normalizations,
        envelope=envelope,
    )


def parse_raw_response(run_request_id: str, attempt_label: str) -> ParseOutcome:
    raw_path, raw_format = discover_raw_response_file(run_request_id, attempt_label)
    if raw_path is None:
        expected_paths = ", ".join(
            repo_rel(attempt_dir(run_request_id, attempt_label) / candidate) for candidate in RAW_RESPONSE_FILE_CANDIDATES
        )
        return ParseOutcome(
            raw_response_path=None,
            raw_response_exists=False,
            raw_response_format=None,
            parse_succeeded=False,
            schema_validation_succeeded=False,
            coercion_or_repair_applied=False,
            parse_warnings=[],
            parser_error_note=f"Raw response file not found for {attempt_label}. Expected: {expected_paths}",
            normalizations_applied=[],
            envelope=None,
        )
    raw_text = raw_path.read_text(encoding="utf-8-sig")
    return parse_model_envelope_text(raw_text, repo_rel(raw_path), raw_format)


def build_parse_report(run_request_id: str, attempt_label: str, outcome: ParseOutcome) -> dict[str, Any]:
    return {
        "artifact_schema_id": "parse_report_v1",
        "parse_report_id": f"{run_request_id}__main__{attempt_label}__parse_report_v1",
        "run_request_id": run_request_id,
        "step_label": None,
        "attempt_label": attempt_label,
        "generated_at": utc_now_iso(),
        "raw_response_path": outcome.raw_response_path,
        "raw_response_exists": outcome.raw_response_exists,
        "raw_response_format": outcome.raw_response_format,
        "parse_succeeded": outcome.parse_succeeded,
        "schema_validation_succeeded": outcome.schema_validation_succeeded,
        "coercion_or_repair_applied": outcome.coercion_or_repair_applied,
        "parse_warnings": outcome.parse_warnings,
        "parser_error_note": outcome.parser_error_note,
        "normalizations_applied": outcome.normalizations_applied,
        "allowed_normalizations": ALLOWED_NORMALIZATIONS,
    }

def build_run_request_payload(existing: dict[str, Any]) -> dict[str, Any]:
    run_request_id = as_str(existing.get("run_request_id"), "run_request_id")
    return {
        "artifact_status": "complete",
        "artifact_status_note": "Awaiting local capture handshake.",
        "artifact_schema_id": "run_request_v1",
        "run_request_id": run_request_id,
        "task_family_id": as_str(existing.get("task_family_id"), "task_family_id"),
        "fixture_id": as_str(existing.get("fixture_id"), "fixture_id"),
        "protocol_id": as_str(existing.get("protocol_id"), "protocol_id"),
        "model_profile_id": as_str(existing.get("model_profile_id"), "model_profile_id"),
        "stack_id": maybe_str(existing.get("stack_id")),
        "input_pack_id": as_str(existing.get("input_pack_id"), "input_pack_id"),
        "run_label": f"{today_utc()}_{run_request_id}",
        "created_at": utc_now_iso(),
        "execution_status": "pending_model_execution",
        "expected_artifact_paths": canonical_expected_artifact_paths(run_request_id),
        "notes": [
            "Awaiting local raw capture for the selected attempt.",
            "Strict no-repair posture: capture handshake required; semantic coercion forbidden.",
            "Scope is NVDA P1/P2 with the primary model profile only.",
        ],
        "runner_binding_id": as_str(existing.get("runner_binding_id"), "runner_binding_id"),
        "input_pack_selection": as_dict(existing.get("input_pack_selection"), "input_pack_selection"),
    }

def build_prompt_render(
    run_request: dict[str, Any],
    source_case: dict[str, Any],
    runner_binding: dict[str, Any],
    input_pack: dict[str, Any] | None,
) -> dict[str, Any]:
    protocol_id = as_str(run_request.get("protocol_id"), "protocol_id")
    template_path, system_template, user_template = wave4b.load_prompt_template(protocol_id, None)
    run_request_id = as_str(run_request.get("run_request_id"), "run_request_id")
    integrity_hash, integrity_source = wave4b.input_pack_integrity(input_pack)
    mapping = {
        "TASK_FAMILY_ID": as_str(run_request.get("task_family_id"), "task_family_id"),
        "RUN_REQUEST_ID": run_request_id,
        "RUN_LABEL": as_str(run_request.get("run_label"), "run_label"),
        "FIXTURE_ID": FIXTURE_ID,
        "PROTOCOL_ID": protocol_id,
        "MODEL_PROFILE_ID": as_str(run_request.get("model_profile_id"), "model_profile_id"),
        "RUNNER_BINDING_ID": as_str(run_request.get("runner_binding_id"), "runner_binding_id"),
        "RUNNER_CAMPAIGN_ID": as_str(runner_binding.get("campaign_id"), "campaign_id"),
        "STACK_ID": maybe_str(run_request.get("stack_id")) or "null",
        "INPUT_PACK_ID": as_str(run_request.get("input_pack_id"), "input_pack_id"),
        "INPUT_PACK_INTEGRITY_NOTE": wave4b.input_pack_integrity_note(input_pack),
        "EXPECTED_OUTPUT_PATHS": wave4b.format_expected_artifact_paths(
            run_request,
            prompt_render_path(run_request_id),
            execution_trace_path(run_request_id),
            evidence_resolution_path(run_request_id),
        ),
        "SOURCE_CASE_SUMMARY": wave4b.build_source_case_summary(source_case),
        "INPUT_CONTENT_BLOCK": wave4b.build_input_content_block(run_request, input_pack),
    }
    return {
        "artifact_status": "complete",
        "artifact_status_note": "Wave 4C1 real-run prompt render.",
        "artifact_schema_id": "prompt_render_v1",
        "prompt_render_id": f"{run_request_id}__prompt_render_v1",
        "run_request_id": run_request_id,
        "fixture_id": FIXTURE_ID,
        "protocol_id": protocol_id,
        "model_profile_id": as_str(run_request.get("model_profile_id"), "model_profile_id"),
        "runner_binding_id": as_str(run_request.get("runner_binding_id"), "runner_binding_id"),
        "stack_id": maybe_str(run_request.get("stack_id")),
        "step_label": None,
        "prompt_template_path": repo_rel(template_path),
        "rendered_system_content": wave4b.render_template(system_template, mapping),
        "rendered_user_content": wave4b.render_template(user_template, mapping),
        "input_pack_id": as_str(run_request.get("input_pack_id"), "input_pack_id"),
        "input_pack_integrity_hash": integrity_hash,
        "input_pack_integrity_source": integrity_source,
        "created_at": as_str(run_request.get("created_at"), "created_at"),
        "notes": [
            "JSON envelope required with exactly change_brief and evidence_bundle.",
            "No semantic repair allowed.",
        ],
    }


def build_prepare_trace(run_request: dict[str, Any], attempt_label: str) -> dict[str, Any]:
    run_request_id = as_str(run_request.get("run_request_id"), "run_request_id")
    now = utc_now_iso()
    return {
        "artifact_status": "complete",
        "artifact_status_note": "Awaiting local capture handshake.",
        "artifact_schema_id": "execution_trace_v1",
        "execution_trace_id": f"{run_request_id}__execution_trace_v1",
        "run_request_id": run_request_id,
        "prompt_render_id": f"{run_request_id}__prompt_render_v1",
        "runner_binding_id": as_str(run_request.get("runner_binding_id"), "runner_binding_id"),
        "step_label": None,
        "run_state": "awaiting_capture",
        "started_at": None,
        "finished_at": None,
        "raw_response_path": None,
        "parse_status": "not_run",
        "postprocess_status": "not_run",
        "usage_metadata": {
            "state_history": [{"run_state": "awaiting_capture", "at": now, "note": "Prepared for Wave 4C1.5 capture handshake."}],
            "selected_attempt_label": attempt_label,
            "evidence_item_count": 0,
        },
        "error_note": None,
        "notes": [
            "Local capture handshake prepared for the selected attempt.",
            "Public trace omits local raw-capture paths by design.",
        ],
    }

def create_raw_capture_scaffold(run_request_id: str, attempt_label: str) -> None:
    current_attempt_dir = attempt_dir(run_request_id, attempt_label)
    current_attempt_dir.mkdir(parents=True, exist_ok=True)
    instructions_file = capture_instructions_path(run_request_id, attempt_label)
    if not instructions_file.exists():
        write_text(
            instructions_file,
            "- Save the unedited raw provider response in this folder as response.json or response.txt.\n"
            "- Keep the raw capture unchanged before finalize; only transport normalizations in the local contract are allowed.\n"
            "- Fill response_meta.json with true captured_at, runner_binding_id, campaign_id, model_name, and capture_method values.\n"
            "- First-pass failures are canonical for Wave 4C1.5; do not auto-create a retry attempt.\n",
        )
    meta_file = response_meta_path(run_request_id, attempt_label)
    if not meta_file.exists():
        write_json(
            meta_file,
            {
                "captured_at": None,
                "runner_binding_id": PRIMARY_RUNNER_BINDING_ID,
                "campaign_id": PRIMARY_RUNNER_CAMPAIGN_ID,
                "model_name": "gpt-5.3-codex",
                "capture_method": "manual",
                "notes": ["Fill with true capture metadata before finalize."],
            },
        )

def empty_rubric_bands() -> dict[str, str | None]:
    return {key: None for key in RUBRIC_KEYS}


def ensure_human_eval_template() -> None:
    existing_entries: dict[str, dict[str, Any]] = {}
    if HUMAN_EVAL_INPUT_PATH.exists():
        payload = read_json(HUMAN_EVAL_INPUT_PATH)
        for raw_entry in payload.get("runs", []):
            if isinstance(raw_entry, dict):
                entry = cast("dict[str, Any]", raw_entry)
                if isinstance(entry.get("run_request_id"), str):
                    existing_entries[entry["run_request_id"]] = entry
    runs: list[dict[str, Any]] = []
    for run_request_id in TARGET_RUN_IDS:
        prior = existing_entries.get(run_request_id, {})
        _rb = prior.get("rubric_bands")
        prior_rubric: dict[str, Any] = cast("dict[str, Any]", _rb) if isinstance(_rb, dict) else {}
        runs.append(
            {
                "run_request_id": run_request_id,
                "rubric_bands": {key: (prior_rubric.get(key) if prior_rubric.get(key) in BAND_SCORES else None) for key in RUBRIC_KEYS},
                "failure_tags": prior.get("failure_tags") if isinstance(prior.get("failure_tags"), list) else [],
                "reviewer_notes": prior.get("reviewer_notes") if isinstance(prior.get("reviewer_notes"), list) else [],
            }
        )
    write_json(
        HUMAN_EVAL_INPUT_PATH,
        {
            "schema_id": "wave4c1_human_eval_input_v1",
            "updated_at": utc_now_iso(),
            "runs": runs,
            "comparison": {
                "preferred_leading_cell_id": None,
                "overall_takeaway_note": None,
                "delta_ledger_notes": [],
            },
        },
    )


def load_human_eval() -> dict[str, Any]:
    if not HUMAN_EVAL_INPUT_PATH.exists():
        return {"runs": {}, "comparison": {}, "available": False}
    payload = read_json(HUMAN_EVAL_INPUT_PATH)
    mapped: dict[str, dict[str, Any]] = {}
    for raw_entry in payload.get("runs", []):
        if isinstance(raw_entry, dict):
            rec = cast("dict[str, Any]", raw_entry)
            if isinstance(rec.get("run_request_id"), str):
                mapped[rec["run_request_id"]] = rec
    return {"runs": mapped, "comparison": payload.get("comparison", {}), "available": True}


def sanitize_human_entry(entry: dict[str, Any] | None) -> tuple[dict[str, str | None], list[str], list[str], bool]:
    if entry is None:
        return empty_rubric_bands(), [], [], False
    _rb = entry.get("rubric_bands")
    raw_rubric: dict[str, Any] = cast("dict[str, Any]", _rb) if isinstance(_rb, dict) else {}
    rubric: dict[str, str | None] = {key: (raw_rubric.get(key) if raw_rubric.get(key) in BAND_SCORES else None) for key in RUBRIC_KEYS}
    failure_tags = [item for item in entry.get("failure_tags", []) if isinstance(item, str)]
    reviewer_notes = [item for item in entry.get("reviewer_notes", []) if isinstance(item, str)]
    human_present = all(rubric[key] in BAND_SCORES for key in RUBRIC_KEYS)
    return rubric, failure_tags, reviewer_notes, human_present

def build_change_brief(run_request: dict[str, Any], envelope: dict[str, Any]) -> dict[str, Any]:
    run_request_id = as_str(run_request.get("run_request_id"), "run_request_id")
    change_brief = as_dict(envelope.get("change_brief"), "change_brief")

    def section_payload(key: str) -> dict[str, Any]:
        section = as_dict(change_brief.get(key), f"change_brief.{key}")
        return {
            "label": SECTION_LABELS[key],
            "text": as_str(section.get("text"), f"change_brief.{key}.text"),
            "evidence_ids": as_list(section.get("evidence_ids"), f"change_brief.{key}.evidence_ids"),
        }

    main_caveat = as_dict(change_brief.get("main_caveat"), "change_brief.main_caveat")
    return {
        "artifact_status": "complete",
        "artifact_status_note": "Real output with deterministic metadata-only injection.",
        "artifact_schema_id": "change_brief_output_v1",
        "change_brief_output_id": f"{run_request_id}__change_brief_output_v1",
        "run_request_id": run_request_id,
        "fixture_id": FIXTURE_ID,
        "protocol_id": as_str(run_request.get("protocol_id"), "protocol_id"),
        "model_profile_id": as_str(run_request.get("model_profile_id"), "model_profile_id"),
        "stack_id": maybe_str(run_request.get("stack_id")),
        "run_label": maybe_str(run_request.get("run_label")),
        "summary_one_liner": section_payload("summary_one_liner"),
        "lead_shift": section_payload("lead_shift"),
        "needle_change": section_payload("needle_change"),
        "novelty_vs_reuse": section_payload("novelty_vs_reuse"),
        "main_caveat": {
            "label": SECTION_LABELS["main_caveat"],
            "text": as_str(main_caveat.get("text"), "change_brief.main_caveat.text"),
            "evidence_ids": as_list(main_caveat.get("evidence_ids"), "change_brief.main_caveat.evidence_ids"),
            "caveat_type": as_str(main_caveat.get("caveat_type"), "change_brief.main_caveat.caveat_type"),
        },
        "evidence_bundle_path": as_str(
            as_dict(run_request.get("expected_artifact_paths"), "expected_artifact_paths").get("evidence_bundle_path"),
            "expected_artifact_paths.evidence_bundle_path",
        ),
        "failure_risk_notes": [item for item in change_brief.get("failure_risk_notes", []) if isinstance(item, str)],
        "notes": [item for item in change_brief.get("notes", []) if isinstance(item, str)] + ["Wave4C1 metadata-only postprocess."],
        "runner_binding_id": as_str(run_request.get("runner_binding_id"), "runner_binding_id"),
    }


def build_evidence_bundle(run_request: dict[str, Any], envelope: dict[str, Any]) -> dict[str, Any]:
    run_request_id = as_str(run_request.get("run_request_id"), "run_request_id")
    items = as_list(as_dict(envelope.get("evidence_bundle"), "evidence_bundle").get("items"), "evidence_bundle.items")
    return {
        "artifact_status": "complete",
        "artifact_status_note": "Real evidence rows copied verbatim from model output.",
        "artifact_schema_id": "evidence_bundle_v1",
        "evidence_bundle_id": f"{run_request_id}__evidence_bundle_v1",
        "run_request_id": run_request_id,
        "fixture_id": FIXTURE_ID,
        "protocol_id": as_str(run_request.get("protocol_id"), "protocol_id"),
        "model_profile_id": as_str(run_request.get("model_profile_id"), "model_profile_id"),
        "runner_binding_id": as_str(run_request.get("runner_binding_id"), "runner_binding_id"),
        "items": json.loads(json.dumps(items)),
        "notes": ["Wave4C1 metadata-only postprocess. No semantic repair."],
    }


def build_hard_checks(
    change_brief: dict[str, Any] | None,
    evidence_bundle: dict[str, Any] | None,
    resolution: dict[str, Any] | None,
) -> dict[str, str]:
    if change_brief is None or evidence_bundle is None:
        return {
            "output_present": "fail",
            "evidence_bundle_present": "fail",
            "section_objects_present": "fail",
            "evidence_refs_resolved": "fail",
        }
    items = as_list(evidence_bundle.get("items"), "evidence_bundle.items")
    evidence_ids = {
        as_str(as_dict(item, "evidence_bundle_item").get("evidence_id"), "evidence_id")
        for item in items
        if isinstance(item, dict)
    }
    referenced_ids: set[str] = set()
    section_objects_present = "pass"
    for key in ("summary_one_liner", "lead_shift", "needle_change", "novelty_vs_reuse", "main_caveat"):
        raw_section = change_brief.get(key)
        if not isinstance(raw_section, dict):
            section_objects_present = "fail"
            continue
        section = cast("dict[str, Any]", raw_section)
        if not isinstance(section.get("text"), str) or not isinstance(section.get("evidence_ids"), list):
            section_objects_present = "fail"
            continue
        for evidence_id in section["evidence_ids"]:
            if isinstance(evidence_id, str):
                referenced_ids.add(evidence_id)
    refs_resolved = bool(referenced_ids) and referenced_ids.issubset(evidence_ids)
    resolution_pass = (
        isinstance(resolution, dict)
        and isinstance(resolution.get("resolution_summary"), dict)
        and resolution["resolution_summary"].get("overall_result") == "pass"
    )
    return {
        "output_present": "pass",
        "evidence_bundle_present": "pass" if items else "fail",
        "section_objects_present": section_objects_present,
        "evidence_refs_resolved": "pass" if refs_resolved and resolution_pass else "fail",
    }


def check_model_identity(meta_outcome: ResponseMetaOutcome) -> tuple[bool, str | None]:
    if not meta_outcome.response_meta_exists:
        return False, "response_meta_missing"
    if not meta_outcome.response_meta_valid or meta_outcome.payload is None:
        if meta_outcome.validation_errors:
            return False, meta_outcome.validation_errors[0]
        return False, "response_meta_invalid"

    meta = meta_outcome.payload
    if maybe_str(meta.get("runner_binding_id")) != PRIMARY_RUNNER_BINDING_ID:
        return False, "runner_binding_id_mismatch"
    if maybe_str(meta.get("campaign_id")) != PRIMARY_RUNNER_CAMPAIGN_ID:
        return False, "campaign_id_mismatch"
    model_name = (maybe_str(meta.get("model_name")) or "").lower()
    if "gpt-5.3-codex" not in model_name and "gpt53codex" not in model_name:
        return False, "model_name_mismatch"
    return True, None


def build_eval(
    run_request_id: str,
    hard_checks: dict[str, str],
    rubric: dict[str, str | None],
    failure_tags: list[str],
    reviewer_notes: list[str],
    change_brief_output_id: str,
    evidence_bundle_id: str,
    human_present: bool,
) -> dict[str, Any]:
    hard_checks_pass = all(value == "pass" for value in hard_checks.values())
    if not hard_checks_pass:
        artifact_status = "blocked"
        artifact_status_note = "Deterministic hard checks failed."
    elif human_present:
        artifact_status = "complete"
        artifact_status_note = "Human rubric bands supplied."
    else:
        artifact_status = "pending"
        artifact_status_note = "Human rubric bands incomplete."
    return {
        "artifact_status": artifact_status,
        "artifact_status_note": artifact_status_note,
        "artifact_schema_id": "change_brief_eval_v1",
        "change_brief_eval_id": f"{run_request_id}__change_brief_eval_v1",
        "run_request_id": run_request_id,
        "hard_checks": hard_checks,
        "rubric_bands": rubric,
        "failure_tags": failure_tags,
        "reviewer_notes": reviewer_notes,
        "evaluated_artifact_ids": {
            "change_brief_output_id": change_brief_output_id,
            "evidence_bundle_id": evidence_bundle_id,
        },
    }


def success_gate(
    parse: ParseOutcome,
    identity_ok: bool,
    evidence_bundle: dict[str, Any] | None,
    resolution: dict[str, Any] | None,
    eval_payload: dict[str, Any] | None,
    hard_checks: dict[str, str] | None,
) -> bool:
    if not parse.raw_response_exists or not parse.parse_succeeded or not parse.schema_validation_succeeded:
        return False
    if not identity_ok or evidence_bundle is None or resolution is None or eval_payload is None or hard_checks is None:
        return False
    raw_items = evidence_bundle.get("items")
    if not isinstance(raw_items, list) or len(cast("list[Any]", raw_items)) == 0:
        return False
    raw_summary = resolution.get("resolution_summary")
    if not isinstance(raw_summary, dict):
        return False
    summary = cast("dict[str, Any]", raw_summary)
    if summary.get("total_evidence_items", 0) <= 0 or summary.get("overall_result") != "pass":
        return False
    if eval_payload.get("artifact_status") != "complete":
        return False
    return all(value == "pass" for value in hard_checks.values())


def update_trace(
    trace: dict[str, Any],
    run_state: str,
    parse_status: str,
    postprocess_status: str,
    raw_path: str | None,
    parse_report_rel: str,
    attempt_label: str,
    outcome: ParseOutcome,
    blockers: list[str],
    evidence_item_count: int,
) -> dict[str, Any]:
    now = utc_now_iso()
    _um = trace.get("usage_metadata")
    usage_metadata: dict[str, Any] = cast("dict[str, Any]", _um) if isinstance(_um, dict) else {}
    _sh = usage_metadata.get("state_history")
    raw_history: list[Any] = cast("list[Any]", _sh) if isinstance(_sh, list) else []
    state_history: list[dict[str, Any]] = [cast("dict[str, Any]", item) for item in raw_history if isinstance(item, dict)]

    if run_state == "capture_missing":
        state_history.append({"run_state": "capture_missing", "at": now, "note": f"Capture handshake missing for {attempt_label}."})
    elif run_state == "captured":
        state_history.append({"run_state": "captured", "at": now, "note": f"Capture handshake satisfied for {attempt_label}."})
    elif run_state == "parse_failed":
        state_history.append({"run_state": "captured", "at": now, "note": f"Capture handshake satisfied for {attempt_label}."})
        state_history.append({"run_state": "parse_failed", "at": now, "note": f"Captured response failed parse for {attempt_label}."})
    elif run_state == "validated":
        state_history.append({"run_state": "captured", "at": now, "note": f"Capture handshake satisfied for {attempt_label}."})
        state_history.append({"run_state": "validated", "at": now, "note": f"Deterministic validation passed for {attempt_label}."})
    elif run_state == "reviewed":
        state_history.append({"run_state": "captured", "at": now, "note": f"Capture handshake satisfied for {attempt_label}."})
        state_history.append({"run_state": "validated", "at": now, "note": f"Deterministic validation passed for {attempt_label}."})
        state_history.append({"run_state": "reviewed", "at": now, "note": f"Human review completed for {attempt_label}."})

    usage_metadata["state_history"] = state_history
    usage_metadata["selected_attempt_label"] = attempt_label
    usage_metadata["evaluated_attempt_label"] = attempt_label
    usage_metadata["raw_response_format"] = outcome.raw_response_format
    usage_metadata["evidence_item_count"] = evidence_item_count

    trace["artifact_status"] = "complete"
    trace["run_state"] = run_state
    trace["started_at"] = trace.get("started_at") or now
    trace["finished_at"] = now
    trace["raw_response_path"] = None
    trace["parse_status"] = parse_status
    trace["postprocess_status"] = postprocess_status
    trace["usage_metadata"] = usage_metadata
    trace["error_note"] = public_blocker_note(blockers, "capture_handshake_pending") if blockers else None
    trace["notes"] = [item for item in trace.get("notes", []) if isinstance(item, str)] + [
        f"evaluated_attempt_label: `{attempt_label}`",
        "Local capture details remain in local audit reports and the Wave 4C1.5 packet.",
    ]
    return trace


def update_request_status(request: dict[str, Any], status: str, note: str) -> dict[str, Any]:
    request["execution_status"] = status
    request["artifact_status"] = "complete"
    request["artifact_status_note"] = note
    request["notes"] = [item for item in request.get("notes", []) if isinstance(item, str)] + [note]
    return request


def dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    ordered: list[Path] = []
    for path in paths:
        key = path.as_posix()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(path)
    return ordered


def text_line(value: str | None, max_len: int = 180) -> str:
    if not value:
        return "[not_available]"
    line = " ".join(value.split())
    return line if len(line) <= max_len else line[: max_len - 3] + "..."

def build_red_team_brief(attempt_labels: dict[str, str], run_results: list[RunFinalizeResult] | None = None) -> str:
    lines = [
        "# Wave 4C1 Desktop Red-Team Brief",
        "",
        "Use this brief in ChatGPT Desktop as an architecture/control-plane red-team review only.",
        "Do not use ChatGPT Desktop to generate canonical outputs, rewrite raw responses, or assign final rubric bands.",
        "",
        "## Fixed Scope",
        "",
        "- Fixture: `NVDA_2024_2025_10k_item1a`",
        "- Protocols only: `p1_structured_contract_v1`, `p2_tagged_input_contract_v1`",
        "- Model profile only: `m_primary_strong_reasoning_v1` via `rb_openai_gpt53codex_real_local_v1`",
        "- No public schema changes, no UI changes, no P3/i3 expansion, no generalized retry system",
        "",
        "## Invariants",
        "",
        "- Raw capture is required and remains local-only under `reports/protocol_lab/raw_runs/...`",
        "- Allowed normalization is transport-only: BOM trim, outer whitespace trim, single fenced-wrapper trim",
        "- No semantic coercion/repair is permitted",
        "- Deterministic postprocess may inject metadata only and must not rewrite analytical text or evidence rows",
        "- First-pass failures are canonical for this wave and are not auto-retried",
        "",
        "## Clean-Audit Hardening Applied",
        "",
        "- Attempt handling now uses the selected/latest attempt instead of being fixed to `attempt_01`",
        "- Prepare does not silently create `attempt_02` or advance retries",
        "- Parse reports are per-attempt and include `attempt_label`",
        "- Blocked finalize no longer pulls forward stale scaffold briefs, evidence bundles, resolutions, or evals into current review/report output",
        "- Blocked comparison state carries no fake analytical delta ledger or pairwise findings before evidence-grounded comparison exists",
        "- Packet assembly is deterministic and runs once per finalize",
        "",
        "## Current Local Status",
        "",
    ]
    if run_results is None:
        for run_request_id in TARGET_RUN_IDS:
            lines.append(f"- `{run_request_id}` -> active attempt `{attempt_labels[run_request_id]}`; no finalize result recorded yet")
    else:
        by_run = {result.run_request_id: result for result in run_results}
        for run_request_id in TARGET_RUN_IDS:
            result = by_run[run_request_id]
            lines.append(
                "- "
                + f"`{run_request_id}` -> attempt `{result.attempt_label}`; run_state=`{result.run_state}`; "
                + f"raw_response_path=`{result.raw_response_path}`; blockers=`{result.blocker_notes}`"
            )
    lines.extend(
        [
            "",
            "## Questions for ChatGPT Desktop",
            "",
            "- Does selected/latest attempt handling preserve audit truth without introducing hidden retry semantics or black-box state?",
            "- Does any local-only artifact now leak into public comparison semantics or other shipped data paths?",
            "- Is the blocked comparison shape decision-complete and honest, or is there still any misleading analytical content before a real evidence-grounded pairwise review exists?",
            "- Do the driver assumptions or payload semantics drift from the lab's canonical control-plane structure or schema discipline?",
            "- Are there any remaining hidden variables that would contaminate a P1 vs P2 protocol comparison beyond protocol choice and model lane?",
        ]
    )
    return "\n".join(lines) + "\n"


def prepare_phase(requested_attempt_label: str | None = None) -> None:
    ensure_parse_report_schema()
    bindings = wave4b.ensure_registry_map(REGISTRIES_ROOT / "runner_bindings_local_v1.json", "runner_binding_id")
    source_case = read_json(SOURCE_CASES_ROOT / FIXTURE_ID / "source_case_manifest_v1.json")
    runner_binding = as_dict(bindings[PRIMARY_RUNNER_BINDING_ID], "runner_binding")
    attempt_labels: dict[str, str] = {}

    for run_request_id in TARGET_RUN_IDS:
        existing = read_json(run_request_path(run_request_id))
        if as_str(existing.get("model_profile_id"), "model_profile_id") != PRIMARY_MODEL_PROFILE_ID:
            raise ValueError(f"{run_request_id} does not use primary model profile")
        if as_str(existing.get("runner_binding_id"), "runner_binding_id") != PRIMARY_RUNNER_BINDING_ID:
            raise ValueError(f"{run_request_id} does not use primary runner binding")
        attempt_label = ensure_prepare_attempt_label(run_request_id, requested_attempt_label)
        attempt_labels[run_request_id] = attempt_label
        request = build_run_request_payload(existing)
        write_json(run_request_path(run_request_id), request)
        input_pack = wave4b.load_input_pack_payload(FIXTURE_ID, as_str(request.get("input_pack_id"), "input_pack_id"))
        write_json(prompt_render_path(run_request_id), build_prompt_render(request, source_case, runner_binding, input_pack))
        write_json(execution_trace_path(run_request_id), build_prepare_trace(request, attempt_label))
        create_raw_capture_scaffold(run_request_id, attempt_label)

    ensure_human_eval_template()
    write_text(RED_TEAM_BRIEF_PATH, build_red_team_brief(attempt_labels))


def build_comparison(
    existing: dict[str, Any],
    results: list[RunFinalizeResult],
    evals: dict[str, dict[str, Any]],
    briefs: dict[str, dict[str, Any]],
    comparison_input: dict[str, Any],
) -> tuple[dict[str, Any], bool, str]:
    by_run = {result.run_request_id: result for result in results}
    compared_cells = as_list(existing.get("compared_cells"), "compared_cells")
    cell_map = {
        as_str(as_dict(cell, "compared_cell").get("run_request_id"), "run_request_id"): as_str(
            as_dict(cell, "compared_cell").get("cell_id"),
            "cell_id",
        )
        for cell in compared_cells
    }
    left_cell_id = cell_map[TARGET_RUN_IDS[0]]
    right_cell_id = cell_map[TARGET_RUN_IDS[1]]
    payload = dict(existing)
    all_reviewed = all(by_run[run_request_id].run_state == "reviewed" for run_request_id in TARGET_RUN_IDS)
    all_validated = all(by_run[run_request_id].run_state in {"validated", "reviewed"} for run_request_id in TARGET_RUN_IDS)

    if not all_validated:
        blocker_notes: list[str] = []
        for run_request_id in TARGET_RUN_IDS:
            blocker_notes.extend(by_run[run_request_id].blocker_notes)
        blocked_reason = public_blocker_note(blocker_notes, "comparison_blocked")
        payload["artifact_status"] = "blocked"
        payload["artifact_status_note"] = blocked_reason
        payload["comparison_verdict"] = {
            "label": "Comparison Verdict",
            "text": f"Comparison blocked before evidence-grounded pairwise review: {blocked_reason}",
            "verdict_kind": "blocked",
            "leading_cell_id": None,
            "cell_ids": [left_cell_id, right_cell_id],
        }
        payload["delta_ledger"] = []
        payload["pairwise_findings"] = []
        payload["high_level_takeaway"] = {
            "label": "High-Level Takeaway",
            "text": "Wave 4C1.5 did not reach a reviewed evidence-grounded pairwise comparison for these runs.",
            "cell_ids": [left_cell_id, right_cell_id],
        }
        payload["review_status"] = {"state": "blocked", "note": blocked_reason}
        payload["notes"] = [
            "Blocked comparison state intentionally omits analytical delta findings.",
            "Local capture details remain local-only.",
        ]
        return payload, False, "Comparison blocked before evidence-grounded pairwise review because at least one run did not reach validated status."

    if not all_reviewed:
        pending_reason = "human_review_pending"
        payload["artifact_status"] = "pending"
        payload["artifact_status_note"] = pending_reason
        payload["comparison_verdict"] = {
            "label": "Comparison Verdict",
            "text": "Both runs validated deterministically; pairwise comparison awaits human review.",
            "verdict_kind": "no_verdict",
            "leading_cell_id": None,
            "cell_ids": [left_cell_id, right_cell_id],
        }
        payload["delta_ledger"] = []
        payload["pairwise_findings"] = []
        payload["high_level_takeaway"] = {
            "label": "High-Level Takeaway",
            "text": "Both runs validated deterministically; comparison awaits human review.",
            "cell_ids": [left_cell_id, right_cell_id],
        }
        payload["review_status"] = {"state": "pending_review", "note": pending_reason}
        payload["notes"] = [
            "Pending comparison state intentionally omits pairwise analytical findings until human review is complete.",
            "Local capture details remain local-only.",
        ]
        return payload, False, "Both runs validated deterministically, but the public comparison remains pending until human review is complete."

    def score(eval_payload: dict[str, Any]) -> int:
        rubric_bands = as_dict(eval_payload.get("rubric_bands"), "rubric_bands")
        return sum(BAND_SCORES.get(maybe_str(rubric_bands.get(key)) or "", 0) for key in RUBRIC_KEYS)

    left_score = score(evals[TARGET_RUN_IDS[0]])
    right_score = score(evals[TARGET_RUN_IDS[1]])
    preferred_cell = maybe_str(as_dict(comparison_input, "comparison_input").get("preferred_leading_cell_id"))
    if preferred_cell == left_cell_id:
        leading_cell_id, verdict_kind = left_cell_id, "left_advantage"
    elif preferred_cell == right_cell_id:
        leading_cell_id, verdict_kind = right_cell_id, "right_advantage"
    elif left_score > right_score:
        leading_cell_id, verdict_kind = left_cell_id, "left_advantage"
    elif right_score > left_score:
        leading_cell_id, verdict_kind = right_cell_id, "right_advantage"
    else:
        leading_cell_id, verdict_kind = None, "no_material_difference"

    left_brief = as_dict(briefs[TARGET_RUN_IDS[0]], "left_brief")
    right_brief = as_dict(briefs[TARGET_RUN_IDS[1]], "right_brief")
    left_summary = as_dict(left_brief.get("summary_one_liner"), "left_summary")
    right_summary = as_dict(right_brief.get("summary_one_liner"), "right_summary")
    takeover = maybe_str(comparison_input.get("overall_takeaway_note"))
    if takeover:
        takeaway = takeover
    elif leading_cell_id == left_cell_id:
        takeaway = "P1 edged P2 in rubric totals with stronger evidence-grounded framing in this run set."
    elif leading_cell_id == right_cell_id:
        takeaway = "P2 edged P1 in rubric totals, indicating tag-aware contract gains in this run set."
    else:
        takeaway = "P1 and P2 were materially close; differences are localized to framing and caveat emphasis."

    payload["artifact_status"] = "complete"
    payload["artifact_status_note"] = "reviewed"
    payload["comparison_verdict"] = {
        "label": "Comparison Verdict",
        "text": f"P1 summary: {text_line(maybe_str(left_summary.get('text')), 130)} | P2 summary: {text_line(maybe_str(right_summary.get('text')), 130)}",
        "verdict_kind": verdict_kind,
        "leading_cell_id": leading_cell_id,
        "cell_ids": [left_cell_id, right_cell_id],
    }
    payload["delta_ledger"] = [
        {
            "delta_id": "nvda_ablation_tag_awareness_v1__delta_evidence_grounding",
            "left_cell_id": left_cell_id,
            "right_cell_id": right_cell_id,
            "dimension_id": "evidence_grounding",
            "delta_kind": "evidence_scope",
            "impact_level": "high",
            "summary": "Stronger/weaker evidence grounding.",
        },
        {
            "delta_id": "nvda_ablation_tag_awareness_v1__delta_novelty_separation",
            "left_cell_id": left_cell_id,
            "right_cell_id": right_cell_id,
            "dimension_id": "novelty_separation",
            "delta_kind": "tag_awareness",
            "impact_level": "high",
            "summary": "Novelty separation differences.",
        },
        {
            "delta_id": "nvda_ablation_tag_awareness_v1__delta_caveat_quality",
            "left_cell_id": left_cell_id,
            "right_cell_id": right_cell_id,
            "dimension_id": "caveat_quality",
            "delta_kind": "other",
            "impact_level": "medium",
            "summary": "Caveat quality and overclaim risk differences.",
        },
        {
            "delta_id": "nvda_ablation_tag_awareness_v1__delta_needle_coverage",
            "left_cell_id": left_cell_id,
            "right_cell_id": right_cell_id,
            "dimension_id": "needle_coverage",
            "delta_kind": "protocol_contract",
            "impact_level": "medium",
            "summary": "Whether one run missed a stronger needle.",
        },
    ]
    payload["pairwise_findings"] = [
        {
            "finding_id": "nvda_ablation_tag_awareness_v1__finding_lead",
            "left_cell_id": left_cell_id,
            "right_cell_id": right_cell_id,
            "finding_category": "lead_shift",
            "label": "Lead shift",
            "text": f"P1: {text_line(maybe_str(as_dict(left_brief.get('lead_shift'), 'left_lead').get('text')), 140)} | P2: {text_line(maybe_str(as_dict(right_brief.get('lead_shift'), 'right_lead').get('text')), 140)}",
            "cell_ids": [left_cell_id, right_cell_id],
            "delta_ids": ["nvda_ablation_tag_awareness_v1__delta_novelty_separation"],
        },
        {
            "finding_id": "nvda_ablation_tag_awareness_v1__finding_needle",
            "left_cell_id": left_cell_id,
            "right_cell_id": right_cell_id,
            "finding_category": "needle_change",
            "label": "Needle",
            "text": f"P1: {text_line(maybe_str(as_dict(left_brief.get('needle_change'), 'left_needle').get('text')), 140)} | P2: {text_line(maybe_str(as_dict(right_brief.get('needle_change'), 'right_needle').get('text')), 140)}",
            "cell_ids": [left_cell_id, right_cell_id],
            "delta_ids": ["nvda_ablation_tag_awareness_v1__delta_needle_coverage"],
        },
    ]
    payload["high_level_takeaway"] = {"label": "High-Level Takeaway", "text": takeaway, "cell_ids": [left_cell_id, right_cell_id]}
    payload["review_status"] = {"state": "reviewed", "note": "reviewed"}
    payload["notes"] = ["Promoted only after both runs reached reviewed status."]
    return payload, True, takeaway

def build_review_packet_text(
    results: dict[str, RunFinalizeResult],
    run_requests: dict[str, dict[str, Any]],
    traces: dict[str, dict[str, Any]],
    parse_reports: dict[str, dict[str, Any]],
    evidence_bundles: dict[str, dict[str, Any]],
    briefs: dict[str, dict[str, Any]],
    resolutions: dict[str, dict[str, Any]],
    evals: dict[str, dict[str, Any]],
    comparison: dict[str, Any],
    takeaway: str,
) -> str:
    review_status = as_dict(comparison.get("review_status"), "review_status") if isinstance(comparison.get("review_status"), dict) else {"state": None, "note": None}
    lines = [
        "# Wave 4C1.5 Capture Boundary Review Packet",
        "",
        f"- generated_at: `{utc_now_iso()}`",
        f"- comparison_status: `{comparison.get('artifact_status')}`",
        f"- comparison_review_state: `{review_status.get('state')}`",
        "",
        "## Boundary Rule",
        "",
        "- Public artifacts keep blocker codes and concise public-safe notes only.",
        "- Local capture roots, parse reports, CAPTURE_INSTRUCTIONS, and response_meta remain local-only and are surfaced in this packet.",
        "",
    ]
    for run_request_id in TARGET_RUN_IDS:
        result = results[run_request_id]
        run_request = run_requests[run_request_id]
        trace = traces[run_request_id]
        parse_report = parse_reports[run_request_id]
        if result.attempt_label is None:
            raise ValueError(f"Missing attempt label for {run_request_id}")
        local_capture_root = repo_rel(attempt_dir(run_request_id, result.attempt_label))
        local_response_meta = repo_rel(response_meta_path(run_request_id, result.attempt_label))
        local_capture_instructions = repo_rel(capture_instructions_path(run_request_id, result.attempt_label))
        lines.extend(
            [
                f"## Run `{run_request_id}`",
                "",
                "Prompt metadata:",
                f"- protocol_id: `{run_request.get('protocol_id')}`",
                f"- input_pack_id: `{run_request.get('input_pack_id')}`",
                f"- model_profile_id: `{run_request.get('model_profile_id')}`",
                f"- runner_binding_id: `{run_request.get('runner_binding_id')}`",
                f"- attempt_label: `{result.attempt_label}`",
                "",
                "Local capture audit:",
                f"- raw_capture_root: `{local_capture_root}`",
                f"- raw_response_path: `{result.raw_response_path}`",
                f"- response_meta_path: `{local_response_meta}`",
                f"- capture_instructions_path: `{local_capture_instructions}`",
                f"- parse_report_path: `{result.parse_report_path}`",
                "",
                "Capture / parse status:",
                f"- run_state: `{trace.get('run_state')}`",
                f"- parse_status/postprocess_status: `{trace.get('parse_status')}` / `{trace.get('postprocess_status')}`",
                f"- raw_response_exists: `{parse_report.get('raw_response_exists')}`",
                f"- parse_succeeded: `{parse_report.get('parse_succeeded')}`",
                f"- schema_validation_succeeded: `{parse_report.get('schema_validation_succeeded')}`",
                f"- coercion_or_repair_applied: `{parse_report.get('coercion_or_repair_applied')}`",
                f"- normalizations_applied: `{parse_report.get('normalizations_applied')}`",
                f"- parse_warnings: `{parse_report.get('parse_warnings')}`",
                f"- parser_error_note: `{parse_report.get('parser_error_note')}`",
                f"- blocker_summary: `{trace.get('error_note')}`",
                "",
            ]
        )
        if run_request_id not in briefs:
            lines.extend(
                [
                    "Current-attempt downstream artifacts:",
                    "- No fresh change brief, evidence bundle, evidence resolution, or eval was materialized for this attempt.",
                    "",
                ]
            )
            continue

        brief = briefs[run_request_id]
        lines.extend(
            [
                "Summary one-liner:",
                f"- {text_line(maybe_str(as_dict(brief.get('summary_one_liner'), 'summary_one_liner').get('text')), 180)}",
                "Evidence anchors / quotes:",
            ]
        )
        bundle_items: list[dict[str, Any]] = []
        if run_request_id in evidence_bundles:
            bundle_items = [cast('dict[str, Any]', item) for item in as_list(evidence_bundles[run_request_id].get('items'), 'evidence_bundle.items') if isinstance(item, dict)]
        if not bundle_items:
            lines.append("- [none]")
        else:
            for item in bundle_items[:6]:
                lines.append(
                    "- "
                    + f"{item.get('evidence_id')} | {item.get('year_label')} | {item.get('paragraph_id')} | "
                    + text_line(maybe_str(item.get('quote_text')), 120)
                )
        if run_request_id in resolutions:
            resolution_summary = as_dict(resolutions[run_request_id].get('resolution_summary'), 'resolution_summary')
            lines.extend(
                [
                    "Evidence-resolution results:",
                    f"- overall_result: `{resolution_summary.get('overall_result')}`",
                    f"- total_evidence_items: `{resolution_summary.get('total_evidence_items')}`",
                    f"- failed_item_count: `{resolution_summary.get('failed_item_count')}`",
                ]
            )
        if run_request_id in evals:
            lines.extend(
                [
                    "Eval:",
                    f"- artifact_status: `{evals[run_request_id].get('artifact_status')}`",
                    f"- rubric_bands: `{evals[run_request_id].get('rubric_bands')}`",
                    f"- failure_tags: `{evals[run_request_id].get('failure_tags')}`",
                ]
            )
        else:
            lines.extend(["Eval:", "- Not materialized for this attempt."])
        lines.append("")

    if comparison.get("artifact_status") == "complete":
        lines.extend(["## Delta Ledger", ""])
        for raw_delta in as_list(comparison.get("delta_ledger"), "delta_ledger"):
            delta = as_dict(raw_delta, "delta")
            lines.append(f"- {delta.get('delta_id')}: {delta.get('summary')}")
        lines.append("")
    elif comparison.get("artifact_status") == "pending":
        lines.extend(
            [
                "## Comparison Status",
                "",
                "- Both runs validated deterministically, but public comparison findings remain withheld until human review is complete.",
                f"- pending_reason: `{review_status.get('note')}`",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "## Comparison Status",
                "",
                "- No evidence-grounded delta ledger is available for this blocked comparison state.",
                f"- blocked_reason: `{review_status.get('note')}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Prompt Diff Summary",
            "",
            "- protocol difference: p1_structured_contract_v1 vs p2_tagged_input_contract_v1",
            "- input-pack difference: fixed i2 packet; selection-source differs (experiment_override vs protocol_default)",
            "- evidence-contract difference: none (both evidence_bundle_v1 exact refs when materialized)",
            "- what stayed fixed: fixture, primary model profile, runner binding, tagged packet scope",
            "",
            f"- most important qualitative takeaway: {takeaway}",
            "",
        ]
    )
    return "\n".join(lines)


def build_execution_report(
    results: list[RunFinalizeResult],
    smoke_result: SmokeSummary,
    packet_dir: Path,
    zip_path: Path,
    takeaway: str,
) -> str:
    lines = [
        "# Wave 4C1.5 Capture Boundary Execution Report",
        "",
        f"- generated_at: `{utc_now_iso()}`",
        f"- smoke_passed: `{smoke_result.smoke_passed}`",
        f"- smoke_run_state: `{smoke_result.run_state}`",
        f"- smoke_parse_status: `{smoke_result.parse_status}`",
        f"- smoke_blocker_codes: `{smoke_result.blocker_codes}`",
        f"- packet_folder_path: `{repo_rel(packet_dir)}`",
        f"- zip_path: `{repo_rel(zip_path)}`",
        f"- takeaway: {takeaway}",
        "",
        "## Run Results",
        "",
    ]
    for result in results:
        if result.attempt_label is None:
            raise ValueError(f"Missing attempt label for {result.run_request_id}")
        lines.extend(
            [
                f"- run_request_id: `{result.run_request_id}`",
                f"- attempt_label: `{result.attempt_label}`",
                f"- run_succeeded: `{result.run_succeeded}`",
                f"- run_state: `{result.run_state}`",
                f"- parse/postprocess: `{result.parse_status}` / `{result.postprocess_status}`",
                f"- raw_capture_root: `{repo_rel(attempt_dir(result.run_request_id, result.attempt_label))}`",
                f"- raw_response_path: `{result.raw_response_path}`",
                f"- response_meta_path: `{repo_rel(response_meta_path(result.run_request_id, result.attempt_label))}`",
                f"- parse_report_path: `{result.parse_report_path}`",
                f"- downstream_artifacts_materialized: `{result.downstream_artifacts_materialized}`",
                f"- evidence_item_count: `{result.evidence_item_count}`",
                f"- evidence_resolution_overall_result: `{result.evidence_resolution_overall_result}`",
                f"- human_eval_present: `{result.human_eval_present}`",
                f"- blocker_notes: `{result.blocker_notes}`",
                "",
            ]
        )
    return "\n".join(lines)


def build_review_notes(
    results: list[RunFinalizeResult],
    evals: dict[str, dict[str, Any]],
    comparison: dict[str, Any],
    takeaway: str,
    smoke_result: SmokeSummary,
) -> str:
    review_status = as_dict(comparison.get("review_status"), "review_status") if isinstance(comparison.get("review_status"), dict) else {"state": None, "note": None}
    lines = [
        "# Wave 4C1.5 Capture Boundary Review Notes",
        "",
        f"- generated_at: `{utc_now_iso()}`",
        f"- smoke_passed: `{smoke_result.smoke_passed}`",
        f"- comparison_state: `{review_status.get('state')}`",
        f"- comparison_note: `{review_status.get('note')}`",
        f"- qualitative_takeaway: {takeaway}",
        "",
        "## Rubric Bands and Failure Tags",
        "",
    ]
    for result in results:
        eval_payload = evals.get(result.run_request_id)
        if eval_payload is None:
            lines.append(f"- {result.run_request_id}: eval not materialized for `{result.attempt_label}`")
            continue
        lines.extend(
            [
                f"- run_request_id: `{result.run_request_id}`",
                f"- attempt_label: `{result.attempt_label}`",
                f"- eval_artifact_status: `{eval_payload.get('artifact_status')}`",
                f"- rubric_bands: `{eval_payload.get('rubric_bands')}`",
                f"- failure_tags: `{eval_payload.get('failure_tags')}`",
                f"- reviewer_notes: `{eval_payload.get('reviewer_notes')}`",
                "",
            ]
        )
    return "\n".join(lines)


def build_manifest(paths: list[Path]) -> str:
    return "# Relevant Files Manifest\n\n" + "\n".join(f"- {path.as_posix()}" for path in paths) + "\n"


def build_packet_readme(
    name: str,
    results: list[RunFinalizeResult],
    comparison: dict[str, Any],
    smoke_result: SmokeSummary,
    takeaway: str,
) -> str:
    return "\n".join(
        [
            f"# {name}",
            "",
            "Wave 4C1.5 capture-boundary packet.",
            "",
            "## Summary",
            f"- smoke_passed: {smoke_result.smoke_passed}",
            f"- comparison_status: {comparison.get('artifact_status')}",
            f"- validated_or_reviewed_runs: {sum(1 for result in results if result.run_state in {'validated', 'reviewed'})}",
            f"- reviewed_runs: {sum(1 for result in results if result.run_state == 'reviewed')}",
            f"- qualitative_takeaway: {takeaway}",
            "",
        ]
    ) + "\n"


def packet_paths_for_stamp(stamp: str) -> tuple[str, Path, Path]:
    name = f"wave4c15_capture_boundary_{stamp}"
    return name, REPO_ROOT / name, REPO_ROOT / f"{name}.zip"


def wave4b_sample_trace_paths() -> list[Path]:
    base = RUNS_ROOT / FIXTURE_ID
    return [
        base / wave4b.SAMPLE_RUN_IDS[0] / 'execution_trace_v1.json',
        base / wave4b.SAMPLE_RUN_IDS[1] / 'execution_trace_v1.json',
        base / wave4b.SAMPLE_RUN_IDS[2] / 'steps' / wave4b.P3_STEP_LABELS[0] / 'execution_trace_v1.json',
        base / wave4b.SAMPLE_RUN_IDS[2] / 'steps' / wave4b.P3_STEP_LABELS[1] / 'execution_trace_v1.json',
    ]


def build_boundary_cleanup_notes() -> str:
    lines = [
        '# Wave 4C1.5 Boundary Cleanup Notes',
        '',
        f'- generated_at: `{utc_now_iso()}`',
        '',
        '## Public / Publishable Artifacts',
        '',
        '- `comparison_view_v1` now carries blocker codes and concise public-safe notes only.',
        '- `execution_trace_v1` keeps `raw_response_path = null` and no longer publishes local capture roots, parse-report paths, or CAPTURE_INSTRUCTIONS references.',
        '- `run_request_v1` status notes are capture-handshake summaries only and do not expose local filesystem paths.',
        '',
        '## Local Audit Surfaces',
        '',
        '- `parse_report_v1.json` remains local-only and preserves raw-response paths, parser notes, and normalization details.',
        '- The Wave 4C1.5 packet and smoke-run report intentionally include `raw_capture_root`, `response_meta.json`, `CAPTURE_INSTRUCTIONS.md`, and parse-report paths.',
        '- Wave 4B sample execution traces were regenerated to remove public path leakage while preserving their historical scaffold semantics.',
        '',
    ]
    return "\n".join(lines) + "\n"


def build_run_state_model_update() -> str:
    lines = [
        '# Wave 4C1.5 Run State Model Update',
        '',
        f'- generated_at: `{utc_now_iso()}`',
        '',
        '## Active States',
        '',
        '- `awaiting_capture`: prompt render exists and the local capture scaffold has been written for the selected attempt.',
        '- `capture_missing`: no accepted raw response file exists, or `response_meta.json` is missing or incomplete, so canonical finalize does not start.',
        '- `captured`: accepted raw response plus valid `response_meta.json` exist, but deterministic finalize has not promoted the run to `validated` or `reviewed`.',
        '- `parse_failed`: an accepted raw response exists and the capture contract is satisfied, but JSON parse or schema validation failed.',
        '- `validated`: deterministic parse, schema validation, metadata checks, and evidence-resolution gates passed, but human review is still pending.',
        '- `reviewed`: deterministic checks passed and the human review artifact is complete.',
        '',
        '## Semantics',
        '',
        '- Missing raw capture must not be labeled `completed` or `parse_failed`.',
        '- When capture is missing or incomplete, `parse_status` stays `not_run`.',
        '- `parse_status = failed` is reserved for real captured raw responses that fail parse or schema validation.',
        '- `comparison_view_v1` may be `blocked`, `pending`, or `complete`; `pending` is the truthful state when both runs are validated but human review is incomplete.',
        '',
    ]
    return "\n".join(lines) + "\n"


def build_local_capture_contract() -> str:
    lines = [
        '# Local Capture Contract v1',
        '',
        f'- generated_at: `{utc_now_iso()}`',
        '',
        '## Accepted Raw File Names',
        '',
        '- `response.json`',
        '- `response.txt`',
        '',
        '## Accepted Raw Formats',
        '',
        '- UTF-8 JSON object text saved directly to `response.json`.',
        '- UTF-8 plain text in `response.txt` when the operator must preserve the raw assistant response before confirming JSON shape.',
        '- Allowed transport-only normalization is limited to UTF-8 BOM trim, outer whitespace trim, and a single fenced-wrapper trim.',
        '',
        '## Required `response_meta.json` Fields',
        '',
        '- `captured_at`: UTC timestamp for the saved raw response.',
        '- `runner_binding_id`: must match the selected local runner binding.',
        '- `campaign_id`: must match the selected local capture campaign.',
        '- `model_name`: concrete model identity captured by the operator or runner.',
        '- `capture_method`: concise truthful description such as `manual_copy`, `desktop_export`, or `local_runner_write`.',
        '',
        '## Capture Completeness',
        '',
        '- A run counts as `captured` only when an accepted raw response file exists and `response_meta.json` is present with all required non-empty fields.',
        '- Finalize expects the prompt render to exist, the selected attempt folder to be stable, and the raw response plus `response_meta.json` to refer to the same run attempt.',
        '- Canonical first-pass failure means the first captured raw response fails parse, schema validation, identity checks, evidence-resolution checks, or later human review; it is recorded truthfully and is not auto-retried in this wave.',
        '',
        '## Local-Only Material',
        '',
        '- Raw capture roots under `reports/protocol_lab/raw_runs/...`',
        '- `parse_report_v1.json`',
        '- `CAPTURE_INSTRUCTIONS.md`',
        '- `response_meta.json`',
        '- Machine-specific runner, workspace, or operator notes',
        '',
    ]
    return "\n".join(lines) + "\n"


def ensure_wave4c15_docs() -> None:
    write_text(BOUNDARY_CLEANUP_NOTES_PATH, build_boundary_cleanup_notes())
    write_text(RUN_STATE_MODEL_UPDATE_PATH, build_run_state_model_update())
    write_text(LOCAL_CAPTURE_CONTRACT_PATH, build_local_capture_contract())


def build_smoke_prompt_render() -> dict[str, Any]:
    return {
        'artifact_status': 'complete',
        'artifact_status_note': 'Local-only smoke prompt render for Wave 4C1.5 capture handshake.',
        'artifact_schema_id': 'prompt_render_v1',
        'prompt_render_id': f'{SMOKE_RUN_ID}__prompt_render_v1',
        'run_request_id': SMOKE_RUN_ID,
        'fixture_id': FIXTURE_ID,
        'protocol_id': 'wave4c15_capture_handshake_v1',
        'model_profile_id': PRIMARY_MODEL_PROFILE_ID,
        'runner_binding_id': PRIMARY_RUNNER_BINDING_ID,
        'prompt_template_path': None,
        'rendered_system_content': 'Return one JSON object that matches the change_brief/evidence_bundle envelope. Do not add commentary outside the JSON object.',
        'rendered_user_content': 'This non-canonical smoke run verifies prompt render -> raw response capture -> local finalize handshake only. Save the raw response into the prepared attempt folder without rewriting it, then fill response_meta.json truthfully.',
        'created_at': utc_now_iso(),
        'notes': [
            f'local_capture_root: `{repo_rel(SMOKE_CAPTURE_ROOT)}`',
            'Smoke run only; do not treat this as a canonical comparison artifact.',
        ],
    }


def build_smoke_execution_trace(
    run_state: str,
    parse_status: str,
    blocker_codes: list[str],
    raw_response_path: str | None,
    parse_report_rel: str,
) -> dict[str, Any]:
    now = utc_now_iso()
    return {
        'artifact_status': 'complete',
        'artifact_status_note': 'Local-only Wave 4C1.5 smoke execution trace.',
        'artifact_schema_id': 'execution_trace_v1',
        'execution_trace_id': f'{SMOKE_RUN_ID}__execution_trace_v1',
        'run_request_id': SMOKE_RUN_ID,
        'prompt_render_id': f'{SMOKE_RUN_ID}__prompt_render_v1',
        'runner_binding_id': PRIMARY_RUNNER_BINDING_ID,
        'step_label': None,
        'run_state': run_state,
        'started_at': now,
        'finished_at': now,
        'raw_response_path': raw_response_path,
        'parse_status': parse_status,
        'postprocess_status': 'not_run',
        'usage_metadata': {
            'raw_capture_root': repo_rel(SMOKE_CAPTURE_ROOT),
            'response_meta_path': repo_rel(SMOKE_CAPTURE_ROOT / 'response_meta.json'),
            'capture_instructions_path': repo_rel(SMOKE_CAPTURE_ROOT / 'CAPTURE_INSTRUCTIONS.md'),
            'parse_report_path': parse_report_rel,
            'blocker_codes': blocker_codes,
        },
        'error_note': public_blocker_note(blocker_codes, 'smoke_capture_pending') if blocker_codes else None,
        'notes': [
            'Local-only smoke trace for capture handshake verification.',
            'This artifact may include workspace-specific paths because it is not publishable.',
        ],
    }


def build_smoke_report(summary: SmokeSummary, parse_report: dict[str, Any], meta_outcome: ResponseMetaOutcome) -> str:
    lines = [
        '# Wave 4C1.5 Smoke Run Report',
        '',
        f'- generated_at: `{utc_now_iso()}`',
        f'- smoke_passed: `{summary.smoke_passed}`',
        f'- run_state: `{summary.run_state}`',
        f'- parse_status: `{summary.parse_status}`',
        f'- blocker_codes: `{summary.blocker_codes}`',
        '',
        '## Local Handshake Files',
        '',
        f'- prompt_render_path: `{repo_rel(SMOKE_PROMPT_RENDER_PATH)}`',
        f'- execution_trace_path: `{repo_rel(SMOKE_EXECUTION_TRACE_PATH)}`',
        f'- raw_capture_root: `{repo_rel(SMOKE_CAPTURE_ROOT)}`',
        f'- response_meta_path: `{summary.response_meta_path}`',
        f'- capture_instructions_path: `{repo_rel(SMOKE_CAPTURE_ROOT / "CAPTURE_INSTRUCTIONS.md")}`',
        f'- parse_report_path: `{summary.parse_report_path}`',
        '',
        '## Smoke Checks',
        '',
        '- prompt render written: `true`',
        f'- raw response present: `{parse_report.get("raw_response_exists")}`',
        f'- response_meta present: `{meta_outcome.response_meta_exists}`',
        f'- response_meta valid: `{meta_outcome.response_meta_valid}`',
        f'- parser could read raw file: `{parse_report.get("parse_succeeded")}`',
        f'- schema validation succeeded: `{parse_report.get("schema_validation_succeeded")}`',
        f'- parser_error_note: `{parse_report.get("parser_error_note")}`',
        f'- response_meta_validation_errors: `{meta_outcome.validation_errors}`',
        '',
        '## Scope Note',
        '',
        '- This smoke run is non-canonical. It does not produce change-brief, evidence bundle, evidence resolution, or comparison outputs.',
        '',
    ]
    return "\n".join(lines) + "\n"


def run_smoke_handshake() -> SmokeSummary:
    write_json(SMOKE_PROMPT_RENDER_PATH, build_smoke_prompt_render())
    create_raw_capture_scaffold(SMOKE_RUN_ID, 'attempt_01')
    meta_outcome = inspect_response_meta(SMOKE_RUN_ID, 'attempt_01')
    parse = parse_raw_response(SMOKE_RUN_ID, 'attempt_01')
    parse_report = build_parse_report(SMOKE_RUN_ID, 'attempt_01', parse)
    parse_report_rel = repo_rel(parse_report_path(SMOKE_RUN_ID, 'attempt_01'))
    write_json(parse_report_path(SMOKE_RUN_ID, 'attempt_01'), parse_report)

    blocker_codes: list[str] = []
    if not parse.raw_response_exists:
        blocker_codes.append('capture_missing')
    if not meta_outcome.response_meta_exists:
        blocker_codes.append('response_meta_missing')
    elif not meta_outcome.response_meta_valid:
        blocker_codes.extend(meta_outcome.validation_errors or ['response_meta_invalid'])

    if not parse.raw_response_exists or not meta_outcome.response_meta_valid:
        run_state = 'capture_missing'
        parse_status = 'not_run'
    elif not parse.parse_succeeded:
        blocker_codes.append('parse_failed')
        run_state = 'parse_failed'
        parse_status = 'failed'
    elif not parse.schema_validation_succeeded:
        blocker_codes.append('schema_validation_failed')
        run_state = 'parse_failed'
        parse_status = 'failed'
    else:
        run_state = 'captured'
        parse_status = 'passed'

    summary = SmokeSummary(
        smoke_passed=run_state == 'captured' and parse_status == 'passed' and not blocker_codes,
        run_state=run_state,
        parse_status=parse_status,
        blocker_codes=unique_codes(blocker_codes),
        raw_response_path=parse.raw_response_path,
        response_meta_path=meta_outcome.response_meta_path,
        parse_report_path=parse_report_rel,
    )
    write_json(
        SMOKE_EXECUTION_TRACE_PATH,
        build_smoke_execution_trace(summary.run_state, summary.parse_status, summary.blocker_codes, summary.raw_response_path, summary.parse_report_path),
    )
    write_text(SMOKE_REPORT_PATH, build_smoke_report(summary, parse_report, meta_outcome))
    return summary


def build_packet(
    stamp: str,
    artifacts: FinalizeArtifacts,
    smoke_result: SmokeSummary,
) -> tuple[Path, Path]:
    name, packet_dir, zip_path = packet_paths_for_stamp(stamp)
    if packet_dir.exists():
        shutil.rmtree(packet_dir)
    if zip_path.exists():
        zip_path.unlink()

    paths: list[Path] = [
        Path(repo_rel(BOUNDARY_CLEANUP_NOTES_PATH)),
        Path(repo_rel(RUN_STATE_MODEL_UPDATE_PATH)),
        Path(repo_rel(LOCAL_CAPTURE_CONTRACT_PATH)),
        Path(repo_rel(SMOKE_REPORT_PATH)),
        Path(repo_rel(SMOKE_PROMPT_RENDER_PATH)),
        Path(repo_rel(SMOKE_EXECUTION_TRACE_PATH)),
        Path(repo_rel(EXECUTION_REPORT_PATH)),
        Path(repo_rel(REVIEW_NOTES_PATH)),
        Path(repo_rel(REVIEW_PACKET_MD_PATH)),
        Path(repo_rel(RED_TEAM_BRIEF_PATH)),
        Path(repo_rel(HUMAN_EVAL_INPUT_PATH)),
        Path(repo_rel(PARSE_REPORT_SCHEMA_PATH)),
        Path(repo_rel(COMPARISON_VIEW_PATH)),
        Path('docs/protocol_lab/README.md'),
        Path('docs/protocol_lab/prompts/p1_structured_contract_v1.md'),
        Path('docs/protocol_lab/prompts/p2_tagged_input_contract_v1.md'),
        Path('schemas/protocol_lab/execution_trace_v1.schema.json'),
        Path('scripts/protocol_lab_wave4b_reviewability.py'),
        Path('scripts/protocol_lab_wave4c1_nvda_execution.py'),
        Path('scripts/tests/test_protocol_lab_wave4b_reviewability.py'),
        Path('scripts/tests/test_protocol_lab_wave4c1_nvda_execution.py'),
    ]
    paths.extend(Path(repo_rel(path)) for path in wave4b_sample_trace_paths())
    smoke_attempt = SMOKE_CAPTURE_ROOT
    paths.extend(
        [
            Path(repo_rel(smoke_attempt / 'CAPTURE_INSTRUCTIONS.md')),
            Path(repo_rel(smoke_attempt / 'response_meta.json')),
            Path(repo_rel(parse_report_path(SMOKE_RUN_ID, 'attempt_01'))),
        ]
    )
    for raw_file_name in RAW_RESPONSE_FILE_CANDIDATES:
        raw_file_path = smoke_attempt / raw_file_name
        if raw_file_path.exists():
            paths.append(Path(repo_rel(raw_file_path)))

    for result in artifacts.results:
        if result.attempt_label is None:
            raise ValueError(f'Missing attempt_label for {result.run_request_id}')
        current_attempt_dir = attempt_dir(result.run_request_id, result.attempt_label)
        paths.extend(
            [
                Path(repo_rel(run_request_path(result.run_request_id))),
                Path(repo_rel(prompt_render_path(result.run_request_id))),
                Path(repo_rel(execution_trace_path(result.run_request_id))),
                Path(repo_rel(parse_report_path(result.run_request_id, result.attempt_label))),
                Path(repo_rel(current_attempt_dir / 'CAPTURE_INSTRUCTIONS.md')),
                Path(repo_rel(current_attempt_dir / 'response_meta.json')),
            ]
        )
        for raw_file_name in RAW_RESPONSE_FILE_CANDIDATES:
            raw_file_path = current_attempt_dir / raw_file_name
            if raw_file_path.exists():
                paths.append(Path(repo_rel(raw_file_path)))
        if result.downstream_artifacts_materialized:
            paths.extend(
                [
                    Path(repo_rel(change_brief_path(result.run_request_id))),
                    Path(repo_rel(evidence_bundle_path(result.run_request_id))),
                    Path(repo_rel(evidence_resolution_path(result.run_request_id))),
                    Path(repo_rel(eval_path(result.run_request_id))),
                ]
            )

    paths = dedupe_paths([path for path in paths if (REPO_ROOT / path).exists()])
    for relative_path in paths:
        source_path = REPO_ROOT / relative_path
        destination_path = packet_dir / relative_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)
    write_text(packet_dir / 'README.md', build_packet_readme(name, artifacts.results, artifacts.comparison, smoke_result, artifacts.takeaway))
    write_text(packet_dir / 'relevant_files_manifest.md', build_manifest(paths))
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as handle:
        for file_path in packet_dir.rglob('*'):
            if file_path.is_file():
                handle.write(file_path, file_path.relative_to(REPO_ROOT).as_posix())
    return packet_dir, zip_path


def finalize_phase(
    requested_attempt_label: str | None = None,
    allow_materialization: bool = False,
) -> FinalizeArtifacts:
    ensure_parse_report_schema()
    human = load_human_eval()
    attempt_labels = {run_request_id: selected_or_latest_attempt_label(run_request_id, requested_attempt_label) for run_request_id in TARGET_RUN_IDS}

    results: list[RunFinalizeResult] = []
    run_requests: dict[str, dict[str, Any]] = {}
    traces: dict[str, dict[str, Any]] = {}
    parse_reports: dict[str, dict[str, Any]] = {}
    evidence_bundles: dict[str, dict[str, Any]] = {}
    briefs: dict[str, dict[str, Any]] = {}
    resolutions: dict[str, dict[str, Any]] = {}
    evals: dict[str, dict[str, Any]] = {}

    for run_request_id in TARGET_RUN_IDS:
        attempt_label = attempt_labels[run_request_id]
        request = read_json(run_request_path(run_request_id))
        trace = read_json(execution_trace_path(run_request_id))
        input_pack = wave4b.load_input_pack_payload(FIXTURE_ID, as_str(request.get('input_pack_id'), 'input_pack_id'))
        parse = parse_raw_response(run_request_id, attempt_label)
        parse_report = build_parse_report(run_request_id, attempt_label, parse)
        write_json(parse_report_path(run_request_id, attempt_label), parse_report)
        meta_outcome = inspect_response_meta(run_request_id, attempt_label)

        blockers: list[str] = []
        parse_status = 'not_run'
        postprocess_status = 'not_run'
        run_state = 'capture_missing'
        evidence_item_count = 0
        evidence_resolution_result = 'not_run'
        human_eval_present = False
        run_succeeded = False
        downstream_artifacts_materialized = False

        if not parse.raw_response_exists:
            blockers.append('capture_missing')
        if not meta_outcome.response_meta_exists:
            blockers.append('response_meta_missing')
        elif not meta_outcome.response_meta_valid:
            blockers.extend(meta_outcome.validation_errors or ['response_meta_invalid'])

        capture_ready = parse.raw_response_exists and meta_outcome.response_meta_valid
        if capture_ready:
            if not parse.parse_succeeded:
                blockers.append('parse_failed')
                run_state = 'parse_failed'
                parse_status = 'failed'
            elif not parse.schema_validation_succeeded:
                blockers.append('schema_validation_failed')
                run_state = 'parse_failed'
                parse_status = 'failed'
            else:
                parse_status = 'passed'
                identity_ok, identity_note = check_model_identity(meta_outcome)
                if not identity_ok:
                    blockers.append(identity_note or 'model_identity_unconfirmed')
                    run_state = 'captured'
                    postprocess_status = 'failed'
                elif not allow_materialization:
                    blockers.append('smoke_run_failed')
                    run_state = 'captured'
                else:
                    envelope = as_dict(parse.envelope, 'parse.envelope')
                    brief = build_change_brief(request, envelope)
                    bundle = build_evidence_bundle(request, envelope)
                    resolution = wave4b.build_evidence_resolution_payload(request, brief, bundle, input_pack)
                    rubric, failure_tags, reviewer_notes, human_eval_present = sanitize_human_entry(human['runs'].get(run_request_id))
                    hard_checks = build_hard_checks(brief, bundle, resolution)
                    eval_payload = build_eval(
                        run_request_id,
                        hard_checks,
                        rubric,
                        failure_tags,
                        reviewer_notes,
                        as_str(brief.get('change_brief_output_id'), 'change_brief_output_id'),
                        as_str(bundle.get('evidence_bundle_id'), 'evidence_bundle_id'),
                        human_eval_present,
                    )
                    write_json(change_brief_path(run_request_id), brief)
                    write_json(evidence_bundle_path(run_request_id), bundle)
                    write_json(evidence_resolution_path(run_request_id), resolution)
                    write_json(eval_path(run_request_id), eval_payload)
                    briefs[run_request_id] = brief
                    evidence_bundles[run_request_id] = bundle
                    resolutions[run_request_id] = resolution
                    evals[run_request_id] = eval_payload
                    downstream_artifacts_materialized = True
                    evidence_item_count = len(as_list(bundle.get('items'), 'evidence_bundle.items'))
                    evidence_resolution_result = as_str(as_dict(resolution.get('resolution_summary'), 'resolution_summary').get('overall_result'), 'overall_result')
                    hard_checks_pass = all(value == 'pass' for value in hard_checks.values())
                    if evidence_item_count == 0:
                        blockers.append('evidence_bundle_empty')
                    if evidence_resolution_result != 'pass':
                        blockers.append('evidence_resolution_not_pass')
                    if not hard_checks_pass:
                        blockers.append('hard_checks_failed')
                    if blockers:
                        run_state = 'captured'
                        postprocess_status = 'failed'
                    elif human_eval_present:
                        run_state = 'reviewed'
                        postprocess_status = 'passed'
                        run_succeeded = True
                    else:
                        run_state = 'validated'
                        postprocess_status = 'passed'
                        run_succeeded = True

        blockers = unique_codes(blockers)
        trace = update_trace(
            trace,
            run_state,
            parse_status,
            postprocess_status,
            parse.raw_response_path,
            repo_rel(parse_report_path(run_request_id, attempt_label)),
            attempt_label,
            parse,
            blockers,
            evidence_item_count,
        )
        write_json(execution_trace_path(run_request_id), trace)

        blocker_note = public_blocker_note(blockers, run_state)
        if run_state in {'validated', 'reviewed'}:
            note = f'Wave 4C1.5 {run_state} for `{attempt_label}`.'
            request = update_request_status(request, 'completed', note)
        elif run_state == 'capture_missing':
            note = f'Wave 4C1.5 blocked: {blocker_note} for `{attempt_label}`.'
            request = update_request_status(request, 'blocked', note)
        elif run_state == 'parse_failed':
            note = f'Wave 4C1.5 failed: {blocker_note} for `{attempt_label}`.'
            request = update_request_status(request, 'failed', note)
        else:
            status = 'failed' if postprocess_status == 'failed' else 'blocked'
            note = f'Wave 4C1.5 blocked: {blocker_note} for `{attempt_label}`.'
            request = update_request_status(request, status, note)
        write_json(run_request_path(run_request_id), request)

        run_requests[run_request_id] = request
        traces[run_request_id] = trace
        parse_reports[run_request_id] = parse_report
        results.append(
            RunFinalizeResult(
                run_request_id=run_request_id,
                run_succeeded=run_succeeded,
                run_state=run_state,
                parse_status=parse_status,
                postprocess_status=postprocess_status,
                raw_response_path=parse.raw_response_path,
                parse_report_path=repo_rel(parse_report_path(run_request_id, attempt_label)),
                evidence_item_count=evidence_item_count,
                evidence_resolution_overall_result=evidence_resolution_result,
                human_eval_present=human_eval_present,
                blocker_notes=blockers,
                attempt_label=attempt_label,
                downstream_artifacts_materialized=downstream_artifacts_materialized,
            )
        )

    write_text(RED_TEAM_BRIEF_PATH, build_red_team_brief(attempt_labels, results))
    comparison_input = human.get('comparison', {})
    comparison, comparison_real, takeaway = build_comparison(read_json(COMPARISON_VIEW_PATH), results, evals, briefs, comparison_input)
    write_json(COMPARISON_VIEW_PATH, comparison)
    return FinalizeArtifacts(
        results=results,
        comparison=comparison,
        comparison_is_real=comparison_real,
        takeaway=takeaway,
        run_requests=run_requests,
        traces=traces,
        parse_reports=parse_reports,
        evidence_bundles=evidence_bundles,
        briefs=briefs,
        resolutions=resolutions,
        evals=evals,
    )


def run_wave4c15(
    requested_attempt_label: str | None = None,
    run_prepare: bool = True,
) -> Wave4c15Summary:
    ensure_parse_report_schema()
    ensure_wave4c15_docs()
    if run_prepare:
        prepare_phase(requested_attempt_label)
    else:
        ensure_human_eval_template()
    wave4b.generate_wave4b_artifacts()
    smoke_result = run_smoke_handshake()
    artifacts = finalize_phase(requested_attempt_label, allow_materialization=smoke_result.smoke_passed)

    results_by_run = {result.run_request_id: result for result in artifacts.results}
    write_text(
        REVIEW_PACKET_MD_PATH,
        build_review_packet_text(
            results_by_run,
            artifacts.run_requests,
            artifacts.traces,
            artifacts.parse_reports,
            artifacts.evidence_bundles,
            artifacts.briefs,
            artifacts.resolutions,
            artifacts.evals,
            artifacts.comparison,
            artifacts.takeaway,
        ),
    )

    takeaway = artifacts.takeaway if smoke_result.smoke_passed else 'Smoke run did not pass; NVDA P1/P2 rerun was not attempted.'
    stamp = utc_stamp()
    _, predicted_packet_dir, predicted_zip_path = packet_paths_for_stamp(stamp)
    write_text(EXECUTION_REPORT_PATH, build_execution_report(artifacts.results, smoke_result, predicted_packet_dir, predicted_zip_path, takeaway))
    write_text(REVIEW_NOTES_PATH, build_review_notes(artifacts.results, artifacts.evals, artifacts.comparison, takeaway, smoke_result))
    packet_dir, zip_path = build_packet(stamp, artifacts, smoke_result)

    real_non_empty_evidence_materialized = any(
        result.downstream_artifacts_materialized and result.evidence_item_count > 0
        for result in artifacts.results
    )
    if not smoke_result.smoke_passed:
        biggest_remaining_blocker = public_blocker_note(smoke_result.blocker_codes, 'operator_capture_required')
    else:
        run_blockers: list[str] = []
        for result in artifacts.results:
            run_blockers.extend(result.blocker_notes)
        if artifacts.comparison.get('artifact_status') == 'pending':
            run_blockers.append('human_review_pending')
        biggest_remaining_blocker = public_blocker_note(run_blockers, 'none')

    return Wave4c15Summary(
        packet_dir=packet_dir,
        zip_path=zip_path,
        boundary_cleanup_completed=True,
        run_state_semantics_updated=True,
        smoke_passed=smoke_result.smoke_passed,
        nvda_rerun_attempted=smoke_result.smoke_passed,
        real_non_empty_evidence_materialized=real_non_empty_evidence_materialized,
        biggest_remaining_blocker=biggest_remaining_blocker,
        takeaway=takeaway,
        run_results=artifacts.results,
        smoke_result=smoke_result,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description='Wave4C1.5 capture boundary driver')
    parser.add_argument('phase', nargs='?', choices=['prepare', 'finalize', 'all'], default='all')
    parser.add_argument('--attempt-label', dest='attempt_label', default=None)
    args = parser.parse_args()

    if args.phase == 'prepare':
        ensure_wave4c15_docs()
        prepare_phase(args.attempt_label)
        print('Wave4C1.5 prepare complete.')
        return 0

    summary = run_wave4c15(args.attempt_label, run_prepare=args.phase == 'all')
    print(f'packet folder path: {summary.packet_dir}')
    print(f'zip path: {summary.zip_path}')
    print(f'whether public/local boundary cleanup was completed: {yes_no(summary.boundary_cleanup_completed)}')
    print(f'whether run-state semantics were updated: {yes_no(summary.run_state_semantics_updated)}')
    print(f'whether the smoke run passed: {yes_no(summary.smoke_passed)}')
    print(f'whether NVDA P1/P2 rerun was attempted: {yes_no(summary.nvda_rerun_attempted)}')
    print(f'whether any real non-empty evidence bundles were materialized: {yes_no(summary.real_non_empty_evidence_materialized)}')
    print(f'biggest remaining blocker after Wave 4C1.5: {summary.biggest_remaining_blocker}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
