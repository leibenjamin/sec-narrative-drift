from __future__ import annotations

import argparse
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]


def to_repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except Exception:
        return path.as_posix()


def utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def run_cmd(args: list[str]) -> None:
    printable = " ".join(shlex.quote(part) for part in args)
    print(f"> {printable}")
    subprocess.run(args, cwd=REPO_ROOT, check=True)


def default_manifest_paths(campaign_id: str) -> tuple[Path, Path, Path]:
    if "chatgpt52ext" in campaign_id:
        return (
            REPO_ROOT / "reports" / "lab_llm_run_manifest_chatgpt52ext.md",
            REPO_ROOT / "reports" / "lab_llm_run_manifest_chatgpt52ext.json",
            REPO_ROOT / "reports" / "lab_llm_manifest_validation_chatgpt52ext.md",
        )
    return (
        REPO_ROOT / "reports" / "lab_llm_run_manifest.md",
        REPO_ROOT / "reports" / "lab_llm_run_manifest.json",
        REPO_ROOT / "reports" / "lab_llm_manifest_validation.md",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run end-to-end full_section_v2 campaign pipeline."
    )
    parser.add_argument("--campaign-id", required=True, help="Campaign id from lab_output_tracks.py")
    parser.add_argument(
        "--bundle",
        default="",
        help="Existing bundle root. If omitted, script builds a fresh showcase bundle.",
    )
    parser.add_argument(
        "--run-day",
        default=utc_day(),
        help="Run-day label for generator (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--lenses",
        default="raw,deboilerplated",
        help="Comma-separated lenses to build into the manifest.",
    )
    parser.add_argument(
        "--source-id",
        default="edgar",
        help="Input source id for manifest generation.",
    )
    parser.add_argument(
        "--manifest-md",
        default="",
        help="Manifest markdown output path (defaults by campaign).",
    )
    parser.add_argument(
        "--manifest-json",
        default="",
        help="Manifest JSON output path (defaults by campaign).",
    )
    parser.add_argument(
        "--validation-report",
        default="",
        help="Validator report output path (defaults by campaign).",
    )
    parser.add_argument(
        "--skip-generate",
        action="store_true",
        help="Skip output generation step (useful for manual campaign runs).",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Pass through allow-missing to manifest validator.",
    )
    parser.add_argument(
        "--allow-invalid",
        action="store_true",
        help="Pass through allow-invalid to manifest validator.",
    )
    parser.add_argument(
        "--no-clean-publish",
        action="store_true",
        help="Preserve existing public llm_inputs_v2 files during publish sync.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    default_md, default_json, default_validation = default_manifest_paths(args.campaign_id)
    manifest_md = Path(args.manifest_md) if args.manifest_md else default_md
    manifest_json = Path(args.manifest_json) if args.manifest_json else default_json
    validation_report = (
        Path(args.validation_report) if args.validation_report else default_validation
    )
    if not manifest_md.is_absolute():
        manifest_md = (REPO_ROOT / manifest_md).resolve()
    if not manifest_json.is_absolute():
        manifest_json = (REPO_ROOT / manifest_json).resolve()
    if not validation_report.is_absolute():
        validation_report = (REPO_ROOT / validation_report).resolve()

    bundle_path: Path
    if args.bundle:
        bundle_path = Path(args.bundle)
        if not bundle_path.is_absolute():
            bundle_path = (REPO_ROOT / bundle_path).resolve()
    else:
        bundle_path = (
            REPO_ROOT / "bundles" / f"showcase_llm_inputs_full_section_v2_{utc_stamp()}"
        )
        run_cmd(
            [
                "python",
                "scripts/build_showcase_llm_inputs_bundle.py",
                "--out_dir",
                to_repo_rel(bundle_path),
            ]
        )

    if not bundle_path.exists():
        raise SystemExit(f"Bundle not found: {bundle_path}")

    publish_cmd = [
        "python",
        "scripts/lab_publish_llm_inputs_v2.py",
        "--bundle",
        to_repo_rel(bundle_path),
    ]
    if args.no_clean_publish:
        publish_cmd.append("--no-clean")
    run_cmd(publish_cmd)

    run_cmd(
        [
            "python",
            "scripts/lab_build_llm_run_manifest.py",
            "--campaign-id",
            args.campaign_id,
            "--bundle",
            to_repo_rel(bundle_path),
            "--input-mode",
            "full_section_v2",
            "--lenses",
            args.lenses,
            "--source-id",
            args.source_id,
            "--out-md",
            to_repo_rel(manifest_md),
            "--out-json",
            to_repo_rel(manifest_json),
        ]
    )

    if not args.skip_generate:
        run_cmd(
            [
                "python",
                "scripts/lab_generate_codex_campaign_outputs.py",
                "--manifest",
                to_repo_rel(manifest_json),
                "--campaign-id",
                args.campaign_id,
                "--run-day",
                args.run_day,
            ]
        )
        # Rebuild manifest once more to sync "present" flags after generation.
        run_cmd(
            [
                "python",
                "scripts/lab_build_llm_run_manifest.py",
                "--campaign-id",
                args.campaign_id,
                "--bundle",
                to_repo_rel(bundle_path),
                "--input-mode",
                "full_section_v2",
                "--lenses",
                args.lenses,
                "--source-id",
                args.source_id,
                "--out-md",
                to_repo_rel(manifest_md),
                "--out-json",
                to_repo_rel(manifest_json),
                "--skip-run-pack",
            ]
        )

    validate_cmd = [
        "python",
        "scripts/lab_validate_llm_manifest_outputs.py",
        "--manifest",
        to_repo_rel(manifest_json),
        "--campaign-id",
        args.campaign_id,
        "--report",
        to_repo_rel(validation_report),
    ]
    if args.allow_missing:
        validate_cmd.append("--allow-missing")
    if args.allow_invalid:
        validate_cmd.append("--allow-invalid")
    run_cmd(validate_cmd)

    run_cmd(["python", "scripts/lab_build_llm_campaigns_index.py"])
    run_cmd(["python", "scripts/lab_build_method_tracks_index.py"])
    run_cmd(["python", "scripts/lab_build_llm_variants_index.py"])
    matrix_cmd = [
        "python",
        "scripts/lab_validate_llm_manifest_outputs.py",
        "--manifest",
        to_repo_rel(manifest_json),
        "--matrix-report",
        "reports/lab_llm_campaign_matrix_validation.md",
    ]
    if args.allow_missing:
        matrix_cmd.append("--allow-missing")
    if args.allow_invalid:
        matrix_cmd.append("--allow-invalid")
    run_cmd(matrix_cmd)

    print(f"Script: {SCRIPT_VERSION}")
    print(f"Campaign id: {args.campaign_id}")
    print(f"Bundle: {to_repo_rel(bundle_path)}")
    print(f"Manifest json: {to_repo_rel(manifest_json)}")
    print(f"Validation report: {to_repo_rel(validation_report)}")
    print("Pipeline completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
