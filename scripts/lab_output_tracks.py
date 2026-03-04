from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from lab_script_version import build_script_version

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")

RUN_LABEL_DATE_PREFIX = "YYYY-MM-DD"
RUN_LABEL_PATTERN = r"^20\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])_[A-Za-z0-9._-]+$"

LLM_DETECTORS = (
    "det_llm_delta_brief_v1",
    "det_llm_excerpt_picker_v1",
)

MASTER_LLM_ARTIFACT_ID = "llm_outline_compare_v1"
MASTER_LLM_ARTIFACT_ID_V2 = "llm_outline_compare_v2"
MASTER_LLM_RESEARCH_ARTIFACT_ID = "llm_outline_research_v1"
MASTER_PROMPT_VERSION = "llm_master_compare_v3"

DETERMINISTIC_DETECTORS = (
    "det_logodds_terms_v1",
    "det_jsd_ngrams_v1",
    "det_minhash_boilerplate_v1",
    "det_winnowing_fingerprint_v1",
    "det_structure_artifacts_v1",
    "det_rbo_agreement_v1",
)

ALL_TRACKED_DETECTORS = tuple(sorted(set(LLM_DETECTORS + DETERMINISTIC_DETECTORS)))


@dataclass(frozen=True)
class OutputTrack:
    track_id: str
    track_slug: str
    display_name: str
    kind: str
    input_mode: Optional[str] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    run_label_prefix_template: Optional[str] = None
    instructions_asset_name: Optional[str] = None
    primary_for_runtime: bool = False
    compare_default: bool = False
    runtime_visible: bool = True


DETERMINISTIC_BASELINE_TRACK = OutputTrack(
    track_id="det_baseline_2026-02-21",
    track_slug="det-baseline-2026-02-21",
    display_name="Deterministic Baseline (2026-02-21)",
    kind="deterministic",
    input_mode="deterministic",
    primary_for_runtime=True,
)

LLM_CAMPAIGNS: tuple[OutputTrack, ...] = (
    OutputTrack(
        track_id="openai_chatgpt52ext_agent_2026-02-21",
        track_slug="openai-chatgpt52ext-agent-2026-02-21",
        display_name="ChatGPT 5.2-Thinking (Extended Thinking)",
        kind="llm",
        input_mode="focuspack_v1",
        model_provider="openai",
        model_name="ChatGPT 5.2-Thinking (Extended Thinking)",
        run_label_prefix_template=f"{RUN_LABEL_DATE_PREFIX}_openai_chatgpt52ext_...",
        instructions_asset_name="llm_project_instructions_openai_chatgpt52ext_agent_2026-02-21.txt",
        primary_for_runtime=False,
        runtime_visible=False,
    ),
    OutputTrack(
        track_id="openai_gpt53codex_xhigh_agent_2026-02-21",
        track_slug="openai-gpt53codex-xhigh-agent-2026-02-21",
        display_name="GPT-5.3-Codex (Extra High Reasoning, Agent Mode)",
        kind="llm",
        input_mode="focuspack_v1",
        model_provider="openai",
        model_name="GPT-5.3-Codex (Extra High Reasoning, Agent Mode)",
        run_label_prefix_template=f"{RUN_LABEL_DATE_PREFIX}_openai_gpt53codex_...",
        instructions_asset_name="llm_project_instructions_openai_gpt53codex_xhigh_agent_2026-02-21.txt",
        compare_default=False,
        runtime_visible=False,
    ),
    OutputTrack(
        track_id="openai_gpt53codex_xhigh_agent_fullsec_2026-02-22",
        track_slug="openai-gpt53codex-xhigh-agent-fullsec-2026-02-22",
        display_name="GPT-5.3-Codex (Full Section v2, Synthetic Baseline)",
        kind="llm",
        input_mode="full_section_v2",
        model_provider="openai",
        model_name="GPT-5.3-Codex (Extra High Reasoning, Agent Mode)",
        run_label_prefix_template=f"{RUN_LABEL_DATE_PREFIX}_openai_gpt53codex_fullsec_...",
        instructions_asset_name="llm_project_instructions_openai_gpt53codex_xhigh_agent_fullsec_2026-02-22.txt",
        primary_for_runtime=False,
        runtime_visible=False,
    ),
    OutputTrack(
        track_id="openai_chatgpt52ext_agent_fullsec_2026-02-22",
        track_slug="openai-chatgpt52ext-agent-fullsec-2026-02-22",
        display_name="ChatGPT 5.2-Thinking (Extended Thinking) (Full Section v2, Synthetic Baseline)",
        kind="llm",
        input_mode="full_section_v2",
        model_provider="openai",
        model_name="ChatGPT 5.2-Thinking (Extended Thinking)",
        run_label_prefix_template=f"{RUN_LABEL_DATE_PREFIX}_openai_chatgpt52ext_fullsec_...",
        instructions_asset_name="llm_project_instructions_openai_chatgpt52ext_agent_fullsec_2026-02-22.txt",
        compare_default=False,
        runtime_visible=False,
    ),
    OutputTrack(
        track_id="openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27",
        track_slug="openai-gpt53codex-xhigh-agent-fullsec-real-2026-02-27",
        display_name="GPT-5.3-Codex (Full Section v2, Real Manual Runs)",
        kind="llm",
        input_mode="full_section_v2",
        model_provider="openai",
        model_name="GPT-5.3-Codex (Extra High Reasoning, Agent Mode)",
        run_label_prefix_template=f"{RUN_LABEL_DATE_PREFIX}_openai_gpt53codex_fullsec_real_...",
        instructions_asset_name="llm_project_instructions_openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27.txt",
        primary_for_runtime=True,
        runtime_visible=True,
    ),
    OutputTrack(
        track_id="openai_chatgpt52ext_agent_fullsec_real_2026-02-27",
        track_slug="openai-chatgpt52ext-agent-fullsec-real-2026-02-27",
        display_name="ChatGPT 5.2-Thinking (Extended Thinking) (Full Section v2, Real Manual Runs)",
        kind="llm",
        input_mode="full_section_v2",
        model_provider="openai",
        model_name="ChatGPT 5.2-Thinking (Extended Thinking)",
        run_label_prefix_template=f"{RUN_LABEL_DATE_PREFIX}_openai_chatgpt52ext_fullsec_real_...",
        instructions_asset_name="llm_project_instructions_openai_chatgpt52ext_agent_fullsec_real_2026-02-27.txt",
        compare_default=True,
        runtime_visible=False,
    ),
)

