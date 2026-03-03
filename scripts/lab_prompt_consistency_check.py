from __future__ import annotations

import argparse
import json
import re
from difflib import unified_diff
from pathlib import Path
from typing import Any, Optional, cast

import sys

from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v6")

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MASTER_STARTERS = REPO_ROOT / "reports" / "lab_llm_master_thread_starters_codex_real.md"
DEFAULT_MASTER_MANIFEST = REPO_ROOT / "reports" / "lab_llm_master_manifest_codex_real.json"
DEFAULT_DOC_INDEX = REPO_ROOT / "docs" / "00_DOC_INDEX.md"
DEFAULT_REMAINING_PLAN_DOC = REPO_ROOT / "docs" / "LAB_REMAINING_WORK_PLAN.md"
DEFAULT_MODEL_COMPARISON_DOC = REPO_ROOT / "docs" / "lab" / "06_llm_model_comparison_workflow.md"

sys.path.append(str(Path(__file__).resolve().parent))
from lab_llm_precompute_utils import resolve_bundle_paths  # type: ignore
from lab_output_tracks import (  # type: ignore
    DEFAULT_PRIMARY_LLM_CAMPAIGN_ID,
    canonical_output_relative_path,
    get_llm_campaign,
)
from lab_prompt_blocks import (  # type: ignore
    DETECTOR_DELTA_BRIEF,
    DETECTOR_EXCERPT_PICKER,
    build_chatgpt_project_instructions_lines,
    build_prompt_template_detector_section_lines,
    build_prompt_templates_showcase_lines,
    build_thread_starter_lines,
)


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8-sig").splitlines()


def _extract_section(lines: list[str], section_header: str) -> list[str]:
    start = -1
    for idx, line in enumerate(lines):
        if line.strip() == section_header:
            start = idx
            break
    if start == -1:
        raise SystemExit(f"Missing section header: {section_header}")

    end = len(lines)
    for idx in range(start + 1, len(lines)):
        if lines[idx].startswith("## "):
            end = idx
            break
    section = lines[start:end]
    while section and not section[-1].strip():
        section.pop()
    return section


def _assert_lines_equal(label: str, expected: list[str], actual: list[str]) -> None:
    if expected == actual:
        return
    diff = "\n".join(
        unified_diff(
            expected,
            actual,
            fromfile=f"{label}:expected",
            tofile=f"{label}:actual",
            lineterm="",
        )
    )
    raise SystemExit(f"{label} mismatch:\n{diff}")


def _assert_markers_present(label: str, text: str, markers: list[str]) -> None:
    missing = [marker for marker in markers if marker not in text]
    if missing:
        raise SystemExit(
            f"{label} missing required marker(s):\n"
            + "\n".join(f"- {marker}" for marker in missing)
        )


def _assert_markers_absent(label: str, text: str, markers: list[str]) -> None:
    present = [marker for marker in markers if marker in text]
    if present:
        raise SystemExit(
            f"{label} contains forbidden marker(s):\n"
            + "\n".join(f"- {marker}" for marker in present)
        )


def _default_instruction_report_path(campaign_id: str) -> Path:
    return REPO_ROOT / "reports" / f"lab_project_instructions_{campaign_id}.txt"


