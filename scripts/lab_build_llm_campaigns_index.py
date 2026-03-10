from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from lab_output_tracks import (  # type: ignore
    DEFAULT_COMPARE_LLM_CAMPAIGN_ID,
    DEFAULT_PRIMARY_LLM_CAMPAIGN_ID,
    LLM_CAMPAIGNS,
)
from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_PATH = (
    REPO_ROOT
    / "public"
    / "data"
    / "sec_narrative_drift_lab"
    / "lab_llm_campaigns_v1.json"
)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_payload(
    *,
    verbose_progress: bool = False,
    progress_interval_sec: int = 300,
) -> dict[str, Any]:
    public_campaigns = [campaign for campaign in LLM_CAMPAIGNS if campaign.runtime_visible]
    campaigns: list[dict[str, Any]] = []
    started = time.monotonic()
    last_heartbeat = started
    total = len(public_campaigns)
    for index, campaign in enumerate(public_campaigns, start=1):
        campaigns.append(
            {
                "campaign_id": campaign.track_id,
                "campaign_slug": campaign.track_slug,
                "display_name": campaign.display_name,
                "input_mode": campaign.input_mode,
                "model_provider": campaign.model_provider,
                "model_name": campaign.model_name,
                "run_label_prefix_template": campaign.run_label_prefix_template,
                "instructions_asset": campaign.instructions_asset_name,
                "primary_for_runtime": campaign.primary_for_runtime,
                "compare_default": campaign.compare_default,
                "runtime_visible": campaign.runtime_visible,
            }
        )
        now = time.monotonic()
        if verbose_progress or now - last_heartbeat >= progress_interval_sec:
            elapsed = int(now - started)
            print(
                "[progress] campaigns_index "
                + f"campaigns={index}/{total} elapsed={elapsed}s",
                flush=True,
            )
            last_heartbeat = now

    return {
        "version": "1.0",
        "updated_at": now_utc_iso(),
        "primary_campaign_id": DEFAULT_PRIMARY_LLM_CAMPAIGN_ID,
        "compare_default_campaign_id": DEFAULT_COMPARE_LLM_CAMPAIGN_ID,
        "campaigns": campaigns,
        "provenance": {
            "script_version": SCRIPT_VERSION,
            "notes": [
                "Generated from scripts/lab_output_tracks.py (runtime-visible campaigns only)",
                "Day-precise run label contract: YYYY-MM-DD_<campaign_tag>",
            ],
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build public LLM campaigns index JSON.")
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT_PATH),
        help="Output path for lab_llm_campaigns_v1.json",
    )
    parser.add_argument(
        "--verbose-progress",
        action="store_true",
        help="Emit progress lines for each campaign processed.",
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
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path
    print(f"[phase] build campaigns index start (script={SCRIPT_VERSION})", flush=True)
    payload = build_payload(
        verbose_progress=bool(args.verbose_progress),
        progress_interval_sec=max(1, int(args.progress_interval_sec)),
    )
    print("[phase] write campaigns index", flush=True)
    write_json(out_path, payload)
    elapsed = int(time.monotonic() - started)
    print(f"Script: {SCRIPT_VERSION}")
    print(f"Wrote campaigns index: {out_path}")
    print(f"Elapsed: {elapsed}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
