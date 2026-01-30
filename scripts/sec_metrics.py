import argparse
import json
import math
import os
import random
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, TYPE_CHECKING, TypedDict, cast

if TYPE_CHECKING:
    ENGLISH_STOP_WORDS: set[str] = set()

    class TfidfVectorizer:
        def __init__(
            self,
            *,
            stop_words: Optional[str | set[str]] = ...,
            token_pattern: Optional[str] = ...,
        ) -> None: ...

        def fit_transform(self, raw_documents: Sequence[str]) -> Any: ...

        def transform(self, raw_documents: Sequence[str]) -> Any: ...

    def cosine_similarity(
        X: Any, Y: Any | None = None, dense_output: bool = True
    ) -> Any: ...

else:
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

from sec_extract_item1a import extract_item1a_from_html, split_paragraphs
from sec_segments import segment_text_v1
from sec_phrases import (
    HONORIFICS,
    NAME_SUFFIXES,
    NOISE_TOKENS,
    PHRASE_BLACKLIST,
    SEC_PHRASE_ALLOWLIST,
    WEAK_EDGE_TOKENS,
)


# =============================================================================
# Configuration Constants
# =============================================================================
# These parameters control text processing, similarity computation, and term
# shift scoring. They were tuned empirically on SEC 10-K filings.

SECTION_NAME = "10k_item1a"
STOPWORDS = set(ENGLISH_STOP_WORDS)
ALLOWED_SHORT_TOKENS: set[str] = {"ai", "ml", "ip", "it", "vr", "ar"}
HYPHEN_CLASS = r"[-\u2010\u2011\u2012\u2013\u2014\u2212'\u2018\u2019]"
SEGMENT_BOUNDARY_RE = re.compile(r"(?:\n{2,}|[.!?;:])")
CANONICAL_TERMS_PATH = Path(__file__).resolve().parent / "resources" / "canonical_terms.json"
_canonical_terms_cache: Optional["CanonicalTermsMap"] = None

# Log-odds smoothing parameters (Bayesian prior for term frequency estimation)
# Higher PRIOR_MASS_DEFAULT = more regularization, reduces noise in low-count terms
PRIOR_MASS_DEFAULT = 200.0
# Minimum prior mass per term to prevent division instability
PRIOR_FLOOR = 0.1

# Output precision for similarity and drift metrics
SIMILARITY_DECIMALS = 4
DRIFT_DECIMALS = 4

# Document Frequency (DF) penalty parameters for term shift scoring
# These reduce the ranking of terms that appear in many years (less distinctive)
# Gamma controls decay rate: higher = steeper penalty for high-DF terms
DF_PENALTY_GAMMA_UNI = 1.25      # Penalty exponent for single-word terms
DF_PENALTY_GAMMA_PHRASE = 1.75   # Penalty exponent for multi-word phrases (stricter)

# Override thresholds: strong signals can bypass DF penalty partially
DF_PENALTY_OVERRIDE_Z = 3.5      # Z-score threshold for override consideration
DF_PENALTY_OVERRIDE_COUNT = 8    # Min count for override consideration
DF_PENALTY_EPS = 0.05            # Epsilon to prevent zero penalty
DF_PENALTY_FLOOR = 0.05          # Minimum penalty (prevents full bypass)
SCORE_DF_MIN = 0.10              # Min absolute score after DF adjustment to show term
DF_PENALTY_OVERRIDE_MAX_DF_FRAC = 0.90   # Max DF fraction for override eligibility
DF_PENALTY_OVERRIDE_MIN_PENALTY = 0.25   # Min penalty even with override

SENTENCE_NORMALIZE_RE = re.compile(r"\s+")


class TermBase(TypedDict):
    term: str


class ShiftTermStats(TermBase):
    score: float
    z: float
    countPrev: int
    countCurr: int
    per10kPrev: float
    per10kCurr: float
    deltaPer10k: float
    distinctive: bool


class ShiftTermOutput(ShiftTermStats, total=False):
    includes: list[str]


class ShiftTermAlt(TermBase):
    score: float


ShiftPairPayload = TypedDict(
    "ShiftPairPayload",
    {
        "from": int,
        "to": int,
        "topRisers": list[ShiftTermOutput],
        "topFallers": list[ShiftTermOutput],
        "summary": str,
        "topRisersAlt": list[ShiftTermAlt],
        "topFallersAlt": list[ShiftTermAlt],
        "summaryAlt": str,
    },
    total=False,
)


class MetricsPayload(TypedDict):
    section: str
    years: list[int]
    drift_vs_prev: list[Optional[float]]
    drift_ci_low: list[Optional[float]]
    drift_ci_high: list[Optional[float]]
    boilerplate_score: list[Optional[float]]


class SimilarityPayload(TypedDict):
    section: str
    years: list[int]
    cosineSimilarity: list[list[float]]


class DeboilerplatedDriftPayload(TypedDict):
    section: str
    years: list[int]
    drift_vs_prev: list[Optional[float]]
    similarity_vs_prev: list[Optional[float]]
    prev_sentence_count: list[Optional[int]]
    curr_sentence_count: list[Optional[int]]
    shared_sentence_count: list[Optional[int]]
    prev_retained_count: list[Optional[int]]
    curr_retained_count: list[Optional[int]]
    notes: dict[str, str]


class ShiftsPayload(TypedDict):
    section: str
    yearPairs: list[ShiftPairPayload]


