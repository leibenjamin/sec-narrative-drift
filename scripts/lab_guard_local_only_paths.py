from __future__ import annotations

import fnmatch
import subprocess
from pathlib import PurePosixPath, Path
from typing import Optional

from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_PREFIXES = (
    "reports/",
    "scripts/_reports/",
    "scripts/_cache/",
    "bundles/",
    "analysis_exports/",
)

FORBIDDEN_GLOBS = (
    "chatgpt_bundle_*",
    "chatgpt_bundle_*.zip",
    "chatgpt_review_bundle_*",
    "chatgpt_review_bundle_*.zip",
    "chatgpt_upload_bundle_*",
    "chatgpt_upload_bundle_*.zip",
    "chatgpt_review_pack_*",
    "chatgpt_review_pack_*.zip",
    "chatgpt_review_prompt2_sync_*",
    "chatgpt_review_prompt2_sync_*.zip",
)


def normalize_git_path(path_value: str) -> Optional[str]:
    normalized = path_value.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        return None
    if normalized.startswith("/"):
        return None
    if len(normalized) >= 2 and normalized[1] == ":":
        return None
    parts = normalized.split("/")
    cleaned: list[str] = []
    for part in parts:
        if part in {"", "."}:
            continue
        if part == "..":
            return None
        cleaned.append(part)
    if not cleaned:
        return None
    return "/".join(cleaned)


def get_forbidden_reason(path_value: str) -> Optional[str]:
    for prefix in FORBIDDEN_PREFIXES:
        if path_value.startswith(prefix):
            return f"matches forbidden local-only prefix '{prefix}'"
    basename = PurePosixPath(path_value).name
    for pattern in FORBIDDEN_GLOBS:
        if fnmatch.fnmatch(path_value, pattern) or fnmatch.fnmatch(basename, pattern):
            return f"matches forbidden local-only pattern '{pattern}'"
    return None


def list_tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    output = result.stdout.splitlines()
    files: list[str] = []
    for line in output:
        normalized = normalize_git_path(line)
        if normalized is not None:
            files.append(normalized)
    return files


def main() -> int:
    tracked_files = list_tracked_files()
    violations: list[tuple[str, str]] = []
    for file_path in tracked_files:
        reason = get_forbidden_reason(file_path)
        if reason is None:
            continue
        violations.append((file_path, reason))

    if violations:
        print(f"Script: {SCRIPT_VERSION}")
        print("FAILED: local-only paths are tracked in git.")
        for file_path, reason in violations:
            print(f"- {file_path}: {reason}")
        print("")
        print("Remediation:")
        print("- Remove tracked files from git index while keeping local copies:")
        print("  git rm --cached <path>")
        print("- Commit the cleanup and rerun this guard.")
        return 1

    print(f"Script: {SCRIPT_VERSION}")
    print("OK: no forbidden local-only tracked paths detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
