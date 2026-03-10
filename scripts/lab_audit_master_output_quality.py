from __future__ import annotations

import argparse
import json
import re
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, cast

from lab_script_version import build_script_version
from lab_output_tracks import (
    DEFAULT_PRIMARY_LLM_CAMPAIGN_ID,
    get_llm_campaign,
    get_report_token_for_campaign_id,
)
from lab_llm_precompute_utils import as_list, as_str_dict, get_int, get_str
from lab_validate_llm_master_outputs import (
    DEFAULT_MANIFEST_PATH,
    MasterTarget,
    load_targets,
    matches_only_token,
    normalize_path_like,
    validate_payload,
)
from lab_validate_llm_outputs import build_paragraph_maps, resolve_input_file

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]

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


def default_quality_report_path_for_args(
    *,
    campaign_id: str,
    target_field: str,
    artifact_id: str,
    targets: list[MasterTarget],
) -> Path:
    campaign_token = _campaign_slug_token(campaign_id)
    artifact_token = _artifact_suffix(target_field, artifact_id, targets)
    filename = f"lab_llm_master_quality_{campaign_token}_{artifact_token}.md"
    return REPO_ROOT / "reports" / filename


def _sanitize_report_token(value: str, *, fallback: str = "filtered") -> str:
    token = re.sub(r"[^A-Za-z0-9._-]+", "_", value.replace("\\", "/").strip())
    token = token.strip("._-")
    if not token:
        return fallback
    if len(token) > 72:
        token = token[-72:]
    return token


