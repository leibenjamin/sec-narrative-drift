from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from lab_script_version import build_script_version
from lab_output_tracks import (
    DEFAULT_PRIMARY_LLM_CAMPAIGN_ID,
    get_llm_campaign,
    get_report_token_for_campaign_id,
)
from lab_llm_precompute_utils import as_list, as_str_dict, get_int, get_str, read_json
from lab_validate_llm_outputs import build_paragraph_maps, resolve_input_file

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "reports" / "lab_llm_master_manifest.json"
DEFAULT_REPORT_PATH = REPO_ROOT / "reports" / "lab_llm_master_validation.md"
RUN_LABEL_RE = re.compile(r"^20\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])_[A-Za-z0-9._-]+$")
REPORT_TOKEN_SANITIZE_RE = re.compile(r"[^A-Za-z0-9._-]+")
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
TOP_LEVEL_KEYS_V3 = TOP_LEVEL_KEYS_V2.union(
    {
        "executive_digest",
        "insight_cards",
        "evidence_map",
        "insight_coverage",
        "ui_contract",
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
    source_master_structured_path: Optional[str]


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
    if "/llm_outline_compare_insight/" in normalized or "llm_outline_compare_insight_" in normalized:
        return "llm_outline_compare_insight"
    if "/llm_outline_compare_structured/" in normalized or "llm_outline_compare_structured_" in normalized:
        return "llm_outline_compare_structured"
    return "llm_outline_compare_runtime"


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
        source_master_block = as_str_dict(entry.get("master_output"))
        projected_v2_block = as_str_dict(entry.get("projected_master_output_structured"))
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
        source_master_structured_path = None
        if target_field == "projected_master_output_runtime" and projected_v2_block is not None:
            source_master_structured_path = get_str(projected_v2_block.get("expected_output_path"))
        elif source_master_block is not None:
            source_master_structured_path = get_str(source_master_block.get("expected_output_path"))
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
                expected_artifact_id=expected_artifact_id or "llm_outline_compare_runtime",
                source_master_structured_path=source_master_structured_path,
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
    source_master_structured_path: Optional[str] = None,
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
    if expected_artifact_id == "llm_outline_compare_insight":
        required_top_keys = TOP_LEVEL_KEYS_V3
    elif expected_artifact_id == "llm_outline_compare_structured":
        required_top_keys = TOP_LEVEL_KEYS_V2
    else:
        required_top_keys = TOP_LEVEL_KEYS_V1
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

    if expected_artifact_id in {"llm_outline_compare_structured", "llm_outline_compare_insight"}:
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
            if get_str(projection_contract.get("projects_to_artifact_id")) != "llm_outline_compare_runtime":
                reasons.append("projection_contract.projects_to_artifact_id must be llm_outline_compare_runtime")
            projection_version = get_str(projection_contract.get("projection_version"))
            if projection_version is None or not projection_version.strip():
                reasons.append("projection_contract.projection_version must be non-empty string")

    if expected_artifact_id == "llm_outline_compare_insight":
        executive_digest = as_str_dict(payload.get("executive_digest"))
        if executive_digest is None:
            reasons.append("executive_digest must be an object")
        else:
            summary_text = get_str(executive_digest.get("summary_text"))
            audience = get_str(executive_digest.get("audience"))
            reading_time = get_int(executive_digest.get("reading_time_sec_estimate"))
            if summary_text is None or not summary_text.strip():
                reasons.append("executive_digest.summary_text must be non-empty string")
            if audience != "investor_analyst":
                reasons.append("executive_digest.audience must be investor_analyst")
            if reading_time is None or reading_time <= 0:
                reasons.append("executive_digest.reading_time_sec_estimate must be positive int")

        evidence_map_any = as_list(payload.get("evidence_map"))
        evidence_map_ids: set[str] = set()
        evidence_map_pairs: set[tuple[int, int]] = set()
        evidence_map_insight_ids: set[str] = set()
        if evidence_map_any is None or not evidence_map_any:
            reasons.append("evidence_map must be a non-empty list")
            evidence_map_any = []
        for idx, row_any in enumerate(evidence_map_any):
            row = as_str_dict(row_any)
            if row is None:
                reasons.append(f"evidence_map[{idx}] must be an object")
                continue
            evidence_id = get_str(row.get("evidence_id"))
            year = get_int(row.get("year"))
            paragraph_idx = get_int(row.get("paragraph_idx"))
            snippet = get_str(row.get("snippet"))
            char_start = row.get("char_start")
            char_end = row.get("char_end")
            row_insight_ids = as_list(row.get("insight_ids"))
            if evidence_id is None or not evidence_id.strip():
                reasons.append(f"evidence_map[{idx}].evidence_id must be non-empty string")
            elif evidence_id in evidence_map_ids:
                reasons.append(f"evidence_map[{idx}] has duplicate evidence_id")
            else:
                evidence_map_ids.add(evidence_id)
            if year not in (target.year_from, target.year_to):
                reasons.append(f"evidence_map[{idx}].year must match pair years")
            if paragraph_idx is None or paragraph_idx < 0:
                reasons.append(f"evidence_map[{idx}].paragraph_idx must be non-negative int")
            elif year is not None:
                pair = (year, paragraph_idx)
                if pair in evidence_map_pairs:
                    reasons.append(f"evidence_map[{idx}] has duplicate (year, paragraph_idx)")
                evidence_map_pairs.add(pair)
            if snippet is None or not snippet.strip():
                reasons.append(f"evidence_map[{idx}].snippet must be non-empty")
            elif len(snippet) > 350:
                reasons.append(f"evidence_map[{idx}].snippet exceeds 350 chars")
            if char_start is not None and get_int(char_start) is None:
                reasons.append(f"evidence_map[{idx}].char_start must be int or null")
            if char_end is not None and get_int(char_end) is None:
                reasons.append(f"evidence_map[{idx}].char_end must be int or null")
            if row_insight_ids is None:
                reasons.append(f"evidence_map[{idx}].insight_ids must be a list")
            else:
                for j, insight_id in enumerate(row_insight_ids):
                    if not isinstance(insight_id, str) or not insight_id.strip():
                        reasons.append(f"evidence_map[{idx}].insight_ids[{j}] must be non-empty string")
                    else:
                        evidence_map_insight_ids.add(insight_id)

        insight_cards_any = as_list(payload.get("insight_cards"))
        insight_ids: set[str] = set()
        if insight_cards_any is None or not insight_cards_any:
            reasons.append("insight_cards must be a non-empty list")
            insight_cards_any = []
        for idx, card_any in enumerate(insight_cards_any):
            card = as_str_dict(card_any)
            if card is None:
                reasons.append(f"insight_cards[{idx}] must be an object")
                continue
            card_id = get_str(card.get("id"))
            insight_type = get_str(card.get("insight_type"))
            title = get_str(card.get("title"))
            claim = get_str(card.get("claim"))
            why_it_matters = get_str(card.get("why_it_matters"))
            confidence_band = get_str(card.get("confidence_band"))
            counterpoint = get_str(card.get("counterpoint_or_limit"))
            salience = card.get("salience")
            if card_id is None or not card_id.strip():
                reasons.append(f"insight_cards[{idx}].id must be non-empty string")
            elif card_id in insight_ids:
                reasons.append(f"insight_cards[{idx}] has duplicate id")
            else:
                insight_ids.add(card_id)
            if insight_type not in {"difference", "similarity"}:
                reasons.append(f"insight_cards[{idx}].insight_type must be difference or similarity")
            for key, value in (
                ("title", title),
                ("claim", claim),
                ("why_it_matters", why_it_matters),
                ("confidence_band", confidence_band),
                ("counterpoint_or_limit", counterpoint),
            ):
                if value is None or not value.strip():
                    reasons.append(f"insight_cards[{idx}].{key} must be non-empty string")
            if isinstance(salience, bool) or not isinstance(salience, (int, float)):
                reasons.append(f"insight_cards[{idx}].salience must be numeric")
            else:
                salience_value = float(salience)
                if salience_value < 0 or salience_value > 1:
                    reasons.append(f"insight_cards[{idx}].salience must be between 0 and 1")

            prev_refs = as_list(card.get("evidence_refs_prev"))
            curr_refs = as_list(card.get("evidence_refs_curr"))
            evidence_ref_ids = as_list(card.get("evidence_ref_ids"))
            if prev_refs is None or not prev_refs:
                reasons.append(f"insight_cards[{idx}].evidence_refs_prev must be non-empty list")
            else:
                for j, ref_any in enumerate(prev_refs):
                    ref = as_str_dict(ref_any)
                    year = get_int(ref.get("year")) if ref is not None else None
                    paragraph_idx = get_int(ref.get("paragraph_idx")) if ref is not None else None
                    if year != target.year_from or paragraph_idx is None or paragraph_idx < 0:
                        reasons.append(f"insight_cards[{idx}].evidence_refs_prev[{j}] must map to year_from and non-negative paragraph_idx")
                    elif evidence_map_pairs and (year, paragraph_idx) not in evidence_map_pairs:
                        reasons.append(f"insight_cards[{idx}] prev ref ({year},{paragraph_idx}) missing from evidence_map")
            if curr_refs is None or not curr_refs:
                reasons.append(f"insight_cards[{idx}].evidence_refs_curr must be non-empty list")
            else:
                for j, ref_any in enumerate(curr_refs):
                    ref = as_str_dict(ref_any)
                    year = get_int(ref.get("year")) if ref is not None else None
                    paragraph_idx = get_int(ref.get("paragraph_idx")) if ref is not None else None
                    if year != target.year_to or paragraph_idx is None or paragraph_idx < 0:
                        reasons.append(f"insight_cards[{idx}].evidence_refs_curr[{j}] must map to year_to and non-negative paragraph_idx")
                    elif evidence_map_pairs and (year, paragraph_idx) not in evidence_map_pairs:
                        reasons.append(f"insight_cards[{idx}] curr ref ({year},{paragraph_idx}) missing from evidence_map")
            if evidence_ref_ids is None or not evidence_ref_ids:
                reasons.append(f"insight_cards[{idx}].evidence_ref_ids must be non-empty list")
            else:
                for j, evidence_id_any in enumerate(evidence_ref_ids):
                    if not isinstance(evidence_id_any, str) or not evidence_id_any.strip():
                        reasons.append(f"insight_cards[{idx}].evidence_ref_ids[{j}] must be non-empty string")
                    elif evidence_map_ids and evidence_id_any not in evidence_map_ids:
                        reasons.append(f"insight_cards[{idx}] evidence_ref_ids[{j}] not found in evidence_map")

        for insight_id in evidence_map_insight_ids:
            if insight_id not in insight_ids:
                reasons.append(f"evidence_map insight_id {insight_id!r} not found in insight_cards")

        insight_coverage = as_str_dict(payload.get("insight_coverage"))
        if insight_coverage is None:
            reasons.append("insight_coverage must be an object")
        else:
            diff_count = get_int(insight_coverage.get("difference_count"))
            sim_count = get_int(insight_coverage.get("similarity_count"))
            if diff_count is None or diff_count < 0:
                reasons.append("insight_coverage.difference_count must be non-negative int")
            if sim_count is None or sim_count < 0:
                reasons.append("insight_coverage.similarity_count must be non-negative int")

        ui_contract = as_str_dict(payload.get("ui_contract"))
        if ui_contract is None:
            reasons.append("ui_contract must be an object")
        else:
            default_id = get_str(ui_contract.get("default_selected_insight_id"))
            order_any = as_list(ui_contract.get("recommended_insight_order"))
            clusters_any = as_list(ui_contract.get("suggested_clusters"))
            if default_id is None or not default_id.strip():
                reasons.append("ui_contract.default_selected_insight_id must be non-empty string")
            elif insight_ids and default_id not in insight_ids:
                reasons.append("ui_contract.default_selected_insight_id must reference insight_cards id")
            if order_any is None:
                reasons.append("ui_contract.recommended_insight_order must be a list")
            else:
                for idx, item in enumerate(order_any):
                    if not isinstance(item, str) or not item.strip():
                        reasons.append(f"ui_contract.recommended_insight_order[{idx}] must be non-empty string")
                    elif insight_ids and item not in insight_ids:
                        reasons.append(f"ui_contract.recommended_insight_order[{idx}] missing insight id")
            if clusters_any is None:
                reasons.append("ui_contract.suggested_clusters must be a list")
            else:
                for idx, cluster_any in enumerate(clusters_any):
                    cluster = as_str_dict(cluster_any)
                    if cluster is None:
                        reasons.append(f"ui_contract.suggested_clusters[{idx}] must be an object")
                        continue
                    cluster_id = get_str(cluster.get("cluster_id"))
                    label = get_str(cluster.get("label"))
                    cluster_insights = as_list(cluster.get("insight_ids"))
                    if cluster_id is None or not cluster_id.strip():
                        reasons.append(f"ui_contract.suggested_clusters[{idx}].cluster_id must be non-empty string")
                    if label is None or not label.strip():
                        reasons.append(f"ui_contract.suggested_clusters[{idx}].label must be non-empty string")
                    if cluster_insights is None:
                        reasons.append(f"ui_contract.suggested_clusters[{idx}].insight_ids must be a list")
                    else:
                        for j, insight_id_any in enumerate(cluster_insights):
                            if not isinstance(insight_id_any, str) or not insight_id_any.strip():
                                reasons.append(f"ui_contract.suggested_clusters[{idx}].insight_ids[{j}] must be non-empty string")
                            elif insight_ids and insight_id_any not in insight_ids:
                                reasons.append(f"ui_contract.suggested_clusters[{idx}].insight_ids[{j}] missing insight id")

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

                    if expected_artifact_id == "llm_outline_compare_insight":
                        evidence_map_any = as_list(payload.get("evidence_map")) or []
                        for idx, row_any in enumerate(evidence_map_any):
                            row = as_str_dict(row_any)
                            if row is None:
                                continue
                            year = get_int(row.get("year"))
                            paragraph_idx = get_int(row.get("paragraph_idx"))
                            snippet = get_str(row.get("snippet"))
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
                                    f"evidence_map[{idx}] snippet not verbatim in mapped paragraph"
                                )

    if expected_artifact_id == "llm_outline_compare_runtime" and source_master_structured_path:
        source_structured_path = Path(source_master_structured_path)
        if not source_structured_path.is_absolute():
            source_structured_path = (REPO_ROOT / source_structured_path).resolve()
        if not source_structured_path.exists():
            reasons.append(
                f"projection source structured missing for runtime artifact: {source_structured_path.as_posix()}"
            )
        else:
            try:
                source_structured_payload_raw = json.loads(source_structured_path.read_text(encoding="utf-8-sig"))
                source_structured_payload = as_str_dict(source_structured_payload_raw)
            except Exception as exc:  # noqa: BLE001
                source_structured_payload = None
                reasons.append(f"projection source structured unreadable: {exc}")
            if source_structured_payload is not None:
                source_artifact_id = get_str(source_structured_payload.get("artifact_id"))
                if source_artifact_id not in {"llm_outline_compare_structured", "llm_outline_compare_insight"}:
                    reasons.append("projection source artifact_id must be llm_outline_compare_structured or llm_outline_compare_insight")
                projection_fields = (
                    "outline_prev",
                    "outline_curr",
                    "node_alignment",
                    "material_changes",
                    "evidence_bank",
                    "lens_divergence",
                )
                for field in projection_fields:
                    if payload.get(field) != source_structured_payload.get(field):
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
            source_master_structured_path=target.source_master_structured_path,
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
    parser = argparse.ArgumentParser(description="Validate llm_outline_compare_runtime/structured/insight outputs.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST_PATH))
    parser.add_argument("--campaign-id", default=DEFAULT_PRIMARY_LLM_CAMPAIGN_ID)
    parser.add_argument(
        "--artifact-id",
        choices=("auto", "llm_outline_compare_runtime", "llm_outline_compare_structured", "llm_outline_compare_insight"),
        default="auto",
        help="Expected artifact id. `auto` uses manifest target metadata/path inference.",
    )
    parser.add_argument(
        "--target-field",
        default="master_output",
        help="Manifest entry field containing expected_output_path and optional artifact_id.",
    )
    parser.add_argument(
        "--report",
        default="",
        help=(
            "Validation report path. If omitted, writes a campaign/artifact-scoped "
            "report under reports/."
        ),
    )
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


def _campaign_slug_token(campaign_id: str) -> str:
    return get_report_token_for_campaign_id(campaign_id)


def _artifact_suffix(target_field: str, forced_artifact_id: str, targets: list[MasterTarget]) -> str:
    if forced_artifact_id != "auto":
        artifact_id = forced_artifact_id
    elif target_field == "projected_master_output_runtime":
        artifact_id = "llm_outline_compare_runtime"
    elif target_field == "projected_master_output_structured":
        artifact_id = "llm_outline_compare_structured"
    elif targets:
        artifact_id = targets[0].expected_artifact_id
    else:
        artifact_id = "llm_outline_compare_runtime"

    if artifact_id == "llm_outline_compare_insight":
        return "insight"
    if artifact_id == "llm_outline_compare_structured":
        return "structured"
    return "runtime"


def default_report_path_for_args(
    *,
    campaign_id: str,
    target_field: str,
    artifact_id: str,
    targets: list[MasterTarget],
) -> Path:
    campaign_token = _campaign_slug_token(campaign_id)
    artifact_token = _artifact_suffix(target_field, artifact_id, targets)
    if artifact_token == "structured":
        filename = f"lab_llm_master_validation_{campaign_token}.md"
    else:
        filename = f"lab_llm_master_validation_{campaign_token}_{artifact_token}.md"
    return REPO_ROOT / "reports" / filename


def _sanitize_report_token(value: str, *, fallback: str = "filtered") -> str:
    token = REPORT_TOKEN_SANITIZE_RE.sub("_", value.replace("\\", "/").strip())
    token = token.strip("._-")
    if not token:
        return fallback
    if len(token) > 72:
        token = token[-72:]
    return token


def default_scratch_report_path_for_args(
    *,
    campaign_id: str,
    target_field: str,
    artifact_id: str,
    targets: list[MasterTarget],
    only: str,
    only_mode: str,
) -> Path:
    campaign_token = _campaign_slug_token(campaign_id)
    artifact_token = _artifact_suffix(target_field, artifact_id, targets)
    filter_slug = _sanitize_report_token(only, fallback="filtered")
    filename = (
        f"_tmp_validation_{campaign_token}_{artifact_token}_{only_mode}_{filter_slug}.md"
    )
    return REPO_ROOT / "reports" / filename


def resolve_report_path_for_args(
    *,
    report_arg: str,
    campaign_id: str,
    target_field: str,
    artifact_id: str,
    targets: list[MasterTarget],
    only: str,
    only_mode: str,
) -> tuple[Path, bool]:
    if report_arg:
        return Path(report_arg), False
    if only.strip():
        return (
            default_scratch_report_path_for_args(
                campaign_id=campaign_id,
                target_field=target_field,
                artifact_id=artifact_id,
                targets=targets,
                only=only,
                only_mode=only_mode,
            ),
            True,
        )
    return (
        default_report_path_for_args(
            campaign_id=campaign_id,
            target_field=target_field,
            artifact_id=artifact_id,
            targets=targets,
        ),
        False,
    )


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
                source_master_structured_path=target.source_master_structured_path,
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
    report_arg = str(args.report).strip()
    report_path, is_scratch_report = resolve_report_path_for_args(
        report_arg=report_arg,
        campaign_id=campaign.track_id,
        target_field=str(args.target_field),
        artifact_id=str(args.artifact_id),
        targets=targets,
        only=str(args.only),
        only_mode=str(args.only_mode),
    )
    if not report_path.is_absolute():
        report_path = (REPO_ROOT / report_path).resolve()
    if is_scratch_report:
        print(
            f"[note] auto-selected scratch validation report for filtered run: {report_path}",
            flush=True,
        )
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


