from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import sys

from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v2")

REPO_ROOT = Path(__file__).resolve().parents[1]
# Legacy default path retained for reference-only queue flow.
DEFAULT_OUTPUTS_DIR = (
    REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab" / "llm_outputs"
)
LAB_INPUTS_ROOT = (
    REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab" / "llm_inputs"
)
LAB_INPUTS_V2_ROOT = (
    REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab" / "llm_inputs_v2"
)

DEFAULT_REQUIRED_FIELDS = [
    "lab_schema_version",
    "detector_id",
    "cleaning_lens",
    "source_id",
    "ticker",
    "section",
    "year_from",
    "year_to",
    "artifacts",
    "evidence",
    "metrics",
    "provenance",
]

FOCUSPACK_WARNING = "Focuspack is a subset; verify in full compare pane."
ALLOWED_CONFIDENCE: set[float] = {0.25, 0.50, 0.75}
PILCROW_SYMBOL = "\u00B6"
MOJIBAKE_PILCROW_SYMBOL = "\u00C2\u00B6"
DELTA_BRIEF_CITATION_RE = re.compile(
    r"(?P<year>20\d{2})\s*(?:(?P<mojibake>\u00C2\u00B6)|(?P<pilcrow>\u00B6)|(?P<para>para))\s*(?P<idx>\d+)",
    re.IGNORECASE,
)

sys.path.append(str(Path(__file__).resolve().parent))
from lab_llm_precompute_utils import (  # type: ignore
    BundlePaths,
    InputIndexEntry,
    as_list,
    as_str_dict,
    get_int,
    get_str,
    load_input_index,
    read_json,
    resolve_bundle_paths,
)


@dataclass(frozen=True)
class FocuspackMeta:
    selected_prev: list[int]
    selected_curr: list[int]
    full_prev_count: Optional[int]
    full_curr_count: Optional[int]


@dataclass(frozen=True)
class ParagraphMaps:
    prev_map: dict[int, str]
    curr_map: dict[int, str]


@dataclass(frozen=True)
class ValidationIssue:
    path: Path
    reasons: list[str]


@dataclass(frozen=True)
class ParsedFilename:
    detector_id: str
    year_from: int
    year_to: int
    lens_key: str
    section: str


@dataclass(frozen=True)
class ResolvedInputFile:
    path: Optional[Path]
    error: Optional[str]


def debug_count_delta_brief_citations(delta_brief: str) -> dict[str, int]:
    counts = {
        "total": 0,
        "pilcrow": 0,
        "mojibake": 0,
        "para": 0,
    }
    for match in DELTA_BRIEF_CITATION_RE.finditer(delta_brief):
        if match.group("mojibake") is not None:
            counts["mojibake"] += 1
        elif match.group("pilcrow") is not None:
            counts["pilcrow"] += 1
        elif match.group("para") is not None:
            counts["para"] += 1
        counts["total"] += 1
    return counts


def run_debug_citation_self_check() -> None:
    checks: list[tuple[str, str, dict[str, int]]] = [
        (
            "pilcrow_only",
            "(2021 \u00B633) and (2022 \u00B612)",
            {"total": 2, "pilcrow": 2, "mojibake": 0, "para": 0},
        ),
        (
            "mojibake_only",
            "(2021 \u00C2\u00B633) and (2022 \u00C2\u00B612)",
            {"total": 2, "pilcrow": 0, "mojibake": 2, "para": 0},
        ),
        (
            "para_only",
            "(2021 para 33) and (2022 para 12)",
            {"total": 2, "pilcrow": 0, "mojibake": 0, "para": 2},
        ),
        (
            "mixed",
            "(2021 \u00B633) and (2022 para 12)",
            {"total": 2, "pilcrow": 1, "mojibake": 0, "para": 1},
        ),
    ]
    for label, text, expected in checks:
        observed = debug_count_delta_brief_citations(text)
        if observed != expected:
            raise SystemExit(
                f"[debug-citations] self-check failed for {label}: expected {expected}, got {observed}"
            )
    print("[debug-citations] citation parser self-check passed.")


def load_required_fields(prompt_path: Optional[Path]) -> list[str]:
    if prompt_path is None or not prompt_path.exists():
        return list(DEFAULT_REQUIRED_FIELDS)
    lines = prompt_path.read_text(encoding="utf-8", errors="replace").splitlines()
    for idx, line in enumerate(lines):
        if "Lab detector envelope" not in line:
            continue
        for j in range(idx + 1, len(lines)):
            candidate = lines[j].strip()
            if not candidate:
                continue
            fields: list[str] = []
            for part in candidate.split(","):
                cleaned = part.strip().rstrip(".")
                if cleaned:
                    fields.append(cleaned)
            if fields:
                return fields
            break
    return list(DEFAULT_REQUIRED_FIELDS)


