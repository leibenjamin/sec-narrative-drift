from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SCRIPT_VERSION = "lab_build_health_review_pack.py@v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLES_ROOT = REPO_ROOT / "bundles"

REGISTRY_PATH = Path("public/data/sec_narrative_drift_lab/lab_cases_v1.json")
HEALTH_REPORT_PATH = Path("reports/lab_cases_health.md")
SUMMARY_REPORT_PATH = Path("reports/lab_cases_summary.md")
WORKSPACE_HANDOFF_PATH = Path("reports/lab_workspace_handoff.md")

CHANGED_SOURCE_FILES = [
    "src/lib/paths.ts",
    "src/lib/labData.ts",
    "src/lib/data.ts",
    "src/components/LabPanel.tsx",
    "src/components/MethodCard.tsx",
    "scripts/lab_build_cases_health_reports.py",
    "scripts/lab_build_health_review_pack.py",
]

CORE_CONTEXT_FILES = [
    "AGENTS.md",
    "docs/00_README_doc_index.md",
    "docs/sec_narrative_drift_codex_spec_v1_13.md",
    "docs/sec_narrative_drift_codex_implementation_checklist_v1_13.md",
    "docs/lab/00_LAB_CANONICAL_SPEC.md",
    "src/lib/labSchemas.ts",
    "src/lib/labTypes.ts",
    "src/components/AgreementMatrix.tsx",
    "scripts/lab_build_cases_registry_v1.py",
    "scripts/lab_precompute_detectors_for_case.py",
    "scripts/build_lab_outputs.py",
    "scripts/lab_smoke_check_case_paths.py",
    "scripts/lab_smoke_check_registry_paths.py",
]

KO_SAMPLE_OUTPUTS = [
    "public/data/sec_narrative_drift_lab/KO/outputs/det_logodds_terms_v1/lab_10k_item1a_2023_2024_det_logodds_terms_v1_deboilerplated_edgar.json",
    "public/data/sec_narrative_drift_lab/KO/outputs/det_jsd_ngrams_v1/lab_10k_item1a_2023_2024_det_jsd_ngrams_v1_deboilerplated_edgar.json",
    "public/data/sec_narrative_drift_lab/KO/outputs/det_minhash_boilerplate_v1/lab_10k_item1a_2023_2024_det_minhash_boilerplate_v1_deboilerplated_edgar.json",
    "public/data/sec_narrative_drift_lab/KO/outputs/det_winnowing_fingerprint_v1/lab_10k_item1a_2023_2024_det_winnowing_fingerprint_v1_deboilerplated_edgar.json",
    "public/data/sec_narrative_drift_lab/KO/outputs/det_structure_artifacts_v1/lab_10k_item1a_2023_2024_det_structure_artifacts_v1_deboilerplated_edgar.json",
    "public/data/sec_narrative_drift_lab/KO/outputs/det_rbo_agreement_v1/lab_10k_item1a_2023_2024_det_rbo_agreement_v1_deboilerplated_edgar.json",
    "public/data/sec_narrative_drift_lab/KO/outputs/det_llm_delta_brief_v1/lab_det_llm_delta_brief_v1_10k_item1a_2023_2024_focuspack_deboilerplated.json",
    "public/data/sec_narrative_drift_lab/KO/outputs/det_llm_excerpt_picker_v1/lab_det_llm_excerpt_picker_v1_10k_item1a_2023_2024_focuspack_deboilerplated.json",
]

NVDA_SAMPLE_OUTPUTS = [
    "public/data/sec_narrative_drift_lab/NVDA/outputs/det_logodds_terms_v1/lab_10k_item1a_2023_2024_det_logodds_terms_v1_deboilerplated_edgar.json",
    "public/data/sec_narrative_drift_lab/NVDA/outputs/det_jsd_ngrams_v1/lab_10k_item1a_2023_2024_det_jsd_ngrams_v1_deboilerplated_edgar.json",
    "public/data/sec_narrative_drift_lab/NVDA/outputs/det_minhash_boilerplate_v1/lab_10k_item1a_2023_2024_det_minhash_boilerplate_v1_deboilerplated_edgar.json",
    "public/data/sec_narrative_drift_lab/NVDA/outputs/det_winnowing_fingerprint_v1/lab_10k_item1a_2023_2024_det_winnowing_fingerprint_v1_deboilerplated_edgar.json",
    "public/data/sec_narrative_drift_lab/NVDA/outputs/det_structure_artifacts_v1/lab_10k_item1a_2023_2024_det_structure_artifacts_v1_deboilerplated_edgar.json",
    "public/data/sec_narrative_drift_lab/NVDA/outputs/det_rbo_agreement_v1/lab_10k_item1a_2023_2024_det_rbo_agreement_v1_deboilerplated_edgar.json",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build ChatGPT review pack for Lab health/path coverage."
    )
    parser.add_argument(
        "--out-zip",
        default="",
        help="Optional explicit output zip path.",
    )
    return parser


def must_exist(rel_path: str) -> Path:
    path = REPO_ROOT / rel_path
    if not path.exists() or not path.is_file():
        raise SystemExit(f"Missing required file for review pack: {rel_path}")
    return path