def _compile_phrase_pattern(phrase: str) -> re.Pattern[str]:
    parts = [re.escape(part) for part in phrase.split()]
    joiner = rf"(?:\s+|{HYPHEN_CLASS}\s*)"
    return re.compile(rf"\b{joiner.join(parts)}\b", re.IGNORECASE)


ALLOWLIST_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (phrase, _compile_phrase_pattern(phrase)) for phrase in SEC_PHRASE_ALLOWLIST
]


def tokenize(text: str) -> list[str]:
    # Lowercase-only tokenization is intentional: we're chasing stable business terms,
    # not proper nouns. Lightweight hygiene avoids common false positives.
    raw = re.findall(r"[a-z]{2,}", text.lower())
    tokens: list[str] = []
    skip_next = False
    for token in raw:
        if skip_next:
            skip_next = False
            continue
        if token in HONORIFICS:
            skip_next = True
            continue
        if token in NAME_SUFFIXES or token in NOISE_TOKENS:
            continue
        if token in STOPWORDS:
            continue
        if len(token) < 3 and token not in ALLOWED_SHORT_TOKENS:
            continue
        tokens.append(token)
    return tokens


def has_repeated_tokens(tokens: Sequence[str]) -> bool:
    seen: set[str] = set()
    for token in tokens:
        if not token:
            continue
        if token in seen:
            return True
        seen.add(token)
    return False


def bigrams(tokens: Sequence[str]) -> list[str]:
    output: list[str] = []
    for i in range(len(tokens) - 1):
        a = tokens[i]
        b = tokens[i + 1]
        if not a or not b:
            continue
        if a == b:
            continue
        output.append(f"{a} {b}")
    return output


def split_phrase_segments(text: str) -> list[str]:
    if not text:
        return []
    segments = [segment.strip() for segment in SEGMENT_BOUNDARY_RE.split(text)]
    return [segment for segment in segments if segment]


def tokenize_segments(text: str) -> list[list[str]]:
    token_lists: list[list[str]] = []
    for segment in split_phrase_segments(text):
        tokens = tokenize(segment)
        if tokens:
            token_lists.append(tokens)
    return token_lists


def _phrase_edge_is_weak(tokens: Sequence[str]) -> bool:
    if not tokens:
        return True
    first = tokens[0]
    last = tokens[-1]
    if first in STOPWORDS or last in STOPWORDS:
        return True
    if first in WEAK_EDGE_TOKENS or last in WEAK_EDGE_TOKENS:
        return True
    return False


def _phrase_is_blacklisted(tokens: Sequence[str]) -> bool:
    phrase = " ".join(tokens).lower()
    return phrase in PHRASE_BLACKLIST


