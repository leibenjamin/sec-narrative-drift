from __future__ import annotations

import argparse
import shutil
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

TASK_NAME = "Wave 4E8.5 = Social Preview + Deploy Acceptance Pass"
PACKET_PREFIX = "wave4e85_social_preview_deploy"
PACKET_README_NAME = "PACKET_README.md"
CHANGED_FILES_MANIFEST_NAME = "changed_files_manifest.md"
RENDER_PREVIEW_NAME = "render_preview.md"

BIGGEST_REMAINING_BLOCKER = (
    "Need to confirm that the Cloudflare-mounted https://benlei.org/sec-narrative-drift/ "
    "path serves crawler-friendly app HTML without a challenge; repo-side social metadata "
    "alone will not matter if the mount still interposes a challenge."
)

REPORT_PATHS = [
    Path("reports/protocol_lab/wave4e85_social_preview_audit.md"),
    Path("reports/protocol_lab/wave4e85_deploy_acceptance_checklist.md"),
    Path("reports/protocol_lab/wave4e85_demo_kit.md"),
    Path("reports/protocol_lab/wave4e85_share_deploy_report.md"),
    Path("reports/protocol_lab/wave4e85_public_asset_decisions.md"),
]

SOURCE_PATHS = [
    Path("src/pages/Home.tsx"),
    Path("src/lib/protocolLabProductPositioning.ts"),
]

ARTIFACT_PATHS = [
    Path("public/data/business_document_protocol_lab/product_positioning/demo_share_v3.json"),
]

ASSET_PATHS = [
    Path("public/favicon.svg"),
    Path("public/apple-touch-icon.png"),
    Path("public/social/sec-narrative-drift-lab-share-1200x630.png"),
    Path("public/social/sec-narrative-drift-lab-icon-512.png"),
]

ROOT_PATHS = [
    Path("README.md"),
    Path("index.html"),
]

SCRIPT_PATH = Path("scripts/protocol_lab_wave4e85_social_preview_deploy.py")
VERIFIER_PATH = Path("scripts/lab_verify_social_preview_deploy.py")
ASSET_GENERATOR_PATH = Path("scripts/lab_generate_social_preview_assets.py")
NODE_TEST_PATH = Path("scripts/tests/test_protocol_lab_product_positioning_data.mjs")
VERIFIER_TEST_PATH = Path("scripts/tests/test_lab_verify_social_preview_deploy.py")
PYTHON_TEST_PATH = Path("scripts/tests/test_protocol_lab_wave4e85_social_preview_deploy.py")

QA_PATHS = [
    SCRIPT_PATH,
    VERIFIER_PATH,
    ASSET_GENERATOR_PATH,
    NODE_TEST_PATH,
    VERIFIER_TEST_PATH,
    PYTHON_TEST_PATH,
]

NODE_TEST_SUPPORT_PATHS = [
    Path("src/App.tsx"),
    Path("src/pages/Companies.tsx"),
    Path("src/pages/Company.tsx"),
    Path("src/components/LabPanel.tsx"),
    Path("src/components/PageMetadata.tsx"),
    Path("src/components/ProtocolLabUseCaseGuide.tsx"),
    Path("src/components/ProtocolLabPilotMatrixPanel.tsx"),
    Path("public/data/business_document_protocol_lab/product_positioning/current_case_mix_v2.json"),
    Path("public/data/business_document_protocol_lab/product_positioning/start_here_v1.json"),
    Path("public/data/sec_narrative_drift_lab/lab_cases_v1.json"),
    Path("public/data/business_document_protocol_lab/pilot_matrices/NVDA_2024_2025_10k_item1a/pilot_matrix_v1.json"),
    Path("public/data/business_document_protocol_lab/pilot_matrices/LLY_2024_2025_10k_item1a/pilot_matrix_v1.json"),
    Path("public/data/business_document_protocol_lab/pilot_matrices/KO_2024_2025_10k_item1a/pilot_matrix_v1.json"),
    Path("public/data/business_document_protocol_lab/pilot_matrices/NVDA_2024_2025_10k_item1a/pilot_matrix_story_v1.json"),
    Path("public/data/business_document_protocol_lab/pilot_matrices/LLY_2024_2025_10k_item1a/pilot_matrix_story_v1.json"),
    Path("public/data/business_document_protocol_lab/pilot_matrices/KO_2024_2025_10k_item1a/pilot_matrix_story_v1.json"),
    Path("public/data/business_document_protocol_lab/pilot_matrices/NVDA_2024_2025_10k_item1a/pilot_matrix_review_v1.json"),
    Path("public/data/business_document_protocol_lab/pilot_matrices/LLY_2024_2025_10k_item1a/pilot_matrix_review_v1.json"),
    Path("public/data/business_document_protocol_lab/pilot_matrices/KO_2024_2025_10k_item1a/pilot_matrix_review_v1.json"),
    Path("public/data/business_document_protocol_lab/pilot_matrices/NVDA_2024_2025_10k_item1a/cells/02_p1_i2_tagged_packet__pilot_matrix_cell_v1.json"),
    Path("public/data/business_document_protocol_lab/pilot_matrices/LLY_2024_2025_10k_item1a/cells/02_p1_i2_tagged_packet__pilot_matrix_cell_v1.json"),
    Path("public/data/business_document_protocol_lab/pilot_matrices/KO_2024_2025_10k_item1a/cells/02_p1_i2_tagged_packet__pilot_matrix_cell_v1.json"),
    Path("public/data/business_document_protocol_lab/novelty_ledger/NVDA_2024_2025_10k_item1a/p4_canonized_matrix_v1.json"),
    Path("public/data/business_document_protocol_lab/novelty_ledger/LLY_2024_2025_10k_item1a/p4_canonized_matrix_v1.json"),
    Path("public/data/business_document_protocol_lab/novelty_ledger/KO_2024_2025_10k_item1a/p4_canonized_matrix_v1.json"),
]

