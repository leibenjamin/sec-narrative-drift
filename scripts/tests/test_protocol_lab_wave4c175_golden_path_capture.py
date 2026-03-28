
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import protocol_lab_wave4c175_golden_path_capture as wave  # noqa: E402


def sample_prompt_render() -> dict[str, str]:
    return {
        "prompt_render_id": f"{wave.RUN_REQUEST_ID}__prompt_render_v1",
        "rendered_system_content": "sys",
        "rendered_user_content": "user",
    }


def sample_response_meta() -> dict[str, str]:
    return {
        "captured_at": "2026-03-15T00:00:00Z",
        "runner_binding_id": wave.PRIMARY_RUNNER_BINDING_ID,
        "campaign_id": wave.PRIMARY_RUNNER_CAMPAIGN_ID,
        "model_name": wave.PRIMARY_MODEL_NAME,
        "capture_method": "manual_copy",
    }


def sample_envelope() -> dict[str, Any]:
    return {
        "change_brief": {
            "summary_one_liner": {"text": "Summary", "evidence_ids": ["e1"]},
            "lead_shift": {"text": "Lead", "evidence_ids": ["e1"]},
            "needle_change": {"text": "Needle", "evidence_ids": ["e1"]},
            "novelty_vs_reuse": {"text": "Novelty", "evidence_ids": ["e1"]},
            "main_caveat": {"text": "Caveat", "evidence_ids": ["e1"], "caveat_type": "evidence_limit"},
        },
        "evidence_bundle": {
            "items": [
                {
                    "evidence_id": "e1",
                    "year_label": "FY2025",
                    "paragraph_id": "p1",
                    "quote_text": "Exact quote",
                    "source_locator": {
                        "accession_number": "acc",
                        "filing_date": "2025-02-26",
                        "form_type": "10-K",
                        "section_id": "item_1a",
                        "source_path": "path",
                        "char_start": 0,
                        "char_end": 5,
                    },
                }
            ]
        },
    }


