from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]

ID_MAP = {
    "llm_outline_compare_v1": "llm_outline_compare_runtime",
    "llm_outline_compare_v2": "llm_outline_compare_structured",
    "llm_outline_compare_v3": "llm_outline_compare_insight",
}
FIELD_MAP = {
    "projected_master_output_v1": "projected_master_output_runtime",
    "projected_master_output_v2": "projected_master_output_structured",
}


def replace_id_tokens(value: str) -> tuple[str, bool]:
    updated = value
    for old, new in ID_MAP.items():
        updated = updated.replace(old, new)
    return updated, updated != value


def transform_json(value: Any) -> tuple[Any, bool]:
    changed = False

    if isinstance(value, dict):
        out: dict[str, Any] = {}
        typed_dict = cast(dict[str, Any], value)
        for raw_key, raw_child in typed_dict.items():
            key: str = str(raw_key)
            mapped_key = FIELD_MAP.get(key, key)
            if mapped_key != key:
                changed = True

            child = raw_child
            if mapped_key in {"artifact_id", "projects_to_artifact_id"} and isinstance(raw_child, str):
                replaced = ID_MAP.get(raw_child, raw_child)
                if replaced != raw_child:
                    child = replaced
                    changed = True
            elif mapped_key in {"expected_output_path", "source_path", "input_file", "output_path"} and isinstance(raw_child, str):
                replaced, replaced_changed = replace_id_tokens(raw_child)
                if replaced_changed:
                    child = replaced
                    changed = True

            transformed_child, child_changed = transform_json(child)
            if child_changed:
                changed = True
            out[mapped_key] = transformed_child
        return out, changed

    if isinstance(value, list):
        typed_list = cast(list[Any], value)
        out_list: list[Any] = []
        for item in typed_list:
            transformed_item, item_changed = transform_json(item)
            if item_changed:
                changed = True
            out_list.append(transformed_item)
        return out_list, changed

    if isinstance(value, str):
        replaced, replaced_changed = replace_id_tokens(value)
        return replaced, replaced_changed

    return value, False


def rename_path(path: Path) -> tuple[Path, bool]:
    updated_name, changed = replace_id_tokens(path.name)
    if not changed:
        return path, False
    return path.with_name(updated_name), True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migrate outline artifact ids/field names/path tokens from v1/v2/v3 to runtime/structured/insight."
    )
    parser.add_argument(
        "--scopes",
        default="public/data/sec_narrative_drift_lab,reports",
        help="Comma-separated repo-relative roots to scan.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned changes without writing files.",
    )
    parser.add_argument(
        "--rename-paths",
        action="store_true",
        help="Also rename files/directories whose names include legacy artifact ids.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    scope_roots: list[Path] = []
    for token in str(args.scopes).split(","):
        cleaned = token.strip()
        if not cleaned:
            continue
        candidate = (REPO_ROOT / cleaned).resolve()
        if candidate.exists():
            scope_roots.append(candidate)

    if not scope_roots:
        raise SystemExit("No valid scope roots found.")

    json_seen = 0
    json_updated = 0
    path_renames = 0

    for scope in scope_roots:
        for json_path in scope.rglob("*.json"):
            json_seen += 1
            try:
                payload = json.loads(json_path.read_text(encoding="utf-8-sig"))
            except Exception:
                continue
            transformed, changed = transform_json(payload)
            if not changed:
                continue
            json_updated += 1
            if not args.dry_run:
                json_path.write_text(
                    json.dumps(transformed, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )

    if args.rename_paths:
        for scope in scope_roots:
            all_paths = sorted(scope.rglob("*"), key=lambda p: len(p.parts), reverse=True)
            for path in all_paths:
                new_path, changed = rename_path(path)
                if not changed:
                    continue
                path_renames += 1
                if args.dry_run:
                    continue
                new_path.parent.mkdir(parents=True, exist_ok=True)
                path.rename(new_path)

    print(
        "MIGRATE_OUTLINE_IDS "
        + f"script={SCRIPT_VERSION} json_seen={json_seen} json_updated={json_updated} "
        + f"path_renames={path_renames} dry_run={bool(args.dry_run)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
