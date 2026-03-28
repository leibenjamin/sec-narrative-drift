import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import protocol_lab_wave4c1_nvda_execution as wave4c1  # noqa: E402


def make_run_request(run_request_id: str) -> dict[str, Any]:
    return {
        "run_request_id": run_request_id,
        "fixture_id": wave4c1.FIXTURE_ID,
        "protocol_id": "p1_structured_contract_v1",
        "model_profile_id": wave4c1.PRIMARY_MODEL_PROFILE_ID,
        "runner_binding_id": wave4c1.PRIMARY_RUNNER_BINDING_ID,
        "stack_id": "s_test",
        "run_label": "2026-03-15_test",
        "expected_artifact_paths": {"evidence_bundle_path": "x"},
        "prompt_render_id": f"{run_request_id}__prompt_render_v1",
    }


def make_envelope() -> dict[str, Any]:
    return {
        "change_brief": {
            "summary_one_liner": {"text": "Summary text", "evidence_ids": ["e1"]},
            "lead_shift": {"text": "Lead text", "evidence_ids": ["e1"]},
            "needle_change": {"text": "Needle text", "evidence_ids": ["e1"]},
            "novelty_vs_reuse": {"text": "Novelty text", "evidence_ids": ["e1"]},
            "main_caveat": {"text": "Caveat text", "evidence_ids": ["e1"], "caveat_type": "evidence_limit"},
            "failure_risk_notes": ["risk"],
            "notes": ["note"],
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
                        "char_end": 10,
                    },
                }
            ]
        },
    }


def make_failed_result(run_request_id: str, attempt_label: str = "attempt_01") -> wave4c1.RunFinalizeResult:
    return wave4c1.RunFinalizeResult(
        run_request_id=run_request_id,
        run_succeeded=False,
        run_state="capture_missing",
        parse_status="not_run",
        postprocess_status="not_run",
        raw_response_path=None,
        parse_report_path=f"reports/{run_request_id}/{attempt_label}/parse_report_v1.json",
        evidence_item_count=0,
        evidence_resolution_overall_result="not_run",
        human_eval_present=False,
        blocker_notes=["capture_missing"],
        attempt_label=attempt_label,
        downstream_artifacts_materialized=False,
    )


def make_validated_result(run_request_id: str, attempt_label: str = "attempt_01") -> wave4c1.RunFinalizeResult:
    return wave4c1.RunFinalizeResult(
        run_request_id=run_request_id,
        run_succeeded=True,
        run_state="validated",
        parse_status="passed",
        postprocess_status="passed",
        raw_response_path=f"reports/{run_request_id}/{attempt_label}/response.json",
        parse_report_path=f"reports/{run_request_id}/{attempt_label}/parse_report_v1.json",
        evidence_item_count=1,
        evidence_resolution_overall_result="pass",
        human_eval_present=False,
        blocker_notes=[],
        attempt_label=attempt_label,
        downstream_artifacts_materialized=True,
    )


def make_success_result(run_request_id: str, attempt_label: str = "attempt_01") -> wave4c1.RunFinalizeResult:
    return wave4c1.RunFinalizeResult(
        run_request_id=run_request_id,
        run_succeeded=True,
        run_state="reviewed",
        parse_status="passed",
        postprocess_status="passed",
        raw_response_path=f"reports/{run_request_id}/{attempt_label}/response.json",
        parse_report_path=f"reports/{run_request_id}/{attempt_label}/parse_report_v1.json",
        evidence_item_count=1,
        evidence_resolution_overall_result="pass",
        human_eval_present=True,
        blocker_notes=[],
        attempt_label=attempt_label,
        downstream_artifacts_materialized=True,
    )


