from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Optional

from lab_script_version import build_script_version
from lab_output_tracks import DEFAULT_PRIMARY_LLM_CAMPAIGN_ID, get_llm_campaign
from lab_llm_precompute_utils import as_list, as_str_dict, get_int, get_str, read_json
from lab_validate_llm_master_outputs import matches_only_token

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "reports" / "lab_llm_master_manifest_codex_real.json"
DEFAULT_OUT_DIR = REPO_ROOT / "bundles" / "portable_master_run_pack_v1"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_manifest_entries(path: Path) -> list[dict[str, Any]]:
    payload = read_json(path)
    root = as_str_dict(payload)
    if root is None:
        raise SystemExit(f"Manifest root must be object: {path}")
    entries = as_list(root.get("entries"))
    if entries is None:
        raise SystemExit(f"Manifest missing entries list: {path}")
    out: list[dict[str, Any]] = []
    for item in entries:
        row = as_str_dict(item)
        if row is not None:
            out.append(row)
    return out


def resolve_input_path(raw_path: str, pair_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate.resolve()
    direct = (REPO_ROOT / candidate).resolve()
    if direct.exists():
        return direct
    pair_candidate = (REPO_ROOT / pair_path).resolve()
    bundle_root = pair_candidate.parents[2]
    via_bundle = (bundle_root / raw_path).resolve()
    return via_bundle



def extract_paragraph_count(payload: object) -> int:
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        return -1
    texts = as_str_dict(payload_dict.get("texts"))
    if texts is None:
        return -1
    paragraphs = as_list(texts.get("paragraphs"))
    return len(paragraphs) if paragraphs is not None else -1


def build_starter_text(job_meta: dict[str, Any]) -> str:
    return "\n".join(
        [
            "BEGIN_STARTER",
            "Execution mode: PORTABLE_AUTOWRITE_VALIDATE",
            f"Case context: ticker={job_meta['ticker']} pair={job_meta['year_from']}-{job_meta['year_to']} lens={job_meta['lens']} section={job_meta['section']} source={job_meta['source_id']}",
            "Use only local files under ./inputs and ./job/job_meta.json.",
            "Forbidden: external web data, sibling outputs, or files outside this pack.",
            "",
            "Required input files:",
            "- inputs/pair.json",
            "- inputs/year_prev.json",
            "- inputs/year_curr.json",
            "- checksums/sha256_manifest.json",
            "",
            "Preflight:",
            "- Verify all three input files exist and parse as JSON.",
            "- Verify sha256 values match checksums/sha256_manifest.json.",
            "- Verify year_prev/year_curr paragraph counts match job_meta expected counts.",
            "- Print exactly one line: PRECHECK_OK ...",
            "",
            "Generation:",
            "- Generate one JSON object with artifact_id llm_outline_compare_structured into outputs/master_structured.json.",
            "- Generate deterministic projected llm_outline_compare_runtime into outputs/master_runtime.json using structured shared fields.",
            "",
            "Checks:",
            "- python -c \"import json, pathlib; json.loads(pathlib.Path('outputs/master_structured.json').read_text(encoding='utf-8-sig')); print('JSON_OK_STRUCTURED')\"",
            "- python -c \"import json, pathlib; json.loads(pathlib.Path('outputs/master_runtime.json').read_text(encoding='utf-8-sig')); print('JSON_OK_RUNTIME')\"",
            "",
            "Final status line:",
            "- Success: WRITE_OK JSON_OK VALIDATION_OK",
            "- Failure: FAILED: <reason>",
            "END_STARTER",
            "",
        ]
    )


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build script-free portable run-pack for llm master jobs."
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--campaign-id", default=DEFAULT_PRIMARY_LLM_CAMPAIGN_ID)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--only", default="")
    parser.add_argument(
        "--only-mode",
        choices=("substring", "basename", "exact_path"),
        default="substring",
    )
    parser.add_argument("--clean", action="store_true")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    campaign = get_llm_campaign(args.campaign_id)
    if campaign is None:
        raise SystemExit(f"Unknown campaign id: {args.campaign_id}")

    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = (REPO_ROOT / manifest_path).resolve()
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = (REPO_ROOT / out_dir).resolve()
    if args.clean and out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    entries = read_manifest_entries(manifest_path)
    filters = [token.strip() for token in str(args.only).split(",") if token.strip()]
    jobs_written = 0
    for entry in entries:
        master_output = as_str_dict(entry.get("master_output"))
        input_block = as_str_dict(entry.get("input"))
        if master_output is None or input_block is None:
            continue
        expected_output = get_str(master_output.get("expected_output_path")) or ""
        normalized = "/" + expected_output.replace("\\", "/").lstrip("/")
        if f"/{campaign.track_slug}/" not in normalized:
            continue
        if filters and not any(matches_only_token(expected_output, token, str(args.only_mode)) for token in filters):
            continue

        ticker = get_str(entry.get("ticker")) or ""
        year_from = get_int(entry.get("year_from"))
        year_to = get_int(entry.get("year_to"))
        lens = get_str(entry.get("lens")) or ""
        section = get_str(entry.get("section")) or "10k_item1a"
        source_id = get_str(entry.get("source_id")) or "edgar"
        pair_path = get_str(input_block.get("source_path")) or ""
        prev_path = get_str(input_block.get("source_year_prev_path")) or ""
        curr_path = get_str(input_block.get("source_year_curr_path")) or ""
        if not ticker or year_from is None or year_to is None:
            continue
        if not pair_path or not prev_path or not curr_path:
            continue

        pair_abs = resolve_input_path(pair_path, pair_path)
        prev_abs = resolve_input_path(prev_path, pair_path)
        curr_abs = resolve_input_path(curr_path, pair_path)
        if not pair_abs.exists() or not prev_abs.exists() or not curr_abs.exists():
            continue

        job_slug = f"{ticker}_{year_from}_{year_to}_{lens}"
        job_root = out_dir / job_slug
        inputs_root = job_root / "inputs"
        checks_root = job_root / "checksums"
        job_meta_root = job_root / "job"
        starter_root = job_root / "starter"
        outputs_root = job_root / "outputs"
        outputs_root.mkdir(parents=True, exist_ok=True)
        starter_root.mkdir(parents=True, exist_ok=True)
        job_meta_root.mkdir(parents=True, exist_ok=True)
        checks_root.mkdir(parents=True, exist_ok=True)

        pair_dst = inputs_root / "pair.json"
        prev_dst = inputs_root / "year_prev.json"
        curr_dst = inputs_root / "year_curr.json"
        pair_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pair_abs, pair_dst)
        shutil.copy2(prev_abs, prev_dst)
        shutil.copy2(curr_abs, curr_dst)

        prev_payload = json.loads(prev_dst.read_text(encoding="utf-8-sig"))
        curr_payload = json.loads(curr_dst.read_text(encoding="utf-8-sig"))
        prev_count = extract_paragraph_count(prev_payload)
        curr_count = extract_paragraph_count(curr_payload)

        checksum_payload = {
            "pair_sha256": sha256_file(pair_dst),
            "year_prev_sha256": sha256_file(prev_dst),
            "year_curr_sha256": sha256_file(curr_dst),
        }
        write_json(checks_root / "sha256_manifest.json", checksum_payload)

        job_meta = {
            "schema_version": "1.0",
            "job_id": f"{ticker}_{year_from}_{year_to}_{lens}_{source_id}",
            "ticker": ticker,
            "year_from": year_from,
            "year_to": year_to,
            "lens": lens,
            "section": section,
            "source_id": source_id,
            "expected_prev_paragraphs": prev_count,
            "expected_curr_paragraphs": curr_count,
            "output_master_structured": "outputs/master_structured.json",
            "output_master_runtime": "outputs/master_runtime.json",
        }
        write_json(job_meta_root / "job_meta.json", job_meta)
        (starter_root / "THREAD_STARTER.txt").write_text(
            build_starter_text(job_meta), encoding="utf-8"
        )
        (job_root / "README_PORTABLE.md").write_text(
            "\n".join(
                [
                    "# Portable Master Run Pack",
                    "",
                    f"- script: {SCRIPT_VERSION}",
                    f"- campaign_id: {campaign.track_id}",
                    f"- job_slug: {job_slug}",
                    "",
                    "Files:",
                    "- job/job_meta.json",
                    "- inputs/pair.json",
                    "- inputs/year_prev.json",
                    "- inputs/year_curr.json",
                    "- checksums/sha256_manifest.json",
                    "- starter/THREAD_STARTER.txt",
                    "- outputs/ (write results here)",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        jobs_written += 1

    print(f"Script: {SCRIPT_VERSION}")
    print(f"Manifest: {manifest_path}")
    print(f"Campaign: {campaign.track_id}")
    print(f"Portable run pack dir: {out_dir}")
    print(f"Jobs written: {jobs_written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
