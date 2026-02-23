from __future__ import annotations

import argparse
import csv
import json
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, cast

import sys

SCRIPT_VERSION = "lab_make_llm_precompute_queue.py@v2"

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_LAB_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"

DEFAULT_HERO_PATH = PUBLIC_LAB_ROOT / "lab_showcase_hero_pairs_v2.json"
DEFAULT_REPORT_PATH = REPO_ROOT / "reports" / "llm_precompute_queue_summary.md"
DEFAULT_SHOWCASE_SANITY_REPORT = REPO_ROOT / "reports" / "showcase_queue_bundle_sanity.md"

DETECTORS = ["det_llm_delta_brief_v1", "det_llm_excerpt_picker_v1"]
INPUT_PRIORITY = [
    ("focuspack", "deboilerplated"),
    ("focuspack", "raw"),
    ("full", "deboilerplated"),
    ("full", "raw"),
]

PILOT_PAIRS = {("NVDA", 2021, 2022), ("KO", 2023, 2024)}
UTF8_BOM = b"\xef\xbb\xbf"

sys.path.append(str(Path(__file__).resolve().parent))
from lab_emit_chatgpt_thread_starters import main as emit_thread_starters  # type: ignore
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


def write_jsonl_utf8_no_bom(path: Path, rows: list[dict[str, Any]]) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row))
            handle.write("\n")
    first_three = path.read_bytes()[:3]
    if first_three == UTF8_BOM:
        raise SystemExit(f"UTF-8 BOM detected in {path}")
    return True