class TestWave4c1(unittest.TestCase):
    def test_normalization_allowed_only(self) -> None:
        raw = '\ufeff  ```json\n{"change_brief":{},"evidence_bundle":{"items":[]}}\n```  '
        text, normalizations, warnings = wave4c1.normalize_transport_text(raw)
        self.assertIn("utf8_bom_trim", normalizations)
        self.assertIn("outer_whitespace_trim", normalizations)
        self.assertIn("single_fenced_wrapper_trim", normalizations)
        self.assertEqual([], warnings)
        self.assertTrue(text.startswith("{"))

    def test_parse_and_schema_failures(self) -> None:
        parse_fail = wave4c1.parse_model_envelope_text("{", None, "text")
        self.assertFalse(parse_fail.parse_succeeded)
        self.assertFalse(parse_fail.schema_validation_succeeded)

        schema_fail = wave4c1.parse_model_envelope_text('{"change_brief":{}}', None, "text")
        self.assertTrue(schema_fail.parse_succeeded)
        self.assertFalse(schema_fail.schema_validation_succeeded)

    def test_coercion_flag_stays_false(self) -> None:
        payload = '{"change_brief":{"summary_one_liner":{"text":"a","evidence_ids":[]},"lead_shift":{"text":"a","evidence_ids":[]},"needle_change":{"text":"a","evidence_ids":[]},"novelty_vs_reuse":{"text":"a","evidence_ids":[]},"main_caveat":{"text":"a","evidence_ids":[],"caveat_type":"other"}},"evidence_bundle":{"items":[]}}'
        outcome = wave4c1.parse_model_envelope_text(payload, None, "text")
        self.assertFalse(outcome.coercion_or_repair_applied)

    def test_metadata_injection_does_not_rewrite_model_text_or_quotes(self) -> None:
        run_request = make_run_request("r1")
        envelope = make_envelope()
        brief = wave4c1.build_change_brief(run_request, envelope)
        bundle = wave4c1.build_evidence_bundle(run_request, envelope)
        self.assertEqual("Summary text", brief["summary_one_liner"]["text"])
        self.assertEqual("Exact quote", bundle["items"][0]["quote_text"])

    def test_success_gate_requires_non_empty_evidence(self) -> None:
        parse_ok = wave4c1.ParseOutcome("x", True, "text", True, True, False, [], None, [], {})
        empty_bundle: dict[str, Any] = {"items": []}
        resolution_pass = {"resolution_summary": {"overall_result": "pass", "total_evidence_items": 1}}
        eval_complete = {"artifact_status": "complete"}
        hard = {
            "output_present": "pass",
            "evidence_bundle_present": "pass",
            "section_objects_present": "pass",
            "evidence_refs_resolved": "pass",
        }

        self.assertFalse(wave4c1.success_gate(parse_ok, True, empty_bundle, resolution_pass, eval_complete, hard))
        non_empty_bundle = {"items": [{"evidence_id": "e1"}]}
        self.assertTrue(wave4c1.success_gate(parse_ok, True, non_empty_bundle, resolution_pass, eval_complete, hard))

    def test_attempt_discovery_prefers_latest_existing_attempt(self) -> None:
        run_request_id = "r_attempts"
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_root = Path(tmpdir)
            base = raw_root / wave4c1.FIXTURE_ID / run_request_id / "main"
            (base / "attempt_01").mkdir(parents=True)
            (base / "attempt_03").mkdir(parents=True)
            (base / "misc_folder").mkdir(parents=True)
            with patch.object(wave4c1, "RAW_RUNS_ROOT", raw_root):
                self.assertEqual(["attempt_01", "attempt_03"], wave4c1.list_attempt_labels(run_request_id))
                self.assertEqual("attempt_03", wave4c1.latest_attempt_label(run_request_id))
                self.assertEqual("attempt_03", wave4c1.selected_or_latest_attempt_label(run_request_id))
                self.assertEqual("attempt_01", wave4c1.selected_or_latest_attempt_label(run_request_id, "attempt_01"))

    def test_prepare_attempt_does_not_auto_advance_retry(self) -> None:
        run_request_id = "r_prepare"
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_root = Path(tmpdir)
            first_attempt = raw_root / wave4c1.FIXTURE_ID / run_request_id / "main" / "attempt_01"
            first_attempt.mkdir(parents=True)
            with patch.object(wave4c1, "RAW_RUNS_ROOT", raw_root):
                attempt = wave4c1.ensure_prepare_attempt_label(run_request_id)
                self.assertEqual("attempt_01", attempt)
                self.assertTrue(first_attempt.exists())
                self.assertFalse((first_attempt.parent / "attempt_02").exists())

    def test_create_raw_capture_scaffold_preserves_existing_meta(self) -> None:
        run_request_id = "r_scaffold"
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            raw_root = repo_root / "reports" / "protocol_lab" / "raw_runs"
            current_attempt = raw_root / wave4c1.FIXTURE_ID / run_request_id / "main" / "attempt_01"
            current_attempt.mkdir(parents=True)
            existing_meta = {"captured_at": "existing", "notes": ["keep_me"]}
            meta_path = current_attempt / "response_meta.json"
            meta_path.write_text(json.dumps(existing_meta), encoding="utf-8")
            with patch.object(wave4c1, "REPO_ROOT", repo_root), patch.object(wave4c1, "RAW_RUNS_ROOT", raw_root):
                wave4c1.create_raw_capture_scaffold(run_request_id, "attempt_01")
                self.assertEqual(existing_meta, json.loads(meta_path.read_text(encoding="utf-8")))
                self.assertTrue((current_attempt / "CAPTURE_INSTRUCTIONS.md").exists())

    def test_response_meta_contract_validation(self) -> None:
        run_request_id = "r_meta"
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            raw_root = repo_root / "reports" / "protocol_lab" / "raw_runs"
            current_attempt = raw_root / wave4c1.FIXTURE_ID / run_request_id / "main" / "attempt_01"
            current_attempt.mkdir(parents=True)
            with patch.object(wave4c1, "REPO_ROOT", repo_root), patch.object(wave4c1, "RAW_RUNS_ROOT", raw_root):
                missing = wave4c1.inspect_response_meta(run_request_id, "attempt_01")
                self.assertFalse(missing.response_meta_exists)
                self.assertIn("response_meta_missing", missing.validation_errors)

                valid_meta = {
                    "captured_at": "2026-03-15T00:00:00Z",
                    "runner_binding_id": wave4c1.PRIMARY_RUNNER_BINDING_ID,
                    "campaign_id": wave4c1.PRIMARY_RUNNER_CAMPAIGN_ID,
                    "model_name": "gpt-5.3-codex",
                    "capture_method": "manual_copy",
                }
                (current_attempt / "response_meta.json").write_text(json.dumps(valid_meta), encoding="utf-8")
                valid = wave4c1.inspect_response_meta(run_request_id, "attempt_01")
                self.assertTrue(valid.response_meta_exists)
                self.assertTrue(valid.response_meta_valid)
                self.assertEqual([], valid.validation_errors)

                invalid_meta = dict(valid_meta)
                invalid_meta["captured_at"] = ""
                (current_attempt / "response_meta.json").write_text(json.dumps(invalid_meta), encoding="utf-8")
                invalid = wave4c1.inspect_response_meta(run_request_id, "attempt_01")
                self.assertFalse(invalid.response_meta_valid)
                self.assertIn("response_meta_incomplete", invalid.validation_errors)

    def test_prepare_trace_is_awaiting_capture_and_public_safe(self) -> None:
        request = make_run_request("r_prepare_trace")
        trace = wave4c1.build_prepare_trace(request, "attempt_01")
        self.assertEqual("awaiting_capture", trace["run_state"])
        self.assertIsNone(trace["raw_response_path"])
        self.assertEqual("not_run", trace["parse_status"])
        self.assertNotIn("raw_capture_root", trace["usage_metadata"])
        self.assertNotIn("parse_report_path", trace["usage_metadata"])
        self.assertNotIn("reports/protocol_lab/raw_runs", json.dumps(trace))

    def test_parse_report_targets_selected_attempt(self) -> None:
        run_request_id = "r_parse"
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            raw_root = repo_root / "reports" / "protocol_lab" / "raw_runs"
            current_attempt = raw_root / wave4c1.FIXTURE_ID / run_request_id / "main" / "attempt_03"
            current_attempt.mkdir(parents=True)
            payload = json.dumps(make_envelope())
            (current_attempt / "response.txt").write_text(payload, encoding="utf-8")
            with patch.object(wave4c1, "REPO_ROOT", repo_root), patch.object(wave4c1, "RAW_RUNS_ROOT", raw_root):
                outcome = wave4c1.parse_raw_response(run_request_id, "attempt_03")
                report = wave4c1.build_parse_report(run_request_id, "attempt_03", outcome)
                self.assertTrue(outcome.schema_validation_succeeded)
                self.assertEqual("attempt_03", report["attempt_label"])
                self.assertIn("attempt_03/response.txt", report["raw_response_path"])

    def test_update_trace_drops_local_paths_from_public_payload(self) -> None:
        request = make_run_request("r_trace")
        trace = wave4c1.build_prepare_trace(request, "attempt_01")
        parse = wave4c1.ParseOutcome(
            raw_response_path="reports/protocol_lab/raw_runs/x/response.txt",
            raw_response_exists=False,
            raw_response_format=None,
            parse_succeeded=False,
            schema_validation_succeeded=False,
            coercion_or_repair_applied=False,
            parse_warnings=[],
            parser_error_note="missing",
            normalizations_applied=[],
            envelope=None,
        )
        updated = wave4c1.update_trace(
            trace,
            "capture_missing",
            "not_run",
            "not_run",
            parse.raw_response_path,
            "reports/protocol_lab/raw_runs/x/parse_report_v1.json",
            "attempt_01",
            parse,
            ["capture_missing"],
            0,
        )
        self.assertEqual("capture_missing", updated["run_state"])
        self.assertIsNone(updated["raw_response_path"])
        self.assertEqual("capture_missing", updated["error_note"])
        self.assertNotIn("raw_capture_root", updated["usage_metadata"])
        self.assertNotIn("parse_report_path", updated["usage_metadata"])
        self.assertNotIn("reports/protocol_lab/raw_runs", json.dumps(updated))

    def test_blocked_comparison_clears_stale_delta_content_and_paths(self) -> None:
        existing: dict[str, Any] = {
            "artifact_status": "scaffolded",
            "compared_cells": [
                {"cell_id": "left", "run_request_id": wave4c1.TARGET_RUN_IDS[0]},
                {"cell_id": "right", "run_request_id": wave4c1.TARGET_RUN_IDS[1]},
            ],
            "comparison_verdict": {},
            "delta_ledger": [{"delta_id": "stale_delta"}],
            "pairwise_findings": [{"finding_id": "stale_finding"}],
            "high_level_takeaway": {},
            "review_status": {},
            "notes": ["stale"],
        }
        failed_results = [
            make_failed_result(wave4c1.TARGET_RUN_IDS[0]),
            make_success_result(wave4c1.TARGET_RUN_IDS[1]),
        ]
        payload, real, _ = wave4c1.build_comparison(existing, failed_results, {}, {}, {})
        self.assertFalse(real)
        self.assertEqual("blocked", payload["artifact_status"])
        self.assertEqual([], payload["delta_ledger"])
        self.assertEqual([], payload["pairwise_findings"])
        self.assertIn("blocked before evidence-grounded pairwise review", payload["comparison_verdict"]["text"])
        self.assertNotIn("reports/protocol_lab/raw_runs", json.dumps(payload))

    def test_pending_comparison_state(self) -> None:
        existing: dict[str, Any] = {
            "artifact_status": "scaffolded",
            "compared_cells": [
                {"cell_id": "left", "run_request_id": wave4c1.TARGET_RUN_IDS[0]},
                {"cell_id": "right", "run_request_id": wave4c1.TARGET_RUN_IDS[1]},
            ],
            "comparison_verdict": {},
            "delta_ledger": [{"delta_id": "stale_delta"}],
            "pairwise_findings": [{"finding_id": "stale_finding"}],
            "high_level_takeaway": {},
            "review_status": {},
            "notes": ["stale"],
        }
        validated_results = [
            make_validated_result(wave4c1.TARGET_RUN_IDS[0]),
            make_validated_result(wave4c1.TARGET_RUN_IDS[1]),
        ]
        payload, real, _ = wave4c1.build_comparison(existing, validated_results, {}, {}, {})
        self.assertFalse(real)
        self.assertEqual("pending", payload["artifact_status"])
        self.assertEqual("pending_review", payload["review_status"]["state"])
        self.assertEqual([], payload["delta_ledger"])
        self.assertEqual([], payload["pairwise_findings"])
        self.assertNotIn("reports/protocol_lab/raw_runs", json.dumps(payload))

    def test_blocked_review_packet_uses_current_attempt_truth_only(self) -> None:
        results = {run_request_id: make_failed_result(run_request_id) for run_request_id in wave4c1.TARGET_RUN_IDS}
        run_requests = {
            run_request_id: {
                "protocol_id": "p_test",
                "input_pack_id": "i_test",
                "model_profile_id": wave4c1.PRIMARY_MODEL_PROFILE_ID,
                "runner_binding_id": wave4c1.PRIMARY_RUNNER_BINDING_ID,
            }
            for run_request_id in wave4c1.TARGET_RUN_IDS
        }
        traces = {
            run_request_id: {
                "run_state": "capture_missing",
                "parse_status": "not_run",
                "postprocess_status": "not_run",
                "error_note": "capture_missing",
            }
            for run_request_id in wave4c1.TARGET_RUN_IDS
        }
        parse_reports: dict[str, dict[str, Any]] = {
            run_request_id: {
                "raw_response_exists": False,
                "parse_succeeded": False,
                "schema_validation_succeeded": False,
                "coercion_or_repair_applied": False,
                "normalizations_applied": [],
                "parse_warnings": [],
                "parser_error_note": "Raw response missing",
            }
            for run_request_id in wave4c1.TARGET_RUN_IDS
        }
        comparison = {
            "artifact_status": "blocked",
            "review_status": {"state": "blocked", "note": "capture_missing"},
        }
        packet = wave4c1.build_review_packet_text(
            results,
            run_requests,
            traces,
            parse_reports,
            evidence_bundles={},
            briefs={},
            resolutions={},
            evals={},
            comparison=comparison,
            takeaway="Comparison blocked.",
        )
        self.assertIn("No fresh change brief, evidence bundle, evidence resolution, or eval was materialized for this attempt.", packet)
        self.assertIn("No evidence-grounded delta ledger is available for this blocked comparison state.", packet)
        self.assertIn("response_meta_path", packet)
        self.assertNotIn("stale_delta", packet)

    def test_comparison_promotion_gate(self) -> None:
        existing: dict[str, Any] = {
            "artifact_status": "scaffolded",
            "compared_cells": [
                {"cell_id": "left", "run_request_id": wave4c1.TARGET_RUN_IDS[0]},
                {"cell_id": "right", "run_request_id": wave4c1.TARGET_RUN_IDS[1]},
            ],
            "comparison_verdict": {},
            "delta_ledger": [],
            "pairwise_findings": [],
            "high_level_takeaway": {},
            "review_status": {},
            "notes": [],
        }
        evals = {
            wave4c1.TARGET_RUN_IDS[0]: {"rubric_bands": {key: "strong" for key in wave4c1.RUBRIC_KEYS}},
            wave4c1.TARGET_RUN_IDS[1]: {"rubric_bands": {key: "fair" for key in wave4c1.RUBRIC_KEYS}},
        }
        briefs = {
            wave4c1.TARGET_RUN_IDS[0]: {
                "summary_one_liner": {"text": "left"},
                "lead_shift": {"text": "left lead"},
                "needle_change": {"text": "left needle"},
            },
            wave4c1.TARGET_RUN_IDS[1]: {
                "summary_one_liner": {"text": "right"},
                "lead_shift": {"text": "right lead"},
                "needle_change": {"text": "right needle"},
            },
        }
        success_results = [
            make_success_result(wave4c1.TARGET_RUN_IDS[0]),
            make_success_result(wave4c1.TARGET_RUN_IDS[1]),
        ]
        payload, real, _ = wave4c1.build_comparison(existing, success_results, evals, briefs, {})
        self.assertTrue(real)
        self.assertEqual("complete", payload["artifact_status"])


if __name__ == "__main__":
    unittest.main()
