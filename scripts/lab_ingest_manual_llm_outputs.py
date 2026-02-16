from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, cast

import sys

SCRIPT_VERSION = "lab_ingest_manual_llm_outputs.py@v2"

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_OUTPUTS_ROOT_REL = "public/data/sec_narrative_drift_lab/llm_outputs"
PUBLIC_INPUTS_ROOT_REL = "public/data/sec_narrative_drift_lab/llm_inputs"
PUBLIC_LAB_ROOT_REL = "public/data/sec_narrative_drift_lab"
PROVENANCE_NORMALIZED_WARNING_TEMPLATE = (
    "Normalized provenance.input_file to llm_inputs/{ticker}/{basename} for UI lookup."
)
MAX_SNIPPET_CHARS = 350

sys.path.append(str(Path(__file__).resolve().parent))
from lab_llm_precompute_utils import (  # type: ignore
    as_list,
    as_str_dict,
    get_int,
    get_str,
    read_json,
    resolve_bundle_paths,
    to_repo_relative,
)
from lab_validate_llm_outputs import (  # type: ignore
    ValidationIssue,
    load_required_fields,
    split_issues,
    validate_outputs,
)

try:
    from lab_reconcile_llm_evidence import reconcile_file  # type: ignore

    _reconcile_available = True
except Exception:
    reconcile_file = None  # type: ignore[assignment]
    _reconcile_available = False


@dataclass(frozen=True)
class QueueTarget:
    job_id: str
    ticker: str
    detector_id: str
    year_from: int
    year_to: int
    input_path: str
    output_path: str


@dataclass(frozen=True)
class OutputIdentity:
    ticker: str
    detector_id: str
    year_from: int
    year_to: int


@dataclass
class ProcessingItem:
    target: QueueTarget
    source_output: Path
    temp_output: Path
    safe_input_member: str
    safe_output_rel: str


def normalize_ticker_symbol(ticker_value: str) -> Optional[str]:
    normalized = ticker_value.strip().upper()
    if not normalized:
        return None
    for char in normalized:
        if char.isalnum():
            continue
        if char in ["_", "-"]:
            continue
        return None
    return normalized


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest manual LLM UI outputs from a showcase queue zip deterministically."
    )
    parser.add_argument(
        "--queue-bundle",
        required=True,
        help="Path to chatgpt_bundle_showcase_llm_queue_<timestamp>.zip",
    )
    parser.add_argument(
        "--outputs-dir",
        required=True,
        help="Directory containing manually collected output JSON files.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write files to repo paths. Default is dry-run.",
    )
    return parser


def normalize_rel_path(path_value: str) -> Optional[str]:
    normalized = path_value.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        return None
    if normalized.startswith("/"):
        return None
    if len(normalized) >= 2 and normalized[1] == ":":
        return None
    parts = normalized.split("/")
    clean_parts: list[str] = []
    for part in parts:
        if not part or part == ".":
            continue
        if part == "..":
            return None
        clean_parts.append(part)
    if not clean_parts:
        return None
    return "/".join(clean_parts)


def ensure_safe_repo_rel(path_value: str, required_prefix: str) -> str:
    normalized = normalize_rel_path(path_value)
    if normalized is None:
        raise SystemExit(f"Unsafe repo-relative path: {path_value}")
    prefix = required_prefix.rstrip("/")
    if not normalized.startswith(f"{prefix}/"):
        raise SystemExit(
            f"Unexpected target path '{normalized}' (must start with '{prefix}/')."
        )
    return normalized


def ensure_safe_zip_member(path_value: str, required_prefix: str) -> str:
    normalized = normalize_rel_path(path_value)
    if normalized is None:
        raise SystemExit(f"Unsafe queue input path in output_targets.jsonl: {path_value}")
    prefix = required_prefix.rstrip("/")
    if not normalized.startswith(f"{prefix}/"):
        raise SystemExit(
            f"Unexpected queue input path '{normalized}' (must start with '{prefix}/')."
        )
    return normalized


