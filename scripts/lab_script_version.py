from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Optional


def _git_short_rev(repo_root: Path) -> Optional[str]:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short=10", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return None
    value = completed.stdout.strip()
    if not value:
        return None
    return value


def build_script_version(script_path: Path, base_version: str) -> str:
    script_name = script_path.name
    try:
        digest = hashlib.sha256(script_path.read_bytes()).hexdigest()[:10]
    except Exception:
        repo_root = script_path.resolve().parents[1]
        digest = _git_short_rev(repo_root) or "unknown"
    return f"{script_name}@{base_version}+{digest}"
