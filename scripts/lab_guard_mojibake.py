from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
LAB_DATA_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"
LLM_INPUTS_V2_ROOT = LAB_DATA_ROOT / "llm_inputs_v2"

SRC_EXTENSIONS = {
    ".css",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
}

SKIP_PATH_PARTS = {
    ".git",
    "attic",
    "build",
    "coverage",
    "dist",
    "node_modules",
}


@dataclass(frozen=True)
class MojibakePattern:
    label: str
    pattern: re.Pattern[str]


MOJIBAKE_PATTERNS = [
    MojibakePattern(
        label="broken smart punctuation / dash",
        pattern=re.compile("\u00e2\u20ac(?:[\u00a6\u009d\u0153\u02dc\u201c\u201d\u2122])"),
    ),
    MojibakePattern(
        label="broken pilcrow",
        pattern=re.compile("\u00c2\u00b6"),
    ),
    MojibakePattern(
        label="broken UTF-8 latin fragment",
        pattern=re.compile("\u00c3[\u0080-\u00bf]"),
    ),
]


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def should_skip_path(path: Path) -> bool:
    return any(part in SKIP_PATH_PARTS for part in path.parts)


def iter_src_files() -> list[Path]:
    if not SRC_ROOT.exists():
        return []

    files: list[Path] = []
    for path in SRC_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SRC_EXTENSIONS:
            continue
        if should_skip_path(path):
            continue
        files.append(path)
    return sorted(files)


def iter_metadata_json_files() -> list[Path]:
    files: list[Path] = []

    if LAB_DATA_ROOT.exists():
        for path in LAB_DATA_ROOT.glob("*.json"):
            if path.is_file() and not should_skip_path(path):
                files.append(path)

    if LLM_INPUTS_V2_ROOT.exists():
        for path in LLM_INPUTS_V2_ROOT.glob("*.json"):
            if path.is_file() and not should_skip_path(path):
                files.append(path)

    return sorted(files)


def format_snippet(line: str, limit: int = 160) -> str:
    snippet = " ".join(line.strip().split())
    if len(snippet) <= limit:
        return snippet
    return snippet[: limit - 3] + "..."


def scan_file(path: Path) -> list[str]:
    violations: list[str] = []

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return [f"{repo_rel(path)}:0: read error: {exc}"]
    except OSError as exc:
        return [f"{repo_rel(path)}:0: read error: {exc}"]

    for idx, line in enumerate(text.splitlines(), start=1):
        for entry in MOJIBAKE_PATTERNS:
            if entry.pattern.search(line):
                violations.append(
                    f"{repo_rel(path)}:{idx}: {entry.label}: {format_snippet(line)}"
                )
                break

    return violations


def main() -> int:
    violations: list[str] = []
    scanned = 0

    targets = iter_src_files() + iter_metadata_json_files()
    for path in targets:
        scanned += 1
        violations.extend(scan_file(path))

    if violations:
        print("Mojibake guard FAILED.")
        print("Repair broken UTF-8/Latin-1 text in shipped authored surfaces.")
        for item in violations:
            print(f"- {item}")
        return 1

    print(f"Mojibake guard OK. scanned_files={scanned}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
