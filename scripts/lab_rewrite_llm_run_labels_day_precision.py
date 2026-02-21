from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Optional

from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"
DEFAULT_CAMPAIGN_SLUG = "openai-chatgpt52ext-agent-2026-02-21"
DEFAULT_DAY = "21"

RUN_LABEL_RE_MONTH = re.compile(
    r'("run_label"\s*:\s*")(?P<ym>20\d{2}-(0[1-9]|1[0-2]))_(?P<tag>[^"]*)(")'
)
RUN_LABEL_RE_DAY = re.compile(
    r'("run_label"\s*:\s*")(?P<ymd>20\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01]))_(?P<tag>[^"]*)(")'
)


def rewrite_file(path: Path, day: str) -> tuple[bool, str]:
    raw = path.read_text(encoding="utf-8")
    if RUN_LABEL_RE_DAY.search(raw):
        return False, "already_day_precise"
    month_match = RUN_LABEL_RE_MONTH.search(raw)
    if month_match is None:
        return False, "run_label_not_found_or_unexpected"
    ym = month_match.group("ym")
    tag = month_match.group("tag")
    replacement = f'"run_label":"{ym}-{day}_{tag}"'
    rewritten = RUN_LABEL_RE_MONTH.sub(replacement, raw, count=1)
    if rewritten == raw:
        return False, "no_change"
    path.write_text(rewritten, encoding="utf-8", newline="\n")
    return True, "updated"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rewrite month-only LLM provenance.run_label values to day-precise format."
    )
    parser.add_argument(
        "--campaign-slug",
        default=DEFAULT_CAMPAIGN_SLUG,
        help="Campaign slug folder under outputs/<detector_id>/<campaign_slug>/",
    )
    parser.add_argument(
        "--day",
        default=DEFAULT_DAY,
        help="Day value to apply when run_label is month-only (DD).",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if not re.fullmatch(r"(0[1-9]|[12]\d|3[01])", args.day):
        raise SystemExit("--day must be DD (01-31)")

    files = sorted(
        LAB_ROOT.glob(
            f"*/outputs/det_llm_*_v1/{args.campaign_slug}/lab_det_llm_*_v1_*.json"
        )
    )
    updated = 0
    skipped_day = 0
    skipped_missing = 0
    for path in files:
        changed, status = rewrite_file(path, args.day)
        if changed:
            updated += 1
        elif status == "already_day_precise":
            skipped_day += 1
        else:
            skipped_missing += 1

    print(f"Script: {SCRIPT_VERSION}")
    print(f"Campaign slug: {args.campaign_slug}")
    print(f"Files scanned: {len(files)}")
    print(f"Updated run_label: {updated}")
    print(f"Already day-precise: {skipped_day}")
    print(f"Skipped (not found/unexpected): {skipped_missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
