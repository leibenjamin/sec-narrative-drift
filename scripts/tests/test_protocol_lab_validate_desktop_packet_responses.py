from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
TMP_ROOT = ROOT_DIR / "_tmp_test_runs"
sys.path.insert(0, str(ROOT_DIR))

import protocol_lab_validate_desktop_packet_responses as validator  # noqa: E402


class PacketResponseValidatorTest(unittest.TestCase):
    def write_run(
        self,
        packet_root: Path,
        run_id: str,
        response_text: str,
        manifest_payload: dict[str, object] | None = None,
    ) -> None:
        run_dir = packet_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "response.json").write_text(response_text, encoding="utf-8")
        payload = manifest_payload if manifest_payload is not None else {}
        (run_dir / "run_manifest.json").write_text(json.dumps(payload), encoding="utf-8")

    def test_validate_packet_reports_parse_and_shape_failures_without_repair(self) -> None:
        repo = TMP_ROOT / "validator_case_a"
        shutil.rmtree(repo, ignore_errors=True)
        repo.mkdir(parents=True, exist_ok=True)
        try:
            packet_root = repo / "wave4e1_standard_thinking_controls_20260319_0213"
            self.write_run(
                packet_root,
                "NVDA_00_b0_unstructured_frontier_baseline_standard",
                json.dumps({"brief_markdown": "brief", "evidence": []}),
            )
            self.write_run(
                packet_root,
                "NVDA_02_p1_i2_tagged_packet_standard",
                json.dumps({"change_brief": {}, "evidence_bundle": {}}),
            )
            self.write_run(
                packet_root,
                "LLY_03_p2_i2_tagged_protocol_standard",
                '{"change_brief":{},"evidence_bundle":{"items":[]}',
            )

            report = validator.validate_packet(
                packet_root,
                [
                    "NVDA_00_b0_unstructured_frontier_baseline_standard",
                    "NVDA_02_p1_i2_tagged_packet_standard",
                    "LLY_03_p2_i2_tagged_protocol_standard",
                ],
            )

            self.assertEqual("fail", report.overall_result)
            result_map = {result.run_id: result for result in report.run_results}

            self.assertEqual([], result_map["NVDA_00_b0_unstructured_frontier_baseline_standard"].blocker_codes)
            self.assertTrue(result_map["NVDA_00_b0_unstructured_frontier_baseline_standard"].top_level_shape_valid)
            self.assertEqual([], result_map["NVDA_02_p1_i2_tagged_packet_standard"].blocker_codes)
            self.assertTrue(result_map["NVDA_02_p1_i2_tagged_packet_standard"].top_level_shape_valid)

            lly_result = result_map["LLY_03_p2_i2_tagged_protocol_standard"]
            self.assertIn("json_parse_failed", lly_result.blocker_codes)
            self.assertFalse(lly_result.json_parseable)
            self.assertFalse(lly_result.top_level_shape_valid)
            self.assertEqual(
                {"change_brief": True, "evidence_bundle": True},
                lly_result.raw_text_expected_key_hints,
            )
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_report_payload_contains_expected_schema_and_run_fields(self) -> None:
        repo = TMP_ROOT / "validator_case_b"
        shutil.rmtree(repo, ignore_errors=True)
        repo.mkdir(parents=True, exist_ok=True)
        try:
            packet_root = repo / "wave4e1_standard_thinking_controls_20260319_0213"
            self.write_run(
                packet_root,
                "NVDA_00_b0_unstructured_frontier_baseline_standard",
                json.dumps({"brief_markdown": "brief", "evidence": []}),
            )

            report = validator.validate_packet(
                packet_root, ["NVDA_00_b0_unstructured_frontier_baseline_standard"]
            )
            payload = validator.report_to_payload(report)

            self.assertEqual("standard_control_validation_report_v1", payload["artifact_schema_id"])
            self.assertEqual("pass", payload["overall_result"])
            self.assertEqual(1, len(payload["run_results"]))
            self.assertEqual(
                ["brief_markdown", "evidence"],
                payload["run_results"][0]["expected_top_level_keys"],
            )
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_expected_top_level_keys_support_reuse_filtered_lane_family(self) -> None:
        self.assertEqual(
            ("change_brief", "evidence_bundle"),
            validator.expected_top_level_keys_for_lane_slug("01_p1_i1_reuse_filtered"),
        )

    def test_manifest_declared_top_level_keys_allow_novelty_ledger_shape(self) -> None:
        repo = TMP_ROOT / "validator_case_c"
        shutil.rmtree(repo, ignore_errors=True)
        repo.mkdir(parents=True, exist_ok=True)
        try:
            packet_root = repo / "wave4e3_nvda_novelty_ledger_packet_20990101_0101"
            self.write_run(
                packet_root,
                "NVDA_04_p4_i2_novelty_ledger_extended",
                json.dumps(
                    {
                        "change_brief": {},
                        "novelty_ledger": {},
                        "evidence_bundle": {"items": []},
                    }
                ),
                manifest_payload={
                    "output_contract": {
                        "top_level_keys": [
                            "change_brief",
                            "novelty_ledger",
                            "evidence_bundle",
                        ]
                    }
                },
            )

            report = validator.validate_packet(
                packet_root, ["NVDA_04_p4_i2_novelty_ledger_extended"]
            )

            self.assertEqual("pass", report.overall_result)
            self.assertEqual(1, len(report.run_results))
            result = report.run_results[0]
            self.assertEqual(
                ("change_brief", "novelty_ledger", "evidence_bundle"),
                result.expected_top_level_keys,
            )
            self.assertEqual([], result.blocker_codes)
            self.assertTrue(result.top_level_shape_valid)
        finally:
            shutil.rmtree(repo, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
