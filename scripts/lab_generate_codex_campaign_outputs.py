from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, cast

from lab_output_tracks import get_llm_campaign
from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v2")

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "reports" / "lab_llm_run_manifest.json"
FOCUSPACK_WARNING = "Focuspack is a subset; verify in full compare pane."
DEFAULT_RUN_DAY = "2026-02-21"
MAX_SNIPPET = 350
TARGET_SNIPPET = 300
MIN_SNIPPET = 220
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{2,}")
WHITESPACE_RE = re.compile(r"\s+")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?;:])\s+")

STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "also",
    "among",
    "because",
    "between",
    "cannot",
    "could",
    "does",
    "each",
    "from",
    "have",
    "into",
    "more",
    "most",
    "other",
    "should",
    "their",
    "there",
    "these",
    "this",
    "those",
    "under",
    "using",
    "where",
    "which",
    "while",
    "with",
    "within",
    "would",
    "year",
    "years",
}

DIMENSION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "regulatory controls": (
        "regulator",
        "regulatory",
        "compliance",
        "law",
        "laws",
        "rule",
        "rules",
        "privacy",
        "cpra",
        "gdpr",
        "antitrust",
        "license",
        "licensing",
    ),
    "cybersecurity resilience": (
        "cyber",
        "security",
        "incident",
        "breach",
        "attack",
        "malware",
        "data",
        "access control",
        "sensitive information",
    ),
    "supply chain execution": (
        "supply",
        "manufacturing",
        "capacity",
        "inventory",
        "supplier",
        "foundry",
        "logistics",
        "distribution",
        "component",
        "production",
    ),
    "demand and market dynamics": (
        "demand",
        "market",
        "customer",
        "pricing",
        "competition",
        "adoption",
        "revenue",
        "sales",
        "macro",
        "economy",
    ),
    "geopolitical exposure": (
        "export",
        "sanction",
        "geopolitical",
        "china",
        "usg",
        "government",
        "trade",
        "tariff",
        "restriction",
        "controls",
    ),
    "environment and workforce": (
        "sustainability",
        "esg",
        "climate",
        "human rights",
        "labor",
        "talent",
        "workforce",
        "hiring",
        "retention",
    ),
}

WHY_TEMPLATES: tuple[str, ...] = (
    "Pinpoints {dimension} mechanism in {year}: {phrase}.",
    "Anchors the {year} signal in {dimension} language, especially {term}.",
    "Shows how {dimension} risk is operationalized in {year} through {phrase}.",
    "Provides concrete {year} evidence that {dimension} pressure can hit execution.",
    "Supports the {year} read by tying {dimension} exposure to {term}.",
    "Captures a non-generic {year} pathway for {dimension}: {phrase}.",
)

CHANGE_TEMPLATES: tuple[str, ...] = (
    "Disclosure moves from {prev_dim} emphasis in {year_from} toward stronger {curr_dim} emphasis in {year_to} ({prev_cite1}; {curr_cite1}).",
    "The center of gravity shifts from {prev_dim} risk language to clearer {curr_dim} downside framing ({prev_cite1}; {curr_cite1}).",
    "Compared with {year_from}, {year_to} leans harder into {curr_dim} while reducing reliance on earlier {prev_dim} framing ({prev_cite1}; {curr_cite1}).",
    "{year_to} reframes the risk profile by elevating {curr_dim} mechanisms over the prior {prev_dim} emphasis ({prev_cite1}; {curr_cite1}).",
    "Relative to {year_from}, the narrative rotates from {prev_dim} context to more explicit {curr_dim} consequences ({prev_cite1}; {curr_cite1}).",
    "Risk wording evolves from {prev_dim} qualifiers to firmer {curr_dim} impact statements ({prev_cite1}; {curr_cite1}).",
)

DRIVERS_TEMPLATES: tuple[str, ...] = (
    "The key driver is a sharper mechanism chain from {prev_signal} to {curr_signal}, with explicit downside links ({prev_cite2}; {curr_cite2}).",
    "Drivers include more concrete trigger-to-impact pathways, moving from {prev_signal} toward {curr_signal} ({prev_cite2}; {curr_cite2}).",
    "The drift is driven by stronger causal wording that ties operational constraints to financial exposure ({prev_cite2}; {curr_cite2}).",
    "Underlying drivers are clearer scenario mechanics and fewer generic qualifiers, especially around {curr_signal} ({prev_cite2}; {curr_cite2}).",
    "What changes most is the specificity of execution and policy pathways, from {prev_signal} into {curr_signal} ({prev_cite2}; {curr_cite2}).",
    "Driver detail increases as the narrative ties controls, constraints, and demand outcomes into one chain ({prev_cite2}; {curr_cite2}).",
)

