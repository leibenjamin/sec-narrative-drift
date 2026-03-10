from __future__ import annotations

import argparse
import json
import re
from difflib import unified_diff
from pathlib import Path
from typing import Any, Optional, cast

import sys

from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v7")

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MASTER_STARTERS = REPO_ROOT / "reports" / "lab_llm_master_thread_starters_codex_real.md"
DEFAULT_MASTER_MANIFEST = REPO_ROOT / "reports" / "lab_llm_master_manifest_codex_real.json"
DEFAULT_DOC_INDEX = REPO_ROOT / "docs" / "00_DOC_INDEX.md"
DEFAULT_REMAINING_PLAN_DOC = REPO_ROOT / "docs" / "LAB_REMAINING_WORK_PLAN.md"
DEFAULT_MODEL_COMPARISON_DOC = REPO_ROOT / "docs" / "lab" / "06_llm_model_comparison_workflow.md"
PROMPT_TEMPLATES_CANONICAL_FILENAME = "prompt_templates_showcase.md"

sys.path.append(str(Path(__file__).resolve().parent))
from lab_llm_precompute_utils import BundlePaths, resolve_bundle_paths  # type: ignore
from lab_output_tracks import (  # type: ignore
    DEFAULT_COMPARE_LLM_CAMPAIGN_ID,
    DEFAULT_PRIMARY_LLM_CAMPAIGN_ID,
    EXECUTION_VENUE_CHATGPT_DESKTOP,
    canonical_output_relative_path,
    get_llm_campaign,
)
from lab_prompt_blocks import (  # type: ignore
    DETECTOR_DELTA_BRIEF,
    DETECTOR_EXCERPT_PICKER,
    build_project_instructions_lines,
    build_prompt_template_detector_section_lines,
    build_prompt_templates_showcase_lines,
    build_thread_starter_lines,
)
from lab_verify_master_input_locks import verify_master_input_locks  # type: ignore


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



def _resolve_repo_relative_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _collect_focus_signal_ids_from_entry(entry_data: dict[str, Any]) -> list[str]:
    input_info = entry_data.get("input")
    if not isinstance(input_info, dict):
        return []
    source_path = input_info.get("source_path")
    if not isinstance(source_path, str) or not source_path.strip():
        return []
    pair_path = _resolve_repo_relative_path(source_path.strip())
    if not pair_path.exists():
        return []

    try:
        payload = json.loads(pair_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, dict):
        return []
    analysis_expectations = payload.get("analysis_expectations")
    if not isinstance(analysis_expectations, dict):
        return []
    focus_signals = analysis_expectations.get("focus_signals")
    if not isinstance(focus_signals, list):
        return []

    signal_ids: list[str] = []
    for signal in focus_signals:
        if not isinstance(signal, dict):
            continue
        signal_id = signal.get("id")
        if isinstance(signal_id, str) and signal_id.strip() and signal_id not in signal_ids:
            signal_ids.append(signal_id)
    return signal_ids


def _extract_validate_pairs(starters_text: str) -> set[tuple[str, str]]:
    pattern = re.compile(
        r'lab_validate_llm_master_outputs\.py[^\n]*--artifact-id "([^"]+)"[^\n]*--target-field "([^"]+)"'
    )
    return {(artifact_id, target_field) for artifact_id, target_field in pattern.findall(starters_text)}


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


def _campaign_prompt_templates_filename(campaign_slug: str) -> str:
    return f"prompt_templates_showcase__{campaign_slug}.md"


