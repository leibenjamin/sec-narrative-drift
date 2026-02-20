from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import sys

from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v3")

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_LAB_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"
DEFAULT_REGISTRY_PATH = PUBLIC_LAB_ROOT / "lab_cases_v1.json"
DEFAULT_OUT_MD = REPO_ROOT / "reports" / "lab_llm_run_manifest.md"
DEFAULT_OUT_JSON = REPO_ROOT / "reports" / "lab_llm_run_manifest.json"

DEFAULT_TICKERS = ("NVDA", "KO", "WM", "GE")
DEFAULT_REQUIRED_START = 2019
DEFAULT_REQUIRED_END = 2024
DEFAULT_INCLUDE_LATEST_AFTER = 2024
DEFAULT_SECTION = "10k_item1a"
DEFAULT_LENS = "deboilerplated"
DEFAULT_SOURCE_ID = "edgar"
LLM_DETECTORS = ("det_llm_delta_brief_v1", "det_llm_excerpt_picker_v1")

sys.path.append(str(Path(__file__).resolve().parent))
from lab_llm_precompute_utils import (  # type: ignore
    InputIndexEntry,
    as_list,
    as_str_dict,
    get_int,
    get_str,
    load_input_index,
    read_json,
    resolve_bundle_paths,
    to_repo_relative,
)
from lab_prompt_blocks import build_thread_starter_lines  # type: ignore


@dataclass(frozen=True)
class DetectorTarget:
    detector_id: str
    expected_output_path: str
    present: bool


@dataclass(frozen=True)
class ManifestEntry:
    ticker: str
    year_from: int
    year_to: int
    section: str
    lens: str
    source_id: str
    case_in_registry: bool
    input_source_path: Optional[str]
    input_source_present: bool
    run_pack_input_path: Optional[str]
    detectors: list[DetectorTarget]

    @property
    def all_outputs_present(self) -> bool:
        if not self.detectors:
            return False
        for detector in self.detectors:
            if not detector.present:
                return False
        return True


def _to_posix(path: Path) -> str:
    return path.as_posix()