def load_jsonl_from_zip(zip_handle: zipfile.ZipFile, member_name: str) -> list[dict[str, Any]]:
    try:
        payload = zip_handle.read(member_name)
    except KeyError:
        raise SystemExit(f"Missing '{member_name}' in queue bundle zip.")
    lines = payload.decode("utf-8-sig").splitlines()
    rows: list[dict[str, Any]] = []
    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue
        data = json.loads(trimmed)
        row = as_str_dict(data)
        if row is None:
            raise SystemExit(f"Invalid JSON object in '{member_name}'.")
        rows.append(row)
    return rows


def parse_queue_targets(rows: list[dict[str, Any]]) -> list[QueueTarget]:
    targets: list[QueueTarget] = []
    for idx, row in enumerate(rows):
        job_id = get_str(row.get("job_id"))
        ticker = get_str(row.get("ticker"))
        detector_id = get_str(row.get("detector_id"))
        year_from = get_int(row.get("year_from"))
        year_to = get_int(row.get("year_to"))
        input_path = get_str(row.get("input_path"))
        output_path = get_str(row.get("output_path"))
        if (
            job_id is None
            or ticker is None
            or detector_id is None
            or year_from is None
            or year_to is None
            or input_path is None
            or output_path is None
        ):
            raise SystemExit(
                f"output_targets.jsonl row {idx} missing required keys."
            )
        targets.append(
            QueueTarget(
                job_id=job_id,
                ticker=ticker,
                detector_id=detector_id,
                year_from=year_from,
                year_to=year_to,
                input_path=input_path,
                output_path=output_path,
            )
        )
    return targets


def infer_bundle_root_from_jobs(rows: list[dict[str, Any]]) -> Optional[str]:
    roots: list[str] = []
    for row in rows:
        bundle_root = get_str(row.get("bundle_root"))
        if bundle_root is None:
            continue
        normalized = normalize_rel_path(bundle_root)
        if normalized is None:
            continue
        if normalized not in roots:
            roots.append(normalized)
    if not roots:
        return None
    if len(roots) > 1:
        raise SystemExit(
            "Queue jobs.jsonl has multiple bundle_root values; ingestion requires one deterministic source."
        )
    candidate = REPO_ROOT / roots[0]
    if candidate.exists() and candidate.is_dir():
        return roots[0]
    return None


def build_output_filename_index(outputs_dir: Path) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    if not outputs_dir.exists():
        return index
    for path in sorted(outputs_dir.rglob("*.json")):
        bucket = index.setdefault(path.name, [])
        bucket.append(path)
    return index


def read_output_identity(path: Path) -> Optional[OutputIdentity]:
    try:
        payload = read_json(path)
    except json.JSONDecodeError:
        return None
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        return None
    ticker = get_str(payload_dict.get("ticker"))
    detector_id = get_str(payload_dict.get("detector_id"))
    year_from = get_int(payload_dict.get("year_from"))
    year_to = get_int(payload_dict.get("year_to"))
    if (
        ticker is None
        or detector_id is None
        or year_from is None
        or year_to is None
    ):
        return None
    return OutputIdentity(
        ticker=ticker,
        detector_id=detector_id,
        year_from=year_from,
        year_to=year_to,
    )


def choose_source_output(
    target: QueueTarget,
    matches: list[Path],
    identity_cache: dict[Path, Optional[OutputIdentity]],
) -> tuple[Optional[Path], Optional[str]]:
    if not matches:
        return None, "missing"

    meta_matches: list[Path] = []
    for candidate in matches:
        if candidate not in identity_cache:
            identity_cache[candidate] = read_output_identity(candidate)
        identity = identity_cache[candidate]
        if identity is None:
            continue
        if (
            identity.ticker.upper() == target.ticker.upper()
            and identity.detector_id == target.detector_id
            and identity.year_from == target.year_from
            and identity.year_to == target.year_to
        ):
            meta_matches.append(candidate)

    if len(meta_matches) == 1:
        return meta_matches[0], None
    if len(meta_matches) > 1:
        details = ", ".join(str(path) for path in meta_matches)
        return None, f"ambiguous metadata match: {details}"
    return None, "missing metadata match"


