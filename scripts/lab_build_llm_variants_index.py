from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, cast

from lab_output_tracks import (  # type: ignore
    LLM_CAMPAIGNS,
    LLM_DETECTORS,
    canonical_outline_compare_relative_path,
    canonical_outline_insight_relative_path,
    canonical_outline_research_relative_path,
    canonical_output_relative_path,
)
from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"
LLM_INPUTS_V2_ROOT = LAB_ROOT / "llm_inputs_v2"
DEFAULT_REGISTRY_PATH = LAB_ROOT / "lab_cases_v1.json"
DEFAULT_OUT_PATH = LAB_ROOT / "lab_llm_variants_v1.json"
DEFAULT_REPORT_PATH = REPO_ROOT / "reports" / "lab_llm_variants_index_build.md"
RUN_LABEL_RE = re.compile(r"^20\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])_[A-Za-z0-9._-]+$")


def campaign_lenses(input_mode: Optional[str]) -> tuple[str, ...]:
    if input_mode == "full_section_v2":
        return ("raw", "deboilerplated")
    return ("deboilerplated",)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def as_dict(value: Any) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    return cast(dict[str, Any], value)


def as_list(value: Any) -> Optional[list[Any]]:
    if isinstance(value, list):
        return cast(list[Any], value)
    return None


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _request_url(ticker: str, rel_path_with_ticker: str) -> str:
    trimmed = rel_path_with_ticker.replace("\\", "/")
    prefix = f"{ticker.upper()}/"
    if trimmed.startswith(prefix):
        suffix = trimmed[len(prefix) :]
    else:
        suffix = trimmed
    return f"data/sec_narrative_drift_lab/{ticker.upper()}/{suffix}"


def _validate_variant_payload(
    payload: dict[str, Any],
    detector_id: str,
    lens: str,
    campaign_provider: str,
    campaign_model: str,
) -> tuple[bool, list[str], str]:
    reasons: list[str] = []
    provenance = as_dict(payload.get("provenance"))
    run_label = ""
    if provenance is None:
        reasons.append("missing provenance object")
    else:
        provider = provenance.get("model_provider")
        model = provenance.get("model_name")
        run_label_raw = provenance.get("run_label")
        if provider != campaign_provider:
            reasons.append("model_provider mismatch")
        if model != campaign_model:
            reasons.append("model_name mismatch")
        if not isinstance(run_label_raw, str) or RUN_LABEL_RE.fullmatch(run_label_raw) is None:
            reasons.append("run_label invalid")
        else:
            run_label = run_label_raw
    if payload.get("detector_id") != detector_id:
        reasons.append("detector_id mismatch")
    if payload.get("cleaning_lens") != lens:
        reasons.append("cleaning_lens mismatch")
    return (len(reasons) == 0, reasons, run_label)


def _validate_outline_compare_payload(
    payload: dict[str, Any],
    lens: str,
    campaign_provider: str,
    campaign_model: str,
    expected_artifact_id: str = "llm_outline_compare_runtime",
) -> bool:
    if payload.get("artifact_id") != expected_artifact_id:
        return False
    if payload.get("cleaning_lens") != lens:
        return False
    provenance = as_dict(payload.get("provenance"))
    if provenance is None:
        return False
    if provenance.get("model_provider") != campaign_provider:
        return False
    if provenance.get("model_name") != campaign_model:
        return False
    run_label_raw = provenance.get("run_label")
    if not isinstance(run_label_raw, str) or RUN_LABEL_RE.fullmatch(run_label_raw) is None:
        return False
    return True


def _validate_outline_research_payload(
    payload: dict[str, Any],
    lens: str,
) -> bool:
    if payload.get("artifact_id") != "llm_outline_research_v1":
        return False
    if payload.get("cleaning_lens") != lens:
        return False
    claims = as_list(payload.get("claims"))
    if claims is None:
        return False
    return True


def _resolve_input_file(input_file: str) -> Optional[Path]:
    normalized = input_file.strip().replace("\\", "/").lstrip("./")
    if not normalized:
        return None
    if normalized.startswith("inputs/"):
        path = (LLM_INPUTS_V2_ROOT / normalized).resolve()
    else:
        path = (REPO_ROOT / normalized).resolve()
    if path.exists() and path.is_file():
        return path
    return None


