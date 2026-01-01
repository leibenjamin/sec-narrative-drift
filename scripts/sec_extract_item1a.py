import argparse
import re
import warnings
from pathlib import Path
from typing import Any, Optional

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning


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


def choose_parser(html: str) -> str:
    head = html.lstrip()[:200].lower()
    if head.startswith("<?xml") or re.match(r"\s*<xbrl", head):
        return "lxml-xml"
    return "lxml"


def clean_html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, choose_parser(html))

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    for tag in soup.find_all(BLOCK_TAGS):
        if tag.name == "br":
            tag.replace_with("\n")
        else:
            tag.append("\n")

    text = soup.get_text(separator="\n")
    return normalize_whitespace(text)


def split_paragraphs(text: str, min_chars: int = 200) -> list[str]:
    paragraphs = [chunk.strip() for chunk in re.split(r"\n{2,}", text) if chunk.strip()]
    return [para for para in paragraphs if len(para) >= min_chars]


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
    ("1C", re.compile(r"(?m)(^|\n\n+)\s*item\s*1\s*\.?\s*c\b", re.IGNORECASE)),
    ("1B", re.compile(r"(?m)(^|\n\n+)\s*item\s*1\s*\.?\s*b\b", re.IGNORECASE)),
    ("2", re.compile(r"(?m)(^|\n\n+)\s*item\s*2\b", re.IGNORECASE)),
]
END_MARKERS_20F: list[tuple[str, re.Pattern[str]]] = [
    ("4A", re.compile(r"(?m)(^|\n\n+)\s*item\s*4\s*a\b", re.IGNORECASE)),
    ("4B", re.compile(r"(?m)(^|\n\n+)\s*item\s*4\s*b\b", re.IGNORECASE)),
    ("4", re.compile(r"(?m)(^|\n\n+)\s*item\s*4\b", re.IGNORECASE)),
]
RISK_FACTORS = re.compile(r"\brisk\s+factors?\b", re.IGNORECASE)
RISK_FACTORS_SLOPPY = re.compile(
    r"r\s*i\s*s\s*k\s+f\s*a\s*c\s*t\s*o\s*r\s*s", re.IGNORECASE
)
RISK_FACTORS_HEADING = re.compile(r"(?m)^\s*risk\s+factors?\b", re.IGNORECASE)
HEADING_LINE = re.compile(r"^(item\s+\d|risk factors|part\s+[ivx]+)\b", re.IGNORECASE)
MODAL_TERMS = ("may", "could", "adversely")


def _heading_start_index(match: re.Match[str]) -> int:
    token = match.group(0).lower()
    rel = token.rfind("item")
    if rel < 0:
        return match.start()
    return match.start() + rel


def _find_anchor_start(
    text: str, anchor_text: str, heading_pattern: re.Pattern[str] = ITEM1A_RISK_HEADING
) -> Optional[int]:
    heading_match = heading_pattern.search(text)
    if heading_match:
        return heading_match.start()
    if not anchor_text:
        return None
    lowered = text.lower()
    anchor_lower = re.sub(r"\s+", " ", anchor_text.strip().lower())
    if not anchor_lower:
        return None
    idx = lowered.find(anchor_lower)
    if idx >= 0:
        return idx
    return None


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


def _toc_cluster_penalty(section_head: str) -> bool:
    lines = [line.strip() for line in section_head.splitlines() if line.strip()]
    count = 0
    for line in lines[:30]:
        if re.match(r"^item\s+\d", line, re.IGNORECASE):
            count += 1
    return count >= 4


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
    if doc_length > 0 and start_idx < (doc_length * 0.08):
        early_penalty = -0.15
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


