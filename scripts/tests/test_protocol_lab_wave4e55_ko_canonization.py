import json
import shutil
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))

import protocol_lab_wave4e55_ko_canonization as wave  # noqa: E402


STAMP = "20990101_0555"


class Wave4E55KOCanonizationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.backup_root = SCRIPTS_DIR / "_tmp_test_backups" / "wave4e55_ko_canonization"
        if self.backup_root.exists():
            shutil.rmtree(self.backup_root)
        self.backup_root.mkdir(parents=True, exist_ok=True)

        self.packet_dir, self.zip_path = wave.packet_paths_for_stamp(STAMP)
        self.removed_targets = [
            REPO_ROOT
            / "public/data/business_document_protocol_lab/pilot_matrices/KO_2024_2025_10k_item1a",
            REPO_ROOT
            / "public/data/business_document_protocol_lab/skeptic_cases/KO_2024_2025_10k_item1a",
            REPO_ROOT
            / "public/data/business_document_protocol_lab/novelty_ledger/KO_2024_2025_10k_item1a",
            REPO_ROOT
            / "public/data/business_document_protocol_lab/skeptic_cases/third_pilot_summary_v1.json",
            REPO_ROOT
            / "public/data/business_document_protocol_lab/skeptic_cases/vivid_vs_skeptic_summary_v1.json",
            REPO_ROOT / wave.CURRENT_CASE_MIX_PATH,
            REPO_ROOT / wave.PILOT_REGISTRY_PATH,
            REPO_ROOT / wave.P4_SUMMARY_PATH,
            REPO_ROOT / wave.P4_VS_P1_SUMMARY_PATH,
            REPO_ROOT / wave.CANONIZATION_REPORT_PATH,
            REPO_ROOT / wave.INTEGRATION_DECISION_REPORT_PATH,
            REPO_ROOT / wave.VIVID_VS_SKEPTIC_REPORT_PATH,
            REPO_ROOT / wave.PRODUCT_FRAMING_REPORT_PATH,
            self.packet_dir,
            self.zip_path,
        ]
        self.preserved_targets = [
            REPO_ROOT / wave.PILOT_REVIEW_PATHS["NVDA_2024_2025_10k_item1a"],
            REPO_ROOT / wave.PILOT_REVIEW_PATHS["LLY_2024_2025_10k_item1a"],
        ]
        self.targets = [*self.removed_targets, *self.preserved_targets]
        self.backups: list[tuple[Path, Path]] = []

        for index, target in enumerate(self.targets):
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
        for target in self.targets:
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

    def test_generate_wave_materializes_ko_outputs_and_packet(self) -> None:
        summary = wave.generate_wave(stamp=STAMP)

        self.assertEqual(summary.packet_dir, self.packet_dir)
        self.assertEqual(summary.zip_path, self.zip_path)
        self.assertTrue(summary.packet_dir.exists())
        self.assertTrue(summary.zip_path.exists())
        self.assertTrue(summary.ko_visible_integration)
        self.assertTrue(summary.app_visible_framing_updated)
        self.assertEqual(summary.biggest_remaining_blocker, wave.BIGGEST_REMAINING_BLOCKER)

        ko_matrix_path = (
            REPO_ROOT
            / "public/data/business_document_protocol_lab/pilot_matrices/KO_2024_2025_10k_item1a/pilot_matrix_v1.json"
        )
        ko_story_path = (
            REPO_ROOT
            / "public/data/business_document_protocol_lab/pilot_matrices/KO_2024_2025_10k_item1a/pilot_matrix_story_v1.json"
        )
        ko_review_path = (
            REPO_ROOT
            / "public/data/business_document_protocol_lab/pilot_matrices/KO_2024_2025_10k_item1a/pilot_matrix_review_v1.json"
        )
        ko_skeptic_matrix_path = (
            REPO_ROOT
            / "public/data/business_document_protocol_lab/skeptic_cases/KO_2024_2025_10k_item1a/ko_canonized_matrix_v1.json"
        )
        ko_skeptic_quality_path = (
            REPO_ROOT
            / "public/data/business_document_protocol_lab/skeptic_cases/KO_2024_2025_10k_item1a/ko_quality_notes_v1.json"
        )
        ko_p4_path = (
            REPO_ROOT
            / "public/data/business_document_protocol_lab/novelty_ledger/KO_2024_2025_10k_item1a/p4_canonized_matrix_v1.json"
        )
        current_case_mix_path = REPO_ROOT / wave.CURRENT_CASE_MIX_PATH

        for path in [
            ko_matrix_path,
            ko_story_path,
            ko_review_path,
            ko_skeptic_matrix_path,
            ko_skeptic_quality_path,
            ko_p4_path,
            current_case_mix_path,
            REPO_ROOT / wave.CANONIZATION_REPORT_PATH,
            REPO_ROOT / wave.INTEGRATION_DECISION_REPORT_PATH,
            REPO_ROOT / wave.VIVID_VS_SKEPTIC_REPORT_PATH,
            REPO_ROOT / wave.PRODUCT_FRAMING_REPORT_PATH,
        ]:
            self.assertTrue(path.exists(), path.as_posix())

        ko_matrix = json.loads(ko_matrix_path.read_text(encoding="utf-8"))
        ko_story = json.loads(ko_story_path.read_text(encoding="utf-8"))
        ko_review = json.loads(ko_review_path.read_text(encoding="utf-8"))
        ko_skeptic_matrix = json.loads(ko_skeptic_matrix_path.read_text(encoding="utf-8"))
        ko_skeptic_quality = json.loads(ko_skeptic_quality_path.read_text(encoding="utf-8"))
        ko_p4 = json.loads(ko_p4_path.read_text(encoding="utf-8"))
        p4_summary = json.loads((REPO_ROOT / wave.P4_SUMMARY_PATH).read_text(encoding="utf-8"))
        current_case_mix = json.loads(current_case_mix_path.read_text(encoding="utf-8"))

        self.assertEqual("pilot_matrix_v1", ko_matrix["artifact_schema_id"])
        self.assertEqual([], ko_matrix["comparison_pairs"])
        self.assertEqual(["02_p1_i2_tagged_packet"], ko_matrix["ordered_cell_ids"])
        self.assertEqual("pilot_active_skeptic_case_slice", ko_matrix["pilot_status"]["state"])

        self.assertEqual("pilot_matrix_story_v1", ko_story["artifact_schema_id"])
        self.assertEqual(4, len(ko_story["consensus_findings"]))
        self.assertEqual(3, len(ko_story["disagreement_findings"]))
        self.assertIn("lower-drift skeptic case", ko_story["why_this_case_matters"])

        self.assertEqual("pilot_matrix_review_v1", ko_review["artifact_schema_id"])
        self.assertIn("visible third pilot", "\n".join(ko_review["supports"]).lower())
        self.assertIn("no ko 03 lane", ko_review["why_03_is_main_comparator"].lower())

        self.assertEqual("skeptic_case_canonized_matrix_v1", ko_skeptic_matrix["artifact_schema_id"])
        self.assertTrue(ko_skeptic_matrix["supports_visible_limited_integration"])
        self.assertEqual(4, len(ko_skeptic_matrix["canonical_run_ids"]))
        self.assertIn("disciplined detection", ko_skeptic_matrix["framing_note"].lower())

        self.assertEqual("skeptic_case_quality_notes_v1", ko_skeptic_quality["artifact_schema_id"])
        self.assertEqual(4, len(ko_skeptic_quality["run_notes"]))
        self.assertEqual({"none"}, {note["issue_family"] for note in ko_skeptic_quality["run_notes"]})

        self.assertEqual("p4_canonized_matrix_v1", ko_p4["artifact_schema_id"])
        self.assertTrue(ko_p4["suitable_for_limited_app_integration"])
        self.assertEqual(2, len(ko_p4["canonized_runs"]))
        self.assertIn("Pillar Two", ko_p4["module_sections"]["fresh_2025_specifics"][0]["label"])

        self.assertEqual(["KO", "LLY", "NVDA"], sorted(p4_summary["covered_issuers"]))
        self.assertIn("skeptic", p4_summary["overall_verdict"].lower())

        self.assertEqual("current_case_mix_v1", current_case_mix["artifact_schema_id"])
        self.assertEqual(["KO", "LLY", "NVDA"], sorted(item["ticker"] for item in current_case_mix["visible_pilots"]))
        self.assertIn("skeptic", current_case_mix["product_statement"].lower())

        packet_readme = (summary.packet_dir / wave.ROOT_README_NAME).read_text(encoding="utf-8")
        changed_manifest = (summary.packet_dir / wave.CHANGED_FILES_MANIFEST_NAME).read_text(
            encoding="utf-8"
        )
        render_preview = (summary.packet_dir / wave.RENDER_PREVIEW_NAME).read_text(
            encoding="utf-8"
        )

        self.assertIn("KO Canonized Artifacts", packet_readme)
        self.assertIn("src/components/ProtocolLabPilotMatrixPanel.tsx", changed_manifest)
        self.assertIn("skeptic-case framing", render_preview.lower())

        console_text = "\n".join(summary.console_summary_lines)
        self.assertIn(str(summary.packet_dir.resolve()), console_text)
        self.assertIn(str(summary.zip_path.resolve()), console_text)
        self.assertIn("whether KO is now visibly integrated as the third pilot: yes", console_text)
        self.assertIn("whether any app-visible framing was updated: yes", console_text)


if __name__ == "__main__":
    unittest.main()
