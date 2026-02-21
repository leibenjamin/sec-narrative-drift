from __future__ import annotations

import argparse
import json
import hashlib
from pathlib import Path
from typing import Any, Optional, cast

from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP_JSON = REPO_ROOT / "reports" / "lab_output_path_migration_map.json"
DEFAULT_PRE_HASHES = REPO_ROOT / "reports" / "lab_pre_migration_hashes_chatgpt52ext_42.json"
DEFAULT_POST_HASHES = REPO_ROOT / "reports" / "lab_post_migration_hashes_chatgpt52ext_42.json"
DEFAULT_INVENTORY = REPO_ROOT / "reports" / "lab_pre_migration_inventory.md"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def load_llm_rows(map_path: Path) -> list[dict[str, Any]]:
    payload = read_json(map_path)
    if not isinstance(payload, dict):
        raise SystemExit(f"Map root is not an object: {map_path}")
    payload_d = cast(dict[str, Any], payload)
    rows_raw = payload_d.get("rows")
    if not isinstance(rows_raw, list):
        raise SystemExit(f"Map missing rows[]: {map_path}")
    rows = cast(list[Any], rows_raw)
    llm_rows: list[dict[str, Any]] = []
    for entry in rows:
        if not isinstance(entry, dict):
            continue
        row_d = cast(dict[str, Any], entry)
        if row_d.get("kind") != "llm":
            continue
        llm_rows.append(row_d)
    return llm_rows


def build_inventory_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    lines.append("# Pre-Migration LLM Inventory")
    lines.append("")
    lines.append(f"- script: `{SCRIPT_VERSION}`")
    lines.append(f"- llm_rows: `{len(rows)}`")
    lines.append("")
    for row in rows:
        old_rel = row.get("old_rel_path")
        ticker = row.get("ticker")
        detector = row.get("detector_id")
        year_from = row.get("year_from")
        year_to = row.get("year_to")
        lines.append(
            f"- {ticker} {year_from}-{year_to} {detector}: `{old_rel}`"
        )
    return lines


def pre_snapshot(map_path: Path, out_hashes: Path, out_inventory: Path) -> int:
    rows = load_llm_rows(map_path)
    hash_rows: list[dict[str, Any]] = []
    missing = 0
    for row in rows:
        old_rel = row.get("old_rel_path")
        if not isinstance(old_rel, str):
            continue
        old_abs = REPO_ROOT / old_rel
        if not old_abs.exists():
            missing += 1
            hash_rows.append({**row, "sha256_old": None, "status": "missing"})
            continue
        digest = sha256_file(old_abs)
        hash_rows.append({**row, "sha256_old": digest, "status": "ok"})

    payload = {
        "version": "1.0",
        "mode": "pre",
        "script_version": SCRIPT_VERSION,
        "rows": hash_rows,
        "missing_old": missing,
    }
    write_json(out_hashes, payload)
    write_text(out_inventory, build_inventory_lines(rows))
    print(f"Wrote pre-migration hashes: {out_hashes}")
    print(f"Wrote pre-migration inventory: {out_inventory}")
    print(f"Rows={len(rows)} missing_old={missing}")
    return 0


def post_verify(map_path: Path, pre_hashes_path: Path, out_post_hashes: Path) -> int:
    rows = load_llm_rows(map_path)
    pre_payload = read_json(pre_hashes_path)
    if not isinstance(pre_payload, dict):
        raise SystemExit(f"Pre-hashes root is not object: {pre_hashes_path}")
    pre_d = cast(dict[str, Any], pre_payload)
    pre_rows_raw = pre_d.get("rows")
    if not isinstance(pre_rows_raw, list):
        raise SystemExit(f"Pre-hashes missing rows[]: {pre_hashes_path}")
    pre_rows = cast(list[Any], pre_rows_raw)

    pre_by_new_path: dict[str, str] = {}
    for entry in pre_rows:
        if not isinstance(entry, dict):
            continue
        row_d = cast(dict[str, Any], entry)
        new_rel = row_d.get("new_rel_path")
        sha = row_d.get("sha256_old")
        if isinstance(new_rel, str) and isinstance(sha, str):
            pre_by_new_path[new_rel] = sha

    mismatches: list[str] = []
    out_rows: list[dict[str, Any]] = []
    for row in rows:
        new_rel = row.get("new_rel_path")
        if not isinstance(new_rel, str):
            continue
        new_abs = REPO_ROOT / new_rel
        expected_sha = pre_by_new_path.get(new_rel)
        if not new_abs.exists():
            mismatches.append(f"missing new file: {new_rel}")
            out_rows.append({**row, "sha256_new": None, "match": False})
            continue
        actual_sha = sha256_file(new_abs)
        match = expected_sha == actual_sha
        if not match:
            mismatches.append(f"hash mismatch: {new_rel}")
        out_rows.append(
            {
                **row,
                "sha256_expected_old": expected_sha,
                "sha256_new": actual_sha,
                "match": match,
            }
        )

    out_payload = {
        "version": "1.0",
        "mode": "post",
        "script_version": SCRIPT_VERSION,
        "rows": out_rows,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }
    write_json(out_post_hashes, out_payload)
    print(f"Wrote post-migration hashes: {out_post_hashes}")
    print(f"Mismatches: {len(mismatches)}")
    if mismatches:
        for item in mismatches:
            print(f"- {item}")
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify migration integrity for ChatGPT baseline LLM files.")
    parser.add_argument("--mode", choices=("pre", "post"), required=True)
    parser.add_argument("--map-json", default=str(DEFAULT_MAP_JSON))
    parser.add_argument("--pre-hashes", default=str(DEFAULT_PRE_HASHES))
    parser.add_argument("--post-hashes", default=str(DEFAULT_POST_HASHES))
    parser.add_argument("--inventory", default=str(DEFAULT_INVENTORY))
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    map_path = Path(args.map_json)
    if not map_path.is_absolute():
        map_path = REPO_ROOT / map_path
    pre_hashes_path = Path(args.pre_hashes)
    if not pre_hashes_path.is_absolute():
        pre_hashes_path = REPO_ROOT / pre_hashes_path
    post_hashes_path = Path(args.post_hashes)
    if not post_hashes_path.is_absolute():
        post_hashes_path = REPO_ROOT / post_hashes_path
    inventory_path = Path(args.inventory)
    if not inventory_path.is_absolute():
        inventory_path = REPO_ROOT / inventory_path

    if args.mode == "pre":
        return pre_snapshot(
            map_path=map_path,
            out_hashes=pre_hashes_path,
            out_inventory=inventory_path,
        )
    return post_verify(
        map_path=map_path,
        pre_hashes_path=pre_hashes_path,
        out_post_hashes=post_hashes_path,
    )


if __name__ == "__main__":
    raise SystemExit(main())
