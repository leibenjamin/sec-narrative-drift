from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional, cast


PairKey = tuple[str, int, int, str, str, str]


_PAIR_FOCUS_SIGNALS: dict[PairKey, list[dict[str, Any]]] = {
    (
        "WM",
        2024,
        2025,
        "10k_item1a",
        "raw",
        "edgar",
    ): [
        {
            "id": "wm_healthcare_solutions_execution_deterioration",
            "priority": "high",
            "focus_summary": (
                "Surface the 2025 Healthcare Solutions / Stericycle deterioration, especially the "
                "ERP, billing, collection, customer-loss, and planned-pricing-delay channel."
            ),
            "paragraph_hints": {
                "curr": [9],
            },
            "anchor_groups": [
                ["Healthcare Solutions", "Stericycle"],
                ["ERP", "billing", "collection", "customer loss", "planned pricing increases"],
            ],
            "surface_requirements": {
                "required_sections": ["material_changes"],
                "required_any_of_sections": ["change_mechanisms", "investor_relevance"],
                "top_material_change_rank_max": 3,
            },
        }
    ],
    (
        "GE",
        2024,
        2025,
        "10k_item1a",
        "raw",
        "edgar",
    ): [
        {
            "id": "ge_leap_services_execution_ramp",
            "priority": "high",
            "focus_summary": (
                "Surface the 2025 LEAP / GE9X installed-base and service-execution ramp, not just "
                "macro, policy, or generic operational framing."
            ),
            "paragraph_hints": {
                "curr": [18],
            },
            "anchor_groups": [
                ["LEAP", "GE9X"],
                [
                    "installed base",
                    "services",
                    "time on wing",
                    "repair turnaround",
                    "delivery",
                    "durability",
                ],
            ],
            "surface_requirements": {
                "required_sections": ["material_changes"],
                "required_any_of_sections": ["change_mechanisms", "investor_relevance"],
                "top_material_change_rank_max": 3,
            },
        }
    ],
}


def validate_focus_signal_paragraph_hints(
    analysis_expectations: Optional[dict[str, Any]],
    *,
    prev_paragraph_count: int,
    curr_paragraph_count: int,
) -> list[str]:
    if analysis_expectations is None:
        return []
    focus_signals_any = analysis_expectations.get("focus_signals")
    if not isinstance(focus_signals_any, list):
        return []

    issues: list[str] = []
    paragraph_counts = {
        "prev": prev_paragraph_count,
        "curr": curr_paragraph_count,
    }
    for signal_any in focus_signals_any:  # type: ignore[reportUnknownVariableType]
        if not isinstance(signal_any, dict):
            continue
        signal = cast(dict[str, Any], signal_any)
        signal_id = str(signal.get("id") or "unknown_signal")
        paragraph_hints_any: Any = signal.get("paragraph_hints")
        if not isinstance(paragraph_hints_any, dict):
            continue
        paragraph_hints = cast(dict[str, Any], paragraph_hints_any)
        for year_side, paragraph_count in paragraph_counts.items():
            hint_values: Any = paragraph_hints.get(year_side)
            if not isinstance(hint_values, list):
                continue
            for hint_value in hint_values:  # type: ignore[reportUnknownVariableType]
                if isinstance(hint_value, bool) or not isinstance(hint_value, int):
                    issues.append(
                        f"focus_signal={signal_id} {year_side}_paragraph_hint={hint_value!r} "
                        + f"is not an integer for paragraph_count={paragraph_count}"
                    )
                    continue
                if hint_value < 0 or hint_value >= paragraph_count:
                    issues.append(
                        f"focus_signal={signal_id} {year_side}_paragraph_hint={hint_value} "
                        + f"out of range for paragraph_count={paragraph_count}"
                    )
    return issues


def assert_focus_signal_paragraph_hints_valid(
    analysis_expectations: Optional[dict[str, Any]],
    *,
    prev_paragraph_count: int,
    curr_paragraph_count: int,
    context: str,
) -> None:
    issues = validate_focus_signal_paragraph_hints(
        analysis_expectations,
        prev_paragraph_count=prev_paragraph_count,
        curr_paragraph_count=curr_paragraph_count,
    )
    if not issues:
        return
    raise SystemExit(
        f"Invalid analysis_expectations paragraph_hints for {context}: "
        + "; ".join(issues)
    )


def get_pair_analysis_expectations(
    *,
    ticker: str,
    section: str,
    year_from: int,
    year_to: int,
    lens: str,
    source_id: str,
) -> Optional[dict[str, Any]]:
    key = (
        ticker.upper(),
        year_from,
        year_to,
        section.lower(),
        lens.lower(),
        source_id.lower(),
    )
    focus_signals = _PAIR_FOCUS_SIGNALS.get(key)
    if not focus_signals:
        return None
    return {
        "focus_signals": deepcopy(focus_signals),
    }
