import sys
import unittest
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import protocol_lab_wave4b_reviewability as wave4b  # noqa: E402


def make_locator(*, accession: str, filing_date: str, source_path: str, char_start: int | None, char_end: int | None) -> dict[str, Any]:
    return {
        "accession_number": accession,
        "filing_date": filing_date,
        "form_type": "10-K",
        "section_id": "item_1a",
        "source_path": source_path,
        "char_start": char_start,
        "char_end": char_end,
    }


def make_tagged_pack() -> dict[str, Any]:
    return {
        "input_pack_id": "i2_tagged_document_packet_v1",
        "pack_kind": "tagged_paragraph_packet",
        "rendered_inputs": {
            "documents": [
                {
                    "document_id": "tagged_document_2024",
                    "year_label": "FY2024",
                    "content_text": None,
                    "source_input_path": "data/sec_cache/example.txt.gz",
                    "source_locator": make_locator(
                        accession="0000000000-24-000001",
                        filing_date="2024-02-21",
                        source_path="data/sec_cache/example.txt.gz",
                        char_start=0,
                        char_end=200,
                    ),
                    "paragraphs": [
                        {
                            "paragraph_id": "fy2024_p001",
                            "text": "Export controls tightened and GPU demand stayed elevated.",
                            "source_locator": make_locator(
                                accession="0000000000-24-000001",
                                filing_date="2024-02-21",
                                source_path="data/sec_cache/example.txt.gz",
                                char_start=10,
                                char_end=65,
                            ),
                        }
                    ],
                }
            ]
        },
    }


def make_document_pack() -> dict[str, Any]:
    return {
        "input_pack_id": "i0_filed_full_text_v1",
        "pack_kind": "section_text_pair",
        "rendered_inputs": {
            "documents": [
                {
                    "document_id": "filed_full_text_2024",
                    "year_label": "FY2024",
                    "content_text": "Alpha beta gamma delta.",
                    "source_input_path": "data/sec_cache/full_text.txt.gz",
                    "source_locator": make_locator(
                        accession="0000000000-24-000002",
                        filing_date="2024-02-21",
                        source_path="data/sec_cache/full_text.txt.gz",
                        char_start=0,
                        char_end=23,
                    ),
                }
            ]
        },
    }


def make_run_request(run_request_id: str) -> dict[str, Any]:
    return {
        "run_request_id": run_request_id,
        "fixture_id": wave4b.FIXTURE_ID,
        "protocol_id": "p2_tagged_input_contract_v1",
        "model_profile_id": "m_primary_strong_reasoning_v1",
        "runner_binding_id": "rb_openai_gpt53codex_real_local_v1",
        "stack_id": "s_test",
        "input_pack_id": "i2_tagged_document_packet_v1",
    }


class TestWave4bEvidenceResolution(unittest.TestCase):
    def test_tagged_pack_success(self) -> None:
        bundle = {
            "items": [
                {
                    "evidence_id": "ev_1",
                    "year_label": "FY2024",
                    "paragraph_id": "fy2024_p001",
                    "quote_text": "GPU demand stayed elevated",
                    "source_locator": make_locator(
                        accession="0000000000-24-000001",
                        filing_date="2024-02-21",
                        source_path="data/sec_cache/example.txt.gz",
                        char_start=20,
                        char_end=44,
                    ),
                }
            ]
        }
        resolution = wave4b.resolve_evidence_items(make_tagged_pack(), bundle)
        self.assertEqual("pass", resolution["resolution_summary"]["overall_result"])
        self.assertEqual("pass", resolution["items"][0]["checks"]["paragraph_id_exists"])
        self.assertEqual("pass", resolution["items"][0]["checks"]["quote_text_present"])

    def test_year_label_mismatch(self) -> None:
        bundle = {
            "items": [
                {
                    "evidence_id": "ev_2",
                    "year_label": "FY2025",
                    "paragraph_id": "fy2024_p001",
                    "quote_text": "GPU demand stayed elevated",
                    "source_locator": make_locator(
                        accession="0000000000-24-000001",
                        filing_date="2024-02-21",
                        source_path="data/sec_cache/example.txt.gz",
                        char_start=20,
                        char_end=44,
                    ),
                }
            ]
        }
        resolution = wave4b.resolve_evidence_items(make_tagged_pack(), bundle)
        self.assertEqual("fail", resolution["resolution_summary"]["overall_result"])
        self.assertEqual("fail", resolution["items"][0]["checks"]["year_label_match"])

    def test_quote_not_found_failure(self) -> None:
        bundle = {
            "items": [
                {
                    "evidence_id": "ev_3",
                    "year_label": "FY2024",
                    "paragraph_id": "fy2024_p001",
                    "quote_text": "this exact phrase does not exist",
                    "source_locator": make_locator(
                        accession="0000000000-24-000001",
                        filing_date="2024-02-21",
                        source_path="data/sec_cache/example.txt.gz",
                        char_start=20,
                        char_end=44,
                    ),
                }
            ]
        }
        resolution = wave4b.resolve_evidence_items(make_tagged_pack(), bundle)
        self.assertEqual("fail", resolution["items"][0]["checks"]["quote_text_present"])
        self.assertEqual("fail", resolution["items"][0]["overall_result"])

    def test_locator_only_document_level_case(self) -> None:
        bundle = {
            "items": [
                {
                    "evidence_id": "ev_4",
                    "year_label": "FY2024",
                    "paragraph_id": "",
                    "quote_text": "beta gamma",
                    "source_locator": make_locator(
                        accession="0000000000-24-000002",
                        filing_date="2024-02-21",
                        source_path="data/sec_cache/full_text.txt.gz",
                        char_start=None,
                        char_end=None,
                    ),
                }
            ]
        }
        resolution = wave4b.resolve_evidence_items(make_document_pack(), bundle)
        self.assertEqual("pass", resolution["resolution_summary"]["overall_result"])
        self.assertEqual("not_applicable", resolution["items"][0]["checks"]["paragraph_id_exists"])
        self.assertEqual("pass", resolution["items"][0]["checks"]["locator_matches_source"])

    def test_empty_scaffolded_bundle_case(self) -> None:
        resolution = wave4b.resolve_evidence_items(None, {"items": []})
        self.assertEqual("not_run", resolution["resolution_summary"]["overall_result"])
        self.assertEqual([], resolution["items"])

    def test_execution_trace_payload_keeps_raw_capture_local_only(self) -> None:
        run_request = make_run_request("r_wave4b")
        prompt_render_payload = {"artifact_status": "complete", "prompt_render_id": "r_wave4b__prompt_render_v1"}
        payload = wave4b.build_execution_trace_payload(run_request, prompt_render_payload, None)
        self.assertEqual("rendered", payload["run_state"])
        self.assertIsNone(payload["raw_response_path"])
        self.assertNotIn("reports/protocol_lab/raw_runs", str(payload["notes"]))
        self.assertIn("Raw capture remains local-only", payload["notes"][1])


if __name__ == "__main__":
    unittest.main()
