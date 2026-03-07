from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from lab_script_version import build_script_version
from lab_output_tracks import (
    DEFAULT_PRIMARY_LLM_CAMPAIGN_ID,
    LLM_DETECTORS,
    canonical_outline_runtime_relative_path,
    canonical_outline_structured_relative_path,
    canonical_outline_insight_relative_path,
    canonical_output_relative_path,
    get_llm_campaign,
    pick_latest_adjacent_pair,
)
from lab_llm_precompute_utils import (
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

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_LAB_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"
DEFAULT_REGISTRY_PATH = PUBLIC_LAB_ROOT / "lab_cases_v1.json"
DEFAULT_OUT_MD = REPO_ROOT / "reports" / "lab_llm_master_manifest.md"
DEFAULT_OUT_JSON = REPO_ROOT / "reports" / "lab_llm_master_manifest.json"
DEFAULT_TICKERS = ("NVDA", "KO", "WM", "GE")
DEFAULT_REQUIRED_START = 2022
DEFAULT_REQUIRED_END = 2025
DEFAULT_INCLUDE_LATEST_AFTER = 2025
PAIR_POLICY_LATEST_TWO = "latest_two"
PAIR_POLICY_FIXED_WINDOW = "fixed_window"
DEFAULT_SECTION = "10k_item1a"
DEFAULT_LENSES = "raw,deboilerplated"
DEFAULT_SOURCE_ID = "edgar"


def parse_lenses(raw: str) -> list[str]:
    values: list[str] = []
    for token in raw.split(","):
        cleaned = token.strip().lower()
        if not cleaned:
            continue
        if cleaned not in values:
            values.append(cleaned)
    if not values:
        raise SystemExit("No valid lenses parsed from --lenses.")
    return values


def parse_tickers(raw: str) -> list[str]:
    values: list[str] = []
    for token in raw.split(","):
        cleaned = token.strip().upper()
        if not cleaned:
            continue
        if cleaned not in values:
            values.append(cleaned)
    if not values:
        raise SystemExit("No valid tickers parsed from --tickers.")
    return values


def load_registry_pairs(path: Path) -> dict[str, set[tuple[int, int]]]:
    payload = read_json(path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        raise SystemExit(f"Registry root is not object: {path}")
    cases = as_list(payload_dict.get("cases"))
    if cases is None:
        raise SystemExit(f"Registry missing list field 'cases': {path}")
    pairs_by_ticker: dict[str, set[tuple[int, int]]] = {}
    for case_any in cases:
        case = as_str_dict(case_any)
        if case is None:
            continue
        ticker = get_str(case.get("ticker"))
        year_from = get_int(case.get("year_from"))
        year_to = get_int(case.get("year_to"))
        if ticker is None or year_from is None or year_to is None:
            continue
        ticker_up = ticker.upper()
        pairs_by_ticker.setdefault(ticker_up, set()).add((year_from, year_to))
    return pairs_by_ticker


def build_required_pairs(start_year: int, end_year: int) -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []
    cursor = start_year
    while cursor < end_year:
        pairs.append((cursor, cursor + 1))
        cursor += 1
    return pairs


def pick_extra_pair(
    pairs: set[tuple[int, int]], include_after_year: int
) -> Optional[tuple[int, int]]:
    candidates: set[tuple[int, int]] = set()
    for year_from, year_to in pairs:
        normalized = (min(year_from, year_to), max(year_from, year_to))
        if normalized[1] <= include_after_year:
            continue
        candidates.add(normalized)
    return pick_latest_adjacent_pair(candidates)


def build_target_pairs(
    pairs_by_ticker: dict[str, set[tuple[int, int]]],
    tickers: list[str],
    start_year: int,
    end_year: int,
    include_after_year: int,
    pair_policy: str,
) -> dict[str, list[tuple[int, int]]]:
    output: dict[str, list[tuple[int, int]]] = {}
    if pair_policy == PAIR_POLICY_LATEST_TWO:
        for ticker in tickers:
            case_pairs = pairs_by_ticker.get(ticker, set())
            latest = pick_latest_adjacent_pair(case_pairs)
            if latest is None:
                output[ticker] = []
            else:
                output[ticker] = [latest]
        return output

    required = build_required_pairs(start_year, end_year)
    for ticker in tickers:
        case_pairs = pairs_by_ticker.get(ticker, set())
        merged = list(required)
        extra = pick_extra_pair(case_pairs, include_after_year)
        if extra is not None and extra not in merged:
            merged.append(extra)
        output[ticker] = merged
    return output


def resolve_input_entry(
    index: dict[tuple[str, int, int, str, str], InputIndexEntry],
    ticker: str,
    year_from: int,
    year_to: int,
    section: str,
    lens: str,
) -> Optional[InputIndexEntry]:
    return index.get((ticker.upper(), year_from, year_to, section, lens))


def write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build canonical LLM-first master manifest for outline compare artifacts."
    )
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY_PATH))
    parser.add_argument("--campaign-id", default=DEFAULT_PRIMARY_LLM_CAMPAIGN_ID)
    parser.add_argument("--tickers", default=",".join(DEFAULT_TICKERS))
    parser.add_argument("--required-start", type=int, default=DEFAULT_REQUIRED_START)
    parser.add_argument("--required-end", type=int, default=DEFAULT_REQUIRED_END)
    parser.add_argument("--include-latest-after", type=int, default=DEFAULT_INCLUDE_LATEST_AFTER)
    parser.add_argument(
        "--pair-policy",
        choices=(PAIR_POLICY_LATEST_TWO, PAIR_POLICY_FIXED_WINDOW),
        default=PAIR_POLICY_LATEST_TWO,
        help=(
            "Target pair policy. latest_two selects one latest adjacent fiscal-year pair per ticker "
            "from registry cases. fixed_window preserves the legacy required-start/end window."
        ),
    )
    parser.add_argument("--section", default=DEFAULT_SECTION)
    parser.add_argument("--lenses", default=DEFAULT_LENSES)
    parser.add_argument("--source-id", default=DEFAULT_SOURCE_ID)
    parser.add_argument(
        "--master-artifact-id",
        choices=("llm_outline_compare_structured", "llm_outline_compare_insight"),
        default="llm_outline_compare_structured",
        help=(
            "Primary authoring artifact for master_output. "
            "structured is production; insight is experimental."
        ),
    )
    parser.add_argument("--bundle", default="")
    parser.add_argument("--inputs-index-pair-v2", default="")
    parser.add_argument("--inputs-index-year-v2", default="")
    parser.add_argument("--out-md", default=str(DEFAULT_OUT_MD))
    parser.add_argument("--out-json", default=str(DEFAULT_OUT_JSON))
    parser.add_argument(
        "--verbose-progress",
        action="store_true",
        help="Emit progress lines for each pair/lens row built.",
    )
    parser.add_argument(
        "--progress-interval-sec",
        type=int,
        default=300,
        help="Heartbeat interval in seconds for long-running operations.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    started = time.monotonic()
    args = build_parser().parse_args(argv)
    registry_path = Path(args.registry)
    if not registry_path.is_absolute():
        registry_path = (REPO_ROOT / registry_path).resolve()
    if not registry_path.exists():
        raise SystemExit(f"Registry not found: {registry_path}")

    campaign = get_llm_campaign(args.campaign_id)
    if campaign is None:
        raise SystemExit(f"Unknown campaign id: {args.campaign_id}")

    bundle_paths = resolve_bundle_paths(
        args.bundle or None,
        None,
        None,
        None,
        args.inputs_index_pair_v2 or None,
        args.inputs_index_year_v2 or None,
    )
    if bundle_paths.pair_index_v2 is None:
        raise SystemExit("Bundle missing inputs_index_pair_v2.json.")

    pair_index = load_input_index(bundle_paths.pair_index_v2, bundle_paths.bundle_root)
    pairs_by_ticker = load_registry_pairs(registry_path)
    tickers = parse_tickers(args.tickers)
    if args.pair_policy == PAIR_POLICY_LATEST_TWO:
        for input_entry in pair_index.values():
            ticker_up = input_entry.ticker.upper()
            if ticker_up not in tickers:
                continue
            normalized_pair = (
                min(input_entry.year_from, input_entry.year_to),
                max(input_entry.year_from, input_entry.year_to),
            )
            pairs_by_ticker.setdefault(ticker_up, set()).add(normalized_pair)
    lenses = parse_lenses(args.lenses)
    target_pairs = build_target_pairs(
        pairs_by_ticker=pairs_by_ticker,
        tickers=tickers,
        start_year=args.required_start,
        end_year=args.required_end,
        include_after_year=args.include_latest_after,
        pair_policy=args.pair_policy,
    )

    print(f"[phase] build master manifest rows (script={SCRIPT_VERSION})", flush=True)
    entries: list[dict[str, Any]] = []
    missing_inputs: list[str] = []
    summary_targets = 0
    summary_present = 0
    progress_interval_sec = max(1, int(args.progress_interval_sec))
    loop_started = time.monotonic()
    last_heartbeat = loop_started
    total_rows = sum(len(target_pairs.get(ticker, [])) * len(lenses) for ticker in tickers)
    processed_rows = 0
    for ticker in tickers:
        case_pairs = pairs_by_ticker.get(ticker, set())
        for year_from, year_to in target_pairs.get(ticker, []):
            for lens in lenses:
                processed_rows += 1
                now = time.monotonic()
                if args.verbose_progress or now - last_heartbeat >= progress_interval_sec:
                    elapsed = int(now - loop_started)
                    print(
                        "[progress] master_manifest "
                        + f"rows={processed_rows}/{total_rows} "
                        + f"master_present={summary_present}/{summary_targets} "
                        + f"missing_inputs={len(missing_inputs)} elapsed={elapsed}s",
                        flush=True,
                    )
                    last_heartbeat = now
                input_entry = resolve_input_entry(
                    pair_index,
                    ticker=ticker,
                    year_from=year_from,
                    year_to=year_to,
                    section=args.section,
                    lens=lens,
                )
                source_path = to_repo_relative(input_entry.path) if input_entry else None
                source_present = bool(input_entry and input_entry.path.exists())
                source_year_prev = input_entry.year_input_prev if input_entry else None
                source_year_curr = input_entry.year_input_curr if input_entry else None
                if not source_present:
                    missing_inputs.append(
                        f"{ticker} {year_from}-{year_to} {lens} ({args.section})"
                    )

                if args.master_artifact_id == "llm_outline_compare_insight":
                    master_rel = canonical_outline_insight_relative_path(
                        ticker=ticker,
                        section=args.section,
                        year_from=year_from,
                        year_to=year_to,
                        cleaning_lens=lens,
                        source_id=args.source_id,
                        track_slug=campaign.track_slug,
                    )
                    projected_master_structured_rel: Optional[str] = canonical_outline_structured_relative_path(
                        ticker=ticker,
                        section=args.section,
                        year_from=year_from,
                        year_to=year_to,
                        cleaning_lens=lens,
                        source_id=args.source_id,
                        track_slug=campaign.track_slug,
                    )
                else:
                    master_rel = canonical_outline_structured_relative_path(
                        ticker=ticker,
                        section=args.section,
                        year_from=year_from,
                        year_to=year_to,
                        cleaning_lens=lens,
                        source_id=args.source_id,
                        track_slug=campaign.track_slug,
                    )
                    projected_master_structured_rel = None

                master_repo_path = f"public/data/sec_narrative_drift_lab/{master_rel}"
                master_present = (REPO_ROOT / master_repo_path).exists()
                if master_present:
                    summary_present += 1
                summary_targets += 1

                projected_master_structured_repo_path: Optional[str] = None
                projected_master_structured_present: Optional[bool] = None
                if projected_master_structured_rel is not None:
                    projected_master_structured_repo_path = (
                        f"public/data/sec_narrative_drift_lab/{projected_master_structured_rel}"
                    )
                    projected_master_structured_present = (REPO_ROOT / projected_master_structured_repo_path).exists()

                runtime_rel = canonical_outline_runtime_relative_path(
                    ticker=ticker,
                    section=args.section,
                    year_from=year_from,
                    year_to=year_to,
                    cleaning_lens=lens,
                    source_id=args.source_id,
                    track_slug=campaign.track_slug,
                )
                runtime_repo_path = f"public/data/sec_narrative_drift_lab/{runtime_rel}"
                runtime_present = (REPO_ROOT / runtime_repo_path).exists()
                projection_outputs: list[dict[str, Any]] = []
                for detector_id in LLM_DETECTORS:
                    rel = canonical_output_relative_path(
                        ticker=ticker,
                        detector_id=detector_id,
                        section=args.section,
                        year_from=year_from,
                        year_to=year_to,
                        cleaning_lens=lens,
                        source_id=args.source_id,
                        track_slug=campaign.track_slug,
                    )
                    repo_path = f"public/data/sec_narrative_drift_lab/{rel}"
                    projection_outputs.append(
                        {
                            "detector_id": detector_id,
                            "expected_output_path": repo_path,
                            "present": (REPO_ROOT / repo_path).exists(),
                        }
                    )

                entries.append(
                    {
                        "ticker": ticker,
                        "year_from": year_from,
                        "year_to": year_to,
                        "section": args.section,
                        "lens": lens,
                        "source_id": args.source_id,
                        "case_in_registry": (year_from, year_to) in case_pairs,
                        "input": {
                            "source_path": source_path,
                            "source_present": source_present,
                            "source_year_prev_path": source_year_prev,
                            "source_year_curr_path": source_year_curr,
                            "integrity": {
                                "pair_payload_sha256": input_entry.pair_payload_sha256
                                if input_entry
                                else None,
                                "pair_payload_bytes": input_entry.pair_payload_bytes
                                if input_entry
                                else None,
                                "prev_payload_sha256": input_entry.prev_payload_sha256
                                if input_entry
                                else None,
                                "curr_payload_sha256": input_entry.curr_payload_sha256
                                if input_entry
                                else None,
                                "prev_paragraph_count": input_entry.prev_paragraph_count
                                if input_entry
                                else None,
                                "curr_paragraph_count": input_entry.curr_paragraph_count
                                if input_entry
                                else None,
                                "prev_paragraphs_sha256": input_entry.prev_paragraphs_sha256
                                if input_entry
                                else None,
                                "curr_paragraphs_sha256": input_entry.curr_paragraphs_sha256
                                if input_entry
                                else None,
                            },
                        },
                        "master_output": {
                            "artifact_id": args.master_artifact_id,
                            "expected_output_path": master_repo_path,
                            "present": master_present,
                        },
                        "projected_master_output_structured": {
                            "artifact_id": "llm_outline_compare_structured",
                            "expected_output_path": projected_master_structured_repo_path,
                            "present": projected_master_structured_present,
                        }
                        if projected_master_structured_repo_path is not None
                        else None,
                        "projected_master_output_runtime": {
                            "artifact_id": "llm_outline_compare_runtime",
                            "expected_output_path": runtime_repo_path,
                            "present": runtime_present,
                        },
                        "projection_outputs": projection_outputs,
                    }
                )

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload: dict[str, Any] = {
        "generated_at_utc": generated_at,
        "script_version": SCRIPT_VERSION,
        "campaign": {
            "campaign_id": campaign.track_id,
            "campaign_slug": campaign.track_slug,
            "display_name": campaign.display_name,
            "model_provider": campaign.model_provider,
            "model_name": campaign.model_name,
            "input_mode": campaign.input_mode,
        },
        "scope": {
            "tickers": tickers,
            "required_start_year": args.required_start,
            "required_end_year": args.required_end,
            "include_latest_after_year": args.include_latest_after,
            "pair_policy": args.pair_policy,
            "section": args.section,
            "source_id": args.source_id,
            "lenses": lenses,
            "master_artifact_id": args.master_artifact_id,
            "projected_master_artifact_id": "llm_outline_compare_structured"
            if args.master_artifact_id == "llm_outline_compare_insight"
            else None,
            "runtime_projected_artifact_id": "llm_outline_compare_runtime",
            "projection_detectors": list(LLM_DETECTORS),
        },
        "bundle_root": to_repo_relative(bundle_paths.bundle_root),
        "pair_index_path": to_repo_relative(bundle_paths.pair_index_v2),
        "summary": {
            "pair_lens_count": len(entries),
            "master_target_count": summary_targets,
            "master_present_count": summary_present,
            "missing_input_count": len(missing_inputs),
        },
        "entries": entries,
    }


    for entry in entries:
        if entry.get("projected_master_output_structured") is None:
            entry.pop("projected_master_output_structured", None)

    scope_block: dict[str, Any] | None = payload.get("scope")
    if isinstance(scope_block, dict) and scope_block.get("projected_master_artifact_id") is None:
        scope_block.pop("projected_master_artifact_id", None)
    out_md = Path(args.out_md)
    if not out_md.is_absolute():
        out_md = (REPO_ROOT / out_md).resolve()
    out_json = Path(args.out_json)
    if not out_json.is_absolute():
        out_json = (REPO_ROOT / out_json).resolve()
    print("[phase] write master manifest outputs", flush=True)
    write_json(out_json, payload)

    master_column_label = ("Master insight" if args.master_artifact_id == "llm_outline_compare_insight" else "Master structured")
    if args.master_artifact_id == "llm_outline_compare_insight":
        report_header = (
            "| Ticker | Pair | Lens | Input | "
            + master_column_label
            + " | Projected structured | Runtime | Delta | Excerpt |"
        )
        report_separator = "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    else:
        report_header = (
            "| Ticker | Pair | Lens | Input | "
            + master_column_label
            + " | Runtime | Delta | Excerpt |"
        )
        report_separator = "| --- | --- | --- | --- | --- | --- | --- | --- |"

    report_lines = [
        "# LLM Master Manifest",
        "",
        f"- generated_at_utc: `{generated_at}`",
        f"- script: `{SCRIPT_VERSION}`",
        f"- campaign: `{campaign.track_id}`",
        f"- bundle_root: `{to_repo_relative(bundle_paths.bundle_root)}`",
        f"- pair_index: `{to_repo_relative(bundle_paths.pair_index_v2)}`",
        f"- pair_lens_rows: `{len(entries)}`",
        f"- pair_policy: `{args.pair_policy}`",
        f"- master_present: `{summary_present}/{summary_targets}`",
        f"- missing_inputs: `{len(missing_inputs)}`",
        f"- master_artifact_id: `{args.master_artifact_id}`",
        "",
        report_header,
        report_separator,
    ]
    for entry in entries:
        pair_label = f"{entry['year_from']}-{entry['year_to']}"
        input_state = "present" if entry["input"]["source_present"] else "missing"
        master_state = "present" if entry["master_output"]["present"] else "missing"
        runtime_state = (
            "present" if entry["projected_master_output_runtime"]["present"] else "missing"
        )
        projected_structured_state = "-"
        projected_structured: dict[str, Any] | None = entry.get("projected_master_output_structured")
        if isinstance(projected_structured, dict):
            projected_structured_state = "present" if projected_structured.get("present") else "missing"
        detector_states: dict[str, str] = {}
        for detector in entry["projection_outputs"]:
            detector_states[detector["detector_id"]] = (
                "present" if detector["present"] else "missing"
            )
        row_values = [
            str(entry["ticker"]),
            pair_label,
            str(entry["lens"]),
            input_state,
            master_state,
        ]
        if args.master_artifact_id == "llm_outline_compare_insight":
            row_values.append(projected_structured_state)
        row_values.extend(
            [
                runtime_state,
                detector_states.get("det_llm_delta_brief_v1", "-"),
                detector_states.get("det_llm_excerpt_picker_v1", "-"),
            ]
        )
        report_lines.append("| " + " | ".join(row_values) + " |")
    report_lines.append("")
    report_lines.append("## Missing Inputs")
    if missing_inputs:
        for row in missing_inputs:
            report_lines.append(f"- {row}")
    else:
        report_lines.append("- none")
    write_text(out_md, report_lines)

    elapsed = int(time.monotonic() - started)
    print(f"Script: {SCRIPT_VERSION}")
    print(f"Wrote master manifest json: {out_json}")
    print(f"Wrote master manifest report: {out_md}")
    print(
        "Summary: "
        + f"pair_rows={len(entries)} master_present={summary_present}/{summary_targets} "
        + f"missing_inputs={len(missing_inputs)}"
    )
    print(f"Elapsed: {elapsed}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())











