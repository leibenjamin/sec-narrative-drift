from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Optional, cast

import build_lab_outputs as blo  # type: ignore

SCRIPT_VERSION = "lab_precompute_detectors_for_case.py@v2"

REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"
REPORTS_ROOT = REPO_ROOT / "reports"

SUPPORTED_DETECTORS = {
    "det_structure_artifacts_v1",
    "det_minhash_boilerplate_v1",
    "det_logodds_terms_v1",
    "det_jsd_ngrams_v1",
    "det_winnowing_fingerprint_v1",
    "det_rbo_agreement_v1",
}


def parse_csv_list(raw_values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for raw_value in raw_values:
        for piece in raw_value.split(","):
            candidate = piece.strip()
            if not candidate:
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            output.append(candidate)
    return output


def to_repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except Exception:
        return path.as_posix()


def resolve_section_source_path(ticker: str, year: int, section: str) -> Optional[Path]:
    suffix = blo.section_suffix(section)
    section_path = (
        REPO_ROOT
        / "scripts"
        / "_reports"
        / "risk_extraction_bundle"
        / "sections"
        / f"{ticker.upper()}_{year}_{suffix}.txt"
    )
    if section_path.exists():
        return section_path
    return blo.find_cached_html(REPO_ROOT, ticker, year)


def write_run_report(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_detector(
    detector_id: str,
    ticker: str,
    year_from: int,
    year_to: int,
    section: str,
    lens_pair: blo.LensPair,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    if detector_id == "det_structure_artifacts_v1":
        return blo.det_structure_artifacts_v1(lens_pair)
    if detector_id == "det_minhash_boilerplate_v1":
        return blo.det_minhash_boilerplate_v1(lens_pair)
    if detector_id == "det_logodds_terms_v1":
        return blo.det_logodds_terms_v1(
            REPO_ROOT, ticker, year_from, year_to, section, lens_pair
        )
    if detector_id == "det_jsd_ngrams_v1":
        return blo.det_jsd_ngrams_v1(lens_pair)
    if detector_id == "det_winnowing_fingerprint_v1":
        return blo.det_winnowing_fingerprint_v1(lens_pair)
    raise SystemExit(f"Unsupported detector: {detector_id}")


def append_warning_unique(payload: dict[str, Any], warning: str) -> None:
    metrics_raw = payload.get("metrics")
    if not isinstance(metrics_raw, dict):
        return
    metrics = cast(dict[str, Any], metrics_raw)
    warnings = metrics.get("warnings")
    if not isinstance(warnings, list):
        return
    for item in cast(list[object], warnings):
        if item == warning:
            return
    cast(list[Any], warnings).append(warning)


def add_conservative_quality_warnings(payload: dict[str, Any]) -> None:
    metrics_raw = payload.get("metrics")
    if not isinstance(metrics_raw, dict):
        return
    metrics = cast(dict[str, Any], metrics_raw)

    coverage: Any = metrics.get("coverage")
    if isinstance(coverage, (int, float)) and float(coverage) < 0.75:
        append_warning_unique(payload, "partial_coverage")

    confidence: Any = metrics.get("confidence")
    if confidence is None:
        append_warning_unique(payload, "confidence_unavailable")
    elif isinstance(confidence, (int, float)) and float(confidence) < 0.6:
        append_warning_unique(payload, "low_confidence")


def collect_metric_warnings(payload: dict[str, Any]) -> list[str]:
    metric_warnings_raw = payload.get("metrics", {}).get("warnings")
    metric_warnings: list[str] = []
    if isinstance(metric_warnings_raw, list):
        for entry in cast(list[object], metric_warnings_raw):
            if isinstance(entry, str):
                metric_warnings.append(entry)
    return metric_warnings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Precompute deterministic Lab detectors for one ticker/year pair."
    )
    parser.add_argument("--ticker", required=True, help="Ticker symbol, e.g. KO")
    parser.add_argument("--year-from", required=True, type=int)
    parser.add_argument("--year-to", required=True, type=int)
    parser.add_argument("--section", default="10k_item1a")
    parser.add_argument("--source", default="edgar", choices=["edgar"])
    parser.add_argument(
        "--lens",
        action="append",
        required=True,
        help="Repeat for multiple lenses, e.g. --lens raw --lens deboilerplated",
    )
    parser.add_argument(
        "--detectors",
        default="det_structure_artifacts_v1,det_minhash_boilerplate_v1",
        help="Comma-separated detector IDs.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    ticker = args.ticker.strip().upper()
    if not ticker:
        raise SystemExit("--ticker must not be empty.")

    year_from = min(args.year_from, args.year_to)
    year_to = max(args.year_from, args.year_to)
    section = args.section.strip()
    source_id = args.source

    lenses = parse_csv_list(args.lens)
    if not lenses:
        raise SystemExit("At least one lens is required.")
    for lens in lenses:
        if lens not in {"raw", "deboilerplated", "stage1_clean", "structure_aware"}:
            raise SystemExit(f"Unsupported lens: {lens}")

    detectors = parse_csv_list([args.detectors])
    if not detectors:
        raise SystemExit("At least one detector is required.")
    for detector in detectors:
        if detector not in SUPPORTED_DETECTORS:
            raise SystemExit(f"Unsupported detector: {detector}")

    prev_source_path = resolve_section_source_path(ticker, year_from, section)
    curr_source_path = resolve_section_source_path(ticker, year_to, section)

    prev_section = blo.load_section_text(ticker, year_from, section, source_id, REPO_ROOT)
    curr_section = blo.load_section_text(ticker, year_to, section, source_id, REPO_ROOT)
    if prev_section is None or curr_section is None:
        raise SystemExit(
            f"Missing section text for {ticker} {year_from}-{year_to} ({section}, source={source_id})."
        )

    outputs_written: list[str] = []
    warnings_by_output: dict[str, list[str]] = {}

    report_lines: list[str] = []
    report_lines.append(f"# Lab Precompute Report: {ticker} {year_from}-{year_to}")
    report_lines.append("")
    report_lines.append(f"- script: {SCRIPT_VERSION}")
    report_lines.append(f"- ticker: {ticker}")
    report_lines.append(f"- section: {section}")
    report_lines.append(f"- years: {year_from}-{year_to}")
    report_lines.append(f"- source: {source_id}")
    report_lines.append(f"- lenses: {', '.join(lenses)}")
    report_lines.append(f"- detectors: {', '.join(detectors)}")
    report_lines.append("")
    report_lines.append("## Inputs Used")
    report_lines.append(
        f"- prev ({year_from}): {to_repo_rel(prev_source_path) if prev_source_path else '(resolved internally)'}"
    )
    report_lines.append(
        f"- curr ({year_to}): {to_repo_rel(curr_source_path) if curr_source_path else '(resolved internally)'}"
    )
    report_lines.append(f"- prev_paragraph_count_raw: {len(prev_section.paragraphs)}")
    report_lines.append(f"- curr_paragraph_count_raw: {len(curr_section.paragraphs)}")
    report_lines.append("")

    report_lines.append("## Outputs Written")

    for lens in lenses:
        lens_pair = blo.build_lens_pair(prev_section, curr_section, lens)
        report_lines.append("")
        report_lines.append(f"### Lens `{lens}`")
        report_lines.append(f"- prev_paragraph_count: {len(lens_pair.prev.paragraphs)}")
        report_lines.append(f"- curr_paragraph_count: {len(lens_pair.curr.paragraphs)}")
        report_lines.append(
            f"- coverage: {lens_pair.coverage if lens_pair.coverage is not None else 'null'}"
        )
        if lens_pair.warnings:
            report_lines.append(f"- lens_warnings: {', '.join(lens_pair.warnings)}")
        else:
            report_lines.append("- lens_warnings: none")

        outputs_for_rbo: dict[str, dict[str, Any]] = {}

        for detector_id in detectors:
            if detector_id == "det_rbo_agreement_v1":
                continue

            artifacts, evidence, metrics = run_detector(
                detector_id=detector_id,
                ticker=ticker,
                year_from=year_from,
                year_to=year_to,
                section=section,
                lens_pair=lens_pair,
            )
            inputs: dict[str, str] = {
                "prev_text_sha256": blo.sha256_text(lens_pair.prev.text),
                "curr_text_sha256": blo.sha256_text(lens_pair.curr.text),
                "lens": lens_pair.lens,
                "source": source_id,
                "script": SCRIPT_VERSION,
            }
            if prev_source_path is not None:
                inputs["prev_input_path"] = to_repo_rel(prev_source_path)
            if curr_source_path is not None:
                inputs["curr_input_path"] = to_repo_rel(curr_source_path)

            payload = blo.build_lab_output(
                detector_id=detector_id,
                ticker=ticker,
                section=section,
                year_from=year_from,
                year_to=year_to,
                lens=lens,
                source_id=source_id,
                artifacts=artifacts,
                evidence=evidence,
                metrics=metrics,
                inputs=inputs,
            )
            validation_warnings = blo.validate_lab_output(payload)
            if validation_warnings:
                warnings_list = cast(list[str], payload["metrics"]["warnings"])
                for warning in validation_warnings:
                    warnings_list.append(warning)
            add_conservative_quality_warnings(payload)

            filename = blo.build_output_filename(
                section=section,
                year_from=year_from,
                year_to=year_to,
                detector_id=detector_id,
                lens=lens,
                source_id=source_id,
            )
            out_path = LAB_ROOT / ticker / "outputs" / detector_id / filename
            out_path.parent.mkdir(parents=True, exist_ok=True)
            blo.write_json(out_path, payload)
            outputs_written.append(to_repo_rel(out_path))

            metric_warnings = collect_metric_warnings(payload)
            warnings_by_output[to_repo_rel(out_path)] = metric_warnings

            report_lines.append(f"- {to_repo_rel(out_path)}")
            report_lines.append(f"  - evidence_blocks: {len(evidence)}")
            if metric_warnings:
                report_lines.append(f"  - warnings: {', '.join(metric_warnings)}")
            else:
                report_lines.append("  - warnings: none")
            outputs_for_rbo[detector_id] = payload

        if "det_rbo_agreement_v1" in detectors:
            artifacts, evidence, metrics = blo.det_rbo_agreement_v1(outputs_for_rbo)
            inputs: dict[str, str] = {
                "prev_text_sha256": blo.sha256_text(lens_pair.prev.text),
                "curr_text_sha256": blo.sha256_text(lens_pair.curr.text),
                "lens": lens_pair.lens,
                "source": source_id,
                "script": SCRIPT_VERSION,
                "ranked_list_inputs": ",".join(sorted(outputs_for_rbo.keys())),
            }
            if prev_source_path is not None:
                inputs["prev_input_path"] = to_repo_rel(prev_source_path)
            if curr_source_path is not None:
                inputs["curr_input_path"] = to_repo_rel(curr_source_path)

            payload = blo.build_lab_output(
                detector_id="det_rbo_agreement_v1",
                ticker=ticker,
                section=section,
                year_from=year_from,
                year_to=year_to,
                lens=lens,
                source_id=source_id,
                artifacts=artifacts,
                evidence=evidence,
                metrics=metrics,
                inputs=inputs,
            )
            validation_warnings = blo.validate_lab_output(payload)
            if validation_warnings:
                warnings_list = cast(list[str], payload["metrics"]["warnings"])
                for warning in validation_warnings:
                    warnings_list.append(warning)
            add_conservative_quality_warnings(payload)

            filename = blo.build_output_filename(
                section=section,
                year_from=year_from,
                year_to=year_to,
                detector_id="det_rbo_agreement_v1",
                lens=lens,
                source_id=source_id,
            )
            out_path = LAB_ROOT / ticker / "outputs" / "det_rbo_agreement_v1" / filename
            out_path.parent.mkdir(parents=True, exist_ok=True)
            blo.write_json(out_path, payload)
            outputs_written.append(to_repo_rel(out_path))

            metric_warnings = collect_metric_warnings(payload)
            warnings_by_output[to_repo_rel(out_path)] = metric_warnings

            report_lines.append(f"- {to_repo_rel(out_path)}")
            report_lines.append(f"  - evidence_blocks: {len(evidence)}")
            if metric_warnings:
                report_lines.append(f"  - warnings: {', '.join(metric_warnings)}")
            else:
                report_lines.append("  - warnings: none")

    report_path = REPORTS_ROOT / f"lab_precompute_{ticker}_{year_from}_{year_to}.md"
    write_run_report(report_path, report_lines)

    print(
        "Lab precompute complete: "
        + f"outputs_written={len(outputs_written)} report={to_repo_rel(report_path)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
