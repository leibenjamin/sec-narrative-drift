import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, TypedDict, cast

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag


BLOCK_TAGS = {
    "p",
    "div",
    "br",
    "li",
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "td",
    "th",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
}

# BlockDoc + heading detection tuning.
BLOCK_MIN_CHARS = 30
HEADING_MAX_CHARS = 140
HEADING_PUNCT_MAX = 8
HEADING_UPPER_RATIO_MIN = 0.35
HEADING_TITLECASE_RATIO_MIN = 0.55
HEADING_NEIGHBOR_MAX_CHARS = 220

# TOC scoring tuning.
TOC_HEAD_BLOCKS = 80
TOC_SLICE_HEAD_BLOCKS = 60
TOC_MIN_PAGE_NUM_BLOCKS = 6
TOC_MIN_ITEM_CODE_BLOCKS = 6
TOC_MIN_DOTLEADER_BLOCKS = 3
TOC_MIN_ALT_PAIRS = 4

# Start candidate ordering.
ITEM1_ORDER_PENALTY = 0.20
WEAK_ITEM1A_NEAR_BLOCKS = 6
CANDIDATE_BASE_SCORE = 0.50
CANDIDATE_TOC_REGION_PENALTY = 0.45
CANDIDATE_TOC_HEAD_PENALTY = 0.35
CANDIDATE_CROSS_REF_PENALTY = 0.35
CANDIDATE_TOC_SIGNAL_PENALTY = 0.02
CANDIDATE_TOC_SIGNAL_MAX_PENALTY = 0.20

# End marker detection.
END_MIN_CHARS = 6000
END_MIN_BLOCKS = 40

# Header/footer cleanup.
HF_SHORT_MAX_CHARS = 40
HF_REPEAT_MIN = 3
PAGE_NUM_MAX_DIGITS = 4

# Confidence + gates.
MAX_SLICE_CHARS_REASONABLE = 250_000
CONF_CAP_IF_TOC_LIKE = 0.25
CONF_PENALTY_TOC_REMOVED = 0.05
CONF_PENALTY_END_FALLBACK = 0.12
CONF_PENALTY_END_NOT_FOUND_LONG = 0.25
STRONG_HEAD_SCAN_BLOCKS = 12
NARRATIVE_MIN_CHARS = 200
TOC_STRONG_SIGNAL_MIN = 6

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


class TocScore(TypedDict):
    pageNumBlocks: int
    itemCodeBlocks: int
    romanBlocks: int
    dotLeaderBlocks: int
    altPairs: int
    tocLike: bool


class CandidateDebug(TypedDict):
    idx: int
    score: float
    rule: str
    headPreview: str
    warningsSubset: list[str]


@dataclass
class Block:
    idx: int
    text: str
    tag: str
    ids: list[str]
    is_heading_like: bool
    raw_len: int
    upper_ratio: float
    titlecase_ratio: float
    punct_count: int


@dataclass
class BlockDoc:
    blocks: list[Block]
    full_text: str
    offsets: list[int]


@dataclass
class StartCandidate:
    idx: int
    rule: str
    score: float
    warnings: list[str]
    toc_score: TocScore
    head_preview: str
    cross_ref: bool
    in_toc_region: bool



def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n")]

    merged: list[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if line == "I" and idx + 1 < len(lines):
            next_line = lines[idx + 1]
            if next_line.startswith("TEM"):
                merged.append(f"I{next_line}")
                idx += 2
                continue
        if line == "RI" and idx + 1 < len(lines):
            next_line = lines[idx + 1]
            if next_line.startswith("SK"):
                merged.append(f"RI{next_line}")
                idx += 2
                continue
        if line == "RISK" and idx + 1 < len(lines):
            next_line = lines[idx + 1]
            if next_line.startswith("FACTORS"):
                merged.append(f"RISK {next_line}")
                idx += 2
                continue
        merged.append(line)
        idx += 1

    lines = merged

    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()

    output: list[str] = []
    blank_count = 0
    for line in lines:
        if line == "":
            blank_count += 1
            if blank_count <= 2:
                output.append("")
        else:
            blank_count = 0
            output.append(line)

    return "\n".join(output)


def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def choose_parser(html: str) -> str:
    head = html.lstrip()[:200].lower()
    if head.startswith("<?xml") or re.match(r"\s*<xbrl", head):
        return "lxml-xml"
    return "lxml"


def clean_html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, choose_parser(html))

    _strip_hidden_nodes(soup)

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    for tag in soup.find_all(BLOCK_TAGS):
        if tag.name == "br":
            tag.replace_with("\n")
        else:
            tag.append("\n")

    text = soup.get_text(separator="\n")
    return normalize_whitespace(text)


def _strip_hidden_nodes(soup: BeautifulSoup) -> None:
    hidden_style = re.compile(r"(display\s*:\s*none|visibility\s*:\s*hidden)", re.IGNORECASE)
    for tag in soup.find_all(True):
        if tag.name == "ix:hidden":
            tag.decompose()
            continue
        attrs = _coerce_attrs(getattr(tag, "attrs", None))
        if "ix:hidden" in attrs:
            tag.decompose()
            continue
        style_value = attrs.get("style")
        style = style_value if isinstance(style_value, str) else None
        if style is not None and hidden_style.search(style):
            tag.decompose()
            continue
        if "hidden" in attrs:
            tag.decompose()
            continue


def split_paragraphs(text: str, min_chars: int = 200) -> list[str]:
    paragraphs = [chunk.strip() for chunk in re.split(r"\n{2,}", text) if chunk.strip()]
    return [para for para in paragraphs if len(para) >= min_chars]


