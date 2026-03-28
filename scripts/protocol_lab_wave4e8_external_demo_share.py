from __future__ import annotations

import argparse
import shutil
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

TASK_NAME = "Wave 4E8 = External Demo/Share Pass + Public Metadata Hygiene"
PACKET_PREFIX = "wave4e8_external_demo_share"
PACKET_README_NAME = "PACKET_README.md"
CHANGED_FILES_MANIFEST_NAME = "changed_files_manifest.md"
RENDER_PREVIEW_NAME = "render_preview.md"

BIGGEST_REMAINING_BLOCKER = "LLY still lacks a true lower-runtime/lower-audit case."

REPORT_PATHS = [
    Path("reports/protocol_lab/wave4e8_public_surface_language_audit.md"),
    Path("reports/protocol_lab/wave4e8_external_demo_readiness.md"),
    Path("reports/protocol_lab/wave4e8_share_pass_report.md"),
    Path("reports/protocol_lab/wave4e8_public_wording_decisions.md"),
]

VISIBLE_SURFACE_PATHS = [
    Path("src/pages/Home.tsx"),
    Path("src/pages/Companies.tsx"),
    Path("src/pages/Company.tsx"),
    Path("src/components/LabPanel.tsx"),
    Path("src/components/ProtocolLabPilotMatrixPanel.tsx"),
]

HELPER_PATHS = [
    Path("src/components/PageMetadata.tsx"),
    Path("src/lib/protocolLabProductPositioning.ts"),
]

ARTIFACT_PATHS = [
    Path("public/data/business_document_protocol_lab/product_positioning/current_case_mix_v2.json"),
    Path("public/data/business_document_protocol_lab/product_positioning/start_here_v1.json"),
    Path("public/data/business_document_protocol_lab/product_positioning/demo_share_v2.json"),
]

ROOT_PATHS = [
    Path("README.md"),
    Path("index.html"),
]

SCRIPT_PATH = Path("scripts/protocol_lab_wave4e8_external_demo_share.py")
NODE_TEST_PATH = Path("scripts/tests/test_protocol_lab_product_positioning_data.mjs")
PYTHON_TEST_PATH = Path("scripts/tests/test_protocol_lab_wave4e8_external_demo_share.py")

QA_PATHS = [
    NODE_TEST_PATH,
    SCRIPT_PATH,
    PYTHON_TEST_PATH,
]

NODE_TEST_SUPPORT_PATHS = [
    Path("src/App.tsx"),
    Path("src/components/ProtocolLabUseCaseGuide.tsx"),
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
    PYTHON_TEST_PATH: [
        SCRIPT_PATH,
    ],
}


@dataclass
class GenerationSummary:
    packet_dir: Path
    zip_path: Path
    changed_repo_paths: list[str]
    packet_support_paths: list[str]
    visible_surface_paths: list[str]
    demo_share_v2_created: bool
    readme_top_section_updated: bool
    public_metadata_improved: bool
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
        "Files created or modified by Wave 4E8:",
        "",
    ]
    for path in paths:
        lines.append(f"- `{path.as_posix()}`")
    return "\n".join(lines) + "\n"


def build_packet_readme(changed_paths: list[Path], support_paths: list[Path]) -> str:
    lines = [
        f"# {PACKET_PREFIX}",
        "",
        f"This packet contains the {TASK_NAME} reports, public-surface source updates, metadata/share artifacts, targeted QA, the updated top-level README, and a deterministic render preview.",
        "",
        "## Included",
        "",
        "- updated Wave 4E8 reports",
        "- modified Home, Companies, Company, and case-comparison source files",
        "- lightweight page-metadata helper and product-positioning loader updates",
        "- updated product-positioning artifacts including `demo_share_v2.json`",
        "- updated root `README.md` and `index.html` baseline metadata",
        "- targeted QA plus deterministic render preview and changed-file manifest",
        "",
        "## Visible Surfaces Modified",
        "",
    ]
    for path in VISIBLE_SURFACE_PATHS:
        lines.append(f"- `{path.as_posix()}`")

    lines.extend(
        [
            "",
            "## Packet-Local Replay Support",
            "",
            "Direct dependencies needed for packet-local replay of the targeted QA are included alongside the changed files.",
            "",
        ]
    )
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


def build_render_preview() -> str:
    lines = [
        "# Render Preview",
        "",
        "## Home",
        "",
        "- The chip row now leads with `Primary read first` and `Fresh vs reused` instead of lane codes.",
        "- Home metadata now uses a real title and the `demo_share_v2` meta-description candidate.",
        "- Error states now describe missing case guidance and case lists in public language.",
        "",
        "## Companies",
        "",
        "- The case chooser now uses the same public wording as Home for read order and start guidance.",
        "- Company-selection copy remains compact and three-case only.",
        "",
        "## Company / LLY",
        "",
        "- Read labels now use `Primary read`, `Comparison read`, and `Control read` instead of protocol codes.",
        "- The entry framing keeps the bounded `LLY` truth without pilot/protocol shorthand.",
        "- Case-comparison labels now read as public-facing read names rather than lane ids.",
        "",
        "## README Top Section",
        "",
        "- The first screen now leads with the exact three-case README blurb from `demo_share_v2`.",
        "- The next paragraph explains why `NVDA`, `LLY`, and `KO` exist together without broader-catalog framing.",
    ]
    return "\n".join(lines) + "\n"


def build_changed_repo_paths() -> list[Path]:
    return unique_paths(
        [
            *REPORT_PATHS,
            *VISIBLE_SURFACE_PATHS,
            *HELPER_PATHS,
            *ARTIFACT_PATHS,
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
        "which visible surfaces were modified:",
        "- Home",
        "- Companies",
        "- Company entry",
        "- Case comparison labels",
        "whether demo_share_v2.json was created: yes",
        "whether README top section was updated: yes",
        "whether lightweight public metadata was improved: yes",
        f"biggest remaining blocker after this wave: {BIGGEST_REMAINING_BLOCKER}",
    ]
    for line in console_summary_lines:
        print(line)

    return GenerationSummary(
        packet_dir=packet_dir,
        zip_path=zip_path,
        changed_repo_paths=[path.as_posix() for path in changed_repo_paths],
        packet_support_paths=[path.as_posix() for path in support_paths],
        visible_surface_paths=[path.as_posix() for path in VISIBLE_SURFACE_PATHS],
        demo_share_v2_created=True,
        readme_top_section_updated=True,
        public_metadata_improved=True,
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
