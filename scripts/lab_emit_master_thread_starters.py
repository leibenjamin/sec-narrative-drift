from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any, Optional, cast

from lab_script_version import build_script_version
from lab_output_tracks import get_llm_campaign

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "reports" / "lab_llm_master_manifest.json"
DEFAULT_OUT = REPO_ROOT / "reports" / "lab_llm_master_thread_starters.md"
DEFAULT_VALIDATION_REPORT = REPO_ROOT / "reports" / "lab_llm_master_validation.md"
DEFAULT_QUALITY_REPORT = REPO_ROOT / "reports" / "lab_llm_master_quality.md"
DEFAULT_BATCH_PROGRESS_REPORT = REPO_ROOT / "reports" / "lab_llm_master_batch_progress.md"
DEFAULT_BATCH_PROGRESS_JSON = REPO_ROOT / "reports" / "lab_llm_master_batch_progress.json"
PROMPT_SYSTEM_PATH = REPO_ROOT / "docs" / "lab" / "llm_master_compare_v3_system.md"
PROMPT_USER_TEMPLATE_PATH = REPO_ROOT / "docs" / "lab" / "llm_master_compare_v3_user_template.md"
PROMPT_SELF_CHECK_PATH = REPO_ROOT / "docs" / "lab" / "llm_master_compare_v3_self_check.md"

OUTPUT_SHAPE_MIN = {
    "lab_schema_version": "1.0",
    "artifact_schema_version": "1.0",
    "artifact_id": "llm_outline_compare_v2",
    "ticker": "<ticker>",
    "section": "10k_item1a",
    "source_id": "edgar",
    "cleaning_lens": "<raw|deboilerplated>",
    "year_from": 2022,
    "year_to": 2023,
    "outline_prev": [
        {
            "node_id": "prev_root",
            "parent_id": None,
            "level": 1,
            "order": 0,
            "label": "...",
            "risk_thesis": "...",
            "evidence_paragraph_idx": [0],
        }
    ],
    "outline_curr": [
        {
            "node_id": "curr_root",
            "parent_id": None,
            "level": 1,
            "order": 0,
            "label": "...",
            "risk_thesis": "...",
            "evidence_paragraph_idx": [0],
        }
    ],
    "node_alignment": [
        {
            "prev_node_id": "prev_root",
            "curr_node_id": "curr_root",
            "change_class": "stable",
            "rationale": "...",
            "salience": 0.5,
        }
    ],
    "material_changes": [
        {
            "id": "mc_1",
            "title": "...",
            "change_class": "reworded",
            "salience": 0.7,
            "caveat": "...",
            "evidence_refs": [{"year": 2022, "paragraph_idx": 0}, {"year": 2023, "paragraph_idx": 0}],
        }
    ],
    "evidence_bank": [
        {
            "year": 2022,
            "paragraph_idx": 0,
            "snippet": "...",
            "why": "...",
            "node_ids": ["prev_root"],
        }
    ],
    "lens_divergence": {"materially_different": False, "summary": "..."},
    "risk_graph_prev": [
        {
            "id": "rg_prev_1",
            "driver": "...",
            "exposure": "...",
            "impact": "...",
            "evidence_paragraph_idx": [0],
        }
    ],
    "risk_graph_curr": [
        {
            "id": "rg_curr_1",
            "driver": "...",
            "exposure": "...",
            "impact": "...",
            "evidence_paragraph_idx": [0],
        }
    ],
    "change_mechanisms": [
        {
            "id": "mech_1",
            "mechanism": "...",
            "transmission_channel": "...",
            "business_effect": "...",
            "time_horizon": "near_term",
            "evidence_refs": [{"year": 2022, "paragraph_idx": 0}, {"year": 2023, "paragraph_idx": 0}],
        }
    ],
    "uncertainty_and_limits": [
        {
            "id": "limit_1",
            "limitation": "...",
            "evidence_refs": [{"year": 2022, "paragraph_idx": 0}],
        }
    ],
    "investor_relevance": [
        {
            "id": "inv_1",
            "why_it_matters": "...",
            "evidence_refs": [{"year": 2023, "paragraph_idx": 0}],
        }
    ],
    "projection_contract": {
        "projects_to_artifact_id": "llm_outline_compare_v1",
        "projection_version": "1.0",
    },
    "provenance": {
        "input_file": "inputs/pair/<pair_basename>.json",
        "model_provider": "<model_provider>",
        "model_name": "<model_name>",
        "run_label": "YYYY-MM-DD_<campaign_tag>",
    },
}


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


