from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"


def parse_track_slug(filename: str) -> Optional[str]:
    if not filename.endswith(".json"):
        return None
    stem = filename[:-5]
    marker = "__"
    if marker not in stem:
        return None
    suffix = stem.split(marker)[-1].strip()
    if not suffix:
        return None
    return suffix


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Remove flat output copies at outputs/<detector>/<file>.json when canonical track-suffixed copy exists."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report candidates without deleting files.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    candidates = 0
    deleted = 0
    skipped = 0

    for ticker_dir in LAB_ROOT.iterdir():
        if not ticker_dir.is_dir():
            continue
        outputs_dir = ticker_dir / "outputs"
        if not outputs_dir.exists() or not outputs_dir.is_dir():
            continue
        for detector_dir in outputs_dir.iterdir():
            if not detector_dir.is_dir():
                continue
            for flat_file in detector_dir.glob("*.json"):
                candidates += 1
                track_slug = parse_track_slug(flat_file.name)
                if track_slug is None:
                    skipped += 1
                    continue
                canonical_path = detector_dir / track_slug / flat_file.name
                if not canonical_path.exists():
                    skipped += 1
                    continue
                if args.dry_run:
                    continue
                flat_file.unlink()
                deleted += 1

    print(f"Script: {SCRIPT_VERSION}")
    print(f"Candidates: {candidates}")
    print(f"Deleted: {deleted}")
    print(f"Skipped: {skipped}")
    print(f"Dry run: {args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
