from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLES_ROOT = REPO_ROOT / "bundles"
UTF8_BOM = b"\xef\xbb\xbf"

sys.path.append(str(Path(__file__).resolve().parent))
from lab_prompt_blocks import build_prompt_templates_showcase_lines  # type: ignore
from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v2")


def find_latest_showcase_bundle(root: Path) -> Optional[Path]:
    if not root.exists():
        return None
    candidates: list[Path] = []
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        if not entry.name.startswith("showcase_llm_inputs_"):
            continue
        candidates.append(entry)
    if not candidates:
        return None
    return sorted(candidates, key=lambda path: path.name)[-1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rewrite prompt_templates_showcase.md from canonical prompt blocks."
    )
    parser.add_argument(
        "--bundle",
        default="",
        help="Showcase bundle directory (defaults to latest bundles/showcase_llm_inputs_*).",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    bundle_dir = Path(args.bundle) if args.bundle else find_latest_showcase_bundle(BUNDLES_ROOT)
    if bundle_dir is None:
        raise SystemExit("No showcase bundle found. Provide --bundle.")
    if not bundle_dir.exists() or not bundle_dir.is_dir():
        raise SystemExit(f"Bundle directory not found: {bundle_dir}")

    output_path = bundle_dir / "prompt_templates_showcase.md"
    prompt_lines = build_prompt_templates_showcase_lines()
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(prompt_lines))
        handle.write("\n")

    if output_path.read_bytes()[:3] == UTF8_BOM:
        raise SystemExit(f"UTF-8 BOM detected in {output_path}")

    print(f"Script: {SCRIPT_VERSION}")
    print(f"Wrote prompt templates to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
