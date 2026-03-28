import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import protocol_lab_wave4e1_standard_thinking_controls_packet as wave  # noqa: E402


STAMP = "20990101_0101"
COMMON_RUN_FILES = {
    "README.md",
    "desktop_run_instructions.md",
    "desktop_attachment_set.md",
    "starter_prompt.txt",
    "run_manifest.json",
    "eval_scaffold.json",
}
EXPECTED_SOURCE_FILES = {
    "NVDA_00_b0_unstructured_frontier_baseline_standard": {
        "source_case_manifest_v1.json",
        "i2_tagged_document_packet_v1.json",
        "i2_tagged_document_packet_v1.rendered_inputs.json",
        wave.I2_FY2024_FILENAME,
        wave.I2_FY2025_FILENAME,
    },
    "NVDA_02_p1_i2_tagged_packet_standard": {
        "p1_structured_contract_v1.md",
        "source_case_manifest_v1.json",
        "i2_tagged_document_packet_v1.json",
        "i2_tagged_document_packet_v1.rendered_inputs.json",
        wave.I2_FY2024_FILENAME,
        wave.I2_FY2025_FILENAME,
    },
    "NVDA_03_p2_i2_tagged_protocol_standard": {
        "p2_tagged_input_contract_v1.md",
        "source_case_manifest_v1.json",
        "i2_tagged_document_packet_v1.json",
        "i2_tagged_document_packet_v1.rendered_inputs.json",
        wave.I2_FY2024_FILENAME,
        wave.I2_FY2025_FILENAME,
    },
    "LLY_00_b0_unstructured_frontier_baseline_standard": {
        "source_case_manifest_v1.json",
        "i2_tagged_document_packet_v1.json",
        "i2_tagged_document_packet_v1.rendered_inputs.json",
        wave.I2_FY2024_FILENAME,
        wave.I2_FY2025_FILENAME,
    },
    "LLY_02_p1_i2_tagged_packet_standard": {
        "p1_structured_contract_v1.md",
        "source_case_manifest_v1.json",
        "i2_tagged_document_packet_v1.json",
        "i2_tagged_document_packet_v1.rendered_inputs.json",
        wave.I2_FY2024_FILENAME,
        wave.I2_FY2025_FILENAME,
    },
    "LLY_03_p2_i2_tagged_protocol_standard": {
        "p2_tagged_input_contract_v1.md",
        "source_case_manifest_v1.json",
        "i2_tagged_document_packet_v1.json",
        "i2_tagged_document_packet_v1.rendered_inputs.json",
        wave.I2_FY2024_FILENAME,
        wave.I2_FY2025_FILENAME,
    },
}


