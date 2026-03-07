from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, cast

from lab_output_tracks import CORE4_SHOWCASE_TICKERS
from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCAN_JSON = REPO_ROOT / "reports" / "sec_recent_annual_scan.json"
DEFAULT_SCAN_CSV = REPO_ROOT / "reports" / "sec_recent_annual_scan.csv"
DEFAULT_SCAN_MD = REPO_ROOT / "reports" / "sec_recent_annual_scan.md"
def _get_default_user_agent() -> str:
    value = os.environ.get("SEC_USER_AGENT", "").strip()
    if not value:
        raise RuntimeError(
            "SEC_USER_AGENT env var is required. "
            "Set it to your name and contact email per SEC EDGAR fair-access policy."
        )
    return value


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def parse_csv_tokens(raw: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for token in raw.split(","):
        cleaned = token.strip().upper()
        if not cleaned:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
    return out


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def to_repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except Exception:
        return path.as_posix()


def run_cmd(cmd: list[str], *, dry_run: bool, env: dict[str, str]) -> None:
    printable = " ".join(shlex.quote(part) for part in cmd)
    print(f"> {printable}")
    if dry_run:
        return
    subprocess.run(cmd, cwd=REPO_ROOT, check=True, env=env)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Two-pass targeted SEC refresh pipeline: all-SEC recent-annual discovery, "
            "then ingest/rebuild for Core4 + ranked shortlist."
        )
    )
    parser.add_argument("--run-scan", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--scan-json", default=str(DEFAULT_SCAN_JSON))
    parser.add_argument("--scan-csv", default=str(DEFAULT_SCAN_CSV))
    parser.add_argument("--scan-md", default=str(DEFAULT_SCAN_MD))
    parser.add_argument("--scan-window-days", type=int, default=90)
    parser.add_argument("--scan-top-shortlist", type=int, default=12)
    parser.add_argument("--scan-max-tickers", type=int, default=0)
    parser.add_argument("--core4", default=",".join(CORE4_SHOWCASE_TICKERS))
    parser.add_argument("--shortlist-size", type=int, default=12)
    parser.add_argument("--start-year", type=int, default=2015)
    parser.add_argument("--sleep-ms", type=int, default=120)
    parser.add_argument("--user-agent", default=None)
    parser.add_argument("--rebuild-lab-assets", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--publish-bundle", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--bundle-out", default="")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    user_agent = (args.user_agent or "").strip() or _get_default_user_agent()
    run_env = os.environ.copy()
    run_env["SEC_USER_AGENT"] = user_agent

    scan_json = Path(args.scan_json)
    if not scan_json.is_absolute():
        scan_json = (REPO_ROOT / scan_json).resolve()
    scan_csv = Path(args.scan_csv)
    if not scan_csv.is_absolute():
        scan_csv = (REPO_ROOT / scan_csv).resolve()
    scan_md = Path(args.scan_md)
    if not scan_md.is_absolute():
        scan_md = (REPO_ROOT / scan_md).resolve()

    if args.run_scan:
        scan_cmd = [
            "python",
            "scripts/sec_scan_recent_annuals.py",
            "--window-days",
            str(args.scan_window_days),
            "--top-shortlist",
            str(args.scan_top_shortlist),
            "--out-json",
            to_repo_rel(scan_json),
            "--out-csv",
            to_repo_rel(scan_csv),
            "--out-md",
            to_repo_rel(scan_md),
            "--user-agent",
            user_agent,
        ]
        if args.scan_max_tickers > 0:
            scan_cmd.extend(["--max-tickers", str(args.scan_max_tickers)])
        run_cmd(scan_cmd, dry_run=args.dry_run, env=run_env)

    if not scan_json.exists() and not args.dry_run:
        raise SystemExit(f"Scan JSON not found: {scan_json}")

    scan_payload: dict[str, Any] = {}
    if scan_json.exists():
        loaded = read_json(scan_json)
        if not isinstance(loaded, dict):
            raise SystemExit(f"Invalid scan JSON root: {scan_json}")
        scan_payload = cast(dict[str, Any], loaded)

    core4 = parse_csv_tokens(args.core4)
    shortlist_from_scan: list[str] = []
    shortlist_payload = scan_payload.get("shortlist")
    if isinstance(shortlist_payload, dict):
        typed_shortlist = cast(dict[str, object], shortlist_payload)
        raw_tickers = typed_shortlist.get("tickers")
        if isinstance(raw_tickers, list):
            for item in cast(list[object], raw_tickers):
                if isinstance(item, str):
                    shortlist_from_scan.append(item.upper())

    shortlist: list[str] = []
    for ticker in shortlist_from_scan:
        if ticker in core4 or ticker in shortlist:
            continue
        shortlist.append(ticker)
        if len(shortlist) >= max(0, int(args.shortlist_size)):
            break

    target_tickers: list[str] = []
    for ticker in core4 + shortlist:
        if ticker not in target_tickers:
            target_tickers.append(ticker)

    print(
        "Pipeline targets: "
        + ", ".join(target_tickers)
        + f" (core4={len(core4)}, shortlist={len(shortlist)})"
    )

    for ticker in target_tickers:
        fetch_cmd = [
            "python",
            "scripts/sec_fetch_and_build.py",
            "--ticker",
            ticker,
            "--start-year",
            str(args.start_year),
            "--incremental",
            "--include-20f",
            "--cache-debug-html",
            "--force-html-cache",
        ]
        run_cmd(fetch_cmd, dry_run=args.dry_run, env=run_env)
        if args.sleep_ms > 0:
            run_cmd(
                [
                    "python",
                    "-c",
                    f"import time; time.sleep({args.sleep_ms}/1000)",
                ],
                dry_run=args.dry_run,
                env=run_env,
            )

    tickers_csv = ",".join(target_tickers)
    run_cmd(
        [
            "python",
            "scripts/refresh_risk_cache_from_html.py",
            "--tickers",
            tickers_csv,
            "--workers",
            "1",
        ],
        dry_run=args.dry_run,
        env=run_env,
    )
    run_cmd(
        ["python", "scripts/rebuild_ticker_year_index_from_cache.py"],
        dry_run=args.dry_run,
        env=run_env,
    )
    run_cmd(
        [
            "python",
            "scripts/sec_risk_extraction_audit.py",
            "--out-csv",
            "reports/sec_risk_extraction_audit.csv",
            "--out-json",
            "reports/sec_risk_extraction_audit.json",
            "--deep-out-json",
            "reports/sec_risk_extraction_audit.deep.json",
            "--limit",
            "0",
            "--top",
            "30",
        ],
        dry_run=args.dry_run,
        env=run_env,
    )
    run_cmd(["python", "scripts/build_risk_manual_checklist.py"], dry_run=args.dry_run, env=run_env)
    run_cmd(
        ["python", "scripts/sec_risk_extraction_report.py", "--fast"],
        dry_run=args.dry_run,
        env=run_env,
    )
    run_cmd(["python", "scripts/sec_build_index.py"], dry_run=args.dry_run, env=run_env)
    run_cmd(
        ["python", "scripts/sec_validate_cache.py", "--require-risk-exports"],
        dry_run=args.dry_run,
        env=run_env,
    )
    run_cmd(["python", "scripts/sec_validate_public_data.py"], dry_run=args.dry_run, env=run_env)

    if args.rebuild_lab_assets:
        run_cmd(
            [
                "python",
                "scripts/build_showcase_roster_continuity.py",
                "--tickers",
                ",".join(core4),
                "--pair-policy",
                "latest_two",
                "--year_min",
                "2019",
                "--year_max",
                "2030",
            ],
            dry_run=args.dry_run,
            env=run_env,
        )
        run_cmd(["python", "scripts/select_showcase_hero_pairs.py"], dry_run=args.dry_run, env=run_env)

        if args.bundle_out:
            bundle_out = Path(args.bundle_out)
            if not bundle_out.is_absolute():
                bundle_out = (REPO_ROOT / bundle_out).resolve()
        else:
            bundle_out = REPO_ROOT / "bundles" / f"showcase_llm_inputs_full_section_v2_{now_stamp()}"

        run_cmd(
            [
                "python",
                "scripts/build_showcase_llm_inputs_bundle.py",
                "--out_dir",
                to_repo_rel(bundle_out),
            ],
            dry_run=args.dry_run,
            env=run_env,
        )
        if args.publish_bundle:
            run_cmd(
                [
                    "python",
                    "scripts/lab_publish_llm_inputs_v2.py",
                    "--bundle",
                    to_repo_rel(bundle_out),
                ],
                dry_run=args.dry_run,
                env=run_env,
            )

        run_cmd(
            [
                "python",
                "scripts/lab_build_cases_registry_v1.py",
                "--pair-policy",
                "latest_two",
                "--adjacent-only",
            ],
            dry_run=args.dry_run,
            env=run_env,
        )
        run_cmd(["python", "scripts/lab_build_llm_variants_index.py"], dry_run=args.dry_run, env=run_env)

        manifest_cmds = [
            [
                "python",
                "scripts/lab_build_llm_master_manifest.py",
                "--campaign-id",
                "openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27",
                "--master-artifact-id",
                "llm_outline_compare_structured",
                "--pair-policy",
                "latest_two",
                "--out-json",
                "reports/lab_llm_master_manifest_codex_real.json",
                "--out-md",
                "reports/lab_llm_master_manifest_codex_real.md",
            ],
            [
                "python",
                "scripts/lab_build_llm_master_manifest.py",
                "--campaign-id",
                "openai_chatgpt52ext_agent_fullsec_real_2026-02-27",
                "--master-artifact-id",
                "llm_outline_compare_structured",
                "--pair-policy",
                "latest_two",
                "--out-json",
                "reports/lab_llm_master_manifest_chatgpt_real.json",
                "--out-md",
                "reports/lab_llm_master_manifest_chatgpt_real.md",
            ],
            [
                "python",
                "scripts/lab_build_llm_master_manifest.py",
                "--campaign-id",
                "openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27",
                "--master-artifact-id",
                "llm_outline_compare_insight",
                "--pair-policy",
                "latest_two",
                "--out-json",
                "reports/lab_llm_master_manifest_codex_real_insight.json",
                "--out-md",
                "reports/lab_llm_master_manifest_codex_real_insight.md",
            ],
        ]
        for cmd in manifest_cmds:
            cmd.extend(["--bundle", to_repo_rel(bundle_out)])
            run_cmd(cmd, dry_run=args.dry_run, env=run_env)

        starter_cmds = [
            [
                "python",
                "scripts/lab_emit_master_thread_starters.py",
                "--manifest",
                "reports/lab_llm_master_manifest_codex_real.json",
                "--out",
                "reports/lab_llm_master_thread_starters_codex_real.md",
                "--validation-report",
                "reports/lab_llm_master_validation_codex_real.md",
                "--quality-report",
                "reports/lab_llm_master_quality_codex_real.md",
                "--format",
                "vscode_autowrite_structured_prod",
            ],
            [
                "python",
                "scripts/lab_emit_master_thread_starters.py",
                "--manifest",
                "reports/lab_llm_master_manifest_chatgpt_real.json",
                "--out",
                "reports/lab_llm_master_thread_starters_chatgpt_real.md",
                "--validation-report",
                "reports/lab_llm_master_validation_chatgpt_real.md",
                "--quality-report",
                "reports/lab_llm_master_quality_chatgpt_real.md",
                "--format",
                "vscode_autowrite_structured_prod",
            ],
            [
                "python",
                "scripts/lab_emit_master_thread_starters.py",
                "--manifest",
                "reports/lab_llm_master_manifest_codex_real_insight.json",
                "--out",
                "reports/lab_llm_master_thread_starters_codex_real_insight.md",
                "--validation-report",
                "reports/lab_llm_master_validation_codex_real.md",
                "--quality-report",
                "reports/lab_llm_master_quality_codex_real.md",
                "--format",
                "vscode_autowrite_insight_exp",
            ],
        ]
        for cmd in starter_cmds:
            run_cmd(cmd, dry_run=args.dry_run, env=run_env)

    print("Latest-two targeted refresh pipeline complete.")
    print(f"Script: {SCRIPT_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
