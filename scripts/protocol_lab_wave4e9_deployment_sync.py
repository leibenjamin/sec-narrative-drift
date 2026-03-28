from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

TASK_NAME = "Wave 4E9 = Deployment Sync + Mounted-Path Acceptance Pass"
PACKET_PREFIX = "wave4e9_deployment_sync_acceptance"
PACKET_README_NAME = "PACKET_README.md"
CHANGED_FILES_MANIFEST_NAME = "changed_files_manifest.md"
LIVE_VERIFIER_OUTPUT_NAME = "live_verifier_output_example.txt"
DIST_INDEX_EXCERPT_NAME = "dist_index_excerpt.md"
METADATA_EXCERPT_NAME = "metadata_excerpt.md"
SLASH_PREVIEW_NAME = "slash_normalization_evidence_preview.md"
DEFAULT_MOUNTED_BASE = "https://benlei.org/sec-narrative-drift"
DEFAULT_EXPECTED_BASE_PATH = "/sec-narrative-drift/"

BIGGEST_REMAINING_BLOCKER = (
    "External deployment truth remains the blocker: the mounted public path is still "
    "serving stale HTML and still needs the mounted-base build plus the external slash "
    "redirect applied live."
)

REPORT_PATHS = [
    Path("reports/protocol_lab/wave4e9_deployment_truth_audit.md"),
    Path("reports/protocol_lab/wave4e9_deploy_mount_runbook.md"),
    Path("reports/protocol_lab/wave4e9_live_acceptance_checklist.md"),
    Path("reports/protocol_lab/wave4e9_deployment_sync_report.md"),
    Path("reports/protocol_lab/wave4e9_mount_normalization_decision.md"),
]

SOURCE_PATHS = [
    Path("public/_redirects"),
    Path("scripts/lab_verify_social_preview_deploy.py"),
    Path("scripts/tests/test_lab_verify_social_preview_deploy.py"),
    Path("scripts/protocol_lab_wave4e9_deployment_sync.py"),
    Path("scripts/tests/test_protocol_lab_wave4e9_deployment_sync.py"),
]

SUPPORT_PATHS = [
    Path("README.md"),
]


@dataclass
class GenerationSummary:
    packet_dir: Path
    zip_path: Path
    changed_repo_paths: list[str]
    packet_support_paths: list[str]
    repo_build_verification_tightened: bool
    mounted_path_acceptance_checks_added: bool
    worker_slash_normalization_improved: bool
    biggest_remaining_blocker: str
    console_summary_lines: list[str]


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M")


def packet_paths_for_stamp(stamp: str) -> tuple[Path, Path]:
    packet_dir = REPO_ROOT / f"{PACKET_PREFIX}_{stamp}"
    zip_path = REPO_ROOT / f"{PACKET_PREFIX}_{stamp}.zip"
    return packet_dir, zip_path


def ensure_clean_output(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    ordered: list[Path] = []
    for path in paths:
        key = path.as_posix()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(path)
    return ordered


def require_repo_file(path: Path) -> None:
    full_path = REPO_ROOT / path
    if not full_path.is_file():
        raise FileNotFoundError(f"Missing required packet file: {path.as_posix()}")


def copy_repo_paths_into_packet(packet_dir: Path, repo_paths: list[Path]) -> None:
    for repo_path in repo_paths:
        require_repo_file(repo_path)
        source_path = REPO_ROOT / repo_path
        destination_path = packet_dir / repo_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)


def zip_directory(source_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(source_dir.rglob("*")):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(source_dir.parent))


def build_changed_files_manifest(paths: list[Path]) -> str:
    lines = [
        "# Changed Files Manifest",
        "",
        "Files created or modified by Wave 4E9:",
        "",
    ]
    for path in paths:
        lines.append(f"- `{path.as_posix()}`")
    return "\n".join(lines) + "\n"


def build_packet_readme(changed_paths: list[Path], support_paths: list[Path]) -> str:
    lines = [
        f"# {PACKET_PREFIX}",
        "",
        f"This packet contains the {TASK_NAME} reports, the mounted-path verifier changes, the packet generator, the redirect normalization support, and the top-level README for operator context.",
        "",
        "## Included",
        "",
        "- Wave 4E9 deployment/mount reports",
        "- tightened verifier and targeted tests",
        "- repo-side slash-normalization support via `public/_redirects`",
        "- deterministic packet evidence excerpts",
        "",
        "## Packet-Local Support Files",
        "",
    ]
    for path in support_paths:
        lines.append(f"- `{path.as_posix()}`")
    lines.extend(
        [
            "",
            "## Changed File Count",
            "",
            f"- {len(changed_paths)} modified files",
        ]
    )
    return "\n".join(lines) + "\n"


def extract_metadata_lines(source_text: str) -> list[str]:
    lines: list[str] = []
    for line in source_text.splitlines():
        stripped = line.strip()
        if (
            "<title>" in stripped
            or "favicon.svg" in stripped
            or "apple-touch-icon.png" in stripped
            or "og:" in stripped
            or "twitter:" in stripped
        ):
            lines.append(f"- `{stripped}`")
    return lines


def build_metadata_excerpt() -> str:
    source = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
    lines = ["# Metadata Excerpt", "", *extract_metadata_lines(source)]
    return "\n".join(lines) + "\n"


def build_dist_index_excerpt() -> str:
    dist_html = REPO_ROOT / "dist" / "index.html"
    if not dist_html.is_file():
        return "# Dist Index Excerpt\n\n`dist/index.html` is missing.\n"
    source = dist_html.read_text(encoding="utf-8")
    lines = [
        "# Dist Index Excerpt",
        "",
        *extract_metadata_lines(source),
    ]
    for line in source.splitlines():
        stripped = line.strip()
        if "/sec-narrative-drift/assets/" in stripped:
            lines.append(f"- `{stripped}`")
    return "\n".join(lines) + "\n"


