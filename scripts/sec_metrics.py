import argparse
import json
import math
import random
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence, cast

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from sec_extract_item1a import clean_html_to_text, extract_item_1a, split_paragraphs


SECTION_NAME = "10k_item1a"
STOPWORDS = set(ENGLISH_STOP_WORDS)
BOOTSTRAP_ITERATIONS = 200
BOOTSTRAP_SEED = 13


@dataclass(frozen=True)
class SectionYear:
    year: int
    text: str
    paragraphs: list[str]
    confidence: Optional[float] = None


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
    text = clean_html_to_text(html)
    section, confidence, _method, _errors = extract_item_1a(text)
    paragraphs = normalize_paragraphs(section, None)
    sections: list[SectionYear] = []
    for year in years:
        sections.append(
            SectionYear(year=year, text=section, paragraphs=paragraphs, confidence=confidence)
        )
    return sorted(sections, key=lambda section: section.year)


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z]{2,}", text.lower())
    return [token for token in tokens if token not in STOPWORDS]


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


def build_shift_summary(top_risers: list[dict[str, Any]], top_fallers: list[dict[str, Any]]) -> str:
    riser_terms = [entry["term"] for entry in top_risers[:3]]
    faller_terms = [entry["term"] for entry in top_fallers[:3]]
    risers_text = ", ".join(riser_terms)
    fallers_text = ", ".join(faller_terms)
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


def build_metrics(sections: list[SectionYear]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    years = [section.year for section in sections]
    drift_vs_prev: list[Optional[float]] = [None] * len(years)
    drift_ci_low: list[Optional[float]] = [None] * len(years)
    drift_ci_high: list[Optional[float]] = [None] * len(years)
    boilerplate_scores: list[Optional[float]] = [None] * len(years)

    valid_sections = [section for section in sections if is_valid_section(section)]
    valid_years = [section.year for section in valid_sections]
    valid_texts = [section.text for section in valid_sections]
    similarity: dict[str, Any]

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
                    rounded_row.append(round(float(value), 2))
            similarity_values.append(rounded_row)

        valid_index = {year: idx for idx, year in enumerate(valid_years)}

        for idx in range(1, len(sections)):
            prev_year = sections[idx - 1].year
            curr_year = sections[idx].year
            if prev_year in valid_index and curr_year in valid_index:
                sim = raw_similarity[valid_index[prev_year]][valid_index[curr_year]]
                drift = 1 - float(sim)
                drift_vs_prev[idx] = round_value(drift)
                low, high = compute_bootstrap_ci(
                    sections[idx - 1], sections[idx], vectorizer
                )
                drift_ci_low[idx] = round_value(low)
                drift_ci_high[idx] = round_value(high)

                prev_text = sections[idx - 1].text
                curr_text = sections[idx].text
                boilerplate_scores[idx] = round_value(boilerplate_score(prev_text, curr_text))

        similarity = {
            "section": SECTION_NAME,
            "years": valid_years,
            "cosineSimilarity": similarity_values,
        }
    else:
        similarity = {
            "section": SECTION_NAME,
            "years": [],
            "cosineSimilarity": [],
        }

    shifts: list[dict[str, Any]] = []
    for idx in range(1, len(valid_sections)):
        prev_section = valid_sections[idx - 1]
        curr_section = valid_sections[idx]
        counts_prev = Counter(tokenize(prev_section.text))
        counts_curr = Counter(tokenize(curr_section.text))
        scores = log_odds_ratio(counts_prev, counts_curr)
        if not scores:
            top_risers: list[dict[str, Any]] = []
            top_fallers: list[dict[str, Any]] = []
        else:
            sorted_risers = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
            sorted_fallers = sorted(scores.items(), key=lambda item: (item[1], item[0]))
            top_risers = [
                {"term": term, "score": round(float(score), 2)}
                for term, score in sorted_risers[:15]
            ]
            top_fallers = [
                {"term": term, "score": round(float(score), 2)}
                for term, score in sorted_fallers[:15]
            ]
        shifts.append(
            {
                "from": prev_section.year,
                "to": curr_section.year,
                "topRisers": top_risers,
                "topFallers": top_fallers,
                "summary": build_shift_summary(top_risers, top_fallers),
            }
        )

    metrics: dict[str, Any] = {
        "section": SECTION_NAME,
        "years": years,
        "drift_vs_prev": drift_vs_prev,
        "drift_ci_low": drift_ci_low,
        "drift_ci_high": drift_ci_high,
        "boilerplate_score": boilerplate_scores,
    }
    shifts_payload: dict[str, Any] = {"section": SECTION_NAME, "yearPairs": shifts}
    return metrics, similarity, shifts_payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
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
        default=str(Path.cwd()),
        help="Output directory for metrics JSON files.",
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

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    write_json(out_dir / "metrics_10k_item1a.json", metrics)
    write_json(out_dir / "similarity_10k_item1a.json", similarity)
    write_json(out_dir / "shifts_10k_item1a.json", shifts)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
