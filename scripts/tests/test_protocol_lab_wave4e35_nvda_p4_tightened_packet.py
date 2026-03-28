import json
import shutil
import sys
import unittest
import zipfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))

import protocol_lab_wave4e35_nvda_p4_tightened_packet as wave  # noqa: E402


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
    "NVDA_04_p4_i2_novelty_ledger_extended_v2": {
        "p4_novelty_ledger_contract_v2.md",
        "source_case_manifest_v1.json",
        "i2_tagged_document_packet_v1.json",
        "i2_tagged_document_packet_v1.rendered_inputs.json",
        wave.I2_FY2024_FILENAME,
        wave.I2_FY2025_FILENAME,
    },
    "NVDA_05_p4_i2_novelty_ledger_standard_v2": {
        "p4_novelty_ledger_contract_v2.md",
        "source_case_manifest_v1.json",
        "i2_tagged_document_packet_v1.json",
        "i2_tagged_document_packet_v1.rendered_inputs.json",
        wave.I2_FY2024_FILENAME,
        wave.I2_FY2025_FILENAME,
    },
}
EXPECTED_BASELINES = {
    "NVDA_04_p4_i2_novelty_ledger_extended_v2": {
        "baseline_run_id": "02_p1_i2_tagged_packet",
        "reasoning_mode": "extended_thinking",
        "baseline_response_path": "wave4c3a6_split_default_flip_20260317_1702/02_p1_i2_tagged_packet/response.json",
        "baseline_run_manifest_path": "wave4c3a6_split_default_flip_20260317_1702/02_p1_i2_tagged_packet/run_manifest.json",
        "prior_p4_v1_run_id": "NVDA_04_p4_i2_novelty_ledger_extended",
        "prior_p4_v1_response_path": "wave4e3_nvda_novelty_ledger_packet_20260320_0530/NVDA_04_p4_i2_novelty_ledger_extended/response.json",
        "prior_p4_v1_run_manifest_path": "wave4e3_nvda_novelty_ledger_packet_20260320_0530/NVDA_04_p4_i2_novelty_ledger_extended/run_manifest.json",
    },
    "NVDA_05_p4_i2_novelty_ledger_standard_v2": {
        "baseline_run_id": "NVDA_02_p1_i2_tagged_packet_standard",
        "reasoning_mode": "standard_thinking",
        "baseline_response_path": "wave4e1_standard_thinking_controls_20260319_0213/NVDA_02_p1_i2_tagged_packet_standard/response.json",
        "baseline_run_manifest_path": "wave4e1_standard_thinking_controls_20260319_0213/NVDA_02_p1_i2_tagged_packet_standard/run_manifest.json",
        "prior_p4_v1_run_id": "NVDA_05_p4_i2_novelty_ledger_standard",
        "prior_p4_v1_response_path": "wave4e3_nvda_novelty_ledger_packet_20260320_0530/NVDA_05_p4_i2_novelty_ledger_standard/response.json",
        "prior_p4_v1_run_manifest_path": "wave4e3_nvda_novelty_ledger_packet_20260320_0530/NVDA_05_p4_i2_novelty_ledger_standard/run_manifest.json",
    },
}
PAIRWISE_QUESTIONS = [
    "Does P4 v2 improve fresh-vs-reused clarity over `02`?",
    "Does it avoid false novelty better than P4 v1 appeared to?",
    "Does it remain evidence-grounded?",
    "Does it stay useful to an investor/analyst rather than becoming taxonomy-heavy?",
    "Is it better enough to justify future limited app integration as a secondary novelty-ledger module?",
]