def build_live_verifier_output(include_live_fetch: bool, mounted_base: str) -> str:
    if not include_live_fetch:
        return (
            "# Live Verifier Output Example\n\n"
            "Live fetch skipped for deterministic packet test mode.\n"
        )

    command = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "lab_verify_social_preview_deploy.py"),
        "--mounted-base",
        mounted_base,
        "--expected-base-path",
        DEFAULT_EXPECTED_BASE_PATH,
    ]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    lines = [
        "# Live Verifier Output Example",
        "",
        f"- command: `{' '.join(command[1:])}`",
        f"- exit_code: {result.returncode}",
        "",
    ]
    if result.stdout.strip():
        lines.append(result.stdout.rstrip())
    if result.stderr.strip():
        lines.extend(["", "## stderr", "", result.stderr.rstrip()])
    return "\n".join(lines) + "\n"


def build_slash_preview(verifier_output: str) -> str:
    lines = ["# Slash Normalization Evidence Preview", ""]
    keep = False
    for raw_line in verifier_output.splitlines():
        line = raw_line.rstrip()
        if line.startswith("## Mounted public path (slashless)"):
            keep = True
        if line.startswith("## Summary"):
            keep = False
        if keep and (
            line.startswith("## ")
            or line.startswith("requested_url:")
            or line.startswith("final_url:")
            or line.startswith("classification:")
            or line.startswith("classification_reasons:")
            or line.startswith("favicon_url:")
            or line.startswith("runtime_asset_paths:")
            or line.startswith("## Slash normalization")
            or line.startswith("slashless_requested_url:")
            or line.startswith("slashed_requested_url:")
            or line.startswith("slashless_redirects_to_slashed:")
            or line.startswith("slash_behavior_diverges:")
            or line.startswith("slash_divergence_details:")
        ):
            lines.append(f"- `{line}`" if not line.startswith("## ") else line)
    if len(lines) == 2:
        lines.append("No live slash-normalization output was captured.")
    return "\n".join(lines) + "\n"


def build_changed_repo_paths() -> list[Path]:
    return unique_paths([*REPORT_PATHS, *SOURCE_PATHS])


def build_packet_repo_paths(changed_paths: list[Path]) -> tuple[list[Path], list[Path]]:
    support_paths = unique_paths(SUPPORT_PATHS)
    packet_paths = unique_paths([*changed_paths, *support_paths])
    return packet_paths, support_paths


def generate_wave(
    stamp: str | None = None,
    *,
    include_live_fetch: bool = True,
    mounted_base: str = DEFAULT_MOUNTED_BASE,
) -> GenerationSummary:
    changed_repo_paths = build_changed_repo_paths()
    packet_repo_paths, support_paths = build_packet_repo_paths(changed_repo_paths)

    stamp_value = stamp or utc_stamp()
    packet_dir, zip_path = packet_paths_for_stamp(stamp_value)
    ensure_clean_output(packet_dir)
    ensure_clean_output(zip_path)
    packet_dir.mkdir(parents=True, exist_ok=True)

    copy_repo_paths_into_packet(packet_dir, packet_repo_paths)
    (packet_dir / CHANGED_FILES_MANIFEST_NAME).write_text(
        build_changed_files_manifest(changed_repo_paths),
        encoding="utf-8",
    )
    (packet_dir / PACKET_README_NAME).write_text(
        build_packet_readme(changed_repo_paths, support_paths),
        encoding="utf-8",
    )

    verifier_output = build_live_verifier_output(include_live_fetch, mounted_base)
    (packet_dir / LIVE_VERIFIER_OUTPUT_NAME).write_text(verifier_output, encoding="utf-8")
    (packet_dir / DIST_INDEX_EXCERPT_NAME).write_text(build_dist_index_excerpt(), encoding="utf-8")
    (packet_dir / METADATA_EXCERPT_NAME).write_text(build_metadata_excerpt(), encoding="utf-8")
    (packet_dir / SLASH_PREVIEW_NAME).write_text(
        build_slash_preview(verifier_output),
        encoding="utf-8",
    )
    zip_directory(packet_dir, zip_path)

    console_summary_lines = [
        f"packet folder path: {packet_dir.resolve()}",
        f"zip path: {zip_path.resolve()}",
        "whether repo/build verification was tightened: yes",
        "whether mounted-path acceptance checks were added: yes",
        "whether Worker slash-normalization was improved: no (manual-only; external Worker source unavailable in repo)",
        f"biggest remaining blocker after this wave: {BIGGEST_REMAINING_BLOCKER}",
    ]
    for line in console_summary_lines:
        print(line)

    return GenerationSummary(
        packet_dir=packet_dir,
        zip_path=zip_path,
        changed_repo_paths=[path.as_posix() for path in changed_repo_paths],
        packet_support_paths=[path.as_posix() for path in support_paths],
        repo_build_verification_tightened=True,
        mounted_path_acceptance_checks_added=True,
        worker_slash_normalization_improved=False,
        biggest_remaining_blocker=BIGGEST_REMAINING_BLOCKER,
        console_summary_lines=console_summary_lines,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--stamp", default="", help="Optional fixed packet stamp (YYYYMMDD_HHMM).")
    parser.add_argument(
        "--skip-live-fetch",
        action="store_true",
        help="Skip the live verifier example and write a deterministic placeholder instead.",
    )
    parser.add_argument(
        "--mounted-base",
        default=DEFAULT_MOUNTED_BASE,
        help="Mounted base URL to use for the live verifier example.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    generate_wave(
        stamp=args.stamp or None,
        include_live_fetch=not args.skip_live_fetch,
        mounted_base=args.mounted_base,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
