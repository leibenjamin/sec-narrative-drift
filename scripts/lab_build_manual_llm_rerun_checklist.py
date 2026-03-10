from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, cast

from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v4")

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "reports" / "lab_llm_run_manifest.json"
DEFAULT_OUT_PATH = REPO_ROOT / "reports" / "lab_llm_manual_rerun_checklist.md"
BUNDLES_ROOT = REPO_ROOT / "bundles"

TICKER_SORT_ORDER = {"NVDA": 0, "KO": 1, "WM": 2, "GE": 3}
DETECTOR_SORT_ORDER = {
    "det_llm_delta_brief_v1": 0,
    "det_llm_excerpt_picker_v1": 1,
}


@dataclass(frozen=True)
class Job:
    job_id: str
    ticker: str
    year_from: int
    year_to: int
    lens: str
    detector_id: str
    input_rel_path: str
    input_year_prev_rel_path: str
    input_year_curr_rel_path: str
    output_rel_path: str
    thread_title: str


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def as_dict(value: object) -> Optional[dict[str, object]]:
    if not isinstance(value, dict):
        return None
    raw = cast(dict[object, object], value)
    out: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            return None
        out[key] = item
    return out


def as_list(value: object) -> Optional[list[object]]:
    if isinstance(value, list):
        return cast(list[object], value)
    return None


def get_str(value: object) -> Optional[str]:
    if isinstance(value, str):
        return value
    return None


def get_int(value: object) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")


