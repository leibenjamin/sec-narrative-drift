from __future__ import annotations

import argparse
import csv
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, cast

import sys

SCRIPT_VERSION = "lab_make_pilot_pack.py@v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_LAB_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"
BUNDLES_ROOT = REPO_ROOT / "bundles"

PILOT_CASES = [
    ("NVDA", 2021, 2022),
    ("KO", 2023, 2024),
]
DETECTORS = ["det_llm_delta_brief_v1", "det_llm_excerpt_picker_v1"]
INPUT_PRIORITY = [
    ("focuspack", "deboilerplated"),
    ("focuspack", "raw"),
    ("full", "deboilerplated"),
    ("full", "raw"),
]

sys.path.append(str(Path(__file__).resolve().parent))
from lab_llm_precompute_utils import (  # type: ignore
    BundlePaths,
    InputIndexEntry,
    as_str_dict,
    get_int,
    get_str,
    load_input_index,
    read_json,
    resolve_bundle_paths,
    to_repo_relative,
)


@dataclass(frozen=True)
class SelectedInput:
    entry: InputIndexEntry
    lens_key: str
    input_kind: str


def load_detector_prompts(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    prompts: dict[str, list[str]] = {}
    current: Optional[str] = None
    for line in lines:
        if line.startswith("## "):
            current = line[3:].strip()
            prompts[current] = []
            continue
        if current is None:
            continue
        prompts[current].append(line)
    output: dict[str, str] = {}
    for detector, block_lines in prompts.items():
        output[detector] = "\n".join(block_lines).strip()
    return output


def pick_input(
    ticker: str,
    year_from: int,
    year_to: int,
    section: str,
    focus_index: dict[tuple[str, int, int, str, str], InputIndexEntry],
    full_index: dict[tuple[str, int, int, str, str], InputIndexEntry],
) -> SelectedInput:
    for input_kind, lens in INPUT_PRIORITY:
        key = (ticker.upper(), year_from, year_to, section, lens)
        entry = focus_index.get(key) if input_kind == "focuspack" else full_index.get(key)
        if entry is None:
            continue
        if not entry.path.exists():
            continue
        lens_key = f"{input_kind}_{lens}"
        return SelectedInput(entry=entry, lens_key=lens_key, input_kind=input_kind)
    raise SystemExit(f"No input found for {ticker} {year_from}-{year_to}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a pilot LLM precompute pack.")
    parser.add_argument(
        "--bundle",
        default="",
        help="LLM input bundle root (defaults to latest bundles/showcase_llm_inputs_*)",
    )
    parser.add_argument(
        "--inputs-index-focuspack",
        default="",
        help="Override path to inputs_index_focuspack.json",
    )
    parser.add_argument(
        "--inputs-index-full",
        default="",
        help="Override path to inputs_index_full.json",
    )
    parser.add_argument(
        "--prompt-templates",
        default="",
        help="Override path to prompt_templates_showcase.md",
    )
    parser.add_argument(
        "--out-dir",
        default="",
        help="Output pilot pack directory (default bundles/llm_pilot_pack_<timestamp>)",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    bundle_paths = resolve_bundle_paths(
        args.bundle or None,
        args.inputs_index_focuspack or None,
        args.inputs_index_full or None,
        args.prompt_templates or None,
    )

    focus_index = load_input_index(bundle_paths.focus_index, bundle_paths.bundle_root)
    full_index = load_input_index(bundle_paths.full_index, bundle_paths.bundle_root)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir) if args.out_dir else BUNDLES_ROOT / f"llm_pilot_pack_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    inputs_dir = out_dir / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    thread_dir = out_dir / "thread_starters"
    thread_dir.mkdir(parents=True, exist_ok=True)

    prompt_path = bundle_paths.prompt_templates
    if prompt_path is None or not prompt_path.exists():
        raise SystemExit("prompt_templates_showcase.md not found.")
    detector_prompts = load_detector_prompts(prompt_path)

    jobs: list[dict[str, Any]] = []
    input_cache: dict[tuple[str, int, int], dict[str, Any]] = {}

    for ticker, year_from, year_to in PILOT_CASES:
        section = "10k_item1a"
        source_id = "edgar"
        selected = pick_input(ticker, year_from, year_to, section, focus_index, full_index)

        cache_key = (ticker, year_from, year_to)
        if cache_key not in input_cache:
            source_path = selected.entry.path
            input_name = f"{ticker}_{year_from}_{year_to}_{selected.lens_key}.json"
            dest_path = inputs_dir / input_name
            shutil.copy2(source_path, dest_path)
            input_cache[cache_key] = {
                "input_path": to_repo_relative(dest_path),
                "input_source_path": to_repo_relative(source_path),
                "lens_key": selected.lens_key,
            }

        entry = input_cache[cache_key]

        for detector_id in DETECTORS:
            output_path = (
                PUBLIC_LAB_ROOT
                / "llm_outputs"
                / detector_id
                / ticker
                / f"lab_{detector_id}_{section}_{year_from}_{year_to}_{entry['lens_key']}.json"
            )
            job_id = f"{ticker}_{year_from}_{year_to}_{detector_id}_{entry['lens_key']}"
            jobs.append(
                {
                    "job_id": job_id,
                    "ticker": ticker,
                    "section": section,
                    "year_from": year_from,
                    "year_to": year_to,
                    "detector_id": detector_id,
                    "source_id": source_id,
                    "input_lens": entry["lens_key"],
                    "input_path": entry["input_path"],
                    "input_source_path": entry["input_source_path"],
                    "output_path": to_repo_relative(output_path),
                }
            )

    jobs_jsonl = out_dir / "pilot_jobs.jsonl"
    with jobs_jsonl.open("w", encoding="utf-8") as handle:
        for job in jobs:
            handle.write(json.dumps(job, sort_keys=True))
            handle.write("\n")

    jobs_csv = out_dir / "pilot_jobs.csv"
    fieldnames = [
        "job_id",
        "ticker",
        "section",
        "year_from",
        "year_to",
        "detector_id",
        "source_id",
        "input_lens",
        "input_path",
        "output_path",
        "input_source_path",
    ]
    with jobs_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for job in jobs:
            writer.writerow({key: job.get(key, "") for key in fieldnames})

    for job in jobs:
        detector_id = cast(str, job.get("detector_id"))
        prompt_text = detector_prompts.get(detector_id)
        if prompt_text is None:
            raise SystemExit(f"Prompt template missing for {detector_id}")
        filename = (
            f"{job['ticker']}_{job['year_from']}_{job['year_to']}__{detector_id}__{job['input_lens']}.md"
        )
        thread_title = f"{job['ticker']} {job['year_from']}-{job['year_to']} {detector_id} ({job['input_lens']})"
        lines: list[str] = []
        lines.append(f"Thread Title: {thread_title}")
        lines.append("")
        lines.append(f"Attach this input file: {job['input_path']}")
        lines.append(f"Save output to: {job['output_path']}")
        lines.append("")
        lines.append("STRICT OUTPUT RULES")
        lines.append("JSON ONLY.")
        lines.append("No markdown.")
        lines.append("No backticks.")
        lines.append("")
        lines.append("Detector Prompt")
        lines.append(prompt_text)
        lines.append("")
        lines.append("Checklist")
        lines.append("- evidence paragraph_idx are FULL indices")
        lines.append("- snippets < 350 chars")
        lines.append("- include warnings if unsure")
        (thread_dir / filename).write_text("\n".join(lines), encoding="utf-8")

    readme_lines: list[str] = []
    readme_lines.append("# LLM Pilot Pack")
    readme_lines.append("")
    readme_lines.append(f"Created: {timestamp}")
    readme_lines.append(f"Bundle: {to_repo_relative(bundle_paths.bundle_root)}")
    readme_lines.append(f"Prompt templates: {to_repo_relative(prompt_path)}")
    readme_lines.append("")
    readme_lines.append("## Upload To ChatGPT Project")
    readme_lines.append("- Upload prompt_templates_showcase.md once (project-level).")
    readme_lines.append("- For each job, attach the input file listed below.")
    readme_lines.append("")
    readme_lines.append("## Jobs")
    readme_lines.append("| Job ID | Input File | Output Path |")
    readme_lines.append("| --- | --- | --- |")
    for job in jobs:
        readme_lines.append(
            f"| {job['job_id']} | {job['input_path']} | {job['output_path']} |"
        )
    readme_lines.append("")
    readme_lines.append("Thread starters are in thread_starters/.")

    (out_dir / "README.md").write_text("\n".join(readme_lines), encoding="utf-8")

    print(f"Wrote pilot pack to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
