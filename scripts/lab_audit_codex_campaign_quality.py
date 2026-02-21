from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, cast

from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "reports" / "lab_llm_run_manifest.json"
DEFAULT_REPORT = REPO_ROOT / "reports" / "lab_llm_codex_quality_audit.md"

DELTA_TEMPLATE_MIN_UNIQUE = 10
WHY_UNIQUE_RATIO_MIN = 0.35
CONFIDENCE_LEVEL_MIN = 2

YEAR_RE = re.compile(r"\b20\d{2}\b")
PARA_RE = re.compile(r"\bpara\s+\d+\b", re.IGNORECASE)
WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ManifestTarget:
    ticker: str
    year_from: int
    year_to: int
    detector_id: str
    expected_output_path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Codex campaign output quality.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Manifest JSON to audit (default: reports/lab_llm_run_manifest.json).",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help="Markdown report output path.",
    )
    return parser.parse_args()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_delta_template(text: str) -> str:
    text = YEAR_RE.sub("YYYY", text)
    text = PARA_RE.sub("para NN", text)
    text = WHITESPACE_RE.sub(" ", text).strip().lower()
    return text


def _normalize_why(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip().lower()


def _load_manifest_targets(manifest_path: Path) -> tuple[list[ManifestTarget], str]:
    payload = _read_json(manifest_path)
    if not isinstance(payload, dict):
        raise SystemExit(f"Manifest root must be object: {manifest_path}")
    payload = cast("dict[str, Any]", payload)
    campaign_block = payload.get("campaign")
    if not isinstance(campaign_block, dict):
        raise SystemExit(f"Manifest missing campaign block: {manifest_path}")
    campaign_block = cast("dict[str, Any]", campaign_block)
    campaign_id = campaign_block.get("campaign_id")
    if not isinstance(campaign_id, str):
        raise SystemExit(f"Manifest missing campaign_id: {manifest_path}")

    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise SystemExit(f"Manifest missing entries[]: {manifest_path}")
    entries = cast("list[Any]", entries)

    targets: list[ManifestTarget] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry = cast("dict[str, Any]", entry)
        ticker = entry.get("ticker")
        year_from = entry.get("year_from")
        year_to = entry.get("year_to")
        detectors = entry.get("detectors")
        if (
            not isinstance(ticker, str)
            or not isinstance(year_from, int)
            or not isinstance(year_to, int)
            or not isinstance(detectors, list)
        ):
            continue
        detectors = cast("list[Any]", detectors)
        for detector in detectors:
            if not isinstance(detector, dict):
                continue
            detector = cast("dict[str, Any]", detector)
            detector_id = detector.get("detector_id")
            expected_path = detector.get("expected_output_path")
            if not isinstance(detector_id, str) or not isinstance(expected_path, str):
                continue
            targets.append(
                ManifestTarget(
                    ticker=ticker,
                    year_from=year_from,
                    year_to=year_to,
                    detector_id=detector_id,
                    expected_output_path=(REPO_ROOT / expected_path).resolve(),
                )
            )
    return targets, campaign_id


def _format_status(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def _coerce_confidence(value: object) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest if args.manifest.is_absolute() else (REPO_ROOT / args.manifest)
    report_path = args.report if args.report.is_absolute() else (REPO_ROOT / args.report)

    targets, campaign_id = _load_manifest_targets(manifest_path)
    delta_template_counter: Counter[str] = Counter()
    why_counter: Counter[str] = Counter()
    confidence_counter: Counter[float] = Counter()
    missing_files: list[str] = []
    unreadable_files: list[str] = []
    total_evidence_blocks = 0
    spot_pair_set = {
        ("NVDA", 2019, 2020),
        ("NVDA", 2023, 2024),
        ("KO", 2020, 2021),
        ("KO", 2023, 2024),
        ("WM", 2021, 2022),
        ("WM", 2023, 2024),
        ("GE", 2020, 2021),
        ("GE", 2022, 2023),
    }
    spot_rows: list[str] = []

    for target in targets:
        if not target.expected_output_path.exists():
            missing_files.append(str(target.expected_output_path))
            continue
        try:
            payload = _read_json(target.expected_output_path)
        except Exception:
            unreadable_files.append(str(target.expected_output_path))
            continue
        if not isinstance(payload, dict):
            unreadable_files.append(str(target.expected_output_path))
            continue
        payload = cast("dict[str, Any]", payload)

        metrics = payload.get("metrics")
        if isinstance(metrics, dict):
            metrics = cast("dict[str, Any]", metrics)
            confidence = _coerce_confidence(metrics.get("confidence"))
            if confidence is not None:
                confidence_counter[confidence] += 1

        evidence = payload.get("evidence")
        if isinstance(evidence, list):
            evidence = cast("list[Any]", evidence)
            for block in evidence:
                if not isinstance(block, dict):
                    continue
                block = cast("dict[str, Any]", block)
                why = block.get("why")
                if isinstance(why, str) and why.strip():
                    why_counter[_normalize_why(why)] += 1
                total_evidence_blocks += 1

        if target.detector_id == "det_llm_delta_brief_v1":
            artifacts = payload.get("artifacts")
            if isinstance(artifacts, dict):
                artifacts = cast("dict[str, Any]", artifacts)
                delta_brief = artifacts.get("delta_brief")
                if isinstance(delta_brief, str):
                    delta_template_counter[_normalize_delta_template(delta_brief)] += 1

        key = (target.ticker, target.year_from, target.year_to)
        if key in spot_pair_set and target.detector_id == "det_llm_delta_brief_v1":
            delta_text = ""
            artifacts = payload.get("artifacts")
            if isinstance(artifacts, dict):
                artifacts = cast("dict[str, Any]", artifacts)
                raw_delta = artifacts.get("delta_brief")
                if isinstance(raw_delta, str):
                    delta_text = WHITESPACE_RE.sub(" ", raw_delta).strip()
            delta_excerpt = delta_text[:220] + ("..." if len(delta_text) > 220 else "")
            spot_rows.append(
                f"- {target.ticker} {target.year_from}-{target.year_to}: `{target.expected_output_path.relative_to(REPO_ROOT)}`\n"
                + f"  - delta_excerpt: {delta_excerpt}"
            )

    delta_unique = len(delta_template_counter)
    delta_total = sum(delta_template_counter.values())
    why_unique = len(why_counter)
    why_ratio = (why_unique / total_evidence_blocks) if total_evidence_blocks else 0.0
    confidence_levels = sorted(confidence_counter.keys())

    delta_pass = delta_unique >= DELTA_TEMPLATE_MIN_UNIQUE
    why_pass = why_ratio >= WHY_UNIQUE_RATIO_MIN
    confidence_pass = len(confidence_levels) >= CONFIDENCE_LEVEL_MIN
    file_health_pass = not missing_files and not unreadable_files

    lines: list[str] = []
    lines.append("# Codex Campaign Quality Audit")
    lines.append("")
    lines.append(f"- script: `{SCRIPT_VERSION}`")
    lines.append(f"- campaign_id: `{campaign_id}`")
    lines.append(f"- manifest: `{manifest_path.relative_to(REPO_ROOT)}`")
    lines.append(f"- targets: `{len(targets)}`")
    lines.append("")
    lines.append("## Gate Results")
    lines.append("")
    lines.append(
        f"- Delta template uniqueness: `{delta_unique}/{delta_total}` "
        + f"(threshold >= `{DELTA_TEMPLATE_MIN_UNIQUE}`) -> `{_format_status(delta_pass)}`"
    )
    lines.append(
        f"- Evidence rationale uniqueness ratio: `{why_unique}/{total_evidence_blocks}` = "
        + f"`{why_ratio:.3f}` (threshold >= `{WHY_UNIQUE_RATIO_MIN:.2f}`) -> `{_format_status(why_pass)}`"
    )
    lines.append(
        "- Confidence variation levels: `"
        + ", ".join(f"{value:.2f}" for value in confidence_levels)
        + "` "
        + f"(need >= `{CONFIDENCE_LEVEL_MIN}` levels) -> `{_format_status(confidence_pass)}`"
    )
    lines.append(
        f"- File readability/presence health -> `{_format_status(file_health_pass)}`"
    )
    lines.append("")
    lines.append("## Top Repetition Signals")
    lines.append("")
    if delta_template_counter:
        lines.append("### Delta Templates (most frequent)")
        for template, count in delta_template_counter.most_common(5):
            lines.append(f"- count={count}: `{template[:180]}`")
    else:
        lines.append("- No delta templates found.")
    lines.append("")
    if why_counter:
        lines.append("### Evidence `why` Strings (most frequent)")
        for why_text, count in why_counter.most_common(8):
            lines.append(f"- count={count}: `{why_text[:180]}`")
    else:
        lines.append("- No `why` strings found.")
    lines.append("")
    lines.append("## Spot Review (8 required pairs)")
    lines.append("")
    if spot_rows:
        lines.extend(spot_rows)
    else:
        lines.append("- No spot-review rows captured.")
    lines.append("")
    if missing_files:
        lines.append("## Missing Files")
        lines.append("")
        for path in missing_files:
            lines.append(f"- `{path}`")
        lines.append("")
    if unreadable_files:
        lines.append("## Unreadable Files")
        lines.append("")
        for path in unreadable_files:
            lines.append(f"- `{path}`")
        lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote quality audit report: {report_path}")
    print(
        "Quality gates: "
        + f"delta={_format_status(delta_pass)}, "
        + f"why={_format_status(why_pass)}, "
        + f"confidence={_format_status(confidence_pass)}, "
        + f"files={_format_status(file_health_pass)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
