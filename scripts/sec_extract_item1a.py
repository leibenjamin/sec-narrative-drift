"""Extract Item 1A (Risk Factors) sections from SEC 10-K/20-F HTML filings.

This script parses HTML filings fetched from SEC EDGAR and extracts the
Item 1A section text using rule-based HTML structure detection (heading
matching, tag boundary identification, confidence scoring).

**No LLM or ML model is involved.**  The extraction is fully deterministic
and reproducible from the same HTML input.  The output is plain text that
downstream scripts split into paragraphs for use as LLM job inputs.
"""
import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING, TypedDict, Union, cast

if TYPE_CHECKING:
    from typing import Iterable

    class Tag:
        name: str
        attrs: dict[str, Any]
        children: Iterable[Any]

        def find(self, name: Any = None, **kwargs: Any) -> Optional["Tag"]: ...

        def find_all(self, name: Any = None, **kwargs: Any) -> list["Tag"]: ...

        def find_parent(self, name: Any = None, **kwargs: Any) -> Optional["Tag"]: ...

        def decompose(self) -> None: ...

        def replace_with(self, item: Any) -> None: ...

        def append(self, item: Any) -> None: ...

        def get_text(self, separator: str = "", strip: bool = False) -> str: ...

        def get(self, key: str, default: Any = None) -> Any: ...

    class NavigableString(str):
        pass

    class BeautifulSoup:
        def __init__(
            self, markup: Any, features: Optional[str] = None, **kwargs: Any
        ) -> None: ...

        def __call__(self, name: Any = None, **kwargs: Any) -> list[Tag]: ...

        def find(self, name: Any = None, **kwargs: Any) -> Optional[Tag]: ...

        def find_all(self, name: Any = None, **kwargs: Any) -> list[Tag]: ...

        def get_text(self, separator: str = "", strip: bool = False) -> str: ...

else:
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
TOC_PAGE_SCAN_BLOCKS = 220
TOC_HEAD_MAX_PAGE = 3
TOC_TAIL_PAGE_WINDOW = 5
TOC_MIN_PAGE_NUM_BLOCKS = 6
TOC_MIN_ITEM_CODE_BLOCKS = 6
TOC_MIN_ITEM_PREFIX_BLOCKS = 4
TOC_MIN_DOTLEADER_BLOCKS = 3
TOC_MIN_ALT_PAIRS = 4
TOC_MIN_ROW_SIGNAL = 2
TOC_MIN_TITLE_PAGE_BLOCKS = 3
TOC_MIN_TRIPLET_HITS = 2
TOC_PAGE_FIRST_MIN_HITS = 3
TOC_WINDOW_STRIDE = 10
TOC_REGION_PAD_BLOCKS = 6
TOC_NARRATIVE_BLOCKS_MAX = 8
TOC_LONG_NARRATIVE_MAX = 5
END_MARKER_TOC_WINDOW_BLOCKS = 20

# Start candidate ordering.
ITEM1_ORDER_PENALTY = 0.20
WEAK_ITEM1A_NEAR_BLOCKS = 6
ITEM_FOLLOWUP_LOOKAHEAD = 6
CANDIDATE_BASE_SCORE = 0.50
CANDIDATE_TOC_REGION_PENALTY = 0.45
CANDIDATE_TOC_HEAD_PENALTY = 0.35
CANDIDATE_CROSS_REF_PENALTY = 0.35
CANDIDATE_TOC_SIGNAL_PENALTY = 0.02
CANDIDATE_TOC_SIGNAL_MAX_PENALTY = 0.20
CANDIDATE_CONTINUED_PENALTY = 0.50
CANDIDATE_CONTINUED_NARRATIVE_PENALTY = 0.15
CANDIDATE_CONTINUED_MARGIN = 0.05
CANDIDATE_NEAR_TIE_MARGIN = 0.03
CANDIDATE_NEAR_TIE_TOC_MARGIN = 0.06
CANDIDATE_ITEM1A_RISK_ADJ_BONUS = 0.06
CANDIDATE_HEADER_REPEAT_PENALTY = 0.25
CANDIDATE_FOLLOWUP_ITEM_PENALTY = 0.20
CANDIDATE_OVERVIEW_TABLE_PENALTY = 0.40
# Warnings that mark a candidate as structurally suspect (not a real heading).
_STRUCTURAL_SUSPECT_WARNINGS = frozenset(
    {"header_footer_repeat", "risk_overview_table", "toc_entry_page_num"}
)
ITEM1A_RISK_CLOSE_CHARS = 60
CANDIDATE_TOC_PAGE_MAX_DELTA = 3

# End marker detection.
END_MIN_CHARS = 6000
END_MIN_BLOCKS = 40

# Header/footer cleanup.
HF_SHORT_MAX_CHARS = 40
HF_REPEAT_MIN = 3
PAGE_NUM_MAX_DIGITS = 4
PAGE_MARKER_MAX_BLOCKS = 40
PAGE_MARKER_NEAR_BLOCKS = 6
PAGE_MARKER_SEQUENCE_MAX_BLOCKS = 600
PAGE_MARKER_SEQUENCE_MAX_DIFF = 3
PAGE_MARKER_ANCHOR_MAX_DELTA = 6

# Confidence + gates.
MAX_SLICE_CHARS_REASONABLE = 250_000
CONF_CAP_IF_TOC_LIKE = 0.25
CONF_PENALTY_TOC_REMOVED = 0.05
CONF_PENALTY_END_FALLBACK = 0.12
CONF_PENALTY_END_NOT_FOUND_LONG = 0.25
CONF_PENALTY_START_PURITY = 0.15
CONF_PENALTY_TOC_LIKE_TAIL = 0.30
CONF_PENALTY_TOC_RANGE_MISMATCH = 0.10
EARLY_PENALTY_RELIEF = 0.05
STRONG_HEAD_SCAN_BLOCKS = 12
NARRATIVE_MIN_CHARS = 200
TOC_STRONG_SIGNAL_MIN = 6
LATER_TRIPWIRE_TAIL_BLOCKS = 80
START_PURITY_BLOCKS = 10
TOC_TAIL_BLOCKS = 40
TOC_RANGE_TOLERANCE = 1
SHORT_TOC_PAGE_SPAN_MAX = 4

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


class TocScore(TypedDict):
    pageNumBlocks: int
    itemCodeBlocks: int
    itemPrefixBlocks: int
    romanBlocks: int
    dotLeaderBlocks: int
    altPairs: int
    titlePageBlocks: int
    tocLike: bool


class TocRegion(TypedDict):
    start_idx: int
    end_idx: int
    score: TocScore
    kind: str


class TocEntry(TypedDict):
    title: str
    item_code: Optional[str]
    page_start: Optional[int]
    page_end: Optional[int]
    raw: str
    idx: int


class TocMap(TypedDict, total=False):
    risk_page_start: int
    risk_page_end: int
    risk_row_text: str
    next_label: str
    next_item_code: str
    next_page_start: int
    next_row_text: str
    region_kind: str


def _new_toc_region_list() -> list[TocRegion]:
    return []


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
    toc_regions: list[TocRegion] = field(default_factory=_new_toc_region_list)
    unsafe_regions: list[TocRegion] = field(default_factory=_new_toc_region_list)
    toc_map: Optional[TocMap] = None


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


@dataclass
class PreparedHtml:
    """Pre-parsed HTML components for efficient reuse across extraction functions.

    This class holds the results of expensive HTML parsing operations so they
    can be shared across extract_item1a_from_prepared(), build_risk_raw_text_from_blockdoc(),
    and build_risk_html_slice_from_prepared() without redundant parsing.

    Attributes:
        soup: BeautifulSoup object with hidden nodes stripped and scripts removed.
        block_tags: List of block-level tags extracted from soup, in document order.
            Used for HTML slicing operations.
        block_doc: Structured BlockDoc with text extraction and heading detection.
            Note: BlockDoc.blocks may have fewer entries than block_tags because
            tags with empty text content are filtered out during BlockDoc construction.
    """

    soup: Any  # BeautifulSoup - use Any to avoid import issues outside TYPE_CHECKING
    block_tags: list[Tag]
    block_doc: "BlockDoc"


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


def build_risk_raw_text_from_html(
    html: str, start_block_idx: int, end_block_idx: int
) -> str:
    """Build raw text from HTML by extracting blocks in the given range.

    This function parses the HTML internally. For better performance when
    multiple operations need the parsed HTML, use prepare_html_for_extraction()
    followed by build_risk_raw_text_from_blockdoc().

    Args:
        html: Raw HTML string.
        start_block_idx: Starting block index (inclusive).
        end_block_idx: Ending block index (inclusive).

    Returns:
        Concatenated text from the specified block range.
    """
    block_doc = build_blockdoc_from_html(html)
    return build_risk_raw_text_from_blockdoc(block_doc, start_block_idx, end_block_idx)


def build_risk_html_slice_from_html(
    html: str,
    start_block_idx: int,
    end_block_idx: int,
    *,
    item: str,
    form_type: str,
    ticker: Optional[str] = None,
    cik: Optional[str] = None,
    accession: Optional[str] = None,
) -> str:
    soup = BeautifulSoup(html, choose_parser(html))
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    tags = soup.find_all(BLOCK_TAGS)
    if not tags:
        return ""
    start = max(0, min(start_block_idx, len(tags) - 1))
    end = max(start, min(end_block_idx, len(tags) - 1))
    slice_tags = tags[start : end + 1]
    slice_html = "".join(str(tag) for tag in slice_tags)

    wrapper_attrs = [
        'data-secnd="risk-slice"',
        f'data-item="{item}"',
        f'data-form="{form_type}"',
    ]
    if ticker:
        wrapper_attrs.append(f'data-ticker="{ticker}"')
    if cik:
        wrapper_attrs.append(f'data-cik="{cik}"')
    if accession:
        wrapper_attrs.append(f'data-accession="{accession}"')

    wrapped = f"<div {' '.join(wrapper_attrs)}>{slice_html}</div>"
    slice_soup = BeautifulSoup(wrapped, choose_parser(html))
    slice_soup_any = cast(Any, slice_soup)
    for tag in slice_soup_any(["script", "style", "noscript"]):
        tag.decompose()
    for tag in slice_soup_any.find_all(True):
        name = getattr(tag, "name", "")
        if ":" in name:
            unwrap = getattr(tag, "unwrap", None)
            if callable(unwrap):
                unwrap()
    container = slice_soup_any.find("div", attrs={"data-secnd": "risk-slice"})
    return str(container) if container is not None else str(slice_soup_any)


def build_risk_raw_text_from_blockdoc(
    block_doc: BlockDoc, start_block_idx: int, end_block_idx: int
) -> str:
    """Build raw text from a pre-built BlockDoc.

    This is the efficient version that avoids redundant HTML parsing.
    Use this when you have already built a BlockDoc via prepare_html_for_extraction().

    Args:
        block_doc: Pre-built BlockDoc (e.g., from PreparedHtml.block_doc).
        start_block_idx: Starting block index (inclusive).
        end_block_idx: Ending block index (inclusive).

    Returns:
        Concatenated text from the specified block range.
    """
    if not block_doc.blocks:
        return ""
    start = max(0, min(start_block_idx, len(block_doc.blocks) - 1))
    end = max(start, min(end_block_idx, len(block_doc.blocks) - 1))
    blocks = block_doc.blocks[start : end + 1]
    return "\n\n".join(block.text for block in blocks).strip()


def build_risk_html_slice_from_prepared(
    prepared: PreparedHtml,
    start_block_idx: int,
    end_block_idx: int,
    *,
    item: str,
    form_type: str,
    ticker: Optional[str] = None,
    cik: Optional[str] = None,
    accession: Optional[str] = None,
) -> str:
    """Build an HTML slice from pre-parsed HTML components.

    This is the efficient version that avoids redundant HTML parsing.
    Use this when you have already called prepare_html_for_extraction().

    Note: This function uses the block_tags list which contains ALL block-level
    tags from the preprocessed soup, including tags with empty text. The indices
    should correspond to the block_tags list, which may differ slightly from
    BlockDoc block indices (which filter out empty-text tags).

    Args:
        prepared: PreparedHtml containing soup and block_tags.
        start_block_idx: Starting block index (inclusive).
        end_block_idx: Ending block index (inclusive).
        item: Item code (e.g., "1A", "3D").
        form_type: Form type (e.g., "10-K", "20-F").
        ticker: Optional ticker symbol.
        cik: Optional CIK number.
        accession: Optional accession number.

    Returns:
        HTML string wrapped in a div with metadata attributes.
    """
    if not prepared.block_tags:
        return ""

    start = max(0, min(start_block_idx, len(prepared.block_tags) - 1))
    end = max(start, min(end_block_idx, len(prepared.block_tags) - 1))
    slice_tags = prepared.block_tags[start : end + 1]
    slice_html = "".join(str(tag) for tag in slice_tags)

    wrapper_attrs = [
        'data-secnd="risk-slice"',
        f'data-item="{item}"',
        f'data-form="{form_type}"',
    ]
    if ticker:
        wrapper_attrs.append(f'data-ticker="{ticker}"')
    if cik:
        wrapper_attrs.append(f'data-cik="{cik}"')
    if accession:
        wrapper_attrs.append(f'data-accession="{accession}"')

    wrapped = f"<div {' '.join(wrapper_attrs)}>{slice_html}</div>"
    # Parse just the small slice, not the full document
    slice_soup = BeautifulSoup(wrapped, "lxml")
    slice_soup_any = cast(Any, slice_soup)
    for tag in slice_soup_any(["script", "style", "noscript"]):
        tag.decompose()
    for tag in slice_soup_any.find_all(True):
        name = getattr(tag, "name", "")
        if ":" in name:
            unwrap = getattr(tag, "unwrap", None)
            if callable(unwrap):
                unwrap()
    container = slice_soup_any.find("div", attrs={"data-secnd": "risk-slice"})
    return str(container) if container is not None else str(slice_soup_any)


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


_SENTENCE_END = re.compile(r"[.!?][\"')\]]?$")


def _merge_short_paragraphs(paragraphs: list[str], min_chars: int) -> list[str]:
    merged: list[str] = []
    buffer: list[str] = []
    buffer_len = 0
    for chunk in paragraphs:
        text = chunk.strip()
        if not text:
            continue
        if _is_heading_shaped_text(text):
            if buffer:
                merged.append(" ".join(buffer).strip())
                buffer = []
                buffer_len = 0
            merged.append(text)
            continue
        buffer.append(text)
        buffer_len += len(text) + 1
        if buffer_len >= min_chars and _SENTENCE_END.search(text):
            merged.append(" ".join(buffer).strip())
            buffer = []
            buffer_len = 0
    if buffer:
        merged.append(" ".join(buffer).strip())
    return merged


def split_paragraphs(text: str, min_chars: int = 200) -> list[str]:
    paragraphs = [chunk.strip() for chunk in re.split(r"\n{2,}", text) if chunk.strip()]
    if not paragraphs:
        return []
    long_paras = [para for para in paragraphs if len(para) >= min_chars]
    if long_paras and len(long_paras) >= max(3, int(len(paragraphs) * 0.45)):
        return long_paras
    max_len = max(len(para) for para in paragraphs)
    avg_len = sum(len(para) for para in paragraphs) / len(paragraphs)
    target_chars = min_chars
    if max_len < min_chars:
        target_chars = max(min_chars, int(max_len * 2.5))
    elif avg_len < min_chars * 0.6:
        target_chars = max(min_chars, int(avg_len * 2))
    if avg_len < min_chars * 0.6 or max_len < min_chars or len(paragraphs) > 40:
        merged = _merge_short_paragraphs(paragraphs, target_chars)
        merged_long = [para for para in merged if len(para) >= min_chars]
        return merged_long if merged_long else [para for para in merged if para.strip()]
    return long_paras


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


ITEM_WORD = r"(?:item|i\s*t\s*e\s*m)"
ITEM_SEP = r"[.\-\u2013\u2014]"
ITEM1A_HEADING = re.compile(
    rf"(?m)(^|\n\n+)\s*{ITEM_WORD}\s*1\s*\.?\s*a\b", re.IGNORECASE
)
ITEM3D_HEADING = re.compile(
    rf"(?m)(^|\n\n+)\s*{ITEM_WORD}\s*3\s*\.?\s*d\b", re.IGNORECASE
)
ITEM3_HEADING = re.compile(r"(?m)^\s*item\s*3\b", re.IGNORECASE)
ITEM1C_HEADING = re.compile(
    rf"(?m)(^|\n\n+)\s*{ITEM_WORD}\s*1\s*{ITEM_SEP}?\s*c\b", re.IGNORECASE
)
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
    ("1B", re.compile(rf"(?m)(^|\n)\s*{ITEM_WORD}\s*1\s*{ITEM_SEP}?\s*b\b", re.IGNORECASE)),
    ("1C", re.compile(rf"(?m)(^|\n)\s*{ITEM_WORD}\s*1\s*{ITEM_SEP}?\s*c\b", re.IGNORECASE)),
    ("2", re.compile(rf"(?m)(^|\n)\s*{ITEM_WORD}\s*2\b", re.IGNORECASE)),
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
RISK_FACTORS_PREFIX = re.compile(r"^\s*risk\s+factors?\b\s*[:.\-]", re.IGNORECASE)
HEADING_LINE = re.compile(r"^(item\s+\d|risk factors|part\s+[ivx]+)\b", re.IGNORECASE)
MODAL_TERMS = ("may", "could", "adversely")
RISK_BURST_TERMS = ("may", "could", "might", "adverse", "adversely", "materially", "risk", "risks", "uncertain")
CONTINUED_MARKER = re.compile(r"\bcontinued\b", re.IGNORECASE)

ITEM_1A_BLOCK = re.compile(rf"\b{ITEM_WORD}\s*1\s*{ITEM_SEP}?\s*a\b", re.IGNORECASE)
ITEM_1_BLOCK = re.compile(r"\bitem\s*1\b", re.IGNORECASE)
ITEM_1B_BLOCK = re.compile(
    rf"\b{ITEM_WORD}\s*1\s*{ITEM_SEP}?\s*b\b", re.IGNORECASE
)
ITEM_1C_BLOCK = re.compile(
    rf"\b{ITEM_WORD}\s*1\s*{ITEM_SEP}?\s*c\b", re.IGNORECASE
)
ITEM_2_BLOCK = re.compile(rf"\b{ITEM_WORD}\s*2\b", re.IGNORECASE)
ITEM_1_BUSINESS_BLOCK = re.compile(r"\bitem\s*1\b.*\bbusiness\b", re.IGNORECASE)
PART_I_BLOCK = re.compile(r"\bpart\s+i\b", re.IGNORECASE)
ITEM_3_BLOCK = re.compile(r"\bitem\s*3\b", re.IGNORECASE)
ITEM_3D_BLOCK = re.compile(r"\bitem\s*3\s*d\b", re.IGNORECASE)
ITEM_4_BLOCK = re.compile(r"\bitem\s*4\b", re.IGNORECASE)
ITEM_4A_BLOCK = re.compile(r"\bitem\s*4\s*a\b", re.IGNORECASE)
ITEM_4B_BLOCK = re.compile(r"\bitem\s*4\s*b\b", re.IGNORECASE)
PART_II_BLOCK = re.compile(r"\bpart\s+ii\b", re.IGNORECASE)
ITEM_5_PLUS_BLOCK = re.compile(r"\bitem\s*(?:[5-9]|1[0-9])\b", re.IGNORECASE)
ITEM_7_BLOCK = re.compile(r"\bitem\s*7\b", re.IGNORECASE)
ITEM_8_BLOCK = re.compile(r"\bitem\s*8\b", re.IGNORECASE)
LEGAL_PROCEEDINGS_BLOCK = re.compile(r"\blegal\s+proceedings\b", re.IGNORECASE)
KEY_INFORMATION_BLOCK = re.compile(r"\bkey\s+information\b", re.IGNORECASE)
D_RISK_FACTORS_BLOCK = re.compile(r"^\s*d\.?\s+risk\s+factors?\b", re.IGNORECASE)
MDNA_BLOCK = re.compile(r"management'?s discussion and analysis", re.IGNORECASE)
FINANCIAL_STATEMENTS_BLOCK = re.compile(r"\bfinancial\s+statements\b", re.IGNORECASE)
NOTES_FINANCIAL_STATEMENTS_BLOCK = re.compile(
    r"\bnotes\s+to\s+consolidated\s+financial\s+statements\b", re.IGNORECASE
)
PART_II_HEADING = re.compile(r"(?m)(^|\n)\s*part\s+ii\b", re.IGNORECASE)
ITEM_5_PLUS_HEADING = re.compile(r"(?m)(^|\n)\s*item\s*(?:[5-9]|1[0-9])\b", re.IGNORECASE)
ITEM_7_HEADING = re.compile(r"(?m)(^|\n)\s*item\s*7\b", re.IGNORECASE)
ITEM_8_HEADING = re.compile(r"(?m)(^|\n)\s*item\s*8\b", re.IGNORECASE)
MDNA_HEADING = re.compile(r"(?m)(^|\n)\s*management'?s discussion and analysis", re.IGNORECASE)
FINANCIAL_STATEMENTS_HEADING = re.compile(
    r"(?m)(^|\n)\s*financial\s+statements\b", re.IGNORECASE
)
NOTES_FINANCIAL_STATEMENTS_HEADING = re.compile(
    r"(?m)(^|\n)\s*notes\s+to\s+consolidated\s+financial\s+statements\b",
    re.IGNORECASE,
)