class TestWave4c175(unittest.TestCase):
    def test_rebind_existing_request_from_legacy_codex_stub(self) -> None:
        rebound = wave.rebind_existing_request({"runner_binding_id": wave.LEGACY_RUNNER_BINDING_ID})
        self.assertEqual(wave.PRIMARY_RUNNER_BINDING_ID, rebound["runner_binding_id"])

    def test_prompt_hash(self) -> None:
        payload = sample_prompt_render()
        expected = "sys\n\n<USER_PROMPT_BOUNDARY>\n\nuser"
        self.assertEqual(wave.prompt_hash(payload), __import__("hashlib").sha256(expected.encode("utf-8")).hexdigest())

    def test_attempt_policy_blocks_extra_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / wave.FIXTURE_ID / wave.RUN_REQUEST_ID / "main"
            (base / "attempt_01").mkdir(parents=True)
            (base / "attempt_02").mkdir(parents=True)
            with patch.object(wave, "RAW_RUNS_ROOT", Path(tmpdir)):
                blockers = wave.attempt_policy_blockers()
                self.assertIn("unexpected_attempt_folder_present:attempt_02", blockers)

    def test_discover_raw_file_invalid_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_root = Path(tmpdir) / wave.FIXTURE_ID / wave.RUN_REQUEST_ID / "main" / "attempt_01"
            run_root.mkdir(parents=True)
            (run_root / "response.md").write_text("x", encoding="utf-8")
            with patch.object(wave, "RAW_RUNS_ROOT", Path(tmpdir)):
                raw, blockers = wave.discover_raw_response_file()
                self.assertIsNone(raw)
                self.assertIn("response.md", blockers)

    def test_valid_response_meta(self) -> None:
        ok, blockers = wave.valid_response_meta(sample_response_meta())
        self.assertTrue(ok)
        self.assertEqual([], blockers)

    def test_invalid_response_meta(self) -> None:
        bad = sample_response_meta()
        bad["captured_at"] = ""
        ok, blockers = wave.valid_response_meta(bad)
        self.assertFalse(ok)
        self.assertIn("response_meta_incomplete", blockers)

    def test_build_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_file = Path(tmpdir) / "response.json"
            raw_file.write_text("{}", encoding="utf-8")
            receipt = wave.build_receipt(sample_response_meta(), sample_prompt_render(), raw_file, "abc")
            self.assertEqual(wave.RUN_REQUEST_ID, receipt["run_request_id"])
            self.assertEqual("attempt_01", receipt["attempt_label"])
            self.assertEqual("abc", receipt["prompt_body_sha256"])

    def test_validate_phase_missing_raw(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            runs = repo / "public" / "data" / "business_document_protocol_lab" / "runs" / wave.FIXTURE_ID / wave.RUN_REQUEST_ID
            raw = repo / "reports" / "protocol_lab" / "raw_runs" / wave.FIXTURE_ID / wave.RUN_REQUEST_ID / "main" / "attempt_01"
            runs.mkdir(parents=True)
            raw.mkdir(parents=True)
            (runs / "prompt_render_v1.json").write_text(json.dumps(sample_prompt_render()), encoding="utf-8")
            (raw / "response_meta.json").write_text(json.dumps(sample_response_meta()), encoding="utf-8")
            (runs / "execution_trace_v1.json").write_text(json.dumps({"usage_metadata": {"state_history": []}, "notes": []}), encoding="utf-8")
            (runs / "run_request_v1.json").write_text(json.dumps({"notes": []}), encoding="utf-8")
            with patch.object(wave, "REPO_ROOT", repo), patch.object(wave, "RUNS_ROOT", repo / "public" / "data" / "business_document_protocol_lab" / "runs"), patch.object(wave, "RAW_RUNS_ROOT", repo / "reports" / "protocol_lab" / "raw_runs"):
                result = wave.validate_phase()
                self.assertFalse(result.passed)
                self.assertIn("raw_response_missing", result.blockers)

    def test_finalize_refuses_without_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            with patch.object(wave, "REPO_ROOT", repo), patch.object(wave, "RAW_RUNS_ROOT", repo / "reports" / "protocol_lab" / "raw_runs"):
                result = wave.finalize_phase()
                self.assertFalse(result.attempted)
                self.assertIn("capture_validation_report_missing", result.blockers)

    def test_finalize_requires_non_empty_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            runs_root = repo / "public" / "data" / "business_document_protocol_lab" / "runs"
            evals_root = repo / "public" / "data" / "business_document_protocol_lab" / "evals"
            raw_root = repo / "reports" / "protocol_lab" / "raw_runs"
            run_dir = runs_root / wave.FIXTURE_ID / wave.RUN_REQUEST_ID
            attempt = raw_root / wave.FIXTURE_ID / wave.RUN_REQUEST_ID / "main" / "attempt_01"
            run_dir.mkdir(parents=True)
            (evals_root / wave.FIXTURE_ID / wave.RUN_REQUEST_ID).mkdir(parents=True)
            attempt.mkdir(parents=True)

            (attempt / "response.json").write_text(json.dumps(sample_envelope()), encoding="utf-8")
            (attempt / "capture_validation_report_v1.json").write_text(
                json.dumps({"run_request_id": wave.RUN_REQUEST_ID, "attempt_label": "attempt_01", "overall_result": "pass"}),
                encoding="utf-8",
            )
            (run_dir / "run_request_v1.json").write_text(
                json.dumps(
                    {
                        "run_request_id": wave.RUN_REQUEST_ID,
                        "fixture_id": wave.FIXTURE_ID,
                        "protocol_id": "p1_structured_contract_v1",
                        "model_profile_id": wave.PRIMARY_MODEL_PROFILE_ID,
                        "runner_binding_id": wave.PRIMARY_RUNNER_BINDING_ID,
                        "stack_id": "s",
                        "run_label": "x",
                        "input_pack_id": "i2_tagged_document_packet_v1",
                        "expected_artifact_paths": {"evidence_bundle_path": "x", "change_brief_output_path": "y", "change_brief_eval_path": "z"},
                        "notes": [],
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "execution_trace_v1.json").write_text(json.dumps({"usage_metadata": {"state_history": []}, "notes": []}), encoding="utf-8")

            parse_ok = wave.wave4c1.ParseOutcome("p", True, "json", True, True, False, [], None, [], sample_envelope())
            with patch.object(wave, "REPO_ROOT", repo), patch.object(wave, "RUNS_ROOT", runs_root), patch.object(wave, "EVALS_ROOT", evals_root), patch.object(wave, "RAW_RUNS_ROOT", raw_root), patch.object(wave.wave4c1, "parse_raw_response", return_value=parse_ok), patch.object(wave.wave4b, "build_evidence_resolution_payload", return_value={"resolution_summary": {"overall_result": "pass", "total_evidence_items": 0}}), patch.object(wave.wave4c1, "build_evidence_bundle", return_value={"evidence_bundle_id": "id", "items": []}):
                result = wave.finalize_phase()
                self.assertTrue(result.attempted)
                self.assertFalse(result.truly_finalized)
                self.assertIn("evidence_bundle_empty", result.blockers)


if __name__ == "__main__":
    unittest.main()
