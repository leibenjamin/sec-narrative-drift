from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from lab_script_version import build_script_version
from lab_output_tracks import DEFAULT_PRIMARY_LLM_CAMPAIGN_ID, get_llm_campaign
from lab_llm_precompute_utils import as_list, as_str_dict, get_int, get_str, read_json
from lab_validate_llm_outputs import build_paragraph_maps, resolve_input_file

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "reports" / "lab_llm_master_manifest.json"
DEFAULT_REPORT_PATH = REPO_ROOT / "reports" / "lab_llm_master_validation.md"
RUN_LABEL_RE = re.compile(r"^20\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])_[A-Za-z0-9._-]+$")
ALLOWED_CHANGE_CLASSES = {
    "added",
    "removed",
    "moved",
    "split",
    "merged",
    "reworded",
    "intensified",
    "softened",
    "stable",
}
TOP_LEVEL_KEYS_V1 = {
    "lab_schema_version",
    "artifact_schema_version",
    "artifact_id",
    "ticker",
    "section",
    "source_id",
    "cleaning_lens",
    "year_from",
    "year_to",
    "outline_prev",
    "outline_curr",
    "node_alignment",
    "material_changes",
    "evidence_bank",
    "lens_divergence",
    "provenance",
}
TOP_LEVEL_KEYS_V2 = TOP_LEVEL_KEYS_V1.union(
    {
        "risk_graph_prev",
        "risk_graph_curr",
        "change_mechanisms",
        "uncertainty_and_limits",
        "investor_relevance",
        "projection_contract",
    }
)


@dataclass(frozen=True)
class MasterTarget:
    ticker: str
    year_from: int
    year_to: int
    section: str
    lens: str
    source_id: str
    expected_output_path: str
    manifest_present_flag: Optional[bool]
    expected_artifact_id: str
    source_master_v2_path: Optional[str]


@dataclass(frozen=True)
class ValidationIssue:
    issue_type: str
    expected_output_path: str
    ticker: str
    year_from: int
    year_to: int
    reasons: list[str]


def write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def infer_artifact_id_from_path(path_value: str) -> str:
    normalized = path_value.replace("\\", "/")
    if "/llm_outline_compare_v2/" in normalized or "llm_outline_compare_v2_" in normalized:
        return "llm_outline_compare_v2"
    return "llm_outline_compare_v1"