def _coerce_attrs(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    output: dict[str, Any] = {}
    for key, value in cast(dict[object, object], raw).items():
        if isinstance(key, str):
            output[key] = value
    return output


def safe_get_text(node: Any) -> str:
    if node is None:
        return ""
    getter = getattr(node, "get_text", None)
    if callable(getter):
        try:
            value = getter(" ", strip=True)
        except TypeError:
            value = getter()
        if isinstance(value, str):
            return value
        return str(value)
    return str(node)


def safe_get_attr(node: Any, name: str) -> Optional[str]:
    if node is None:
        return None
    getter = getattr(node, "get", None)
    if not callable(getter):
        return None
    value = getter(name)
    if isinstance(value, str):
        return value
    return None


ITEM1A_HEADING = re.compile(r"(?m)(^|\n\n+)\s*item\s*1\s*\.?\s*a\b", re.IGNORECASE)
ITEM3D_HEADING = re.compile(r"(?m)(^|\n\n+)\s*item\s*3\s*\.?\s*d\b", re.IGNORECASE)
ITEM3_HEADING = re.compile(r"(?m)^\s*item\s*3\b", re.IGNORECASE)
ITEM1C_HEADING = re.compile(r"(?m)(^|\n\n+)\s*item\s*1\s*\.?\s*c\b", re.IGNORECASE)
ITEM1A_RISK_HEADING = re.compile(
    r"(?m)^\s*item\s*1\s*\.?\s*a\b.*risk\s+factors?", re.IGNORECASE
)
ITEM3_RISK_HEADING = re.compile(
    r"(?m)^\s*item\s*3\b.*risk\s+factors?", re.IGNORECASE
)
ANCHOR_ITEM1A = re.compile(r"item\s*1\s*\.?\s*a", re.IGNORECASE)
ANCHOR_ITEM3D = re.compile(r"item\s*3\s*\.?\s*d", re.IGNORECASE)
ANCHOR_ITEM3 = re.compile(r"item\s*3\b", re.IGNORECASE)
END_MARKERS_10K: list[tuple[str, re.Pattern[str]]] = [
    ("1B", re.compile(r"(?m)(^|\n)\s*item\s*1\s*\.?\s*b\b", re.IGNORECASE)),
    ("1C", re.compile(r"(?m)(^|\n)\s*item\s*1\s*\.?\s*c\b", re.IGNORECASE)),
    ("2", re.compile(r"(?m)(^|\n)\s*item\s*2\b", re.IGNORECASE)),
]
END_MARKERS_20F: list[tuple[str, re.Pattern[str]]] = [
    ("4", re.compile(r"(?m)(^|\n)\s*item\s*4\b", re.IGNORECASE)),
    ("4A", re.compile(r"(?m)(^|\n)\s*item\s*4\s*a\b", re.IGNORECASE)),
    ("4B", re.compile(r"(?m)(^|\n)\s*item\s*4\s*b\b", re.IGNORECASE)),
]
RISK_FACTORS = re.compile(r"\brisk\s+factors?\b", re.IGNORECASE)
RISK_FACTORS_SLOPPY = re.compile(
    r"r\s*i\s*s\s*k\s+f\s*a\s*c\s*t\s*o\s*r\s*s", re.IGNORECASE
)
RISK_FACTORS_HEADING = re.compile(r"(?m)^\s*risk\s+factors?\b", re.IGNORECASE)
HEADING_LINE = re.compile(r"^(item\s+\d|risk factors|part\s+[ivx]+)\b", re.IGNORECASE)
MODAL_TERMS = ("may", "could", "adversely")

ITEM_1A_BLOCK = re.compile(r"\bitem\s*1\s*a\b", re.IGNORECASE)
ITEM_1_BLOCK = re.compile(r"\bitem\s*1\b", re.IGNORECASE)
ITEM_1B_BLOCK = re.compile(r"\bitem\s*1\s*b\b", re.IGNORECASE)
ITEM_1C_BLOCK = re.compile(r"\bitem\s*1\s*c\b", re.IGNORECASE)
ITEM_2_BLOCK = re.compile(r"\bitem\s*2\b", re.IGNORECASE)
ITEM_1_BUSINESS_BLOCK = re.compile(r"\bitem\s*1\b.*\bbusiness\b", re.IGNORECASE)
PART_I_BLOCK = re.compile(r"\bpart\s+i\b", re.IGNORECASE)
ITEM_3_BLOCK = re.compile(r"\bitem\s*3\b", re.IGNORECASE)
ITEM_3D_BLOCK = re.compile(r"\bitem\s*3\s*d\b", re.IGNORECASE)
ITEM_4_BLOCK = re.compile(r"\bitem\s*4\b", re.IGNORECASE)
ITEM_4A_BLOCK = re.compile(r"\bitem\s*4\s*a\b", re.IGNORECASE)
ITEM_4B_BLOCK = re.compile(r"\bitem\s*4\s*b\b", re.IGNORECASE)
PART_II_BLOCK = re.compile(r"\bpart\s+ii\b", re.IGNORECASE)
ITEM_5_PLUS_BLOCK = re.compile(r"\bitem\s*(?:[5-9]|1[0-9])\b", re.IGNORECASE)
KEY_INFORMATION_BLOCK = re.compile(r"\bkey\s+information\b", re.IGNORECASE)
D_RISK_FACTORS_BLOCK = re.compile(r"^\s*d\.?\s+risk\s+factors?\b", re.IGNORECASE)
MDNA_BLOCK = re.compile(r"management'?s discussion and analysis", re.IGNORECASE)
PART_II_HEADING = re.compile(r"(?m)(^|\n)\s*part\s+ii\b", re.IGNORECASE)
ITEM_5_PLUS_HEADING = re.compile(r"(?m)(^|\n)\s*item\s*(?:[5-9]|1[0-9])\b", re.IGNORECASE)
MDNA_HEADING = re.compile(r"(?m)(^|\n)\s*management'?s discussion and analysis", re.IGNORECASE)

CROSS_REF_PREFIX = re.compile(
    r"\b(see|refer to|as described in|discussed in)\b.*\bitem\s*1\s*a\b",
    re.IGNORECASE,
)
CROSS_REF_QUOTED = re.compile(
    r"item\s*1\s*a\s*,\s*[\"']\s*risk\s+factors?",
    re.IGNORECASE,
)
CROSS_REF_AND_ITEM = re.compile(r"\band\s+item\s+1\b", re.IGNORECASE)
CROSS_REF_ITEM8 = re.compile(
    r"\band\s+our\s+consolidated\s+financial\s+statements\s+in\s+item\s+8\b",
    re.IGNORECASE,
)

TOC_PAGE_NUM = re.compile(r"^\d{1,4}$")
TOC_ITEM_CODE = re.compile(r"^\d{1,2}[A-Za-z]$")
TOC_ROMAN = re.compile(r"^[IVXLCDM]{1,7}$", re.IGNORECASE)
TOC_DOT_LEADER = re.compile(r"(?:\.\s*){2,}\d+\s*$")
TOC_ITEM_PREFIX = re.compile(r"^(item|part)\s+[0-9ivxlcdm]+", re.IGNORECASE)


def _collect_inline_text(node: Any) -> str:
    if isinstance(node, NavigableString):
        return str(node)
    if not isinstance(node, Tag):
        return ""
    if node.name in BLOCK_TAGS:
        return ""
    parts: list[str] = []
    for child in node.children:
        text = _collect_inline_text(child)
        if text:
            parts.append(text)
    return " ".join(parts)


def _extract_block_text(tag: Tag) -> str:
    if tag.name == "br":
        return ""
    parts: list[str] = []
    for child in tag.children:
        if isinstance(child, NavigableString):
            value = str(child)
            if value.strip():
                parts.append(value)
            continue
        if isinstance(child, Tag):
            if child.name in BLOCK_TAGS:
                continue
            text = _collect_inline_text(child)
            if text:
                parts.append(text)
    return collapse_whitespace(" ".join(parts))


def _collect_block_ids(tag: Tag) -> list[str]:
    seen: set[str] = set()
    ids: list[str] = []

    def consider(node: Tag) -> None:
        for attr in ("id", "name"):
            value = safe_get_attr(node, attr)
            if value and value not in seen:
                seen.add(value)
                ids.append(value)

    consider(tag)
    for child in tag.find_all(True):
        consider(child)
    return ids


def _word_ratios(text: str) -> tuple[float, float]:
    words = re.findall(r"[A-Za-z]{2,}", text)
    if not words:
        return 0.0, 0.0
    upper_count = 0
    title_count = 0
    for word in words:
        if word.isupper():
            upper_count += 1
        if word[0].isupper() and word[1:].islower():
            title_count += 1
    total = len(words)
    return upper_count / total, title_count / total


def _punct_count(text: str) -> int:
    return len(re.findall(r"[^\w\s]", text))


def _is_strong_item_heading(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if len(stripped) > HEADING_MAX_CHARS:
        return False
    if _is_cross_ref_suspected(stripped):
        return False
    if _is_toc_line(stripped):
        return False
    if re.search(r"\s\d{1,4}$", stripped):
        return False
    if ITEM1A_RISK_HEADING.search(stripped):
        return True
    if ITEM3_RISK_HEADING.search(stripped):
        return True
    if D_RISK_FACTORS_BLOCK.search(stripped):
        return True
    lowered = stripped.lower()
    if len(stripped) <= 80 and lowered.startswith("item"):
        if ITEM_1A_BLOCK.search(stripped) and _contains_risk_factors(stripped):
            return True
        if ITEM_3_BLOCK.search(stripped) and _contains_risk_factors(stripped):
            return True
    return False


def _is_heading_like(
    idx: int,
    texts: list[str],
    tags: list[str],
    upper_ratios: list[float],
    titlecase_ratios: list[float],
    punct_counts: list[int],
) -> bool:
    if tags[idx] in HEADING_TAGS:
        return True
    text = texts[idx]
    if _is_cross_ref_suspected(text):
        return False
    if _is_strong_item_heading(text):
        return True
    if not text or len(text) > HEADING_MAX_CHARS:
        return False
    if punct_counts[idx] > HEADING_PUNCT_MAX:
        return False
    if (
        upper_ratios[idx] < HEADING_UPPER_RATIO_MIN
        and titlecase_ratios[idx] < HEADING_TITLECASE_RATIO_MIN
    ):
        return False
    prev_len = len(texts[idx - 1]) if idx > 0 else 0
    next_len = len(texts[idx + 1]) if idx + 1 < len(texts) else 0
    if prev_len >= HEADING_NEIGHBOR_MAX_CHARS and next_len >= HEADING_NEIGHBOR_MAX_CHARS:
        return False
    return True


def build_blockdoc_from_html(html: str) -> BlockDoc:
    soup = BeautifulSoup(html, choose_parser(html))
    _strip_hidden_nodes(soup)
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    block_texts: list[str] = []
    block_tags: list[str] = []
    block_ids: list[list[str]] = []
    raw_lens: list[int] = []
    upper_ratios: list[float] = []
    titlecase_ratios: list[float] = []
    punct_counts: list[int] = []

    for tag in soup.find_all(BLOCK_TAGS):
        text = _extract_block_text(tag)
        if not text:
            continue
        block_texts.append(text)
        block_tags.append(tag.name or "text")
        block_ids.append(_collect_block_ids(tag))
        raw_lens.append(len(text))
        upper_ratio, title_ratio = _word_ratios(text)
        upper_ratios.append(upper_ratio)
        titlecase_ratios.append(title_ratio)
        punct_counts.append(_punct_count(text))

    heading_flags: list[bool] = []
    for idx in range(len(block_texts)):
        heading_flags.append(
            _is_heading_like(
                idx,
                block_texts,
                block_tags,
                upper_ratios,
                titlecase_ratios,
                punct_counts,
            )
        )

    blocks: list[Block] = []
    offsets: list[int] = []
    full_parts: list[str] = []
    offset = 0
    for idx, text in enumerate(block_texts):
        if idx > 0:
            offset += 2
        offsets.append(offset)
        full_parts.append(text)
        blocks.append(
            Block(
                idx=idx,
                text=text,
                tag=block_tags[idx],
                ids=block_ids[idx],
                is_heading_like=heading_flags[idx],
                raw_len=raw_lens[idx],
                upper_ratio=upper_ratios[idx],
                titlecase_ratio=titlecase_ratios[idx],
                punct_count=punct_counts[idx],
            )
        )
        offset += len(text)

    full_text = "\n\n".join(full_parts)
    return BlockDoc(blocks=blocks, full_text=full_text, offsets=offsets)


def _is_heading_boundary_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if len(stripped) > HEADING_MAX_CHARS:
        return False
    if _is_cross_ref_suspected(stripped):
        return False
    upper_ratio, title_ratio = _word_ratios(stripped)
    if (
        upper_ratio < HEADING_UPPER_RATIO_MIN
        and title_ratio < HEADING_TITLECASE_RATIO_MIN
    ):
        return False
    if _punct_count(stripped) > HEADING_PUNCT_MAX:
        return False
    return True


def build_blockdoc_from_text(text: str) -> BlockDoc:
    cleaned = normalize_whitespace(text)
    lines = cleaned.split("\n")
    blocks_raw: list[str] = []
    current: list[str] = []

    def flush_current() -> None:
        if not current:
            return
        block_text = collapse_whitespace(" ".join(current))
        if block_text:
            blocks_raw.append(block_text)
        current.clear()

    for line in lines:
        if not line.strip():
            flush_current()
            continue
        if _is_heading_boundary_line(line):
            flush_current()
            heading_text = collapse_whitespace(line)
            if heading_text:
                blocks_raw.append(heading_text)
            continue
        current.append(line)
    flush_current()

    block_texts: list[str] = []
    block_tags: list[str] = []
    raw_lens: list[int] = []
    upper_ratios: list[float] = []
    titlecase_ratios: list[float] = []
    punct_counts: list[int] = []

    for chunk in blocks_raw:
        text_chunk = chunk
        if not text_chunk:
            continue
        block_texts.append(text_chunk)
        block_tags.append("text")
        raw_lens.append(len(text_chunk))
        upper_ratio, title_ratio = _word_ratios(text_chunk)
        upper_ratios.append(upper_ratio)
        titlecase_ratios.append(title_ratio)
        punct_counts.append(_punct_count(text_chunk))

    heading_flags: list[bool] = []
    for idx in range(len(block_texts)):
        heading_flags.append(
            _is_heading_like(
                idx,
                block_texts,
                block_tags,
                upper_ratios,
                titlecase_ratios,
                punct_counts,
            )
        )

    blocks: list[Block] = []
    offsets: list[int] = []
    full_parts: list[str] = []
    offset = 0
    for idx, text_chunk in enumerate(block_texts):
        if idx > 0:
            offset += 2
        offsets.append(offset)
        full_parts.append(text_chunk)
        blocks.append(
            Block(
                idx=idx,
                text=text_chunk,
                tag=block_tags[idx],
                ids=[],
                is_heading_like=heading_flags[idx],
                raw_len=raw_lens[idx],
                upper_ratio=upper_ratios[idx],
                titlecase_ratio=titlecase_ratios[idx],
                punct_count=punct_counts[idx],
            )
        )
        offset += len(text_chunk)

    full_text = "\n\n".join(full_parts)
    return BlockDoc(blocks=blocks, full_text=full_text, offsets=offsets)


def _is_toc_signal(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if "table of contents" in stripped.lower():
        return True
    if TOC_PAGE_NUM.match(stripped):
        return True
    if TOC_ITEM_CODE.match(stripped):
        return True
    if TOC_ROMAN.match(stripped):
        return True
    if TOC_DOT_LEADER.search(stripped):
        return True
    if TOC_ITEM_PREFIX.match(stripped):
        return True
    return False


def score_toc_window(blocks: list[Block]) -> TocScore:
    page_num_blocks = 0
    item_code_blocks = 0
    roman_blocks = 0
    dot_leader_blocks = 0
    alt_pairs = 0
    toc_phrase = False

    for idx, block in enumerate(blocks):
        text = block.text.strip()
        if not text:
            continue
        lower = text.lower()
        if "table of contents" in lower:
            toc_phrase = True
        if TOC_PAGE_NUM.match(text):
            page_num_blocks += 1
        if TOC_ITEM_CODE.match(text):
            item_code_blocks += 1
        if TOC_ROMAN.match(text):
            roman_blocks += 1
        if TOC_DOT_LEADER.search(text):
            dot_leader_blocks += 1

        short_title = len(text) <= 25
        numeric_like = bool(TOC_PAGE_NUM.match(text) or TOC_ITEM_CODE.match(text) or TOC_ROMAN.match(text))
        if short_title and not numeric_like and not TOC_DOT_LEADER.search(text):
            if idx + 1 < len(blocks):
                next_text = blocks[idx + 1].text.strip()
                if TOC_PAGE_NUM.match(next_text) or TOC_ITEM_CODE.match(next_text):
                    alt_pairs += 1

    toc_like = False
    if dot_leader_blocks >= TOC_MIN_DOTLEADER_BLOCKS:
        toc_like = True
    if page_num_blocks >= TOC_MIN_PAGE_NUM_BLOCKS and alt_pairs >= TOC_MIN_ALT_PAIRS:
        toc_like = True
    if item_code_blocks >= TOC_MIN_ITEM_CODE_BLOCKS and page_num_blocks >= 4:
        toc_like = True
    if toc_phrase and (dot_leader_blocks + page_num_blocks) >= 3:
        toc_like = True

    return {
        "pageNumBlocks": page_num_blocks,
        "itemCodeBlocks": item_code_blocks,
        "romanBlocks": roman_blocks,
        "dotLeaderBlocks": dot_leader_blocks,
        "altPairs": alt_pairs,
        "tocLike": toc_like,
    }


def _has_title_tail(text: str, pattern: re.Pattern[str]) -> bool:
    match = pattern.search(text)
    if not match:
        return False
    tail = text[match.end() :]
    return re.search(r"[A-Za-z]{3,}", tail) is not None


def _is_toc_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if TOC_DOT_LEADER.search(stripped):
        return True
    if TOC_PAGE_NUM.match(stripped) or TOC_ITEM_CODE.match(stripped):
        return True
    return False


def _end_marker_block_ok(block: Block, pattern: re.Pattern[str]) -> bool:
    if block.is_heading_like:
        return True
    if len(block.text) > HEADING_MAX_CHARS:
        return False
    if _is_toc_line(block.text):
        return False
    return _has_title_tail(block.text, pattern)


def _end_marker_distance_ok(block_doc: BlockDoc, start_idx: int, end_idx: int) -> bool:
    if end_idx <= start_idx:
        return False
    char_dist = block_doc.offsets[end_idx] - block_doc.offsets[start_idx]
    block_dist = end_idx - start_idx
    return char_dist >= END_MIN_CHARS or block_dist >= END_MIN_BLOCKS


def _slice_blocks_by_offset(block_doc: BlockDoc, start_idx: int, end_offset: int) -> list[Block]:
    blocks = block_doc.blocks
    if not blocks:
        return []
    end_idx = start_idx
    for idx in range(start_idx + 1, len(blocks)):
        if block_doc.offsets[idx] >= end_offset:
            break
        end_idx = idx
    return blocks[start_idx : end_idx + 1]


def _block_index_for_offset(block_doc: BlockDoc, offset: int) -> int:
    blocks = block_doc.blocks
    if not blocks:
        return 0
    last_idx = 0
    for idx, start in enumerate(block_doc.offsets):
        if start >= offset:
            return idx
        last_idx = idx
    return last_idx


def _cleanup_repeated_headers(blocks: list[Block]) -> tuple[list[Block], list[str]]:
    warnings: list[str] = []
    if not blocks:
        return [], warnings

    freq: dict[str, int] = {}
    for block in blocks:
        text = block.text.strip()
        if not text or len(text) > HF_SHORT_MAX_CHARS:
            continue
        key = text.lower()
        freq[key] = freq.get(key, 0) + 1

    def is_page_num(text: str) -> bool:
        stripped = text.strip()
        return stripped.isdigit() and len(stripped) <= PAGE_NUM_MAX_DIGITS

    cleaned: list[Block] = []
    for block in blocks:
        text = block.text.strip()
        if text and len(text) <= HF_SHORT_MAX_CHARS:
            key = text.lower()
            if freq.get(key, 0) >= HF_REPEAT_MIN:
                continue
            if is_page_num(text) and freq.get(key, 0) >= HF_REPEAT_MIN:
                continue
        cleaned.append(block)

    toc_repeats = 0
    for block in cleaned:
        if "table of contents" in block.text.lower():
            toc_repeats += 1
    if toc_repeats >= HF_REPEAT_MIN:
        warnings.append("toc_header_repeated")

    return cleaned, warnings


def _is_strong_risk_heading(block: Block, form_type: str) -> bool:
    text = block.text
    if not block.is_heading_like:
        return False
    if form_type == "20-F":
        if ITEM_3D_BLOCK.search(text) and _contains_risk_factors(text):
            return True
        if D_RISK_FACTORS_BLOCK.search(text):
            return True
        if ITEM_3_BLOCK.search(text) and _contains_risk_factors(text):
            return True
        return False
    return ITEM_1A_BLOCK.search(text) is not None and _contains_risk_factors(text)


def _strong_heading_in_head(blocks: list[Block], form_type: str, limit: int) -> bool:
    end = min(len(blocks), limit)
    for idx in range(end):
        if _is_strong_risk_heading(blocks[idx], form_type):
            return True
    return False


def _business_before_item1a(blocks: list[Block]) -> bool:
    first_item1a: Optional[int] = None
    for idx, block in enumerate(blocks):
        if _is_strong_risk_heading(block, "10-K"):
            first_item1a = idx
            break
    if first_item1a is None:
        return False
    for idx in range(first_item1a):
        block = blocks[idx]
        if block.is_heading_like and ITEM_1_BUSINESS_BLOCK.search(block.text):
            return True
    return False


def _narrative_blocks_in_head(blocks: list[Block], limit: int) -> int:
    count = 0
    end = min(len(blocks), limit)
    for idx in range(end):
        block = blocks[idx]
        if block.is_heading_like:
            continue
        if len(block.text) >= NARRATIVE_MIN_CHARS:
            count += 1
    return count


def _apply_confidence_adjustments(
    score: float,
    toc_like_head: bool,
    toc_removed: bool,
    end_fallback: bool,
    end_not_found: bool,
    slice_len: int,
    cross_ref_suspected: bool,
    strong_heading_near: bool,
) -> float:
    adjusted = score
    if toc_removed:
        adjusted -= CONF_PENALTY_TOC_REMOVED
    if end_fallback:
        adjusted -= CONF_PENALTY_END_FALLBACK
    if end_not_found and slice_len > MAX_SLICE_CHARS_REASONABLE:
        adjusted -= CONF_PENALTY_END_NOT_FOUND_LONG
    if toc_like_head:
        adjusted = min(adjusted, CONF_CAP_IF_TOC_LIKE)
    if cross_ref_suspected and not strong_heading_near:
        adjusted = min(adjusted, CONF_CAP_IF_TOC_LIKE)
    return max(0.05, min(adjusted, 0.95))


def find_end_marker_blockdoc(
    block_doc: BlockDoc, start_idx: int, form_type: str
) -> tuple[Optional[int], Optional[str], bool]:
    blocks = block_doc.blocks
    if form_type == "20-F":
        primary = [
            ("4", ITEM_4_BLOCK),
            ("4A", ITEM_4A_BLOCK),
            ("4B", ITEM_4B_BLOCK),
        ]
        fallback = [("5", ITEM_5_PLUS_BLOCK)]
    else:
        primary = [
            ("1B", ITEM_1B_BLOCK),
            ("1C", ITEM_1C_BLOCK),
            ("2", ITEM_2_BLOCK),
        ]
        fallback = [("PART II", PART_II_BLOCK), ("5+", ITEM_5_PLUS_BLOCK)]

    for idx in range(start_idx + 1, len(blocks)):
        block = blocks[idx]
        text = block.text
        for label, pattern in primary:
            if not pattern.search(text):
                continue
            if not _end_marker_block_ok(block, pattern):
                continue
            if not _end_marker_distance_ok(block_doc, start_idx, idx):
                continue
            return idx, label, False

    for idx in range(start_idx + 1, len(blocks)):
        block = blocks[idx]
        text = block.text
        for label, pattern in fallback:
            if not pattern.search(text):
                continue
            if not _end_marker_block_ok(block, pattern):
                continue
            if not _end_marker_distance_ok(block_doc, start_idx, idx):
                continue
            return idx, label, True

    secondary = [("MD&A", MDNA_BLOCK)]
    for idx in range(start_idx + 1, len(blocks)):
        block = blocks[idx]
        text = block.text
        for label, pattern in secondary:
            if not pattern.search(text):
                continue
            if not _end_marker_block_ok(block, pattern):
                continue
            if not _end_marker_distance_ok(block_doc, start_idx, idx):
                continue
            return idx, label, True

    start_offset = block_doc.offsets[start_idx]
    search_start = min(len(block_doc.full_text), start_offset + END_MIN_CHARS)
    if form_type == "20-F":
        text_markers = END_MARKERS_20F + [("5", ITEM_5_PLUS_HEADING)]
    else:
        text_markers = END_MARKERS_10K + [
            ("PART II", PART_II_HEADING),
            ("5+", ITEM_5_PLUS_HEADING),
            ("MD&A", MDNA_HEADING),
        ]
    end_offset, end_label = find_end_marker_in_text(
        block_doc.full_text, search_start, text_markers
    )
    if end_offset is not None and end_label is not None:
        end_block_idx = _block_index_for_offset(block_doc, end_offset)
        if _end_marker_distance_ok(block_doc, start_idx, end_block_idx):
            return end_block_idx, end_label, True

    return None, None, False


def detect_toc_region(blocks: list[Block]) -> tuple[bool, Optional[int], TocScore]:
    if not blocks:
        empty: TocScore = {
            "pageNumBlocks": 0,
            "itemCodeBlocks": 0,
            "romanBlocks": 0,
            "dotLeaderBlocks": 0,
            "altPairs": 0,
            "tocLike": False,
        }
        return False, None, empty
    head_blocks = blocks[:TOC_HEAD_BLOCKS]
    doc_head_score = score_toc_window(head_blocks)
    window_size = min(TOC_SLICE_HEAD_BLOCKS, len(head_blocks))
    toc_score = doc_head_score
    window_start: Optional[int] = None
    if window_size > 0:
        for start in range(0, len(head_blocks) - window_size + 1):
            score = score_toc_window(head_blocks[start : start + window_size])
            if score["tocLike"]:
                toc_score = score
                window_start = start
                break
    if window_start is None:
        return False, None, doc_head_score
    toc_end_idx: Optional[int] = None
    scan_start = window_start
    scan_end = min(window_start + window_size, len(head_blocks))
    for idx in range(scan_start, scan_end):
        block = head_blocks[idx]
        if _is_toc_signal(block.text):
            toc_end_idx = idx
    if toc_end_idx is None:
        toc_end_idx = scan_end - 1
    return True, toc_end_idx + 1, toc_score


def _find_heading_index(
    blocks: list[Block], pattern: re.Pattern[str], start: int = 0
) -> Optional[int]:
    for block in blocks[start:]:
        if block.is_heading_like and pattern.search(block.text):
            return block.idx
    return None


def _has_nearby_strong_item1a(blocks: list[Block], idx: int) -> bool:
    start = max(0, idx - WEAK_ITEM1A_NEAR_BLOCKS)
    end = min(len(blocks), idx + WEAK_ITEM1A_NEAR_BLOCKS + 1)
    for offset in range(start, end):
        if offset == idx:
            continue
        block = blocks[offset]
        if not block.is_heading_like:
            continue
        if ITEM_1A_BLOCK.search(block.text) and _contains_risk_factors(block.text):
            return True
    return False


def _is_cross_ref_suspected(text: str) -> bool:
    if not ITEM_1A_BLOCK.search(text):
        return False
    if CROSS_REF_PREFIX.search(text):
        return True
    if CROSS_REF_QUOTED.search(text):
        return True
    if CROSS_REF_AND_ITEM.search(text) and _contains_risk_factors(text):
        return True
    if CROSS_REF_ITEM8.search(text):
        return True
    return False


def _score_start_candidate(
    rule: str,
    cross_ref: bool,
    in_toc_region: bool,
    toc_like_head: bool,
    before_item1: bool,
) -> float:
    rule_bonus = {
        "item1a_risk_heading": 0.3,
        "item1a_heading_followed_by_risk": 0.2,
        "risk_factors_heading": 0.1,
        "item3d_risk_heading": 0.3,
        "item3d_heading_followed_by_risk": 0.2,
        "d_risk_factors_heading": 0.1,
    }
    score = CANDIDATE_BASE_SCORE + rule_bonus.get(rule, 0.0)
    if in_toc_region:
        score -= CANDIDATE_TOC_REGION_PENALTY
    if toc_like_head:
        score -= CANDIDATE_TOC_HEAD_PENALTY
    if cross_ref:
        score -= CANDIDATE_CROSS_REF_PENALTY
    if before_item1:
        score -= ITEM1_ORDER_PENALTY
    return max(0.05, min(score, 0.95))


def analyze_blockdoc_candidates(block_doc: BlockDoc) -> dict[str, Any]:
    blocks = block_doc.blocks
    toc_detected, toc_region_end_idx, toc_score_doc_head = detect_toc_region(blocks)

    idx_part_i = _find_heading_index(blocks, PART_I_BLOCK)
    idx_item1_business = None
    if idx_part_i is not None:
        idx_item1_business = _find_heading_index(blocks, ITEM_1_BUSINESS_BLOCK, start=idx_part_i)
    else:
        idx_item1_business = _find_heading_index(blocks, ITEM_1_BUSINESS_BLOCK)

    candidate_rules: dict[int, str] = {}

    def add_candidate(idx: int, rule: str) -> None:
        priority = {
            "item1a_risk_heading": 3,
            "item1a_heading_followed_by_risk": 2,
            "risk_factors_heading": 1,
            "item3d_risk_heading": 3,
            "item3d_heading_followed_by_risk": 2,
            "d_risk_factors_heading": 1,
        }.get(rule, 0)
        existing = candidate_rules.get(idx)
        if existing is None:
            candidate_rules[idx] = rule
            return
        existing_priority = {
            "item1a_risk_heading": 3,
            "item1a_heading_followed_by_risk": 2,
            "risk_factors_heading": 1,
            "item3d_risk_heading": 3,
            "item3d_heading_followed_by_risk": 2,
            "d_risk_factors_heading": 1,
        }.get(existing, 0)
        if priority > existing_priority:
            candidate_rules[idx] = rule

    for idx, block in enumerate(blocks):
        if not block.is_heading_like:
            continue
        text = block.text
        if ITEM_1A_BLOCK.search(text) and _contains_risk_factors(text):
            add_candidate(idx, "item1a_risk_heading")
            continue
        if ITEM_1A_BLOCK.search(text):
            for look_idx in range(idx + 1, min(len(blocks), idx + 3)):
                if _contains_risk_factors(blocks[look_idx].text):
                    add_candidate(idx, "item1a_heading_followed_by_risk")
                    break
            continue

    form_type = "10-K"
    idx_item3 = None
    idx_item4 = None
    if not candidate_rules:
        start_search = toc_region_end_idx or 0
        idx_item3 = _find_heading_index(blocks, ITEM_3_BLOCK, start=start_search)
        idx_key_info = _find_heading_index(blocks, KEY_INFORMATION_BLOCK, start=start_search)
        if idx_item3 is None:
            idx_item3 = idx_key_info
        if idx_item3 is not None:
            idx_item4 = None
            for candidate in range(idx_item3 + 1, len(blocks)):
                block = blocks[candidate]
                if not block.is_heading_like:
                    continue
                if not ITEM_4_BLOCK.search(block.text):
                    continue
                if candidate - idx_item3 < END_MIN_BLOCKS:
                    continue
                idx_item4 = candidate
                break
            end = idx_item4 if idx_item4 is not None else len(blocks)
            for idx in range(idx_item3, end):
                block = blocks[idx]
                if not block.is_heading_like:
                    continue
                text = block.text
                if ITEM_3D_BLOCK.search(text) and _contains_risk_factors(text):
                    add_candidate(idx, "item3d_risk_heading")
                    continue
                if ITEM_3D_BLOCK.search(text):
                    for look_idx in range(idx + 1, min(end, idx + 3)):
                        if _contains_risk_factors(blocks[look_idx].text):
                            add_candidate(idx, "item3d_heading_followed_by_risk")
                            break
                    continue
                if D_RISK_FACTORS_BLOCK.search(text):
                    add_candidate(idx, "d_risk_factors_heading")
                    continue
                if _contains_risk_factors(text):
                    add_candidate(idx, "d_risk_factors_heading")
        if candidate_rules:
            form_type = "20-F"
    if candidate_rules and form_type == "10-K":
        for idx, block in enumerate(blocks):
            if not block.is_heading_like:
                continue
            if _contains_risk_factors(block.text) and _has_nearby_strong_item1a(blocks, idx):
                add_candidate(idx, "risk_factors_heading")
    if not candidate_rules:
        for idx, block in enumerate(blocks):
            if not block.is_heading_like:
                continue
            if _contains_risk_factors(block.text):
                add_candidate(idx, "risk_factors_heading")

    candidates: list[StartCandidate] = []
    for idx, rule in candidate_rules.items():
        block = blocks[idx]
        toc_score = score_toc_window(blocks[idx : idx + TOC_SLICE_HEAD_BLOCKS])
        in_toc_region = toc_region_end_idx is not None and idx < toc_region_end_idx
        cross_ref = _is_cross_ref_suspected(block.text)
        before_item1 = idx_item1_business is not None and idx < idx_item1_business
        warnings: list[str] = []
        if cross_ref:
            warnings.append("start_crossref_suspected")
        if toc_score["tocLike"]:
            warnings.append("toc_like_head")
        if before_item1 and form_type == "10-K":
            warnings.append("start_before_item1_business")
        if in_toc_region and toc_detected:
            warnings.append("toc_detected")
        score = _score_start_candidate(
            rule, cross_ref, in_toc_region, toc_score["tocLike"], before_item1
        )
        if toc_score["tocLike"]:
            toc_signal = (
                toc_score["pageNumBlocks"]
                + toc_score["itemCodeBlocks"]
                + toc_score["dotLeaderBlocks"]
                + toc_score["altPairs"]
            )
            if toc_signal > 0:
                toc_signal_penalty = min(
                    CANDIDATE_TOC_SIGNAL_MAX_PENALTY,
                    toc_signal * CANDIDATE_TOC_SIGNAL_PENALTY,
                )
                score = max(0.05, min(score - toc_signal_penalty, 0.95))
        head_preview = block.text[:160]
        candidates.append(
            StartCandidate(
                idx=idx,
                rule=rule,
                score=score,
                warnings=warnings,
                toc_score=toc_score,
                head_preview=head_preview,
                cross_ref=cross_ref,
                in_toc_region=in_toc_region,
            )
        )

    selected: Optional[StartCandidate] = None
    if candidates:
        non_cross_ref = [candidate for candidate in candidates if not candidate.cross_ref]
        pool = non_cross_ref if non_cross_ref else candidates
        pool.sort(key=lambda candidate: (-candidate.score, candidate.idx))
        selected = pool[0]

    return {
        "candidates": candidates,
        "selected": selected,
        "form_type": form_type,
        "toc_score_doc_head": toc_score_doc_head,
        "toc_region_end_idx": toc_region_end_idx,
        "idx_part_i": idx_part_i,
        "idx_item1_business": idx_item1_business,
        "idx_item3": idx_item3,
        "idx_item4": idx_item4,
    }


def format_candidate_report(candidates: list[StartCandidate], selected_idx: Optional[int]) -> str:
    lines: list[str] = []
    ordered = sorted(candidates, key=lambda candidate: (-candidate.score, candidate.idx))
    for candidate in ordered:
        marker = "*" if selected_idx is not None and candidate.idx == selected_idx else " "
        warning_text = ", ".join(candidate.warnings) if candidate.warnings else ""
        preview = candidate.head_preview.replace("\n", " ").strip()
        lines.append(
            f"{marker} idx={candidate.idx} score={candidate.score:.2f} rule={candidate.rule} "
            f"warnings=[{warning_text}] head={preview}"
        )
    return "\n".join(lines)


def _contains_risk_factors(text: str) -> bool:
    if RISK_FACTORS.search(text):
        return True
    return RISK_FACTORS_SLOPPY.search(text) is not None


def _find_end_marker(
    text: str, start_idx: int, markers: list[tuple[str, re.Pattern[str]]]
) -> tuple[Optional[int], Optional[str]]:
    end_idx: Optional[int] = None
    end_marker: Optional[str] = None
    for label, pattern in markers:
        match = pattern.search(text, start_idx + 1)
        if not match:
            continue
        idx = match.start()
        if end_idx is None or idx < end_idx:
            end_idx = idx
            end_marker = label
    return end_idx, end_marker


def find_end_marker_in_text(
    text: str, start_idx: int, markers: list[tuple[str, re.Pattern[str]]]
) -> tuple[Optional[int], Optional[str]]:
    return _find_end_marker(text, start_idx, markers)


def _toc_cluster_penalty(section_head: str) -> bool:
    lines = [line.strip() for line in section_head.splitlines() if line.strip()]
    count = 0
    for line in lines[:30]:
        if re.match(r"^item\s+\d", line, re.IGNORECASE):
            count += 1
    return count >= 4


def _strip_toc_block(section: str) -> tuple[str, bool, bool]:
    lines = section.splitlines()
    if not lines:
        return section, False, False
    head_lines = lines[:80]
    head_text = "\n".join(head_lines).lower()
    dot_leader = re.compile(r"\.{2,}\s*\d+\s*$")
    item_line = re.compile(r"^\s*item\s+\d", re.IGNORECASE)
    dot_lines = sum(1 for line in head_lines if dot_leader.search(line))
    item_lines = sum(1 for line in head_lines if item_line.search(line))
    toc_phrase = "table of contents" in head_text
    toc_detected = (toc_phrase and (dot_lines >= 2 or item_lines >= 3)) or (
        dot_lines >= 4 and item_lines >= 3
    )
    if not toc_detected:
        return section, False, False

    min_offset = 300
    match = ITEM1A_RISK_HEADING.search(section, min_offset)
    if match is None:
        match = ITEM3_RISK_HEADING.search(section, min_offset)
    if match is None:
        match = ITEM1A_HEADING.search(section, min_offset)
    if match is None:
        match = ITEM3D_HEADING.search(section, min_offset)
    if match:
        trimmed = section[match.start() :].lstrip()
        return trimmed, True, True
    return section, True, False


def _heading_density_bonus(section: str) -> float:
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    if not lines:
        return 0.0
    heading_like = sum(
        1
        for line in lines
        if len(line) <= 80 and (line.isupper() or HEADING_LINE.match(line))
    )
    density = heading_like / len(lines)
    if heading_like >= 6 and density >= 0.03:
        return 0.1
    return 0.0


def _modality_bonus(section: str) -> float:
    words = re.findall(r"[a-z]+", section.lower())
    if not words:
        return 0.0
    modal_count = sum(1 for word in words if word in MODAL_TERMS)
    modal_count += section.lower().count("subject to")
    per_1k = modal_count / (len(words) / 1000.0) if words else 0.0
    if per_1k >= 8:
        return 0.2
    if per_1k >= 4:
        return 0.1
    return 0.0


def _score_candidate(
    text: str, start_idx: int, end_idx: int, doc_length: int
) -> tuple[float, dict[str, float], list[str]]:
    warnings: list[str] = []
    base = 0.5
    length = max(0, end_idx - start_idx)
    length_bonus = 0.0
    if 15000 <= length <= 400000:
        length_bonus = 0.2
    elif length < 8000:
        length_bonus = -0.25
        warnings.append("length_out_of_band")
    else:
        length_bonus = -0.1
        warnings.append("length_out_of_band")

    early_penalty = 0.0
    if doc_length > 0 and start_idx < (doc_length * 0.05):
        early_penalty = -0.1
        warnings.append("early_position_penalty")

    head_snippet = text[start_idx : min(end_idx, start_idx + 2500)]
    toc_penalty = 0.0
    if _toc_cluster_penalty(head_snippet):
        toc_penalty = -0.2
        warnings.append("toc_cluster_penalty")

    modality_bonus = _modality_bonus(text[start_idx:end_idx])
    heading_bonus = _heading_density_bonus(text[start_idx:end_idx])

    score = base + length_bonus + early_penalty + toc_penalty + modality_bonus + heading_bonus
    score = max(0.05, min(score, 0.95))
    breakdown = {
        "base": base,
        "lengthBonus": length_bonus,
        "earlyPositionPenalty": early_penalty,
        "tocClusterPenalty": toc_penalty,
        "modalityBonus": modality_bonus,
        "headingDensityBonus": heading_bonus,
        "finalScore": score,
    }
    return score, breakdown, warnings


def _dedupe_warnings(warnings: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for warning in warnings:
        if warning in seen:
            continue
        seen.add(warning)
        ordered.append(warning)
    return ordered


def extract_item1a_from_blockdoc(
    block_doc: BlockDoc,
) -> tuple[str, float, str, list[str], dict[str, Any]]:
    analysis = analyze_blockdoc_candidates(block_doc)
    candidates = cast(list[StartCandidate], analysis.get("candidates", []))
    selected = cast(Optional[StartCandidate], analysis.get("selected"))

    toc_score_doc = cast(TocScore, analysis.get("toc_score_doc_head"))
    toc_detected = toc_score_doc.get("tocLike", False)

    debug_meta: dict[str, Any] = {
        "lengthChars": 0,
        "endMarkerUsed": None,
        "hasItem1C": False,
        "startMarker": None,
        "tocDetected": False,
        "tocRemoved": False,
    }

    debug_candidates: list[CandidateDebug] = []
    if candidates:
        ordered = sorted(candidates, key=lambda candidate: (-candidate.score, candidate.idx))
        for candidate in ordered[:5]:
            debug_candidates.append(
                {
                    "idx": candidate.idx,
                    "score": candidate.score,
                    "rule": candidate.rule,
                    "headPreview": candidate.head_preview[:160],
                    "warningsSubset": candidate.warnings[:3],
                }
            )

    if selected is None:
        debug_meta["debug"] = {
            "candidateCount": len(candidates),
            "topCandidates": debug_candidates,
            "selectedStart": None,
            "tocScoreDocHead": toc_score_doc,
            "idxPartI": analysis.get("idx_part_i"),
            "idxItem1Business": analysis.get("idx_item1_business"),
        }
        return "", 0.0, "blockdoc_not_found", ["item1a_not_found"], debug_meta

    form_type = cast(str, analysis.get("form_type", "10-K"))
    start_offset = block_doc.offsets[selected.idx]
    end_block_idx: Optional[int]
    end_marker: Optional[str]
    end_block_idx, end_marker, end_fallback = find_end_marker_blockdoc(
        block_doc, selected.idx, form_type
    )
    warnings: list[str] = list(selected.warnings)
    end_idx: Optional[int] = None

    if end_block_idx is None:
        end_idx = min(start_offset + 80000, len(block_doc.full_text))
        warnings.append("end_not_found")
        slice_blocks = _slice_blocks_by_offset(block_doc, selected.idx, end_idx)
    else:
        end_idx = block_doc.offsets[end_block_idx]
        if end_fallback:
            warnings.append("end_fallback_used")
        slice_blocks = block_doc.blocks[selected.idx : end_block_idx + 1]

    cleaned_blocks, cleanup_warnings = _cleanup_repeated_headers(slice_blocks)
    warnings.extend(cleanup_warnings)
    section = "\n\n".join(block.text for block in cleaned_blocks).strip()
    section, toc_detected_slice, toc_removed = _strip_toc_block(section)
    if toc_detected_slice:
        warnings.append("toc_detected")
    if toc_removed:
        warnings.append("toc_removed")

    score, breakdown, score_warnings = _score_candidate(
        block_doc.full_text, start_offset, end_idx, len(block_doc.full_text)
    )
    warnings.extend(score_warnings)

    if toc_detected and "toc_detected" not in warnings:
        warnings.append("toc_detected")

    slice_toc_score = score_toc_window(cleaned_blocks[:TOC_SLICE_HEAD_BLOCKS])
    warnings = [warning for warning in warnings if warning != "toc_like_head"]
    if slice_toc_score["tocLike"]:
        warnings.append("toc_like_head")

    strong_head_near = _strong_heading_in_head(cleaned_blocks, form_type, STRONG_HEAD_SCAN_BLOCKS)
    score = _apply_confidence_adjustments(
        score=score,
        toc_like_head=slice_toc_score["tocLike"],
        toc_removed=toc_removed,
        end_fallback=end_fallback,
        end_not_found="end_not_found" in warnings,
        slice_len=len(section),
        cross_ref_suspected=selected.cross_ref,
        strong_heading_near=strong_head_near,
    )

    quality_gate_failed = False
    if slice_toc_score["tocLike"] and not strong_head_near:
        quality_gate_failed = True
        warnings.append("toc_like_head")

    if form_type == "10-K" and _business_before_item1a(cleaned_blocks):
        quality_gate_failed = True
        warnings.append("business_heading_inside_slice")

    if "end_not_found" in warnings and len(section) > MAX_SLICE_CHARS_REASONABLE:
        quality_gate_failed = True

    if slice_toc_score["tocLike"]:
        toc_signal = (
            slice_toc_score["pageNumBlocks"]
            + slice_toc_score["itemCodeBlocks"]
            + slice_toc_score["dotLeaderBlocks"]
        )
        if toc_signal >= TOC_STRONG_SIGNAL_MIN:
            narrative_blocks = _narrative_blocks_in_head(cleaned_blocks, 20)
            if narrative_blocks < 2:
                quality_gate_failed = True

    if form_type == "20-F":
        idx_item3 = analysis.get("idx_item3")
        idx_item4 = analysis.get("idx_item4")
        if isinstance(idx_item3, int):
            if selected.idx < idx_item3:
                quality_gate_failed = True
                warnings.append("anchor_low_confidence")
            if isinstance(idx_item4, int) and selected.idx >= idx_item4:
                quality_gate_failed = True
                warnings.append("anchor_low_confidence")

    warnings = _dedupe_warnings(warnings)

    has_item1c = bool(ITEM1C_HEADING.search(block_doc.full_text)) if form_type == "10-K" else False
    selected_end: Optional[dict[str, Any]] = None
    if end_block_idx is not None:
        selected_end = {
            "idx": end_block_idx,
            "rule": end_marker,
            "headPreview": block_doc.blocks[end_block_idx].text[:160],
        }

    debug_meta = {
        "lengthChars": len(section),
        "endMarkerUsed": end_marker,
        "hasItem1C": has_item1c,
        "startMarker": selected.rule,
        "tocDetected": toc_detected_slice or toc_detected,
        "tocRemoved": toc_removed,
        "qualityGateFailed": quality_gate_failed,
        "scoreBreakdown": breakdown,
        "debug": {
            "candidateCount": len(candidates),
            "topCandidates": debug_candidates,
            "selectedStart": {
                "idx": selected.idx,
                "rule": selected.rule,
                "headPreview": selected.head_preview[:160],
            },
            "selectedEnd": selected_end,
            "tocScoreDocHead": toc_score_doc,
            "tocScoreSliceHead": slice_toc_score,
            "idxPartI": analysis.get("idx_part_i"),
            "idxItem1Business": analysis.get("idx_item1_business"),
        },
    }
    return section, score, "blockdoc_scored", warnings, debug_meta


def extract_item1a_from_text(
    text: str,
) -> tuple[str, float, str, list[str], dict[str, Any]]:
    block_doc = build_blockdoc_from_text(text)
    if block_doc.blocks:
        return extract_item1a_from_blockdoc(block_doc)

    debug_meta = {
        "lengthChars": 0,
        "endMarkerUsed": None,
        "hasItem1C": bool(ITEM1C_HEADING.search(text)),
        "startMarker": None,
        "tocDetected": False,
        "tocRemoved": False,
    }
    return "", 0.0, "not_found", ["item1a_not_found"], debug_meta


def extract_item1a_from_html(
    html: str,
) -> tuple[str, float, str, list[str], dict[str, Any]]:
    block_doc = build_blockdoc_from_html(html)
    if block_doc.blocks:
        section, confidence, method, block_warnings, debug_meta = extract_item1a_from_blockdoc(
            block_doc
        )
        if method != "blockdoc_not_found":
            return section, confidence, method, block_warnings, debug_meta

    text = clean_html_to_text(html)
    return extract_item1a_from_text(text)


def extract_item_1a(text: str) -> tuple[str, float, str, list[str]]:
    section, confidence, method, warnings, _debug = extract_item1a_from_text(text)
    return section, confidence, method, warnings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract Item 1A from a fixture HTML file.")
    parser.add_argument("--fixture", required=True, help="Path to fixture HTML file.")
    parser.add_argument(
        "--debug-candidates",
        action="store_true",
        help="Print BlockDoc start candidate scores.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    html = Path(args.fixture).read_text(encoding="utf-8", errors="replace")
    section, confidence, method, warnings, debug_meta = extract_item1a_from_html(html)
    paragraphs = split_paragraphs(section)

    if args.debug_candidates:
        block_doc = build_blockdoc_from_html(html)
        analysis = analyze_blockdoc_candidates(block_doc)
        candidates = cast(list[StartCandidate], analysis.get("candidates", []))
        selected = cast(Optional[StartCandidate], analysis.get("selected"))
        selected_idx = selected.idx if selected else None
        print("candidate_scores:")
        if candidates:
            print(format_candidate_report(candidates, selected_idx))
        else:
            print("(no candidates)")

    preview = section[:300].replace("\n", " ").strip()

    print(f"confidence: {confidence:.2f}")
    print(f"method: {method}")
    if warnings:
        print(f"warnings: {warnings}")
    if debug_meta:
        print(f"debug: {debug_meta}")
    print(f"extracted_length: {len(section)}")
    print(f"paragraphs: {len(paragraphs)}")
    print(f"preview: {preview}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
