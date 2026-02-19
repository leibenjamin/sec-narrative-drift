from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from lab_prompt_blocks import build_chatgpt_project_instructions_lines  # type: ignore

SCRIPT_VERSION = "lab_write_chatgpt_project_instructions.py@v1"
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
        description="Write canonical ChatGPT Project instructions from lab_prompt_blocks."
    )
    parser.add_argument(
        "--out-report",
        default=str(DEFAULT_REPORT_OUT),
        help="Path to reports/lab_chatgpt_project_instructions.txt",
    )
    parser.add_argument(
        "--out-public",
        default=str(DEFAULT_PUBLIC_OUT),
        help="Path to public runtime instruction text asset.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    lines = build_chatgpt_project_instructions_lines()

    report_path = Path(args.out_report)
    if not report_path.is_absolute():
        report_path = REPO_ROOT / report_path
    public_path = Path(args.out_public)
    if not public_path.is_absolute():
        public_path = REPO_ROOT / public_path

    write_text(report_path, lines)
    write_text(public_path, lines)

    print(f"Script: {SCRIPT_VERSION}")
    print(f"Wrote report instructions: {report_path}")
    print(f"Wrote public instructions: {public_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