def default_scratch_quality_report_path_for_args(
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
    filename = f"_tmp_quality_{campaign_token}_{artifact_token}_{only_mode}_{filter_slug}.md"
    return REPO_ROOT / "reports" / filename


def resolve_quality_report_path_for_args(
    *,
    report_arg: str,
    campaign_id: str,
    target_field: str,
    artifact_id: str,
    targets: list[MasterTarget],
    output: str,
    only: str,
    only_mode: str,
) -> tuple[Path, bool]:
    if report_arg:
        return Path(report_arg), False
    filter_value = only.strip()
    filter_mode_value = only_mode
    if not filter_value and output.strip():
        filter_value = output.strip()
        filter_mode_value = 'output_path'
    if filter_value:
        return (
            default_scratch_quality_report_path_for_args(
                campaign_id=campaign_id,
                target_field=target_field,
                artifact_id=artifact_id,
                targets=targets,
                only=filter_value,
                only_mode=filter_mode_value,
            ),
            True,
        )
    return (
        default_quality_report_path_for_args(
            campaign_id=campaign_id,
            target_field=target_field,
            artifact_id=artifact_id,
            targets=targets,
        ),
        False,
    )

BOUNDARY_CHARS = set(" \t\r\n,.;:!?)]}\"'/-")
SENTENCE_END_CHARS = {".", "!", "?"}
CLAUSE_END_CHARS = {",", ";", ":"}
GENERIC_PHRASES = (
    "remains a risk",
    "continues to be a risk",
    "risk remains",
    "is a concern",
    "could adversely affect",
    "may adversely impact",
    "broad risk",
    "general risk",
    "ongoing risk",
    "directional shift",
)
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9'-]{4,}")
PAGE_PREFIX_RE = re.compile(r"^\s*\d{1,3}\s")
YEAR_OR_REF_RE = re.compile(r"\b(19|20)\d{2}\b|\bpara(?:graph)?\b|\bidx\b|\bindex\b", re.IGNORECASE)


@dataclass(frozen=True)
class AuditIssue:
    code: str
    detail: str
    severity: str  # blocker|advisory


@dataclass(frozen=True)
class OutputAudit:
    path: Path
    blockers: list[AuditIssue]
    advisories: list[AuditIssue]
    quality_score: int


def parse_output_filename(path: Path) -> Optional[dict[str, object]]:
    match = re.search(
        r"lab_(?P<artifact_id>llm_outline_compare_(?:runtime|structured|insight))_(?P<section>.+?)_(?P<year_from>\d{4})_(?P<year_to>\d{4})_(?P<lens>.+)_(?P<source_id>[a-zA-Z0-9]+)__",
        path.name,
    )
    if match is None:
        return None
    year_from = int(match.group("year_from"))
    year_to = int(match.group("year_to"))
    section = match.group("section")
    artifact_id = match.group("artifact_id")
    lens = match.group("lens")
    source_id = match.group("source_id")
    normalized = path.as_posix().replace("\\", "/")
    ticker_match = re.search(r"/sec_narrative_drift_lab/(?P<ticker>[A-Z]+)/outputs/", normalized)
    if ticker_match is None:
        return None
    ticker = ticker_match.group("ticker")
    return {
        "ticker": ticker,
        "year_from": year_from,
        "year_to": year_to,
        "section": section,
        "artifact_id": artifact_id,
        "lens": lens,
        "source_id": source_id,
    }


def infer_target_from_output(path: Path) -> Optional[MasterTarget]:
    parsed = parse_output_filename(path)
    if parsed is None:
        return None
    if not isinstance(parsed.get("ticker"), str):
        return None
    ticker = str(parsed["ticker"])
    year_from = int(str(parsed["year_from"]))
    year_to = int(str(parsed["year_to"]))
    section = str(parsed["section"])
    lens = str(parsed["lens"])
    source_id = str(parsed["source_id"])
    artifact_id = str(parsed["artifact_id"])
    relative = path
    try:
        relative = path.resolve().relative_to(REPO_ROOT.resolve())
    except ValueError:
        relative = path
    return MasterTarget(
        ticker=ticker,
        year_from=year_from,
        year_to=year_to,
        section=section,
        lens=lens,
        source_id=source_id,
        expected_output_path=relative.as_posix(),
        manifest_present_flag=None,
        expected_artifact_id=artifact_id,
        source_master_structured_path=None,
    )


def load_payload(path: Path) -> Optional[dict[str, object]]:
    try:
        payload_raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    payload = as_str_dict(payload_raw)
    if payload is None:
        return None
    output: dict[str, object] = {}
    for key, value in payload.items():
        output[key] = value
    return output


def tokenize(text: str) -> set[str]:
    tokens: set[str] = set()
    for match in TOKEN_RE.finditer(text.lower()):
        tokens.add(match.group(0))
    return tokens


def normalize_match_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def contains_anchor(text_norm: str, anchor: str) -> bool:
    anchor_norm = normalize_match_text(anchor)
    if not anchor_norm:
        return False
    padded = f" {text_norm} "
    return f" {anchor_norm} " in padded


def signal_matches_text(text: str, anchor_groups_any: object) -> bool:
    text_norm = normalize_match_text(text)
    if not text_norm:
        return False
    anchor_groups = as_list(anchor_groups_any) or []
    if not anchor_groups:
        return False
    for group_any in anchor_groups:
        group = as_list(group_any) or []
        anchors = [str(item) for item in group if isinstance(item, str) and item.strip()]
        if not anchors:
            return False
        if not any(contains_anchor(text_norm, anchor) for anchor in anchors):
            return False
    return True


def collect_signal_match_indexes(
    rows: list[dict[str, object]],
    keys: tuple[str, ...],
    signal: dict[str, object],
) -> list[int]:
    matches: list[int] = []
    for idx, row in enumerate(rows):
        pieces: list[str] = []
        for key in keys:
            value = get_str(row.get(key))
            if value:
                pieces.append(value)
        if pieces and signal_matches_text(" ".join(pieces), signal.get("anchor_groups")):
            matches.append(idx)
    return matches


def classify_boundary(paragraph_text: str, snippet: str, start_idx: int) -> str:
    end_idx = start_idx + len(snippet)
    start_boundary = start_idx == 0 or paragraph_text[start_idx - 1] in BOUNDARY_CHARS
    end_boundary = end_idx >= len(paragraph_text) or paragraph_text[end_idx] in BOUNDARY_CHARS
    if not start_boundary or not end_boundary:
        return "hard_cut"
    stripped = snippet.rstrip()
    if stripped and stripped[-1] in SENTENCE_END_CHARS:
        return "sentence"
    if stripped and stripped[-1] in CLAUSE_END_CHARS:
        return "clause"
    return "clause"


def resolve_input_payload(
    path: Path,
    payload: dict[str, object],
) -> tuple[Optional[Path], Optional[dict[str, object]], list[AuditIssue]]:
    issues: list[AuditIssue] = []
    provenance = as_str_dict(payload.get("provenance")) or {}
    input_file_value = get_str(provenance.get("input_file"))
    if input_file_value is None or not input_file_value.strip():
        issues.append(
            AuditIssue(
                code="missing_provenance_input_file",
                detail="provenance.input_file is missing.",
                severity="blocker",
            )
        )
        return None, None, issues
    resolution = resolve_input_file(input_file_value, path)
    if resolution.path is None:
        issues.append(
            AuditIssue(
                code="unresolvable_input_file",
                detail=f"Unable to resolve provenance.input_file: {resolution.error}",
                severity="blocker",
            )
        )
        return None, None, issues
    try:
        input_payload_raw = json.loads(resolution.path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        issues.append(
            AuditIssue(
                code="invalid_input_json",
                detail=f"Input payload JSON is invalid: {exc}",
                severity="blocker",
            )
        )
        return None, None, issues
    input_payload_dict = as_str_dict(input_payload_raw)
    if input_payload_dict is None:
        issues.append(
            AuditIssue(
                code="invalid_input_payload_shape",
                detail="Resolved input payload root is not an object.",
                severity="blocker",
            )
        )
        return None, None, issues
    input_payload: dict[str, object] = {}
    for key, value in input_payload_dict.items():
        input_payload[key] = value
    return resolution.path, input_payload, issues


def collect_paragraph_maps(
    input_payload_path: Optional[Path],
    input_payload: Optional[dict[str, object]],
) -> tuple[Optional[dict[int, str]], Optional[dict[int, str]], list[AuditIssue]]:
    issues: list[AuditIssue] = []
    if input_payload_path is None or input_payload is None:
        return None, None, issues
    maps = build_paragraph_maps(input_payload, input_payload_path=input_payload_path)
    if maps is None:
        issues.append(
            AuditIssue(
                code="missing_paragraph_maps",
                detail="Unable to build paragraph maps from provenance.input_file.",
                severity="blocker",
            )
        )
        return None, None, issues
    prev_map: dict[int, str] = {}
    curr_map: dict[int, str] = {}
    for idx, text in maps.prev_map.items():
        prev_map[idx] = text
    for idx, text in maps.curr_map.items():
        curr_map[idx] = text
    return prev_map, curr_map, issues


def evaluate_output(
    path: Path,
    target: MasterTarget,
    expected_model_provider: str,
    expected_model_name: str,
    *,
    strict_depth: bool = False,
) -> OutputAudit:
    blockers: list[AuditIssue] = []
    advisories: list[AuditIssue] = []

    reasons = validate_payload(
        target=target,
        path=path,
        expected_model_provider=expected_model_provider,
        expected_model_name=expected_model_name,
        expected_artifact_id=target.expected_artifact_id,
        source_master_structured_path=target.source_master_structured_path,
    )
    for reason in reasons:
        blockers.append(
            AuditIssue(
                code="validator_failure",
                detail=reason,
                severity="blocker",
            )
        )

    payload = load_payload(path)
    if payload is None:
        blockers.append(
            AuditIssue(
                code="invalid_json",
                detail="Output JSON cannot be parsed into an object.",
                severity="blocker",
            )
        )
        return OutputAudit(path=path, blockers=blockers, advisories=advisories, quality_score=0)

    input_payload_path, input_payload, input_issues = resolve_input_payload(path, payload)
    blockers.extend(input_issues)

    prev_map, curr_map, map_issues = collect_paragraph_maps(input_payload_path, input_payload)
    blockers.extend(map_issues)

    evidence_list_any = as_list(payload.get("evidence_bank")) or []
    evidence_entries: list[dict[str, object]] = []
    evidence_lookup: dict[tuple[int, int], dict[str, object]] = {}
    for item in evidence_list_any:
        evidence_dict = as_str_dict(item)
        if evidence_dict is None:
            continue
        normalized: dict[str, object] = {}
        for key, value in evidence_dict.items():
            normalized[key] = value
        evidence_entries.append(normalized)
        year = get_int(evidence_dict.get("year"))
        paragraph_idx = get_int(evidence_dict.get("paragraph_idx"))
        if year is not None and paragraph_idx is not None and paragraph_idx >= 0:
            evidence_lookup[(year, paragraph_idx)] = normalized

    hard_cut_count = 0
    boundary_total = 0
    page_prefix_count = 0
    for index, evidence in enumerate(evidence_entries):
        year = get_int(evidence.get("year"))
        paragraph_idx = get_int(evidence.get("paragraph_idx"))
        snippet = get_str(evidence.get("snippet"))
        if year is None or paragraph_idx is None or snippet is None:
            continue
        paragraph_text: Optional[str] = None
        if prev_map is not None and curr_map is not None:
            if year == target.year_from:
                paragraph_text = prev_map.get(paragraph_idx)
            elif year == target.year_to:
                paragraph_text = curr_map.get(paragraph_idx)
        if paragraph_text is None:
            continue
        start_idx = paragraph_text.find(snippet)
        if start_idx < 0:
            continue
        boundary_total += 1
        classification = classify_boundary(paragraph_text, snippet, start_idx)
        if classification == "hard_cut":
            hard_cut_count += 1
        if PAGE_PREFIX_RE.match(snippet):
            page_prefix_count += 1
            advisories.append(
                AuditIssue(
                    code="snippet_starts_with_page_prefix",
                    detail=f"evidence_bank[{index}] snippet begins with page-number style prefix.",
                    severity="advisory",
                )
            )
        end_idx = start_idx + len(snippet)
        # Obvious mid-token clipping: snippet cuts through alphanumeric token boundaries.
        if start_idx > 0 and start_idx < len(paragraph_text):
            if paragraph_text[start_idx - 1].isalnum() and snippet[0].isalnum():
                blockers.append(
                    AuditIssue(
                        code="snippet_mid_token_start",
                        detail=f"evidence_bank[{index}] snippet starts mid-token.",
                        severity="blocker",
                    )
                )
        if end_idx > 0 and end_idx < len(paragraph_text):
            if paragraph_text[end_idx - 1].isalnum() and paragraph_text[end_idx].isalnum():
                blockers.append(
                    AuditIssue(
                        code="snippet_mid_token_end",
                        detail=f"evidence_bank[{index}] snippet ends mid-token.",
                        severity="blocker",
                    )
                )

    if boundary_total > 0:
        hard_cut_ratio = hard_cut_count / boundary_total
        if hard_cut_ratio > 0.35:
            advisories.append(
                AuditIssue(
                    code="high_hard_cut_ratio",
                    detail=f"Hard-cut snippet ratio is high ({hard_cut_ratio:.2f}).",
                    severity="advisory",
                )
            )
    if page_prefix_count > 0:
        advisories.append(
            AuditIssue(
                code="page_prefix_noise",
                detail=f"{page_prefix_count} snippets begin with page-prefix artifacts.",
                severity="advisory",
            )
        )

    material_changes_any = as_list(payload.get("material_changes")) or []
    material_changes: list[dict[str, object]] = []
    for change in material_changes_any:
        change_dict = as_str_dict(change)
        if change_dict is None:
            continue
        normalized: dict[str, object] = {}
        for key, value in change_dict.items():
            normalized[key] = value
        material_changes.append(normalized)

    material_ref_unique_by_year: dict[int, set[int]] = {
        target.year_from: set(),
        target.year_to: set(),
    }
    for change in material_changes:
        evidence_refs_any = as_list(change.get("evidence_refs")) or []
        for ref_any in evidence_refs_any:
            ref = as_str_dict(ref_any)
            year = get_int(ref.get("year")) if ref is not None else None
            paragraph_idx = get_int(ref.get("paragraph_idx")) if ref is not None else None
            if year is None or paragraph_idx is None:
                continue
            if year in material_ref_unique_by_year:
                material_ref_unique_by_year[year].add(paragraph_idx)

    if target.expected_artifact_id in {"llm_outline_compare_structured", "llm_outline_compare_insight"}:
        change_mechanisms_any = as_list(payload.get("change_mechanisms")) or []
        if not change_mechanisms_any:
            blockers.append(
                AuditIssue(
                    code="missing_change_mechanisms",
                    detail="structured payload must include non-empty change_mechanisms.",
                    severity="blocker",
                )
            )
        else:
            mechanism_ref_pairs: set[tuple[int, int]] = set()
            for idx, mechanism_any in enumerate(change_mechanisms_any):
                mechanism = as_str_dict(mechanism_any)
                if mechanism is None:
                    blockers.append(
                        AuditIssue(
                            code="invalid_change_mechanism_row",
                            detail=f"change_mechanisms[{idx}] must be object.",
                            severity="blocker",
                        )
                    )
                    continue
                for key in ("mechanism", "transmission_channel", "business_effect", "time_horizon"):
                    value = get_str(mechanism.get(key)) or ""
                    if not value.strip():
                        blockers.append(
                            AuditIssue(
                                code="incomplete_change_mechanism_row",
                                detail=f"change_mechanisms[{idx}].{key} must be non-empty.",
                                severity="blocker",
                            )
                        )
                evidence_refs_any = as_list(mechanism.get("evidence_refs")) or []
                for ref_any in evidence_refs_any:
                    ref = as_str_dict(ref_any)
                    year = get_int(ref.get("year")) if ref is not None else None
                    paragraph_idx = get_int(ref.get("paragraph_idx")) if ref is not None else None
                    if year is None or paragraph_idx is None:
                        continue
                    mechanism_ref_pairs.add((year, paragraph_idx))
            material_ref_pairs: set[tuple[int, int]] = set()
            for change in material_changes:
                evidence_refs_any = as_list(change.get("evidence_refs")) or []
                for ref_any in evidence_refs_any:
                    ref = as_str_dict(ref_any)
                    year = get_int(ref.get("year")) if ref is not None else None
                    paragraph_idx = get_int(ref.get("paragraph_idx")) if ref is not None else None
                    if year is None or paragraph_idx is None:
                        continue
                    material_ref_pairs.add((year, paragraph_idx))
            if material_ref_pairs and not (material_ref_pairs.intersection(mechanism_ref_pairs)):
                blockers.append(
                    AuditIssue(
                        code="lexical_only_change_claims",
                        detail="material_changes evidence does not overlap any change_mechanisms evidence refs.",
                        severity="blocker",
                    )
                )

    for idx, change in enumerate(material_changes):
        caveat = get_str(change.get("caveat")) or ""
        evidence_refs_any = as_list(change.get("evidence_refs")) or []
        evidence_tokens: set[str] = set()
        for ref_any in evidence_refs_any:
            ref = as_str_dict(ref_any)
            if ref is None:
                continue
            year = get_int(ref.get("year"))
            paragraph_idx = get_int(ref.get("paragraph_idx"))
            if year is None or paragraph_idx is None:
                continue
            linked = evidence_lookup.get((year, paragraph_idx))
            if linked is None:
                continue
            linked_snippet = get_str(linked.get("snippet"))
            if linked_snippet is None:
                continue
            evidence_tokens.update(tokenize(linked_snippet))
        caveat_tokens = tokenize(caveat)
        overlap = evidence_tokens.intersection(caveat_tokens)
        has_ref_signal = YEAR_OR_REF_RE.search(caveat) is not None
        if len(caveat.strip()) < 40:
            blockers.append(
                AuditIssue(
                    code="caveat_too_short",
                    detail=f"material_changes[{idx}] caveat is too short for case-specific limitation.",
                    severity="blocker",
                )
            )
        if not overlap and not has_ref_signal:
            blockers.append(
                AuditIssue(
                    code="caveat_not_specific",
                    detail=f"material_changes[{idx}] caveat lacks evidence-specific anchors.",
                    severity="blocker",
                )
            )

    generic_hits = 0
    generic_candidates = 0
    node_alignment_any = as_list(payload.get("node_alignment")) or []
    for row_any in node_alignment_any:
        row = as_str_dict(row_any)
        if row is None:
            continue
        rationale = (get_str(row.get("rationale")) or "").lower()
        generic_candidates += 1
        if any(phrase in rationale for phrase in GENERIC_PHRASES):
            generic_hits += 1
    for change in material_changes:
        for key in ("title", "caveat"):
            value = (get_str(change.get(key)) or "").lower()
            generic_candidates += 1
            if any(phrase in value for phrase in GENERIC_PHRASES):
                generic_hits += 1
    if generic_candidates > 0:
        generic_ratio = generic_hits / generic_candidates
        if generic_ratio > 0.18:
            advisories.append(
                AuditIssue(
                    code="generic_phrase_density",
                    detail=f"Generic phrase ratio is high ({generic_ratio:.2f}).",
                    severity="advisory",
                )
            )

    salience_values: list[float] = []
    for change in material_changes:
        salience_raw = change.get("salience")
        if isinstance(salience_raw, bool):
            continue
        if isinstance(salience_raw, (int, float)):
            salience_values.append(float(salience_raw))
    if len(salience_values) >= 3:
        spread = max(salience_values) - min(salience_values)
        if spread < 0.2:
            advisories.append(
                AuditIssue(
                    code="low_salience_spread",
                    detail=f"Material-change salience spread is low ({spread:.2f}).",
                    severity="advisory",
                )
            )
        stdev = statistics.pstdev(salience_values)
        if stdev < 0.08:
            advisories.append(
                AuditIssue(
                    code="flat_salience_distribution",
                    detail=f"Material-change salience stdev is low ({stdev:.2f}).",
                    severity="advisory",
                )
            )
        descending = all(
            salience_values[i] >= salience_values[i + 1]
            for i in range(len(salience_values) - 1)
        )
        if not descending:
            advisories.append(
                AuditIssue(
                    code="salience_not_ranked_desc",
                    detail="Material changes are not ordered by descending salience.",
                    severity="advisory",
                )
            )

    ref_counts: dict[tuple[int, int], int] = {}
    total_refs = 0
    opening_refs = 0
    for change in material_changes:
        evidence_refs_any = as_list(change.get("evidence_refs")) or []
        for ref_any in evidence_refs_any:
            ref = as_str_dict(ref_any)
            if ref is None:
                continue
            year = get_int(ref.get("year"))
            paragraph_idx = get_int(ref.get("paragraph_idx"))
            if year is None or paragraph_idx is None:
                continue
            pair = (year, paragraph_idx)
            ref_counts[pair] = ref_counts.get(pair, 0) + 1
            total_refs += 1
            if paragraph_idx == 0:
                opening_refs += 1
    if total_refs > 0 and ref_counts:
        max_ref_use = max(ref_counts.values())
        concentration = max_ref_use / total_refs
        unique_ratio = len(ref_counts) / total_refs
        if concentration > 0.4:
            advisories.append(
                AuditIssue(
                    code="evidence_ref_concentration",
                    detail=f"Evidence reference concentration is high ({concentration:.2f}).",
                    severity="advisory",
                )
            )
        if unique_ratio < 0.55:
            advisories.append(
                AuditIssue(
                    code="low_evidence_ref_diversity",
                    detail=f"Evidence reference uniqueness ratio is low ({unique_ratio:.2f}).",
                    severity="advisory",
                )
            )
        opening_ratio = opening_refs / total_refs
        if opening_ratio > 0.35:
            advisories.append(
                AuditIssue(
                    code="opening_paragraph_overuse",
                    detail=f"Opening paragraph reference ratio is high ({opening_ratio:.2f}).",
                    severity="advisory",
                )
            )
        if strict_depth and target.expected_artifact_id in {"llm_outline_compare_structured", "llm_outline_compare_insight"}:
            if opening_ratio > 0.35:
                blockers.append(
                    AuditIssue(
                        code="opening_paragraph_overuse_blocker",
                        detail=f"Opening paragraph reference ratio exceeds strict threshold ({opening_ratio:.2f} > 0.35).",
                        severity="blocker",
                    )
                )
            if concentration > 0.50:
                blockers.append(
                    AuditIssue(
                        code="evidence_ref_concentration_blocker",
                        detail=f"Evidence reference concentration exceeds strict threshold ({concentration:.2f} > 0.50).",
                        severity="blocker",
                    )
                )
            if unique_ratio < 0.50:
                blockers.append(
                    AuditIssue(
                        code="low_evidence_ref_diversity_blocker",
                        detail=f"Evidence reference uniqueness is below strict threshold ({unique_ratio:.2f} < 0.50).",
                        severity="blocker",
                    )
                )

    if strict_depth and target.expected_artifact_id in {"llm_outline_compare_structured", "llm_outline_compare_insight"}:
        if len(material_changes) < 4:
            blockers.append(
                AuditIssue(
                    code="insufficient_material_change_rows",
                    detail=f"Strict depth mode requires >=4 material_changes rows; got {len(material_changes)}.",
                    severity="blocker",
                )
            )

        prev_count = len(prev_map) if prev_map is not None else 0
        curr_count = len(curr_map) if curr_map is not None else 0
        if prev_count <= 0 or curr_count <= 0:
            blockers.append(
                AuditIssue(
                    code="insufficient_biyear_material_ref_coverage",
                    detail="Strict depth mode could not resolve year paragraph counts from paragraph maps.",
                    severity="blocker",
                )
            )
        else:
            coverage_failures: list[str] = []
            for year, paragraph_count in (
                (target.year_from, prev_count),
                (target.year_to, curr_count),
            ):
                required = 4 if paragraph_count >= 50 else 3
                observed = len(material_ref_unique_by_year.get(year, set()))
                if observed < required:
                    coverage_failures.append(
                        f"year={year} observed_unique_refs={observed} required={required} paragraph_count={paragraph_count}"
                    )
            if coverage_failures:
                blockers.append(
                    AuditIssue(
                        code="insufficient_biyear_material_ref_coverage",
                        detail="; ".join(coverage_failures),
                        severity="blocker",
                    )
                )

            def tercile_bucket(idx: int, paragraph_count: int) -> int:
                if paragraph_count <= 0:
                    return 0
                return min(2, (idx * 3) // paragraph_count)

            for year, paragraph_count, code in (
                (target.year_from, prev_count, "narrow_material_ref_span_prev"),
                (target.year_to, curr_count, "narrow_material_ref_span_curr"),
            ):
                if paragraph_count < 30:
                    continue
                refs = material_ref_unique_by_year.get(year, set())
                buckets = {tercile_bucket(idx, paragraph_count) for idx in refs}
                if len(buckets) < 2:
                    blockers.append(
                        AuditIssue(
                            code=code,
                            detail=(
                                f"Strict depth mode requires material refs to span >=2 terciles "
                                f"for year {year}; observed_terciles={sorted(buckets)} refs={sorted(refs)}."
                            ),
                            severity="blocker",
                        )
                    )

        ranked_changes: list[dict[str, object]] = []
        for change in material_changes:
            salience_raw = change.get("salience")
            if isinstance(salience_raw, bool) or not isinstance(salience_raw, (int, float)):
                continue
            ranked_changes.append(change)
        ranked_changes.sort(key=lambda change: float(cast(float, change.get("salience", 0.0))), reverse=True)
        top_ranked = ranked_changes[:3]
        if top_ranked:
            found_top3_non_opening_biyear = False
            for change in top_ranked:
                refs_by_year: dict[int, list[int]] = {
                    target.year_from: [],
                    target.year_to: [],
                }
                evidence_refs_any = as_list(change.get("evidence_refs")) or []
                for ref_any in evidence_refs_any:
                    ref = as_str_dict(ref_any)
                    year = get_int(ref.get("year")) if ref is not None else None
                    paragraph_idx = get_int(ref.get("paragraph_idx")) if ref is not None else None
                    if year is None or paragraph_idx is None:
                        continue
                    if year in refs_by_year:
                        refs_by_year[year].append(paragraph_idx)
                if (
                    refs_by_year[target.year_from]
                    and refs_by_year[target.year_to]
                    and any(idx > 0 for idx in refs_by_year[target.year_from])
                    and any(idx > 0 for idx in refs_by_year[target.year_to])
                ):
                    found_top3_non_opening_biyear = True
                    break
            if not found_top3_non_opening_biyear:
                blockers.append(
                    AuditIssue(
                        code="missing_top3_non_opening_biyear_change",
                        detail="Strict depth mode requires at least one top-3 material change with non-opening evidence refs in both years.",
                        severity="blocker",
                    )
                )

        analysis_expectations = as_str_dict(input_payload.get("analysis_expectations")) if input_payload else None
        focus_signals_any = as_list(analysis_expectations.get("focus_signals")) if analysis_expectations else []
        if focus_signals_any:
            ranked_change_positions: list[int] = []
            for position, change in enumerate(material_changes):
                salience_raw = change.get("salience")
                if isinstance(salience_raw, bool) or not isinstance(salience_raw, (int, float)):
                    continue
                ranked_change_positions.append(position)
            ranked_change_positions.sort(
                key=lambda idx: float(cast(float, material_changes[idx].get("salience", 0.0))),
                reverse=True,
            )
            mechanism_rows = [
                cast(dict[str, object], row)
                for row in (as_str_dict(item) for item in (as_list(payload.get("change_mechanisms")) or []))
                if row is not None
            ]
            investor_rows = [
                cast(dict[str, object], row)
                for row in (as_str_dict(item) for item in (as_list(payload.get("investor_relevance")) or []))
                if row is not None
            ]
            for signal_any in focus_signals_any:
                signal = as_str_dict(signal_any)
                if signal is None:
                    continue
                signal_id = get_str(signal.get("id")) or "unknown_signal"
                surface_requirements = as_str_dict(signal.get("surface_requirements")) or {}
                material_matches = collect_signal_match_indexes(
                    material_changes,
                    ("title", "caveat"),
                    signal,
                )
                required_sections_any = as_list(surface_requirements.get("required_sections")) or []
                requires_material_changes = any(
                    isinstance(section_name, str) and section_name == "material_changes"
                    for section_name in required_sections_any
                )
                if requires_material_changes and not material_matches:
                    blockers.append(
                        AuditIssue(
                            code="missing_required_focus_signal",
                            detail=f"focus_signal={signal_id} missing from required material_changes surface.",
                            severity="blocker",
                        )
                    )
                    continue
                top_rank_max = get_int(surface_requirements.get("top_material_change_rank_max"))
                if top_rank_max is not None and top_rank_max > 0 and material_matches:
                    top_positions = set(ranked_change_positions[:top_rank_max])
                    if not any(idx in top_positions for idx in material_matches):
                        blockers.append(
                            AuditIssue(
                                code="required_focus_signal_not_top_ranked",
                                detail=(
                                    f"focus_signal={signal_id} is present but not surfaced within top-{top_rank_max} "
                                    "material_changes by salience."
                                ),
                                severity="blocker",
                            )
                        )
                required_any_of_sections_any = as_list(surface_requirements.get("required_any_of_sections")) or []
                required_any_of_sections = [
                    str(item)
                    for item in required_any_of_sections_any
                    if isinstance(item, str) and item.strip()
                ]
                if required_any_of_sections:
                    supporting_matches = False
                    for section_name in required_any_of_sections:
                        if section_name == "change_mechanisms":
                            if collect_signal_match_indexes(
                                mechanism_rows,
                                ("mechanism", "transmission_channel", "business_effect"),
                                signal,
                            ):
                                supporting_matches = True
                                break
                        elif section_name == "investor_relevance":
                            if collect_signal_match_indexes(
                                investor_rows,
                                ("why_it_matters",),
                                signal,
                            ):
                                supporting_matches = True
                                break
                    if not supporting_matches:
                        blockers.append(
                            AuditIssue(
                                code="required_focus_signal_missing_supporting_surface",
                                detail=(
                                    f"focus_signal={signal_id} missing required supporting surface in one of "
                                    f"{required_any_of_sections}."
                                ),
                                severity="blocker",
                            )
                        )

    if target.expected_artifact_id == "llm_outline_compare_insight":
        executive_digest = as_str_dict(payload.get("executive_digest")) or {}
        summary_text = get_str(executive_digest.get("summary_text")) or ""
        digest_word_count = len(summary_text.split())
        if digest_word_count < 450 or digest_word_count > 650:
            blockers.append(
                AuditIssue(
                    code="digest_length_out_of_budget",
                    detail=f"executive_digest.summary_text word count out of range ({digest_word_count}, expected 450-650).",
                    severity="blocker",
                )
            )

        insight_cards_any = as_list(payload.get("insight_cards")) or []
        if len(insight_cards_any) < 4:
            blockers.append(
                AuditIssue(
                    code="insufficient_insight_card_rows",
                    detail=f"insight_cards must contain at least 4 rows; got {len(insight_cards_any)}.",
                    severity="blocker",
                )
            )

        evidence_map_any = as_list(payload.get("evidence_map")) or []
        evidence_ids: set[str] = set()
        evidence_pairs: set[tuple[int, int]] = set()
        for row_any in evidence_map_any:
            row = as_str_dict(row_any)
            if row is None:
                continue
            evidence_id = get_str(row.get("evidence_id"))
            year = get_int(row.get("year"))
            paragraph_idx = get_int(row.get("paragraph_idx"))
            if evidence_id:
                evidence_ids.add(evidence_id)
            if year is not None and paragraph_idx is not None and paragraph_idx >= 0:
                evidence_pairs.add((year, paragraph_idx))

        difference_count = 0
        similarity_count = 0
        unresolved_link_count = 0
        ref_counts_v3: dict[tuple[int, int], int] = {}
        refs_by_year_v3: dict[int, set[int]] = {
            target.year_from: set(),
            target.year_to: set(),
        }
        for idx, card_any in enumerate(insight_cards_any):
            card = as_str_dict(card_any)
            if card is None:
                continue
            insight_type = get_str(card.get("insight_type")) or ""
            if insight_type == "difference":
                difference_count += 1
            elif insight_type == "similarity":
                similarity_count += 1

            evidence_ref_ids = as_list(card.get("evidence_ref_ids")) or []
            for evidence_id_any in evidence_ref_ids:
                if isinstance(evidence_id_any, str) and evidence_id_any:
                    if evidence_ids and evidence_id_any not in evidence_ids:
                        unresolved_link_count += 1
                else:
                    unresolved_link_count += 1

            for list_key in ("evidence_refs_prev", "evidence_refs_curr"):
                refs_any = as_list(card.get(list_key)) or []
                for ref_any in refs_any:
                    ref = as_str_dict(ref_any)
                    year = get_int(ref.get("year")) if ref is not None else None
                    paragraph_idx = get_int(ref.get("paragraph_idx")) if ref is not None else None
                    if year is None or paragraph_idx is None or paragraph_idx < 0:
                        unresolved_link_count += 1
                        continue
                    pair = (year, paragraph_idx)
                    ref_counts_v3[pair] = ref_counts_v3.get(pair, 0) + 1
                    if year in refs_by_year_v3:
                        refs_by_year_v3[year].add(paragraph_idx)
                    if evidence_pairs and pair not in evidence_pairs:
                        unresolved_link_count += 1

        if difference_count < 1:
            blockers.append(
                AuditIssue(
                    code="missing_difference_insights",
                    detail="insight_cards must include at least one difference insight.",
                    severity="blocker",
                )
            )
        if similarity_count < 1:
            blockers.append(
                AuditIssue(
                    code="missing_similarity_insights",
                    detail="insight_cards must include at least one similarity insight.",
                    severity="blocker",
                )
            )
        if unresolved_link_count > 0:
            blockers.append(
                AuditIssue(
                    code="unresolved_insight_evidence_links",
                    detail=f"Found {unresolved_link_count} unresolved insight/evidence references.",
                    severity="blocker",
                )
            )

        if ref_counts_v3:
            total_refs_v3 = sum(ref_counts_v3.values())
            max_ref_use_v3 = max(ref_counts_v3.values())
            unique_ratio_v3 = len(ref_counts_v3) / total_refs_v3
            concentration_v3 = max_ref_use_v3 / total_refs_v3
            opening_ratio_v3 = sum(v for (_, idx), v in ref_counts_v3.items() if idx == 0) / total_refs_v3
            if concentration_v3 > 0.50:
                blockers.append(
                    AuditIssue(
                        code="insight_evidence_ref_concentration_blocker",
                        detail=f"Insight evidence concentration exceeds strict threshold ({concentration_v3:.2f} > 0.50).",
                        severity="blocker",
                    )
                )
            if unique_ratio_v3 < 0.50:
                blockers.append(
                    AuditIssue(
                        code="insight_low_evidence_ref_diversity_blocker",
                        detail=f"Insight evidence uniqueness below strict threshold ({unique_ratio_v3:.2f} < 0.50).",
                        severity="blocker",
                    )
                )
            if opening_ratio_v3 > 0.35:
                blockers.append(
                    AuditIssue(
                        code="insight_opening_paragraph_overuse_blocker",
                        detail=f"Insight opening-paragraph ratio exceeds strict threshold ({opening_ratio_v3:.2f} > 0.35).",
                        severity="blocker",
                    )
                )

            prev_count = len(prev_map) if prev_map is not None else 0
            curr_count = len(curr_map) if curr_map is not None else 0
            for year, paragraph_count in ((target.year_from, prev_count), (target.year_to, curr_count)):
                if paragraph_count <= 0:
                    continue
                required = 4 if paragraph_count >= 50 else 3
                observed = len(refs_by_year_v3.get(year, set()))
                if observed < required:
                    blockers.append(
                        AuditIssue(
                            code="insufficient_insight_biyear_ref_coverage",
                            detail=f"year={year} observed_unique_refs={observed} required={required} paragraph_count={paragraph_count}",
                            severity="blocker",
                        )
                    )

            def tercile_bucket_v3(idx: int, paragraph_count: int) -> int:
                if paragraph_count <= 0:
                    return 0
                return min(2, (idx * 3) // paragraph_count)

            for year, paragraph_count, code in (
                (target.year_from, prev_count, "narrow_insight_ref_span_prev"),
                (target.year_to, curr_count, "narrow_insight_ref_span_curr"),
            ):
                if paragraph_count < 30:
                    continue
                buckets = {tercile_bucket_v3(idx, paragraph_count) for idx in refs_by_year_v3.get(year, set())}
                if len(buckets) < 2:
                    blockers.append(
                        AuditIssue(
                            code=code,
                            detail=f"Insight refs must span >=2 terciles for year {year}; observed_terciles={sorted(buckets)}.",
                            severity="blocker",
                        )
                    )


    class_counts: dict[str, int] = {}
    for row_any in node_alignment_any:
        row = as_str_dict(row_any)
        if row is None:
            continue
        change_class = get_str(row.get("change_class"))
        if change_class is None:
            continue
        class_counts[change_class] = class_counts.get(change_class, 0) + 1
    total_alignment_rows = sum(class_counts.values())
    if total_alignment_rows > 0:
        stable_reworded = class_counts.get("stable", 0) + class_counts.get("reworded", 0)
        ratio = stable_reworded / total_alignment_rows
        if ratio > 0.75:
            advisories.append(
                AuditIssue(
                    code="stable_reworded_bias",
                    detail=f"Stable/reworded share is high ({ratio:.2f}).",
                    severity="advisory",
                )
            )

    score = 100
    score -= min(80, len(blockers) * 12)
    score -= min(25, len(advisories) * 4)
    score = max(0, min(100, score))
    return OutputAudit(path=path, blockers=blockers, advisories=advisories, quality_score=score)


def build_markdown_report(
    audits: list[OutputAudit],
    missing_paths: list[str],
    mode: str,
) -> list[str]:
    blockers_count = sum(len(item.blockers) for item in audits)
    advisories_count = sum(len(item.advisories) for item in audits)
    avg_score = 0.0
    if audits:
        avg_score = sum(item.quality_score for item in audits) / len(audits)

    lines: list[str] = []
    lines.append("# LLM Master Output Quality Audit")
    lines.append("")
    lines.append(f"Script: {SCRIPT_VERSION}")
    lines.append(f"Mode: {mode}")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| Audited files | {len(audits)} |")
    lines.append(f"| Missing files | {len(missing_paths)} |")
    lines.append(f"| Blockers | {blockers_count} |")
    lines.append(f"| Advisories | {advisories_count} |")
    lines.append(f"| Average quality score | {avg_score:.1f} |")
    lines.append("")
    if missing_paths:
        lines.append("## Missing Files")
        for path in missing_paths:
            lines.append(f"- {path}")
        lines.append("")
    for audit in audits:
        lines.append(f"## {normalize_path_like(str(audit.path))}")
        lines.append(f"- quality_score: {audit.quality_score}")
        if audit.blockers:
            lines.append("- blockers:")
            for issue in audit.blockers:
                lines.append(f"  - [{issue.code}] {issue.detail}")
        else:
            lines.append("- blockers: none")
        if audit.advisories:
            lines.append("- advisories:")
            for issue in audit.advisories:
                lines.append(f"  - [{issue.code}] {issue.detail}")
        else:
            lines.append("- advisories: none")
        lines.append("")
    return lines


def parse_output_paths(value: str) -> list[Path]:
    parts = [item.strip() for item in value.split(",") if item.strip()]
    output: list[Path] = []
    for part in parts:
        candidate = Path(part)
        if not candidate.is_absolute():
            candidate = (REPO_ROOT / candidate).resolve()
        output.append(candidate)
    return output


def resolve_targets_from_manifest(
    manifest_path: Path,
    campaign_id: str,
    target_field: str,
    only: str,
    only_mode: str,
) -> list[MasterTarget]:
    campaign = get_llm_campaign(campaign_id)
    if campaign is None:
        raise SystemExit(f"Unknown campaign id: {campaign_id}")
    targets = load_targets(manifest_path, target_field=target_field)
    if only:
        filters = [item.strip() for item in only.split(",") if item.strip()]
        targets = [
            target
            for target in targets
            if any(
                matches_only_token(target.expected_output_path, token, only_mode)
                for token in filters
            )
        ]
    marker = f"/{campaign.track_slug}/"
    return [
        target
        for target in targets
        if marker in ("/" + target.expected_output_path.replace("\\", "/").lstrip("/"))
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit llm_outline_compare_runtime/structured/insight output quality.")
    parser.add_argument("--output", default="", help="Single output path or comma-separated output paths.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST_PATH))
    parser.add_argument("--campaign-id", default=DEFAULT_PRIMARY_LLM_CAMPAIGN_ID)
    parser.add_argument(
        "--artifact-id",
        choices=("auto", "llm_outline_compare_runtime", "llm_outline_compare_structured", "llm_outline_compare_insight"),
        default="auto",
        help="Expected artifact id. `auto` infers from manifest target metadata/path.",
    )
    parser.add_argument(
        "--target-field",
        default="master_output",
        help="Manifest entry field containing expected output path metadata.",
    )
    parser.add_argument("--only", default="", help="Optional manifest target filter token(s).")
    parser.add_argument(
        "--only-mode",
        choices=("substring", "basename", "exact_path"),
        default="substring",
        help="Matching mode for --only token(s).",
    )
    parser.add_argument(
        "--mode",
        choices=("blockers", "advisory", "both"),
        default="both",
        help="Gate mode used for return code decisions.",
    )
    parser.add_argument(
        "--strict-depth",
        action="store_true",
        help=(
            "Enable stricter depth blockers for structured/insight outputs "
            "(material-change count, bi-year evidence breadth, top-ranked non-opening bi-year coverage, "
            "section-span coverage, and shallow-reference blocker promotion)."
        ),
    )
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument(
        "--report",
        default="",
        help=(
            "Quality report path. If omitted, writes a campaign/artifact-scoped "
            "report under reports/."
        ),
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    campaign = get_llm_campaign(args.campaign_id)
    if campaign is None or campaign.model_provider is None or campaign.model_name is None:
        raise SystemExit(f"Unknown or invalid campaign id: {args.campaign_id}")

    missing_paths: list[str] = []
    path_target_pairs: list[tuple[Path, MasterTarget]] = []

    if args.output.strip():
        output_paths = parse_output_paths(args.output)
        for output_path in output_paths:
            target = infer_target_from_output(output_path)
            if target is None:
                raise SystemExit(f"Unable to infer output metadata from path: {output_path}")
            path_target_pairs.append((output_path, target))
    else:
        manifest_path = Path(args.manifest)
        if not manifest_path.is_absolute():
            manifest_path = (REPO_ROOT / manifest_path).resolve()
        if not manifest_path.exists():
            raise SystemExit(f"Manifest not found: {manifest_path}")
        targets = resolve_targets_from_manifest(
            manifest_path=manifest_path,
            campaign_id=args.campaign_id,
            target_field=str(args.target_field),
            only=args.only,
            only_mode=args.only_mode,
        )
        if str(args.artifact_id) != "auto":
            forced_artifact = str(args.artifact_id)
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
                    expected_artifact_id=forced_artifact,
                    source_master_structured_path=target.source_master_structured_path,
                )
                for target in targets
            ]
        for target in targets:
            output_path = (REPO_ROOT / target.expected_output_path).resolve()
            if not output_path.exists():
                missing_paths.append(target.expected_output_path)
                continue
            path_target_pairs.append((output_path, target))

    audits: list[OutputAudit] = []
    for output_path, target in path_target_pairs:
        if not output_path.exists():
            missing_paths.append(normalize_path_like(str(output_path)))
            continue
        if str(args.artifact_id) != "auto":
            forced_artifact = str(args.artifact_id)
            target = MasterTarget(
                ticker=target.ticker,
                year_from=target.year_from,
                year_to=target.year_to,
                section=target.section,
                lens=target.lens,
                source_id=target.source_id,
                expected_output_path=target.expected_output_path,
                manifest_present_flag=target.manifest_present_flag,
                expected_artifact_id=forced_artifact,
                source_master_structured_path=target.source_master_structured_path,
            )
        audits.append(
            evaluate_output(
                path=output_path,
                target=target,
                expected_model_provider=campaign.model_provider,
                expected_model_name=campaign.model_name,
                strict_depth=bool(args.strict_depth),
            )
        )

    blocker_count = sum(len(item.blockers) for item in audits)
    advisory_count = sum(len(item.advisories) for item in audits)
    if missing_paths and not args.allow_missing:
        blocker_count += len(missing_paths)

    report_lines = build_markdown_report(audits=audits, missing_paths=missing_paths, mode=str(args.mode))
    report_arg = str(args.report).strip()
    report_path, is_scratch_report = resolve_quality_report_path_for_args(
        report_arg=report_arg,
        campaign_id=campaign.track_id,
        target_field=str(args.target_field),
        artifact_id=str(args.artifact_id),
        targets=[target for _, target in path_target_pairs],
        output=str(args.output),
        only=str(args.only),
        only_mode=str(args.only_mode),
    )
    if not report_path.is_absolute():
        report_path = (REPO_ROOT / report_path).resolve()
    if is_scratch_report:
        print(
            f"[note] auto-selected scratch quality report for filtered run: {report_path}",
            flush=True,
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    should_fail = False
    mode = str(args.mode)
    if mode in {"blockers", "both"}:
        if blocker_count > 0:
            should_fail = True
    status = "FAIL" if should_fail else "PASS"
    print(
        "QUALITY_AUDIT "
        + f"files={len(audits)} missing={len(missing_paths)} blockers={blocker_count} "
        + f"advisories={advisory_count} status={status}"
    )
    print(f"Wrote quality report: {report_path}")
    return 1 if should_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())



