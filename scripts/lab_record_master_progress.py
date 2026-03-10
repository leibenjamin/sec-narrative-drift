from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, cast

from lab_audit_master_output_quality import evaluate_output
from lab_output_tracks import (
    DEFAULT_PRIMARY_LLM_CAMPAIGN_ID,
    get_llm_campaign,
    get_report_token_for_campaign_id,
)
from lab_script_version import build_script_version
from lab_validate_llm_master_outputs import (
    REPO_ROOT,
    MasterTarget,
    load_targets,
    validate_targets,
)

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
DEFAULT_MANIFEST_PATH = REPO_ROOT / "reports" / "lab_llm_master_manifest.json"


def _campaign_slug_token(campaign_id: str) -> str:
    return get_report_token_for_campaign_id(campaign_id)


def default_report_md_for_campaign(campaign_id: str) -> Path:
    token = _campaign_slug_token(campaign_id)
    return REPO_ROOT / "reports" / f"lab_llm_master_batch_progress_{token}.md"


def default_history_json_for_campaign(campaign_id: str) -> Path:
    token = _campaign_slug_token(campaign_id)
    return REPO_ROOT / "reports" / f"lab_llm_master_batch_progress_{token}.json"


@dataclass(frozen=True)
class ProgressSnapshot:
    timestamp_utc: str
    label: str
    campaign_id: str
    targets: int
    present: int
    missing: int
    invalid: int
    blockers: int
    present_flag_mismatch: int

    def to_dict(self) -> dict[str, object]:
        return {
            "timestamp_utc": self.timestamp_utc,
            "label": self.label,
            "campaign_id": self.campaign_id,
            "targets": self.targets,
            "present": self.present,
            "missing": self.missing,
            "invalid": self.invalid,
            "blockers": self.blockers,
            "present_flag_mismatch": self.present_flag_mismatch,
        }


def as_dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    typed_list = cast(list[Any], value)
    output: list[dict[str, object]] = []
    for item in typed_list:
        if isinstance(item, dict):
            typed_dict = cast(dict[Any, Any], item)
            normalized: dict[str, object] = {}
            for key, sub in typed_dict.items():
                if isinstance(key, str):
                    normalized[key] = sub
            output.append(normalized)
    return output


def as_int(value: object) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def as_str(value: object) -> Optional[str]:
    if isinstance(value, str):
        return value
    return None


