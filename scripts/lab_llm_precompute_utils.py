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
    input_mode: Optional[str] = None
    year: Optional[int] = None
    pair_year_from: Optional[int] = None
    pair_year_to: Optional[int] = None
    year_input_prev: Optional[str] = None
    year_input_curr: Optional[str] = None
    paragraph_count: Optional[int] = None
    paragraph_chars_total: Optional[int] = None
    paragraphs_sha256: Optional[str] = None
    payload_sha256: Optional[str] = None
    payload_bytes: Optional[int] = None
    pair_payload_sha256: Optional[str] = None
    pair_payload_bytes: Optional[int] = None
    prev_payload_sha256: Optional[str] = None
    curr_payload_sha256: Optional[str] = None
    prev_paragraph_count: Optional[int] = None
    curr_paragraph_count: Optional[int] = None
    prev_paragraphs_sha256: Optional[str] = None
    curr_paragraphs_sha256: Optional[str] = None


@dataclass(frozen=True)
class BundlePaths:
    bundle_root: Path
    focus_index: Optional[Path]
    full_index: Optional[Path]
    pair_index_v2: Optional[Path]
    year_index_v2: Optional[Path]
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
        has_legacy = (entry / "inputs_index_focuspack.json").exists()
        has_v2 = (entry / "inputs_index_pair_v2.json").exists() and (
            entry / "inputs_index_year_v2.json"
        ).exists()
        if not has_legacy and not has_v2:
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
    pair_index_v2: Optional[str] = None,
    year_index_v2: Optional[str] = None,
) -> BundlePaths:
    focus_path = Path(focus_index) if focus_index else None
    full_path = Path(full_index) if full_index else None
    pair_v2_path = Path(pair_index_v2) if pair_index_v2 else None
    year_v2_path = Path(year_index_v2) if year_index_v2 else None
    bundle_path = Path(bundle_root) if bundle_root else None

    if bundle_path is None:
        if focus_path is not None:
            bundle_path = focus_path.parent
        elif full_path is not None:
            bundle_path = full_path.parent
        elif pair_v2_path is not None:
            bundle_path = pair_v2_path.parent
        elif year_v2_path is not None:
            bundle_path = year_v2_path.parent
        else:
            bundle_path = find_latest_bundle(BUNDLES_ROOT)
            if bundle_path is None:
                raise SystemExit("No LLM input bundle found. Provide --bundle or index paths.")

    if not bundle_path.is_absolute():
        bundle_path = (REPO_ROOT / bundle_path).resolve()
    if not bundle_path.exists():
        raise SystemExit(f"Bundle root not found: {bundle_path}")

    if focus_path is None:
        candidate = bundle_path / "inputs_index_focuspack.json"
        if candidate.exists():
            focus_path = candidate
    elif not focus_path.is_absolute():
        focus_path = (REPO_ROOT / focus_path).resolve()

    if full_path is None:
        candidate = bundle_path / "inputs_index_full.json"
        if candidate.exists():
            full_path = candidate
    elif not full_path.is_absolute():
        full_path = (REPO_ROOT / full_path).resolve()

    if pair_v2_path is None:
        candidate = bundle_path / "inputs_index_pair_v2.json"
        if candidate.exists():
            pair_v2_path = candidate
    elif not pair_v2_path.is_absolute():
        pair_v2_path = (REPO_ROOT / pair_v2_path).resolve()

    if year_v2_path is None:
        candidate = bundle_path / "inputs_index_year_v2.json"
        if candidate.exists():
            year_v2_path = candidate
    elif not year_v2_path.is_absolute():
        year_v2_path = (REPO_ROOT / year_v2_path).resolve()

    if (
        focus_path is None
        and full_path is None
        and pair_v2_path is None
        and year_v2_path is None
    ):
        raise SystemExit(
            "Bundle has no recognized input indexes (expected legacy inputs_index_focuspack/full or v2 inputs_index_pair_v2/year_v2)."
        )

    if focus_path is not None and not focus_path.exists():
        raise SystemExit(f"Focuspack index not found: {focus_path}")
    if full_path is not None and not full_path.exists():
        raise SystemExit(f"Full index not found: {full_path}")
    if pair_v2_path is not None and not pair_v2_path.exists():
        raise SystemExit(f"Pair v2 index not found: {pair_v2_path}")
    if year_v2_path is not None and not year_v2_path.exists():
        raise SystemExit(f"Year v2 index not found: {year_v2_path}")

    prompt_path = Path(prompt_templates) if prompt_templates else None
    if prompt_path is not None and not prompt_path.is_absolute():
        prompt_path = (REPO_ROOT / prompt_path).resolve()
    if prompt_path is None:
        # Legacy detector-oriented helpers still default to prompt_templates_showcase.md.
        # Casebook candidate prep uses prompt_templates_casebook.md through
        # scripts/build_casebook_candidate_inputs_bundle.py instead.
        candidate = bundle_path / "prompt_templates_showcase.md"
        if candidate.exists():
            prompt_path = candidate

    return BundlePaths(
        bundle_root=bundle_path,
        focus_index=focus_path,
        full_index=full_path,
        pair_index_v2=pair_v2_path,
        year_index_v2=year_v2_path,
        prompt_templates=prompt_path,
    )