def sha256_bytes(payload: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(payload)
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def sync_input_bytes(
    input_bytes: bytes,
    input_dest_abs: Path,
    input_dest_rel: str,
    apply_changes: bool,
) -> tuple[str, bool]:
    if input_dest_abs.exists():
        src_hash = sha256_bytes(input_bytes)
        dst_hash = sha256_file(input_dest_abs)
        if src_hash != dst_hash:
            raise SystemExit(
                "Input sync conflict for "
                + f"{input_dest_rel}: existing hash {dst_hash} != queue hash {src_hash}"
            )
        return "existing_identical", False

    if apply_changes:
        input_dest_abs.parent.mkdir(parents=True, exist_ok=True)
        input_dest_abs.write_bytes(input_bytes)
        return "copied", True

    return "would_copy", True


def normalize_optional_provenance_path(path_value: Optional[str]) -> Optional[str]:
    if path_value is None:
        return None
    return normalize_rel_path(path_value)


def normalize_warning_list(values: list[Any]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for entry in values:
        if not isinstance(entry, str):
            continue
        trimmed = entry.strip()
        if not trimmed:
            continue
        if trimmed in seen:
            continue
        seen.add(trimmed)
        normalized.append(trimmed)
    return normalized


def is_nonfatal_pre_ingest_reason(reason: str) -> bool:
    nonfatal_prefixes = [
        "provenance.input_file not found",
        "provenance.input_file ambiguous for",
        "provenance.input_file missing focuspack texts/meta",
    ]
    for prefix in nonfatal_prefixes:
        if reason.startswith(prefix):
            return True
    return False


def build_validation_error_map(errors: list[ValidationIssue]) -> dict[Path, list[str]]:
    mapping: dict[Path, list[str]] = {}
    for issue in errors:
        fatal_reasons: list[str] = []
        for reason in issue.reasons:
            if is_nonfatal_pre_ingest_reason(reason):
                continue
            fatal_reasons.append(reason)
        if fatal_reasons:
            mapping[issue.path.resolve()] = fatal_reasons
    return mapping


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    queue_bundle = Path(args.queue_bundle)
    outputs_dir = Path(args.outputs_dir)
    apply_changes = bool(args.apply)

    if not queue_bundle.exists() or not queue_bundle.is_file():
        raise SystemExit(f"Queue bundle zip not found: {queue_bundle}")
    if not outputs_dir.exists() or not outputs_dir.is_dir():
        raise SystemExit(f"Outputs directory not found: {outputs_dir}")

    with zipfile.ZipFile(queue_bundle, "r") as queue_zip:
        output_target_rows = load_jsonl_from_zip(queue_zip, "output_targets.jsonl")
        targets = parse_queue_targets(output_target_rows)
        jobs_rows = load_jsonl_from_zip(queue_zip, "jobs.jsonl")
        bundle_root = infer_bundle_root_from_jobs(jobs_rows)

        bundle_paths = resolve_bundle_paths(bundle_root, None, None, None)
        required_fields = load_required_fields(bundle_paths.prompt_templates)

        output_by_name = build_output_filename_index(outputs_dir)
        identity_cache: dict[Path, Optional[OutputIdentity]] = {}
        items: list[ProcessingItem] = []
        missing_count = 0
        failed_count = 0

        tmp_root = REPO_ROOT / "reports" / "_tmp_ingest_manual"
        tmp_root.mkdir(parents=True, exist_ok=True)
        tmp_outputs_dir = tmp_root / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        if tmp_outputs_dir.exists():
            shutil.rmtree(tmp_outputs_dir, ignore_errors=True)
        tmp_outputs_dir.mkdir(parents=True, exist_ok=True)
        try:
            for target in targets:
                output_rel = ensure_safe_repo_rel(
                    target.output_path, PUBLIC_OUTPUTS_ROOT_REL
                )
                input_member = ensure_safe_zip_member(target.input_path, "inputs")
                output_name = Path(output_rel).name
                matches = output_by_name.get(output_name, [])
                if not matches:
                    missing_count += 1
                    print(f"WARN: missing output file for target '{target.job_id}' ({output_name})")
                    continue

                source_output, select_error = choose_source_output(
                    target, matches, identity_cache
                )
                if source_output is None and select_error == "missing metadata match":
                    missing_count += 1
                    print(
                        "WARN: missing output file for target "
                        + f"'{target.job_id}' ({output_name}) after metadata match."
                    )
                    continue
                if source_output is None:
                    failed_count += 1
                    print(
                        "FAIL: could not resolve output file for "
                        + f"'{target.job_id}' ({output_name}): {select_error}"
                    )
                    continue

                relative_under_outputs = output_rel[len(PUBLIC_OUTPUTS_ROOT_REL) + 1 :]
                temp_path = tmp_outputs_dir / relative_under_outputs
                temp_path.parent.mkdir(parents=True, exist_ok=True)
                temp_path.write_bytes(source_output.read_bytes())
                items.append(
                    ProcessingItem(
                        target=target,
                        source_output=source_output,
                        temp_output=temp_path,
                        safe_input_member=input_member,
                        safe_output_rel=output_rel,
                    )
                )

            issues = validate_outputs(tmp_outputs_dir, bundle_paths, required_fields)
            errors, warnings = split_issues(issues)
            if warnings:
                print(f"WARN: validator produced {len(warnings)} warning file(s).")
            validation_error_map = build_validation_error_map(errors)

            written_count = 0
            reconciled_count = 0
            input_synced_count = 0
            input_sync_existing_count = 0
            input_alias_written_count = 0
            ticker_output_written_count = 0

            for item in items:
                temp_path = item.temp_output.resolve()
                if temp_path in validation_error_map:
                    failed_count += 1
                    reasons = "; ".join(validation_error_map[temp_path])
                    print(f"FAIL: validator errors for {item.target.job_id}: {reasons}")
                    continue

                payload = read_json(item.temp_output)
                payload_dict = as_str_dict(payload)
                if payload_dict is None:
                    failed_count += 1
                    print(f"FAIL: payload root is not an object for {item.target.job_id}")
                    continue

                queue_basename = Path(item.safe_input_member).name
                target_ticker = normalize_ticker_symbol(item.target.ticker)
                if target_ticker is None:
                    failed_count += 1
                    print(
                        "FAIL: invalid queue ticker for "
                        + f"{item.target.job_id}: {item.target.ticker}"
                    )
                    continue

                payload_ticker_raw = get_str(payload_dict.get("ticker"))
                payload_ticker = (
                    normalize_ticker_symbol(payload_ticker_raw)
                    if payload_ticker_raw is not None
                    else None
                )
                if payload_ticker_raw is not None and payload_ticker is None:
                    failed_count += 1
                    print(
                        "FAIL: invalid payload ticker for "
                        + f"{item.target.job_id}: {payload_ticker_raw}"
                    )
                    continue
                if payload_ticker is not None and payload_ticker != target_ticker:
                    failed_count += 1
                    print(
                        "FAIL: payload/queue ticker mismatch for "
                        + f"{item.target.job_id}: payload '{payload_ticker}' != queue '{target_ticker}'"
                    )
                    continue

                sync_ticker = payload_ticker if payload_ticker is not None else target_ticker

                try:
                    input_bytes = queue_zip.read(item.safe_input_member)
                except KeyError:
                    failed_count += 1
                    print(
                        "FAIL: queue bundle missing input member for "
                        + f"{item.target.job_id}: {item.safe_input_member}"
                    )
                    continue

                provenance = as_str_dict(payload_dict.get("provenance")) or {}

                provenance_input_raw = get_str(provenance.get("input_file"))
                provenance_before = (
                    provenance_input_raw.strip() if provenance_input_raw is not None else ""
                )
                provenance_basename: Optional[str] = None
                if provenance_input_raw is not None and provenance_input_raw.strip():
                    provenance_basename = Path(
                        provenance_input_raw.replace("\\", "/")
                    ).name
                    if not provenance_basename or not provenance_basename.lower().endswith(".json"):
                        failed_count += 1
                        print(
                            "FAIL: invalid provenance.input_file basename for "
                            + f"{item.target.job_id}: {provenance_input_raw}"
                        )
                        continue

                if provenance_basename is not None and provenance_basename != queue_basename:
                    failed_count += 1
                    print(
                        "FAIL: provenance/input mismatch for "
                        + f"{item.target.job_id}: provenance basename '{provenance_basename}' "
                        + f"!= queue input basename '{queue_basename}'"
                    )
                    continue

                input_dest_rel = f"{PUBLIC_INPUTS_ROOT_REL}/{sync_ticker}/{queue_basename}"
                input_dest_abs = REPO_ROOT / input_dest_rel
                input_sync_status, input_dest_new = sync_input_bytes(
                    input_bytes, input_dest_abs, input_dest_rel, apply_changes
                )
                if input_dest_new:
                    input_synced_count += 1
                elif input_sync_status == "existing_identical":
                    input_sync_existing_count += 1

                alias_sync_status: Optional[str] = None
                alias_dest_rel: Optional[str] = None
                normalized_old_provenance = normalize_optional_provenance_path(provenance_input_raw)
                old_flat_candidate = f"llm_inputs/{queue_basename}"
                if normalized_old_provenance == old_flat_candidate:
                    alias_dest_rel = f"{PUBLIC_INPUTS_ROOT_REL}/{queue_basename}"
                    alias_dest_abs = REPO_ROOT / alias_dest_rel
                    alias_sync_status, alias_is_new = sync_input_bytes(
                        input_bytes, alias_dest_abs, alias_dest_rel, apply_changes
                    )
                    if alias_is_new:
                        input_alias_written_count += 1

                normalized_provenance = f"llm_inputs/{sync_ticker}/{queue_basename}"
                provenance["input_file"] = normalized_provenance
                provenance_normalized = provenance_before != normalized_provenance
                payload_dict["provenance"] = provenance
                item.temp_output.write_text(
                    json.dumps(payload_dict, indent=2) + "\n", encoding="utf-8"
                )

                old_display = provenance_before if provenance_before else "<missing>"
                sync_state = (
                    "already_existed"
                    if input_sync_status == "existing_identical"
                    else input_sync_status
                )
                print(
                    "INFO: input_sync "
                    + f"{item.target.job_id}: dest='{input_dest_rel}' status={sync_state}"
                )
                if alias_sync_status is not None and alias_dest_rel is not None:
                    alias_state = (
                        "already_existed"
                        if alias_sync_status == "existing_identical"
                        else alias_sync_status
                    )
                    print(
                        "INFO: input_sync_alias "
                        + f"{item.target.job_id}: dest='{alias_dest_rel}' status={alias_state}"
                    )
                print(
                    "INFO: provenance_rewrite "
                    + f"{item.target.job_id}: '{old_display}' -> '{normalized_provenance}'"
                )

                if _reconcile_available and reconcile_file is not None:
                    reconcile_result = cast(
                        dict[str, Any],
                        reconcile_file(item.temp_output, "in_place", MAX_SNIPPET_CHARS),
                    )
                    reconcile_errors_raw = as_list(reconcile_result.get("errors"))
                    reconcile_errors: list[str] = []
                    if reconcile_errors_raw is not None:
                        for entry in reconcile_errors_raw:
                            if isinstance(entry, str):
                                reconcile_errors.append(entry)
                    if reconcile_errors:
                        nonfatal_dry_run = (
                            not apply_changes
                            and all(is_nonfatal_pre_ingest_reason(entry) for entry in reconcile_errors)
                        )
                        if nonfatal_dry_run:
                            detail = "; ".join(reconcile_errors)
                            print(
                                "WARN: reconcile skipped in dry-run for "
                                + f"{item.target.job_id}: {detail}"
                            )
                        else:
                            failed_count += 1
                            detail = "; ".join(reconcile_errors)
                            print(f"FAIL: reconcile errors for {item.target.job_id}: {detail}")
                            continue
                    else:
                        corrected_total = (
                            int(reconcile_result.get("paragraph_idx_corrected", 0))
                            + int(reconcile_result.get("snippets_trimmed", 0))
                            + int(reconcile_result.get("input_file_inferred", 0))
                        )
                        if corrected_total > 0:
                            reconciled_count += 1

                payload_after_reconcile = read_json(item.temp_output)
                payload_after_reconcile_dict = as_str_dict(payload_after_reconcile)
                if payload_after_reconcile_dict is None:
                    failed_count += 1
                    print(f"FAIL: payload root became invalid for {item.target.job_id}")
                    continue
                metrics_after = as_str_dict(payload_after_reconcile_dict.get("metrics")) or {}
                warnings_after = normalize_warning_list(as_list(metrics_after.get("warnings")) or [])
                if provenance_normalized:
                    warning_value = PROVENANCE_NORMALIZED_WARNING_TEMPLATE.format(
                        ticker=sync_ticker,
                        basename=queue_basename
                    )
                    if warning_value not in warnings_after:
                        warnings_after.append(warning_value)
                metrics_after["warnings"] = normalize_warning_list(warnings_after)
                payload_after_reconcile_dict["metrics"] = metrics_after
                payload_after_reconcile_dict["provenance"] = provenance

                output_dest_abs = REPO_ROOT / item.safe_output_rel
                ticker_output_rel_raw = (
                    f"{PUBLIC_LAB_ROOT_REL}/{sync_ticker}/outputs/{item.target.detector_id}/"
                    + Path(item.safe_output_rel).name
                )
                ticker_output_rel = ensure_safe_repo_rel(
                    ticker_output_rel_raw, PUBLIC_LAB_ROOT_REL
                )
                ticker_output_abs = REPO_ROOT / ticker_output_rel
                if apply_changes:
                    output_dest_abs.parent.mkdir(parents=True, exist_ok=True)
                    output_dest_abs.write_text(
                        json.dumps(payload_after_reconcile_dict, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    ticker_output_abs.parent.mkdir(parents=True, exist_ok=True)
                    ticker_output_abs.write_text(
                        json.dumps(payload_after_reconcile_dict, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    ticker_output_written_count += 1
                else:
                    print(
                        "INFO: ticker_output_sync "
                        + f"{item.target.job_id}: would_write='{ticker_output_rel}'"
                    )
                written_count += 1
        finally:
            shutil.rmtree(tmp_outputs_dir, ignore_errors=True)

    total_targets = len(targets)
    print("")
    print("Ingest summary")
    print(f"- script: {SCRIPT_VERSION}")
    print(f"- mode: {'apply' if apply_changes else 'dry-run'}")
    print(f"- queue_bundle: {to_repo_relative(queue_bundle)}")
    print(f"- outputs_dir: {outputs_dir}")
    print(f"- targets: {total_targets}")
    print(f"- written: {written_count}")
    print(f"- missing: {missing_count}")
    print(f"- reconciled: {reconciled_count}")
    print(f"- failed: {failed_count}")
    print(f"- input_sync_new_files: {input_synced_count}")
    print(f"- input_sync_existing_files: {input_sync_existing_count}")
    print(f"- input_sync_flat_alias_new_files: {input_alias_written_count}")
    print(f"- ticker_output_sync_writes: {ticker_output_written_count}")
    print(f"- reconcile_available: {'yes' if _reconcile_available else 'no'}")

    return 1 if failed_count > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
