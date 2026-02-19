from __future__ import annotations

import argparse
import json
import shutil
import sys
from difflib import unified_diff
from pathlib import Path
from typing import Any, Optional

SCRIPT_VERSION = "lab_prompt_consistency_check.py@v1"

REPO_ROOT = Path(__file__).resolve().parents[1]

sys.path.append(str(Path(__file__).resolve().parent))
from lab_emit_chatgpt_thread_starters import main as emit_thread_starters  # type: ignore
from lab_llm_precompute_utils import resolve_bundle_paths, to_repo_relative  # type: ignore
from lab_prompt_blocks import (  # type: ignore
    DETECTOR_DELTA_BRIEF,
    DETECTOR_EXCERPT_PICKER,
    build_chatgpt_project_instructions_lines,
    build_prompt_template_detector_section_lines,
    build_prompt_templates_showcase_lines,
    build_thread_starter_lines,
)


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8-sig").splitlines()


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


def _extract_section(lines: list[str], section_header: str) -> list[str]:
    start = -1
    for idx, line in enumerate(lines):
        if line.strip() == section_header:
            start = idx
            break
    if start == -1:
        raise SystemExit(f"Missing section header: {section_header}")

    end = len(lines)
    for idx in range(start + 1, len(lines)):
        if lines[idx].startswith("## "):
            end = idx
            break
    section = lines[start:end]
    while section and not section[-1].strip():
        section.pop()
    return section


