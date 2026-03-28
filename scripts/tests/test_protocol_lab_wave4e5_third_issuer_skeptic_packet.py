import json
import shutil
import sys
import unittest
import zipfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))

import protocol_lab_wave4e5_third_issuer_skeptic_packet as wave  # noqa: E402


STAMP = "20990101_0101"
COMMON_RUN_FILES = {
    "README.md",
    "desktop_run_instructions.md",
    "desktop_attachment_set.md",
    "starter_prompt.txt",
    "run_manifest.json",
    "eval_scaffold.json",
    "pairwise_eval_scaffold.json",
}
EXPECTED_SOURCE_FILES = {
    "KO_02_p1_i2_tagged_packet": {
        "p1_structured_contract_v1.md",
        "source_case_manifest_v1.json",
        "i2_tagged_document_packet_v1.json",
        "i2_tagged_document_packet_v1.rendered_inputs.json",
        wave.I2_FY2024_FILENAME,
        wave.I2_FY2025_FILENAME,
    },
    "KO_02_p1_i2_tagged_packet_standard": {
        "p1_structured_contract_v1.md",
        "source_case_manifest_v1.json",
        "i2_tagged_document_packet_v1.json",
        "i2_tagged_document_packet_v1.rendered_inputs.json",
        wave.I2_FY2024_FILENAME,
        wave.I2_FY2025_FILENAME,
    },
    "KO_04_p4_i2_novelty_ledger_extended_v2": {
        "p4_novelty_ledger_contract_v2.md",
        "source_case_manifest_v1.json",
        "i2_tagged_document_packet_v1.json",
        "i2_tagged_document_packet_v1.rendered_inputs.json",
        wave.I2_FY2024_FILENAME,
        wave.I2_FY2025_FILENAME,
    },
    "KO_05_p4_i2_novelty_ledger_standard_v2": {
        "p4_novelty_ledger_contract_v2.md",
        "source_case_manifest_v1.json",
        "i2_tagged_document_packet_v1.json",
        "i2_tagged_document_packet_v1.rendered_inputs.json",
        wave.I2_FY2024_FILENAME,
        wave.I2_FY2025_FILENAME,
    },
}
EXPECTED_PAIRWISE_PEERS = {
    "KO_02_p1_i2_tagged_packet": {
        "KO_02_p1_i2_tagged_packet_standard",
        "KO_04_p4_i2_novelty_ledger_extended_v2",
    },
    "KO_02_p1_i2_tagged_packet_standard": {
        "KO_02_p1_i2_tagged_packet",
        "KO_05_p4_i2_novelty_ledger_standard_v2",
    },
    "KO_04_p4_i2_novelty_ledger_extended_v2": {
        "KO_05_p4_i2_novelty_ledger_standard_v2",
        "KO_02_p1_i2_tagged_packet",
    },
    "KO_05_p4_i2_novelty_ledger_standard_v2": {
        "KO_04_p4_i2_novelty_ledger_extended_v2",
        "KO_02_p1_i2_tagged_packet_standard",
    },
}


