from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLES_ROOT = REPO_ROOT / "bundles"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def as_str_dict(value: Any) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    output: dict[str, Any] = {}
    for key, item in cast(dict[object, object], value).items():
        if not isinstance(key, str):
            return None
        output[key] = item
    return output


def as_list(value: Any) -> Optional[list[Any]]:
    if not isinstance(value, list):
        return None
    return list(cast(list[Any], value))


def get_str(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    return None


def get_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


@dataclass(frozen=True)
class InputIndexEntry:
    ticker: str
    year_from: int
    year_to: int
    section: str
    lens: str
    path: Path


@dataclass(frozen=True)
class BundlePaths:
    bundle_root: Path
    focus_index: Path
    full_index: Path
    prompt_templates: Optional[Path]


def find_latest_bundle(root: Path) -> Optional[Path]:
    if not root.exists():
        return None
    candidates: list[Path] = []
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        if not entry.name.startswith("showcase_llm_inputs_"):
            continue
        if not (entry / "inputs_index_focuspack.json").exists():
            continue
        if not (entry / "inputs_index_full.json").exists():
            continue
        candidates.append(entry)
    if not candidates:
        return None
    return sorted(candidates, key=lambda path: path.name)[-1]


def resolve_bundle_paths(
    bundle_root: Optional[str],
    focus_index: Optional[str],
    full_index: Optional[str],
    prompt_templates: Optional[str],
) -> BundlePaths:
    focus_path = Path(focus_index) if focus_index else None
    full_path = Path(full_index) if full_index else None
    bundle_path = Path(bundle_root) if bundle_root else None

    if bundle_path is None:
        if focus_path is not None:
            bundle_path = focus_path.parent
        elif full_path is not None:
            bundle_path = full_path.parent
        else:
            bundle_path = find_latest_bundle(BUNDLES_ROOT)
            if bundle_path is None:
                raise SystemExit("No LLM input bundle found. Provide --bundle or index paths.")

    if focus_path is None:
        focus_path = bundle_path / "inputs_index_focuspack.json"
    if full_path is None:
        full_path = bundle_path / "inputs_index_full.json"

    if not focus_path.exists():
        raise SystemExit(f"Focuspack index not found: {focus_path}")
    if not full_path.exists():
        raise SystemExit(f"Full index not found: {full_path}")

    prompt_path = Path(prompt_templates) if prompt_templates else None
    if prompt_path is None:
        candidate = bundle_path / "prompt_templates_showcase.md"
        if candidate.exists():
            prompt_path = candidate

    return BundlePaths(
        bundle_root=bundle_path,
        focus_index=focus_path,
        full_index=full_path,
        prompt_templates=prompt_path,
    )


def load_input_index(path: Path, bundle_root: Path) -> dict[tuple[str, int, int, str, str], InputIndexEntry]:
    payload = read_json(path)
    payload_list = as_list(payload)
    if payload_list is None:
        raise SystemExit(f"Input index invalid: {path}")
    output: dict[tuple[str, int, int, str, str], InputIndexEntry] = {}
    for entry in payload_list:
        entry_dict = as_str_dict(entry)
        if entry_dict is None:
            continue
        ticker = get_str(entry_dict.get("ticker"))
        year_from = get_int(entry_dict.get("year_from"))
        year_to = get_int(entry_dict.get("year_to"))
        section = get_str(entry_dict.get("section"))
        lens = get_str(entry_dict.get("lens"))
        path_value = get_str(entry_dict.get("path"))
        if (
            ticker is None
            or year_from is None
            or year_to is None
            or section is None
            or lens is None
            or path_value is None
        ):
            continue
        rel_path = Path(path_value)
        full_path = rel_path if rel_path.is_absolute() else bundle_root / rel_path
        key = (ticker.upper(), year_from, year_to, section, lens)
        output[key] = InputIndexEntry(
            ticker=ticker.upper(),
            year_from=year_from,
            year_to=year_to,
            section=section,
            lens=lens,
            path=full_path,
        )
    return output


def to_repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except Exception:
        return path.as_posix()
