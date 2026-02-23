from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from lab_prompt_blocks import build_chatgpt_project_instructions_lines  # type: ignore
from lab_output_tracks import (  # type: ignore
    DEFAULT_PRIMARY_LLM_CAMPAIGN_ID,
    get_llm_campaign,
)
from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v2")
REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_REPORT_OUT = REPO_ROOT / "reports" / "lab_chatgpt_project_instructions.txt"
DEFAULT_PUBLIC_OUT = (
    REPO_ROOT
    / "public"
    / "data"
    / "sec_narrative_drift_lab"
    / "llm_project_instructions_v1.txt"
)


def write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write canonical project instructions from lab_prompt_blocks."
    )
    parser.add_argument(
        "--campaign-id",
        default=DEFAULT_PRIMARY_LLM_CAMPAIGN_ID,
        help="Campaign id defined in scripts/lab_output_tracks.py.",
    )
    parser.add_argument(
        "--out-report",
        default="",
        help="Optional explicit report output path.",
    )
    parser.add_argument(
        "--out-public",
        default="",
        help="Optional explicit public output path.",
    )
    parser.add_argument(
        "--write-legacy-primary-alias",
        action="store_true",
        help="When set for primary campaign, also write legacy *_v1 instruction alias files.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    campaign = get_llm_campaign(args.campaign_id)
    if campaign is None:
        raise SystemExit(f"Unknown campaign id: {args.campaign_id}")
    lines = build_chatgpt_project_instructions_lines(
        campaign=campaign,
        input_mode=campaign.input_mode or "full_section_v2",
    )

    if args.out_report:
        report_path = Path(args.out_report)
        if not report_path.is_absolute():
            report_path = REPO_ROOT / report_path
    else:
        report_path = (
            REPO_ROOT / "reports" / f"lab_project_instructions_{campaign.track_id}.txt"
        )
    if args.out_public:
        public_path = Path(args.out_public)
        if not public_path.is_absolute():
            public_path = REPO_ROOT / public_path
    else:
        asset_name = campaign.instructions_asset_name or f"llm_project_instructions_{campaign.track_id}.txt"
        public_path = (
            REPO_ROOT
            / "public"
            / "data"
            / "sec_narrative_drift_lab"
            / asset_name
        )

    write_text(report_path, lines)
    write_text(public_path, lines)

    if args.write_legacy_primary_alias and args.campaign_id == DEFAULT_PRIMARY_LLM_CAMPAIGN_ID:
        write_text(DEFAULT_REPORT_OUT, lines)
        write_text(DEFAULT_PUBLIC_OUT, lines)

    print(f"Script: {SCRIPT_VERSION}")
    print(f"Campaign: {campaign.track_id}")
    print(f"Wrote report instructions: {report_path}")
    print(f"Wrote public instructions: {public_path}")
    if args.write_legacy_primary_alias and args.campaign_id == DEFAULT_PRIMARY_LLM_CAMPAIGN_ID:
        print(f"Wrote legacy report alias: {DEFAULT_REPORT_OUT}")
        print(f"Wrote legacy public alias: {DEFAULT_PUBLIC_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
