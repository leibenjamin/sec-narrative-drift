from __future__ import annotations

import argparse
import json
import shutil
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import sys

from lab_script_version import build_script_version
from lab_output_tracks import (  # type: ignore
    CORE4_SHOWCASE_TICKERS,
    DEFAULT_PRIMARY_LLM_CAMPAIGN_ID,
    canonical_output_relative_path,
    get_llm_campaign,
)

SCRIPT_VERSION = build_script_version(Path(__file__), "v5")

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_LAB_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"
DEFAULT_REGISTRY_PATH = PUBLIC_LAB_ROOT / "lab_cases_v1.json"
DEFAULT_OUT_MD = REPO_ROOT / "reports" / "lab_llm_run_manifest.md"
DEFAULT_OUT_JSON = REPO_ROOT / "reports" / "lab_llm_run_manifest.json"

DEFAULT_TICKERS = CORE4_SHOWCASE_TICKERS  # Legacy Core4 backstage runtime tickers.
DEFAULT_REQUIRED_START = 2022
DEFAULT_REQUIRED_END = 2025
DEFAULT_INCLUDE_LATEST_AFTER = 2025
DEFAULT_SECTION = "10k_item1a"
DEFAULT_LENSES = "raw,deboilerplated"
DEFAULT_SOURCE_ID = "edgar"
DEFAULT_INPUT_MODE = "full_section_v2"
SUPPORTED_INPUT_MODES = ("full_section_v2", "focuspack_v1")
LLM_DETECTORS = ("det_llm_delta_brief_v1", "det_llm_excerpt_picker_v1")

sys.path.append(str(Path(__file__).resolve().parent))
from lab_llm_precompute_utils import (  # type: ignore
    BundlePaths,
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
    input_mode: str
    case_in_registry: bool
    input_source_path: Optional[str]
    input_source_present: bool
    input_source_year_prev_path: Optional[str]
    input_source_year_curr_path: Optional[str]
    run_pack_input_path: Optional[str]
    run_pack_year_prev_path: Optional[str]
    run_pack_year_curr_path: Optional[str]
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


def _norm_rel_path(path_value: str) -> str:
    return path_value.replace("\\", "/").lstrip("./")


def _bundle_relative(path: Path, bundle_root: Path) -> Optional[str]:
    try:
        return _to_posix(path.resolve().relative_to(bundle_root.resolve()))
    except Exception:
        return None


def parse_lenses(raw: str) -> list[str]:
    values: list[str] = []
    for token in raw.split(","):
        lens = token.strip().lower()
        if not lens:
            continue
        if lens not in values:
            values.append(lens)
    if not values:
        raise SystemExit("No valid lenses parsed from --lenses.")
    return values


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
    source_id: str,
    track_slug: str,
) -> Path:
    rel = canonical_output_relative_path(
        ticker=ticker,
        detector_id=detector_id,
        section=section,
        year_from=year_from,
        year_to=year_to,
        cleaning_lens=lens,
        source_id=source_id,
        track_slug=track_slug,
    )
    return PUBLIC_LAB_ROOT / rel


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


def resolve_input_index(
    input_mode: str,
    bundle_paths: "BundlePaths",
) -> tuple[dict[tuple[str, int, int, str, str], InputIndexEntry], Path]:
    if input_mode == "full_section_v2":
        if bundle_paths.pair_index_v2 is None:
            raise SystemExit("Bundle missing inputs_index_pair_v2.json required for full_section_v2.")
        return (
            load_input_index(bundle_paths.pair_index_v2, bundle_paths.bundle_root),
            bundle_paths.pair_index_v2,
        )
    if input_mode == "focuspack_v1":
        if bundle_paths.focus_index is None:
            raise SystemExit("Bundle missing inputs_index_focuspack.json required for focuspack_v1.")
        return (
            load_input_index(bundle_paths.focus_index, bundle_paths.bundle_root),
            bundle_paths.focus_index,
        )
    raise SystemExit(f"Unsupported --input-mode: {input_mode}")