def resolve_prompt_templates_path(
    *,
    bundle_paths: BundlePaths,
    campaign_id: str,
    campaign_slug: str,
    prompt_templates_override: str,
) -> Path:
    if prompt_templates_override:
        prompt_path = bundle_paths.prompt_templates
        if prompt_path is None or not prompt_path.exists():
            raise SystemExit("prompt_templates override path not found.")
        return prompt_path

    canonical_prompt_path = bundle_paths.bundle_root / PROMPT_TEMPLATES_CANONICAL_FILENAME
    if campaign_id == DEFAULT_PRIMARY_LLM_CAMPAIGN_ID:
        if not canonical_prompt_path.exists():
            raise SystemExit("prompt_templates_showcase.md not found for primary campaign.")
        return canonical_prompt_path

    campaign_prompt_path = bundle_paths.bundle_root / _campaign_prompt_templates_filename(
        campaign_slug
    )
    if campaign_prompt_path.exists():
        return campaign_prompt_path

    write_cmd = (
        "python scripts/lab_write_prompt_templates.py "
        + f'--bundle "{bundle_paths.bundle_root.as_posix()}" '
        + f'--campaign-id "{campaign_id}" '
        + f'--out "{campaign_prompt_path.name}"'
    )
    raise SystemExit(
        "Missing campaign-scoped prompt template for non-primary campaign: "
        + f"{campaign_prompt_path}\n"
        + "Generate it with:\n"
        + write_cmd
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
        default="",
        help=(
            "Campaign id from scripts/lab_output_tracks.py. If omitted, auto-detect from "
            "--master-manifest campaign.campaign_id; falls back to primary campaign."
        ),
    )
    parser.add_argument(
        "--prompt-templates",
        default="",
        help=(
            "Override path to prompt templates markdown. By default: primary campaign "
            "uses prompt_templates_showcase.md; non-primary campaigns require "
            "prompt_templates_showcase__<track_slug>.md in the selected bundle."
        ),
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


def _resolve_campaign_id(raw_campaign_id: str, master_manifest_arg: str) -> str:
    campaign_id = raw_campaign_id.strip()
    if campaign_id:
        return campaign_id

    manifest_path = Path(master_manifest_arg)
    if not manifest_path.is_absolute():
        manifest_path = REPO_ROOT / manifest_path
    if manifest_path.exists():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            typed_payload = cast(dict[str, object], payload)
            campaign = typed_payload.get("campaign")
            if isinstance(campaign, dict):
                typed_campaign = cast(dict[str, object], campaign)
                detected = typed_campaign.get("campaign_id")
                if isinstance(detected, str) and detected.strip():
                    return detected.strip()

    return DEFAULT_PRIMARY_LLM_CAMPAIGN_ID


def check_canonical_docs(doc_index_path: Path, remaining_plan_path: Path, comparison_doc_path: Path) -> None:
    if not doc_index_path.exists():
        raise SystemExit(f"Missing canonical doc index: {doc_index_path}")
    if not remaining_plan_path.exists():
        raise SystemExit(f"Missing remaining work plan doc: {remaining_plan_path}")
    if not comparison_doc_path.exists():
        raise SystemExit(f"Missing model comparison doc: {comparison_doc_path}")

    compare_campaign = get_llm_campaign(DEFAULT_COMPARE_LLM_CAMPAIGN_ID)
    if compare_campaign is None:
        raise SystemExit("Compare campaign metadata unavailable for doc checks.")

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
            f"`{DEFAULT_PRIMARY_LLM_CAMPAIGN_ID}`",
            f"`{compare_campaign.track_id}`",
            "`llm_outline_compare_runtime`",
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
            f"`{DEFAULT_PRIMARY_LLM_CAMPAIGN_ID}`",
            "`openai-gpt53codex-xhigh-agent-fullsec-real-2026-02-27`",
            f"`{compare_campaign.track_id}`",
            f"`{compare_campaign.track_slug}`",
            "runtime-visible",
            "runtime_visible=true",
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


def _check_master_starters(master_starters_path: Path, master_manifest_path: Path, campaign_slug: str, execution_venue: str) -> None:
    if not master_starters_path.exists():
        raise SystemExit(f"Missing master starters file: {master_starters_path}")
    if not master_manifest_path.exists():
        raise SystemExit(f"Missing master manifest file: {master_manifest_path}")

    starters_text = master_starters_path.read_text(encoding="utf-8-sig")
    _assert_markers_present(
        "master_starters",
        starters_text,
        [
            "Execution focus: use only the declared pair/year input files plus this embedded prompt contract.",
            "Forbidden sources: do not inspect existing output artifacts",
            "JOB_META",
            "\"job_id\":",
            "\"model_provider\":",
            "\"model_name\":",
            "\"run_label_template\":",
            "\"provenance_input_file\":",
            "\"expected_prev_paragraphs\":",
            "\"expected_curr_paragraphs\":",
            "\"expected_pair_sha256\":",
            "\"expected_prev_sha256\":",
            "\"expected_curr_sha256\":",
            "\"projected_output_path_runtime\":",
            "texts.paragraphs",
            "preflight input lock mismatch",
            "--artifact-id \"llm_outline_compare_runtime\"",
            "--target-field \"projected_master_output_runtime\"",
            "--only-mode \"exact_path\"",
            "--expect-target-count 1",
            "--fail-if-target-count-mismatch",
            "lab_audit_master_output_quality.py --output",
            "--strict-depth",
            "python -c \"import json, pathlib;",
        ],
    )
    _assert_markers_absent(
        "master_starters",
        starters_text,
        [
            "year_payload.texts.paragraphs",
        ],
    )
    if "> NUL" in starters_text:
        raise SystemExit("master_starters includes shell-fragile `> NUL` redirection.")

    format_match = re.search(r"- output format: `([^`]+)`", starters_text)
    starter_format = format_match.group(1) if format_match else ""
    is_v5 = starter_format in {"vscode_autowrite_insight_exp", "chatgpt_desktop_insight_exp"}
    is_v4 = starter_format in {"vscode_autowrite_structured_prod", "chatgpt_desktop_structured_prod"}
    is_chatgpt_desktop = execution_venue == EXECUTION_VENUE_CHATGPT_DESKTOP

    validate_pairs = _extract_validate_pairs(starters_text)
    if is_v5:
        if is_chatgpt_desktop:
            _assert_markers_present(
                "master_starters_v5_chatgpt_desktop",
                starters_text,
                [
                    "COPY FROM NEXT LINE THROUGH END_STARTER AND PASTE INTO A FRESH CHATGPT DESKTOP THREAD:",
                    "Execution mode: MANUAL_CHATGPT_DESKTOP_INSIGHT_EXP",
                    "INPUT_ATTACHMENTS (attach before generation):",
                    "LOCAL_POSTCHECK (run in workspace terminal after saving model JSON):",
                    "Operator save target for insight JSON (you cannot write files directly from this chat):",
                    "\"output_path_insight\":",
                    "--artifact-id \"llm_outline_compare_insight\"",
                    "--target-field \"projected_master_output_structured\"",
                    "lab_project_master_v3_to_v2.py",
                    "Build `llm_outline_compare_insight`",
                    "`executive_digest`",
                    "`insight_cards`",
                    "`evidence_map`",
                    "`ui_contract`",
                ],
            )
            _assert_markers_absent(
                "master_starters_v5_chatgpt_desktop",
                starters_text,
                [
                    "You are Codex operating inside this workspace. Execute this job end-to-end.",
                    "You are ChatGPT running a manual desktop job for this workspace.",
                    "1. Reads pair/year files directly from workspace",
                    "PRECHECK_OK ticker=",
                    "COPY FROM NEXT LINE THROUGH END_STARTER AND PASTE INTO A FRESH CODEX THREAD:",
                    "Execution mode: AUTOWRITE_VALIDATE_INSIGHT_EXP",
                    "Windows-safe write guardrail (required for large artifacts):",
                    "Write output JSON directly to this structured path:",
                    "Write output JSON directly to this insight path:",
                    "Build `llm_outline_compare_structured`",
                ],
            )
        else:
            _assert_markers_present(
                "master_starters_v5",
                starters_text,
                [
                    "Execution mode: AUTOWRITE_VALIDATE_INSIGHT_EXP",
                    "\"output_path_insight\":",
                    "--artifact-id \"llm_outline_compare_insight\"",
                    "--target-field \"projected_master_output_structured\"",
                    "lab_project_master_v3_to_v2.py",
                    "Build `llm_outline_compare_insight`",
                    "`executive_digest`",
                    "`insight_cards`",
                    "`evidence_map`",
                    "`ui_contract`",
                    "Windows-safe write guardrail (required for large artifacts):",
                    "Do not use one-shot oversized inline write commands for large JSON writes.",
                    "temporary workspace-relative generator script path",
                    "`Set-Content` + `Add-Content`",
                ],
            )
            _assert_markers_absent(
                "master_starters_v5",
                starters_text,
                [
                    "Build `llm_outline_compare_structured`",
                ],
            )
    elif is_v4:
        if is_chatgpt_desktop:
            _assert_markers_present(
                "master_starters_v4_chatgpt_desktop",
                starters_text,
                [
                    "COPY FROM NEXT LINE THROUGH END_STARTER AND PASTE INTO A FRESH CHATGPT DESKTOP THREAD:",
                    "Execution mode: MANUAL_CHATGPT_DESKTOP_STRUCTURED_PROD",
                    "INPUT_ATTACHMENTS (attach before generation):",
                    "LOCAL_POSTCHECK (run in workspace terminal after saving model JSON):",
                    "Operator save target (you cannot write files directly from this chat):",
                    "\"output_path_structured\":",
                    "--artifact-id \"llm_outline_compare_structured\"",
                    "--target-field \"master_output\"",
                    "lab_project_master_v2_to_v1.py",
                    "Build `llm_outline_compare_structured`",
                ],
            )
            _assert_markers_absent(
                "master_starters_v4_chatgpt_desktop",
                starters_text,
                [
                    "You are Codex operating inside this workspace. Execute this job end-to-end.",
                    "You are ChatGPT running a manual desktop job for this workspace.",
                    "1. Reads pair/year files directly from workspace",
                    "PRECHECK_OK ticker=",
                    "COPY FROM NEXT LINE THROUGH END_STARTER AND PASTE INTO A FRESH CODEX THREAD:",
                    "Execution mode: AUTOWRITE_VALIDATE_STRUCTURED_PROD",
                    "Windows-safe write guardrail (required for large artifacts):",
                    "Write output JSON directly to this structured path:",
                    "Write output JSON directly to this insight path:",
                ],
            )
        else:
            _assert_markers_present(
                "master_starters_v4",
                starters_text,
                [
                    "Execution mode: AUTOWRITE_VALIDATE_STRUCTURED_PROD",
                    "\"output_path_structured\":",
                    "--artifact-id \"llm_outline_compare_structured\"",
                    "--target-field \"master_output\"",
                    "lab_project_master_v2_to_v1.py",
                    "Build `llm_outline_compare_structured`",
                    "Windows-safe write guardrail (required for large artifacts):",
                    "Do not use one-shot oversized inline write commands for large JSON writes.",
                    "temporary workspace-relative generator script path",
                    "`Set-Content` + `Add-Content`",
                ],
            )
            _assert_markers_absent(
                "master_starters_v4",
                starters_text,
                [
                    "--target-field \"projected_master_output_structured\"",
                    "lab_project_master_v3_to_v2.py",
                    "Build `llm_outline_compare_insight`",
                ],
            )
    else:
        raise SystemExit("master_starters output format must be one of vscode_autowrite_structured_prod, chatgpt_desktop_structured_prod, vscode_autowrite_insight_exp, or chatgpt_desktop_insight_exp")

    expected_pairs = {
        ("llm_outline_compare_structured", "master_output"),
        ("llm_outline_compare_runtime", "projected_master_output_runtime"),
    }
    if is_v5:
        expected_pairs = {
            ("llm_outline_compare_insight", "master_output"),
            ("llm_outline_compare_structured", "projected_master_output_structured"),
            ("llm_outline_compare_runtime", "projected_master_output_runtime"),
        }
    missing_pairs = sorted(pair for pair in expected_pairs if pair not in validate_pairs)
    if missing_pairs:
        formatted = ", ".join(f"{a}/{t}" for a, t in missing_pairs)
        raise SystemExit(f"master_starters missing required validate artifact/target-field pair(s): {formatted}")

    allowed_pairs = expected_pairs | {
        ("llm_outline_compare_structured", "master_output"),
        ("llm_outline_compare_insight", "master_output"),
    }
    unexpected_pairs = sorted(pair for pair in validate_pairs if pair not in allowed_pairs)
    if unexpected_pairs:
        formatted = ", ".join(f"{a}/{t}" for a, t in unexpected_pairs)
        raise SystemExit(
            "master_starters includes incompatible validate artifact/target-field pair(s): "
            + formatted
        )

    manifest_payload = json.loads(master_manifest_path.read_text(encoding="utf-8-sig"))
    if not isinstance(manifest_payload, dict):
        raise SystemExit("master manifest root must be an object")
    manifest_data = cast(dict[str, Any], manifest_payload)
    entries = manifest_data.get("entries")
    if not isinstance(entries, list):
        raise SystemExit("master manifest missing entries list")

    expected_paths: list[str] = []
    manifest_issues: list[str] = []
    expected_focus_signal_ids: list[str] = []
    for entry in entries:  # type: ignore[reportUnknownVariableType]
        if not isinstance(entry, dict):
            continue
        entry_data = cast(dict[str, Any], entry)
        ticker = str(entry_data.get("ticker") or "?")
        year_from = str(entry_data.get("year_from") or "?")
        year_to = str(entry_data.get("year_to") or "?")
        lens = str(entry_data.get("lens") or "?")
        case_label = f"{ticker} {year_from}-{year_to} {lens}"

        master_output = entry_data.get("master_output")
        if not isinstance(master_output, dict):
            continue
        master_data = cast(dict[str, Any], master_output)
        master_path = master_data.get("expected_output_path")
        if not isinstance(master_path, str):
            continue
        normalized_master = master_path.replace("\\", "/").lstrip("/")
        if f"/{campaign_slug}/" not in "/" + normalized_master:
            continue

        master_artifact_id = master_data.get("artifact_id")
        projected_v2 = entry_data.get("projected_master_output_structured")
        projected_v1 = entry_data.get("projected_master_output_runtime")

        if is_v5:
            if master_artifact_id != "llm_outline_compare_insight" or "llm_outline_compare_insight" not in normalized_master:
                manifest_issues.append(case_label + ": master_output must be llm_outline_compare_insight")
                continue
            if not isinstance(projected_v2, dict):
                manifest_issues.append(case_label + ": missing projected_master_output_structured")
                continue
            projected_v2_data = cast(dict[str, Any], projected_v2)
            projected_v2_path = projected_v2_data.get("expected_output_path")
            if not isinstance(projected_v2_path, str):
                manifest_issues.append(case_label + ": projected_master_output_structured missing expected_output_path")
                continue
            normalized_v2 = projected_v2_path.replace("\\", "/").lstrip("/")
            if projected_v2_data.get("artifact_id") != "llm_outline_compare_structured" or "llm_outline_compare_structured" not in normalized_v2:
                manifest_issues.append(case_label + ": projected_master_output_structured must be llm_outline_compare_structured")
                continue
            if not isinstance(projected_v1, dict):
                manifest_issues.append(case_label + ": missing projected_master_output_runtime")
                continue
            projected_v1_data = cast(dict[str, Any], projected_v1)
            projected_v1_path = projected_v1_data.get("expected_output_path")
            if not isinstance(projected_v1_path, str):
                manifest_issues.append(case_label + ": projected_master_output_runtime missing expected_output_path")
                continue

            expected_paths.append(normalized_master)
            expected_paths.append(normalized_v2)
            expected_paths.append(projected_v1_path.replace("\\", "/").lstrip("/"))
        else:
            if master_artifact_id not in {None, "llm_outline_compare_structured"} or "llm_outline_compare_structured" not in normalized_master:
                manifest_issues.append(case_label + ": master_output must be llm_outline_compare_structured for v4 starters")
                continue
            if not isinstance(projected_v1, dict):
                manifest_issues.append(case_label + ": missing projected_master_output_runtime")
                continue
            projected_v1_data = cast(dict[str, Any], projected_v1)
            projected_v1_path = projected_v1_data.get("expected_output_path")
            if not isinstance(projected_v1_path, str):
                manifest_issues.append(case_label + ": projected_master_output_runtime missing expected_output_path")
                continue

            expected_paths.append(normalized_master)
            expected_paths.append(projected_v1_path.replace("\\", "/").lstrip("/"))

        for signal_id in _collect_focus_signal_ids_from_entry(entry_data):
            if signal_id not in expected_focus_signal_ids:
                expected_focus_signal_ids.append(signal_id)

    if manifest_issues:
        raise SystemExit(
            "master manifest starter-compatibility issues:\n"
            + "\n".join(f"- {item}" for item in manifest_issues[:10])
        )
    if not expected_paths:
        raise SystemExit("master manifest yielded no campaign paths for starter verification")

    only_tokens = re.findall(r'--only "([^"]+)"', starters_text)
    if not only_tokens:
        raise SystemExit("master starters missing --only tokens")
    normalized_tokens = [token.replace("\\", "/").lstrip("/") for token in only_tokens]
    expected_set = set(expected_paths)
    token_set = set(normalized_tokens)
    unknown = sorted(token for token in token_set if token not in expected_set)
    if unknown:
        raise SystemExit(
            "starter --only tokens include paths not present in manifest targets: "
            + ", ".join(unknown[:5])
        )
    missing_expected = sorted(path for path in expected_set if path not in token_set)
    if missing_expected:
        raise SystemExit(
            "starter --only tokens missing expected manifest targets: "
            + ", ".join(missing_expected[:5])
        )
    if expected_focus_signal_ids:
        _assert_markers_present(
            "master_starters_focus_signals",
            starters_text,
            ["CASE-SPECIFIC COVERAGE GATE"] + expected_focus_signal_ids,
        )

def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    resolved_campaign_id = _resolve_campaign_id(args.campaign_id, args.master_manifest)
    campaign = get_llm_campaign(resolved_campaign_id)
    if campaign is None or campaign.instructions_asset_name is None:
        raise SystemExit(f"Unknown campaign id: {resolved_campaign_id}")

    prompt_templates_override = args.prompt_templates or ""
    bundle_paths = resolve_bundle_paths(
        args.bundle or None,
        None,
        None,
        prompt_templates_override or None,
    )
    prompt_path = resolve_prompt_templates_path(
        bundle_paths=bundle_paths,
        campaign_id=campaign.track_id,
        campaign_slug=campaign.track_slug,
        prompt_templates_override=prompt_templates_override,
    )

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

    expected_instructions = build_project_instructions_lines(
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
            "`llm_outline_compare_structured`",
            "`llm_outline_compare_runtime`",
            "`analysis_expectations.focus_signals`",
            "Evidence snippets must be `<=350` chars.",
            "`material_changes` must have at least `4` rows.",
            "Required signal surfacing is evaluated on surfaced analytical sections, not evidence-bank presence alone.",
            "`provenance.run_label` must start with `YYYY-MM-DD_`.",
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
        execution_venue=campaign.execution_venue,
    )

    lock_issues = verify_master_input_locks(
        bundle_arg=str(bundle_paths.bundle_root),
        master_manifest_path=master_manifest_path,
        master_starters_path=master_starters_path,
    )
    if lock_issues:
        preview = "\n".join(
            f"- [{issue.layer}] {issue.code}: {issue.detail}" for issue in lock_issues[:10]
        )
        raise SystemExit(
            "master input lock verification failed:\n" + preview
        )

    print("Prompt consistency check: PASS")
    print(f"Script: {SCRIPT_VERSION}")
    print(f"Campaign: {campaign.track_id}")
    print(f"Prompt templates: {prompt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())










