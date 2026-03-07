from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from lab_script_version import build_script_version
from lab_output_tracks import DEFAULT_PRIMARY_LLM_CAMPAIGN_ID, get_llm_campaign
from lab_llm_precompute_utils import as_list, as_str_dict, get_str, read_json
from lab_validate_llm_master_outputs import DEFAULT_MANIFEST_PATH, matches_only_token

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]

STRUCTURED_FIELDS = (
    "lab_schema_version",
    "artifact_schema_version",
    "ticker",
    "section",
    "source_id",
    "cleaning_lens",
    "year_from",
    "year_to",
    "outline_prev",
    "outline_curr",
    "node_alignment",
    "material_changes",
    "evidence_bank",
    "lens_divergence",
    "risk_graph_prev",
    "risk_graph_curr",
    "change_mechanisms",
    "uncertainty_and_limits",
    "investor_relevance",
    "projection_contract",
    "provenance",
)


@dataclass(frozen=True)
class ProjectionTarget:
    source_insight_path: Path
    target_structured_path: Path
    source_insight_display: str


def resolve_repo_relative(path_value: str) -> Path:
    return (REPO_ROOT / path_value).resolve()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def derive_structured_path_from_insight(insight_path: str) -> Optional[str]:
    normalized = insight_path.replace("\\", "/")
    if "llm_outline_compare_insight" not in normalized:
        return None
    return (
        normalized.replace("/llm_outline_compare_insight/", "/llm_outline_compare_structured/")
        .replace("lab_llm_outline_compare_insight_", "lab_llm_outline_compare_structured_")
    )


def load_targets(
    manifest_path: Path,
    campaign_slug: str,
    only: str,
    only_mode: str,
) -> list[ProjectionTarget]:
    payload = read_json(manifest_path)
    root = as_str_dict(payload)
    if root is None:
        raise SystemExit(f"Manifest root must be object: {manifest_path}")
    entries = as_list(root.get("entries"))
    if entries is None:
        raise SystemExit(f"Manifest missing entries list: {manifest_path}")

    filters = [token.strip() for token in only.split(",") if token.strip()]
    targets: list[ProjectionTarget] = []
    for entry_any in entries:
        entry = as_str_dict(entry_any)
        if entry is None:
            continue
        master_output = as_str_dict(entry.get("master_output"))
        projected_v2 = as_str_dict(entry.get("projected_master_output_structured"))
        if master_output is None:
            continue
        source_insight = get_str(master_output.get("expected_output_path"))
        source_artifact_id = get_str(master_output.get("artifact_id"))
        if source_insight is None:
            continue
        if source_artifact_id not in {None, "llm_outline_compare_insight"} and "llm_outline_compare_insight" not in source_insight:
            continue

        normalized = "/" + source_insight.replace("\\", "/").lstrip("/")
        if f"/{campaign_slug}/" not in normalized:
            continue
        if filters and not any(matches_only_token(source_insight, token, mode=only_mode) for token in filters):
            continue

        target_structured = get_str(projected_v2.get("expected_output_path")) if projected_v2 is not None else None
        if not target_structured:
            target_structured = derive_structured_path_from_insight(source_insight)
        if not target_structured:
            continue

        targets.append(
            ProjectionTarget(
                source_insight_path=resolve_repo_relative(source_insight),
                target_structured_path=resolve_repo_relative(target_structured),
                source_insight_display=source_insight,
            )
        )
    return targets


def project_payload(insight_payload: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for field in STRUCTURED_FIELDS:
        output[field] = insight_payload.get(field)
    output["artifact_id"] = "llm_outline_compare_structured"
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Project llm_outline_compare_insight master artifacts into llm_outline_compare_structured outputs."
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST_PATH))
    parser.add_argument("--campaign-id", default=DEFAULT_PRIMARY_LLM_CAMPAIGN_ID)
    parser.add_argument("--only", default="")
    parser.add_argument(
        "--only-mode",
        choices=("substring", "basename", "exact_path"),
        default="substring",
        help="Matching mode for --only token(s) against source insight path.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--verbose-progress",
        action="store_true",
        help="Emit progress lines for each projection target.",
    )
    parser.add_argument(
        "--progress-interval-sec",
        type=int,
        default=300,
        help="Heartbeat interval in seconds for long-running operations.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    campaign = get_llm_campaign(args.campaign_id)
    if campaign is None:
        raise SystemExit(f"Unknown campaign id: {args.campaign_id}")

    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = (REPO_ROOT / manifest_path).resolve()
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")

    print(f"[phase] insight->structured projection start (script={SCRIPT_VERSION})", flush=True)
    targets = load_targets(
        manifest_path=manifest_path,
        campaign_slug=campaign.track_slug,
        only=str(args.only),
        only_mode=str(args.only_mode),
    )
    projected = 0
    skipped = 0
    started = time.monotonic()
    last_heartbeat = started
    interval = max(1, int(args.progress_interval_sec))
    for index, target in enumerate(targets, start=1):
        now = time.monotonic()
        if args.verbose_progress or now - last_heartbeat >= interval:
            print(
                "[progress] insight_to_structured_projection "
                + f"targets={index}/{len(targets)} projected={projected} skipped={skipped}",
                flush=True,
            )
            last_heartbeat = now
        if not target.source_insight_path.exists():
            skipped += 1
            continue
        try:
            payload_raw = json.loads(target.source_insight_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            skipped += 1
            continue
        payload = as_str_dict(payload_raw)
        if payload is None:
            skipped += 1
            continue
        if payload.get("artifact_id") != "llm_outline_compare_insight":
            skipped += 1
            continue
        output_payload = project_payload(payload)
        if not args.dry_run:
            write_json(target.target_structured_path, output_payload)
        projected += 1

    elapsed = int(time.monotonic() - started)
    print(
        "INSIGHT_TO_STRUCTURED_PROJECTION "
        + f"targets={len(targets)} projected={projected} skipped={skipped} dry_run={bool(args.dry_run)}"
    )
    print(f"Elapsed: {elapsed}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