class Wave4E5ThirdIssuerSkepticPacketTest(unittest.TestCase):
    def setUp(self) -> None:
        self.backup_root = SCRIPTS_DIR / "_tmp_test_backups" / "wave4e5_third_issuer_skeptic_packet"
        if self.backup_root.exists():
            shutil.rmtree(self.backup_root)
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self.packet_dir, self.zip_path = wave.packet_paths_for_stamp(STAMP)
        self.targets = [
            self.packet_dir,
            self.zip_path,
            REPO_ROOT / wave.SELECTION_MEMO_PATH,
            REPO_ROOT / wave.HYPOTHESIS_NOTE_PATH,
            REPO_ROOT / wave.ANTI_OVERREADING_NOTE_PATH,
            REPO_ROOT / wave.SCOPE_DISCIPLINE_NOTE_PATH,
            REPO_ROOT / wave.PACKET_REPORT_PATH,
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

    def test_generate_packet_outputs_wave4e5_ko_skeptic_packet(self) -> None:
        summary = wave.generate_packet(stamp=STAMP)

        self.assertEqual(summary.selected_issuer, "KO (The Coca-Cola Company)")
        self.assertEqual(summary.packet_dir, self.packet_dir)
        self.assertEqual(summary.zip_path, self.zip_path)
        self.assertEqual(summary.included_run_ids, list(EXPECTED_SOURCE_FILES.keys()))
        self.assertEqual(summary.selection_origin, wave.SELECTION_ORIGIN)
        self.assertFalse(summary.app_visible_files_modified)
        self.assertEqual(summary.biggest_remaining_blocker, wave.BIGGEST_REMAINING_BLOCKER)
        self.assertTrue(summary.packet_dir.exists())
        self.assertTrue(summary.zip_path.exists())
        self.assertTrue((REPO_ROOT / wave.SELECTION_MEMO_PATH).exists())
        self.assertTrue((REPO_ROOT / wave.HYPOTHESIS_NOTE_PATH).exists())
        self.assertTrue((REPO_ROOT / wave.ANTI_OVERREADING_NOTE_PATH).exists())
        self.assertTrue((REPO_ROOT / wave.SCOPE_DISCIPLINE_NOTE_PATH).exists())
        self.assertTrue((REPO_ROOT / wave.PACKET_REPORT_PATH).exists())

        console_text = "\n".join(summary.console_summary_lines)
        self.assertIn("selected issuer: KO (The Coca-Cola Company)", console_text)
        self.assertIn(str(summary.packet_dir.resolve()), console_text)
        self.assertIn(str(summary.zip_path.resolve()), console_text)
        self.assertIn(wave.SELECTION_ORIGIN, console_text)
        self.assertIn("whether any app-visible files were modified: no", console_text)
        self.assertIn(wave.BIGGEST_REMAINING_BLOCKER, console_text)

        root_readme = (summary.packet_dir / wave.ROOT_README_NAME).read_text(encoding="utf-8")
        changed_manifest = (summary.packet_dir / wave.CHANGED_FILES_MANIFEST_NAME).read_text(
            encoding="utf-8"
        )
        selection_memo = (REPO_ROOT / wave.SELECTION_MEMO_PATH).read_text(encoding="utf-8")
        hypothesis_note = (REPO_ROOT / wave.HYPOTHESIS_NOTE_PATH).read_text(encoding="utf-8")
        anti_overreading_note = (REPO_ROOT / wave.ANTI_OVERREADING_NOTE_PATH).read_text(
            encoding="utf-8"
        )
        scope_note = (REPO_ROOT / wave.SCOPE_DISCIPLINE_NOTE_PATH).read_text(encoding="utf-8")
        packet_report = (REPO_ROOT / wave.PACKET_REPORT_PATH).read_text(encoding="utf-8")

        self.assertIn("Wave 4E5 KO Third-Issuer Skeptic Packet", root_readme)
        self.assertIn(wave.REZIP_GUARDRAIL_COMMAND, root_readme)
        self.assertIn("Current visible pilots excluded as controls rather than new candidates: `NVDA`, `LLY`.", selection_memo)
        self.assertIn("Select `KO` because it is the lowest-drift prepared candidate", selection_memo)
        self.assertIn("Most Likely Failure Modes", hypothesis_note)
        self.assertIn("forced significance on routine sharpening", hypothesis_note)
        self.assertIn("over-populating fresh novelty rows from routine maintenance", hypothesis_note)
        self.assertIn("“Mostly stable, selectively sharpened” is a valid and useful result", anti_overreading_note)
        self.assertIn("credibility, not visible expansion", scope_note)
        self.assertIn("selected_issuer: `KO` / `The Coca-Cola Company`", packet_report)
        self.assertIn(wave.SELECTION_ORIGIN, packet_report)
        self.assertIn("`none`", changed_manifest)
        self.assertIn(wave.SELF_SCRIPT_PATH.as_posix(), changed_manifest)
        self.assertIn(wave.SELF_TEST_PATH.as_posix(), changed_manifest)

        for run_name, expected_sources in EXPECTED_SOURCE_FILES.items():
            run_dir = summary.packet_dir / run_name
            self.assertTrue(run_dir.exists(), run_name)
            self.assertEqual(
                {path.name for path in run_dir.iterdir() if path.is_file()},
                COMMON_RUN_FILES,
            )
            self.assertEqual(
                {path.name for path in (run_dir / "sources").iterdir()},
                expected_sources,
            )

            manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
            eval_scaffold = json.loads((run_dir / "eval_scaffold.json").read_text(encoding="utf-8"))
            pairwise_scaffold = json.loads(
                (run_dir / "pairwise_eval_scaffold.json").read_text(encoding="utf-8")
            )
            instructions = (run_dir / "desktop_run_instructions.md").read_text(encoding="utf-8")
            attachment_guidance = (run_dir / "desktop_attachment_set.md").read_text(
                encoding="utf-8"
            )
            starter_prompt = (run_dir / "starter_prompt.txt").read_text(encoding="utf-8")

            self.assertEqual(manifest["selection_basis"]["selection_origin"], wave.SELECTION_ORIGIN)
            self.assertEqual(manifest["run_identity"]["ticker"], "KO")
            self.assertEqual(manifest["run_identity"]["issuer_name"], "The Coca-Cola Company")
            self.assertEqual(manifest["run_identity"]["current_app_role"], "Internal-only skeptic case")
            self.assertEqual(manifest["operator_notes"]["post_run_rezip_guardrail"], wave.REZIP_GUARDRAIL_COMMAND)
            self.assertIn(
                "source_case_manifest_v1.json, i2_tagged_document_packet_v1.json, run_manifest.json, and the packet docs are operator-only files.",
                manifest["transformation_log"],
            )

            hard_checks = eval_scaffold["hard_checks"]
            for key in [
                "routine_wording_maintenance_not_overstated",
                "generic_upkeep_not_promoted_to_fresh_specifics",
                "useful_even_if_mostly_stable",
                "novelty_discipline_under_low_drift",
                "forced_drama_or_overconfidence_absent",
            ]:
                self.assertIn(key, hard_checks)
            self.assertEqual(len(eval_scaffold["skeptic_review_questions"]), 5)

            comparison_blocks = pairwise_scaffold["comparison_blocks"]
            self.assertEqual(len(comparison_blocks), 2)
            self.assertEqual(
                {block["peer_run_id"] for block in comparison_blocks},
                EXPECTED_PAIRWISE_PEERS[run_name],
            )
            self.assertEqual(
                {block["comparison_id"] for block in comparison_blocks},
                {"same_lane_effort", "matched_effort_cross_lane"},
            )
            for block in comparison_blocks:
                self.assertEqual(len(block["review_questions"]), 5)
                self.assertIn(summary.packet_dir.name, block["peer_response_path"])
                self.assertIn(summary.packet_dir.name, block["peer_run_manifest_path"])

            self.assertIn("Use `pairwise_eval_scaffold.json` to review both the same-lane-effort and matched-effort-cross-lane comparisons.", instructions)
            self.assertIn("source_case_manifest_v1.json", attachment_guidance)
            self.assertIn("i2_tagged_document_packet_v1.json", attachment_guidance)

            if run_name.startswith("KO_02"):
                self.assertEqual(
                    manifest["output_contract"]["top_level_keys"],
                    ["change_brief", "evidence_bundle"],
                )
                self.assertIn(
                    "Do not overstate routine wording maintenance or generic filing upkeep.",
                    starter_prompt,
                )
                self.assertIn("A mostly stable, selectively sharpened outcome is valid.", starter_prompt)
                self.assertNotIn("source_case_manifest_v1.json", manifest["input_basis"]["attachment_list"])
            else:
                self.assertEqual(
                    manifest["output_contract"]["top_level_keys"],
                    ["change_brief", "novelty_ledger", "evidence_bundle"],
                )
                self.assertIn(
                    "If a case is borderline, default to intensified_or_broadened_points or ambiguities_or_boundary_notes.",
                    starter_prompt,
                )
                self.assertIn("Do not treat added examples under existing themes as automatically fresh.", starter_prompt)
                self.assertIn("fresh_vs_intensified_boundary_discipline", hard_checks)

        source_case = json.loads(
            (
                summary.packet_dir
                / "KO_02_p1_i2_tagged_packet"
                / "sources"
                / "source_case_manifest_v1.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(source_case["selection_origin"], wave.SELECTION_ORIGIN)
        self.assertEqual(source_case["ticker"], "KO")
        self.assertEqual(len(source_case["years"]), 2)
        self.assertIsNone(source_case["years"][0]["accession_number"])
        self.assertIsNone(source_case["years"][0]["filing_date"])
        self.assertEqual(
            source_case["years"][0]["reuse_filtered_year_input_path"],
            wave.repo_rel(wave.REPO_ROOT / wave.DEBOILERPLATED_YEAR_INPUTS[2024]),
        )

        with zipfile.ZipFile(summary.zip_path) as archive:
            names = set(archive.namelist())
        self.assertIn(f"{summary.packet_dir.name}/README.md", names)
        self.assertIn(f"{summary.packet_dir.name}/changed_files_manifest.md", names)
        self.assertIn(f"{summary.packet_dir.name}/{wave.P1_CONTRACT_PATH.name}", names)
        self.assertIn(f"{summary.packet_dir.name}/{wave.P4_CONTRACT_PATH.name}", names)
        self.assertIn(
            f"{summary.packet_dir.name}/{wave.SELECTION_MEMO_PATH.as_posix()}",
            names,
        )
        self.assertIn(
            f"{summary.packet_dir.name}/{wave.SELF_SCRIPT_PATH.as_posix()}",
            names,
        )
        self.assertIn(
            f"{summary.packet_dir.name}/{wave.SELF_TEST_PATH.as_posix()}",
            names,
        )


if __name__ == "__main__":
    unittest.main()
