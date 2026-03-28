import hashlib
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import protocol_lab_wave4c2a_capture_import_bridge as wave  # noqa: E402


def sample_prompt_render() -> dict[str, str]:
    return {
        "prompt_render_id": f"{wave.RUN_REQUEST_ID}__prompt_render_v1",
        "rendered_system_content": "sys",
        "rendered_user_content": "user",
    }


def sample_run_request() -> dict[str, Any]:
    return {
        "run_request_id": wave.RUN_REQUEST_ID,
        "fixture_id": wave.FIXTURE_ID,
        "protocol_id": "p1_structured_contract_v1",
        "model_profile_id": wave.PRIMARY_MODEL_PROFILE_ID,
        "runner_binding_id": wave.PRIMARY_RUNNER_BINDING_ID,
        "stack_id": "s_p1_m1_v1",
        "run_label": "2026-03-15_test_run",
        "input_pack_id": "i2_tagged_document_packet_v1",
        "expected_artifact_paths": {
            "evidence_bundle_path": "x",
            "change_brief_output_path": "y",
            "change_brief_eval_path": "z",
        },
        "notes": [],
    }


def sample_trace() -> dict[str, Any]:
    return {
        "usage_metadata": {"state_history": []},
        "notes": [],
        "run_state": "awaiting_capture",
        "parse_status": "not_run",
        "postprocess_status": "not_run",
        "raw_response_path": None,
        "finished_at": None,
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


def sample_response_meta(filename: str, sha: str, *, runner_binding: str | None = None, model_name: str = wave.PRIMARY_MODEL_NAME) -> dict[str, Any]:
    return {
        "run_request_id": wave.RUN_REQUEST_ID,
        "prompt_render_id": f"{wave.RUN_REQUEST_ID}__prompt_render_v1",
        "attempt_label": wave.ATTEMPT_LABEL,
        "runner_binding_id": runner_binding or wave.PRIMARY_RUNNER_BINDING_ID,
        "campaign_id": wave.PRIMARY_RUNNER_CAMPAIGN_ID,
        "captured_at": "2026-03-15T21:00:00Z",
        "model_name": model_name,
        "capture_method": "saved_response_json_file" if filename.endswith(".json") else "saved_response_text_file",
        "raw_response_filename": filename,
        "raw_response_sha256": sha,
        "notes": ["note"],
    }


def sample_receipt(filename: str, sha: str, prompt_sha: str) -> dict[str, Any]:
    return {
        "artifact_schema_id": "capture_receipt_v1",
        "capture_receipt_id": f"{wave.RUN_REQUEST_ID}__{wave.ATTEMPT_LABEL}__capture_receipt_v1",
        "run_request_id": wave.RUN_REQUEST_ID,
        "prompt_render_id": f"{wave.RUN_REQUEST_ID}__prompt_render_v1",
        "attempt_label": wave.ATTEMPT_LABEL,
        "runner_binding_id": wave.PRIMARY_RUNNER_BINDING_ID,
        "campaign_id": wave.PRIMARY_RUNNER_CAMPAIGN_ID,
        "captured_at": "2026-03-15T21:00:00Z",
        "model_name": wave.PRIMARY_MODEL_NAME,
        "capture_method": "saved_response_json_file" if filename.endswith(".json") else "saved_response_text_file",
        "raw_response_filename": filename,
        "raw_response_sha256": sha,
        "prompt_body_sha256": prompt_sha,
        "notes": ["note"],
    }


def sample_legacy_run_request() -> dict[str, Any]:
    payload = sample_run_request()
    payload["runner_binding_id"] = wave.LEGACY_RUNNER_BINDING_ID
    return payload


def seed_core_files(repo: Path) -> tuple[Path, Path, Path, Path]:
    runs_root = repo / "public" / "data" / "business_document_protocol_lab" / "runs"
    evals_root = repo / "public" / "data" / "business_document_protocol_lab" / "evals"
    reports_root = repo / "reports" / "protocol_lab"
    raw_root = reports_root / "raw_runs"
    run_dir = runs_root / wave.FIXTURE_ID / wave.RUN_REQUEST_ID
    attempt = raw_root / wave.FIXTURE_ID / wave.RUN_REQUEST_ID / "main" / wave.ATTEMPT_LABEL
    eval_dir = evals_root / wave.FIXTURE_ID / wave.RUN_REQUEST_ID
    run_dir.mkdir(parents=True)
    attempt.mkdir(parents=True)
    eval_dir.mkdir(parents=True)
    (run_dir / "prompt_render_v1.json").write_text(json.dumps(sample_prompt_render()), encoding="utf-8")
    (run_dir / "run_request_v1.json").write_text(json.dumps(sample_run_request()), encoding="utf-8")
    (run_dir / "execution_trace_v1.json").write_text(json.dumps(sample_trace()), encoding="utf-8")
    return run_dir, attempt, eval_dir, reports_root


def seed_valid_capture(repo: Path, *, raw_filename: str = "response.json") -> tuple[Path, Path, str]:
    run_dir, attempt, _eval_dir, _reports_root = seed_core_files(repo)
    raw_path = attempt / raw_filename
    payload = json.dumps(sample_envelope()) if raw_filename.endswith(".json") else json.dumps(sample_envelope())
    raw_path.write_text(payload, encoding="utf-8")
    sha = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    prompt_sha = wave.prompt_hash(sample_prompt_render())
    (attempt / "response_meta.json").write_text(json.dumps(sample_response_meta(raw_filename, sha)), encoding="utf-8")
    (attempt / "capture_receipt_v1.json").write_text(json.dumps(sample_receipt(raw_filename, sha, prompt_sha)), encoding="utf-8")
    return run_dir, attempt, sha


class TestWave4c2a(unittest.TestCase):
    def test_rebind_existing_request_from_legacy_codex_stub(self) -> None:
        rebound = wave.rebind_existing_request(sample_legacy_run_request())
        self.assertEqual(wave.PRIMARY_RUNNER_BINDING_ID, rebound["runner_binding_id"])
        self.assertEqual(wave.LEGACY_RUNNER_BINDING_ID, sample_legacy_run_request()["runner_binding_id"])

    def patched_repo(self, repo: Path):
        reports_root = repo / "reports" / "protocol_lab"
        runs_root = repo / "public" / "data" / "business_document_protocol_lab" / "runs"
        evals_root = repo / "public" / "data" / "business_document_protocol_lab" / "evals"
        raw_root = reports_root / "raw_runs"
        registries_root = repo / "public" / "data" / "business_document_protocol_lab" / "registries"
        source_cases_root = repo / "public" / "data" / "business_document_protocol_lab" / "source_cases"
        parse_schema = reports_root / "parse_report_v1.schema.json"
        stack = ExitStack()
        stack.enter_context(patch.object(wave, "REPO_ROOT", repo))
        stack.enter_context(patch.object(wave, "RUNS_ROOT", runs_root))
        stack.enter_context(patch.object(wave, "EVALS_ROOT", evals_root))
        stack.enter_context(patch.object(wave, "RAW_RUNS_ROOT", raw_root))
        stack.enter_context(patch.object(wave, "REPORTS_ROOT", reports_root))
        stack.enter_context(patch.object(wave, "REGISTRIES_ROOT", registries_root))
        stack.enter_context(patch.object(wave, "SOURCE_CASES_ROOT", source_cases_root))
        stack.enter_context(patch.object(wave, "CAPTURE_RECEIPT_SCHEMA_PATH", reports_root / "capture_receipt_v1.schema.json"))
        stack.enter_context(patch.object(wave, "CAPTURE_VALIDATION_SCHEMA_PATH", reports_root / "capture_validation_report_v1.schema.json"))
        stack.enter_context(patch.object(wave, "LOCAL_CAPTURE_CONTRACT_PATH", reports_root / "local_capture_contract_v1.md"))
        stack.enter_context(patch.object(wave, "RUNBOOK_PATH", reports_root / "wave4c2a_operator_runbook.md"))
        stack.enter_context(patch.object(wave, "BRIDGE_REPORT_PATH", reports_root / "wave4c2a_capture_import_bridge_report.md"))
        stack.enter_context(patch.object(wave, "REVIEW_NOTES_PATH", reports_root / "wave4c2a_review_notes.md"))
        stack.enter_context(patch.object(wave.wave4c1, "REPO_ROOT", repo))
        stack.enter_context(patch.object(wave.wave4c1, "RUNS_ROOT", runs_root))
        stack.enter_context(patch.object(wave.wave4c1, "EVALS_ROOT", evals_root))
        stack.enter_context(patch.object(wave.wave4c1, "RAW_RUNS_ROOT", raw_root))
        stack.enter_context(patch.object(wave.wave4c1, "PARSE_REPORT_SCHEMA_PATH", parse_schema))
        return stack

    def test_import_json_writes_canonical_files_and_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            with self.patched_repo(repo), patch.object(wave, "prepare_phase", return_value=None):
                _run_dir, attempt, _eval_dir, _reports = seed_core_files(repo)
                source = repo / "incoming" / "response.json"
                source.parent.mkdir(parents=True)
                source.write_text(json.dumps(sample_envelope()), encoding="utf-8")
                result = wave.import_phase(str(source), "2026-03-15T21:00:00Z", wave.PRIMARY_MODEL_NAME, ["note"])
                self.assertTrue(result.imported)
                raw_path = attempt / "response.json"
                self.assertTrue(raw_path.exists())
                self.assertEqual(source.read_text(encoding="utf-8"), raw_path.read_text(encoding="utf-8"))
                meta = json.loads((attempt / "response_meta.json").read_text(encoding="utf-8"))
                receipt = json.loads((attempt / "capture_receipt_v1.json").read_text(encoding="utf-8"))
                sha = hashlib.sha256(raw_path.read_bytes()).hexdigest()
                self.assertEqual("saved_response_json_file", meta["capture_method"])
                self.assertEqual(sha, meta["raw_response_sha256"])
                self.assertEqual(sha, receipt["raw_response_sha256"])

    def test_import_text_writes_canonical_files_and_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            with self.patched_repo(repo), patch.object(wave, "prepare_phase", return_value=None):
                _run_dir, attempt, _eval_dir, _reports = seed_core_files(repo)
                source = repo / "incoming" / "response.txt"
                source.parent.mkdir(parents=True)
                source.write_text(json.dumps(sample_envelope()), encoding="utf-8")
                result = wave.import_phase(str(source), "2026-03-15T21:00:00Z", wave.PRIMARY_MODEL_NAME, [])
                self.assertTrue(result.imported)
                self.assertTrue((attempt / "response.txt").exists())
                meta = json.loads((attempt / "response_meta.json").read_text(encoding="utf-8"))
                self.assertEqual("saved_response_text_file", meta["capture_method"])

    def test_import_rejects_unsupported_source_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            with self.patched_repo(repo), patch.object(wave, "prepare_phase", return_value=None):
                seed_core_files(repo)
                source = repo / "incoming" / "response.md"
                source.parent.mkdir(parents=True)
                source.write_text("x", encoding="utf-8")
                result = wave.import_phase(str(source), "2026-03-15T21:00:00Z", wave.PRIMARY_MODEL_NAME, [])
                self.assertFalse(result.imported)
                self.assertIn("unsupported_import_source_type", result.blockers)

    def test_validate_fails_on_prompt_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            with self.patched_repo(repo):
                run_dir, _attempt, _sha = seed_valid_capture(repo)
                drifted = sample_prompt_render()
                drifted["rendered_user_content"] = "changed"
                (run_dir / "prompt_render_v1.json").write_text(json.dumps(drifted), encoding="utf-8")
                result = wave.validate_phase()
                self.assertFalse(result.passed)
                self.assertIn("capture_receipt_prompt_body_sha256_mismatch", result.blockers)

    def test_validate_fails_on_runner_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            with self.patched_repo(repo):
                _run_dir, attempt, sha = seed_valid_capture(repo)
                bad_meta = sample_response_meta("response.json", sha, runner_binding="rb_wrong")
                (attempt / "response_meta.json").write_text(json.dumps(bad_meta), encoding="utf-8")
                result = wave.validate_phase()
                self.assertFalse(result.passed)
                self.assertIn("runner_binding_id_mismatch", result.blockers)

    def test_validate_fails_on_model_and_receipt_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            with self.patched_repo(repo):
                _run_dir, attempt, sha = seed_valid_capture(repo)
                bad_meta = sample_response_meta("response.json", sha, model_name="different-model")
                (attempt / "response_meta.json").write_text(json.dumps(bad_meta), encoding="utf-8")
                receipt = json.loads((attempt / "capture_receipt_v1.json").read_text(encoding="utf-8"))
                receipt["raw_response_sha256"] = "bad"
                (attempt / "capture_receipt_v1.json").write_text(json.dumps(receipt), encoding="utf-8")
                result = wave.validate_phase()
                self.assertFalse(result.passed)
                self.assertIn("model_name_mismatch", result.blockers)
                self.assertIn("capture_receipt_raw_response_sha256_mismatch", result.blockers)

    def test_finalize_success_materializes_artifacts_and_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            with self.patched_repo(repo):
                run_dir, attempt, _sha = seed_valid_capture(repo)
                _reports_root = repo / "reports" / "protocol_lab"
                scripts_root = repo / "scripts"
                (scripts_root / "tests").mkdir(parents=True)
                (scripts_root / "protocol_lab_wave4c2a_capture_import_bridge.py").write_text("# bridge\n", encoding="utf-8")
                (scripts_root / "tests" / "test_protocol_lab_wave4c2a_capture_import_bridge.py").write_text("# test\n", encoding="utf-8")
                wave.ensure_capture_receipt_schema()
                wave.ensure_capture_validation_schema()
                wave.write_local_capture_contract()
                wave.write_operator_runbook()
                wave.wave4c1.write_json(wave.wave4c1.PARSE_REPORT_SCHEMA_PATH, {"artifact_schema_id": "parse_report_v1"})
                wave.wave4c1.write_json(
                    attempt / "capture_validation_report_v1.json",
                    {"run_request_id": wave.RUN_REQUEST_ID, "attempt_label": wave.ATTEMPT_LABEL, "overall_result": "pass", "blocker_codes": []},
                )
                parse_ok = wave.wave4c1.ParseOutcome(
                    raw_response_path=wave.repo_rel(attempt / "response.json"),
                    raw_response_exists=True,
                    raw_response_format="json",
                    parse_succeeded=True,
                    schema_validation_succeeded=True,
                    coercion_or_repair_applied=False,
                    parse_warnings=[],
                    parser_error_note=None,
                    normalizations_applied=[],
                    envelope=sample_envelope(),
                )
                resolution: dict[str, Any] = {
                    "resolution_summary": {"overall_result": "pass", "total_evidence_items": 1, "failed_item_count": 0},
                    "items": [],
                }
                with patch.object(wave.wave4c1, "parse_raw_response", return_value=parse_ok), patch.object(wave.wave4b, "build_evidence_resolution_payload", return_value=resolution):
                    finalize = wave.finalize_phase()
                    self.assertTrue(finalize.truly_finalized)
                    validation = wave.CaptureValidationResult(True, [], wave.repo_rel(attempt / "response.json"), "response.json", hashlib.sha256((attempt / "response.json").read_bytes()).hexdigest(), "cid")
                    summary = wave.write_reports_and_packet(validation, finalize)
                    self.assertTrue(summary.p1_truly_finalized)
                    self.assertTrue(summary.non_empty_evidence_materialized)
                    self.assertTrue((run_dir / "change_brief_output_v1.json").exists())
                    manifest = (summary.packet_dir / "relevant_files_manifest.md").read_text(encoding="utf-8")
                    self.assertIn("change_brief_output_v1.json", manifest)
                    self.assertTrue(summary.zip_path.exists())

    def test_no_capture_path_reports_truthful_blocker_and_ignores_scaffolds(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            with self.patched_repo(repo):
                run_dir, attempt, _eval_dir, _reports = seed_core_files(repo)
                scripts_root = repo / "scripts"
                (scripts_root / "tests").mkdir(parents=True)
                (scripts_root / "protocol_lab_wave4c2a_capture_import_bridge.py").write_text("# bridge\n", encoding="utf-8")
                (scripts_root / "tests" / "test_protocol_lab_wave4c2a_capture_import_bridge.py").write_text("# test\n", encoding="utf-8")
                wave.ensure_capture_receipt_schema()
                wave.ensure_capture_validation_schema()
                wave.write_local_capture_contract()
                wave.write_operator_runbook()
                wave.wave4c1.write_json(wave.wave4c1.PARSE_REPORT_SCHEMA_PATH, {"artifact_schema_id": "parse_report_v1"})
                (attempt / "response_meta.json").write_text(json.dumps(wave.response_meta_template()), encoding="utf-8")
                wave.wave4c1.write_json(run_dir / "change_brief_output_v1.json", {"artifact_status": "scaffolded"})
                wave.wave4c1.write_json(run_dir / "evidence_bundle_v1.json", {"artifact_status": "scaffolded", "items": []})
                validation = wave.validate_phase()
                finalize = wave.finalize_phase()
                summary = wave.write_reports_and_packet(validation, finalize)
                self.assertFalse(summary.real_raw_response_imported)
                self.assertFalse(summary.capture_validation_passed)
                self.assertFalse(summary.p1_truly_finalized)
                self.assertFalse(summary.non_empty_evidence_materialized)
                self.assertEqual(wave.MANUAL_CAPTURE_BLOCKER, summary.biggest_remaining_blocker)
                notes = (repo / "reports" / "protocol_lab" / "wave4c2a_review_notes.md").read_text(encoding="utf-8")
                self.assertIn(wave.MANUAL_CAPTURE_BLOCKER, notes)
                manifest = (summary.packet_dir / "relevant_files_manifest.md").read_text(encoding="utf-8")
                self.assertNotIn("change_brief_output_v1.json", manifest)


if __name__ == "__main__":
    unittest.main()
