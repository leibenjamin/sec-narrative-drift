from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = ROOT_DIR.parent
TMP_ROOT = ROOT_DIR / "_tmp_test_runs"
sys.path.insert(0, str(ROOT_DIR))

import protocol_lab_validate_desktop_packet_responses as validator  # noqa: E402


class PacketResponseValidatorTest(unittest.TestCase):
    def minimal_evidence_bundle(
        self,
        *,
        fixture_id: str,
        protocol_id: str,
    ) -> dict[str, object]:
        return {
            "artifact_status": "complete",
            "artifact_schema_id": "evidence_bundle_v1",
            "evidence_bundle_id": f"{fixture_id}__evidence",
            "run_request_id": f"{fixture_id}__run_request",
            "fixture_id": fixture_id,
            "protocol_id": protocol_id,
            "model_profile_id": "m_alternate_strong_reasoning_v1",
            "runner_binding_id": "rb_openai_chatgpt54ext_real_local_v1",
            "items": [],
            "notes": [],
        }

    def minimal_evidence_bundle_transportless(self) -> dict[str, object]:
        return {
            "items": [],
        }

    def minimal_simple_vs_structured_adjudication(self, *, fixture_id: str) -> dict[str, object]:
        return {
            "fixture_id": fixture_id,
            "simple_read_source": {
                "workflow_id": "p0_plain_prompt_v1",
                "artifact_ref": "simple",
            },
            "structured_read_source": {
                "workflow_id": "p2_tagged_input_contract_v1",
                "artifact_ref": "structured",
            },
            "source_consistency_verdict": "consistent",
            "source_consistency_check": "Both sources use the same fixture, years, and tagged packet.",
            "contrast_verdict": "mixed",
            "what_simple_gets_right": "It catches the broad direction.",
            "what_structure_adds": "It names the sharper mechanism.",
            "allowed_public_claim_delta": "clearer",
            "most_likely_misread_if_using_only_simple_read": "A reader would blur a selective sharpening into a broader shift.",
            "why_the_difference_matters": "The structured read narrows the public claim.",
            "stop_note": "The extra structure adds precision, not scope.",
        }

    def minimal_decision_relevance_entry(self, *, anchor: str, implication: str) -> dict[str, object]:
        return {
            "change_anchor": anchor,
            "change_type": "sharpened",
            "decision_relevance": "high",
            "public_claim_effect": "clarifies",
            "why_it_matters": "It changes what the reader should monitor.",
            "why_not_to_overclaim": "The filing narrows the point; it does not justify a bigger conclusion.",
            "why_this_is_not_just_novelty": "It changes the decision the reader should make.",
            "public_route_implication": implication,
            "evidence_ids": ["ev_01"],
        }

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

    def test_manifest_declared_schema_blocks_invalid_simple_vs_structured_response(self) -> None:
        repo = TMP_ROOT / "validator_case_d"
        shutil.rmtree(repo, ignore_errors=True)
        repo.mkdir(parents=True, exist_ok=True)
        try:
            packet_root = repo / "nextgen_bundle_runs"
            fixture_id = "WMT_2025_2026_10k_item1a"
            adjudication = self.minimal_simple_vs_structured_adjudication(fixture_id=fixture_id)
            adjudication.pop("source_consistency_verdict")
            self.write_run(
                packet_root,
                "simple_vs_structured__WMT_2025_2026_10k_item1a",
                json.dumps(
                    {
                        "simple_vs_structured_adjudication": adjudication,
                        "evidence_bundle": self.minimal_evidence_bundle_transportless(),
                    }
                ),
                manifest_payload={
                    "schema_basis": {
                        "response_schema_repo_path": (
                            REPO_DIR
                            / "schemas"
                            / "protocol_lab"
                            / "experimental"
                            / "simple_read_vs_structured_read_contrast_v1_1.schema.json"
                        ).as_posix()
                    },
                    "run_identity": {
                        "run_id": "simple_vs_structured__WMT_2025_2026_10k_item1a",
                        "fixture_id": fixture_id,
                        "protocol_id": "simple_read_vs_structured_read_contrast_v1_1",
                        "model_profile_id": "m_alternate_strong_reasoning_v1",
                        "runner_binding_id": "rb_openai_chatgpt54ext_real_local_v1",
                    },
                    "output_contract": {
                        "top_level_keys": [
                            "simple_vs_structured_adjudication",
                            "evidence_bundle",
                        ]
                    },
                },
            )

            report = validator.validate_packet(
                packet_root, ["simple_vs_structured__WMT_2025_2026_10k_item1a"]
            )

            self.assertEqual("fail", report.overall_result)
            result = report.run_results[0]
            self.assertTrue(result.top_level_shape_valid)
            self.assertIn("schema_validation_failed", result.blocker_codes)
            self.assertTrue(
                any("source_consistency_verdict" in note for note in result.notes),
                msg=result.notes,
            )
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_manifest_declared_schema_blocks_more_than_two_foreground_entries(self) -> None:
        repo = TMP_ROOT / "validator_case_e"
        shutil.rmtree(repo, ignore_errors=True)
        repo.mkdir(parents=True, exist_ok=True)
        try:
            packet_root = repo / "nextgen_bundle_runs"
            fixture_id = "LLY_2024_2025_10k_item1a"
            ledger = {
                "fixture_id": fixture_id,
                "reader_of_record": {
                    "id": "general_business_reader",
                    "description": "A general professional reader deciding whether the filing pair contains a sharper risk signal that should change what they remember, monitor, or say publicly about the company's risk posture.",
                },
                "entries": [
                    self.minimal_decision_relevance_entry(anchor="Entry 1", implication="foreground"),
                    self.minimal_decision_relevance_entry(anchor="Entry 2", implication="foreground"),
                    self.minimal_decision_relevance_entry(anchor="Entry 3", implication="foreground"),
                ],
                "overall_verdict": {
                    "most_decision_relevant_shift": "Entry 1 is the main shift.",
                    "what_remains_background": "Everything else is secondary.",
                    "boundary_note": "Do not overread the case.",
                    "tempting_bad_read": "A careless reader would treat every refreshed item as foreground.",
                },
            }
            self.write_run(
                packet_root,
                "decision_relevance_ledger__LLY_2024_2025_10k_item1a",
                json.dumps(
                    {
                        "decision_relevance_ledger": ledger,
                        "evidence_bundle": self.minimal_evidence_bundle_transportless(),
                    }
                ),
                manifest_payload={
                    "schema_basis": {
                        "response_schema_repo_path": "schemas/protocol_lab/experimental/decision_relevance_ledger_v1_1.schema.json"
                    },
                    "run_identity": {
                        "run_id": "decision_relevance_ledger__LLY_2024_2025_10k_item1a",
                        "fixture_id": fixture_id,
                        "protocol_id": "decision_relevance_ledger_v1_1",
                        "model_profile_id": "m_alternate_strong_reasoning_v1",
                        "runner_binding_id": "rb_openai_chatgpt54ext_real_local_v1",
                    },
                    "output_contract": {
                        "top_level_keys": [
                            "decision_relevance_ledger",
                            "evidence_bundle",
                        ]
                    },
                },
            )

            report = validator.validate_packet(
                packet_root, ["decision_relevance_ledger__LLY_2024_2025_10k_item1a"]
            )

            self.assertEqual("fail", report.overall_result)
            result = report.run_results[0]
            self.assertTrue(result.top_level_shape_valid)
            self.assertIn("schema_validation_failed", result.blocker_codes)
            self.assertTrue(
                any("Too many items match" in note for note in result.notes),
                msg=result.notes,
            )
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_manifest_declared_schema_hydrates_transport_fields_and_writes_sidecars(self) -> None:
        repo = TMP_ROOT / "validator_case_f"
        shutil.rmtree(repo, ignore_errors=True)
        repo.mkdir(parents=True, exist_ok=True)
        original_repo_root = validator.REPO_ROOT
        validator.REPO_ROOT = repo
        try:
            packet_root = repo / "nextgen_bundle_runs"
            fixture_id = "WMT_2025_2026_10k_item1a"
            run_id = "simple_vs_structured__WMT_2025_2026_10k_item1a"
            response_path = packet_root / run_id / "response.json"
            evidence_sidecar_path = (
                repo
                / "bundles"
                / "nextgen_workflow_prototypes_v1_1_2026-04-10"
                / "runs"
                / run_id
                / "artifacts"
                / "evidence_bundle_v1.json"
            )
            primary_sidecar_path = (
                repo
                / "bundles"
                / "nextgen_workflow_prototypes_v1_1_2026-04-10"
                / "runs"
                / run_id
                / "artifacts"
                / "simple_vs_structured_adjudication_v1_1.json"
            )
            adjudication = self.minimal_simple_vs_structured_adjudication(fixture_id=fixture_id)
            raw_response = {
                "simple_vs_structured_adjudication": adjudication,
                "evidence_bundle": self.minimal_evidence_bundle_transportless(),
            }
            self.write_run(
                packet_root,
                run_id,
                json.dumps(raw_response),
                manifest_payload={
                    "schema_basis": {
                        "response_schema_repo_path": (
                            REPO_DIR
                            / "schemas"
                            / "protocol_lab"
                            / "experimental"
                            / "simple_read_vs_structured_read_contrast_v1_1.schema.json"
                        ).as_posix()
                    },
                    "run_identity": {
                        "run_id": run_id,
                        "fixture_id": fixture_id,
                        "protocol_id": "simple_read_vs_structured_read_contrast_v1_1",
                        "model_profile_id": "m_alternate_strong_reasoning_v1",
                        "runner_binding_id": "rb_openai_chatgpt54ext_real_local_v1",
                    },
                    "output_contract": {
                        "top_level_keys": [
                            "simple_vs_structured_adjudication",
                            "evidence_bundle",
                        ],
                        "sidecar_outputs": [
                            {
                                "response_key": "simple_vs_structured_adjudication",
                                "relative_path": primary_sidecar_path.relative_to(repo).as_posix(),
                            },
                            {
                                "response_key": "evidence_bundle",
                                "relative_path": evidence_sidecar_path.relative_to(repo).as_posix(),
                            },
                        ],
                    },
                },
            )

            report = validator.validate_packet(
                packet_root,
                [run_id],
                write_sidecars=True,
            )

            self.assertEqual("pass", report.overall_result)
            result = report.run_results[0]
            self.assertEqual([], result.blocker_codes)
            self.assertTrue(evidence_sidecar_path.exists())
            self.assertTrue(primary_sidecar_path.exists())
            self.assertTrue(any("Hydrated missing `evidence_bundle` transport fields" in note for note in result.notes))

            sidecar_payload = json.loads(evidence_sidecar_path.read_text(encoding="utf-8"))
            self.assertEqual("complete", sidecar_payload["artifact_status"])
            self.assertEqual("evidence_bundle_v1", sidecar_payload["artifact_schema_id"])
            self.assertEqual(f"{run_id}__evidence_bundle_v1", sidecar_payload["evidence_bundle_id"])
            self.assertEqual(run_id, sidecar_payload["run_request_id"])
            self.assertEqual(fixture_id, sidecar_payload["fixture_id"])
            self.assertEqual("simple_read_vs_structured_read_contrast_v1_1", sidecar_payload["protocol_id"])
            self.assertEqual("m_alternate_strong_reasoning_v1", sidecar_payload["model_profile_id"])
            self.assertEqual("rb_openai_chatgpt54ext_real_local_v1", sidecar_payload["runner_binding_id"])
            self.assertEqual([], sidecar_payload["notes"])
            self.assertEqual([], sidecar_payload["items"])

            raw_saved_response = json.loads(response_path.read_text(encoding="utf-8"))
            self.assertEqual(raw_response, raw_saved_response)
        finally:
            validator.REPO_ROOT = original_repo_root
            shutil.rmtree(repo, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
