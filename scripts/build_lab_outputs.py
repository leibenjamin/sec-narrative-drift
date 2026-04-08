"""Deterministic analysis pipeline for SEC filing sections.

This script produces all deterministic (non-LLM) artifacts for the Document
Protocol Lab.  It handles:

  - Loading extracted filing text from cached EDGAR HTML or pre-extracted
    plain-text files (no LLM involvement).
  - Paragraph splitting via whitespace heuristics (no LLM involvement).
  - The **deboilerplated** cleaning lens: a sentence-level exact-match
    set-difference filter that removes sentences shared verbatim between
    adjacent filing years.  This is a pure string operation (normalize,
    intersect, subtract) with no LLM or semantic-similarity step.
  - Running the six deterministic detectors (log-odds, JSD, MinHash,
    winnowing, structure, RBO agreement).

No LLM or ML model is invoked anywhere in this script.  All outputs are
fully reproducible from the same input text.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, cast

from sec_cache import load_gz_text, load_json, risk_text_path, ticker_year_index_path
from sec_extract_item1a import extract_item1a_from_html, split_paragraphs
from sec_metrics import (
    DF_PENALTY_EPS,
    DF_PENALTY_FLOOR,
    DF_PENALTY_GAMMA_PHRASE,
    DF_PENALTY_GAMMA_UNI,
    DF_PENALTY_OVERRIDE_COUNT,
    DF_PENALTY_OVERRIDE_MAX_DF_FRAC,
    DF_PENALTY_OVERRIDE_MIN_PENALTY,
    DF_PENALTY_OVERRIDE_Z,
    NO_DISTINCTIVE_COUNT_MIN,
    NO_DISTINCTIVE_Z_MIN,
    PRIOR_FLOOR,
    PRIOR_MASS_DEFAULT,
    SCORE_DF_MIN,
    bigrams as sec_bigrams,
    build_shift_summary,
    canonicalize_counts,
    count_allowlist_phrases,
    extract_terms,
    get_canonical_terms,
    merge_includes,
    pmi_keep_bigrams,
    tokenize as sec_tokenize,
    tokenize_segments,
    textrank_keyphrases,
)
from sec_segments import segment_text_v1
from lab_script_version import build_script_version

LAB_SCHEMA_VERSION = "1.0"
SCRIPT_VERSION = build_script_version(Path(__file__), "v2")
DEFAULT_SECTION = "10k_item1a"
DEFAULT_SOURCE = "edgar"
DEFAULT_LENSES = ["raw", "deboilerplated"]
DEFAULT_DETECTORS = [
    "det_logodds_terms_v1",
    "det_jsd_ngrams_v1",
    "det_minhash_boilerplate_v1",
    "det_winnowing_fingerprint_v1",
    "det_structure_artifacts_v1",
    "det_rbo_agreement_v1",
]

RAW_LENS = "raw"
DEBOILER_LENS = "deboilerplated"
STUB_LENSES = {"stage1_clean", "structure_aware"}

TOKEN_RE = re.compile(r"[a-z]{2,}")
WHITESPACE_RE = re.compile(r"\s+")

def _load_stopwords() -> set[str]:
    try:
        from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

        return set(ENGLISH_STOP_WORDS)
    except Exception:
        return {
            "the",
            "and",
            "for",
            "with",
            "that",
            "this",
            "from",
            "are",
            "was",
            "were",
            "will",
            "shall",
            "may",
            "might",
            "could",
            "should",
            "into",
            "over",
            "under",
            "such",
            "their",
            "there",
            "here",
            "have",
            "has",
            "had",
            "our",
            "its",
            "but",
            "not",
            "any",
            "all",
            "can",
        }


STOPWORDS: set[str] = _load_stopwords()


@dataclass(frozen=True)
class SectionText:
    year: int
    text: str
    paragraphs: list[str]


@dataclass(frozen=True)
class LensPair:
    prev: SectionText
    curr: SectionText
    coverage: Optional[float]
    warnings: list[str]
    lens: str


@dataclass(frozen=True)
class CaseSpec:
    ticker: str
    year_from: int
    year_to: int
    section: str
    why_interesting: str
    expected_detectors: list[str]
    tags: list[str]



def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            value = result.stdout.strip()
            if value:
                return value
    except Exception:
        return "unknown"
    return "unknown"


def as_str_dict(value: Any) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    output: dict[str, Any] = {}
    typed_dict = cast(dict[Any, Any], value)
    for key, item in typed_dict.items():
        if not isinstance(key, str):
            return None
        output[key] = item
    return output


def as_list(value: Any) -> Optional[list[Any]]:
    if isinstance(value, list):
        return cast(list[Any], value)
    return None


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def parse_pairs(raw: str) -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []
    if not raw:
        return pairs
    for item in raw.split(","):
        cleaned = item.strip()
        if not cleaned:
            continue
        if "-" not in cleaned:
            continue
        left, right = cleaned.split("-", 1)
        if not left.isdigit() or not right.isdigit():
            continue
        year_from = int(left)
        year_to = int(right)
        if year_from == year_to:
            continue
        if year_from > year_to:
            year_from, year_to = year_to, year_from
        pairs.append((year_from, year_to))
    return pairs


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    if not text:
        return tokens
    lowered = text.lower()
    for match in TOKEN_RE.findall(lowered):
        if match in STOPWORDS:
            continue
        tokens.append(match)
    return tokens


def build_bigrams(tokens: list[str]) -> list[str]:
    output: list[str] = []
    if len(tokens) < 2:
        return output
    for idx in range(len(tokens) - 1):
        output.append(f"{tokens[idx]} {tokens[idx + 1]}")
    return output


def normalize_sentence(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text.strip()).lower()


def extract_sentences(text: str) -> list[str]:
    payload = segment_text_v1(text)
    sentences: list[str] = []
    raw_sentences = payload.get("sentences")
    if not isinstance(raw_sentences, list):
        return sentences
    typed_sentences = cast(list[Any], raw_sentences)
    for entry in typed_sentences:
        if not isinstance(entry, dict):
            continue
        entry_dict = cast(dict[str, Any], entry)
        start: Any = entry_dict.get("start")
        end: Any = entry_dict.get("end")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if start < 0 or end <= start or end > len(text):
            continue
        sentences.append(text[start:end])
    return sentences


def build_paragraphs(text: str, min_chars: int = 200) -> list[str]:
    paragraphs = split_paragraphs(text, min_chars=min_chars)
    cleaned: list[str] = []
    for para in paragraphs:
        trimmed = para.strip()
        if trimmed:
            cleaned.append(trimmed)
    return cleaned



def section_suffix(section: str) -> str:
    lowered = section.lower()
    if lowered.endswith("item1a"):
        return "item_1a"
    if lowered.endswith("item3d"):
        return "item_3d"
    if "item1a" in lowered:
        return "item_1a"
    if "item3d" in lowered:
        return "item_3d"
    return section


def find_cached_html(root: Path, ticker: str, year: int) -> Optional[Path]:
    cache_dir = root / "scripts" / "_cache" / ticker.upper()
    if not cache_dir.exists():
        return None
    candidates: list[Path] = []
    year_token = str(year)
    for path in cache_dir.glob("*.htm*"):
        name = path.name.lower()
        if year_token in name:
            candidates.append(path)
    if not candidates:
        return None
    candidates.sort(key=lambda item: item.name)
    return candidates[0]


def find_cached_sec_risk_text(ticker: str, year: int) -> Optional[Path]:
    index_path = ticker_year_index_path()
    index_raw = load_json(index_path)
    if not isinstance(index_raw, dict):
        return None
    index_payload = cast(dict[str, Any], index_raw)

    ticker_raw = index_payload.get(ticker.upper())
    if not isinstance(ticker_raw, dict):
        return None
    ticker_payload = cast(dict[str, Any], ticker_raw)

    year_raw = ticker_payload.get(str(year))
    if not isinstance(year_raw, dict):
        return None
    year_payload = cast(dict[str, Any], year_raw)

    cik: str | None = year_payload.get("cik")
    accession: str | None = year_payload.get("accession")
    form_type: str | None = year_payload.get("formType")
    if not isinstance(cik, str) or not isinstance(accession, str) or not isinstance(form_type, str):
        return None

    path = risk_text_path(cik, accession, form_type)
    if path.exists():
        return path
    return None


def load_section_text(
    ticker: str,
    year: int,
    section: str,
    source_id: str,
    root: Path,
) -> Optional[SectionText]:
    if source_id != "edgar":
        return None
    suffix = section_suffix(section)
    filename = f"{ticker.upper()}_{year}_{suffix}.txt"
    path = root / "scripts" / "_reports" / "risk_extraction_bundle" / "sections" / filename
    if path.exists():
        text = path.read_text(encoding="utf-8", errors="replace")
        paragraphs = build_paragraphs(text, min_chars=200)
        return SectionText(year=year, text=text, paragraphs=paragraphs)

    sec_risk_text = find_cached_sec_risk_text(ticker, year)
    if sec_risk_text is not None:
        text = load_gz_text(sec_risk_text)
        if text:
            paragraphs = build_paragraphs(text, min_chars=200)
            return SectionText(year=year, text=text, paragraphs=paragraphs)

    cached_html = find_cached_html(root, ticker, year)
    if cached_html is None:
        return None
    html = cached_html.read_text(encoding="utf-8", errors="replace")
    section_text, _confidence, _method, _errors, _debug = extract_item1a_from_html(html)
    if not section_text:
        return None
    paragraphs = build_paragraphs(section_text, min_chars=200)
    return SectionText(year=year, text=section_text, paragraphs=paragraphs)


def build_deboilerplated_pair(prev_text: str, curr_text: str) -> tuple[list[str], list[str], dict[str, int]]:
    """Remove sentences shared verbatim between adjacent filing years.

    Algorithm:
      1. Split each year's text into sentences.
      2. Normalize each sentence (lowercase, collapse whitespace).
      3. Compute the set intersection of normalized sentences.
      4. Retain only sentences whose normalized form is NOT in the
         shared set.

    This is a deterministic exact-match string filter.  No LLM, no
    semantic similarity, and no ML is involved.  The filter removes
    recurring legal boilerplate that companies copy-paste year to year,
    leaving the sentences that actually changed between filings.
    """
    prev_sentences = extract_sentences(prev_text)
    curr_sentences = extract_sentences(curr_text)

    prev_norm: list[str] = []
    for sentence in prev_sentences:
        norm = normalize_sentence(sentence)
        if norm:
            prev_norm.append(norm)
    curr_norm: list[str] = []
    for sentence in curr_sentences:
        norm = normalize_sentence(sentence)
        if norm:
            curr_norm.append(norm)

    prev_norm_set = set(prev_norm)
    curr_norm_set = set(curr_norm)
    shared_norm = prev_norm_set & curr_norm_set

    prev_retained: list[str] = []
    for sentence, norm in zip(prev_sentences, prev_norm):
        if norm not in shared_norm:
            prev_retained.append(sentence)
    curr_retained: list[str] = []
    for sentence, norm in zip(curr_sentences, curr_norm):
        if norm not in shared_norm:
            curr_retained.append(sentence)

    stats = {
        "prev_sentence_count": len(prev_norm),
        "curr_sentence_count": len(curr_norm),
        "shared_sentence_count": len(shared_norm),
        "prev_retained_count": len(prev_retained),
        "curr_retained_count": len(curr_retained),
    }
    return prev_retained, curr_retained, stats


def build_lens_pair(
    prev: SectionText,
    curr: SectionText,
    lens: str,
) -> LensPair:
    warnings: list[str] = []
    coverage: Optional[float] = None

    if lens == RAW_LENS:
        return LensPair(prev=prev, curr=curr, coverage=1.0, warnings=warnings, lens=lens)

    if lens == DEBOILER_LENS:
        prev_retained, curr_retained, stats = build_deboilerplated_pair(prev.text, curr.text)
        if not prev_retained or not curr_retained:
            warnings.append("fallback_to_raw")
            return LensPair(prev=prev, curr=curr, coverage=1.0, warnings=warnings, lens=lens)

        prev_text = "\n\n".join(prev_retained)
        curr_text = "\n\n".join(curr_retained)
        raw_prev_len = max(1, len(prev.text))
        raw_curr_len = max(1, len(curr.text))
        coverage = min(len(prev_text) / raw_prev_len, len(curr_text) / raw_curr_len)

        prev_paragraphs = build_paragraphs(prev_text, min_chars=120)
        curr_paragraphs = build_paragraphs(curr_text, min_chars=120)
        prev_section = SectionText(year=prev.year, text=prev_text, paragraphs=prev_paragraphs)
        curr_section = SectionText(year=curr.year, text=curr_text, paragraphs=curr_paragraphs)

        if stats.get("prev_retained_count", 0) < 5 or stats.get("curr_retained_count", 0) < 5:
            warnings.append("low_retained_text")

        return LensPair(prev=prev_section, curr=curr_section, coverage=coverage, warnings=warnings, lens=lens)

    if lens in STUB_LENSES:
        warnings.append("lens_stub_fallback")
        return LensPair(prev=prev, curr=curr, coverage=1.0, warnings=warnings, lens=lens)

    warnings.append("unknown_lens_fallback")
    return LensPair(prev=prev, curr=curr, coverage=1.0, warnings=warnings, lens=lens)


def build_output_filename(
    section: str,
    year_from: int,
    year_to: int,
    detector_id: str,
    lens: str,
    source_id: str,
) -> str:
    return f"lab_{section}_{year_from}_{year_to}_{detector_id}_{lens}_{source_id}.json"


def build_provenance(inputs: dict[str, str]) -> dict[str, Any]:
    return {
        "build_utc": now_utc_iso(),
        "git_commit": get_git_commit(),
        "script_version": SCRIPT_VERSION,
        "inputs": inputs,
    }


def make_metrics(
    drift_score: Optional[float],
    confidence: Optional[float],
    coverage: Optional[float],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "drift_score": drift_score,
        "confidence": confidence,
        "coverage": coverage,
        "warnings": warnings,
    }


def find_paragraphs_with_terms(
    paragraphs: list[str],
    terms: list[str],
    max_hits: int = 3,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    if not paragraphs or not terms:
        return hits
    lowered_terms = [term.lower() for term in terms if term]
    for idx, paragraph in enumerate(paragraphs):
        para_lower = paragraph.lower()
        matched: list[str] = []
        for term in lowered_terms:
            if term and term in para_lower:
                matched.append(term)
        if matched:
            hits.append(
                {
                    "paragraph_idx": idx,
                    "snippet": paragraph,
                    "highlights": matched,
                }
            )
        if len(hits) >= max_hits:
            break
    return hits



def resolve_prior_mass() -> float:
    raw = os.getenv("TERM_SHIFT_PRIOR_MASS")
    if raw:
        try:
            value = float(raw)
            if value > 0:
                return value
        except ValueError:
            pass
    return PRIOR_MASS_DEFAULT


def build_primary_term_counts_for_pair(
    prev_text: str,
    curr_text: str,
) -> tuple[Counter[str], Counter[str], dict[str, list[str]]]:
    pooled_tokens: list[list[str]] = []
    for text_value in (prev_text, curr_text):
        pooled_tokens.extend(tokenize_segments(text_value))
    bigram_keep = pmi_keep_bigrams(pooled_tokens)
    canonical_terms = get_canonical_terms()

    raw_counts: list[Counter[str]] = []
    for text_value in (prev_text, curr_text):
        counts: Counter[str] = Counter(sec_tokenize(text_value))
        for seg_tokens in tokenize_segments(text_value):
            for phrase in sec_bigrams(seg_tokens):
                if phrase in bigram_keep:
                    counts[phrase] += 1
        counts.update(count_allowlist_phrases(text_value))
        raw_counts.append(counts)

    if not canonical_terms:
        return raw_counts[0], raw_counts[1], {}

    prev_normalized, includes_prev = canonicalize_counts(raw_counts[0], canonical_terms)
    curr_normalized, includes_curr = canonicalize_counts(raw_counts[1], canonical_terms)
    includes_by_term = merge_includes(includes_prev, includes_curr)
    return prev_normalized, curr_normalized, includes_by_term


def build_alt_term_counts_for_pair(prev_text: str, curr_text: str) -> tuple[Counter[str], Counter[str]]:
    canonical_terms = get_canonical_terms()
    counts_by_text: list[Counter[str]] = []
    for text_value in (prev_text, curr_text):
        counts: Counter[str] = Counter()
        counts.update(textrank_keyphrases(text_value))
        counts.update(count_allowlist_phrases(text_value))
        if canonical_terms:
            normalized, _includes = canonicalize_counts(counts, canonical_terms)
            counts = normalized
        counts_by_text.append(counts)
    return counts_by_text[0], counts_by_text[1]


def build_year_df(counts_by_year: list[Counter[str]]) -> dict[str, int]:
    year_df: dict[str, int] = {}
    for counts in counts_by_year:
        for term in counts.keys():
            year_df[term] = year_df.get(term, 0) + 1
    return year_df


def compute_log_odds_stats(
    counts_prev: Counter[str],
    counts_curr: Counter[str],
    background_counts: Counter[str],
    total_background: int,
    prior_mass: float,
    year_df: dict[str, int],
    num_years: int,
) -> dict[str, dict[str, Any]]:
    vocab = set(counts_prev.keys()) | set(counts_curr.keys())
    if not vocab:
        return {}

    total_prev = sum(counts_prev.values())
    total_curr = sum(counts_curr.values())
    if total_prev <= 0 or total_curr <= 0:
        return {}

    uniform_prior = 1.0 / max(1, len(vocab))
    stats: dict[str, dict[str, Any]] = {}
    for term in vocab:
        count_prev = counts_prev.get(term, 0)
        count_curr = counts_curr.get(term, 0)
        if total_background > 0:
            background_prob = background_counts.get(term, 0) / total_background
        else:
            background_prob = uniform_prior

        alpha_i = max(prior_mass * background_prob, PRIOR_FLOOR)
        denom_prev = total_prev + prior_mass - (count_prev + alpha_i)
        denom_curr = total_curr + prior_mass - (count_curr + alpha_i)
        if denom_prev <= 0 or denom_curr <= 0:
            continue

        log_prev = math.log((count_prev + alpha_i) / denom_prev)
        log_curr = math.log((count_curr + alpha_i) / denom_curr)
        score = log_curr - log_prev
        z_value = score / math.sqrt((1 / (count_curr + alpha_i)) + (1 / (count_prev + alpha_i)))

        per10k_prev = count_prev / total_prev * 10000.0 if total_prev else 0.0
        per10k_curr = count_curr / total_curr * 10000.0 if total_curr else 0.0
        delta_per10k = per10k_curr - per10k_prev
        df_frac = year_df.get(term, 0) / num_years if num_years else 0.0
        distinctive = (
            abs(z_value) >= 2.0
            and max(count_prev, count_curr) >= 3
            and abs(delta_per10k) >= 0.25
            and df_frac <= 0.70
        )

        stats[term] = {
            "term": term,
            "score": score,
            "z": z_value,
            "countPrev": count_prev,
            "countCurr": count_curr,
            "per10kPrev": per10k_prev,
            "per10kCurr": per10k_curr,
            "deltaPer10k": delta_per10k,
            "distinctive": distinctive,
        }
    return stats


def build_df_penalty_scores(
    stats: dict[str, dict[str, Any]],
    year_df: dict[str, int],
    num_years: int,
) -> dict[str, float]:
    scores: dict[str, float] = {}
    if not num_years:
        return scores
    for term, item in stats.items():
        df_frac = year_df.get(term, 0) / num_years
        gamma = DF_PENALTY_GAMMA_PHRASE if " " in term else DF_PENALTY_GAMMA_UNI
        df_penalty = max(DF_PENALTY_FLOOR, (1 - df_frac + DF_PENALTY_EPS) ** gamma)
        if abs(float(item["z"])) >= DF_PENALTY_OVERRIDE_Z and max(int(item["countPrev"]), int(item["countCurr"])) >= DF_PENALTY_OVERRIDE_COUNT:
            if df_frac <= DF_PENALTY_OVERRIDE_MAX_DF_FRAC:
                df_penalty = max(df_penalty, DF_PENALTY_OVERRIDE_MIN_PENALTY)
        scores[term] = float(item["z"]) * df_penalty
    return scores


def build_ranked_shift_items(
    items: list[dict[str, Any]],
    includes_by_term: dict[str, list[str]],
    limit: int = 15,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for item in items[:limit]:
        term = item.get("term")
        if not isinstance(term, str):
            continue
        meta: dict[str, Any] = {
            "z": float(item.get("z", 0.0)),
            "countPrev": int(item.get("countPrev", 0)),
            "countCurr": int(item.get("countCurr", 0)),
            "per10kPrev": float(item.get("per10kPrev", 0.0)),
            "per10kCurr": float(item.get("per10kCurr", 0.0)),
            "deltaPer10k": float(item.get("deltaPer10k", 0.0)),
            "distinctive": bool(item.get("distinctive", False)),
        }
        includes = includes_by_term.get(term)
        if includes:
            meta["includes"] = list(includes)
        output.append({"label": term, "score": float(item.get("score", 0.0)), "meta": meta})
    return output


def build_ranked_alt_items(items: list[dict[str, Any]], limit: int = 15) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for item in items[:limit]:
        term = item.get("term")
        if not isinstance(term, str):
            continue
        output.append({"label": term, "score": float(item.get("score", 0.0))})
    return output


def compute_cosine_drift_from_counts(counts_prev: Counter[str], counts_curr: Counter[str]) -> Optional[float]:
    vocab = set(counts_prev.keys()) | set(counts_curr.keys())
    if not vocab:
        return None
    dot_product = 0.0
    prev_norm_sq = 0.0
    curr_norm_sq = 0.0
    for term in vocab:
        prev_value = float(counts_prev.get(term, 0))
        curr_value = float(counts_curr.get(term, 0))
        dot_product += prev_value * curr_value
        prev_norm_sq += prev_value * prev_value
        curr_norm_sq += curr_value * curr_value
    if prev_norm_sq <= 0.0 or curr_norm_sq <= 0.0:
        return None
    similarity = dot_product / math.sqrt(prev_norm_sq * curr_norm_sq)
    similarity = max(0.0, min(1.0, similarity))
    return round(1.0 - similarity, 6)


def det_logodds_terms_v1(
    root: Path,
    ticker: str,
    year_from: int,
    year_to: int,
    section: str,
    lens_pair: LensPair,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    del root, ticker, year_from, year_to, section
    warnings: list[str] = []

    counts_prev, counts_curr, includes_by_term = build_primary_term_counts_for_pair(
        lens_pair.prev.text,
        lens_pair.curr.text,
    )
    counts_prev_alt, counts_curr_alt = build_alt_term_counts_for_pair(
        lens_pair.prev.text,
        lens_pair.curr.text,
    )

    background_counts = Counter[str]()
    background_counts.update(counts_prev)
    background_counts.update(counts_curr)
    total_background = sum(background_counts.values())
    year_df = build_year_df([counts_prev, counts_curr])
    num_years = 2
    prior_mass = resolve_prior_mass()

    stats = compute_log_odds_stats(
        counts_prev,
        counts_curr,
        background_counts,
        total_background,
        prior_mass,
        year_df,
        num_years,
    )
    fallback_scores = build_df_penalty_scores(stats, year_df, num_years)

    has_distinctive = any(bool(item.get("distinctive")) for item in stats.values())
    fallback_items = [
        item
        for item in stats.values()
        if bool(item.get("distinctive")) or max(int(item.get("countPrev", 0)), int(item.get("countCurr", 0))) >= 2
    ]
    if not has_distinctive:
        filtered_items: list[dict[str, Any]] = []
        for item in fallback_items:
            term = item.get("term")
            if not isinstance(term, str):
                continue
            score_df = fallback_scores.get(term, float(item.get("z", 0.0)))
            if abs(score_df) < SCORE_DF_MIN:
                continue
            if not (
                abs(float(item.get("z", 0.0))) >= NO_DISTINCTIVE_Z_MIN
                or max(int(item.get("countPrev", 0)), int(item.get("countCurr", 0))) >= NO_DISTINCTIVE_COUNT_MIN
            ):
                continue
            filtered_items.append(item)
        fallback_items = filtered_items

    for term, item in stats.items():
        item["score"] = fallback_scores.get(term, float(item.get("z", 0.0)))

    def score_bucket(value: float) -> float:
        return round(value, 9)

    def sort_key_riser(item: dict[str, Any]) -> tuple[float, int, int, float, str]:
        term_value = item.get("term")
        term = term_value if isinstance(term_value, str) else ""
        score_df = fallback_scores.get(term, float(item.get("z", 0.0)))
        min_count = min(int(item.get("countPrev", 0)), int(item.get("countCurr", 0)))
        total_count = int(item.get("countPrev", 0)) + int(item.get("countCurr", 0))
        abs_delta = abs(float(item.get("deltaPer10k", 0.0)))
        return (-score_bucket(score_df), -min_count, -total_count, -abs_delta, term)

    def sort_key_faller(item: dict[str, Any]) -> tuple[float, int, int, float, str]:
        term_value = item.get("term")
        term = term_value if isinstance(term_value, str) else ""
        score_df = fallback_scores.get(term, float(item.get("z", 0.0)))
        min_count = min(int(item.get("countPrev", 0)), int(item.get("countCurr", 0)))
        total_count = int(item.get("countPrev", 0)) + int(item.get("countCurr", 0))
        abs_delta = abs(float(item.get("deltaPer10k", 0.0)))
        return (score_bucket(score_df), -min_count, -total_count, -abs_delta, term)

    riser_pool = [item for item in fallback_items if float(item.get("score", 0.0)) > 0]
    faller_pool = [item for item in fallback_items if float(item.get("score", 0.0)) < 0]
    sorted_risers = sorted(riser_pool, key=sort_key_riser)
    sorted_fallers = sorted(faller_pool, key=sort_key_faller)

    if has_distinctive:
        top_risers = build_ranked_shift_items(sorted_risers, includes_by_term)
        top_fallers = build_ranked_shift_items(sorted_fallers, includes_by_term)
    else:
        top_risers = build_ranked_shift_items(sorted_risers, includes_by_term) if len(sorted_risers) >= 3 else []
        top_fallers = build_ranked_shift_items(sorted_fallers, includes_by_term) if len(sorted_fallers) >= 3 else []

    if not has_distinctive:
        summary = "No strong distinctive term shifts detected."
    else:
        summary = build_shift_summary(extract_terms(top_risers), extract_terms(top_fallers))

    background_counts_alt = Counter[str]()
    background_counts_alt.update(counts_prev_alt)
    background_counts_alt.update(counts_curr_alt)
    total_background_alt = sum(background_counts_alt.values())
    year_df_alt = build_year_df([counts_prev_alt, counts_curr_alt])
    stats_alt = compute_log_odds_stats(
        counts_prev_alt,
        counts_curr_alt,
        background_counts_alt,
        total_background_alt,
        prior_mass,
        year_df_alt,
        num_years,
    )
    alt_risers = [item for item in stats_alt.values() if float(item.get("z", 0.0)) > 0]
    alt_fallers = [item for item in stats_alt.values() if float(item.get("z", 0.0)) < 0]
    sorted_risers_alt = sorted(alt_risers, key=lambda item: (-float(item.get("z", 0.0)), str(item.get("term", ""))))
    sorted_fallers_alt = sorted(alt_fallers, key=lambda item: (float(item.get("z", 0.0)), str(item.get("term", ""))))
    top_risers_alt = build_ranked_alt_items(sorted_risers_alt)
    top_fallers_alt = build_ranked_alt_items(sorted_fallers_alt)
    summary_alt = ""
    if top_risers_alt or top_fallers_alt:
        riser_terms_alt = [item["label"] for item in top_risers_alt if isinstance(item.get("label"), str)]
        faller_terms_alt = [item["label"] for item in top_fallers_alt if isinstance(item.get("label"), str)]
        summary_alt = build_shift_summary(riser_terms_alt, faller_terms_alt)

    min_primary_total = min(sum(counts_prev.values()), sum(counts_curr.values()))
    if min_primary_total < 500:
        warnings.append("thin_counts")
    if len(top_risers) < 3 or len(top_fallers) < 3:
        warnings.append("thin_counts")
    if not top_risers and not top_fallers:
        warnings.append("no_distinctive_terms")

    artifacts: dict[str, Any] = {
        "top_risers": top_risers,
        "top_fallers": top_fallers,
        "summary": summary,
        "ranked_items": [*top_risers, *top_fallers],
    }
    if top_risers_alt or top_fallers_alt:
        artifacts["top_risers_alt"] = top_risers_alt
        artifacts["top_fallers_alt"] = top_fallers_alt
        artifacts["summary_alt"] = summary_alt or summary

    evidence: list[dict[str, Any]] = []
    evidence_terms: list[str] = []
    for item in [*top_risers[:5], *top_fallers[:5]]:
        label = item.get("label")
        if isinstance(label, str) and label not in evidence_terms:
            evidence_terms.append(label)

    for hit in find_paragraphs_with_terms(lens_pair.curr.paragraphs, evidence_terms, max_hits=2):
        evidence.append(
            {
                "year": lens_pair.curr.year,
                "paragraph_idx": hit.get("paragraph_idx", 0),
                "snippet": hit.get("snippet", ""),
                "why": "Paragraph containing shifted term.",
                "highlights": hit.get("highlights", []),
            }
        )
    for hit in find_paragraphs_with_terms(lens_pair.prev.paragraphs, evidence_terms, max_hits=2):
        evidence.append(
            {
                "year": lens_pair.prev.year,
                "paragraph_idx": hit.get("paragraph_idx", 0),
                "snippet": hit.get("snippet", ""),
                "why": "Paragraph containing shifted term.",
                "highlights": hit.get("highlights", []),
            }
        )

    drift_score = compute_cosine_drift_from_counts(counts_prev, counts_curr)
    confidence = min(1.0, min_primary_total / 1000.0) if min_primary_total else 0.0
    metrics = make_metrics(drift_score, confidence, lens_pair.coverage, warnings + lens_pair.warnings)
    return artifacts, evidence, metrics


def jsd_contributions(
    counts_a: Counter[str],
    counts_b: Counter[str],
) -> tuple[float, list[tuple[str, float]]]:
    total_a = sum(counts_a.values())
    total_b = sum(counts_b.values())
    if total_a == 0 or total_b == 0:
        return 0.0, []

    contributions: list[tuple[str, float]] = []
    jsd = 0.0
    vocab = set(counts_a.keys()) | set(counts_b.keys())
    for term in vocab:
        p = counts_a.get(term, 0) / total_a
        q = counts_b.get(term, 0) / total_b
        m = 0.5 * (p + q)
        if p > 0:
            jsd += 0.5 * p * math.log(p / m, 2)
        if q > 0:
            jsd += 0.5 * q * math.log(q / m, 2)
        if m > 0:
            contrib = 0.0
            if p > 0:
                contrib += 0.5 * p * math.log(p / m, 2)
            if q > 0:
                contrib += 0.5 * q * math.log(q / m, 2)
            contributions.append((term, contrib))

    contributions.sort(key=lambda item: item[1], reverse=True)
    return jsd, contributions


def det_jsd_ngrams_v1(
    lens_pair: LensPair,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    warnings: list[str] = []

    tokens_prev = tokenize(lens_pair.prev.text)
    tokens_curr = tokenize(lens_pair.curr.text)

    counts_prev: Counter[str] = Counter(tokens_prev)
    counts_curr: Counter[str] = Counter(tokens_curr)

    bigrams_prev = build_bigrams(tokens_prev)
    bigrams_curr = build_bigrams(tokens_curr)
    counts_prev.update(bigrams_prev)
    counts_curr.update(bigrams_curr)

    jsd, contributions = jsd_contributions(counts_prev, counts_curr)

    ranked_items: list[dict[str, Any]] = []
    for term, score in contributions[:20]:
        ranked_items.append({"label": term, "score": float(score)})

    min_tokens = min(len(tokens_prev), len(tokens_curr))
    if min_tokens < 500:
        warnings.append("thin_counts")

    coverage = lens_pair.coverage
    confidence = min(1.0, (min_tokens / 1000.0)) if min_tokens else 0.0

    evidence: list[dict[str, Any]] = []
    top_terms = [item[0] for item in contributions[:5]]
    for hit in find_paragraphs_with_terms(lens_pair.curr.paragraphs, top_terms, max_hits=2):
        evidence.append(
            {
                "year": lens_pair.curr.year,
                "paragraph_idx": hit.get("paragraph_idx", 0),
                "snippet": hit.get("snippet", ""),
                "why": "Paragraph with high-contribution n-grams.",
                "highlights": hit.get("highlights", []),
            }
        )
    for hit in find_paragraphs_with_terms(lens_pair.prev.paragraphs, top_terms, max_hits=2):
        evidence.append(
            {
                "year": lens_pair.prev.year,
                "paragraph_idx": hit.get("paragraph_idx", 0),
                "snippet": hit.get("snippet", ""),
                "why": "Paragraph with high-contribution n-grams.",
                "highlights": hit.get("highlights", []),
            }
        )

    artifacts = {
        "ranked_items": ranked_items,
        "stats": {
            "jsd": round(jsd, 6),
            "tokens_prev": len(tokens_prev),
            "tokens_curr": len(tokens_curr),
        },
    }
    metrics = make_metrics(round(jsd, 6), confidence, coverage, warnings + lens_pair.warnings)
    return artifacts, evidence, metrics


def shingle_tokens(tokens: list[str], k: int = 5) -> set[int]:
    if len(tokens) < k:
        return set()
    hashes: set[int] = set()
    for idx in range(len(tokens) - k + 1):
        shingle = " ".join(tokens[idx : idx + k])
        digest = hashlib.sha1(shingle.encode("utf-8")).hexdigest()
        hashes.add(int(digest[:8], 16))
    return hashes


def jaccard(a: set[int], b: set[int]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def det_minhash_boilerplate_v1(
    lens_pair: LensPair,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    warnings: list[str] = []

    prev_paragraphs = lens_pair.prev.paragraphs
    curr_paragraphs = lens_pair.curr.paragraphs

    if len(prev_paragraphs) < 4 or len(curr_paragraphs) < 4:
        warnings.append("thin_counts")

    prev_sets: list[set[int]] = []
    for para in prev_paragraphs:
        tokens = tokenize(para)
        prev_sets.append(shingle_tokens(tokens, k=5))

    curr_sets: list[set[int]] = []
    for para in curr_paragraphs:
        tokens = tokenize(para)
        curr_sets.append(shingle_tokens(tokens, k=5))

    reused_hits: list[tuple[int, int, float]] = []
    for idx, curr_set in enumerate(curr_sets):
        best = 0.0
        best_idx = -1
        for jdx, prev_set in enumerate(prev_sets):
            score = jaccard(curr_set, prev_set)
            if score > best:
                best = score
                best_idx = jdx
        if best >= 0.8:
            reused_hits.append((idx, best_idx, best))

    percent_reused = None
    if curr_sets:
        percent_reused = len(reused_hits) / len(curr_sets)

    percent_new = None
    if percent_reused is not None:
        percent_new = 1.0 - percent_reused

    evidence: list[dict[str, Any]] = []
    reused_hits.sort(key=lambda item: item[2], reverse=True)
    for idx, prev_idx, score in reused_hits[:3]:
        snippet = curr_paragraphs[idx] if idx < len(curr_paragraphs) else ""
        why = f"Near-duplicate paragraph (Jaccard {score:.2f})."
        evidence.append(
            {
                "year": lens_pair.curr.year,
                "paragraph_idx": idx,
                "snippet": snippet,
                "why": why,
            }
        )
        if prev_idx >= 0 and prev_idx < len(prev_paragraphs):
            evidence.append(
                {
                    "year": lens_pair.prev.year,
                    "paragraph_idx": prev_idx,
                    "snippet": prev_paragraphs[prev_idx],
                    "why": "Matching paragraph from prior year.",
                }
            )

    drift_score = None
    if percent_reused is not None:
        drift_score = 1.0 - percent_reused

    confidence = None
    if curr_sets:
        confidence = min(1.0, len(curr_sets) / 20.0)

    artifacts = {
        "stats": {
            "percent_reused": percent_reused,
            "percent_new": percent_new,
            "reused_paragraphs": len(reused_hits),
            "total_paragraphs": len(curr_sets),
        }
    }
    metrics = make_metrics(drift_score, confidence, lens_pair.coverage, warnings + lens_pair.warnings)
    return artifacts, evidence, metrics



def winnow_fingerprints(text: str, k: int = 25, window: int = 4) -> list[tuple[int, int]]:
    normalized = WHITESPACE_RE.sub(" ", text.lower()).strip()
    if len(normalized) < k:
        return []
    hashes: list[tuple[int, int]] = []
    for idx in range(len(normalized) - k + 1):
        gram = normalized[idx : idx + k]
        digest = hashlib.sha1(gram.encode("utf-8")).hexdigest()
        hashes.append((int(digest[:8], 16), idx))

    fingerprints: list[tuple[int, int]] = []
    if len(hashes) <= window:
        return hashes
    last_hash = None
    last_pos = None
    for idx in range(len(hashes) - window + 1):
        window_slice = hashes[idx : idx + window]
        min_hash, min_pos = min(window_slice, key=lambda item: (item[0], item[1]))
        if min_hash != last_hash or min_pos != last_pos:
            fingerprints.append((min_hash, min_pos))
            last_hash = min_hash
            last_pos = min_pos
    return fingerprints


def det_winnowing_fingerprint_v1(
    lens_pair: LensPair,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    warnings: list[str] = []

    prev_fps = winnow_fingerprints(lens_pair.prev.text)
    curr_fps = winnow_fingerprints(lens_pair.curr.text)

    if not prev_fps or not curr_fps:
        warnings.append("thin_counts")

    prev_hashes = {h for h, _ in prev_fps}
    curr_hashes = {h for h, _ in curr_fps}
    shared = prev_hashes & curr_hashes

    ratio = None
    if prev_fps and curr_fps:
        denom = min(len(prev_fps), len(curr_fps))
        ratio = len(shared) / denom if denom else None

    evidence: list[dict[str, Any]] = []
    shared_positions = [pos for h, pos in curr_fps if h in shared]
    for pos in shared_positions[:3]:
        start = max(0, pos - 60)
        end = min(len(lens_pair.curr.text), pos + 120)
        snippet = lens_pair.curr.text[start:end]
        evidence.append(
            {
                "year": lens_pair.curr.year,
                "paragraph_idx": 0,
                "snippet": snippet,
                "why": "Shared fingerprint span.",
            }
        )

    artifacts = {
        "stats": {
            "shared_fingerprints": len(shared),
            "prev_fingerprints": len(prev_fps),
            "curr_fingerprints": len(curr_fps),
            "shared_ratio": ratio,
        }
    }
    confidence = None
    if prev_fps and curr_fps:
        confidence = min(1.0, min(len(prev_fps), len(curr_fps)) / 200.0)
    metrics = make_metrics(ratio, confidence, lens_pair.coverage, warnings + lens_pair.warnings)
    return artifacts, evidence, metrics


def is_heading_line(line: str) -> bool:
    cleaned = line.strip()
    if len(cleaned) < 4 or len(cleaned) > 120:
        return False
    if cleaned.startswith(("-", "*", "?")):
        return False
    letters = [c for c in cleaned if c.isalpha()]
    if not letters:
        return False
    upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    if upper_ratio >= 0.75:
        return True
    if cleaned.endswith(":"):
        return True
    if cleaned.istitle() and len(cleaned.split()) <= 8:
        return True
    return False


def extract_headings(text: str) -> list[str]:
    headings: list[str] = []
    for line in text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        if is_heading_line(cleaned):
            headings.append(cleaned)
    return headings


def headings_with_paragraphs(text: str) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    current_heading = "General"
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        if not buffer:
            return
        paragraph = " ".join(buffer).strip()
        buffer = []
        if not paragraph:
            return
        mapping.setdefault(current_heading, []).append(paragraph)

    for line in text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            flush()
            continue
        if is_heading_line(cleaned):
            flush()
            current_heading = cleaned
            continue
        buffer.append(cleaned)
    flush()
    return mapping


def det_structure_artifacts_v1(
    lens_pair: LensPair,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    warnings: list[str] = []
    prev_headings = extract_headings(lens_pair.prev.text)
    curr_headings = extract_headings(lens_pair.curr.text)

    added = [h for h in curr_headings if h not in prev_headings]
    removed = [h for h in prev_headings if h not in curr_headings]

    prev_map = headings_with_paragraphs(lens_pair.prev.text)
    curr_map = headings_with_paragraphs(lens_pair.curr.text)

    evidence: list[dict[str, Any]] = []
    for heading in added[:3]:
        paragraphs = curr_map.get(heading, [])
        snippet = paragraphs[0] if paragraphs else heading
        paragraph_idx = 0
        if paragraphs and lens_pair.curr.paragraphs:
            try:
                paragraph_idx = lens_pair.curr.paragraphs.index(paragraphs[0])
            except ValueError:
                paragraph_idx = 0
        evidence.append(
            {
                "year": lens_pair.curr.year,
                "paragraph_idx": paragraph_idx,
                "snippet": snippet,
                "why": f"Heading added: {heading}",
            }
        )
    for heading in removed[:3]:
        paragraphs = prev_map.get(heading, [])
        snippet = paragraphs[0] if paragraphs else heading
        paragraph_idx = 0
        if paragraphs and lens_pair.prev.paragraphs:
            try:
                paragraph_idx = lens_pair.prev.paragraphs.index(paragraphs[0])
            except ValueError:
                paragraph_idx = 0
        evidence.append(
            {
                "year": lens_pair.prev.year,
                "paragraph_idx": paragraph_idx,
                "snippet": snippet,
                "why": f"Heading removed: {heading}",
            }
        )

    artifacts = {
        "stats": {
            "headings_prev": prev_headings,
            "headings_curr": curr_headings,
            "headings_added": added,
            "headings_removed": removed,
            "paragraph_count_prev": len(lens_pair.prev.paragraphs),
            "paragraph_count_curr": len(lens_pair.curr.paragraphs),
            "length_chars_prev": len(lens_pair.prev.text),
            "length_chars_curr": len(lens_pair.curr.text),
        }
    }

    drift_score = None
    if prev_headings or curr_headings:
        denom = max(1, len(set(prev_headings) | set(curr_headings)))
        drift_score = (len(added) + len(removed)) / denom
    confidence = (
        min(1.0, (len(prev_headings) + len(curr_headings)) / 20.0)
        if (prev_headings or curr_headings)
        else 0.0
    )

    metrics = make_metrics(drift_score, confidence, lens_pair.coverage, warnings + lens_pair.warnings)
    return artifacts, evidence, metrics



def rbo_score(list_a: list[str], list_b: list[str], p: float = 0.9) -> float:
    if not list_a and not list_b:
        return 0.0
    if not list_a or not list_b:
        return 0.0

    depth = max(len(list_a), len(list_b))
    score = 0.0
    set_a: set[str] = set()
    set_b: set[str] = set()

    for d in range(1, depth + 1):
        if d <= len(list_a):
            set_a.add(list_a[d - 1])
        if d <= len(list_b):
            set_b.add(list_b[d - 1])
        overlap = len(set_a & set_b)
        score += (overlap / d) * (p ** (d - 1))

    return (1 - p) * score


def extract_ranked_labels(artifacts: dict[str, Any]) -> list[str]:
    ranked: list[str] = []
    ranked_items = artifacts.get("ranked_items")
    if isinstance(ranked_items, list):
        typed_ranked_items = cast(list[Any], ranked_items)
        for item in typed_ranked_items:
            if isinstance(item, dict):
                item_dict = cast(dict[str, Any], item)
                label: Any = item_dict.get("label")
                if isinstance(label, str):
                    ranked.append(label)
            elif isinstance(item, str):
                ranked.append(item)
    if not ranked:
        for key in ("top_risers", "top_fallers"):
            items = artifacts.get(key)
            if isinstance(items, list):
                typed_items = cast(list[Any], items)
                for item in typed_items:
                    if isinstance(item, dict):
                        item_dict = cast(dict[str, Any], item)
                        label = item_dict.get("label")
                        if isinstance(label, str):
                            ranked.append(label)
                    elif isinstance(item, str):
                        ranked.append(item)
    return ranked


def det_rbo_agreement_v1(
    detector_outputs: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    warnings: list[str] = []
    detector_ids: list[str] = []
    ranked_lists: list[list[str]] = []

    for detector_id, output in detector_outputs.items():
        artifacts = output.get("artifacts")
        if not isinstance(artifacts, dict):
            continue
        typed_artifacts = cast(dict[str, Any], artifacts)
        labels = extract_ranked_labels(typed_artifacts)
        if labels:
            detector_ids.append(detector_id)
            ranked_lists.append(labels)

    if len(detector_ids) < 2:
        warnings.append("insufficient_ranked_lists")
        artifacts = {"detectors": detector_ids, "matrix": []}
        metrics = make_metrics(None, 0.0, None, warnings)
        return artifacts, [], metrics

    matrix: list[list[Optional[float]]] = []
    scores: list[float] = []
    for idx, list_a in enumerate(ranked_lists):
        row: list[Optional[float]] = []
        for jdx, list_b in enumerate(ranked_lists):
            if idx == jdx:
                row.append(1.0)
                continue
            score = rbo_score(list_a, list_b, p=0.9)
            row.append(round(score, 4))
            scores.append(score)
        matrix.append(row)

    agreement_score = sum(scores) / len(scores) if scores else 0.0
    artifacts = {
        "detectors": detector_ids,
        "matrix": matrix,
        "agreement_score": round(agreement_score, 4),
    }
    metrics = make_metrics(round(agreement_score, 4), 1.0, None, warnings)
    return artifacts, [], metrics


def validate_lab_output(payload: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    required_keys = [
        "lab_schema_version",
        "detector_id",
        "cleaning_lens",
        "source_id",
        "ticker",
        "section",
        "year_from",
        "year_to",
        "artifacts",
        "evidence",
        "metrics",
        "provenance",
    ]
    for key in required_keys:
        if key not in payload:
            warnings.append(f"missing_{key}")
    if payload.get("lab_schema_version") != LAB_SCHEMA_VERSION:
        warnings.append("schema_version_mismatch")
    metrics = payload.get("metrics")
    if not isinstance(metrics, dict):
        warnings.append("metrics_not_object")
    evidence = payload.get("evidence")
    if not isinstance(evidence, list):
        warnings.append("evidence_not_list")
    return warnings


def build_lab_output(
    detector_id: str,
    ticker: str,
    section: str,
    year_from: int,
    year_to: int,
    lens: str,
    source_id: str,
    artifacts: dict[str, Any],
    evidence: list[dict[str, Any]],
    metrics: dict[str, Any],
    inputs: dict[str, str],
) -> dict[str, Any]:
    return {
        "lab_schema_version": LAB_SCHEMA_VERSION,
        "detector_id": detector_id,
        "cleaning_lens": lens,
        "source_id": source_id,
        "ticker": ticker,
        "section": section,
        "year_from": year_from,
        "year_to": year_to,
        "artifacts": artifacts,
        "evidence": evidence,
        "metrics": metrics,
        "provenance": build_provenance(inputs),
    }


def load_cases_registry(path: Path) -> list[CaseSpec]:
    payload = read_json(path)
    root = as_str_dict(payload)
    if root is None:
        return []
    cases_raw = as_list(root.get("cases"))
    if cases_raw is None:
        return []
    cases: list[CaseSpec] = []
    for entry in cases_raw:
        entry_dict = as_str_dict(entry)
        if entry_dict is None:
            continue
        ticker = entry_dict.get("ticker")
        year_from = entry_dict.get("year_from")
        year_to = entry_dict.get("year_to")
        section = entry_dict.get("section")
        why = entry_dict.get("why_interesting")
        expected = entry_dict.get("expected_detectors")
        tags_raw = entry_dict.get("tags")
        if not isinstance(ticker, str) or not isinstance(section, str):
            continue
        if not isinstance(year_from, int) or not isinstance(year_to, int):
            continue
        if not isinstance(why, str):
            why = ""
        expected_list: list[str] = []
        if isinstance(expected, list):
            typed_expected = cast(list[Any], expected)
            for item in typed_expected:
                if isinstance(item, str):
                    expected_list.append(item)
        tags: list[str] = []
        if isinstance(tags_raw, list):
            typed_tags_raw = cast(list[Any], tags_raw)
            for item in typed_tags_raw:
                if isinstance(item, str):
                    tags.append(item)
        cases.append(
            CaseSpec(
                ticker=ticker.upper(),
                year_from=min(year_from, year_to),
                year_to=max(year_from, year_to),
                section=section,
                why_interesting=why,
                expected_detectors=expected_list,
                tags=tags,
            )
        )
    return cases


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build lab outputs for Narrative Drift Lab.")
    parser.add_argument("--tickers", help="Comma-separated tickers")
    parser.add_argument("--pairs", help="CSV of year pairs, e.g. 2022-2023,2023-2024")
    parser.add_argument("--section", default=DEFAULT_SECTION)
    parser.add_argument("--out_dir", default="public/data/sec_narrative_drift_lab")
    parser.add_argument("--source", default=DEFAULT_SOURCE, choices=["edgar", "sraf_nd"])
    parser.add_argument("--lenses", default=",".join(DEFAULT_LENSES))
    parser.add_argument("--detectors", default=",".join(DEFAULT_DETECTORS))
    parser.add_argument("--cases_registry", help="Optional seed registry JSON with curated cases")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    lenses = [item.strip() for item in args.lenses.split(",") if item.strip()]
    detectors = [item.strip() for item in args.detectors.split(",") if item.strip()]

    cases: list[CaseSpec] = []
    if args.cases_registry:
        cases = load_cases_registry(Path(args.cases_registry))

    if not cases:
        tickers: list[str] = []
        if args.tickers:
            for item in args.tickers.split(","):
                if item.strip():
                    tickers.append(item.strip().upper())
        pairs = parse_pairs(args.pairs or "")
        for ticker in tickers:
            for year_from, year_to in pairs:
                cases.append(
                    CaseSpec(
                        ticker=ticker,
                        year_from=year_from,
                        year_to=year_to,
                        section=args.section,
                        why_interesting="Curated v1 case.",
                        expected_detectors=detectors,
                        tags=["recommended"],
                    )
                )

    if not cases:
        raise SystemExit("No cases provided. Use --cases_registry or --tickers/--pairs.")

    outputs_written = 0
    outputs_linked = 0
    registry_entries: list[dict[str, Any]] = []

    for case in cases:
        prev_section = load_section_text(case.ticker, case.year_from, case.section, args.source, root)
        curr_section = load_section_text(case.ticker, case.year_to, case.section, args.source, root)
        if prev_section is None or curr_section is None:
            print(f"Skipping {case.ticker} {case.year_from}-{case.year_to}: missing text")
            continue

        output_links: list[dict[str, Any]] = []

        for lens in lenses:
            lens_pair = build_lens_pair(prev_section, curr_section, lens)

            outputs_for_rbo: dict[str, dict[str, Any]] = {}

            for detector_id in detectors:
                if detector_id == "det_rbo_agreement_v1":
                    continue
                if detector_id.startswith("det_llm_"):
                    filename = build_output_filename(
                        case.section,
                        case.year_from,
                        case.year_to,
                        detector_id,
                        lens,
                        args.source,
                    )
                    ticker_dir = out_dir / case.ticker
                    if (ticker_dir / filename).exists():
                        output_links.append(
                            {
                                "detector_id": detector_id,
                                "cleaning_lens": lens,
                                "source_id": args.source,
                                "filename": filename,
                            }
                        )
                        outputs_linked += 1
                    continue

                if detector_id == "det_logodds_terms_v1":
                    artifacts, evidence, metrics = det_logodds_terms_v1(
                        root,
                        case.ticker,
                        case.year_from,
                        case.year_to,
                        case.section,
                        lens_pair,
                    )
                elif detector_id == "det_jsd_ngrams_v1":
                    artifacts, evidence, metrics = det_jsd_ngrams_v1(lens_pair)
                elif detector_id == "det_minhash_boilerplate_v1":
                    artifacts, evidence, metrics = det_minhash_boilerplate_v1(lens_pair)
                elif detector_id == "det_winnowing_fingerprint_v1":
                    artifacts, evidence, metrics = det_winnowing_fingerprint_v1(lens_pair)
                elif detector_id == "det_structure_artifacts_v1":
                    artifacts, evidence, metrics = det_structure_artifacts_v1(lens_pair)
                else:
                    continue

                inputs = {
                    "prev_text_sha256": sha256_text(lens_pair.prev.text),
                    "curr_text_sha256": sha256_text(lens_pair.curr.text),
                    "lens": lens_pair.lens,
                    "source": args.source,
                }
                payload = build_lab_output(
                    detector_id,
                    case.ticker,
                    case.section,
                    case.year_from,
                    case.year_to,
                    lens,
                    args.source,
                    artifacts,
                    evidence,
                    metrics,
                    inputs,
                )
                validation_warnings = validate_lab_output(payload)
                if validation_warnings:
                    metrics["warnings"].extend(validation_warnings)

                filename = build_output_filename(
                    case.section,
                    case.year_from,
                    case.year_to,
                    detector_id,
                    lens,
                    args.source,
                )
                ticker_dir = out_dir / case.ticker
                ticker_dir.mkdir(parents=True, exist_ok=True)
                write_json(ticker_dir / filename, payload)
                outputs_written += 1

                output_links.append(
                    {
                        "detector_id": detector_id,
                        "cleaning_lens": lens,
                        "source_id": args.source,
                        "filename": filename,
                    }
                )
                outputs_for_rbo[detector_id] = payload

            if "det_rbo_agreement_v1" in detectors:
                artifacts, evidence, metrics = det_rbo_agreement_v1(outputs_for_rbo)
                inputs = {
                    "lens": lens_pair.lens,
                    "source": args.source,
                }
                payload = build_lab_output(
                    "det_rbo_agreement_v1",
                    case.ticker,
                    case.section,
                    case.year_from,
                    case.year_to,
                    lens,
                    args.source,
                    artifacts,
                    evidence,
                    metrics,
                    inputs,
                )
                filename = build_output_filename(
                    case.section,
                    case.year_from,
                    case.year_to,
                    "det_rbo_agreement_v1",
                    lens,
                    args.source,
                )
                ticker_dir = out_dir / case.ticker
                ticker_dir.mkdir(parents=True, exist_ok=True)
                write_json(ticker_dir / filename, payload)
                outputs_written += 1

                output_links.append(
                    {
                        "detector_id": "det_rbo_agreement_v1",
                        "cleaning_lens": lens,
                        "source_id": args.source,
                        "filename": filename,
                    }
                )

        registry_entries.append(
            {
                "ticker": case.ticker,
                "year_from": case.year_from,
                "year_to": case.year_to,
                "section": case.section,
                "why_interesting": case.why_interesting,
                "expected_detectors": case.expected_detectors,
                "tags": case.tags,
                "outputs": output_links,
            }
        )

    build_utc = now_utc_iso()
    registry_payload = {
        "version": "1.0",
        "updated_at": build_utc,
        "notes": ["Curated v1 demo set."],
        "cases": registry_entries,
        "provenance": build_provenance({"source": args.source}),
    }
    write_json(out_dir / "lab_cases_v1.json", registry_payload)

    print(
        "Lab build complete. "
        f"cases={len(registry_entries)} outputs_written={outputs_written} "
        f"outputs_linked={outputs_linked}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