def read_jsonl_dicts(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue
        payload = json.loads(trimmed)
        payload_dict = as_str_dict(payload)
        if payload_dict is None:
            raise SystemExit(f"Invalid JSONL row in {path}")
        rows.append(payload_dict)
    return rows


def write_text_utf8_lf(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")


def build_output_target_rows(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for job in jobs:
        job_id = cast(str, job.get("job_id"))
        ticker = cast(str, job.get("ticker"))
        detector_id = cast(str, job.get("detector_id"))
        year_from = cast(int, job.get("year_from"))
        year_to = cast(int, job.get("year_to"))
        input_path = cast(str, job.get("input_path"))
        output_path = cast(str, job.get("output_path"))
        rows.append(
            {
                "job_id": job_id,
                "ticker": ticker,
                "detector_id": detector_id,
                "year_from": year_from,
                "year_to": year_to,
                "input_path": input_path,
                "output_path": output_path,
            }
        )
    return rows


def build_showcase_runbook_lines(
    queue_dir: Path,
    total_jobs: int,
    counts_by_ticker: dict[str, int],
    counts_by_detector: dict[str, int],
) -> list[str]:
    lines: list[str] = []
    lines.append("# Showcase LLM Queue Runbook")
    lines.append("")
    lines.append(f"Source queue: {to_repo_relative(queue_dir)}")
    lines.append(f"Total jobs: {total_jobs}")
    lines.append("")
    lines.append("## Manual execution (ChatGPT Plus)")
    lines.append("1. Open a NEW ChatGPT Plus thread per job in thread_starters/.")
    lines.append("2. Attach the exact input JSON file named in that starter (from inputs/).")
    lines.append("3. Paste the full starter text and submit.")
    lines.append("4. Save JSON output to the exact target in output_targets.jsonl.")
    lines.append("5. Do not change the detector envelope keys.")
    lines.append("")
    lines.append("## FAST MODE (Optional: 1 thread per pair)")
    lines.append("1. For a given ticker/year pair, you may run both detector prompts in one thread.")
    lines.append("2. Run det_llm_delta_brief_v1 first, save to its exact target path.")
    lines.append("3. Then run det_llm_excerpt_picker_v1 in the same thread, save to its exact target path.")
    lines.append("4. Caution: paste the FULL starter text each time; do not use short follow-ups.")
    lines.append("")
    lines.append("## Strict index + evidence rules (must follow)")
    lines.append("- paragraph_idx values must be FULL paragraph indices.")
    lines.append(
        "- For focuspack inputs, map local i -> focuspack_meta.selected_prev_indices[i] / selected_curr_indices[i]."
    )
    lines.append("- snippets must be verbatim and <= 350 chars.")
    lines.append("- highlights are required where the starter specifies them (1-3 non-empty tags).")
    lines.append("")
    lines.append("## Status table: jobs per ticker")
    lines.append("| Ticker | Jobs |")
    lines.append("| --- | --- |")
    for ticker in sorted(counts_by_ticker.keys()):
        lines.append(f"| {ticker} | {counts_by_ticker[ticker]} |")
    lines.append("")
    lines.append("## Status table: jobs per detector")
    lines.append("| Detector | Jobs |")
    lines.append("| --- | --- |")
    for detector_id in sorted(counts_by_detector.keys()):
        lines.append(f"| {detector_id} | {counts_by_detector[detector_id]} |")
    return lines


def build_queue_local_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    localized: list[dict[str, Any]] = []
    for job in jobs:
        ticker = get_str(job.get("ticker"))
        input_path = get_str(job.get("input_path"))
        if ticker is None or input_path is None:
            raise SystemExit("Job missing ticker or input_path")
        source_name = Path(input_path).name
        local_input = (Path("inputs") / ticker / source_name).as_posix()
        job_local = dict(job)
        job_local["input_path"] = local_input
        job_local["repo_input_path"] = input_path.replace("\\", "/")
        localized.append(job_local)
    return localized


def copy_queue_inputs_for_jobs(
    jobs: list[dict[str, Any]], bundle_out_dir: Path
) -> tuple[int, list[str]]:
    copied: set[str] = set()
    missing: list[str] = []
    for job in jobs:
        ticker = get_str(job.get("ticker"))
        input_rel = get_str(job.get("input_path"))
        if ticker is None or input_rel is None:
            missing.append("job missing ticker/input_path")
            continue
        source_path = REPO_ROOT / input_rel
        if not source_path.exists() or not source_path.is_file():
            missing.append(f"missing input source: {source_path}")
            continue
        dest_rel = (Path("inputs") / ticker / source_path.name).as_posix()
        if dest_rel in copied:
            continue
        copied.add(dest_rel)
        dest_path = bundle_out_dir / Path(dest_rel)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest_path)
    return len(copied), missing


def self_check_showcase_queue_zip(
    zip_path: Path,
) -> tuple[bool, int, int, int]:
    errors: list[str] = []
    if not zip_path.exists():
        raise SystemExit(f"Showcase queue zip not found: {zip_path}")

    extract_root = REPO_ROOT / "bundles" / f"_tmp_showcase_selfcheck_{zip_path.stem}"
    if extract_root.exists():
        shutil.rmtree(extract_root, ignore_errors=True)
    extract_root.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_handle:
            zip_handle.extractall(extract_root)

        jobs_path = extract_root / "jobs.jsonl"
        if not jobs_path.exists():
            errors.append("jobs.jsonl missing in extracted showcase queue bundle")
            raise SystemExit("\n".join(errors))
        jobs = read_jsonl_dicts(jobs_path)

        output_targets_path = extract_root / "output_targets.jsonl"
        if not output_targets_path.exists():
            errors.append("output_targets.jsonl missing in extracted showcase queue bundle")
        else:
            if output_targets_path.read_bytes()[:3] == UTF8_BOM:
                errors.append("output_targets.jsonl has UTF-8 BOM")

        thread_starters_count = len(
            [path for path in (extract_root / "thread_starters").glob("*.md") if path.is_file()]
        )
        input_paths_seen: set[str] = set()
        for idx, job in enumerate(jobs):
            input_rel = get_str(job.get("input_path"))
            ticker = get_str(job.get("ticker"))
            year_from = get_int(job.get("year_from"))
            year_to = get_int(job.get("year_to"))
            if (
                input_rel is None
                or ticker is None
                or year_from is None
                or year_to is None
            ):
                errors.append(f"job[{idx}] missing required fields")
                continue
            input_paths_seen.add(input_rel)
            bundled_input = extract_root / Path(input_rel)
            if not bundled_input.exists() or not bundled_input.is_file():
                errors.append(f"missing bundled input for job[{idx}]: {input_rel}")
                continue

            payload = json.loads(bundled_input.read_text(encoding="utf-8-sig"))
            payload_dict = as_str_dict(payload)
            if payload_dict is None:
                errors.append(f"input JSON root invalid: {input_rel}")
                continue
            case = as_str_dict(payload_dict.get("case"))
            if case is None:
                errors.append(f"input JSON missing case object: {input_rel}")
                continue
            case_ticker = get_str(case.get("ticker"))
            case_year_from = get_int(case.get("year_from"))
            case_year_to = get_int(case.get("year_to"))
            if case_ticker != ticker:
                errors.append(
                    f"ticker mismatch for {input_rel}: case={case_ticker} job={ticker}"
                )
            if case_year_from != year_from or case_year_to != year_to:
                errors.append(
                    "year mismatch for "
                    + input_rel
                    + f": case={case_year_from}-{case_year_to} job={year_from}-{year_to}"
                )

        if errors:
            joined = "\n".join(f"- {entry}" for entry in errors)
            raise SystemExit(f"Showcase queue bundle self-check failed:\n{joined}")
        return True, len(jobs), thread_starters_count, len(input_paths_seen)
    finally:
        shutil.rmtree(extract_root, ignore_errors=True)


def write_showcase_queue_sanity_report(
    path: Path,
    queue_bundle_dir: Path,
    queue_zip_path: Path,
    jobs_count: int,
    thread_starters_count: int,
    inputs_copied_count: int,
    missing_items: list[str],
) -> None:
    lines: list[str] = []
    lines.append("# Showcase Queue Bundle Sanity")
    lines.append("")
    lines.append(f"Bundle dir: {to_repo_relative(queue_bundle_dir)}")
    lines.append(f"Bundle zip: {to_repo_relative(queue_zip_path)}")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| jobs | {jobs_count} |")
    lines.append(f"| thread_starters | {thread_starters_count} |")
    lines.append(f"| inputs_copied | {inputs_copied_count} |")
    lines.append("")
    lines.append("## Missing Items")
    if missing_items:
        for item in missing_items:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    write_text_utf8_lf(path, lines)


def build_showcase_queue_bundle(
    jobs: list[dict[str, Any]],
    queue_dir: Path,
    bundle_out_dir: Path,
    prompt_templates_path: Path,
    timestamp: str,
) -> tuple[Path, Path, bool, bool, int, int, int, list[str]]:
    bundle_out_dir.mkdir(parents=True, exist_ok=True)
    local_jobs = build_queue_local_jobs(jobs)
    _inputs_copied_count, missing_inputs = copy_queue_inputs_for_jobs(jobs, bundle_out_dir)
    if missing_inputs:
        details = "\n".join(f"- {item}" for item in missing_inputs)
        raise SystemExit(f"Missing queue inputs while building bundle:\n{details}")

    jobs_jsonl_path = bundle_out_dir / "jobs.jsonl"
    write_jsonl_utf8_no_bom(jobs_jsonl_path, local_jobs)

    emit_rc = emit_thread_starters(
        [
            "--jobs",
            str(jobs_jsonl_path),
            "--prompt-templates",
            str(prompt_templates_path),
        ]
    )
    if emit_rc != 0:
        raise SystemExit(
            f"Thread starter generation failed for showcase queue bundle {bundle_out_dir}"
        )
    thread_starters_dir = bundle_out_dir / "thread_starters"
    thread_files = sorted(path for path in thread_starters_dir.glob("*.md") if path.is_file())
    if not thread_files:
        raise SystemExit(f"No thread starter files found in {thread_starters_dir}")

    output_targets_rows = build_output_target_rows(local_jobs)
    output_targets_path = bundle_out_dir / "output_targets.jsonl"
    bom_check_passed = write_jsonl_utf8_no_bom(output_targets_path, output_targets_rows)

    counts_by_ticker: dict[str, int] = {}
    counts_by_detector: dict[str, int] = {}
    for job in local_jobs:
        ticker = cast(str, job.get("ticker"))
        detector_id = cast(str, job.get("detector_id"))
        counts_by_ticker[ticker] = counts_by_ticker.get(ticker, 0) + 1
        counts_by_detector[detector_id] = counts_by_detector.get(detector_id, 0) + 1

    readme_lines = build_showcase_runbook_lines(
        queue_dir=queue_dir,
        total_jobs=len(local_jobs),
        counts_by_ticker=counts_by_ticker,
        counts_by_detector=counts_by_detector,
    )
    write_text_utf8_lf(bundle_out_dir / "README.md", readme_lines)

    zip_path = REPO_ROOT / f"chatgpt_bundle_showcase_llm_queue_{timestamp}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_handle:
        for path in sorted(bundle_out_dir.rglob("*")):
            if path.is_file():
                zip_handle.write(path, path.relative_to(bundle_out_dir).as_posix())

    self_check_passed, jobs_count, thread_count, input_count = self_check_showcase_queue_zip(
        zip_path
    )
    return (
        bundle_out_dir,
        zip_path,
        bom_check_passed,
        self_check_passed,
        jobs_count,
        thread_count,
        input_count,
        missing_inputs,
    )


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
    parser.add_argument(
        "--make-showcase-queue-bundle",
        action="store_true",
        help=(
            "Also build bundles/showcase_llm_queue_<timestamp>/ with inputs, "
            "thread_starters, output_targets.jsonl, README, and zip."
        ),
    )
    parser.add_argument(
        "--showcase-queue-out-dir",
        default="",
        help="Override showcase queue bundle output directory.",
    )
    parser.add_argument(
        "--showcase-sanity-report",
        default=str(DEFAULT_SHOWCASE_SANITY_REPORT),
        help="Sanity report output path for showcase queue bundle.",
    )
    parser.add_argument(
        "--self-check-showcase-zip",
        default="",
        help="Run showcase queue zip self-check and exit.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.self_check_showcase_zip:
        self_check_passed, jobs_count, thread_count, input_count = (
            self_check_showcase_queue_zip(Path(args.self_check_showcase_zip))
        )
        print(
            "Showcase queue self-check: "
            + ("PASS" if self_check_passed else "FAIL")
            + f" (jobs={jobs_count}, thread_starters={thread_count}, inputs={input_count})"
        )
        return 0

    hero_path = Path(args.hero)
    if not hero_path.exists():
        raise SystemExit(f"Hero pairs file not found: {hero_path}")

    bundle_paths = resolve_bundle_paths(
        args.bundle or None,
        args.inputs_index_focuspack or None,
        args.inputs_index_full or None,
        args.prompt_templates or None,
    )

    if bundle_paths.focus_index is None:
        raise SystemExit("Focus index path not resolved — provide --inputs-index-focuspack or --bundle")
    if bundle_paths.full_index is None:
        raise SystemExit("Full index path not resolved — provide --inputs-index-full or --bundle")
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
    if args.make_showcase_queue_bundle:
        if prompt_path is None:
            raise SystemExit(
                "prompt_templates_showcase.md not found. Provide --prompt-templates when building showcase queue bundle."
            )
        emit_rc = emit_thread_starters(["--queue-dir", str(out_dir)])
        if emit_rc != 0:
            raise SystemExit(
                f"Thread starter generation failed for queue {out_dir} (exit {emit_rc})"
            )
        showcase_out_dir = (
            Path(args.showcase_queue_out_dir)
            if args.showcase_queue_out_dir
            else REPO_ROOT / "bundles" / f"showcase_llm_queue_{timestamp}"
        )
        (
            _,
            showcase_zip_path,
            bom_check_passed,
            self_check_passed,
            sanity_jobs_count,
            sanity_thread_count,
            sanity_inputs_count,
            missing_items,
        ) = build_showcase_queue_bundle(
            jobs=jobs,
            queue_dir=out_dir,
            bundle_out_dir=showcase_out_dir,
            prompt_templates_path=prompt_path,
            timestamp=timestamp,
        )
        sanity_report_path = Path(args.showcase_sanity_report)
        write_showcase_queue_sanity_report(
            path=sanity_report_path,
            queue_bundle_dir=showcase_out_dir,
            queue_zip_path=showcase_zip_path,
            jobs_count=sanity_jobs_count,
            thread_starters_count=sanity_thread_count,
            inputs_copied_count=sanity_inputs_count,
            missing_items=missing_items,
        )
        print(f"Wrote showcase queue bundle to {showcase_out_dir}")
        print(f"Wrote showcase queue zip to {showcase_zip_path}")
        print(f"Wrote showcase queue sanity report to {sanity_report_path}")
        print(
            "BOM check: "
            + ("passed" if bom_check_passed else "failed")
            + f" for {showcase_out_dir / 'output_targets.jsonl'}"
        )
        print(
            "Showcase queue self-check: "
            + ("passed" if self_check_passed else "failed")
            + f" for {showcase_zip_path}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