def resolve_year_source_path(bundle_root: Path, rel_path: Optional[str]) -> Optional[Path]:
    if rel_path is None:
        return None
    normalized = _norm_rel_path(rel_path)
    if not normalized:
        return None
    candidate = (bundle_root / normalized).resolve()
    if not candidate.exists():
        return None
    return candidate


def copy_if_exists(source: Optional[Path], destination: Path) -> None:
    if source is None:
        return
    if not source.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


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
    campaign_id: str,
    input_mode: str,
    bundle_root: Path,
    input_index_path: Path,
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
        "campaign_id": campaign_id,
        "input_mode": input_mode,
        "source_bundle_root": to_repo_relative(bundle_root),
        "source_input_index_path": to_repo_relative(input_index_path),
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
        "input_mode": entry.input_mode,
        "case_in_registry": entry.case_in_registry,
        "input": {
            "source_path": entry.input_source_path,
            "source_present": entry.input_source_present,
            "source_year_prev_path": entry.input_source_year_prev_path,
            "source_year_curr_path": entry.input_source_year_curr_path,
            "run_pack_path": entry.run_pack_input_path,
            "run_pack_year_prev_path": entry.run_pack_year_prev_path,
            "run_pack_year_curr_path": entry.run_pack_year_curr_path,
        },
        "detectors": detectors_payload,
        "all_outputs_present": entry.all_outputs_present,
    }


