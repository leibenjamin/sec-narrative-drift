import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional, Union, cast

import yaml

NOISE_TOKENS = ("mr", "ms", "mrs", "dr")
WHITELIST_SHORT_TOKENS = ("ai", "us", "uk", "eu", "ip", "llm", "llms")

NORMALIZATION_INFO = {
    "lowercase": True,
    "hyphenToSpace": True,
    "stripNonWordPunctuation": True,
    "collapseWhitespace": True,
    "trim": True,
}

SHIFT_TERM_KEYS = (
    "risers",
    "fallers",
    "topRisers",
    "topFallers",
    "topRisersAlt",
    "topFallersAlt",
)

ConditionValue = Union[str, dict[str, Any]]


def as_str_dict(value: Any) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    output: dict[str, Any] = {}
    raw = cast(dict[object, object], value)
    for key, item in raw.items():
        if not isinstance(key, str):
            return None
        output[key] = item
    return output


def as_list(value: Any) -> Optional[list[Any]]:
    if not isinstance(value, list):
        return None
    return list(cast(list[Any], value))


def as_str_str_dict(value: Any) -> Optional[dict[str, str]]:
    if not isinstance(value, dict):
        return None
    output: dict[str, str] = {}
    raw = cast(dict[object, object], value)
    for key, item in raw.items():
        if not isinstance(key, str) or not isinstance(item, str):
            return None
        output[key] = item
    return output


class ValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("\n".join(errors))
        self.errors = errors


@dataclass
class ScanResult:
    top_terms: list[tuple[str, int]]
    coverage_top_percent: float
    coverage_all_percent: float
    uncovered_terms: list[tuple[str, int]]
    near_duplicates: list[tuple[str, str, float]]
    total_terms: int


def normalize_variant(value: str) -> str:
    lowered = value.lower()
    for dash in ("-", "\u2013", "\u2014"):
        lowered = lowered.replace(dash, " ")
    lowered = "".join(ch for ch in lowered if ch.isalnum() or ch.isspace() or ch == "_")
    collapsed = " ".join(lowered.split())
    return collapsed.strip()


def token_count(value: str) -> int:
    if not value:
        return 0
    return len(value.split())


def sort_variants(variants: list[str]) -> list[str]:
    def sort_key(value: str) -> tuple[int, int, str]:
        return (-token_count(value), -len(value), value)

    return sorted(variants, key=sort_key)


def load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace"))
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        raise ValidationError([f"YAML root must be a mapping: {path}"])
    return payload_dict


def validate_variant(
    raw: Any,
    concept_id: str,
    errors: list[str],
    warnings: list[str],
) -> Optional[str]:
    if not isinstance(raw, str):
        errors.append(f"{concept_id}: variant must be a string")
        return None
    trimmed = raw.strip()
    if not trimmed:
        errors.append(f"{concept_id}: variant is empty")
        return None
    normalized = normalize_variant(trimmed)
    if not normalized:
        errors.append(f"{concept_id}: variant normalizes to empty ({raw})")
        return None
    if not any(ch.isalpha() for ch in normalized):
        errors.append(f"{concept_id}: variant must include letters ({raw})")
        return None
    if normalized in NOISE_TOKENS:
        errors.append(f"{concept_id}: noise token not allowed ({normalized})")
        return None
    if len(normalized) < 3 and normalized not in WHITELIST_SHORT_TOKENS:
        errors.append(f"{concept_id}: short token not whitelisted ({normalized})")
        return None
    if token_count(normalized) > 5:
        warnings.append(f"{concept_id}: variant has >5 tokens ({normalized})")
    return normalized


