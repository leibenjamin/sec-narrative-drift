from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, cast

from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v2")

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_LAB_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"
PUBLIC_BASELINE_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift"

sys.path.append(str(Path(__file__).resolve().parent))
import build_lab_outputs as blo  # type: ignore
from lab_prompt_blocks import build_prompt_templates_showcase_lines  # type: ignore


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def as_str_dict(value: Any) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    output: dict[str, Any] = {}
    for key, item in cast(dict[Any, Any], value).items():
        if not isinstance(key, str):
            return None
        output[key] = item
    return output


def as_list(value: Any) -> Optional[list[Any]]:
    if isinstance(value, list):
        return cast(list[Any], value)
    return None


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def heading_like(text: str) -> bool:
    trimmed = text.strip()
    if not trimmed:
        return False
    if len(trimmed) > 120:
        return False
    if trimmed.upper() == trimmed and len(trimmed) >= 5:
        return True
    if trimmed.lower().startswith("item "):
        return True
    if trimmed.endswith(":"):
        return True
    words = trimmed.split()
    if len(words) <= 8 and trimmed[0].isupper():
        return True
    return False


def load_roster(path: Path) -> tuple[list[str], str, dict[str, list[tuple[int, int]]]]:
    payload = read_json(path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        raise SystemExit("Roster JSON invalid.")
    tickers_raw = payload_dict.get("tickers")
    section = payload_dict.get("section")
    pairs_raw = payload_dict.get("pairs_per_ticker")
    if not isinstance(tickers_raw, list) or not isinstance(section, str) or not isinstance(pairs_raw, dict):
        raise SystemExit("Roster JSON missing required fields.")

    tickers: list[str] = []
    for item in cast(list[Any], tickers_raw):
        if isinstance(item, str):
            tickers.append(item)

    pairs_per_ticker: dict[str, list[tuple[int, int]]] = {}
    for ticker, entries in cast(dict[Any, Any], pairs_raw).items():
        if not isinstance(ticker, str) or not isinstance(entries, list):
            continue
        pairs: list[tuple[int, int]] = []
        for entry in cast(list[Any], entries):
            entry_dict = as_str_dict(entry)
            if entry_dict is None:
                continue
            year_from = entry_dict.get("year_from")
            year_to = entry_dict.get("year_to")
            if isinstance(year_from, int) and isinstance(year_to, int):
                pairs.append((year_from, year_to))
        pairs_per_ticker[ticker] = pairs

    return tickers, section, pairs_per_ticker


def load_hero_pairs(path: Path) -> dict[str, list[tuple[int, int]]]:
    payload = read_json(path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        raise SystemExit("Hero pairs JSON invalid.")
    heroes_raw = payload_dict.get("hero_pairs_per_ticker")
    if not isinstance(heroes_raw, dict):
        raise SystemExit("Hero pairs JSON missing hero_pairs_per_ticker.")

    heroes: dict[str, list[tuple[int, int]]] = {}
    for ticker, entries in cast(dict[Any, Any], heroes_raw).items():
        if not isinstance(ticker, str) or not isinstance(entries, list):
            continue
        pairs: list[tuple[int, int]] = []
        for entry in cast(list[Any], entries):
            entry_dict = as_str_dict(entry)
            if entry_dict is None:
                continue
            year_from = entry_dict.get("year_from")
            year_to = entry_dict.get("year_to")
            if isinstance(year_from, int) and isinstance(year_to, int):
                pairs.append((year_from, year_to))
        heroes[ticker] = pairs

    return heroes


def load_lab_logodds_terms(
    ticker: str, section: str, year_from: int, year_to: int, lens: str
) -> list[str]:
    filename = blo.build_output_filename(section, year_from, year_to, "det_logodds_terms_v1", lens, "edgar")
    path = PUBLIC_LAB_ROOT / ticker.upper() / filename
    if not path.exists():
        return []
    payload = read_json(path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        return []
    artifacts = payload_dict.get("artifacts")
    if not isinstance(artifacts, dict):
        return []
    labels: list[str] = []
    for key in ("top_risers", "top_fallers"):
        items = cast(dict[str, Any], artifacts).get(key)
        if not isinstance(items, list):
            continue
        for entry in cast(list[Any], items):
            entry_dict = as_str_dict(entry)
            if entry_dict is None:
                continue
            label = entry_dict.get("label")
            if isinstance(label, str):
                labels.append(label)
    return labels


def load_baseline_terms(
    ticker: str, section: str, year_from: int, year_to: int
) -> list[str]:
    path = PUBLIC_BASELINE_ROOT / ticker.upper() / f"shifts_{section}.json"
    if not path.exists():
        return []
    payload = read_json(path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        return []
    year_pairs = as_list(payload_dict.get("yearPairs"))
    if year_pairs is None:
        year_pairs = as_list(payload_dict.get("pairs"))
    if year_pairs is None:
        return []
    for entry in year_pairs:
        entry_dict = as_str_dict(entry)
        if entry_dict is None:
            continue
        if entry_dict.get("from") != year_from or entry_dict.get("to") != year_to:
            continue
        labels: list[str] = []
        for key in ("topRisers", "topFallers"):
            items = entry_dict.get(key)
            if not isinstance(items, list):
                continue
            for item in cast(list[Any], items):
                item_dict = as_str_dict(item)
                if item_dict is None:
                    continue
                term = item_dict.get("term")
                if isinstance(term, str):
                    labels.append(term)
        return labels
    return []


def get_trigger_terms(
    ticker: str, section: str, year_from: int, year_to: int, lens: str
) -> list[str]:
    labels = load_lab_logodds_terms(ticker, section, year_from, year_to, lens)
    if not labels:
        labels = load_baseline_terms(ticker, section, year_from, year_to)
    cleaned: list[str] = []
    for label in labels:
        trimmed = label.strip()
        if trimmed and trimmed not in cleaned:
            cleaned.append(trimmed)
        if len(cleaned) >= 24:
            break
    return cleaned


def add_window(indices: set[int], idx: int, total: int) -> None:
    for offset in (-1, 0, 1):
        candidate = idx + offset
        if 0 <= candidate < total:
            indices.add(candidate)


def select_focus_indices(
    prev_paras: list[str],
    curr_paras: list[str],
    trigger_terms: list[str],
    max_prev: int,
    max_curr: int,
) -> tuple[list[int], list[int], dict[str, Any]]:
    selected_prev: set[int] = set()
    selected_curr: set[int] = set()

    lowered_prev = [p.lower() for p in prev_paras]
    lowered_curr = [p.lower() for p in curr_paras]

    trigger_hits = 0
    for term in trigger_terms:
        term_lower = term.lower()
        for idx, para in enumerate(lowered_prev):
            if term_lower in para:
                add_window(selected_prev, idx, len(prev_paras))
                trigger_hits += 1
                break
        for idx, para in enumerate(lowered_curr):
            if term_lower in para:
                add_window(selected_curr, idx, len(curr_paras))
                trigger_hits += 1
                break

    heading_hits = 0
    for idx, para in enumerate(prev_paras):
        if heading_like(para):
            add_window(selected_prev, idx, len(prev_paras))
            heading_hits += 1
    for idx, para in enumerate(curr_paras):
        if heading_like(para):
            add_window(selected_curr, idx, len(curr_paras))
            heading_hits += 1

    prev_norm = [normalize_text(p) for p in prev_paras]
    curr_norm = [normalize_text(p) for p in curr_paras]
    prev_set = set(prev_norm)
    curr_set = set(curr_norm)

    diff_hits = 0
    for idx, value in enumerate(prev_norm):
        if value and value not in curr_set:
            add_window(selected_prev, idx, len(prev_paras))
            diff_hits += 1
        if diff_hits >= 20:
            break
    diff_hits = 0
    for idx, value in enumerate(curr_norm):
        if value and value not in prev_set:
            add_window(selected_curr, idx, len(curr_paras))
            diff_hits += 1
        if diff_hits >= 20:
            break

    sorted_prev = sorted(selected_prev)
    sorted_curr = sorted(selected_curr)

    if len(sorted_prev) > max_prev:
        sorted_prev = sorted_prev[:max_prev]
    if len(sorted_curr) > max_curr:
        sorted_curr = sorted_curr[:max_curr]

    meta = {
        "selected_prev_indices": sorted_prev,
        "selected_curr_indices": sorted_curr,
        "full_prev_count": len(prev_paras),
        "full_curr_count": len(curr_paras),
        "trigger_terms": trigger_terms,
        "trigger_hits": trigger_hits,
        "heading_hits": heading_hits,
    }

    return sorted_prev, sorted_curr, meta


def build_full_payload(
    ticker: str,
    section: str,
    year_from: int,
    year_to: int,
    lens: str,
    lens_pair: blo.LensPair,
) -> dict[str, Any]:
    output_targets = {
        "det_llm_delta_brief_v1": blo.build_output_filename(
            section, year_from, year_to, "det_llm_delta_brief_v1", lens, "edgar"
        ),
        "det_llm_excerpt_picker_v1": blo.build_output_filename(
            section, year_from, year_to, "det_llm_excerpt_picker_v1", lens, "edgar"
        ),
    }
    return {
        "case": {
            "ticker": ticker,
            "section": section,
            "year_from": year_from,
            "year_to": year_to,
            "source_id": "edgar",
        },
        "lens": {
            "name": lens,
            "coverage": lens_pair.coverage,
            "warnings": lens_pair.warnings,
        },
        "output_targets": output_targets,
        "texts": {
            "prev_paragraphs": lens_pair.prev.paragraphs,
            "curr_paragraphs": lens_pair.curr.paragraphs,
        },
    }


def build_year_payload(
    ticker: str,
    section: str,
    year: int,
    lens: str,
    source_id: str,
    paragraphs: list[str],
) -> dict[str, Any]:
    paragraphs_sha256 = hashlib.sha256(
        json.dumps(paragraphs, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    chars_total = sum(len(paragraph) for paragraph in paragraphs)
    return {
        "schema_version": "2.0",
        "input_mode": "full_section_v2",
        "case": {
            "ticker": ticker,
            "section": section,
            "year": year,
            "source_id": source_id,
        },
        "lens": {
            "name": lens,
        },
        "texts": {
            "paragraphs": paragraphs,
        },
        "integrity": {
            "paragraph_count": len(paragraphs),
            "paragraphs_sha256": paragraphs_sha256,
            "paragraph_chars_total": chars_total,
        },
    }


def build_pair_manifest_payload(
    ticker: str,
    section: str,
    year_from: int,
    year_to: int,
    lens: str,
    source_id: str,
    prev_year_input_path: str,
    curr_year_input_path: str,
    lens_pair: blo.LensPair,
    prev_paragraphs_sha256: str,
    curr_paragraphs_sha256: str,
) -> dict[str, Any]:
    output_targets = {
        "det_llm_delta_brief_v1": blo.build_output_filename(
            section, year_from, year_to, "det_llm_delta_brief_v1", lens, source_id
        ),
        "det_llm_excerpt_picker_v1": blo.build_output_filename(
            section, year_from, year_to, "det_llm_excerpt_picker_v1", lens, source_id
        ),
    }
    return {
        "schema_version": "2.0",
        "input_mode": "full_section_v2",
        "case": {
            "ticker": ticker,
            "section": section,
            "year_from": year_from,
            "year_to": year_to,
            "source_id": source_id,
        },
        "lens": {
            "name": lens,
            "coverage": lens_pair.coverage,
            "warnings": lens_pair.warnings,
        },
        "year_inputs": {
            "prev": prev_year_input_path,
            "curr": curr_year_input_path,
        },
        "input_identity": {
            "pair_ticker": ticker,
            "pair_year_from": year_from,
            "pair_year_to": year_to,
            "pair_section": section,
            "pair_lens": lens,
            "pair_source_id": source_id,
            "year_input_prev": prev_year_input_path,
            "year_input_curr": curr_year_input_path,
            "year_input_prev_paragraphs_sha256": prev_paragraphs_sha256,
            "year_input_curr_paragraphs_sha256": curr_paragraphs_sha256,
        },
        "integrity": {
            "prev_paragraph_count": len(lens_pair.prev.paragraphs),
            "curr_paragraph_count": len(lens_pair.curr.paragraphs),
            "prev_paragraphs_sha256": prev_paragraphs_sha256,
            "curr_paragraphs_sha256": curr_paragraphs_sha256,
            "year_inputs_prev": prev_year_input_path,
            "year_inputs_curr": curr_year_input_path,
        },
        "output_targets": output_targets,
    }


def build_focus_payload(
    ticker: str,
    section: str,
    year_from: int,
    year_to: int,
    lens: str,
    lens_pair: blo.LensPair,
    focus_prev: list[int],
    focus_curr: list[int],
    meta: dict[str, Any],
) -> dict[str, Any]:
    output_targets = {
        "det_llm_delta_brief_v1": blo.build_output_filename(
            section, year_from, year_to, "det_llm_delta_brief_v1", lens, "edgar"
        ),
        "det_llm_excerpt_picker_v1": blo.build_output_filename(
            section, year_from, year_to, "det_llm_excerpt_picker_v1", lens, "edgar"
        ),
    }
    prev_paras = [lens_pair.prev.paragraphs[i] for i in focus_prev]
    curr_paras = [lens_pair.curr.paragraphs[i] for i in focus_curr]
    return {
        "case": {
            "ticker": ticker,
            "section": section,
            "year_from": year_from,
            "year_to": year_to,
            "source_id": "edgar",
        },
        "lens": {
            "name": lens,
            "coverage": lens_pair.coverage,
            "warnings": lens_pair.warnings,
        },
        "output_targets": output_targets,
        "texts": {
            "prev_paragraphs": prev_paras,
            "curr_paragraphs": curr_paras,
        },
        "focuspack_meta": meta,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build LLM input bundles for showcase precompute.")
    parser.add_argument(
        "--roster",
        default=str(PUBLIC_LAB_ROOT / "lab_showcase_roster_v2.json"),
        help="Roster JSON path",
    )
    parser.add_argument(
        "--hero",
        default=str(PUBLIC_LAB_ROOT / "lab_showcase_hero_pairs_v2.json"),
        help="Hero pairs JSON path",
    )
    parser.add_argument(
        "--out_dir",
        default="",
        help="Output bundle directory (default bundles/showcase_llm_inputs_<timestamp>)",
    )
    parser.add_argument(
        "--include-focuspack",
        action="store_true",
        help="Also emit legacy focuspack inputs/index (v1 compatibility mode).",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / "bundles" / f"showcase_llm_inputs_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    roster_path = Path(args.roster)
    hero_path = Path(args.hero)

    tickers, section, pairs_per_ticker = load_roster(roster_path)
    hero_pairs = load_hero_pairs(hero_path)
    hero_pair_count = 0
    for pairs in hero_pairs.values():
        hero_pair_count += len(pairs)
    hero_ticker_count = 0
    for pairs in hero_pairs.values():
        if pairs:
            hero_ticker_count += 1

    year_v2_dir = out_dir / "inputs" / "year"
    pair_v2_dir = out_dir / "inputs" / "pair"
    year_v2_dir.mkdir(parents=True, exist_ok=True)
    pair_v2_dir.mkdir(parents=True, exist_ok=True)
    focus_dir = out_dir / "llm_inputs_focuspack"
    if args.include_focuspack:
        focus_dir.mkdir(parents=True, exist_ok=True)

    year_v2_index: list[dict[str, Any]] = []
    pair_v2_index: list[dict[str, Any]] = []
    focus_index: list[dict[str, Any]] = []

    packet_lines: list[str] = []
    packet_lines.append("# LLM Packet Size Report")
    packet_lines.append("")
    packet_lines.append("| Ticker | Pair | full_raw_prev_chars | full_raw_curr_chars | full_deboiler_prev_chars | full_deboiler_curr_chars | focus_raw_prev_chars | focus_raw_curr_chars | focus_deboiler_prev_chars | focus_deboiler_curr_chars | recommendation |")
    packet_lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")

    for ticker in sorted(tickers):
        pairs = pairs_per_ticker.get(ticker, [])
        for year_from, year_to in pairs:
            prev = blo.load_section_text(ticker, year_from, section, "edgar", REPO_ROOT)
            curr = blo.load_section_text(ticker, year_to, section, "edgar", REPO_ROOT)
            if prev is None or curr is None:
                continue

            lens_pairs: dict[str, blo.LensPair] = {
                "raw": blo.build_lens_pair(prev, curr, "raw"),
                "deboilerplated": blo.build_lens_pair(prev, curr, "deboilerplated"),
            }

            raw_pair = lens_pairs["raw"]
            deboiler_pair = lens_pairs["deboilerplated"]
            raw_full_prev = len(raw_pair.prev.text)
            raw_full_curr = len(raw_pair.curr.text)
            deboiler_full_prev = len(deboiler_pair.prev.text)
            deboiler_full_curr = len(deboiler_pair.curr.text)

            focus_raw_prev = 0
            focus_raw_curr = 0
            focus_deboiler_prev = 0
            focus_deboiler_curr = 0

            for lens_name, lens_pair in lens_pairs.items():
                trigger_terms = get_trigger_terms(ticker, section, year_from, year_to, lens_name)
                max_prev = 60 if lens_name == "raw" else 90
                max_curr = 60 if lens_name == "raw" else 90
                focus_prev, focus_curr, meta = select_focus_indices(
                    lens_pair.prev.paragraphs,
                    lens_pair.curr.paragraphs,
                    trigger_terms,
                    max_prev,
                    max_curr,
                )

                focus_prev_text = "".join(lens_pair.prev.paragraphs[i] for i in focus_prev)
                focus_curr_text = "".join(lens_pair.curr.paragraphs[i] for i in focus_curr)
                if lens_name == "raw":
                    focus_raw_prev = len(focus_prev_text)
                    focus_raw_curr = len(focus_curr_text)
                else:
                    focus_deboiler_prev = len(focus_prev_text)
                    focus_deboiler_curr = len(focus_curr_text)

                # Pair-relative year files are canonical because deboilerplated text is pair-dependent.
                prev_year_name = (
                    f"{ticker}_{year_from}_{section}_{lens_name}_edgar__pair_{year_from}_{year_to}.json"
                )
                curr_year_name = (
                    f"{ticker}_{year_to}_{section}_{lens_name}_edgar__pair_{year_from}_{year_to}.json"
                )
                prev_year_rel = Path("inputs") / "year" / prev_year_name
                curr_year_rel = Path("inputs") / "year" / curr_year_name

                prev_year_payload = build_year_payload(
                    ticker=ticker,
                    section=section,
                    year=year_from,
                    lens=lens_name,
                    source_id="edgar",
                    paragraphs=lens_pair.prev.paragraphs,
                )
                curr_year_payload = build_year_payload(
                    ticker=ticker,
                    section=section,
                    year=year_to,
                    lens=lens_name,
                    source_id="edgar",
                    paragraphs=lens_pair.curr.paragraphs,
                )
                prev_year_abs = out_dir / prev_year_rel
                curr_year_abs = out_dir / curr_year_rel
                write_json(prev_year_abs, prev_year_payload)
                write_json(curr_year_abs, curr_year_payload)
                prev_year_file_sha256 = file_sha256(prev_year_abs)
                curr_year_file_sha256 = file_sha256(curr_year_abs)
                prev_year_file_bytes = prev_year_abs.stat().st_size
                curr_year_file_bytes = curr_year_abs.stat().st_size
                prev_year_integrity = cast(
                    dict[str, Any], prev_year_payload.get("integrity") or {}
                )
                curr_year_integrity = cast(
                    dict[str, Any], curr_year_payload.get("integrity") or {}
                )
                prev_paragraphs_sha256 = str(prev_year_integrity.get("paragraphs_sha256") or "")
                curr_paragraphs_sha256 = str(curr_year_integrity.get("paragraphs_sha256") or "")
                prev_paragraph_chars_total = int(prev_year_integrity.get("paragraph_chars_total") or 0)
                curr_paragraph_chars_total = int(curr_year_integrity.get("paragraph_chars_total") or 0)

                year_v2_index.append(
                    {
                        "schema_version": "2.0",
                        "input_mode": "full_section_v2",
                        "ticker": ticker,
                        "year": year_from,
                        "pair_year_from": year_from,
                        "pair_year_to": year_to,
                        "section": section,
                        "lens": lens_name,
                        "source_id": "edgar",
                        "path": str(prev_year_rel).replace("\\", "/"),
                        "paragraph_count": len(lens_pair.prev.paragraphs),
                        "paragraph_chars_total": prev_paragraph_chars_total,
                        "paragraphs_sha256": prev_paragraphs_sha256,
                        "payload_sha256": prev_year_file_sha256,
                        "payload_bytes": prev_year_file_bytes,
                    }
                )
                year_v2_index.append(
                    {
                        "schema_version": "2.0",
                        "input_mode": "full_section_v2",
                        "ticker": ticker,
                        "year": year_to,
                        "pair_year_from": year_from,
                        "pair_year_to": year_to,
                        "section": section,
                        "lens": lens_name,
                        "source_id": "edgar",
                        "path": str(curr_year_rel).replace("\\", "/"),
                        "paragraph_count": len(lens_pair.curr.paragraphs),
                        "paragraph_chars_total": curr_paragraph_chars_total,
                        "paragraphs_sha256": curr_paragraphs_sha256,
                        "payload_sha256": curr_year_file_sha256,
                        "payload_bytes": curr_year_file_bytes,
                    }
                )

                pair_name = (
                    f"{ticker}_{year_from}_{year_to}_{section}_{lens_name}_edgar.json"
                )
                pair_rel = Path("inputs") / "pair" / pair_name
                pair_payload = build_pair_manifest_payload(
                    ticker=ticker,
                    section=section,
                    year_from=year_from,
                    year_to=year_to,
                    lens=lens_name,
                    source_id="edgar",
                    prev_year_input_path=str(prev_year_rel).replace("\\", "/"),
                    curr_year_input_path=str(curr_year_rel).replace("\\", "/"),
                    lens_pair=lens_pair,
                    prev_paragraphs_sha256=prev_paragraphs_sha256,
                    curr_paragraphs_sha256=curr_paragraphs_sha256,
                )
                pair_abs = out_dir / pair_rel
                write_json(pair_abs, pair_payload)
                pair_payload_sha256 = file_sha256(pair_abs)
                pair_payload_bytes = pair_abs.stat().st_size
                pair_v2_index.append(
                    {
                        "schema_version": "2.0",
                        "input_mode": "full_section_v2",
                        "ticker": ticker,
                        "year_from": year_from,
                        "year_to": year_to,
                        "section": section,
                        "lens": lens_name,
                        "source_id": "edgar",
                        "path": str(pair_rel).replace("\\", "/"),
                        "year_input_prev": str(prev_year_rel).replace("\\", "/"),
                        "year_input_curr": str(curr_year_rel).replace("\\", "/"),
                        "prev_paragraph_count": len(lens_pair.prev.paragraphs),
                        "curr_paragraph_count": len(lens_pair.curr.paragraphs),
                        "prev_paragraphs_sha256": prev_paragraphs_sha256,
                        "curr_paragraphs_sha256": curr_paragraphs_sha256,
                        "prev_payload_sha256": prev_year_file_sha256,
                        "curr_payload_sha256": curr_year_file_sha256,
                        "pair_payload_sha256": pair_payload_sha256,
                        "pair_payload_bytes": pair_payload_bytes,
                        "output_targets": pair_payload.get("output_targets"),
                    }
                )

                if args.include_focuspack:
                    focus_payload = build_focus_payload(
                        ticker,
                        section,
                        year_from,
                        year_to,
                        lens_name,
                        lens_pair,
                        focus_prev,
                        focus_curr,
                        meta,
                    )
                    focus_rel = Path(ticker) / (
                        f"lab_llm_focuspack_{section}_{year_from}_{year_to}_{lens_name}.json"
                    )
                    write_json(focus_dir / focus_rel, focus_payload)
                    focus_index.append(
                        {
                            "schema_version": "1.0",
                            "input_mode": "focuspack_v1",
                            "ticker": ticker,
                            "year_from": year_from,
                            "year_to": year_to,
                            "section": section,
                            "lens": lens_name,
                            "source_id": "edgar",
                            "path": str(Path("llm_inputs_focuspack") / focus_rel).replace("\\", "/"),
                            "output_targets": focus_payload.get("output_targets"),
                        }
                    )

            recommendation = "focuspack"
            if raw_full_prev and raw_full_curr:
                raw_full = raw_full_prev + raw_full_curr
                raw_focus = focus_raw_prev + focus_raw_curr
                if raw_focus >= 0.8 * raw_full:
                    recommendation = "full"
            packet_lines.append(
                "| "
                + " | ".join(
                    [
                        ticker,
                        f"{year_from}-{year_to}",
                        str(raw_full_prev),
                        str(raw_full_curr),
                        str(deboiler_full_prev),
                        str(deboiler_full_curr),
                        str(focus_raw_prev),
                        str(focus_raw_curr),
                        str(focus_deboiler_prev),
                        str(focus_deboiler_curr),
                        recommendation,
                    ]
                )
                + " |"
            )

    write_json(out_dir / "inputs_index_year_v2.json", year_v2_index)
    write_json(out_dir / "inputs_index_pair_v2.json", pair_v2_index)
    if args.include_focuspack:
        write_json(out_dir / "inputs_index_focuspack.json", focus_index)

    prompt_lines = build_prompt_templates_showcase_lines()
    (out_dir / "prompt_templates_showcase.md").write_text(
        "\n".join(prompt_lines) + "\n", encoding="utf-8"
    )

    (out_dir / "packet_sizes_report.md").write_text("\n".join(packet_lines), encoding="utf-8")

    readme_lines = [
        "# Showcase LLM Inputs Bundle",
        "",
        f"Created: {timestamp}",
        f"Roster: {roster_path}",
        f"Hero pairs: {hero_path}",
        f"Hero pair count: {hero_pair_count}",
        f"Hero tickers with pairs: {hero_ticker_count}",
        "",
        "Contents:",
        "- inputs/year/ (v2 canonical per-year full-section inputs)",
        "- inputs/pair/ (v2 canonical pair manifests referencing year inputs)",
        "- inputs_index_year_v2.json",
        "- inputs_index_pair_v2.json",
        "- llm_inputs_focuspack/ and inputs_index_focuspack.json (optional legacy, when --include-focuspack is set)",
        "- prompt_templates_showcase.md",
        "- packet_sizes_report.md",
        "",
        "Notes:",
        "- v2 canonical inputs are full-section and direct FULL-index based.",
        "- pair manifests reference canonical per-year files and preserve provenance.input_file as a single path.",
        "- year/pair payloads and v2 indexes include additive integrity metadata (sha256, bytes, paragraph counts).",
        "- Focuspack is legacy compatibility only and not default.",
        "- LLM outputs must be precomputed (no runtime API calls).",
    ]
    (out_dir / "README_bundle.md").write_text("\n".join(readme_lines), encoding="utf-8")

    zip_name = f"chatgpt_bundle_showcase_llm_inputs_{timestamp}.zip"
    zip_path = REPO_ROOT / zip_name
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_handle:
        for path in out_dir.rglob("*"):
            if path.is_file():
                zip_handle.write(path, path.relative_to(out_dir))

    print(f"Wrote bundle to {out_dir}")
    print(f"Wrote zip to {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
