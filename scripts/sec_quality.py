import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence, TypeGuard, cast

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from sec_extract_item1a import extract_item1a_from_html, split_paragraphs


SECTION_NAME = "10k_item1a"
MAX_TERMS = 15
MAX_PARAGRAPHS_PER_YEAR = 3
BULLET_TOKEN = "__BULLET_BREAK__"
BULLET_SYMBOL = "\u2022"

COMMON_SHORT_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "can",
    "did",
    "do",
    "for",
    "had",
    "has",
    "i",
    "if",
    "in",
    "is",
    "it",
    "its",
    "may",
    "not",
    "nor",
    "of",
    "on",
    "or",
    "our",
    "per",
    "the",
    "to",
    "us",
    "we",
    "who",
    "why",
    "you",
}

SUFFIX_FRAGMENTS = [
    "mation",
    "mations",
    "tion",
    "tions",
    "sion",
    "sions",
    "ment",
    "ments",
    "ness",
    "less",
    "ance",
    "ances",
    "ence",
    "ences",
    "ing",
    "ings",
    "ity",
    "ities",
    "ative",
    "atives",
    "able",
    "ably",
    "ization",
    "izations",
    "tory",
    "tories",
]

BULLET_PATTERN = re.compile(r"\n\s*(?:\u2022|\u00b7|\*|\u2013|\u2014|-)\s+")
SHORT_SPLIT_PATTERN = re.compile(r"\b([A-Za-z]{1,3})\s*\n\s*([a-z][A-Za-z]+)")
TAIL_SPLIT_PATTERN = re.compile(r"\b([A-Za-z]{3,})\s*\n\s*([a-z]{1,2})\b")
SUFFIX_SPLIT_PATTERN = re.compile(r"\b([A-Za-z]{3,})\s*\n\s*([a-z]{2,})")


@dataclass(frozen=True)
class SectionYear:
    year: int
    paragraphs: list[str]
    confidence: Optional[float] = None


@dataclass(frozen=True)
class ShiftTerm:
    term: str
    score: float


@dataclass(frozen=True)
class ShiftPair:
    from_year: int
    to_year: int
    top_risers: list[ShiftTerm]
    top_fallers: list[ShiftTerm]


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


def starts_with_any(value: str, fragments: Sequence[str]) -> bool:
    for fragment in fragments:
        if value.startswith(fragment):
            return True
    return False


def normalize_excerpt_text(text: str) -> str:
    if not text:
        return ""
    normalized = (
        text.replace("\u00a0", " ")
        .replace("\u0091", "'")
        .replace("\u0092", "'")
        .replace("\u0093", '"')
        .replace("\u0094", '"')
        .replace("\u0096", "\u2013")
        .replace("\u0097", "\u2014")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )
    normalized = re.sub(r"([A-Za-z])-\n([A-Za-z])", r"\1\2", normalized)
    normalized = BULLET_PATTERN.sub(f"{BULLET_TOKEN}{BULLET_SYMBOL} ", normalized)

    def short_split(match: re.Match[str]) -> str:
        left = match.group(1)
        right = match.group(2)
        left_lower = left.lower()
        right_lower = right.lower()
        if left_lower in COMMON_SHORT_WORDS or right_lower in COMMON_SHORT_WORDS:
            return f"{left} {right}"
        return f"{left}{right}"

    def tail_split(match: re.Match[str]) -> str:
        left = match.group(1)
        right = match.group(2)
        left_lower = left.lower()
        right_lower = right.lower()
        if left_lower in COMMON_SHORT_WORDS or right_lower in COMMON_SHORT_WORDS:
            return f"{left} {right}"
        return f"{left}{right}"

    def suffix_split(match: re.Match[str]) -> str:
        left = match.group(1)
        right = match.group(2)
        right_lower = right.lower()
        if starts_with_any(right_lower, SUFFIX_FRAGMENTS):
            return f"{left}{right}"
        return f"{left} {right}"

    normalized = SHORT_SPLIT_PATTERN.sub(short_split, normalized)
    normalized = TAIL_SPLIT_PATTERN.sub(tail_split, normalized)
    normalized = SUFFIX_SPLIT_PATTERN.sub(suffix_split, normalized)
    normalized = re.sub(r"\s*\n+\s*", " ", normalized)
    normalized = re.sub(r"([A-Za-z])\s+([\u00ae\u2122\u2120])", r"\1\2", normalized)
    normalized = re.sub(r"([\u00ae\u2122\u2120])\s+([A-Za-z])", r"\1 \2", normalized)
    normalized = re.sub(r"\u201c\s+", "\u201c", normalized)
    normalized = re.sub(r"\s+\u201d", "\u201d", normalized)
    normalized = normalized.replace(BULLET_TOKEN, "\n")
    normalized = re.sub(r"\s{2,}", " ", normalized).strip()
    return normalized


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
        try:
            year = parse_year(entry.get("year"))
        except ValueError:
            continue
        text = parse_text(entry.get("text"))
        paragraphs = normalize_paragraphs(text, as_str_list(entry.get("paragraphs")))
        confidence = parse_confidence(entry.get("confidence"))
        sections.append(SectionYear(year=year, paragraphs=paragraphs, confidence=confidence))

    return sorted(sections, key=lambda section: section.year)