def _default_instruction_public_path(campaign_asset_name: str) -> Path:
    return (
        REPO_ROOT
        / "public"
        / "data"
        / "sec_narrative_drift_lab"
        / campaign_asset_name
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check campaign-aware prompt/instruction consistency against canonical emitters."
    )
    parser.add_argument(
        "--bundle",
        default="",
        help="Showcase LLM input bundle root (defaults to latest showcase_llm_inputs_*).",
    )
    parser.add_argument(
        "--campaign-id",
        default=DEFAULT_PRIMARY_LLM_CAMPAIGN_ID,
        help="Campaign id from scripts/lab_output_tracks.py.",
    )
    parser.add_argument(
        "--prompt-templates",
        default="",
        help="Override path to prompt_templates_showcase.md.",
    )
    parser.add_argument(
        "--instructions-report",
        default="",
        help="Path to report instructions text. Defaults to reports/lab_project_instructions_<campaign_id>.txt.",
    )
    parser.add_argument(
        "--instructions-public",
        default="",
        help="Path to public instructions text. Defaults to public/data/sec_narrative_drift_lab/<campaign_asset_name>.",
    )
    parser.add_argument(
        "--setup-doc",
        default=str(REPO_ROOT / "docs" / "lab" / "04_chatgpt_project_setup.md"),
        help="Path to docs/lab/04_chatgpt_project_setup.md.",
    )
    parser.add_argument(
        "--contract-doc",
        default=str(REPO_ROOT / "docs" / "lab" / "05_llm_reproducibility_contract.md"),
        help="Path to docs/lab/05_llm_reproducibility_contract.md.",
    )
    parser.add_argument(
        "--master-starters",
        default=str(DEFAULT_MASTER_STARTERS),
        help="Path to generated master thread starters markdown.",
    )
    parser.add_argument(
        "--master-manifest",
        default=str(DEFAULT_MASTER_MANIFEST),
        help="Path to master manifest used for thread starters.",
    )
    parser.add_argument(
        "--doc-index",
        default=str(DEFAULT_DOC_INDEX),
        help="Path to docs/00_DOC_INDEX.md.",
    )
    parser.add_argument(
        "--remaining-plan-doc",
        default=str(DEFAULT_REMAINING_PLAN_DOC),
        help="Path to docs/LAB_REMAINING_WORK_PLAN.md.",
    )
    parser.add_argument(
        "--comparison-doc",
        default=str(DEFAULT_MODEL_COMPARISON_DOC),
        help="Path to docs/lab/06_llm_model_comparison_workflow.md.",
    )
    return parser


def check_canonical_docs(doc_index_path: Path, remaining_plan_path: Path, comparison_doc_path: Path) -> None:
    if not doc_index_path.exists():
        raise SystemExit(f"Missing canonical doc index: {doc_index_path}")
    if not remaining_plan_path.exists():
        raise SystemExit(f"Missing remaining work plan doc: {remaining_plan_path}")
    if not comparison_doc_path.exists():
        raise SystemExit(f"Missing model comparison doc: {comparison_doc_path}")

    doc_index_text = doc_index_path.read_text(encoding="utf-8-sig")
    _assert_markers_present(
        "doc_index",
        doc_index_text,
        [
            "`docs/_archive/legacy_context_20260302/00_README_doc_index.md`",
            "`docs/_archive/legacy_context_20260302/sec_narrative_drift_codex_spec_v1_13.md`",
            "`docs/_archive/legacy_context_20260302/sec_narrative_drift_codex_implementation_checklist_v1_13.md`",
            "`reports/lab_llm_master_manifest_codex_real.json`",
            "`reports/lab_llm_master_thread_starters_codex_real.md`",
            "`reports/lab_llm_master_validation_codex_real.md`",
        ],
    )
    _assert_markers_absent(
        "doc_index",
        doc_index_text,
        [
            "`docs/00_README_doc_index.md`",
            "`docs/sec_narrative_drift_codex_spec_v1_13.md`",
            "`docs/sec_narrative_drift_codex_implementation_checklist_v1_13.md`",
            "`reports/lab_llm_run_manifest.md`",
            "`reports/lab_llm_run_manifest.json`",
        ],
    )

    remaining_plan_text = remaining_plan_path.read_text(encoding="utf-8-sig")
    _assert_markers_present(
        "remaining_plan_doc",
        remaining_plan_text,
        [
            "`openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27`",
            "`openai_chatgpt52ext_agent_fullsec_real_2026-02-27`",
            "`llm_outline_compare_v1`",
            "`docs/lab/08_remaining_work_plan_history.md`",
        ],
    )
    _assert_markers_absent(
        "remaining_plan_doc",
        remaining_plan_text,
        [
            "# PHASE 0 - Ship and lock the deterministic baseline",
            "# CODEx: One-shot Agent Prompt (surgical execution)",
            "`reports/lab_llm_run_manifest.md`",
            "`reports/lab_llm_run_manifest.json`",
        ],
    )

    comparison_text = comparison_doc_path.read_text(encoding="utf-8-sig")
    _assert_markers_present(
        "comparison_doc",
        comparison_text,
        [
            "`openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27`",
            "`openai-gpt53codex-xhigh-agent-fullsec-real-2026-02-27`",
            "`openai_chatgpt52ext_agent_fullsec_real_2026-02-27`",
            "`openai-chatgpt52ext-agent-fullsec-real-2026-02-27`",
            "runtime-visible",
            "runtime-hidden",
        ],
    )
    _assert_markers_absent(
        "comparison_doc",
        comparison_text,
        [
            "`openai_chatgpt52ext_agent_2026-02-21`",
            "`openai_gpt53codex_xhigh_agent_2026-02-21`",
            "`openai-chatgpt52ext-agent-2026-02-21`",
            "`openai-gpt53codex-xhigh-agent-2026-02-21`",
        ],
    )