def build_report_lines(
    generated_at_utc: str,
    campaign_id: str,
    campaign_slug: str,
    campaign_display_name: str,
    input_mode: str,
    registry_path: Path,
    bundle_root: Path,
    input_index_path: Path,
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
    lines.append(f"Campaign id: {campaign_id}")
    lines.append(f"Campaign slug: {campaign_slug}")
    lines.append(f"Campaign display: {campaign_display_name}")
    lines.append(f"Input mode: {input_mode}")
    lines.append(f"Registry: {to_repo_relative(registry_path)}")
    lines.append(f"Inputs bundle root: {to_repo_relative(bundle_root)}")
    lines.append(f"Input index: {to_repo_relative(input_index_path)}")
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
    lines.append(f"| Pair-lens rows | {total_pairs} |")
    lines.append(f"| Detector targets | {total_targets} |")
    lines.append(f"| Present targets | {present_targets} |")
    lines.append(f"| Missing targets | {missing_targets} |")
    lines.append("")
    lines.append("| Ticker | Pair | Lens | In registry | Input source | Delta brief | Excerpt picker |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
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
            f"| {entry.ticker} | {pair_label} | {entry.lens} | {registry_status} | {input_status} | {delta_status} | {excerpt_status} |"
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
                f"- {entry.ticker} {pair_label} {entry.lens} {detector.detector_id}: {detector.expected_output_path}"
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
    campaign_id: str,
) -> None:
    campaign = get_llm_campaign(campaign_id)
    if campaign is None:
        raise SystemExit(f"Unknown campaign id: {campaign_id}")
    lines: list[str] = []
    lines.append("# Thread Starters")
    lines.append("")
    lines.append("One section per pair + detector. Copy one code block at a time.")
    lines.append("")
    for entry in entries:
        run_pack_input_path = entry.run_pack_input_path or ""
        if not run_pack_input_path:
            continue
        additional_inputs: list[str] = []
        if entry.run_pack_year_prev_path:
            additional_inputs.append(entry.run_pack_year_prev_path)
        if entry.run_pack_year_curr_path:
            additional_inputs.append(entry.run_pack_year_curr_path)
        for detector in entry.detectors:
            heading = (
                f"## {entry.ticker} {entry.year_from}-{entry.year_to} {entry.lens} {detector.detector_id}"
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
                input_lens=entry.lens if entry.input_mode == "full_section_v2" else f"focuspack_{entry.lens}",
                input_path=run_pack_input_path,
                output_path=detector.expected_output_path,
                repo_input_path=entry.input_source_path,
                additional_input_paths=additional_inputs,
                input_mode=entry.input_mode,
                campaign=campaign,
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
        help="Section id for input lookup and expected filenames.",
    )
    parser.add_argument(
        "--lenses",
        default=DEFAULT_LENSES,
        help="Comma-separated cleaning lenses for the run manifest.",
    )
    parser.add_argument(
        "--source-id",
        default=DEFAULT_SOURCE_ID,
        help="Source id to place in thread starters.",
    )
    parser.add_argument(
        "--campaign-id",
        default=DEFAULT_PRIMARY_LLM_CAMPAIGN_ID,
        help="Campaign id from scripts/lab_output_tracks.py.",
    )
    parser.add_argument(
        "--input-mode",
        default=DEFAULT_INPUT_MODE,
        choices=SUPPORTED_INPUT_MODES,
        help="Input mode: full_section_v2 (canonical) or focuspack_v1 (legacy).",
    )
    parser.add_argument(
        "--bundle",
        default="",
        help="Bundle root containing LLM input indexes (defaults to latest showcase bundle).",
    )
    parser.add_argument(
        "--inputs-index-focuspack",
        default="",
        help="Override focuspack index path.",
    )
    parser.add_argument(
        "--inputs-index-pair-v2",
        default="",
        help="Override full-section v2 pair index path.",
    )
    parser.add_argument(
        "--inputs-index-year-v2",
        default="",
        help="Override full-section v2 year index path.",
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

    lenses = parse_lenses(args.lenses)
    tickers = parse_tickers(args.tickers)
    if not tickers:
        raise SystemExit("No valid tickers were parsed from --tickers.")
    campaign = get_llm_campaign(args.campaign_id)
    if campaign is None:
        raise SystemExit(f"Unknown campaign id: {args.campaign_id}")

    bundle_paths = resolve_bundle_paths(
        args.bundle or None,
        args.inputs_index_focuspack or None,
        None,
        None,
        args.inputs_index_pair_v2 or None,
        args.inputs_index_year_v2 or None,
    )
    input_index, input_index_path = resolve_input_index(args.input_mode, bundle_paths)

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
    entry_started = time.monotonic()
    last_entry_heartbeat = entry_started
    total_pair_lens_targets = 0
    for ticker in tickers:
        total_pair_lens_targets += len(target_pairs.get(ticker, [])) * len(lenses)
    built_pair_lens_targets = 0
    for ticker in tickers:
        pairs = target_pairs.get(ticker, [])
        case_pairs = pairs_by_ticker.get(ticker, set())
        for year_from, year_to in pairs:
            for lens in lenses:
                built_pair_lens_targets += 1
                now = time.monotonic()
                if now - last_entry_heartbeat >= 300:
                    elapsed = int(now - entry_started)
                    print(
                        "[progress] run_manifest_entries "
                        + f"rows={built_pair_lens_targets}/{total_pair_lens_targets} "
                        + f"entries={len(entries)} missing_inputs={len(missing_input_rows)} "
                        + f"elapsed={elapsed}s",
                        flush=True,
                    )
                    last_entry_heartbeat = now
                input_entry = get_input_index_entry(
                    index=input_index,
                    ticker=ticker,
                    year_from=year_from,
                    year_to=year_to,
                    section=args.section,
                    lens=lens,
                )
                input_source_path: Optional[str] = None
                input_source_present = False
                input_source_year_prev_path: Optional[str] = None
                input_source_year_curr_path: Optional[str] = None
                if input_entry is not None:
                    input_source_path = to_repo_relative(input_entry.path)
                    input_source_present = input_entry.path.exists()
                    if args.input_mode == "full_section_v2":
                        prev_source = resolve_year_source_path(
                            bundle_paths.bundle_root, input_entry.year_input_prev
                        )
                        curr_source = resolve_year_source_path(
                            bundle_paths.bundle_root, input_entry.year_input_curr
                        )
                        if prev_source is not None:
                            input_source_year_prev_path = to_repo_relative(prev_source)
                        if curr_source is not None:
                            input_source_year_curr_path = to_repo_relative(curr_source)
                if not input_source_present:
                    missing_input_rows.append(
                        f"{ticker} {year_from}-{year_to} (section={args.section}, lens={lens}, input_mode={args.input_mode})"
                    )

                detectors: list[DetectorTarget] = []
                for detector_id in LLM_DETECTORS:
                    expected_path_abs = expected_output_path(
                        ticker=ticker,
                        detector_id=detector_id,
                        section=args.section,
                        year_from=year_from,
                        year_to=year_to,
                        lens=lens,
                        source_id=args.source_id,
                        track_slug=campaign.track_slug,
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
                        lens=lens,
                        source_id=args.source_id,
                        input_mode=args.input_mode,
                        case_in_registry=(year_from, year_to) in case_pairs,
                        input_source_path=input_source_path,
                        input_source_present=input_source_present,
                        input_source_year_prev_path=input_source_year_prev_path,
                        input_source_year_curr_path=input_source_year_curr_path,
                        run_pack_input_path=None,
                        run_pack_year_prev_path=None,
                        run_pack_year_curr_path=None,
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
            entries_with_pack_paths.append(entry)
    else:
        run_pack_generated_now = True
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_pack_dir = run_pack_root / f"llm_run_pack_{stamp}_{campaign.track_id}"
        run_pack_dir.mkdir(parents=True, exist_ok=True)
        copy_started = time.monotonic()
        last_copy_heartbeat = copy_started
        copied_entries = 0
        for entry in entries:
            copied_entries += 1
            now = time.monotonic()
            if now - last_copy_heartbeat >= 300:
                elapsed = int(now - copy_started)
                print(
                    "[progress] run_manifest_run_pack "
                    + f"entries={copied_entries}/{len(entries)} elapsed={elapsed}s",
                    flush=True,
                )
                last_copy_heartbeat = now
            run_pack_input_rel: Optional[str] = None
            run_pack_year_prev_rel: Optional[str] = None
            run_pack_year_curr_rel: Optional[str] = None

            if entry.input_source_path is not None:
                source_abs = (REPO_ROOT / entry.input_source_path).resolve()
                if source_abs.exists():
                    rel_from_bundle = _bundle_relative(source_abs, bundle_paths.bundle_root)
                    if rel_from_bundle is None:
                        rel_from_bundle = f"inputs/{source_abs.name}"
                    run_pack_input_rel = _norm_rel_path(rel_from_bundle)
                    copy_if_exists(source_abs, run_pack_dir / run_pack_input_rel)

            if entry.input_source_year_prev_path is not None:
                prev_abs = (REPO_ROOT / entry.input_source_year_prev_path).resolve()
                if prev_abs.exists():
                    rel_from_bundle = _bundle_relative(prev_abs, bundle_paths.bundle_root)
                    if rel_from_bundle is None:
                        rel_from_bundle = f"inputs/year/{prev_abs.name}"
                    run_pack_year_prev_rel = _norm_rel_path(rel_from_bundle)
                    copy_if_exists(prev_abs, run_pack_dir / run_pack_year_prev_rel)

            if entry.input_source_year_curr_path is not None:
                curr_abs = (REPO_ROOT / entry.input_source_year_curr_path).resolve()
                if curr_abs.exists():
                    rel_from_bundle = _bundle_relative(curr_abs, bundle_paths.bundle_root)
                    if rel_from_bundle is None:
                        rel_from_bundle = f"inputs/year/{curr_abs.name}"
                    run_pack_year_curr_rel = _norm_rel_path(rel_from_bundle)
                    copy_if_exists(curr_abs, run_pack_dir / run_pack_year_curr_rel)

            entries_with_pack_paths.append(
                ManifestEntry(
                    ticker=entry.ticker,
                    year_from=entry.year_from,
                    year_to=entry.year_to,
                    section=entry.section,
                    lens=entry.lens,
                    source_id=entry.source_id,
                    input_mode=entry.input_mode,
                    case_in_registry=entry.case_in_registry,
                    input_source_path=entry.input_source_path,
                    input_source_present=entry.input_source_present,
                    input_source_year_prev_path=entry.input_source_year_prev_path,
                    input_source_year_curr_path=entry.input_source_year_curr_path,
                    run_pack_input_path=run_pack_input_rel,
                    run_pack_year_prev_path=run_pack_year_prev_rel,
                    run_pack_year_curr_path=run_pack_year_curr_rel,
                    detectors=entry.detectors,
                )
            )
        thread_starters_path = run_pack_dir / "THREAD_STARTERS.md"
        write_thread_starters(
            thread_starters_path,
            entries_with_pack_paths,
            campaign_id=campaign.track_id,
        )
        run_pack_meta_path = run_pack_dir / "RUN_PACK_META.json"
        run_pack_meta_payload = build_run_pack_meta_payload(
            generated_at_utc=generated_at_utc,
            campaign_id=campaign.track_id,
            input_mode=args.input_mode,
            bundle_root=bundle_paths.bundle_root,
            input_index_path=input_index_path,
            run_pack_dir=run_pack_dir,
            thread_starters_path=thread_starters_path,
        )
        write_json(run_pack_meta_path, run_pack_meta_payload)

    effective_entries = entries_with_pack_paths if entries_with_pack_paths else entries
    report_lines = build_report_lines(
        generated_at_utc=generated_at_utc,
        campaign_id=campaign.track_id,
        campaign_slug=campaign.track_slug,
        campaign_display_name=campaign.display_name,
        input_mode=args.input_mode,
        registry_path=registry_path,
        bundle_root=bundle_paths.bundle_root,
        input_index_path=input_index_path,
        run_pack_dir=run_pack_dir,
        run_pack_thread_starters=thread_starters_path,
        run_pack_meta_path=run_pack_meta_path,
        entries=effective_entries,
        missing_input_rows=missing_input_rows,
    )
    write_text(Path(args.out_md), report_lines)

    total_pairs = len(effective_entries)
    total_targets = total_pairs * len(LLM_DETECTORS)
    present_targets = 0
    missing_targets = 0
    for entry in effective_entries:
        for detector in entry.detectors:
            if detector.present:
                present_targets += 1
            else:
                missing_targets += 1

    payload_entries: list[dict[str, Any]] = []
    for entry in effective_entries:
        payload_entries.append(entry_to_json_dict(entry))

    manifest_payload: dict[str, Any] = {
        "generated_at_utc": generated_at_utc,
        "script_version": SCRIPT_VERSION,
        "campaign": {
            "campaign_id": campaign.track_id,
            "campaign_slug": campaign.track_slug,
            "display_name": campaign.display_name,
            "model_provider": campaign.model_provider,
            "model_name": campaign.model_name,
            "input_mode": campaign.input_mode,
        },
        "registry_path": to_repo_relative(registry_path),
        "bundle_root": to_repo_relative(bundle_paths.bundle_root),
        "input_index_path": to_repo_relative(input_index_path),
        "scope": {
            "tickers": tickers,
            "required_start_year": args.required_start,
            "required_end_year": args.required_end,
            "include_latest_after_year": args.include_latest_after,
            "section": args.section,
            "lenses": lenses,
            "source_id": args.source_id,
            "detectors": list(LLM_DETECTORS),
            "input_mode": args.input_mode,
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
            "pair_lens_count": total_pairs,
            "target_count": total_targets,
            "present_target_count": present_targets,
            "missing_target_count": missing_targets,
            "missing_input_count": len(missing_input_rows),
        },
        "entries": payload_entries,
    }
    write_json(Path(args.out_json), manifest_payload)

    print(f"Script: {SCRIPT_VERSION}")
    print(f"Campaign: {campaign.track_id}")
    print(f"Input mode: {args.input_mode}")
    print(f"Wrote manifest markdown: {args.out_md}")
    print(f"Wrote manifest json: {args.out_json}")
    if run_pack_generated_now and run_pack_dir is not None:
        print(f"Wrote run pack: {to_repo_relative(run_pack_dir)}")
        if thread_starters_path is not None:
            print(f"Wrote thread starters: {to_repo_relative(thread_starters_path)}")
        if run_pack_meta_path is not None:
            print(f"Wrote run pack metadata: {to_repo_relative(run_pack_meta_path)}")
    elif args.skip_run_pack:
        print("Run pack generation skipped (--skip-run-pack)")
        if run_pack_dir is not None:
            print(
                "Using latest existing run pack context: "
                + f"{to_repo_relative(run_pack_dir)}"
            )
    print(
        "Manifest summary: "
        + f"pair_rows={total_pairs}, targets={total_targets}, "
        + f"present={present_targets}, missing={missing_targets}, "
        + f"missing_inputs={len(missing_input_rows)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
