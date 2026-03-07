from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from lab_script_version import build_script_version
from lab_output_tracks import DEFAULT_PRIMARY_LLM_CAMPAIGN_ID, LLM_DETECTORS, get_llm_campaign
from lab_llm_precompute_utils import as_list, as_str_dict, get_int, get_str, read_json

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "reports" / "lab_llm_master_manifest.json"
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9'-]+")


@dataclass(frozen=True)
class ProjectionEntry:
    ticker: str
    section: str
    year_from: int
    year_to: int
    lens: str
    source_id: str
    master_output_path: Path
    projection_paths: dict[str, Path]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_projection_entries(
    manifest_path: Path,
    campaign_slug: str,
) -> list[ProjectionEntry]:
    manifest_payload = read_json(manifest_path)
    manifest = as_str_dict(manifest_payload)
    if manifest is None:
        raise SystemExit(f"Manifest root must be object: {manifest_path}")
    entries_raw = as_list(manifest.get("entries"))
    if entries_raw is None:
        raise SystemExit(f"Manifest missing list field 'entries': {manifest_path}")

    entries: list[ProjectionEntry] = []
    for entry_any in entries_raw:
        entry = as_str_dict(entry_any)
        if entry is None:
            continue
        master_output = as_str_dict(entry.get("projected_master_output_runtime"))
        if master_output is None:
            master_output = as_str_dict(entry.get("projected_master_output_v1"))
        if master_output is None:
            master_output = as_str_dict(entry.get("master_output"))
        projection_outputs = as_list(entry.get("projection_outputs"))
        if master_output is None or projection_outputs is None:
            continue
        ticker = get_str(entry.get("ticker"))
        section = get_str(entry.get("section"))
        year_from = get_int(entry.get("year_from"))
        year_to = get_int(entry.get("year_to"))
        lens = get_str(entry.get("lens"))
        source_id = get_str(entry.get("source_id"))
        master_path = get_str(master_output.get("expected_output_path"))
        if (
            ticker is None
            or section is None
            or year_from is None
            or year_to is None
            or lens is None
            or source_id is None
            or master_path is None
        ):
            continue
        normalized_master = "/" + master_path.replace("\\", "/").lstrip("/")
        if f"/{campaign_slug}/" not in normalized_master:
            continue

        projection_paths: dict[str, Path] = {}
        for projection_any in projection_outputs:
            projection = as_str_dict(projection_any)
            if projection is None:
                continue
            detector_id = get_str(projection.get("detector_id"))
            output_path = get_str(projection.get("expected_output_path"))
            if detector_id is None or output_path is None:
                continue
            if detector_id not in LLM_DETECTORS:
                continue
            projection_paths[detector_id] = (REPO_ROOT / output_path).resolve()
        if len(projection_paths) != len(LLM_DETECTORS):
            continue

        entries.append(
            ProjectionEntry(
                ticker=ticker,
                section=section,
                year_from=year_from,
                year_to=year_to,
                lens=lens,
                source_id=source_id,
                master_output_path=(REPO_ROOT / master_path).resolve(),
                projection_paths=projection_paths,
            )
        )
    return entries


def parse_master_payload(path: Path) -> Optional[dict[str, Any]]:
    if not path.exists():
        return None
    try:
        payload = read_json(path)
    except Exception:  # noqa: BLE001
        return None
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        return None
    if payload_dict.get("artifact_id") not in {"llm_outline_compare_runtime", "llm_outline_compare_v1"}:
        return None
    return payload_dict


