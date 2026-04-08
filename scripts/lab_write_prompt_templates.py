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
from lab_output_tracks import (  # type: ignore
    DEFAULT_PRIMARY_LLM_CAMPAIGN_ID,
    get_llm_campaign,
)
from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v3")


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
        description=(
            "Rewrite archived detector compatibility prompt templates "
            "(`prompt_templates_showcase.md`) from canonical prompt blocks."
        )
    )
    parser.add_argument(
        "--bundle",
        default="",
        help="Compatibility bundle directory (defaults to latest bundles/showcase_llm_inputs_*).",
    )
    parser.add_argument(
        "--campaign-id",
        default=DEFAULT_PRIMARY_LLM_CAMPAIGN_ID,
        help="Campaign id from scripts/lab_output_tracks.py.",
    )
    parser.add_argument(
        "--out",
        default="",
        help=(
            "Output filename/path for prompt templates. Relative values resolve from the "
            "selected bundle directory. Defaults to prompt_templates_showcase.md "
            "(archived detector flow only; not casebook candidate prep)."
        ),
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

    campaign = get_llm_campaign(args.campaign_id)
    if campaign is None:
        raise SystemExit(f"Unknown campaign id: {args.campaign_id}")

    if args.out:
        output_path = Path(args.out)
        if not output_path.is_absolute():
            output_path = bundle_dir / output_path
    else:
        output_path = bundle_dir / "prompt_templates_showcase.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    prompt_lines = build_prompt_templates_showcase_lines(
        campaign=campaign,
        input_mode=campaign.input_mode or "full_section_v2",
    )
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(prompt_lines))
        handle.write("\n")

    if output_path.read_bytes()[:3] == UTF8_BOM:
        raise SystemExit(f"UTF-8 BOM detected in {output_path}")

    print(f"Script: {SCRIPT_VERSION}")
    print(f"Campaign: {campaign.track_id}")
    print(f"Wrote prompt templates to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