def _resolve_pair_years(entry_dict: dict[str, Any]) -> tuple[Optional[int], Optional[int]]:
    year_from = get_int(entry_dict.get("year_from"))
    year_to = get_int(entry_dict.get("year_to"))
    if year_from is not None and year_to is not None:
        return year_from, year_to

    pair_year_from = get_int(entry_dict.get("pair_year_from"))
    pair_year_to = get_int(entry_dict.get("pair_year_to"))
    if pair_year_from is not None and pair_year_to is not None:
        return pair_year_from, pair_year_to

    year_value = get_int(entry_dict.get("year"))
    if year_value is not None:
        return year_value, year_value
    return None, None


def load_input_index(path: Path, bundle_root: Path) -> dict[tuple[str, int, int, str, str], InputIndexEntry]:
    payload = read_json(path)
    payload_list = as_list(payload)
    if payload_list is None:
        raise SystemExit(f"Input index invalid (must be JSON list): {path}")

    output: dict[tuple[str, int, int, str, str], InputIndexEntry] = {}
    for entry in payload_list:
        entry_dict = as_str_dict(entry)
        if entry_dict is None:
            continue

        ticker = get_str(entry_dict.get("ticker"))
        year_from, year_to = _resolve_pair_years(entry_dict)
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
        full_path = rel_path if rel_path.is_absolute() else (bundle_root / rel_path).resolve()
        key = (ticker.upper(), year_from, year_to, section, lens)
        output[key] = InputIndexEntry(
            ticker=ticker.upper(),
            year_from=year_from,
            year_to=year_to,
            section=section,
            lens=lens,
            path=full_path,
            input_mode=get_str(entry_dict.get("input_mode")),
            year=get_int(entry_dict.get("year")),
            pair_year_from=get_int(entry_dict.get("pair_year_from")),
            pair_year_to=get_int(entry_dict.get("pair_year_to")),
            year_input_prev=get_str(entry_dict.get("year_input_prev")),
            year_input_curr=get_str(entry_dict.get("year_input_curr")),
            paragraph_count=get_int(entry_dict.get("paragraph_count")),
            paragraph_chars_total=get_int(entry_dict.get("paragraph_chars_total")),
            paragraphs_sha256=get_str(entry_dict.get("paragraphs_sha256")),
            payload_sha256=get_str(entry_dict.get("payload_sha256")),
            payload_bytes=get_int(entry_dict.get("payload_bytes")),
            pair_payload_sha256=get_str(entry_dict.get("pair_payload_sha256")),
            pair_payload_bytes=get_int(entry_dict.get("pair_payload_bytes")),
            prev_payload_sha256=get_str(entry_dict.get("prev_payload_sha256")),
            curr_payload_sha256=get_str(entry_dict.get("curr_payload_sha256")),
            prev_paragraph_count=get_int(entry_dict.get("prev_paragraph_count")),
            curr_paragraph_count=get_int(entry_dict.get("curr_paragraph_count")),
            prev_paragraphs_sha256=get_str(entry_dict.get("prev_paragraphs_sha256")),
            curr_paragraphs_sha256=get_str(entry_dict.get("curr_paragraphs_sha256")),
        )
    return output


def to_repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except Exception:
        return path.as_posix()
