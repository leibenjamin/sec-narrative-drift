from __future__ import annotations

import argparse
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

SCRIPT_VERSION = "lab_build_chatgpt_review_bundle_inputs_sync.py@v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLES_ROOT = REPO_ROOT / "bundles"

REQUIRED_FILES = [
    "src/lib/labData.ts",
    "scripts/lab_ingest_manual_llm_outputs.py",
    "docs/lab/03_llm_precompute_workflow.md",
    "reports/ingest_smoke_summary.md",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build ChatGPT review bundle for input-path sync and manual-ingest changes."
    )
    parser.add_argument(
        "--out-zip",
        default="",
        help="Output zip path (default chatgpt_review_bundle_inputs_sync_<timestamp>.zip).",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stage_dir = BUNDLES_ROOT / f"review_inputs_sync_{timestamp}"
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True, exist_ok=True)

    included: list[str] = []
    for rel_path in REQUIRED_FILES:
        src = REPO_ROOT / rel_path
        if not src.exists() or not src.is_file():
            raise SystemExit(f"Missing required file for review bundle: {rel_path}")
        dest = stage_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        included.append(rel_path)

    out_zip = (
        Path(args.out_zip)
        if args.out_zip
        else REPO_ROOT / f"chatgpt_review_bundle_inputs_sync_{timestamp}.zip"
    )
    if out_zip.exists():
        out_zip.unlink()

    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zip_handle:
        for path in sorted(stage_dir.rglob("*")):
            if path.is_file():
                zip_handle.write(path, path.relative_to(stage_dir).as_posix())

    print(f"Wrote review bundle zip: {out_zip}")
    print(f"Script: {SCRIPT_VERSION}")
    print("Included files:")
    for rel_path in included:
        print(f"- {rel_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