CROSS_REF_VERB = re.compile(
    r"\b(see|refer to|as described in|described in|discussed in|included in|contained in|set forth in)\b",
    re.IGNORECASE,
)
CROSS_REF_PREFIX = re.compile(
    r"\b(see|refer to|as described in|described in|discussed in|included in|contained in|set forth in)\b.*\bitem\s*1\s*a\b",
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
CROSS_REF_TERMS = re.compile(
    r"\b(see|refer to|as described in|described in|discussed in|included in|contained in|set forth in)\b",
    re.IGNORECASE,
)
CROSS_REF_ITEM_OTHER = re.compile(r"\bitem\s*(?:7|8)\b", re.IGNORECASE)

TOC_PAGE_NUM = re.compile(r"^\d{1,4}$")
TOC_PAGE_RANGE = re.compile(r"^\d{1,4}\s*-\s*\d{1,4}$")
TOC_PAGE_RANGE_WITH_LETTER = re.compile(
    r"^[A-Z]{1,5}\s*-?\s*\d{1,4}\s*-\s*[A-Z]{1,5}\s*-?\s*\d{1,4}$",
    re.IGNORECASE,
)
TOC_PAGE_WITH_NUM = re.compile(
    r"^(page|pages)\s+\d{1,4}(?:\s*-\s*\d{1,4})?(?:\s*,\s*\d{1,4})*",
    re.IGNORECASE,
)
TOC_PAGE_WITH_LETTER = re.compile(r"^[A-Z]{1,5}\s*-?\s*\d{1,4}$", re.IGNORECASE)
TOC_PAGE_WITH_PART = re.compile(
    r"^(page|pages)\s+[A-Z]{1,5}\s*-?\s*\d{1,4}(?:\s*-\s*[A-Z]{1,5}\s*-?\s*\d{1,4})?(?:\s*,\s*[A-Z]{1,5}\s*-?\s*\d{1,4})*$",
    re.IGNORECASE,
)
TOC_ITEM_CODE = re.compile(r"^\d{1,2}[A-Za-z]$")
TOC_ITEM_CODE_DOT = re.compile(r"^\d\.[A-Za-z]\.?$")
TOC_ROMAN = re.compile(r"^[IVXLCDM]{1,7}$", re.IGNORECASE)
TOC_DOT_LEADER = re.compile(r"(?:\.\s*){2,}\d+\s*$")
TOC_ITEM_PREFIX = re.compile(r"^(item|part)\s+[0-9ivxlcdm]+", re.IGNORECASE)
TOC_ITEM_INLINE = re.compile(
    r"\bitem\s*(\d{1,2})\s*[\.\-]?\s*([a-z])?\b", re.IGNORECASE
)
TOC_ITEM_BARE = re.compile(r"\b(\d{1,2})\s*[\.\-]\s*([a-z])\b", re.IGNORECASE)
TOC_ITEM_CODE_PREFIX = re.compile(r"^\s*\d{1,2}\s*[\.\-]?\s*[A-Za-z]?\b")
TOC_TITLE_PAGE = re.compile(r"^[A-Za-z].*\s\d{1,4}$")
TOC_TITLE_PAGE_NUMERIC = re.compile(
    r"^\s*\d{1,2}\s*[A-Za-z]?\s*[.\-]?\s+.*\s\d{1,4}$"
)
TOC_TITLE_MAX_CHARS = 80
TOC_EARLY_PAGE_IGNORE_MAX = 6
TOC_HEADING = re.compile(r"\btable of contents\b", re.IGNORECASE)
XREF_INDEX_HEADING = re.compile(r"\bcross[- ]reference index\b", re.IGNORECASE)
INDEX_ITEM_MENTIONS = re.compile(r"\bitem\s+\d+[a-z]?\b", re.IGNORECASE)
PAGE_HEADER = re.compile(r"\bform\s+10-k\b|\bform\s+20-f\b", re.IGNORECASE)
PAGE_HEADER_NUM = re.compile(r"(\d{1,4})\s*$")
PAGE_HEADER_NUM_LEAD = re.compile(r"^\s*(\d{1,4})\b")
PAGE_WORD_LINE = re.compile(r"^\s*page\s+(\d{1,4})\s*$", re.IGNORECASE)
PAGE_OF_LINE = re.compile(r"^\s*(\d{1,4})\s+of\s+\d{1,4}\s*$", re.IGNORECASE)
HEADER_FOOTER_HINT = re.compile(
    r"\b(form\s+10-?k|form\s+20-?f|annual\s+report|company|corporation|corp\.?|inc\.?|ltd\.?|plc|group|bank|holdings)\b",
    re.IGNORECASE,
)
YEAR_HINT = re.compile(r"\b(19|20)\d{2}\b")

PART_PAGE_MULTIPLIER = 10000
DOC_PAGE_MAX = 500
DOC_PAGE_MIN_COUNT = 10
DOC_PAGE_CLUSTER_GAP = 3
DOC_PAGE_CLUSTER_MIN_SPAN = 5

RISK_RELATED_SUBHEAD = re.compile(r"\brisks?\s+related\s+to\b", re.IGNORECASE)

# Pre-compiled patterns for hot path functions (called millions of times)
# These were previously inline re.fullmatch/re.match/re.search calls causing
# 395+ million re._compile calls per filing.
_PAGE_NUM_SIMPLE = re.compile(r"(\d{1,4})[.)-]?$")
_PAGE_PART_RANGE = re.compile(
    r"([A-Za-z]{1,5})\s*-?\s*(\d{1,4})\s*-\s*([A-Za-z]{1,5})\s*-?\s*(\d{1,4})$",
    re.IGNORECASE,
)
_PAGE_PART_SINGLE = re.compile(r"([A-Za-z]{1,5})\s*-?\s*(\d{1,4})$", re.IGNORECASE)
_DIGITS_1_4 = re.compile(r"\d{1,4}")
_PAGE_LETTER_PREFIX = re.compile(r"^([A-Za-z]{1,5})\s*-?\s*\d{1,4}$")
_PAGE_PAGES_PREFIX = re.compile(r"^(page|pages)\s+", re.IGNORECASE)
_WHITESPACE_COLLAPSE = re.compile(r"\s+")
_ALPHA_2_PLUS = re.compile(r"[A-Za-z]{2,}")
_ALPHA_3_PLUS = re.compile(r"[A-Za-z]{3,}")
_ALNUM_PLUS = re.compile(r"[A-Za-z0-9]+")
_NON_ALNUM = re.compile(r"[^A-Za-z0-9]+")
_NON_WORD_SPACE = re.compile(r"[^\w\s]")
_ITEM_CODE_SUFFIX = re.compile(r"\d+[a-z]?$")
_ROMAN_NUMERAL = re.compile(r"[ivxlcdm]{1,4}$")
_PART_ROMAN = re.compile(r"part\s+[ivxlcdm]+$", re.IGNORECASE)
_PAGE_TRAILING_DIGITS = re.compile(r"\s\d{1,4}$")
_HEADER_YEAR_PAGE = re.compile(r"^(.+?)\s+(19|20)\d{2}\s+(\d{1,4})$")
_HEADER_PAGE_YEAR = re.compile(r"^(\d{1,4})\s+(.+?)\s+(19|20)\d{2}$")
_HEADER_PAGE_TEXT = re.compile(r"^(\d{1,4})\s+(.+)$")
_HEADER_TEXT_PAGE = re.compile(r"^(.+?)\s+(\d{1,4})$")
_PAGE_NUM_ONLY = re.compile(r"(\d{1,4})[.)-]?$")
_ITEM_NUM_LETTER = re.compile(r"\b(\d{1,2})([A-Za-z])\b")
_ITEM_NUM_WORD = re.compile(r"\bitem\s*(\d{1,2})\b", re.IGNORECASE)
_DOT_LEADER_COLLAPSE = re.compile(r"\.{2,}")
_TRAILING_PUNCT = re.compile(r"[.,;:]+$")
_PART_PREFIX = re.compile(r"^\s*part\s+[ivxlcdm]+\b", re.IGNORECASE)
_ITEM_1B_SEARCH = re.compile(r"(?m)^\s*item\s*1\s*\.?\s*b\b", re.IGNORECASE)
_LOWER_ALNUM = re.compile(r"[a-z0-9]+")
_LOWER_ALPHA = re.compile(r"[a-z]+")
_ITEM_LINE_START = re.compile(r"^item\s+\d", re.IGNORECASE)
_PAGE_DIGIT_START = re.compile(r"^\d{1,4}\s+\D+")
_PAGE_DIGIT_END = re.compile(r"^\D.+\s+\d{1,4}$")
# Additional patterns for _extract_inline_page_number (called 19.6M times)
_INLINE_PART_PREFIX = re.compile(
    r"^([A-Za-z]{1,5})\s*-?\s*(\d{1,4})\s+(.+)$", re.IGNORECASE
)
_INLINE_PART_SUFFIX = re.compile(
    r"^(.+?)\s+([A-Za-z]{1,5})\s*-?\s*(\d{1,4})$", re.IGNORECASE
)

NEXT_SECTION_LABELS: dict[str, tuple[str, bool]] = {
    "unresolved staff comments": ("Unresolved Staff Comments", False),
    "legal proceedings": ("Legal Proceedings", True),
    "properties": ("Properties", False),
    "sales and marketing": ("Sales and Marketing", False),
    "non gaap financial measures": ("Non-GAAP Financial Measures", False),
    "selected financial data": ("Selected Financial Data", False),
    "management s discussion and analysis of financial condition and results of operations": (
        "Management's Discussion and Analysis of Financial Condition and Results of Operations",
        False,
    ),
    "managements discussion and analysis of financial condition and results of operations": (
        "Management's Discussion and Analysis of Financial Condition and Results of Operations",
        False,
    ),
    "cybersecurity": ("Cybersecurity", False),
    "item 1c cybersecurity": ("Cybersecurity", False),
}


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


def _looks_like_clause(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 120:
        return False
    comma_count = stripped.count(",")
    semi_count = stripped.count(";")
    return (comma_count + semi_count) >= 2


def _normalize_heading_candidate(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return stripped
    stripped = re.sub(
        r"^\d{1,4}\s*[|.\-]\s+(?=(?:item|part)\s+[0-9ivx])",
        "",
        stripped,
        flags=re.IGNORECASE,
    )
    stripped = re.sub(
        r"^\d{1,4}\s+(?=(?:item|part)\s+[0-9ivx])",
        "",
        stripped,
        flags=re.IGNORECASE,
    )
    stripped = re.sub(
        r"^\d{1,4}\s+(?=\d{1,2}\s*[.\-]?\s*[A-Za-z]\b)",
        "",
        stripped,
        flags=re.IGNORECASE,
    )
    return stripped


def _is_heading_shaped_text(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if len(stripped) > HEADING_MAX_CHARS:
        return False
    normalized_label = re.sub(r"[^a-z0-9]+", " ", stripped.lower()).strip()
    if normalized_label in NEXT_SECTION_LABELS:
        return True
    if ITEM_1A_BLOCK.search(stripped) and _is_cross_ref_suspected(stripped):
        return False
    if _is_toc_line(stripped) or _is_page_number_line(stripped):
        return False
    if CROSS_REF_TERMS.search(stripped):
        return False
    if _punct_count(stripped) > HEADING_PUNCT_MAX:
        return False
    if _looks_like_clause(stripped):
        return False
    upper_ratio, title_ratio = _word_ratios(stripped)
    if (
        upper_ratio < HEADING_UPPER_RATIO_MIN
        and title_ratio < HEADING_TITLECASE_RATIO_MIN
    ):
        lowered = stripped.lower()
        if not lowered.startswith("item") and not lowered.startswith("part"):
            if not RISK_FACTORS_HEADING.search(stripped):
                return False
    return True


def _is_heading_shaped_block(block: Block) -> bool:
    if block.is_heading_like:
        return True
    return _is_heading_shaped_text(block.text)


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


def _build_blockdoc_from_tags(tags: list[Tag]) -> BlockDoc:
    """Build a BlockDoc from a list of pre-extracted block-level tags.

    This is the core BlockDoc construction logic, separated from HTML parsing
    to allow reuse when the soup has already been parsed.

    Args:
        tags: List of BeautifulSoup Tag objects (block-level elements).

    Returns:
        BlockDoc with blocks, full_text, and offsets. Tags with empty text
        content are filtered out, so len(blocks) may be less than len(tags).
    """
    block_texts: list[str] = []
    block_tag_names: list[str] = []
    block_ids: list[list[str]] = []
    raw_lens: list[int] = []
    upper_ratios: list[float] = []
    titlecase_ratios: list[float] = []
    punct_counts: list[int] = []

    for tag in tags:
        text = _extract_block_text(tag)
        if not text:
            continue
        block_texts.append(text)
        block_tag_names.append(tag.name or "text")
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
                block_tag_names,
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
                tag=block_tag_names[idx],
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


# ---------------------------------------------------------------------------
# Card-layout table detection and column-major reordering
# ---------------------------------------------------------------------------
# Some filings (e.g., ASML 20-F) use CSS-positioned multi-column "card"
# tables where each column is a risk factor card (title row + body row).
# The DOM reads row-by-row, grouping all titles then all bodies.  For correct
# reading order we need column-by-column: title1+body1, title2+body2, …
# The functions below detect these tables and reorder the block_tags list.

_CARD_TABLE_MIN_COLS = 7
_CARD_TABLE_CONTENT_WIDTH_MIN = 100  # pt
_CARD_TABLE_MIN_CONTENT_COLS = 3
_CARD_TABLE_MIN_ROWS = 4


def _build_table_column_grid(
    table_tag: Tag,
) -> tuple[dict[tuple[int, int], Tag], int, int]:
    """Build (row, col) -> <td>/<th> mapping, handling rowspan/colspan.

    Returns (grid, n_cols, n_rows).
    """
    tbody = table_tag.find("tbody")
    container = tbody if tbody else table_tag
    rows = container.find_all("tr", recursive=False)

    grid: dict[tuple[int, int], Tag] = {}
    occupied: set[tuple[int, int]] = set()
    max_col = 0

    for row_idx, row in enumerate(rows):
        cells = row.find_all(["td", "th"], recursive=False)
        col_idx = 0
        for cell in cells:
            while (row_idx, col_idx) in occupied:
                col_idx += 1
            rowspan = int(cell.get("rowspan", 1))
            colspan = int(cell.get("colspan", 1))
            for r in range(rowspan):
                for c in range(colspan):
                    occupied.add((row_idx + r, col_idx + c))
                    grid[(row_idx + r, col_idx + c)] = cell
            max_col = max(max_col, col_idx + colspan)
            col_idx += colspan

    return grid, max_col, len(rows)


def _detect_card_layout(table_tag: Tag) -> Optional[dict[str, Any]]:
    """Return layout info if *table_tag* uses a card-column pattern, else None.

    Detection criteria (conservative to avoid false positives):
    * First <tr> is a width-definition row: all cells empty, each with an
      explicit ``width:…pt`` style.
    * ≥ 7 columns, ≥ 3 of which are "content" columns (> 100 pt).
    * ≥ 4 rows total.
    """
    tbody = table_tag.find("tbody")
    container = tbody if tbody else table_tag
    rows = container.find_all("tr", recursive=False)
    if len(rows) < _CARD_TABLE_MIN_ROWS:
        return None

    first_cells = rows[0].find_all(["td", "th"], recursive=False)
    if len(first_cells) < _CARD_TABLE_MIN_COLS:
        return None

    col_widths: list[float] = []
    for cell in first_cells:
        # Width-definition cells must be empty and have a width style.
        if cell.get_text(strip=True):
            return None
        style = cell.get("style", "")
        m = re.search(r"width:\s*([\d.]+)pt", style)
        col_widths.append(float(m.group(1)) if m else 0)

    content_cols = [i for i, w in enumerate(col_widths) if w > _CARD_TABLE_CONTENT_WIDTH_MIN]
    if len(content_cols) < _CARD_TABLE_MIN_CONTENT_COLS:
        return None

    grid, n_cols, n_rows = _build_table_column_grid(table_tag)
    return {
        "table": table_tag,
        "grid": grid,
        "col_widths": col_widths,
        "content_cols": content_cols,
        "n_cols": n_cols,
        "n_rows": n_rows,
    }


def _assign_column_group(col_idx: int, content_cols: list[int]) -> int:
    """Map a column index to its content-column group (0-based)."""
    for g, cc in enumerate(content_cols):
        if col_idx <= cc:
            return g
    return len(content_cols) - 1


def _reorder_card_table_block_tags(
    block_tags: list[Tag], soup: Union[Tag, "BeautifulSoup"]
) -> list[Tag]:
    """Reorder *block_tags* so card-layout tables are read column-by-column.

    For every table that matches the card-layout pattern, block tags that are
    descendants of that table are rearranged so that all blocks belonging to
    column-group 0 come first (in their original row order), then column-group
    1, etc.  Tags that are table-structure elements (``table``, ``tbody``,
    ``tr``) or not inside any ``<td>`` are kept in front of the column groups.

    Non-card-table block tags are left in their original positions.
    """
    card_infos: list[dict[str, Any]] = []
    for table in soup.find_all("table"):
        info = _detect_card_layout(table)
        if info is not None:
            card_infos.append(info)

    if not card_infos:
        return block_tags

    result = list(block_tags)

    for info in card_infos:
        table = info["table"]
        grid = info["grid"]
        content_cols = info["content_cols"]

        # Map cell-id → column group
        cell_group: dict[int, int] = {}
        for (_, col), cell in grid.items():
            cid = id(cell)
            if cid not in cell_group:
                cell_group[cid] = _assign_column_group(col, content_cols)

        # Identify which entries in *result* belong to this table.
        table_desc_ids = {id(tag) for tag in table.find_all(BLOCK_TAGS)}
        table_desc_ids.add(id(table))
        table_indices = [i for i, tag in enumerate(result) if id(tag) in table_desc_ids]
        if not table_indices:
            continue
        first_idx = table_indices[0]
        last_idx = table_indices[-1]

        # Classify each tag in the range by column group.
        range_tags = result[first_idx : last_idx + 1]
        grouped: dict[int, list[Tag]] = {}
        for tag in range_tags:
            td_ancestor: Optional[Tag] = None
            if tag.name in ("td", "th"):
                td_ancestor = tag
            elif tag.name not in ("table", "tbody", "thead", "tfoot", "tr"):
                td_ancestor = tag.find_parent("td") or tag.find_parent("th")

            if td_ancestor is None:
                g = -1  # structural / non-cell tag
            else:
                g = cell_group.get(id(td_ancestor), -1)
            grouped.setdefault(g, []).append(tag)

        # Column-major ordering: structural tags, then each group in order.
        reordered: list[Tag] = []
        if -1 in grouped:
            reordered.extend(grouped[-1])
        for g in sorted(k for k in grouped if k >= 0):
            reordered.extend(grouped[g])

        result[first_idx : last_idx + 1] = reordered

    return result


# ---------------------------------------------------------------------------
# Risk overview/index table detection (for candidate penalty)
# ---------------------------------------------------------------------------
_OVERVIEW_RE = re.compile(r"\boverview\b", re.IGNORECASE)
_OVERVIEW_LOOKBEHIND_BLOCKS = 12
_OVERVIEW_LOOKAHEAD_BLOCKS = 30
_OVERVIEW_DENSE_THRESHOLD = 10


def _is_risk_overview_table(blocks: list[Block], candidate_idx: int) -> bool:
    """Return True if the candidate block appears to be inside a risk-factor
    overview/index table rather than being the actual section heading.

    Pattern: a short "Risk factor(s)" block preceded (within 12 blocks) by
    text containing "overview" and followed by a dense run of short blocks
    (10+ blocks under 160 chars) without any narrative-length body text.
    """
    text = blocks[candidate_idx].text.strip()
    if len(text) > 30:
        return False

    # Look behind for "overview" indicator.
    start = max(0, candidate_idx - _OVERVIEW_LOOKBEHIND_BLOCKS)
    has_overview = False
    for i in range(start, candidate_idx):
        if _OVERVIEW_RE.search(blocks[i].text):
            has_overview = True
            break
    if not has_overview:
        return False

    # Look ahead for a dense run of short blocks with no narrative body text.
    end = min(len(blocks), candidate_idx + _OVERVIEW_LOOKAHEAD_BLOCKS)
    short_count = 0
    for i in range(candidate_idx + 1, end):
        if len(blocks[i].text) >= NARRATIVE_MIN_CHARS:
            return False  # body text found — not an overview table
        if len(blocks[i].text) < 160:
            short_count += 1

    return short_count >= _OVERVIEW_DENSE_THRESHOLD


def _is_toc_entry_candidate(blocks: list[Block], candidate_idx: int) -> bool:
    """Return True if the candidate block appears to be a TOC/navigation entry.

    Pattern: a short heading-like block immediately followed (within 2 blocks)
    by a page-number block.  This is a reliable indicator of TOC-style listings
    even when the broader TOC scoring doesn't reach the ``tocLike`` threshold.
    """
    text = blocks[candidate_idx].text.strip()
    if len(text) > 40:
        return False
    end = min(len(blocks), candidate_idx + 3)
    for i in range(candidate_idx + 1, end):
        if _is_page_number_line(blocks[i].text):
            return True
    return False


def prepare_html_for_extraction(html: str) -> PreparedHtml:
    """Parse HTML once and prepare all components needed for extraction.

    This function centralizes the expensive HTML parsing and preprocessing,
    returning components that can be reused across multiple extraction functions:
    - extract_item1a_from_prepared()
    - build_risk_raw_text_from_blockdoc()
    - build_risk_html_slice_from_prepared()

    The preprocessing (hidden node stripping, script removal) is applied
    consistently to ensure block indices align between operations.

    Args:
        html: Raw HTML string from SEC filing.

    Returns:
        PreparedHtml containing the cleaned soup, block tags list, and BlockDoc.
    """
    soup = BeautifulSoup(html, choose_parser(html))
    _strip_hidden_nodes(soup)
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    block_tags = list(soup.find_all(BLOCK_TAGS))
    block_tags = _reorder_card_table_block_tags(block_tags, soup)
    block_doc = _build_blockdoc_from_tags(block_tags)

    return PreparedHtml(soup=soup, block_tags=block_tags, block_doc=block_doc)


def build_blockdoc_from_html(html: str) -> BlockDoc:
    """Build a BlockDoc from raw HTML.

    This function parses the HTML internally. For better performance when
    multiple operations need the parsed HTML, use prepare_html_for_extraction()
    instead and access the block_doc attribute.

    Args:
        html: Raw HTML string.

    Returns:
        BlockDoc with extracted blocks, full text, and offsets.
    """
    prepared = prepare_html_for_extraction(html)
    return prepared.block_doc


def _is_heading_boundary_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if _is_cross_ref_suspected(stripped):
        return False
    return _is_heading_shaped_text(stripped)


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


def _is_page_number_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if TOC_PAGE_NUM.match(stripped) or TOC_PAGE_RANGE.match(stripped):
        return True
    if TOC_PAGE_RANGE_WITH_LETTER.match(stripped):
        return True
    if TOC_PAGE_WITH_LETTER.match(stripped):
        return True
    if TOC_PAGE_WITH_NUM.match(stripped) or TOC_PAGE_WITH_PART.match(stripped):
        return True
    if _is_numeric_page_line(stripped) is not None:
        return True
    return False


def _is_page_range_text_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if _is_page_number_line(stripped):
        return True
    if TOC_PAGE_RANGE_WITH_LETTER.match(stripped):
        return True
    return re.fullmatch(r"[0-9\\s,\\-]+", stripped) is not None


def _is_item_code_only(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if TOC_ITEM_CODE.match(stripped):
        return True
    if TOC_ITEM_CODE_DOT.match(stripped):
        return True
    return False


def _starts_with_item_code(text: str) -> bool:
    stripped = text.strip()
    if TOC_ITEM_PREFIX.match(stripped):
        return True
    return TOC_ITEM_CODE_PREFIX.match(stripped) is not None


def _is_title_page_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped or len(stripped) > TOC_TITLE_MAX_CHARS:
        return False
    if TOC_TITLE_PAGE.match(stripped):
        return True
    if TOC_TITLE_PAGE_NUMERIC.match(stripped):
        return True
    return False


def _is_plausible_toc_title(text: str) -> bool:
    stripped = text.strip()
    if not stripped or len(stripped) > TOC_TITLE_MAX_CHARS:
        return False
    normalized_label = re.sub(r"[^a-z0-9]+", " ", stripped.lower()).strip()
    if normalized_label in NEXT_SECTION_LABELS:
        return True
    if _is_page_number_line(stripped) or _is_item_code_only(stripped):
        return False
    if TOC_DOT_LEADER.search(stripped):
        return False
    words = re.findall(r"[A-Za-z]{2,}", stripped)
    if len(words) < 2 or len(words) > 6:
        return False
    upper_ratio, title_ratio = _word_ratios(stripped)
    return upper_ratio >= 0.4 or title_ratio >= 0.5


def _looks_like_toc_triplet(blocks: list[Block], idx: int) -> bool:
    if idx + 2 >= len(blocks):
        return False
    first = blocks[idx].text.strip()
    second = blocks[idx + 1].text.strip()
    third = blocks[idx + 2].text.strip()
    if not _is_plausible_toc_title(first):
        return False
    if not _is_item_code_only(second):
        return False
    if not TOC_PAGE_NUM.match(third):
        return False
    return True


def _is_toc_heading(text: str) -> bool:
    return bool(TOC_HEADING.search(text))


def _roman_to_int(value: str) -> Optional[int]:
    cleaned = value.upper()
    if not TOC_ROMAN.match(cleaned):
        return None
    roman_map = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for char in reversed(cleaned):
        current = roman_map.get(char)
        if current is None:
            return None
        if current < prev:
            total -= current
        else:
            total += current
            prev = current
    return total if total > 0 else None


def _encode_part_page(prefix: str, page: int) -> Optional[int]:
    part = _roman_to_int(prefix)
    if part is None:
        return None
    return part * PART_PAGE_MULTIPLIER + page


def _parse_prefixed_page_value(prefix: str, page: int) -> Optional[int]:
    encoded = _encode_part_page(prefix, page)
    if encoded is not None:
        return encoded
    if len(prefix) == 1:
        return page
    return None


def _is_part_page_value(value: int) -> bool:
    return value >= PART_PAGE_MULTIPLIER


def _is_cross_reference_index_heading(text: str) -> bool:
    stripped = collapse_whitespace(text).strip()
    if not stripped:
        return False
    if len(stripped) > HEADING_MAX_CHARS:
        return False
    if not XREF_INDEX_HEADING.search(stripped):
        return False
    if "." in stripped:
        return False
    if '"' in stripped or "“" in stripped or "”" in stripped:
        return False
    words = re.findall(r"[A-Za-z0-9]+", stripped)
    if len(words) > 8:
        return False
    return True


def _is_index_with_item_mentions(text: str) -> bool:
    lower = text.lower()
    if "index" not in lower:
        return False
    if "financial statements" in lower:
        return False
    if len(text) > HEADING_MAX_CHARS:
        return False
    if not _is_heading_shaped_text(text):
        return False
    return len(INDEX_ITEM_MENTIONS.findall(text)) >= 2


def _repeat_text_key(text: str) -> str:
    return collapse_whitespace(text).lower()


def _build_repeat_texts(blocks: list[Block]) -> dict[str, int]:
    freq: dict[str, int] = {}
    for block in blocks:
        text = block.text.strip()
        if not text:
            continue
        if len(text) > HF_SHORT_MAX_CHARS:
            continue
        key = _repeat_text_key(text)
        freq[key] = freq.get(key, 0) + 1
    return freq


def _is_repeated_short_text(text: str, freq: dict[str, int]) -> bool:
    cleaned = text.strip()
    if not cleaned or len(cleaned) > HF_SHORT_MAX_CHARS:
        return False
    key = _repeat_text_key(cleaned)
    return freq.get(key, 0) >= HF_REPEAT_MIN


def score_toc_window(
    blocks: list[Block], repeat_freq: Optional[dict[str, int]] = None
) -> TocScore:
    page_num_blocks = 0
    numeric_only_blocks = 0
    item_code_blocks = 0
    item_prefix_blocks = 0
    roman_blocks = 0
    dot_leader_blocks = 0
    alt_pairs = 0
    title_page_blocks = 0
    toc_phrase = False
    triplet_hits = 0

    for idx, block in enumerate(blocks):
        text = block.text.strip()
        if not text:
            continue
        if _is_toc_heading(text):
            if repeat_freq is None or not _is_repeated_short_text(text, repeat_freq):
                toc_phrase = True
        if _is_page_number_line(text):
            page_num_blocks += 1
        if TOC_PAGE_NUM.match(text):
            numeric_only_blocks += 1
        if _is_item_code_only(text):
            item_code_blocks += 1
        if _starts_with_item_code(text):
            item_prefix_blocks += 1
        if TOC_ROMAN.match(text):
            roman_blocks += 1
        if TOC_DOT_LEADER.search(text):
            dot_leader_blocks += 1
        if _is_title_page_line(text):
            title_page_blocks += 1
        elif len(text) <= TOC_TITLE_MAX_CHARS and _parse_toc_row_line(text) is not None:
            title_page_blocks += 1

        short_title = len(text) <= 25
        numeric_like = bool(
            _is_page_number_line(text) or _is_item_code_only(text) or TOC_ROMAN.match(text)
        )
        if short_title and not numeric_like and not TOC_DOT_LEADER.search(text):
            if idx + 1 < len(blocks):
                next_text = blocks[idx + 1].text.strip()
                if TOC_PAGE_NUM.match(next_text):
                    alt_pairs += 1

    for idx in range(len(blocks) - 2):
        if _looks_like_toc_triplet(blocks, idx):
            triplet_hits += 1
    if triplet_hits:
        alt_pairs += triplet_hits * 2

    toc_like = False
    if dot_leader_blocks >= TOC_MIN_DOTLEADER_BLOCKS:
        toc_like = True
    if title_page_blocks >= TOC_MIN_TITLE_PAGE_BLOCKS and (
        item_prefix_blocks >= 2 or item_code_blocks >= 2
    ):
        toc_like = True
    if numeric_only_blocks >= TOC_MIN_PAGE_NUM_BLOCKS and alt_pairs >= TOC_MIN_ALT_PAIRS:
        toc_like = True
    if item_code_blocks >= TOC_MIN_ITEM_CODE_BLOCKS and numeric_only_blocks >= 4:
        toc_like = True
    if (
        triplet_hits >= TOC_MIN_TRIPLET_HITS
        and item_code_blocks >= 2
        and numeric_only_blocks >= 2
    ):
        toc_like = True
    if toc_phrase and (dot_leader_blocks + numeric_only_blocks + title_page_blocks) >= 3:
        toc_like = True

    toc_score: TocScore = {
        "pageNumBlocks": page_num_blocks,
        "itemCodeBlocks": item_code_blocks,
        "itemPrefixBlocks": item_prefix_blocks,
        "romanBlocks": roman_blocks,
        "dotLeaderBlocks": dot_leader_blocks,
        "altPairs": alt_pairs,
        "titlePageBlocks": title_page_blocks,
        "tocLike": toc_like,
    }
    return toc_score


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
    if _is_page_number_line(stripped) or _is_item_code_only(stripped):
        return True
    if _is_title_page_line(stripped):
        return True
    return False


def _parse_toc_page_number_simple(text: str) -> Optional[tuple[int, int]]:
    stripped = text.strip()
    match = _PAGE_NUM_SIMPLE.fullmatch(stripped)
    if match:
        stripped = match.group(1)
    part_range = _PAGE_PART_RANGE.fullmatch(stripped)
    if part_range:
        prefix_start = part_range.group(1)
        prefix_end = part_range.group(3)
        if prefix_start.upper() != prefix_end.upper():
            return None
        try:
            start_value = int(part_range.group(2))
            end_value = int(part_range.group(4))
        except ValueError:
            return None
        start_key = _parse_prefixed_page_value(prefix_start, start_value)
        end_key = _parse_prefixed_page_value(prefix_end, end_value)
        if start_key is None or end_key is None:
            return None
        if start_value <= end_value:
            return start_key, end_key
    part_single = _PAGE_PART_SINGLE.fullmatch(stripped)
    if part_single:
        prefix = part_single.group(1)
        try:
            value = int(part_single.group(2))
        except ValueError:
            return None
        encoded = _parse_prefixed_page_value(prefix, value)
        if encoded is not None:
            return encoded, encoded
    if TOC_PAGE_RANGE.match(stripped):
        parts = stripped.split("-")
        if len(parts) == 2:
            try:
                start = int(parts[0].strip())
                end = int(parts[1].strip())
            except ValueError:
                return None
            if start >= 1900 or end >= 1900:
                return None
            if start <= end:
                return start, end
    if TOC_PAGE_NUM.match(stripped):
        try:
            value = int(stripped)
        except ValueError:
            return None
        if value >= 1900:
            return None
        return value, value
    if TOC_PAGE_WITH_LETTER.match(stripped):
        match = _DIGITS_1_4.search(stripped)
        if match:
            prefix_match = _PAGE_LETTER_PREFIX.match(stripped)
            try:
                value = int(match.group(0))
            except ValueError:
                return None
            if prefix_match:
                prefix = prefix_match.group(1)
                encoded = _parse_prefixed_page_value(prefix, value)
                if encoded is not None:
                    return encoded, encoded
            if value >= 1900:
                return None
            return value, value
    return None


def _parse_toc_page_number(text: str) -> Optional[tuple[int, int]]:
    stripped = text.strip()
    if _PAGE_PAGES_PREFIX.match(stripped):
        stripped = _PAGE_PAGES_PREFIX.sub("", stripped)
    if "," in stripped:
        segments = [segment.strip() for segment in stripped.split(",") if segment.strip()]
        parsed_segments: list[tuple[int, int]] = []
        for segment in segments:
            parsed = _parse_toc_page_number_simple(segment)
            if parsed is not None:
                parsed_segments.append(parsed)
        if parsed_segments:
            if len(parsed_segments) > 1:
                later = [
                    seg for seg in parsed_segments if seg[1] > TOC_EARLY_PAGE_IGNORE_MAX
                ]
                if later:
                    parsed_segments = later
            parsed_segments.sort(
                key=lambda pair: (pair[1] - pair[0], pair[1], pair[0]), reverse=True
            )
            return parsed_segments[0]
    parsed_simple = _parse_toc_page_number_simple(stripped)
    if parsed_simple is not None:
        return parsed_simple
    if TOC_PAGE_WITH_NUM.match(stripped):
        tail = _PAGE_PAGES_PREFIX.sub("", stripped)
        match = _DIGITS_1_4.match(tail)
        if match:
            try:
                value = int(match.group(0))
            except ValueError:
                return None
            return value, value
    return None


def _normalize_toc_text(text: str) -> str:
    if not text:
        return text
    cleaned = text.replace("\u00a0", " ")
    cleaned = cleaned.replace("\ufeff", "")
    cleaned = cleaned.replace("\u2013", "-")
    cleaned = cleaned.replace("\u2014", "-")
    cleaned = cleaned.replace("\u2212", "-")
    cleaned = cleaned.replace("\u00b7", ".")
    cleaned = cleaned.replace("\u2022", ".")
    cleaned = cleaned.replace("\u2027", ".")
    cleaned = cleaned.replace("\ufffd", "")
    cleaned = cleaned.replace("\u00c2", "")
    cleaned = cleaned.replace("\u00e2\u20ac\u201c", "-")
    cleaned = cleaned.replace("\u00e2\u20ac\u201d", "-")
    cleaned = cleaned.replace("\u00e2\u20ac\u2014", "-")
    cleaned = cleaned.replace("\u00e2\u20ac\u2013", "-")
    return collapse_whitespace(cleaned)


def _extract_item_code_inline(text: str) -> Optional[str]:
    match = TOC_ITEM_INLINE.search(text)
    if match:
        number = match.group(1)
        letter = match.group(2) or ""
        return f"{number}{letter.upper()}"
    match = TOC_ITEM_BARE.search(text)
    if match:
        return f"{match.group(1)}{match.group(2).upper()}"
    match = re.search(r"\b(\d{1,2})([A-Za-z])\b", text)
    if match:
        return f"{match.group(1)}{match.group(2).upper()}"
    match = re.search(r"\bitem\s*(\d{1,2})\b", text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def _normalize_item_code(text: str) -> Optional[str]:
    stripped = _normalize_toc_text(text).strip()
    if not stripped:
        return None
    if _is_item_code_only(stripped):
        cleaned = re.sub(r"[.\s]", "", stripped).upper()
        return cleaned
    return _extract_item_code_inline(stripped)


def _strip_item_prefix(text: str) -> str:
    stripped = text.strip()
    stripped = re.sub(
        r"^\s*item\s*\d{1,2}\s*[\.\-]?\s*[a-z]?\b",
        "",
        stripped,
        flags=re.IGNORECASE,
    )
    stripped = re.sub(
        r"^\s*\d{1,2}\s*[\.\-]?\s*[a-z]\b",
        "",
        stripped,
        flags=re.IGNORECASE,
    )
    stripped = re.sub(r"^\s*part\s+[ivxlcdm]+\b", "", stripped, flags=re.IGNORECASE)
    return stripped.strip(" .:-")


def _strip_dot_leaders(text: str) -> str:
    return re.sub(r"\.{2,}", " ", text)


def _strip_leading_page_ranges(text: str) -> str:
    return re.sub(
        r"^\s*\d{1,4}(?:\s*-\s*\d{1,4})?(?:\s*,\s*\d{1,4}(?:\s*-\s*\d{1,4})?)*\s+",
        "",
        text.strip(),
    )


def _extract_page_tail(text: str) -> tuple[Optional[tuple[int, int]], str]:
    cleaned = _strip_dot_leaders(text)
    tokens = cleaned.split()
    if not tokens:
        return None, cleaned
    for span in (3, 2, 1):
        if len(tokens) < span:
            continue
        tail = " ".join(tokens[-span:])
        tail = re.sub(r"[.,;:]+$", "", tail)
        parsed = _parse_toc_page_number(tail)
        if parsed is not None:
            head = " ".join(tokens[:-span])
            return parsed, head
    return None, cleaned


def _extract_page_head(text: str) -> tuple[Optional[tuple[int, int]], str]:
    cleaned = _strip_dot_leaders(text)
    tokens = cleaned.split()
    if not tokens:
        return None, cleaned
    for span in (3, 2, 1):
        if len(tokens) < span:
            continue
        head = " ".join(tokens[:span])
        head = re.sub(r"[.,;:]+$", "", head)
        parsed = _parse_toc_page_number(head)
        if parsed is not None:
            tail = " ".join(tokens[span:])
            return parsed, tail
    return None, cleaned


def _is_part_heading_line(text: str) -> bool:
    normalized = _normalize_toc_text(text).strip()
    if not normalized:
        return False
    return re.fullmatch(r"part\\s+[ivxlcdm]+", normalized, flags=re.IGNORECASE) is not None


def _is_toc_title_candidate(text: str, min_words: int = 1, max_words: int = 10) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if _is_part_heading_line(stripped) or _is_toc_heading(stripped):
        return False
    if len(stripped) > TOC_TITLE_MAX_CHARS:
        return False
    if _is_page_number_line(stripped) or _is_item_code_only(stripped):
        return False
    if TOC_DOT_LEADER.search(stripped):
        return False
    if _looks_like_clause(stripped):
        return False
    words = re.findall(r"[A-Za-z]{2,}", stripped)
    if len(words) < min_words or len(words) > max_words:
        return False
    return True


def _parse_toc_row_line(
    text: str,
) -> Optional[tuple[str, Optional[str], int, int]]:
    return _parse_toc_row_line_mode(text, prefer_head=False)


def _parse_toc_row_line_mode(
    text: str, prefer_head: bool
) -> Optional[tuple[str, Optional[str], int, int]]:
    normalized = _normalize_toc_text(text)
    if not normalized:
        return None
    if _is_toc_heading(normalized) or _is_cross_reference_index_heading(normalized):
        return None
    if _is_page_number_line(normalized) or _is_item_code_only(normalized):
        return None
    head_range, head_text = _extract_page_head(normalized)
    tail_range, tail_text = _extract_page_tail(normalized)
    page_range: Optional[tuple[int, int]] = None
    head = ""
    if prefer_head:
        if head_range is not None:
            page_range, head = head_range, head_text
        elif tail_range is not None:
            page_range, head = tail_range, tail_text
    else:
        if head_range is not None and _extract_item_code_inline(head_text) is not None:
            page_range, head = head_range, head_text
        elif tail_range is not None:
            page_range, head = tail_range, tail_text
        elif head_range is not None:
            page_range, head = head_range, head_text
    if page_range is None:
        return None
    head = _strip_leading_page_ranges(head)
    item_code = _extract_item_code_inline(head)
    title = _strip_item_prefix(head)
    if not title:
        return None
    if not _is_toc_title_candidate(title) and item_code is None:
        return None
    return title, item_code, page_range[0], page_range[1]


def _split_multi_item_toc_line(text: str) -> list[str]:
    matches = list(TOC_ITEM_INLINE.finditer(text))
    if len(matches) <= 1:
        return [text]
    segments: list[str] = []
    for idx, match in enumerate(matches):
        start = 0 if idx == 0 else match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        segment = text[start:end].strip()
        if segment:
            segments.append(segment)
    return segments


def parse_toc_page_number(text: str) -> Optional[tuple[int, int]]:
    return _parse_toc_page_number(text)


def parse_toc_row_line(
    text: str,
) -> Optional[tuple[str, Optional[str], int, int]]:
    return _parse_toc_row_line(text)


def _is_page_header_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if len(stripped) > HEADING_MAX_CHARS:
        return False
    return PAGE_HEADER.search(stripped) is not None


def _extract_page_header_number(text: str) -> Optional[int]:
    stripped = text.strip()
    if not _is_page_header_line(stripped):
        return None
    match = PAGE_HEADER_NUM.search(stripped)
    if not match:
        match = PAGE_HEADER_NUM_LEAD.match(stripped)
    if not match:
        part_match = re.search(
            r"([A-Za-z]{1,5})\s*-?\s*(\d{1,4})\s*$", stripped, re.IGNORECASE
        )
        if part_match:
            try:
                value = int(part_match.group(2))
            except ValueError:
                return None
            encoded = _parse_prefixed_page_value(part_match.group(1), value)
            if encoded is not None:
                return encoded
        return None
    try:
        value = int(match.group(1))
        if value >= 1900:
            return None
        return value
    except ValueError:
        return None


def _looks_like_header_footer_text(text: str) -> bool:
    if not text:
        return False
    return bool(HEADER_FOOTER_HINT.search(text) or YEAR_HINT.search(text))


def _extract_inline_page_number(text: str) -> Optional[int]:
    stripped = text.strip()
    if not stripped or len(stripped) > HEADING_MAX_CHARS:
        return None
    if TOC_ITEM_PREFIX.search(stripped) or TOC_DOT_LEADER.search(stripped):
        return None
    part_match = _INLINE_PART_PREFIX.match(stripped)
    if part_match:
        head = part_match.group(3).strip()
        if _looks_like_header_footer_text(head) and _is_heading_shaped_text(head):
            try:
                value = int(part_match.group(2))
            except ValueError:
                return None
            encoded = _parse_prefixed_page_value(part_match.group(1), value)
            if encoded is not None:
                return encoded
    part_match = _INLINE_PART_SUFFIX.match(stripped)
    if part_match:
        head = part_match.group(1).strip()
        if _looks_like_header_footer_text(head) and _is_heading_shaped_text(head):
            try:
                value = int(part_match.group(3))
            except ValueError:
                return None
            encoded = _parse_prefixed_page_value(part_match.group(2), value)
            if encoded is not None:
                return encoded
    match = _HEADER_YEAR_PAGE.match(stripped)
    if match:
        head = match.group(1).strip()
        if _looks_like_header_footer_text(head) and _is_heading_shaped_text(head):
            try:
                return int(match.group(3))
            except ValueError:
                return None
    match = _HEADER_PAGE_YEAR.match(stripped)
    if match:
        head = match.group(2).strip()
        if _looks_like_header_footer_text(head) and _is_heading_shaped_text(head):
            try:
                return int(match.group(1))
            except ValueError:
                return None
    match = _HEADER_PAGE_TEXT.match(stripped)
    if match:
        try:
            value = int(match.group(1))
        except ValueError:
            value = None
        tail = match.group(2).strip()
        if (
            value is not None
            and value < 1900
            and _looks_like_header_footer_text(tail)
            and _is_heading_shaped_text(tail)
        ):
            return value
    match = _HEADER_TEXT_PAGE.match(stripped)
    if match:
        try:
            value = int(match.group(2))
        except ValueError:
            value = None
        head = match.group(1).strip()
        if (
            value is not None
            and value < 1900
            and _looks_like_header_footer_text(head)
            and _is_heading_shaped_text(head)
        ):
            return value
    return None


def _is_numeric_page_line(text: str) -> Optional[int]:
    stripped = text.strip()
    if not stripped:
        return None
    match = _PAGE_NUM_SIMPLE.fullmatch(stripped)
    if match:
        stripped = match.group(1)
    if not stripped.isdigit():
        return None
    if len(stripped) > 4:
        return None
    try:
        return int(stripped)
    except ValueError:
        return None


def _page_context_is_narrative(block: Block) -> bool:
    if block.is_heading_like:
        return False
    return len(block.text) >= NARRATIVE_MIN_CHARS


def _extract_page_number_from_block(blocks: list[Block], idx: int) -> Optional[int]:
    text = blocks[idx].text.strip()
    if not text:
        return None
    header_page = _extract_page_header_number(text)
    if header_page is not None:
        return header_page
    inline_page = _extract_inline_page_number(text)
    if inline_page is not None:
        return inline_page
    match = PAGE_WORD_LINE.match(text)
    if match is not None:
        return int(match.group(1))
    match = PAGE_OF_LINE.match(text)
    if match is not None:
        return int(match.group(1))
    letter_match = _PAGE_PART_SINGLE.fullmatch(text)
    numeric_page: Optional[int]
    if letter_match is not None:
        prefix = letter_match.group(1).upper()
        try:
            value = int(letter_match.group(2))
        except ValueError:
            value = None
        if value is None or value >= 1900:
            numeric_page = None
        else:
            encoded = _parse_prefixed_page_value(prefix, value)
            if encoded is not None:
                numeric_page = encoded
            elif len(prefix) == 1:
                numeric_page = value
            else:
                numeric_page = None
    else:
        numeric_page = _is_numeric_page_line(text)
    if numeric_page is None:
        return None
    if numeric_page >= 1900 and not _is_part_page_value(numeric_page):
        return None
    window = blocks[max(0, idx - 2) : min(len(blocks), idx + 3)]
    toc_score = score_toc_window(window)
    if toc_score["tocLike"]:
        toc_signal = (
            toc_score["pageNumBlocks"]
            + toc_score["itemCodeBlocks"]
            + toc_score["itemPrefixBlocks"]
            + toc_score["dotLeaderBlocks"]
            + toc_score["altPairs"]
        )
        if toc_signal >= TOC_STRONG_SIGNAL_MIN:
            return None
    prev_block = blocks[idx - 1] if idx > 0 else None
    next_block = blocks[idx + 1] if idx + 1 < len(blocks) else None
    near_header = False
    if prev_block is not None and _is_page_header_line(prev_block.text):
        near_header = True
    if next_block is not None and _is_page_header_line(next_block.text):
        near_header = True
    if numeric_page >= 1900 and not _is_part_page_value(numeric_page) and not near_header:
        return None
    numeric_neighbor = False
    for offset in range(-2, 3):
        if offset == 0:
            continue
        neighbor_idx = idx + offset
        if neighbor_idx < 0 or neighbor_idx >= len(blocks):
            continue
        if _is_numeric_page_line(blocks[neighbor_idx].text.strip()) is not None:
            numeric_neighbor = True
            break
    if numeric_neighbor and not near_header:
        return None
    if near_header:
        return numeric_page
    if prev_block is not None and _page_context_is_narrative(prev_block):
        return numeric_page
    if next_block is not None and _page_context_is_narrative(next_block):
        return numeric_page
    if prev_block is not None and prev_block.is_heading_like:
        return numeric_page
    if next_block is not None and next_block.is_heading_like:
        return numeric_page
    return None


def _extract_toc_risk_page_end(blocks: list[Block]) -> Optional[int]:
    scan_end = min(len(blocks), TOC_PAGE_SCAN_BLOCKS)
    for idx in range(scan_end):
        text = blocks[idx].text
        if not _contains_risk_factors(text):
            continue
        if not blocks[idx].is_heading_like and len(text) > HEADING_MAX_CHARS:
            continue
        start_page = None
        end_page = None
        parsed_row = _parse_toc_row_line(text)
        if parsed_row is not None:
            start_page = parsed_row[2]
            end_page = parsed_row[3]
        look_idx: Optional[int] = None
        if start_page is None:
            for look in range(idx + 1, min(scan_end, idx + 6)):
                parsed = _parse_toc_page_number(blocks[look].text)
                if parsed is None:
                    continue
                start_page, end_page = parsed
                look_idx = look
                break
        if start_page is None:
            continue
        if end_page is not None and end_page > start_page:
            return end_page
        if look_idx is None:
            look_idx = idx
        next_page = None
        for look in range(look_idx + 1, scan_end):
            parsed = _parse_toc_page_number(blocks[look].text)
            if parsed is None:
                continue
            if parsed[0] <= start_page:
                continue
            next_page = parsed[0]
            break
        if next_page is not None and next_page > start_page:
            return next_page - 1
    return None


def _parse_toc_region_entries(blocks: list[Block], region: TocRegion) -> list[TocEntry]:
    entries: list[TocEntry] = []
    start = max(0, region["start_idx"])
    end = min(len(blocks), region["end_idx"] + TOC_REGION_PAD_BLOCKS)
    is_xref = region["kind"] == "xref_index"
    page_first_hits = 0
    page_last_hits = 0
    head_line_hits = 0
    tail_line_hits = 0
    scan_limit = min(end - 2, len(blocks) - 2)
    for scan_idx in range(start, scan_limit):
        parsed_head = _parse_toc_row_line_mode(blocks[scan_idx].text, prefer_head=True)
        parsed_tail = _parse_toc_row_line_mode(blocks[scan_idx].text, prefer_head=False)
        if parsed_head is not None and parsed_tail is None:
            head_line_hits += 1
        elif parsed_tail is not None and parsed_head is None:
            tail_line_hits += 1

        page_range_head = _parse_toc_page_number(blocks[scan_idx].text)
        if page_range_head is not None:
            item_code = _normalize_item_code(blocks[scan_idx + 1].text)
            title = _normalize_toc_text(blocks[scan_idx + 2].text)
            if item_code is not None and title and _is_toc_title_candidate(title):
                page_first_hits += 1

        item_code = _normalize_item_code(blocks[scan_idx].text)
        title = _normalize_toc_text(blocks[scan_idx + 1].text)
        page_range_tail = _parse_toc_page_number(blocks[scan_idx + 2].text)
        if (
            item_code is not None
            and title
            and _is_toc_title_candidate(title)
            and page_range_tail is not None
        ):
            page_last_hits += 1
    page_first_table = False
    if page_first_hits >= TOC_PAGE_FIRST_MIN_HITS or page_last_hits >= TOC_PAGE_FIRST_MIN_HITS:
        if page_first_hits > page_last_hits:
            page_first_table = True
        elif page_last_hits > page_first_hits:
            page_first_table = False
        else:
            page_first_table = head_line_hits >= TOC_PAGE_FIRST_MIN_HITS and head_line_hits > tail_line_hits
    else:
        page_first_table = head_line_hits >= TOC_PAGE_FIRST_MIN_HITS and head_line_hits > tail_line_hits
    idx = start
    while idx < end:
        if is_xref and idx + 2 < end:
            item_code = _normalize_item_code(blocks[idx].text)
            title_raw = blocks[idx + 1].text
            title = _normalize_toc_text(title_raw)
            page_range_text = blocks[idx + 2].text
            page_range = _parse_toc_page_number(page_range_text)
            if (
                item_code is not None
                and page_range is not None
                and title
                and _is_toc_title_candidate(title)
            ):
                entries.append(
                    {
                        "title": title,
                        "item_code": item_code,
                        "page_start": page_range[0],
                        "page_end": page_range[1],
                        "raw": collapse_whitespace(
                            f"{blocks[idx].text} {blocks[idx + 1].text} {blocks[idx + 2].text}"
                        ),
                        "idx": idx,
                    }
                )
                idx += 3
                continue
        multi_parts = _split_multi_item_toc_line(blocks[idx].text)
        if len(multi_parts) > 1:
            for part in multi_parts:
                parsed = _parse_toc_row_line_mode(part, prefer_head=page_first_table)
                if parsed is None:
                    continue
                title, item_code, page_start, page_end = parsed
                entries.append(
                    {
                        "title": title,
                        "item_code": item_code,
                        "page_start": page_start,
                        "page_end": page_end,
                        "raw": part,
                        "idx": idx,
                    }
                )
            idx += 1
            continue
        if idx + 2 < end:
            page_range = _parse_toc_page_number(blocks[idx].text)
            if page_range is not None:
                if not page_first_table and idx - 1 >= start:
                    prev_text = _normalize_toc_text(blocks[idx - 1].text).strip()
                    prev_item_code = _normalize_item_code(prev_text) or _extract_item_code_inline(
                        prev_text
                    )
                    if (
                        prev_text
                        and prev_item_code is None
                        and not _is_page_number_line(prev_text)
                        and not _is_toc_heading(prev_text)
                        and not _is_part_heading_line(prev_text)
                    ):
                        prev_prev_item_code = None
                        if idx - 2 >= start:
                            prev_prev_text = _normalize_toc_text(blocks[idx - 2].text).strip()
                            prev_prev_item_code = _normalize_item_code(prev_prev_text)
                        if prev_prev_item_code is None:
                            idx += 1
                            continue
                item_code = _normalize_item_code(blocks[idx + 1].text)
                title_raw = blocks[idx + 2].text
                title = _normalize_toc_text(title_raw)
                if item_code is not None and title and _is_toc_title_candidate(title):
                    trailing_range: Optional[tuple[int, int]] = None
                    use_trailing = False
                    if idx + 3 < end:
                        trailing_text = _normalize_toc_text(blocks[idx + 3].text)
                        trailing_range = _parse_toc_page_number(blocks[idx + 3].text)
                        if trailing_range is not None:
                            next_item_code = None
                            if idx + 4 < end:
                                next_item_code = _normalize_item_code(blocks[idx + 4].text)
                            is_risk_row = _contains_risk_factors(title) or item_code in {"1A", "3D"}
                            if (
                                is_risk_row
                                and page_range[0] == page_range[1]
                                and trailing_range[1] > trailing_range[0]
                            ):
                                page_range = trailing_range
                                use_trailing = True
                            elif is_xref and ("," in trailing_text or trailing_range[1] > page_range[1]):
                                page_range = trailing_range
                                use_trailing = True
                            elif next_item_code is None:
                                page_range = trailing_range
                                use_trailing = True
                    raw_parts = [blocks[idx].text, blocks[idx + 1].text, blocks[idx + 2].text]
                    if trailing_range is not None and use_trailing:
                        raw_parts.append(blocks[idx + 3].text)
                    raw = collapse_whitespace(" ".join(raw_parts))
                    entries.append(
                        {
                            "title": title,
                            "item_code": item_code,
                            "page_start": page_range[0],
                            "page_end": page_range[1],
                            "raw": raw,
                            "idx": idx,
                        }
                    )
                    idx += 4 if (trailing_range is not None and use_trailing) else 3
                    continue
                if item_code is None:
                    title_raw = blocks[idx + 1].text
                    title = _normalize_toc_text(title_raw)
                    if title and _is_toc_title_candidate(title):
                        item_code = _extract_item_code_inline(title)
                        stripped = _strip_item_prefix(title)
                        if stripped:
                            title = stripped
                        raw = collapse_whitespace(f"{blocks[idx].text} {blocks[idx + 1].text}")
                        entries.append(
                            {
                                "title": title,
                                "item_code": item_code,
                                "page_start": page_range[0],
                                "page_end": page_range[1],
                                "raw": raw,
                                "idx": idx,
                            }
                        )
                        idx += 2
                        continue
        if idx + 2 < end:
            page_range = _parse_toc_page_number(blocks[idx].text)
            item_code = _normalize_item_code(blocks[idx + 1].text)
            title_raw = blocks[idx + 2].text
            title = _normalize_toc_text(title_raw)
            if page_range is not None and item_code is not None and title and _is_toc_title_candidate(title):
                entries.append(
                    {
                        "title": title,
                        "item_code": item_code,
                        "page_start": page_range[0],
                        "page_end": page_range[1],
                        "raw": collapse_whitespace(
                            f"{blocks[idx].text} {blocks[idx + 1].text} {blocks[idx + 2].text}"
                        ),
                        "idx": idx,
                    }
                )
                idx += 3
                continue
            if (
                page_range is None
                and item_code is not None
                and title
                and _is_toc_title_candidate(title)
            ):
                lookahead_range: Optional[tuple[int, int]] = None
                lookahead_idx: Optional[int] = None
                for offset in range(3, 6):
                    candidate_idx = idx + offset
                    if candidate_idx >= end:
                        break
                    candidate_text = blocks[candidate_idx].text
                    if _normalize_item_code(candidate_text) is not None:
                        break
                    parsed = _parse_toc_page_number(candidate_text)
                    if parsed is not None:
                        lookahead_range = parsed
                        lookahead_idx = candidate_idx
                        break
                if lookahead_range is not None and lookahead_idx is not None:
                    entries.append(
                        {
                            "title": title,
                            "item_code": item_code,
                            "page_start": lookahead_range[0],
                            "page_end": lookahead_range[1],
                            "raw": collapse_whitespace(
                                f"{blocks[idx].text} {blocks[idx + 1].text} {blocks[idx + 2].text} {blocks[lookahead_idx].text}"
                            ),
                            "idx": idx,
                        }
                    )
                    idx = lookahead_idx + 1
                    continue
            item_code = _normalize_item_code(blocks[idx].text)
            title_raw = blocks[idx + 1].text
            page_range_text = blocks[idx + 2].text
            page_range = _parse_toc_page_number(page_range_text)
            title = _normalize_toc_text(title_raw)
            if (
                item_code is not None
                and page_range is not None
                and title
                and _is_toc_title_candidate(title)
                and _is_page_range_text_line(page_range_text)
            ):
                entries.append(
                    {
                        "title": title,
                        "item_code": item_code,
                        "page_start": page_range[0],
                        "page_end": page_range[1],
                        "raw": collapse_whitespace(
                            f"{blocks[idx].text} {blocks[idx + 1].text} {blocks[idx + 2].text}"
                        ),
                        "idx": idx,
                    }
                )
                idx += 3
                continue
        if idx + 2 < end and not page_first_table and _looks_like_toc_triplet(blocks, idx):
            title_raw = blocks[idx].text
            item_code = _normalize_item_code(blocks[idx + 1].text)
            page_range = _parse_toc_page_number(blocks[idx + 2].text)
            if item_code is not None and page_range is not None:
                title = _strip_item_prefix(_normalize_toc_text(title_raw))
                if not title:
                    title = _normalize_toc_text(title_raw)
                raw = collapse_whitespace(
                    f"{blocks[idx].text} {blocks[idx + 1].text} {blocks[idx + 2].text}"
                )
                entries.append(
                    {
                        "title": title,
                        "item_code": item_code,
                        "page_start": page_range[0],
                        "page_end": page_range[1],
                        "raw": raw,
                        "idx": idx,
                    }
                )
                idx += 3
                continue
        if idx + 1 < end:
            page_range = _parse_toc_page_number(blocks[idx + 1].text)
            if page_range is not None:
                title_raw = blocks[idx].text
                title = _normalize_toc_text(title_raw)
                title = _strip_leading_page_ranges(title)
                if title and _is_toc_title_candidate(title) and not page_first_table:
                    item_code = _extract_item_code_inline(title)
                    stripped = _strip_item_prefix(title)
                    if stripped:
                        title = stripped
                    raw = collapse_whitespace(f"{blocks[idx].text} {blocks[idx + 1].text}")
                    entries.append(
                        {
                            "title": title,
                            "item_code": item_code,
                            "page_start": page_range[0],
                            "page_end": page_range[1],
                            "raw": raw,
                            "idx": idx,
                        }
                    )
                    idx += 2
                    continue
        parsed = _parse_toc_row_line_mode(blocks[idx].text, prefer_head=page_first_table)
        if parsed is not None:
            title, item_code, page_start, page_end = parsed
            entries.append(
                {
                    "title": title,
                    "item_code": item_code,
                    "page_start": page_start,
                    "page_end": page_end,
                    "raw": blocks[idx].text,
                    "idx": idx,
                }
            )
        idx += 1
    return entries


def _is_item_label_only(title: str) -> bool:
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", title).strip().lower()
    if not cleaned:
        return True
    if cleaned == "item":
        return True
    if cleaned.startswith("item "):
        suffix = cleaned.replace("item ", "").strip()
        if re.fullmatch(r"\d+[a-z]?", suffix):
            return True
    if re.fullmatch(r"[ivxlcdm]{1,4}", cleaned):
        return True
    if cleaned.startswith("part "):
        suffix = cleaned.replace("part ", "").strip()
        if re.fullmatch(r"[ivxlcdm]{1,4}", suffix):
            return True
    return False


def _build_toc_map_from_entries(
    entries: list[TocEntry], region_kind: str
) -> Optional[TocMap]:
    if not entries:
        return None
    risk_candidates: list[tuple[int, TocEntry, int]] = []
    for idx, entry in enumerate(entries):
        if not (_contains_risk_factors(entry["title"]) or _contains_risk_factors(entry["raw"])):
            continue
        score = 0
        item_code = entry.get("item_code")
        if isinstance(item_code, str):
            if item_code.upper() == "1A":
                score += 2
            elif item_code.upper() == "3D":
                score += 2
        title_lower = entry["title"].lower()
        if title_lower.strip() == "risk factors":
            score += 1
        if "summary" in title_lower:
            score -= 1
        risk_candidates.append((idx, entry, score))
    risk_idx: Optional[int] = None
    if risk_candidates:
        risk_candidates.sort(key=lambda item: (-item[2], item[0]))
        risk_idx = risk_candidates[0][0]
    if risk_idx is None:
        return None

    risk_entry = entries[risk_idx]
    risk_item_code = risk_entry.get("item_code") or _extract_item_code_inline(
        risk_entry["raw"]
    )
    risk_page_start = risk_entry["page_start"]
    risk_page_end = risk_entry["page_end"]

    if risk_page_end is None and risk_page_start is not None:
        for entry in entries[risk_idx + 1 :]:
            next_page = entry.get("page_start")
            if isinstance(next_page, int) and next_page > risk_page_start:
                risk_page_end = next_page - 1
                break

    next_entry: Optional[TocEntry] = None
    for entry in entries[risk_idx + 1 :]:
        title = entry["title"]
        item_code = entry.get("item_code")
        if _is_item_label_only(title):
            continue
        if risk_item_code is not None and item_code == risk_item_code:
            continue
        if item_code is not None:
            next_entry = entry
            break
        title_lower = title.lower()
        if "risk" in title_lower:
            continue
        words = re.findall(r"[A-Za-z]{2,}", title)
        if len(words) < 1 or len(words) > 6:
            continue
        if not _is_heading_shaped_text(title):
            continue
        next_entry = entry
        break

    toc_map: TocMap = {"risk_row_text": risk_entry["raw"], "region_kind": region_kind}
    if risk_page_start is not None:
        toc_map["risk_page_start"] = risk_page_start
    if risk_page_end is not None:
        toc_map["risk_page_end"] = risk_page_end
    if next_entry is not None:
        toc_map["next_label"] = next_entry["title"]
        next_item_code = next_entry["item_code"]
        if next_item_code:
            toc_map["next_item_code"] = next_item_code
        next_page_start = next_entry.get("page_start")
        if isinstance(next_page_start, int):
            toc_map["next_page_start"] = next_page_start
        toc_map["next_row_text"] = next_entry["raw"]
    return toc_map


def _toc_map_has_range(toc_map: TocMap) -> bool:
    risk_start = toc_map.get("risk_page_start")
    risk_end = toc_map.get("risk_page_end")
    if not isinstance(risk_start, int) or not isinstance(risk_end, int):
        return False
    return risk_end >= risk_start


def _toc_map_score(toc_map: TocMap) -> int:
    score = 0
    row_text = toc_map.get("risk_row_text")
    if isinstance(row_text, str):
        if ITEM_1A_BLOCK.search(row_text):
            score += 5
        if ITEM_3_BLOCK.search(row_text):
            score += 5
        if _contains_risk_factors(row_text):
            score += 1
    risk_start = toc_map.get("risk_page_start")
    risk_end = toc_map.get("risk_page_end")
    if isinstance(risk_start, int) and isinstance(risk_end, int):
        if risk_end > risk_start:
            span = min(risk_end - risk_start, 15)
            score += 3 + span
        else:
            score += 1
    kind = toc_map.get("region_kind")
    if kind == "toc_head":
        score += 1
    elif kind == "xref_index":
        score += 1
    return score


def _toc_map_has_item_code(toc_map: TocMap) -> bool:
    row_text = toc_map.get("risk_row_text")
    if not isinstance(row_text, str):
        return False
    return bool(ITEM_1A_BLOCK.search(row_text) or ITEM_3_BLOCK.search(row_text))


def _toc_map_has_next_label(toc_map: TocMap) -> bool:
    label = toc_map.get("next_label")
    if not isinstance(label, str):
        return False
    if _is_item_label_only(label):
        return False
    return bool(label.strip())


def extract_toc_entries(block_doc: BlockDoc, regions: list[TocRegion]) -> Optional[TocMap]:
    if not regions:
        return None
    strong_regions: list[TocRegion] = []
    non_xref: list[TocRegion] = []
    for region in regions:
        if region["kind"] != "xref_index":
            non_xref.append(region)
            if _toc_window_is_strong(region["score"]):
                strong_regions.append(region)
    strong_regions.sort(key=lambda region: region["start_idx"])
    non_xref.sort(key=lambda region: region["start_idx"])
    regions_to_try: list[TocRegion] = []
    seen: set[tuple[int, int, str]] = set()
    for region in strong_regions + non_xref:
        start_idx = region["start_idx"]
        end_idx = region["end_idx"]
        kind = region["kind"]
        key = (start_idx, end_idx, kind)
        if key in seen:
            continue
        seen.add(key)
        regions_to_try.append(region)
    xref_regions: list[TocRegion] = []
    for region in regions:
        if region["kind"] == "xref_index":
            xref_regions.append(region)
    xref_regions.sort(key=lambda region: region["start_idx"])
    regions_to_try.extend(xref_regions)

    toc_maps: list[TocMap] = []
    for region in regions_to_try:
        entries = _parse_toc_region_entries(block_doc.blocks, region)
        toc_map = _build_toc_map_from_entries(entries, region["kind"])
        if toc_map is not None:
            toc_maps.append(toc_map)

    if not toc_maps:
        return None

    item_code_maps = [toc_map for toc_map in toc_maps if _toc_map_has_item_code(toc_map)]
    maps_to_score = item_code_maps or toc_maps
    range_map_candidates = [toc_map for toc_map in maps_to_score if _toc_map_has_range(toc_map)]
    range_map: Optional[TocMap] = None
    if range_map_candidates:
        range_map = max(range_map_candidates, key=_toc_map_score)

    next_map: Optional[TocMap] = None
    non_xref_next = [
        toc_map
        for toc_map in toc_maps
        if toc_map.get("region_kind") != "xref_index" and _toc_map_has_next_label(toc_map)
    ]
    if non_xref_next:
        next_map = max(non_xref_next, key=_toc_map_score)
    if next_map is None:
        any_next = [toc_map for toc_map in toc_maps if _toc_map_has_next_label(toc_map)]
        if any_next:
            next_map = max(any_next, key=_toc_map_score)

    combined: TocMap = {}
    base_map = range_map or next_map or max(maps_to_score, key=_toc_map_score)
    combined.update(base_map)
    if next_map is not None and next_map is not base_map:
        if _toc_map_has_next_label(next_map):
            combined["next_label"] = next_map.get("next_label", "")
            next_item_code = next_map.get("next_item_code")
            if isinstance(next_item_code, str) and next_item_code:
                combined["next_item_code"] = next_item_code
            else:
                combined.pop("next_item_code", None)
            next_page_start = next_map.get("next_page_start")
            if isinstance(next_page_start, int):
                combined["next_page_start"] = next_page_start
            next_row_text = next_map.get("next_row_text")
            if isinstance(next_row_text, str) and next_row_text:
                combined["next_row_text"] = next_row_text
    if "risk_page_start" not in combined and next_map is not None:
        next_risk_start = next_map.get("risk_page_start")
        if isinstance(next_risk_start, int):
            combined["risk_page_start"] = next_risk_start
    if "risk_page_end" not in combined and next_map is not None:
        next_risk_end = next_map.get("risk_page_end")
        if isinstance(next_risk_end, int):
            combined["risk_page_end"] = next_risk_end
    return combined


def _find_end_by_page_header(
    blocks: list[Block], start_idx: int, end_page: int
) -> Optional[int]:
    stop_page = end_page + 1
    for idx in range(start_idx + 1, len(blocks)):
        page_num = _extract_page_number_from_block(blocks, idx)
        if page_num is None:
            continue
        if page_num >= stop_page:
            return idx - 1 if idx > start_idx else idx
    return None


def _candidate_page_hint(
    blocks: list[Block],
    idx: int,
    exclude_ranges: Optional[list[tuple[int, int]]] = None,
    page_anchor: Optional[int] = None,
) -> Optional[int]:
    def within_anchor(value: int) -> bool:
        if page_anchor is None:
            return True
        return abs(value - page_anchor) <= PAGE_MARKER_ANCHOR_MAX_DELTA

    page_num = _page_number_for_index(blocks, idx, exclude_ranges, page_anchor)
    if page_num is not None and within_anchor(page_num):
        return page_num
    max_radius = 30
    for offset in range(max_radius + 1):
        if offset == 0:
            candidate_idx = idx
            if 0 <= candidate_idx < len(blocks):
                page_num = _extract_page_number_from_block(blocks, candidate_idx)
                if page_num is not None and within_anchor(page_num):
                    return page_num
            continue
        back_idx = idx - offset
        if back_idx >= 0:
            page_num = _extract_page_number_from_block(blocks, back_idx)
            if page_num is not None and within_anchor(page_num):
                return page_num
        forward_idx = idx + offset
        if forward_idx < len(blocks):
            page_num = _extract_page_number_from_block(blocks, forward_idx)
            if page_num is not None and within_anchor(page_num):
                return page_num
    return None


def _end_marker_toc_like(blocks: list[Block], idx: int) -> bool:
    window = blocks[idx : idx + END_MARKER_TOC_WINDOW_BLOCKS]
    score = score_toc_window(window)
    if score["tocLike"]:
        return True
    if score["pageNumBlocks"] >= TOC_MIN_PAGE_NUM_BLOCKS and score["altPairs"] >= max(
        1, TOC_MIN_ALT_PAIRS - 1
    ):
        if (
            score["dotLeaderBlocks"] > 0
            or score["itemPrefixBlocks"] > 0
            or score["itemCodeBlocks"] > 0
        ):
            return True
    return False


def _adjacent_page_range_line(blocks: list[Block], idx: int) -> bool:
    for offset in range(-2, 3):
        if offset == 0:
            continue
        neighbor_idx = idx + offset
        if neighbor_idx < 0 or neighbor_idx >= len(blocks):
            continue
        text = blocks[neighbor_idx].text.strip()
        if not text:
            continue
        if (
            TOC_PAGE_RANGE.match(text)
            or TOC_PAGE_RANGE_WITH_LETTER.match(text)
            or TOC_PAGE_WITH_NUM.match(text)
            or TOC_PAGE_WITH_PART.match(text)
            or TOC_PAGE_WITH_LETTER.match(text)
        ):
            return True
    return False


def _allow_end_marker_in_unsafe(block_doc: BlockDoc, idx: int) -> bool:
    region = _unsafe_region_for_idx(block_doc, idx)
    if region is None:
        return True
    kind = region.get("kind")
    if kind in {"xref_index", "toc_head"}:
        return False
    if kind != "toc_late":
        return False
    text = block_doc.blocks[idx].text
    normalized = _normalize_heading_candidate(text)
    if _is_toc_line(normalized) or _is_page_number_line(normalized):
        return False
    if _parse_toc_page_number(text) is not None:
        return False
    if _parse_toc_row_line(text) is not None:
        return False
    if _adjacent_page_range_line(block_doc.blocks, idx):
        return False
    return True


def _section_page_range(blocks: list[Block]) -> Optional[tuple[int, int]]:
    pages: list[tuple[int, int]] = []
    for idx in range(len(blocks)):
        page_num = _extract_page_number_from_block(blocks, idx)
        if page_num is None:
            continue
        pages.append((idx, page_num))
    if not pages:
        return None
    pages.sort(key=lambda pair: pair[0])
    return pages[0][1], pages[-1][1]


def _nearest_page_marker(
    blocks: list[Block], start_idx: int, direction: int, max_blocks: int
) -> tuple[Optional[int], Optional[int]]:
    for offset in range(1, max_blocks + 1):
        idx = start_idx + (offset * direction)
        if idx < 0 or idx >= len(blocks):
            break
        page_num = _extract_page_number_from_block(blocks, idx)
        if page_num is not None:
            return page_num, offset
    return None, None


def _near_heading_context(blocks: list[Block], idx: int, direction: int, span: int = 3) -> bool:
    for offset in range(1, span + 1):
        neighbor_idx = idx + (offset * direction)
        if neighbor_idx < 0 or neighbor_idx >= len(blocks):
            break
        text = blocks[neighbor_idx].text.strip()
        if not text:
            continue
        if blocks[neighbor_idx].is_heading_like or _is_heading_shaped_text(text):
            return True
    return False


def _near_narrative_context(blocks: list[Block], idx: int, direction: int, span: int = 3) -> bool:
    for offset in range(1, span + 1):
        neighbor_idx = idx + (offset * direction)
        if neighbor_idx < 0 or neighbor_idx >= len(blocks):
            break
        if _page_context_is_narrative(blocks[neighbor_idx]):
            return True
    return False


def _page_marker_kind(blocks: list[Block], idx: int) -> str:
    text = blocks[idx].text.strip()
    if not text:
        return "unknown"
    inline_marker = bool(
        re.match(r"^\d{1,4}\s+\D+", text) or re.match(r"^\D.+\s+\d{1,4}$", text)
    )
    numeric_only = _is_numeric_page_line(text) is not None
    prev_block = blocks[idx - 1] if idx > 0 else None
    next_block = blocks[idx + 1] if idx + 1 < len(blocks) else None
    prev_heading = prev_block is not None and (
        prev_block.is_heading_like or _is_heading_shaped_text(prev_block.text)
    )
    next_heading = next_block is not None and (
        next_block.is_heading_like or _is_heading_shaped_text(next_block.text)
    )
    prev_narrative = _near_narrative_context(blocks, idx, -1, span=2)
    next_narrative = _near_narrative_context(blocks, idx, 1, span=2)
    header_footer_hint = _looks_like_header_footer_text(text)
    next_strong_heading = False
    for look in range(1, 4):
        next_idx = idx + look
        if next_idx >= len(blocks):
            break
        candidate = blocks[next_idx].text.strip()
        if not candidate:
            continue
        if _is_strong_item_heading(candidate) or RISK_FACTORS_HEADING.search(candidate):
            next_strong_heading = True
        break
    if prev_heading and next_narrative and not prev_narrative:
        return "header"
    if prev_narrative and next_heading and not next_narrative:
        return "footer"
    if inline_marker and header_footer_hint and prev_narrative and next_narrative:
        return "header"
    if prev_narrative and next_narrative:
        if numeric_only:
            before_heading = _near_heading_context(blocks, idx, -1)
            after_heading = _near_heading_context(blocks, idx, 1)
            if after_heading and not before_heading:
                if prev_narrative and next_strong_heading:
                    return "footer"
                return "header"
            if before_heading and not after_heading:
                return "footer"
            return "unknown"
        return "footer"
    before_heading = _near_heading_context(blocks, idx, -1)
    after_heading = _near_heading_context(blocks, idx, 1)
    if PAGE_HEADER.search(text) or inline_marker:
        if after_heading and not before_heading:
            return "header"
        if before_heading and not after_heading:
            return "footer"
        return "unknown"
    if PAGE_WORD_LINE.match(text) or PAGE_OF_LINE.match(text) or TOC_PAGE_NUM.match(text):
        if after_heading and not before_heading:
            return "header"
        if before_heading and not after_heading:
            return "footer"
        return "unknown"
    return "unknown"


def _idx_in_ranges(idx: int, ranges: list[tuple[int, int]]) -> bool:
    for start, end in ranges:
        if start <= idx < end:
            return True
    return False


def _build_toc_exclude_ranges(
    toc_regions: list[TocRegion], idx_item1_business: Optional[int]
) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for region in toc_regions:
        start_idx = region["start_idx"]
        end_idx = region["end_idx"]
        if (
            region.get("kind") == "toc_head"
            and idx_item1_business is not None
            and idx_item1_business > start_idx
        ):
            end_idx = min(end_idx, idx_item1_business)
        if end_idx <= start_idx:
            continue
        ranges.append((start_idx, end_idx))
    return ranges


# Cache for _collect_page_markers_full to avoid recomputing for the same blocks list
_page_markers_cache: dict[int, list[tuple[int, int, str]]] = {}


def _collect_page_markers_full(blocks: list[Block]) -> list[tuple[int, int, str]]:
    """Collect ALL page markers from blocks (without filtering by exclude_ranges).

    Results are cached by blocks list identity to avoid recomputation.
    """
    cache_key = id(blocks)
    if cache_key in _page_markers_cache:
        return _page_markers_cache[cache_key]

    markers: list[tuple[int, int, str]] = []
    for idx in range(len(blocks)):
        page_num = _extract_page_number_from_block(blocks, idx)
        if page_num is None:
            continue
        kind = _page_marker_kind(blocks, idx)
        markers.append((idx, page_num, kind))

    _page_markers_cache[cache_key] = markers
    # Keep cache bounded to avoid memory issues
    if len(_page_markers_cache) > 10:
        # Remove oldest entry
        oldest_key = next(iter(_page_markers_cache))
        del _page_markers_cache[oldest_key]

    return markers


def _collect_page_markers(
    blocks: list[Block], exclude_ranges: Optional[list[tuple[int, int]]] = None
) -> list[tuple[int, int, str]]:
    # Get all markers (cached)
    all_markers = _collect_page_markers_full(blocks)

    # Filter by exclude_ranges if specified
    if exclude_ranges is not None:
        markers = [m for m in all_markers if not _idx_in_ranges(m[0], exclude_ranges)]
    else:
        markers = all_markers

    if len(markers) < 3:
        return markers
    filtered: list[tuple[int, int, str]] = []
    for i, marker in enumerate(markers):
        if marker[2] in {"header", "footer"}:
            filtered.append(marker)
            continue
        prev_marker = markers[i - 1] if i > 0 else None
        next_marker = markers[i + 1] if i + 1 < len(markers) else None
        keep = False
        for neighbor in (prev_marker, next_marker):
            if neighbor is None:
                continue
            if abs(neighbor[0] - marker[0]) > PAGE_MARKER_SEQUENCE_MAX_BLOCKS:
                continue
            if abs(neighbor[1] - marker[1]) <= PAGE_MARKER_SEQUENCE_MAX_DIFF:
                keep = True
                break
        if keep:
            filtered.append(marker)
    return filtered


def _collect_page_marker_sequences(
    markers: list[tuple[int, int, str]]
) -> list[list[tuple[int, int, str]]]:
    if not markers:
        return []
    sequences: list[list[tuple[int, int, str]]] = []
    current: list[tuple[int, int, str]] = [markers[0]]
    for marker in markers[1:]:
        prev = current[-1]
        page_jump = marker[1] - prev[1]
        idx_jump = marker[0] - prev[0]
        if (
            page_jump < 0
            or page_jump > PAGE_MARKER_SEQUENCE_MAX_DIFF
            or idx_jump > PAGE_MARKER_SEQUENCE_MAX_BLOCKS
        ):
            sequences.append(current)
            current = [marker]
        else:
            current.append(marker)
    if current:
        sequences.append(current)
    return sequences


def _page_sequence_score(seq: list[tuple[int, int, str]]) -> tuple[int, int]:
    if len(seq) < 2:
        return 0, len(seq)
    good_jumps = 0
    for idx in range(1, len(seq)):
        if seq[idx][1] - seq[idx - 1][1] == 1:
            good_jumps += 1
    return good_jumps, len(seq)


def _page_number_for_index(
    blocks: list[Block],
    idx: int,
    exclude_ranges: Optional[list[tuple[int, int]]] = None,
    page_anchor: Optional[int] = None,
) -> Optional[int]:
    markers = _collect_page_markers(blocks, exclude_ranges)
    if not markers:
        return None
    sequences = _collect_page_marker_sequences(markers)
    if not sequences:
        return None
    chosen: list[tuple[int, int, str]] = sequences[0]
    best_key: Optional[tuple[int, int, int, int]] = None
    for seq in sequences:
        start_idx = seq[0][0]
        end_idx = seq[-1][0]
        if start_idx <= idx <= end_idx:
            dist = 0
        else:
            dist = min(abs(idx - start_idx), abs(idx - end_idx))
        good_jumps, length = _page_sequence_score(seq)
        anchor_dist = 0
        if page_anchor is not None:
            anchor_dist = min(abs(marker[1] - page_anchor) for marker in seq)
        key = (anchor_dist, dist, -good_jumps, -length)
        if best_key is None or key < best_key:
            best_key = key
            chosen = seq
    prev_marker: Optional[tuple[int, int, str]] = None
    next_marker: Optional[tuple[int, int, str]] = None
    for marker in chosen:
        if marker[0] <= idx:
            prev_marker = marker
        elif marker[0] > idx:
            next_marker = marker
            break
    if prev_marker is not None and prev_marker[0] == idx:
        return prev_marker[1]
    if prev_marker is not None and next_marker is not None:
        page_gap = next_marker[1] - prev_marker[1]
        idx_gap = next_marker[0] - prev_marker[0]
        if page_gap > 1 and idx_gap > 0:
            if prev_marker[2] == "footer" and (idx - prev_marker[0]) <= PAGE_MARKER_NEAR_BLOCKS:
                return prev_marker[1] + 1
            if next_marker[2] == "header" and (next_marker[0] - idx) <= PAGE_MARKER_NEAR_BLOCKS:
                return next_marker[1] - 1
            rel = (idx - prev_marker[0]) / idx_gap
            est = int(round(prev_marker[1] + (rel * page_gap)))
            if est < prev_marker[1]:
                est = prev_marker[1]
            if est > next_marker[1]:
                est = next_marker[1]
            return est
    if prev_marker is not None and prev_marker[2] == "header":
        return prev_marker[1]
    if next_marker is not None and next_marker[2] == "footer":
        return next_marker[1]
    if prev_marker is not None and next_marker is not None:
        prev_dist = idx - prev_marker[0]
        next_dist = next_marker[0] - idx
        return prev_marker[1] if prev_dist <= next_dist else next_marker[1]
    if prev_marker is not None:
        return prev_marker[1]
    if next_marker is not None:
        return next_marker[1]
    return None


def _boundary_page_guess(blocks: list[Block], idx: int) -> Optional[int]:
    prev_page, prev_dist = _nearest_page_marker(blocks, idx, -1, PAGE_MARKER_MAX_BLOCKS)
    next_page, next_dist = _nearest_page_marker(blocks, idx, 1, PAGE_MARKER_MAX_BLOCKS)
    if prev_page is None and next_page is None:
        return None
    if prev_page is None:
        return next_page
    if next_page is None:
        return prev_page
    if prev_dist is not None and next_dist is not None and prev_dist <= next_dist:
        return prev_page
    return next_page


def _section_page_range_with_context(
    blocks: list[Block],
    start_idx: int,
    end_idx: int,
    exclude_ranges: Optional[list[tuple[int, int]]] = None,
) -> Optional[tuple[int, int]]:
    start_idx = max(0, min(start_idx, len(blocks) - 1))
    end_idx = max(0, min(end_idx, len(blocks) - 1))
    if end_idx < start_idx:
        start_idx, end_idx = end_idx, start_idx
    pages_in_slice: list[tuple[int, int]] = []
    for idx in range(start_idx, end_idx + 1):
        page_num = _extract_page_number_from_block(blocks, idx)
        if page_num is not None:
            pages_in_slice.append((idx, page_num))
    if pages_in_slice:
        pages_in_slice.sort(key=lambda pair: pair[0])
    start_page = None
    end_page = None
    start_page = _page_number_for_index(blocks, start_idx, exclude_ranges)
    end_page = _page_number_for_index(blocks, end_idx, exclude_ranges)
    if pages_in_slice:
        first_idx, first_page = pages_in_slice[0]
        last_idx, last_page = pages_in_slice[-1]
        if start_page is None and (first_idx - start_idx) <= PAGE_MARKER_MAX_BLOCKS:
            start_page = first_page
        if end_page is None or (
            end_page < last_page and (end_idx - last_idx) <= PAGE_MARKER_MAX_BLOCKS
        ):
            end_page = last_page
        if end_page > last_page:
            if (end_idx - last_idx) <= PAGE_MARKER_MAX_BLOCKS:
                end_page = last_page
    if start_page is None:
        start_page = _boundary_page_guess(blocks, start_idx)
    if end_page is None:
        end_page = _boundary_page_guess(blocks, end_idx)
    if start_page is None or end_page is None:
        return None
    if start_page > end_page and pages_in_slice:
        start_page = pages_in_slice[0][1]
        end_page = pages_in_slice[-1][1]
    return start_page, end_page


def _apply_toc_range_hint(
    section_page_range: tuple[int, int], toc_map: TocMap
) -> tuple[int, int]:
    start_page, end_page = section_page_range
    toc_start = toc_map.get("risk_page_start")
    if isinstance(toc_start, int):
        start_page = toc_start

    toc_end = toc_map.get("risk_page_end")
    next_start = _next_start_from_toc(toc_map)

    if isinstance(toc_start, int) and isinstance(toc_end, int):
        if toc_end > toc_start:
            end_page = toc_end
        elif isinstance(next_start, int) and next_start > start_page:
            if end_page not in {next_start, next_start - 1}:
                end_page = max(start_page, next_start - 1)
    elif isinstance(next_start, int) and next_start > start_page:
        if end_page not in {next_start, next_start - 1}:
            end_page = max(start_page, next_start - 1)

    return start_page, end_page


def _next_start_from_toc(toc_map: TocMap) -> Optional[int]:
    next_row_text = toc_map.get("next_row_text")
    if not isinstance(next_row_text, str):
        return None
    parsed = _parse_toc_page_number(next_row_text)
    if parsed is None:
        parsed_row = _parse_toc_row_line(next_row_text)
        if parsed_row is not None:
            parsed = (parsed_row[2], parsed_row[3])
    if parsed is None:
        return None
    return parsed[0]


def _document_page_bounds(blocks: list[Block]) -> Optional[tuple[int, int]]:
    pages: list[int] = []
    for idx in range(len(blocks)):
        page_num = _extract_page_number_from_block(blocks, idx)
        if page_num is None:
            continue
        if _is_part_page_value(page_num):
            continue
        if page_num > DOC_PAGE_MAX:
            continue
        pages.append(page_num)
    if not pages:
        return None
    pages.sort()
    unique_pages = sorted(set(pages))
    if len(unique_pages) >= DOC_PAGE_MIN_COUNT:
        best_start = unique_pages[0]
        best_end = unique_pages[0]
        cluster_start = unique_pages[0]
        cluster_end = unique_pages[0]
        for page in unique_pages[1:]:
            if page - cluster_end <= DOC_PAGE_CLUSTER_GAP:
                cluster_end = page
                continue
            if (cluster_end - cluster_start) > (best_end - best_start):
                best_start, best_end = cluster_start, cluster_end
            cluster_start = page
            cluster_end = page
        if (cluster_end - cluster_start) > (best_end - best_start):
            best_start, best_end = cluster_start, cluster_end
        if (best_end - best_start) >= DOC_PAGE_CLUSTER_MIN_SPAN:
            return best_start, best_end
    return pages[0], pages[-1]


def _page_number_hint_for_toc(blocks: list[Block], idx: int, radius: int = 6) -> Optional[int]:
    start = max(0, idx - radius)
    end = min(len(blocks), idx + radius + 1)
    for neighbor_idx in range(start, end):
        text = blocks[neighbor_idx].text.strip()
        if not text:
            continue
        header_page = _extract_page_header_number(text)
        if header_page is not None:
            return header_page
        parsed = _parse_toc_page_number(text)
        if parsed is not None:
            return parsed[0]
        match = PAGE_WORD_LINE.match(text)
        if match is not None:
            return int(match.group(1))
        match = PAGE_OF_LINE.match(text)
        if match is not None:
            return int(match.group(1))
        numeric_page = _is_numeric_page_line(text)
        if numeric_page is not None and numeric_page <= 500:
            return numeric_page
    return None


def _start_crossref_like(blocks: list[Block]) -> bool:
    if not blocks:
        return False
    first_block: Optional[Block] = None
    for block in blocks:
        if block.text.strip():
            first_block = block
            break
    combined = " ".join(block.text for block in blocks if block.text)
    normalized = normalize_whitespace(combined)
    if not normalized:
        return False
    if first_block is not None and _is_strong_item_heading(first_block.text):
        if CROSS_REF_TERMS.search(first_block.text):
            return True
        return False
    if CROSS_REF_PREFIX.search(normalized) or CROSS_REF_QUOTED.search(normalized):
        return True
    if CROSS_REF_ITEM8.search(normalized) or CROSS_REF_ITEM_OTHER.search(normalized):
        return True
    if CROSS_REF_VERB.search(normalized) and ITEM_1A_BLOCK.search(normalized):
        return True
    return False


def _end_marker_block_ok(block: Block, pattern: re.Pattern[str]) -> bool:
    text = block.text
    normalized = _normalize_heading_candidate(text)
    if pattern is ITEM_1B_BLOCK:
        if re.search(r"(?m)^\s*item\s*1\s*\.?\s*b\b", text, re.IGNORECASE):
            return True
    if _is_heading_shaped_text(normalized):
        return True
    if block.is_heading_like:
        if _is_toc_line(normalized):
            return False
        if CROSS_REF_TERMS.search(normalized):
            return False
        if _looks_like_clause(normalized):
            return False
        return True
    if len(normalized) > HEADING_MAX_CHARS:
        return False
    if _is_toc_line(normalized) or _is_page_number_line(normalized):
        return False
    if CROSS_REF_TERMS.search(normalized):
        return False
    if _looks_like_clause(normalized):
        return False
    return _has_title_tail(normalized, pattern)


def _normalize_heading_label(text: str) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return " ".join(words)


def _label_spec_from_text(text: Optional[str]) -> Optional[tuple[str, bool]]:
    if not text:
        return None
    normalized = _normalize_heading_label(text)
    return NEXT_SECTION_LABELS.get(normalized)


def _primary_marker_matches_toc_label(
    marker: str, toc_label_spec: Optional[tuple[str, bool]]
) -> bool:
    if toc_label_spec is None:
        return True
    normalized = _normalize_heading_label(toc_label_spec[0])
    if marker == "1B":
        return normalized == _normalize_heading_label("Unresolved Staff Comments")
    if marker == "1C":
        return normalized == _normalize_heading_label("Cybersecurity")
    if marker == "2":
        return normalized == _normalize_heading_label("Properties")
    return True


def _starts_with_upper_label(text: str, label: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    words = label.split()
    if not words:
        return False
    pattern = r"^" + r"\s+".join(re.escape(word.upper()) for word in words)
    pattern += r"(\b|\s*[:.\-–])"
    return re.match(pattern, stripped) is not None


def _find_heading_end_marker(
    block_doc: BlockDoc,
    start_idx: int,
    allowed_labels: Optional[set[str]],
    page_anchor_min: Optional[int] = None,
) -> Optional[tuple[int, str]]:
    blocks = block_doc.blocks
    for idx in range(start_idx + 1, len(blocks)):
        if not _allow_end_marker_in_unsafe(block_doc, idx):
            continue
        if _end_marker_toc_like(blocks, idx):
            continue
        block = blocks[idx]
        heading_like = _is_heading_shaped_block(block)
        upper_label_match = False
        matched_label: Optional[str] = None
        if not heading_like:
            if allowed_labels is None:
                continue
            for label in allowed_labels:
                if _starts_with_upper_label(block.text, label):
                    upper_label_match = True
                    matched_label = label
                    break
            if not upper_label_match:
                continue
        if page_anchor_min is not None and not upper_label_match:
            page_hint = _candidate_page_hint(blocks, idx)
            if page_hint is not None and page_hint < page_anchor_min:
                continue
        normalized = _normalize_heading_label(block.text)
        if allowed_labels is not None:
            if upper_label_match and matched_label is not None:
                normalized = matched_label
            elif normalized not in allowed_labels:
                continue
        label_spec = NEXT_SECTION_LABELS.get(normalized)
        if label_spec is None:
            continue
        label, strict = label_spec
        if strict and normalized != _normalize_heading_label(label):
            continue
        return idx, label
    return None


def _toc_window_is_strong(score: TocScore) -> bool:
    has_item_marker = score["itemCodeBlocks"] >= 2 or score["itemPrefixBlocks"] >= 2
    has_dot_leaders = score["dotLeaderBlocks"] >= TOC_MIN_DOTLEADER_BLOCKS
    has_title_pages = score["titlePageBlocks"] >= TOC_MIN_TITLE_PAGE_BLOCKS
    numeric_signal = (
        score["pageNumBlocks"] >= 2
        or score["altPairs"] >= 2
        or has_dot_leaders
        or has_title_pages
    )
    if score["tocLike"] and has_item_marker and numeric_signal:
        return True
    toc_signal = (
        score["pageNumBlocks"]
        + score["dotLeaderBlocks"]
        + score["altPairs"]
        + score["titlePageBlocks"]
    )
    if toc_signal >= TOC_STRONG_SIGNAL_MIN and has_item_marker and numeric_signal:
        return True
    if (
        score["pageNumBlocks"] >= TOC_MIN_PAGE_NUM_BLOCKS
        and score["altPairs"] >= TOC_MIN_ALT_PAIRS
        and has_item_marker
    ):
        return True
    return False


def _toc_row_signal(blocks: list[Block]) -> int:
    hits = 0
    end = len(blocks)
    for idx, block in enumerate(blocks):
        if _parse_toc_row_line(block.text) is not None:
            hits += 1
            if hits >= TOC_MIN_ROW_SIGNAL:
                return hits
        if idx + 2 < end and _looks_like_toc_triplet(blocks, idx):
            hits += 1
            if hits >= TOC_MIN_ROW_SIGNAL:
                return hits
    return hits


def _classify_toc_region(blocks: list[Block], start: int, end: int) -> str:
    has_toc = False
    has_xref = False
    has_index = False
    for block in blocks[start:end]:
        text = block.text
        if _is_cross_reference_index_heading(text):
            has_xref = True
            break
        if _is_toc_heading(text):
            has_toc = True
        if _is_index_with_item_mentions(text):
            has_index = True
    early_region = start < TOC_PAGE_SCAN_BLOCKS
    if has_toc:
        return "toc_head" if early_region else "toc_late"
    if (has_xref or has_index) and early_region:
        return "toc_head"
    if has_xref or has_index:
        return "xref_index"
    return "toc_head" if early_region else "toc_late"


def detect_toc_regions(
    blocks: list[Block], repeat_freq: Optional[dict[str, int]] = None
) -> list[TocRegion]:
    if not blocks:
        return []
    repeat_freq = repeat_freq or _build_repeat_texts(blocks)
    window_size = min(TOC_SLICE_HEAD_BLOCKS, len(blocks))
    candidate_ranges: list[tuple[int, int]] = []
    doc_page_bounds = _document_page_bounds(blocks)

    scan_ranges: list[tuple[int, int]] = [(0, min(len(blocks), TOC_PAGE_SCAN_BLOCKS))]
    tail_start = max(0, len(blocks) - TOC_PAGE_SCAN_BLOCKS)
    if tail_start > 0:
        scan_ranges.append((tail_start, len(blocks)))

    for scan_start, scan_end in scan_ranges:
        for start in range(scan_start, scan_end, TOC_WINDOW_STRIDE):
            end = min(start + window_size, scan_end)
            if end <= start:
                break
            score = score_toc_window(blocks[start:end], repeat_freq)
            score = _adjust_toc_like(blocks[start:end], score)
            if _toc_window_is_strong(score):
                narrative_blocks = _narrative_blocks_in_head(
                    blocks[start:end], min(end - start, 60)
                )
                has_toc_heading = False
                for block in blocks[start:end]:
                    text = block.text
                    if (
                        _is_toc_heading(text)
                        or _is_cross_reference_index_heading(text)
                        or _is_index_with_item_mentions(text)
                    ):
                        has_toc_heading = True
                        break
                if scan_start == tail_start and not has_toc_heading:
                    continue
                if (
                    not has_toc_heading
                    and score["dotLeaderBlocks"] == 0
                    and score["itemCodeBlocks"] == 0
                    and _toc_row_signal(blocks[start:end]) < TOC_MIN_ROW_SIGNAL
                ):
                    continue
                # Very high narrative content = definitely not TOC
                if (
                    narrative_blocks >= TOC_NARRATIVE_BLOCKS_MAX * 3
                    and score["itemCodeBlocks"] == 0
                    and score["dotLeaderBlocks"] == 0
                ):
                    continue
                if (
                    narrative_blocks >= TOC_NARRATIVE_BLOCKS_MAX
                    and score["itemCodeBlocks"] == 0
                    and score["dotLeaderBlocks"] == 0
                    and score["titlePageBlocks"] <= 2
                ):
                    continue
                if (
                    not has_toc_heading
                    and narrative_blocks >= TOC_LONG_NARRATIVE_MAX
                    and score["itemCodeBlocks"] == 0
                    and score["dotLeaderBlocks"] == 0
                    and score["titlePageBlocks"] <= 2
                ):
                    continue
                if scan_start == tail_start and doc_page_bounds is not None:
                    page_hint = _page_number_hint_for_toc(blocks, start)
                    if page_hint is not None and (doc_page_bounds[1] - page_hint) > TOC_TAIL_PAGE_WINDOW:
                        continue
                candidate_ranges.append((start, end))

    last_toc_heading_idx: Optional[int] = None
    last_xref_heading_idx: Optional[int] = None
    last_index_heading_idx: Optional[int] = None
    for idx, block in enumerate(blocks):
        if _is_toc_heading(block.text):
            if _is_repeated_short_text(block.text, repeat_freq):
                continue
            if idx >= TOC_HEAD_BLOCKS and idx < tail_start:
                continue
            if last_toc_heading_idx is None or idx - last_toc_heading_idx > TOC_PAGE_SCAN_BLOCKS:
                start = idx
                end = min(idx + window_size, len(blocks))
                score = score_toc_window(blocks[start:end], repeat_freq)
                score = _adjust_toc_like(blocks[start:end], score)
                page_hint = _page_number_hint_for_toc(blocks, idx)
                if idx < TOC_HEAD_BLOCKS:
                    if page_hint is not None and page_hint > TOC_HEAD_MAX_PAGE:
                        continue
                else:
                    if page_hint is None:
                        continue
                    if doc_page_bounds is not None and (doc_page_bounds[1] - page_hint) > TOC_TAIL_PAGE_WINDOW:
                        continue
                    if not _toc_window_is_strong(score):
                        continue
                candidate_ranges.append((start, end))
                last_toc_heading_idx = idx
            continue
        if _is_cross_reference_index_heading(block.text):
            if last_xref_heading_idx is None or idx - last_xref_heading_idx > TOC_PAGE_SCAN_BLOCKS:
                page_hint = _page_number_hint_for_toc(blocks, idx)
                if (
                    page_hint is not None
                    and doc_page_bounds is not None
                    and (doc_page_bounds[1] - page_hint) > TOC_TAIL_PAGE_WINDOW
                ):
                    continue
                start = idx
                end = min(idx + window_size, len(blocks))
                candidate_ranges.append((start, end))
                last_xref_heading_idx = idx
            continue
        if _is_index_with_item_mentions(block.text):
            if last_index_heading_idx is not None and idx - last_index_heading_idx <= TOC_PAGE_SCAN_BLOCKS:
                continue
            start = idx
            end = min(idx + window_size, len(blocks))
            score = score_toc_window(blocks[start:end], repeat_freq)
            score = _adjust_toc_like(blocks[start:end], score)
            if _toc_window_is_strong(score):
                page_hint = _page_number_hint_for_toc(blocks, idx)
                if (
                    page_hint is not None
                    and doc_page_bounds is not None
                    and (doc_page_bounds[1] - page_hint) > TOC_TAIL_PAGE_WINDOW
                ):
                    continue
                candidate_ranges.append((start, end))
                last_index_heading_idx = idx

    if not candidate_ranges:
        return []

    candidate_ranges.sort(key=lambda pair: pair[0])
    merged: list[list[int]] = []
    for start, end in candidate_ranges:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    regions: list[TocRegion] = []
    for start, end in merged:
        score = score_toc_window(blocks[start:end], repeat_freq)
        score = _adjust_toc_like(blocks[start:end], score)
        kind = _classify_toc_region(blocks, start, end)
        regions.append({"start_idx": start, "end_idx": end, "score": score, "kind": kind})
    return regions


def is_in_unsafe_zone(block_doc: BlockDoc, block_idx: int) -> bool:
    for region in block_doc.unsafe_regions:
        if region["start_idx"] <= block_idx < region["end_idx"]:
            return True
    return False


def _unsafe_region_for_idx(block_doc: BlockDoc, block_idx: int) -> Optional[TocRegion]:
    for region in block_doc.unsafe_regions:
        if region["start_idx"] <= block_idx < region["end_idx"]:
            return region
    return None


def _end_marker_distance_ok(block_doc: BlockDoc, start_idx: int, end_idx: int) -> bool:
    if end_idx <= start_idx:
        return False
    char_dist = block_doc.offsets[end_idx] - block_doc.offsets[start_idx]
    block_dist = end_idx - start_idx
    return char_dist >= END_MIN_CHARS or block_dist >= END_MIN_BLOCKS


def _allow_short_end_marker(
    block_doc: BlockDoc, start_idx: int, end_idx: int, form_type: str
) -> bool:
    if form_type != "10-K":
        return False
    if end_idx <= start_idx:
        return False
    if start_idx < TOC_HEAD_BLOCKS:
        return False
    blocks = block_doc.blocks
    if start_idx >= len(blocks):
        return False
    start_block = blocks[start_idx]
    strong_start = _is_strong_risk_heading(start_block, form_type)
    if not strong_start and ITEM_1A_BLOCK.search(start_block.text):
        if start_idx + 1 < len(blocks) and _contains_risk_factors(blocks[start_idx + 1].text):
            strong_start = True
    if not strong_start:
        return False
    for idx in range(start_idx + 1, end_idx):
        block = blocks[idx]
        if block.is_heading_like:
            continue
        if len(block.text) >= NARRATIVE_MIN_CHARS:
            return True
    return False


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
    toc_freq: dict[str, int] = {}
    numeric_only_count = 0
    for block in blocks:
        text = block.text.strip()
        if not text:
            continue
        key = text.lower()
        if "table of contents" in key:
            toc_freq[key] = toc_freq.get(key, 0) + 1
        if TOC_PAGE_NUM.match(text):
            numeric_only_count += 1
        if len(text) > HF_SHORT_MAX_CHARS:
            continue
        freq[key] = freq.get(key, 0) + 1

    def is_heading_marker(text: str) -> bool:
        if len(text) > HF_SHORT_MAX_CHARS:
            return False
        if not _is_heading_shaped_text(text):
            return False
        if RISK_FACTORS_HEADING.search(text):
            return True
        if ITEM_1A_BLOCK.search(text) or ITEM_1B_BLOCK.search(text) or ITEM_1C_BLOCK.search(text):
            return True
        if ITEM_2_BLOCK.search(text) or ITEM_3_BLOCK.search(text) or ITEM_3D_BLOCK.search(text):
            return True
        if ITEM_4_BLOCK.search(text) or ITEM_5_PLUS_BLOCK.search(text):
            return True
        if ITEM_7_BLOCK.search(text) or ITEM_8_BLOCK.search(text):
            return True
        if PART_I_BLOCK.search(text) or PART_II_BLOCK.search(text):
            return True
        return False

    cleaned: list[Block] = []
    toc_repeat_found = False
    # Track which heading markers we've already kept (preserve first occurrence)
    kept_heading_markers: set[str] = set()
    for block in blocks:
        text = block.text.strip()
        if not text:
            continue
        lower = text.lower()
        if "table of contents" in lower:
            key = lower
            if toc_freq.get(key, 0) >= HF_REPEAT_MIN:
                toc_repeat_found = True
                continue
        if len(text) <= HF_SHORT_MAX_CHARS:
            if is_heading_marker(text):
                if freq.get(lower, 0) >= HF_REPEAT_MIN:
                    # Preserve the first occurrence of each repeated heading marker
                    if lower not in kept_heading_markers:
                        kept_heading_markers.add(lower)
                        cleaned.append(block)
                    continue
                cleaned.append(block)
                continue
            if TOC_PAGE_NUM.match(text) and numeric_only_count >= HF_REPEAT_MIN:
                continue
            key = lower
            if freq.get(key, 0) >= HF_REPEAT_MIN:
                continue
        cleaned.append(block)

    if toc_repeat_found:
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
        # Check for "RISK FACTORS" at the very start of the first few blocks,
        # even if not heading-shaped (handles merged heading+content like GE 2024)
        if idx < 3:
            text = blocks[idx].text.strip()
            if text.upper().startswith("RISK FACTORS"):
                return True
        if not blocks[idx].is_heading_like:
            continue
        if form_type == "10-K":
            if ITEM_1A_BLOCK.search(blocks[idx].text):
                if idx + 1 < end and _contains_risk_factors(blocks[idx + 1].text):
                    return True
        else:
            if ITEM_3D_BLOCK.search(blocks[idx].text):
                if idx + 1 < end and _contains_risk_factors(blocks[idx + 1].text):
                    return True
    return False


def _is_item1_business_heading(block: Block) -> bool:
    if not ITEM_1_BUSINESS_BLOCK.search(block.text):
        return False
    return _is_heading_shaped_text(block.text)


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
        if _is_item1_business_heading(block):
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


def _adjust_toc_like(blocks: list[Block], toc_score: TocScore) -> TocScore:
    narrative_blocks = _narrative_blocks_in_head(blocks, 20)
    extended_narrative = _narrative_blocks_in_head(blocks, min(len(blocks), 60))
    if toc_score["tocLike"]:
        if narrative_blocks >= 2 and toc_score["itemPrefixBlocks"] < TOC_MIN_ITEM_PREFIX_BLOCKS:
            adjusted: TocScore = {
                "pageNumBlocks": toc_score["pageNumBlocks"],
                "itemCodeBlocks": toc_score["itemCodeBlocks"],
                "itemPrefixBlocks": toc_score["itemPrefixBlocks"],
                "romanBlocks": toc_score["romanBlocks"],
                "dotLeaderBlocks": toc_score["dotLeaderBlocks"],
                "altPairs": toc_score["altPairs"],
                "titlePageBlocks": toc_score["titlePageBlocks"],
                "tocLike": False,
            }
            return adjusted
        if (
            extended_narrative >= TOC_NARRATIVE_BLOCKS_MAX
            and toc_score["itemCodeBlocks"] == 0
            and toc_score["dotLeaderBlocks"] == 0
            and toc_score["titlePageBlocks"] <= 2
        ):
            adjusted: TocScore = {
                "pageNumBlocks": toc_score["pageNumBlocks"],
                "itemCodeBlocks": toc_score["itemCodeBlocks"],
                "itemPrefixBlocks": toc_score["itemPrefixBlocks"],
                "romanBlocks": toc_score["romanBlocks"],
                "dotLeaderBlocks": toc_score["dotLeaderBlocks"],
                "altPairs": toc_score["altPairs"],
                "titlePageBlocks": toc_score["titlePageBlocks"],
                "tocLike": False,
            }
            return adjusted
        return toc_score
    if toc_score["itemPrefixBlocks"] >= TOC_MIN_ITEM_PREFIX_BLOCKS and narrative_blocks < 2:
        adjusted: TocScore = {
            "pageNumBlocks": toc_score["pageNumBlocks"],
            "itemCodeBlocks": toc_score["itemCodeBlocks"],
            "itemPrefixBlocks": toc_score["itemPrefixBlocks"],
            "romanBlocks": toc_score["romanBlocks"],
            "dotLeaderBlocks": toc_score["dotLeaderBlocks"],
            "altPairs": toc_score["altPairs"],
            "titlePageBlocks": toc_score["titlePageBlocks"],
            "tocLike": True,
        }
        return adjusted
    return toc_score


def _apply_confidence_adjustments(
    score: float,
    toc_like_head: bool,
    toc_removed: bool,
    end_fallback: bool,
    end_not_found: bool,
    slice_len: int,
    cross_ref_suspected: bool,
    strong_heading_near: bool,
    start_crossref_like: bool,
    toc_like_tail: bool,
    toc_range_mismatch: bool,
    early_penalty_relief: float,
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
    if start_crossref_like:
        adjusted -= CONF_PENALTY_START_PURITY
    if toc_like_tail:
        adjusted -= CONF_PENALTY_TOC_LIKE_TAIL
    if toc_range_mismatch:
        adjusted -= CONF_PENALTY_TOC_RANGE_MISMATCH
    if early_penalty_relief > 0:
        adjusted += early_penalty_relief
    return max(0.05, min(adjusted, 0.95))


_RF_CONTINUED_RE = re.compile(r"^Risk\s+factors?\s*(\(continued\))?$", re.IGNORECASE)
_PAGE_BREAK_STRATEGIC_RE = re.compile(r"^STRATEGIC\s+REPORT$", re.IGNORECASE)
_RF_CONTINUED_LOOKAHEAD = 18


def _find_rf_continued_boundary(
    blocks: list[Block], start_idx: int
) -> Optional[int]:
    """For 20-F filings whose body uses 'Risk factors (continued)' page headers
    instead of standard Item numbering (e.g. ASML): find the first page-break
    block ('STRATEGIC REPORT') after the start that is NOT followed within
    ``_RF_CONTINUED_LOOKAHEAD`` blocks by 'Risk factors' or
    'Risk factors (continued)'.

    Returns the block index of that page-break block, or ``None`` if no such
    boundary is found (meaning either the filing doesn't use the pattern or
    the risk factors section runs to the end of the filing).
    """
    # First verify the filing actually uses the pattern.
    has_continued = any(
        _RF_CONTINUED_RE.match(b.text.strip())
        for b in blocks[start_idx + 1 : min(start_idx + 800, len(blocks))]
    )
    if not has_continued:
        return None

    for i in range(start_idx + 1, len(blocks)):
        if not _PAGE_BREAK_STRATEGIC_RE.match(blocks[i].text.strip()):
            continue
        # Check whether the next ~18 blocks contain a 'Risk factors' header,
        # indicating we're still inside the Risk Factors section.
        is_rf_page = False
        for j in range(i + 1, min(i + _RF_CONTINUED_LOOKAHEAD, len(blocks))):
            if _RF_CONTINUED_RE.match(blocks[j].text.strip()):
                is_rf_page = True
                break
        if not is_rf_page:
            return i
    return None


def find_end_marker_blockdoc(
    block_doc: BlockDoc, start_idx: int, form_type: str
) -> tuple[Optional[int], Optional[str], bool]:
    blocks = block_doc.blocks
    toc_map = block_doc.toc_map
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
        fallback = [
            ("LEGAL PROCEEDINGS", LEGAL_PROCEEDINGS_BLOCK),
            ("PART II", PART_II_BLOCK),
            ("ITEM 7", ITEM_7_BLOCK),
            ("ITEM 8", ITEM_8_BLOCK),
            ("MD&A", MDNA_BLOCK),
            ("FINANCIAL STATEMENTS", FINANCIAL_STATEMENTS_BLOCK),
            ("NOTES", NOTES_FINANCIAL_STATEMENTS_BLOCK),
        ]

    toc_label_spec = _label_spec_from_text(toc_map.get("next_label") if toc_map else None)
    next_page_start = _next_start_from_toc(toc_map) if isinstance(toc_map, dict) else None
    primary_match: Optional[tuple[int, str]] = None
    for idx in range(start_idx + 1, len(blocks)):
        block = blocks[idx]
        text = block.text
        for label, pattern in primary:
            if not pattern.search(text):
                continue
            if not _end_marker_block_ok(block, pattern):
                continue
            if not _allow_end_marker_in_unsafe(block_doc, idx):
                continue
            if not _end_marker_distance_ok(block_doc, start_idx, idx):
                if not _allow_short_end_marker(block_doc, start_idx, idx, form_type):
                    continue
            if _end_marker_toc_like(blocks, idx):
                if label not in {"1B", "1C", "2", "4", "4A", "4B"}:
                    continue
            primary_match = (idx, label)
            break
        if primary_match is not None:
            break

    primary_rejected = False
    if primary_match is not None and toc_label_spec is not None:
        if not _primary_marker_matches_toc_label(primary_match[1], toc_label_spec):
            allowed_labels = {_normalize_heading_label(toc_label_spec[0])}
            heading_match = _find_heading_end_marker(
                block_doc, start_idx, allowed_labels, page_anchor_min=next_page_start
            )
            if heading_match is not None:
                return heading_match[0], heading_match[1], False
            primary_rejected = True
    if primary_match is not None and not primary_rejected:
        return primary_match[0], primary_match[1], False

    heading_fallback = _find_heading_end_marker(
        block_doc, start_idx, None, page_anchor_min=next_page_start
    )
    if toc_label_spec is not None:
        allowed_labels = {_normalize_heading_label(toc_label_spec[0])}
        heading_match = _find_heading_end_marker(
            block_doc, start_idx, allowed_labels, page_anchor_min=next_page_start
        )
        if heading_fallback is not None and (
            heading_match is None or heading_fallback[0] < heading_match[0]
        ):
            return heading_fallback[0], heading_fallback[1], True
        if heading_match is not None:
            return heading_match[0], heading_match[1], True
    if heading_fallback is not None:
        return heading_fallback[0], heading_fallback[1], True

    for idx in range(start_idx + 1, len(blocks)):
        block = blocks[idx]
        if is_in_unsafe_zone(block_doc, idx):
            continue
        text = block.text
        for label, pattern in fallback:
            if not pattern.search(text):
                continue
            if not _end_marker_block_ok(block, pattern):
                continue
            if not _end_marker_distance_ok(block_doc, start_idx, idx):
                if not _allow_short_end_marker(block_doc, start_idx, idx, form_type):
                    continue
            if _end_marker_toc_like(blocks, idx):
                continue
            return idx, label, True

    start_offset = block_doc.offsets[start_idx]
    search_start = min(len(block_doc.full_text), start_offset + END_MIN_CHARS)
    if form_type == "20-F":
        text_markers = END_MARKERS_20F + [("5", ITEM_5_PLUS_HEADING)]
    else:
        text_markers = END_MARKERS_10K + [
            ("PART II", PART_II_HEADING),
            ("ITEM 7", ITEM_7_HEADING),
            ("ITEM 8", ITEM_8_HEADING),
            ("MD&A", MDNA_HEADING),
            ("FINANCIAL STATEMENTS", FINANCIAL_STATEMENTS_HEADING),
            ("NOTES", NOTES_FINANCIAL_STATEMENTS_HEADING),
        ]
    end_offset: Optional[int] = None
    end_label: Optional[str] = None
    for label, pattern in text_markers:
        for match in pattern.finditer(block_doc.full_text, search_start + 1):
            line_start = block_doc.full_text.rfind("\n", 0, match.start())
            if line_start == -1:
                line_start = 0
            else:
                line_start += 1
            line_end = block_doc.full_text.find("\n", match.start())
            if line_end == -1:
                line_end = len(block_doc.full_text)
            line = block_doc.full_text[line_start:line_end]
            if not _is_heading_shaped_text(line):
                continue
            candidate_offset = match.start()
            candidate_block_idx = _block_index_for_offset(block_doc, candidate_offset)
            if is_in_unsafe_zone(block_doc, candidate_block_idx):
                continue
            if _end_marker_toc_like(block_doc.blocks, candidate_block_idx):
                continue
            if end_offset is None or candidate_offset < end_offset:
                end_offset = candidate_offset
                end_label = label
            break
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
            "itemPrefixBlocks": 0,
            "romanBlocks": 0,
            "dotLeaderBlocks": 0,
            "altPairs": 0,
            "titlePageBlocks": 0,
            "tocLike": False,
        }
        return False, None, empty
    repeat_freq = _build_repeat_texts(blocks)
    toc_regions = detect_toc_regions(blocks, repeat_freq)
    doc_head_score = score_toc_window(blocks[:TOC_HEAD_BLOCKS], repeat_freq)
    if toc_regions:
        for region in toc_regions:
            if region["kind"] == "toc_head":
                return True, region["end_idx"], region["score"]
    return False, None, doc_head_score


def _find_heading_index(
    blocks: list[Block], pattern: re.Pattern[str], start: int = 0
) -> Optional[int]:
    for block in blocks[start:]:
        if _is_heading_shaped_block(block) and pattern.search(block.text):
            return block.idx
    return None


def _has_nearby_strong_item1a(blocks: list[Block], idx: int) -> bool:
    start = max(0, idx - WEAK_ITEM1A_NEAR_BLOCKS)
    end = min(len(blocks), idx + WEAK_ITEM1A_NEAR_BLOCKS + 1)
    for offset in range(start, end):
        if offset == idx:
            continue
        block = blocks[offset]
        if not _is_heading_shaped_block(block):
            continue
        if ITEM_1A_BLOCK.search(block.text) and _contains_risk_factors(block.text):
            return True
    return False


def _item_heading_followup(blocks: list[Block], start_idx: int) -> bool:
    end = min(len(blocks), start_idx + ITEM_FOLLOWUP_LOOKAHEAD + 1)
    for idx in range(start_idx + 1, end):
        block = blocks[idx]
        text = block.text.strip()
        if not text:
            continue
        if len(text) <= HEADING_MAX_CHARS:
            if (
                ITEM_1B_BLOCK.search(text)
                or ITEM_1C_BLOCK.search(text)
                or ITEM_2_BLOCK.search(text)
                or ITEM_3_BLOCK.search(text)
                or ITEM_4_BLOCK.search(text)
                or PART_II_BLOCK.search(text)
            ):
                if len(text) < NARRATIVE_MIN_CHARS:
                    return True
        if _is_heading_shaped_block(block):
            if (
                ITEM_1B_BLOCK.search(text)
                or ITEM_1C_BLOCK.search(text)
                or ITEM_2_BLOCK.search(text)
                or ITEM_3_BLOCK.search(text)
                or ITEM_4_BLOCK.search(text)
                or PART_II_BLOCK.search(text)
            ):
                return True
            if _contains_risk_factors(text):
                return False
            continue
        if len(text) >= NARRATIVE_MIN_CHARS:
            return False
    return False


def _dense_item_followup(blocks: list[Block], start_idx: int) -> bool:
    end = min(len(blocks), start_idx + ITEM_FOLLOWUP_LOOKAHEAD + 1)
    seen: set[str] = set()
    for idx in range(start_idx + 1, end):
        text = blocks[idx].text.strip()
        if not text:
            continue
        if len(text) > HEADING_MAX_CHARS:
            continue
        if ITEM_1B_BLOCK.search(text):
            seen.add("1B")
        if ITEM_1C_BLOCK.search(text):
            seen.add("1C")
        if ITEM_2_BLOCK.search(text):
            seen.add("2")
        if ITEM_3_BLOCK.search(text):
            seen.add("3")
        if ITEM_4_BLOCK.search(text):
            seen.add("4")
        if PART_II_BLOCK.search(text):
            seen.add("PART_II")
        if len(seen) >= 2:
            return True
    return False


def _has_nearby_narrative(blocks: list[Block], start_idx: int) -> bool:
    end = min(len(blocks), start_idx + ITEM_FOLLOWUP_LOOKAHEAD + 1)
    for idx in range(start_idx + 1, end):
        block = blocks[idx]
        if block.is_heading_like:
            continue
        if len(block.text) >= NARRATIVE_MIN_CHARS:
            return True
    return False


def _has_continued_heading_near(blocks: list[Block], start_idx: int) -> bool:
    end = min(len(blocks), start_idx + ITEM_FOLLOWUP_LOOKAHEAD + 1)
    for idx in range(start_idx, end):
        block = blocks[idx]
        text = block.text.strip()
        if not text:
            continue
        if idx != start_idx and not _is_heading_shaped_block(block):
            continue
        if CONTINUED_MARKER.search(text):
            return True
    return False


def _candidate_has_item1_business_before_item1a(
    block_doc: BlockDoc, start_idx: int, max_chars: int
) -> bool:
    blocks = block_doc.blocks
    if start_idx >= len(blocks):
        return False
    start_offset = block_doc.offsets[start_idx]
    limit_offset = start_offset + max_chars
    for idx in range(start_idx + 1, len(blocks)):
        if block_doc.offsets[idx] > limit_offset:
            break
        block = blocks[idx]
        if not _is_heading_shaped_block(block):
            continue
        if _is_item1_business_heading(block):
            return True
        if ITEM_1A_BLOCK.search(block.text) and _contains_risk_factors(block.text):
            return False
    return False


def _force_toc_like(toc_score: TocScore) -> TocScore:
    if toc_score["tocLike"]:
        return toc_score
    return {
        "pageNumBlocks": toc_score["pageNumBlocks"],
        "itemCodeBlocks": toc_score["itemCodeBlocks"],
        "itemPrefixBlocks": toc_score["itemPrefixBlocks"],
        "romanBlocks": toc_score["romanBlocks"],
        "dotLeaderBlocks": toc_score["dotLeaderBlocks"],
        "altPairs": toc_score["altPairs"],
        "titlePageBlocks": toc_score["titlePageBlocks"],
        "tocLike": True,
    }


def _item1a_risk_close(text: str) -> bool:
    match_item = ITEM_1A_BLOCK.search(text)
    match_risk = RISK_FACTORS.search(text)
    if match_item is None or match_risk is None:
        return False
    return abs(match_item.start() - match_risk.start()) <= ITEM1A_RISK_CLOSE_CHARS


def _has_strong_cross_ref_signal(text: str) -> bool:
    if CROSS_REF_PREFIX.search(text):
        return True
    if CROSS_REF_QUOTED.search(text):
        return True
    if CROSS_REF_ITEM8.search(text):
        return True
    if CROSS_REF_ITEM_OTHER.search(text):
        return True
    return False


def _cross_ref_window_text(blocks: list[Block], idx: int, radius: int = 2) -> str:
    start = max(0, idx - radius)
    end = min(len(blocks), idx + radius + 1)
    parts: list[str] = []
    for block in blocks[start:end]:
        if block.text:
            parts.append(block.text)
    return normalize_whitespace(" ".join(parts))


def _next_block_is_risk_heading(blocks: list[Block], idx: int) -> bool:
    if idx + 1 >= len(blocks):
        return False
    next_block = blocks[idx + 1]
    if not _is_heading_shaped_block(next_block):
        return False
    return _contains_risk_factors(next_block.text)


def _is_cross_ref_suspected(text: str, prev_text: Optional[str] = None) -> bool:
    if not ITEM_1A_BLOCK.search(text):
        return False
    combined = text
    if prev_text and CROSS_REF_VERB.search(prev_text):
        combined = f"{prev_text} {text}".strip()
    if CROSS_REF_PREFIX.search(combined):
        return True
    if CROSS_REF_QUOTED.search(combined):
        return True
    if CROSS_REF_AND_ITEM.search(combined) and _contains_risk_factors(combined):
        return True
    if CROSS_REF_ITEM8.search(combined):
        return True
    if CROSS_REF_ITEM_OTHER.search(combined):
        return True
    return False


def _item1a_risk_adjacency_bonus(blocks: list[Block], idx: int) -> float:
    text = blocks[idx].text
    if ITEM_1A_BLOCK.search(text) and _contains_risk_factors(text):
        if _item1a_risk_close(text):
            return CANDIDATE_ITEM1A_RISK_ADJ_BONUS
    if ITEM_1A_BLOCK.search(text) and idx + 1 < len(blocks):
        next_block = blocks[idx + 1]
        if _is_heading_shaped_block(next_block) and _contains_risk_factors(next_block.text):
            return CANDIDATE_ITEM1A_RISK_ADJ_BONUS
    if _contains_risk_factors(text) and idx > 0:
        prev_block = blocks[idx - 1]
        if _is_heading_shaped_block(prev_block) and ITEM_1A_BLOCK.search(prev_block.text):
            return CANDIDATE_ITEM1A_RISK_ADJ_BONUS
    return 0.0


def _is_cross_ref_candidate(
    blocks: list[Block],
    idx: int,
    prev_text: Optional[str],
) -> bool:
    block = blocks[idx]
    text = block.text
    combined = text
    if prev_text and CROSS_REF_VERB.search(prev_text):
        combined = f"{prev_text} {text}".strip()

    cross_ref = _is_cross_ref_suspected(text, prev_text)
    strong_cross_ref = _has_strong_cross_ref_signal(combined)

    window_text = _cross_ref_window_text(blocks, idx)
    if _has_strong_cross_ref_signal(window_text):
        cross_ref = True
        strong_cross_ref = True

    if cross_ref and _is_strong_item_heading(text) and _has_nearby_narrative(blocks, idx):
        if not (CROSS_REF_TERMS.search(text) or (prev_text and CROSS_REF_VERB.search(prev_text))):
            cross_ref = False
            strong_cross_ref = False

    if cross_ref and not strong_cross_ref:
        if _is_heading_shaped_block(block) and _next_block_is_risk_heading(blocks, idx):
            cross_ref = False

    return cross_ref


def _score_start_candidate(
    rule: str,
    cross_ref: bool,
    in_toc_region: bool,
    toc_like_head: bool,
    before_item1: bool,
    strong_heading: bool,
    lookahead_bonus: float,
) -> float:
    rule_bonus = {
        "item1a_risk_heading": 0.3,
        "item1a_heading_followed_by_risk": 0.2,
        "risk_factors_heading": 0.1,
        "risk_factors_prefix": 0.1,
        "anchor_item1a": 0.05,
        "item3d_risk_heading": 0.3,
        "item3d_heading_followed_by_risk": 0.2,
        "d_risk_factors_heading": 0.1,
        "anchor_item3d": 0.05,
    }
    score = CANDIDATE_BASE_SCORE + rule_bonus.get(rule, 0.0)
    if strong_heading:
        score += 0.05
    score += lookahead_bonus
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
    repeat_freq = _build_repeat_texts(blocks)
    toc_regions = detect_toc_regions(blocks, repeat_freq)

    def score_window(window: list[Block]) -> TocScore:
        return score_toc_window(window, repeat_freq)
    unsafe_regions: list[TocRegion] = []
    for region in toc_regions:
        if region["kind"] != "xref_index" and not _toc_window_is_strong(region["score"]):
            continue
        end_idx = region["end_idx"]
        if region["kind"] == "toc_head":
            end_idx = region["end_idx"]
        unsafe_regions.append(
            {
                "start_idx": region["start_idx"],
                "end_idx": end_idx,
                "score": region["score"],
                "kind": region["kind"],
            }
        )
    block_doc.toc_regions = toc_regions
    block_doc.unsafe_regions = unsafe_regions
    toc_map = extract_toc_entries(block_doc, toc_regions)
    block_doc.toc_map = toc_map

    toc_detected = bool(toc_regions)
    toc_region_end_idx: Optional[int] = None
    toc_score_doc_head = score_window(blocks[:TOC_HEAD_BLOCKS])
    for region in toc_regions:
        if region["kind"] == "toc_head":
            toc_region_end_idx = min(region["end_idx"], region["start_idx"] + TOC_HEAD_BLOCKS)
            toc_score_doc_head = region["score"]
            break
    if not toc_detected and toc_score_doc_head.get("tocLike", False):
        toc_signal = (
            toc_score_doc_head["pageNumBlocks"]
            + toc_score_doc_head["dotLeaderBlocks"]
            + toc_score_doc_head["altPairs"]
        )
        if toc_signal >= TOC_STRONG_SIGNAL_MIN or (
            toc_score_doc_head["pageNumBlocks"] >= TOC_MIN_PAGE_NUM_BLOCKS
            and toc_score_doc_head["altPairs"] >= TOC_MIN_ALT_PAIRS
        ):
            toc_detected = True
            toc_region_end_idx = TOC_HEAD_BLOCKS
            fallback_region: TocRegion = {
                "start_idx": 0,
                "end_idx": TOC_HEAD_BLOCKS,
                "score": toc_score_doc_head,
                "kind": "toc_head",
            }
            toc_regions.insert(
                0,
                fallback_region,
            )
            unsafe_regions.insert(0, fallback_region)
            block_doc.toc_regions = toc_regions
            block_doc.unsafe_regions = unsafe_regions

    idx_part_i = _find_heading_index(blocks, PART_I_BLOCK)
    idx_item1_business = None
    if idx_part_i is not None:
        idx_item1_business = _find_heading_index(blocks, ITEM_1_BUSINESS_BLOCK, start=idx_part_i)
    else:
        idx_item1_business = _find_heading_index(blocks, ITEM_1_BUSINESS_BLOCK)

    exclude_ranges = _build_toc_exclude_ranges(toc_regions, idx_item1_business)

    candidate_rules: dict[int, str] = {}

    def add_candidate(idx: int, rule: str) -> None:
        priority = {
            "item1a_risk_heading": 3,
            "item1a_heading_followed_by_risk": 2,
            "risk_factors_heading": 1,
            "risk_factors_prefix": 1,
            "anchor_item1a": 0,
            "item3d_risk_heading": 3,
            "item3d_heading_followed_by_risk": 2,
            "d_risk_factors_heading": 1,
            "anchor_item3d": 0,
        }.get(rule, 0)
        existing = candidate_rules.get(idx)
        if existing is None:
            candidate_rules[idx] = rule
            return
        existing_priority = {
            "item1a_risk_heading": 3,
            "item1a_heading_followed_by_risk": 2,
            "risk_factors_heading": 1,
            "risk_factors_prefix": 1,
            "anchor_item1a": 0,
            "item3d_risk_heading": 3,
            "item3d_heading_followed_by_risk": 2,
            "d_risk_factors_heading": 1,
            "anchor_item3d": 0,
        }.get(existing, 0)
        if priority > existing_priority:
            candidate_rules[idx] = rule

    for idx, block in enumerate(blocks):
        if not _is_heading_shaped_block(block):
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

    for idx, block in enumerate(blocks):
        if not block.ids:
            continue
        for anchor in block.ids:
            if ANCHOR_ITEM1A.search(anchor):
                add_candidate(idx, "anchor_item1a")
            if ANCHOR_ITEM3D.search(anchor):
                add_candidate(idx, "anchor_item3d")

    def has_non_anchor_rule() -> bool:
        for rule in candidate_rules.values():
            if rule not in ("anchor_item1a", "anchor_item3d"):
                return True
        return False

    form_type = "10-K"
    idx_item3 = None
    idx_item4 = None
    if not has_non_anchor_rule():
        start_search = toc_region_end_idx or 0
        # Search for successive Item 3 / Item 4 pairs, skipping cross-reference
        # table entries where the distance between them is too short to contain
        # actual risk narrative (e.g., ASML 20-F form reference tables).
        _search_from = start_search
        while _search_from < len(blocks):
            idx_item3 = _find_heading_index(blocks, ITEM_3_BLOCK, start=_search_from)
            idx_key_info = _find_heading_index(blocks, KEY_INFORMATION_BLOCK, start=_search_from)
            if idx_item3 is None:
                idx_item3 = idx_key_info
            if idx_item3 is None:
                break
            idx_item4 = None
            for candidate in range(idx_item3 + 1, len(blocks)):
                block = blocks[candidate]
                if not _is_heading_shaped_block(block):
                    continue
                if not ITEM_4_BLOCK.search(block.text):
                    continue
                if candidate - idx_item3 < END_MIN_BLOCKS:
                    continue
                idx_item4 = candidate
                break
            # If the region around Item 3 has no narrative content (blocks
            # >= 200 chars), it is likely a cross-reference / form-item mapping
            # table rather than the real body section.  Skip forward past
            # whatever Item 4 we found (or past this Item 3) and keep looking.
            if not _has_nearby_narrative(blocks, idx_item3):
                _search_from = (idx_item4 + 1) if idx_item4 is not None else (idx_item3 + 1)
                idx_item3 = None
                idx_item4 = None
                continue
            break
        if idx_item3 is not None:
            end = idx_item4 if idx_item4 is not None else len(blocks)
            for idx in range(idx_item3, end):
                block = blocks[idx]
                if not _is_heading_shaped_block(block):
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
    if has_non_anchor_rule() and form_type == "10-K":
        for idx, block in enumerate(blocks):
            if not _is_heading_shaped_block(block):
                continue
            if _contains_risk_factors(block.text) and _has_nearby_strong_item1a(blocks, idx):
                add_candidate(idx, "risk_factors_heading")
        item1a_indices = [
            idx for idx, rule in candidate_rules.items() if rule.startswith("item1a")
        ]
        if item1a_indices:
            has_reliable_item1a = False
            for idx in item1a_indices:
                block = blocks[idx]
                toc_score = score_window(blocks[idx : idx + TOC_SLICE_HEAD_BLOCKS])
                toc_score = _adjust_toc_like(
                    blocks[idx : idx + TOC_SLICE_HEAD_BLOCKS], toc_score
                )
                if _item_heading_followup(blocks, idx):
                    toc_score = _force_toc_like(toc_score)
                in_unsafe_zone = is_in_unsafe_zone(block_doc, idx)
                if toc_score["tocLike"] or in_unsafe_zone:
                    continue
                prev_text = blocks[idx - 1].text if idx > 0 else None
                if _is_strong_item_heading(block.text):
                    prev_text = None
                if _is_cross_ref_candidate(blocks, idx, prev_text):
                    continue
                has_reliable_item1a = True
                break
            if not has_reliable_item1a:
                for idx, block in enumerate(blocks):
                    is_prefix = False
                    heading_shaped = _is_heading_shaped_block(block)
                    if not heading_shaped:
                        if not (
                            RISK_FACTORS_PREFIX.search(block.text)
                            or RISK_FACTORS_HEADING.search(block.text)
                        ):
                            continue
                        is_prefix = True
                    else:
                        if not _contains_risk_factors(block.text):
                            continue
                    if idx in candidate_rules:
                        continue
                    if idx < TOC_HEAD_BLOCKS:
                        continue
                    if is_in_unsafe_zone(block_doc, idx):
                        continue
                    toc_score = score_window(blocks[idx : idx + TOC_SLICE_HEAD_BLOCKS])
                    toc_score = _adjust_toc_like(
                        blocks[idx : idx + TOC_SLICE_HEAD_BLOCKS], toc_score
                    )
                    if toc_score["tocLike"]:
                        if not (is_prefix and len(block.text) > HEADING_MAX_CHARS):
                            continue
                    add_candidate(idx, "risk_factors_prefix" if is_prefix else "risk_factors_heading")
    if not has_non_anchor_rule():
        for idx, block in enumerate(blocks):
            if not _is_heading_shaped_block(block):
                continue
            if _contains_risk_factors(block.text):
                add_candidate(idx, "risk_factors_heading")

    candidates: list[StartCandidate] = []
    continued_candidates = {
        idx for idx in candidate_rules if _has_continued_heading_near(blocks, idx)
    }
    non_continued_indices = sorted(
        idx for idx in candidate_rules if idx not in continued_candidates
    )
    first_non_continued = non_continued_indices[0] if non_continued_indices else None
    candidate_narrative: dict[int, bool] = {}
    for idx in candidate_rules:
        candidate_narrative[idx] = _has_nearby_narrative(blocks, idx)
    narrative_non_continued: list[int] = []
    for idx in non_continued_indices:
        if idx_item1_business is not None and idx < idx_item1_business:
            continue
        if candidate_narrative.get(idx, False):
            narrative_non_continued.append(idx)
    for idx, rule in candidate_rules.items():
        block = blocks[idx]
        toc_score = score_window(blocks[idx : idx + TOC_SLICE_HEAD_BLOCKS])
        toc_score = _adjust_toc_like(blocks[idx : idx + TOC_SLICE_HEAD_BLOCKS], toc_score)
        if _item_heading_followup(blocks, idx):
            toc_score = _force_toc_like(toc_score)
        in_unsafe_zone = is_in_unsafe_zone(block_doc, idx)
        is_strong_heading = _is_strong_item_heading(block.text)
        # Skip candidates in unsafe zones unless they have a strong Item 1A heading
        # (e.g., PG 2015 has financial summary data that triggers false TOC detection)
        if in_unsafe_zone and toc_detected and not is_strong_heading:
            continue
        prev_text = blocks[idx - 1].text if idx > 0 else None
        if is_strong_heading:
            prev_text = None
        cross_ref = _is_cross_ref_candidate(blocks, idx, prev_text)
        if form_type == "10-K" and rule not in (
            "item1a_risk_heading",
            "item1a_heading_followed_by_risk",
        ):
            if _candidate_has_item1_business_before_item1a(block_doc, idx, 8000):
                continue
        before_item1 = idx_item1_business is not None and idx < idx_item1_business
        warnings: list[str] = []
        repeated_header = _is_repeated_short_text(block.text, repeat_freq)
        if cross_ref and repeated_header:
            cross_ref = False
        if cross_ref:
            warnings.append("start_crossref_suspected")
        if toc_score["tocLike"]:
            warnings.append("toc_like_head")
        if repeated_header:
            warnings.append("header_footer_repeat")
        if before_item1 and form_type == "10-K":
            warnings.append("start_before_item1_business")
        if in_unsafe_zone and toc_detected:
            warnings.append("toc_detected")
        start_offset = block_doc.offsets[idx] if idx < len(block_doc.offsets) else 0
        lookahead_end = min(len(block_doc.full_text), start_offset + 6000)
        lookahead_text = block_doc.full_text[start_offset:lookahead_end]
        lookahead_bonus = _lookahead_bonus(lookahead_text) + _item1a_risk_adjacency_bonus(
            blocks, idx
        )
        strong_heading = _is_strong_item_heading(block.text)
        score = _score_start_candidate(
            rule,
            cross_ref,
            in_unsafe_zone,
            toc_score["tocLike"],
            before_item1,
            strong_heading,
            lookahead_bonus,
        )
        dense_followup = _dense_item_followup(blocks, idx)
        if dense_followup:
            warnings.append("toc_like_followup")
        risk_overview = _is_risk_overview_table(blocks, idx)
        if risk_overview:
            warnings.append("risk_overview_table")
        toc_entry = _is_toc_entry_candidate(blocks, idx)
        if toc_entry:
            warnings.append("toc_entry_page_num")
        if repeated_header:
            score = max(0.05, min(score - CANDIDATE_HEADER_REPEAT_PENALTY, 0.95))
        if risk_overview:
            score = max(0.05, min(score - CANDIDATE_OVERVIEW_TABLE_PENALTY, 0.95))
        if toc_entry:
            score = max(0.05, min(score - CANDIDATE_TOC_HEAD_PENALTY, 0.95))
        if dense_followup:
            score = max(0.05, min(score - CANDIDATE_FOLLOWUP_ITEM_PENALTY, 0.95))
        if toc_score["tocLike"]:
            toc_signal = (
                toc_score["pageNumBlocks"]
                + toc_score["itemCodeBlocks"]
                + toc_score["itemPrefixBlocks"]
                + toc_score["dotLeaderBlocks"]
                + toc_score["altPairs"]
            )
            if toc_signal > 0:
                toc_signal_penalty = min(
                    CANDIDATE_TOC_SIGNAL_MAX_PENALTY,
                    toc_signal * CANDIDATE_TOC_SIGNAL_PENALTY,
                )
                score = max(0.05, min(score - toc_signal_penalty, 0.95))
        continued_near = idx in continued_candidates
        if continued_near:
            warnings.append("continued_heading")
        if continued_near and first_non_continued is not None and idx > first_non_continued:
            score = max(0.05, min(score - CANDIDATE_CONTINUED_PENALTY, 0.95))
        if continued_near and narrative_non_continued:
            has_prior_narrative = False
            for prior_idx in narrative_non_continued:
                if prior_idx < idx:
                    has_prior_narrative = True
                    break
            if has_prior_narrative:
                score = max(
                    0.05, min(score - CANDIDATE_CONTINUED_NARRATIVE_PENALTY, 0.95)
                )
                warnings.append("continued_after_narrative")
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
                in_toc_region=in_unsafe_zone,
            )
        )

    selected: Optional[StartCandidate] = None
    if candidates:
        non_cross_ref = [candidate for candidate in candidates if not candidate.cross_ref]
        pool = non_cross_ref if non_cross_ref else candidates
        if non_cross_ref:
            non_cross_ref_non_toc = [
                candidate
                for candidate in non_cross_ref
                if not candidate.in_toc_region and not candidate.toc_score["tocLike"]
            ]
            if non_cross_ref_non_toc:
                # Prefer candidates that are not in TOC regions and not TOC-like
                pool = non_cross_ref_non_toc
            else:
                # Fall back to cross-ref candidates that are not in TOC regions
                cross_ref_non_toc = [
                    candidate
                    for candidate in candidates
                    if candidate.cross_ref
                    and not candidate.in_toc_region
                    and not candidate.toc_score["tocLike"]
                ]
                if cross_ref_non_toc:
                    pool = cross_ref_non_toc
        if toc_map is None:
            non_toc = [
                candidate
                for candidate in pool
                if not candidate.in_toc_region and not candidate.toc_score["tocLike"]
            ]
            if non_toc:
                pool = non_toc
        else:
            non_toc_region = [
                candidate for candidate in pool if not candidate.in_toc_region
            ]
            if non_toc_region:
                pool = non_toc_region
        if toc_detected and toc_region_end_idx is not None:
            after_toc = [candidate for candidate in pool if candidate.idx >= toc_region_end_idx]
            if after_toc:
                pool = after_toc
        if continued_candidates:
            continued_pool = [
                candidate for candidate in pool if candidate.idx in continued_candidates
            ]
            non_continued_pool = [
                candidate for candidate in pool if candidate.idx not in continued_candidates
            ]
            if continued_pool and non_continued_pool:
                best_continued = max(candidate.score for candidate in continued_pool)
                best_non_continued = max(candidate.score for candidate in non_continued_pool)
                if best_non_continued >= best_continued - CANDIDATE_CONTINUED_MARGIN:
                    pool = non_continued_pool
        if selected is None:
            strong_head = [
                candidate
                for candidate in pool
                if _is_strong_item_heading(blocks[candidate.idx].text)
            ]
            if toc_map is not None:
                toc_start = toc_map.get("risk_page_start")
                if isinstance(toc_start, int):
                    toc_start_int = toc_start
                    page_candidates: list[tuple[StartCandidate, int]] = []
                    for candidate in pool:
                        page_hint = _candidate_page_hint(
                            blocks,
                            candidate.idx,
                            exclude_ranges or None,
                            page_anchor=toc_start_int,
                        )
                        if page_hint is None:
                            continue
                        page_candidates.append((candidate, page_hint))
                    if page_candidates:
                        page_candidates_clean = [
                            item
                            for item in page_candidates
                            if not _STRUCTURAL_SUSPECT_WARNINGS.intersection(
                                item[0].warnings
                            )
                        ]
                        page_candidates_use = page_candidates
                        if page_candidates_clean:
                            best_all_distance = min(
                                abs(item[1] - toc_start_int) for item in page_candidates
                            )
                            best_clean_distance = min(
                                abs(item[1] - toc_start_int) for item in page_candidates_clean
                            )
                            if best_clean_distance <= best_all_distance:
                                page_candidates_use = page_candidates_clean
                        after = [item for item in page_candidates_use if item[1] >= toc_start_int]
                        if after:
                            after.sort(key=lambda item: (item[1], item[0].idx))
                            if (
                                abs(after[0][1] - toc_start_int)
                                <= CANDIDATE_TOC_PAGE_MAX_DELTA
                            ):
                                selected = after[0][0]
                        if selected is None:
                            page_candidates_use.sort(
                                key=lambda item: (
                                    abs(item[1] - toc_start_int),
                                    item[0].idx,
                                )
                            )
                            if (
                                abs(page_candidates_use[0][1] - toc_start_int)
                                <= CANDIDATE_TOC_PAGE_MAX_DELTA
                            ):
                                selected = page_candidates_use[0][0]
            if selected is not None:
                return {
                    "candidates": candidates,
                    "selected": selected,
                    "form_type": form_type,
                    "toc_score_doc_head": toc_score_doc_head,
                    "toc_region_end_idx": toc_region_end_idx,
                    "toc_regions": toc_regions,
                    "unsafe_regions": unsafe_regions,
                    "toc_map": toc_map,
                    "idx_part_i": idx_part_i,
                    "idx_item1_business": idx_item1_business,
                }
            if strong_head and toc_map is None:
                pool = strong_head
            pool.sort(key=lambda candidate: (-candidate.score, candidate.idx))
            best_score = pool[0].score
            near_tie_margin = CANDIDATE_NEAR_TIE_MARGIN
            if toc_map is not None and _toc_map_has_range(toc_map):
                near_tie_margin = max(near_tie_margin, CANDIDATE_NEAR_TIE_TOC_MARGIN)
            near_ties = [
                candidate for candidate in pool if best_score - candidate.score <= near_tie_margin
            ]
            if near_ties:
                if toc_map is not None:
                    toc_start = toc_map.get("risk_page_start")
                    if isinstance(toc_start, int):
                        toc_start_int = toc_start
                        best_candidate: Optional[StartCandidate] = None
                        best_distance: Optional[int] = None
                        best_over_toc: Optional[StartCandidate] = None
                        best_over_page: Optional[int] = None
                        clean_candidates: list[StartCandidate] = [
                            candidate
                            for candidate in near_ties
                            if not _STRUCTURAL_SUSPECT_WARNINGS.intersection(
                                candidate.warnings
                            )
                        ]
                        has_clean = False
                        if clean_candidates:
                            best_all_distance = None
                            best_clean_distance = None
                            for candidate in near_ties:
                                page_hint = _candidate_page_hint(
                                    blocks,
                                    candidate.idx,
                                    exclude_ranges or None,
                                    page_anchor=toc_start_int,
                                )
                                if page_hint is None:
                                    continue
                                distance = abs(page_hint - toc_start_int)
                                if best_all_distance is None or distance < best_all_distance:
                                    best_all_distance = distance
                            for candidate in clean_candidates:
                                page_hint = _candidate_page_hint(
                                    blocks,
                                    candidate.idx,
                                    exclude_ranges or None,
                                    page_anchor=toc_start_int,
                                )
                                if page_hint is None:
                                    continue
                                distance = abs(page_hint - toc_start_int)
                                if best_clean_distance is None or distance < best_clean_distance:
                                    best_clean_distance = distance
                            if best_clean_distance is not None and best_all_distance is not None:
                                if best_clean_distance <= best_all_distance:
                                    has_clean = True
                        for candidate in near_ties:
                            page_hint = _candidate_page_hint(
                                blocks,
                                candidate.idx,
                                exclude_ranges or None,
                                page_anchor=toc_start_int,
                            )
                            if page_hint is None:
                                continue
                            if has_clean and _STRUCTURAL_SUSPECT_WARNINGS.intersection(
                                candidate.warnings
                            ):
                                continue
                            if page_hint >= toc_start_int:
                                if (
                                    best_over_page is None
                                    or page_hint < best_over_page
                                    or (
                                        page_hint == best_over_page
                                        and best_over_toc is not None
                                        and candidate.idx < best_over_toc.idx
                                    )
                                ):
                                    best_over_page = page_hint
                                    best_over_toc = candidate
                            distance = abs(page_hint - toc_start_int)
                            if (
                                best_candidate is None
                                or best_distance is None
                                or distance < best_distance
                                or (distance == best_distance and candidate.idx < best_candidate.idx)
                            ):
                                best_candidate = candidate
                                best_distance = distance
                        if best_over_toc is not None:
                            selected = best_over_toc
                        elif best_candidate is not None:
                            selected = best_candidate
                if selected is None:
                    near_ties.sort(key=lambda candidate: (-candidate.score, candidate.idx))
                    selected = near_ties[0]
            else:
                selected = pool[0]

    return {
        "candidates": candidates,
        "selected": selected,
        "form_type": form_type,
        "toc_score_doc_head": toc_score_doc_head,
        "toc_region_end_idx": toc_region_end_idx,
        "toc_regions": toc_regions,
        "unsafe_regions": unsafe_regions,
        "toc_map": toc_map,
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
        for match in pattern.finditer(text, start_idx + 1):
            line_start = text.rfind("\n", 0, match.start())
            if line_start == -1:
                line_start = 0
            else:
                line_start += 1
            line_end = text.find("\n", match.start())
            if line_end == -1:
                line_end = len(text)
            line = text[line_start:line_end]
            if not _is_heading_shaped_text(line):
                continue
            idx = match.start()
            if end_idx is None or idx < end_idx:
                end_idx = idx
                end_marker = label
            break
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


def _first_non_empty_lines(text: str, count: int) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        lines.append(stripped)
        if len(lines) >= count:
            break
    return lines


def _last_non_empty_lines(text: str, count: int) -> list[str]:
    lines: list[str] = []
    for raw in reversed(text.splitlines()):
        stripped = raw.strip()
        if not stripped:
            continue
        lines.append(stripped)
        if len(lines) >= count:
            break
    lines.reverse()
    return lines


def _find_true_heading_offset_in_text(
    text: str, form_type: str, max_chars: int
) -> Optional[int]:
    offset = 0
    lines: list[tuple[str, int]] = []
    for raw in text.splitlines(True):
        stripped = raw.strip()
        if stripped:
            lines.append((stripped, offset))
        offset += len(raw)
        if offset > max_chars:
            break

    if not lines:
        return None

    if form_type == "20-F":
        heading_pattern = ITEM_3D_BLOCK
    else:
        heading_pattern = ITEM_1A_BLOCK

    for idx, (line, line_offset) in enumerate(lines):
        if not _is_heading_shaped_text(line):
            continue
        if not heading_pattern.search(line):
            continue
        if RISK_FACTORS.search(line) or D_RISK_FACTORS_BLOCK.search(line):
            return line_offset
        for look_idx in range(idx + 1, min(idx + 4, len(lines))):
            next_line, _ = lines[look_idx]
            if _is_heading_shaped_text(next_line) and RISK_FACTORS.search(next_line):
                return line_offset
    return None


def _is_end_marker_label(text: str, end_marker: Optional[str]) -> bool:
    if not end_marker:
        return False
    label = end_marker.lower()
    lowered = text.lower()
    if label == "1b":
        return "item 1b" in lowered
    if label == "1c":
        return "item 1c" in lowered
    if label == "2":
        return "item 2" in lowered
    if label == "4":
        return "item 4" in lowered
    if label == "4a":
        return "item 4a" in lowered
    if label == "4b":
        return "item 4b" in lowered
    if label == "part ii":
        return "part ii" in lowered
    if label == "item 7":
        return "item 7" in lowered
    if label == "item 8":
        return "item 8" in lowered
    if label == "md&a":
        return "management" in lowered
    if label == "financial statements":
        return "financial statements" in lowered
    if label == "notes":
        return "notes to consolidated financial statements" in lowered
    return False


def _later_item_tripwire(
    blocks: list[Block], form_type: str, end_marker: Optional[str]
) -> bool:
    if not blocks:
        return False
    last_idx = len(blocks) - 1
    tail_start = max(0, len(blocks) - LATER_TRIPWIRE_TAIL_BLOCKS)
    for idx in range(tail_start, len(blocks)):
        text = blocks[idx].text.strip()
        if not text:
            continue
        normalized = _normalize_heading_candidate(text)
        if idx == last_idx and _is_end_marker_label(normalized, end_marker):
            continue
        if CROSS_REF_TERMS.search(normalized):
            continue
        if re.search(r"\s\d{1,4}$", normalized):
            continue
        if not _is_heading_shaped_text(normalized):
            continue
        lowered = normalized.lower()
        if form_type == "20-F":
            if re.match(r"item\s*4[ab]?\b", lowered) or re.match(r"item\s*5\b", lowered):
                return True
            continue
        if re.match(r"item\s*7[a]?\b", lowered) or re.match(r"item\s*8\b", lowered):
            return True
        if re.match(r"part\s+ii\b", lowered):
            return True
        if re.match(r"management'?s discussion and analysis", lowered):
            return True
        if re.match(r"financial statements\b", lowered):
            return True
        if re.match(r"notes to consolidated financial statements\b", lowered):
            return True
    return False


def _risk_word_density(text: str) -> float:
    if not text:
        return 0.0
    words = re.findall(r"[a-z]+", text.lower())
    if not words:
        return 0.0
    count = 0
    for word in words:
        if word in RISK_BURST_TERMS:
            count += 1
    chars = max(len(text), 1)
    return count / (chars / 1000.0)


def _lookahead_bonus(text: str) -> float:
    bonus = 0.0
    density = _risk_word_density(text)
    if density >= 6:
        bonus += 0.12
    elif density >= 4:
        bonus += 0.08
    elif density >= 2:
        bonus += 0.04
    if RISK_RELATED_SUBHEAD.search(text):
        bonus += 0.05
    return bonus


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


def _toc_map_debug_fields(toc_map: Optional[TocMap]) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "tocNextLabel": None,
        "tocNextItemCode": None,
        "tocRiskPage": None,
        "tocRiskRange": None,
    }
    if toc_map is None:
        return fields
    risk_start = toc_map.get("risk_page_start")
    risk_end = toc_map.get("risk_page_end")
    if isinstance(risk_start, int):
        fields["tocRiskPage"] = risk_start
    if isinstance(risk_start, int) and isinstance(risk_end, int):
        fields["tocRiskRange"] = {"start": risk_start, "end": risk_end}
    fields["tocNextLabel"] = toc_map.get("next_label")
    fields["tocNextItemCode"] = toc_map.get("next_item_code")
    return fields


def extract_item1a_from_blockdoc(
    block_doc: BlockDoc,
) -> tuple[str, float, str, list[str], dict[str, Any]]:
    analysis = analyze_blockdoc_candidates(block_doc)
    candidates = cast(list[StartCandidate], analysis.get("candidates", []))
    selected = cast(Optional[StartCandidate], analysis.get("selected"))
    toc_map = cast(Optional[TocMap], analysis.get("toc_map") or block_doc.toc_map)
    toc_debug_fields = _toc_map_debug_fields(toc_map)

    toc_score_doc = cast(TocScore, analysis.get("toc_score_doc_head"))
    toc_detected = bool(analysis.get("toc_regions")) or toc_score_doc.get("tocLike", False)

    debug_meta: dict[str, Any] = {
        "lengthChars": 0,
        "endMarkerUsed": None,
        "hasItem1C": False,
        "startMarker": None,
        "tocDetected": False,
        "tocRemoved": False,
    }
    debug_meta.update(toc_debug_fields)

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
            "tocRegions": analysis.get("toc_regions"),
            "unsafeRegions": analysis.get("unsafe_regions"),
            "tocMap": toc_map,
            "idxPartI": analysis.get("idx_part_i"),
            "idxItem1Business": analysis.get("idx_item1_business"),
        }
        return "", 0.0, "blockdoc_not_found", ["item1a_not_found"], debug_meta

    form_type = cast(str, analysis.get("form_type", "10-K"))
    toc_region_end_idx = analysis.get("toc_region_end_idx")
    toc_page_end: Optional[int] = None
    if form_type == "10-K":
        toc_page_end = _extract_toc_risk_page_end(block_doc.blocks)
    start_offset = block_doc.offsets[selected.idx]
    if toc_map is None and is_in_unsafe_zone(block_doc, selected.idx):
        block_doc.unsafe_regions = [
            region for region in block_doc.unsafe_regions if region.get("kind") != "toc_head"
        ]
        block_doc.toc_regions = [
            region for region in block_doc.toc_regions if region.get("kind") != "toc_head"
        ]
        toc_detected = False
    end_block_idx: Optional[int]
    end_marker: Optional[str]
    end_block_idx, end_marker, end_fallback = find_end_marker_blockdoc(
        block_doc, selected.idx, form_type
    )
    if toc_page_end is not None:
        page_end_idx = _find_end_by_page_header(block_doc.blocks, selected.idx, toc_page_end)
        if page_end_idx is not None and not _end_marker_distance_ok(
            block_doc, selected.idx, page_end_idx
        ):
            page_end_idx = None
        if page_end_idx is not None:
            allow_override = False
            has_primary_end = end_block_idx is not None and not end_fallback
            heading_end = False
            if (
                isinstance(end_block_idx, int)
                and isinstance(end_marker, str)
                and not is_in_unsafe_zone(block_doc, end_block_idx)
            ):
                normalized = _normalize_heading_label(end_marker)
                if normalized in NEXT_SECTION_LABELS:
                    heading_end = True
            if not has_primary_end:
                allow_override = not heading_end
                if (
                    heading_end
                    and isinstance(end_block_idx, int)
                    and (end_block_idx - page_end_idx) > 200
                ):
                    allow_override = True
            elif isinstance(toc_region_end_idx, int) and isinstance(end_block_idx, int) and end_block_idx < toc_region_end_idx:
                allow_override = True
            elif isinstance(end_block_idx, int) and is_in_unsafe_zone(block_doc, end_block_idx):
                normalized = _normalize_heading_candidate(block_doc.blocks[end_block_idx].text)
                if (
                    _end_marker_toc_like(block_doc.blocks, end_block_idx)
                    or _is_toc_line(normalized)
                    or _is_page_number_line(normalized)
                ):
                    allow_override = True
            elif (
                not has_primary_end
                and toc_region_end_idx is None
                and isinstance(end_block_idx, int)
                and _end_marker_toc_like(block_doc.blocks, end_block_idx)
            ):
                allow_override = True
            if allow_override:
                end_block_idx = page_end_idx
                end_marker = "toc_page_end"
                end_fallback = True
    # -- Boundary refinement via "Risk factors (continued)" pattern -----------
    # When the start marker is a bare "risk_factors_heading" (non-standard body
    # structure, e.g. ASML 20-F) and the end marker is a fallback or missing,
    # try to find the end by detecting the page break that leaves the Risk
    # Factors section (first page header not followed by "Risk factors
    # (continued)").  The helper self-gates: if the filing doesn't use the
    # "Risk factors (continued)" page-header pattern, it returns None.
    if (end_fallback or end_block_idx is None) and selected.rule in (
        "risk_factors_heading",
        "risk_factors_prefix",
    ):
        rf_boundary = _find_rf_continued_boundary(block_doc.blocks, selected.idx)
        if rf_boundary is not None and _end_marker_distance_ok(
            block_doc, selected.idx, rf_boundary
        ):
            if end_block_idx is None or rf_boundary < end_block_idx:
                end_block_idx = rf_boundary
                end_marker = "rf_continued_boundary"
                end_fallback = False  # high-confidence structural signal

    end_fallback_for_conf = end_fallback
    if end_fallback and toc_map is not None and isinstance(end_marker, str):
        next_label = toc_map.get("next_label")
        if isinstance(next_label, str):
            if _normalize_heading_label(next_label) == _normalize_heading_label(end_marker):
                end_fallback_for_conf = False
    warnings: list[str] = list(selected.warnings)
    end_idx: Optional[int] = None

    if end_block_idx is None:
        end_idx = min(start_offset + 80000, len(block_doc.full_text))
        warnings.append("end_not_found")
        slice_blocks = _slice_blocks_by_offset(block_doc, selected.idx, end_idx)
        slice_end_idx = selected.idx + len(slice_blocks) - 1 if slice_blocks else selected.idx
    else:
        effective_end_block_idx = end_block_idx
        if end_marker is not None and end_marker != "toc_page_end":
            effective_end_block_idx = max(selected.idx, end_block_idx - 1)
        end_idx = block_doc.offsets[effective_end_block_idx]
        if end_fallback_for_conf:
            warnings.append("end_fallback_used")
        slice_blocks = block_doc.blocks[selected.idx : effective_end_block_idx + 1]
        slice_end_idx = effective_end_block_idx

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
    # Note: toc_like_head warning is added later after strong_head_near check (line ~5233)

    start_blocks = cleaned_blocks[: min(len(cleaned_blocks), START_PURITY_BLOCKS)]
    start_crossref_like = _start_crossref_like(start_blocks)

    tail_blocks = cleaned_blocks[-min(len(cleaned_blocks), TOC_TAIL_BLOCKS) :]
    tail_toc_score = score_toc_window(tail_blocks) if tail_blocks else slice_toc_score
    toc_like_tail = False
    if tail_blocks:
        if tail_toc_score["tocLike"]:
            toc_like_tail = True
        else:
            tail_signal = (
                tail_toc_score["pageNumBlocks"]
                + tail_toc_score["itemCodeBlocks"]
                + tail_toc_score["dotLeaderBlocks"]
            )
            if tail_signal >= TOC_STRONG_SIGNAL_MIN:
                toc_like_tail = True
    if toc_like_tail:
        warnings.append("toc_like_tail")

    toc_range_mismatch = False
    end_marker_label = ""
    end_is_item1c = False
    if isinstance(end_marker, str):
        end_marker_label = _normalize_heading_label(end_marker)
        end_is_item1c = end_marker_label in {"cybersecurity", "item 1c cybersecurity"}
    toc_regions = analysis.get("toc_regions", [])
    idx_item1_business = analysis.get("idx_item1_business")
    exclude_ranges = _build_toc_exclude_ranges(
        toc_regions, idx_item1_business if isinstance(idx_item1_business, int) else None
    )
    section_page_range = _section_page_range_with_context(
        block_doc.blocks, selected.idx, slice_end_idx, exclude_ranges or None
    )
    if section_page_range is None:
        section_page_range = _section_page_range(cleaned_blocks)
    if section_page_range is not None and toc_map is not None:
        section_page_range = _apply_toc_range_hint(section_page_range, toc_map)
        next_start = _next_start_from_toc(toc_map)
        if isinstance(next_start, int):
            marker_idx = end_block_idx if isinstance(end_block_idx, int) else slice_end_idx
            end_marker_page = _candidate_page_hint(
                block_doc.blocks, marker_idx, exclude_ranges or None, page_anchor=next_start
            )
            if end_marker_page == next_start:
                section_page_range = (section_page_range[0], next_start)
    toc_range_start: Optional[int] = None
    toc_range_end: Optional[int] = None
    if toc_map is not None:
        toc_range_start = toc_map.get("risk_page_start")
        toc_range_end = toc_map.get("risk_page_end")
    if (
        section_page_range is not None
        and isinstance(toc_range_start, int)
        and isinstance(toc_range_end, int)
    ):
        toc_region_kind = None
        if toc_map is not None:
            toc_region_kind = toc_map.get("region_kind")
        toc_range_end_effective = toc_range_end
        inferred_end: Optional[int] = None
        start_only_checked = False
        if toc_range_end == toc_range_start:
            if section_page_range[0] != toc_range_start:
                toc_range_mismatch = True
                warnings.append("toc_range_mismatch")
            next_start: Optional[int] = None
            next_row_text = toc_map.get("next_row_text") if toc_map is not None else None
            if isinstance(next_row_text, str):
                parsed = _parse_toc_page_number(next_row_text)
                if parsed is None:
                    parsed_row = _parse_toc_row_line(next_row_text)
                    if parsed_row is not None:
                        parsed = (parsed_row[2], parsed_row[3])
                if parsed is not None and parsed[0] > toc_range_start:
                    next_start = parsed[0]
            if isinstance(next_start, int):
                start_only_checked = True
                allowed_end = {next_start, next_start - 1}
                if (
                    end_is_item1c
                    and section_page_range[0] == toc_range_start
                    and section_page_range[1] < next_start
                ):
                    toc_range_end_effective = section_page_range[1]
                    toc_range_end = section_page_range[1]
                    if toc_map is not None:
                        toc_map["risk_page_end"] = section_page_range[1]
                elif section_page_range[1] in allowed_end and section_page_range[0] == toc_range_start:
                    toc_range_end_effective = section_page_range[1]
                    toc_range_end = section_page_range[1]
                    if toc_map is not None:
                        toc_map["risk_page_end"] = section_page_range[1]
                else:
                    if not toc_range_mismatch:
                        toc_range_mismatch = True
                        warnings.append("toc_range_mismatch")
        if not start_only_checked:
            if toc_range_end == toc_range_start:
                if section_page_range[0] != toc_range_start:
                    toc_range_mismatch = True
                    warnings.append("toc_range_mismatch")
                next_row_text = toc_map.get("next_row_text") if toc_map is not None else None
                if isinstance(next_row_text, str):
                    parsed = _parse_toc_page_number(next_row_text)
                    if parsed is None:
                        parsed_row = _parse_toc_row_line(next_row_text)
                        if parsed_row is not None:
                            parsed = (parsed_row[2], parsed_row[3])
                    if parsed is not None and parsed[0] > toc_range_start:
                        inferred_end = parsed[0]
                if isinstance(toc_page_end, int) and toc_page_end >= toc_range_end:
                    if inferred_end is None:
                        inferred_end = toc_page_end
                    else:
                        inferred_end = max(inferred_end, toc_page_end)
                if inferred_end is not None:
                    toc_range_end_effective = inferred_end
            if (
                toc_range_end == toc_range_start
                and toc_region_kind == "xref_index"
                and toc_map is not None
                and not toc_map.get("next_row_text")
            ):
                skip_mismatch = True
            else:
                skip_mismatch = toc_range_end == toc_range_start and section_page_range[1] < (
                    toc_range_start - TOC_RANGE_TOLERANCE
                )
            if (section_page_range[1] - section_page_range[0]) > 200:
                skip_mismatch = True
            if not skip_mismatch and (
                section_page_range[0] < (toc_range_start - TOC_RANGE_TOLERANCE)
                or section_page_range[1] > (toc_range_end_effective + TOC_RANGE_TOLERANCE)
            ):
                toc_range_mismatch = True
                warnings.append("toc_range_mismatch")

    strong_head_near = _strong_heading_in_head(cleaned_blocks, form_type, STRONG_HEAD_SCAN_BLOCKS)
    if start_crossref_like and strong_head_near:
        start_crossref_like = False
    if start_crossref_like:
        warnings.append("start_crossref_like")
    first_heading_offset = _find_true_heading_offset_in_text(section, form_type, 50000)
    early_heading_offset = (
        first_heading_offset if first_heading_offset is not None and first_heading_offset <= 2000 else None
    )
    later_tripwire = _later_item_tripwire(cleaned_blocks, form_type, end_marker)
    early_penalty_relief = 0.0
    if (
        "early_position_penalty" in warnings
        and toc_removed
        and _item1a_risk_adjacency_bonus(block_doc.blocks, selected.idx) > 0
        and early_heading_offset is not None
    ):
        early_penalty_relief = EARLY_PENALTY_RELIEF
        warnings.append("early_penalty_relief")
    # Suppress toc_like_head penalty when there's a strong Item 1A / Risk Factors heading
    toc_like_head_effective = slice_toc_score["tocLike"] and not strong_head_near
    score = _apply_confidence_adjustments(
        score=score,
        toc_like_head=toc_like_head_effective,
        toc_removed=toc_removed,
        end_fallback=end_fallback_for_conf,
        end_not_found="end_not_found" in warnings,
        slice_len=len(section),
        cross_ref_suspected=selected.cross_ref,
        strong_heading_near=strong_head_near,
        start_crossref_like=start_crossref_like,
        toc_like_tail=toc_like_tail,
        toc_range_mismatch=toc_range_mismatch,
        early_penalty_relief=early_penalty_relief,
    )
    breakdown["startPurityPenalty"] = -CONF_PENALTY_START_PURITY if start_crossref_like else 0.0
    breakdown["tocTailPenalty"] = -CONF_PENALTY_TOC_LIKE_TAIL if toc_like_tail else 0.0
    breakdown["tocRangePenalty"] = -CONF_PENALTY_TOC_RANGE_MISMATCH if toc_range_mismatch else 0.0
    breakdown["earlyPenaltyRelief"] = early_penalty_relief
    breakdown["finalScore"] = score

    quality_gate_failed = False
    gate_reasons: list[str] = []
    if slice_toc_score["tocLike"] and not strong_head_near:
        quality_gate_failed = True
        warnings.append("toc_like_head")
        if early_heading_offset is None:
            gate_reasons.append("start_in_toc_region")

    if form_type == "10-K" and _business_before_item1a(cleaned_blocks):
        quality_gate_failed = True
        warnings.append("business_heading_inside_slice")
        gate_reasons.append("business_heading_inside_slice")

    if "end_not_found" in warnings and len(section) > MAX_SLICE_CHARS_REASONABLE:
        quality_gate_failed = True
        gate_reasons.append("end_not_found_spill")

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
                if "start_in_toc_region" not in gate_reasons:
                    gate_reasons.append("start_in_toc_region")
    if toc_like_tail:
        tail_signal = (
            tail_toc_score["pageNumBlocks"]
            + tail_toc_score["itemCodeBlocks"]
            + tail_toc_score["dotLeaderBlocks"]
        )
        narrative_tail = _narrative_blocks_in_head(tail_blocks, min(len(tail_blocks), 20))
        if tail_signal >= TOC_STRONG_SIGNAL_MIN and narrative_tail < 2:
            quality_gate_failed = True
            gate_reasons.append("toc_like_tail")

    if form_type == "20-F":
        idx_item3 = analysis.get("idx_item3")
        idx_item4 = analysis.get("idx_item4")
        if isinstance(idx_item3, int):
            if selected.idx < idx_item3:
                quality_gate_failed = True
                warnings.append("anchor_low_confidence")
                gate_reasons.append("anchor_outside_item3")
            if isinstance(idx_item4, int) and selected.idx >= idx_item4:
                quality_gate_failed = True
                warnings.append("anchor_low_confidence")
                gate_reasons.append("anchor_outside_item3")

    if first_heading_offset is not None and first_heading_offset > 20000:
        quality_gate_failed = True
        gate_reasons.append("start_heading_late")

    if later_tripwire:
        quality_gate_failed = True
        warnings.append("drift_into_later_items")
        gate_reasons.append("later_item_tripwire")

    if form_type == "10-K" and len(section) < 1200:
        if ITEM_1A_BLOCK.search(section) and (ITEM_1B_BLOCK.search(section) or end_marker == "1B"):
            quality_gate_failed = True
            if "length_out_of_band" not in warnings:
                warnings.append("length_out_of_band")
            gate_reasons.append("length_out_of_band")

    if form_type == "20-F" and len(section) < 2000:
        quality_gate_failed = True
        if "length_out_of_band" not in warnings:
            warnings.append("length_out_of_band")
        gate_reasons.append("length_out_of_band")

    if toc_map is not None and "length_out_of_band" in warnings:
        risk_start = toc_map.get("risk_page_start")
        risk_end = toc_map.get("risk_page_end")
        if isinstance(risk_start, int) and isinstance(risk_end, int):
            if 0 <= (risk_end - risk_start) <= SHORT_TOC_PAGE_SPAN_MAX:
                warnings = [warning for warning in warnings if warning != "length_out_of_band"]
    if "length_out_of_band" in warnings and len(section) >= 10000:
        warnings = [warning for warning in warnings if warning != "length_out_of_band"]

    warnings = _dedupe_warnings(warnings)

    gate_reasons = _dedupe_warnings(gate_reasons)
    status = "PASS"
    if quality_gate_failed:
        status = "FAIL"
    else:
        strong_start = early_heading_offset is not None
        strong_end = end_marker is not None and "end_not_found" not in warnings
        if "length_out_of_band" in warnings and strong_start and strong_end:
            status = "REVIEW"
            gate_reasons.append("length_out_of_band")
        elif toc_detected and not slice_toc_score["tocLike"] and not toc_removed:
            status = "REVIEW"
            gate_reasons.append("toc_present_in_filing")
        elif "end_fallback_used" in warnings and not later_tripwire:
            status = "REVIEW"
            gate_reasons.append("end_fallback_used")

    if status == "FAIL" or quality_gate_failed:
        score = min(score, 0.25)

    has_item1c = bool(ITEM1C_HEADING.search(block_doc.full_text)) if form_type == "10-K" else False
    selected_end: Optional[dict[str, Any]] = None
    if end_block_idx is not None:
        selected_end = {
            "idx": end_block_idx,
            "rule": end_marker,
            "headPreview": block_doc.blocks[end_block_idx].text[:160],
        }

    first_lines = _first_non_empty_lines(section, 5)
    last_lines = _last_non_empty_lines(section, 5)
    start_snippet = selected.head_preview[:120]
    end_snippet = block_doc.blocks[end_block_idx].text[:120] if end_block_idx is not None else None

    debug_meta = {
        "lengthChars": len(section),
        "endMarkerUsed": end_marker,
        "hasItem1C": has_item1c,
        "startMarker": selected.rule,
        "tocDetected": toc_detected_slice or toc_detected,
        "tocRemoved": toc_removed,
        "qualityGateFailed": quality_gate_failed,
        "status": status,
        "gateReasons": gate_reasons,
        "startSnippet": start_snippet,
        "endSnippet": end_snippet,
        "firstLines": first_lines,
        "lastLines": last_lines,
        "candidateCount": len(candidates),
        "topCandidates": debug_candidates[:3],
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
            "sliceEndIdx": slice_end_idx,
            "tocScoreDocHead": toc_score_doc,
            "tocRegions": analysis.get("toc_regions"),
            "unsafeRegions": analysis.get("unsafe_regions"),
            "tocMap": toc_map,
            "tocScoreSliceHead": slice_toc_score,
            "tocScoreSliceTail": tail_toc_score,
            "startCrossrefLike": start_crossref_like,
            "tocRangeMismatch": toc_range_mismatch,
            "sectionPageRange": section_page_range,
            "tocPageEnd": toc_page_end,
            "idxPartI": analysis.get("idx_part_i"),
            "idxItem1Business": analysis.get("idx_item1_business"),
        },
    }
    debug_meta.update(toc_debug_fields)
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


def extract_item1a_from_prepared(
    prepared: PreparedHtml,
) -> tuple[str, float, str, list[str], dict[str, Any]]:
    """Extract Item 1A from pre-parsed HTML components.

    This is the efficient version that avoids redundant HTML parsing.
    Use this when you have already called prepare_html_for_extraction().

    Args:
        prepared: PreparedHtml containing soup, block_tags, and block_doc.

    Returns:
        Tuple of (section_text, confidence, method, warnings, debug_meta).
    """
    if prepared.block_doc.blocks:
        section, confidence, method, block_warnings, debug_meta = extract_item1a_from_blockdoc(
            prepared.block_doc
        )
        if method != "blockdoc_not_found":
            return section, confidence, method, block_warnings, debug_meta

    # Fallback: extract text directly from soup (avoids re-parsing HTML)
    text = prepared.soup.get_text(separator="\n")
    text = normalize_whitespace(text)
    return extract_item1a_from_text(text)


def extract_item1a_from_html(
    html: str,
) -> tuple[str, float, str, list[str], dict[str, Any]]:
    """Extract Item 1A from raw HTML.

    This function parses the HTML internally. For better performance when
    multiple operations need the parsed HTML, use prepare_html_for_extraction()
    followed by extract_item1a_from_prepared().

    Args:
        html: Raw HTML string from SEC filing.

    Returns:
        Tuple of (section_text, confidence, method, warnings, debug_meta).
    """
    prepared = prepare_html_for_extraction(html)
    return extract_item1a_from_prepared(prepared)


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
