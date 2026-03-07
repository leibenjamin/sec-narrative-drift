from __future__ import annotations

import argparse
import shlex
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class PipelinePaths:
    manifest_md: Path
    manifest_json: Path
    validation_report: Path
    quality_report: Path
    progress_report_md: Path
    progress_history_json: Path


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


def campaign_slug_token(campaign_id: str) -> str:
    if "chatgpt52ext" in campaign_id:
        return "chatgpt_real"
    if "gpt53codex_xhigh" in campaign_id:
        return "codex_real"
    sanitized = "".join(ch if ch.isalnum() else "_" for ch in campaign_id.lower())
    return sanitized.strip("_") or "campaign"


def artifact_slug_token(master_artifact_id: str) -> str:
    if master_artifact_id == "llm_outline_compare_insight":
        return "insight"
    return "structured"


def default_master_paths(campaign_id: str, master_artifact_id: str) -> PipelinePaths:
    campaign_token = campaign_slug_token(campaign_id)
    artifact_token = artifact_slug_token(master_artifact_id)

    manifest_base = f"lab_llm_master_manifest_{campaign_token}"
    validation_base = f"lab_llm_master_validation_{campaign_token}"
    quality_base = f"lab_llm_master_quality_{campaign_token}_{artifact_token}"

    if artifact_token == "insight":
        manifest_base = f"{manifest_base}_insight"
        validation_base = f"{validation_base}_insight"

    return PipelinePaths(
        manifest_md=REPO_ROOT / "reports" / f"{manifest_base}.md",
        manifest_json=REPO_ROOT / "reports" / f"{manifest_base}.json",
        validation_report=REPO_ROOT / "reports" / f"{validation_base}.md",
        quality_report=REPO_ROOT / "reports" / f"{quality_base}.md",
        progress_report_md=REPO_ROOT / "reports" / f"lab_llm_master_batch_progress_{campaign_token}.md",
        progress_history_json=REPO_ROOT / "reports" / f"lab_llm_master_batch_progress_{campaign_token}.json",
    )


def default_legacy_paths(campaign_id: str) -> tuple[Path, Path, Path]:
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


def resolve_path(path_arg: str, default_path: Path) -> Path:
    path = Path(path_arg) if path_arg else default_path
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    return path


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
        "--master-artifact-id",
        choices=("llm_outline_compare_structured", "llm_outline_compare_insight"),
        default="llm_outline_compare_structured",
        help="Primary master artifact id for canonical pipeline mode.",
    )
    parser.add_argument(
        "--manifest-md",
        default="",
        help="Manifest markdown output path (defaults by campaign/artifact).",
    )
    parser.add_argument(
        "--manifest-json",
        default="",
        help="Manifest JSON output path (defaults by campaign/artifact).",
    )
    parser.add_argument(
        "--validation-report",
        default="",
        help="Validator report output path (defaults by campaign/artifact).",
    )
    parser.add_argument(
        "--quality-report",
        default="",
        help="Quality report output path (defaults by campaign/artifact).",
    )
    parser.add_argument(
        "--progress-report-md",
        default="",
        help="Batch progress markdown output path (defaults by campaign).",
    )
    parser.add_argument(
        "--progress-history-json",
        default="",
        help="Batch progress history output path (defaults by campaign).",
    )
    parser.add_argument(
        "--skip-generate",
        action="store_true",
        help="Skip output generation step (required for canonical master-manifest mode).",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Pass through allow-missing to validators/auditors.",
    )
    parser.add_argument(
        "--allow-invalid",
        action="store_true",
        help="Pass through allow-invalid to validators.",
    )
    parser.add_argument(
        "--no-clean-publish",
        action="store_true",
        help="Preserve existing public llm_inputs_v2 files during publish sync.",
    )
    parser.add_argument(
        "--legacy-detector-manifest",
        action="store_true",
        help="Run legacy detector-manifest build/validation flow instead of canonical master-manifest flow.",
    )
    return parser


def build_or_resolve_bundle(bundle_arg: str) -> Path:
    if bundle_arg:
        bundle_path = Path(bundle_arg)
        if not bundle_path.is_absolute():
            bundle_path = (REPO_ROOT / bundle_path).resolve()
        return bundle_path

    bundle_path = REPO_ROOT / "bundles" / f"showcase_llm_inputs_full_section_v2_{utc_stamp()}"
    run_cmd(
        [
            "python",
            "scripts/build_showcase_llm_inputs_bundle.py",
            "--out_dir",
            to_repo_rel(bundle_path),
        ]
    )
    return bundle_path