def count_allowlist_phrases(text: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    if not text:
        return counts
    lowered = text.lower()
    for phrase, pattern in ALLOWLIST_PATTERNS:
        matches = pattern.findall(lowered)
        if matches:
            counts[phrase] += len(matches)
    return counts


def pmi_keep_bigrams(
    token_lists: Sequence[Sequence[str]], min_count: int = 4, pmi_threshold: float = 4.0
) -> set[str]:
    # Compute PMI on the pooled corpus and keep only strong collocations.
    uni: Counter[str] = Counter()
    bi: Counter[str] = Counter()
    total_tokens = 0
    total_bigrams = 0
    for tokens in token_lists:
        uni.update(tokens)
        total_tokens += len(tokens)
        bi_list = bigrams(tokens)
        bi.update(bi_list)
        total_bigrams += len(bi_list)
    keep: set[str] = set()
    if total_tokens == 0 or total_bigrams == 0:
        return keep
    for phrase, c_xy in bi.items():
        if c_xy < min_count:
            continue
        w1, w2 = phrase.split(" ", 1)
        if _phrase_edge_is_weak([w1, w2]) or _phrase_is_blacklisted([w1, w2]):
            continue
        c_x = uni.get(w1, 0)
        c_y = uni.get(w2, 0)
        if c_x == 0 or c_y == 0:
            continue
        p_xy = c_xy / total_bigrams
        p_x = c_x / total_tokens
        p_y = c_y / total_tokens
        pmi = math.log(p_xy / (p_x * p_y), 2)
        if pmi >= pmi_threshold:
            keep.add(phrase)
    return keep


def textrank_keyphrases(
    text: str, window: int = 4, top_keywords: int = 60, max_phrases: int = 250
) -> Counter[str]:
    # Lightweight TextRank-style phrases: PageRank over a co-occurrence graph.
    tokens = tokenize(text)
    if len(tokens) < 80:
        empty: Counter[str] = Counter()
        return empty

    freq: Counter[str] = Counter(tokens)
    candidates: list[str] = []
    for token, count in freq.items():
        if count >= 3:
            candidates.append(token)
    candidates.sort(key=lambda t: (-freq[t], t))
    candidates = candidates[:2000]
    cand_set = set(candidates)

    neighbors: dict[str, set[str]] = {}
    for token in candidates:
        neighbors[token] = set[str]()
    for i in range(len(tokens)):
        a = tokens[i]
        if a not in cand_set:
            continue
        for j in range(i + 1, min(i + window, len(tokens))):
            b = tokens[j]
            if b not in cand_set or b == a:
                continue
            neighbors[a].add(b)
            neighbors[b].add(a)

    d = 0.85
    scores: dict[str, float] = {}
    for token in candidates:
        scores[token] = 1.0
    for _ in range(25):
        new_scores: dict[str, float] = {}
        for node in candidates:
            rank_sum = 0.0
            for nb in neighbors[node]:
                deg = len(neighbors[nb]) or 1
                rank_sum += scores[nb] / deg
            new_scores[node] = (1 - d) + d * rank_sum
        scores = new_scores

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    top_set: set[str] = set()
    for token, _score in ranked[:top_keywords]:
        top_set.add(token)

    phrases: Counter[str] = Counter()
    for segment in split_phrase_segments(text):
        seg_tokens = tokenize(segment)
        if not seg_tokens:
            continue
        i = 0
        while i < len(seg_tokens):
            if seg_tokens[i] not in top_set:
                i += 1
                continue
            j = i
            while j < len(seg_tokens) and seg_tokens[j] in top_set and (j - i) < 4:
                j += 1
            if j - i >= 2:
                phrase_tokens = seg_tokens[i:j]
                if (
                    not has_repeated_tokens(phrase_tokens)
                    and not _phrase_edge_is_weak(phrase_tokens)
                    and not _phrase_is_blacklisted(phrase_tokens)
                ):
                    phrase = " ".join(phrase_tokens)
                    phrases[phrase] += 1
            i = j

    trimmed: Counter[str] = Counter()
    for phrase, count in phrases.items():
        if count >= 2:
            trimmed[phrase] = count
    if len(trimmed) > max_phrases:
        limited: Counter[str] = Counter()
        for phrase, count in trimmed.most_common(max_phrases):
            limited[phrase] = count
        trimmed = limited
    return trimmed


BOOTSTRAP_ITERATIONS = 100
BOOTSTRAP_SEED = 13


@dataclass(frozen=True)
class SectionYear:
    year: int
    text: str
    paragraphs: list[str]
    confidence: Optional[float] = None


@dataclass(frozen=True)
class CanonicalTermsMap:
    variant_to_concept: dict[str, str]
    concept_labels: dict[str, str]


def normalize_canonical_term(value: str) -> str:
    lowered = value.lower()
    lowered = re.sub(HYPHEN_CLASS, " ", lowered)
    lowered = re.sub(r"[^\w\s]", "", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def load_canonical_terms(path: Path) -> Optional[CanonicalTermsMap]:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    root = as_str_dict(payload)
    if root is None:
        return None

    variant_raw = as_str_dict(root.get("variantToConcept"))
    concepts_raw = as_list(root.get("concepts"))
    if variant_raw is None or concepts_raw is None:
        return None

    variant_to_concept: dict[str, str] = {}
    for key, value in variant_raw.items():
        if isinstance(value, str):
            variant_to_concept[key] = value

    concept_labels: dict[str, str] = {}
    for concept in concepts_raw:
        entry = as_str_dict(concept)
        if entry is None:
            continue
        concept_id = entry.get("id")
        label = entry.get("label")
        if isinstance(concept_id, str) and isinstance(label, str):
            concept_labels[concept_id] = label

    if not variant_to_concept or not concept_labels:
        return None

    return CanonicalTermsMap(
        variant_to_concept=variant_to_concept, concept_labels=concept_labels
    )


def get_canonical_terms() -> Optional[CanonicalTermsMap]:
    """Get canonical terms map, using module-level cache."""
    global _canonical_terms_cache
    if _canonical_terms_cache is None:
        _canonical_terms_cache = load_canonical_terms(CANONICAL_TERMS_PATH)
    return _canonical_terms_cache


def sort_variants(variants: Sequence[str]) -> list[str]:
    cleaned: list[str] = []
    for variant in variants:
        if not variant:
            continue
        cleaned.append(variant)

    def sort_key(value: str) -> tuple[int, int, str]:
        normalized = normalize_canonical_term(value)
        token_count = len(normalized.split()) if normalized else 0
        return (-token_count, -len(value), value)

    cleaned.sort(key=sort_key)
    return cleaned


def canonicalize_counts(
    counts: Counter[str],
    canonical_terms: CanonicalTermsMap,
) -> tuple[Counter[str], dict[str, set[str]]]:
    output: Counter[str] = Counter()
    includes: dict[str, set[str]] = {}
    for term, count in counts.items():
        if count <= 0:
            continue
        normalized = normalize_canonical_term(term)
        if not normalized:
            continue
        concept_id = canonical_terms.variant_to_concept.get(normalized)
        if concept_id:
            label = canonical_terms.concept_labels.get(concept_id)
            if label:
                output[label] += count
                if label not in includes:
                    includes[label] = set()
                includes[label].add(term)
                continue
        output[term] += count
    return output, includes


def merge_includes(
    first: Mapping[str, set[str]],
    second: Mapping[str, set[str]],
) -> dict[str, list[str]]:
    combined: dict[str, set[str]] = {}
    for mapping in (first, second):
        for term, variants in mapping.items():
            if term not in combined:
                combined[term] = set()
            combined[term].update(variants)

    output: dict[str, list[str]] = {}
    for term, variants in combined.items():
        output[term] = sort_variants(list(variants))
    return output


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
    if isinstance(value, list):
        return list(cast(list[Any], value))
    return None


def as_str_list(value: Any) -> Optional[list[str]]:
    if not isinstance(value, list):
        return None
    output: list[str] = []
    for item in cast(list[object], value):
        if not isinstance(item, str):
            return None
        output.append(item)
    return output


def parse_year(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    raise ValueError("year must be an integer")


def parse_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return ""


def parse_confidence(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def normalize_paragraphs(text: str, paragraphs: Optional[Sequence[str]]) -> list[str]:
    if paragraphs:
        cleaned = [para.strip() for para in paragraphs if para.strip()]
        if cleaned:
            return cleaned
    text = text.strip()
    if not text:
        return []
    split = split_paragraphs(text)
    if split:
        return split
    return [text]


def load_sections_from_json(path: Path) -> list[SectionYear]:
    payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    items = as_list(payload)
    if items is None:
        raise RuntimeError("Input JSON must be a list of year sections.")

    sections: list[SectionYear] = []
    for item in items:
        entry = as_str_dict(item)
        if entry is None:
            continue
        year = parse_year(entry.get("year"))
        text = parse_text(entry.get("text"))
        raw_paragraphs = entry.get("paragraphs")
        paragraphs = normalize_paragraphs(text, as_str_list(raw_paragraphs))
        confidence = parse_confidence(entry.get("confidence"))
        sections.append(SectionYear(year=year, text=text, paragraphs=paragraphs, confidence=confidence))

    return sorted(sections, key=lambda section: section.year)


def load_sections_from_fixture(path: Path, years: Sequence[int]) -> list[SectionYear]:
    html = path.read_text(encoding="utf-8", errors="replace")
    section, confidence, _method, _errors, _debug = extract_item1a_from_html(html)
    paragraphs = normalize_paragraphs(section, None)
    sections: list[SectionYear] = []
    for year in years:
        sections.append(
            SectionYear(year=year, text=section, paragraphs=paragraphs, confidence=confidence)
        )
    return sorted(sections, key=lambda section: section.year)


def sentence_tokens(text: str) -> list[str]:
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    output: list[str] = []
    for part in parts:
        cleaned = re.sub(r"\s+", " ", part).strip().lower()
        if cleaned:
            output.append(cleaned)
    return output


def boilerplate_score(prev_text: str, curr_text: str) -> Optional[float]:
    curr_sentences = sentence_tokens(curr_text)
    if not curr_sentences:
        return None
    prev_set = set(sentence_tokens(prev_text))
    reused = sum(1 for sentence in curr_sentences if sentence in prev_set)
    return reused / len(curr_sentences)


def percentile(values: list[float], pct: float) -> Optional[float]:
    if not values:
        return None
    values_sorted = sorted(values)
    index = (len(values_sorted) - 1) * (pct / 100.0)
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return values_sorted[int(index)]
    fraction = index - lower
    return values_sorted[lower] * (1 - fraction) + values_sorted[upper] * fraction


def round_value(value: Optional[float], digits: int = 2) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), digits)


def extract_terms(items: Sequence[TermBase], limit: int = 3) -> list[str]:
    terms: list[str] = []
    for item in items:
        terms.append(item["term"])
        if len(terms) >= limit:
            break
    return terms


def build_shift_summary(riser_terms: Sequence[str], faller_terms: Sequence[str]) -> str:
    risers_text = ", ".join(riser_terms[:3])
    fallers_text = ", ".join(faller_terms[:3])
    if risers_text and fallers_text:
        return f"Adds emphasis on {risers_text}; de-emphasizes {fallers_text}."
    if risers_text:
        return f"Adds emphasis on {risers_text}."
    if fallers_text:
        return f"De-emphasizes {fallers_text}."
    return ""


def log_odds_ratio(
    counts_a: Counter[str], counts_b: Counter[str], alpha: float = 0.01
) -> dict[str, float]:
    vocab = sorted(set(counts_a.keys()) | set(counts_b.keys()))
    total_a = sum(counts_a.values())
    total_b = sum(counts_b.values())
    if not vocab or total_a == 0 or total_b == 0:
        return {}
    vocab_size = len(vocab)
    scores: dict[str, float] = {}
    for term in vocab:
        count_a = counts_a.get(term, 0)
        count_b = counts_b.get(term, 0)
        denom_a = total_a - count_a + alpha * vocab_size
        denom_b = total_b - count_b + alpha * vocab_size
        score = math.log((count_b + alpha) / denom_b) - math.log((count_a + alpha) / denom_a)
        scores[term] = score
    return scores


def is_valid_section(section: SectionYear) -> bool:
    if not section.text.strip():
        return False
    if section.confidence is not None and section.confidence < 0.5:
        return False
    return True


def compute_bootstrap_ci(
    prev_section: SectionYear,
    curr_section: SectionYear,
    vectorizer: TfidfVectorizer,
    iterations: int = BOOTSTRAP_ITERATIONS,
) -> tuple[Optional[float], Optional[float]]:
    prev_paragraphs = normalize_paragraphs(prev_section.text, prev_section.paragraphs)
    curr_paragraphs = normalize_paragraphs(curr_section.text, curr_section.paragraphs)
    if not prev_paragraphs or not curr_paragraphs:
        return None, None

    rng = random.Random(BOOTSTRAP_SEED)
    vectorizer_any = cast(Any, vectorizer)
    samples: list[float] = []
    for _ in range(iterations):
        prev_sample = rng.choices(prev_paragraphs, k=len(prev_paragraphs))
        curr_sample = rng.choices(curr_paragraphs, k=len(curr_paragraphs))
        docs = ["\n".join(prev_sample), "\n".join(curr_sample)]
        vectors = vectorizer_any.transform(docs)
        similarity_matrix = cosine_similarity(vectors)
        similarity_values = cast(list[list[float]], similarity_matrix.tolist())
        similarity = similarity_values[0][1]
        samples.append(1 - float(similarity))

    low = percentile(samples, 5)
    high = percentile(samples, 95)
    return low, high


def normalize_sentence(text: str) -> str:
    return SENTENCE_NORMALIZE_RE.sub(" ", text.strip()).lower()


def extract_sentence_texts(text: str) -> list[str]:
    payload = segment_text_v1(text)
    sentences: list[str] = []
    raw_sentences = payload.get("sentences")
    if not isinstance(raw_sentences, list):
        return sentences
    for entry in cast(list[object], raw_sentences):
        if not isinstance(entry, dict):
            continue
        entry_dict = cast(dict[str, Any], entry)
        start = entry_dict.get("start")
        end = entry_dict.get("end")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if start < 0 or end <= start or end > len(text):
            continue
        sentences.append(text[start:end])
    return sentences


def compute_deboilerplated_pair(
    prev_text: str,
    curr_text: str,
) -> tuple[
    Optional[float],
    Optional[float],
    int,
    int,
    int,
    int,
    int,
]:
    prev_sentences = extract_sentence_texts(prev_text)
    curr_sentences = extract_sentence_texts(curr_text)
    prev_norm = [normalize_sentence(s) for s in prev_sentences]
    curr_norm = [normalize_sentence(s) for s in curr_sentences]
    prev_pairs = [(s, n) for s, n in zip(prev_sentences, prev_norm) if n]
    curr_pairs = [(s, n) for s, n in zip(curr_sentences, curr_norm) if n]

    prev_norm_set = {n for _, n in prev_pairs}
    curr_norm_set = {n for _, n in curr_pairs}
    shared_norm = prev_norm_set & curr_norm_set

    prev_retained = [s for s, n in prev_pairs if n not in shared_norm]
    curr_retained = [s for s, n in curr_pairs if n not in shared_norm]

    prev_count = len(prev_pairs)
    curr_count = len(curr_pairs)
    shared_count = len(shared_norm)
    prev_retained_count = len(prev_retained)
    curr_retained_count = len(curr_retained)

    if not prev_retained or not curr_retained:
        return (
            None,
            None,
            prev_count,
            curr_count,
            shared_count,
            prev_retained_count,
            curr_retained_count,
        )

    vectorizer = TfidfVectorizer(
        stop_words="english",
        token_pattern=r"(?u)\b[a-zA-Z]{2,}\b",
    )
    vectorizer_any = cast(Any, vectorizer)
    docs = ["\n".join(prev_retained), "\n".join(curr_retained)]
    tfidf_matrix = vectorizer_any.fit_transform(docs)
    similarity_matrix = cosine_similarity(tfidf_matrix)
    similarity_values = cast(list[list[float]], similarity_matrix.tolist())
    similarity = similarity_values[0][1]
    drift = 1 - float(similarity)
    return (
        round_value(float(similarity), DRIFT_DECIMALS),
        round_value(drift, DRIFT_DECIMALS),
        prev_count,
        curr_count,
        shared_count,
        prev_retained_count,
        curr_retained_count,
    )


def build_deboilerplated_drift(sections: list[SectionYear]) -> DeboilerplatedDriftPayload:
    years = [section.year for section in sections]
    drift_vs_prev: list[Optional[float]] = [None] * len(years)
    similarity_vs_prev: list[Optional[float]] = [None] * len(years)
    prev_sentence_count: list[Optional[int]] = [None] * len(years)
    curr_sentence_count: list[Optional[int]] = [None] * len(years)
    shared_sentence_count: list[Optional[int]] = [None] * len(years)
    prev_retained_count: list[Optional[int]] = [None] * len(years)
    curr_retained_count: list[Optional[int]] = [None] * len(years)

    for idx in range(1, len(sections)):
        prev_text = sections[idx - 1].text
        curr_text = sections[idx].text
        (
            similarity,
            drift,
            prev_count,
            curr_count,
            shared_count,
            prev_keep,
            curr_keep,
        ) = compute_deboilerplated_pair(prev_text, curr_text)
        similarity_vs_prev[idx] = similarity
        drift_vs_prev[idx] = drift
        prev_sentence_count[idx] = prev_count
        curr_sentence_count[idx] = curr_count
        shared_sentence_count[idx] = shared_count
        prev_retained_count[idx] = prev_keep
        curr_retained_count[idx] = curr_keep

    return {
        "section": SECTION_NAME,
        "years": years,
        "drift_vs_prev": drift_vs_prev,
        "similarity_vs_prev": similarity_vs_prev,
        "prev_sentence_count": prev_sentence_count,
        "curr_sentence_count": curr_sentence_count,
        "shared_sentence_count": shared_sentence_count,
        "prev_retained_count": prev_retained_count,
        "curr_retained_count": curr_retained_count,
        "notes": {
            "sentence_split": "sec_segments.segment_text_v1",
            "match_norm": "whitespace+lower",
        },
    }


def build_metrics(
    sections: list[SectionYear],
    skip_ci: bool = False,
) -> tuple[MetricsPayload, SimilarityPayload, ShiftsPayload]:
    canonical_terms = get_canonical_terms()
    years = [section.year for section in sections]
    drift_vs_prev: list[Optional[float]] = [None] * len(years)
    drift_ci_low: list[Optional[float]] = [None] * len(years)
    drift_ci_high: list[Optional[float]] = [None] * len(years)
    boilerplate_scores: list[Optional[float]] = [None] * len(years)

    valid_sections = [section for section in sections if is_valid_section(section)]
    valid_years = [section.year for section in valid_sections]
    valid_texts = [section.text for section in valid_sections]
    similarity: SimilarityPayload

    if valid_sections:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            token_pattern=r"(?u)\b[a-zA-Z]{2,}\b",
        )
        vectorizer_any = cast(Any, vectorizer)
        tfidf_matrix = vectorizer_any.fit_transform(valid_texts)
        raw_similarity_matrix = cosine_similarity(tfidf_matrix)
        raw_similarity = cast(list[list[float]], raw_similarity_matrix.tolist())
        similarity_values: list[list[float]] = []
        for row_index, row in enumerate(raw_similarity):
            rounded_row: list[float] = []
            for col_index, value in enumerate(row):
                if row_index == col_index:
                    rounded_row.append(1.0)
                else:
                    rounded_row.append(round(float(value), SIMILARITY_DECIMALS))
            similarity_values.append(rounded_row)

        valid_index = {year: idx for idx, year in enumerate(valid_years)}

        for idx in range(1, len(sections)):
            prev_year = sections[idx - 1].year
            curr_year = sections[idx].year
            if prev_year in valid_index and curr_year in valid_index:
                sim = raw_similarity[valid_index[prev_year]][valid_index[curr_year]]
                drift = 1 - float(sim)
                drift_vs_prev[idx] = round_value(drift, DRIFT_DECIMALS)
                if skip_ci:
                    # Skip expensive bootstrap CI computation in fast mode
                    drift_ci_low[idx] = None
                    drift_ci_high[idx] = None
                else:
                    low, high = compute_bootstrap_ci(
                        sections[idx - 1], sections[idx], vectorizer
                    )
                    drift_ci_low[idx] = round_value(low, DRIFT_DECIMALS)
                    drift_ci_high[idx] = round_value(high, DRIFT_DECIMALS)

                prev_text = sections[idx - 1].text
                curr_text = sections[idx].text
                boilerplate_scores[idx] = round_value(
                    boilerplate_score(prev_text, curr_text), DRIFT_DECIMALS
                )

        similarity = {
            "section": SECTION_NAME,
            "years": valid_years,
            "cosineSimilarity": similarity_values,
        }
    else:
        empty_years: list[int] = []
        empty_similarity: list[list[float]] = []
        similarity = {
            "section": SECTION_NAME,
            "years": empty_years,
            "cosineSimilarity": empty_similarity,
        }

    shifts: list[ShiftPairPayload] = []

    pooled_tokens: list[list[str]] = []
    for section in valid_sections:
        pooled_tokens.extend(tokenize_segments(section.text))
    bigram_keep = pmi_keep_bigrams(pooled_tokens)

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

    def build_background_counts(counts_by_year: Sequence[Counter[str]]) -> tuple[Counter[str], int]:
        background: Counter[str] = Counter()
        total = 0
        for counts in counts_by_year:
            background.update(counts)
            total += sum(counts.values())
        return background, total

    def build_year_df(counts_by_year: Sequence[Counter[str]]) -> dict[str, int]:
        df: dict[str, int] = {}
        for counts in counts_by_year:
            for term in counts.keys():
                df[term] = df.get(term, 0) + 1
        return df

    def log_odds_stats(
        counts_prev: Counter[str],
        counts_curr: Counter[str],
        counts_bg: Counter[str],
        total_bg: int,
        prior_mass: float,
        year_df: Mapping[str, int],
        num_years: int,
    ) -> dict[str, ShiftTermStats]:
        vocab = set(counts_prev) | set(counts_curr)
        if not vocab:
            return {}
        total_prev = sum(counts_prev.values())
        total_curr = sum(counts_curr.values())
        stats: dict[str, ShiftTermStats] = {}
        uniform_prior = 1.0 / max(1, len(vocab))
        for term in vocab:
            c_prev = counts_prev.get(term, 0)
            c_curr = counts_curr.get(term, 0)
            if total_bg:
                p_bg = counts_bg.get(term, 0) / total_bg
            else:
                p_bg = uniform_prior
            alpha_i = max(prior_mass * p_bg, PRIOR_FLOOR)
            denom_prev = total_prev + prior_mass - (c_prev + alpha_i)
            denom_curr = total_curr + prior_mass - (c_curr + alpha_i)
            if denom_prev <= 0 or denom_curr <= 0:
                continue
            log_prev = math.log((c_prev + alpha_i) / denom_prev)
            log_curr = math.log((c_curr + alpha_i) / denom_curr)
            score = log_curr - log_prev

            z = score / math.sqrt((1 / (c_curr + alpha_i)) + (1 / (c_prev + alpha_i)))

            per10k_prev = (c_prev / total_prev * 10000.0) if total_prev else 0.0
            per10k_curr = (c_curr / total_curr * 10000.0) if total_curr else 0.0
            delta = per10k_curr - per10k_prev

            df_frac = (year_df.get(term, 0) / num_years) if num_years else 0.0
            distinctive = (
                (abs(z) >= 2.0)
                and (max(c_prev, c_curr) >= 3)
                and (abs(delta) >= 0.25)
                and (df_frac <= 0.70)
            )

            stats[term] = {
                "term": term,
                "score": score,
                "z": z,
                "countPrev": c_prev,
                "countCurr": c_curr,
                "per10kPrev": per10k_prev,
                "per10kCurr": per10k_curr,
                "deltaPer10k": delta,
                "distinctive": distinctive,
            }
        return stats

    def build_df_penalty_scores(
        items: Sequence[ShiftTermStats],
        year_df: Mapping[str, int],
        num_years: int,
    ) -> dict[str, float]:
        scores: dict[str, float] = {}
        if not num_years:
            return scores
        for item in items:
            term = item["term"]
            df_frac = year_df.get(term, 0) / num_years
            gamma = DF_PENALTY_GAMMA_PHRASE if " " in term else DF_PENALTY_GAMMA_UNI
            df_penalty = max(
                DF_PENALTY_FLOOR, (1 - df_frac + DF_PENALTY_EPS) ** gamma
            )
            if (
                abs(item["z"]) >= DF_PENALTY_OVERRIDE_Z
                and max(item["countPrev"], item["countCurr"]) >= DF_PENALTY_OVERRIDE_COUNT
            ):
                if df_frac <= DF_PENALTY_OVERRIDE_MAX_DF_FRAC:
                    df_penalty = max(df_penalty, DF_PENALTY_OVERRIDE_MIN_PENALTY)
            scores[term] = item["z"] * df_penalty
        return scores

    def build_term_counts_primary(text: str) -> Counter[str]:
        toks = tokenize(text)
        counts: Counter[str] = Counter(toks)
        for seg_tokens in tokenize_segments(text):
            for phrase in bigrams(seg_tokens):
                if phrase in bigram_keep:
                    counts[phrase] += 1
        counts.update(count_allowlist_phrases(text))
        return counts

    def build_term_counts_alt(text: str) -> Counter[str]:
        counts: Counter[str] = Counter()
        counts.update(textrank_keyphrases(text))
        counts.update(count_allowlist_phrases(text))
        return counts

    def build_shift_term_outputs(
        items: Sequence[ShiftTermStats],
        limit: int = 15,
        includes_by_term: Optional[Mapping[str, Sequence[str]]] = None,
    ) -> list[ShiftTermOutput]:
        output: list[ShiftTermOutput] = []
        for item in items:
            term = item["term"]
            term_output: ShiftTermOutput = {
                "term": term,
                "score": float(item["score"]),
                "z": float(item["z"]),
                "countPrev": int(item["countPrev"]),
                "countCurr": int(item["countCurr"]),
                "per10kPrev": float(item["per10kPrev"]),
                "per10kCurr": float(item["per10kCurr"]),
                "deltaPer10k": float(item["deltaPer10k"]),
                "distinctive": bool(item["distinctive"]),
            }
            if includes_by_term is not None:
                includes = includes_by_term.get(term)
                if includes:
                    term_output["includes"] = list(includes)
            output.append(term_output)
            if len(output) >= limit:
                break
        return output

    def build_alt_terms(items: Sequence[ShiftTermStats], limit: int = 15) -> list[ShiftTermAlt]:
        output: list[ShiftTermAlt] = []
        for item in items:
            output.append({"term": item["term"], "score": float(item["score"])})
            if len(output) >= limit:
                break
        return output

    prior_mass = resolve_prior_mass()

    counts_primary_by_year = [build_term_counts_primary(section.text) for section in valid_sections]
    counts_alt_by_year = [build_term_counts_alt(section.text) for section in valid_sections]

    if canonical_terms:
        canonical_primary: list[Counter[str]] = []
        canonical_alt: list[Counter[str]] = []
        for counts in counts_primary_by_year:
            normalized, _ = canonicalize_counts(counts, canonical_terms)
            canonical_primary.append(normalized)
        for counts in counts_alt_by_year:
            normalized, _ = canonicalize_counts(counts, canonical_terms)
            canonical_alt.append(normalized)
        counts_primary_by_year = canonical_primary
        counts_alt_by_year = canonical_alt

    bg_primary, bg_total_primary = build_background_counts(counts_primary_by_year)
    bg_alt, bg_total_alt = build_background_counts(counts_alt_by_year)
    year_df_primary = build_year_df(counts_primary_by_year)
    year_df_alt = build_year_df(counts_alt_by_year)
    num_years = len(valid_sections)

    for idx in range(1, len(valid_sections)):
        prev_section = valid_sections[idx - 1]
        curr_section = valid_sections[idx]

        counts_prev = counts_primary_by_year[idx - 1]
        counts_curr = counts_primary_by_year[idx]
        includes_by_term: dict[str, list[str]] = {}
        if canonical_terms:
            _, includes_prev = canonicalize_counts(build_term_counts_primary(prev_section.text), canonical_terms)
            _, includes_curr = canonicalize_counts(build_term_counts_primary(curr_section.text), canonical_terms)
            includes_by_term = merge_includes(includes_prev, includes_curr)
        stats = log_odds_stats(
            counts_prev,
            counts_curr,
            bg_primary,
            bg_total_primary,
            prior_mass,
            year_df_primary,
            num_years,
        )

        if not stats:
            top_risers: list[ShiftTermOutput] = []
            top_fallers: list[ShiftTermOutput] = []
        else:
            fallback_scores = build_df_penalty_scores(
                list(stats.values()), year_df_primary, num_years
            )
            has_distinctive = any(item["distinctive"] for item in stats.values())
            fallback_items = [
                item
                for item in stats.values()
                if item["distinctive"]
                or max(item["countPrev"], item["countCurr"]) >= 2
            ]
            if not has_distinctive:
                filtered: list[ShiftTermStats] = []
                for item in fallback_items:
                    score_df = fallback_scores.get(item["term"], item["z"])
                    if abs(score_df) < SCORE_DF_MIN:
                        continue
                    filtered.append(item)
                fallback_items = filtered

            def _score_bucket(score: float) -> float:
                return round(score, 9)

            def sort_key_riser(
                item: ShiftTermStats,
            ) -> tuple[float, int, int, float, str]:
                score_df = fallback_scores.get(item["term"], item["z"])
                min_count = min(item["countPrev"], item["countCurr"])
                total_count = item["countPrev"] + item["countCurr"]
                abs_delta = abs(item["deltaPer10k"])
                return (
                    -_score_bucket(score_df),
                    -min_count,
                    -total_count,
                    -abs_delta,
                    item["term"],
                )

            def sort_key_faller(
                item: ShiftTermStats,
            ) -> tuple[float, int, int, float, str]:
                score_df = fallback_scores.get(item["term"], item["z"])
                min_count = min(item["countPrev"], item["countCurr"])
                total_count = item["countPrev"] + item["countCurr"]
                abs_delta = abs(item["deltaPer10k"])
                return (
                    _score_bucket(score_df),
                    -min_count,
                    -total_count,
                    -abs_delta,
                    item["term"],
                )

            for item in stats.values():
                item["score"] = fallback_scores.get(item["term"], item["z"])

            sorted_risers = sorted(fallback_items, key=sort_key_riser)
            sorted_fallers = sorted(fallback_items, key=sort_key_faller)
            top_risers = build_shift_term_outputs(
                sorted_risers, includes_by_term=includes_by_term
            )
            top_fallers = build_shift_term_outputs(
                sorted_fallers, includes_by_term=includes_by_term
            )

        summary = build_shift_summary(extract_terms(top_risers), extract_terms(top_fallers))

        counts_prev_alt = counts_alt_by_year[idx - 1]
        counts_curr_alt = counts_alt_by_year[idx]
        stats_alt = log_odds_stats(
            counts_prev_alt,
            counts_curr_alt,
            bg_alt,
            bg_total_alt,
            prior_mass,
            year_df_alt,
            num_years,
        )

        top_risers_alt: list[ShiftTermAlt] = []
        top_fallers_alt: list[ShiftTermAlt] = []
        summary_alt = ""

        if stats_alt:
            sorted_risers_alt = sorted(
                stats_alt.values(), key=lambda item: (-item["z"], item["term"])
            )
            sorted_fallers_alt = sorted(
                stats_alt.values(), key=lambda item: (item["z"], item["term"])
            )
            top_risers_alt = build_alt_terms(sorted_risers_alt)
            top_fallers_alt = build_alt_terms(sorted_fallers_alt)
            if (len(top_risers_alt) + len(top_fallers_alt)) >= 10:
                summary_alt = build_shift_summary(
                    extract_terms(top_risers_alt), extract_terms(top_fallers_alt)
                )
            else:
                top_risers_alt = []
                top_fallers_alt = []

        payload: ShiftPairPayload = {
            "from": prev_section.year,
            "to": curr_section.year,
            "topRisers": top_risers,
            "topFallers": top_fallers,
            "summary": summary,
        }
        if top_risers_alt or top_fallers_alt:
            payload["topRisersAlt"] = top_risers_alt
            payload["topFallersAlt"] = top_fallers_alt
            payload["summaryAlt"] = summary_alt or summary

        shifts.append(payload)

    metrics: MetricsPayload = {
        "section": SECTION_NAME,
        "years": years,
        "drift_vs_prev": drift_vs_prev,
        "drift_ci_low": drift_ci_low,
        "drift_ci_high": drift_ci_high,
        "boilerplate_score": boilerplate_scores,
    }
    shifts_payload: ShiftsPayload = {"section": SECTION_NAME, "yearPairs": shifts}
    return metrics, similarity, shifts_payload


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute metrics for Item 1A text.")
    parser.add_argument("--input", help="JSON list of {year,text,paragraphs,confidence}.")
    parser.add_argument("--fixture-html", help="Fixture HTML to extract Item 1A from.")
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        help="Year list to use with --fixture-html (e.g., 2022 2023 2024).",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output directory for metrics JSON files (default: scripts/_reports/sec_metrics).",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.input:
        sections = load_sections_from_json(Path(args.input))
    elif args.fixture_html:
        if not args.years:
            raise SystemExit("--years is required when using --fixture-html.")
        sections = load_sections_from_fixture(Path(args.fixture_html), args.years)
    else:
        raise SystemExit("Provide --input or --fixture-html.")

    if not sections:
        raise SystemExit("No sections provided.")

    metrics, similarity, shifts = build_metrics(sections)

    default_out_dir = (
        Path(__file__).resolve().parents[1] / "scripts" / "_reports" / "sec_metrics"
    )
    out_dir = Path(args.out) if args.out else default_out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    write_json(out_dir / "metrics_10k_item1a.json", metrics)
    write_json(out_dir / "similarity_10k_item1a.json", similarity)
    write_json(out_dir / "shifts_10k_item1a.json", shifts)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