TRACKS_BY_ID = {track.track_id: track for track in (DETERMINISTIC_BASELINE_TRACK, *LLM_CAMPAIGNS)}
TRACKS_BY_SLUG = {track.track_slug: track for track in (DETERMINISTIC_BASELINE_TRACK, *LLM_CAMPAIGNS)}

DEFAULT_PRIMARY_LLM_CAMPAIGN_ID = "openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27"
DEFAULT_COMPARE_LLM_CAMPAIGN_ID = "openai_chatgpt52ext_agent_fullsec_real_2026-02-27"

FY2022_RUNTIME_CASES: dict[str, tuple[tuple[int, int], ...]] = {
    "NVDA": ((2022, 2023), (2023, 2024), (2024, 2025)),
    "KO": ((2022, 2023), (2023, 2024), (2024, 2025)),
    "WM": ((2022, 2023), (2023, 2024), (2024, 2025)),
    "GE": ((2022, 2023), (2023, 2024), (2024, 2025)),
}


def is_llm_detector(detector_id: str) -> bool:
    return detector_id in LLM_DETECTORS


def is_deterministic_detector(detector_id: str) -> bool:
    return detector_id in DETERMINISTIC_DETECTORS


def get_track(track_id: str) -> Optional[OutputTrack]:
    return TRACKS_BY_ID.get(track_id)


def get_llm_campaign(campaign_id: str) -> Optional[OutputTrack]:
    track = TRACKS_BY_ID.get(campaign_id)
    if track is None or track.kind != "llm":
        return None
    return track


def get_primary_llm_campaign() -> OutputTrack:
    campaign = get_llm_campaign(DEFAULT_PRIMARY_LLM_CAMPAIGN_ID)
    if campaign is None:
        raise SystemExit("Primary LLM campaign is not configured.")
    return campaign


def get_compare_default_llm_campaign() -> OutputTrack:
    campaign = get_llm_campaign(DEFAULT_COMPARE_LLM_CAMPAIGN_ID)
    if campaign is None:
        raise SystemExit("Compare-default LLM campaign is not configured.")
    return campaign


def get_track_slug_for_detector(detector_id: str, campaign_id: Optional[str] = None) -> str:
    if is_llm_detector(detector_id):
        selected = campaign_id or DEFAULT_PRIMARY_LLM_CAMPAIGN_ID
        campaign = get_llm_campaign(selected)
        if campaign is None:
            raise SystemExit(f"Unknown LLM campaign id: {selected}")
        return campaign.track_slug
    return DETERMINISTIC_BASELINE_TRACK.track_slug


