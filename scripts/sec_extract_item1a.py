import argparse
import re
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup


BLOCK_TAGS = {
    "p",
    "div",
    "br",
    "li",
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

    for tag in soup.find_all("table"):
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


def extract_item_1a(text: str) -> tuple[str, float, str, list[str]]:
    errors: list[str] = []
    start_idx = None
    end_idx = None

    item_1a = re.compile(r"\bitem\s+1a\b", re.IGNORECASE)
    risk_factors = re.compile(r"\brisk\s+factors?\b", re.IGNORECASE)
    end_item = re.compile(r"\bitem\s+1b\b|\bitem\s+2\b", re.IGNORECASE)

    for match in item_1a.finditer(text):
        window = text[match.start() : match.start() + 400]
        if risk_factors.search(window):
            start_idx = match.start()
            break

    if start_idx is None:
        match = item_1a.search(text)
        if match:
            start_idx = match.start()

    if start_idx is not None:
        end_match = end_item.search(text, start_idx + 1)
        if end_match:
            end_idx = end_match.start()
            section = text[start_idx:end_idx].strip()
            confidence = 0.85 if risk_factors.search(text[start_idx:start_idx + 400]) else 0.7
            return section, confidence, "regex_item1a_to_item1b", errors
        errors.append("end_not_found")

    risk_match = risk_factors.search(text)
    if risk_match:
        start_idx = risk_match.start()
        end_match = end_item.search(text, start_idx + 1)
        end_idx = end_match.start() if end_match else min(start_idx + 80000, len(text))
        section = text[start_idx:end_idx].strip()
        confidence = 0.45 if end_match else 0.3
        if not end_match and "end_not_found" not in errors:
            errors.append("end_not_found")
        return section, confidence, "risk_factors_fallback", errors

    return "", 0.0, "not_found", ["item1a_not_found"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract Item 1A from a fixture HTML file.")
    parser.add_argument("--fixture", required=True, help="Path to fixture HTML file.")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    html = Path(args.fixture).read_text(encoding="utf-8", errors="replace")
    text = clean_html_to_text(html)
    section, confidence, method, errors = extract_item_1a(text)
    paragraphs = split_paragraphs(section)

    preview = section[:300].replace("\n", " ").strip()

    print(f"confidence: {confidence:.2f}")
    print(f"method: {method}")
    if errors:
        print(f"errors: {errors}")
    print(f"extracted_length: {len(section)}")
    print(f"paragraphs: {len(paragraphs)}")
    print(f"preview: {preview}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
