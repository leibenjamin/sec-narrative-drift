from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional, cast

SCRIPT_VERSION = "lab_emit_chatgpt_thread_starters.py@v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLES_ROOT = REPO_ROOT / "bundles"


def read_json_lines(path: Path) -> list[Any]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    payloads: list[Any] = []
    for line in lines:
        if not line.strip():
            continue
        payloads.append(json.loads(line))
    return payloads


def as_str_dict(value: Any) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    output: dict[str, Any] = {}
    for key, item in cast(dict[object, object], value).items():
        if not isinstance(key, str):
            return None
        output[key] = item
    return output


def get_str(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    return None


def get_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def find_latest_queue(root: Path) -> Optional[Path]:
    if not root.exists():
        return None
    candidates: list[Path] = []
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        if not entry.name.startswith("llm_precompute_queue_"):
            continue
        if (entry / "jobs.jsonl").exists():
            candidates.append(entry)
    if not candidates:
        return None
    return sorted(candidates, key=lambda path: path.name)[-1]


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
        trimmed = "\n".join(block_lines).strip()
        output[detector] = trimmed
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Emit ChatGPT thread starter files for LLM jobs.")
    parser.add_argument(
        "--queue-dir",
        default="",
        help="Queue directory (bundles/llm_precompute_queue_*) containing jobs.jsonl",
    )
    parser.add_argument(
        "--jobs",
        default="",
        help="Explicit path to jobs.jsonl (overrides --queue-dir)",
    )
    parser.add_argument(
        "--prompt-templates",
        default="",
        help="Path to prompt_templates_showcase.md (defaults to bundle_root from job)",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    queue_dir = Path(args.queue_dir) if args.queue_dir else None
    jobs_path = Path(args.jobs) if args.jobs else None

    if jobs_path is None:
        if queue_dir is None:
            queue_dir = find_latest_queue(BUNDLES_ROOT)
        if queue_dir is None:
            raise SystemExit("Queue folder not found. Provide --queue-dir or --jobs.")
        jobs_path = queue_dir / "jobs.jsonl"

    if not jobs_path.exists():
        raise SystemExit(f"jobs.jsonl not found: {jobs_path}")

    if queue_dir is None:
        queue_dir = jobs_path.parent

    jobs_payloads = read_json_lines(jobs_path)
    jobs: list[dict[str, Any]] = []
    for payload in jobs_payloads:
        payload_dict = as_str_dict(payload)
        if payload_dict is None:
            raise SystemExit(f"Invalid job entry in {jobs_path}")
        jobs.append(payload_dict)

    prompt_path = Path(args.prompt_templates) if args.prompt_templates else None
    if prompt_path is None:
        bundle_root = get_str(jobs[0].get("bundle_root")) if jobs else None
        if bundle_root:
            candidate = REPO_ROOT / bundle_root / "prompt_templates_showcase.md"
            if candidate.exists():
                prompt_path = candidate
    if prompt_path is None or not prompt_path.exists():
        raise SystemExit("prompt_templates_showcase.md not found. Provide --prompt-templates.")

    detector_prompts = load_detector_prompts(prompt_path)

    output_dir = queue_dir / "thread_starters"
    output_dir.mkdir(parents=True, exist_ok=True)

    for job in jobs:
        ticker = get_str(job.get("ticker"))
        year_from = get_int(job.get("year_from"))
        year_to = get_int(job.get("year_to"))
        detector_id = get_str(job.get("detector_id"))
        lens = get_str(job.get("input_lens"))
        input_path = get_str(job.get("input_path"))
        output_path = get_str(job.get("output_path"))

        if (
            ticker is None
            or year_from is None
            or year_to is None
            or detector_id is None
            or lens is None
            or input_path is None
        ):
            raise SystemExit("Job entry missing required fields.")

        prompt_text = detector_prompts.get(detector_id)
        if prompt_text is None:
            raise SystemExit(f"Prompt template missing for {detector_id}")

        filename = f"{ticker}_{year_from}_{year_to}__{detector_id}__{lens}.md"
        thread_title = f"{ticker} {year_from}-{year_to} {detector_id} ({lens})"

        lines: list[str] = []
        lines.append(f"Thread Title: {thread_title}")
        lines.append("")
        lines.append(f"Attach this input file: {input_path}")
        if output_path:
            lines.append(f"Save output to: {output_path}")
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

        (output_dir / filename).write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {len(jobs)} thread starters to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