TEST_DEPENDENCY_MAP = {
    NODE_TEST_PATH: NODE_TEST_SUPPORT_PATHS,
    VERIFIER_TEST_PATH: [VERIFIER_PATH],
    PYTHON_TEST_PATH: [SCRIPT_PATH],
}


@dataclass
class GenerationSummary:
    packet_dir: Path
    zip_path: Path
    changed_repo_paths: list[str]
    packet_support_paths: list[str]
    demo_share_v3_created: bool
    og_twitter_static_tags_added: bool
    real_share_image_created: bool
    default_favicon_replaced: bool
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
    file_path = REPO_ROOT / path
    if not file_path.is_file():
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
        "Files created or modified by Wave 4E8.5:",
        "",
    ]
    for path in paths:
        lines.append(f"- `{path.as_posix()}`")
    return "\n".join(lines) + "\n"


def build_packet_readme(changed_paths: list[Path], support_paths: list[Path]) -> str:
    lines = [
        f"# {PACKET_PREFIX}",
        "",
        f"This packet contains the {TASK_NAME} reports, static share assets, targeted QA, the social-preview deploy verifier, and the updated top-level README and HTML metadata.",
        "",
        "## Included",
        "",
        "- Wave 4E8.5 reports and review materials",
        "- static OG/Twitter metadata changes in `index.html`",
        "- `demo_share_v3.json` and production-facing share assets",
        "- targeted QA for share metadata, asset existence, deploy verification, and packet generation",
        "- a text-only render preview and changed-file manifest",
        "",
        "## Packet-Local Replay Support",
        "",
        "Direct dependencies needed for packet-local replay of the targeted QA are included alongside the changed files.",
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


def build_metadata_excerpt() -> str:
    source = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
    excerpt_lines: list[str] = []
    for line in source.splitlines():
        stripped = line.strip()
        if (
            "og:" in stripped
            or "twitter:" in stripped
            or "favicon.svg" in stripped
            or "apple-touch-icon.png" in stripped
        ):
            excerpt_lines.append(f"- `{stripped}`")
    return "\n".join(excerpt_lines)


def build_render_preview() -> str:
    lines = [
        "# Render Preview",
        "",
        "## Browser Tab / Favicon",
        "",
        "- `index.html` now points at `./favicon.svg` and `./apple-touch-icon.png` instead of `/vite.svg`.",
        "- The icon system stays compact and comparison-toned rather than decorative.",
        "",
        "## Home Preview",
        "",
        "- Static share metadata targets the top-level three-case home surface only.",
        "- Home copy still leads with NVDA, LLY, and KO as the compact selected set.",
        "",
        "## Share Asset Preview",
        "",
        "- Primary card: `public/social/sec-narrative-drift-lab-share-1200x630.png`",
        "- Square icon: `public/social/sec-narrative-drift-lab-icon-512.png`",
        "- Share card reflects `SEC Narrative Drift Lab`, the three selected cases, and the compare-first workflow.",
        "",
        "## Metadata Excerpt",
        "",
        build_metadata_excerpt(),
        "",
        "## Cloudflare Note",
        "",
        "- The repo/build layer now carries the right static metadata.",
        "- Actual external preview readiness still depends on the mounted public path serving app HTML instead of a Cloudflare challenge.",
    ]
    return "\n".join(lines) + "\n"


def build_changed_repo_paths() -> list[Path]:
    return unique_paths(
        [
            *REPORT_PATHS,
            *SOURCE_PATHS,
            *ARTIFACT_PATHS,
            *ASSET_PATHS,
            *ROOT_PATHS,
            *QA_PATHS,
        ]
    )


def build_packet_repo_paths(changed_paths: list[Path]) -> tuple[list[Path], list[Path]]:
    support_paths = unique_paths(
        [path for dependency_paths in TEST_DEPENDENCY_MAP.values() for path in dependency_paths]
    )
    packet_paths = unique_paths([*changed_paths, *support_paths])
    return packet_paths, support_paths


def generate_wave(stamp: str | None = None) -> GenerationSummary:
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
    (packet_dir / RENDER_PREVIEW_NAME).write_text(build_render_preview(), encoding="utf-8")
    zip_directory(packet_dir, zip_path)

    console_summary_lines = [
        f"packet folder path: {packet_dir.resolve()}",
        f"zip path: {zip_path.resolve()}",
        "whether demo_share_v3.json was created: yes",
        "whether OG/Twitter static tags were added: yes",
        "whether a real share image was created: yes",
        "whether the default favicon was replaced: yes",
        f"biggest remaining blocker after this wave: {BIGGEST_REMAINING_BLOCKER}",
    ]
    for line in console_summary_lines:
        print(line)

    return GenerationSummary(
        packet_dir=packet_dir,
        zip_path=zip_path,
        changed_repo_paths=[path.as_posix() for path in changed_repo_paths],
        packet_support_paths=[path.as_posix() for path in support_paths],
        demo_share_v3_created=True,
        og_twitter_static_tags_added=True,
        real_share_image_created=True,
        default_favicon_replaced=True,
        biggest_remaining_blocker=BIGGEST_REMAINING_BLOCKER,
        console_summary_lines=console_summary_lines,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--stamp", default="", help="Optional fixed packet stamp (YYYYMMDD_HHMM).")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    generate_wave(stamp=args.stamp or None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
