from __future__ import annotations

import argparse
import shutil
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

TASK_NAME = "Wave 4E7.5 = First-Run QA + Demo-Readiness Pass"
PACKET_PREFIX = "wave4e75_first_run_demo_readiness"
ROOT_README_NAME = "README.md"
CHANGED_FILES_MANIFEST_NAME = "changed_files_manifest.md"
RENDER_PREVIEW_NAME = "render_preview.md"

BIGGEST_REMAINING_BLOCKER = "LLY still lacks a true lower-runtime/lower-audit case."

REPORT_PATHS = [
    Path("reports/protocol_lab/wave4e75_first_run_ux_audit.md"),
    Path("reports/protocol_lab/wave4e75_narrow_width_review.md"),
    Path("reports/protocol_lab/wave4e75_demo_readiness_report.md"),
    Path("reports/protocol_lab/wave4e75_first_run_copy_decisions.md"),
]

VISIBLE_SURFACE_PATHS = [
    Path("src/pages/Home.tsx"),
    Path("src/pages/Companies.tsx"),
    Path("src/pages/Company.tsx"),
    Path("src/components/LabPanel.tsx"),
]

HELPER_PATHS = [
    Path("src/components/ProtocolLabUseCaseGuide.tsx"),
]

ARTIFACT_PATHS = [
    Path("public/data/business_document_protocol_lab/product_positioning/current_case_mix_v2.json"),
    Path("public/data/business_document_protocol_lab/product_positioning/start_here_v1.json"),
    Path("public/data/business_document_protocol_lab/product_positioning/demo_share_v1.json"),
]

SCRIPT_PATH = Path("scripts/protocol_lab_wave4e75_first_run_demo_readiness.py")
NODE_TEST_PATH = Path("scripts/tests/test_protocol_lab_product_positioning_data.mjs")
PYTHON_TEST_PATH = Path("scripts/tests/test_protocol_lab_wave4e75_first_run_demo_readiness.py")

QA_PATHS = [
    NODE_TEST_PATH,
    SCRIPT_PATH,
    PYTHON_TEST_PATH,
]

NODE_TEST_SUPPORT_PATHS = [
    Path("src/App.tsx"),
    Path("src/lib/protocolLabProductPositioning.ts"),
    Path("src/components/ProtocolLabPilotMatrixPanel.tsx"),
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
    first_run_qa_added: bool
    demo_share_created: bool
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
        "Files created or modified by Wave 4E7.5:",
        "",
    ]
    for path in paths:
        lines.append(f"- `{path.as_posix()}`")
    return "\n".join(lines) + "\n"


def build_packet_readme(changed_paths: list[Path], support_paths: list[Path]) -> str:
    lines = [
        f"# {PACKET_PREFIX}",
        "",
        f"This packet contains the {TASK_NAME} reports, visible-surface source changes, targeted QA, updated product-positioning artifacts, and a deterministic render preview.",
        "",
        "## Included",
        "",
        "- updated Wave 4E7.5 reports",
        "- modified Home, Companies, and company-entry source files",
        "- modified first-run helper support and targeted QA files",
        "- updated product-positioning artifacts including `demo_share_v1.json`",
        "- deterministic render preview plus changed-file manifest",
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
        "- The primary CTA now reads `Open NVDA first` and the secondary CTA now reads `Browse all 3 cases`.",
        "- The right-rail start block now reads `Where to start` and includes a compact use-case guide.",
        "- Selected-case cards now end with ticker-specific action labels such as `Open KO case`.",
        "",
        "## Companies",
        "",
        "- The top CTA now reads `Open NVDA first` instead of a generic start action.",
        "- The start strip now reads `Where to start` and is followed by the same three-row use-case guide used on Home.",
        "- Case cards now use `Best first if` and ticker-specific CTA labels.",
        "",
        "## Company / NVDA",
        "",
        "- `Case thesis` now reads `What this case shows`.",
        "- `Available reads` now renders as chips instead of one comma-separated line.",
        "- `First read` now renders as short numbered cards, and the back-link now reads `Back to 3 cases`.",
        "",
        "## Narrow Width Note",
        "",
        "- Home and Companies top CTAs now stack cleanly on narrow widths with full-width mobile treatment.",
        "- Company / NVDA keeps the entry sidebar readable on narrow widths because read labels are chipped and the reading order is carded.",
    ]
    return "\n".join(lines) + "\n"


def build_changed_repo_paths() -> list[Path]:
    return unique_paths(
        [
            *REPORT_PATHS,
            *VISIBLE_SURFACE_PATHS,
            *HELPER_PATHS,
            *ARTIFACT_PATHS,
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
    (packet_dir / ROOT_README_NAME).write_text(
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
        "- Company first-run support",
        "whether first-run QA was added or expanded: yes",
        "whether demo_share_v1.json was created: yes",
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
        first_run_qa_added=True,
        demo_share_created=True,
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
