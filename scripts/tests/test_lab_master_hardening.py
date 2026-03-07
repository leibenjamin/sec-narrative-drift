import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT_DIR.parent
sys.path.insert(0, str(ROOT_DIR))

import lab_audit_master_output_quality as quality_audit  # noqa: E402
import lab_emit_master_thread_starters as emit_starters  # noqa: E402
import lab_prompt_consistency_check as prompt_consistency  # noqa: E402
import lab_validate_llm_master_outputs as master_validate  # noqa: E402
from lab_output_tracks import (  # noqa: E402
    DEFAULT_COMPARE_LLM_CAMPAIGN_ID,
    DEFAULT_PRIMARY_LLM_CAMPAIGN_ID,
    get_llm_campaign,
)


PAIR_INPUT_FILE = "inputs/pair/NVDA_2022_2023_10k_item1a_raw_edgar.json"
AMBIGUOUS_PAIR_INPUT_FILE = "inputs/pair/NVDA_2022_2023_10k_item1a_raw_edgar.json"
YEAR_PREV_PATH = (
    REPO_ROOT
    / "bundles"
    / "showcase_llm_inputs_full_section_v2_20260222"
    / "inputs"
    / "year"
    / "NVDA_2022_10k_item1a_raw_edgar__pair_2022_2023.json"
)
YEAR_CURR_PATH = (
    REPO_ROOT
    / "bundles"
    / "showcase_llm_inputs_full_section_v2_20260222"
    / "inputs"
    / "year"
    / "NVDA_2023_10k_item1a_raw_edgar__pair_2022_2023.json"
)
FIXTURE_INPUTS_ROOT = YEAR_PREV_PATH.parents[1]
PAIR_INPUT_SOURCE_PATH = FIXTURE_INPUTS_ROOT / "pair" / "NVDA_2022_2023_10k_item1a_raw_edgar.json"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def first_sentence(paragraph: str) -> str:
    normalized = " ".join(paragraph.split())
    period_idx = normalized.find(".")
    if period_idx >= 0:
        candidate = normalized[: period_idx + 1]
    else:
        candidate = normalized
    return candidate[:340]


def load_year_paragraph(path: Path, idx: int) -> str:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload["texts"]["paragraphs"][idx]


def verbatim_snippet(paragraph: str, cap: int = 320) -> str:
    if len(paragraph) <= cap:
        return paragraph
    best_end = -1
    for marker in (". ", "; ", ", "):
        pos = paragraph.rfind(marker, 0, cap)
        if pos > best_end:
            best_end = pos
    if best_end >= 120:
        return paragraph[: best_end + 1]
    return paragraph[:cap]


def make_single_entry_manifest(
    campaign_id: str,
    expected_output_path_v2: str,
    expected_output_path_v1: str | None = None,
) -> dict[str, Any]:
    projected_v1 = (
        expected_output_path_v1
        if expected_output_path_v1 is not None
        else expected_output_path_v2.replace("/llm_outline_compare_structured/", "/llm_outline_compare_structured/")
    )
    return {
        "campaign": {
            "campaign_id": campaign_id,
            "display_name": "Unit Test Campaign",
        },
        "entries": [
            {
                "ticker": "NVDA",
                "year_from": 2022,
                "year_to": 2023,
                "section": "10k_item1a",
                "lens": "raw",
                "source_id": "edgar",
                "input": {
                    "source_path": "bundles/showcase_llm_inputs_full_section_v2_20260222/inputs/pair/NVDA_2022_2023_10k_item1a_raw_edgar.json",
                    "source_year_prev_path": "bundles/showcase_llm_inputs_full_section_v2_20260222/inputs/year/NVDA_2022_10k_item1a_raw_edgar__pair_2022_2023.json",
                    "source_year_curr_path": "bundles/showcase_llm_inputs_full_section_v2_20260222/inputs/year/NVDA_2023_10k_item1a_raw_edgar__pair_2022_2023.json",
                    "integrity": {
                        "pair_payload_sha256": "unit_pair_sha",
                        "prev_payload_sha256": "unit_prev_sha",
                        "curr_payload_sha256": "unit_curr_sha",
                    },
                },
                "master_output": {
                    "artifact_id": "llm_outline_compare_structured",
                    "expected_output_path": expected_output_path_v2,
                    "present": False,
                },
                "projected_master_output_runtime": {
                    "artifact_id": "llm_outline_compare_runtime",
                    "expected_output_path": projected_v1,
                    "present": False,
                },
            }
        ],
    }


def make_single_entry_manifest_v3(
    campaign_id: str,
    expected_output_path_v3: str,
    expected_output_path_v2: str,
    expected_output_path_v1: str,
) -> dict[str, Any]:
    return {
        "campaign": {
            "campaign_id": campaign_id,
            "display_name": "Unit Test Campaign",
        },
        "entries": [
            {
                "ticker": "NVDA",
                "year_from": 2022,
                "year_to": 2023,
                "section": "10k_item1a",
                "lens": "raw",
                "source_id": "edgar",
                "input": {
                    "source_path": "bundles/showcase_llm_inputs_full_section_v2_20260222/inputs/pair/NVDA_2022_2023_10k_item1a_raw_edgar.json",
                    "source_year_prev_path": "bundles/showcase_llm_inputs_full_section_v2_20260222/inputs/year/NVDA_2022_10k_item1a_raw_edgar__pair_2022_2023.json",
                    "source_year_curr_path": "bundles/showcase_llm_inputs_full_section_v2_20260222/inputs/year/NVDA_2023_10k_item1a_raw_edgar__pair_2022_2023.json",
                    "integrity": {
                        "pair_payload_sha256": "unit_pair_sha",
                        "prev_payload_sha256": "unit_prev_sha",
                        "curr_payload_sha256": "unit_curr_sha",
                    },
                },
                "master_output": {
                    "artifact_id": "llm_outline_compare_insight",
                    "expected_output_path": expected_output_path_v3,
                    "present": False,
                },
                "projected_master_output_structured": {
                    "artifact_id": "llm_outline_compare_structured",
                    "expected_output_path": expected_output_path_v2,
                    "present": False,
                },
                "projected_master_output_runtime": {
                    "artifact_id": "llm_outline_compare_runtime",
                    "expected_output_path": expected_output_path_v1,
                    "present": False,
                },
            }
        ],
    }