class Wave4E35TightenedPacketTest(unittest.TestCase):
    def setUp(self) -> None:
        self.backup_root = SCRIPTS_DIR / "_tmp_test_backups" / "wave4e35_nvda_p4_tightened_packet"
        if self.backup_root.exists():
            shutil.rmtree(self.backup_root)
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self.packet_dir, self.zip_path = wave.packet_paths_for_stamp(STAMP)
        self.targets = [
            self.packet_dir,
            self.zip_path,
            REPO_ROOT / wave.REVIEW_PLAN_PATH,
            REPO_ROOT / wave.RATIONALE_PATH,
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

    def test_generate_packet_outputs_tightened_packet(self) -> None:
        summary = wave.generate_packet(stamp=STAMP)

        self.assertEqual(summary.packet_dir, self.packet_dir)
        self.assertEqual(summary.zip_path, self.zip_path)
        self.assertEqual(summary.contract_path, REPO_ROOT / wave.P4_CONTRACT_PATH)
        self.assertEqual(summary.included_run_ids, list(EXPECTED_SOURCE_FILES.keys()))
        self.assertFalse(summary.app_visible_files_modified)
        self.assertEqual(summary.biggest_remaining_blocker, wave.BIGGEST_REMAINING_BLOCKER)
        self.assertTrue(summary.packet_dir.exists())
        self.assertTrue(summary.zip_path.exists())
        self.assertTrue((REPO_ROOT / wave.REVIEW_PLAN_PATH).exists())
        self.assertTrue((REPO_ROOT / wave.RATIONALE_PATH).exists())
        self.assertTrue((REPO_ROOT / wave.PACKET_REPORT_PATH).exists())

        console_text = "\n".join(summary.console_summary_lines)
        self.assertIn(str(summary.packet_dir.resolve()), console_text)
        self.assertIn(str(summary.zip_path.resolve()), console_text)
        self.assertIn(str((REPO_ROOT / wave.P4_CONTRACT_PATH).resolve()), console_text)
        self.assertIn("whether any app-visible files were modified: no", console_text)
        self.assertIn(wave.BIGGEST_REMAINING_BLOCKER, console_text)

        root_readme = (summary.packet_dir / wave.ROOT_README_NAME).read_text(encoding="utf-8")
        changed_manifest = (summary.packet_dir / wave.CHANGED_FILES_MANIFEST_NAME).read_text(
            encoding="utf-8"
        )
        review_plan = (REPO_ROOT / wave.REVIEW_PLAN_PATH).read_text(encoding="utf-8")
        rationale = (REPO_ROOT / wave.RATIONALE_PATH).read_text(encoding="utf-8")
        packet_report = (REPO_ROOT / wave.PACKET_REPORT_PATH).read_text(encoding="utf-8")

        self.assertIn("secondary novelty-ledger module", review_plan)
        self.assertIn("nvda_2025_p169", rationale)
        self.assertIn("packet-local contract tightening", packet_report)
        self.assertIn("prior P4 v1 output", packet_report)
        self.assertIn("pairwise_eval_scaffold.json", root_readme)
        self.assertIn("prior P4 v1 output", root_readme)
        self.assertFalse((summary.packet_dir / "src").exists())

        for path in wave.MODIFIED_REPO_FILES:
            self.assertIn(path.as_posix(), changed_manifest)
            self.assertTrue((summary.packet_dir / path).exists(), path.as_posix())

        self.assertTrue((summary.packet_dir / wave.P4_CONTRACT_PATH.name).exists())
        self.assertTrue((summary.packet_dir / Path(wave.REVIEW_PLAN_PATH).name).exists())
        self.assertTrue((summary.packet_dir / Path(wave.RATIONALE_PATH).name).exists())
        self.assertTrue((summary.packet_dir / Path(wave.PACKET_REPORT_PATH).name).exists())

        prompts: dict[str, str] = {}

        for run_name, expected_source_files in EXPECTED_SOURCE_FILES.items():
            baseline = EXPECTED_BASELINES[run_name]
            run_dir = summary.packet_dir / run_name
            self.assertEqual(
                {path.name for path in run_dir.iterdir() if path.is_file()},
                COMMON_RUN_FILES,
            )
            self.assertEqual({path.name for path in (run_dir / "sources").iterdir()}, expected_source_files)

            starter_prompt = (run_dir / "starter_prompt.txt").read_text(encoding="utf-8")
            prompts[run_name] = starter_prompt
            self.assertIn("Do not overstate novelty.", starter_prompt)
            self.assertIn("borderline", starter_prompt)
            self.assertIn("verbatim substrings", starter_prompt)
            self.assertIn("exactly these top-level keys", starter_prompt)
            self.assertIn(baseline["reasoning_mode"].replace("_", " "), starter_prompt)
            self.assertLess(len(starter_prompt), 950)

            instructions = (run_dir / "desktop_run_instructions.md").read_text(encoding="utf-8")
            self.assertIn("pairwise_eval_scaffold.json", instructions)
            self.assertIn("prior P4 v1 reference", instructions)
            self.assertIn(baseline["reasoning_mode"].replace("_", " "), instructions)

            attachment_guidance = (run_dir / "desktop_attachment_set.md").read_text(encoding="utf-8")
            self.assertIn("Do Not Attach These Files", attachment_guidance)
            self.assertIn("pairwise_eval_scaffold.json", attachment_guidance)
            self.assertIn("i2_tagged_document_packet_v1.json", attachment_guidance)

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
            self.assertEqual(
                baseline["prior_p4_v1_run_id"],
                manifest["what_this_run_tests"]["prior_p4_v1_reference"]["run_id"],
            )
            self.assertEqual(
                baseline["prior_p4_v1_response_path"],
                manifest["what_this_run_tests"]["prior_p4_v1_reference"]["response_path"],
            )
            self.assertEqual(
                baseline["prior_p4_v1_run_manifest_path"],
                manifest["what_this_run_tests"]["prior_p4_v1_reference"]["run_manifest_path"],
            )
            self.assertIn(
                f"{summary.packet_dir.name}/{run_name}/sources/p4_novelty_ledger_contract_v2.md",
                manifest["input_basis"]["attachment_list"],
            )
            self.assertIn(
                f"{summary.packet_dir.name}/{run_name}/pairwise_eval_scaffold.json",
                manifest["input_basis"]["operator_only_files"],
            )

            eval_scaffold = json.loads((run_dir / "eval_scaffold.json").read_text(encoding="utf-8"))
            self.assertEqual(
                "pending",
                eval_scaffold["hard_checks"]["evidence_quotes_verbatim_substrings"],
            )
            self.assertEqual(
                "pending",
                eval_scaffold["hard_checks"]["fresh_vs_intensified_boundary_discipline"],
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
                baseline["baseline_run_id"],
                pairwise_scaffold["matched_effort_02_baseline"]["run_id"],
            )
            self.assertEqual(
                baseline["prior_p4_v1_run_id"],
                pairwise_scaffold["prior_p4_v1_reference"]["run_id"],
            )
            self.assertEqual(
                PAIRWISE_QUESTIONS,
                [item["question"] for item in pairwise_scaffold["pairwise_review_questions"]],
            )
            self.assertEqual("pending", pairwise_scaffold["preferred_run_vs_02"])
            self.assertEqual("pending", pairwise_scaffold["preferred_run_vs_p4_v1"])
            self.assertEqual(
                "pending", pairwise_scaffold["better_enough_for_limited_secondary_module"]
            )

        normalized_extended = prompts["NVDA_04_p4_i2_novelty_ledger_extended_v2"].replace(
            "extended thinking", "<mode> thinking"
        )
        normalized_standard = prompts["NVDA_05_p4_i2_novelty_ledger_standard_v2"].replace(
            "standard thinking", "<mode> thinking"
        )
        self.assertEqual(normalized_extended, normalized_standard)

        with zipfile.ZipFile(summary.zip_path) as handle:
            names = set(handle.namelist())
        self.assertIn(f"{summary.packet_dir.name}/{wave.ROOT_README_NAME}", names)
        self.assertIn(f"{summary.packet_dir.name}/{wave.CHANGED_FILES_MANIFEST_NAME}", names)
        self.assertIn(
            f"{summary.packet_dir.name}/docs/protocol_lab/p4_novelty_ledger_contract_v2.md",
            names,
        )
        self.assertIn(
            f"{summary.packet_dir.name}/reports/protocol_lab/{Path(wave.REVIEW_PLAN_PATH).name}",
            names,
        )
        self.assertIn(
            f"{summary.packet_dir.name}/reports/protocol_lab/{Path(wave.RATIONALE_PATH).name}",
            names,
        )
        self.assertIn(
            f"{summary.packet_dir.name}/reports/protocol_lab/{Path(wave.PACKET_REPORT_PATH).name}",
            names,
        )
        self.assertIn(
            f"{summary.packet_dir.name}/scripts/protocol_lab_wave4e35_nvda_p4_tightened_packet.py",
            names,
        )
        self.assertIn(
            f"{summary.packet_dir.name}/scripts/tests/test_protocol_lab_wave4e35_nvda_p4_tightened_packet.py",
            names,
        )
        self.assertIn(f"{summary.packet_dir.name}/p4_novelty_ledger_contract_v2.md", names)
        self.assertIn(
            f"{summary.packet_dir.name}/wave4e35_p4_tightening_review_plan.md",
            names,
        )
        self.assertIn(
            f"{summary.packet_dir.name}/wave4e35_p4_tightening_rationale.md",
            names,
        )
        self.assertIn(
            f"{summary.packet_dir.name}/wave4e35_p4_tightened_packet_report.md",
            names,
        )


if __name__ == "__main__":
    unittest.main()
