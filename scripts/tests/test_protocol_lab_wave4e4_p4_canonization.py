import json
import shutil
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))

import protocol_lab_wave4e4_p4_canonization as wave  # noqa: E402


STAMP = "20990101_0404"


class Wave4E4P4CanonizationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.backup_root = SCRIPTS_DIR / "_tmp_test_backups" / "wave4e4_p4_canonization"
        if self.backup_root.exists():
            shutil.rmtree(self.backup_root)
        self.backup_root.mkdir(parents=True, exist_ok=True)

        self.packet_dir, self.zip_path = wave.packet_paths_for_stamp(STAMP)
        self.removed_targets = [
            wave.NOVELTY_LEDGER_ROOT,
            REPO_ROOT / wave.CANONIZATION_REPORT_PATH,
            REPO_ROOT / wave.INTEGRATION_DECISION_REPORT_PATH,
            REPO_ROOT / wave.FINDINGS_REPORT_PATH,
            self.packet_dir,
            self.zip_path,
        ]
        self.preserved_targets = [
            REPO_ROOT / wave.PILOT_REVIEW_PATHS["NVDA_2024_2025_10k_item1a"],
            REPO_ROOT / wave.PILOT_REVIEW_PATHS["LLY_2024_2025_10k_item1a"],
            wave.EFFORT_SUMMARY_PATH,
        ]
        self.backups: list[tuple[Path, Path]] = []

        for index, target in enumerate([*self.removed_targets, *self.preserved_targets]):
            if target.exists():
                backup_path = self.backup_root / f"{index}_{target.name}"
                if target.is_dir():
                    shutil.copytree(target, backup_path)
                else:
                    shutil.copy2(target, backup_path)
                self.backups.append((target, backup_path))
                if target in self.removed_targets:
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink()

    def tearDown(self) -> None:
        for target in [*self.removed_targets, *self.preserved_targets]:
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()

        for target, backup_path in self.backups:
            target.parent.mkdir(parents=True, exist_ok=True)
            if backup_path.is_dir():
                shutil.copytree(backup_path, target)
            else:
                shutil.copy2(backup_path, target)

        shutil.rmtree(self.backup_root, ignore_errors=True)

    def test_generate_wave_materializes_canonized_outputs_and_packet(self) -> None:
        summary = wave.generate_wave(stamp=STAMP)

        self.assertEqual(summary.packet_dir, self.packet_dir)
        self.assertEqual(summary.zip_path, self.zip_path)
        self.assertTrue(summary.packet_dir.exists())
        self.assertTrue(summary.zip_path.exists())
        self.assertTrue(summary.renders_both_pilots)
        self.assertEqual(summary.biggest_remaining_blocker, wave.BIGGEST_REMAINING_BLOCKER)

        nvda_case_path = (
            wave.NOVELTY_LEDGER_ROOT
            / "NVDA_2024_2025_10k_item1a"
            / "p4_canonized_matrix_v1.json"
        )
        lly_case_path = (
            wave.NOVELTY_LEDGER_ROOT
            / "LLY_2024_2025_10k_item1a"
            / "p4_canonized_matrix_v1.json"
        )
        nvda_quality_path = wave.NOVELTY_LEDGER_ROOT / "nvda_p4_quality_notes_v1.json"
        lly_quality_path = wave.NOVELTY_LEDGER_ROOT / "lly_p4_quality_notes_v1.json"
        cross_summary_path = wave.NOVELTY_LEDGER_ROOT / "p4_canonized_summary_v1.json"
        p4_vs_p1_path = wave.NOVELTY_LEDGER_ROOT / "p4_vs_p1_summary_v1.json"

        for path in [
            nvda_case_path,
            lly_case_path,
            nvda_quality_path,
            lly_quality_path,
            cross_summary_path,
            p4_vs_p1_path,
            REPO_ROOT / wave.CANONIZATION_REPORT_PATH,
            REPO_ROOT / wave.INTEGRATION_DECISION_REPORT_PATH,
            REPO_ROOT / wave.FINDINGS_REPORT_PATH,
        ]:
            self.assertTrue(path.exists(), path.as_posix())

        nvda_case = json.loads(nvda_case_path.read_text(encoding="utf-8"))
        lly_case = json.loads(lly_case_path.read_text(encoding="utf-8"))
        nvda_quality = json.loads(nvda_quality_path.read_text(encoding="utf-8"))
        lly_quality = json.loads(lly_quality_path.read_text(encoding="utf-8"))
        effort_summary = json.loads(wave.EFFORT_SUMMARY_PATH.read_text(encoding="utf-8"))
        nvda_review = json.loads(
            (REPO_ROOT / wave.PILOT_REVIEW_PATHS["NVDA_2024_2025_10k_item1a"]).read_text(
                encoding="utf-8"
            )
        )
        lly_review = json.loads(
            (REPO_ROOT / wave.PILOT_REVIEW_PATHS["LLY_2024_2025_10k_item1a"]).read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual("p4_canonized_matrix_v1", nvda_case["artifact_schema_id"])
        self.assertEqual("p4_canonized_matrix_v1", lly_case["artifact_schema_id"])
        self.assertTrue(nvda_case["suitable_for_limited_app_integration"])
        self.assertTrue(lly_case["suitable_for_limited_app_integration"])
        self.assertEqual(
            "canonized_with_transport_repair",
            nvda_case["canonized_runs"][1]["canonization_status"],
        )
        self.assertEqual(
            "canonized_with_evidence_row_correction",
            lly_case["canonized_runs"][1]["canonization_status"],
        )
        self.assertIn("AI Diffusion", nvda_case["module_sections"]["fresh_2025_specifics"][0]["label"])
        self.assertIn(
            "Updated Medicare selection",
            lly_case["module_sections"]["fresh_2025_specifics"][1]["label"],
        )

        self.assertEqual("p4_quality_notes_v1", nvda_quality["artifact_schema_id"])
        self.assertEqual("p4_quality_notes_v1", lly_quality["artifact_schema_id"])
        self.assertEqual(2, len(nvda_quality["notes"]))
        self.assertEqual(1, len(lly_quality["notes"]))

        self.assertNotIn(
            "novelty-ledger workflows",
            "\n".join(nvda_review["does_not_yet_support"]).lower(),
        )
        self.assertNotIn(
            "novelty-ledger workflows",
            "\n".join(lly_review["does_not_yet_support"]).lower(),
        )
        self.assertIn("secondary novelty-ledger module", "\n".join(nvda_review["supports"]).lower())
        self.assertIn("secondary novelty-ledger module", "\n".join(lly_review["supports"]).lower())
        self.assertNotIn("novelty-ledger coverage", effort_summary["still_should_not_claim"].lower())
        self.assertIn("equal-lane p4 expansion", effort_summary["still_should_not_claim"].lower())

        packet_readme = (summary.packet_dir / wave.ROOT_README_NAME).read_text(encoding="utf-8")
        changed_manifest = (summary.packet_dir / wave.CHANGED_FILES_MANIFEST_NAME).read_text(
            encoding="utf-8"
        )
        render_preview = (summary.packet_dir / wave.RENDER_PREVIEW_NAME).read_text(
            encoding="utf-8"
        )
        canonization_report = (
            REPO_ROOT / wave.CANONIZATION_REPORT_PATH
        ).read_text(encoding="utf-8")
        integration_report = (
            REPO_ROOT / wave.INTEGRATION_DECISION_REPORT_PATH
        ).read_text(encoding="utf-8")
        findings_report = (REPO_ROOT / wave.FINDINGS_REPORT_PATH).read_text(encoding="utf-8")

        self.assertIn("canonized novelty-ledger artifacts", packet_readme)
        self.assertIn("render preview", packet_readme.lower())
        self.assertIn("scripts/protocol_lab_wave4e4_p4_canonization.py", changed_manifest)
        self.assertIn("scripts/tests/test_protocol_lab_novelty_ledger_data.mjs", changed_manifest)
        self.assertIn("novelty ledger module", render_preview.lower())
        self.assertIn("transport-only repair", canonization_report.lower())
        self.assertIn("secondary novelty-ledger module", integration_report.lower())
        self.assertIn("fresh-versus-reused clarity", findings_report.lower())

        console_text = "\n".join(summary.console_summary_lines)
        self.assertIn(str(summary.packet_dir.resolve()), console_text)
        self.assertIn(str(summary.zip_path.resolve()), console_text)
        self.assertIn("whether NVDA and LLY both render the limited P4 module: yes", console_text)


if __name__ == "__main__":
    unittest.main()