def build_valid_payload() -> dict[str, Any]:
    prev_p0 = load_year_paragraph(YEAR_PREV_PATH, 0)
    prev_p14 = load_year_paragraph(YEAR_PREV_PATH, 14)
    curr_p0 = load_year_paragraph(YEAR_CURR_PATH, 0)
    curr_p14 = load_year_paragraph(YEAR_CURR_PATH, 14)
    prev_snippet_0 = first_sentence(prev_p0)
    prev_snippet_14 = first_sentence(prev_p14)
    curr_snippet_0 = first_sentence(curr_p0)
    curr_snippet_14 = first_sentence(curr_p14)
    return {
        "lab_schema_version": "1.0",
        "artifact_schema_version": "1.0",
        "artifact_id": "llm_outline_compare_runtime",
        "ticker": "NVDA",
        "section": "10k_item1a",
        "source_id": "edgar",
        "cleaning_lens": "raw",
        "year_from": 2022,
        "year_to": 2023,
        "outline_prev": [
            {
                "node_id": "prev_1",
                "parent_id": None,
                "level": 1,
                "order": 0,
                "label": "Top-level risk framing",
                "risk_thesis": "The filing opens with broad investment-risk framing.",
                "evidence_paragraph_idx": [0],
            },
            {
                "node_id": "prev_1_1",
                "parent_id": "prev_1",
                "level": 2,
                "order": 0,
                "label": "Supply and foundry dependency",
                "risk_thesis": "Foundry and fabrication dependence can constrain execution.",
                "evidence_paragraph_idx": [14],
            },
            {
                "node_id": "prev_1_1_1",
                "parent_id": "prev_1_1",
                "level": 3,
                "order": 0,
                "label": "Wafer fabrication dependence",
                "risk_thesis": "The company does not own wafer fabrication capacity.",
                "evidence_paragraph_idx": [14],
            },
        ],
        "outline_curr": [
            {
                "node_id": "curr_1",
                "parent_id": None,
                "level": 1,
                "order": 0,
                "label": "Top-level risk framing",
                "risk_thesis": "The filing opens with broad investment-risk framing.",
                "evidence_paragraph_idx": [0],
            },
            {
                "node_id": "curr_1_1",
                "parent_id": "curr_1",
                "level": 2,
                "order": 0,
                "label": "Evolving market needs",
                "risk_thesis": "Execution risk is tied to rapid platform and market change.",
                "evidence_paragraph_idx": [14],
            },
            {
                "node_id": "curr_1_1_1",
                "parent_id": "curr_1_1",
                "level": 3,
                "order": 0,
                "label": "Demand and adaptation cadence",
                "risk_thesis": "The business must match changing requirements and pace.",
                "evidence_paragraph_idx": [14],
            },
        ],
        "node_alignment": [
            {
                "prev_node_id": "prev_1",
                "curr_node_id": "curr_1",
                "change_class": "stable",
                "rationale": "Both years retain the same opening investment-risk framing structure.",
                "salience": 0.32,
            },
            {
                "prev_node_id": "prev_1_1",
                "curr_node_id": "curr_1_1",
                "change_class": "reworded",
                "rationale": "Current-year language shifts from fabrication dependence emphasis to explicit market-evolution pressure.",
                "salience": 0.81,
            },
        ],
        "material_changes": [
            {
                "change_class": "reworded",
                "title": "Fabrication dependence reframed as evolving-market execution pressure",
                "salience": 0.81,
                "summary": "Risk framing moves from manufacturing dependency specifics toward adaptation pace and market requirement shifts.",
                "caveat": "Evidence compares paragraph 14 across 2022 and 2023 only; adjacent paragraphs may contain additional qualifier language not cited here.",
                "evidence_refs": [
                    {"year": 2022, "paragraph_idx": 14},
                    {"year": 2023, "paragraph_idx": 14},
                ],
            }
        ],
        "evidence_bank": [
            {
                "year": 2022,
                "paragraph_idx": 0,
                "snippet": prev_snippet_0,
                "why": "Opening risk frame for 2022.",
                "node_ids": ["prev_1"],
            },
            {
                "year": 2023,
                "paragraph_idx": 0,
                "snippet": curr_snippet_0,
                "why": "Opening risk frame for 2023.",
                "node_ids": ["curr_1"],
            },
            {
                "year": 2022,
                "paragraph_idx": 14,
                "snippet": prev_snippet_14,
                "why": "Manufacturing and foundry dependency in 2022.",
                "node_ids": ["prev_1_1", "prev_1_1_1"],
            },
            {
                "year": 2023,
                "paragraph_idx": 14,
                "snippet": curr_snippet_14,
                "why": "Market-evolution framing in 2023.",
                "node_ids": ["curr_1_1", "curr_1_1_1"],
            },
        ],
        "lens_divergence": {
            "materially_different": False,
            "summary": "No lens divergence analysis included in this single-lens artifact.",
        },
        "provenance": {
            "input_file": PAIR_INPUT_FILE,
            "model_provider": "unit_provider",
            "model_name": "unit_model",
            "run_label": "2026-03-01_unit_hardening",
        },
    }