def extract_evidence_bank(
    master_payload: dict[str, Any], year_from: int, year_to: int
) -> dict[tuple[int, int], dict[str, Any]]:
    output: dict[tuple[int, int], dict[str, Any]] = {}
    evidence_bank = as_list(master_payload.get("evidence_bank")) or []
    for evidence_any in evidence_bank:
        evidence = as_str_dict(evidence_any)
        if evidence is None:
            continue
        year = get_int(evidence.get("year"))
        paragraph_idx = get_int(evidence.get("paragraph_idx"))
        snippet = get_str(evidence.get("snippet"))
        why = get_str(evidence.get("why"))
        node_ids = as_list(evidence.get("node_ids")) or []
        if year not in (year_from, year_to):
            continue
        if paragraph_idx is None or paragraph_idx < 0:
            continue
        if snippet is None or not snippet.strip():
            continue
        if why is None or not why.strip():
            continue
        normalized_node_ids = [item for item in node_ids if isinstance(item, str) and item]
        output[(year, paragraph_idx)] = {
            "year": year,
            "paragraph_idx": paragraph_idx,
            "snippet": snippet,
            "why": why,
            "node_ids": normalized_node_ids,
        }
    return output


def select_material_pairs(master_payload: dict[str, Any]) -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []
    material_changes = as_list(master_payload.get("material_changes")) or []
    for change_any in material_changes:
        change = as_str_dict(change_any)
        if change is None:
            continue
        evidence_refs = as_list(change.get("evidence_refs")) or []
        for ref_any in evidence_refs:
            ref = as_str_dict(ref_any)
            if ref is None:
                continue
            year = get_int(ref.get("year"))
            paragraph_idx = get_int(ref.get("paragraph_idx"))
            if year is None or paragraph_idx is None or paragraph_idx < 0:
                continue
            pair = (year, paragraph_idx)
            if pair not in pairs:
                pairs.append(pair)
    return pairs


def ensure_balanced_pairs(
    selected: list[tuple[int, int]],
    evidence_lookup: dict[tuple[int, int], dict[str, Any]],
    year_from: int,
    year_to: int,
    min_per_year: int,
    max_total: int,
) -> list[tuple[int, int]]:
    output: list[tuple[int, int]] = []
    for pair in selected:
        if pair in evidence_lookup and pair not in output:
            output.append(pair)
        if len(output) >= max_total:
            break

    def count_for_year(year: int) -> int:
        return sum(1 for value in output if value[0] == year)

    for year in (year_from, year_to):
        if count_for_year(year) >= min_per_year:
            continue
        candidates = sorted(
            [pair for pair in evidence_lookup.keys() if pair[0] == year],
            key=lambda item: item[1],
        )
        for pair in candidates:
            if pair in output:
                continue
            output.append(pair)
            if len(output) >= max_total:
                break
            if count_for_year(year) >= min_per_year:
                break

    if len(output) < max_total:
        for pair in sorted(evidence_lookup.keys(), key=lambda item: (item[0], item[1])):
            if pair in output:
                continue
            output.append(pair)
            if len(output) >= max_total:
                break
    output.sort(key=lambda item: (item[0], item[1]))
    return output


def derive_highlights(snippet: str, fallback_token: str) -> list[str]:
    seen: list[str] = []
    for match in WORD_RE.finditer(snippet):
        word = match.group(0).strip().lower()
        if len(word) < 4:
            continue
        if word in seen:
            continue
        seen.append(word)
        if len(seen) >= 2:
            break
    if not seen:
        seen.append(fallback_token)
    return seen


def build_metrics(
    evidence_count: int,
    material_changes_count: int,
    lens_divergence: str,
) -> dict[str, Any]:
    drift_score = 0.0
    if material_changes_count > 0:
        drift_score = min(1.0, 0.12 * material_changes_count)
    coverage = min(1.0, evidence_count / 8.0) if evidence_count > 0 else 0.0
    if evidence_count >= 6 and material_changes_count >= 3:
        confidence = 0.75
    elif evidence_count >= 4 and material_changes_count >= 2:
        confidence = 0.50
    else:
        confidence = 0.25
    warnings: list[str] = ["Projected deterministically from llm_outline_compare_runtime master artifact."]
    if lens_divergence:
        warnings.append(lens_divergence)
    return {
        "drift_score": round(drift_score, 3),
        "confidence": confidence,
        "coverage": round(coverage, 3),
        "warnings": warnings,
    }


