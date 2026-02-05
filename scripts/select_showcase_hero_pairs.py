from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, cast

SCRIPT_VERSION = "select_showcase_hero_pairs.py@v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_LAB_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"
PUBLIC_BASELINE_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift"

sys.path.append(str(Path(__file__).resolve().parent))
import build_lab_outputs as blo  # type: ignore


@dataclass(frozen=True)
class PairScores:
    year_from: int
    year_to: int
    boilerplate_score: float
    structure_score: float
    drift_score: float
    term_signal_score: float
    term_signal_norm: float
    meaningful_score: float
    overall_score: float
    warnings: list[str]
    most_recent: bool


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def heading_like(text: str) -> bool:
    trimmed = text.strip()
    if not trimmed:
        return False
    if len(trimmed) > 120:
        return False
    if trimmed.upper() == trimmed and len(trimmed) >= 5:
        return True
    if trimmed.lower().startswith("item "):
        return True
    if trimmed.endswith(":"):
        return True
    words = trimmed.split()
    if len(words) <= 8 and trimmed[0].isupper():
        return True
    return False


def compute_jsd(tokens_a: list[str], tokens_b: list[str]) -> float:
    if not tokens_a or not tokens_b:
        return 0.0
    count_a = Counter(tokens_a)
    count_b = Counter(tokens_b)
    total_a = sum(count_a.values())
    total_b = sum(count_b.values())
    if total_a == 0 or total_b == 0:
        return 0.0
    vocab = set(count_a.keys()) | set(count_b.keys())
    jsd = 0.0
    for term in vocab:
        p = count_a.get(term, 0) / total_a
        q = count_b.get(term, 0) / total_b
        m = 0.5 * (p + q)
        if p > 0:
            jsd += 0.5 * p * math.log2(p / m)
        if q > 0:
            jsd += 0.5 * q * math.log2(q / m)
    return jsd


