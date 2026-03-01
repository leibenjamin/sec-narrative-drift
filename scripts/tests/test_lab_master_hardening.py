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
import lab_validate_llm_master_outputs as master_validate  # noqa: E402
from lab_output_tracks import DEFAULT_PRIMARY_LLM_CAMPAIGN_ID, get_llm_campaign  # noqa: E402


PAIR_INPUT_FILE = "inputs/pair/NVDA_2022_2023_10k_item1a_raw_edgar.json"
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


def make_single_entry_manifest(campaign_id: str, expected_output_path: str) -> dict[str, Any]:
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
                },
                "master_output": {
                    "expected_output_path": expected_output_path,
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
        "artifact_id": "llm_outline_compare_v1",
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
            f"public/data/sec_narrative_drift_lab/NVDA/outputs/llm_outline_compare_v1/"
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
            f"public/data/sec_narrative_drift_lab/NVDA/outputs/llm_outline_compare_v1/"
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
                ]
            )
            self.assertEqual(rc, 0)
            text = out_path.read_text(encoding="utf-8")
            self.assertNotIn("> NUL", text)
            self.assertIn("--only-mode \"exact_path\"", text)
            self.assertIn("--expect-target-count 1", text)
            self.assertIn("--fail-if-target-count-mismatch", text)
            self.assertIn("lab_audit_master_output_quality.py --output", text)
            self.assertIn("python -c \"import json, pathlib;", text)
            self.assertIn(f'--only "{expected_output_path}"', text)

    def test_emitter_v2_includes_job_meta_and_shape_min(self) -> None:
        campaign = get_llm_campaign(DEFAULT_PRIMARY_LLM_CAMPAIGN_ID)
        if campaign is None:
            self.fail("Default campaign not found for unit test.")
        expected_output_path = (
            f"public/data/sec_narrative_drift_lab/NVDA/outputs/llm_outline_compare_v1/"
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


class TestMasterQualityAuditHardening(unittest.TestCase):
    def _evaluate_payload(self, payload: dict[str, Any]) -> quality_audit.OutputAudit:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "unit_output.json"
            write_json(output_path, payload)
            target = master_validate.MasterTarget(
                ticker="NVDA",
                year_from=2022,
                year_to=2023,
                section="10k_item1a",
                lens="raw",
                source_id="edgar",
                expected_output_path="public/data/sec_narrative_drift_lab/NVDA/outputs/llm_outline_compare_v1/unit_test/unit_output.json",
                manifest_present_flag=None,
            )
            return quality_audit.evaluate_output(
                output_path,
                target,
                expected_model_provider="unit_provider",
                expected_model_name="unit_model",
            )

    def test_quality_audit_strong_payload_has_no_blockers(self) -> None:
        payload = build_valid_payload()
        audit = self._evaluate_payload(payload)
        self.assertEqual([], [issue.code for issue in audit.blockers])

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


if __name__ == "__main__":
    unittest.main()