def extract_item1a_from_text(
    text: str,
) -> tuple[str, float, str, list[str], dict[str, Any]]:
    warnings: list[str] = []
    doc_length = len(text)
    has_item1c = bool(ITEM1C_HEADING.search(text))

    candidates: list[int] = []
    candidate_set: set[int] = set()
    found_item1a = False
    found_20f = False

    def add_candidate(start_idx: int) -> None:
        if start_idx in candidate_set:
            return
        candidate_set.add(start_idx)
        candidates.append(start_idx)

    for match in ITEM1A_HEADING.finditer(text):
        start_idx = _heading_start_index(match)
        window = text[start_idx : start_idx + 400]
        if not _contains_risk_factors(window):
            continue
        add_candidate(start_idx)
        found_item1a = True

    end_markers = END_MARKERS_10K
    if not candidates:
        for match in ITEM3D_HEADING.finditer(text):
            start_idx = _heading_start_index(match)
            window = text[start_idx : start_idx + 400]
            if not _contains_risk_factors(window):
                continue
            add_candidate(start_idx)
        if candidates:
            found_20f = True
        else:
            for match in ITEM3_HEADING.finditer(text):
                start_idx = _heading_start_index(match)
                risk_match = RISK_FACTORS_HEADING.search(text, start_idx)
                if not risk_match:
                    continue
                if (risk_match.start() - start_idx) > 20000:
                    continue
                add_candidate(risk_match.start())
            if candidates:
                found_20f = True

    for match in RISK_FACTORS_HEADING.finditer(text):
        line_end = text.find("\n", match.start())
        line = text[match.start() : line_end if line_end != -1 else len(text)]
        if len(line.strip()) > 80:
            continue
        add_candidate(match.start())

    if found_20f:
        end_markers = END_MARKERS_20F
    elif not found_item1a:
        has_10k_marker = any(pattern.search(text) for _, pattern in END_MARKERS_10K)
        end_markers = END_MARKERS_10K if has_10k_marker else END_MARKERS_20F
    else:
        end_markers = END_MARKERS_10K

    best: Optional[dict[str, Any]] = None
    for start_idx in candidates:
        end_idx, end_marker = _find_end_marker(text, start_idx, end_markers)
        penalty = 0.0
        local_warnings: list[str] = []
        if end_idx is None:
            end_idx = min(start_idx + 80000, doc_length)
            local_warnings.append("end_not_found")
            penalty = -0.2
        section = text[start_idx:end_idx].strip()
        score, breakdown, score_warnings = _score_candidate(text, start_idx, end_idx, doc_length)
        score = max(0.05, min(score + penalty, 0.95))
        breakdown["endNotFoundPenalty"] = penalty
        if local_warnings:
            score_warnings.extend(local_warnings)
        candidate = {
            "section": section,
            "confidence": score,
            "endMarkerUsed": end_marker,
            "warnings": score_warnings,
            "scoreBreakdown": breakdown,
            "lengthChars": len(section),
        }
        if not best or candidate["confidence"] > best["confidence"]:
            best = candidate

    if best:
        warnings.extend(best["warnings"])
        debug_meta = {
            "lengthChars": best["lengthChars"],
            "endMarkerUsed": best["endMarkerUsed"],
            "hasItem1C": has_item1c,
            "scoreBreakdown": best["scoreBreakdown"],
        }
        return best["section"], best["confidence"], "text_scored", warnings, debug_meta

    risk_match = RISK_FACTORS.search(text) or RISK_FACTORS_SLOPPY.search(text)
    if risk_match:
        start_idx = risk_match.start()
        end_idx, end_marker = _find_end_marker(text, start_idx, end_markers)
        if end_idx is None:
            end_idx = min(start_idx + 80000, doc_length)
            warnings.append("end_not_found")
        warnings.append("fallback_risk_word_only")
        section = text[start_idx:end_idx].strip()
        debug_meta = {
            "lengthChars": len(section),
            "endMarkerUsed": end_marker,
            "hasItem1C": has_item1c,
        }
        return section, 0.35, "risk_factors_fallback", warnings, debug_meta

    debug_meta = {"lengthChars": 0, "endMarkerUsed": None, "hasItem1C": has_item1c}
    return "", 0.0, "not_found", ["item1a_not_found"], debug_meta


def extract_item1a_from_html(
    html: str,
) -> tuple[str, float, str, list[str], dict[str, Any]]:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(html, "lxml")
    anchor_warnings: list[str] = []

    anchor_links: list[tuple[Any, bool]] = []
    soup_any: Any = soup
    raw_links: Any = soup_any.find_all("a")
    for link in list(raw_links):
        text = safe_get_text(link).lower()
        if ANCHOR_ITEM1A.search(text):
            anchor_links.append((link, False))
            continue
        if ANCHOR_ITEM3D.search(text) or ANCHOR_ITEM3.search(text):
            anchor_links.append((link, True))
            continue
        if "risk factors" in text:
            anchor_links.append((link, False))

    text = clean_html_to_text(html)
    for link, is_item3d in anchor_links:
        href = safe_get_attr(link, "href") or ""
        if not href.startswith("#") or len(href) <= 1:
            continue
        anchor_id = href[1:]
        target = soup_any.find(id=anchor_id) or soup_any.find(attrs={"name": anchor_id})
        if target is None:
            continue
        anchor_text = safe_get_text(target) or safe_get_text(link)
        heading_pattern = ITEM3_RISK_HEADING if is_item3d else ITEM1A_RISK_HEADING
        start_idx = _find_anchor_start(text, anchor_text, heading_pattern)
        if start_idx is None:
            continue
        end_markers = END_MARKERS_20F if is_item3d else END_MARKERS_10K
        end_idx, end_marker = _find_end_marker(text, start_idx, end_markers)
        local_warnings: list[str] = []
        confidence = 0.9
        if end_idx is None:
            end_idx = min(start_idx + 80000, len(text))
            local_warnings.append("end_not_found")
            confidence -= 0.2
        section = text[start_idx:end_idx].strip()
        if len(section) < 8000:
            local_warnings.append("length_out_of_band")
            confidence -= 0.15
        if len(text) > 0 and start_idx < (len(text) * 0.08):
            local_warnings.append("early_position_penalty")
            confidence -= 0.1
        if _toc_cluster_penalty(section[:2500]):
            local_warnings.append("toc_cluster_penalty")
            confidence -= 0.15
        confidence = max(0.1, min(confidence, 0.95))
        if confidence < 0.5 or len(section) < 8000:
            if "anchor_low_confidence" not in anchor_warnings:
                anchor_warnings.append("anchor_low_confidence")
            continue
        debug_meta = {
            "lengthChars": len(section),
            "endMarkerUsed": end_marker,
            "hasItem1C": bool(ITEM1C_HEADING.search(text)) if not is_item3d else False,
        }
        return section, confidence, "html_anchor", local_warnings, debug_meta

    anchor_warnings.append("anchor_missing")
    section, confidence, method, result_warnings, debug_meta = extract_item1a_from_text(text)
    result_warnings = anchor_warnings + result_warnings
    return section, confidence, method, result_warnings, debug_meta


def extract_item_1a(text: str) -> tuple[str, float, str, list[str]]:
    section, confidence, method, warnings, _debug = extract_item1a_from_text(text)
    return section, confidence, method, warnings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract Item 1A from a fixture HTML file.")
    parser.add_argument("--fixture", required=True, help="Path to fixture HTML file.")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    html = Path(args.fixture).read_text(encoding="utf-8", errors="replace")
    section, confidence, method, warnings, debug_meta = extract_item1a_from_html(html)
    paragraphs = split_paragraphs(section)

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