def parse_output_filename(name: str, section: str) -> Optional[ParsedFilename]:
    marker = f"_{section}_"
    if not name.startswith("lab_"):
        return None
    if marker not in name:
        return None
    prefix, rest = name.split(marker, 1)
    detector_id = prefix[len("lab_") :]
    rest_parts = rest.split("_")
    if len(rest_parts) < 3:
        return None
    year_from = None
    year_to = None
    if rest_parts[0].isdigit():
        year_from = int(rest_parts[0])
    if rest_parts[1].isdigit():
        year_to = int(rest_parts[1])
    if year_from is None or year_to is None:
        return None
    lens_key = "_".join(rest_parts[2:])
    if not lens_key:
        return None
    return ParsedFilename(
        detector_id=detector_id,
        year_from=year_from,
        year_to=year_to,
        lens_key=lens_key,
        section=section,
    )


def load_focuspack_meta(path: Path) -> Optional[FocuspackMeta]:
    try:
        payload = read_json(path)
    except json.JSONDecodeError:
        return None
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        return None
    meta_raw = as_str_dict(payload_dict.get("focuspack_meta"))
    if meta_raw is None:
        return None
    selected_prev_raw = as_list(meta_raw.get("selected_prev_indices"))
    selected_curr_raw = as_list(meta_raw.get("selected_curr_indices"))
    if selected_prev_raw is None or selected_curr_raw is None:
        return None
    selected_prev: list[int] = []
    selected_curr: list[int] = []
    for value in selected_prev_raw:
        if isinstance(value, int) and not isinstance(value, bool):
            selected_prev.append(value)
        else:
            return None
    for value in selected_curr_raw:
        if isinstance(value, int) and not isinstance(value, bool):
            selected_curr.append(value)
        else:
            return None
    full_prev_count = get_int(meta_raw.get("full_prev_count"))
    full_curr_count = get_int(meta_raw.get("full_curr_count"))
    return FocuspackMeta(
        selected_prev=selected_prev,
        selected_curr=selected_curr,
        full_prev_count=full_prev_count,
        full_curr_count=full_curr_count,
    )


def load_full_counts(path: Path) -> Optional[tuple[int, int]]:
    try:
        payload = read_json(path)
    except json.JSONDecodeError:
        return None
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        return None
    texts = as_str_dict(payload_dict.get("texts"))
    if texts is None:
        return None
    prev_paras = as_list(texts.get("prev_paragraphs"))
    curr_paras = as_list(texts.get("curr_paragraphs"))
    if prev_paras is None or curr_paras is None:
        return None
    return (len(prev_paras), len(curr_paras))


def _is_json_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() == ".json"


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def resolve_input_file(path_value: str, output_path: Path) -> ResolvedInputFile:
    if not path_value or not path_value.strip():
        return ResolvedInputFile(path=None, error="provenance.input_file missing")

    raw_path = Path(path_value.strip().replace("\\", "/"))
    if raw_path.is_absolute():
        absolute_path = raw_path.resolve()
        if not _is_within(absolute_path, REPO_ROOT):
            return ResolvedInputFile(
                path=None,
                error=(
                    "provenance.input_file absolute paths must stay within repository root"
                ),
            )
        if _is_json_file(absolute_path):
            return ResolvedInputFile(path=absolute_path, error=None)
        return ResolvedInputFile(
            path=None,
            error=f"provenance.input_file not found or not JSON: {path_value}",
        )

    repo_relative_candidate = (REPO_ROOT / raw_path).resolve()
    if _is_within(repo_relative_candidate, REPO_ROOT) and _is_json_file(repo_relative_candidate):
        return ResolvedInputFile(path=repo_relative_candidate, error=None)

    normalized = path_value.strip().replace("\\", "/").lstrip("./")
    if normalized.startswith("inputs/"):
        v2_candidate = (LAB_INPUTS_V2_ROOT / normalized).resolve()
        if _is_json_file(v2_candidate):
            return ResolvedInputFile(path=v2_candidate, error=None)
    if normalized.startswith("data/"):
        data_candidate = (REPO_ROOT / "public" / normalized).resolve()
        if _is_json_file(data_candidate):
            return ResolvedInputFile(path=data_candidate, error=None)
    if normalized.startswith("public/"):
        public_candidate = (REPO_ROOT / normalized).resolve()
        if _is_json_file(public_candidate):
            return ResolvedInputFile(path=public_candidate, error=None)

    llm_inputs_candidate = (LAB_INPUTS_ROOT / raw_path.name).resolve()
    if _is_json_file(llm_inputs_candidate):
        return ResolvedInputFile(path=llm_inputs_candidate, error=None)

    # v2 local run-pack references may be relative to pair-manifest location.
    parent_candidate = (output_path.parent / raw_path).resolve()
    if _is_within(parent_candidate, REPO_ROOT) and _is_json_file(parent_candidate):
        return ResolvedInputFile(path=parent_candidate, error=None)

    bundles_root = REPO_ROOT / "bundles"
    matches: list[Path] = []
    if bundles_root.exists():
        for candidate in bundles_root.rglob(raw_path.name):
            candidate_resolved = candidate.resolve()
            if not _is_within(candidate_resolved, bundles_root):
                continue
            if not _is_json_file(candidate_resolved):
                continue
            matches.append(candidate_resolved)
    matches = sorted(set(matches), key=lambda item: str(item))
    if len(matches) == 1:
        return ResolvedInputFile(path=matches[0], error=None)
    if len(matches) > 1:
        preview = ", ".join(
            str(candidate.relative_to(REPO_ROOT)) for candidate in matches[:3]
        )
        suffix = " ..." if len(matches) > 3 else ""
        return ResolvedInputFile(
            path=None,
            error=(
                f"provenance.input_file ambiguous for '{path_value}': {len(matches)} matches "
                f"under bundles/**/inputs ({preview}{suffix}); use an exact repo-relative path"
            ),
        )
    return ResolvedInputFile(path=None, error=f"provenance.input_file not found: {path_value}")


