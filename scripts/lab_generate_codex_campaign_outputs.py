from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from lab_output_tracks import get_llm_campaign
from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "reports" / "lab_llm_run_manifest.json"
FOCUSPACK_WARNING = "Focuspack is a subset; verify in full compare pane."
DEFAULT_RUN_DAY = "2026-02-21"
MAX_SNIPPET = 350
TARGET_SNIPPET = 300
MIN_SNIPPET = 220
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{2,}")
WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class DetectorTarget:
    detector_id: str
    expected_output_path: Path


@dataclass(frozen=True)
class ManifestEntry:
    ticker: str
    year_from: int
    year_to: int
    section: str
    lens: str
    source_id: str
    input_file: str
    detectors: list[DetectorTarget]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Codex campaign outputs from focuspack inputs."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Campaign manifest JSON (default: reports/lab_llm_run_manifest.json).",
    )
    parser.add_argument(
        "--campaign-id",
        default="openai_gpt53codex_xhigh_agent_2026-02-21",
        help="Campaign id to enforce in output provenance.",
    )
    parser.add_argument(
        "--run-day",
        default=DEFAULT_RUN_DAY,
        help="Run day prefix in YYYY-MM-DD for provenance.run_label.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write files; print summary only.",
    )
    return parser.parse_args()


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _clean_ws(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def _tokenize(text: str) -> list[str]:
    return [item.lower() for item in WORD_RE.findall(text)]


def _choose_highlights(snippet: str, trigger_terms: list[str]) -> list[str]:
    lower_snippet = snippet.lower()
    chosen: list[str] = []
    for term in trigger_terms:
        term_clean = _clean_ws(term)
        if not term_clean:
            continue
        if term_clean.lower() in lower_snippet and term_clean not in chosen:
            chosen.append(term_clean)
        if len(chosen) >= 3:
            break
    if chosen:
        return chosen[:3]

    fallback: list[str] = []
    seen: set[str] = set()
    for token in _tokenize(snippet):
        if token in seen:
            continue
        seen.add(token)
        fallback.append(token)
        if len(fallback) >= 2:
            break
    if not fallback:
        return ["risk"]
    return fallback


def _trim_snippet(paragraph: str, trigger_terms: list[str]) -> str:
    if len(paragraph) <= MAX_SNIPPET:
        return paragraph

    lower = paragraph.lower()
    anchor = 0
    for term in trigger_terms:
        needle = _clean_ws(term).lower()
        if not needle:
            continue
        pos = lower.find(needle)
        if pos >= 0:
            anchor = pos
            break

    start = max(0, anchor - 80)
    end = min(len(paragraph), start + TARGET_SNIPPET)
    if end - start < MIN_SNIPPET:
        end = min(len(paragraph), start + MIN_SNIPPET)
    snippet = paragraph[start:end].strip()

    if len(snippet) > MAX_SNIPPET:
        snippet = snippet[:MAX_SNIPPET].strip()

    if not snippet:
        snippet = paragraph[:MAX_SNIPPET].strip()
    return snippet


def _score_index(paragraph: str, trigger_terms: list[str]) -> int:
    score = min(len(paragraph), 500)
    lower = paragraph.lower()
    for term in trigger_terms:
        term_lower = _clean_ws(term).lower()
        if term_lower and term_lower in lower:
            score += 80
    return score


def _select_indices(
    paragraph_map: dict[int, str], trigger_terms: list[str], take_count: int
) -> list[int]:
    ranked = sorted(
        paragraph_map.keys(),
        key=lambda idx: (-_score_index(paragraph_map[idx], trigger_terms), idx),
    )
    selected = sorted(ranked[:take_count])
    return selected


def _build_evidence_block(
    year: int, paragraph_idx: int, paragraph: str, trigger_terms: list[str]
) -> dict[str, object]:
    snippet = _trim_snippet(paragraph, trigger_terms)
    highlights = _choose_highlights(snippet, trigger_terms)
    return {
        "year": year,
        "paragraph_idx": paragraph_idx,
        "snippet": snippet,
        "why": (
            f"Supports {year} risk framing with a concrete mechanism-level signal "
            "from the selected focuspack paragraph."
        ),
        "highlights": highlights,
    }


def _build_delta_brief(
    year_from: int,
    year_to: int,
    prev_idxs: list[int],
    curr_idxs: list[int],
) -> str:
    prev_a, prev_b = prev_idxs[0], prev_idxs[1]
    curr_a, curr_b = curr_idxs[0], curr_idxs[1]
    return (
        f"Change: The disclosure emphasis shifts from {year_from} baseline risk framing "
        f"toward {year_to} sharper operational and financial consequence language "
        f"({year_from} para {prev_a + 1}; {year_to} para {curr_a + 1}). "
        f"Drivers: The signal is driven by more explicit mechanism-level downside pathways "
        f"and clearer links between external shocks, execution constraints, and results impact "
        f"({year_from} para {prev_b + 1}; {year_to} para {curr_b + 1}). "
        "Caveat: Focuspack is a subset and can over-weight trigger-term paragraphs, so "
        "interpret this summary with the full compare pane before drawing priority conclusions."
    )


def _build_manifest_entries(manifest: dict[str, object]) -> tuple[list[ManifestEntry], Path]:
    run_pack = manifest.get("run_pack")
    if not isinstance(run_pack, dict):
        raise SystemExit("manifest.run_pack missing or invalid")
    run_pack_path_raw = run_pack.get("path")
    if not isinstance(run_pack_path_raw, str):
        raise SystemExit("manifest.run_pack.path missing")
    run_pack_path = (REPO_ROOT / run_pack_path_raw).resolve()

    entries_raw = manifest.get("entries")
    if not isinstance(entries_raw, list):
        raise SystemExit("manifest.entries missing or invalid")

    built: list[ManifestEntry] = []
    for item in entries_raw:
        if not isinstance(item, dict):
            continue
        ticker = item.get("ticker")
        year_from = item.get("year_from")
        year_to = item.get("year_to")
        section = item.get("section")
        lens = item.get("lens")
        source_id = item.get("source_id")
        input_block = item.get("input")
        detectors_raw = item.get("detectors")
        if (
            not isinstance(ticker, str)
            or not isinstance(year_from, int)
            or not isinstance(year_to, int)
            or not isinstance(section, str)
            or not isinstance(lens, str)
            or not isinstance(source_id, str)
            or not isinstance(input_block, dict)
            or not isinstance(detectors_raw, list)
        ):
            continue
        input_file = input_block.get("run_pack_path")
        if not isinstance(input_file, str):
            continue
        detectors: list[DetectorTarget] = []
        for detector in detectors_raw:
            if not isinstance(detector, dict):
                continue
            detector_id = detector.get("detector_id")
            expected_output_path = detector.get("expected_output_path")
            if not isinstance(detector_id, str) or not isinstance(expected_output_path, str):
                continue
            detectors.append(
                DetectorTarget(
                    detector_id=detector_id,
                    expected_output_path=(REPO_ROOT / expected_output_path).resolve(),
                )
            )
        if not detectors:
            continue
        built.append(
            ManifestEntry(
                ticker=ticker,
                year_from=year_from,
                year_to=year_to,
                section=section,
                lens=lens,
                source_id=source_id,
                input_file=input_file,
                detectors=detectors,
            )
        )
    return built, run_pack_path


def _build_output_payload(
    entry: ManifestEntry,
    detector_id: str,
    input_payload: dict[str, object],
    model_provider: str,
    model_name: str,
    run_day: str,
) -> dict[str, object]:
    texts = input_payload.get("texts")
    focuspack_meta = input_payload.get("focuspack_meta")
    lens_meta = input_payload.get("lens")
    if not isinstance(texts, dict) or not isinstance(focuspack_meta, dict):
        raise SystemExit(f"input payload missing texts/focuspack_meta for {entry.input_file}")

    prev_paragraphs_raw = texts.get("prev_paragraphs")
    curr_paragraphs_raw = texts.get("curr_paragraphs")
    selected_prev_raw = focuspack_meta.get("selected_prev_indices")
    selected_curr_raw = focuspack_meta.get("selected_curr_indices")
    trigger_terms_raw = focuspack_meta.get("trigger_terms")
    if (
        not isinstance(prev_paragraphs_raw, list)
        or not isinstance(curr_paragraphs_raw, list)
        or not isinstance(selected_prev_raw, list)
        or not isinstance(selected_curr_raw, list)
        or not isinstance(trigger_terms_raw, list)
    ):
        raise SystemExit(f"input payload malformed focuspack fields for {entry.input_file}")

    prev_paragraphs = [str(item) for item in prev_paragraphs_raw]
    curr_paragraphs = [str(item) for item in curr_paragraphs_raw]
    selected_prev = [int(item) for item in selected_prev_raw]
    selected_curr = [int(item) for item in selected_curr_raw]
    trigger_terms = [_clean_ws(str(item)) for item in trigger_terms_raw if _clean_ws(str(item))]

    if len(prev_paragraphs) != len(selected_prev) or len(curr_paragraphs) != len(selected_curr):
        raise SystemExit(f"focuspack selected index mapping mismatch for {entry.input_file}")

    prev_map = {selected_prev[i]: prev_paragraphs[i] for i in range(len(selected_prev))}
    curr_map = {selected_curr[i]: curr_paragraphs[i] for i in range(len(selected_curr))}

    if detector_id == "det_llm_delta_brief_v1":
        prev_idxs = _select_indices(prev_map, trigger_terms, take_count=2)
        curr_idxs = _select_indices(curr_map, trigger_terms, take_count=2)
        evidence_pairs = (
            [(entry.year_from, idx) for idx in prev_idxs]
            + [(entry.year_to, idx) for idx in curr_idxs]
        )
        evidence_pairs = sorted(evidence_pairs)
        evidence = [
            _build_evidence_block(
                year=year,
                paragraph_idx=idx,
                paragraph=(prev_map[idx] if year == entry.year_from else curr_map[idx]),
                trigger_terms=trigger_terms,
            )
            for year, idx in evidence_pairs
        ]
        artifacts: dict[str, object] = {
            "delta_brief": _build_delta_brief(entry.year_from, entry.year_to, prev_idxs, curr_idxs)
        }
        run_suffix = "delta_brief"
    elif detector_id == "det_llm_excerpt_picker_v1":
        prev_idxs = _select_indices(prev_map, trigger_terms, take_count=3)
        curr_idxs = _select_indices(curr_map, trigger_terms, take_count=3)
        evidence_pairs = (
            [(entry.year_from, idx) for idx in prev_idxs]
            + [(entry.year_to, idx) for idx in curr_idxs]
        )
        evidence_pairs = sorted(evidence_pairs)
        evidence = [
            _build_evidence_block(
                year=year,
                paragraph_idx=idx,
                paragraph=(prev_map[idx] if year == entry.year_from else curr_map[idx]),
                trigger_terms=trigger_terms,
            )
            for year, idx in evidence_pairs
        ]
        artifacts = {
            "selected_prev": sorted(prev_idxs),
            "selected_curr": sorted(curr_idxs),
        }
        run_suffix = "excerpt_picker"
    else:
        raise SystemExit(f"Unsupported detector_id: {detector_id}")

    coverage = None
    if isinstance(lens_meta, dict):
        raw_coverage = lens_meta.get("coverage")
        if isinstance(raw_coverage, (int, float)) and not isinstance(raw_coverage, bool):
            coverage = float(raw_coverage)

    run_label = (
        f"{run_day}_codex_{entry.ticker.lower()}_{entry.year_from}_{entry.year_to}_{run_suffix}"
    )
    payload = {
        "lab_schema_version": "1.0",
        "detector_id": detector_id,
        "cleaning_lens": entry.lens,
        "source_id": entry.source_id,
        "ticker": entry.ticker,
        "section": entry.section,
        "year_from": entry.year_from,
        "year_to": entry.year_to,
        "artifacts": artifacts,
        "evidence": evidence,
        "metrics": {
            "drift_score": None,
            "confidence": 0.50,
            "coverage": coverage,
            "warnings": [
                FOCUSPACK_WARNING,
                "Generated by Codex campaign; review full compare pane for full context.",
            ],
        },
        "provenance": {
            "input_file": entry.input_file,
            "model_provider": model_provider,
            "model_name": model_name,
            "run_label": run_label,
        },
    }
    return payload


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    campaign = get_llm_campaign(args.campaign_id)
    if campaign is None:
        raise SystemExit(f"Unknown campaign id: {args.campaign_id}")
    if campaign.model_provider is None or campaign.model_name is None:
        raise SystemExit(f"Campaign missing model metadata: {args.campaign_id}")
    if re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])", args.run_day) is None:
        raise SystemExit("run-day must match YYYY-MM-DD")

    manifest_payload = _load_json(args.manifest)
    if not isinstance(manifest_payload, dict):
        raise SystemExit(f"manifest root invalid: {args.manifest}")
    manifest_campaign = manifest_payload.get("campaign")
    if not isinstance(manifest_campaign, dict):
        raise SystemExit("manifest missing campaign block")
    if manifest_campaign.get("campaign_id") != args.campaign_id:
        raise SystemExit(
            "manifest campaign_id mismatch: "
            + f"got {manifest_campaign.get('campaign_id')!r}, expected {args.campaign_id!r}"
        )

    entries, run_pack_path = _build_manifest_entries(manifest_payload)
    if not run_pack_path.exists():
        raise SystemExit(f"run-pack path not found: {run_pack_path}")

    written = 0
    for entry in entries:
        input_abs = (run_pack_path / entry.input_file).resolve()
        if not input_abs.exists():
            raise SystemExit(f"input file missing for entry: {input_abs}")
        input_payload = _load_json(input_abs)
        if not isinstance(input_payload, dict):
            raise SystemExit(f"input payload must be object: {input_abs}")
        for detector in entry.detectors:
            payload = _build_output_payload(
                entry=entry,
                detector_id=detector.detector_id,
                input_payload=input_payload,
                model_provider=campaign.model_provider,
                model_name=campaign.model_name,
                run_day=args.run_day,
            )
            if not args.dry_run:
                _write_json(detector.expected_output_path, payload)
            written += 1

    print(
        "Codex campaign generation complete: "
        + f"targets={written}, dry_run={args.dry_run}, "
        + f"campaign_id={args.campaign_id}, script={SCRIPT_VERSION}"
    )


if __name__ == "__main__":
    main()
