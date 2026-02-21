from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, cast

from lab_output_tracks import (  # type: ignore
    DETERMINISTIC_BASELINE_TRACK,
    DEFAULT_PRIMARY_LLM_CAMPAIGN_ID,
    canonical_output_filename,
    get_llm_campaign,
    is_llm_detector,
)
from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"
DEFAULT_REGISTRY = LAB_ROOT / "lab_cases_v1.json"
DEFAULT_MAP_JSON = REPO_ROOT / "reports" / "lab_output_path_migration_map.json"
DEFAULT_LLM_REPORT = REPO_ROOT / "reports" / "lab_llm_path_migration_map.md"
DEFAULT_DET_REPORT = REPO_ROOT / "reports" / "lab_deterministic_path_migration_map.md"


@dataclass(frozen=True)
class MigrationRow:
    ticker: str
    detector_id: str
    cleaning_lens: str
    source_id: str
    section: str
    year_from: int
    year_to: int
    old_rel: str
    new_rel: str
    old_abs: Path
    new_abs: Path
    kind: str
    track_slug: str


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def normalize_rel(path_value: str) -> str:
    return path_value.replace("\\", "/").lstrip("./")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def copy_if_needed(source: Path, destination: Path) -> bool:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and sha256_file(source) == sha256_file(destination):
        return False
    shutil.copy2(source, destination)
    return True


def build_rows(registry_path: Path) -> tuple[dict[str, Any], list[MigrationRow]]:
    payload = read_json(registry_path)
    if not isinstance(payload, dict):
        raise SystemExit(f"Registry root is not an object: {registry_path}")
    payload_d = cast(dict[str, Any], payload)
    cases_raw = payload_d.get("cases")
    if not isinstance(cases_raw, list):
        raise SystemExit(f"Registry missing cases[]: {registry_path}")
    cases = cast(list[Any], cases_raw)

    chatgpt_campaign = get_llm_campaign(DEFAULT_PRIMARY_LLM_CAMPAIGN_ID)
    if chatgpt_campaign is None:
        raise SystemExit("Primary ChatGPT campaign is not configured.")

    rows: list[MigrationRow] = []
    seen_keys: set[tuple[str, str, str]] = set()
    for case_entry in cases:
        if not isinstance(case_entry, dict):
            continue
        case = cast(dict[str, Any], case_entry)
        ticker = str(case.get("ticker", "")).upper()
        section = str(case.get("section", "10k_item1a"))
        year_from = case.get("year_from")
        year_to = case.get("year_to")
        outputs_raw = case.get("outputs")
        if not isinstance(year_from, int) or not isinstance(year_to, int):
            continue
        if not isinstance(outputs_raw, list):
            continue
        outputs = cast(list[Any], outputs_raw)
        for output_entry in outputs:
            if not isinstance(output_entry, dict):
                continue
            output = cast(dict[str, Any], output_entry)
            detector_id = str(output.get("detector_id", ""))
            cleaning_lens = str(output.get("cleaning_lens", "raw"))
            source_id = str(output.get("source_id", "edgar"))
            filename = str(output.get("filename", ""))
            if not detector_id or not filename:
                continue
            old_rel = f"{ticker}/{normalize_rel(filename)}"

            if is_llm_detector(detector_id):
                track_slug = chatgpt_campaign.track_slug
                kind = "llm"
            else:
                track_slug = DETERMINISTIC_BASELINE_TRACK.track_slug
                kind = "deterministic"

            new_filename = canonical_output_filename(
                detector_id=detector_id,
                section=section,
                year_from=year_from,
                year_to=year_to,
                cleaning_lens=cleaning_lens,
                source_id=source_id,
                track_slug=track_slug,
            )
            new_rel = f"{ticker}/outputs/{detector_id}/{track_slug}/{new_filename}"
            key = (ticker, detector_id, new_rel)
            if key in seen_keys:
                output["filename"] = new_rel.split("/", 1)[1]
                continue
            seen_keys.add(key)
            row = MigrationRow(
                ticker=ticker,
                detector_id=detector_id,
                cleaning_lens=cleaning_lens,
                source_id=source_id,
                section=section,
                year_from=year_from,
                year_to=year_to,
                old_rel=old_rel,
                new_rel=new_rel,
                old_abs=LAB_ROOT / old_rel,
                new_abs=LAB_ROOT / new_rel,
                kind=kind,
                track_slug=track_slug,
            )
            rows.append(row)
            output["filename"] = new_rel.split("/", 1)[1]

    return payload_d, rows


