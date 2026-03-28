from __future__ import annotations

import json
import shutil
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
TMP_ROOT = ROOT_DIR / "_tmp_test_runs"
sys.path.insert(0, str(ROOT_DIR))

import protocol_lab_wave4e2_effort_robustness as wave  # noqa: E402


class Wave4E2EffortRobustnessTest(unittest.TestCase):
    def write_json(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def seed_support_files(self, repo: Path) -> None:
        for relative_path in [*wave.SCRIPT_AND_TEST_PATHS, *wave.SOURCE_PATHS]:
            full_path = repo / relative_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(f"placeholder for {relative_path.as_posix()}\n", encoding="utf-8")

    def seed_inputs(self, repo: Path) -> None:
        business_root = repo / "public" / "data" / "business_document_protocol_lab"
        standard_controls_root = business_root / "standard_controls"
        comparisons_root = standard_controls_root / "comparisons"

        self.write_json(
            standard_controls_root / "NVDA_2024_2025_10k_item1a" / "standard_control_matrix_v1.json",
            {
                "fixture_id": "NVDA_2024_2025_10k_item1a",
                "issuer": {"ticker": "NVDA", "issuer_name": "NVIDIA Corporation"},
                "pair_info": {
                    "ticker": "NVDA",
                    "issuer_name": "NVIDIA Corporation",
                    "year_from": 2024,
                    "year_to": 2025,
                    "form_type": "10-K",
                    "section_id": "item_1a",
                },
                "wave_summary": {
                    "strongest_lane": "02_p1_i2_tagged_packet",
                    "bounded_claim": "On this fixed NVDA pair, protocol value still appears visible under standard thinking, but the claim remains bounded.",
                },
                "lane_assessments": [
                    {"lane_slug": "02_p1_i2_tagged_packet", "assessment": "strongest"},
                    {"lane_slug": "03_p2_i2_tagged_protocol", "assessment": "meaningful_comparator"},
                    {"lane_slug": "00_b0_unstructured_frontier_baseline", "assessment": "control"},
                ],
                "canonical_sources": [
                    {
                        "lane_slug": "02_p1_i2_tagged_packet",
                        "validation_snapshot": {"blocker_codes": []},
                    },
                    {
                        "lane_slug": "03_p2_i2_tagged_protocol",
                        "validation_snapshot": {"blocker_codes": []},
                    },
                    {
                        "lane_slug": "00_b0_unstructured_frontier_baseline",
                        "validation_snapshot": {"blocker_codes": []},
                    },
                ],
            },
        )
        self.write_json(
            standard_controls_root / "LLY_2024_2025_10k_item1a" / "standard_control_matrix_v1.json",
            {
                "fixture_id": "LLY_2024_2025_10k_item1a",
                "issuer": {"ticker": "LLY", "issuer_name": "Eli Lilly and Company"},
                "pair_info": {
                    "ticker": "LLY",
                    "issuer_name": "Eli Lilly and Company",
                    "year_from": 2024,
                    "year_to": 2025,
                    "form_type": "10-K",
                    "section_id": "item_1a",
                },
                "wave_summary": {
                    "strongest_lane": "02_p1_i2_tagged_packet",
                    "bounded_claim": "On this fixed LLY pair, protocol value still appears directionally visible under standard thinking, but the claim remains bounded.",
                },
                "lane_assessments": [
                    {"lane_slug": "02_p1_i2_tagged_packet", "assessment": "strongest"},
                    {"lane_slug": "03_p2_i2_tagged_protocol", "assessment": "meaningful_comparator"},
                    {"lane_slug": "00_b0_unstructured_frontier_baseline", "assessment": "control"},
                ],
                "canonical_sources": [
                    {
                        "lane_slug": "02_p1_i2_tagged_packet",
                        "validation_snapshot": {"blocker_codes": ["json_parse_failed"]},
                    },
                    {
                        "lane_slug": "03_p2_i2_tagged_protocol",
                        "validation_snapshot": {"blocker_codes": ["json_parse_failed"]},
                    },
                    {
                        "lane_slug": "00_b0_unstructured_frontier_baseline",
                        "validation_snapshot": {"blocker_codes": []},
                    },
                ],
            },
        )
        self.write_json(
            standard_controls_root / "standard_control_summary_v1.json",
            {
                "by_issuer_ranking": [
                    {"issuer": {"ticker": "NVDA"}},
                    {"issuer": {"ticker": "LLY"}},
                ],
                "validation_overview": {
                    "failure_note": "LLY_02 and LLY_03 fail JSON parseability in their current canonical raw form.",
                },
            },
        )
        self.write_json(
            comparisons_root / "nvda_standard_vs_extended_v1.json",
            {
                "lane_comparisons": [
                    {
                        "lane_slug": "02_p1_i2_tagged_packet",
                        "stable_points": ["02 remains the strongest default lane."],
                        "degraded_points": ["The standard wave stays bounded rather than benchmark-grade."],
                        "lane_order_changed": False,
                    },
                    {
                        "lane_slug": "03_p2_i2_tagged_protocol",
                        "stable_points": ["03 still changes the read relative to 02."],
                        "degraded_points": ["03 still trails 02 as the default lane."],
                        "lane_order_changed": False,
                    },
                    {
                        "lane_slug": "00_b0_unstructured_frontier_baseline",
                        "stable_points": ["00 still functions as a readable control."],
                        "degraded_points": ["00 stays noncanonical and ad hoc."],
                        "lane_order_changed": False,
                    },
                ]
            },
        )
        self.write_json(
            comparisons_root / "lly_standard_vs_extended_v1.json",
            {
                "lane_comparisons": [
                    {
                        "lane_slug": "02_p1_i2_tagged_packet",
                        "stable_points": ["02 remains the intended strongest first-read lane."],
                        "degraded_points": ["The canonical standard raw file is malformed JSON."],
                        "lane_order_changed": False,
                    },
                    {
                        "lane_slug": "03_p2_i2_tagged_protocol",
                        "stable_points": ["03 still matters as the intended same-substrate comparator."],
                        "degraded_points": ["The canonical standard raw file is malformed JSON."],
                        "lane_order_changed": False,
                    },
                    {
                        "lane_slug": "00_b0_unstructured_frontier_baseline",
                        "stable_points": ["00 still functions as a readable control."],
                        "degraded_points": ["00 stays noncanonical and ad hoc."],
                        "lane_order_changed": False,
                    },
                ]
            },
        )
        self.write_json(
            comparisons_root / "standard_vs_extended_summary_v1.json",
            {
                "protocol_value_under_reduced_reasoning": "The current two-issuer slice still supports a bounded claim that protocol structure adds value under reduced reasoning effort.",
            },
        )

    def patched_repo(self, repo: Path) -> ExitStack:
        business_root = repo / "public" / "data" / "business_document_protocol_lab"
        standard_controls_root = business_root / "standard_controls"
        comparisons_root = standard_controls_root / "comparisons"
        effort_root = standard_controls_root / "effort_robustness"
        reports_root = repo / "reports" / "protocol_lab"
        stack = ExitStack()
        stack.enter_context(patch.object(wave, "REPO_ROOT", repo))
        stack.enter_context(patch.object(wave, "BUSINESS_ROOT", business_root))
        stack.enter_context(patch.object(wave, "STANDARD_CONTROLS_ROOT", standard_controls_root))
        stack.enter_context(patch.object(wave, "STANDARD_COMPARISONS_ROOT", comparisons_root))
        stack.enter_context(patch.object(wave, "EFFORT_ROBUSTNESS_ROOT", effort_root))
        stack.enter_context(patch.object(wave, "REPORTS_ROOT", reports_root))
        stack.enter_context(
            patch.object(
                wave,
                "NVDA_STANDARD_MATRIX_PATH",
                standard_controls_root / "NVDA_2024_2025_10k_item1a" / "standard_control_matrix_v1.json",
            )
        )
        stack.enter_context(
            patch.object(
                wave,
                "LLY_STANDARD_MATRIX_PATH",
                standard_controls_root / "LLY_2024_2025_10k_item1a" / "standard_control_matrix_v1.json",
            )
        )
        stack.enter_context(
            patch.object(wave, "STANDARD_CONTROL_SUMMARY_PATH", standard_controls_root / "standard_control_summary_v1.json")
        )
        stack.enter_context(patch.object(wave, "NVDA_COMPARISON_PATH", comparisons_root / "nvda_standard_vs_extended_v1.json"))
        stack.enter_context(patch.object(wave, "LLY_COMPARISON_PATH", comparisons_root / "lly_standard_vs_extended_v1.json"))
        stack.enter_context(
            patch.object(wave, "STANDARD_VS_EXTENDED_SUMMARY_PATH", comparisons_root / "standard_vs_extended_summary_v1.json")
        )
        stack.enter_context(patch.object(wave, "NVDA_EFFORT_ARTIFACT_PATH", effort_root / "nvda_effort_robustness_v1.json"))
        stack.enter_context(patch.object(wave, "LLY_EFFORT_ARTIFACT_PATH", effort_root / "lly_effort_robustness_v1.json"))
        stack.enter_context(
            patch.object(wave, "EFFORT_SUMMARY_ARTIFACT_PATH", effort_root / "effort_robustness_summary_v1.json")
        )
        stack.enter_context(patch.object(wave, "REPORT_PATH", reports_root / "wave4e2_effort_robustness_report.md"))
        stack.enter_context(patch.object(wave, "FINDINGS_PATH", reports_root / "wave4e2_effort_robustness_findings.md"))
        return stack

    def test_generate_wave_materializes_artifacts_packet_and_zip(self) -> None:
        repo = TMP_ROOT / "wave4e2_case"
        shutil.rmtree(repo, ignore_errors=True)
        repo.mkdir(parents=True, exist_ok=True)
        try:
            self.seed_inputs(repo)
            self.seed_support_files(repo)

            with self.patched_repo(repo):
                summary = wave.generate_wave(stamp="20990101_0202")

            self.assertTrue(summary.packet_dir.exists())
            self.assertTrue(summary.zip_path.exists())
            self.assertTrue(summary.renders_both_pilots)

            nvda_payload = json.loads(
                (
                    repo
                    / "public"
                    / "data"
                    / "business_document_protocol_lab"
                    / "standard_controls"
                    / "effort_robustness"
                    / "nvda_effort_robustness_v1.json"
                ).read_text(encoding="utf-8")
            )
            lly_payload = json.loads(
                (
                    repo
                    / "public"
                    / "data"
                    / "business_document_protocol_lab"
                    / "standard_controls"
                    / "effort_robustness"
                    / "lly_effort_robustness_v1.json"
                ).read_text(encoding="utf-8")
            )
            summary_payload = json.loads(
                (
                    repo
                    / "public"
                    / "data"
                    / "business_document_protocol_lab"
                    / "standard_controls"
                    / "effort_robustness"
                    / "effort_robustness_summary_v1.json"
                ).read_text(encoding="utf-8")
            )

            self.assertEqual("effort_robustness_case_v1", nvda_payload["artifact_schema_id"])
            self.assertEqual("effort_robustness_case_v1", lly_payload["artifact_schema_id"])
            self.assertEqual("effort_robustness_summary_v1", summary_payload["artifact_schema_id"])
            self.assertIn("integrity caveat", lly_payload["headline"])
            self.assertEqual(["NVDA", "LLY"], summary_payload["covered_issuers"])

            packet_readme = (summary.packet_dir / "README.md").read_text(encoding="utf-8")
            changed_manifest = (summary.packet_dir / "changed_files_manifest.md").read_text(encoding="utf-8")
            render_preview = (summary.packet_dir / "render_preview.md").read_text(encoding="utf-8")
            report_text = (
                repo / "reports" / "protocol_lab" / "wave4e2_effort_robustness_report.md"
            ).read_text(encoding="utf-8")
            findings_text = (
                repo / "reports" / "protocol_lab" / "wave4e2_effort_robustness_findings.md"
            ).read_text(encoding="utf-8")

            self.assertIn("public effort-robustness artifacts", packet_readme)
            self.assertIn("scripts/protocol_lab_capture_guardrail.py", changed_manifest)
            self.assertIn("src/components/ProtocolLabPilotMatrixPanel.tsx", changed_manifest)
            self.assertIn("src/components/LabPanel.tsx", changed_manifest)
            self.assertIn("src/pages/Company.tsx", changed_manifest)
            self.assertIn("effort robustness headline", render_preview)
            self.assertIn("Capture Guardrail", report_text)
            self.assertIn("strongest lane overall", findings_text)
            self.assertIn("whether NVDA and LLY both render the effort-robustness block: yes", "\n".join(summary.console_summary_lines))
            self.assertIn("scripts/protocol_lab_capture_guardrail.py", summary.guardrail_script_path)
            self.assertEqual(wave.BIGGEST_REMAINING_BLOCKER, summary.biggest_remaining_blocker)
        finally:
            shutil.rmtree(repo, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
