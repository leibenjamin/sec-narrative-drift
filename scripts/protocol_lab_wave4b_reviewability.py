from __future__ import annotations

import json
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
BUSINESS_ROOT = REPO_ROOT / "public" / "data" / "business_document_protocol_lab"
RUNS_ROOT = BUSINESS_ROOT / "runs"
EVALS_ROOT = BUSINESS_ROOT / "evals"
INPUT_PACKS_ROOT = BUSINESS_ROOT / "input_packs"
SOURCE_CASES_ROOT = BUSINESS_ROOT / "source_cases"
REGISTRIES_ROOT = BUSINESS_ROOT / "registries"
PROMPTS_ROOT = REPO_ROOT / "docs" / "protocol_lab" / "prompts"
REPORTS_ROOT = REPO_ROOT / "reports" / "protocol_lab"
SCHEMAS_ROOT = REPO_ROOT / "schemas" / "protocol_lab"

FIXTURE_ID = "NVDA_2024_2025_10k_item1a"
SAMPLE_RUN_IDS = [
    "NVDA_2024_2025_10k_item1a__p2_tagged_input_contract_v1__m_primary_strong_reasoning_v1",
    "NVDA_2024_2025_10k_item1a__p1_structured_contract_v1__m_primary_strong_reasoning_v1__i0_filed_full_text_v1",
    "NVDA_2024_2025_10k_item1a__p3_extract_then_synthesize_v1__m_primary_strong_reasoning_v1",
]
P3_STEP_LABELS = [
    "step_1_extract_evidence",
    "step_2_synthesize_change_brief",
]
BIGGEST_UNRESOLVED_QUESTION = (
    "When should NVDA i3_extractive_evidence_packet_v1 become a deterministic reusable artifact "
    "so the first true P3/topology pilot can move from scaffolded lineage into real execution?"
)
PROMPT_TEMPLATE_PATHS: dict[tuple[str, str | None], Path] = {
    ("p0_plain_prompt_v1", None): PROMPTS_ROOT / "p0_plain_prompt_v1.md",
    ("p1_structured_contract_v1", None): PROMPTS_ROOT / "p1_structured_contract_v1.md",
    ("p2_tagged_input_contract_v1", None): PROMPTS_ROOT / "p2_tagged_input_contract_v1.md",
    (
        "p3_extract_then_synthesize_v1",
        "step_1_extract_evidence",
    ): PROMPTS_ROOT / "p3_extract_then_synthesize_v1__step_1_extract_evidence.md",
    (
        "p3_extract_then_synthesize_v1",
        "step_2_synthesize_change_brief",
    ): PROMPTS_ROOT / "p3_extract_then_synthesize_v1__step_2_synthesize_change_brief.md",
}
PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected object at {path}.")
    return cast(dict[str, Any], payload)


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
    return cast(dict[str, Any], value)


def as_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError(f"Expected array for {label}.")
    return cast(list[Any], value)


def as_str(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"Expected string for {label}.")
    return value


def maybe_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def maybe_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None

def ensure_registry_map(path: Path, key_name: str) -> dict[str, dict[str, Any]]:
    payload = read_json(path)
    items = as_list(payload.get("items"), f"{path} items")
    mapped: dict[str, dict[str, Any]] = {}
    for raw_item in items:
        item = as_dict(raw_item, f"{path} item")
        mapped[as_str(item.get(key_name), f"{path} {key_name}")] = item
    return mapped


def load_prompt_template(protocol_id: str, step_label: str | None) -> tuple[Path, str, str]:
    key = (protocol_id, step_label)
    if key not in PROMPT_TEMPLATE_PATHS:
        raise KeyError(f"No prompt template for {key}.")
    path = PROMPT_TEMPLATE_PATHS[key]
    text = path.read_text(encoding="utf-8")
    system_marker = "## System Template"
    user_marker = "## User Template"
    system_start = text.index(system_marker) + len(system_marker)
    user_start = text.index(user_marker)
    system_template = text[system_start:user_start].strip()
    user_template = text[user_start + len(user_marker) :].strip()
    return path, system_template, user_template