def build_valid_v2_strict_payload() -> dict[str, Any]:
    prev_indices = [5, 20, 40, 70]
    curr_indices = [15, 30, 45, 80]
    prev_paragraphs = {idx: load_year_paragraph(YEAR_PREV_PATH, idx) for idx in prev_indices}
    curr_paragraphs = {idx: load_year_paragraph(YEAR_CURR_PATH, idx) for idx in curr_indices}
    prev_opening = load_year_paragraph(YEAR_PREV_PATH, 0)
    curr_opening = load_year_paragraph(YEAR_CURR_PATH, 0)

    evidence_bank: list[dict[str, Any]] = []
    for idx in prev_indices:
        evidence_bank.append(
            {
                "year": 2022,
                "paragraph_idx": idx,
                "snippet": verbatim_snippet(prev_paragraphs[idx]),
                "why": f"2022 paragraph {idx} evidence for strict-depth test.",
                "node_ids": ["prev_root", "prev_ops"],
            }
        )
    for idx in curr_indices:
        evidence_bank.append(
            {
                "year": 2023,
                "paragraph_idx": idx,
                "snippet": verbatim_snippet(curr_paragraphs[idx]),
                "why": f"2023 paragraph {idx} evidence for strict-depth test.",
                "node_ids": ["curr_root", "curr_ops"],
            }
        )
    evidence_bank.append(
        {
            "year": 2022,
            "paragraph_idx": 0,
            "snippet": verbatim_snippet(prev_opening),
            "why": "Opening paragraph evidence for strict-depth mutation tests.",
            "node_ids": ["prev_root"],
        }
    )
    evidence_bank.append(
        {
            "year": 2023,
            "paragraph_idx": 0,
            "snippet": verbatim_snippet(curr_opening),
            "why": "Opening paragraph evidence for strict-depth mutation tests.",
            "node_ids": ["curr_root"],
        }
    )

    return {
        "lab_schema_version": "1.0",
        "artifact_schema_version": "1.0",
        "artifact_id": "llm_outline_compare_structured",
        "ticker": "NVDA",
        "section": "10k_item1a",
        "source_id": "edgar",
        "cleaning_lens": "raw",
        "year_from": 2022,
        "year_to": 2023,
        "outline_prev": [
            {
                "node_id": "prev_root",
                "parent_id": None,
                "level": 1,
                "order": 0,
                "label": "Primary 2022 risk frame",
                "risk_thesis": "The 2022 filing highlights operating-model, security, and policy exposures.",
                "evidence_paragraph_idx": [5],
            },
            {
                "node_id": "prev_ops",
                "parent_id": "prev_root",
                "level": 2,
                "order": 0,
                "label": "Operations and demand risk",
                "risk_thesis": "Execution depends on demand visibility and resilient operating systems.",
                "evidence_paragraph_idx": [20],
            },
            {
                "node_id": "prev_ops_detail",
                "parent_id": "prev_ops",
                "level": 3,
                "order": 0,
                "label": "Legal and policy exposure",
                "risk_thesis": "Legal and policy constraints can pressure flexibility and execution.",
                "evidence_paragraph_idx": [70],
            },
        ],
        "outline_curr": [
            {
                "node_id": "curr_root",
                "parent_id": None,
                "level": 1,
                "order": 0,
                "label": "Primary 2023 risk frame",
                "risk_thesis": "The 2023 filing emphasizes platform adoption, cyber exposure, and policy pressure.",
                "evidence_paragraph_idx": [15],
            },
            {
                "node_id": "curr_ops",
                "parent_id": "curr_root",
                "level": 2,
                "order": 0,
                "label": "Demand and ecosystem execution",
                "risk_thesis": "Execution depends on developers, ecosystem adoption, and customer demand timing.",
                "evidence_paragraph_idx": [30],
            },
            {
                "node_id": "curr_ops_detail",
                "parent_id": "curr_ops",
                "level": 3,
                "order": 0,
                "label": "Regulatory and legal exposure",
                "risk_thesis": "Policy and legal constraints can impose compliance and market-access costs.",
                "evidence_paragraph_idx": [80],
            },
        ],
        "node_alignment": [
            {
                "prev_node_id": "prev_root",
                "curr_node_id": "curr_root",
                "change_class": "stable",
                "rationale": "Both years retain an umbrella framing where execution risk links demand, operations, and compliance.",
                "salience": 0.45,
            },
            {
                "prev_node_id": "prev_ops",
                "curr_node_id": "curr_ops",
                "change_class": "intensified",
                "rationale": "Current-year language ties execution risk more explicitly to external ecosystem adoption channels.",
                "salience": 0.77,
            },
            {
                "prev_node_id": "prev_ops_detail",
                "curr_node_id": "curr_ops_detail",
                "change_class": "reworded",
                "rationale": "Policy and legal exposure remains present but is reframed with updated implementation details.",
                "salience": 0.66,
            },
        ],
        "material_changes": [
            {
                "id": "mc_1",
                "title": "Demand-shaping exposure at 2022 para 5 and 2023 para 15",
                "change_class": "intensified",
                "salience": 0.96,
                "caveat": "Evidence is limited to 2022 para 5 and 2023 para 15, so adjacent paragraphs may contain additional qualifiers not captured in this mapping.",
                "evidence_refs": [
                    {"year": 2022, "paragraph_idx": 5},
                    {"year": 2023, "paragraph_idx": 15},
                ],
            },
            {
                "id": "mc_2",
                "title": "Execution-channel dependence at 2022 para 20 and 2023 para 30",
                "change_class": "reworded",
                "salience": 0.90,
                "caveat": "This comparison anchors on para 20 and para 30, so statement-level differences outside those references are not exhaustively mapped.",
                "evidence_refs": [
                    {"year": 2022, "paragraph_idx": 20},
                    {"year": 2023, "paragraph_idx": 30},
                ],
            },
            {
                "id": "mc_3",
                "title": "Cyber and system continuity pressure at 2022 para 40 and 2023 para 45",
                "change_class": "intensified",
                "salience": 0.84,
                "caveat": "The cited evidence is paragraph-bounded (2022 para 40 and 2023 para 45) and does not quantify incident probability or loss distribution.",
                "evidence_refs": [
                    {"year": 2022, "paragraph_idx": 40},
                    {"year": 2023, "paragraph_idx": 45},
                ],
            },
            {
                "id": "mc_4",
                "title": "Policy and legal operating constraints at 2022 para 70 and 2023 para 80",
                "change_class": "reworded",
                "salience": 0.79,
                "caveat": "Coverage is constrained to 2022 para 70 and 2023 para 80 and does not provide an estimated compliance-cost range.",
                "evidence_refs": [
                    {"year": 2022, "paragraph_idx": 70},
                    {"year": 2023, "paragraph_idx": 80},
                ],
            },
        ],
        "evidence_bank": evidence_bank,
        "lens_divergence": {
            "materially_different": False,
            "summary": "Single-lens unit fixture; no cross-lens divergence evidence is included.",
        },
        "risk_graph_prev": [
            {
                "id": "rg_prev_1",
                "driver": "Demand and operating-model volatility",
                "exposure": "Planning and resource-allocation mismatches",
                "impact": "Margin and execution variability",
                "evidence_paragraph_idx": [20],
            }
        ],
        "risk_graph_curr": [
            {
                "id": "rg_curr_1",
                "driver": "Ecosystem and cyber execution volatility",
                "exposure": "Platform adoption and continuity dependencies",
                "impact": "Revenue timing and operating disruption",
                "evidence_paragraph_idx": [30],
            }
        ],
        "change_mechanisms": [
            {
                "id": "mech_1",
                "mechanism": "Demand-shift pressure",
                "transmission_channel": "Customer and ecosystem adoption timing",
                "business_effect": "Forecast variance and operating leverage sensitivity",
                "time_horizon": "near_term",
                "evidence_refs": [
                    {"year": 2022, "paragraph_idx": 5},
                    {"year": 2023, "paragraph_idx": 15},
                ],
            },
            {
                "id": "mech_2",
                "mechanism": "Execution channel dependence",
                "transmission_channel": "Third-party development and deployment paths",
                "business_effect": "Commercialization timing risk",
                "time_horizon": "near_term",
                "evidence_refs": [
                    {"year": 2022, "paragraph_idx": 20},
                    {"year": 2023, "paragraph_idx": 30},
                ],
            },
            {
                "id": "mech_3",
                "mechanism": "System continuity and cyber pressure",
                "transmission_channel": "Operational control and incident response",
                "business_effect": "Service disruption and remediation cost",
                "time_horizon": "medium_term",
                "evidence_refs": [
                    {"year": 2022, "paragraph_idx": 40},
                    {"year": 2023, "paragraph_idx": 45},
                ],
            },
            {
                "id": "mech_4",
                "mechanism": "Policy and legal operating constraints",
                "transmission_channel": "Compliance and market-access requirements",
                "business_effect": "Higher operating cost and planning friction",
                "time_horizon": "medium_term",
                "evidence_refs": [
                    {"year": 2022, "paragraph_idx": 70},
                    {"year": 2023, "paragraph_idx": 80},
                ],
            },
        ],
        "uncertainty_and_limits": [
            {
                "id": "limit_1",
                "limitation": "This mapping uses selected paragraph anchors and does not fully resolve cross-paragraph dependency effects.",
                "evidence_refs": [
                    {"year": 2022, "paragraph_idx": 20},
                    {"year": 2023, "paragraph_idx": 30},
                ],
            }
        ],
        "investor_relevance": [
            {
                "id": "inv_1",
                "why_it_matters": "Execution-channel and policy constraints can alter revenue timing, cost structure, and risk-adjusted valuation ranges.",
                "evidence_refs": [
                    {"year": 2022, "paragraph_idx": 70},
                    {"year": 2023, "paragraph_idx": 80},
                ],
            }
        ],
        "projection_contract": {
            "projects_to_artifact_id": "llm_outline_compare_runtime",
            "projection_version": "1.0",
        },
        "provenance": {
            "input_file": PAIR_INPUT_FILE,
            "model_provider": "unit_provider",
            "model_name": "unit_model",
            "run_label": "2026-03-01_unit_hardening",
        },
    }