def load_sections_from_fixture(path: Path, years: Sequence[int]) -> list[SectionYear]:
    html = path.read_text(encoding="utf-8", errors="replace")
    section, confidence, _method, _errors, _debug = extract_item1a_from_html(html)
    paragraphs = normalize_paragraphs(section, None)
    sections: list[SectionYear] = []
    for year in years:
        sections.append(SectionYear(year=year, paragraphs=paragraphs, confidence=confidence))
    return sorted(sections, key=lambda section: section.year)


def parse_shift_terms(value: Any) -> list[ShiftTerm]:
    items = as_list(value)
    if items is None:
        return []
    terms: list[ShiftTerm] = []
    for item in items:
        entry = as_str_dict(item)
        if entry is None:
            continue
        term_value = entry.get("term")
        score_value = entry.get("score")
        if not isinstance(term_value, str):
            continue
        if not isinstance(score_value, (int, float)):
            continue
        terms.append(ShiftTerm(term=term_value, score=float(score_value)))
    return terms


def load_shifts(path: Path) -> list[ShiftPair]:
    payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        raise RuntimeError("Shift JSON must be an object.")
    pairs = as_list(payload_dict.get("yearPairs"))
    if pairs is None:
        raise RuntimeError("Shift JSON missing yearPairs.")
    shifts: list[ShiftPair] = []
    for item in pairs:
        entry = as_str_dict(item)
        if entry is None:
            continue
        try:
            from_year = parse_year(entry.get("from"))
            to_year = parse_year(entry.get("to"))
        except ValueError:
            continue
        top_risers = parse_shift_terms(entry.get("topRisers"))
        top_fallers = parse_shift_terms(entry.get("topFallers"))
        shifts.append(
            ShiftPair(
                from_year=from_year,
                to_year=to_year,
                top_risers=top_risers,
                top_fallers=top_fallers,
            )
        )
    return shifts


def build_highlight_terms(top_risers: Sequence[ShiftTerm], top_fallers: Sequence[ShiftTerm]) -> list[str]:
    terms = [term.term for term in top_risers[:MAX_TERMS]] + [
        term.term for term in top_fallers[:MAX_TERMS]
    ]
    seen: set[str] = set()
    output: list[str] = []
    for term in terms:
        key = term.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(term)
    return output


def compile_term_patterns(terms: Sequence[str]) -> list[re.Pattern[str]]:
    patterns: list[re.Pattern[str]] = []
    for term in terms:
        normalized = term.strip()
        if not normalized:
            continue
        pattern = re.compile(rf"\b{re.escape(normalized)}\b", re.IGNORECASE)
        patterns.append(pattern)
    return patterns


def compile_weighted_patterns(terms: Sequence[ShiftTerm]) -> list[tuple[str, re.Pattern[str], float]]:
    # Compile phrase-aware patterns with weights derived from ShiftTerm.score.
    patterns: list[tuple[str, re.Pattern[str], float]] = []
    hyphen_class = r"[-\u2010\u2011\u2012\u2013\u2014\u2212'\u2018\u2019]"
    for item in terms:
        term = item.term.strip()
        if not term:
            continue
        weight = max(abs(item.score), 0.5)
        if " " in term:
            parts = [re.escape(part) for part in term.split()]
            joiner = rf"(?:\s+|{hyphen_class}\s*)"
            pattern = re.compile(rf"\b{joiner.join(parts)}\b", re.IGNORECASE)
        else:
            pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        patterns.append((term, pattern, weight))
    return patterns


def _paragraph_is_candidate(paragraph: str) -> bool:
    if not paragraph:
        return False
    if len(paragraph) < 220:
        return False
    if len(paragraph) > 2600:
        return False
    digits = sum(ch.isdigit() for ch in paragraph)
    if digits / max(len(paragraph), 1) > 0.22:
        return False
    return True


def count_matches(text: str, patterns: Sequence[re.Pattern[str]]) -> int:
    return sum(len(pattern.findall(text)) for pattern in patterns)


def score_paragraph(
    paragraph: str,
    risers: Sequence[tuple[str, re.Pattern[str], float]],
    fallers: Sequence[tuple[str, re.Pattern[str], float]],
    direction: str,
) -> tuple[float, list[str]]:
    if not _paragraph_is_candidate(paragraph):
        return 0.0, []

    cross_weight = 0.25
    if direction not in {"from", "to"}:
        direction = "to"

    primary = risers if direction == "to" else fallers
    secondary = fallers if direction == "to" else risers

    score = 0.0
    hits: list[str] = []

    def add_hits(patterns: Sequence[tuple[str, re.Pattern[str], float]], multiplier: float) -> None:
        nonlocal score, hits
        for term, pattern, weight in patterns:
            count = len(pattern.findall(paragraph))
            if count <= 0:
                continue
            count = min(count, 3)
            score += multiplier * weight * count
            hits.append(term)

    add_hits(primary, 1.0)
    add_hits(secondary, cross_weight)

    if direction == "to":
        has_primary = any(pattern.findall(paragraph) for _term, pattern, _weight in risers)
    else:
        has_primary = any(pattern.findall(paragraph) for _term, pattern, _weight in fallers)
    if not has_primary:
        return 0.0, []

    seen: set[str] = set()
    uniq_hits: list[str] = []
    for term in hits:
        if term in seen:
            continue
        seen.add(term)
        uniq_hits.append(term)

    return score, uniq_hits