def load_registry_pairs(path: Path) -> dict[str, set[tuple[int, int]]]:
    payload = read_json(path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        raise SystemExit(f"Registry JSON root is not an object: {path}")
    cases_raw = as_list(payload_dict.get("cases"))
    if cases_raw is None:
        raise SystemExit(f"Registry missing list field 'cases': {path}")

    pairs_by_ticker: dict[str, set[tuple[int, int]]] = {}
    for case in cases_raw:
        case_dict = as_str_dict(case)
        if case_dict is None:
            continue
        ticker_value = get_str(case_dict.get("ticker"))
        year_from_value = get_int(case_dict.get("year_from"))
        year_to_value = get_int(case_dict.get("year_to"))
        if ticker_value is None or year_from_value is None or year_to_value is None:
            continue
        ticker = ticker_value.upper()
        if ticker not in pairs_by_ticker:
            pairs_by_ticker[ticker] = set()
        pairs_by_ticker[ticker].add((year_from_value, year_to_value))
    return pairs_by_ticker


def build_required_pairs(start_year: int, end_year: int) -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []
    year = start_year
    while year < end_year:
        pairs.append((year, year + 1))
        year += 1
    return pairs


def pick_extra_pair(
    pairs: set[tuple[int, int]],
    include_after_year: int,
) -> Optional[tuple[int, int]]:
    candidates: list[tuple[int, int]] = []
    for year_from, year_to in pairs:
        if year_to <= include_after_year:
            continue
        if year_to != year_from + 1:
            continue
        candidates.append((year_from, year_to))
    if not candidates:
        return None
    candidates_sorted = sorted(candidates, key=lambda pair: (pair[1], pair[0]))
    return candidates_sorted[-1]


def build_target_pairs(
    pairs_by_ticker: dict[str, set[tuple[int, int]]],
    tickers: list[str],
    start_year: int,
    end_year: int,
    include_after_year: int,
) -> dict[str, list[tuple[int, int]]]:
    required_pairs = build_required_pairs(start_year, end_year)
    targets: dict[str, list[tuple[int, int]]] = {}
    for ticker in tickers:
        ticker_pairs = pairs_by_ticker.get(ticker, set())
        ordered: list[tuple[int, int]] = []
        for pair in required_pairs:
            ordered.append(pair)
        extra_pair = pick_extra_pair(ticker_pairs, include_after_year)
        if extra_pair is not None and extra_pair not in ordered:
            ordered.append(extra_pair)
        targets[ticker] = ordered
    return targets


def expected_output_path(
    ticker: str,
    detector_id: str,
    section: str,
    year_from: int,
    year_to: int,
    lens: str,
) -> Path:
    filename = (
        f"lab_{detector_id}_{section}_{year_from}_{year_to}_focuspack_{lens}.json"
    )
    return (
        PUBLIC_LAB_ROOT
        / ticker
        / "outputs"
        / detector_id
        / filename
    )


def get_input_index_entry(
    index: dict[tuple[str, int, int, str, str], InputIndexEntry],
    ticker: str,
    year_from: int,
    year_to: int,
    section: str,
    lens: str,
) -> Optional[InputIndexEntry]:
    key = (ticker.upper(), year_from, year_to, section, lens)
    return index.get(key)


def write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def build_run_pack_meta_payload(
    generated_at_utc: str,
    bundle_root: Path,
    focus_index_path: Path,
    run_pack_dir: Path,
    thread_starters_path: Path,
) -> dict[str, Any]:
    prompt_blocks_path = Path(__file__).resolve().parent / "lab_prompt_blocks.py"
    return {
        "generated_at_utc": generated_at_utc,
        "generator_script_versions": {
            "lab_build_llm_run_manifest.py": SCRIPT_VERSION,
            "lab_prompt_blocks.py": build_script_version(prompt_blocks_path, "v1"),
        },
        "source_bundle_root": to_repo_relative(bundle_root),
        "source_focus_index_path": to_repo_relative(focus_index_path),
        "run_pack_path": to_repo_relative(run_pack_dir),
        "thread_starters_path": to_repo_relative(thread_starters_path),
    }


def entry_to_json_dict(entry: ManifestEntry) -> dict[str, Any]:
    detectors_payload: list[dict[str, Any]] = []
    for detector in entry.detectors:
        detectors_payload.append(
            {
                "detector_id": detector.detector_id,
                "expected_output_path": detector.expected_output_path,
                "present": detector.present,
            }
        )
    return {
        "ticker": entry.ticker,
        "year_from": entry.year_from,
        "year_to": entry.year_to,
        "section": entry.section,
        "lens": entry.lens,
        "source_id": entry.source_id,
        "case_in_registry": entry.case_in_registry,
        "input": {
            "source_path": entry.input_source_path,
            "source_present": entry.input_source_present,
            "run_pack_path": entry.run_pack_input_path,
        },
        "detectors": detectors_payload,
        "all_outputs_present": entry.all_outputs_present,
    }


def build_report_lines(
    generated_at_utc: str,
    registry_path: Path,
    bundle_root: Path,
    run_pack_dir: Optional[Path],
    run_pack_thread_starters: Optional[Path],
    run_pack_meta_path: Optional[Path],
    entries: list[ManifestEntry],
    missing_input_rows: list[str],
) -> list[str]:
    total_pairs = len(entries)
    total_targets = total_pairs * len(LLM_DETECTORS)
    present_targets = 0
    missing_targets = 0
    for entry in entries:
        for detector in entry.detectors:
            if detector.present:
                present_targets += 1
            else:
                missing_targets += 1

    lines: list[str] = []
    lines.append("# Lab LLM Run Manifest")
    lines.append("")
    lines.append(f"Generated at (UTC): {generated_at_utc}")
    lines.append(f"Script: {SCRIPT_VERSION}")
    lines.append(f"Registry: {to_repo_relative(registry_path)}")
    lines.append(f"Inputs bundle root: {to_repo_relative(bundle_root)}")
    lines.append("")
    if run_pack_dir is not None:
        lines.append(f"Run pack: {to_repo_relative(run_pack_dir)}")
    else:
        lines.append("Run pack: (not generated)")
    if run_pack_thread_starters is not None:
        lines.append(f"Thread starters: {to_repo_relative(run_pack_thread_starters)}")
    else:
        lines.append("Thread starters: (not generated)")
    if run_pack_meta_path is not None:
        lines.append(f"Run pack metadata: {to_repo_relative(run_pack_meta_path)}")
    else:
        lines.append("Run pack metadata: (not generated)")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| Pair count | {total_pairs} |")
    lines.append(f"| Detector targets | {total_targets} |")
    lines.append(f"| Present targets | {present_targets} |")
    lines.append(f"| Missing targets | {missing_targets} |")
    lines.append("")
    lines.append("| Ticker | Pair | In registry | Input source | Delta brief | Excerpt picker |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for entry in entries:
        delta_status = "missing"
        excerpt_status = "missing"
        for detector in entry.detectors:
            if detector.detector_id == "det_llm_delta_brief_v1":
                delta_status = "present" if detector.present else "missing"
            if detector.detector_id == "det_llm_excerpt_picker_v1":
                excerpt_status = "present" if detector.present else "missing"
        registry_status = "yes" if entry.case_in_registry else "no"
        input_status = "present" if entry.input_source_present else "missing"
        pair_label = f"{entry.year_from}-{entry.year_to}"
        lines.append(
            f"| {entry.ticker} | {pair_label} | {registry_status} | {input_status} | {delta_status} | {excerpt_status} |"
        )
    lines.append("")
    lines.append("## Missing Canonical LLM Outputs")
    missing_lines_written = False
    for entry in entries:
        for detector in entry.detectors:
            if detector.present:
                continue
            pair_label = f"{entry.year_from}-{entry.year_to}"
            lines.append(
                f"- {entry.ticker} {pair_label} {detector.detector_id}: {detector.expected_output_path}"
            )
            missing_lines_written = True
    if not missing_lines_written:
        lines.append("- none")
    lines.append("")
    lines.append("## Missing Input Sources")
    if missing_input_rows:
        for row in missing_input_rows:
            lines.append(f"- {row}")
    else:
        lines.append("- none")
    return lines


def write_thread_starters(
    path: Path,
    entries: list[ManifestEntry],
) -> None:
    lines: list[str] = []
    lines.append("# Thread Starters")
    lines.append("")
    lines.append("One section per pair + detector. Copy one code block at a time.")
    lines.append("")
    for entry in entries:
        input_name = f"{entry.ticker}_{entry.year_from}_{entry.year_to}_focuspack_{entry.lens}.json"
        run_pack_input_path = f"inputs/{input_name}"
        for detector in entry.detectors:
            heading = (
                f"## {entry.ticker} {entry.year_from}-{entry.year_to} {detector.detector_id}"
            )
            lines.append(heading)
            lines.append("")
            lines.append("```text")
            starter_lines = build_thread_starter_lines(
                detector_id=detector.detector_id,
                ticker=entry.ticker,
                year_from=entry.year_from,
                year_to=entry.year_to,
                section=entry.section,
                source_id=entry.source_id,
                input_lens=f"focuspack_{entry.lens}",
                input_path=run_pack_input_path,
                output_path=detector.expected_output_path,
                repo_input_path=entry.input_source_path,
            )
            lines.extend(starter_lines)
            lines.append("```")
            lines.append("")
    write_text(path, lines)


def find_latest_run_pack_path(run_pack_root: Path) -> Optional[Path]:
    if not run_pack_root.exists():
        return None
    candidates: list[Path] = []
    for entry in run_pack_root.iterdir():
        if not entry.is_dir():
            continue
        if not entry.name.startswith("llm_run_pack_"):
            continue
        candidates.append(entry)
    if not candidates:
        return None
    return sorted(candidates, key=lambda path: path.name)[-1]


def parse_tickers(raw: str) -> list[str]:
    tokens = [token.strip().upper() for token in raw.split(",")]
    tickers: list[str] = []
    for token in tokens:
        if not token:
            continue
        if token not in tickers:
            tickers.append(token)
    return tickers


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build LLM run manifest and local run pack for showcase cases."
    )
    parser.add_argument(
        "--registry",
        default=str(DEFAULT_REGISTRY_PATH),
        help="Path to lab_cases_v1.json",
    )
    parser.add_argument(
        "--tickers",
        default=",".join(DEFAULT_TICKERS),
        help="Comma-separated tickers to include.",
    )
    parser.add_argument(
        "--required-start",
        type=int,
        default=DEFAULT_REQUIRED_START,
        help="First year for required adjacent range (inclusive).",
    )
    parser.add_argument(
        "--required-end",
        type=int,
        default=DEFAULT_REQUIRED_END,
        help="Last year for required adjacent range (inclusive in year_to).",
    )
    parser.add_argument(
        "--include-latest-after",
        type=int,
        default=DEFAULT_INCLUDE_LATEST_AFTER,
        help="Optionally include the most recent adjacent pair with year_to > this value.",
    )
    parser.add_argument(
        "--section",
        default=DEFAULT_SECTION,
        help="Section id for focuspack lookup and expected filenames.",
    )
    parser.add_argument(
        "--lens",
        default=DEFAULT_LENS,
        help="Cleaning lens for the run manifest (default deboilerplated).",
    )
    parser.add_argument(
        "--source-id",
        default=DEFAULT_SOURCE_ID,
        help="Source id to place in thread starters.",
    )
    parser.add_argument(
        "--bundle",
        default="",
        help="Bundle root containing inputs_index_focuspack.json (defaults to latest showcase bundle).",
    )
    parser.add_argument(
        "--inputs-index-focuspack",
        default="",
        help="Override focuspack index path.",
    )
    parser.add_argument(
        "--out-md",
        default=str(DEFAULT_OUT_MD),
        help="Markdown manifest report path.",
    )
    parser.add_argument(
        "--out-json",
        default=str(DEFAULT_OUT_JSON),
        help="Machine-readable manifest JSON path.",
    )
    parser.add_argument(
        "--run-pack-root",
        default=str(REPO_ROOT / "bundles"),
        help="Root directory for local run pack folders.",
    )
    parser.add_argument(
        "--skip-run-pack",
        action="store_true",
        help="Build reports only; do not create bundles/llm_run_pack_<UTCSTAMP>/",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    registry_path = Path(args.registry)
    if not registry_path.exists():
        raise SystemExit(f"Registry not found: {registry_path}")

    tickers = parse_tickers(args.tickers)
    if not tickers:
        raise SystemExit("No valid tickers were parsed from --tickers.")

    bundle_paths = resolve_bundle_paths(
        args.bundle or None,
        args.inputs_index_focuspack or None,
        None,
        None,
    )
    focus_index = load_input_index(bundle_paths.focus_index, bundle_paths.bundle_root)

    pairs_by_ticker = load_registry_pairs(registry_path)
    target_pairs = build_target_pairs(
        pairs_by_ticker=pairs_by_ticker,
        tickers=tickers,
        start_year=args.required_start,
        end_year=args.required_end,
        include_after_year=args.include_latest_after,
    )

    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    entries: list[ManifestEntry] = []
    missing_input_rows: list[str] = []
    for ticker in tickers:
        pairs = target_pairs.get(ticker, [])
        case_pairs = pairs_by_ticker.get(ticker, set())
        for year_from, year_to in pairs:
            input_entry = get_input_index_entry(
                index=focus_index,
                ticker=ticker,
                year_from=year_from,
                year_to=year_to,
                section=args.section,
                lens=args.lens,
            )
            input_source_path: Optional[str] = None
            input_source_present = False
            if input_entry is not None:
                input_source_path = to_repo_relative(input_entry.path)
                if input_entry.path.exists():
                    input_source_present = True
            if not input_source_present:
                missing_input_rows.append(
                    f"{ticker} {year_from}-{year_to} (section={args.section}, lens={args.lens})"
                )

            detectors: list[DetectorTarget] = []
            for detector_id in LLM_DETECTORS:
                expected_path_abs = expected_output_path(
                    ticker=ticker,
                    detector_id=detector_id,
                    section=args.section,
                    year_from=year_from,
                    year_to=year_to,
                    lens=args.lens,
                )
                detectors.append(
                    DetectorTarget(
                        detector_id=detector_id,
                        expected_output_path=_to_posix(expected_path_abs.relative_to(REPO_ROOT)),
                        present=expected_path_abs.exists(),
                    )
                )

            entries.append(
                ManifestEntry(
                    ticker=ticker,
                    year_from=year_from,
                    year_to=year_to,
                    section=args.section,
                    lens=args.lens,
                    source_id=args.source_id,
                    case_in_registry=(year_from, year_to) in case_pairs,
                    input_source_path=input_source_path,
                    input_source_present=input_source_present,
                    run_pack_input_path=None,
                    detectors=detectors,
                )
            )

    run_pack_dir: Optional[Path] = None
    thread_starters_path: Optional[Path] = None
    run_pack_meta_path: Optional[Path] = None
    run_pack_generated_now = False
    run_pack_root = Path(args.run_pack_root)
    entries_with_pack_paths: list[ManifestEntry] = []
    if args.skip_run_pack:
        run_pack_dir = find_latest_run_pack_path(run_pack_root)
        if run_pack_dir is not None:
            candidate_thread_starters = run_pack_dir / "THREAD_STARTERS.md"
            if candidate_thread_starters.exists():
                thread_starters_path = candidate_thread_starters
            candidate_run_pack_meta = run_pack_dir / "RUN_PACK_META.json"
            if candidate_run_pack_meta.exists():
                run_pack_meta_path = candidate_run_pack_meta
        for entry in entries:
            filename = (
                f"{entry.ticker}_{entry.year_from}_{entry.year_to}_focuspack_{entry.lens}.json"
            )
            run_pack_input_rel: Optional[str] = None
            if run_pack_dir is not None:
                candidate_input = run_pack_dir / "inputs" / filename
                if candidate_input.exists():
                    run_pack_input_rel = f"inputs/{filename}"
            entries_with_pack_paths.append(
                ManifestEntry(
                    ticker=entry.ticker,
                    year_from=entry.year_from,
                    year_to=entry.year_to,
                    section=entry.section,
                    lens=entry.lens,
                    source_id=entry.source_id,
                    case_in_registry=entry.case_in_registry,
                    input_source_path=entry.input_source_path,
                    input_source_present=entry.input_source_present,
                    run_pack_input_path=run_pack_input_rel,
                    detectors=entry.detectors,
                )
            )
    else:
        run_pack_generated_now = True
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_pack_dir = run_pack_root / f"llm_run_pack_{stamp}"
        inputs_dir = run_pack_dir / "inputs"
        inputs_dir.mkdir(parents=True, exist_ok=True)
        for entry in entries:
            filename = (
                f"{entry.ticker}_{entry.year_from}_{entry.year_to}_focuspack_{entry.lens}.json"
            )
            run_pack_input_rel = f"inputs/{filename}"
            run_pack_input_abs = run_pack_dir / "inputs" / filename
            if entry.input_source_path is not None:
                source_abs = REPO_ROOT / entry.input_source_path
                if source_abs.exists():
                    shutil.copy2(source_abs, run_pack_input_abs)
            entries_with_pack_paths.append(
                ManifestEntry(
                    ticker=entry.ticker,
                    year_from=entry.year_from,
                    year_to=entry.year_to,
                    section=entry.section,
                    lens=entry.lens,
                    source_id=entry.source_id,
                    case_in_registry=entry.case_in_registry,
                    input_source_path=entry.input_source_path,
                    input_source_present=entry.input_source_present,
                    run_pack_input_path=run_pack_input_rel,
                    detectors=entry.detectors,
                )
            )
        thread_starters_path = run_pack_dir / "THREAD_STARTERS.md"
        write_thread_starters(thread_starters_path, entries_with_pack_paths)
        run_pack_meta_path = run_pack_dir / "RUN_PACK_META.json"
        run_pack_meta_payload = build_run_pack_meta_payload(
            generated_at_utc=generated_at_utc,
            bundle_root=bundle_paths.bundle_root,
            focus_index_path=bundle_paths.focus_index,
            run_pack_dir=run_pack_dir,
            thread_starters_path=thread_starters_path,
        )
        write_json(run_pack_meta_path, run_pack_meta_payload)

    report_lines = build_report_lines(
        generated_at_utc=generated_at_utc,
        registry_path=registry_path,
        bundle_root=bundle_paths.bundle_root,
        run_pack_dir=run_pack_dir,
        run_pack_thread_starters=thread_starters_path,
        run_pack_meta_path=run_pack_meta_path,
        entries=entries_with_pack_paths,
        missing_input_rows=missing_input_rows,
    )
    write_text(Path(args.out_md), report_lines)

    total_pairs = len(entries_with_pack_paths)
    total_targets = total_pairs * len(LLM_DETECTORS)
    present_targets = 0
    missing_targets = 0
    for entry in entries_with_pack_paths:
        for detector in entry.detectors:
            if detector.present:
                present_targets += 1
            else:
                missing_targets += 1

    payload_entries: list[dict[str, Any]] = []
    for entry in entries_with_pack_paths:
        payload_entries.append(entry_to_json_dict(entry))

    manifest_payload: dict[str, Any] = {
        "generated_at_utc": generated_at_utc,
        "script_version": SCRIPT_VERSION,
        "registry_path": to_repo_relative(registry_path),
        "bundle_root": to_repo_relative(bundle_paths.bundle_root),
        "focus_index_path": to_repo_relative(bundle_paths.focus_index),
        "scope": {
            "tickers": tickers,
            "required_start_year": args.required_start,
            "required_end_year": args.required_end,
            "include_latest_after_year": args.include_latest_after,
            "section": args.section,
            "lens": args.lens,
            "source_id": args.source_id,
            "detectors": list(LLM_DETECTORS),
        },
        "run_pack": {
            "generated": run_pack_generated_now,
            "path": to_repo_relative(run_pack_dir) if run_pack_dir is not None else None,
            "thread_starters": (
                to_repo_relative(thread_starters_path)
                if thread_starters_path is not None
                else None
            ),
            "meta": (
                to_repo_relative(run_pack_meta_path)
                if run_pack_meta_path is not None
                else None
            ),
        },
        "summary": {
            "pair_count": total_pairs,
            "target_count": total_targets,
            "present_target_count": present_targets,
            "missing_target_count": missing_targets,
            "missing_input_count": len(missing_input_rows),
        },
        "entries": payload_entries,
    }
    write_json(Path(args.out_json), manifest_payload)

    print(f"Wrote manifest markdown: {args.out_md}")
    print(f"Wrote manifest json: {args.out_json}")
    if run_pack_dir is not None:
        print(f"Wrote run pack: {to_repo_relative(run_pack_dir)}")
        if thread_starters_path is not None:
            print(f"Wrote thread starters: {to_repo_relative(thread_starters_path)}")
        if run_pack_meta_path is not None:
            print(f"Wrote run pack metadata: {to_repo_relative(run_pack_meta_path)}")
    print(
        "Manifest summary: "
        + f"pairs={total_pairs}, targets={total_targets}, "
        + f"present={present_targets}, missing={missing_targets}, "
        + f"missing_inputs={len(missing_input_rows)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
