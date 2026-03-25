"""Guard: scan public JSON data for suspicious injection patterns.

Belt-and-suspenders defense.  The React front end renders all JSON text
as plain text (no dangerouslySetInnerHTML), and Zod schemas validate
structure before rendering.  This guard adds an additional layer: if
any public JSON file contains content that looks like an HTML injection
or protocol-handler payload, the deploy pipeline stops.

This catches poisoned data at build time rather than relying solely on
runtime rendering safety.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Union

JsonValue = Union[str, int, float, bool, None, list["JsonValue"], dict[str, "JsonValue"]]

REPO_ROOT = Path(__file__).resolve().parents[1]

SCAN_ROOTS = [
    REPO_ROOT / "public" / "data",
]

# Patterns that should never appear inside shipped JSON string values.
# Each tuple is (label, compiled regex).
SUSPICIOUS_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("script tag", re.compile(r"<\s*script", re.IGNORECASE)),
    ("event handler attribute", re.compile(
        r"\b(?:on(?:error|load|click|mouseover|focus|blur|submit|input|change))\s*=",
        re.IGNORECASE,
    )),
    ("javascript: URI", re.compile(r"javascript\s*:", re.IGNORECASE)),
    ("data: text/html URI", re.compile(r"data\s*:\s*text/html", re.IGNORECASE)),
    ("vbscript: URI", re.compile(r"vbscript\s*:", re.IGNORECASE)),
    ("embedded style expression", re.compile(
        r"expression\s*\(", re.IGNORECASE,
    )),
    ("meta refresh injection", re.compile(
        r"<\s*meta[^>]*http-equiv", re.IGNORECASE,
    )),
    ("iframe injection", re.compile(r"<\s*iframe", re.IGNORECASE)),
    ("object/embed injection", re.compile(
        r"<\s*(?:object|embed)", re.IGNORECASE,
    )),
    ("svg script injection", re.compile(
        r"<\s*svg[^>]*on\w+\s*=", re.IGNORECASE,
    )),
]


def collect_strings(obj: JsonValue) -> list[str]:
    """Recursively extract all string values from parsed JSON."""
    strings: list[str] = []
    if isinstance(obj, str):
        strings.append(obj)
    elif isinstance(obj, dict):
        for value in obj.values():
            strings.extend(collect_strings(value))
    elif isinstance(obj, list):
        for item in obj:
            strings.extend(collect_strings(item))
    return strings


def scan_file(path: Path) -> list[str]:
    violations: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"{path.relative_to(REPO_ROOT).as_posix()}: read error: {exc}"]

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []  # Non-JSON or malformed — other guards catch this

    strings = collect_strings(data)
    rel = path.relative_to(REPO_ROOT).as_posix()

    for value in strings:
        for label, pattern in SUSPICIOUS_PATTERNS:
            if pattern.search(value):
                snippet = value[:120].replace("\n", " ")
                violations.append(f"{rel}: {label}: {snippet!r}")
                break  # One report per string is enough

    return violations


def main() -> int:
    violations: list[str] = []
    scanned = 0

    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            if not path.is_file():
                continue
            scanned += 1
            violations.extend(scan_file(path))

    if violations:
        print("JSON content guard FAILED.")
        print("Suspicious injection patterns found in public JSON data.")
        for item in violations:
            print(f"  - {item}")
        return 1

    print(f"JSON content guard OK. scanned_files={scanned}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
