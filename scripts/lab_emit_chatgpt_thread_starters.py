from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional, cast

SCRIPT_VERSION = "lab_emit_chatgpt_thread_starters.py@v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLES_ROOT = REPO_ROOT / "bundles"

FOCUSPACK_WARNING = "Focuspack is a subset; verify in full compare pane."


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
    highlights_placeholder = (
        '["<tag>"]'
        if detector_id in {"det_llm_delta_brief_v1", "det_llm_excerpt_picker_v1"}
        else "[]"
    )
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
        source_id = get_str(job.get("source_id")) or "edgar"
        section = get_str(job.get("section")) or "10k_item1a"

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

        cleaning_lens = derive_cleaning_lens(lens)
        skeleton_lines = build_skeleton(
            detector_id,
            cleaning_lens,
            source_id,
            ticker,
            section,
            year_from,
            year_to,
            input_path,
        )

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
        lines.append("No extra top-level keys.")
        lines.append("")
        lines.append("EVIDENCE RULES")
        lines.append("- paragraph_idx must be a FULL paragraph index (not focuspack-local).")
        if lens.startswith("focuspack_"):
            lines.append("- Focuspack mapping:")
            lines.append("  - If you cite texts.prev_paragraphs[i], set paragraph_idx = focuspack_meta.selected_prev_indices[i].")
            lines.append("  - If you cite texts.curr_paragraphs[i], set paragraph_idx = focuspack_meta.selected_curr_indices[i].")
        lines.append("- snippet must be copied verbatim from the cited paragraph.")
        lines.append("- snippet is only a short highlight substring; UI displays the full paragraph.")
        lines.append("- max 350 characters per snippet.")
        if detector_id == "det_llm_excerpt_picker_v1":
            lines.append("EXCERPT PICKER INDEX RULES")
            lines.append(
                "- artifacts.selected_prev/curr MUST list FULL paragraph_idx values (0-based FULL indices)."
            )
            lines.append(
                "- If you cite texts.prev_paragraphs[i], paragraph_idx = focuspack_meta.selected_prev_indices[i]."
            )
            lines.append(
                "- If you cite texts.curr_paragraphs[i], paragraph_idx = focuspack_meta.selected_curr_indices[i]."
            )
            lines.append(
                "- Highlights REQUIRED: 1-3 per evidence (non-empty). Validator will fail if empty."
            )
            lines.append(
                "- Before finalizing, verify each snippet is a verbatim substring and <= 350 chars."
            )
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
            lines.append(
                "- Evidence distribution MUST include >=2 blocks for year_from and >=2 blocks for year_to."
            )
            lines.append(
                "- If needed, choose different paragraphs to satisfy the per-year minimum."
            )
            lines.append("- Highlights REQUIRED: 1-3 per evidence (non-empty).")
            lines.append(
                "- Paired baseline REQUIRED for >=2 major claims: reuse identical highlight tags across years."
            )
            lines.append(
                "- Include >=2 inline citations total in artifacts.delta_brief."
            )
            lines.append(
                '- Use one citation format consistently in artifacts.delta_brief.'
            )
            lines.append(
                '- Primary citation format: "YYYY \u00B6NN" where NN is 1-based (NN = paragraph_idx + 1).'
            )
            lines.append(
                '- Fallback citation format: "YYYY para NN" is fully acceptable.'
            )
            lines.append(
                '- Do NOT output "\u00C2\u00B6".'
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
            lines.append(
                "- excerpt picker: artifacts.selected_prev/curr list FULL paragraph_idx values (0-based FULL indices)"
            )
            lines.append(
                "- mapping: prev -> focuspack_meta.selected_prev_indices[i], curr -> focuspack_meta.selected_curr_indices[i]"
            )
            lines.append(
                "- excerpt picker: highlights REQUIRED (1-3 non-empty tags per evidence)"
            )
            lines.append(
                "- self-check: each snippet is verbatim and <= 350 chars"
            )
            lines.append("- reuse highlight tokens across years for paired comparisons")
            lines.append("- avoid buzzword over-weighting (cap AI/ML highlights)")
        lines.append("")
        lines.append("REPAIR MODE")
        lines.append("Given validator errors pasted below, output corrected JSON only.")

        (output_dir / filename).write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {len(jobs)} thread starters to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