def build_map_payload(rows: list[MigrationRow]) -> dict[str, Any]:
    map_rows: list[dict[str, Any]] = []
    for row in rows:
        map_rows.append(
            {
                "ticker": row.ticker,
                "detector_id": row.detector_id,
                "cleaning_lens": row.cleaning_lens,
                "source_id": row.source_id,
                "section": row.section,
                "year_from": row.year_from,
                "year_to": row.year_to,
                "kind": row.kind,
                "track_slug": row.track_slug,
                "old_rel_path": f"public/data/sec_narrative_drift_lab/{row.old_rel}",
                "new_rel_path": f"public/data/sec_narrative_drift_lab/{row.new_rel}",
            }
        )
    return {
        "version": "1.0",
        "generated_by": SCRIPT_VERSION,
        "rows": map_rows,
    }


def build_report_lines(title: str, rows: list[MigrationRow]) -> list[str]:
    lines: list[str] = [f"# {title}", ""]
    lines.append(f"- script: `{SCRIPT_VERSION}`")
    lines.append(f"- rows: `{len(rows)}`")
    lines.append("")
    if not rows:
        lines.append("- none")
        return lines
    for row in rows:
        lines.append(
            f"- {row.ticker} {row.year_from}-{row.year_to} {row.detector_id} "
            + f"({row.cleaning_lens}/{row.source_id})"
        )
        lines.append(f"  - old: `public/data/sec_narrative_drift_lab/{row.old_rel}`")
        lines.append(f"  - new: `public/data/sec_narrative_drift_lab/{row.new_rel}`")
    return lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Migrate outputs to track-aware canonical paths.")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--map-json", default=str(DEFAULT_MAP_JSON))
    parser.add_argument("--llm-report", default=str(DEFAULT_LLM_REPORT))
    parser.add_argument("--det-report", default=str(DEFAULT_DET_REPORT))
    parser.add_argument("--no-hard-cut", action="store_true")
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Write map/reports only; do not copy/remove files and do not rewrite registry.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    registry_path = Path(args.registry)
    if not registry_path.is_absolute():
        registry_path = REPO_ROOT / registry_path
    map_json_path = Path(args.map_json)
    if not map_json_path.is_absolute():
        map_json_path = REPO_ROOT / map_json_path
    llm_report_path = Path(args.llm_report)
    if not llm_report_path.is_absolute():
        llm_report_path = REPO_ROOT / llm_report_path
    det_report_path = Path(args.det_report)
    if not det_report_path.is_absolute():
        det_report_path = REPO_ROOT / det_report_path

    registry_payload, rows = build_rows(registry_path)
    copied = 0
    removed = 0
    if not args.plan_only:
        for row in rows:
            if row.old_abs == row.new_abs:
                continue
            if not row.old_abs.exists():
                raise SystemExit(f"Source file missing during migration: {row.old_abs}")
            if copy_if_needed(row.old_abs, row.new_abs):
                copied += 1

        # hard cut removal of legacy paths
        if not args.no_hard_cut:
            for row in rows:
                if row.old_abs == row.new_abs:
                    continue
                if row.old_abs.exists():
                    row.old_abs.unlink()
                    removed += 1

        # write updated registry
        write_json(registry_path, registry_payload)

    # write reports and map json
    map_payload = build_map_payload(rows)
    write_json(map_json_path, map_payload)
    llm_rows = [row for row in rows if row.kind == "llm"]
    det_rows = [row for row in rows if row.kind == "deterministic"]
    write_text(llm_report_path, build_report_lines("LLM Path Migration Map", llm_rows))
    write_text(
        det_report_path,
        build_report_lines("Deterministic Path Migration Map", det_rows),
    )

    print(f"Script: {SCRIPT_VERSION}")
    print(
        f"Migrated rows={len(rows)} copied={copied} removed_legacy={removed} hard_cut={not args.no_hard_cut} plan_only={args.plan_only}"
    )
    if not args.plan_only:
        print(f"Updated registry: {registry_path}")
    print(f"Wrote map json: {map_json_path}")
    print(f"Wrote llm report: {llm_report_path}")
    print(f"Wrote deterministic report: {det_report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
