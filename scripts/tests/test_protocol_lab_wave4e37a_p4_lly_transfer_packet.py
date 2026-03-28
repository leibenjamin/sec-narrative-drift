import json
import shutil
import sys
import unittest
import zipfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))

import protocol_lab_wave4e37a_lly_p4_transfer_packet as wave  # noqa: E402


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
    "LLY_04_p4_i2_novelty_ledger_extended_v2": {
        "p4_novelty_ledger_contract_v2.md",
        "source_case_manifest_v1.json",
        "i2_tagged_document_packet_v1.json",
        "i2_tagged_document_packet_v1.rendered_inputs.json",
        wave.I2_FY2024_FILENAME,
        wave.I2_FY2025_FILENAME,
    },
    "LLY_05_p4_i2_novelty_ledger_standard_v2": {
        "p4_novelty_ledger_contract_v2.md",
        "source_case_manifest_v1.json",
        "i2_tagged_document_packet_v1.json",
        "i2_tagged_document_packet_v1.rendered_inputs.json",
        wave.I2_FY2024_FILENAME,
        wave.I2_FY2025_FILENAME,
    },
}
EXPECTED_BASELINES = {
    "LLY_04_p4_i2_novelty_ledger_extended_v2": {
        "baseline_run_id": "02_p1_i2_tagged_packet",
        "reasoning_mode": "extended_thinking",
        "baseline_response_path": "wave4d2_lly_desktop_packet_20260318_1851/02_p1_i2_tagged_packet/response.json",
        "baseline_run_manifest_path": "wave4d2_lly_desktop_packet_20260318_1851/02_p1_i2_tagged_packet/run_manifest.json",
    },
    "LLY_05_p4_i2_novelty_ledger_standard_v2": {
        "baseline_run_id": "LLY_02_p1_i2_tagged_packet_standard",
        "reasoning_mode": "standard_thinking",
        "baseline_response_path": "wave4e1_standard_thinking_controls_20260319_0213/LLY_02_p1_i2_tagged_packet_standard/response.json",
        "baseline_run_manifest_path": "wave4e1_standard_thinking_controls_20260319_0213/LLY_02_p1_i2_tagged_packet_standard/run_manifest.json",
    },
}