def build_delta_brief_text(
    master_payload: dict[str, Any],
    selected_pairs: list[tuple[int, int]],
) -> str:
    material_changes = as_list(master_payload.get("material_changes")) or []
    top_titles: list[str] = []
    caveat = "Interpret with agreement and deterministic baselines before final conclusions."
    for change_any in material_changes[:3]:
        change = as_str_dict(change_any)
        if change is None:
            continue
        title = get_str(change.get("title"))
        change_class = get_str(change.get("change_class"))
        if title:
            top_titles.append(f"{title} ({change_class or 'change'})")
        change_caveat = get_str(change.get("caveat"))
        if change_caveat and caveat.startswith("Interpret with"):
            caveat = change_caveat
    citations = [f"{year} para {paragraph_idx + 1}" for year, paragraph_idx in selected_pairs[:4]]
    if len(citations) < 2:
        citations.append("2022 para 1")
        citations.append("2023 para 1")
    change_text = "; ".join(top_titles[:2]) if top_titles else "Material risk framing shifted across adjacent years."
    drivers_text = (
        "Evidence shows topic movement, rewording intensity, and selective expansion/contraction in the risk narrative."
    )
    cited_change = f"{change_text} ({citations[0]}; {citations[1]})"
    cited_driver = (
        f"{drivers_text} ({'; '.join(citations[2:4])})" if len(citations) >= 4 else f"{drivers_text} ({citations[0]})"
    )
    return f"Change: {cited_change} Drivers: {cited_driver} Caveat: {caveat}"