def normalize_output_stem(name: str) -> str:
    if name.endswith(".fixed"):
        return name[: -len(".fixed")]
    return name


def _extract_year_paragraphs(payload: dict[str, object]) -> Optional[list[str]]:
    texts = as_str_dict(payload.get("texts"))
    if texts is None:
        return None
    year_raw = as_list(texts.get("paragraphs"))
    if year_raw is None:
        return None
    output: list[str] = []
    for item in year_raw:
        if not isinstance(item, str):
            return None
        output.append(item)
    return output


def build_paragraph_maps(
    input_payload: dict[str, object],
    input_payload_path: Optional[Path] = None,
) -> Optional[ParagraphMaps]:
    year_inputs = as_str_dict(input_payload.get("year_inputs"))
    if year_inputs is not None:
        prev_ref = get_str(year_inputs.get("prev"))
        curr_ref = get_str(year_inputs.get("curr"))
        if prev_ref is None or curr_ref is None:
            return None
        anchor = input_payload_path if input_payload_path is not None else REPO_ROOT
        prev_resolution = resolve_input_file(prev_ref, anchor)
        curr_resolution = resolve_input_file(curr_ref, anchor)
        if prev_resolution.path is None or curr_resolution.path is None:
            return None
        try:
            prev_payload_raw = read_json(prev_resolution.path)
            curr_payload_raw = read_json(curr_resolution.path)
        except json.JSONDecodeError:
            return None
        prev_payload = as_str_dict(prev_payload_raw)
        curr_payload = as_str_dict(curr_payload_raw)
        if prev_payload is None or curr_payload is None:
            return None
        yr_prev = _extract_year_paragraphs(prev_payload)
        yr_curr = _extract_year_paragraphs(curr_payload)
        if yr_prev is None or yr_curr is None:
            return None
        prev_map = {idx: text for idx, text in enumerate(yr_prev)}
        curr_map = {idx: text for idx, text in enumerate(yr_curr)}
        return ParagraphMaps(prev_map=prev_map, curr_map=curr_map)

    texts = as_str_dict(input_payload.get("texts"))
    if texts is None:
        return None
    prev_raw = as_list(texts.get("prev_paragraphs"))
    curr_raw = as_list(texts.get("curr_paragraphs"))
    if prev_raw is None or curr_raw is None:
        return None
    prev_paras: list[str] = []
    for item in prev_raw:
        if not isinstance(item, str):
            return None
        prev_paras.append(item)
    curr_paras: list[str] = []
    for item in curr_raw:
        if not isinstance(item, str):
            return None
        curr_paras.append(item)

    focus_meta = as_str_dict(input_payload.get("focuspack_meta"))
    if focus_meta is not None:
        selected_prev_raw = as_list(focus_meta.get("selected_prev_indices"))
        selected_curr_raw = as_list(focus_meta.get("selected_curr_indices"))
        if selected_prev_raw is None or selected_curr_raw is None:
            return None
        selected_prev: list[int] = []
        selected_curr: list[int] = []
        for value in selected_prev_raw:
            if isinstance(value, int) and not isinstance(value, bool):
                selected_prev.append(value)
            else:
                return None
        for value in selected_curr_raw:
            if isinstance(value, int) and not isinstance(value, bool):
                selected_curr.append(value)
            else:
                return None
        if len(selected_prev) != len(prev_paras) or len(selected_curr) != len(curr_paras):
            return None
        prev_map = {full_idx: prev_paras[i] for i, full_idx in enumerate(selected_prev)}
        curr_map = {full_idx: curr_paras[i] for i, full_idx in enumerate(selected_curr)}
        return ParagraphMaps(prev_map=prev_map, curr_map=curr_map)

    prev_map = {idx: text for idx, text in enumerate(prev_paras)}
    curr_map = {idx: text for idx, text in enumerate(curr_paras)}
    return ParagraphMaps(prev_map=prev_map, curr_map=curr_map)


