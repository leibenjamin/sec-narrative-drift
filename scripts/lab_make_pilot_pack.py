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

FOCUSPACK_WARNING = "Focuspack is a subset; verify in full compare pane."

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
    InputIndexEntry,
    load_input_index,
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


def derive_cleaning_lens(input_lens: str) -> str:
    if input_lens.startswith("focuspack_"):
        return input_lens[len("focuspack_") :]
    if input_lens.startswith("full_"):
        return input_lens[len("full_") :]
    return input_lens


def build_skeleton(
    detector_id: str,
    cleaning_lens: str,
    source_id: str,
    ticker: str,
    section: str,
    year_from: int,
    year_to: int,
    input_file: str,
) -> list[str]:
    highlights_placeholder = '["<tag>"]' if detector_id == "det_llm_delta_brief_v1" else "[]"
    if detector_id == "det_llm_delta_brief_v1":
        artifacts_lines = [
            '  "artifacts": {',
            '    "delta_brief": "<5-10 sentence summary>"',
            "  },",
        ]
    else:
        artifacts_lines = [
            '  "artifacts": {',
            '    "selected_prev": [],',
            '    "selected_curr": []',
            "  },",
        ]
    skeleton = [
        "{",
        '  "lab_schema_version": "1.0",',
        f'  "detector_id": "{detector_id}",',
        f'  "cleaning_lens": "{cleaning_lens}",',
        f'  "source_id": "{source_id}",',
        f'  "ticker": "{ticker}",',
        f'  "section": "{section}",',
        f'  "year_from": {year_from},',
        f'  "year_to": {year_to},',
    ]
    skeleton.extend(artifacts_lines)
    skeleton.extend(
        [
            '  "evidence": [',
            "    {",
            f'      "year": {year_from},',
            '      "paragraph_idx": 0,',
            '      "snippet": "<verbatim snippet>",',
            '      "why": "<why this matters>",',
            f'      "highlights": {highlights_placeholder}',
            "    }",
            "  ],",
            '  "metrics": {',
            '    "drift_score": null,',
            '    "confidence": 0.50,',
            '    "coverage": null,',
            f'    "warnings": ["{FOCUSPACK_WARNING}"]',
            "  },",
            '  "provenance": {',
            f'    "input_file": "{input_file}"',
            "  }",
            "}",
        ]
    )
    return skeleton


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
        cleaning_lens = derive_cleaning_lens(cast(str, job.get("input_lens")))
        skeleton_lines = build_skeleton(
            detector_id,
            cleaning_lens,
            cast(str, job.get("source_id")),
            cast(str, job.get("ticker")),
            cast(str, job.get("section")),
            cast(int, job.get("year_from")),
            cast(int, job.get("year_to")),
            cast(str, job.get("input_path")),
        )
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
        lines.append("No extra top-level keys.")
        lines.append("")
        lines.append("EVIDENCE RULES")
        lines.append("- paragraph_idx must be a FULL paragraph index (not focuspack-local).")
        if cast(str, job.get("input_lens")).startswith("focuspack_"):
            lines.append("- Focuspack mapping:")
            lines.append("  - If you cite texts.prev_paragraphs[i], set paragraph_idx = focuspack_meta.selected_prev_indices[i].")
            lines.append("  - If you cite texts.curr_paragraphs[i], set paragraph_idx = focuspack_meta.selected_curr_indices[i].")
        lines.append("- snippet must be copied verbatim from the cited paragraph.")
        lines.append("- snippet is only a short highlight substring; UI displays the full paragraph.")
        lines.append("- max 350 characters per snippet.")
        if detector_id == "det_llm_excerpt_picker_v1":
            lines.append("PAIRING + DIVERSITY RULES")
            lines.append(
                "- Ensure at least 2 prev-year excerpts share at least one identical highlight token with"
            )
            lines.append(
                "  at least 2 curr-year excerpts (deterministic pairing)."
            )
            lines.append(
                "- Do not let a single theme (e.g., AI/ML) dominate: at most 2 excerpts total across"
            )
            lines.append(
                "  both years may include AI/ML-related highlights unless the filing is overwhelmingly about it."
            )
        if detector_id == "det_llm_delta_brief_v1":
            lines.append("DELTA BRIEF RULES")
            lines.append("- Evidence distribution target: >=2 blocks per year where possible.")
            lines.append("- Highlights REQUIRED: 1-3 per evidence (non-empty).")
            lines.append(
                "- Paired baseline REQUIRED for >=2 major claims: reuse identical highlight tags across years."
            )
            lines.append(
                '- Delta brief must include >=2 inline citations like "YYYY ¶NN" using FULL indices.'
            )
        lines.append("")
        lines.append("METRICS RULES")
        lines.append("- metrics.confidence MUST be one of {0.25, 0.50, 0.75} (never null).")
        lines.append(f"- metrics.warnings MUST include: \"{FOCUSPACK_WARNING}\"")
        lines.append("")
        lines.append("JSON SKELETON (fill in values, keep keys exact)")
        lines.extend(skeleton_lines)
        lines.append("")
        lines.append("Detector Prompt")
        lines.append(prompt_text)
        lines.append("")
        lines.append("Checklist")
        lines.append("- evidence paragraph_idx are FULL indices")
        lines.append("- snippets < 350 chars")
        lines.append("- include warnings if unsure")
        lines.append("- provenance.input_file matches attached input file")
        if detector_id == "det_llm_excerpt_picker_v1":
            lines.append("- excerpt picker: artifacts.selected_prev/curr list focuspack positions (0-based)")
            lines.append("- reuse highlight tokens across years for paired comparisons")
            lines.append("- avoid buzzword over-weighting (cap AI/ML highlights)")
        lines.append("")
        lines.append("REPAIR MODE")
        lines.append("Given validator errors pasted below, output corrected JSON only.")
        (thread_dir / filename).write_text("\n".join(lines), encoding="utf-8")

    readme_lines: list[str] = []
    readme_lines.append("# LLM Pilot Pack")
    readme_lines.append("")
    readme_lines.append(f"Created: {timestamp}")
    readme_lines.append(f"Bundle: {to_repo_relative(bundle_paths.bundle_root)}")
    readme_lines.append(f"Prompt templates: {to_repo_relative(prompt_path)}")
    readme_lines.append("")
    readme_lines.append("## Upload To ChatGPT Project")
    readme_lines.append("- Upload prompt_templates_showcase.md once (optional; thread starters are self-contained).")
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