def _assert_lines_equal(label: str, expected: list[str], actual: list[str]) -> None:
    if expected == actual:
        return
    diff = "\n".join(
        unified_diff(
            expected,
            actual,
            fromfile=f"{label}:expected",
            tofile=f"{label}:actual",
            lineterm="",
        )
    )
    raise SystemExit(f"{label} mismatch:\n{diff}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check prompt/template consistency across canonical emitters."
    )
    parser.add_argument(
        "--bundle",
        default="",
        help="Showcase LLM input bundle root (defaults to latest showcase_llm_inputs_*).",
    )
    parser.add_argument(
        "--prompt-templates",
        default="",
        help="Override path to prompt_templates_showcase.md.",
    )
    parser.add_argument(
        "--sample-out-dir",
        default=str(REPO_ROOT / "reports" / "prompt2_sample_starters"),
        help="Directory for generated sample starter artifacts.",
    )
    parser.add_argument(
        "--instructions-report",
        default=str(REPO_ROOT / "reports" / "lab_chatgpt_project_instructions.txt"),
        help="Path to canonical report instructions text.",
    )
    parser.add_argument(
        "--instructions-public",
        default=str(
            REPO_ROOT
            / "public"
            / "data"
            / "sec_narrative_drift_lab"
            / "llm_project_instructions_v1.txt"
        ),
        help="Path to canonical public instructions text.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    bundle_paths = resolve_bundle_paths(
        args.bundle or None,
        None,
        None,
        args.prompt_templates or None,
    )
    prompt_path = bundle_paths.prompt_templates
    if prompt_path is None or not prompt_path.exists():
        raise SystemExit("prompt_templates_showcase.md not found.")

    expected_full = build_prompt_templates_showcase_lines()
    actual_full = _read_lines(prompt_path)
    _assert_lines_equal("prompt_templates_showcase", expected_full, actual_full)

    for detector_id in (DETECTOR_DELTA_BRIEF, DETECTOR_EXCERPT_PICKER):
        expected_section = build_prompt_template_detector_section_lines(detector_id)
        actual_section = _extract_section(actual_full, f"## {detector_id}")
        _assert_lines_equal(f"prompt_section:{detector_id}", expected_section, actual_section)

    expected_instructions = build_chatgpt_project_instructions_lines()
    instructions_report = Path(args.instructions_report)
    if not instructions_report.is_absolute():
        instructions_report = REPO_ROOT / instructions_report
    if instructions_report.exists():
        actual_report_instructions = _read_lines(instructions_report)
        _assert_lines_equal(
            "project_instructions_report", expected_instructions, actual_report_instructions
        )
    instructions_public = Path(args.instructions_public)
    if not instructions_public.is_absolute():
        instructions_public = REPO_ROOT / instructions_public
    if instructions_public.exists():
        actual_public_instructions = _read_lines(instructions_public)
        _assert_lines_equal(
            "project_instructions_public", expected_instructions, actual_public_instructions
        )

    sample_dir = Path(args.sample_out_dir)
    if sample_dir.exists():
        shutil.rmtree(sample_dir)
    sample_dir.mkdir(parents=True, exist_ok=True)

    sample_ticker = "KO"
    sample_year_from = 2023
    sample_year_to = 2024
    sample_lens = "focuspack_deboilerplated"
    sample_input = (
        f"inputs/{sample_ticker}_{sample_year_from}_{sample_year_to}_focuspack_deboilerplated.json"
    )
    sample_repo_input = (
        f"{to_repo_relative(bundle_paths.bundle_root)}/llm_inputs_focuspack/"
        f"{sample_ticker}/lab_llm_focuspack_10k_item1a_{sample_year_from}_{sample_year_to}_deboilerplated.json"
    )

    jobs: list[dict[str, Any]] = []
    for detector_id in (DETECTOR_DELTA_BRIEF, DETECTOR_EXCERPT_PICKER):
        output_path = (
            f"public/data/sec_narrative_drift_lab/{sample_ticker}/outputs/{detector_id}/"
            f"lab_{detector_id}_10k_item1a_{sample_year_from}_{sample_year_to}_{sample_lens}.json"
        )
        jobs.append(
            {
                "job_id": f"{sample_ticker}_{sample_year_from}_{sample_year_to}_{detector_id}_{sample_lens}",
                "ticker": sample_ticker,
                "section": "10k_item1a",
                "year_from": sample_year_from,
                "year_to": sample_year_to,
                "detector_id": detector_id,
                "source_id": "edgar",
                "input_lens": sample_lens,
                "input_path": sample_input,
                "repo_input_path": sample_repo_input,
                "output_path": output_path,
            }
        )

    jobs_path = sample_dir / "jobs.jsonl"
    _write_jsonl(jobs_path, jobs)

    emit_rc = emit_thread_starters(
        [
            "--jobs",
            str(jobs_path),
            "--prompt-templates",
            str(prompt_path),
        ]
    )
    if emit_rc != 0:
        raise SystemExit(f"Starter generation failed with exit code {emit_rc}")

    starters_dir = sample_dir / "thread_starters"
    for detector_id in (DETECTOR_DELTA_BRIEF, DETECTOR_EXCERPT_PICKER):
        starter_name = (
            f"{sample_ticker}_{sample_year_from}_{sample_year_to}__{detector_id}__{sample_lens}.md"
        )
        starter_path = starters_dir / starter_name
        if not starter_path.exists():
            raise SystemExit(f"Missing generated starter: {starter_path}")
        expected_starter = build_thread_starter_lines(
            detector_id=detector_id,
            ticker=sample_ticker,
            year_from=sample_year_from,
            year_to=sample_year_to,
            section="10k_item1a",
            source_id="edgar",
            input_lens=sample_lens,
            input_path=sample_input,
            output_path=next(
                row["output_path"] for row in jobs if row["detector_id"] == detector_id
            ),
            repo_input_path=sample_repo_input,
        )
        actual_starter = _read_lines(starter_path)
        _assert_lines_equal(f"starter:{detector_id}", expected_starter, actual_starter)

    readme_lines = [
        "# Prompt 2 Sample Starters",
        "",
        f"Script: {SCRIPT_VERSION}",
        f"Prompt templates checked: {to_repo_relative(prompt_path)}",
        f"Sample jobs: {to_repo_relative(jobs_path)}",
        "",
        "Generated starters:",
        f"- {to_repo_relative(starters_dir / f'{sample_ticker}_{sample_year_from}_{sample_year_to}__{DETECTOR_DELTA_BRIEF}__{sample_lens}.md')}",
        f"- {to_repo_relative(starters_dir / f'{sample_ticker}_{sample_year_from}_{sample_year_to}__{DETECTOR_EXCERPT_PICKER}__{sample_lens}.md')}",
    ]
    (sample_dir / "README.md").write_text("\n".join(readme_lines) + "\n", encoding="utf-8")

    print("Prompt consistency check: PASS")
    print(f"Prompt templates: {prompt_path}")
    print(f"Sample starters dir: {sample_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
