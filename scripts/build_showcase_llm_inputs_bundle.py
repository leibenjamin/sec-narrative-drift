from __future__ import annotations

import argparse
import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, cast

SCRIPT_VERSION = "build_showcase_llm_inputs_bundle.py@v1"

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

    full_dir = out_dir / "llm_inputs_full"
    focus_dir = out_dir / "llm_inputs_focuspack"
    full_dir.mkdir(parents=True, exist_ok=True)
    focus_dir.mkdir(parents=True, exist_ok=True)

    full_index: list[dict[str, Any]] = []
    focus_index: list[dict[str, Any]] = []

    packet_lines: list[str] = []
    packet_lines.append("# LLM Packet Size Report")
    packet_lines.append("")
    packet_lines.append("| Ticker | Pair | full_raw_prev_chars | full_raw_curr_chars | full_deboiler_prev_chars | full_deboiler_curr_chars | focus_raw_prev_chars | focus_raw_curr_chars | focus_deboiler_prev_chars | focus_deboiler_curr_chars | recommendation |")
    packet_lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")

    for ticker in sorted(tickers):
        pairs = pairs_per_ticker.get(ticker, [])
        hero_set = set(hero_pairs.get(ticker, []))
        for year_from, year_to in pairs:
            prev = blo.load_section_text(ticker, year_from, section, "edgar", REPO_ROOT)
            curr = blo.load_section_text(ticker, year_to, section, "edgar", REPO_ROOT)
            if prev is None or curr is None:
                continue

            lens_pairs: dict[str, blo.LensPair] = {}
            lens_pairs["raw"] = blo.build_lens_pair(prev, curr, "raw")
            deboiler_pair = blo.build_lens_pair(prev, curr, "deboilerplated")
            if "fallback_to_raw" not in deboiler_pair.warnings:
                lens_pairs["deboilerplated"] = deboiler_pair

            raw_full_prev = len(prev.text)
            raw_full_curr = len(curr.text)
            deboiler_full_prev = len(deboiler_pair.prev.text) if "deboilerplated" in lens_pairs else 0
            deboiler_full_curr = len(deboiler_pair.curr.text) if "deboilerplated" in lens_pairs else 0

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

                focus_rel = Path(ticker) / f"lab_llm_focuspack_{section}_{year_from}_{year_to}_{lens_name}.json"
                write_json(focus_dir / focus_rel, focus_payload)
                focus_index.append(
                    {
                        "ticker": ticker,
                        "year_from": year_from,
                        "year_to": year_to,
                        "section": section,
                        "lens": lens_name,
                        "path": str(Path("llm_inputs_focuspack") / focus_rel),
                        "output_targets": focus_payload.get("output_targets"),
                    }
                )

                if (year_from, year_to) in hero_set:
                    full_payload = build_full_payload(
                        ticker, section, year_from, year_to, lens_name, lens_pair
                    )
                    full_rel = Path(ticker) / f"lab_llm_full_{section}_{year_from}_{year_to}_{lens_name}.json"
                    write_json(full_dir / full_rel, full_payload)
                    full_index.append(
                        {
                            "ticker": ticker,
                            "year_from": year_from,
                            "year_to": year_to,
                            "section": section,
                            "lens": lens_name,
                            "path": str(Path("llm_inputs_full") / full_rel),
                            "output_targets": full_payload.get("output_targets"),
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

    write_json(out_dir / "inputs_index_full.json", full_index)
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
        "",
        "Contents:",
        "- llm_inputs_full/ (hero pairs only)",
        "- llm_inputs_focuspack/ (all adjacent pairs)",
        "- inputs_index_full.json",
        "- inputs_index_focuspack.json",
        "- prompt_templates_showcase.md",
        "- packet_sizes_report.md",
        "",
        "Notes:",
        "- Focuspack uses reduced paragraph arrays with focuspack_meta for FULL index mapping.",
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
