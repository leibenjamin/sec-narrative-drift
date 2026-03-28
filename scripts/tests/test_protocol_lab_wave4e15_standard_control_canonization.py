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

import protocol_lab_wave4e15_standard_control_canonization as wave  # noqa: E402


class Wave4E15StandardControlCanonizationTest(unittest.TestCase):
    def write_json(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def seed_pilot_matrix(self, repo: Path, fixture_id: str, ticker: str, issuer_name: str) -> None:
        self.write_json(
            repo
            / "public"
            / "data"
            / "business_document_protocol_lab"
            / "pilot_matrices"
            / fixture_id
            / "pilot_matrix_v1.json",
            {
                "artifact_schema_id": "pilot_matrix_v1",
                "matrix_id": f"{fixture_id}__desktop_pilot_matrix_v1",
                "fixture_id": fixture_id,
                "pair_info": {
                    "ticker": ticker,
                    "issuer_name": issuer_name,
                    "year_from": 2024,
                    "year_to": 2025,
                    "form_type": "10-K",
                    "section_id": "item_1a",
                },
            },
        )

    def seed_run(self, repo: Path, run_id: str, response_text: str) -> None:
        run_dir = repo / wave.STANDARD_PACKET_ROOT_NAME / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "response.json").write_text(response_text, encoding="utf-8")
        (run_dir / "run_manifest.json").write_text("{}", encoding="utf-8")

    def seed_support_files(self, repo: Path) -> None:
        for relative_path in [*wave.SCRIPT_AND_TEST_PATHS, *wave.SOURCE_SUPPORT_PATHS]:
            full_path = repo / relative_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(f"placeholder for {relative_path.as_posix()}\n", encoding="utf-8")

    def patched_repo(self, repo: Path) -> ExitStack:
        business_root = repo / "public" / "data" / "business_document_protocol_lab"
        reports_root = repo / "reports" / "protocol_lab"
        stack = ExitStack()
        stack.enter_context(patch.object(wave, "REPO_ROOT", repo))
        stack.enter_context(patch.object(wave, "BUSINESS_ROOT", business_root))
        stack.enter_context(patch.object(wave, "PILOT_MATRICES_ROOT", business_root / "pilot_matrices"))
        stack.enter_context(patch.object(wave, "STANDARD_CONTROLS_ROOT", business_root / "standard_controls"))
        stack.enter_context(
            patch.object(wave, "STANDARD_COMPARISONS_ROOT", business_root / "standard_controls" / "comparisons")
        )
        stack.enter_context(patch.object(wave, "REPORTS_ROOT", reports_root))
        stack.enter_context(patch.object(wave, "STANDARD_PACKET_ROOT", repo / wave.STANDARD_PACKET_ROOT_NAME))
        stack.enter_context(
            patch.object(wave, "VALIDATION_REPORT_PATH", reports_root / "wave4e15_standard_control_validation_report.json")
        )
        stack.enter_context(
            patch.object(wave, "CANONIZATION_REPORT_PATH", reports_root / "wave4e15_standard_control_canonization_report.md")
        )
        stack.enter_context(
            patch.object(wave, "FINDINGS_REPORT_PATH", reports_root / "wave4e15_standard_control_findings.md")
        )
        stack.enter_context(patch.object(wave.packet_validator, "REPO_ROOT", repo))
        stack.enter_context(patch.object(wave.packet_validator, "REPORTS_ROOT", reports_root))
        stack.enter_context(
            patch.object(
                wave.packet_validator,
                "DEFAULT_REPORT_PATH",
                reports_root / "wave4e15_standard_control_validation_report.json",
            )
        )
        return stack

    def test_generate_wave_materializes_artifacts_packet_and_zip(self) -> None:
        repo = TMP_ROOT / "wave_case"
        shutil.rmtree(repo, ignore_errors=True)
        repo.mkdir(parents=True, exist_ok=True)
        try:
            self.seed_pilot_matrix(repo, "NVDA_2024_2025_10k_item1a", "NVDA", "NVIDIA Corporation")
            self.seed_pilot_matrix(repo, "LLY_2024_2025_10k_item1a", "LLY", "Eli Lilly and Company")
            self.seed_support_files(repo)

            self.seed_run(
                repo,
                "NVDA_00_b0_unstructured_frontier_baseline_standard",
                json.dumps({"brief_markdown": "brief", "evidence": []}),
            )
            self.seed_run(
                repo,
                "NVDA_02_p1_i2_tagged_packet_standard",
                json.dumps({"change_brief": {}, "evidence_bundle": {}}),
            )
            self.seed_run(
                repo,
                "NVDA_03_p2_i2_tagged_protocol_standard",
                json.dumps({"change_brief": {}, "evidence_bundle": {}}),
            )
            self.seed_run(
                repo,
                "LLY_00_b0_unstructured_frontier_baseline_standard",
                json.dumps({"brief_markdown": "brief", "evidence": []}),
            )
            self.seed_run(
                repo,
                "LLY_02_p1_i2_tagged_packet_standard",
                '{"change_brief":{},"evidence_bundle":{"items":[]}',
            )
            self.seed_run(
                repo,
                "LLY_03_p2_i2_tagged_protocol_standard",
                '{"change_brief":{},"evidence_bundle":{"items":[]}',
            )

            with self.patched_repo(repo):
                summary = wave.generate_wave(stamp="20990101_0101")

            self.assertFalse(summary.validation_passed)
            self.assertTrue(summary.packet_dir.exists())
            self.assertTrue(summary.zip_path.exists())
            self.assertIn("whether the six standard-thinking runs validated successfully: no", "\n".join(summary.console_summary_lines))

            validation_report = json.loads((repo / "reports" / "protocol_lab" / "wave4e15_standard_control_validation_report.json").read_text(encoding="utf-8"))
            self.assertEqual("fail", validation_report["overall_result"])

            nvda_matrix = json.loads(
                (
                    repo
                    / "public"
                    / "data"
                    / "business_document_protocol_lab"
                    / "standard_controls"
                    / "NVDA_2024_2025_10k_item1a"
                    / "standard_control_matrix_v1.json"
                ).read_text(encoding="utf-8")
            )
            lly_matrix = json.loads(
                (
                    repo
                    / "public"
                    / "data"
                    / "business_document_protocol_lab"
                    / "standard_controls"
                    / "LLY_2024_2025_10k_item1a"
                    / "standard_control_matrix_v1.json"
                ).read_text(encoding="utf-8")
            )
            summary_payload = json.loads(
                (
                    repo
                    / "public"
                    / "data"
                    / "business_document_protocol_lab"
                    / "standard_controls"
                    / "standard_control_summary_v1.json"
                ).read_text(encoding="utf-8")
            )

            self.assertEqual("standard_control_matrix_v1", nvda_matrix["artifact_schema_id"])
            self.assertEqual("standard_control_matrix_v1", lly_matrix["artifact_schema_id"])
            self.assertEqual("standard_control_summary_v1", summary_payload["artifact_schema_id"])
            self.assertIn("fail JSON parseability", "\n".join(lly_matrix["caveats"]))

            packet_readme = (summary.packet_dir / "README.md").read_text(encoding="utf-8")
            changed_manifest = (summary.packet_dir / "changed_files_manifest.md").read_text(encoding="utf-8")
            self.assertIn("standard-control canonization artifacts", packet_readme)
            self.assertIn("scripts/protocol_lab_validate_desktop_packet_responses.py", changed_manifest)
            self.assertIn("src/lib/protocolLabMatrixTypes.ts", changed_manifest)
        finally:
            shutil.rmtree(repo, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
