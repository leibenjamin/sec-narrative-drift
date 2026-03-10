from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, cast

from lab_llm_precompute_utils import (
    as_list,
    as_str_dict,
    get_int,
    get_str,
    read_json,
    resolve_bundle_paths,
)
from lab_output_tracks import DEFAULT_PRIMARY_LLM_CAMPAIGN_ID, get_llm_campaign
from lab_case_focus_expectations import validate_focus_signal_paragraph_hints
from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_INPUTS_V2_ROOT = (
    REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab" / "llm_inputs_v2"
)
DEFAULT_MASTER_MANIFEST = REPO_ROOT / "reports" / "lab_llm_master_manifest_codex_real.json"
DEFAULT_MASTER_STARTERS = REPO_ROOT / "reports" / "lab_llm_master_thread_starters_codex_real.md"
DEFAULT_REPORT = REPO_ROOT / "reports" / "lab_llm_master_input_locks.md"


@dataclass(frozen=True)
class LockIssue:
    layer: str
    code: str
    detail: str


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def paragraphs_sha256(paragraphs: list[str]) -> str:
    encoded = json.dumps(paragraphs, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def year_paragraph_count(path: Path) -> Optional[int]:
    payload = read_json(path)
    root = as_str_dict(payload)
    if root is None:
        return None
    texts = as_str_dict(root.get("texts"))
    if texts is None:
        return None
    paragraphs = as_list(texts.get("paragraphs"))
    if paragraphs is None:
        return None
    return len(paragraphs)


def year_paragraphs_digest(path: Path) -> Optional[str]:
    payload = read_json(path)
    root = as_str_dict(payload)
    if root is None:
        return None
    texts = as_str_dict(root.get("texts"))
    if texts is None:
        return None
    paragraphs_any = as_list(texts.get("paragraphs"))
    if paragraphs_any is None:
        return None
    paragraphs: list[str] = []
    for item in paragraphs_any:
        if not isinstance(item, str):
            return None
        paragraphs.append(item)
    return paragraphs_sha256(paragraphs)


def resolve_repo_path(raw_path: str, *, bundle_root: Optional[Path], pair_abs_path: Optional[Path]) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate.resolve()
    direct = (REPO_ROOT / candidate).resolve()
    if direct.exists():
        return direct
    if bundle_root is not None:
        via_bundle = (bundle_root / candidate).resolve()
        if via_bundle.exists():
            return via_bundle
    if pair_abs_path is not None:
        try:
            pair_bundle_root = pair_abs_path.parents[2]
            via_pair_root = (pair_bundle_root / candidate).resolve()
            if via_pair_root.exists():
                return via_pair_root
        except IndexError:
            pass
    return direct


def load_index_rows(path: Path) -> list[dict[str, Any]]:
    payload = read_json(path)
    rows = as_list(payload)
    if rows is None:
        raise SystemExit(f"Index root is not a list: {path}")
    out: list[dict[str, Any]] = []
    for row_any in rows:
        row = as_str_dict(row_any)
        if row is not None:
            out.append(row)
    return out


def verify_bundle_index(index_path: Path, bundle_root: Path, kind: str) -> list[LockIssue]:
    issues: list[LockIssue] = []
    for row in load_index_rows(index_path):
        rel = get_str(row.get("path"))
        if rel is None:
            issues.append(LockIssue("bundle_index", f"{kind}_missing_path", f"{index_path}: row missing path"))
            continue
        source_path = (bundle_root / rel).resolve()
        if not source_path.exists():
            issues.append(LockIssue("bundle_index", f"{kind}_missing_file", f"{rel} missing from bundle"))
            continue
        actual_sha = file_sha256(source_path)
        actual_bytes = source_path.stat().st_size
        if kind == "pair":
            expected_sha = get_str(row.get("pair_payload_sha256"))
            expected_bytes = get_int(row.get("pair_payload_bytes"))
            if expected_sha and actual_sha != expected_sha:
                issues.append(LockIssue("bundle_index", "pair_sha_mismatch", f"{rel}: index={expected_sha} actual={actual_sha}"))
            if expected_bytes is not None and actual_bytes != expected_bytes:
                issues.append(LockIssue("bundle_index", "pair_bytes_mismatch", f"{rel}: index={expected_bytes} actual={actual_bytes}"))
        else:
            expected_sha = get_str(row.get("payload_sha256"))
            expected_bytes = get_int(row.get("payload_bytes"))
            expected_count = get_int(row.get("paragraph_count"))
            expected_paragraphs_sha = get_str(row.get("paragraphs_sha256"))
            actual_count = year_paragraph_count(source_path)
            actual_paragraphs_sha = year_paragraphs_digest(source_path)
            if expected_sha and actual_sha != expected_sha:
                issues.append(LockIssue("bundle_index", "year_sha_mismatch", f"{rel}: index={expected_sha} actual={actual_sha}"))
            if expected_bytes is not None and actual_bytes != expected_bytes:
                issues.append(LockIssue("bundle_index", "year_bytes_mismatch", f"{rel}: index={expected_bytes} actual={actual_bytes}"))
            if expected_count is not None and actual_count != expected_count:
                issues.append(LockIssue("bundle_index", "year_count_mismatch", f"{rel}: index={expected_count} actual={actual_count}"))
            if expected_paragraphs_sha and actual_paragraphs_sha != expected_paragraphs_sha:
                issues.append(LockIssue("bundle_index", "year_paragraphs_sha_mismatch", f"{rel}: index={expected_paragraphs_sha} actual={actual_paragraphs_sha}"))
    return issues


def verify_public_mirror(bundle_root: Path, pair_index_path: Path, year_index_path: Path) -> list[LockIssue]:
    issues: list[LockIssue] = []
    mirror_pair_index = PUBLIC_INPUTS_V2_ROOT / "inputs_index_pair_v2.json"
    mirror_year_index = PUBLIC_INPUTS_V2_ROOT / "inputs_index_year_v2.json"
    for src, dst, code in (
        (pair_index_path, mirror_pair_index, "pair_index_mirror_mismatch"),
        (year_index_path, mirror_year_index, "year_index_mirror_mismatch"),
    ):
        if not dst.exists():
            issues.append(LockIssue("public_mirror", "missing_mirror_index", f"{dst} missing"))
            continue
        if src.read_bytes() != dst.read_bytes():
            issues.append(LockIssue("public_mirror", code, f"{dst} does not match bundle index {src.name}"))
    for index_path in (pair_index_path, year_index_path):
        for row in load_index_rows(index_path):
            rel = get_str(row.get("path"))
            if rel is None:
                continue
            bundle_file = (bundle_root / rel).resolve()
            mirror_file = (PUBLIC_INPUTS_V2_ROOT / rel).resolve()
            if not mirror_file.exists():
                issues.append(LockIssue("public_mirror", "missing_mirror_file", f"{rel} missing from public mirror"))
                continue
            if bundle_file.read_bytes() != mirror_file.read_bytes():
                issues.append(LockIssue("public_mirror", "mirror_file_mismatch", f"{rel} differs between bundle and public mirror"))
    return issues


def build_manifest_entry_map(manifest_path: Path) -> tuple[Optional[Path], dict[str, dict[str, Any]], list[LockIssue]]:
    payload = read_json(manifest_path)
    root = as_str_dict(payload)
    if root is None:
        raise SystemExit(f"Manifest root is not an object: {manifest_path}")
    bundle_root_raw = get_str(root.get("bundle_root"))
    bundle_root = (REPO_ROOT / bundle_root_raw).resolve() if bundle_root_raw else None
    entries_any = as_list(root.get("entries"))
    if entries_any is None:
        raise SystemExit(f"Manifest missing entries list: {manifest_path}")
    issues: list[LockIssue] = []
    mapping: dict[str, dict[str, Any]] = {}
    for entry_any in entries_any:
        entry = as_str_dict(entry_any)
        if entry is None:
            continue
        input_block = as_str_dict(entry.get("input")) or {}
        source_path_raw = get_str(input_block.get("source_path"))
        if source_path_raw is None:
            issues.append(LockIssue("manifest", "missing_source_path", "entry missing input.source_path"))
            continue
        canonical_input = f"inputs/pair/{Path(source_path_raw).name}"
        mapping[canonical_input] = entry
    return bundle_root, mapping, issues


def verify_manifest(manifest_path: Path) -> tuple[dict[str, dict[str, Any]], list[LockIssue]]:
    bundle_root, entry_map, issues = build_manifest_entry_map(manifest_path)
    for canonical_input, entry in entry_map.items():
        input_block = as_str_dict(entry.get("input")) or {}
        integrity = as_str_dict(input_block.get("integrity")) or {}
        source_path_raw = get_str(input_block.get("source_path")) or ""
        prev_path_raw = get_str(input_block.get("source_year_prev_path")) or ""
        curr_path_raw = get_str(input_block.get("source_year_curr_path")) or ""
        pair_path = resolve_repo_path(source_path_raw, bundle_root=bundle_root, pair_abs_path=None)
        prev_path = resolve_repo_path(prev_path_raw, bundle_root=bundle_root, pair_abs_path=pair_path)
        curr_path = resolve_repo_path(curr_path_raw, bundle_root=bundle_root, pair_abs_path=pair_path)
        if not pair_path.exists() or not prev_path.exists() or not curr_path.exists():
            issues.append(LockIssue("manifest", "missing_source_file", f"{canonical_input}: source files missing"))
            continue
        pair_payload = as_str_dict(read_json(pair_path))
        actual_pair_sha = file_sha256(pair_path)
        actual_prev_sha = file_sha256(prev_path)
        actual_curr_sha = file_sha256(curr_path)
        actual_prev_count = year_paragraph_count(prev_path)
        actual_curr_count = year_paragraph_count(curr_path)
        actual_prev_paragraphs_sha = year_paragraphs_digest(prev_path)
        actual_curr_paragraphs_sha = year_paragraphs_digest(curr_path)
        expected_pair_sha = get_str(integrity.get("pair_payload_sha256"))
        expected_prev_sha = get_str(integrity.get("prev_payload_sha256"))
        expected_curr_sha = get_str(integrity.get("curr_payload_sha256"))
        expected_prev_count = get_int(integrity.get("prev_paragraph_count"))
        expected_curr_count = get_int(integrity.get("curr_paragraph_count"))
        expected_prev_paragraphs_sha = get_str(integrity.get("prev_paragraphs_sha256"))
        expected_curr_paragraphs_sha = get_str(integrity.get("curr_paragraphs_sha256"))
        if expected_pair_sha and actual_pair_sha != expected_pair_sha:
            issues.append(LockIssue("manifest", "manifest_pair_sha_mismatch", f"{canonical_input}: manifest={expected_pair_sha} actual={actual_pair_sha}"))
        if expected_prev_sha and actual_prev_sha != expected_prev_sha:
            issues.append(LockIssue("manifest", "manifest_prev_sha_mismatch", f"{canonical_input}: manifest={expected_prev_sha} actual={actual_prev_sha}"))
        if expected_curr_sha and actual_curr_sha != expected_curr_sha:
            issues.append(LockIssue("manifest", "manifest_curr_sha_mismatch", f"{canonical_input}: manifest={expected_curr_sha} actual={actual_curr_sha}"))
        if expected_prev_count is not None and actual_prev_count != expected_prev_count:
            issues.append(LockIssue("manifest", "manifest_prev_count_mismatch", f"{canonical_input}: manifest={expected_prev_count} actual={actual_prev_count}"))
        if expected_curr_count is not None and actual_curr_count != expected_curr_count:
            issues.append(LockIssue("manifest", "manifest_curr_count_mismatch", f"{canonical_input}: manifest={expected_curr_count} actual={actual_curr_count}"))
        if expected_prev_paragraphs_sha and actual_prev_paragraphs_sha != expected_prev_paragraphs_sha:
            issues.append(LockIssue("manifest", "manifest_prev_paragraphs_sha_mismatch", f"{canonical_input}: manifest={expected_prev_paragraphs_sha} actual={actual_prev_paragraphs_sha}"))
        if expected_curr_paragraphs_sha and actual_curr_paragraphs_sha != expected_curr_paragraphs_sha:
            issues.append(LockIssue("manifest", "manifest_curr_paragraphs_sha_mismatch", f"{canonical_input}: manifest={expected_curr_paragraphs_sha} actual={actual_curr_paragraphs_sha}"))
        analysis_expectations = as_str_dict(pair_payload.get("analysis_expectations")) if pair_payload else None
        if analysis_expectations is not None:
            if actual_prev_count is None or actual_curr_count is None:
                issues.append(
                    LockIssue(
                        "manifest",
                        "unverifiable_focus_signal_hints",
                        f"{canonical_input}: could not resolve prev/curr paragraph counts for analysis_expectations validation",
                    )
                )
            else:
                for detail in validate_focus_signal_paragraph_hints(
                    analysis_expectations,
                    prev_paragraph_count=actual_prev_count,
                    curr_paragraph_count=actual_curr_count,
                ):
                    issues.append(
                        LockIssue(
                            "manifest",
                            "invalid_focus_signal_hint",
                            f"{canonical_input}: {detail}",
                        )
                    )
    return entry_map, issues


def extract_job_meta_blocks(starters_path: Path) -> list[dict[str, Any]]:
    text = starters_path.read_text(encoding="utf-8-sig")
    decoder = json.JSONDecoder()
    blocks: list[dict[str, Any]] = []
    for match in re.finditer(r"(?m)^JOB_META\s*$", text):
        brace_idx = text.find("{", match.end())
        if brace_idx == -1:
            continue
        try:
            payload, _ = decoder.raw_decode(text[brace_idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            blocks.append(cast(dict[str, Any], payload))
    return blocks


def verify_starters(starters_path: Path, manifest_entries: dict[str, dict[str, Any]]) -> list[LockIssue]:
    issues: list[LockIssue] = []
    blocks = extract_job_meta_blocks(starters_path)
    if not blocks:
        issues.append(LockIssue("starters", "missing_job_meta", f"No JOB_META blocks found in {starters_path}"))
        return issues
    for block in blocks:
        canonical_input = get_str(block.get("provenance_input_file"))
        if canonical_input is None:
            issues.append(LockIssue("starters", "missing_provenance_input_file", "JOB_META missing provenance_input_file"))
            continue
        entry = manifest_entries.get(canonical_input)
        if entry is None:
            issues.append(LockIssue("starters", "starter_entry_missing_from_manifest", f"{canonical_input} not found in manifest"))
            continue
        input_block = as_str_dict(entry.get("input")) or {}
        integrity = as_str_dict(input_block.get("integrity")) or {}
        master_output = as_str_dict(entry.get("master_output")) or {}
        structured_output = as_str_dict(entry.get("projected_master_output_structured")) or {}
        runtime_output = as_str_dict(entry.get("projected_master_output_runtime")) or {}
        expected_prev_count = get_int(integrity.get("prev_paragraph_count"))
        expected_curr_count = get_int(integrity.get("curr_paragraph_count"))
        expected_pair_sha = get_str(integrity.get("pair_payload_sha256"))
        expected_prev_sha = get_str(integrity.get("prev_payload_sha256"))
        expected_curr_sha = get_str(integrity.get("curr_payload_sha256"))
        actual_prev_count = get_int(block.get("expected_prev_paragraphs"))
        actual_curr_count = get_int(block.get("expected_curr_paragraphs"))
        block_pair_sha = get_str(block.get("expected_pair_sha256"))
        block_prev_sha = get_str(block.get("expected_prev_sha256"))
        block_curr_sha = get_str(block.get("expected_curr_sha256"))
        if expected_prev_count is not None and actual_prev_count != expected_prev_count:
            issues.append(LockIssue("starters", "starter_prev_count_mismatch", f"{canonical_input}: starter={actual_prev_count} manifest={expected_prev_count}"))
        if expected_curr_count is not None and actual_curr_count != expected_curr_count:
            issues.append(LockIssue("starters", "starter_curr_count_mismatch", f"{canonical_input}: starter={actual_curr_count} manifest={expected_curr_count}"))
        if expected_pair_sha and block_pair_sha != expected_pair_sha:
            issues.append(LockIssue("starters", "starter_pair_sha_mismatch", f"{canonical_input}: starter={block_pair_sha} manifest={expected_pair_sha}"))
        if expected_prev_sha and block_prev_sha != expected_prev_sha:
            issues.append(LockIssue("starters", "starter_prev_sha_mismatch", f"{canonical_input}: starter={block_prev_sha} manifest={expected_prev_sha}"))
        if expected_curr_sha and block_curr_sha != expected_curr_sha:
            issues.append(LockIssue("starters", "starter_curr_sha_mismatch", f"{canonical_input}: starter={block_curr_sha} manifest={expected_curr_sha}"))
        block_structured_path = get_str(block.get("output_path_structured"))
        block_insight_path = get_str(block.get("output_path_insight"))
        block_projected_structured_path = get_str(block.get("projected_output_path_structured"))
        block_runtime_path = get_str(block.get("projected_output_path_runtime"))
        expected_master_path = get_str(master_output.get("expected_output_path"))
        expected_structured_path = get_str(structured_output.get("expected_output_path"))
        expected_runtime_path = get_str(runtime_output.get("expected_output_path"))
        if expected_master_path:
            if block_structured_path and block_structured_path != expected_master_path:
                issues.append(LockIssue("starters", "starter_structured_path_mismatch", f"{canonical_input}: starter={block_structured_path} manifest={expected_master_path}"))
            if block_insight_path and block_insight_path != expected_master_path:
                issues.append(LockIssue("starters", "starter_insight_path_mismatch", f"{canonical_input}: starter={block_insight_path} manifest={expected_master_path}"))
        if expected_structured_path and block_projected_structured_path != expected_structured_path:
            issues.append(LockIssue("starters", "starter_projected_structured_path_mismatch", f"{canonical_input}: starter={block_projected_structured_path} manifest={expected_structured_path}"))
        if expected_runtime_path and block_runtime_path != expected_runtime_path:
            issues.append(LockIssue("starters", "starter_runtime_path_mismatch", f"{canonical_input}: starter={block_runtime_path} manifest={expected_runtime_path}"))
    return issues


def verify_master_input_locks(
    *,
    bundle_arg: str,
    master_manifest_path: Path,
    master_starters_path: Path,
) -> list[LockIssue]:
    bundle_paths = resolve_bundle_paths(bundle_arg or None, None, None, None, None, None)
    if bundle_paths.pair_index_v2 is None or bundle_paths.year_index_v2 is None:
        raise SystemExit("Bundle is missing pair/year v2 indexes.")
    issues: list[LockIssue] = []
    issues.extend(verify_bundle_index(bundle_paths.pair_index_v2, bundle_paths.bundle_root, "pair"))
    issues.extend(verify_bundle_index(bundle_paths.year_index_v2, bundle_paths.bundle_root, "year"))
    issues.extend(verify_public_mirror(bundle_paths.bundle_root, bundle_paths.pair_index_v2, bundle_paths.year_index_v2))
    manifest_entries, manifest_issues = verify_manifest(master_manifest_path)
    issues.extend(manifest_issues)
    issues.extend(verify_starters(master_starters_path, manifest_entries))
    return issues


def write_report(path: Path, *, bundle_root: Path, campaign_id: str, issues: list[LockIssue]) -> None:
    lines: list[str] = []
    lines.append("# Master Input Lock Verification")
    lines.append("")
    lines.append(f"- script: `{SCRIPT_VERSION}`")
    lines.append(f"- campaign_id: `{campaign_id}`")
    lines.append(f"- bundle_root: `{bundle_root.relative_to(REPO_ROOT).as_posix()}`")
    lines.append(f"- issue_count: `{len(issues)}`")
    lines.append("")
    if not issues:
        lines.append("Verification status: PASS")
    else:
        lines.append("Verification status: FAIL")
        lines.append("")
        lines.append("| Layer | Code | Detail |")
        lines.append("| --- | --- | --- |")
        for issue in issues:
            detail = issue.detail.replace("|", "\\|")
            lines.append(f"| {issue.layer} | {issue.code} | {detail} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify bundle/mirror/manifest/starter lock coherence for master runs.")
    parser.add_argument("--bundle", default="", help="Bundle root (defaults to latest showcase bundle).")
    parser.add_argument("--campaign-id", default=DEFAULT_PRIMARY_LLM_CAMPAIGN_ID)
    parser.add_argument("--master-manifest", default=str(DEFAULT_MASTER_MANIFEST))
    parser.add_argument("--master-starters", default=str(DEFAULT_MASTER_STARTERS))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    started = time.monotonic()
    args = build_parser().parse_args(argv)
    campaign = get_llm_campaign(args.campaign_id)
    if campaign is None:
        raise SystemExit(f"Unknown campaign id: {args.campaign_id}")
    manifest_path = Path(args.master_manifest)
    if not manifest_path.is_absolute():
        manifest_path = (REPO_ROOT / manifest_path).resolve()
    starters_path = Path(args.master_starters)
    if not starters_path.is_absolute():
        starters_path = (REPO_ROOT / starters_path).resolve()
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = (REPO_ROOT / report_path).resolve()
    bundle_paths = resolve_bundle_paths(args.bundle or None, None, None, None, None, None)
    issues = verify_master_input_locks(
        bundle_arg=str(bundle_paths.bundle_root),
        master_manifest_path=manifest_path,
        master_starters_path=starters_path,
    )
    write_report(
        report_path,
        bundle_root=bundle_paths.bundle_root,
        campaign_id=campaign.track_id,
        issues=issues,
    )
    elapsed = int(time.monotonic() - started)
    print(f"Script: {SCRIPT_VERSION}")
    print(f"Campaign: {campaign.track_id}")
    print(f"Bundle: {bundle_paths.bundle_root}")
    print(f"Issues: {len(issues)}")
    print(f"Report: {report_path}")
    print(f"Elapsed: {elapsed}s")
    if issues:
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