def select_top_paragraphs(
    paragraphs: Sequence[str],
    year: int,
    risers: Sequence[tuple[str, re.Pattern[str], float]],
    fallers: Sequence[tuple[str, re.Pattern[str], float]],
    direction: str,
    max_paragraphs: int = MAX_PARAGRAPHS_PER_YEAR,
) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for idx, paragraph in enumerate(paragraphs):
        normalized = normalize_excerpt_text(paragraph)
        if not normalized:
            continue
        score, hits = score_paragraph(normalized, risers, fallers, direction=direction)
        if score <= 0:
            continue
        scored.append(
            {
                "year": year,
                "paragraphIndex": idx,
                "text": normalized,
                "score": score,
                "hits": hits,
            }
        )

    if not scored:
        return []

    scored.sort(key=lambda item: (-item["score"], len(item["text"])))

    texts = [item["text"] for item in scored]
    try:
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=8000)
        vec_any = cast(Any, vec)
        matrix = vec_any.fit_transform(texts)
        sims = cosine_similarity(matrix)
    except Exception:
        return [
            {
                "year": item["year"],
                "paragraphIndex": item["paragraphIndex"],
                "text": item["text"],
            }
            for item in scored[:max_paragraphs]
        ]

    selected: list[int] = []
    candidates = list(range(len(scored)))
    diversity_lambda = 0.35

    while candidates and len(selected) < max_paragraphs:
        best_idx: Optional[int] = None
        best_value: Optional[float] = None
        for idx in candidates:
            relevance = float(scored[idx]["score"])
            if not selected:
                mmr = relevance
            else:
                max_sim = max(float(sims[idx][j]) for j in selected)
                mmr = relevance - diversity_lambda * max_sim
            if best_value is None or mmr > best_value:
                best_value = mmr
                best_idx = idx
        if best_idx is None:
            break
        selected.append(best_idx)
        candidates.remove(best_idx)

    selected_items = [scored[i] for i in selected]
    selected_items.sort(key=lambda item: -item["score"])
    return [
        {
            "year": item["year"],
            "paragraphIndex": item["paragraphIndex"],
            "text": item["text"],
        }
        for item in selected_items
    ]


def is_valid_section(section: Optional[SectionYear]) -> TypeGuard[SectionYear]:
    if section is None:
        return False
    if section.confidence is not None and section.confidence < 0.5:
        return False
    return bool(section.paragraphs)


def build_excerpt_pairs(
    sections: list[SectionYear], shifts: list[ShiftPair]
) -> list[dict[str, Any]]:
    sections_by_year = {section.year: section for section in sections}
    pairs: list[dict[str, Any]] = []

    for shift in shifts:
        highlight_terms = build_highlight_terms(shift.top_risers, shift.top_fallers)
        from_section = sections_by_year.get(shift.from_year)
        to_section = sections_by_year.get(shift.to_year)
        representative: list[dict[str, Any]] = []

        if is_valid_section(from_section) and is_valid_section(to_section):
            riser_patterns = compile_weighted_patterns(shift.top_risers[:MAX_TERMS])
            faller_patterns = compile_weighted_patterns(shift.top_fallers[:MAX_TERMS])
            representative = select_top_paragraphs(
                to_section.paragraphs,
                shift.to_year,
                riser_patterns,
                faller_patterns,
                direction="to",
            ) + select_top_paragraphs(
                from_section.paragraphs,
                shift.from_year,
                riser_patterns,
                faller_patterns,
                direction="from",
            )

        pairs.append(
            {
                "from": shift.from_year,
                "to": shift.to_year,
                "highlightTerms": highlight_terms,
                "representativeParagraphs": representative,
            }
        )

    return pairs


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build excerpts for compare pane.")
    parser.add_argument("--input", help="JSON list of {year,text,paragraphs,confidence}.")
    parser.add_argument("--fixture-html", help="Fixture HTML to extract Item 1A from.")
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        help="Year list to use with --fixture-html (e.g., 2022 2023 2024).",
    )
    parser.add_argument("--shifts", required=True, help="Path to shifts_10k_item1a.json.")
    parser.add_argument(
        "--out",
        default=str(Path.cwd()),
        help="Output directory for excerpts JSON.",
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

    shifts = load_shifts(Path(args.shifts))
    pairs = build_excerpt_pairs(sections, shifts)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {"section": SECTION_NAME, "pairs": pairs}
    write_json(out_dir / "excerpts_10k_item1a.json", payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