def _to_repo_posix(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def find_latest_run_pack_path() -> Optional[str]:
    if not BUNDLES_ROOT.exists():
        return None
    candidates: list[Path] = []
    for entry in BUNDLES_ROOT.iterdir():
        if not entry.is_dir():
            continue
        if not entry.name.startswith("llm_run_pack_"):
            continue
        candidates.append(entry)
    if not candidates:
        return None
    latest = sorted(candidates, key=lambda item: item.name)[-1]
    return _to_repo_posix(latest)


def ticker_sort_key(ticker: str) -> int:
    return TICKER_SORT_ORDER.get(ticker.upper(), 999)


def detector_sort_key(detector_id: str) -> int:
    return DETECTOR_SORT_ORDER.get(detector_id, 999)


def build_jobs(
    manifest_path: Path,
) -> tuple[list[Job], str, str, str, str, str, str, str]:
    payload = read_json(manifest_path)
    root = as_dict(payload)
    if root is None:
        raise SystemExit(f"Manifest root is not an object: {manifest_path}")

    generated_at_utc = get_str(root.get("generated_at_utc")) or "<missing>"
    bundle_root = get_str(root.get("bundle_root")) or "<missing>"
    campaign_obj = as_dict(root.get("campaign")) or {}
    campaign_id = get_str(campaign_obj.get("campaign_id")) or "<missing>"
    model_provider = get_str(campaign_obj.get("model_provider")) or "<missing>"
    model_name = get_str(campaign_obj.get("model_name")) or "<missing>"
    run_pack = as_dict(root.get("run_pack")) or {}
    run_pack_path = get_str(run_pack.get("path")) or "<missing>"
    thread_starters = get_str(run_pack.get("thread_starters")) or "<missing>"
    if run_pack_path == "<missing>" or not run_pack_path:
        fallback_run_pack_path = find_latest_run_pack_path()
        if fallback_run_pack_path:
            run_pack_path = fallback_run_pack_path
            fallback_thread_starters = (
                REPO_ROOT / run_pack_path / "THREAD_STARTERS.md"
            )
            if fallback_thread_starters.exists():
                thread_starters = _to_repo_posix(fallback_thread_starters)

    entries = as_list(root.get("entries"))
    if entries is None:
        raise SystemExit(f"Manifest missing entries[]: {manifest_path}")

    pending_jobs: list[tuple[str, int, int, str, str, str, str, str, str]] = []
    for entry_any in entries:
        entry = as_dict(entry_any)
        if entry is None:
            continue
        ticker = (get_str(entry.get("ticker")) or "").upper()
        year_from = get_int(entry.get("year_from"))
        year_to = get_int(entry.get("year_to"))
        lens = get_str(entry.get("lens")) or ""
        input_obj = as_dict(entry.get("input")) or {}
        input_rel = get_str(input_obj.get("run_pack_path")) or ""
        input_year_prev_rel = get_str(input_obj.get("run_pack_year_prev_path")) or ""
        input_year_curr_rel = get_str(input_obj.get("run_pack_year_curr_path")) or ""
        detectors = as_list(entry.get("detectors")) or []
        if not ticker or year_from is None or year_to is None or not lens:
            continue
        for detector_any in detectors:
            detector = as_dict(detector_any)
            if detector is None:
                continue
            detector_id = get_str(detector.get("detector_id")) or ""
            output_rel = get_str(detector.get("expected_output_path")) or ""
            if not detector_id or not output_rel:
                continue
            pending_jobs.append(
                (
                    ticker,
                    year_from,
                    year_to,
                    lens,
                    detector_id,
                    input_rel,
                    input_year_prev_rel,
                    input_year_curr_rel,
                    output_rel,
                )
            )

    pending_jobs.sort(
        key=lambda item: (
            ticker_sort_key(item[0]),
            item[1],
            item[2],
            detector_sort_key(item[4]),
            item[4],
        )
    )

    jobs: list[Job] = []
    for idx, item in enumerate(pending_jobs, start=1):
        (
            ticker,
            year_from,
            year_to,
            lens,
            detector_id,
            input_rel,
            input_year_prev_rel,
            input_year_curr_rel,
            output_rel,
        ) = item
        job_id = f"J{idx:02d}"
        thread_title = f"{ticker} {year_from}-{year_to} {detector_id} ({lens})"
        jobs.append(
            Job(
                job_id=job_id,
                ticker=ticker,
                year_from=year_from,
                year_to=year_to,
                lens=lens,
                detector_id=detector_id,
                input_rel_path=input_rel,
                input_year_prev_rel_path=input_year_prev_rel,
                input_year_curr_rel_path=input_year_curr_rel,
                output_rel_path=output_rel,
                thread_title=thread_title,
            )
        )

    return (
        jobs,
        generated_at_utc,
        bundle_root,
        run_pack_path,
        thread_starters,
        campaign_id,
        model_provider,
        model_name,
    )


def build_lines(
    jobs: list[Job],
    generated_at_utc: str,
    bundle_root: str,
    run_pack_path: str,
    thread_starters: str,
    campaign_id: str,
    model_provider: str,
    model_name: str,
) -> list[str]:
    lines: list[str] = []
    lines.append(f"# Manual LLM Rerun Checklist ({len(jobs)} Jobs)")
    lines.append("")
    lines.append(f"- script: `{SCRIPT_VERSION}`")
    lines.append(f"- manifest_generated_at_utc: `{generated_at_utc}`")
    lines.append(f"- bundle_root: `{bundle_root}`")
    lines.append(f"- campaign_id: `{campaign_id}`")
    lines.append(f"- model_provider: `{model_provider}`")
    lines.append(f"- model_name: `{model_name}`")
    lines.append(f"- run_pack: `{run_pack_path}`")
    lines.append(f"- thread_starters: `{thread_starters}`")
    lines.append(f"- job_count: `{len(jobs)}`")
    lines.append("")
    lines.append("## Start Here")
    lines.append("1. Open `docs/lab/04_chatgpt_project_setup.md` and paste the Project Instructions into ChatGPT Desktop Project settings.")
    lines.append("2. Use one ChatGPT thread per job (strict isolation).")
    lines.append("3. For each job, attach the exact pair manifest plus both year files from run pack `inputs/`, then paste the matching starter from `THREAD_STARTERS.md`.")
    lines.append("4. Save JSON directly to the exact output path listed for that job.")
    lines.append("5. After each ticker wave, run the validator command in the Validation Loop section.")
    lines.append("")
    lines.append("## Validation Loop")
    lines.append("- After each wave:")
    lines.append(
        "  - "
        + "`python scripts/lab_validate_llm_manifest_outputs.py "
        + f"--campaign-id {campaign_id} "
        + "--allow-missing --allow-invalid "
        + "--report reports/lab_llm_manifest_validation.md`"
    )
    lines.append("- After all 42 jobs:")
    lines.append(
        "  - "
        + "`python scripts/lab_validate_llm_manifest_outputs.py "
        + f"--campaign-id {campaign_id} "
        + "--report reports/lab_llm_manifest_validation.md`"
    )
    lines.append("  - `npm run lab:predeploy`")
    lines.append("  - `npm run lab:readiness`")
    lines.append("  - `npm run build`")
    lines.append("")
    lines.append("## Quick Pass (8 jobs)")
    lines.append("If you want early visible quality gains before completing all 42 jobs, do these first:")
    lines.append("- NVDA 2021-2022: delta brief + excerpt picker")
    lines.append("- KO 2023-2024: delta brief + excerpt picker")
    lines.append("- WM 2023-2024: delta brief + excerpt picker")
    lines.append("- GE 2022-2023: delta brief + excerpt picker")
    lines.append("")

    ticker_buckets: dict[str, list[Job]] = {}
    for job in jobs:
        ticker_buckets.setdefault(job.ticker, []).append(job)

    for ticker in ("NVDA", "KO", "WM", "GE"):
        wave_jobs = ticker_buckets.get(ticker, [])
        if not wave_jobs:
            continue
        lines.append(f"## Wave: {ticker} ({len(wave_jobs)} jobs)")
        lines.append("")
        lines.append("### Status")
        lines.append("| Job | Thread | Saved | Validated | Pair | Detector |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for job in wave_jobs:
            pair = f"{job.year_from}-{job.year_to}"
            lines.append(
                f"| {job.job_id} | [ ] | [ ] | [ ] | {pair} | `{job.detector_id}` |"
            )
        lines.append("")

        lines.append("### Job Details")
        lines.append("| Job | Pair Manifest | Year Prev | Year Curr | Output | Thread Title |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for job in wave_jobs:
            input_pair_path = (
                f"{run_pack_path}/{job.input_rel_path}"
                if run_pack_path != "<missing>" and job.input_rel_path
                else job.input_rel_path or "<missing>"
            )
            input_prev_path = (
                f"{run_pack_path}/{job.input_year_prev_rel_path}"
                if run_pack_path != "<missing>" and job.input_year_prev_rel_path
                else job.input_year_prev_rel_path or "<missing>"
            )
            input_curr_path = (
                f"{run_pack_path}/{job.input_year_curr_rel_path}"
                if run_pack_path != "<missing>" and job.input_year_curr_rel_path
                else job.input_year_curr_rel_path or "<missing>"
            )
            lines.append(
                f"| {job.job_id} | `{input_pair_path}` | `{input_prev_path}` | `{input_curr_path}` | `{job.output_rel_path}` | `{job.thread_title}` |"
            )
        lines.append("")

    lines.append("## Notes")
    lines.append("- Keep `provenance.input_file` exactly `inputs/pair/<TICKER>_<FROM>_<TO>_<SECTION>_<LENS>_<SOURCE>.json`.")
    lines.append(f"- Keep `provenance.model_provider` exactly `{model_provider}` (required).")
    lines.append(f"- Keep `provenance.model_name` exactly `{model_name}` (required).")
    lines.append("- Keep `provenance.run_label` required with `YYYY-MM-DD_` prefix (example: `2026-03-06_openai_chatgpt54ext_fullsec_real_nvda_2024_2025_outline_compare`).")
    lines.append("- Do not include extra provenance keys.")
    lines.append('- Delta citations must be ASCII-only format: `"YYYY para NN"`.')
    lines.append("- Do not add top-level keys such as `section_id`.")
    lines.append("- Keep snippets verbatim and <=350 chars; highlights must be non-empty.")
    return lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a manual ChatGPT Desktop rerun checklist from lab_llm_run_manifest.json."
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST_PATH),
        help="Path to reports/lab_llm_run_manifest.json",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT_PATH),
        help="Path to write markdown checklist.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = REPO_ROOT / manifest_path
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")

    (
        jobs,
        generated_at_utc,
        bundle_root,
        run_pack_path,
        thread_starters,
        campaign_id,
        model_provider,
        model_name,
    ) = build_jobs(manifest_path)
    lines = build_lines(
        jobs=jobs,
        generated_at_utc=generated_at_utc,
        bundle_root=bundle_root,
        run_pack_path=run_pack_path,
        thread_starters=thread_starters,
        campaign_id=campaign_id,
        model_provider=model_provider,
        model_name=model_name,
    )
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path
    write_text(out_path, lines)
    print(
        f"Wrote manual rerun checklist: {out_path} (jobs={len(jobs)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