def load_lab_output(
    ticker: str,
    section: str,
    year_from: int,
    year_to: int,
    detector_id: str,
    lens: str = "raw",
    source_id: str = "edgar",
) -> Optional[dict[str, Any]]:
    filename = blo.build_output_filename(section, year_from, year_to, detector_id, lens, source_id)
    path = PUBLIC_LAB_ROOT / ticker.upper() / filename
    if not path.exists():
        return None
    payload = read_json(path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        return None
    return payload_dict


def extract_minhash_score(payload: Optional[dict[str, Any]]) -> Optional[float]:
    if payload is None:
        return None
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        return None
    artifacts_dict = cast(dict[str, Any], artifacts)
    stats = artifacts_dict.get("stats")
    if not isinstance(stats, dict):
        return None
    stats_dict = cast(dict[str, Any], stats)
    value = stats_dict.get("percent_reused")
    if isinstance(value, (int, float)):
        return float(value)
    return None


def extract_metric_score(payload: Optional[dict[str, Any]]) -> Optional[float]:
    if payload is None:
        return None
    metrics = payload.get("metrics")
    if not isinstance(metrics, dict):
        return None
    metrics_dict = cast(dict[str, Any], metrics)
    value = metrics_dict.get("drift_score")
    if isinstance(value, (int, float)):
        return float(value)
    return None


def extract_metric_warnings(payload: Optional[dict[str, Any]]) -> list[str]:
    if payload is None:
        return []
    metrics = payload.get("metrics")
    if not isinstance(metrics, dict):
        return []
    metrics_dict = cast(dict[str, Any], metrics)
    warnings = metrics_dict.get("warnings")
    if not isinstance(warnings, list):
        return []
    warnings_list = cast(list[Any], warnings)
    output: list[str] = []
    for entry in warnings_list:
        if isinstance(entry, str):
            output.append(entry)
    return output


def compute_boilerplate_proxy(prev_paras: list[str], curr_paras: list[str]) -> float:
    if not prev_paras or not curr_paras:
        return 0.0
    prev_norm = {normalize_text(p) for p in prev_paras if p.strip()}
    curr_norm = {normalize_text(p) for p in curr_paras if p.strip()}
    if not prev_norm or not curr_norm:
        return 0.0
    shared = len(prev_norm & curr_norm)
    denom = max(len(prev_norm), len(curr_norm))
    if denom == 0:
        return 0.0
    return shared / denom


def compute_structure_proxy(prev_text: str, curr_text: str, prev_paras: list[str], curr_paras: list[str]) -> float:
    prev_headings = sum(1 for p in prev_paras if heading_like(p))
    curr_headings = sum(1 for p in curr_paras if heading_like(p))
    heading_delta = abs(prev_headings - curr_headings) / max(prev_headings, curr_headings, 1)

    prev_len = max(1, len(prev_text))
    curr_len = max(1, len(curr_text))
    length_delta = abs(prev_len - curr_len) / max(prev_len, curr_len)

    prev_general = "general risk factors" in prev_text.lower()
    curr_general = "general risk factors" in curr_text.lower()
    general_delta = 1.0 if prev_general != curr_general else 0.0

    score = 0.5 * heading_delta + 0.4 * length_delta + 0.1 * general_delta
    return clamp01(score)


def load_term_shift_entry(
    ticker: str,
    section: str,
    year_from: int,
    year_to: int,
) -> Optional[dict[str, Any]]:
    path = PUBLIC_BASELINE_ROOT / ticker.upper() / f"shifts_{section}.json"
    if not path.exists():
        return None
    payload = read_json(path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        return None
    year_pairs = as_list(payload_dict.get("yearPairs"))
    if year_pairs is None:
        year_pairs = as_list(payload_dict.get("pairs"))
    if year_pairs is None:
        return None
    for entry in year_pairs:
        entry_dict = as_str_dict(entry)
        if entry_dict is None:
            continue
        if entry_dict.get("from") == year_from and entry_dict.get("to") == year_to:
            return entry_dict
    return None


def compute_term_signal(entry: Optional[dict[str, Any]], warnings: list[str]) -> float:
    if entry is None:
        warnings.append("missing_term_shift")
        return 0.0
    top_risers = entry.get("topRisers")
    top_fallers = entry.get("topFallers")
    if not isinstance(top_risers, list) and not isinstance(top_fallers, list):
        warnings.append("empty_shifts")
        return 0.0

    items: list[dict[str, Any]] = []
    groups = cast(tuple[Any, Any], (top_risers, top_fallers))
    for group in groups:
        if isinstance(group, list):
            group_list = cast(list[Any], group)
            for item in group_list:
                item_dict = as_str_dict(item)
                if item_dict is not None:
                    items.append(item_dict)

    if not items:
        warnings.append("empty_shifts")
        return 0.0

    distinctive_count = 0
    z_scores: list[float] = []
    for item in items:
        distinctive = item.get("distinctive")
        if distinctive is True:
            distinctive_count += 1
        z_value = item.get("z")
        if isinstance(z_value, (int, float)):
            z_scores.append(abs(float(z_value)))

    if distinctive_count == 0:
        warnings.append("no_distinctive_terms")

    median_z = statistics.median(z_scores) if z_scores else 0.0
    return float(distinctive_count) + float(median_z)


def compute_pair_scores(
    ticker: str,
    section: str,
    year_from: int,
    year_to: int,
    most_recent: bool,
) -> PairScores:
    warnings: list[str] = []

    prev = blo.load_section_text(ticker, year_from, section, "edgar", REPO_ROOT)
    curr = blo.load_section_text(ticker, year_to, section, "edgar", REPO_ROOT)

    if prev is None or curr is None:
        warnings.append("missing_text")
        return PairScores(
            year_from=year_from,
            year_to=year_to,
            boilerplate_score=0.0,
            structure_score=0.0,
            drift_score=0.0,
            term_signal_score=0.0,
            term_signal_norm=0.0,
            meaningful_score=0.0,
            overall_score=0.0,
            warnings=warnings,
            most_recent=most_recent,
        )

    lens_pair_deboiler = blo.build_lens_pair(prev, curr, "deboilerplated")
    if "fallback_to_raw" in lens_pair_deboiler.warnings:
        warnings.append("missing_lens")
    if "low_retained_text" in lens_pair_deboiler.warnings:
        warnings.append("low_retained_text")

    tokens_prev = blo.tokenize(prev.text)
    tokens_curr = blo.tokenize(curr.text)
    if len(tokens_prev) < 200 or len(tokens_curr) < 200:
        warnings.append("thin_counts")

    minhash_payload = load_lab_output(ticker, section, year_from, year_to, "det_minhash_boilerplate_v1")
    structure_payload = load_lab_output(ticker, section, year_from, year_to, "det_structure_artifacts_v1")
    jsd_payload = load_lab_output(ticker, section, year_from, year_to, "det_jsd_ngrams_v1")

    warnings.extend(extract_metric_warnings(minhash_payload))
    warnings.extend(extract_metric_warnings(structure_payload))
    warnings.extend(extract_metric_warnings(jsd_payload))

    boilerplate_score = extract_minhash_score(minhash_payload)
    if boilerplate_score is None:
        boilerplate_score = compute_boilerplate_proxy(prev.paragraphs, curr.paragraphs)

    structure_score = extract_metric_score(structure_payload)
    if structure_score is None:
        structure_score = compute_structure_proxy(prev.text, curr.text, prev.paragraphs, curr.paragraphs)

    drift_score = extract_metric_score(jsd_payload)
    if drift_score is None:
        drift_score = compute_jsd(tokens_prev, tokens_curr)

    term_entry = load_term_shift_entry(ticker, section, year_from, year_to)
    term_signal_score = compute_term_signal(term_entry, warnings)

    boilerplate_score = clamp01(boilerplate_score)
    structure_score = clamp01(structure_score)
    drift_score = max(0.0, drift_score)

    return PairScores(
        year_from=year_from,
        year_to=year_to,
        boilerplate_score=boilerplate_score,
        structure_score=structure_score,
        drift_score=drift_score,
        term_signal_score=term_signal_score,
        term_signal_norm=0.0,
        meaningful_score=0.0,
        overall_score=0.0,
        warnings=sorted(set(warnings)),
        most_recent=most_recent,
    )


def select_candidate(
    candidates: list[PairScores],
    key: Callable[[PairScores], float],
    exclude_pairs: set[tuple[int, int]],
    require_ok: bool = False,
) -> Optional[PairScores]:
    filtered: list[PairScores] = []
    for item in candidates:
        if (item.year_from, item.year_to) in exclude_pairs:
            continue
        if require_ok and "missing_text" in item.warnings:
            continue
        filtered.append(item)
    if not filtered:
        return None
    return max(filtered, key=key)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Select hero pairs for Narrative Drift Lab showcase.")
    parser.add_argument(
        "--roster",
        default=str(REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab" / "lab_showcase_roster_v2.json"),
        help="Roster JSON path",
    )
    parser.add_argument(
        "--out",
        default=str(REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab" / "lab_showcase_hero_pairs_v2.json"),
        help="Output hero pairs JSON",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    roster_path = Path(args.roster)
    if not roster_path.exists():
        raise SystemExit(f"Roster not found: {roster_path}")
    roster_payload = read_json(roster_path)
    roster_dict = as_str_dict(roster_payload)
    if roster_dict is None:
        raise SystemExit("Roster JSON invalid.")

    tickers = roster_dict.get("tickers")
    if not isinstance(tickers, list):
        raise SystemExit("Roster missing tickers.")
    tickers_list = cast(list[str], tickers)
    section = roster_dict.get("section")
    if not isinstance(section, str):
        raise SystemExit("Roster missing section.")

    pairs_per_ticker = roster_dict.get("pairs_per_ticker")
    if not isinstance(pairs_per_ticker, dict):
        raise SystemExit("Roster missing pairs_per_ticker.")
    pairs_per_ticker_dict = cast(dict[str, Any], pairs_per_ticker)

    hero_pairs_per_ticker: dict[str, list[dict[str, Any]]] = {}
    scoring_table: dict[str, list[dict[str, Any]]] = {}

    for ticker in tickers_list:
        pairs_raw = pairs_per_ticker_dict.get(ticker)
        if not isinstance(pairs_raw, list):
            continue
        pairs_raw_list = cast(list[Any], pairs_raw)
        pairs: list[tuple[int, int]] = []
        for entry in pairs_raw_list:
            entry_dict = as_str_dict(entry)
            if entry_dict is None:
                continue
            year_from = entry_dict.get("year_from")
            year_to = entry_dict.get("year_to")
            if isinstance(year_from, int) and isinstance(year_to, int):
                pairs.append((year_from, year_to))

        if not pairs:
            continue

        most_recent_pair = max(pairs, key=lambda item: (item[1], item[0]))

        pair_scores: list[PairScores] = []
        for year_from, year_to in pairs:
            most_recent = (year_from, year_to) == most_recent_pair
            pair_scores.append(
                compute_pair_scores(ticker, section, year_from, year_to, most_recent)
            )

        term_scores = [p.term_signal_score for p in pair_scores if p.term_signal_score > 0]
        if term_scores:
            min_term = min(term_scores)
            max_term = max(term_scores)
        else:
            min_term = 0.0
            max_term = 0.0

        normalized_scores: list[PairScores] = []
        for entry in pair_scores:
            if max_term > min_term:
                term_norm = (entry.term_signal_score - min_term) / (max_term - min_term)
            elif max_term > 0:
                term_norm = 1.0
            else:
                term_norm = 0.0

            meaningful = entry.drift_score * (1.0 - entry.boilerplate_score) * term_norm
            overall = 0.4 * meaningful + 0.3 * entry.structure_score + 0.3 * (1.0 - entry.boilerplate_score)
            normalized_scores.append(
                PairScores(
                    year_from=entry.year_from,
                    year_to=entry.year_to,
                    boilerplate_score=entry.boilerplate_score,
                    structure_score=entry.structure_score,
                    drift_score=entry.drift_score,
                    term_signal_score=entry.term_signal_score,
                    term_signal_norm=term_norm,
                    meaningful_score=meaningful,
                    overall_score=overall,
                    warnings=entry.warnings,
                    most_recent=entry.most_recent,
                )
            )

        selected_pairs: dict[tuple[int, int], list[str]] = {}
        selected_set: set[tuple[int, int]] = set()

        boilerplate_pick = select_candidate(
            normalized_scores,
            key=lambda item: item.boilerplate_score,
            exclude_pairs=selected_set,
            require_ok=True,
        )
        if boilerplate_pick is not None:
            pair_key = (boilerplate_pick.year_from, boilerplate_pick.year_to)
            selected_pairs.setdefault(pair_key, []).append("boilerplate")
            selected_set.add(pair_key)

        structure_pick = select_candidate(
            normalized_scores,
            key=lambda item: item.structure_score,
            exclude_pairs=selected_set,
            require_ok=True,
        )
        if structure_pick is not None:
            pair_key = (structure_pick.year_from, structure_pick.year_to)
            selected_pairs.setdefault(pair_key, []).append("structure")
            selected_set.add(pair_key)

        meaningful_candidates = [
            item
            for item in normalized_scores
            if "missing_text" not in item.warnings and "missing_term_shift" not in item.warnings
        ]
        meaningful_candidates = [
            item for item in meaningful_candidates if (item.year_from, item.year_to) not in selected_set
        ]
        if meaningful_candidates:
            meaningful_pick = max(meaningful_candidates, key=lambda item: item.meaningful_score)
            pair_key = (meaningful_pick.year_from, meaningful_pick.year_to)
            selected_pairs.setdefault(pair_key, []).append("meaningful")
            selected_set.add(pair_key)

        most_recent_pick = next(
            (item for item in normalized_scores if (item.year_from, item.year_to) == most_recent_pair),
            None,
        )
        if most_recent_pick is not None:
            pair_key = (most_recent_pick.year_from, most_recent_pick.year_to)
            selected_pairs.setdefault(pair_key, []).append("most_recent")
            selected_set.add(pair_key)

        if len(selected_set) < 3:
            remaining = [
                item for item in normalized_scores if (item.year_from, item.year_to) not in selected_set
            ]
            remaining.sort(key=lambda item: item.overall_score, reverse=True)
            for item in remaining:
                if len(selected_set) >= 3:
                    break
                pair_key = (item.year_from, item.year_to)
                selected_pairs.setdefault(pair_key, []).append("additional")
                selected_set.add(pair_key)

        if len(selected_set) > 5:
            sorted_selected = sorted(
                [item for item in normalized_scores if (item.year_from, item.year_to) in selected_set],
                key=lambda item: item.overall_score,
                reverse=True,
            )
            keep = set((item.year_from, item.year_to) for item in sorted_selected[:5])
            selected_pairs = {key: value for key, value in selected_pairs.items() if key in keep}
            selected_set = keep

        hero_output: list[dict[str, Any]] = []
        for item in normalized_scores:
            pair_key = (item.year_from, item.year_to)
            if pair_key not in selected_set:
                continue
            hero_output.append(
                {
                    "year_from": item.year_from,
                    "year_to": item.year_to,
                    "tags": selected_pairs.get(pair_key, []),
                    "scores": {
                        "boilerplate_score": round(item.boilerplate_score, 6),
                        "structure_score": round(item.structure_score, 6),
                        "drift_score": round(item.drift_score, 6),
                        "term_signal_score": round(item.term_signal_score, 6),
                        "meaningful_score": round(item.meaningful_score, 6),
                        "overall_score": round(item.overall_score, 6),
                    },
                    "warnings": item.warnings,
                }
            )

        hero_output.sort(key=lambda item: (item["year_from"], item["year_to"]))
        hero_pairs_per_ticker[ticker] = hero_output

        table_rows: list[dict[str, Any]] = []
        for item in normalized_scores:
            table_rows.append(
                {
                    "year_from": item.year_from,
                    "year_to": item.year_to,
                    "scores": {
                        "boilerplate_score": round(item.boilerplate_score, 6),
                        "structure_score": round(item.structure_score, 6),
                        "drift_score": round(item.drift_score, 6),
                        "term_signal_score": round(item.term_signal_score, 6),
                        "meaningful_score": round(item.meaningful_score, 6),
                        "overall_score": round(item.overall_score, 6),
                    },
                    "warnings": item.warnings,
                    "most_recent": item.most_recent,
                }
            )
        table_rows.sort(key=lambda item: (item["year_from"], item["year_to"]))
        scoring_table[ticker] = table_rows

    selection_rules = [
        "High boilerplate hero: max boilerplate_score, require no missing_text.",
        "Structure hero: max structure_score, require no missing_text.",
        "Meaningful hero: maximize drift_score * (1 - boilerplate_score) * term_signal_norm, exclude missing_text and missing_term_shift.",
        "Most recent hero: newest adjacent pair available (prefer 2024-2025 if present).",
        "Ensure at least 3 hero pairs per ticker; fill with highest overall_score.",
        "Cap hero pairs at 5 per ticker.",
        "Scores computed on raw lens; proxy metrics used when lab outputs missing.",
    ]

    out_payload = {
        "version": "2.0",
        "updated_at": now_utc_iso(),
        "section": section,
        "source_id": "edgar",
        "hero_pairs_per_ticker": hero_pairs_per_ticker,
        "full_scoring_table": scoring_table,
        "selection_rules": selection_rules,
        "provenance": {
            "build_utc": now_utc_iso(),
            "script_version": SCRIPT_VERSION,
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_payload, indent=2), encoding="utf-8")

    report_path = REPO_ROOT / "reports" / "showcase_hero_pairs_summary.md"
    report_lines: list[str] = []
    report_lines.append("# Showcase Hero Pairs Summary")
    report_lines.append("")
    report_lines.append(f"Generated: {now_utc_iso()}")
    report_lines.append("")

    for ticker, hero_pairs in hero_pairs_per_ticker.items():
        report_lines.append(f"## {ticker}")
        report_lines.append("")
        report_lines.append("### Hero selections")
        report_lines.append("")
        report_lines.append("| Pair | Tags | Boilerplate | Structure | Drift | Term signal | Warnings |")
        report_lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for hero in hero_pairs:
            pair_label = f"{hero['year_from']}-{hero['year_to']}"
            tags = ",".join(hero.get("tags", []))
            scores = hero.get("scores", {})
            warnings = ",".join(hero.get("warnings", []))
            report_lines.append(
                "| "
                + " | ".join(
                    [
                        pair_label,
                        tags,
                        f"{scores.get('boilerplate_score', 0):.3f}",
                        f"{scores.get('structure_score', 0):.3f}",
                        f"{scores.get('drift_score', 0):.3f}",
                        f"{scores.get('term_signal_score', 0):.3f}",
                        warnings or "-",
                    ]
                )
                + " |"
            )
        report_lines.append("")

    report_lines.append("# Coverage and Selection Transparency (No Cherry-Picking)")
    report_lines.append("")

    for ticker, rows in scoring_table.items():
        report_lines.append(f"## {ticker}")
        report_lines.append("")
        report_lines.append(
            "| Pair | selected_as_hero | hero_tags | boilerplate_score | structure_score | drift_score | term_signal_score | warnings_count | top_warning | most_recent_flag |"
        )
        report_lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")

        hero_map: dict[tuple[int, int], list[str]] = {
            (entry["year_from"], entry["year_to"]): cast(list[str], entry.get("tags", []))
            for entry in hero_pairs_per_ticker.get(ticker, [])
        }

        for entry in rows:
            pair_key = (entry["year_from"], entry["year_to"])
            scores = entry.get("scores", {})
            warnings = entry.get("warnings", [])
            warnings_list: list[str] = cast(list[str], warnings) if isinstance(warnings, list) else []
            selected = "yes" if pair_key in hero_map else "no"
            tags = ",".join(hero_map.get(pair_key, []))
            warnings_count = len(warnings_list)
            top_warning: str = warnings_list[0] if warnings_list else ""
            most_recent_flag = "yes" if entry.get("most_recent") else "no"
            report_lines.append(
                "| "
                + " | ".join(
                    [
                        f"{entry['year_from']}-{entry['year_to']}",
                        selected,
                        tags,
                        f"{scores.get('boilerplate_score', 0):.3f}",
                        f"{scores.get('structure_score', 0):.3f}",
                        f"{scores.get('drift_score', 0):.3f}",
                        f"{scores.get('term_signal_score', 0):.3f}",
                        str(warnings_count),
                        top_warning,
                        most_recent_flag,
                    ]
                )
                + " |"
            )

        total_pairs = len(rows)
        total_heroes = len(hero_pairs_per_ticker.get(ticker, []))
        tag_counts: Counter[str] = Counter()
        for tag_list in hero_map.values():
            for tag in tag_list:
                tag_counts[tag] += 1

        report_lines.append("")
        report_lines.append(
            f"Summary: total_pairs={total_pairs}, total_hero_pairs={total_heroes}, "
            f"hero_pairs_by_tag={dict(tag_counts)}"
        )

        missing_tags = [tag for tag in ("boilerplate", "structure", "meaningful", "most_recent") if tag_counts.get(tag, 0) == 0]
        if missing_tags:
            report_lines.append(
                f"Note: missing hero tags: {', '.join(missing_tags)} (insufficient candidates or warnings)."
            )
        report_lines.append("")

    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Wrote hero pairs to {out_path}")
    print(f"Wrote summary report to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