def publish_bundle(bundle_path: Path, no_clean_publish: bool) -> None:
    publish_cmd = [
        "python",
        "scripts/lab_publish_llm_inputs_v2.py",
        "--bundle",
        to_repo_rel(bundle_path),
    ]
    if no_clean_publish:
        publish_cmd.append("--no-clean")
    run_cmd(publish_cmd)


def run_legacy_pipeline(
    *,
    campaign_id: str,
    bundle_path: Path,
    manifest_md: Path,
    manifest_json: Path,
    validation_report: Path,
    lenses: str,
    source_id: str,
    run_day: str,
    skip_generate: bool,
    allow_missing: bool,
    allow_invalid: bool,
) -> None:
    run_cmd(
        [
            "python",
            "scripts/lab_build_llm_run_manifest.py",
            "--campaign-id",
            campaign_id,
            "--bundle",
            to_repo_rel(bundle_path),
            "--input-mode",
            "full_section_v2",
            "--lenses",
            lenses,
            "--source-id",
            source_id,
            "--out-md",
            to_repo_rel(manifest_md),
            "--out-json",
            to_repo_rel(manifest_json),
        ]
    )

    if not skip_generate:
        run_cmd(
            [
                "python",
                "scripts/lab_generate_codex_campaign_outputs.py",
                "--manifest",
                to_repo_rel(manifest_json),
                "--campaign-id",
                campaign_id,
                "--run-day",
                run_day,
            ]
        )
        run_cmd(
            [
                "python",
                "scripts/lab_build_llm_run_manifest.py",
                "--campaign-id",
                campaign_id,
                "--bundle",
                to_repo_rel(bundle_path),
                "--input-mode",
                "full_section_v2",
                "--lenses",
                lenses,
                "--source-id",
                source_id,
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
        campaign_id,
        "--report",
        to_repo_rel(validation_report),
    ]
    if allow_missing:
        validate_cmd.append("--allow-missing")
    if allow_invalid:
        validate_cmd.append("--allow-invalid")
    run_cmd(validate_cmd)

    matrix_cmd = [
        "python",
        "scripts/lab_validate_llm_manifest_outputs.py",
        "--manifest",
        to_repo_rel(manifest_json),
        "--matrix-report",
        "reports/lab_llm_campaign_matrix_validation.md",
    ]
    if allow_missing:
        matrix_cmd.append("--allow-missing")
    if allow_invalid:
        matrix_cmd.append("--allow-invalid")
    run_cmd(matrix_cmd)


def run_master_pipeline(
    *,
    campaign_id: str,
    master_artifact_id: str,
    bundle_path: Path,
    manifest_md: Path,
    manifest_json: Path,
    validation_report: Path,
    quality_report: Path,
    progress_report_md: Path,
    progress_history_json: Path,
    lenses: str,
    source_id: str,
    skip_generate: bool,
    allow_missing: bool,
    allow_invalid: bool,
) -> None:
    run_cmd(
        [
            "python",
            "scripts/lab_build_llm_master_manifest.py",
            "--campaign-id",
            campaign_id,
            "--master-artifact-id",
            master_artifact_id,
            "--bundle",
            to_repo_rel(bundle_path),
            "--lenses",
            lenses,
            "--source-id",
            source_id,
            "--out-md",
            to_repo_rel(manifest_md),
            "--out-json",
            to_repo_rel(manifest_json),
        ]
    )

    if not skip_generate:
        raise SystemExit(
            "Canonical master-manifest mode does not support auto generation. "
            "Run manual LLM jobs from generated starters, or use --legacy-detector-manifest."
        )

    validate_cmd = [
        "python",
        "scripts/lab_validate_llm_master_outputs.py",
        "--manifest",
        to_repo_rel(manifest_json),
        "--campaign-id",
        campaign_id,
        "--artifact-id",
        master_artifact_id,
        "--target-field",
        "master_output",
        "--report",
        to_repo_rel(validation_report),
    ]
    if allow_missing:
        validate_cmd.append("--allow-missing")
    if allow_invalid:
        validate_cmd.append("--allow-invalid")
    run_cmd(validate_cmd)

    quality_cmd = [
        "python",
        "scripts/lab_audit_master_output_quality.py",
        "--manifest",
        to_repo_rel(manifest_json),
        "--campaign-id",
        campaign_id,
        "--artifact-id",
        master_artifact_id,
        "--target-field",
        "master_output",
        "--mode",
        "blockers",
        "--strict-depth",
        "--report",
        to_repo_rel(quality_report),
    ]
    if allow_missing:
        quality_cmd.append("--allow-missing")
    run_cmd(quality_cmd)

    run_cmd(
        [
            "python",
            "scripts/lab_record_master_progress.py",
            "--manifest",
            to_repo_rel(manifest_json),
            "--campaign-id",
            campaign_id,
            "--report-md",
            to_repo_rel(progress_report_md),
            "--history-json",
            to_repo_rel(progress_history_json),
            "--label",
            "pipeline",
        ]
    )


def run_indexes_and_readiness() -> None:
    run_cmd(["python", "scripts/lab_build_llm_campaigns_index.py"])
    run_cmd(["python", "scripts/lab_build_method_tracks_index.py"])
    run_cmd(["python", "scripts/lab_build_llm_variants_index.py"])
    run_cmd(["python", "scripts/lab_runtime_readiness_check.py"])


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.legacy_detector_manifest:
        legacy_md, legacy_json, legacy_validation = default_legacy_paths(args.campaign_id)
        paths = PipelinePaths(
            manifest_md=resolve_path(str(args.manifest_md), legacy_md),
            manifest_json=resolve_path(str(args.manifest_json), legacy_json),
            validation_report=resolve_path(str(args.validation_report), legacy_validation),
            quality_report=Path(),
            progress_report_md=Path(),
            progress_history_json=Path(),
        )
    else:
        master_defaults = default_master_paths(
            campaign_id=args.campaign_id,
            master_artifact_id=str(args.master_artifact_id),
        )
        paths = PipelinePaths(
            manifest_md=resolve_path(str(args.manifest_md), master_defaults.manifest_md),
            manifest_json=resolve_path(str(args.manifest_json), master_defaults.manifest_json),
            validation_report=resolve_path(
                str(args.validation_report),
                master_defaults.validation_report,
            ),
            quality_report=resolve_path(str(args.quality_report), master_defaults.quality_report),
            progress_report_md=resolve_path(
                str(args.progress_report_md),
                master_defaults.progress_report_md,
            ),
            progress_history_json=resolve_path(
                str(args.progress_history_json),
                master_defaults.progress_history_json,
            ),
        )

    bundle_path = build_or_resolve_bundle(str(args.bundle))
    if not bundle_path.exists():
        raise SystemExit(f"Bundle not found: {bundle_path}")

    publish_bundle(bundle_path=bundle_path, no_clean_publish=bool(args.no_clean_publish))

    if args.legacy_detector_manifest:
        run_legacy_pipeline(
            campaign_id=args.campaign_id,
            bundle_path=bundle_path,
            manifest_md=paths.manifest_md,
            manifest_json=paths.manifest_json,
            validation_report=paths.validation_report,
            lenses=args.lenses,
            source_id=args.source_id,
            run_day=args.run_day,
            skip_generate=bool(args.skip_generate),
            allow_missing=bool(args.allow_missing),
            allow_invalid=bool(args.allow_invalid),
        )
    else:
        run_master_pipeline(
            campaign_id=args.campaign_id,
            master_artifact_id=str(args.master_artifact_id),
            bundle_path=bundle_path,
            manifest_md=paths.manifest_md,
            manifest_json=paths.manifest_json,
            validation_report=paths.validation_report,
            quality_report=paths.quality_report,
            progress_report_md=paths.progress_report_md,
            progress_history_json=paths.progress_history_json,
            lenses=args.lenses,
            source_id=args.source_id,
            skip_generate=bool(args.skip_generate),
            allow_missing=bool(args.allow_missing),
            allow_invalid=bool(args.allow_invalid),
        )

    run_indexes_and_readiness()

    mode = "legacy_detector_manifest" if args.legacy_detector_manifest else "master_manifest"
    print(f"Script: {SCRIPT_VERSION}")
    print(f"Pipeline mode: {mode}")
    print(f"Campaign id: {args.campaign_id}")
    print(f"Bundle: {to_repo_rel(bundle_path)}")
    print(f"Manifest json: {to_repo_rel(paths.manifest_json)}")
    print(f"Validation report: {to_repo_rel(paths.validation_report)}")
    if not args.legacy_detector_manifest:
        print(f"Quality report: {to_repo_rel(paths.quality_report)}")
        print(f"Progress report: {to_repo_rel(paths.progress_report_md)}")
        print(f"Progress history: {to_repo_rel(paths.progress_history_json)}")
    print("Pipeline completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