def _load_year_refs(input_file: str) -> tuple[str, str]:
    input_path = _resolve_input_file(input_file)
    if input_path is None:
        return ("", "")
    try:
        payload = read_json(input_path)
    except Exception:
        return ("", "")
    root = as_dict(payload)
    if root is None:
        return ("", "")
    year_inputs = as_dict(root.get("year_inputs"))
    if year_inputs is None:
        return ("", "")
    prev = year_inputs.get("prev")
    curr = year_inputs.get("curr")
    prev_value = prev if isinstance(prev, str) else ""
    curr_value = curr if isinstance(curr, str) else ""
    return (prev_value, curr_value)


def build_variant_rows(
    registry_path: Path,
    *,
    verbose_progress: bool = False,
    progress_interval_sec: int = 300,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    payload = read_json(registry_path)
    root = as_dict(payload)
    if root is None:
        raise SystemExit(f"Registry root is not an object: {registry_path}")
    cases = as_list(root.get("cases"))
    if cases is None:
        raise SystemExit(f"Registry missing list field 'cases': {registry_path}")
    total_cases = len(cases)

    rows: list[dict[str, Any]] = []
    stats = {
        "targets": 0,
        "present": 0,
        "valid": 0,
        "invalid": 0,
        "missing": 0,
    }
    started = time.monotonic()
    last_heartbeat = started
    processed_cases = 0

    for case_any in cases:
        processed_cases += 1
        now = time.monotonic()
        if verbose_progress or now - last_heartbeat >= progress_interval_sec:
            elapsed = int(now - started)
            print(
                "[progress] variants_index "
                + f"cases={processed_cases}/{total_cases} "
                + f"rows={len(rows)} targets={stats['targets']} "
                + f"present={stats['present']} missing={stats['missing']} "
                + f"elapsed={elapsed}s",
                flush=True,
            )
            last_heartbeat = now
        case = as_dict(case_any)
        if case is None:
            continue
        ticker = case.get("ticker")
        section = case.get("section")
        year_from = case.get("year_from")
        year_to = case.get("year_to")
        if not isinstance(ticker, str) or not isinstance(section, str):
            continue
        if not isinstance(year_from, int) or not isinstance(year_to, int):
            continue

        for detector_id in LLM_DETECTORS:
            for campaign in LLM_CAMPAIGNS:
                if campaign.model_provider is None or campaign.model_name is None:
                    continue
                for lens in campaign_lenses(campaign.input_mode):
                    rel = canonical_output_relative_path(
                        ticker=ticker,
                        detector_id=detector_id,
                        section=section,
                        year_from=year_from,
                        year_to=year_to,
                        cleaning_lens=lens,
                        source_id="edgar",
                        track_slug=campaign.track_slug,
                    )
                    repo_path = f"public/data/sec_narrative_drift_lab/{rel}"
                    request_url = _request_url(ticker, rel)
                    abs_path = REPO_ROOT / repo_path
                    outline_compare_rel = canonical_outline_compare_relative_path(
                        ticker=ticker,
                        section=section,
                        year_from=year_from,
                        year_to=year_to,
                        cleaning_lens=lens,
                        source_id="edgar",
                        track_slug=campaign.track_slug,
                    )
                    outline_compare_repo_path = (
                        f"public/data/sec_narrative_drift_lab/{outline_compare_rel}"
                    )
                    outline_compare_request_url = _request_url(ticker, outline_compare_rel)
                    outline_compare_abs_path = REPO_ROOT / outline_compare_repo_path
                    outline_compare_present = outline_compare_abs_path.exists()
                    outline_compare_valid = False
                    if outline_compare_present:
                        try:
                            outline_payload_raw = read_json(outline_compare_abs_path)
                            outline_payload = as_dict(outline_payload_raw)
                            if outline_payload is not None:
                                outline_compare_valid = _validate_outline_compare_payload(
                                    outline_payload,
                                    lens=lens,
                                    campaign_provider=campaign.model_provider,
                                    campaign_model=campaign.model_name,
                                    expected_artifact_id="llm_outline_compare_runtime",
                                )
                        except Exception:
                            outline_compare_valid = False

                    outline_compare_insight_rel = canonical_outline_insight_relative_path(
                        ticker=ticker,
                        section=section,
                        year_from=year_from,
                        year_to=year_to,
                        cleaning_lens=lens,
                        source_id="edgar",
                        track_slug=campaign.track_slug,
                    )
                    outline_compare_insight_repo_path = (
                        f"public/data/sec_narrative_drift_lab/{outline_compare_insight_rel}"
                    )
                    outline_compare_insight_request_url = _request_url(ticker, outline_compare_insight_rel)
                    outline_compare_insight_abs_path = REPO_ROOT / outline_compare_insight_repo_path
                    outline_compare_insight_present = outline_compare_insight_abs_path.exists()
                    outline_compare_insight_valid = False
                    if outline_compare_insight_present:
                        try:
                            outline_insight_payload_raw = read_json(outline_compare_insight_abs_path)
                            outline_insight_payload = as_dict(outline_insight_payload_raw)
                            if outline_insight_payload is not None:
                                outline_compare_insight_valid = _validate_outline_compare_payload(
                                    outline_insight_payload,
                                    lens=lens,
                                    campaign_provider=campaign.model_provider,
                                    campaign_model=campaign.model_name,
                                    expected_artifact_id="llm_outline_compare_insight",
                                )
                        except Exception:
                            outline_compare_insight_valid = False

                    outline_research_rel = canonical_outline_research_relative_path(
                        ticker=ticker,
                        section=section,
                        year_from=year_from,
                        year_to=year_to,
                        cleaning_lens=lens,
                        source_id="edgar",
                        track_slug=campaign.track_slug,
                    )
                    outline_research_repo_path = (
                        f"public/data/sec_narrative_drift_lab/{outline_research_rel}"
                    )
                    outline_research_request_url = _request_url(ticker, outline_research_rel)
                    outline_research_abs_path = REPO_ROOT / outline_research_repo_path
                    outline_research_present = outline_research_abs_path.exists()
                    outline_research_valid = False
                    if outline_research_present:
                        try:
                            outline_research_payload_raw = read_json(outline_research_abs_path)
                            outline_research_payload = as_dict(outline_research_payload_raw)
                            if outline_research_payload is not None:
                                outline_research_valid = _validate_outline_research_payload(
                                    outline_research_payload,
                                    lens=lens,
                                )
                        except Exception:
                            outline_research_valid = False

                    present = abs_path.exists()
                    valid = False
                    reasons: list[str] = []
                    run_label = ""
                    input_file = ""
                    year_input_prev = ""
                    year_input_curr = ""
                    if present:
                        stats["present"] += 1
                        try:
                            output_payload = read_json(abs_path)
                            output_dict = as_dict(output_payload)
                            if output_dict is None:
                                reasons = ["output root is not object"]
                            else:
                                valid, reasons, run_label = _validate_variant_payload(
                                    payload=output_dict,
                                    detector_id=detector_id,
                                    lens=lens,
                                    campaign_provider=campaign.model_provider,
                                    campaign_model=campaign.model_name,
                                )
                                provenance = as_dict(output_dict.get("provenance"))
                                if provenance is not None:
                                    raw_input_file = provenance.get("input_file")
                                    if isinstance(raw_input_file, str):
                                        input_file = raw_input_file
                                        year_input_prev, year_input_curr = _load_year_refs(input_file)
                        except Exception as exc:  # noqa: BLE001
                            reasons = [f"failed to parse output: {exc}"]
                    else:
                        stats["missing"] += 1
                        reasons = ["file not found"]

                    if valid:
                        stats["valid"] += 1
                    elif present:
                        stats["invalid"] += 1

                    stats["targets"] += 1
                    rows.append(
                        {
                            "ticker": ticker.upper(),
                            "section": section,
                            "year_from": year_from,
                            "year_to": year_to,
                            "lens": lens,
                            "source_id": "edgar",
                            "detector_id": detector_id,
                            "campaign_id": campaign.track_id,
                            "campaign_slug": campaign.track_slug,
                            "display_name": campaign.display_name,
                            "input_mode": campaign.input_mode,
                            "runtime_visible": campaign.runtime_visible,
                            "model_provider": campaign.model_provider,
                            "model_name": campaign.model_name,
                            "filename": rel.split("/", 1)[1] if "/" in rel else rel,
                            "expected_repo_path": repo_path,
                            "request_url": request_url,
                            "present": present,
                            "valid": valid,
                            "run_label": run_label,
                            "input_file": input_file,
                            "year_input_prev": year_input_prev,
                            "year_input_curr": year_input_curr,
                            "outline_compare_present": outline_compare_present,
                            "outline_compare_valid": outline_compare_valid,
                            "outline_compare_expected_repo_path": outline_compare_repo_path,
                            "outline_compare_request_url": outline_compare_request_url,
                            "outline_compare_insight_present": outline_compare_insight_present,
                            "outline_compare_insight_valid": outline_compare_insight_valid,
                            "outline_compare_insight_expected_repo_path": outline_compare_insight_repo_path,
                            "outline_compare_insight_request_url": outline_compare_insight_request_url,
                            "outline_research_present": outline_research_present,
                            "outline_research_valid": outline_research_valid,
                            "outline_research_expected_repo_path": outline_research_repo_path,
                            "outline_research_request_url": outline_research_request_url,
                            "validation_reasons": reasons,
                        }
                    )
    return rows, stats


def build_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": "1.0",
        "updated_at": now_utc_iso(),
        "variants": rows,
        "provenance": {
            "script_version": SCRIPT_VERSION,
            "notes": [
                "Built from canonical path expectations in scripts/lab_output_tracks.py",
                "Run-label contract enforced at day precision (YYYY-MM-DD_...).",
            ],
        },
    }


