from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SCAN_ROOTS = [
    REPO_ROOT / "src",
    REPO_ROOT / "docs",
    REPO_ROOT / ".github" / "workflows",
    REPO_ROOT / "README.md",
    REPO_ROOT / "package.json",
]

SKIP_PATH_PARTS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "attic",
}

SKIP_PATH_PREFIXES = [
    "docs/llm_oriented_lab_pivot/",
    "docs/_archive/",
    "docs/00_README_doc_index.md",
    "docs/sec_narrative_drift_",
]

BANNED_PATTERNS = [
    re.compile(r"\bhiring\b", re.IGNORECASE),
    re.compile(r"\brecruiter\b", re.IGNORECASE),
    re.compile(r"\binterview(?:s)?\b", re.IGNORECASE),
    re.compile(r"\bportfolio\b", re.IGNORECASE),
    re.compile(r"\bdemo framing\b", re.IGNORECASE),
    re.compile(r"\bvibe-?coded\b", re.IGNORECASE),
    re.compile(r"\bbuilt with ai\b", re.IGNORECASE),
    re.compile(r"\bai-generated\b", re.IGNORECASE),
]

# Allow operational identifiers and immutable corpus references where needed.
ALLOWLIST_PATTERNS = [
    re.compile(r"openai_[a-z0-9_]+", re.IGNORECASE),
    re.compile(r"chatgpt", re.IGNORECASE),
    re.compile(r"codex", re.IGNORECASE),
    re.compile(r"SEC", re.IGNORECASE),
]

TEXT_EXTENSIONS = {
    ".ts",
    ".tsx",
    ".js",
    ".mjs",
    ".cjs",
    ".json",
    ".md",
    ".yml",
    ".yaml",
}


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def should_skip_path(path: Path) -> bool:
    rel = repo_rel(path)
    for prefix in SKIP_PATH_PREFIXES:
        if rel.startswith(prefix):
            return True
    for part in path.parts:
        if part in SKIP_PATH_PARTS:
            return True
    return False


def should_scan_file(path: Path) -> bool:
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return False
    if should_skip_path(path):
        return False
    return True


def is_allowlisted_line(line: str) -> bool:
    for pattern in ALLOWLIST_PATTERNS:
        if pattern.search(line):
            return True
    return False


def iter_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.exists():
        return []
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if should_scan_file(path):
            files.append(path)
    return files


def main() -> int:
    violations: list[str] = []
    scanned = 0

    targets: list[Path] = []
    for root in SCAN_ROOTS:
        targets.extend(iter_files(root))

    for path in targets:
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            violations.append(f"{repo_rel(path)}:0: read error: {exc}")
            continue

        for idx, line in enumerate(text.splitlines(), start=1):
            if is_allowlisted_line(line):
                continue
            for pattern in BANNED_PATTERNS:
                if pattern.search(line):
                    snippet = line.strip()
                    if len(snippet) > 160:
                        snippet = snippet[:157] + "..."
                    violations.append(
                        f"{repo_rel(path)}:{idx}: prohibited phrase ({pattern.pattern}): {snippet}"
                    )
                    break

    if violations:
        print("Public tone guard FAILED.")
        print("Remove hiring/portfolio/AI-authorship framing from public text.")
        for item in violations:
            print(f"- {item}")
        return 1

    print(f"Public tone guard OK. scanned_files={scanned}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
