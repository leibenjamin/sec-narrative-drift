from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
TMP_ROOT = ROOT_DIR / "_tmp_test_runs"
sys.path.insert(0, str(ROOT_DIR))

import protocol_lab_capture_guardrail as guardrail  # noqa: E402


class CaptureGuardrailTest(unittest.TestCase):
    def write_run(self, packet_root: Path, run_id: str, response_text: str | None) -> None:
        run_dir = packet_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        if response_text is not None:
            (run_dir / "response.json").write_text(response_text, encoding="utf-8")
        (run_dir / "run_manifest.json").write_text("{}", encoding="utf-8")

    def test_guardrail_proceeds_when_checked_runs_parse_and_match_expected_shape(self) -> None:
        repo = TMP_ROOT / "guardrail_case_pass"
        shutil.rmtree(repo, ignore_errors=True)
        repo.mkdir(parents=True, exist_ok=True)
        try:
            packet_root = repo / "wave_packet"
            self.write_run(
                packet_root,
                "NVDA_00_b0_unstructured_frontier_baseline_standard",
                json.dumps({"brief_markdown": "brief", "evidence": []}),
            )
            self.write_run(
                packet_root,
                "NVDA_01_p1_i1_reuse_filtered_standard",
                json.dumps({"change_brief": {}, "evidence_bundle": {}}),
            )

            summary = guardrail.run_guardrail(packet_root)
            console_lines = guardrail.build_console_lines(summary)

            self.assertTrue(summary.proceed)
            self.assertEqual("proceed", summary.overall_result)
            self.assertIn("capture_guardrail: PROCEED", console_lines)
            self.assertIn(
                "Proceed. Every checked response.json file exists, is non-empty, parses cleanly, and matches the expected top-level shape.",
                summary.plain_language_summary,
            )
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_guardrail_stops_on_missing_empty_parse_and_shape_failures(self) -> None:
        repo = TMP_ROOT / "guardrail_case_stop"
        shutil.rmtree(repo, ignore_errors=True)
        repo.mkdir(parents=True, exist_ok=True)
        try:
            packet_root = repo / "wave_packet"
            self.write_run(packet_root, "NVDA_00_b0_unstructured_frontier_baseline_standard", None)
            self.write_run(packet_root, "NVDA_02_p1_i2_tagged_packet_standard", "   ")
            self.write_run(
                packet_root,
                "NVDA_03_p2_i2_tagged_protocol_standard",
                '{"change_brief":{},"evidence_bundle":{"items":[]}',
            )
            self.write_run(
                packet_root,
                "NVDA_01_p1_i1_reuse_filtered_standard",
                json.dumps({"brief_markdown": "wrong", "evidence": []}),
            )

            summary = guardrail.run_guardrail(packet_root)
            result_map = {result.run_id: result for result in summary.run_results}
            console_lines = guardrail.build_console_lines(summary)

            self.assertFalse(summary.proceed)
            self.assertEqual("stop", summary.overall_result)
            self.assertIn("NVDA_00_b0_unstructured_frontier_baseline_standard", summary.blocking_run_ids)
            self.assertIn("NVDA_02_p1_i2_tagged_packet_standard", summary.blocking_run_ids)
            self.assertIn("NVDA_03_p2_i2_tagged_protocol_standard", summary.blocking_run_ids)
            self.assertIn("NVDA_01_p1_i1_reuse_filtered_standard", summary.blocking_run_ids)
            self.assertIn("response_missing", result_map["NVDA_00_b0_unstructured_frontier_baseline_standard"].blocker_codes)
            self.assertIn("response_empty", result_map["NVDA_02_p1_i2_tagged_packet_standard"].blocker_codes)
            self.assertIn("json_parse_failed", result_map["NVDA_03_p2_i2_tagged_protocol_standard"].blocker_codes)
            self.assertIn("top_level_keys_mismatch", result_map["NVDA_01_p1_i1_reuse_filtered_standard"].blocker_codes)
            self.assertIn("capture_guardrail: STOP", console_lines)
            self.assertTrue(
                summary.plain_language_summary.startswith("Stop. 4 checked runs failed capture preflight")
            )
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_guardrail_can_write_optional_report(self) -> None:
        repo = TMP_ROOT / "guardrail_case_report"
        shutil.rmtree(repo, ignore_errors=True)
        repo.mkdir(parents=True, exist_ok=True)
        try:
            packet_root = repo / "wave_packet"
            report_path = repo / "reports" / "capture_guardrail_report.json"
            self.write_run(
                packet_root,
                "NVDA_01_p1_i1_reuse_filtered_standard",
                json.dumps({"change_brief": {}, "evidence_bundle": {}}),
            )

            summary = guardrail.run_guardrail(packet_root, report_out=report_path)
            payload = json.loads(report_path.read_text(encoding="utf-8"))

            self.assertTrue(summary.proceed)
            self.assertEqual("capture_guardrail_report_v1", payload["artifact_schema_id"])
            self.assertEqual("proceed", payload["overall_result"])
            self.assertEqual(["NVDA_01_p1_i1_reuse_filtered_standard"], payload["checked_run_ids"])
        finally:
            shutil.rmtree(repo, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