def build_valid_v3_payload() -> dict[str, Any]:
    base = build_valid_v2_strict_payload()
    base["artifact_id"] = "llm_outline_compare_insight"

    evidence_map: list[dict[str, Any]] = []
    evidence_id_by_pair: dict[tuple[int, int], str] = {}
    counter = 1
    for row in base["evidence_bank"]:
        year = row["year"]
        paragraph_idx = row["paragraph_idx"]
        evidence_id = f"ev_{counter}"
        counter += 1
        evidence_id_by_pair[(year, paragraph_idx)] = evidence_id
        evidence_map.append(
            {
                "evidence_id": evidence_id,
                "year": year,
                "paragraph_idx": paragraph_idx,
                "snippet": row["snippet"],
                "char_start": 0,
                "char_end": min(len(str(row["snippet"])), 120),
                "insight_ids": [],
            }
        )

    insight_specs = [
        ("ins_1", "difference", [(2022, 5)], [(2023, 15)], 0.93),
        ("ins_2", "difference", [(2022, 20)], [(2023, 30)], 0.88),
        ("ins_3", "similarity", [(2022, 40)], [(2023, 45)], 0.82),
        ("ins_4", "similarity", [(2022, 70)], [(2023, 80)], 0.77),
    ]

    insight_cards: list[dict[str, Any]] = []
    for insight_id, insight_type, prev_refs, curr_refs, salience in insight_specs:
        evidence_ref_ids = [
            evidence_id_by_pair[(year, paragraph_idx)]
            for year, paragraph_idx in [*prev_refs, *curr_refs]
            if (year, paragraph_idx) in evidence_id_by_pair
        ]
        for entry in evidence_map:
            if entry["evidence_id"] in evidence_ref_ids:
                entry["insight_ids"].append(insight_id)
        insight_cards.append(
            {
                "id": insight_id,
                "insight_type": insight_type,
                "title": f"Insight {insight_id} anchors para evidence",
                "claim": f"{insight_type.title()} framing for {insight_id} based on paired paragraph evidence.",
                "why_it_matters": f"{insight_id} matters for investment-case interpretation of risk transmission channels.",
                "salience": salience,
                "confidence_band": "medium",
                "evidence_refs_prev": [
                    {"year": year, "paragraph_idx": paragraph_idx}
                    for year, paragraph_idx in prev_refs
                ],
                "evidence_refs_curr": [
                    {"year": year, "paragraph_idx": paragraph_idx}
                    for year, paragraph_idx in curr_refs
                ],
                "evidence_ref_ids": evidence_ref_ids,
                "counterpoint_or_limit": f"{insight_id} is paragraph-bounded and may omit adjacent qualifier language.",
            }
        )

    base["executive_digest"] = {
        "summary_text": " ".join(["digest"] * 500),
        "audience": "investor_analyst",
        "reading_time_sec_estimate": 540,
    }
    base["insight_cards"] = insight_cards
    base["evidence_map"] = evidence_map
    base["insight_coverage"] = {
        "difference_count": 2,
        "similarity_count": 2,
        "per_year_evidence_spread": {"2022": 4, "2023": 4},
    }
    base["ui_contract"] = {
        "default_selected_insight_id": "ins_1",
        "recommended_insight_order": ["ins_1", "ins_2", "ins_3", "ins_4"],
        "suggested_clusters": [
            {
                "cluster_id": "cluster_core",
                "label": "Core",
                "insight_ids": ["ins_1", "ins_2", "ins_3", "ins_4"],
            }
        ],
    }
    return base


class TestMasterValidatorHardening(unittest.TestCase):
    def test_matches_only_token_modes(self) -> None:
        path_value = "public/data/sec_narrative_drift_lab/NVDA/outputs/x/y/z.json"
        self.assertTrue(master_validate.matches_only_token(path_value, "NVDA/outputs/x", "substring"))
        self.assertTrue(master_validate.matches_only_token(path_value, "z.json", "basename"))
        self.assertTrue(
            master_validate.matches_only_token(
                path_value,
                "public/data/sec_narrative_drift_lab/NVDA/outputs/x/y/z.json",
                "exact_path",
            )
        )
        self.assertFalse(
            master_validate.matches_only_token(
                path_value,
                "public/data/sec_narrative_drift_lab/KO/outputs/x/y/z.json",
                "exact_path",
            )
        )

    def test_target_count_mismatch_fails_when_enabled(self) -> None:
        campaign = get_llm_campaign(DEFAULT_PRIMARY_LLM_CAMPAIGN_ID)
        if campaign is None:
            self.fail("Default campaign not found for unit test.")
        expected_output_path = (
            f"public/data/sec_narrative_drift_lab/NVDA/outputs/llm_outline_compare_structured/"
            f"{campaign.track_slug}/unit_test_output.json"
        )
        manifest = make_single_entry_manifest(DEFAULT_PRIMARY_LLM_CAMPAIGN_ID, expected_output_path)
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "manifest.json"
            report_path = root / "report.md"
            write_json(manifest_path, manifest)
            rc = master_validate.main(
                [
                    "--manifest",
                    str(manifest_path),
                    "--campaign-id",
                    DEFAULT_PRIMARY_LLM_CAMPAIGN_ID,
                    "--report",
                    str(report_path),
                    "--allow-missing",
                    "--allow-invalid",
                    "--only",
                    "does-not-match-any-target",
                    "--only-mode",
                    "exact_path",
                    "--expect-target-count",
                    "1",
                    "--fail-if-target-count-mismatch",
                ]
            )
            self.assertEqual(rc, 1)
            report_text = report_path.read_text(encoding="utf-8")
            self.assertIn("| Targets | 0 |", report_text)