def build_file_list() -> list[str]:
    files: list[str] = []
    seen: set[str] = set()

    def add(rel_path: str) -> None:
        if rel_path in seen:
            return
        seen.add(rel_path)
        files.append(rel_path)

    add(str(REGISTRY_PATH).replace("\\", "/"))
    add(str(HEALTH_REPORT_PATH).replace("\\", "/"))
    add(str(SUMMARY_REPORT_PATH).replace("\\", "/"))
    add(str(WORKSPACE_HANDOFF_PATH).replace("\\", "/"))

    for rel_path in CHANGED_SOURCE_FILES:
        add(rel_path)
    for rel_path in CORE_CONTEXT_FILES:
        add(rel_path)
    for rel_path in KO_SAMPLE_OUTPUTS:
        add(rel_path)
    for rel_path in NVDA_SAMPLE_OUTPUTS:
        add(rel_path)

    return files


def build_readme(file_paths: list[str], timestamp: str) -> str:
    lines: list[str] = []
    lines.append("# ChatGPT Review Pack: Lab Health")
    lines.append("")
    lines.append(f"- created_utc: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}")
    lines.append(f"- script: {SCRIPT_VERSION}")
    lines.append(f"- timestamp: {timestamp}")
    lines.append("")
    lines.append("## What Changed")
    lines.append("- Added base-path helper usage for Lab/data fetch URL construction.")
    lines.append("- Added Lab UI debug strings to show requested dataset path when fetch fails.")
    lines.append("- Regenerated deterministic Lab outputs/registry for KO and showcase tickers.")
    lines.append("- Added deterministic health reports for registry path/file coverage.")
    lines.append("")
    lines.append("## Included")
    lines.append("- Updated/added source files from this change set.")
    lines.append("- Registry: public/data/sec_narrative_drift_lab/lab_cases_v1.json")
    lines.append("- Reports: reports/lab_cases_health.md, reports/lab_cases_summary.md")
    lines.append("- KO 2023-2024 sample outputs and NVDA 2023-2024 sample outputs.")
    lines.append("- Core Lab scripts/spec/context files and workspace handoff map.")
    lines.append("")
    lines.append("## KO Expected Output Paths (2023-2024)")
    lines.append(
        "- public/data/sec_narrative_drift_lab/KO/outputs/det_logodds_terms_v1/lab_10k_item1a_2023_2024_det_logodds_terms_v1_deboilerplated_edgar.json"
    )
    lines.append(
        "- public/data/sec_narrative_drift_lab/KO/outputs/det_jsd_ngrams_v1/lab_10k_item1a_2023_2024_det_jsd_ngrams_v1_deboilerplated_edgar.json"
    )
    lines.append(
        "- public/data/sec_narrative_drift_lab/KO/outputs/det_minhash_boilerplate_v1/lab_10k_item1a_2023_2024_det_minhash_boilerplate_v1_deboilerplated_edgar.json"
    )
    lines.append(
        "- public/data/sec_narrative_drift_lab/KO/outputs/det_winnowing_fingerprint_v1/lab_10k_item1a_2023_2024_det_winnowing_fingerprint_v1_deboilerplated_edgar.json"
    )
    lines.append(
        "- public/data/sec_narrative_drift_lab/KO/outputs/det_structure_artifacts_v1/lab_10k_item1a_2023_2024_det_structure_artifacts_v1_deboilerplated_edgar.json"
    )
    lines.append(
        "- public/data/sec_narrative_drift_lab/KO/outputs/det_rbo_agreement_v1/lab_10k_item1a_2023_2024_det_rbo_agreement_v1_deboilerplated_edgar.json"
    )
    lines.append(
        "- public/data/sec_narrative_drift_lab/KO/outputs/det_llm_delta_brief_v1/lab_det_llm_delta_brief_v1_10k_item1a_2023_2024_focuspack_deboilerplated.json"
    )
    lines.append(
        "- public/data/sec_narrative_drift_lab/KO/outputs/det_llm_excerpt_picker_v1/lab_det_llm_excerpt_picker_v1_10k_item1a_2023_2024_focuspack_deboilerplated.json"
    )
    lines.append("")
    lines.append("## File Count")
    lines.append(f"- {len(file_paths)} files (plus README.md and manifest.json)")
    return "\n".join(lines) + "\n"


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stage_dir = BUNDLES_ROOT / f"review_pack_lab_health_{timestamp}"

    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True, exist_ok=True)

    file_paths = build_file_list()
    manifest_files: list[dict[str, object]] = []

    for rel_path in file_paths:
        source_path = must_exist(rel_path)
        destination_path = stage_dir / rel_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)
        manifest_files.append(
            {
                "path": rel_path,
                "sha256": sha256_file(source_path),
                "size_bytes": source_path.stat().st_size,
            }
        )

    readme_text = build_readme(file_paths, timestamp)
    (stage_dir / "README.md").write_text(readme_text, encoding="utf-8")

    manifest_payload = {
        "created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "script_version": SCRIPT_VERSION,
        "file_count": len(manifest_files),
        "files": manifest_files,
    }
    (stage_dir / "manifest.json").write_text(
        json.dumps(manifest_payload, indent=2) + "\n",
        encoding="utf-8",
    )

    out_zip = (
        Path(args.out_zip)
        if args.out_zip
        else REPO_ROOT / f"chatgpt_review_pack_lab_health_{timestamp}.zip"
    )
    if out_zip.exists():
        out_zip.unlink()

    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zip_handle:
        for path in sorted(stage_dir.rglob("*")):
            if path.is_file():
                zip_handle.write(path, path.relative_to(stage_dir).as_posix())

    print(f"Wrote review pack zip: {out_zip}")
    print(f"Stage dir: {stage_dir}")
    print(f"Files copied: {len(manifest_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