class Wave4E37ALLYTransferPacketTest(unittest.TestCase):
    def setUp(self) -> None:
        self.backup_root = SCRIPTS_DIR / "_tmp_test_backups" / "wave4e37a_lly_p4_transfer_packet"
        if self.backup_root.exists():
            shutil.rmtree(self.backup_root)
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self.packet_dir, self.zip_path = wave.packet_paths_for_stamp(STAMP)
        self.targets = [
            self.packet_dir,
            self.zip_path,
            REPO_ROOT / wave.TRANSFER_HYPOTHESIS_PATH,
            REPO_ROOT / wave.SELECTION_NOTE_PATH,
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

    def test_generate_packet_outputs_hardened_lly_transfer_packet(self) -> None:
        summary = wave.generate_packet(stamp=STAMP)

        self.assertEqual(summary.packet_dir, self.packet_dir)
        self.assertEqual(summary.zip_path, self.zip_path)
        self.assertEqual(summary.contract_path, REPO_ROOT / wave.P4_CONTRACT_PATH)
        self.assertEqual(summary.included_run_ids, list(EXPECTED_SOURCE_FILES.keys()))
        self.assertFalse(summary.app_visible_files_modified)
        self.assertEqual(summary.biggest_remaining_blocker, wave.BIGGEST_REMAINING_BLOCKER)
        self.assertTrue(summary.packet_dir.exists())
        self.assertTrue(summary.zip_path.exists())
        self.assertTrue((REPO_ROOT / wave.TRANSFER_HYPOTHESIS_PATH).exists())
        self.assertTrue((REPO_ROOT / wave.SELECTION_NOTE_PATH).exists())
        self.assertTrue((REPO_ROOT / wave.PACKET_REPORT_PATH).exists())

        console_text = "\n".join(summary.console_summary_lines)
        self.assertIn(str(summary.packet_dir.resolve()), console_text)
        self.assertIn(str(summary.zip_path.resolve()), console_text)
        self.assertIn(str((REPO_ROOT / wave.P4_CONTRACT_PATH).resolve()), console_text)
        self.assertIn(
            "whether source_case_manifest_v1.json was removed from the default attachment set: yes",
            console_text,
        )
        self.assertIn("whether any app-visible files were modified: no", console_text)
        self.assertIn(wave.BIGGEST_REMAINING_BLOCKER, console_text)

        root_readme = (summary.packet_dir / wave.ROOT_README_NAME).read_text(encoding="utf-8")
        changed_manifest = (summary.packet_dir / wave.CHANGED_FILES_MANIFEST_NAME).read_text(
            encoding="utf-8"
        )
        hypothesis = (REPO_ROOT / wave.TRANSFER_HYPOTHESIS_PATH).read_text(encoding="utf-8")
        selection_note = (REPO_ROOT / wave.SELECTION_NOTE_PATH).read_text(encoding="utf-8")
        packet_report = (REPO_ROOT / wave.PACKET_REPORT_PATH).read_text(encoding="utf-8")

        self.assertIn("transfer_hypothesis", root_readme)
        self.assertIn("selection_note", root_readme)
        self.assertIn("source_case_manifest_v1.json", root_readme)
        self.assertIn("NVDA-Shaped", hypothesis)
        self.assertIn("secondary novelty-ledger module", hypothesis)
        self.assertIn("Second Issuer", selection_note)
        self.assertIn("Removed `source_case_manifest_v1.json` from every model-upload attachment set", packet_report)
        self.assertIn("filing-paragraph-only", packet_report)
        self.assertIn("unescaped internal quotation marks", packet_report)
        self.assertFalse((summary.packet_dir / "src").exists())

        modified_section = changed_manifest.split("## Packet Root Convenience Copies", maxsplit=1)[0]
        self.assertNotIn(wave.P4_CONTRACT_PATH.as_posix(), modified_section)
        for path in wave.MODIFIED_REPO_FILES:
            self.assertIn(path.as_posix(), changed_manifest)
            self.assertTrue((summary.packet_dir / path).exists(), path.as_posix())

        self.assertTrue((summary.packet_dir / wave.P4_CONTRACT_PATH.name).exists())
        self.assertTrue((summary.packet_dir / Path(wave.TRANSFER_HYPOTHESIS_PATH).name).exists())
        self.assertTrue((summary.packet_dir / Path(wave.SELECTION_NOTE_PATH).name).exists())
        self.assertTrue((summary.packet_dir / Path(wave.PACKET_REPORT_PATH).name).exists())

        for run_name, expected_source_files in EXPECTED_SOURCE_FILES.items():
            baseline = EXPECTED_BASELINES[run_name]
            run_dir = summary.packet_dir / run_name
            self.assertEqual(
                {path.name for path in run_dir.iterdir() if path.is_file()},
                COMMON_RUN_FILES,
            )
            self.assertEqual({path.name for path in (run_dir / "sources").iterdir()}, expected_source_files)

            starter_prompt = (run_dir / "starter_prompt.txt").read_text(encoding="utf-8")
            self.assertIn("Do not overstate novelty.", starter_prompt)
            self.assertIn("borderline", starter_prompt)
            self.assertIn("verbatim substrings", starter_prompt)
            self.assertIn("filing paragraphs only", starter_prompt)
            self.assertIn("Do not use source manifests, operator metadata, or packet metadata as evidence rows.", starter_prompt)
            self.assertIn(baseline["reasoning_mode"].replace("_", " "), starter_prompt)
            self.assertLess(len(starter_prompt), 1200)

            instructions = (run_dir / "desktop_run_instructions.md").read_text(encoding="utf-8")
            self.assertIn("pairwise_eval_scaffold.json", instructions)
            self.assertNotIn("prior P4 v1 reference", instructions)
            self.assertIn("unescaped internal quotation marks", instructions)
            self.assertIn("transport-only", instructions)
            self.assertIn(baseline["reasoning_mode"].replace("_", " "), instructions)

            attachment_guidance = (run_dir / "desktop_attachment_set.md").read_text(encoding="utf-8")
            self.assertIn("Do Not Attach These Files", attachment_guidance)
            self.assertIn("source_case_manifest_v1.json", attachment_guidance)
            self.assertIn("i2_tagged_document_packet_v1.json", attachment_guidance)
            self.assertIn("metadata leakage", attachment_guidance)

            manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual("desktop_core_run_manifest_v1", manifest["artifact_schema_id"])
            self.assertEqual("p4_novelty_ledger_v1", manifest["protocol_basis"]["canonical_protocol_id"])
            self.assertEqual(
                "p4_novelty_ledger_contract_v2",
                manifest["protocol_basis"]["protocol_revision_label"],
            )
            self.assertEqual(
                "docs/protocol_lab/p4_novelty_ledger_contract_v2.md",
                manifest["protocol_basis"]["canonical_contract_repo_path"],
            )
            self.assertEqual(
                ["change_brief", "novelty_ledger", "evidence_bundle"],
                manifest["output_contract"]["top_level_keys"],
            )
            self.assertEqual(
                wave.NOVELTY_LEDGER_REQUIRED_SECTIONS,
                manifest["output_contract"]["novelty_ledger_required_sections"],
            )
            self.assertEqual(
                baseline["reasoning_mode"], manifest["desktop_target"]["reasoning_mode"]
            )
            self.assertEqual(
                baseline["baseline_run_id"],
                manifest["what_this_run_tests"]["matched_pairwise_baseline"]["baseline_run_id"],
            )
            self.assertEqual(
                baseline["baseline_response_path"],
                manifest["what_this_run_tests"]["matched_pairwise_baseline"]["baseline_response_path"],
            )
            self.assertEqual(
                baseline["baseline_run_manifest_path"],
                manifest["what_this_run_tests"]["matched_pairwise_baseline"]["baseline_run_manifest_path"],
            )
            self.assertNotIn("prior_p4_v1_reference", manifest["what_this_run_tests"])

            attachment_list = manifest["input_basis"]["attachment_list"]
            self.assertEqual(3, len(attachment_list))
            self.assertIn(
                f"{summary.packet_dir.name}/{run_name}/sources/p4_novelty_ledger_contract_v2.md",
                attachment_list,
            )
            self.assertNotIn(
                f"{summary.packet_dir.name}/{run_name}/sources/source_case_manifest_v1.json",
                attachment_list,
            )
            self.assertIn(
                f"{summary.packet_dir.name}/{run_name}/sources/source_case_manifest_v1.json",
                manifest["input_basis"]["operator_only_files"],
            )
            self.assertEqual(
                [f"{summary.packet_dir.name}/{run_name}/sources/source_case_manifest_v1.json"],
                manifest["input_basis"]["reference_only_files"],
            )
            optional_sets = {
                item["attachment_set_id"]: item
                for item in manifest["input_basis"]["optional_attachment_sets"]
            }
            self.assertEqual(
                attachment_list,
                optional_sets[wave.I2_SPLIT_ATTACHMENT_SET_ID]["packet_relative_paths"],
            )
            self.assertEqual(
                [
                    f"{summary.packet_dir.name}/{run_name}/sources/p4_novelty_ledger_contract_v2.md",
                    f"{summary.packet_dir.name}/{run_name}/sources/i2_tagged_document_packet_v1.rendered_inputs.json",
                ],
                optional_sets[wave.I2_COMBINED_ATTACHMENT_SET_ID]["packet_relative_paths"],
            )
            for path in optional_sets[wave.I2_COMBINED_ATTACHMENT_SET_ID]["packet_relative_paths"]:
                self.assertNotIn("source_case_manifest_v1.json", path)

            source_case_rows = [
                item
                for item in manifest["input_basis"]["copied_source_files"]
                if item["role"] == "source_case_manifest"
            ]
            self.assertEqual(1, len(source_case_rows))
            self.assertFalse(source_case_rows[0]["attach_by_default"])
            self.assertEqual("reference_only", source_case_rows[0]["desktop_file_role"])

            eval_scaffold = json.loads((run_dir / "eval_scaffold.json").read_text(encoding="utf-8"))
            self.assertEqual(
                "pending",
                eval_scaffold["hard_checks"]["evidence_quotes_verbatim_substrings"],
            )
            self.assertEqual(
                "pending",
                eval_scaffold["hard_checks"]["evidence_bundle_filing_paragraph_only"],
            )
            self.assertEqual(
                "pending",
                eval_scaffold["hard_checks"]["no_manifest_or_packet_metadata_leakage"],
            )
            self.assertEqual(
                "pending",
                eval_scaffold["rubric_bands"]["false_novelty_control"],
            )
            self.assertEqual(
                "pending",
                eval_scaffold["rubric_bands"]["investor_usefulness"],
            )

            pairwise_scaffold = json.loads(
                (run_dir / "pairwise_eval_scaffold.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                "desktop_pairwise_eval_scaffold_v1",
                pairwise_scaffold["artifact_schema_id"],
            )
            self.assertEqual(
                wave.PAIRWISE_REVIEW_QUESTIONS,
                [item["question"] for item in pairwise_scaffold["pairwise_review_questions"]],
            )
            self.assertEqual(
                baseline["baseline_run_id"],
                pairwise_scaffold["matched_effort_02_baseline"]["run_id"],
            )
            self.assertNotIn("prior_p4_v1_reference", pairwise_scaffold)

        with zipfile.ZipFile(summary.zip_path) as handle:
            names = set(handle.namelist())
        self.assertIn(f"{summary.packet_dir.name}/README.md", names)
        self.assertIn(f"{summary.packet_dir.name}/changed_files_manifest.md", names)
        self.assertIn(
            f"{summary.packet_dir.name}/LLY_04_p4_i2_novelty_ledger_extended_v2/starter_prompt.txt",
            names,
        )
        self.assertIn(
            f"{summary.packet_dir.name}/LLY_05_p4_i2_novelty_ledger_standard_v2/pairwise_eval_scaffold.json",
            names,
        )


if __name__ == "__main__":
    unittest.main()