def _check_master_starters(master_starters_path: Path, master_manifest_path: Path, campaign_slug: str) -> None:
    if not master_starters_path.exists():
        raise SystemExit(f"Missing master starters file: {master_starters_path}")
    if not master_manifest_path.exists():
        raise SystemExit(f"Missing master manifest file: {master_manifest_path}")

    starters_text = master_starters_path.read_text(encoding="utf-8-sig")
    _assert_markers_present(
        "master_starters",
        starters_text,
        [
            "Execution focus: do not inspect unrelated scripts/docs unless a required gate fails.",
            "JOB_META",
            "\"job_id\":",
            "\"model_provider\":",
            "\"model_name\":",
            "\"run_label_template\":",
            "\"provenance_input_file\":",
            "\"expected_prev_paragraphs\":",
            "\"expected_curr_paragraphs\":",
            "\"output_path\":",
            "year_payload.texts.paragraphs",
            "If observed counts do not exactly match JOB_META.expected_prev_paragraphs / JOB_META.expected_curr_paragraphs",
            "preflight paragraph count mismatch",
            "--only-mode \"exact_path\"",
            "--expect-target-count 1",
            "--fail-if-target-count-mismatch",
            "lab_audit_master_output_quality.py --output",
            "python -c \"import json, pathlib;",
        ],
    )
    if "> NUL" in starters_text:
        raise SystemExit("master_starters includes shell-fragile `> NUL` redirection.")

    manifest_payload = json.loads(master_manifest_path.read_text(encoding="utf-8-sig"))
    if not isinstance(manifest_payload, dict):
        raise SystemExit("master manifest root must be an object")
    manifest_data = cast(dict[str, Any], manifest_payload)
    entries = manifest_data.get("entries")
    if not isinstance(entries, list):
        raise SystemExit("master manifest missing entries list")

    expected_paths: list[str] = []
    for entry in entries:  # type: ignore[reportUnknownVariableType]
        if not isinstance(entry, dict):
            continue
        entry_data = cast(dict[str, Any], entry)
        master_output = entry_data.get("master_output")
        if not isinstance(master_output, dict):
            continue
        output_data = cast(dict[str, Any], master_output)
        expected_output_path = output_data.get("expected_output_path")
        if not isinstance(expected_output_path, str):
            continue
        normalized = "/" + expected_output_path.replace("\\", "/").lstrip("/")
        if f"/{campaign_slug}/" not in normalized:
            continue
        expected_paths.append(expected_output_path.replace("\\", "/").lstrip("/"))

    if not expected_paths:
        raise SystemExit("master manifest yielded no campaign paths for starter verification")

    only_tokens = re.findall(r'--only "([^"]+)"', starters_text)
    if not only_tokens:
        raise SystemExit("master starters missing --only tokens")
    if len(only_tokens) != len(expected_paths):
        raise SystemExit(
            "master starters token count mismatch: "
            + f"tokens={len(only_tokens)} manifest_targets={len(expected_paths)}"
        )
    for token in only_tokens:
        normalized_token = token.replace("\\", "/").lstrip("/")
        match_count = sum(1 for expected_path in expected_paths if expected_path == normalized_token)
        if match_count != 1:
            raise SystemExit(
                f"starter --only token must map to exactly one expected path: token={token!r}, matches={match_count}"
            )


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    campaign = get_llm_campaign(args.campaign_id)
    if campaign is None or campaign.instructions_asset_name is None:
        raise SystemExit(f"Unknown campaign id: {args.campaign_id}")

    bundle_paths = resolve_bundle_paths(
        args.bundle or None,
        None,
        None,
        args.prompt_templates or None,
    )
    prompt_path = bundle_paths.prompt_templates
    if prompt_path is None or not prompt_path.exists():
        raise SystemExit("prompt_templates_showcase.md not found.")

    expected_full = build_prompt_templates_showcase_lines(
        campaign=campaign,
        input_mode=campaign.input_mode or "full_section_v2",
    )
    actual_full = _read_lines(prompt_path)
    _assert_lines_equal("prompt_templates_showcase", expected_full, actual_full)

    for detector_id in (DETECTOR_DELTA_BRIEF, DETECTOR_EXCERPT_PICKER):
        expected_section = build_prompt_template_detector_section_lines(
            detector_id,
            campaign=campaign,
            input_mode=campaign.input_mode or "full_section_v2",
        )
        actual_section = _extract_section(actual_full, f"## {detector_id}")
        _assert_lines_equal(f"prompt_section:{detector_id}", expected_section, actual_section)

    expected_instructions = build_chatgpt_project_instructions_lines(
        campaign=campaign,
        input_mode=campaign.input_mode or "full_section_v2",
    )
    instructions_report = (
        Path(args.instructions_report)
        if args.instructions_report
        else _default_instruction_report_path(campaign.track_id)
    )
    if not instructions_report.is_absolute():
        instructions_report = REPO_ROOT / instructions_report
    if instructions_report.exists():
        actual_report_instructions = _read_lines(instructions_report)
        _assert_lines_equal(
            "project_instructions_report",
            expected_instructions,
            actual_report_instructions,
        )

    instructions_public = (
        Path(args.instructions_public)
        if args.instructions_public
        else _default_instruction_public_path(campaign.instructions_asset_name)
    )
    if not instructions_public.is_absolute():
        instructions_public = REPO_ROOT / instructions_public
    if instructions_public.exists():
        actual_public_instructions = _read_lines(instructions_public)
        _assert_lines_equal(
            "project_instructions_public",
            expected_instructions,
            actual_public_instructions,
        )

    setup_doc_path = Path(args.setup_doc)
    if not setup_doc_path.is_absolute():
        setup_doc_path = REPO_ROOT / setup_doc_path
    contract_doc_path = Path(args.contract_doc)
    if not contract_doc_path.is_absolute():
        contract_doc_path = REPO_ROOT / contract_doc_path
    doc_index_path = Path(args.doc_index)
    if not doc_index_path.is_absolute():
        doc_index_path = REPO_ROOT / doc_index_path
    remaining_plan_path = Path(args.remaining_plan_doc)
    if not remaining_plan_path.is_absolute():
        remaining_plan_path = REPO_ROOT / remaining_plan_path
    comparison_doc_path = Path(args.comparison_doc)
    if not comparison_doc_path.is_absolute():
        comparison_doc_path = REPO_ROOT / comparison_doc_path
    if not setup_doc_path.exists():
        raise SystemExit(f"Missing setup doc: {setup_doc_path}")
    if not contract_doc_path.exists():
        raise SystemExit(f"Missing reproducibility contract doc: {contract_doc_path}")

    setup_doc_text = setup_doc_path.read_text(encoding="utf-8-sig")
    _assert_markers_present(
        "setup_doc",
        setup_doc_text,
        [
            "exactly equal deduped evidence index sets for each year",
            "sorted by `(year, paragraph_idx)` ascending",
            "Change:`, `Drivers:`, `Caveat:`",
            "4-8` blocks with `>=2` blocks per year",
            "6-10` blocks with `>=3` blocks per year",
            "recommended `220-320` chars, hard cap `350`",
            "placeholder tails like `Input file citation:`, `Source:`, `Input source:` are invalid",
            "YYYY-MM-DD_",
        ],
    )

    contract_doc_text = contract_doc_path.read_text(encoding="utf-8-sig")
    _assert_markers_present(
        "repro_contract_doc",
        contract_doc_text,
        [
            "exactly equal deduped evidence indices per year",
            "sorted by `(year, paragraph_idx)` ascending",
            "4-8` total with `>=2` per year",
            "6-10` total with `>=3` per year",
            "`Change:`, `Drivers:`, `Caveat:`",
            "recommended `220-320` chars, hard cap `350`",
            "placeholder tails like `Input file citation:`, `Source:`, `Input source:` are invalid",
            "YYYY-MM-DD_",
        ],
    )
    check_canonical_docs(
        doc_index_path=doc_index_path,
        remaining_plan_path=remaining_plan_path,
        comparison_doc_path=comparison_doc_path,
    )

    sample_ticker = "KO"
    sample_year_from = 2023
    sample_year_to = 2024
    sample_lens = "deboilerplated"
    sample_input = (
        f"inputs/pair/{sample_ticker}_{sample_year_from}_{sample_year_to}_10k_item1a_{sample_lens}_edgar.json"
    )
    sample_year_prev = (
        f"inputs/year/{sample_ticker}_{sample_year_from}_10k_item1a_{sample_lens}_edgar__pair_{sample_year_from}_{sample_year_to}.json"
    )
    sample_year_curr = (
        f"inputs/year/{sample_ticker}_{sample_year_to}_10k_item1a_{sample_lens}_edgar__pair_{sample_year_from}_{sample_year_to}.json"
    )
    sample_repo_input = (
        f"{bundle_paths.bundle_root.as_posix()}/inputs/pair/"
        f"{sample_ticker}_{sample_year_from}_{sample_year_to}_10k_item1a_{sample_lens}_edgar.json"
    )

    for detector_id in (DETECTOR_DELTA_BRIEF, DETECTOR_EXCERPT_PICKER):
        output_path = canonical_output_relative_path(
            ticker=sample_ticker,
            detector_id=detector_id,
            section="10k_item1a",
            year_from=sample_year_from,
            year_to=sample_year_to,
            cleaning_lens="deboilerplated",
            source_id="edgar",
            track_slug=campaign.track_slug,
        )
        starter = build_thread_starter_lines(
            detector_id=detector_id,
            ticker=sample_ticker,
            year_from=sample_year_from,
            year_to=sample_year_to,
            section="10k_item1a",
            source_id="edgar",
            input_lens=sample_lens,
            input_path=sample_input,
            output_path=f"public/data/sec_narrative_drift_lab/{output_path}",
            repo_input_path=sample_repo_input,
            additional_input_paths=[sample_year_prev, sample_year_curr],
            input_mode=campaign.input_mode or "full_section_v2",
            campaign=campaign,
        )
        starter_text = "\n".join(starter)
        starter_markers = [
            "YYYY-MM-DD_",
            campaign.model_name or "",
            campaign.model_provider or "",
            "evidence paragraph_idx are FULL indices",
            "snippets are verbatim and <= 350 chars",
        ]
        if detector_id == DETECTOR_DELTA_BRIEF:
            starter_markers.extend(["Change:", "Drivers:", "Caveat:"])
        _assert_markers_present(
            f"starter:{detector_id}",
            starter_text,
            starter_markers,
        )

    master_starters_path = Path(args.master_starters)
    if not master_starters_path.is_absolute():
        master_starters_path = REPO_ROOT / master_starters_path
    master_manifest_path = Path(args.master_manifest)
    if not master_manifest_path.is_absolute():
        master_manifest_path = REPO_ROOT / master_manifest_path
    _check_master_starters(
        master_starters_path=master_starters_path,
        master_manifest_path=master_manifest_path,
        campaign_slug=campaign.track_slug,
    )

    print("Prompt consistency check: PASS")
    print(f"Script: {SCRIPT_VERSION}")
    print(f"Campaign: {campaign.track_id}")
    print(f"Prompt templates: {prompt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