def compile_terms(config: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    version = config.get("version")
    if not isinstance(version, (str, int, float)):
        errors.append("version is required and must be string/number")

    concepts_raw = config.get("concepts")
    concepts_list = as_list(concepts_raw)
    if concepts_list is None:
        errors.append("concepts must be a list")

    if errors:
        raise ValidationError(errors)

    concepts_output: list[dict[str, Any]] = []
    variant_to_concept: dict[str, str] = {}
    concept_ids: set[str] = set()
    total_variants = 0

    for concept_entry in concepts_list or []:
        concept = as_str_dict(concept_entry)
        if concept is None:
            errors.append("concept entry must be a mapping")
            continue
        concept_id = concept.get("id")
        label = concept.get("label")
        variants_value = as_list(concept.get("variants"))
        if not isinstance(concept_id, str) or not concept_id:
            errors.append("concept id must be a non-empty string")
            continue
        if concept_id in concept_ids:
            errors.append(f"duplicate concept id: {concept_id}")
            continue
        concept_ids.add(concept_id)
        if not isinstance(label, str) or not label:
            errors.append(f"{concept_id}: label must be a non-empty string")
        if variants_value is None or not variants_value:
            errors.append(f"{concept_id}: variants must be a non-empty list")

        normalized_variants: list[str] = []
        seen_variants: set[str] = set()
        if isinstance(variants_value, list):
            for variant in variants_value:
                normalized = validate_variant(variant, concept_id, errors, warnings)
                if normalized is None:
                    continue
                if normalized in seen_variants:
                    errors.append(
                        f"{concept_id}: duplicate variant after normalization ({normalized})"
                    )
                    continue
                if normalized in variant_to_concept:
                    existing = variant_to_concept[normalized]
                    if existing != concept_id:
                        errors.append(
                            f"variant overlap: {normalized} in {existing} and {concept_id}"
                        )
                        continue
                seen_variants.add(normalized)
                normalized_variants.append(normalized)
                variant_to_concept[normalized] = concept_id

        conditional_entries: list[tuple[str, ConditionValue]] = []
        conditional_variants = concept.get("conditional_variants")
        if conditional_variants is not None:
            conditional_list = as_list(conditional_variants)
            if conditional_list is None:
                errors.append(f"{concept_id}: conditional_variants must be a list")
            else:
                for entry in conditional_list:
                    entry_dict = as_str_dict(entry)
                    if entry_dict is None:
                        errors.append(f"{concept_id}: conditional variant must be a mapping")
                        continue
                    cond_variant = entry_dict.get("variant")
                    condition = entry_dict.get("condition")
                    normalized = validate_variant(cond_variant, concept_id, errors, warnings)
                    if normalized is None:
                        continue
                    if normalized in seen_variants:
                        errors.append(
                            f"{concept_id}: duplicate variant after normalization ({normalized})"
                        )
                        continue
                    if normalized in variant_to_concept:
                        existing = variant_to_concept[normalized]
                        if existing != concept_id:
                            errors.append(
                                f"variant overlap: {normalized} in {existing} and {concept_id}"
                            )
                            continue
                    condition_value: Optional[ConditionValue] = None
                    if isinstance(condition, str):
                        condition_value = condition
                    elif isinstance(condition, dict):
                        condition_dict = as_str_dict(condition)
                        if condition_dict is None:
                            errors.append(
                                f"{concept_id}: conditional variant invalid condition ({normalized})"
                            )
                            continue
                        condition_value = condition_dict
                    else:
                        errors.append(
                            f"{concept_id}: conditional variant missing condition ({normalized})"
                        )
                        continue
                    seen_variants.add(normalized)
                    variant_to_concept[normalized] = concept_id
                    conditional_entries.append((normalized, condition_value))

        normalized_variants = sort_variants(normalized_variants)

        conditional_entries.sort(
            key=lambda entry: (-token_count(entry[0]), -len(entry[0]), entry[0])
        )
        conditional_output: list[dict[str, Any]] = []
        for variant, condition in conditional_entries:
            conditional_output.append({"variant": variant, "condition": condition})

        total_variants += len(normalized_variants) + len(conditional_output)

        if len(normalized_variants) > 25:
            warnings.append(f"{concept_id}: variants > 25")

        concept_output: dict[str, Any] = {
            "id": concept_id,
            "label": label if isinstance(label, str) else "",
            "variants": normalized_variants,
        }
        notes = concept.get("notes")
        if isinstance(notes, str) and notes:
            concept_output["notes"] = notes
        if conditional_output:
            concept_output["conditionalVariants"] = conditional_output
        concepts_output.append(concept_output)

    if len(concepts_output) > 40:
        warnings.append("concept count > 40")
    if total_variants > 250:
        warnings.append("total variants > 250")

    if errors:
        raise ValidationError(errors)

    output = {
        "version": version,
        "concepts": concepts_output,
        "variantToConcept": variant_to_concept,
        "whitelistShortTokens": list(WHITELIST_SHORT_TOKENS),
        "noiseTokens": list(NOISE_TOKENS),
        "normalization": NORMALIZATION_INFO,
    }
    return output, warnings


def read_json(path: Path) -> Optional[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        return None
    return payload_dict


def extract_term_value(entry: Any) -> Optional[str]:
    if isinstance(entry, str):
        return entry
    entry_dict = as_str_dict(entry)
    if entry_dict is not None:
        term_value = entry_dict.get("term")
        if isinstance(term_value, str):
            return term_value
        label_value = entry_dict.get("label")
        if isinstance(label_value, str):
            return label_value
    return None


def collect_terms(payload: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    year_pairs = as_list(payload.get("yearPairs"))
    if year_pairs is not None:
        for pair in year_pairs:
            pair_dict = as_str_dict(pair)
            if pair_dict is None:
                continue
            for key in SHIFT_TERM_KEYS:
                items = as_list(pair_dict.get(key))
                if items is None:
                    continue
                for item in items:
                    value = extract_term_value(item)
                    if value:
                        terms.append(value)
    else:
        for key in SHIFT_TERM_KEYS:
            items = as_list(payload.get(key))
            if items is None:
                continue
            for item in items:
                value = extract_term_value(item)
                if value:
                    terms.append(value)
    return terms


def similarity_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def containment_ratio(a: str, b: str) -> float:
    if a in b:
        return len(a) / len(b)
    if b in a:
        return len(b) / len(a)
    return 0.0


def scan_corpus(scan_dir: Path, variant_to_concept: dict[str, str], top_k: int) -> ScanResult:
    counter: Counter[str] = Counter()
    for path in scan_dir.rglob("shifts_*.json"):
        payload = read_json(path)
        if payload is None:
            continue
        terms = collect_terms(payload)
        for term in terms:
            normalized = normalize_variant(term)
            if normalized:
                counter[normalized] += 1

    total_terms = sum(counter.values())
    top_terms = counter.most_common(top_k)
    mapped_top = 0
    for term, _count in top_terms:
        if term in variant_to_concept:
            mapped_top += 1
    mapped_all = 0
    for term, count in counter.items():
        if term in variant_to_concept:
            mapped_all += count

    coverage_top = (mapped_top / len(top_terms)) * 100 if top_terms else 0.0
    coverage_all = (mapped_all / total_terms) * 100 if total_terms else 0.0

    uncovered_terms: list[tuple[str, int]] = []
    for term, count in top_terms:
        if term not in variant_to_concept:
            uncovered_terms.append((term, count))

    near_duplicates: list[tuple[str, str, float]] = []
    for idx, (term_a, _count_a) in enumerate(uncovered_terms):
        for term_b, _count_b in uncovered_terms[idx + 1 :]:
            sim = similarity_ratio(term_a, term_b)
            contain = containment_ratio(term_a, term_b)
            if sim >= 0.92 or contain >= 0.95:
                near_duplicates.append((term_a, term_b, max(sim, contain)))
    near_duplicates = near_duplicates[:20]

    return ScanResult(
        top_terms=top_terms,
        coverage_top_percent=coverage_top,
        coverage_all_percent=coverage_all,
        uncovered_terms=uncovered_terms,
        near_duplicates=near_duplicates,
        total_terms=total_terms,
    )


def build_report(
    output: dict[str, Any],
    warnings: list[str],
    scan_result: Optional[ScanResult],
    generated_at: str,
) -> str:
    concepts = as_list(output.get("concepts")) or []
    concepts_count = len(concepts)
    variant_to_concept = as_str_str_dict(output.get("variantToConcept")) or {}
    variants_count = len(variant_to_concept)

    lines: list[str] = []
    lines.append("# Canonical Terms Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- generatedAt: {generated_at}")
    lines.append(f"- concepts: {concepts_count}")
    lines.append(f"- variants: {variants_count}")
    if warnings:
        lines.append("- warnings:")
        for warning in warnings:
            lines.append(f"  - {warning}")
    else:
        lines.append("- warnings: none")

    lines.append("")
    lines.append("## Validation results")
    lines.append(f"- noiseTokens: {', '.join(NOISE_TOKENS)}")
    lines.append(f"- whitelistShortTokens: {', '.join(WHITELIST_SHORT_TOKENS)}")
    lines.append("- overlap check: none")

    lines.append("")
    lines.append("## Concepts table")
    lines.append("| id | label | variants | conditional | notes |")
    lines.append("| --- | --- | --- | --- | --- |")
    for concept in concepts:
        concept_dict = as_str_dict(concept)
        if concept_dict is None:
            continue
        concept_id = concept_dict.get("id")
        label = concept_dict.get("label")
        variants = as_list(concept_dict.get("variants"))
        conditional = as_list(concept_dict.get("conditionalVariants"))
        notes = concept_dict.get("notes")
        concept_id_text = concept_id if isinstance(concept_id, str) else ""
        label_text = label if isinstance(label, str) else ""
        variant_count = len(variants) if variants is not None else 0
        conditional_count = len(conditional) if conditional is not None else 0
        notes_value = notes if isinstance(notes, str) else ""
        lines.append(
            f"| {concept_id_text} | {label_text} | {variant_count} | {conditional_count} | {notes_value} |"
        )

    if scan_result:
        lines.append("")
        lines.append("## Corpus scan")
        lines.append(f"- total terms scanned: {scan_result.total_terms}")
        lines.append(
            f"- coverage top terms: {scan_result.coverage_top_percent:.1f}%"
        )
        lines.append(
            f"- coverage all terms: {scan_result.coverage_all_percent:.1f}%"
        )
        lines.append("")
        lines.append("### Top terms by frequency")
        for term, count in scan_result.top_terms:
            lines.append(f"- {term}: {count}")

        lines.append("")
        lines.append("### Top uncovered terms")
        if scan_result.uncovered_terms:
            for term, count in scan_result.uncovered_terms:
                lines.append(f"- {term}: {count}")
        else:
            lines.append("- none")

        lines.append("")
        lines.append("### Suggested near-duplicate pairs")
        if scan_result.near_duplicates:
            for left, right, score in scan_result.near_duplicates:
                lines.append(f"- {left} ~ {right} ({score:.2f})")
        else:
            lines.append("- none")

    lines.append("")
    return "\n".join(lines)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_report(path: Path, report: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build canonical terms JSON from YAML.")
    parser.add_argument(
        "--in",
        dest="input_path",
        default="scripts/resources/canonical_terms.yml",
        help="Path to canonical_terms.yml",
    )
    parser.add_argument(
        "--out",
        dest="output_path",
        help="Path to canonical_terms.json",
    )
    parser.add_argument(
        "--report",
        dest="report_path",
        help="Path to canonical_terms_report.md",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate only; do not write outputs.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat validation warnings as visible in output (still non-fatal).",
    )
    parser.add_argument(
        "--scan-public",
        dest="scan_public",
        help="Directory to scan for shifts_*.json",
    )
    parser.add_argument(
        "--scan-top-k",
        dest="scan_top_k",
        type=int,
        default=50,
        help="Top N terms to include in scan report.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_yaml(Path(args.input_path))
        output, warnings = compile_terms(config)
        generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        )
        output["generatedAt"] = generated_at

        scan_result = None
        if args.scan_public:
            variant_to_concept = as_str_str_dict(output.get("variantToConcept")) or {}
            scan_result = scan_corpus(
                Path(args.scan_public),
                variant_to_concept,
                args.scan_top_k,
            )

        if args.check:
            if warnings and args.strict:
                for warning in warnings:
                    print(f"warning: {warning}", file=sys.stderr)
            return 0

        if not args.output_path or not args.report_path:
            raise ValidationError(["--out and --report are required unless --check is used"])

        report = build_report(output, warnings, scan_result, generated_at)
        write_json(Path(args.output_path), output)
        write_report(Path(args.report_path), report)
        return 0

    except ValidationError as exc:
        for error in exc.errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - unexpected runtime failure
        print(f"error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
