from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional

from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "reports" / "lab_llm_master_manifest.json"
DEFAULT_OUT = REPO_ROOT / "reports" / "lab_llm_master_thread_starters.md"
PROMPT_SYSTEM_PATH = REPO_ROOT / "docs" / "lab" / "llm_master_compare_v3_system.md"
PROMPT_USER_TEMPLATE_PATH = REPO_ROOT / "docs" / "lab" / "llm_master_compare_v3_user_template.md"
PROMPT_SELF_CHECK_PATH = REPO_ROOT / "docs" / "lab" / "llm_master_compare_v3_self_check.md"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def as_dict(value: Any) -> Optional[dict[str, Any]]:
    if isinstance(value, dict):
        return value  # pyright: ignore[reportUnknownVariableType]
    return None


def as_list(value: Any) -> Optional[list[Any]]:
    if isinstance(value, list):
        return value  # pyright: ignore[reportUnknownVariableType]
    return None


def load_prompt_block(path: Path) -> str:
    if not path.exists():
        return f"[missing prompt block: {path.as_posix()}]"
    return path.read_text(encoding="utf-8")


def write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Emit canonical thread starters for llm_outline_compare_v1 master jobs."
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = (REPO_ROOT / manifest_path).resolve()
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = (REPO_ROOT / out_path).resolve()

    manifest = read_json(manifest_path)
    manifest_dict = as_dict(manifest)
    if manifest_dict is None:
        raise SystemExit("Manifest root must be an object.")
    entries = as_list(manifest_dict.get("entries"))
    if entries is None:
        raise SystemExit("Manifest missing entries list.")
    campaign_dict = as_dict(manifest_dict.get("campaign")) or {}
    campaign_id = str(campaign_dict.get("campaign_id") or "<campaign_id>")
    campaign_name = str(campaign_dict.get("display_name") or "<campaign_display>")

    system_block = load_prompt_block(PROMPT_SYSTEM_PATH).strip()
    user_template = load_prompt_block(PROMPT_USER_TEMPLATE_PATH).strip()
    self_check = load_prompt_block(PROMPT_SELF_CHECK_PATH).strip()

    lines: list[str] = []
    lines.append("# Master Thread Starters (llm_outline_compare_v1)")
    lines.append("")
    lines.append(f"- script: `{SCRIPT_VERSION}`")
    lines.append(f"- manifest: `{manifest_path.as_posix()}`")
    lines.append(f"- campaign: `{campaign_id}`")
    lines.append(f"- campaign display: `{campaign_name}`")
    lines.append("")
    lines.append("Run one thread per pair/lens. Attach exactly three files per job:")
    lines.append("1. Pair manifest JSON")
    lines.append("2. Year prev input JSON")
    lines.append("3. Year curr input JSON")
    lines.append("")

    emitted = 0
    for entry_any in entries:
        entry = as_dict(entry_any)
        if entry is None:
            continue
        input_block = as_dict(entry.get("input")) or {}
        master_output = as_dict(entry.get("master_output")) or {}
        ticker = str(entry.get("ticker") or "")
        year_from = entry.get("year_from")
        year_to = entry.get("year_to")
        lens = str(entry.get("lens") or "")
        section = str(entry.get("section") or "10k_item1a")
        source_id = str(entry.get("source_id") or "edgar")
        pair_path = str(input_block.get("source_path") or "")
        prev_path = str(input_block.get("source_year_prev_path") or "")
        curr_path = str(input_block.get("source_year_curr_path") or "")
        output_path = str(master_output.get("expected_output_path") or "")
        if not pair_path:
            continue
        emitted += 1

        lines.append(f"## {ticker} {year_from}-{year_to} {lens}")
        lines.append("")
        lines.append("```text")
        lines.append(f"Thread title: {ticker} {year_from}-{year_to} outline compare ({lens})")
        lines.append(f"Attach this input file: {pair_path}")
        if prev_path:
            lines.append(f"Attach this input file: {prev_path}")
        if curr_path:
            lines.append(f"Attach this input file: {curr_path}")
        lines.append(f"Save output to: {output_path}")
        lines.append("")
        lines.append(f"Case context: ticker={ticker}, pair={year_from}-{year_to}, section={section}, lens={lens}, source={source_id}")
        lines.append("")
        lines.append("SYSTEM PROMPT")
        lines.append(system_block)
        lines.append("")
        lines.append("USER PROMPT TEMPLATE")
        lines.append(user_template)
        lines.append("")
        lines.append("SELF-CHECK GATE (must pass before final JSON)")
        lines.append(self_check)
        lines.append("")
        lines.append("Output requirements:")
        lines.append("- JSON only, one top-level object.")
        lines.append("- artifact_id must be llm_outline_compare_v1.")
        lines.append("- provenance.input_file must exactly match the attached pair manifest path.")
        lines.append("- Evidence paragraph indices must map to full-year paragraph arrays.")
        lines.append("- Do not include markdown or commentary outside JSON.")
        lines.append("```")
        lines.append("")

    write_text(out_path, lines)
    print(f"Script: {SCRIPT_VERSION}")
    print(f"Wrote master thread starters: {out_path}")
    print(f"Jobs emitted: {emitted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
