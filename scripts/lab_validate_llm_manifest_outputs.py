from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import sys

from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v5")

REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_OUTPUT_ROOT = (
    REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"
).resolve()
DEFAULT_MANIFEST_PATH = REPO_ROOT / "reports" / "lab_llm_run_manifest.json"
DEFAULT_REPORT_PATH = REPO_ROOT / "reports" / "lab_llm_manifest_validation.md"

REQUIRED_TOP_LEVEL_FIELDS = [
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
REQUIRED_TOP_LEVEL_FIELD_SET = set(REQUIRED_TOP_LEVEL_FIELDS)
EXPECTED_SCHEMA_VERSION = "1.0"

FOCUSPACK_WARNING = "Focuspack is a subset; verify in full compare pane."
ALLOWED_CONFIDENCE: set[float] = {0.25, 0.50, 0.75}
MAX_SNIPPET_CHARS = 350
DELTA_BRIEF_CITATION_RE = re.compile(r"\b(20\d{2})\s+para\s+(\d+)\b", re.IGNORECASE)
FORBIDDEN_CITATION_TOKENS: tuple[tuple[str, str], ...] = (
    ("pilcrow", "\u00b6"),
    ("mojibake_pilcrow_1", "\u00c2\u00b6"),
    ("mojibake_pilcrow_2", "\u00c3\u201a\u00c2\u00b6"),
)
PROVENANCE_REQUIRED = ("input_file", "model_provider", "model_name", "run_label")
PROVENANCE_ALLOWED = set(PROVENANCE_REQUIRED)
EXPECTED_MODEL_PROVIDER = "openai"
EXPECTED_MODEL_NAME = "ChatGPT 5.2-Thinking (Extended Thinking)"
RUN_LABEL_RE = re.compile(r"^20\d{2}-(0[1-9]|1[0-2])_[A-Za-z0-9._-]+$")

sys.path.append(str(Path(__file__).resolve().parent))
from lab_llm_precompute_utils import (  # type: ignore
    as_list,
    as_str_dict,
    get_int,
    get_str,
    read_json,
)
from lab_validate_llm_outputs import build_paragraph_maps, resolve_input_file  # type: ignore


@dataclass(frozen=True)
class ManifestTarget:
    ticker: str
    year_from: int
    year_to: int
    section: str
    lens: str
    detector_id: str
    expected_output_path: str
    manifest_present_flag: Optional[bool]


@dataclass(frozen=True)
class ValidationIssue:
    issue_type: str
    expected_output_path: str
    ticker: str
    year_from: int
    year_to: int
    detector_id: str
    reasons: list[str]


def resolve_expected_output_path(expected_output_path: str) -> tuple[Optional[Path], Optional[str]]:
    raw_path = Path(expected_output_path)
    if raw_path.is_absolute():
        return None, "expected_output_path must be repo-relative, not absolute"
    resolved = (REPO_ROOT / raw_path).resolve()
    try:
        resolved.relative_to(LAB_OUTPUT_ROOT)
    except ValueError:
        return (
            None,
            "expected_output_path resolves outside public/data/sec_narrative_drift_lab",
        )
    if resolved.suffix.lower() != ".json":
        return None, "expected_output_path must point to a .json file"
    return resolved, None


def write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")


def load_manifest_targets(manifest_path: Path) -> list[ManifestTarget]:
    payload = read_json(manifest_path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        raise SystemExit(f"Manifest root is not an object: {manifest_path}")

    entries_raw = as_list(payload_dict.get("entries"))
    if entries_raw is None:
        raise SystemExit(f"Manifest missing list field 'entries': {manifest_path}")

    targets: list[ManifestTarget] = []
    for entry in entries_raw:
        entry_dict = as_str_dict(entry)
        if entry_dict is None:
            continue
        ticker = get_str(entry_dict.get("ticker"))
        year_from = get_int(entry_dict.get("year_from"))
        year_to = get_int(entry_dict.get("year_to"))
        section = get_str(entry_dict.get("section"))
        lens = get_str(entry_dict.get("lens"))
        detectors_raw = as_list(entry_dict.get("detectors"))
        if (
            ticker is None
            or year_from is None
            or year_to is None
            or section is None
            or lens is None
            or detectors_raw is None
        ):
            continue
        for detector in detectors_raw:
            detector_dict = as_str_dict(detector)
            if detector_dict is None:
                continue
            detector_id = get_str(detector_dict.get("detector_id"))
            expected_path = get_str(detector_dict.get("expected_output_path"))
            present_flag_raw = detector_dict.get("present")
            present_flag: Optional[bool] = None
            if isinstance(present_flag_raw, bool):
                present_flag = present_flag_raw
            if detector_id is None or expected_path is None:
                continue
            targets.append(
                ManifestTarget(
                    ticker=ticker,
                    year_from=year_from,
                    year_to=year_to,
                    section=section,
                    lens=lens,
                    detector_id=detector_id,
                    expected_output_path=expected_path,
                    manifest_present_flag=present_flag,
                )
            )
    return targets


def parse_int_list(value: object, field_name: str, reasons: list[str]) -> Optional[list[int]]:
    values_raw = as_list(value)
    if values_raw is None:
        reasons.append(f"{field_name} must be a list")
        return None
    values: list[int] = []
    for idx, item in enumerate(values_raw):
        item_int = get_int(item)
        if item_int is None:
            reasons.append(f"{field_name}[{idx}] must be an int")
            continue
        values.append(item_int)
    return values


def parse_string_list(
    value: object, field_name: str, reasons: list[str]
) -> Optional[list[str]]:
    values_raw = as_list(value)
    if values_raw is None:
        reasons.append(f"{field_name} must be a list")
        return None
    values: list[str] = []
    for idx, item in enumerate(values_raw):
        item_str = get_str(item)
        if item_str is None:
            reasons.append(f"{field_name}[{idx}] must be a string")
            continue
        stripped = item_str.strip()
        if not stripped:
            reasons.append(f"{field_name}[{idx}] must be non-empty")
            continue
        values.append(stripped)
    return values


def _validate_artifact_keys(
    detector_id: str, artifacts: dict[str, object], reasons: list[str]
) -> None:
    expected_keys = (
        {"delta_brief"}
        if detector_id == "det_llm_delta_brief_v1"
        else {"selected_prev", "selected_curr"}
    )
    actual_keys = set(artifacts.keys())
    if actual_keys != expected_keys:
        missing = sorted(expected_keys.difference(actual_keys))
        extra = sorted(actual_keys.difference(expected_keys))
        if missing:
            reasons.append(
                f"artifacts missing key(s): {', '.join(missing)}"
            )
        if extra:
            reasons.append(
                f"artifacts has unexpected key(s): {', '.join(extra)}"
            )


def _validate_provenance_keys(
    provenance: dict[str, object], reasons: list[str]
) -> None:
    keys = set(provenance.keys())
    for key in PROVENANCE_REQUIRED:
        if key not in keys:
            reasons.append(f"provenance missing key: {key}")
    extras = sorted(key for key in keys if key not in PROVENANCE_ALLOWED)
    if extras:
        reasons.append(
            "provenance has unexpected key(s): " + ", ".join(extras)
        )


def _validate_evidence_snippet_mapping(
    target: ManifestTarget,
    provenance_input_file: str,
    output_path: Path,
    evidence_raw: list[object],
    reasons: list[str],
) -> None:
    resolution = resolve_input_file(provenance_input_file, output_path)
    input_path = resolution.path
    if input_path is None:
        reasons.append(
            f"provenance.input_file not resolvable: {resolution.error or provenance_input_file}"
        )
        return

    try:
        input_payload_raw = read_json(input_path)
    except json.JSONDecodeError as exc:
        reasons.append(f"input JSON decode failed for provenance.input_file: {exc}")
        return
    input_payload = as_str_dict(input_payload_raw)
    if input_payload is None:
        reasons.append("input payload root is not an object")
        return
    paragraph_maps = build_paragraph_maps(input_payload)
    if paragraph_maps is None:
        reasons.append("input payload missing paragraph maps/focuspack_meta")
        return

    for idx, entry in enumerate(evidence_raw):
        entry_dict = as_str_dict(entry)
        if entry_dict is None:
            continue
        evidence_year = get_int(entry_dict.get("year"))
        paragraph_idx = get_int(entry_dict.get("paragraph_idx"))
        snippet = get_str(entry_dict.get("snippet"))
        if evidence_year is None or paragraph_idx is None or snippet is None:
            continue
        if evidence_year == target.year_from:
            paragraph_text = paragraph_maps.prev_map.get(paragraph_idx)
        elif evidence_year == target.year_to:
            paragraph_text = paragraph_maps.curr_map.get(paragraph_idx)
        else:
            continue
        if paragraph_text is None:
            reasons.append(
                f"evidence[{idx}] paragraph_idx {paragraph_idx} not found in mapped FULL indices for year {evidence_year}"
            )
            continue
        if snippet not in paragraph_text:
            reasons.append(
                f"evidence[{idx}] snippet is not a verbatim substring of mapped paragraph"
            )


def validate_output_json(target: ManifestTarget, output_path: Path) -> list[str]:
    reasons: list[str] = []
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        reasons.append(f"invalid JSON: {exc}")
        return reasons

    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        reasons.append("JSON root is not an object")
        return reasons

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in payload_dict:
            reasons.append(f"missing top-level field: {field}")
    extra_fields = [field for field in payload_dict.keys() if field not in REQUIRED_TOP_LEVEL_FIELD_SET]
    if extra_fields:
        reasons.append(
            "unexpected top-level field(s): " + ", ".join(sorted(extra_fields))
        )

    schema_version = get_str(payload_dict.get("lab_schema_version"))
    if schema_version != EXPECTED_SCHEMA_VERSION:
        reasons.append(
            f"lab_schema_version mismatch: got {schema_version!r}, expected {EXPECTED_SCHEMA_VERSION!r}"
        )

    detector_id = get_str(payload_dict.get("detector_id"))
    if detector_id != target.detector_id:
        reasons.append(
            f"detector_id mismatch: got {detector_id!r}, expected {target.detector_id!r}"
        )

    cleaning_lens = get_str(payload_dict.get("cleaning_lens"))
    if cleaning_lens != target.lens:
        reasons.append(
            f"cleaning_lens mismatch: got {cleaning_lens!r}, expected {target.lens!r}"
        )

    ticker = get_str(payload_dict.get("ticker"))
    if ticker is None or ticker.upper() != target.ticker.upper():
        reasons.append(f"ticker mismatch: got {ticker!r}, expected {target.ticker!r}")

    section = get_str(payload_dict.get("section"))
    if section != target.section:
        reasons.append(f"section mismatch: got {section!r}, expected {target.section!r}")

    year_from = get_int(payload_dict.get("year_from"))
    year_to = get_int(payload_dict.get("year_to"))
    if year_from != target.year_from:
        reasons.append(
            f"year_from mismatch: got {year_from!r}, expected {target.year_from!r}"
        )
    if year_to != target.year_to:
        reasons.append(f"year_to mismatch: got {year_to!r}, expected {target.year_to!r}")

    artifacts = as_str_dict(payload_dict.get("artifacts"))
    if artifacts is None:
        reasons.append("artifacts must be an object")
        artifacts = {}
    _validate_artifact_keys(target.detector_id, artifacts, reasons)

    evidence_raw = as_list(payload_dict.get("evidence"))
    evidence_prev_indices: list[int] = []
    evidence_curr_indices: list[int] = []
    if evidence_raw is None:
        reasons.append("evidence must be a list")
        evidence_raw = []
    else:
        seen_prev: set[int] = set()
        seen_curr: set[int] = set()
        for idx, entry in enumerate(evidence_raw):
            entry_dict = as_str_dict(entry)
            if entry_dict is None:
                reasons.append(f"evidence[{idx}] must be an object")
                continue

            evidence_year = get_int(entry_dict.get("year"))
            if evidence_year is None:
                reasons.append(f"evidence[{idx}].year must be an int")
            elif evidence_year not in (target.year_from, target.year_to):
                reasons.append(
                    f"evidence[{idx}].year must be {target.year_from} or {target.year_to}"
                )

            paragraph_idx = get_int(entry_dict.get("paragraph_idx"))
            if paragraph_idx is None:
                reasons.append(f"evidence[{idx}].paragraph_idx must be an int")
            elif paragraph_idx < 0:
                reasons.append(f"evidence[{idx}].paragraph_idx must be >= 0")

            snippet = get_str(entry_dict.get("snippet"))
            if snippet is None or not snippet.strip():
                reasons.append(f"evidence[{idx}].snippet must be a non-empty string")
            elif len(snippet) > MAX_SNIPPET_CHARS:
                reasons.append(
                    f"evidence[{idx}].snippet length must be <= {MAX_SNIPPET_CHARS}"
                )

            why = get_str(entry_dict.get("why"))
            if why is None or not why.strip():
                reasons.append(f"evidence[{idx}].why must be a non-empty string")

            highlights = parse_string_list(
                entry_dict.get("highlights"), f"evidence[{idx}].highlights", reasons
            )
            if highlights is not None and len(highlights) < 1:
                reasons.append(f"evidence[{idx}].highlights must include at least one value")

            if evidence_year == target.year_from and paragraph_idx is not None and paragraph_idx >= 0:
                if paragraph_idx not in seen_prev:
                    seen_prev.add(paragraph_idx)
                    evidence_prev_indices.append(paragraph_idx)
            if evidence_year == target.year_to and paragraph_idx is not None and paragraph_idx >= 0:
                if paragraph_idx not in seen_curr:
                    seen_curr.add(paragraph_idx)
                    evidence_curr_indices.append(paragraph_idx)

        if len(evidence_prev_indices) < 1:
            reasons.append("evidence must include at least one block for year_from")
        if len(evidence_curr_indices) < 1:
            reasons.append("evidence must include at least one block for year_to")

    metrics = as_str_dict(payload_dict.get("metrics"))
    if metrics is None:
        reasons.append("metrics must be an object")
        metrics = {}
    confidence_raw = metrics.get("confidence")
    if confidence_raw is None:
        reasons.append("metrics.confidence is required")
    elif isinstance(confidence_raw, bool) or not isinstance(confidence_raw, (int, float)):
        reasons.append("metrics.confidence must be numeric")
    else:
        confidence_value = float(confidence_raw)
        if confidence_value not in ALLOWED_CONFIDENCE:
            reasons.append(
                f"metrics.confidence must be one of {sorted(ALLOWED_CONFIDENCE)}"
            )

    warning_values = parse_string_list(metrics.get("warnings"), "metrics.warnings", reasons)
    if warning_values is not None and FOCUSPACK_WARNING not in warning_values:
        reasons.append(f'metrics.warnings must include "{FOCUSPACK_WARNING}"')

    provenance = as_str_dict(payload_dict.get("provenance"))
    provenance_input_file = ""
    if provenance is None:
        reasons.append("provenance must be an object")
    else:
        _validate_provenance_keys(provenance, reasons)
        input_file = get_str(provenance.get("input_file"))
        if input_file is None or not input_file.strip():
            reasons.append("provenance.input_file must be a non-empty string")
        else:
            provenance_input_file = input_file
            expected_input_file = (
                f"inputs/{target.ticker}_{target.year_from}_{target.year_to}_focuspack_{target.lens}.json"
            )
            if input_file != expected_input_file:
                reasons.append(
                    "provenance.input_file mismatch: "
                    + f"got {input_file!r}, expected {expected_input_file!r}"
                )
        model_provider = get_str(provenance.get("model_provider"))
        if model_provider is None or not model_provider.strip():
            reasons.append("provenance.model_provider must be a non-empty string")
        elif model_provider != EXPECTED_MODEL_PROVIDER:
            reasons.append(
                "provenance.model_provider must be exactly "
                + f"{EXPECTED_MODEL_PROVIDER!r}, got {model_provider!r}"
            )
        model_name = get_str(provenance.get("model_name"))
        if model_name is None or not model_name.strip():
            reasons.append("provenance.model_name must be a non-empty string")
        elif model_name != EXPECTED_MODEL_NAME:
            reasons.append(
                "provenance.model_name must be exactly "
                + f"{EXPECTED_MODEL_NAME!r}, got {model_name!r}"
            )
        run_label = get_str(provenance.get("run_label"))
        if run_label is None or not run_label.strip():
            reasons.append("provenance.run_label must be a non-empty string")
        elif RUN_LABEL_RE.fullmatch(run_label) is None:
            reasons.append(
                "provenance.run_label must match YYYY-MM_<campaign_tag> "
                + f"(regex={RUN_LABEL_RE.pattern})"
            )

    if provenance_input_file:
        _validate_evidence_snippet_mapping(
            target=target,
            provenance_input_file=provenance_input_file,
            output_path=output_path,
            evidence_raw=evidence_raw,
            reasons=reasons,
        )

    if target.detector_id == "det_llm_delta_brief_v1":
        delta_brief = get_str(artifacts.get("delta_brief"))
        if delta_brief is None or not delta_brief.strip():
            reasons.append("artifacts.delta_brief must be a non-empty string")
        else:
            for token_name, token_value in FORBIDDEN_CITATION_TOKENS:
                if token_value in delta_brief:
                    reasons.append(
                        "delta_brief contains forbidden pilcrow-style citation token: "
                        + token_name
                    )
            citation_matches = DELTA_BRIEF_CITATION_RE.findall(delta_brief)
            if len(citation_matches) < 2:
                reasons.append(
                    'delta_brief must include >=2 inline citations in "YYYY para NN" format'
                )
            else:
                for year_text, para_text in citation_matches:
                    year_val = int(year_text)
                    para_val = int(para_text)
                    if year_val not in (target.year_from, target.year_to):
                        reasons.append(
                            f'delta_brief citation year must be {target.year_from} or {target.year_to}, got {year_val}'
                        )
                    if para_val < 1:
                        reasons.append(
                            f'delta_brief citation paragraph number must be >=1, got {para_val}'
                        )

    if target.detector_id == "det_llm_excerpt_picker_v1":
        selected_prev = parse_int_list(
            artifacts.get("selected_prev"), "artifacts.selected_prev", reasons
        )
        selected_curr = parse_int_list(
            artifacts.get("selected_curr"), "artifacts.selected_curr", reasons
        )
        if selected_prev is not None:
            if len(selected_prev) != len(set(selected_prev)):
                reasons.append("artifacts.selected_prev must not contain duplicates")
            for idx, value in enumerate(selected_prev):
                if value < 0:
                    reasons.append(f"artifacts.selected_prev[{idx}] must be >= 0")
        if selected_curr is not None:
            if len(selected_curr) != len(set(selected_curr)):
                reasons.append("artifacts.selected_curr must not contain duplicates")
            for idx, value in enumerate(selected_curr):
                if value < 0:
                    reasons.append(f"artifacts.selected_curr[{idx}] must be >= 0")

        if selected_prev is not None and evidence_prev_indices:
            selected_prev_set = set(selected_prev)
            missing_prev = [
                idx for idx in evidence_prev_indices if idx not in selected_prev_set
            ]
            if missing_prev:
                reasons.append(
                    "artifacts.selected_prev missing evidence paragraph_idx values: "
                    + ", ".join(str(idx) for idx in missing_prev)
                )
        if selected_curr is not None and evidence_curr_indices:
            selected_curr_set = set(selected_curr)
            missing_curr = [
                idx for idx in evidence_curr_indices if idx not in selected_curr_set
            ]
            if missing_curr:
                reasons.append(
                    "artifacts.selected_curr missing evidence paragraph_idx values: "
                    + ", ".join(str(idx) for idx in missing_curr)
                )

    return reasons


def validate_targets(
    targets: list[ManifestTarget],
) -> tuple[list[ValidationIssue], list[ValidationIssue], list[ValidationIssue]]:
    missing: list[ValidationIssue] = []
    invalid: list[ValidationIssue] = []
    manifest_mismatch: list[ValidationIssue] = []

    for target in targets:
        expected_abs, expected_path_error = resolve_expected_output_path(
            target.expected_output_path
        )
        if expected_path_error is not None or expected_abs is None:
            invalid.append(
                ValidationIssue(
                    issue_type="invalid_expected_path",
                    expected_output_path=target.expected_output_path,
                    ticker=target.ticker,
                    year_from=target.year_from,
                    year_to=target.year_to,
                    detector_id=target.detector_id,
                    reasons=[expected_path_error or "invalid expected path"],
                )
            )
            continue
        exists_now = expected_abs.exists()

        if (
            target.manifest_present_flag is not None
            and target.manifest_present_flag != exists_now
        ):
            manifest_mismatch.append(
                ValidationIssue(
                    issue_type="manifest_present_mismatch",
                    expected_output_path=target.expected_output_path,
                    ticker=target.ticker,
                    year_from=target.year_from,
                    year_to=target.year_to,
                    detector_id=target.detector_id,
                    reasons=[
                        "manifest 'present' flag does not match filesystem state",
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
                    detector_id=target.detector_id,
                    reasons=["file not found"],
                )
            )
            continue

        reasons = validate_output_json(target, expected_abs)
        if reasons:
            invalid.append(
                ValidationIssue(
                    issue_type="invalid",
                    expected_output_path=target.expected_output_path,
                    ticker=target.ticker,
                    year_from=target.year_from,
                    year_to=target.year_to,
                    detector_id=target.detector_id,
                    reasons=reasons,
                )
            )

    return missing, invalid, manifest_mismatch


def issue_lines(issues: list[ValidationIssue]) -> list[str]:
    lines: list[str] = []
    for issue in issues:
        pair_label = f"{issue.year_from}-{issue.year_to}"
        lines.append(
            f"- {issue.ticker} {pair_label} {issue.detector_id}: {issue.expected_output_path}"
        )
        for reason in issue.reasons:
            lines.append(f"  - {reason}")
    if not lines:
        lines.append("- none")
    return lines


def build_report(
    manifest_path: Path,
    target_count: int,
    missing: list[ValidationIssue],
    invalid: list[ValidationIssue],
    manifest_mismatch: list[ValidationIssue],
) -> list[str]:
    lines: list[str] = []
    lines.append("# LLM Manifest Validation")
    lines.append("")
    lines.append(f"Manifest: {manifest_path.as_posix()}")
    lines.append(f"Script: {SCRIPT_VERSION}")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| Targets | {target_count} |")
    lines.append(f"| Missing files | {len(missing)} |")
    lines.append(f"| Invalid files | {len(invalid)} |")
    lines.append(f"| Present-flag mismatches | {len(manifest_mismatch)} |")
    lines.append("")
    lines.append("## Missing Outputs")
    lines.extend(issue_lines(missing))
    lines.append("")
    lines.append("## Invalid Outputs")
    lines.extend(issue_lines(invalid))
    lines.append("")
    lines.append("## Manifest Present-Flag Mismatches")
    lines.extend(issue_lines(manifest_mismatch))
    return lines


def _parse_only_filter(value: str) -> list[str]:
    parts = [token.strip() for token in value.split(",")]
    return [token for token in parts if token]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate LLM outputs referenced by reports/lab_llm_run_manifest.json."
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST_PATH),
        help="Path to reports/lab_llm_run_manifest.json",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT_PATH),
        help="Write markdown validation report to this path.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Return success even when manifest targets are missing.",
    )
    parser.add_argument(
        "--allow-invalid",
        action="store_true",
        help="Return success even when manifest targets are invalid.",
    )
    parser.add_argument(
        "--only",
        default="",
        help="Comma-separated filter tokens; validate only targets whose expected path contains one token.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")

    targets = load_manifest_targets(manifest_path)
    only_filters = _parse_only_filter(args.only)
    if only_filters:
        filtered_targets: list[ManifestTarget] = []
        for target in targets:
            if any(token in target.expected_output_path for token in only_filters):
                filtered_targets.append(target)
        targets = filtered_targets

    missing, invalid, manifest_mismatch = validate_targets(targets)

    report_lines = build_report(
        manifest_path=manifest_path,
        target_count=len(targets),
        missing=missing,
        invalid=invalid,
        manifest_mismatch=manifest_mismatch,
    )
    write_text(Path(args.report), report_lines)

    print(
        "Manifest validation summary: "
        + f"targets={len(targets)}, missing={len(missing)}, "
        + f"invalid={len(invalid)}, present_flag_mismatch={len(manifest_mismatch)}"
    )
    if missing:
        print("Missing outputs:")
        for line in issue_lines(missing):
            print(line)
    if invalid:
        print("Invalid outputs:")
        for line in issue_lines(invalid):
            print(line)
    if manifest_mismatch:
        print("Manifest present-flag mismatches:")
        for line in issue_lines(manifest_mismatch):
            print(line)
    print(f"Wrote validation report: {args.report}")

    if invalid and not args.allow_invalid:
        return 1
    if missing and not args.allow_missing:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
