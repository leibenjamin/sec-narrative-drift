from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, cast

import sys

SCRIPT_VERSION = "lab_make_llm_precompute_queue.py@v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_LAB_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"

DEFAULT_HERO_PATH = PUBLIC_LAB_ROOT / "lab_showcase_hero_pairs_v2.json"
DEFAULT_REPORT_PATH = REPO_ROOT / "reports" / "llm_precompute_queue_summary.md"

DETECTORS = ["det_llm_delta_brief_v1", "det_llm_excerpt_picker_v1"]
INPUT_PRIORITY = [
    ("focuspack", "deboilerplated"),
    ("focuspack", "raw"),
    ("full", "deboilerplated"),
    ("full", "raw"),
]

PILOT_PAIRS = {("NVDA", 2021, 2022), ("KO", 2023, 2024)}

sys.path.append(str(Path(__file__).resolve().parent))
from lab_llm_precompute_utils import (  # type: ignore
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


def load_hero_pairs(path: Path) -> tuple[str, str, dict[str, list[tuple[int, int]]]]:
    payload = read_json(path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        raise SystemExit("Hero pairs JSON invalid.")
    section = get_str(payload_dict.get("section")) or "10k_item1a"
    source_id = get_str(payload_dict.get("source_id")) or "edgar"
    heroes_raw = payload_dict.get("hero_pairs_per_ticker")
    if not isinstance(heroes_raw, dict):
        raise SystemExit("Hero pairs JSON missing hero_pairs_per_ticker.")

    heroes: dict[str, list[tuple[int, int]]] = {}
    for ticker, entries in cast(dict[str, list[Any]], heroes_raw).items():
        pairs: list[tuple[int, int]] = []
        for entry in entries:
            entry_dict = as_str_dict(entry)
            if entry_dict is None:
                continue
            year_from = get_int(entry_dict.get("year_from"))
            year_to = get_int(entry_dict.get("year_to"))
            if year_from is None or year_to is None:
                continue
            pairs.append((year_from, year_to))
        if pairs:
            heroes[ticker.upper()] = pairs
    return section, source_id, heroes


def pick_input(
    ticker: str,
    year_from: int,
    year_to: int,
    section: str,
    focus_index: dict[tuple[str, int, int, str, str], InputIndexEntry],
    full_index: dict[tuple[str, int, int, str, str], InputIndexEntry],
) -> tuple[Optional[SelectedInput], list[str]]:
    errors: list[str] = []
    for input_kind, lens in INPUT_PRIORITY:
        key = (ticker.upper(), year_from, year_to, section, lens)
        entry = focus_index.get(key) if input_kind == "focuspack" else full_index.get(key)
        if entry is None:
            continue
        if not entry.path.exists():
            errors.append(f"{input_kind}_{lens} missing file: {entry.path}")
            continue
        lens_key = f"{input_kind}_{lens}"
        return SelectedInput(entry=entry, lens_key=lens_key, input_kind=input_kind), errors
    return None, errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build LLM precompute queue for hero pairs.")
    parser.add_argument(
        "--hero",
        default=str(DEFAULT_HERO_PATH),
        help="Hero pairs JSON path",
    )
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
        help="Output queue directory (default bundles/llm_precompute_queue_<timestamp>)",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT_PATH),
        help="Summary report output path",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    hero_path = Path(args.hero)
    if not hero_path.exists():
        raise SystemExit(f"Hero pairs file not found: {hero_path}")

    bundle_paths = resolve_bundle_paths(
        args.bundle or None,
        args.inputs_index_focuspack or None,
        args.inputs_index_full or None,
        args.prompt_templates or None,
    )

    focus_index = load_input_index(bundle_paths.focus_index, bundle_paths.bundle_root)
    full_index = load_input_index(bundle_paths.full_index, bundle_paths.bundle_root)

    section, source_id, hero_pairs = load_hero_pairs(hero_path)

    hero_list: list[tuple[str, int, int]] = []
    for ticker in sorted(hero_pairs.keys()):
        pairs = hero_pairs[ticker]
        for year_from, year_to in sorted(pairs):
            hero_list.append((ticker, year_from, year_to))

    jobs: list[dict[str, Any]] = []
    missing: list[str] = []

    for ticker, year_from, year_to in hero_list:
        selected, errors = pick_input(
            ticker, year_from, year_to, section, focus_index, full_index
        )
        if selected is None:
            detail = "; ".join(errors) if errors else "no matching input found"
            missing.append(f"{ticker} {year_from}-{year_to}: {detail}")
            continue
        for detector_id in DETECTORS:
            output_path = (
                PUBLIC_LAB_ROOT
                / "llm_outputs"
                / detector_id
                / ticker
                / f"lab_{detector_id}_{section}_{year_from}_{year_to}_{selected.lens_key}.json"
            )
            job_id = f"{ticker}_{year_from}_{year_to}_{detector_id}_{selected.lens_key}"
            jobs.append(
                {
                    "job_id": job_id,
                    "ticker": ticker,
                    "section": section,
                    "year_from": year_from,
                    "year_to": year_to,
                    "detector_id": detector_id,
                    "source_id": source_id,
                    "input_lens": selected.lens_key,
                    "input_path": to_repo_relative(selected.entry.path),
                    "output_path": to_repo_relative(output_path),
                    "bundle_root": to_repo_relative(bundle_paths.bundle_root),
                }
            )

    if missing:
        missing_lines = "\n".join(missing)
        raise SystemExit(f"Missing inputs for hero pairs:\n{missing_lines}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / "bundles" / f"llm_precompute_queue_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    jobs_jsonl = out_dir / "jobs.jsonl"
    with jobs_jsonl.open("w", encoding="utf-8") as handle:
        for job in jobs:
            handle.write(json.dumps(job, sort_keys=True))
            handle.write("\n")

    jobs_csv = out_dir / "jobs.csv"
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
    ]
    with jobs_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for job in jobs:
            writer.writerow({key: job.get(key, "") for key in fieldnames})

    prompt_path = bundle_paths.prompt_templates
    prompt_ref = to_repo_relative(prompt_path) if prompt_path else "(prompt_templates_showcase.md missing)"

    instructions_lines: list[str] = []
    instructions_lines.append("# LLM Precompute Instructions")
    instructions_lines.append("")
    instructions_lines.append(f"Created: {timestamp}")
    instructions_lines.append(f"Hero pairs: {to_repo_relative(hero_path)}")
    instructions_lines.append(f"Bundle: {to_repo_relative(bundle_paths.bundle_root)}")
    instructions_lines.append(f"Prompt templates: {prompt_ref}")
    instructions_lines.append(f"Jobs: {len(jobs)}")
    instructions_lines.append("")
    instructions_lines.append("## How To Run Manually")
    instructions_lines.append("1. Open the input JSON listed for the job below.")
    instructions_lines.append("2. Use the appropriate prompt template for the detector.")
    instructions_lines.append("3. Run the detector in your LLM UI with the input JSON.")
    instructions_lines.append("4. Save the output JSON to the output target path.")
    instructions_lines.append("5. Ensure the output follows the Lab envelope fields.")
    instructions_lines.append("")
    instructions_lines.append(
        "Reminder: cite FULL paragraph indices using focuspack_meta.selected_*_indices mapping."
    )
    instructions_lines.append("")
    instructions_lines.append("## Jobs")
    instructions_lines.append(
        "| Job ID | Ticker | Pair | Detector | Input | Output |"
    )
    instructions_lines.append("| --- | --- | --- | --- | --- | --- |")
    for job in jobs:
        pair = f"{job['year_from']}-{job['year_to']}"
        instructions_lines.append(
            "| "
            + " | ".join(
                [
                    job["job_id"],
                    job["ticker"],
                    pair,
                    job["detector_id"],
                    job["input_path"],
                    job["output_path"],
                ]
            )
            + " |"
        )

    (out_dir / "precompute_instructions.md").write_text(
        "\n".join(instructions_lines), encoding="utf-8"
    )

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    counts_by_ticker: dict[str, int] = {}
    counts_by_detector: dict[str, int] = {}
    counts_by_input: dict[str, int] = {}
    for job in jobs:
        ticker = cast(str, job.get("ticker"))
        detector_id = cast(str, job.get("detector_id"))
        input_lens = cast(str, job.get("input_lens"))
        counts_by_ticker[ticker] = counts_by_ticker.get(ticker, 0) + 1
        counts_by_detector[detector_id] = counts_by_detector.get(detector_id, 0) + 1
        counts_by_input[input_lens] = counts_by_input.get(input_lens, 0) + 1

    best_first: list[dict[str, Any]] = []
    for job in jobs:
        pair_key = (job["ticker"], job["year_from"], job["year_to"])
        if pair_key in PILOT_PAIRS:
            best_first.append(job)

    report_lines: list[str] = []
    report_lines.append("# LLM Precompute Queue Summary")
    report_lines.append("")
    report_lines.append(f"Created: {timestamp}")
    report_lines.append(f"Queue folder: {to_repo_relative(out_dir)}")
    report_lines.append(f"Hero pairs: {to_repo_relative(hero_path)}")
    report_lines.append(f"Bundle: {to_repo_relative(bundle_paths.bundle_root)}")
    report_lines.append(f"Script: {SCRIPT_VERSION}")
    report_lines.append("")
    report_lines.append("## Counts By Ticker")
    report_lines.append("| Ticker | Jobs |")
    report_lines.append("| --- | --- |")
    for ticker in sorted(counts_by_ticker.keys()):
        report_lines.append(f"| {ticker} | {counts_by_ticker[ticker]} |")
    report_lines.append("")
    report_lines.append("## Counts By Detector")
    report_lines.append("| Detector | Jobs |")
    report_lines.append("| --- | --- |")
    for detector_id in sorted(counts_by_detector.keys()):
        report_lines.append(f"| {detector_id} | {counts_by_detector[detector_id]} |")
    report_lines.append("")
    report_lines.append("## Counts By Input Type")
    report_lines.append("| Input Lens | Jobs |")
    report_lines.append("| --- | --- |")
    for input_lens in sorted(counts_by_input.keys()):
        report_lines.append(f"| {input_lens} | {counts_by_input[input_lens]} |")
    report_lines.append("")
    report_lines.append("## Best First Jobs")
    report_lines.append("| Priority | Ticker | Pair | Detector | Input Lens | Input | Output |")
    report_lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for job in best_first:
        pair = f"{job['year_from']}-{job['year_to']}"
        report_lines.append(
            "| "
            + " | ".join(
                [
                    "PILOT FIRST",
                    job["ticker"],
                    pair,
                    job["detector_id"],
                    job["input_lens"],
                    job["input_path"],
                    job["output_path"],
                ]
            )
            + " |"
        )

    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Wrote queue to {out_dir}")
    print(f"Wrote summary to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
