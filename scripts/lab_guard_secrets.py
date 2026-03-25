"""Guard: scan tracked files for accidentally committed secrets.

Checks git-tracked source, config, and data files for patterns that
look like API keys, tokens, or other credentials.  Runs in CI and as
a predeploy gate to prevent secrets from reaching production.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# File extensions worth scanning (source, config, data).
SCAN_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx", ".json", ".py",
    ".yml", ".yaml", ".toml", ".cfg", ".ini",
    ".env", ".sh", ".bash", ".zsh",
    ".md", ".txt", ".csv",
}

# Skip binary / generated directories even if tracked.
SKIP_PARTS = {"node_modules", ".git", "dist", "build", "coverage"}

# Each tuple: (label, compiled regex).
# Patterns target high-entropy key formats from common providers.
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # OpenAI keys: sk-proj-... or sk-<org>-... with mostly alphanumeric chars.
    # Exclude URL slugs (which contain many hyphens) by requiring the key body
    # to be dominated by alphanumerics/underscores, not hyphens.
    ("OpenAI API key", re.compile(r"(?<![/\w])sk-(?:proj-)?[A-Za-z0-9_]{20,}")),
    ("Anthropic API key", re.compile(r"(?<![/\w])sk-ant-[A-Za-z0-9_]{20,}")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("AWS secret key assignment", re.compile(
        r"""(?:aws_secret_access_key|AWS_SECRET_ACCESS_KEY)\s*[=:]\s*['"]?[A-Za-z0-9/+=]{30,}""",
    )),
    ("GitHub token", re.compile(r"gh[pous]_[A-Za-z0-9_]{36,}")),
    # Generic secrets: require the variable name to end with _SECRET, _TOKEN,
    # _PASSWORD, _APIKEY, or _API_KEY, and the value to be at least 16 chars
    # (short identifiers like "codex_real" are not secrets).
    ("Generic secret assignment", re.compile(
        r"""(?:_SECRET|_TOKEN|_PASSWORD|_APIKEY|_API_KEY)\s*[=:]\s*['"][A-Za-z0-9/+=_-]{16,}['"]""",
        re.IGNORECASE,
    )),
    ("Private key header", re.compile(r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----")),
    ("Slack token", re.compile(r"xox[bpras]-[0-9A-Za-z-]{10,}")),
    ("Google API key", re.compile(r"AIzaSy[A-Za-z0-9_-]{33}")),
    ("Stripe secret key", re.compile(r"sk_live_[A-Za-z0-9]{20,}")),
]

# Lines matching these patterns are false positives (documentation,
# schema definitions, test fixtures describing the format).
FALSE_POSITIVE_INDICATORS = re.compile(
    r"""(?x)
      \b example \b
    | \b placeholder \b
    | \b fake \b
    | \b dummy \b
    | \b test[_-]?key \b
    | \b redacted \b
    | \b xxx+ \b
    | sk-[A-Za-z0-9_-]*\.\.\.          # truncated display
    | SECRET_PATTERNS                    # this script's own definitions
    | re\.compile                        # regex definitions in code
    | https?://                          # URLs are not secrets
    | href\s*[:=]                        # link definitions
    | BULLET_TOKEN                       # text-processing sentinel
    | report_token                       # internal slug identifier
    """,
    re.IGNORECASE,
)


def list_tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    files: list[Path] = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        path = REPO_ROOT / stripped
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.suffix.lower() not in SCAN_EXTENSIONS:
            continue
        if path.is_file():
            files.append(path)
    return sorted(files)


def scan_file(path: Path) -> list[str]:
    violations: list[str] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    rel = path.relative_to(REPO_ROOT).as_posix()

    for line_num, line in enumerate(text.splitlines(), start=1):
        # Skip lines that are clearly not real secrets.
        if FALSE_POSITIVE_INDICATORS.search(line):
            continue
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                snippet = line.strip()[:120]
                violations.append(f"{rel}:{line_num}: {label}: {snippet}")
                break  # One report per line

    return violations


def main() -> int:
    tracked = list_tracked_files()
    violations: list[str] = []
    scanned = 0

    for path in tracked:
        scanned += 1
        violations.extend(scan_file(path))

    if violations:
        print("Secrets guard FAILED.")
        print("Possible secrets found in tracked files:")
        for item in violations:
            print(f"  - {item}")
        print()
        print("Remediation:")
        print("  1. Remove the secret from the file.")
        print("  2. Rotate the compromised credential immediately.")
        print("  3. Use environment variables or a secrets manager instead.")
        return 1

    print(f"Secrets guard OK. scanned_files={scanned}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
