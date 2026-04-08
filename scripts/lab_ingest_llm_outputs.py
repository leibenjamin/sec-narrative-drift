from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import sys

SCRIPT_VERSION = "lab_ingest_llm_outputs.py@v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUTS_DIR = (
    REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab" / "llm_outputs"
)

sys.path.append(str(Path(__file__).resolve().parent))
from lab_llm_precompute_utils import (  # type: ignore
    resolve_bundle_paths,
    to_repo_relative,
)
from lab_validate_llm_outputs import (  # type: ignore
    load_required_fields,
    print_issues,
    validate_outputs,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Package validated legacy detector-shaped LLM outputs into a shareable bundle."
        )
    )
    parser.add_argument(
        "--outputs-dir",
        default=str(DEFAULT_OUTPUTS_DIR),
        help="Path to public/data/sec_narrative_drift_lab/llm_outputs",
    )
    parser.add_argument(
        "--bundle",
        default="",
        help="Legacy queue bundle root (defaults to latest bundles/showcase_llm_inputs_*)",
    )
    parser.add_argument(
        "--inputs-index-focuspack",
        default="",
        help="Override path to inputs_index_focuspack.json",
    )
    parser.add_argument(
        "--inputs-index-full",
        default="",
        help="Override path to inputs_index_full.json",
    )
    parser.add_argument(
        "--prompt-templates",
        default="",
        help="Override path to prompt_templates_showcase.md (archived detector flow only)",
    )
    parser.add_argument(
        "--out-dir",
        default="",
        help="Output pack directory (default bundles/llm_outputs_pack_<timestamp>)",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    bundle_paths = resolve_bundle_paths(
        args.bundle or None,
        args.inputs_index_focuspack or None,
        args.inputs_index_full or None,
        args.prompt_templates or None,
    )
    outputs_dir = Path(args.outputs_dir)
    required_fields = load_required_fields(bundle_paths.prompt_templates)

    issues = validate_outputs(outputs_dir, bundle_paths, required_fields)
    if issues:
        print_issues(f"Validation failed: {len(issues)} invalid file(s)", issues)
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / "bundles" / f"llm_outputs_pack_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    output_files = sorted(outputs_dir.rglob("*.json"))
    for path in output_files:
        rel_path = path.relative_to(outputs_dir)
        dest_path = out_dir / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest_path)

    counts_by_detector: dict[str, int] = {}
    counts_by_ticker: dict[str, int] = {}
    for path in output_files:
        rel_parts = path.relative_to(outputs_dir).parts
        if len(rel_parts) < 2:
            continue
        detector_id = rel_parts[0]
        ticker = rel_parts[1]
        counts_by_detector[detector_id] = counts_by_detector.get(detector_id, 0) + 1
        counts_by_ticker[ticker] = counts_by_ticker.get(ticker, 0) + 1

    readme_lines: list[str] = []
    readme_lines.append("# LLM Outputs Pack")
    readme_lines.append("")
    readme_lines.append(f"Created: {timestamp}")
    readme_lines.append(f"Source outputs: {to_repo_relative(outputs_dir)}")
    readme_lines.append(f"Files: {len(output_files)}")
    readme_lines.append(f"Script: {SCRIPT_VERSION}")
    readme_lines.append("")
    readme_lines.append("## Counts By Detector")
    readme_lines.append("| Detector | Files |")
    readme_lines.append("| --- | --- |")
    for detector_id in sorted(counts_by_detector.keys()):
        readme_lines.append(f"| {detector_id} | {counts_by_detector[detector_id]} |")
    readme_lines.append("")
    readme_lines.append("## Counts By Ticker")
    readme_lines.append("| Ticker | Files |")
    readme_lines.append("| --- | --- |")
    for ticker in sorted(counts_by_ticker.keys()):
        readme_lines.append(f"| {ticker} | {counts_by_ticker[ticker]} |")

    (out_dir / "README.md").write_text("\n".join(readme_lines), encoding="utf-8")

    print(f"Wrote outputs pack to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