class TestStarterEmitterHardening(unittest.TestCase):
    def test_emitter_outputs_shell_safe_and_strict_target_args(self) -> None:
        campaign = get_llm_campaign(DEFAULT_PRIMARY_LLM_CAMPAIGN_ID)
        if campaign is None:
            self.fail("Default campaign not found for unit test.")
        expected_output_path = (
            f"public/data/sec_narrative_drift_lab/NVDA/outputs/llm_outline_compare_structured/"
            f"{campaign.track_slug}/unit_test_output.json"
        )
        manifest = make_single_entry_manifest(DEFAULT_PRIMARY_LLM_CAMPAIGN_ID, expected_output_path)
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "manifest.json"
            out_path = root / "starters.md"
            validation_report = root / "validation.md"
            quality_report = root / "quality.md"
            write_json(manifest_path, manifest)
            rc = emit_starters.main(
                [
                    "--manifest",
                    str(manifest_path),
                    "--out",
                    str(out_path),
                    "--validation-report",
                    str(validation_report),
                    "--quality-report",
                    str(quality_report),
                    "--format",
                    "vscode_autowrite",
                    "--allow-legacy-formats",
                ]
            )
            self.assertEqual(rc, 0)
            text = out_path.read_text(encoding="utf-8")
            self.assertNotIn("> NUL", text)
            self.assertIn("--only-mode \"exact_path\"", text)
            self.assertIn("--expect-target-count 1", text)
            self.assertIn("--fail-if-target-count-mismatch", text)
            self.assertIn("lab_audit_master_output_quality.py --output", text)
            self.assertIn("--strict-depth", text)
            self.assertIn("python -c \"import json, pathlib;", text)
            self.assertIn(f'--only "{expected_output_path}"', text)

    def test_emitter_legacy_format_requires_opt_in(self) -> None:
        campaign = get_llm_campaign(DEFAULT_PRIMARY_LLM_CAMPAIGN_ID)
        if campaign is None:
            self.fail("Default campaign not found for unit test.")
        expected_output_path = (
            f"public/data/sec_narrative_drift_lab/NVDA/outputs/llm_outline_compare_structured/"
            f"{campaign.track_slug}/unit_test_output.json"
        )
        manifest = make_single_entry_manifest(DEFAULT_PRIMARY_LLM_CAMPAIGN_ID, expected_output_path)
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "manifest_legacy_guard.json"
            out_path = root / "starters_legacy_guard.md"
            write_json(manifest_path, manifest)
            with self.assertRaises(SystemExit) as exc:
                emit_starters.main(
                    [
                        "--manifest",
                        str(manifest_path),
                        "--out",
                        str(out_path),
                        "--format",
                        "vscode_autowrite_v2",
                    ]
                )
            self.assertIn("Legacy starter formats are disabled by default", str(exc.exception))


    def test_emitter_default_format_is_v4(self) -> None:
        campaign = get_llm_campaign(DEFAULT_PRIMARY_LLM_CAMPAIGN_ID)
        if campaign is None:
            self.fail("Default campaign not found for unit test.")
        expected_output_path = (
            f"public/data/sec_narrative_drift_lab/NVDA/outputs/llm_outline_compare_structured/"
            f"{campaign.track_slug}/unit_test_output.json"
        )
        manifest = make_single_entry_manifest(DEFAULT_PRIMARY_LLM_CAMPAIGN_ID, expected_output_path)
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "manifest.json"
            out_path = root / "starters_default.md"
            write_json(manifest_path, manifest)
            rc = emit_starters.main(
                [
                    "--manifest",
                    str(manifest_path),
                    "--out",
                    str(out_path),
                ]
            )
            self.assertEqual(rc, 0)
            text = out_path.read_text(encoding="utf-8")
            self.assertIn("- output format: `vscode_autowrite_structured_prod`", text)
            self.assertIn("JOB_META", text)
            self.assertIn("OUTPUT_SHAPE_MIN", text)
            self.assertIn(
                "Execution focus: use only the declared pair/year input files plus this embedded prompt contract.",
                text,
            )
            self.assertIn("texts.paragraphs", text)
            self.assertNotIn("year_payload.texts.paragraphs", text)
            self.assertIn("--strict-depth", text)
            self.assertIn(
                "\"expected_pair_sha256\":",
                text,
            )
            self.assertIn("lab_project_master_v2_to_v1.py", text)

    def test_emitter_v4_preflight_lock_markers(self) -> None:
        campaign = get_llm_campaign(DEFAULT_PRIMARY_LLM_CAMPAIGN_ID)
        if campaign is None:
            self.fail("Default campaign not found for unit test.")
        expected_output_path = (
            f"public/data/sec_narrative_drift_lab/NVDA/outputs/llm_outline_compare_structured/"
            f"{campaign.track_slug}/unit_test_output.json"
        )
        manifest = make_single_entry_manifest(DEFAULT_PRIMARY_LLM_CAMPAIGN_ID, expected_output_path)
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "manifest.json"
            out_path = root / "starters_v4.md"
            write_json(manifest_path, manifest)
            rc = emit_starters.main(
                [
                    "--manifest",
                    str(manifest_path),
                    "--out",
                    str(out_path),
                    "--format",
                    "vscode_autowrite_structured_prod",
                ]
            )
            self.assertEqual(rc, 0)
            text = out_path.read_text(encoding="utf-8")
            self.assertIn("PREV_COUNT", text)
            self.assertIn("CURR_COUNT", text)
            self.assertIn("PRECHECK_MATCH prev=", text)
            self.assertIn("preflight input lock mismatch", text)
            self.assertIn("Forbidden sources: do not inspect existing output artifacts", text)
            self.assertIn("--only-mode \"exact_path\"", text)
            self.assertIn("--expect-target-count 1", text)
            self.assertIn("--fail-if-target-count-mismatch", text)
            self.assertIn("--target-field \"projected_master_output_runtime\"", text)
            self.assertIn("--strict-depth", text)
            self.assertIn("Windows-safe write guardrail (required for large artifacts):", text)
            self.assertIn("Do not use one-shot oversized inline write commands for large JSON writes.", text)
            self.assertIn("`Set-Content` + `Add-Content`", text)

    def test_emitter_v2_includes_job_meta_and_shape_min(self) -> None:
        campaign = get_llm_campaign(DEFAULT_PRIMARY_LLM_CAMPAIGN_ID)
        if campaign is None:
            self.fail("Default campaign not found for unit test.")
        expected_output_path = (
            f"public/data/sec_narrative_drift_lab/NVDA/outputs/llm_outline_compare_structured/"
            f"{campaign.track_slug}/unit_test_output.json"
        )
        manifest = make_single_entry_manifest(DEFAULT_PRIMARY_LLM_CAMPAIGN_ID, expected_output_path)
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "manifest.json"
            out_path = root / "starters_v2.md"
            write_json(manifest_path, manifest)
            rc = emit_starters.main(
                [
                    "--manifest",
                    str(manifest_path),
                    "--out",
                    str(out_path),
                    "--format",
                    "vscode_autowrite_v2",
                    "--allow-legacy-formats",
                ]
            )
            self.assertEqual(rc, 0)
            text = out_path.read_text(encoding="utf-8")
            self.assertIn("JOB_META", text)
            self.assertIn("\"model_provider\": \"openai\"", text)
            self.assertIn("OUTPUT_SHAPE_MIN", text)
            self.assertIn("Execution focus: do not inspect unrelated scripts/docs unless a required gate fails.", text)
            self.assertIn(
                "present_flag_mismatch can be non-blocking during incremental manual runs",
                text,
            )

    def test_chatgpt_master_starter_v4_markers(self) -> None:
        campaign = get_llm_campaign(DEFAULT_COMPARE_LLM_CAMPAIGN_ID)
        if campaign is None:
            self.fail("Compare campaign not found for unit test.")
        expected_output_path = (
            f"public/data/sec_narrative_drift_lab/NVDA/outputs/llm_outline_compare_structured/"
            f"{campaign.track_slug}/unit_test_output.json"
        )
        manifest = make_single_entry_manifest(DEFAULT_COMPARE_LLM_CAMPAIGN_ID, expected_output_path)
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "manifest_chatgpt.json"
            out_path = root / "starters_chatgpt_v4.md"
            write_json(manifest_path, manifest)
            rc = emit_starters.main(
                [
                    "--manifest",
                    str(manifest_path),
                    "--out",
                    str(out_path),
                    "--format",
                    "vscode_autowrite_structured_prod",
                ]
            )
            self.assertEqual(rc, 0)
            text = out_path.read_text(encoding="utf-8")
            self.assertIn("- output format: `vscode_autowrite_structured_prod`", text)
            self.assertIn("BEGIN_STARTER", text)
            self.assertIn("COPY FROM NEXT LINE THROUGH END_STARTER AND PASTE INTO A FRESH CHATGPT DESKTOP THREAD:", text)
            self.assertIn("Execution mode: MANUAL_CHATGPT_DESKTOP_STRUCTURED_PROD", text)
            self.assertIn("INPUT_ATTACHMENTS (attach before generation):", text)
            self.assertIn("LOCAL_POSTCHECK (run in workspace terminal after saving model JSON):", text)
            self.assertIn("Operator save target (you cannot write files directly from this chat):", text)
            self.assertNotIn("Write output JSON directly to this structured path:", text)
            self.assertIn("Execution focus: use only the declared pair/year input files plus this embedded prompt contract.", text)
            self.assertIn("JOB_META", text)
            self.assertIn("--strict-depth", text)
            self.assertIn("--only-mode \"exact_path\"", text)
            self.assertIn("--expect-target-count 1", text)
            self.assertIn("--fail-if-target-count-mismatch", text)
            self.assertIn(f'--only "{expected_output_path}"', text)
            self.assertNotIn("You are Codex operating inside this workspace. Execute this job end-to-end.", text)
            self.assertNotIn("Execution mode: AUTOWRITE_VALIDATE_STRUCTURED_PROD", text)
            self.assertNotIn("You are ChatGPT running a manual desktop job for this workspace.", text)
            self.assertNotIn("PRECHECK_OK ticker=", text)
            self.assertNotIn("reports/lab_llm_master_validation.md", text)
            self.assertNotIn("reports/lab_llm_master_quality.md", text)
            self.assertIn("1. Uses only the three attached input files", text)


    def test_emitter_v5_includes_v3_projection_chain(self) -> None:
        campaign = get_llm_campaign(DEFAULT_PRIMARY_LLM_CAMPAIGN_ID)
        if campaign is None:
            self.fail("Default campaign not found for unit test.")
        expected_output_path_v3 = (
            f"public/data/sec_narrative_drift_lab/NVDA/outputs/llm_outline_compare_insight/"
            f"{campaign.track_slug}/unit_test_output_v3.json"
        )
        expected_output_path_v2 = (
            f"public/data/sec_narrative_drift_lab/NVDA/outputs/llm_outline_compare_structured/"
            f"{campaign.track_slug}/unit_test_output_v2.json"
        )
        expected_output_path_v1 = (
            f"public/data/sec_narrative_drift_lab/NVDA/outputs/llm_outline_compare_runtime/"
            f"{campaign.track_slug}/unit_test_output_v1.json"
        )
        manifest = make_single_entry_manifest_v3(
            DEFAULT_PRIMARY_LLM_CAMPAIGN_ID,
            expected_output_path_v3,
            expected_output_path_v2,
            expected_output_path_v1,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "manifest_v5.json"
            out_path = root / "starters_v5.md"
            write_json(manifest_path, manifest)
            rc = emit_starters.main(
                [
                    "--manifest",
                    str(manifest_path),
                    "--out",
                    str(out_path),
                    "--format",
                    "vscode_autowrite_insight_exp",
                ]
            )
            self.assertEqual(rc, 0)
            rendered = out_path.read_text(encoding="utf-8")
            self.assertIn("llm_outline_compare_insight", rendered)
            self.assertIn("lab_project_master_v3_to_v2.py", rendered)
            self.assertIn("--target-field \"projected_master_output_structured\"", rendered)
            self.assertIn("--target-field \"projected_master_output_runtime\"", rendered)
            self.assertIn(f'--only "{expected_output_path_v3}"', rendered)
            self.assertIn(f'--only "{expected_output_path_v2}"', rendered)
            self.assertIn(f'--only "{expected_output_path_v1}"', rendered)
            self.assertIn("Windows-safe write guardrail (required for large artifacts):", rendered)
            self.assertIn("Do not use one-shot oversized inline write commands for large JSON writes.", rendered)
            self.assertIn("`Set-Content` + `Add-Content`", rendered)


class TestPromptTemplateResolutionHardening(unittest.TestCase):
    def _bundle_paths(
        self,
        bundle_root: Path,
        prompt_templates: Path | None = None,
    ) -> prompt_consistency.BundlePaths:
        return prompt_consistency.BundlePaths(
            bundle_root=bundle_root,
            focus_index=None,
            full_index=None,
            pair_index_v2=None,
            year_index_v2=None,
            prompt_templates=prompt_templates,
        )

    def test_non_primary_campaign_prefers_campaign_scoped_prompt_template(self) -> None:
        campaign = get_llm_campaign(DEFAULT_COMPARE_LLM_CAMPAIGN_ID)
        if campaign is None:
            self.fail("Compare campaign not found for unit test.")
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_root = Path(tmpdir)
            canonical_path = bundle_root / "prompt_templates_showcase.md"
            canonical_path.write_text("codex-canonical", encoding="utf-8")
            campaign_path = bundle_root / (
                f"prompt_templates_showcase__{campaign.track_slug}.md"
            )
            campaign_path.write_text("chatgpt-campaign", encoding="utf-8")
            resolved = prompt_consistency.resolve_prompt_templates_path(
                bundle_paths=self._bundle_paths(bundle_root),
                campaign_id=campaign.track_id,
                campaign_slug=campaign.track_slug,
                prompt_templates_override="",
            )
            self.assertEqual(campaign_path, resolved)

    def test_non_primary_campaign_missing_scoped_template_fails_with_remediation(self) -> None:
        campaign = get_llm_campaign(DEFAULT_COMPARE_LLM_CAMPAIGN_ID)
        if campaign is None:
            self.fail("Compare campaign not found for unit test.")
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_root = Path(tmpdir)
            (bundle_root / "prompt_templates_showcase.md").write_text(
                "codex-canonical", encoding="utf-8"
            )
            expected_filename = f"prompt_templates_showcase__{campaign.track_slug}.md"
            with self.assertRaises(SystemExit) as ctx:
                prompt_consistency.resolve_prompt_templates_path(
                    bundle_paths=self._bundle_paths(bundle_root),
                    campaign_id=campaign.track_id,
                    campaign_slug=campaign.track_slug,
                    prompt_templates_override="",
                )
            message = str(ctx.exception)
            self.assertIn("Missing campaign-scoped prompt template for non-primary campaign", message)
            self.assertIn(expected_filename, message)
            self.assertIn("python scripts/lab_write_prompt_templates.py", message)

    def test_prompt_template_override_takes_precedence(self) -> None:
        campaign = get_llm_campaign(DEFAULT_COMPARE_LLM_CAMPAIGN_ID)
        if campaign is None:
            self.fail("Compare campaign not found for unit test.")
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_root = Path(tmpdir)
            override_path = bundle_root / "prompt_templates_override.md"
            override_path.write_text("override", encoding="utf-8")
            resolved = prompt_consistency.resolve_prompt_templates_path(
                bundle_paths=self._bundle_paths(bundle_root, prompt_templates=override_path),
                campaign_id=campaign.track_id,
                campaign_slug=campaign.track_slug,
                prompt_templates_override=str(override_path),
            )
            self.assertEqual(override_path, resolved)


class TestPromptConsistencyDocGuards(unittest.TestCase):
    def _write_doc(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_doc_guards_pass_with_required_markers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            doc_index = root / "docs" / "00_DOC_INDEX.md"
            remaining_plan = root / "docs" / "LAB_REMAINING_WORK_PLAN.md"
            comparison_doc = root / "docs" / "lab" / "06_llm_model_comparison_workflow.md"

            self._write_doc(
                doc_index,
                "\n".join(
                    [
                        "`docs/_archive/legacy_context_20260302/00_README_doc_index.md`",
                        "`docs/_archive/legacy_context_20260302/sec_narrative_drift_codex_spec_v1_13.md`",
                        "`docs/_archive/legacy_context_20260302/sec_narrative_drift_codex_implementation_checklist_v1_13.md`",
                        "`reports/lab_llm_master_manifest_codex_real.json`",
                        "`reports/lab_llm_master_thread_starters_codex_real.md`",
                        "`reports/lab_llm_master_validation_codex_real.md`",
                    ]
                ),
            )
            self._write_doc(
                remaining_plan,
                "\n".join(
                    [
                        "`openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27`",
                        "`openai_chatgpt52ext_agent_fullsec_real_2026-02-27`",
                        "`llm_outline_compare_runtime`",
                        "`docs/lab/08_remaining_work_plan_history.md`",
                    ]
                ),
            )
            self._write_doc(
                comparison_doc,
                "\n".join(
                    [
                        "`openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27`",
                        "`openai-gpt53codex-xhigh-agent-fullsec-real-2026-02-27`",
                        "`openai_chatgpt52ext_agent_fullsec_real_2026-02-27`",
                        "`openai-chatgpt52ext-agent-fullsec-real-2026-02-27`",
                        "runtime-visible",
                        "runtime-hidden",
                    ]
                ),
            )

            prompt_consistency.check_canonical_docs(doc_index, remaining_plan, comparison_doc)

    def test_doc_guards_fail_on_missing_required_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            doc_index = root / "docs" / "00_DOC_INDEX.md"
            remaining_plan = root / "docs" / "LAB_REMAINING_WORK_PLAN.md"
            comparison_doc = root / "docs" / "lab" / "06_llm_model_comparison_workflow.md"

            self._write_doc(
                doc_index,
                "\n".join(
                    [
                        "`docs/_archive/legacy_context_20260302/00_README_doc_index.md`",
                        "`docs/_archive/legacy_context_20260302/sec_narrative_drift_codex_spec_v1_13.md`",
                        "`docs/_archive/legacy_context_20260302/sec_narrative_drift_codex_implementation_checklist_v1_13.md`",
                        "`reports/lab_llm_master_manifest_codex_real.json`",
                        "`reports/lab_llm_master_thread_starters_codex_real.md`",
                        "`reports/lab_llm_master_validation_codex_real.md`",
                    ]
                ),
            )
            self._write_doc(
                remaining_plan,
                "\n".join(
                    [
                        "`openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27`",
                        "`openai_chatgpt52ext_agent_fullsec_real_2026-02-27`",
                        "`llm_outline_compare_runtime`",
                        "`docs/lab/08_remaining_work_plan_history.md`",
                    ]
                ),
            )
            # Missing required runtime-hidden marker on purpose.
            self._write_doc(
                comparison_doc,
                "\n".join(
                    [
                        "`openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27`",
                        "`openai-gpt53codex-xhigh-agent-fullsec-real-2026-02-27`",
                        "`openai_chatgpt52ext_agent_fullsec_real_2026-02-27`",
                        "`openai-chatgpt52ext-agent-fullsec-real-2026-02-27`",
                        "runtime-visible",
                    ]
                ),
            )

            with self.assertRaises(SystemExit) as ctx:
                prompt_consistency.check_canonical_docs(doc_index, remaining_plan, comparison_doc)
            self.assertIn("comparison_doc missing required marker(s)", str(ctx.exception))

    def test_doc_guards_fail_on_stale_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            doc_index = root / "docs" / "00_DOC_INDEX.md"
            remaining_plan = root / "docs" / "LAB_REMAINING_WORK_PLAN.md"
            comparison_doc = root / "docs" / "lab" / "06_llm_model_comparison_workflow.md"

            self._write_doc(
                doc_index,
                "\n".join(
                    [
                        "`docs/_archive/legacy_context_20260302/00_README_doc_index.md`",
                        "`docs/_archive/legacy_context_20260302/sec_narrative_drift_codex_spec_v1_13.md`",
                        "`docs/_archive/legacy_context_20260302/sec_narrative_drift_codex_implementation_checklist_v1_13.md`",
                        "`reports/lab_llm_master_manifest_codex_real.json`",
                        "`reports/lab_llm_master_thread_starters_codex_real.md`",
                        "`reports/lab_llm_master_validation_codex_real.md`",
                        "`docs/00_README_doc_index.md`",
                    ]
                ),
            )
            self._write_doc(
                remaining_plan,
                "\n".join(
                    [
                        "`openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27`",
                        "`openai_chatgpt52ext_agent_fullsec_real_2026-02-27`",
                        "`llm_outline_compare_runtime`",
                        "`docs/lab/08_remaining_work_plan_history.md`",
                    ]
                ),
            )
            self._write_doc(
                comparison_doc,
                "\n".join(
                    [
                        "`openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27`",
                        "`openai-gpt53codex-xhigh-agent-fullsec-real-2026-02-27`",
                        "`openai_chatgpt52ext_agent_fullsec_real_2026-02-27`",
                        "`openai-chatgpt52ext-agent-fullsec-real-2026-02-27`",
                        "runtime-visible",
                        "runtime-hidden",
                    ]
                ),
            )

            with self.assertRaises(SystemExit) as ctx:
                prompt_consistency.check_canonical_docs(doc_index, remaining_plan, comparison_doc)
            self.assertIn("doc_index contains forbidden marker(s)", str(ctx.exception))


class TestMasterQualityAuditHardening(unittest.TestCase):
    def _stage_fixture_input_mirror(self) -> list[Path]:
        mapping = [
            (PAIR_INPUT_SOURCE_PATH, REPO_ROOT / "inputs" / "pair" / PAIR_INPUT_SOURCE_PATH.name),
            (YEAR_PREV_PATH, REPO_ROOT / "inputs" / "year" / YEAR_PREV_PATH.name),
            (YEAR_CURR_PATH, REPO_ROOT / "inputs" / "year" / YEAR_CURR_PATH.name),
        ]
        created: list[Path] = []
        for source_path, mirror_path in mapping:
            if not source_path.exists():
                self.fail(f"Fixture source path missing: {source_path}")
            mirror_path.parent.mkdir(parents=True, exist_ok=True)
            if mirror_path.exists():
                if mirror_path.read_bytes() != source_path.read_bytes():
                    self.fail(f"Fixture mirror path already exists with mismatched contents: {mirror_path}")
                continue
            mirror_path.write_bytes(source_path.read_bytes())
            created.append(mirror_path)
        return created

    def _cleanup_fixture_input_mirror(self, created_paths: list[Path]) -> None:
        for mirror_path in reversed(created_paths):
            try:
                mirror_path.unlink()
            except FileNotFoundError:
                pass
        for directory in (
            REPO_ROOT / "inputs" / "pair",
            REPO_ROOT / "inputs" / "year",
            REPO_ROOT / "inputs",
        ):
            try:
                directory.rmdir()
            except OSError:
                pass

    def _evaluate_payload(
        self,
        payload: dict[str, Any],
        *,
        expected_artifact_id: str = "llm_outline_compare_runtime",
        strict_depth: bool = False,
        stage_fixture_inputs: bool = True,
    ) -> quality_audit.OutputAudit:
        created_paths: list[Path] = []
        if stage_fixture_inputs:
            created_paths = self._stage_fixture_input_mirror()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = Path(tmpdir) / "unit_output.json"
                write_json(output_path, payload)
                if expected_artifact_id == "llm_outline_compare_runtime":
                    expected_output_path = "public/data/sec_narrative_drift_lab/NVDA/outputs/llm_outline_compare_runtime/unit_test/unit_output.json"
                elif expected_artifact_id == "llm_outline_compare_structured":
                    expected_output_path = "public/data/sec_narrative_drift_lab/NVDA/outputs/llm_outline_compare_structured/unit_test/unit_output.json"
                else:
                    expected_output_path = "public/data/sec_narrative_drift_lab/NVDA/outputs/llm_outline_compare_insight/unit_test/unit_output.json"
                target = master_validate.MasterTarget(
                    ticker="NVDA",
                    year_from=2022,
                    year_to=2023,
                    section="10k_item1a",
                    lens="raw",
                    source_id="edgar",
                    expected_output_path=expected_output_path,
                    manifest_present_flag=None,
                    expected_artifact_id=expected_artifact_id,
                    source_master_structured_path=None,
                )
                return quality_audit.evaluate_output(
                    output_path,
                    target,
                    expected_model_provider="unit_provider",
                    expected_model_name="unit_model",
                    strict_depth=strict_depth,
                )
        finally:
            if stage_fixture_inputs:
                self._cleanup_fixture_input_mirror(created_paths)

    def test_quality_audit_strong_payload_has_no_blockers(self) -> None:
        payload = build_valid_payload()
        audit = self._evaluate_payload(payload)
        self.assertEqual([], [issue.code for issue in audit.blockers])

    def test_quality_audit_ambiguous_provenance_input_remains_blocker(self) -> None:
        payload = build_valid_payload()
        payload["provenance"]["input_file"] = AMBIGUOUS_PAIR_INPUT_FILE
        audit = self._evaluate_payload(payload, stage_fixture_inputs=False)
        codes = [issue.code for issue in audit.blockers]
        self.assertIn("unresolvable_input_file", codes)
        details = [
            issue.detail
            for issue in audit.blockers
            if issue.code in {"unresolvable_input_file", "validator_failure"}
        ]
        self.assertTrue(any("ambiguous" in detail.lower() for detail in details))

    def test_quality_audit_flags_mid_token_snippet(self) -> None:
        payload = build_valid_payload()
        snippet = payload["evidence_bank"][0]["snippet"]
        if not isinstance(snippet, str) or len(snippet) < 8:
            self.fail("Expected a sufficiently long snippet for mid-token test.")
        payload["evidence_bank"][0]["snippet"] = snippet[1:]
        audit = self._evaluate_payload(payload)
        codes = [issue.code for issue in audit.blockers]
        self.assertIn("snippet_mid_token_start", codes)

    def test_quality_audit_flags_weak_caveat(self) -> None:
        payload = build_valid_payload()
        payload["material_changes"][0]["caveat"] = "This remains a risk."
        audit = self._evaluate_payload(payload)
        codes = [issue.code for issue in audit.blockers]
        self.assertIn("caveat_too_short", codes)
        self.assertIn("caveat_not_specific", codes)

    def test_quality_audit_flags_generic_phrase_density(self) -> None:
        payload = build_valid_payload()
        payload["node_alignment"][0]["rationale"] = "This remains a risk and is a concern in both years."
        payload["material_changes"][0]["title"] = "Broad risk remains a risk across years"
        payload["material_changes"][0]["caveat"] = (
            "Paragraph 14 in 2022 and 2023 remains a risk and is a concern, "
            "and this caveat references those two years directly for traceability."
        )
        audit = self._evaluate_payload(payload)
        advisory_codes = [issue.code for issue in audit.advisories]
        self.assertIn("generic_phrase_density", advisory_codes)

    def test_quality_audit_strict_depth_strong_v2_payload_has_no_blockers(self) -> None:
        payload = build_valid_v2_strict_payload()
        audit = self._evaluate_payload(
            payload,
            expected_artifact_id="llm_outline_compare_structured",
            strict_depth=True,
        )
        self.assertEqual([], [issue.code for issue in audit.blockers])

    def test_quality_audit_strict_depth_blocks_insufficient_material_rows(self) -> None:
        payload = build_valid_v2_strict_payload()
        payload["material_changes"] = payload["material_changes"][:3]
        audit = self._evaluate_payload(
            payload,
            expected_artifact_id="llm_outline_compare_structured",
            strict_depth=True,
        )
        codes = [issue.code for issue in audit.blockers]
        self.assertIn("insufficient_material_change_rows", codes)

    def test_quality_audit_strict_depth_blocks_weak_biyear_coverage(self) -> None:
        payload = build_valid_v2_strict_payload()
        repeated_refs = [
            {"year": 2022, "paragraph_idx": 5},
            {"year": 2023, "paragraph_idx": 15},
        ]
        for row in payload["material_changes"]:
            row["evidence_refs"] = [dict(ref) for ref in repeated_refs]
        audit = self._evaluate_payload(
            payload,
            expected_artifact_id="llm_outline_compare_structured",
            strict_depth=True,
        )
        codes = [issue.code for issue in audit.blockers]
        self.assertIn("insufficient_biyear_material_ref_coverage", codes)

    def test_quality_audit_strict_depth_blocks_missing_top3_non_opening_biyear(self) -> None:
        payload = build_valid_v2_strict_payload()
        rows = payload["material_changes"]
        rows[0]["change_class"] = "added"
        rows[0]["salience"] = 0.99
        rows[0]["evidence_refs"] = [{"year": 2023, "paragraph_idx": 15}]
        rows[1]["change_class"] = "added"
        rows[1]["salience"] = 0.95
        rows[1]["evidence_refs"] = [{"year": 2023, "paragraph_idx": 30}]
        rows[2]["change_class"] = "added"
        rows[2]["salience"] = 0.92
        rows[2]["evidence_refs"] = [{"year": 2023, "paragraph_idx": 45}]
        rows[3]["salience"] = 0.40
        rows[3]["evidence_refs"] = [
            {"year": 2022, "paragraph_idx": 5},
            {"year": 2022, "paragraph_idx": 20},
            {"year": 2022, "paragraph_idx": 40},
            {"year": 2022, "paragraph_idx": 70},
            {"year": 2023, "paragraph_idx": 80},
        ]
        audit = self._evaluate_payload(
            payload,
            expected_artifact_id="llm_outline_compare_structured",
            strict_depth=True,
        )
        codes = [issue.code for issue in audit.blockers]
        self.assertIn("missing_top3_non_opening_biyear_change", codes)

    def test_quality_audit_strict_depth_blocks_narrow_tercile_span(self) -> None:
        payload = build_valid_v2_strict_payload()
        rows = payload["material_changes"]
        rows[0]["evidence_refs"] = [
            {"year": 2022, "paragraph_idx": 5},
            {"year": 2023, "paragraph_idx": 15},
        ]
        rows[1]["evidence_refs"] = [
            {"year": 2022, "paragraph_idx": 20},
            {"year": 2023, "paragraph_idx": 30},
        ]
        rows[2]["evidence_refs"] = [
            {"year": 2022, "paragraph_idx": 5},
            {"year": 2023, "paragraph_idx": 45},
        ]
        rows[3]["evidence_refs"] = [
            {"year": 2022, "paragraph_idx": 20},
            {"year": 2023, "paragraph_idx": 80},
        ]
        audit = self._evaluate_payload(
            payload,
            expected_artifact_id="llm_outline_compare_structured",
            strict_depth=True,
        )
        codes = [issue.code for issue in audit.blockers]
        self.assertIn("narrow_material_ref_span_prev", codes)

    def test_quality_audit_strict_depth_blocks_opening_and_concentration(self) -> None:
        payload = build_valid_v2_strict_payload()
        for row in payload["material_changes"]:
            row["change_class"] = "added"
            row["evidence_refs"] = [{"year": 2023, "paragraph_idx": 0}]
        audit = self._evaluate_payload(
            payload,
            expected_artifact_id="llm_outline_compare_structured",
            strict_depth=True,
        )
        codes = [issue.code for issue in audit.blockers]
        self.assertIn("opening_paragraph_overuse_blocker", codes)
        self.assertIn("evidence_ref_concentration_blocker", codes)

    def test_quality_audit_strict_depth_blocks_low_ref_diversity(self) -> None:
        payload = build_valid_v2_strict_payload()
        refs_a = {"year": 2022, "paragraph_idx": 5}
        refs_b = {"year": 2023, "paragraph_idx": 15}
        refs_c = {"year": 2022, "paragraph_idx": 20}
        refs_d = {"year": 2023, "paragraph_idx": 30}
        combos = [
            [refs_a, refs_b, refs_c],
            [refs_a, refs_b, refs_d],
            [refs_a, refs_c, refs_d],
            [refs_b, refs_c, refs_d],
        ]
        for row, combo in zip(payload["material_changes"], combos):
            row["evidence_refs"] = [dict(ref) for ref in combo]
        audit = self._evaluate_payload(
            payload,
            expected_artifact_id="llm_outline_compare_structured",
            strict_depth=True,
        )
        codes = [issue.code for issue in audit.blockers]
        self.assertIn("low_evidence_ref_diversity_blocker", codes)


    def test_quality_audit_v3_strong_payload_has_no_blockers(self) -> None:
        payload = build_valid_v3_payload()
        audit = self._evaluate_payload(
            payload,
            expected_artifact_id="llm_outline_compare_insight",
            strict_depth=True,
        )
        self.assertEqual([], [issue.code for issue in audit.blockers])

    def test_quality_audit_v3_blocks_digest_budget_miss(self) -> None:
        payload = build_valid_v3_payload()
        payload["executive_digest"]["summary_text"] = "too short"
        audit = self._evaluate_payload(
            payload,
            expected_artifact_id="llm_outline_compare_insight",
            strict_depth=True,
        )
        self.assertIn("digest_length_out_of_budget", [issue.code for issue in audit.blockers])

    def test_quality_audit_v3_blocks_missing_similarity_category(self) -> None:
        payload = build_valid_v3_payload()
        for card in payload["insight_cards"]:
            card["insight_type"] = "difference"
        payload["insight_coverage"]["difference_count"] = len(payload["insight_cards"])
        payload["insight_coverage"]["similarity_count"] = 0
        audit = self._evaluate_payload(
            payload,
            expected_artifact_id="llm_outline_compare_insight",
            strict_depth=True,
        )
        self.assertIn("missing_similarity_insights", [issue.code for issue in audit.blockers])

    def test_quality_audit_v3_blocks_unresolved_evidence_links(self) -> None:
        payload = build_valid_v3_payload()
        payload["insight_cards"][0]["evidence_ref_ids"] = ["ev_missing"]
        audit = self._evaluate_payload(
            payload,
            expected_artifact_id="llm_outline_compare_insight",
            strict_depth=True,
        )
        self.assertIn("unresolved_insight_evidence_links", [issue.code for issue in audit.blockers])


if __name__ == "__main__":
    unittest.main()