def load_targets(path: Path, target_field: str = "master_output") -> list[MasterTarget]:
    payload = read_json(path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        raise SystemExit(f"Manifest root is not an object: {path}")
    entries = as_list(payload_dict.get("entries"))
    if entries is None:
        raise SystemExit(f"Manifest missing list field 'entries': {path}")
    targets: list[MasterTarget] = []
    for entry_any in entries:
        entry = as_str_dict(entry_any)
        if entry is None:
            continue
        target_block = as_str_dict(entry.get(target_field))
        source_master_v2 = as_str_dict(entry.get("master_output"))
        if target_block is None:
            continue
        ticker = get_str(entry.get("ticker"))
        year_from = get_int(entry.get("year_from"))
        year_to = get_int(entry.get("year_to"))
        section = get_str(entry.get("section"))
        lens = get_str(entry.get("lens"))
        source_id = get_str(entry.get("source_id"))
        expected = get_str(target_block.get("expected_output_path"))
        present_flag = target_block.get("present")
        expected_artifact_id = get_str(target_block.get("artifact_id"))
        if expected_artifact_id is None and expected is not None:
            expected_artifact_id = infer_artifact_id_from_path(expected)
        source_master_v2_path = (
            get_str(source_master_v2.get("expected_output_path"))
            if source_master_v2 is not None
            else None
        )
        present: Optional[bool] = None
        if isinstance(present_flag, bool):
            present = present_flag
        if (
            ticker is None
            or year_from is None
            or year_to is None
            or section is None
            or lens is None
            or source_id is None
            or expected is None
        ):
            continue
        targets.append(
            MasterTarget(
                ticker=ticker,
                year_from=year_from,
                year_to=year_to,
                section=section,
                lens=lens,
                source_id=source_id,
                expected_output_path=expected,
                manifest_present_flag=present,
                expected_artifact_id=expected_artifact_id or "llm_outline_compare_v1",
                source_master_v2_path=source_master_v2_path,
            )
        )
    return targets


def parse_nodes(raw: object, label: str, reasons: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    nodes = as_list(raw)
    if nodes is None:
        reasons.append(f"{label} must be a list")
        return out
    for idx, node_any in enumerate(nodes):
        node = as_str_dict(node_any)
        if node is None:
            reasons.append(f"{label}[{idx}] must be an object")
            continue
        node_id = get_str(node.get("node_id"))
        parent_id = node.get("parent_id")
        level = get_int(node.get("level"))
        order = get_int(node.get("order"))
        node_label = get_str(node.get("label"))
        risk_thesis = get_str(node.get("risk_thesis"))
        evidence_idx = as_list(node.get("evidence_paragraph_idx"))
        if node_id is None:
            reasons.append(f"{label}[{idx}].node_id must be a string")
        if parent_id is not None and not isinstance(parent_id, str):
            reasons.append(f"{label}[{idx}].parent_id must be string or null")
        if level not in (1, 2, 3):
            reasons.append(f"{label}[{idx}].level must be one of 1,2,3")
        if order is None or order < 0:
            reasons.append(f"{label}[{idx}].order must be non-negative int")
        if node_label is None:
            reasons.append(f"{label}[{idx}].label must be a string")
        if risk_thesis is None:
            reasons.append(f"{label}[{idx}].risk_thesis must be a string")
        parsed_evidence: list[int] = []
        if evidence_idx is None:
            reasons.append(f"{label}[{idx}].evidence_paragraph_idx must be a list")
        else:
            for j, value in enumerate(evidence_idx):
                parsed = get_int(value)
                if parsed is None or parsed < 0:
                    reasons.append(
                        f"{label}[{idx}].evidence_paragraph_idx[{j}] must be non-negative int"
                    )
                else:
                    parsed_evidence.append(parsed)
        out.append(
            {
                "node_id": node_id,
                "parent_id": parent_id if isinstance(parent_id, str) else None,
                "evidence_paragraph_idx": parsed_evidence,
            }
        )
    return out


def validate_payload(
    target: MasterTarget,
    path: Path,
    expected_model_provider: str,
    expected_model_name: str,
    expected_artifact_id: str,
    source_master_v2_path: Optional[str] = None,
) -> list[str]:
    reasons: list[str] = []
    try:
        payload_raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return [f"invalid JSON: {exc}"]
    payload = as_str_dict(payload_raw)
    if payload is None:
        return ["JSON root must be an object"]

    keys = set(payload.keys())
    required_top_keys = TOP_LEVEL_KEYS_V2 if expected_artifact_id == "llm_outline_compare_v2" else TOP_LEVEL_KEYS_V1
    missing_keys = sorted(required_top_keys.difference(keys))
    extra_keys = sorted(keys.difference(required_top_keys))
    if missing_keys:
        reasons.append("missing top-level keys: " + ", ".join(missing_keys))
    if extra_keys:
        reasons.append("unexpected top-level keys: " + ", ".join(extra_keys))

    if payload.get("lab_schema_version") != "1.0":
        reasons.append("lab_schema_version must be '1.0'")
    if payload.get("artifact_schema_version") != "1.0":
        reasons.append("artifact_schema_version must be '1.0'")
    if payload.get("artifact_id") != expected_artifact_id:
        reasons.append(f"artifact_id must be '{expected_artifact_id}'")
    if get_str(payload.get("ticker")) != target.ticker:
        reasons.append(f"ticker mismatch: expected {target.ticker}")
    if get_str(payload.get("section")) != target.section:
        reasons.append(f"section mismatch: expected {target.section}")
    if get_str(payload.get("source_id")) != target.source_id:
        reasons.append(f"source_id mismatch: expected {target.source_id}")
    if get_str(payload.get("cleaning_lens")) != target.lens:
        reasons.append(f"cleaning_lens mismatch: expected {target.lens}")
    if get_int(payload.get("year_from")) != target.year_from:
        reasons.append(f"year_from mismatch: expected {target.year_from}")
    if get_int(payload.get("year_to")) != target.year_to:
        reasons.append(f"year_to mismatch: expected {target.year_to}")

    outline_prev = parse_nodes(payload.get("outline_prev"), "outline_prev", reasons)
    outline_curr = parse_nodes(payload.get("outline_curr"), "outline_curr", reasons)
    prev_node_ids = [node.get("node_id") for node in outline_prev if node.get("node_id")]
    curr_node_ids = [node.get("node_id") for node in outline_curr if node.get("node_id")]
    if len(prev_node_ids) != len(set(prev_node_ids)):
        reasons.append("outline_prev has duplicate node_id values")
    if len(curr_node_ids) != len(set(curr_node_ids)):
        reasons.append("outline_curr has duplicate node_id values")

    for label, nodes, ids in (
        ("outline_prev", outline_prev, set(prev_node_ids)),
        ("outline_curr", outline_curr, set(curr_node_ids)),
    ):
        for idx, node in enumerate(nodes):
            parent_id = node.get("parent_id")
            if parent_id and parent_id not in ids:
                reasons.append(f"{label}[{idx}].parent_id must reference an existing node_id")

    node_alignment = as_list(payload.get("node_alignment"))
    seen_alignment_pairs: set[tuple[Optional[str], Optional[str]]] = set()
    if node_alignment is None:
        reasons.append("node_alignment must be a list")
    else:
        for idx, alignment_any in enumerate(node_alignment):
            alignment = as_str_dict(alignment_any)
            if alignment is None:
                reasons.append(f"node_alignment[{idx}] must be an object")
                continue
            prev_node = alignment.get("prev_node_id")
            curr_node = alignment.get("curr_node_id")
            change_class = get_str(alignment.get("change_class"))
            rationale = get_str(alignment.get("rationale"))
            salience = alignment.get("salience")
            if prev_node is None and curr_node is None:
                reasons.append(f"node_alignment[{idx}] cannot have both node refs null")
            if prev_node is not None and not isinstance(prev_node, str):
                reasons.append(f"node_alignment[{idx}].prev_node_id must be string or null")
            if curr_node is not None and not isinstance(curr_node, str):
                reasons.append(f"node_alignment[{idx}].curr_node_id must be string or null")
            if isinstance(prev_node, str) and prev_node not in set(prev_node_ids):
                reasons.append(f"node_alignment[{idx}].prev_node_id is unknown")
            if isinstance(curr_node, str) and curr_node not in set(curr_node_ids):
                reasons.append(f"node_alignment[{idx}].curr_node_id is unknown")
            pair_key = (
                prev_node if isinstance(prev_node, str) else None,
                curr_node if isinstance(curr_node, str) else None,
            )
            if pair_key in seen_alignment_pairs:
                reasons.append(
                    f"node_alignment[{idx}] duplicates prev/curr pair already declared"
                )
            else:
                seen_alignment_pairs.add(pair_key)
            if change_class not in ALLOWED_CHANGE_CLASSES:
                reasons.append(f"node_alignment[{idx}].change_class invalid")
            if rationale is None or not rationale.strip():
                reasons.append(f"node_alignment[{idx}].rationale must be non-empty")
            if isinstance(salience, bool) or not isinstance(salience, (int, float)):
                reasons.append(f"node_alignment[{idx}].salience must be numeric")
            else:
                salience_value = float(salience)
                if salience_value < 0 or salience_value > 1:
                    reasons.append(f"node_alignment[{idx}].salience must be between 0 and 1")

    evidence_bank = as_list(payload.get("evidence_bank"))
    evidence_index: set[tuple[int, int]] = set()
    if evidence_bank is None:
        reasons.append("evidence_bank must be a list")
        evidence_bank = []
    else:
        for idx, evidence_any in enumerate(evidence_bank):
            evidence = as_str_dict(evidence_any)
            if evidence is None:
                reasons.append(f"evidence_bank[{idx}] must be an object")
                continue
            year = get_int(evidence.get("year"))
            paragraph_idx = get_int(evidence.get("paragraph_idx"))
            snippet = get_str(evidence.get("snippet"))
            why = get_str(evidence.get("why"))
            node_ids = as_list(evidence.get("node_ids"))
            if year not in (target.year_from, target.year_to):
                reasons.append(f"evidence_bank[{idx}].year must match pair years")
            if paragraph_idx is None or paragraph_idx < 0:
                reasons.append(f"evidence_bank[{idx}].paragraph_idx must be non-negative int")
            if snippet is None or not snippet.strip():
                reasons.append(f"evidence_bank[{idx}].snippet must be non-empty")
            elif len(snippet) > 350:
                reasons.append(f"evidence_bank[{idx}].snippet exceeds 350 chars")
            if why is None or not why.strip():
                reasons.append(f"evidence_bank[{idx}].why must be non-empty")
            if node_ids is None:
                reasons.append(f"evidence_bank[{idx}].node_ids must be a list")
            else:
                for j, node_id in enumerate(node_ids):
                    if not isinstance(node_id, str) or not node_id:
                        reasons.append(f"evidence_bank[{idx}].node_ids[{j}] must be non-empty string")
            if year is not None and paragraph_idx is not None and paragraph_idx >= 0:
                pair = (year, paragraph_idx)
                if pair in evidence_index:
                    reasons.append("evidence_bank contains duplicate (year, paragraph_idx)")
                evidence_index.add(pair)

    material_changes = as_list(payload.get("material_changes"))
    if material_changes is None:
        reasons.append("material_changes must be a list")
    else:
        for idx, change_any in enumerate(material_changes):
            change = as_str_dict(change_any)
            if change is None:
                reasons.append(f"material_changes[{idx}] must be an object")
                continue
            change_class = get_str(change.get("change_class"))
            if change_class not in ALLOWED_CHANGE_CLASSES or change_class == "stable":
                reasons.append(f"material_changes[{idx}].change_class invalid for material changes")
            salience = change.get("salience")
            if isinstance(salience, bool) or not isinstance(salience, (int, float)):
                reasons.append(f"material_changes[{idx}].salience must be numeric")
            else:
                salience_value = float(salience)
                if salience_value < 0 or salience_value > 1:
                    reasons.append(f"material_changes[{idx}].salience must be between 0 and 1")
            evidence_refs = as_list(change.get("evidence_refs"))
            if evidence_refs is None or not evidence_refs:
                reasons.append(f"material_changes[{idx}].evidence_refs must be non-empty list")
            else:
                referenced_years: set[int] = set()
                for j, ref_any in enumerate(evidence_refs):
                    ref = as_str_dict(ref_any)
                    if ref is None:
                        reasons.append(f"material_changes[{idx}].evidence_refs[{j}] must be object")
                        continue
                    year = get_int(ref.get("year"))
                    paragraph_idx = get_int(ref.get("paragraph_idx"))
                    if year is None or paragraph_idx is None or paragraph_idx < 0:
                        reasons.append(
                            f"material_changes[{idx}].evidence_refs[{j}] must include valid year and paragraph_idx"
                        )
                        continue
                    if (year, paragraph_idx) not in evidence_index:
                        reasons.append(
                            f"material_changes[{idx}] reference ({year},{paragraph_idx}) missing from evidence_bank"
                        )
                    referenced_years.add(year)
                if change_class not in {"added", "removed"}:
                    if target.year_from not in referenced_years or target.year_to not in referenced_years:
                        reasons.append(
                            f"material_changes[{idx}] must reference both years for class '{change_class}'"
                        )

    lens_divergence = as_str_dict(payload.get("lens_divergence"))
    if lens_divergence is None:
        reasons.append("lens_divergence must be an object")
    else:
        materially_different = lens_divergence.get("materially_different")
        summary = get_str(lens_divergence.get("summary"))
        if not isinstance(materially_different, bool):
            reasons.append("lens_divergence.materially_different must be boolean")
        if summary is None or not summary.strip():
            reasons.append("lens_divergence.summary must be non-empty string")

    if expected_artifact_id == "llm_outline_compare_v2":
        def validate_graph_nodes(label: str) -> None:
            graph_nodes = as_list(payload.get(label))
            if graph_nodes is None or not graph_nodes:
                reasons.append(f"{label} must be a non-empty list")
                return
            for idx, node_any in enumerate(graph_nodes):
                node = as_str_dict(node_any)
                if node is None:
                    reasons.append(f"{label}[{idx}] must be an object")
                    continue
                for key in ("id", "driver", "exposure", "impact"):
                    value = get_str(node.get(key))
                    if value is None or not value.strip():
                        reasons.append(f"{label}[{idx}].{key} must be non-empty string")
                evidence_idx = as_list(node.get("evidence_paragraph_idx"))
                if evidence_idx is None or not evidence_idx:
                    reasons.append(f"{label}[{idx}].evidence_paragraph_idx must be non-empty list")
                    continue
                for j, raw in enumerate(evidence_idx):
                    value = get_int(raw)
                    if value is None or value < 0:
                        reasons.append(
                            f"{label}[{idx}].evidence_paragraph_idx[{j}] must be non-negative int"
                        )

        validate_graph_nodes("risk_graph_prev")
        validate_graph_nodes("risk_graph_curr")

        change_mechanisms = as_list(payload.get("change_mechanisms"))
        if change_mechanisms is None or not change_mechanisms:
            reasons.append("change_mechanisms must be a non-empty list")
        else:
            for idx, mechanism_any in enumerate(change_mechanisms):
                mechanism = as_str_dict(mechanism_any)
                if mechanism is None:
                    reasons.append(f"change_mechanisms[{idx}] must be an object")
                    continue
                for key in ("id", "mechanism", "transmission_channel", "business_effect", "time_horizon"):
                    value = get_str(mechanism.get(key))
                    if value is None or not value.strip():
                        reasons.append(f"change_mechanisms[{idx}].{key} must be non-empty string")
                evidence_refs = as_list(mechanism.get("evidence_refs"))
                if evidence_refs is None or not evidence_refs:
                    reasons.append(f"change_mechanisms[{idx}].evidence_refs must be non-empty list")
                    continue
                for j, ref_any in enumerate(evidence_refs):
                    ref = as_str_dict(ref_any)
                    year = get_int(ref.get("year")) if ref is not None else None
                    paragraph_idx = get_int(ref.get("paragraph_idx")) if ref is not None else None
                    if year is None or paragraph_idx is None or paragraph_idx < 0:
                        reasons.append(
                            f"change_mechanisms[{idx}].evidence_refs[{j}] must include valid year and paragraph_idx"
                        )
                    elif (year, paragraph_idx) not in evidence_index:
                        reasons.append(
                            f"change_mechanisms[{idx}] reference ({year},{paragraph_idx}) missing from evidence_bank"
                        )

        for list_key, text_key in (
            ("uncertainty_and_limits", "limitation"),
            ("investor_relevance", "why_it_matters"),
        ):
            rows = as_list(payload.get(list_key))
            if rows is None or not rows:
                reasons.append(f"{list_key} must be a non-empty list")
                continue
            for idx, row_any in enumerate(rows):
                row = as_str_dict(row_any)
                if row is None:
                    reasons.append(f"{list_key}[{idx}] must be an object")
                    continue
                row_id = get_str(row.get("id"))
                if row_id is None or not row_id.strip():
                    reasons.append(f"{list_key}[{idx}].id must be non-empty string")
                text_value = get_str(row.get(text_key))
                if text_value is None or not text_value.strip():
                    reasons.append(f"{list_key}[{idx}].{text_key} must be non-empty string")
                evidence_refs = as_list(row.get("evidence_refs"))
                if evidence_refs is None or not evidence_refs:
                    reasons.append(f"{list_key}[{idx}].evidence_refs must be non-empty list")
                    continue
                for j, ref_any in enumerate(evidence_refs):
                    ref = as_str_dict(ref_any)
                    year = get_int(ref.get("year")) if ref is not None else None
                    paragraph_idx = get_int(ref.get("paragraph_idx")) if ref is not None else None
                    if year is None or paragraph_idx is None or paragraph_idx < 0:
                        reasons.append(
                            f"{list_key}[{idx}].evidence_refs[{j}] must include valid year and paragraph_idx"
                        )
                    elif (year, paragraph_idx) not in evidence_index:
                        reasons.append(
                            f"{list_key}[{idx}] reference ({year},{paragraph_idx}) missing from evidence_bank"
                        )

        projection_contract = as_str_dict(payload.get("projection_contract"))
        if projection_contract is None:
            reasons.append("projection_contract must be an object")
        else:
            if get_str(projection_contract.get("projects_to_artifact_id")) != "llm_outline_compare_v1":
                reasons.append("projection_contract.projects_to_artifact_id must be llm_outline_compare_v1")
            projection_version = get_str(projection_contract.get("projection_version"))
            if projection_version is None or not projection_version.strip():
                reasons.append("projection_contract.projection_version must be non-empty string")

    provenance = as_str_dict(payload.get("provenance"))
    input_file = ""
    if provenance is None:
        reasons.append("provenance must be an object")
    else:
        expected_keys = {"input_file", "model_provider", "model_name", "run_label"}
        keys = set(provenance.keys())
        if keys != expected_keys:
            reasons.append(
                "provenance keys must be exactly input_file, model_provider, model_name, run_label"
            )
        input_file_raw = get_str(provenance.get("input_file"))
        if input_file_raw is None or not input_file_raw.strip():
            reasons.append("provenance.input_file must be non-empty string")
        else:
            input_file = input_file_raw
            expected = (
                f"inputs/pair/{target.ticker}_{target.year_from}_{target.year_to}_{target.section}_{target.lens}_{target.source_id}.json"
            )
            if input_file != expected:
                reasons.append(
                    f"provenance.input_file mismatch: got {input_file!r}, expected {expected!r}"
                )
        if get_str(provenance.get("model_provider")) != expected_model_provider:
            reasons.append("provenance.model_provider mismatch")
        if get_str(provenance.get("model_name")) != expected_model_name:
            reasons.append("provenance.model_name mismatch")
        run_label = get_str(provenance.get("run_label"))
        if run_label is None or RUN_LABEL_RE.fullmatch(run_label) is None:
            reasons.append("provenance.run_label must match YYYY-MM-DD_<campaign_tag>")

    if input_file:
        resolution = resolve_input_file(input_file, path)
        if resolution.path is None:
            reasons.append(f"provenance.input_file not resolvable: {resolution.error}")
        else:
            try:
                input_payload_raw = read_json(resolution.path)
                input_payload = as_str_dict(input_payload_raw)
            except Exception as exc:  # noqa: BLE001
                input_payload = None
                reasons.append(f"failed to read input payload: {exc}")
            if input_payload is not None:
                paragraph_maps = build_paragraph_maps(input_payload, input_payload_path=resolution.path)
                if paragraph_maps is None:
                    reasons.append("input payload missing resolvable paragraph maps")
                else:
                    prev_map = paragraph_maps.prev_map
                    curr_map = paragraph_maps.curr_map
                    for idx, node in enumerate(outline_prev):
                        for paragraph_idx in node.get("evidence_paragraph_idx", []):
                            if paragraph_idx not in prev_map:
                                reasons.append(
                                    f"outline_prev[{idx}] evidence idx {paragraph_idx} missing from prev year input"
                                )
                    for idx, node in enumerate(outline_curr):
                        for paragraph_idx in node.get("evidence_paragraph_idx", []):
                            if paragraph_idx not in curr_map:
                                reasons.append(
                                    f"outline_curr[{idx}] evidence idx {paragraph_idx} missing from curr year input"
                                )
                    for idx, evidence_any in enumerate(evidence_bank):
                        evidence = as_str_dict(evidence_any)
                        if evidence is None:
                            continue
                        year = get_int(evidence.get("year"))
                        paragraph_idx = get_int(evidence.get("paragraph_idx"))
                        snippet = get_str(evidence.get("snippet"))
                        if (
                            year is None
                            or paragraph_idx is None
                            or paragraph_idx < 0
                            or snippet is None
                        ):
                            continue
                        paragraph_text = prev_map.get(paragraph_idx) if year == target.year_from else curr_map.get(paragraph_idx)
                        if paragraph_text is None:
                            continue
                        if snippet not in paragraph_text:
                            reasons.append(
                                f"evidence_bank[{idx}] snippet not verbatim in mapped paragraph"
                            )

    if expected_artifact_id == "llm_outline_compare_v1" and source_master_v2_path:
        source_v2_path = Path(source_master_v2_path)
        if not source_v2_path.is_absolute():
            source_v2_path = (REPO_ROOT / source_v2_path).resolve()
        if not source_v2_path.exists():
            reasons.append(
                f"projection source v2 missing for v1 artifact: {source_v2_path.as_posix()}"
            )
        else:
            try:
                source_v2_payload_raw = json.loads(source_v2_path.read_text(encoding="utf-8-sig"))
                source_v2_payload = as_str_dict(source_v2_payload_raw)
            except Exception as exc:  # noqa: BLE001
                source_v2_payload = None
                reasons.append(f"projection source v2 unreadable: {exc}")
            if source_v2_payload is not None:
                if source_v2_payload.get("artifact_id") != "llm_outline_compare_v2":
                    reasons.append("projection source artifact_id must be llm_outline_compare_v2")
                projection_fields = (
                    "outline_prev",
                    "outline_curr",
                    "node_alignment",
                    "material_changes",
                    "evidence_bank",
                    "lens_divergence",
                )
                for field in projection_fields:
                    if payload.get(field) != source_v2_payload.get(field):
                        reasons.append(f"projection_equivalence_mismatch in field '{field}'")

    return reasons


def validate_targets(
    targets: list[MasterTarget],
    expected_model_provider: str,
    expected_model_name: str,
    *,
    verbose_progress: bool = False,
    progress_interval_sec: int = 300,
) -> tuple[list[ValidationIssue], list[ValidationIssue], list[ValidationIssue]]:
    missing: list[ValidationIssue] = []
    invalid: list[ValidationIssue] = []
    mismatch: list[ValidationIssue] = []
    started = time.monotonic()
    last_heartbeat = started
    total = len(targets)
    for index, target in enumerate(targets, start=1):
        now = time.monotonic()
        if verbose_progress or now - last_heartbeat >= progress_interval_sec:
            elapsed = int(now - started)
            print(
                "[progress] master_validate "
                + f"targets={index}/{total} missing={len(missing)} invalid={len(invalid)} "
                + f"mismatch={len(mismatch)} elapsed={elapsed}s",
                flush=True,
            )
            last_heartbeat = now
        output_path = (REPO_ROOT / target.expected_output_path).resolve()
        if output_path.suffix.lower() != ".json":
            invalid.append(
                ValidationIssue(
                    issue_type="invalid_expected_path",
                    expected_output_path=target.expected_output_path,
                    ticker=target.ticker,
                    year_from=target.year_from,
                    year_to=target.year_to,
                    reasons=["expected_output_path must point to a .json file"],
                )
            )
            continue
        exists_now = output_path.exists()
        if target.manifest_present_flag is not None and target.manifest_present_flag != exists_now:
            mismatch.append(
                ValidationIssue(
                    issue_type="manifest_present_mismatch",
                    expected_output_path=target.expected_output_path,
                    ticker=target.ticker,
                    year_from=target.year_from,
                    year_to=target.year_to,
                    reasons=[
                        "manifest present flag does not match filesystem",
                        f"manifest_present={target.manifest_present_flag}, filesystem_present={exists_now}",
                    ],
                )
            )
        if not exists_now:
            missing.append(
                ValidationIssue(
                    issue_type="missing",
                    expected_output_path=target.expected_output_path,
                    ticker=target.ticker,
                    year_from=target.year_from,
                    year_to=target.year_to,
                    reasons=["file not found"],
                )
            )
            continue
        reasons = validate_payload(
            target=target,
            path=output_path,
            expected_model_provider=expected_model_provider,
            expected_model_name=expected_model_name,
            expected_artifact_id=target.expected_artifact_id,
            source_master_v2_path=target.source_master_v2_path,
        )
        if reasons:
            invalid.append(
                ValidationIssue(
                    issue_type="invalid",
                    expected_output_path=target.expected_output_path,
                    ticker=target.ticker,
                    year_from=target.year_from,
                    year_to=target.year_to,
                    reasons=reasons,
                )
            )
    return missing, invalid, mismatch


def issue_lines(items: list[ValidationIssue]) -> list[str]:
    lines: list[str] = []
    for issue in items:
        lines.append(
            f"- {issue.ticker} {issue.year_from}-{issue.year_to}: {issue.expected_output_path}"
        )
        for reason in issue.reasons:
            lines.append(f"  - {reason}")
    if not lines:
        lines.append("- none")
    return lines


def build_report(
    manifest_path: Path,
    campaign_id: str,
    expected_model_provider: str,
    expected_model_name: str,
    target_count: int,
    missing: list[ValidationIssue],
    invalid: list[ValidationIssue],
    mismatch: list[ValidationIssue],
) -> list[str]:
    lines: list[str] = []
    lines.append("# LLM Master Manifest Validation")
    lines.append("")
    lines.append(f"Manifest: {manifest_path.as_posix()}")
    lines.append(f"Campaign: {campaign_id}")
    lines.append(f"Expected model: {expected_model_provider} / {expected_model_name}")
    lines.append(f"Script: {SCRIPT_VERSION}")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| Targets | {target_count} |")
    lines.append(f"| Missing files | {len(missing)} |")
    lines.append(f"| Invalid files | {len(invalid)} |")
    lines.append(f"| Present-flag mismatches | {len(mismatch)} |")
    lines.append("")
    lines.append("## Missing Master Outputs")
    lines.extend(issue_lines(missing))
    lines.append("")
    lines.append("## Invalid Master Outputs")
    lines.extend(issue_lines(invalid))
    lines.append("")
    lines.append("## Manifest Present-Flag Mismatches")
    lines.extend(issue_lines(mismatch))
    return lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate llm_outline_compare_v1/v2 outputs.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST_PATH))
    parser.add_argument("--campaign-id", default=DEFAULT_PRIMARY_LLM_CAMPAIGN_ID)
    parser.add_argument(
        "--artifact-id",
        choices=("auto", "llm_outline_compare_v1", "llm_outline_compare_v2"),
        default="auto",
        help="Expected artifact id. `auto` uses manifest target metadata/path inference.",
    )
    parser.add_argument(
        "--target-field",
        default="master_output",
        help="Manifest entry field containing expected_output_path and optional artifact_id.",
    )
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument("--allow-invalid", action="store_true")
    parser.add_argument("--only", default="")
    parser.add_argument(
        "--only-mode",
        choices=("substring", "basename", "exact_path"),
        default="substring",
        help="Matching mode for --only tokens.",
    )
    parser.add_argument(
        "--expect-target-count",
        type=int,
        default=None,
        help="Expected number of targets after filtering.",
    )
    parser.add_argument(
        "--fail-if-target-count-mismatch",
        action="store_true",
        help="Fail when filtered target count != --expect-target-count.",
    )
    parser.add_argument(
        "--verbose-progress",
        action="store_true",
        help="Emit progress lines for each target validated.",
    )
    parser.add_argument(
        "--progress-interval-sec",
        type=int,
        default=300,
        help="Heartbeat interval in seconds for long-running operations.",
    )
    return parser