def workspace_display(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def resolve_from_manifest(
    raw_path: str,
    *,
    bundle_root: Optional[Path],
    pair_abs_path: Optional[Path],
) -> str:
    if not raw_path:
        return ""
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return workspace_display(candidate)
    direct = (REPO_ROOT / candidate).resolve()
    if direct.exists():
        return workspace_display(direct)
    if bundle_root is not None:
        via_bundle = (bundle_root / candidate).resolve()
        if via_bundle.exists():
            return workspace_display(via_bundle)
    if pair_abs_path is not None:
        try:
            pair_bundle_root = pair_abs_path.parents[2]
            via_pair_root = (pair_bundle_root / candidate).resolve()
            if via_pair_root.exists():
                return workspace_display(via_pair_root)
        except IndexError:
            pass
    # fallback to a path-like value so the operator can still diagnose quickly
    return candidate.as_posix()


def emit_prompt_block(lines: list[str], title: str, block: str) -> None:
    lines.append(title)
    for raw in block.splitlines():
        lines.append(raw.rstrip())


def extract_year_paragraph_count(path_like: str) -> Optional[int]:
    path = Path(path_like)
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    if not path.exists():
        return None
    try:
        payload = read_json(path)
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(payload, dict):
        return None
    sec_data = cast(dict[str, Any], payload)
    texts = sec_data.get("texts")
    if not isinstance(texts, dict):
        return None
    text_data = cast(dict[str, Any], texts)
    paragraphs = text_data.get("paragraphs", [])
    if not isinstance(paragraphs, list):
        return None
    return len(cast(list[Any], paragraphs))


def build_run_label_template(campaign_id: str, ticker: str, year_from: object, year_to: object) -> str:
    campaign_tag = campaign_id
    if re.fullmatch(r".+_20\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])", campaign_id):
        campaign_tag = campaign_id.rsplit("_", 1)[0]
    return (
        f"YYYY-MM-DD_{campaign_tag}_{str(ticker).lower()}_"
        + f"{year_from}_{year_to}_outline_compare"
    )


def emit_batch_checkpoint_block(
    *,
    lines: list[str],
    completed_jobs: int,
    total_jobs: int,
    manifest_path: str,
    campaign_id: str,
    validation_report: str,
    quality_report: str,
    progress_md: str,
    progress_json: str,
) -> None:
    lines.append(f"### Batch Checkpoint After Job {completed_jobs:02d}")
    lines.append(
        "Run these commands before starting the next job block "
        + f"({completed_jobs}/{total_jobs} complete):"
    )
    lines.append("```bash")
    lines.append(
        f'python scripts/lab_validate_llm_master_outputs.py --manifest "{manifest_path}" --campaign-id "{campaign_id}" --allow-missing --allow-invalid --report "{validation_report}"'
    )
    lines.append(
        f'python scripts/lab_audit_master_output_quality.py --manifest "{manifest_path}" --campaign-id "{campaign_id}" --allow-missing --mode blockers --report "{quality_report}"'
    )
    lines.append(
        "python scripts/lab_record_master_progress.py "
        + f'--manifest "{manifest_path}" '
        + f'--campaign-id "{campaign_id}" '
        + f'--report-md "{progress_md}" '
        + f'--history-json "{progress_json}" '
        + f'--label "after_job_{completed_jobs:02d}"'
    )
    lines.append("```")
    lines.append("")


def build_json_parse_command(output_path: str) -> str:
    normalized = output_path.replace("\\", "/")
    escaped = normalized.replace("'", "\\'")
    command = (
        "import json, pathlib; "
        + f"json.loads(pathlib.Path(r'{escaped}').read_text(encoding='utf-8-sig')); "
        + "print('JSON_OK')"
    )
    return f'python -c "{command}"'


def build_integrity_precheck_command(
    *,
    ticker: str,
    year_from: object,
    year_to: object,
    lens: str,
    section: str,
    source_id: str,
    pair_path: str,
    prev_path: str,
    curr_path: str,
    expected_prev_paragraphs: Optional[int],
    expected_curr_paragraphs: Optional[int],
    expected_pair_sha256: str,
    expected_prev_sha256: str,
    expected_curr_sha256: str,
) -> str:
    pair_norm = pair_path.replace("\\", "/")
    prev_norm = prev_path.replace("\\", "/")
    curr_norm = curr_path.replace("\\", "/")
    expected_prev_ref = f"inputs/year/{ticker}_{year_from}_{section}_{lens}_{source_id}__pair_{year_from}_{year_to}.json"
    expected_curr_ref = f"inputs/year/{ticker}_{year_to}_{section}_{lens}_{source_id}__pair_{year_from}_{year_to}.json"
    command = (
        "import json, pathlib, sys, hashlib; "
        f"ticker={ticker!r}; year_from={year_from!r}; year_to={year_to!r}; lens={lens!r}; section={section!r}; source_id={source_id!r}; "
        f"pair_path=pathlib.Path(r'{pair_norm}'); prev_path=pathlib.Path(r'{prev_norm}'); curr_path=pathlib.Path(r'{curr_norm}'); "
        f"exp_prev={int(expected_prev_paragraphs or -1)}; exp_curr={int(expected_curr_paragraphs or -1)}; "
        f"exp_pair_sha={expected_pair_sha256!r}; exp_prev_sha={expected_prev_sha256!r}; exp_curr_sha={expected_curr_sha256!r}; "
        f"exp_prev_ref={expected_prev_ref!r}; exp_curr_ref={expected_curr_ref!r}; "
        "pair=json.loads(pair_path.read_text(encoding='utf-8-sig')); prev=json.loads(prev_path.read_text(encoding='utf-8-sig')); curr=json.loads(curr_path.read_text(encoding='utf-8-sig')); "
        "errs=[]; "
        "case=pair.get('case') if isinstance(pair, dict) and isinstance(pair.get('case'), dict) else None; "
        "lens_obj=pair.get('lens') if isinstance(pair, dict) and isinstance(pair.get('lens'), dict) else None; "
        "year_inputs=pair.get('year_inputs') if isinstance(pair, dict) and isinstance(pair.get('year_inputs'), dict) else None; "
        "prev_t=prev.get('texts') if isinstance(prev, dict) and isinstance(prev.get('texts'), dict) else None; "
        "curr_t=curr.get('texts') if isinstance(curr, dict) and isinstance(curr.get('texts'), dict) else None; "
        "prev_p=prev_t.get('paragraphs') if isinstance(prev_t, dict) and isinstance(prev_t.get('paragraphs'), list) else None; "
        "curr_p=curr_t.get('paragraphs') if isinstance(curr_t, dict) and isinstance(curr_t.get('paragraphs'), list) else None; "
        "prev_n=len(prev_p) if isinstance(prev_p, list) else -1; curr_n=len(curr_p) if isinstance(curr_p, list) else -1; "
        "pair_sha=hashlib.sha256(pair_path.read_bytes()).hexdigest(); prev_sha=hashlib.sha256(prev_path.read_bytes()).hexdigest(); curr_sha=hashlib.sha256(curr_path.read_bytes()).hexdigest(); "
        "errs.append('pair_schema_version_mismatch') if not (isinstance(pair, dict) and pair.get('schema_version')=='2.0') else None; "
        "errs.append('pair_input_mode_mismatch') if not (isinstance(pair, dict) and pair.get('input_mode')=='full_section_v2') else None; "
        "errs.append('pair_case_missing') if case is None else None; "
        "errs.append('pair_case_ticker_mismatch') if isinstance(case, dict) and case.get('ticker')!=ticker else None; "
        "errs.append('pair_case_section_mismatch') if isinstance(case, dict) and case.get('section')!=section else None; "
        "errs.append('pair_case_year_from_mismatch') if isinstance(case, dict) and case.get('year_from')!=year_from else None; "
        "errs.append('pair_case_year_to_mismatch') if isinstance(case, dict) and case.get('year_to')!=year_to else None; "
        "errs.append('pair_case_source_id_mismatch') if isinstance(case, dict) and case.get('source_id')!=source_id else None; "
        "errs.append('pair_lens_name_mismatch') if not (isinstance(lens_obj, dict) and lens_obj.get('name')==lens) else None; "
        "errs.append('pair_year_inputs_prev_mismatch') if not (isinstance(year_inputs, dict) and year_inputs.get('prev')==exp_prev_ref) else None; "
        "errs.append('pair_year_inputs_curr_mismatch') if not (isinstance(year_inputs, dict) and year_inputs.get('curr')==exp_curr_ref) else None; "
        "errs.append(f'prev_count_mismatch:{prev_n}/{exp_prev}') if prev_n!=exp_prev else None; "
        "errs.append(f'curr_count_mismatch:{curr_n}/{exp_curr}') if curr_n!=exp_curr else None; "
        "errs.append('pair_sha_mismatch') if pair_sha!=exp_pair_sha else None; "
        "errs.append('prev_sha_mismatch') if prev_sha!=exp_prev_sha else None; "
        "errs.append('curr_sha_mismatch') if curr_sha!=exp_curr_sha else None; "
        "print('PRECHECK_FAIL', ';'.join([e for e in errs if isinstance(e, str) and e])) if any(errs) else None; "
        "sys.exit(2) if any(errs) else None; "
        "print(f'PRECHECK_MATCH prev={prev_n}/{exp_prev} curr={curr_n}/{exp_curr} pair_sha={pair_sha[:12]} prev_sha={prev_sha[:12]} curr_sha={curr_sha[:12]}')"
    )
    return f'python -c "{command}"'


def emit_legacy_block(
    *,
    lines: list[str],
    ticker: str,
    year_from: object,
    year_to: object,
    lens: str,
    section: str,
    source_id: str,
    pair_path: str,
    prev_path: str,
    curr_path: str,
    output_path: str,
    canonical_input_file: str,
    system_block: str,
    user_template: str,
    self_check: str,
) -> None:
    lines.append(f"## {ticker} {year_from}-{year_to} {lens}")
    lines.append("")
    lines.append("```text")
    lines.append(f"Thread title: {ticker} {year_from}-{year_to} outline compare ({lens})")
    lines.append(f"Read this input file from workspace: {pair_path}")
    if prev_path:
        lines.append(f"Read this input file from workspace: {prev_path}")
    if curr_path:
        lines.append(f"Read this input file from workspace: {curr_path}")
    lines.append(f"Save output to: {output_path}")
    lines.append("")
    lines.append(
        f"Case context: ticker={ticker}, pair={year_from}-{year_to}, section={section}, lens={lens}, source={source_id}"
    )
    lines.append(f"Canonical provenance.input_file: {canonical_input_file}")
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
    lines.append("- provenance.input_file must use canonical `inputs/pair/<basename>.json`.")
    lines.append("- Evidence paragraph indices must map to full-year paragraph arrays.")
    lines.append("- Do not include markdown or commentary outside JSON.")
    lines.append("```")
    lines.append("")


def emit_vscode_autowrite_block(
    *,
    lines: list[str],
    job_number: int,
    ticker: str,
    year_from: object,
    year_to: object,
    lens: str,
    section: str,
    source_id: str,
    pair_path: str,
    prev_path: str,
    curr_path: str,
    output_path: str,
    canonical_input_file: str,
    manifest_path: str,
    campaign_id: str,
    validation_report: str,
    quality_report: str,
    only_token: str,
    system_block: str,
    user_template: str,
    self_check: str,
) -> None:
    lines.append(f"## Job {job_number:02d} - {ticker} {year_from}-{year_to} {lens}")
    lines.append("COPY FROM NEXT LINE THROUGH END_STARTER AND PASTE INTO A FRESH CODEX THREAD:")
    lines.append("BEGIN_STARTER")
    lines.append("You are Codex operating inside this workspace. Execute this job end-to-end.")
    lines.append("Do not ask for manual file attachments or manual save steps.")
    lines.append("")
    lines.append("Execution mode: AUTOWRITE_VALIDATE")
    lines.append(f"Thread title: {ticker} {year_from}-{year_to} outline compare ({lens})")
    lines.append(
        f"Case context: ticker={ticker}, pair={year_from}-{year_to}, section={section}, lens={lens}, source={source_id}"
    )
    lines.append("")
    lines.append("1) Read and parse these workspace JSON files:")
    lines.append(f"- Pair manifest: {pair_path}")
    lines.append(f"- Year prev: {prev_path}")
    lines.append(f"- Year curr: {curr_path}")
    lines.append("")
    lines.append("2) Preflight checks before generation:")
    lines.append("- Fail hard if any file is missing/unreadable or invalid JSON.")
    lines.append("- Compute prev/curr paragraph counts from year files.")
    lines.append("- Print exactly one preflight line:")
    lines.append(
        f"PRECHECK_OK ticker={ticker} pair={year_from}-{year_to} lens={lens} provenance_input_file={canonical_input_file} prev_paragraphs=<N> curr_paragraphs=<N>"
    )
    lines.append("")
    lines.append("3) Generate exactly one JSON object for `llm_outline_compare_v1` using the prompt contract below.")
    emit_prompt_block(lines, "SYSTEM PROMPT", system_block)
    lines.append("")
    emit_prompt_block(lines, "USER PROMPT TEMPLATE", user_template)
    lines.append("")
    emit_prompt_block(lines, "SELF-CHECK GATE (must pass before final JSON)", self_check)
    lines.append("")
    lines.append("4) Hard failure policy:")
    lines.append("- If schema requirements cannot be satisfied, do not fabricate data.")
    lines.append('- Return exactly: {"error":"HARD_FAILURE","reason":"<short reason>"}')
    lines.append("- Never paraphrase snippets in evidence; use contiguous verbatim substrings only.")
    lines.append("")
    lines.append("5) Write output JSON directly to this path:")
    lines.append(f"- {output_path}")
    lines.append("")
    lines.append("6) Run immediate checks exactly:")
    lines.append(f"- {build_json_parse_command(output_path)}")
    lines.append(
        f'- python scripts/lab_validate_llm_master_outputs.py --manifest "{manifest_path}" --campaign-id "{campaign_id}" --allow-missing --allow-invalid --only "{only_token}" --only-mode "exact_path" --expect-target-count 1 --fail-if-target-count-mismatch --report "{validation_report}"'
    )
    lines.append(
        f'- python scripts/lab_audit_master_output_quality.py --output "{output_path}" --mode blockers --report "{quality_report}"'
    )
    lines.append("")
    lines.append("7) Print exactly one final status line:")
    lines.append("- Success: WRITE_OK JSON_OK VALIDATION_OK")
    lines.append("- Failure: FAILED: <short reason list>")
    lines.append("END_STARTER")
    lines.append("")


def emit_vscode_autowrite_v2_block(
    *,
    lines: list[str],
    job_number: int,
    ticker: str,
    year_from: object,
    year_to: object,
    lens: str,
    section: str,
    source_id: str,
    pair_path: str,
    prev_path: str,
    curr_path: str,
    output_path: str,
    canonical_input_file: str,
    manifest_path: str,
    campaign_id: str,
    validation_report: str,
    quality_report: str,
    only_token: str,
    system_block: str,
    user_template: str,
    self_check: str,
    model_provider: str,
    model_name: str,
    run_label_template: str,
    expected_prev_paragraphs: Optional[int],
    expected_curr_paragraphs: Optional[int],
) -> None:
    lines.append(f"## Job {job_number:02d} - {ticker} {year_from}-{year_to} {lens}")
    lines.append("COPY FROM NEXT LINE THROUGH END_STARTER AND PASTE INTO A FRESH CODEX THREAD:")
    lines.append("BEGIN_STARTER")
    lines.append("You are Codex operating inside this workspace. Execute this job end-to-end.")
    lines.append("Do not ask for manual file attachments or manual save steps.")
    lines.append(
        "Execution focus: do not inspect unrelated scripts/docs unless a required gate fails."
    )
    lines.append("")
    lines.append("Execution mode: AUTOWRITE_VALIDATE")
    lines.append(f"Thread title: {ticker} {year_from}-{year_to} outline compare ({lens})")
    lines.append(
        f"Case context: ticker={ticker}, pair={year_from}-{year_to}, section={section}, lens={lens}, source={source_id}"
    )
    lines.append("")
    lines.append("JOB_META")
    lines.append(
        json.dumps(
            {
                "job_id": f"{ticker}_{year_from}_{year_to}_{lens}_{source_id}",
                "model_provider": model_provider,
                "model_name": model_name,
                "run_label_template": run_label_template,
                "provenance_input_file": canonical_input_file,
                "expected_prev_paragraphs": expected_prev_paragraphs,
                "expected_curr_paragraphs": expected_curr_paragraphs,
                "output_path": output_path,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    lines.append("")
    lines.append("OUTPUT_SHAPE_MIN")
    lines.append(json.dumps(OUTPUT_SHAPE_MIN, indent=2, ensure_ascii=False))
    lines.append("")
    lines.append("1) Read and parse these workspace JSON files:")
    lines.append(f"- Pair manifest: {pair_path}")
    lines.append(f"- Year prev: {prev_path}")
    lines.append(f"- Year curr: {curr_path}")
    lines.append("")
    lines.append("2) Preflight checks before generation:")
    lines.append("- Fail hard if any file is missing/unreadable or invalid JSON.")
    lines.append("- Compute prev/curr paragraph counts from year files.")
    if expected_prev_paragraphs is not None and expected_curr_paragraphs is not None:
        lines.append(
            "- Expected counts from bundle indexing: "
            + f"prev={expected_prev_paragraphs}, curr={expected_curr_paragraphs}."
        )
    lines.append("- Print exactly one preflight line:")
    lines.append(
        f"PRECHECK_OK ticker={ticker} pair={year_from}-{year_to} lens={lens} provenance_input_file={canonical_input_file} prev_paragraphs=<N> curr_paragraphs=<N>"
    )
    lines.append("")
    lines.append("3) Generate exactly one JSON object for `llm_outline_compare_v1` using the prompt contract below.")
    emit_prompt_block(lines, "SYSTEM PROMPT", system_block)
    lines.append("")
    emit_prompt_block(lines, "USER PROMPT TEMPLATE", user_template)
    lines.append("")
    emit_prompt_block(lines, "SELF-CHECK GATE (must pass before final JSON)", self_check)
    lines.append("")
    lines.append("4) Hard failure policy:")
    lines.append("- If schema requirements cannot be satisfied, do not fabricate data.")
    lines.append('- Return exactly: {"error":"HARD_FAILURE","reason":"<short reason>"}')
    lines.append("- Never paraphrase snippets in evidence; use contiguous verbatim substrings only.")
    lines.append("")
    lines.append("5) Write output JSON directly to this path:")
    lines.append(f"- {output_path}")
    lines.append("")
    lines.append("6) Run immediate checks exactly:")
    lines.append(f"- {build_json_parse_command(output_path)}")
    lines.append(
        f'- python scripts/lab_validate_llm_master_outputs.py --manifest "{manifest_path}" --campaign-id "{campaign_id}" --allow-missing --allow-invalid --only "{only_token}" --only-mode "exact_path" --expect-target-count 1 --fail-if-target-count-mismatch --report "{validation_report}"'
    )
    lines.append(
        f'- python scripts/lab_audit_master_output_quality.py --output "{output_path}" --mode blockers --report "{quality_report}"'
    )
    lines.append(
        "- Note: validator present_flag_mismatch can be non-blocking during incremental manual runs."
    )
    lines.append("")
    lines.append("7) Print exactly one final status line:")
    lines.append("- Success: WRITE_OK JSON_OK VALIDATION_OK")
    lines.append("- Failure: FAILED: <short reason list>")
    lines.append("END_STARTER")
    lines.append("")


def emit_vscode_autowrite_v3_block(
    *,
    lines: list[str],
    job_number: int,
    ticker: str,
    year_from: object,
    year_to: object,
    lens: str,
    section: str,
    source_id: str,
    pair_path: str,
    prev_path: str,
    curr_path: str,
    output_path: str,
    canonical_input_file: str,
    manifest_path: str,
    campaign_id: str,
    validation_report: str,
    quality_report: str,
    only_token: str,
    system_block: str,
    user_template: str,
    self_check: str,
    model_provider: str,
    model_name: str,
    run_label_template: str,
    expected_prev_paragraphs: Optional[int],
    expected_curr_paragraphs: Optional[int],
) -> None:
    lines.append(f"## Job {job_number:02d} - {ticker} {year_from}-{year_to} {lens}")
    lines.append("COPY FROM NEXT LINE THROUGH END_STARTER AND PASTE INTO A FRESH CODEX THREAD:")
    lines.append("BEGIN_STARTER")
    lines.append("You are Codex operating inside this workspace. Execute this job end-to-end.")
    lines.append("Do not ask for manual file attachments or manual save steps.")
    lines.append(
        "Execution focus: do not inspect unrelated scripts/docs unless a required gate fails."
    )
    lines.append("")
    lines.append("Execution mode: AUTOWRITE_VALIDATE")
    lines.append(f"Thread title: {ticker} {year_from}-{year_to} outline compare ({lens})")
    lines.append(
        f"Case context: ticker={ticker}, pair={year_from}-{year_to}, section={section}, lens={lens}, source={source_id}"
    )
    lines.append("")
    lines.append("JOB_META")
    lines.append(
        json.dumps(
            {
                "job_id": f"{ticker}_{year_from}_{year_to}_{lens}_{source_id}",
                "model_provider": model_provider,
                "model_name": model_name,
                "run_label_template": run_label_template,
                "provenance_input_file": canonical_input_file,
                "expected_prev_paragraphs": expected_prev_paragraphs,
                "expected_curr_paragraphs": expected_curr_paragraphs,
                "output_path": output_path,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    lines.append("")
    lines.append("OUTPUT_SHAPE_MIN")
    lines.append(json.dumps(OUTPUT_SHAPE_MIN, indent=2, ensure_ascii=False))
    lines.append("")
    lines.append("1) Read and parse these workspace JSON files:")
    lines.append(f"- Pair manifest: {pair_path}")
    lines.append(f"- Year prev: {prev_path}")
    lines.append(f"- Year curr: {curr_path}")
    lines.append("")
    lines.append("2) Preflight checks before generation:")
    lines.append("- Fail hard if any file is missing/unreadable or invalid JSON.")
    lines.append(
        "- Compute prev/curr paragraph counts from `year_payload.texts.paragraphs` (not top-level `paragraphs`)."
    )
    lines.append("- Run extraction templates exactly with the two year files:")
    lines.append(
        '- python -c "import json, pathlib; d=json.loads(pathlib.Path(r\''
        + prev_path.replace("\\", "/")
        + '\').read_text(encoding=\'utf-8-sig\')); t=d.get(\'texts\'); p=t.get(\'paragraphs\') if isinstance(t, dict) else None; print(\'PREV_COUNT\', len(p) if isinstance(p, list) else \'INVALID\')"'
    )
    lines.append(
        '- python -c "import json, pathlib; d=json.loads(pathlib.Path(r\''
        + curr_path.replace("\\", "/")
        + '\').read_text(encoding=\'utf-8-sig\')); t=d.get(\'texts\'); p=t.get(\'paragraphs\') if isinstance(t, dict) else None; print(\'CURR_COUNT\', len(p) if isinstance(p, list) else \'INVALID\')"'
    )
    if expected_prev_paragraphs is not None and expected_curr_paragraphs is not None:
        lines.append(
            "- Expected counts from bundle indexing: "
            + f"prev={expected_prev_paragraphs}, curr={expected_curr_paragraphs}."
        )
        lines.append(
            '- python -c "import json, pathlib, sys;'
            + f" exp_prev={expected_prev_paragraphs}; exp_curr={expected_curr_paragraphs};"
            + " prev=json.loads(pathlib.Path(r'"
            + prev_path.replace("\\", "/")
            + "').read_text(encoding='utf-8-sig'));"
            + " curr=json.loads(pathlib.Path(r'"
            + curr_path.replace("\\", "/")
            + "').read_text(encoding='utf-8-sig'));"
            + " prev_t=prev.get('texts'); curr_t=curr.get('texts');"
            + " prev_p=prev_t.get('paragraphs') if isinstance(prev_t, dict) else None;"
            + " curr_p=curr_t.get('paragraphs') if isinstance(curr_t, dict) else None;"
            + " prev_n=len(prev_p) if isinstance(prev_p, list) else -1;"
            + " curr_n=len(curr_p) if isinstance(curr_p, list) else -1;"
            + " print(f'PRECHECK_MATCH prev={prev_n}/{exp_prev} curr={curr_n}/{exp_curr}');"
            + " sys.exit(0 if prev_n==exp_prev and curr_n==exp_curr else 2)\""
        )
    else:
        lines.append(
            "- If `JOB_META.expected_prev_paragraphs` or `JOB_META.expected_curr_paragraphs` is null, stop and emit HARD_FAILURE."
        )
    lines.append(
        "- If observed counts do not exactly match JOB_META.expected_prev_paragraphs / JOB_META.expected_curr_paragraphs, stop and emit:"
    )
    lines.append('- `{"error":"HARD_FAILURE","reason":"preflight paragraph count mismatch"}`')
    lines.append("- Print exactly one preflight line after counts are verified:")
    lines.append(
        f"PRECHECK_OK ticker={ticker} pair={year_from}-{year_to} lens={lens} provenance_input_file={canonical_input_file} prev_paragraphs=<N> curr_paragraphs=<N>"
    )
    lines.append("")
    lines.append("3) Generate exactly one JSON object for `llm_outline_compare_v1` using the prompt contract below.")
    emit_prompt_block(lines, "SYSTEM PROMPT", system_block)
    lines.append("")
    emit_prompt_block(lines, "USER PROMPT TEMPLATE", user_template)
    lines.append("")
    emit_prompt_block(lines, "SELF-CHECK GATE (must pass before final JSON)", self_check)
    lines.append("")
    lines.append("4) Hard failure policy:")
    lines.append("- If schema requirements cannot be satisfied, do not fabricate data.")
    lines.append('- Return exactly: {"error":"HARD_FAILURE","reason":"<short reason>"}')
    lines.append("- Never paraphrase snippets in evidence; use contiguous verbatim substrings only.")
    lines.append("")
    lines.append("5) Write output JSON directly to this path:")
    lines.append(f"- {output_path}")
    lines.append("")
    lines.append("6) Run immediate checks exactly:")
    lines.append(f"- {build_json_parse_command(output_path)}")
    lines.append(
        f'- python scripts/lab_validate_llm_master_outputs.py --manifest "{manifest_path}" --campaign-id "{campaign_id}" --allow-missing --allow-invalid --only "{only_token}" --only-mode "exact_path" --expect-target-count 1 --fail-if-target-count-mismatch --report "{validation_report}"'
    )
    lines.append(
        f'- python scripts/lab_audit_master_output_quality.py --output "{output_path}" --mode blockers --report "{quality_report}"'
    )
    lines.append(
        "- Note: validator present_flag_mismatch can be non-blocking during incremental manual runs."
    )
    lines.append("")
    lines.append("7) Print exactly one final status line:")
    lines.append("- Success: WRITE_OK JSON_OK VALIDATION_OK")
    lines.append("- Failure: FAILED: <short reason list>")
    lines.append("END_STARTER")
    lines.append("")


def emit_vscode_autowrite_v4_block(
    *,
    lines: list[str],
    job_number: int,
    ticker: str,
    year_from: object,
    year_to: object,
    lens: str,
    section: str,
    source_id: str,
    pair_path: str,
    prev_path: str,
    curr_path: str,
    output_path_v2: str,
    output_path_v1: str,
    canonical_input_file: str,
    manifest_path: str,
    campaign_id: str,
    validation_report: str,
    quality_report: str,
    only_token_v2: str,
    only_token_v1: str,
    system_block: str,
    user_template: str,
    self_check: str,
    model_provider: str,
    model_name: str,
    run_label_template: str,
    expected_prev_paragraphs: Optional[int],
    expected_curr_paragraphs: Optional[int],
    expected_pair_sha256: str,
    expected_prev_sha256: str,
    expected_curr_sha256: str,
) -> None:
    lines.append(f"## Job {job_number:02d} - {ticker} {year_from}-{year_to} {lens}")
    lines.append("COPY FROM NEXT LINE THROUGH END_STARTER AND PASTE INTO A FRESH CODEX THREAD:")
    lines.append("BEGIN_STARTER")
    lines.append("You are Codex operating inside this workspace. Execute this job end-to-end.")
    lines.append("Do not ask for manual file attachments or manual save steps.")
    lines.append(
        "Execution focus: use only the declared pair/year input files plus this embedded prompt contract."
    )
    lines.append(
        "Forbidden sources: do not inspect existing output artifacts (including sibling raw/deboiler files) as templates unless a required gate fails."
    )
    lines.append("")
    lines.append("Execution mode: AUTOWRITE_VALIDATE_V4")
    lines.append(f"Thread title: {ticker} {year_from}-{year_to} outline compare ({lens})")
    lines.append(
        f"Case context: ticker={ticker}, pair={year_from}-{year_to}, section={section}, lens={lens}, source={source_id}"
    )
    lines.append("")
    lines.append("JOB_META")
    lines.append(
        json.dumps(
            {
                "job_id": f"{ticker}_{year_from}_{year_to}_{lens}_{source_id}",
                "model_provider": model_provider,
                "model_name": model_name,
                "run_label_template": run_label_template,
                "provenance_input_file": canonical_input_file,
                "expected_prev_paragraphs": expected_prev_paragraphs,
                "expected_curr_paragraphs": expected_curr_paragraphs,
                "expected_pair_sha256": expected_pair_sha256,
                "expected_prev_sha256": expected_prev_sha256,
                "expected_curr_sha256": expected_curr_sha256,
                "output_path_v2": output_path_v2,
                "projected_output_path_v1": output_path_v1,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    lines.append("")
    lines.append("OUTPUT_SHAPE_MIN")
    lines.append(json.dumps(OUTPUT_SHAPE_MIN, indent=2, ensure_ascii=False))
    lines.append("")
    lines.append("1) Read and parse these workspace JSON files:")
    lines.append(f"- Pair manifest: {pair_path}")
    lines.append(f"- Year prev: {prev_path}")
    lines.append(f"- Year curr: {curr_path}")
    lines.append("")
    lines.append("2) Preflight checks before generation:")
    lines.append("- Fail hard if any file is missing/unreadable or invalid JSON.")
    lines.append("- Verify pair manifest schema/input_mode/case/year_inputs linkage and file SHA256 locks.")
    lines.append("- Verify prev/curr counts from `year_payload.texts.paragraphs` against JOB_META expected counts.")
    lines.append("- Run extraction templates exactly with the two year files:")
    lines.append(
        '- python -c "import json, pathlib; d=json.loads(pathlib.Path(r\''
        + prev_path.replace("\\", "/")
        + '\').read_text(encoding=\'utf-8-sig\')); t=d.get(\'texts\'); p=t.get(\'paragraphs\') if isinstance(t, dict) else None; print(\'PREV_COUNT\', len(p) if isinstance(p, list) else \'INVALID\')"'
    )
    lines.append(
        '- python -c "import json, pathlib; d=json.loads(pathlib.Path(r\''
        + curr_path.replace("\\", "/")
        + '\').read_text(encoding=\'utf-8-sig\')); t=d.get(\'texts\'); p=t.get(\'paragraphs\') if isinstance(t, dict) else None; print(\'CURR_COUNT\', len(p) if isinstance(p, list) else \'INVALID\')"'
    )
    lines.append(
        "- Expected counts from bundle indexing: "
        + f"prev={expected_prev_paragraphs}, curr={expected_curr_paragraphs}."
    )
    lines.append(
        f"- {build_integrity_precheck_command(ticker=ticker, year_from=year_from, year_to=year_to, lens=lens, section=section, source_id=source_id, pair_path=pair_path, prev_path=prev_path, curr_path=curr_path, expected_prev_paragraphs=expected_prev_paragraphs, expected_curr_paragraphs=expected_curr_paragraphs, expected_pair_sha256=expected_pair_sha256, expected_prev_sha256=expected_prev_sha256, expected_curr_sha256=expected_curr_sha256)}"
    )
    lines.append(
        "- If any lock check fails, stop and emit exactly: `{\"error\":\"HARD_FAILURE\",\"reason\":\"preflight input lock mismatch\"}`"
    )
    lines.append("- Print exactly one preflight line after checks pass:")
    lines.append(
        f"PRECHECK_OK ticker={ticker} pair={year_from}-{year_to} lens={lens} provenance_input_file={canonical_input_file} prev_paragraphs=<N> curr_paragraphs=<N>"
    )
    lines.append("")
    lines.append("3) Generate exactly one JSON object for `llm_outline_compare_v2` using the prompt contract below.")
    emit_prompt_block(lines, "SYSTEM PROMPT", system_block)
    lines.append("")
    emit_prompt_block(lines, "USER PROMPT TEMPLATE", user_template)
    lines.append("")
    emit_prompt_block(lines, "SELF-CHECK GATE (must pass before final JSON)", self_check)
    lines.append("")
    lines.append("4) Hard failure policy:")
    lines.append("- If schema requirements cannot be satisfied, do not fabricate data.")
    lines.append('- Return exactly: {"error":"HARD_FAILURE","reason":"<short reason>"}')
    lines.append("- Never paraphrase snippets in evidence; use contiguous verbatim substrings only.")
    lines.append("")
    lines.append("5) Write output JSON directly to this v2 path:")
    lines.append(f"- {output_path_v2}")
    lines.append("")
    lines.append("6) Run immediate checks exactly:")
    lines.append(f"- {build_json_parse_command(output_path_v2)}")
    lines.append(
        f'- python scripts/lab_validate_llm_master_outputs.py --manifest "{manifest_path}" --campaign-id "{campaign_id}" --artifact-id "llm_outline_compare_v2" --target-field "master_output" --allow-missing --allow-invalid --only "{only_token_v2}" --only-mode "exact_path" --expect-target-count 1 --fail-if-target-count-mismatch --report "{validation_report}"'
    )
    lines.append(
        f'- python scripts/lab_audit_master_output_quality.py --output "{output_path_v2}" --artifact-id "llm_outline_compare_v2" --mode blockers --report "{quality_report}"'
    )
    lines.append(
        f'- python scripts/lab_project_master_v2_to_v1.py --manifest "{manifest_path}" --campaign-id "{campaign_id}" --only "{only_token_v2}" --only-mode "exact_path"'
    )
    lines.append(f"- {build_json_parse_command(output_path_v1)}")
    lines.append(
        f'- python scripts/lab_validate_llm_master_outputs.py --manifest "{manifest_path}" --campaign-id "{campaign_id}" --artifact-id "llm_outline_compare_v1" --target-field "projected_master_output_v1" --allow-missing --allow-invalid --only "{only_token_v1}" --only-mode "exact_path" --expect-target-count 1 --fail-if-target-count-mismatch --report "{validation_report}"'
    )
    lines.append("")
    lines.append("7) Print exactly one final status line:")
    lines.append("- Success: WRITE_OK JSON_OK VALIDATION_OK")
    lines.append("- Failure: FAILED: <short reason list>")
    lines.append("END_STARTER")
    lines.append("")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Emit canonical thread starters for llm_outline_compare_v2 master jobs."
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument(
        "--validation-report",
        default=str(DEFAULT_VALIDATION_REPORT),
        help="Validation report path inserted into vscode_autowrite starter checks.",
    )
    parser.add_argument(
        "--quality-report",
        default=str(DEFAULT_QUALITY_REPORT),
        help="Quality report path inserted into vscode_autowrite starter checks.",
    )
    parser.add_argument(
        "--format",
        choices=(
            "vscode_autowrite",
            "vscode_autowrite_v2",
            "vscode_autowrite_v3",
            "vscode_autowrite_v4",
            "legacy",
        ),
        default="vscode_autowrite_v4",
        help="Starter output format. vscode_autowrite_v4 is the canonical one-paste VS Code run profile.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=6,
        help="When using vscode_autowrite_v2/v3/v4, emit governance checkpoints every N jobs.",
    )
    parser.add_argument(
        "--batch-progress-report",
        default=str(DEFAULT_BATCH_PROGRESS_REPORT),
        help="Batch progress markdown report used by vscode_autowrite_v2/v3 checkpoints.",
    )
    parser.add_argument(
        "--batch-progress-json",
        default=str(DEFAULT_BATCH_PROGRESS_JSON),
        help="Batch progress JSON history used by vscode_autowrite_v2/v3 checkpoints.",
    )
    parser.add_argument(
        "--verbose-progress",
        action="store_true",
        help="Emit progress lines for each starter emitted.",
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
    campaign_track = get_llm_campaign(campaign_id)
    model_provider = (
        campaign_track.model_provider
        if campaign_track is not None and campaign_track.model_provider
        else "<model_provider>"
    )
    model_name = (
        campaign_track.model_name
        if campaign_track is not None and campaign_track.model_name
        else "<model_name>"
    )
    bundle_root_raw = str(manifest_dict.get("bundle_root") or "")
    bundle_root: Optional[Path] = None
    if bundle_root_raw:
        bundle_candidate = Path(bundle_root_raw)
        if bundle_candidate.is_absolute():
            bundle_root = bundle_candidate.resolve()
        else:
            bundle_root = (REPO_ROOT / bundle_candidate).resolve()
    validation_report_path = Path(args.validation_report)
    if not validation_report_path.is_absolute():
        validation_report_path = (REPO_ROOT / validation_report_path).resolve()
    quality_report_path = Path(args.quality_report)
    if not quality_report_path.is_absolute():
        quality_report_path = (REPO_ROOT / quality_report_path).resolve()
    batch_progress_report_path = Path(args.batch_progress_report)
    if not batch_progress_report_path.is_absolute():
        batch_progress_report_path = (REPO_ROOT / batch_progress_report_path).resolve()
    batch_progress_json_path = Path(args.batch_progress_json)
    if not batch_progress_json_path.is_absolute():
        batch_progress_json_path = (REPO_ROOT / batch_progress_json_path).resolve()

    system_block = load_prompt_block(PROMPT_SYSTEM_PATH).strip()
    user_template = load_prompt_block(PROMPT_USER_TEMPLATE_PATH).strip()
    self_check = load_prompt_block(PROMPT_SELF_CHECK_PATH).strip()

    lines: list[str] = []
    lines.append("# Master Thread Starters (llm_outline_compare_v2)")
    lines.append("")
    lines.append(f"- script: `{SCRIPT_VERSION}`")
    lines.append(f"- manifest: `{manifest_path.as_posix()}`")
    lines.append(f"- campaign: `{campaign_id}`")
    lines.append(f"- campaign display: `{campaign_name}`")
    lines.append(f"- output format: `{args.format}`")
    lines.append("")
    lines.append("Run one thread per pair/lens.")
    if args.format in {"vscode_autowrite", "vscode_autowrite_v2", "vscode_autowrite_v3", "vscode_autowrite_v4"}:
        lines.append("Each job block is paste-ready for a fresh VS Code Codex thread:")
        lines.append("1. Reads pair/year files directly from workspace")
        lines.append("2. Writes output to canonical path(s)")
        lines.append("3. Runs parse + validator + quality blocker checks immediately")
        if args.format in {"vscode_autowrite_v2", "vscode_autowrite_v3", "vscode_autowrite_v4"}:
            lines.append("4. Includes JOB_META constants + output skeleton to reduce exploration overhead")
            lines.append("5. Applies strict preflight lock on year_payload.texts.paragraphs counts")
            if args.format == "vscode_autowrite_v4":
                lines.append("6. Enforces SHA/path input locks and explicit no-template policy")
                lines.append("7. Projects llm_outline_compare_v2 to runtime llm_outline_compare_v1")
            else:
                lines.append("6. Inserts batch governance checkpoints every N jobs")
    else:
        lines.append("Legacy format:")
        lines.append("1. Read pair manifest JSON")
        lines.append("2. Read year prev input JSON")
        lines.append("3. Read year curr input JSON")
    lines.append("")

    print(f"[phase] emit master thread starters (script={SCRIPT_VERSION})", flush=True)
    emitted = 0
    total_entries = len(entries)
    loop_started = time.monotonic()
    last_heartbeat = loop_started
    progress_interval_sec = max(1, int(args.progress_interval_sec))
    for entry_any in entries:
        entry = as_dict(entry_any)
        if entry is None:
            continue
        input_block = as_dict(entry.get("input")) or {}
        master_output = as_dict(entry.get("master_output")) or {}
        projected_master_output_v1 = as_dict(entry.get("projected_master_output_v1")) or {}
        ticker = str(entry.get("ticker") or "")
        year_from = entry.get("year_from")
        year_to = entry.get("year_to")
        lens = str(entry.get("lens") or "")
        section = str(entry.get("section") or "10k_item1a")
        source_id = str(entry.get("source_id") or "edgar")
        pair_path_raw = str(input_block.get("source_path") or "")
        prev_path_raw = str(input_block.get("source_year_prev_path") or "")
        curr_path_raw = str(input_block.get("source_year_curr_path") or "")
        output_path = str(master_output.get("expected_output_path") or "")
        projected_output_path_v1 = str(
            projected_master_output_v1.get("expected_output_path") or ""
        )
        input_integrity = as_dict(input_block.get("integrity")) or {}
        expected_pair_sha256 = str(input_integrity.get("pair_payload_sha256") or "")
        expected_prev_sha256 = str(input_integrity.get("prev_payload_sha256") or "")
        expected_curr_sha256 = str(input_integrity.get("curr_payload_sha256") or "")
        if not pair_path_raw:
            continue
        pair_abs = (REPO_ROOT / pair_path_raw).resolve() if not Path(pair_path_raw).is_absolute() else Path(pair_path_raw).resolve()
        pair_path = resolve_from_manifest(
            pair_path_raw, bundle_root=bundle_root, pair_abs_path=pair_abs
        )
        prev_path = resolve_from_manifest(
            prev_path_raw, bundle_root=bundle_root, pair_abs_path=pair_abs
        )
        curr_path = resolve_from_manifest(
            curr_path_raw, bundle_root=bundle_root, pair_abs_path=pair_abs
        )
        pair_basename = Path(pair_path_raw).name
        canonical_input_file = f"inputs/pair/{pair_basename}" if pair_basename else ""
        output_display = resolve_from_manifest(
            output_path, bundle_root=None, pair_abs_path=None
        )
        manifest_display = workspace_display(manifest_path)
        validation_report_display = workspace_display(validation_report_path)
        quality_report_display = workspace_display(quality_report_path)
        batch_progress_report_display = workspace_display(batch_progress_report_path)
        batch_progress_json_display = workspace_display(batch_progress_json_path)
        only_token = output_display
        runtime_output_display = resolve_from_manifest(
            projected_output_path_v1, bundle_root=None, pair_abs_path=None
        )
        only_token_v1 = runtime_output_display
        expected_prev_paragraphs = extract_year_paragraph_count(prev_path)
        expected_curr_paragraphs = extract_year_paragraph_count(curr_path)
        run_label_template = build_run_label_template(
            campaign_id=campaign_id,
            ticker=ticker,
            year_from=year_from,
            year_to=year_to,
        )
        emitted += 1
        now = time.monotonic()
        if args.verbose_progress or now - last_heartbeat >= progress_interval_sec:
            elapsed = int(now - loop_started)
            print(
                "[progress] master_thread_starters "
                + f"entries_seen={emitted}/{total_entries} elapsed={elapsed}s",
                flush=True,
            )
            last_heartbeat = now

        if args.format == "legacy":
            emit_legacy_block(
                lines=lines,
                ticker=ticker,
                year_from=year_from,
                year_to=year_to,
                lens=lens,
                section=section,
                source_id=source_id,
                pair_path=pair_path,
                prev_path=prev_path,
                curr_path=curr_path,
                output_path=output_display,
                canonical_input_file=canonical_input_file,
                system_block=system_block,
                user_template=user_template,
                self_check=self_check,
            )
        elif args.format == "vscode_autowrite":
            emit_vscode_autowrite_block(
                lines=lines,
                job_number=emitted,
                ticker=ticker,
                year_from=year_from,
                year_to=year_to,
                lens=lens,
                section=section,
                source_id=source_id,
                pair_path=pair_path,
                prev_path=prev_path,
                curr_path=curr_path,
                output_path=output_display,
                canonical_input_file=canonical_input_file,
                manifest_path=manifest_display,
                campaign_id=campaign_id,
                validation_report=validation_report_display,
                quality_report=quality_report_display,
                only_token=only_token,
                system_block=system_block,
                user_template=user_template,
                self_check=self_check,
            )
        elif args.format == "vscode_autowrite_v2":
            emit_vscode_autowrite_v2_block(
                lines=lines,
                job_number=emitted,
                ticker=ticker,
                year_from=year_from,
                year_to=year_to,
                lens=lens,
                section=section,
                source_id=source_id,
                pair_path=pair_path,
                prev_path=prev_path,
                curr_path=curr_path,
                output_path=output_display,
                canonical_input_file=canonical_input_file,
                manifest_path=manifest_display,
                campaign_id=campaign_id,
                validation_report=validation_report_display,
                quality_report=quality_report_display,
                only_token=only_token,
                system_block=system_block,
                user_template=user_template,
                self_check=self_check,
                model_provider=model_provider,
                model_name=model_name,
                run_label_template=run_label_template,
                expected_prev_paragraphs=expected_prev_paragraphs,
                expected_curr_paragraphs=expected_curr_paragraphs,
            )
            batch_size = max(1, int(args.batch_size))
            if emitted % batch_size == 0 and emitted < total_entries:
                emit_batch_checkpoint_block(
                    lines=lines,
                    completed_jobs=emitted,
                    total_jobs=total_entries,
                    manifest_path=manifest_display,
                    campaign_id=campaign_id,
                    validation_report=validation_report_display,
                    quality_report=quality_report_display,
                    progress_md=batch_progress_report_display,
                    progress_json=batch_progress_json_display,
                )
        elif args.format == "vscode_autowrite_v3":
            emit_vscode_autowrite_v3_block(
                lines=lines,
                job_number=emitted,
                ticker=ticker,
                year_from=year_from,
                year_to=year_to,
                lens=lens,
                section=section,
                source_id=source_id,
                pair_path=pair_path,
                prev_path=prev_path,
                curr_path=curr_path,
                output_path=output_display,
                canonical_input_file=canonical_input_file,
                manifest_path=manifest_display,
                campaign_id=campaign_id,
                validation_report=validation_report_display,
                quality_report=quality_report_display,
                only_token=only_token,
                system_block=system_block,
                user_template=user_template,
                self_check=self_check,
                model_provider=model_provider,
                model_name=model_name,
                run_label_template=run_label_template,
                expected_prev_paragraphs=expected_prev_paragraphs,
                expected_curr_paragraphs=expected_curr_paragraphs,
            )
            batch_size = max(1, int(args.batch_size))
            if emitted % batch_size == 0 and emitted < total_entries:
                emit_batch_checkpoint_block(
                    lines=lines,
                    completed_jobs=emitted,
                    total_jobs=total_entries,
                    manifest_path=manifest_display,
                    campaign_id=campaign_id,
                    validation_report=validation_report_display,
                    quality_report=quality_report_display,
                    progress_md=batch_progress_report_display,
                    progress_json=batch_progress_json_display,
                )
        else:
            emit_vscode_autowrite_v4_block(
                lines=lines,
                job_number=emitted,
                ticker=ticker,
                year_from=year_from,
                year_to=year_to,
                lens=lens,
                section=section,
                source_id=source_id,
                pair_path=pair_path,
                prev_path=prev_path,
                curr_path=curr_path,
                output_path_v2=output_display,
                output_path_v1=runtime_output_display,
                canonical_input_file=canonical_input_file,
                manifest_path=manifest_display,
                campaign_id=campaign_id,
                validation_report=validation_report_display,
                quality_report=quality_report_display,
                only_token_v2=only_token,
                only_token_v1=only_token_v1,
                system_block=system_block,
                user_template=user_template,
                self_check=self_check,
                model_provider=model_provider,
                model_name=model_name,
                run_label_template=run_label_template,
                expected_prev_paragraphs=expected_prev_paragraphs,
                expected_curr_paragraphs=expected_curr_paragraphs,
                expected_pair_sha256=expected_pair_sha256,
                expected_prev_sha256=expected_prev_sha256,
                expected_curr_sha256=expected_curr_sha256,
            )
            batch_size = max(1, int(args.batch_size))
            if emitted % batch_size == 0 and emitted < total_entries:
                emit_batch_checkpoint_block(
                    lines=lines,
                    completed_jobs=emitted,
                    total_jobs=total_entries,
                    manifest_path=manifest_display,
                    campaign_id=campaign_id,
                    validation_report=validation_report_display,
                    quality_report=quality_report_display,
                    progress_md=batch_progress_report_display,
                    progress_json=batch_progress_json_display,
                )

    print("[phase] write starter markdown", flush=True)
    write_text(out_path, lines)
    elapsed = int(time.monotonic() - started)
    print(f"Script: {SCRIPT_VERSION}")
    print(f"Wrote master thread starters: {out_path}")
    print(f"Jobs emitted: {emitted}")
    print(f"Elapsed: {elapsed}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
