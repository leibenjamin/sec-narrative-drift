from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"


def as_dict(value: Any) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    raw = cast(dict[Any, Any], value)
    output: dict[str, Any] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            return None
        output[key] = item
    return output


def iter_candidate_paths() -> list[Path]:
    candidates: list[Path] = []
    seen: set[Path] = set()
    if not LAB_ROOT.exists():
        return candidates

    patterns = [
        "**/outputs/det_llm_*/**/*.json",
        "llm_outputs/**/*.json",
    ]
    for pattern in patterns:
        for path in LAB_ROOT.glob(pattern):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            candidates.append(path)
    return candidates


def migrate_file(path: Path) -> bool:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    root = as_dict(payload)
    if root is None:
        return False
    changed = False
    if "section" in root and "section_id" not in root:
        root["section_id"] = root["section"]
        changed = True
    if "section_id" in root and "section" not in root:
        root["section"] = root["section_id"]
        changed = True
    if not changed:
        return False
    path.write_text(json.dumps(root, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def main() -> int:
    files = iter_candidate_paths()
    modified = 0
    for path in files:
        if migrate_file(path):
            modified += 1
    print(f"files_scanned={len(files)} files_modified={modified}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