def normalize_path_like(path_value: str) -> str:
    return path_value.replace("\\", "/").strip()


def matches_only_token(path_value: str, token: str, mode: str) -> bool:
    normalized_path = normalize_path_like(path_value)
    normalized_token = normalize_path_like(token)
    if mode == "basename":
        return Path(normalized_path).name == Path(normalized_token).name
    if mode == "exact_path":
        return normalized_path.lstrip("/") == normalized_token.lstrip("/")
    return normalized_token in normalized_path


def main(argv: Optional[list[str]] = None) -> int:
    started = time.monotonic()
    args = build_parser().parse_args(argv)
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = (REPO_ROOT / manifest_path).resolve()
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")
    campaign = get_llm_campaign(args.campaign_id)
    if campaign is None or campaign.model_provider is None or campaign.model_name is None:
        raise SystemExit(f"Unknown or invalid campaign id: {args.campaign_id}")

    targets = load_targets(manifest_path, target_field=str(args.target_field))
    if str(args.artifact_id) != "auto":
        forced_artifact_id = str(args.artifact_id)
        targets = [
            MasterTarget(
                ticker=target.ticker,
                year_from=target.year_from,
                year_to=target.year_to,
                section=target.section,
                lens=target.lens,
                source_id=target.source_id,
                expected_output_path=target.expected_output_path,
                manifest_present_flag=target.manifest_present_flag,
                expected_artifact_id=forced_artifact_id,
                source_master_v2_path=target.source_master_v2_path,
            )
            for target in targets
        ]
    if args.only:
        filters = [item.strip() for item in args.only.split(",") if item.strip()]
        targets = [
            target
            for target in targets
            if any(
                matches_only_token(
                    target.expected_output_path,
                    token,
                    mode=str(args.only_mode),
                )
                for token in filters
            )
        ]
    marker = f"/{campaign.track_slug}/"
    targets = [
        target
        for target in targets
        if marker in ("/" + target.expected_output_path.replace("\\", "/").lstrip("/"))
    ]
    target_count_mismatch = False
    if args.expect_target_count is not None:
        expected_count = int(args.expect_target_count)
        target_count_mismatch = len(targets) != expected_count

    print(f"[phase] validate master outputs start (script={SCRIPT_VERSION})", flush=True)
    missing, invalid, mismatch = validate_targets(
        targets=targets,
        expected_model_provider=campaign.model_provider,
        expected_model_name=campaign.model_name,
        verbose_progress=bool(args.verbose_progress),
        progress_interval_sec=max(1, int(args.progress_interval_sec)),
    )
    report_lines = build_report(
        manifest_path=manifest_path,
        campaign_id=campaign.track_id,
        expected_model_provider=campaign.model_provider,
        expected_model_name=campaign.model_name,
        target_count=len(targets),
        missing=missing,
        invalid=invalid,
        mismatch=mismatch,
    )
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = (REPO_ROOT / report_path).resolve()
    print("[phase] write master validation report", flush=True)
    write_text(report_path, report_lines)
    elapsed = int(time.monotonic() - started)
    print(
        "Master validation summary: "
        + f"targets={len(targets)}, missing={len(missing)}, invalid={len(invalid)}, "
        + f"present_flag_mismatch={len(mismatch)}"
    )
    print(f"Wrote validation report: {report_path}")
    print(f"Elapsed: {elapsed}s")
    should_fail = False
    if target_count_mismatch and bool(args.fail_if_target_count_mismatch):
        should_fail = True
        expected_count = int(args.expect_target_count) if args.expect_target_count is not None else -1
        print(
            "Target count mismatch: "
            + f"expected={expected_count}, actual={len(targets)}"
        )
    if invalid and not args.allow_invalid:
        should_fail = True
    if missing and not args.allow_missing:
        should_fail = True
    status = "FAIL" if should_fail else "PASS"
    target_count_mismatch_count = 1 if target_count_mismatch else 0
    print(
        "JOB_VALIDATE "
        + f"targets={len(targets)} missing={len(missing)} invalid={len(invalid)} "
        + f"mismatch={target_count_mismatch_count} present_mismatch={len(mismatch)} status={status}"
    )
    return 1 if should_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