def render_template(template: str, mapping: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in mapping:
            raise KeyError(f"Missing template value for {key}.")
        return mapping[key]

    rendered = PLACEHOLDER_RE.sub(replace, template)
    leftovers = PLACEHOLDER_RE.findall(rendered)
    if leftovers:
        raise ValueError(f"Unresolved placeholders remain: {leftovers}")
    return rendered


def load_input_pack_payload(fixture_id: str, input_pack_id: str) -> dict[str, Any] | None:
    manifest_path = INPUT_PACKS_ROOT / fixture_id / f"{input_pack_id}.json"
    if not manifest_path.exists():
        return None
    payload = read_json(manifest_path)
    if "rendered_inputs" not in payload:
        rendered_inputs_path = maybe_str(payload.get("rendered_inputs_path"))
        if rendered_inputs_path is None:
            raise ValueError(f"Missing rendered_inputs payload for {manifest_path}.")
        materialized = dict(payload)
        materialized["rendered_inputs"] = read_json(REPO_ROOT / rendered_inputs_path)
        return materialized
    return payload


def format_locator(locator: dict[str, Any] | None) -> str:
    if locator is None:
        return "not_available"
    char_start = maybe_int(locator.get("char_start"))
    char_end = maybe_int(locator.get("char_end"))
    char_range = f"{char_start}-{char_end}" if char_start is not None and char_end is not None else "null"
    return (
        f"accession={maybe_str(locator.get('accession_number')) or 'null'}; "
        f"filing_date={maybe_str(locator.get('filing_date')) or 'null'}; "
        f"form_type={maybe_str(locator.get('form_type')) or 'null'}; "
        f"section_id={maybe_str(locator.get('section_id')) or 'null'}; "
        f"source_path={maybe_str(locator.get('source_path')) or 'null'}; "
        f"chars={char_range}"
    )


_QUOTE_MAP = str.maketrans({
    "\u2018": "'",   # left single quote
    "\u2019": "'",   # right single quote / apostrophe
    "\u201C": '"',   # left double quote
    "\u201D": '"',   # right double quote
    "\u2013": "-",   # en dash
    "\u2014": "-",   # em dash
})


def normalize_text_for_match(text: str) -> str:
    """Normalize line endings and smart punctuation for substring matching.

    SEC EDGAR sources commonly contain Unicode smart quotes and dashes that
    models straighten to ASCII equivalents when quoting.  Normalizing both
    sides prevents false-negative quote-match failures from typographic
    transport differences.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n").translate(_QUOTE_MAP).strip()


def path_for_run(run_request: dict[str, Any]) -> Path:
    fixture_id = as_str(run_request.get("fixture_id"), "fixture_id")
    run_request_id = as_str(run_request.get("run_request_id"), "run_request_id")
    return RUNS_ROOT / fixture_id / run_request_id


def path_for_prompt_render(run_request: dict[str, Any], step_label: str | None) -> Path:
    run_dir = path_for_run(run_request)
    if step_label is None:
        return run_dir / "prompt_render_v1.json"
    return run_dir / "steps" / step_label / "prompt_render_v1.json"


def path_for_execution_trace(run_request: dict[str, Any], step_label: str | None) -> Path:
    run_dir = path_for_run(run_request)
    if step_label is None:
        return run_dir / "execution_trace_v1.json"
    return run_dir / "steps" / step_label / "execution_trace_v1.json"


def path_for_evidence_resolution(run_request: dict[str, Any]) -> Path:
    return path_for_run(run_request) / "evidence_resolution_v1.json"


def path_for_raw_attempt(run_request: dict[str, Any], step_label: str | None) -> Path:
    fixture_id = as_str(run_request.get("fixture_id"), "fixture_id")
    run_request_id = as_str(run_request.get("run_request_id"), "run_request_id")
    lane = step_label or "main"
    return REPORTS_ROOT / "raw_runs" / fixture_id / run_request_id / lane / "attempt_01"

def build_source_case_summary(source_case_manifest: dict[str, Any]) -> str:
    years = as_list(source_case_manifest.get("years"), "source_case years")
    lines = [
        f"- ticker: `{as_str(source_case_manifest.get('ticker'), 'ticker')}`",
        f"- issuer_name: `{as_str(source_case_manifest.get('issuer_name'), 'issuer_name')}`",
        f"- form_type: `{as_str(source_case_manifest.get('form_type'), 'form_type')}`",
        f"- section_id: `{as_str(source_case_manifest.get('section_id'), 'section_id')}`",
        f"- availability_status: `{as_str(source_case_manifest.get('availability_status'), 'availability_status')}`",
        f"- extraction_quality_status: `{as_str(source_case_manifest.get('extraction_quality_status'), 'extraction_quality_status')}`",
        f"- analysis_readiness_status: `{as_str(source_case_manifest.get('analysis_readiness_status'), 'analysis_readiness_status')}`",
    ]
    for raw_year in years:
        year = as_dict(raw_year, "source_case year")
        lines.append(
            "- "
            + f"{as_str(year.get('year_label'), 'year_label')}: accession `"
            + f"{as_str(year.get('accession_number'), 'accession_number')}`, filing_date `"
            + f"{as_str(year.get('filing_date'), 'filing_date')}`, readiness `"
            + f"{as_str(year.get('analysis_readiness_status'), 'analysis_readiness_status')}`"
        )
    return "\n".join(lines)


def format_expected_artifact_paths(
    run_request: dict[str, Any],
    prompt_render_path: Path,
    execution_trace_path: Path,
    evidence_resolution_path: Path,
) -> str:
    expected_paths = as_dict(run_request.get("expected_artifact_paths"), "expected_artifact_paths")
    lines = [f"- {key}: `{value}`" for key, value in expected_paths.items()]
    lines.extend(
        [
            f"- prompt_render_path: `{repo_rel(prompt_render_path)}`",
            f"- execution_trace_path: `{repo_rel(execution_trace_path)}`",
            f"- evidence_resolution_path: `{repo_rel(evidence_resolution_path)}`",
        ]
    )
    return "\n".join(lines)


def build_input_content_block(run_request: dict[str, Any], input_pack_payload: dict[str, Any] | None) -> str:
    if input_pack_payload is None:
        return (
            "Deferred contract-only input pack.\n"
            + f"- input_pack_id: `{as_str(run_request.get('input_pack_id'), 'input_pack_id')}`\n"
            + "- materialized_input_pack: `not_present`\n"
            + "- note: `Wave 4B keeps this multi-step lineage scaffolded until a deterministic i3 extractor exists.`"
        )

    rendered_inputs = as_dict(input_pack_payload.get("rendered_inputs"), "rendered_inputs")
    documents = as_list(rendered_inputs.get("documents"), "rendered_inputs.documents")
    chunks: list[str] = []
    for raw_document in documents:
        document = as_dict(raw_document, "rendered document")
        lines = [
            f"Document `{as_str(document.get('document_id'), 'document_id')}`",
            f"- year_label: `{as_str(document.get('year_label'), 'year_label')}`",
            f"- source_input_path: `{maybe_str(document.get('source_input_path')) or 'null'}`",
            f"- source_locator: {format_locator(as_dict(document.get('source_locator'), 'source_locator'))}",
        ]
        if isinstance(document.get("paragraphs"), list):
            lines.append("Paragraphs:")
            for raw_paragraph in as_list(document.get("paragraphs"), "paragraphs"):
                paragraph = as_dict(raw_paragraph, "paragraph")
                lines.append(
                    "- "
                    + f"{as_str(paragraph.get('paragraph_id'), 'paragraph_id')} | "
                    + f"{format_locator(as_dict(paragraph.get('source_locator'), 'paragraph locator'))} | "
                    + as_str(paragraph.get("text"), "paragraph text")
                )
        else:
            lines.append("Content:")
            lines.append(maybe_str(document.get("content_text")) or "[no content_text supplied]")
        chunks.append("\n".join(lines))
    return "\n\n".join(chunks)


def has_locator(locator: dict[str, Any] | None) -> bool:
    if locator is None:
        return False
    return bool(maybe_str(locator.get("form_type"))) and bool(maybe_str(locator.get("section_id"))) and bool(
        maybe_str(locator.get("source_path"))
    )


def locator_matches(evidence_locator: dict[str, Any] | None, reference_locator: dict[str, Any] | None) -> bool:
    if evidence_locator is None or reference_locator is None:
        return False
    for key in ("accession_number", "filing_date", "form_type", "section_id", "source_path"):
        evidence_value = evidence_locator.get(key)
        if evidence_value is None:
            continue
        if evidence_value != reference_locator.get(key):
            return False
    return True


def char_range_status(evidence_locator: dict[str, Any] | None, reference_locator: dict[str, Any] | None) -> str:
    if evidence_locator is None:
        return "fail"
    evidence_start = maybe_int(evidence_locator.get("char_start"))
    evidence_end = maybe_int(evidence_locator.get("char_end"))
    if evidence_start is None or evidence_end is None:
        return "not_applicable"
    if reference_locator is None:
        return "fail"
    reference_start = maybe_int(reference_locator.get("char_start"))
    reference_end = maybe_int(reference_locator.get("char_end"))
    if reference_start is None or reference_end is None:
        return "fail"
    return "pass" if reference_start <= evidence_start <= evidence_end <= reference_end else "fail"

def resolve_evidence_items(
    input_pack_payload: dict[str, Any] | None,
    evidence_bundle_payload: dict[str, Any],
) -> dict[str, Any]:
    evidence_items = as_list(evidence_bundle_payload.get("items"), "evidence_bundle items")
    if not evidence_items:
        return {
            "resolution_summary": {
                "overall_result": "not_run",
                "total_evidence_items": 0,
                "resolved_item_count": 0,
                "failed_item_count": 0,
                "quote_text_pass_count": 0,
                "locator_match_pass_count": 0,
                "paragraph_id_pass_count": 0,
            },
            "items": [],
        }

    indexed_documents: list[dict[str, Any]] = []
    if input_pack_payload is not None:
        rendered_inputs = as_dict(input_pack_payload.get("rendered_inputs"), "rendered_inputs")
        for raw_document in as_list(rendered_inputs.get("documents"), "rendered_inputs.documents"):
            document = as_dict(raw_document, "document")
            paragraphs_by_id: dict[str, dict[str, Any]] = {}
            if isinstance(document.get("paragraphs"), list):
                for raw_paragraph in as_list(document.get("paragraphs"), "paragraphs"):
                    paragraph = as_dict(raw_paragraph, "paragraph")
                    paragraphs_by_id[as_str(paragraph.get("paragraph_id"), "paragraph_id")] = paragraph
            indexed_documents.append(
                {
                    "document_id": as_str(document.get("document_id"), "document_id"),
                    "year_label": as_str(document.get("year_label"), "year_label"),
                    "content_text": maybe_str(document.get("content_text")),
                    "source_locator": as_dict(document.get("source_locator"), "source_locator"),
                    "paragraphs_by_id": paragraphs_by_id,
                }
            )

    resolved_items: list[dict[str, Any]] = []
    for raw_item in evidence_items:
        evidence = as_dict(raw_item, "evidence item")
        evidence_id = maybe_str(evidence.get("evidence_id")) or ""
        year_label = maybe_str(evidence.get("year_label")) or ""
        paragraph_id = maybe_str(evidence.get("paragraph_id")) or ""
        quote_text = maybe_str(evidence.get("quote_text")) or ""
        evidence_locator = as_dict(evidence.get("source_locator"), "evidence source_locator")

        matched_document: dict[str, Any] | None = None
        year_matches = [doc for doc in indexed_documents if doc["year_label"] == year_label]
        for candidate in year_matches or indexed_documents:
            candidate_locator = candidate.get("source_locator")
            if locator_matches(evidence_locator, candidate_locator):
                matched_document = candidate
                break
        if matched_document is None and year_matches:
            matched_document = year_matches[0]

        matched_paragraph: dict[str, Any] | None = None
        paragraph_check = "not_applicable"
        reference_text: str | None = None
        reference_locator: dict[str, Any] | None = None
        matched_document_id = None
        matched_year_label = None
        matched_paragraph_id = None

        if matched_document is not None:
            matched_document_id = matched_document["document_id"]
            matched_year_label = matched_document["year_label"]
            paragraphs_by_id = matched_document["paragraphs_by_id"]
            if paragraphs_by_id:
                matched_paragraph = paragraphs_by_id.get(paragraph_id)
                paragraph_check = "pass" if matched_paragraph is not None else "fail"
            if matched_paragraph is not None:
                matched_paragraph_id = matched_paragraph["paragraph_id"]
                reference_text = as_str(matched_paragraph.get("text"), "paragraph text")
                reference_locator = as_dict(matched_paragraph.get("source_locator"), "paragraph source_locator")
            else:
                reference_text = matched_document["content_text"]
                reference_locator = matched_document["source_locator"]

        quote_check = "fail"
        if quote_text and reference_text is not None:
            quote_check = (
                "pass"
                if normalize_text_for_match(quote_text) in normalize_text_for_match(reference_text)
                else "fail"
            )

        checks = {
            "evidence_id_present": "pass" if evidence_id else "fail",
            "source_locator_present": "pass" if has_locator(evidence_locator) else "fail",
            "locator_matches_source": (
                "pass" if locator_matches(evidence_locator, reference_locator) else "fail"
            ),
            "year_label_match": "pass" if matched_year_label == year_label else "fail",
            "paragraph_id_exists": paragraph_check,
            "quote_text_present": quote_check,
            "char_range_within_source": char_range_status(evidence_locator, reference_locator),
        }
        overall_result = "pass" if all(value in {"pass", "not_applicable"} for value in checks.values()) else "fail"
        note = None
        if matched_document is None:
            note = "No input-pack document matched the evidence year label or locator."
        elif paragraph_check == "fail":
            note = "Paragraph id did not resolve in the tagged packet."

        resolved_items.append(
            {
                "evidence_id": evidence_id,
                "year_label": year_label,
                "paragraph_id": paragraph_id,
                "matched_document_id": matched_document_id,
                "matched_year_label": matched_year_label,
                "matched_paragraph_id": matched_paragraph_id,
                "overall_result": overall_result,
                "checks": checks,
                "note": note,
            }
        )

    failed_item_count = sum(1 for item in resolved_items if item["overall_result"] == "fail")
    resolved_item_count = sum(1 for item in resolved_items if item["overall_result"] == "pass")
    quote_text_pass_count = sum(1 for item in resolved_items if item["checks"]["quote_text_present"] == "pass")
    locator_match_pass_count = sum(1 for item in resolved_items if item["checks"]["locator_matches_source"] == "pass")
    paragraph_id_pass_count = sum(1 for item in resolved_items if item["checks"]["paragraph_id_exists"] == "pass")
    return {
        "resolution_summary": {
            "overall_result": "pass" if failed_item_count == 0 else "fail",
            "total_evidence_items": len(resolved_items),
            "resolved_item_count": resolved_item_count,
            "failed_item_count": failed_item_count,
            "quote_text_pass_count": quote_text_pass_count,
            "locator_match_pass_count": locator_match_pass_count,
            "paragraph_id_pass_count": paragraph_id_pass_count,
        },
        "items": resolved_items,
    }


def input_pack_integrity(input_pack_payload: dict[str, Any] | None) -> tuple[str | None, str]:
    if input_pack_payload is None:
        return None, "deferred_contract_only"
    integrity_hash = maybe_str(input_pack_payload.get("integrity_hash"))
    if integrity_hash is None:
        return None, "not_available"
    return integrity_hash, "input_pack_manifest"


def input_pack_integrity_note(input_pack_payload: dict[str, Any] | None) -> str:
    integrity_hash, integrity_source = input_pack_integrity(input_pack_payload)
    if integrity_hash is not None:
        return f"{integrity_source}: {integrity_hash}"
    if integrity_source == "deferred_contract_only":
        return "deferred_contract_only: no materialized input-pack artifact exists for this fixture yet"
    return "not_available: integrity hash missing from the input-pack manifest"

def build_prompt_render_payload(
    run_request: dict[str, Any],
    source_case_manifest: dict[str, Any],
    runner_binding: dict[str, Any],
    input_pack_payload: dict[str, Any] | None,
    step_label: str | None,
) -> dict[str, Any]:
    protocol_id = as_str(run_request.get("protocol_id"), "protocol_id")
    template_path, system_template, user_template = load_prompt_template(protocol_id, step_label)
    prompt_render_path = path_for_prompt_render(run_request, step_label)
    execution_trace_path = path_for_execution_trace(run_request, step_label)
    evidence_resolution_path = path_for_evidence_resolution(run_request)
    integrity_hash, integrity_source = input_pack_integrity(input_pack_payload)
    selection = as_dict(run_request.get("input_pack_selection"), "input_pack_selection")
    mapping = {
        "TASK_FAMILY_ID": as_str(run_request.get("task_family_id"), "task_family_id"),
        "RUN_REQUEST_ID": as_str(run_request.get("run_request_id"), "run_request_id"),
        "RUN_LABEL": as_str(run_request.get("run_label"), "run_label"),
        "FIXTURE_ID": as_str(run_request.get("fixture_id"), "fixture_id"),
        "PROTOCOL_ID": protocol_id,
        "MODEL_PROFILE_ID": as_str(run_request.get("model_profile_id"), "model_profile_id"),
        "RUNNER_BINDING_ID": as_str(run_request.get("runner_binding_id"), "runner_binding_id"),
        "RUNNER_CAMPAIGN_ID": as_str(runner_binding.get("campaign_id"), "campaign_id"),
        "STACK_ID": maybe_str(run_request.get("stack_id")) or "null",
        "STEP_LABEL": step_label or "main",
        "INPUT_PACK_ID": as_str(run_request.get("input_pack_id"), "input_pack_id"),
        "INPUT_PACK_INTEGRITY_NOTE": input_pack_integrity_note(input_pack_payload),
        "EXPECTED_OUTPUT_PATHS": format_expected_artifact_paths(
            run_request,
            prompt_render_path,
            execution_trace_path,
            evidence_resolution_path,
        ),
        "SOURCE_CASE_SUMMARY": build_source_case_summary(source_case_manifest),
        "INPUT_CONTENT_BLOCK": build_input_content_block(run_request, input_pack_payload),
    }
    is_scaffolded = integrity_source == "deferred_contract_only"
    return {
        "artifact_status": "scaffolded" if is_scaffolded else "complete",
        "artifact_status_note": (
            "Scaffolded only because the i3 contract is deferred for NVDA in Wave 4B."
            if is_scaffolded
            else "Prompt rendered deterministically from repo-local template sources."
        ),
        "artifact_schema_id": "prompt_render_v1",
        "prompt_render_id": (
            f"{as_str(run_request.get('run_request_id'), 'run_request_id')}__{step_label}__prompt_render_v1"
            if step_label is not None
            else f"{as_str(run_request.get('run_request_id'), 'run_request_id')}__prompt_render_v1"
        ),
        "run_request_id": as_str(run_request.get("run_request_id"), "run_request_id"),
        "fixture_id": as_str(run_request.get("fixture_id"), "fixture_id"),
        "protocol_id": protocol_id,
        "model_profile_id": as_str(run_request.get("model_profile_id"), "model_profile_id"),
        "runner_binding_id": as_str(run_request.get("runner_binding_id"), "runner_binding_id"),
        "stack_id": maybe_str(run_request.get("stack_id")),
        "step_label": step_label,
        "prompt_template_path": repo_rel(template_path),
        "rendered_system_content": render_template(system_template, mapping),
        "rendered_user_content": render_template(user_template, mapping),
        "input_pack_id": as_str(run_request.get("input_pack_id"), "input_pack_id"),
        "input_pack_integrity_hash": integrity_hash,
        "input_pack_integrity_source": integrity_source,
        "created_at": as_str(run_request.get("created_at"), "created_at"),
        "notes": [
            f"Rendered deterministically from `{repo_rel(template_path)}`.",
            f"Input-pack selection source: `{as_str(selection.get('selection_source'), 'selection_source')}`.",
            "Wave 4B does not submit real model executions for these sample lineage artifacts.",
        ],
    }


def build_execution_trace_payload(
    run_request: dict[str, Any],
    prompt_render_payload: dict[str, Any],
    step_label: str | None,
) -> dict[str, Any]:
    is_scaffolded = prompt_render_payload["artifact_status"] == "scaffolded"
    return {
        "artifact_status": "scaffolded" if is_scaffolded else "complete",
        "artifact_status_note": (
            "Scaffolded execution trace only; no submitted run exists for this step."
            if is_scaffolded
            else "Rendered-only execution trace; no submission occurred in Wave 4B."
        ),
        "artifact_schema_id": "execution_trace_v1",
        "execution_trace_id": (
            f"{as_str(run_request.get('run_request_id'), 'run_request_id')}__{step_label}__execution_trace_v1"
            if step_label is not None
            else f"{as_str(run_request.get('run_request_id'), 'run_request_id')}__execution_trace_v1"
        ),
        "run_request_id": as_str(run_request.get("run_request_id"), "run_request_id"),
        "prompt_render_id": as_str(prompt_render_payload.get("prompt_render_id"), "prompt_render_id"),
        "runner_binding_id": as_str(run_request.get("runner_binding_id"), "runner_binding_id"),
        "step_label": step_label,
        "run_state": "scaffolded" if is_scaffolded else "rendered",
        "started_at": None,
        "finished_at": None,
        "raw_response_path": None,
        "parse_status": "not_run",
        "postprocess_status": "not_run",
        "usage_metadata": None,
        "error_note": None,
        "notes": [
            "No real model submission occurred in Wave 4B.",
            "Raw capture remains local-only and is not exposed in public execution traces.",
        ],
    }


def build_evidence_resolution_payload(
    run_request: dict[str, Any],
    change_brief_output_payload: dict[str, Any],
    evidence_bundle_payload: dict[str, Any],
    input_pack_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    resolution = resolve_evidence_items(input_pack_payload, evidence_bundle_payload)
    scaffolded = resolution["resolution_summary"]["overall_result"] == "not_run"
    return {
        "artifact_status": "scaffolded" if scaffolded else "complete",
        "artifact_status_note": (
            "Zero-item scaffold only; no fresh evidence bundle exists for deterministic checking."
            if scaffolded
            else None
        ),
        "artifact_schema_id": "evidence_resolution_v1",
        "evidence_resolution_id": f"{as_str(run_request.get('run_request_id'), 'run_request_id')}__evidence_resolution_v1",
        "run_request_id": as_str(run_request.get("run_request_id"), "run_request_id"),
        "fixture_id": as_str(run_request.get("fixture_id"), "fixture_id"),
        "protocol_id": as_str(run_request.get("protocol_id"), "protocol_id"),
        "model_profile_id": as_str(run_request.get("model_profile_id"), "model_profile_id"),
        "runner_binding_id": as_str(run_request.get("runner_binding_id"), "runner_binding_id"),
        "input_pack_id": as_str(run_request.get("input_pack_id"), "input_pack_id"),
        "evidence_bundle_path": as_str(
            run_request["expected_artifact_paths"].get("evidence_bundle_path"),
            "evidence_bundle_path",
        ),
        "change_brief_output_path": as_str(
            run_request["expected_artifact_paths"].get("change_brief_output_path"),
            "change_brief_output_path",
        ),
        "resolution_summary": resolution["resolution_summary"],
        "items": resolution["items"],
        "notes": [
            f"Evidence bundle artifact_status: `{as_str(evidence_bundle_payload.get('artifact_status'), 'artifact_status')}`.",
            f"Change brief artifact_status: `{as_str(change_brief_output_payload.get('artifact_status'), 'artifact_status')}`.",
            "Wave 4B evidence resolution is deterministic and intentionally narrow: exact locator and quote checks only.",
        ],
    }

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


def build_packet_readme(packet_name: str, generated_paths: list[Path]) -> str:
    lines = [
        f"# {packet_name}",
        "",
        "Wave 4B review packet for Protocol Lab run lineage, evidence resolution, and reviewability.",
        "",
        "## Included sample lineages",
        f"- {SAMPLE_RUN_IDS[0]}: rendered single-pass lineage scaffold with tagged-input prompt render and execution trace.",
        f"- {SAMPLE_RUN_IDS[1]}: rendered single-pass lineage scaffold using the filed full text override path.",
        f"- {SAMPLE_RUN_IDS[2]}: multi-step scaffold with step-level lineage artifacts only because NVDA i3 remains deferred.",
        "",
        "## Scope notes",
        "- No real model responses were executed for this packet.",
        "- Raw-response storage remains local-only under reports/protocol_lab/raw_runs/.",
        "- Deterministic evidence resolution is implemented, but the sample NVDA bundles remain zero-item scaffolds.",
        "",
        "## Generated artifact paths",
    ]
    lines.extend(f"- {path.as_posix()}" for path in generated_paths)
    lines.extend(["", "## Biggest unresolved question", f"- {BIGGEST_UNRESOLVED_QUESTION}"])
    return "\n".join(lines) + "\n"


def build_relevant_files_manifest(paths: list[Path]) -> str:
    lines = ["# Relevant Files Manifest", ""]
    lines.extend(f"- {path.as_posix()}" for path in paths)
    return "\n".join(lines) + "\n"


def build_review_packet(generated_paths: list[Path]) -> tuple[Path, Path]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    packet_name = f"wave4b_run_lineage_reviewability_{timestamp}"
    packet_dir = REPO_ROOT / packet_name
    zip_path = REPO_ROOT / f"{packet_name}.zip"
    packet_paths = dedupe_paths(
        [
            Path("docs/protocol_lab/README.md"),
            Path("docs/protocol_lab/prompts/README.md"),
            Path("docs/protocol_lab/prompts/p0_plain_prompt_v1.md"),
            Path("docs/protocol_lab/prompts/p1_structured_contract_v1.md"),
            Path("docs/protocol_lab/prompts/p2_tagged_input_contract_v1.md"),
            Path("docs/protocol_lab/prompts/p3_extract_then_synthesize_v1__step_1_extract_evidence.md"),
            Path("docs/protocol_lab/prompts/p3_extract_then_synthesize_v1__step_2_synthesize_change_brief.md"),
            Path("reports/protocol_lab/run_state_model.md"),
            Path("reports/protocol_lab/raw_response_storage_conventions.md"),
            Path("reports/protocol_lab/evidence_resolution_rules.md"),
            Path("reports/protocol_lab/wave4b_run_lineage_reviewability_report.md"),
            Path("schemas/protocol_lab/input_pack_v1.schema.json"),
            Path("schemas/protocol_lab/run_request_v1.schema.json"),
            Path("schemas/protocol_lab/change_brief_output_v1.schema.json"),
            Path("schemas/protocol_lab/evidence_bundle_v1.schema.json"),
            Path("schemas/protocol_lab/change_brief_eval_v1.schema.json"),
            Path("schemas/protocol_lab/prompt_render_v1.schema.json"),
            Path("schemas/protocol_lab/execution_trace_v1.schema.json"),
            Path("schemas/protocol_lab/evidence_resolution_v1.schema.json"),
            Path("scripts/protocol_lab_wave4b_reviewability.py"),
            Path("scripts/tests/test_protocol_lab_wave4b_reviewability.py"),
            Path("public/data/business_document_protocol_lab/registries/input_packs_v1.json"),
            Path("public/data/business_document_protocol_lab/registries/runner_bindings_local_v1.json"),
            Path("public/data/business_document_protocol_lab/source_cases/NVDA_2024_2025_10k_item1a/source_case_manifest_v1.json"),
            Path("public/data/business_document_protocol_lab/input_packs/NVDA_2024_2025_10k_item1a/i0_filed_full_text_v1.json"),
            Path("public/data/business_document_protocol_lab/input_packs/NVDA_2024_2025_10k_item1a/i0_filed_full_text_v1.rendered_inputs.json"),
            Path("public/data/business_document_protocol_lab/input_packs/NVDA_2024_2025_10k_item1a/i1_reuse_filtered_v1.json"),
            Path("public/data/business_document_protocol_lab/input_packs/NVDA_2024_2025_10k_item1a/i2_tagged_document_packet_v1.json"),
            Path("public/data/business_document_protocol_lab/input_packs/NVDA_2024_2025_10k_item1a/i2_tagged_document_packet_v1.rendered_inputs.json"),
            Path(f"public/data/business_document_protocol_lab/runs/{FIXTURE_ID}/{SAMPLE_RUN_IDS[0]}/run_request_v1.json"),
            Path(f"public/data/business_document_protocol_lab/runs/{FIXTURE_ID}/{SAMPLE_RUN_IDS[0]}/change_brief_output_v1.json"),
            Path(f"public/data/business_document_protocol_lab/runs/{FIXTURE_ID}/{SAMPLE_RUN_IDS[0]}/evidence_bundle_v1.json"),
            Path(f"public/data/business_document_protocol_lab/evals/{FIXTURE_ID}/{SAMPLE_RUN_IDS[0]}/change_brief_eval_v1.json"),
            Path(f"public/data/business_document_protocol_lab/runs/{FIXTURE_ID}/{SAMPLE_RUN_IDS[1]}/run_request_v1.json"),
            Path(f"public/data/business_document_protocol_lab/runs/{FIXTURE_ID}/{SAMPLE_RUN_IDS[1]}/change_brief_output_v1.json"),
            Path(f"public/data/business_document_protocol_lab/runs/{FIXTURE_ID}/{SAMPLE_RUN_IDS[1]}/evidence_bundle_v1.json"),
            Path(f"public/data/business_document_protocol_lab/evals/{FIXTURE_ID}/{SAMPLE_RUN_IDS[1]}/change_brief_eval_v1.json"),
            Path(f"public/data/business_document_protocol_lab/runs/{FIXTURE_ID}/{SAMPLE_RUN_IDS[2]}/run_request_v1.json"),
            Path(f"public/data/business_document_protocol_lab/runs/{FIXTURE_ID}/{SAMPLE_RUN_IDS[2]}/change_brief_output_v1.json"),
            Path(f"public/data/business_document_protocol_lab/runs/{FIXTURE_ID}/{SAMPLE_RUN_IDS[2]}/evidence_bundle_v1.json"),
            Path(f"public/data/business_document_protocol_lab/evals/{FIXTURE_ID}/{SAMPLE_RUN_IDS[2]}/change_brief_eval_v1.json"),
        ]
        + generated_paths
    )
    if packet_dir.exists():
        shutil.rmtree(packet_dir)
    if zip_path.exists():
        zip_path.unlink()
    for relative_path in packet_paths:
        source_path = REPO_ROOT / relative_path
        destination_path = packet_dir / relative_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)
    write_text(packet_dir / "README.md", build_packet_readme(packet_name, generated_paths))
    write_text(packet_dir / "relevant_files_manifest.md", build_relevant_files_manifest(packet_paths))
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for file_path in packet_dir.rglob("*"):
            if file_path.is_file():
                handle.write(file_path, file_path.relative_to(REPO_ROOT).as_posix())
    return packet_dir, zip_path

def generate_wave4b_artifacts() -> tuple[list[Path], Path, Path]:
    runner_bindings = ensure_registry_map(
        REGISTRIES_ROOT / "runner_bindings_local_v1.json",
        "runner_binding_id",
    )
    generated_paths: list[Path] = []
    for run_request_id in SAMPLE_RUN_IDS:
        run_request_path = RUNS_ROOT / FIXTURE_ID / run_request_id / "run_request_v1.json"
        run_request = read_json(run_request_path)
        source_case_manifest = read_json(
            SOURCE_CASES_ROOT / FIXTURE_ID / "source_case_manifest_v1.json"
        )
        runner_binding = runner_bindings[as_str(run_request.get("runner_binding_id"), "runner_binding_id")]
        input_pack_payload = load_input_pack_payload(
            FIXTURE_ID,
            as_str(run_request.get("input_pack_id"), "input_pack_id"),
        )

        protocol_id = as_str(run_request.get("protocol_id"), "protocol_id")
        step_labels = P3_STEP_LABELS if protocol_id == "p3_extract_then_synthesize_v1" else [None]
        for step_label in step_labels:
            prompt_render_payload = build_prompt_render_payload(
                run_request,
                source_case_manifest,
                runner_binding,
                input_pack_payload,
                step_label,
            )
            prompt_render_path = path_for_prompt_render(run_request, step_label)
            write_json(prompt_render_path, prompt_render_payload)
            generated_paths.append(Path(repo_rel(prompt_render_path)))

            execution_trace_payload = build_execution_trace_payload(
                run_request,
                prompt_render_payload,
                step_label,
            )
            execution_trace_path = path_for_execution_trace(run_request, step_label)
            write_json(execution_trace_path, execution_trace_payload)
            generated_paths.append(Path(repo_rel(execution_trace_path)))

        run_dir = path_for_run(run_request)
        change_brief_output_payload = read_json(run_dir / "change_brief_output_v1.json")
        evidence_bundle_payload = read_json(run_dir / "evidence_bundle_v1.json")
        evidence_resolution_payload = build_evidence_resolution_payload(
            run_request,
            change_brief_output_payload,
            evidence_bundle_payload,
            input_pack_payload,
        )
        evidence_resolution_path = path_for_evidence_resolution(run_request)
        write_json(evidence_resolution_path, evidence_resolution_payload)
        generated_paths.append(Path(repo_rel(evidence_resolution_path)))

    packet_dir, zip_path = build_review_packet(generated_paths)
    return generated_paths, packet_dir, zip_path


def main() -> int:
    _, packet_dir, zip_path = generate_wave4b_artifacts()
    created_schemas = [
        "schemas/protocol_lab/prompt_render_v1.schema.json",
        "schemas/protocol_lab/execution_trace_v1.schema.json",
        "schemas/protocol_lab/evidence_resolution_v1.schema.json",
    ]
    print(f"packet folder path: {packet_dir}")
    print(f"zip path: {zip_path}")
    print(f"schemas created: {', '.join(created_schemas)}")
    print(
        "sample lineage artifacts are real or scaffolded: "
        "scaffolded (rendered or scaffold-only lineage; no real model responses)"
    )
    print("deterministic evidence resolution: implemented")
    print(f"biggest unresolved question after Wave 4B: {BIGGEST_UNRESOLVED_QUESTION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