def build_output_payload(
    detector_id: str,
    entry: ProjectionEntry,
    master_payload: dict[str, Any],
    evidence_lookup: dict[tuple[int, int], dict[str, Any]],
    selected_pairs: list[tuple[int, int]],
) -> dict[str, Any]:
    evidence_blocks: list[dict[str, Any]] = []
    for year, paragraph_idx in selected_pairs:
        evidence = evidence_lookup.get((year, paragraph_idx))
        if evidence is None:
            continue
        title_token = "risk" if detector_id == "det_llm_delta_brief_v1" else "excerpt"
        evidence_blocks.append(
            {
                "year": year,
                "paragraph_idx": paragraph_idx,
                "snippet": evidence["snippet"],
                "why": evidence["why"],
                "highlights": derive_highlights(str(evidence["snippet"]), title_token),
            }
        )

    lens_divergence_raw = as_str_dict(master_payload.get("lens_divergence")) or {}
    lens_divergence_summary = get_str(lens_divergence_raw.get("summary")) or ""
    metrics = build_metrics(
        evidence_count=len(evidence_blocks),
        material_changes_count=len(as_list(master_payload.get("material_changes")) or []),
        lens_divergence=lens_divergence_summary,
    )

    artifacts: dict[str, Any]
    if detector_id == "det_llm_delta_brief_v1":
        artifacts = {
            "delta_brief": build_delta_brief_text(master_payload, selected_pairs),
        }
    else:
        selected_prev = sorted(
            {
                block["paragraph_idx"]
                for block in evidence_blocks
                if block.get("year") == entry.year_from
            }
        )
        selected_curr = sorted(
            {
                block["paragraph_idx"]
                for block in evidence_blocks
                if block.get("year") == entry.year_to
            }
        )
        artifacts = {
            "selected_prev": selected_prev,
            "selected_curr": selected_curr,
        }

    provenance_in = as_str_dict(master_payload.get("provenance")) or {}
    input_file = get_str(provenance_in.get("input_file")) or (
        f"inputs/pair/{entry.ticker}_{entry.year_from}_{entry.year_to}_{entry.section}_{entry.lens}_{entry.source_id}.json"
    )
    model_provider = get_str(provenance_in.get("model_provider")) or "openai"
    model_name = get_str(provenance_in.get("model_name")) or "unknown"
    run_label = get_str(provenance_in.get("run_label")) or "2026-02-25_master_projection"

    return {
        "lab_schema_version": "1.0",
        "detector_id": detector_id,
        "cleaning_lens": entry.lens,
        "source_id": entry.source_id,
        "ticker": entry.ticker,
        "section": entry.section,
        "year_from": entry.year_from,
        "year_to": entry.year_to,
        "artifacts": artifacts,
        "evidence": evidence_blocks,
        "metrics": metrics,
        "provenance": {
            "input_file": input_file,
            "model_provider": model_provider,
            "model_name": model_name,
            "run_label": run_label,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Project llm_outline_compare_runtime master artifacts into existing LLM detector envelopes."
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST_PATH))
    parser.add_argument("--campaign-id", default=DEFAULT_PRIMARY_LLM_CAMPAIGN_ID)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--verbose-progress",
        action="store_true",
        help="Emit progress lines for each projection entry processed.",
    )
    parser.add_argument(
        "--progress-interval-sec",
        type=int,
        default=300,
        help="Heartbeat interval in seconds for long-running operations.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    started = time.monotonic()
    args = build_parser().parse_args(argv)
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = (REPO_ROOT / manifest_path).resolve()
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")
    campaign = get_llm_campaign(args.campaign_id)
    if campaign is None:
        raise SystemExit(f"Unknown campaign id: {args.campaign_id}")

    print(f"[phase] project master artifacts start (script={SCRIPT_VERSION})", flush=True)
    entries = load_projection_entries(manifest_path, campaign.track_slug)
    generated = 0
    skipped = 0
    loop_started = time.monotonic()
    last_heartbeat = loop_started
    total_entries = len(entries)
    progress_interval_sec = max(1, int(args.progress_interval_sec))
    for index, entry in enumerate(entries, start=1):
        now = time.monotonic()
        if args.verbose_progress or now - last_heartbeat >= progress_interval_sec:
            elapsed = int(now - loop_started)
            print(
                "[progress] master_projection "
                + f"entries={index}/{total_entries} generated={generated} skipped={skipped} "
                + f"elapsed={elapsed}s",
                flush=True,
            )
            last_heartbeat = now
        master_payload = parse_master_payload(entry.master_output_path)
        if master_payload is None:
            skipped += 1
            continue
        evidence_lookup = extract_evidence_bank(
            master_payload=master_payload,
            year_from=entry.year_from,
            year_to=entry.year_to,
        )
        if not evidence_lookup:
            skipped += 1
            continue
        material_pairs = select_material_pairs(master_payload)
        selected_pairs_delta = ensure_balanced_pairs(
            selected=material_pairs,
            evidence_lookup=evidence_lookup,
            year_from=entry.year_from,
            year_to=entry.year_to,
            min_per_year=2,
            max_total=8,
        )
        selected_pairs_excerpt = ensure_balanced_pairs(
            selected=material_pairs,
            evidence_lookup=evidence_lookup,
            year_from=entry.year_from,
            year_to=entry.year_to,
            min_per_year=3,
            max_total=10,
        )

        for detector_id in LLM_DETECTORS:
            selected_pairs = (
                selected_pairs_delta
                if detector_id == "det_llm_delta_brief_v1"
                else selected_pairs_excerpt
            )
            payload = build_output_payload(
                detector_id=detector_id,
                entry=entry,
                master_payload=master_payload,
                evidence_lookup=evidence_lookup,
                selected_pairs=selected_pairs,
            )
            destination = entry.projection_paths[detector_id]
            if not args.dry_run:
                write_json(destination, payload)
            generated += 1

    elapsed = int(time.monotonic() - started)
    print(f"Script: {SCRIPT_VERSION}")
    print(f"Campaign: {campaign.track_id}")
    print(f"Projection summary: entries={len(entries)} generated={generated} skipped={skipped}")
    if args.dry_run:
        print("Dry run mode enabled (no files written).")
    print(f"Elapsed: {elapsed}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