def load_text_counts(input_payload: dict[str, object]) -> Optional[tuple[int, int]]:
    texts = as_str_dict(input_payload.get("texts"))
    if texts is None:
        return None
    prev_raw = as_list(texts.get("prev_paragraphs"))
    curr_raw = as_list(texts.get("curr_paragraphs"))
    if prev_raw is None or curr_raw is None:
        return None
    return (len(prev_raw), len(curr_raw))


def get_input_entry(
    index_map: dict[tuple[str, int, int, str, str], InputIndexEntry],
    ticker: str,
    year_from: int,
    year_to: int,
    section: str,
    lens: str,
) -> Optional[InputIndexEntry]:
    return index_map.get((ticker.upper(), year_from, year_to, section, lens))


def validate_outputs(
    outputs_dir: Path,
    bundle_paths: BundlePaths,
    required_fields: list[str],
) -> list[ValidationIssue]:
    if not outputs_dir.exists():
        return [ValidationIssue(outputs_dir, ["outputs directory not found"])]

    if bundle_paths.focus_index is None or bundle_paths.full_index is None:
        return [ValidationIssue(outputs_dir, ["bundle missing focus or full input index"])]
    focus_index = load_input_index(bundle_paths.focus_index, bundle_paths.bundle_root)
    full_index = load_input_index(bundle_paths.full_index, bundle_paths.bundle_root)

    focus_meta_cache: dict[Path, Optional[FocuspackMeta]] = {}
    full_counts_cache: dict[Path, Optional[tuple[int, int]]] = {}

    issues: list[ValidationIssue] = []

    output_files = sorted(outputs_dir.rglob("*.json"))
    for path in output_files:
        reasons: list[str] = []
        try:
            payload = read_json(path)
        except json.JSONDecodeError as exc:
            issues.append(ValidationIssue(path, [f"invalid JSON: {exc}"]))
            continue
        payload_dict = as_str_dict(payload)
        if payload_dict is None:
            issues.append(ValidationIssue(path, ["JSON root is not an object"]))
            continue

        for field in required_fields:
            if field not in payload_dict:
                reasons.append(f"missing field: {field}")

        section = get_str(payload_dict.get("section")) or "10k_item1a"
        normalized_stem = normalize_output_stem(path.stem)
        parsed = parse_output_filename(normalized_stem, section)
        if parsed is None and section != "10k_item1a":
            parsed = parse_output_filename(normalized_stem, "10k_item1a")
        if parsed is None:
            reasons.append("filename does not match expected pattern")
            issues.append(ValidationIssue(path, reasons))
            continue

        detector_folder = path.parent.parent.name
        ticker_folder = path.parent.name
        if detector_folder and detector_folder != parsed.detector_id:
            reasons.append(
                f"detector folder mismatch: {detector_folder} vs {parsed.detector_id}"
            )

        detector_id = get_str(payload_dict.get("detector_id"))
        if detector_id and detector_id != parsed.detector_id:
            reasons.append(
                f"detector_id mismatch: {detector_id} vs {parsed.detector_id}"
            )
        ticker_value = get_str(payload_dict.get("ticker"))
        if ticker_value and ticker_value.upper() != ticker_folder.upper():
            reasons.append(
                f"ticker mismatch: {ticker_value.upper()} vs {ticker_folder.upper()}"
            )

        year_from = get_int(payload_dict.get("year_from"))
        year_to = get_int(payload_dict.get("year_to"))
        if year_from is None or year_to is None:
            reasons.append("year_from/year_to missing or not integers")
            issues.append(ValidationIssue(path, reasons))
            continue
        if year_from != parsed.year_from or year_to != parsed.year_to:
            reasons.append(
                f"year mismatch: {year_from}-{year_to} vs {parsed.year_from}-{parsed.year_to}"
            )

        cleaning_lens = get_str(payload_dict.get("cleaning_lens"))

        evidence_raw = payload_dict.get("evidence")
        evidence_list = as_list(evidence_raw)
        if evidence_list is None:
            reasons.append("evidence is not a list")
            issues.append(ValidationIssue(path, reasons))
            continue

        detector = parsed.detector_id

        metrics = as_str_dict(payload_dict.get("metrics"))
        if metrics is None:
            reasons.append("metrics is not an object")
            metrics = {}

        confidence_raw = metrics.get("confidence")
        if confidence_raw is None:
            reasons.append("metrics.confidence missing")
        elif isinstance(confidence_raw, bool) or not isinstance(confidence_raw, (int, float)):
            reasons.append("metrics.confidence not a number")
        else:
            confidence_value = float(confidence_raw)
            if confidence_value not in ALLOWED_CONFIDENCE:
                reasons.append(
                    f"metrics.confidence must be one of {sorted(ALLOWED_CONFIDENCE)} (got {confidence_value})"
                )

        warnings_raw = as_list(metrics.get("warnings"))
        warnings_list: list[str] = []
        if warnings_raw is None:
            reasons.append("metrics.warnings missing or not a list")
        else:
            for idx, item in enumerate(warnings_raw):
                if isinstance(item, str):
                    warnings_list.append(item)
                else:
                    reasons.append(f"metrics.warnings[{idx}] is not a string")

        artifacts = as_str_dict(payload_dict.get("artifacts"))
        if artifacts is None:
            reasons.append("artifacts is not an object")
            artifacts = {}

        if detector == "det_llm_delta_brief_v1":
            delta_brief = get_str(artifacts.get("delta_brief"))
            if delta_brief is None or not delta_brief.strip():
                reasons.append("artifacts.delta_brief missing or empty")
            if len(evidence_list) < 3 or len(evidence_list) > 8:
                reasons.append(
                    f"evidence count out of range for delta brief: {len(evidence_list)} (expected 3-8)"
                )
            if delta_brief:
                citation_counts = debug_count_delta_brief_citations(delta_brief)
                has_pilcrow_format = (
                    citation_counts["pilcrow"] + citation_counts["mojibake"]
                ) > 0
                has_para_format = citation_counts["para"] > 0
                if MOJIBAKE_PILCROW_SYMBOL in delta_brief:
                    reasons.append(
                        "WARN: delta_brief contains mojibake 'Â¶' (encoding issue). Prefer '¶' or fallback 'para'."
                    )
                if has_pilcrow_format and has_para_format:
                    reasons.append(
                        'WARN: delta_brief mixes citation formats ("YYYY ¶NN" and "YYYY para NN"). Use one format consistently.'
                    )
                if citation_counts["total"] < 2:
                    reasons.append(
                        'WARN: delta_brief should include at least 2 inline citations like "YYYY ¶NN" or "YYYY para NN"'
                    )

        selected_prev: list[int] = []
        selected_curr: list[int] = []
        if detector == "det_llm_excerpt_picker_v1":
            selected_prev_raw = as_list(artifacts.get("selected_prev"))
            selected_curr_raw = as_list(artifacts.get("selected_curr"))
            if selected_prev_raw is None:
                reasons.append("artifacts.selected_prev missing or not a list")
            else:
                for idx, value in enumerate(selected_prev_raw):
                    if isinstance(value, int) and not isinstance(value, bool):
                        selected_prev.append(value)
                    else:
                        reasons.append(f"artifacts.selected_prev[{idx}] is not an int")
            if selected_curr_raw is None:
                reasons.append("artifacts.selected_curr missing or not a list")
            else:
                for idx, value in enumerate(selected_curr_raw):
                    if isinstance(value, int) and not isinstance(value, bool):
                        selected_curr.append(value)
                    else:
                        reasons.append(f"artifacts.selected_curr[{idx}] is not an int")
            if len(evidence_list) < 6 or len(evidence_list) > 10:
                reasons.append(
                    f"WARN: excerpt picker evidence count out of band: {len(evidence_list)} (expected 6-10)"
                )

        provenance = as_str_dict(payload_dict.get("provenance")) or {}
        input_file_value = get_str(provenance.get("input_file"))
        if input_file_value is not None and not input_file_value.strip():
            input_file_value = None
        paragraph_maps: Optional[ParagraphMaps] = None
        input_text_counts: Optional[tuple[int, int]] = None
        if input_file_value:
            resolution = resolve_input_file(input_file_value, path)
            input_path = resolution.path
            if input_path is None or not input_path.exists():
                reasons.append(
                    resolution.error
                    or f"provenance.input_file not found: {input_file_value}"
                )
            else:
                input_payload = as_str_dict(read_json(input_path))
                if input_payload is None:
                    reasons.append("provenance.input_file JSON invalid")
                else:
                    input_text_counts = load_text_counts(input_payload)
                    paragraph_maps = build_paragraph_maps(
                        input_payload,
                        input_payload_path=input_path,
                    )
                    if paragraph_maps is None:
                        reasons.append("provenance.input_file missing resolvable paragraph maps")
        else:
            reasons.append("provenance.input_file missing")

        lens_key = parsed.lens_key
        lens_name = ""
        is_focuspack = False
        if lens_key.startswith("focuspack_"):
            lens_name = lens_key[len("focuspack_") :]
            is_focuspack = True
        elif lens_key.startswith("full_"):
            lens_name = lens_key[len("full_") :]
        else:
            reasons.append(f"unknown lens key: {lens_key}")

        if cleaning_lens and lens_name and cleaning_lens != lens_name:
            reasons.append(
                f"cleaning_lens mismatch: {cleaning_lens} vs {lens_name}"
            )

        focus_entry = None
        focus_meta = None
        full_entry = None
        full_counts = None

        if lens_name:
            if is_focuspack:
                focus_entry = get_input_entry(
                    focus_index,
                    ticker_folder,
                    year_from,
                    year_to,
                    parsed.section,
                    lens_name,
                )
                if focus_entry is None:
                    reasons.append("missing focuspack input index entry")
                else:
                    cached = focus_meta_cache.get(focus_entry.path)
                    if cached is None:
                        cached = load_focuspack_meta(focus_entry.path)
                        focus_meta_cache[focus_entry.path] = cached
                    focus_meta = cached
                    if focus_meta is None:
                        reasons.append("invalid focuspack_meta in input JSON")

            full_entry = get_input_entry(
                full_index,
                ticker_folder,
                year_from,
                year_to,
                parsed.section,
                lens_name,
            )
            if full_entry is None:
                reasons.append("missing full input index entry")
            else:
                cached_full = full_counts_cache.get(full_entry.path)
                if cached_full is None:
                    cached_full = load_full_counts(full_entry.path)
                    full_counts_cache[full_entry.path] = cached_full
                full_counts = cached_full
                if full_counts is None:
                    reasons.append("invalid full input JSON for paragraph counts")

        evidence_counts_by_year: dict[int, int] = {year_from: 0, year_to: 0}
        evidence_prev_indices: list[int] = []
        evidence_curr_indices: list[int] = []
        evidence_prev_seen: set[int] = set()
        evidence_curr_seen: set[int] = set()
        for idx, evidence in enumerate(evidence_list):
            evidence_dict = as_str_dict(evidence)
            if evidence_dict is None:
                reasons.append(f"evidence[{idx}] is not an object")
                continue
            paragraph_idx = get_int(evidence_dict.get("paragraph_idx"))
            year_value = get_int(evidence_dict.get("year"))
            if paragraph_idx is None:
                reasons.append(f"evidence[{idx}] paragraph_idx missing or not int")
                continue
            if year_value is None:
                reasons.append(f"evidence[{idx}] year missing or not int")
                continue
            if year_value in evidence_counts_by_year:
                evidence_counts_by_year[year_value] += 1
            if paragraph_idx < 0:
                reasons.append(f"evidence[{idx}] paragraph_idx negative")
                continue
            if year_value == year_from and paragraph_idx not in evidence_prev_seen:
                evidence_prev_seen.add(paragraph_idx)
                evidence_prev_indices.append(paragraph_idx)
            if year_value == year_to and paragraph_idx not in evidence_curr_seen:
                evidence_curr_seen.add(paragraph_idx)
                evidence_curr_indices.append(paragraph_idx)

            snippet = get_str(evidence_dict.get("snippet"))
            if snippet is None:
                reasons.append(f"evidence[{idx}] snippet missing or not a string")
            elif not snippet.strip():
                reasons.append(f"evidence[{idx}] snippet empty")
            elif len(snippet) > 350:
                reasons.append(
                    f"evidence[{idx}] snippet too long ({len(snippet)} chars, max 350)"
                )

            why_value = get_str(evidence_dict.get("why"))
            if why_value is None or not why_value.strip():
                reasons.append(f"evidence[{idx}] why missing or empty")

            highlights_raw = evidence_dict.get("highlights")
            if highlights_raw is None:
                if detector == "det_llm_delta_brief_v1":
                    reasons.append(f"evidence[{idx}] highlights missing")
                highlights_list: list[str] = []
            else:
                highlights_any = as_list(highlights_raw)
                highlights_list = []
                if highlights_any is None:
                    reasons.append(f"evidence[{idx}] highlights is not a list")
                else:
                    for j, item in enumerate(highlights_any):
                        if isinstance(item, str):
                            highlights_list.append(item)
                        else:
                            reasons.append(
                                f"evidence[{idx}] highlights[{j}] is not a string"
                            )
            if detector in {"det_llm_delta_brief_v1", "det_llm_excerpt_picker_v1"} and len(
                highlights_list
            ) < 1:
                detector_label = (
                    "delta brief"
                    if detector == "det_llm_delta_brief_v1"
                    else "excerpt picker"
                )
                reasons.append(
                    f"evidence[{idx}] highlights missing/empty ({detector_label})"
                )

            if is_focuspack:
                if focus_meta is None:
                    continue
                selected = (
                    focus_meta.selected_prev
                    if year_value == year_from
                    else focus_meta.selected_curr
                    if year_value == year_to
                    else None
                )
                if selected is None:
                    reasons.append(
                        f"evidence[{idx}] year not in pair: {year_value}"
                    )
                    continue
                if paragraph_idx not in selected:
                    reasons.append(
                        f"evidence[{idx}] paragraph_idx not in focuspack mapping"
                    )
                count_prev = (
                    full_counts[0]
                    if full_counts is not None
                    else focus_meta.full_prev_count
                )
                count_curr = (
                    full_counts[1]
                    if full_counts is not None
                    else focus_meta.full_curr_count
                )
                count = count_prev if year_value == year_from else count_curr
                if count is not None and paragraph_idx >= count:
                    reasons.append(
                        f"evidence[{idx}] paragraph_idx out of bounds (count {count})"
                    )
            elif lens_name and full_counts is not None:
                count = full_counts[0] if year_value == year_from else full_counts[1]
                if paragraph_idx >= count:
                    reasons.append(
                        f"evidence[{idx}] paragraph_idx out of bounds (count {count})"
                    )

            if paragraph_maps is not None and snippet is not None:
                if year_value == year_from:
                    mapped_text = paragraph_maps.prev_map.get(paragraph_idx)
                elif year_value == year_to:
                    mapped_text = paragraph_maps.curr_map.get(paragraph_idx)
                else:
                    mapped_text = None
                if mapped_text is None:
                    reasons.append(
                        f"snippet mapping missing (year={year_value}, paragraph_idx={paragraph_idx})"
                    )
                elif snippet not in mapped_text:
                    reasons.append(
                        f"snippet not found in mapped paragraph (year={year_value}, paragraph_idx={paragraph_idx})"
                    )

        if detector == "det_llm_excerpt_picker_v1":
            if len(selected_prev) != len(set(selected_prev)):
                reasons.append("artifacts.selected_prev contains duplicate FULL indices")
            if len(selected_curr) != len(set(selected_curr)):
                reasons.append("artifacts.selected_curr contains duplicate FULL indices")

            for idx, value in enumerate(selected_prev):
                if value < 0:
                    reasons.append(f"artifacts.selected_prev[{idx}] must be >= 0")
            for idx, value in enumerate(selected_curr):
                if value < 0:
                    reasons.append(f"artifacts.selected_curr[{idx}] must be >= 0")

            selected_prev_set = set(selected_prev)
            selected_curr_set = set(selected_curr)
            evidence_prev_set = set(evidence_prev_indices)
            evidence_curr_set = set(evidence_curr_indices)

            missing_prev = [
                value for value in evidence_prev_indices if value not in selected_prev_set
            ]
            missing_curr = [
                value for value in evidence_curr_indices if value not in selected_curr_set
            ]
            if missing_prev:
                reasons.append(
                    "artifacts.selected_prev missing evidence paragraph_idx values "
                    f"for year_from: {missing_prev}"
                )
            if missing_curr:
                reasons.append(
                    "artifacts.selected_curr missing evidence paragraph_idx values "
                    f"for year_to: {missing_curr}"
                )

            extras_prev = [
                value for value in selected_prev if value not in evidence_prev_set
            ]
            extras_curr = [
                value for value in selected_curr if value not in evidence_curr_set
            ]
            if extras_prev:
                reasons.append(
                    f"WARN: artifacts.selected_prev includes indices not used in evidence: {extras_prev}"
                )
            if extras_curr:
                reasons.append(
                    f"WARN: artifacts.selected_curr includes indices not used in evidence: {extras_curr}"
                )

            if is_focuspack:
                if focus_meta is None:
                    reasons.append(
                        "cannot validate artifacts.selected_prev/curr FULL membership (missing focuspack_meta)"
                    )
                else:
                    prev_allowed = set(focus_meta.selected_prev)
                    curr_allowed = set(focus_meta.selected_curr)
                    prev_local_count = (
                        input_text_counts[0]
                        if input_text_counts is not None
                        else len(focus_meta.selected_prev)
                    )
                    curr_local_count = (
                        input_text_counts[1]
                        if input_text_counts is not None
                        else len(focus_meta.selected_curr)
                    )

                    invalid_prev = [
                        value for value in selected_prev if value not in prev_allowed
                    ]
                    invalid_curr = [
                        value for value in selected_curr if value not in curr_allowed
                    ]

                    if invalid_prev:
                        looks_prev_local = (
                            len(selected_prev) > 0
                            and all(
                                0 <= value < prev_local_count
                                for value in selected_prev
                            )
                            and all(
                                value not in prev_allowed for value in selected_prev
                            )
                        )
                        if looks_prev_local:
                            reasons.append(
                                "artifacts.selected_prev looks focuspack-local; map via focuspack_meta.selected_prev_indices[pos]"
                            )
                        else:
                            reasons.append(
                                "artifacts.selected_prev must use FULL indices from "
                                f"focuspack_meta.selected_prev_indices (invalid: {invalid_prev})"
                            )

                    if invalid_curr:
                        looks_curr_local = (
                            len(selected_curr) > 0
                            and all(
                                0 <= value < curr_local_count
                                for value in selected_curr
                            )
                            and all(
                                value not in curr_allowed for value in selected_curr
                            )
                        )
                        if looks_curr_local:
                            reasons.append(
                                "artifacts.selected_curr looks focuspack-local; map via focuspack_meta.selected_curr_indices[pos]"
                            )
                        else:
                            reasons.append(
                                "artifacts.selected_curr must use FULL indices from "
                                f"focuspack_meta.selected_curr_indices (invalid: {invalid_curr})"
                            )
            elif full_counts is not None:
                prev_count, curr_count = full_counts
                for idx, value in enumerate(selected_prev):
                    if value >= prev_count:
                        reasons.append(
                            f"artifacts.selected_prev[{idx}] out of bounds (count {prev_count})"
                        )
                for idx, value in enumerate(selected_curr):
                    if value >= curr_count:
                        reasons.append(
                            f"artifacts.selected_curr[{idx}] out of bounds (count {curr_count})"
                        )

        if detector == "det_llm_delta_brief_v1" and len(evidence_list) >= 4:
            prev_count = evidence_counts_by_year.get(year_from, 0)
            curr_count = evidence_counts_by_year.get(year_to, 0)
            if prev_count < 2 or curr_count < 2:
                reasons.append(
                    f"WARN: delta brief evidence distribution lopsided (year_from={prev_count}, year_to={curr_count}); target >=2 per year when possible"
                )

        if reasons:
            issues.append(ValidationIssue(path, reasons))

    return issues