def load_history(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return []
    return as_dict_list(payload)


def write_json(path: Path, payload: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def filter_targets_for_campaign(
    manifest_path: Path,
    campaign_id: str,
) -> tuple[str, list[MasterTarget]]:
    campaign = get_llm_campaign(campaign_id)
    if campaign is None:
        raise SystemExit(f"Unknown campaign id: {campaign_id}")
    targets_all = load_targets(manifest_path)
    marker = f"/{campaign.track_slug}/"
    filtered: list[MasterTarget] = []
    for target in targets_all:
        normalized = "/" + target.expected_output_path.replace("\\", "/").lstrip("/")
        if marker in normalized:
            filtered.append(target)
    return campaign.track_slug, filtered


def compute_snapshot(
    manifest_path: Path,
    campaign_id: str,
    label: str,
) -> ProgressSnapshot:
    campaign = get_llm_campaign(campaign_id)
    if campaign is None or campaign.model_provider is None or campaign.model_name is None:
        raise SystemExit(f"Unknown or invalid campaign id: {campaign_id}")

    _track_slug, targets = filter_targets_for_campaign(manifest_path, campaign_id)
    present_count = 0
    for target in targets:
        output_path = (REPO_ROOT / target.expected_output_path).resolve()
        if output_path.exists():
            present_count += 1

    missing, invalid, mismatch = validate_targets(
        targets=targets,
        expected_model_provider=campaign.model_provider,
        expected_model_name=campaign.model_name,
        verbose_progress=False,
        progress_interval_sec=300,
    )

    blocker_count = 0
    for target in targets:
        output_path = (REPO_ROOT / target.expected_output_path).resolve()
        if not output_path.exists():
            continue
        audit = evaluate_output(
            path=output_path,
            target=target,
            expected_model_provider=campaign.model_provider,
            expected_model_name=campaign.model_name,
        )
        blocker_count += len(audit.blockers)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return ProgressSnapshot(
        timestamp_utc=timestamp,
        label=label,
        campaign_id=campaign_id,
        targets=len(targets),
        present=present_count,
        missing=len(missing),
        invalid=len(invalid),
        blockers=blocker_count,
        present_flag_mismatch=len(mismatch),
    )


def build_report(
    snapshot: ProgressSnapshot,
    history: list[dict[str, object]],
    delta: dict[str, int],
) -> list[str]:
    lines: list[str] = []
    lines.append("# LLM Master Batch Progress")
    lines.append("")
    lines.append(f"Script: {SCRIPT_VERSION}")
    lines.append(f"Campaign: {snapshot.campaign_id}")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| Timestamp (UTC) | {snapshot.timestamp_utc} |")
    lines.append(f"| Label | {snapshot.label} |")
    lines.append(f"| Targets | {snapshot.targets} |")
    lines.append(f"| Present | {snapshot.present} |")
    lines.append(f"| Missing | {snapshot.missing} |")
    lines.append(f"| Invalid | {snapshot.invalid} |")
    lines.append(f"| Blockers | {snapshot.blockers} |")
    lines.append(f"| Present-flag mismatches | {snapshot.present_flag_mismatch} |")
    lines.append("")
    lines.append("| Delta metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| Delta present | {delta['present']:+d} |")
    lines.append(f"| Delta invalid | {delta['invalid']:+d} |")
    lines.append(f"| Delta blockers | {delta['blockers']:+d} |")
    lines.append("")
    lines.append("## History")
    lines.append("| Timestamp (UTC) | Label | Present | Invalid | Blockers | Missing |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for row in history[-20:]:
        ts = as_str(row.get("timestamp_utc")) or "unknown"
        label = as_str(row.get("label")) or "-"
        present = as_int(row.get("present"))
        invalid = as_int(row.get("invalid"))
        blockers = as_int(row.get("blockers"))
        missing = as_int(row.get("missing"))
        lines.append(
            "| "
            + f"{ts} | {label} | {present if present is not None else '?'} | "
            + f"{invalid if invalid is not None else '?'} | "
            + f"{blockers if blockers is not None else '?'} | "
            + f"{missing if missing is not None else '?'} |"
        )
    return lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record batch-level LLM master progress with count deltas."
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST_PATH))
    parser.add_argument("--campaign-id", default=DEFAULT_PRIMARY_LLM_CAMPAIGN_ID)
    parser.add_argument(
        "--report-md",
        default="",
        help=(
            "Markdown progress report path. If omitted, writes a campaign-scoped "
            "report under reports/."
        ),
    )
    parser.add_argument(
        "--history-json",
        default="",
        help=(
            "Progress history JSON path. If omitted, writes a campaign-scoped "
            "history file under reports/."
        ),
    )
    parser.add_argument("--label", default="")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    started = time.monotonic()
    args = build_parser().parse_args(argv)
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = (REPO_ROOT / manifest_path).resolve()
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")

    report_md_arg = str(args.report_md).strip()
    report_md = Path(report_md_arg) if report_md_arg else default_report_md_for_campaign(str(args.campaign_id))
    if not report_md.is_absolute():
        report_md = (REPO_ROOT / report_md).resolve()

    history_json_arg = str(args.history_json).strip()
    history_json = Path(history_json_arg) if history_json_arg else default_history_json_for_campaign(str(args.campaign_id))
    if not history_json.is_absolute():
        history_json = (REPO_ROOT / history_json).resolve()

    snapshot_label = str(args.label).strip()
    if not snapshot_label:
        snapshot_label = "checkpoint"

    print(f"[phase] record batch progress start (script={SCRIPT_VERSION})", flush=True)
    history = load_history(history_json)
    snapshot = compute_snapshot(
        manifest_path=manifest_path,
        campaign_id=str(args.campaign_id),
        label=snapshot_label,
    )
    delta = {"present": 0, "invalid": 0, "blockers": 0}
    if history:
        last = history[-1]
        last_present = as_int(last.get("present"))
        last_invalid = as_int(last.get("invalid"))
        last_blockers = as_int(last.get("blockers"))
        if last_present is not None:
            delta["present"] = snapshot.present - last_present
        if last_invalid is not None:
            delta["invalid"] = snapshot.invalid - last_invalid
        if last_blockers is not None:
            delta["blockers"] = snapshot.blockers - last_blockers

    history.append(snapshot.to_dict())
    write_json(history_json, history)
    report_lines = build_report(snapshot=snapshot, history=history, delta=delta)
    write_text(report_md, report_lines)

    elapsed = int(time.monotonic() - started)
    print(
        "BATCH_PROGRESS "
        + f"targets={snapshot.targets} present={snapshot.present} missing={snapshot.missing} "
        + f"invalid={snapshot.invalid} blockers={snapshot.blockers} "
        + f"delta_present={delta['present']:+d} delta_invalid={delta['invalid']:+d} "
        + f"delta_blockers={delta['blockers']:+d}"
    )
    print(f"Wrote report: {report_md}")
    print(f"Wrote history: {history_json}")
    print(f"Elapsed: {elapsed}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
