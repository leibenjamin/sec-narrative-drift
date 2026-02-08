from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional, cast

SCRIPT_VERSION = "lab_emit_chatgpt_thread_starters.py@v2"

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLES_ROOT = REPO_ROOT / "bundles"

sys.path.append(str(Path(__file__).resolve().parent))
from lab_prompt_blocks import (  # type: ignore
    build_thread_starter_lines,
    is_supported_detector,
)


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
        help="Deprecated/optional (canonical prompts are generated from lab_prompt_blocks.py).",
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

    output_dir = queue_dir / "thread_starters"
    output_dir.mkdir(parents=True, exist_ok=True)

    for job in jobs:
        ticker = get_str(job.get("ticker"))
        year_from = get_int(job.get("year_from"))
        year_to = get_int(job.get("year_to"))
        detector_id = get_str(job.get("detector_id"))
        input_lens = get_str(job.get("input_lens"))
        input_path = get_str(job.get("input_path"))
        repo_input_path = get_str(job.get("repo_input_path"))
        output_path = get_str(job.get("output_path"))
        source_id = get_str(job.get("source_id")) or "edgar"
        section = get_str(job.get("section")) or "10k_item1a"

        if (
            ticker is None
            or year_from is None
            or year_to is None
            or detector_id is None
            or input_lens is None
            or input_path is None
        ):
            raise SystemExit("Job entry missing required fields.")
        if not is_supported_detector(detector_id):
            raise SystemExit(f"Unsupported detector_id in job: {detector_id}")

        filename = f"{ticker}_{year_from}_{year_to}__{detector_id}__{input_lens}.md"
        lines = build_thread_starter_lines(
            detector_id=detector_id,
            ticker=ticker,
            year_from=year_from,
            year_to=year_to,
            section=section,
            source_id=source_id,
            input_lens=input_lens,
            input_path=input_path,
            output_path=output_path,
            repo_input_path=repo_input_path,
        )
        (output_dir / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {len(jobs)} thread starters to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