def split_issues(
    issues: list[ValidationIssue],
) -> tuple[list[ValidationIssue], list[ValidationIssue]]:
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    for issue in issues:
        has_error = any(not reason.startswith("WARN:") for reason in issue.reasons)
        if has_error:
            errors.append(issue)
        else:
            warnings.append(issue)
    return errors, warnings


def print_issues(title: str, issues: list[ValidationIssue]) -> None:
    print(title)
    for issue in issues:
        print(f"- {issue.path}")
        for reason in issue.reasons:
            print(f"  - {reason}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate LLM outputs in the lab sidecar.")
    parser.add_argument(
        "--outputs-dir",
        default=str(DEFAULT_OUTPUTS_DIR),
        help=(
            "Path to legacy queue-style outputs directory "
            "(public/data/sec_narrative_drift_lab/llm_outputs)."
        ),
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
        "--debug-citations",
        action="store_true",
        help="Run built-in citation parser self-check and exit.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.debug_citations:
        run_debug_citation_self_check()
        return 0

    bundle_paths = resolve_bundle_paths(
        args.bundle or None,
        args.inputs_index_focuspack or None,
        args.inputs_index_full or None,
        args.prompt_templates or None,
    )
    outputs_dir = Path(args.outputs_dir)
    required_fields = load_required_fields(bundle_paths.prompt_templates)

    issues = validate_outputs(outputs_dir, bundle_paths, required_fields)
    errors, warnings = split_issues(issues)
    if warnings:
        print_issues(f"Validation warnings: {len(warnings)} file(s)", warnings)
        print("")
    if errors:
        print_issues(f"Validation failed: {len(errors)} invalid file(s)", errors)
        return 1

    file_count = len(list(outputs_dir.rglob("*.json"))) if outputs_dir.exists() else 0
    print(f"Validated {file_count} output file(s) OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
