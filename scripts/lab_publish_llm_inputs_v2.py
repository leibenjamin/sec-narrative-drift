from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, cast

from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLES_ROOT = REPO_ROOT / "bundles"
PUBLIC_V2_ROOT = (
    REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab" / "llm_inputs_v2"
)
DEFAULT_REPORT = REPO_ROOT / "reports" / "lab_llm_inputs_v2_publish.md"


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _find_latest_bundle() -> Optional[Path]:
    if not BUNDLES_ROOT.exists():
        return None
    candidates: list[Path] = []
    for entry in BUNDLES_ROOT.iterdir():
        if not entry.is_dir():
            continue
        if not entry.name.startswith("showcase_llm_inputs_"):
            continue
        if not (entry / "inputs_index_year_v2.json").exists():
            continue
        if not (entry / "inputs_index_pair_v2.json").exists():
            continue
        if not (entry / "inputs").exists():
            continue
        candidates.append(entry)
    if not candidates:
        return None
    return sorted(candidates, key=lambda path: path.name)[-1]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish full-section v2 LLM inputs from bundle to public mirror."
    )
    parser.add_argument(
        "--bundle",
        default="",
        help="Bundle root (defaults to latest showcase_llm_inputs_* with v2 indexes).",
    )
    parser.add_argument(
        "--out-root",
        default=str(PUBLIC_V2_ROOT),
        help="Destination mirror root under public/data.",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT),
        help="Publish report markdown path.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove destination root before publishing.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    bundle_root = Path(args.bundle) if args.bundle else _find_latest_bundle()
    if bundle_root is None:
        raise SystemExit(
            "No v2 bundle found. Pass --bundle or generate a bundle with inputs_index_year_v2.json."
        )
    if not bundle_root.is_absolute():
        bundle_root = (REPO_ROOT / bundle_root).resolve()
    if not bundle_root.exists():
        raise SystemExit(f"Bundle not found: {bundle_root}")

    out_root = Path(args.out_root)
    if not out_root.is_absolute():
        out_root = (REPO_ROOT / out_root).resolve()

    year_index_src = bundle_root / "inputs_index_year_v2.json"
    pair_index_src = bundle_root / "inputs_index_pair_v2.json"
    inputs_src = bundle_root / "inputs"

    if not year_index_src.exists() or not pair_index_src.exists():
        raise SystemExit(
            f"Bundle missing v2 indexes: {year_index_src} / {pair_index_src}"
        )
    if not inputs_src.exists():
        raise SystemExit(f"Bundle missing inputs directory: {inputs_src}")

    _yi_raw = _read_json(year_index_src)
    _pi_raw = _read_json(pair_index_src)
    if not isinstance(_yi_raw, list) or not isinstance(_pi_raw, list):
        raise SystemExit("v2 indexes must be JSON lists")
    year_index = cast(list[dict[str, object]], _yi_raw)
    pair_index = cast(list[dict[str, object]], _pi_raw)

    if args.clean and out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    inputs_dst = out_root / "inputs"
    copied_files = 0
    for path in sorted(inputs_src.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(inputs_src)
        dst = inputs_dst / rel
        _copy_file(path, dst)
        copied_files += 1

    _copy_file(year_index_src, out_root / "inputs_index_year_v2.json")
    _copy_file(pair_index_src, out_root / "inputs_index_pair_v2.json")

    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = (REPO_ROOT / report_path).resolve()

    lines: list[str] = []
    lines.append("# LLM Inputs v2 Publish Report")
    lines.append("")
    lines.append(f"- script: `{SCRIPT_VERSION}`")
    lines.append(f"- published_at_utc: `{now_utc_iso()}`")
    lines.append(f"- bundle_root: `{bundle_root.relative_to(REPO_ROOT).as_posix()}`")
    lines.append(f"- out_root: `{out_root.relative_to(REPO_ROOT).as_posix()}`")
    lines.append(f"- copied_input_files: `{copied_files}`")
    lines.append(f"- year_index_rows: `{len(year_index)}`")
    lines.append(f"- pair_index_rows: `{len(pair_index)}`")
    lines.append("")
    lines.append("## Published Artifacts")
    lines.append(f"- `{(out_root / 'inputs_index_year_v2.json').relative_to(REPO_ROOT).as_posix()}`")
    lines.append(f"- `{(out_root / 'inputs_index_pair_v2.json').relative_to(REPO_ROOT).as_posix()}`")
    lines.append(f"- `{(out_root / 'inputs').relative_to(REPO_ROOT).as_posix()}`")
    _write_text(report_path, lines)

    print(f"Script: {SCRIPT_VERSION}")
    print(f"Bundle: {bundle_root}")
    print(f"Published to: {out_root}")
    print(f"Copied input files: {copied_files}")
    print(f"Wrote report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
