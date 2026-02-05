from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Optional, cast


def as_str_dict(value: Any) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    output: dict[str, Any] = {}
    for key, item in cast(dict[Any, Any], value).items():
        if not isinstance(key, str):
            return None
        output[key] = item
    return output


def as_list(value: Any) -> Optional[list[Any]]:
    if isinstance(value, list):
        return cast(list[Any], value)
    return None


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def rbo_score(list_a: list[str], list_b: list[str], p: float = 0.9) -> float:
    if not list_a and not list_b:
        return 0.0
    if not list_a or not list_b:
        return 0.0

    depth = max(len(list_a), len(list_b))
    score = 0.0
    set_a: set[str] = set()
    set_b: set[str] = set()

    for d in range(1, depth + 1):
        if d <= len(list_a):
            set_a.add(list_a[d - 1])
        if d <= len(list_b):
            set_b.add(list_b[d - 1])
        overlap = len(set_a & set_b)
        score += (overlap / d) * (p ** (d - 1))

    return (1 - p) * score


def extract_ranked_labels(artifacts: dict[str, Any]) -> list[str]:
    ranked: list[str] = []
    ranked_items = artifacts.get("ranked_items")
    if isinstance(ranked_items, list):
        for item in cast(list[Any], ranked_items):
            if isinstance(item, dict):
                label: Any = cast(dict[str, Any], item).get("label")
                if isinstance(label, str):
                    ranked.append(label)
            elif isinstance(item, str):
                ranked.append(item)
    if not ranked:
        for key in ("top_risers", "top_fallers"):
            items = artifacts.get(key)
            if isinstance(items, list):
                for item in cast(list[Any], items):
                    if isinstance(item, dict):
                        label: Any = cast(dict[str, Any], item).get("label")
                        if isinstance(label, str):
                            ranked.append(label)
                    elif isinstance(item, str):
                        ranked.append(item)
    return ranked


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate Narrative Drift Lab outputs.")
    parser.add_argument(
        "--registry",
        default="public/data/sec_narrative_drift_lab/lab_cases_v1.json",
        help="Path to lab cases registry",
    )
    parser.add_argument("--out_dir", default="reports", help="Output directory for reports")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    registry_path = Path(args.registry)
    if not registry_path.exists():
        raise SystemExit(f"Registry not found: {registry_path}")

    registry = read_json(registry_path)
    registry_dict = as_str_dict(registry)
    if registry_dict is None:
        raise SystemExit("Registry JSON invalid.")

    cases_raw = as_list(registry_dict.get("cases"))
    if cases_raw is None:
        raise SystemExit("Registry missing cases list.")

    rows: list[dict[str, Any]] = []
    detector_presence: Counter[str] = Counter()
    detector_expected: Counter[str] = Counter()
    warning_counts: Counter[str] = Counter()

    base_dir = registry_path.parent

    for case in cases_raw:
        case_dict = as_str_dict(case)
        if case_dict is None:
            continue
        ticker = case_dict.get("ticker")
        year_from = case_dict.get("year_from")
        year_to = case_dict.get("year_to")
        expected = case_dict.get("expected_detectors")
        outputs = case_dict.get("outputs")
        if not isinstance(ticker, str) or not isinstance(year_from, int) or not isinstance(year_to, int):
            continue
        expected_list: list[str] = []
        if isinstance(expected, list):
            for item in cast(list[Any], expected):
                if isinstance(item, str):
                    expected_list.append(item)
                    detector_expected[item] += 1

        if not isinstance(outputs, list):
            continue

        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for output in cast(list[Any], outputs):
            output_dict = as_str_dict(output)
            if output_dict is None:
                continue
            lens = output_dict.get("cleaning_lens")
            source_id = output_dict.get("source_id")
            if not isinstance(lens, str) or not isinstance(source_id, str):
                continue
            grouped.setdefault((lens, source_id), []).append(output_dict)

        for (lens, source_id), outputs_for_group in grouped.items():
            present_detectors: list[str] = []
            ranked_lists: list[list[str]] = []
            group_warning_count = 0

            for output in outputs_for_group:
                detector_id = output.get("detector_id")
                filename = output.get("filename")
                if not isinstance(detector_id, str) or not isinstance(filename, str):
                    continue
                present_detectors.append(detector_id)
                detector_presence[detector_id] += 1

                output_path = base_dir / ticker / filename
                if not output_path.exists():
                    continue
                payload = read_json(output_path)
                payload_dict = as_str_dict(payload)
                if payload_dict is None:
                    continue
                artifacts = payload_dict.get("artifacts")
                if isinstance(artifacts, dict):
                    labels = extract_ranked_labels(cast(dict[str, Any], artifacts))
                    if labels:
                        ranked_lists.append(labels)

                metrics = payload_dict.get("metrics")
                if isinstance(metrics, dict):
                    warnings: Any = cast(dict[str, Any], metrics).get("warnings")
                    if isinstance(warnings, list):
                        for entry in cast(list[Any], warnings):
                            if isinstance(entry, str):
                                warning_counts[entry] += 1
                                group_warning_count += 1

            missing = [item for item in expected_list if item not in present_detectors]

            agreement_score = None
            if len(ranked_lists) >= 2:
                scores: list[float] = []
                for i in range(len(ranked_lists)):
                    for j in range(i + 1, len(ranked_lists)):
                        scores.append(rbo_score(ranked_lists[i], ranked_lists[j], p=0.9))
                if scores:
                    agreement_score = sum(scores) / len(scores)

            rows.append(
                {
                    "ticker": ticker,
                    "year_from": year_from,
                    "year_to": year_to,
                    "lens": lens,
                    "source_id": source_id,
                    "detectors_present": ";".join(sorted(set(present_detectors))),
                    "missing_detectors": ";".join(sorted(missing)),
                    "agreement_score": "" if agreement_score is None else f"{agreement_score:.4f}",
                    "warning_count": group_warning_count,
                }
            )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "lab_eval_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "ticker",
                "year_from",
                "year_to",
                "lens",
                "source_id",
                "detectors_present",
                "missing_detectors",
                "agreement_score",
                "warning_count",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    md_path = out_dir / "lab_eval_summary.md"
    lines: list[str] = []
    lines.append("# Narrative Drift Lab - Evaluation Summary")
    lines.append("")
    lines.append(f"Total cases evaluated: {len(rows)}")
    lines.append("")

    lines.append("## Detector coverage")
    lines.append("")
    lines.append("| Detector | Present | Expected | Coverage |")
    lines.append("| --- | --- | --- | --- |")
    for detector, expected_count in detector_expected.items():
        present_count = detector_presence.get(detector, 0)
        coverage = present_count / expected_count if expected_count else 0.0
        lines.append(
            f"| {detector} | {present_count} | {expected_count} | {coverage:.2f} |"
        )

    lines.append("")
    lines.append("## Warning rates")
    lines.append("")
    lines.append("| Warning | Count |")
    lines.append("| --- | --- |")
    for warning, count in warning_counts.most_common():
        lines.append(f"| {warning} | {count} |")

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {csv_path} and {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