class Wave4E1StandardThinkingControlsPacketTest(unittest.TestCase):
    def setUp(self) -> None:
        self.backup_root = Path(tempfile.mkdtemp())
        self.packet_dir, self.zip_path = wave.packet_paths_for_stamp(STAMP)
        self.targets = [
            self.packet_dir,
            self.zip_path,
            wave.PLAN_REPORT_PATH,
            wave.PACKET_REPORT_PATH,
        ]
        self.backups: list[tuple[Path, Path]] = []
        for index, target in enumerate(self.targets):
            if target.exists():
                backup_path = self.backup_root / f"{index}_{target.name}"
                shutil.move(str(target), str(backup_path))
                self.backups.append((target, backup_path))

    def tearDown(self) -> None:
        for target in self.targets:
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
        for target, backup_path in self.backups:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(backup_path), str(target))
        shutil.rmtree(self.backup_root, ignore_errors=True)

    def test_generate_packet_outputs_standard_thinking_controls(self) -> None:
        summary = wave.generate_packet(stamp=STAMP)

        self.assertEqual(summary.packet_dir, self.packet_dir)
        self.assertEqual(summary.zip_path, self.zip_path)
        self.assertTrue(summary.packet_dir.exists())
        self.assertTrue(summary.zip_path.exists())
        self.assertTrue(wave.PLAN_REPORT_PATH.exists())
        self.assertTrue(wave.PACKET_REPORT_PATH.exists())
        self.assertTrue(summary.both_pilot_slices_intact)
        self.assertEqual(summary.biggest_remaining_blocker, wave.BIGGEST_REMAINING_BLOCKER)
        self.assertEqual(summary.modified_copy_polish_files, [path.as_posix() for path in wave.UI_COPY_POLISH_FILES])

        console_text = "\n".join(summary.console_summary_lines)
        self.assertIn(str(summary.packet_dir.resolve()), console_text)
        self.assertIn(str(summary.zip_path.resolve()), console_text)
        self.assertIn("whether both NVDA and LLY pilot slices remain intact: yes", console_text)
        self.assertIn(wave.BIGGEST_REMAINING_BLOCKER, console_text)

        expected_run_ids = list(EXPECTED_SOURCE_FILES.keys())
        self.assertEqual(summary.included_run_ids, expected_run_ids)
        self.assertEqual(
            sorted(path.name for path in summary.packet_dir.iterdir() if path.is_dir() and path.name in EXPECTED_SOURCE_FILES),
            sorted(expected_run_ids),
        )
        self.assertTrue((summary.packet_dir / wave.ROOT_README_NAME).exists())
        self.assertTrue((summary.packet_dir / wave.STANDARD_MANIFEST_NAME).exists())
        self.assertTrue((summary.packet_dir / wave.CHANGED_FILES_MANIFEST_NAME).exists())

        plan_report = wave.PLAN_REPORT_PATH.read_text(encoding="utf-8")
        packet_report = wave.PACKET_REPORT_PATH.read_text(encoding="utf-8")
        root_readme = (summary.packet_dir / wave.ROOT_README_NAME).read_text(encoding="utf-8")
        standard_manifest = (summary.packet_dir / wave.STANDARD_MANIFEST_NAME).read_text(encoding="utf-8")
        changed_files_manifest = (summary.packet_dir / wave.CHANGED_FILES_MANIFEST_NAME).read_text(encoding="utf-8")

        self.assertIn("Why 01 Is Excluded", plan_report)
        self.assertIn("smallest useful", plan_report.lower())
        self.assertIn("Small UI Copy Polish Applied", packet_report)
        self.assertIn("standard thinking, not extended thinking", root_readme)
        self.assertIn("Why This Is The Smallest Useful Wave", standard_manifest)
        for path in wave.MODIFIED_REPO_FILES:
            self.assertIn(path.as_posix(), changed_files_manifest)
            self.assertTrue((summary.packet_dir / path).exists(), path.as_posix())

        for run_name in expected_run_ids:
            run_dir = summary.packet_dir / run_name
            self.assertEqual({path.name for path in run_dir.iterdir() if path.is_file()}, COMMON_RUN_FILES)
            sources_dir = run_dir / "sources"
            self.assertEqual({path.name for path in sources_dir.iterdir()}, EXPECTED_SOURCE_FILES[run_name])

            starter_prompt = (run_dir / "starter_prompt.txt").read_text(encoding="utf-8")
            self.assertIn("standard thinking", starter_prompt)
            self.assertIn("Use only the attached files.", starter_prompt)
            self.assertNotIn("run_manifest.json", starter_prompt)
            self.assertLess(len(starter_prompt), 1500)

            instructions = (run_dir / "desktop_run_instructions.md").read_text(encoding="utf-8")
            self.assertIn("standard thinking, not extended thinking", instructions)
            self.assertIn("Do not upload `starter_prompt.txt`", instructions)
            self.assertIn("Expected output shape:", instructions)

            attachment_guidance = (run_dir / "desktop_attachment_set.md").read_text(encoding="utf-8")
            self.assertIn("Optional combined rendered-input fallback", attachment_guidance)
            self.assertIn("Do Not Attach These Files", attachment_guidance)
            self.assertIn("run_manifest.json", attachment_guidance)

            manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["artifact_schema_id"], "desktop_core_run_manifest_v1")
            self.assertEqual(manifest["desktop_target"]["runner_binding_id"], wave.LINEAGE_RUNNER_BINDING_ID)
            self.assertEqual(manifest["desktop_target"]["campaign_id"], wave.LINEAGE_CAMPAIGN_ID)
            self.assertEqual(manifest["desktop_target"]["lineage_model_name"], wave.LINEAGE_MODEL_NAME)
            self.assertEqual(manifest["desktop_target"]["model_name"], wave.MODEL_NAME)
            self.assertEqual(manifest["desktop_target"]["reasoning_mode"], wave.REASONING_MODE)
            self.assertTrue(manifest["desktop_target"]["fresh_thread_required"])
            self.assertEqual(manifest["readiness"]["desktop_ready_label"], "Desktop-ready")
            self.assertEqual(manifest["readiness"]["practical_limit_status"], "not_expected_to_exceed_desktop_limits")
            self.assertEqual(len(manifest["input_basis"]["optional_attachment_sets"]), 2)
            self.assertEqual(manifest["input_basis"]["optional_attachment_sets"][0]["attachment_set_id"], wave.I2_SPLIT_ATTACHMENT_SET_ID)
            self.assertTrue(manifest["input_basis"]["optional_attachment_sets"][0]["is_default"])
            self.assertEqual(manifest["input_basis"]["optional_attachment_sets"][1]["attachment_set_id"], wave.I2_COMBINED_ATTACHMENT_SET_ID)
            self.assertFalse(manifest["input_basis"]["optional_attachment_sets"][1]["is_default"])
            self.assertIn(f"{summary.packet_dir.name}/{run_name}/sources/{wave.I2_FY2024_FILENAME}", manifest["input_basis"]["attachment_list"])
            self.assertIn(f"{summary.packet_dir.name}/{run_name}/sources/{wave.I2_FY2025_FILENAME}", manifest["input_basis"]["attachment_list"])
            self.assertNotIn(f"{summary.packet_dir.name}/{run_name}/sources/i2_tagged_document_packet_v1.rendered_inputs.json", manifest["input_basis"]["attachment_list"])
            self.assertIn(f"{summary.packet_dir.name}/{run_name}/run_manifest.json", manifest["input_basis"]["operator_only_files"])
            self.assertIn(f"{summary.packet_dir.name}/{run_name}/starter_prompt.txt", manifest["input_basis"]["operator_only_files"])
            self.assertIn(f"{summary.packet_dir.name}/{run_name}/sources/i2_tagged_document_packet_v1.json", manifest["input_basis"]["operator_only_files"])

            if "_00_b0_" in run_name:
                self.assertEqual(manifest["protocol_basis"]["protocol_mode"], "desktop_packet_only")
                self.assertIsNone(manifest["protocol_basis"]["canonical_contract_repo_path"])
                self.assertEqual(manifest["output_contract"]["top_level_keys"], ["brief_markdown", "evidence"])
            elif "_02_" in run_name:
                self.assertEqual(manifest["protocol_basis"]["canonical_protocol_id"], "p1_structured_contract_v1")
                self.assertIn("source_run_request_repo_path", manifest["protocol_basis"])
                self.assertEqual(manifest["output_contract"]["top_level_keys"], ["change_brief", "evidence_bundle"])
            else:
                self.assertEqual(manifest["protocol_basis"]["canonical_protocol_id"], "p2_tagged_input_contract_v1")
                self.assertEqual(manifest["output_contract"]["top_level_keys"], ["change_brief", "evidence_bundle"])

        with zipfile.ZipFile(summary.zip_path) as handle:
            names = set(handle.namelist())
        self.assertIn(f"{summary.packet_dir.name}/{wave.ROOT_README_NAME}", names)
        self.assertIn(f"{summary.packet_dir.name}/{wave.STANDARD_MANIFEST_NAME}", names)
        self.assertIn(f"{summary.packet_dir.name}/{wave.CHANGED_FILES_MANIFEST_NAME}", names)
        self.assertIn(f"{summary.packet_dir.name}/reports/protocol_lab/{wave.PLAN_REPORT_PATH.name}", names)
        self.assertIn(f"{summary.packet_dir.name}/reports/protocol_lab/{wave.PACKET_REPORT_PATH.name}", names)
        self.assertIn(f"{summary.packet_dir.name}/src/components/ProtocolLabPilotMatrixPanel.tsx", names)
        self.assertIn(f"{summary.packet_dir.name}/scripts/protocol_lab_wave4e1_standard_thinking_controls_packet.py", names)


if __name__ == "__main__":
    unittest.main()