def build_report_lines(
    registry_path: Path,
    out_path: Path,
    rows: list[dict[str, Any]],
    stats: dict[str, int],
) -> list[str]:
    lines: list[str] = []
    lines.append("# LLM Variants Index Build")
    lines.append("")
    lines.append(f"- script: `{SCRIPT_VERSION}`")
    lines.append(f"- registry: `{registry_path.as_posix()}`")
    lines.append(f"- out: `{out_path.as_posix()}`")
    lines.append(f"- targets: `{stats['targets']}`")
    lines.append(f"- present: `{stats['present']}`")
    lines.append(f"- valid: `{stats['valid']}`")
    lines.append(f"- invalid: `{stats['invalid']}`")
    lines.append(f"- missing: `{stats['missing']}`")
    lines.append("")
    lines.append("## Invalid or Missing Rows")
    missing = [row for row in rows if not row.get("valid")]
    if not missing:
        lines.append("- none")
        return lines
    for row in missing:
        lines.append(
            "- "
            + f"{row['campaign_id']} {row['ticker']} {row['year_from']}-{row['year_to']} {row['detector_id']}: "
            + f"{row['expected_repo_path']}"
        )
        for reason in row.get("validation_reasons", []):
            lines.append(f"  - {reason}")
    return lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build LLM variants index JSON.")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY_PATH))
    parser.add_argument("--out", default=str(DEFAULT_OUT_PATH))
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument(
        "--verbose-progress",
        action="store_true",
        help="Emit progress lines for each processed case.",
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
        registry_path = REPO_ROOT / registry_path
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = REPO_ROOT / report_path

    print(f"[phase] build variants rows start (script={SCRIPT_VERSION})", flush=True)
    rows, stats = build_variant_rows(
        registry_path=registry_path,
        verbose_progress=bool(args.verbose_progress),
        progress_interval_sec=max(1, int(args.progress_interval_sec)),
    )
    print("[phase] write variants index and report", flush=True)
    payload = build_payload(rows)
    write_json(out_path, payload)
    report_lines = build_report_lines(registry_path, out_path, rows, stats)
    write_text(report_path, report_lines)

    elapsed = int(time.monotonic() - started)
    print(f"Script: {SCRIPT_VERSION}")
    print(
        "Summary: "
        + f"targets={stats['targets']} present={stats['present']} "
        + f"valid={stats['valid']} invalid={stats['invalid']} missing={stats['missing']}"
    )
    print(f"Wrote variants index: {out_path}")
    print(f"Wrote report: {report_path}")
    print(f"Elapsed: {elapsed}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