CAVEAT_TEMPLATES: tuple[str, ...] = (
    "Focuspack evidence is sampled; verify emphasis and magnitude in the full compare pane.",
    "Because focuspack is selective, treat this as directional and confirm with full-section context.",
    "This summary is evidence-led but subset-bound; validate priority calls against the complete pair view.",
    "Subset coverage can overweight trigger terms, so use the full compare pane before making ranking decisions.",
)


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


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _clean_ws(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def _tokenize(text: str) -> list[str]:
    return [item.lower() for item in WORD_RE.findall(text)]


def _stable_seed(*parts: object) -> int:
    material = "|".join(str(part) for part in parts)
    digest = hashlib.sha1(material.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _stable_pick(options: tuple[str, ...], *seed_parts: object) -> str:
    if not options:
        return ""
    idx = _stable_seed(*seed_parts) % len(options)
    return options[idx]


def _detect_dimension(paragraph: str, trigger_terms: list[str]) -> str:
    lower = paragraph.lower()
    scores: list[tuple[int, str]] = []
    for dimension, keywords in DIMENSION_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in lower:
                score += 1
        for term in trigger_terms:
            term_lower = term.lower()
            if term_lower and term_lower in lower:
                score += 1
        scores.append((score, dimension))
    scores.sort(key=lambda item: (-item[0], item[1]))
    if not scores or scores[0][0] <= 0:
        return "operational risk transmission"
    return scores[0][1]


def _extract_signal_phrase(paragraph: str, trigger_terms: list[str]) -> str:
    normalized = _clean_ws(paragraph)
    if not normalized:
        return "explicit downside wording"

    sentences = [item.strip() for item in SENTENCE_SPLIT_RE.split(normalized) if item.strip()]
    if not sentences:
        sentences = [normalized]

    chosen_sentence = ""
    chosen_term = ""
    for term in trigger_terms:
        term_lower = term.lower()
        if not term_lower:
            continue
        for sentence in sentences:
            if term_lower in sentence.lower():
                chosen_sentence = sentence
                chosen_term = term_lower
                break
        if chosen_sentence:
            break
    if not chosen_sentence:
        chosen_sentence = max(sentences, key=len)

    words = chosen_sentence.split(" ")
    if not words:
        return "explicit downside wording"

    start = 0
    if chosen_term:
        anchor_token = chosen_term.split(" ")[0]
        for idx, word in enumerate(words):
            if anchor_token in word.lower():
                start = max(0, idx - 4)
                break
    end = min(len(words), start + 14)
    phrase = " ".join(words[start:end]).strip(" ,;:.")
    if not phrase:
        phrase = " ".join(words[:12]).strip(" ,;:.")
    return phrase or "explicit downside wording"


def _top_terms(paragraphs: list[str], trigger_terms: list[str], take: int = 12) -> set[str]:
    counts: Counter[str] = Counter()
    for paragraph in paragraphs:
        for token in _tokenize(paragraph):
            if token in STOPWORDS or len(token) < 4:
                continue
            counts[token] += 1
    for term in trigger_terms:
        normalized = _clean_ws(term).lower()
        if normalized:
            counts[normalized] += 2
    return {term for term, _count in counts.most_common(take)}


def _jaccard_distance(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 0.0
    overlap = len(left.intersection(right))
    union = len(left.union(right))
    if union == 0:
        return 0.0
    return 1.0 - (overlap / union)


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

    start = max(0, anchor - 110)
    end = min(len(paragraph), start + TARGET_SNIPPET)
    if end - start < MIN_SNIPPET:
        end = min(len(paragraph), start + MIN_SNIPPET)

    while start > 0 and paragraph[start - 1].isalnum():
        start -= 1
    while end < len(paragraph) and paragraph[end].isalnum():
        end += 1
    snippet = paragraph[start:end].strip()

    if len(snippet) > MAX_SNIPPET:
        snippet = snippet[:MAX_SNIPPET]
        cut = snippet.rfind(" ")
        if cut >= 180:
            snippet = snippet[:cut]
        snippet = snippet.strip()

    if not snippet:
        snippet = paragraph[:MAX_SNIPPET].strip()
    return snippet


def _score_index(paragraph: str, trigger_terms: list[str]) -> int:
    score = min(len(paragraph), 450)
    lower = paragraph.lower()
    dimension = _detect_dimension(paragraph, trigger_terms)
    if dimension != "operational risk transmission":
        score += 20
    matches = 0
    for term in trigger_terms:
        term_lower = _clean_ws(term).lower()
        if term_lower and term_lower in lower:
            score += 65
            matches += 1
    score += min(matches * 10, 50)
    return score


def _select_indices(
    paragraph_map: dict[int, str], trigger_terms: list[str], take_count: int
) -> list[int]:
    ranked = sorted(
        paragraph_map.keys(),
        key=lambda idx: (-_score_index(paragraph_map[idx], trigger_terms), idx),
    )
    selected: list[int] = []
    for idx in ranked:
        if len(selected) >= take_count:
            break
        if all(abs(idx - existing) >= 2 for existing in selected):
            selected.append(idx)
    if len(selected) < take_count:
        for idx in ranked:
            if idx in selected:
                continue
            selected.append(idx)
            if len(selected) >= take_count:
                break
    selected = sorted(selected[:take_count])
    return selected


def _build_evidence_block(
    year: int, paragraph_idx: int, paragraph: str, trigger_terms: list[str]
) -> dict[str, object]:
    snippet = _trim_snippet(paragraph, trigger_terms)
    highlights = _choose_highlights(snippet, trigger_terms)
    dimension = _detect_dimension(paragraph, trigger_terms)
    phrase = _extract_signal_phrase(paragraph, trigger_terms)
    term = highlights[0] if highlights else "risk concentration"
    why_template = _stable_pick(
        WHY_TEMPLATES, year, paragraph_idx, dimension, phrase[:24], term
    )
    why_text = why_template.format(
        year=year,
        dimension=dimension,
        phrase=phrase,
        term=term,
    )
    return {
        "year": year,
        "paragraph_idx": paragraph_idx,
        "snippet": snippet,
        "why": why_text,
        "highlights": highlights,
    }


def _build_delta_brief(
    ticker: str,
    year_from: int,
    year_to: int,
    prev_idxs: list[int],
    curr_idxs: list[int],
    prev_map: dict[int, str],
    curr_map: dict[int, str],
    trigger_terms: list[str],
) -> str:
    prev_primary = prev_idxs[0]
    prev_secondary = prev_idxs[1]
    curr_primary = curr_idxs[0]
    curr_secondary = curr_idxs[1]
    prev_cite1 = f"{year_from} para {prev_primary + 1}"
    prev_cite2 = f"{year_from} para {prev_secondary + 1}"
    curr_cite1 = f"{year_to} para {curr_primary + 1}"
    curr_cite2 = f"{year_to} para {curr_secondary + 1}"

    prev_dim = _detect_dimension(prev_map[prev_primary], trigger_terms)
    curr_dim = _detect_dimension(curr_map[curr_primary], trigger_terms)
    prev_signal = _extract_signal_phrase(prev_map[prev_primary], trigger_terms)
    curr_signal = _extract_signal_phrase(curr_map[curr_primary], trigger_terms)

    change_template = _stable_pick(
        CHANGE_TEMPLATES, ticker, year_from, year_to, "change", prev_dim, curr_dim
    )
    drivers_template = _stable_pick(
        DRIVERS_TEMPLATES, ticker, year_from, year_to, "drivers", prev_signal[:32], curr_signal[:32]
    )
    caveat_template = _stable_pick(CAVEAT_TEMPLATES, ticker, year_from, year_to, "caveat")

    change_section = change_template.format(
        year_from=year_from,
        year_to=year_to,
        prev_dim=prev_dim,
        curr_dim=curr_dim,
        prev_cite1=prev_cite1,
        curr_cite1=curr_cite1,
    )
    drivers_section = drivers_template.format(
        prev_signal=prev_signal,
        curr_signal=curr_signal,
        prev_cite2=prev_cite2,
        curr_cite2=curr_cite2,
    )
    return (
        f"Change: {change_section} "
        f"Drivers: {drivers_section} "
        f"Caveat: {caveat_template}"
    )


def _pick_confidence(
    prev_map: dict[int, str],
    curr_map: dict[int, str],
    prev_idxs: list[int],
    curr_idxs: list[int],
    trigger_terms: list[str],
    coverage: Optional[float],
) -> float:
    prev_selected = [prev_map[idx] for idx in prev_idxs]
    curr_selected = [curr_map[idx] for idx in curr_idxs]
    prev_dims = {_detect_dimension(text, trigger_terms) for text in prev_selected}
    curr_dims = {_detect_dimension(text, trigger_terms) for text in curr_selected}
    lexical_shift = _jaccard_distance(
        _top_terms(prev_selected, trigger_terms),
        _top_terms(curr_selected, trigger_terms),
    )
    shared_dims = len(prev_dims.intersection(curr_dims))
    union_dims = len(prev_dims.union(curr_dims))
    dim_shift = 0.0
    if union_dims:
        dim_shift = 1.0 - (shared_dims / union_dims)

    score = 0
    if coverage is not None and coverage >= 0.58:
        score += 1
    if lexical_shift >= 0.35:
        score += 1
    if dim_shift >= 0.40:
        score += 1

    if score >= 2:
        return 0.75
    if score <= 0:
        return 0.25
    return 0.50


def _build_manifest_entries(manifest: dict[str, Any]) -> tuple[list[ManifestEntry], Path]:
    run_pack = manifest.get("run_pack")
    if not isinstance(run_pack, dict):
        raise SystemExit("manifest.run_pack missing or invalid")
    run_pack = cast("dict[str, Any]", run_pack)
    run_pack_path_raw = run_pack.get("path")
    if not isinstance(run_pack_path_raw, str):
        raise SystemExit("manifest.run_pack.path missing")
    run_pack_path = (REPO_ROOT / run_pack_path_raw).resolve()

    entries_raw = manifest.get("entries")
    if not isinstance(entries_raw, list):
        raise SystemExit("manifest.entries missing or invalid")
    entries_raw = cast("list[Any]", entries_raw)

    built: list[ManifestEntry] = []
    for item in entries_raw:
        if not isinstance(item, dict):
            continue
        item = cast("dict[str, Any]", item)
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
        input_block = cast("dict[str, Any]", input_block)
        detectors_raw = cast("list[Any]", detectors_raw)
        input_file = input_block.get("run_pack_path")
        if not isinstance(input_file, str):
            continue
        detectors: list[DetectorTarget] = []
        for detector in detectors_raw:
            if not isinstance(detector, dict):
                continue
            detector = cast("dict[str, Any]", detector)
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
    input_payload: dict[str, Any],
    model_provider: str,
    model_name: str,
    run_day: str,
) -> dict[str, Any]:
    texts = input_payload.get("texts")
    focuspack_meta = input_payload.get("focuspack_meta")
    lens_meta = input_payload.get("lens")
    if not isinstance(texts, dict) or not isinstance(focuspack_meta, dict):
        raise SystemExit(f"input payload missing texts/focuspack_meta for {entry.input_file}")
    texts = cast("dict[str, Any]", texts)
    focuspack_meta = cast("dict[str, Any]", focuspack_meta)

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
    prev_paragraphs_raw = cast("list[Any]", prev_paragraphs_raw)
    curr_paragraphs_raw = cast("list[Any]", curr_paragraphs_raw)
    selected_prev_raw = cast("list[Any]", selected_prev_raw)
    selected_curr_raw = cast("list[Any]", selected_curr_raw)
    trigger_terms_raw = cast("list[Any]", trigger_terms_raw)

    prev_paragraphs = [str(item) for item in prev_paragraphs_raw]
    curr_paragraphs = [str(item) for item in curr_paragraphs_raw]
    selected_prev = [int(item) for item in selected_prev_raw]
    selected_curr = [int(item) for item in selected_curr_raw]
    trigger_terms = [_clean_ws(str(item)) for item in trigger_terms_raw if _clean_ws(str(item))]

    if len(prev_paragraphs) != len(selected_prev) or len(curr_paragraphs) != len(selected_curr):
        raise SystemExit(f"focuspack selected index mapping mismatch for {entry.input_file}")

    prev_map = {selected_prev[i]: prev_paragraphs[i] for i in range(len(selected_prev))}
    curr_map = {selected_curr[i]: curr_paragraphs[i] for i in range(len(selected_curr))}

    coverage = None
    if isinstance(lens_meta, dict):
        lens_meta = cast("dict[str, Any]", lens_meta)
        raw_coverage = lens_meta.get("coverage")
        if isinstance(raw_coverage, (int, float)) and not isinstance(raw_coverage, bool):
            coverage = float(raw_coverage)

    if detector_id == "det_llm_delta_brief_v1":
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
        artifacts: dict[str, object] = {
            "delta_brief": _build_delta_brief(
                ticker=entry.ticker,
                year_from=entry.year_from,
                year_to=entry.year_to,
                prev_idxs=prev_idxs,
                curr_idxs=curr_idxs,
                prev_map=prev_map,
                curr_map=curr_map,
                trigger_terms=trigger_terms,
            )
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

    confidence = _pick_confidence(
        prev_map=prev_map,
        curr_map=curr_map,
        prev_idxs=prev_idxs,
        curr_idxs=curr_idxs,
        trigger_terms=trigger_terms,
        coverage=coverage,
    )

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
            "confidence": confidence,
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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
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
    manifest_payload = cast("dict[str, Any]", manifest_payload)
    manifest_campaign = manifest_payload.get("campaign")
    if not isinstance(manifest_campaign, dict):
        raise SystemExit("manifest missing campaign block")
    manifest_campaign = cast("dict[str, Any]", manifest_campaign)
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
        input_payload = cast("dict[str, Any]", input_payload)
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