def canonical_output_filename(
    detector_id: str,
    section: str,
    year_from: int,
    year_to: int,
    cleaning_lens: str,
    source_id: str,
    track_slug: str,
) -> str:
    return (
        f"lab_{detector_id}_{section}_{year_from}_{year_to}_"
        f"{cleaning_lens}_{source_id}__{track_slug}.json"
    )


def canonical_output_relative_path(
    ticker: str,
    detector_id: str,
    section: str,
    year_from: int,
    year_to: int,
    cleaning_lens: str,
    source_id: str,
    track_slug: str,
) -> str:
    filename = canonical_output_filename(
        detector_id=detector_id,
        section=section,
        year_from=year_from,
        year_to=year_to,
        cleaning_lens=cleaning_lens,
        source_id=source_id,
        track_slug=track_slug,
    )
    return f"{ticker.upper()}/outputs/{detector_id}/{track_slug}/{filename}"


def canonical_outline_compare_filename(
    section: str,
    year_from: int,
    year_to: int,
    cleaning_lens: str,
    source_id: str,
    track_slug: str,
    artifact_id: str = MASTER_LLM_ARTIFACT_ID,
) -> str:
    return (
        f"lab_{artifact_id}_{section}_{year_from}_{year_to}_"
        f"{cleaning_lens}_{source_id}__{track_slug}.json"
    )


def canonical_outline_compare_relative_path(
    ticker: str,
    section: str,
    year_from: int,
    year_to: int,
    cleaning_lens: str,
    source_id: str,
    track_slug: str,
    artifact_id: str = MASTER_LLM_ARTIFACT_ID,
) -> str:
    filename = canonical_outline_compare_filename(
        section=section,
        year_from=year_from,
        year_to=year_to,
        cleaning_lens=cleaning_lens,
        source_id=source_id,
        track_slug=track_slug,
        artifact_id=artifact_id,
    )
    return f"{ticker.upper()}/outputs/{artifact_id}/{track_slug}/{filename}"


def canonical_outline_compare_v2_filename(
    section: str,
    year_from: int,
    year_to: int,
    cleaning_lens: str,
    source_id: str,
    track_slug: str,
) -> str:
    return canonical_outline_compare_filename(
        section=section,
        year_from=year_from,
        year_to=year_to,
        cleaning_lens=cleaning_lens,
        source_id=source_id,
        track_slug=track_slug,
        artifact_id=MASTER_LLM_ARTIFACT_ID_V2,
    )


def canonical_outline_compare_v2_relative_path(
    ticker: str,
    section: str,
    year_from: int,
    year_to: int,
    cleaning_lens: str,
    source_id: str,
    track_slug: str,
) -> str:
    return canonical_outline_compare_relative_path(
        ticker=ticker,
        section=section,
        year_from=year_from,
        year_to=year_to,
        cleaning_lens=cleaning_lens,
        source_id=source_id,
        track_slug=track_slug,
        artifact_id=MASTER_LLM_ARTIFACT_ID_V2,
    )


def canonical_outline_research_filename(
    section: str,
    year_from: int,
    year_to: int,
    cleaning_lens: str,
    source_id: str,
    track_slug: str,
) -> str:
    return (
        f"lab_{MASTER_LLM_RESEARCH_ARTIFACT_ID}_{section}_{year_from}_{year_to}_"
        f"{cleaning_lens}_{source_id}__{track_slug}.json"
    )


def canonical_outline_research_relative_path(
    ticker: str,
    section: str,
    year_from: int,
    year_to: int,
    cleaning_lens: str,
    source_id: str,
    track_slug: str,
) -> str:
    filename = canonical_outline_research_filename(
        section=section,
        year_from=year_from,
        year_to=year_to,
        cleaning_lens=cleaning_lens,
        source_id=source_id,
        track_slug=track_slug,
    )
    return f"{ticker.upper()}/outputs/{MASTER_LLM_RESEARCH_ARTIFACT_ID}/{track_slug}/{filename}"


def strip_repo_prefix(path_value: str) -> str:
    normalized = path_value.replace("\\", "/")
    if normalized.startswith("public/data/sec_narrative_drift_lab/"):
        return normalized[len("public/data/sec_narrative_drift_lab/") :]
    return normalized
