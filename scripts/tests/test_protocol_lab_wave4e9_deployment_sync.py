import shutil
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))

import protocol_lab_wave4e9_deployment_sync as wave  # noqa: E402


STAMP = "20990101_1145"


class Wave4E9DeploymentSyncPacketTest(unittest.TestCase):
    def setUp(self) -> None:
        self.packet_dir, self.zip_path = wave.packet_paths_for_stamp(STAMP)
        if self.packet_dir.exists():
            shutil.rmtree(self.packet_dir)
        if self.zip_path.exists():
            self.zip_path.unlink()

    def tearDown(self) -> None:
        if self.packet_dir.exists():
            shutil.rmtree(self.packet_dir)
        if self.zip_path.exists():
            self.zip_path.unlink()

    def test_generate_wave_builds_packet_and_console_summary(self) -> None:
        summary = wave.generate_wave(stamp=STAMP, include_live_fetch=False)

        self.assertEqual(summary.packet_dir, self.packet_dir)
        self.assertEqual(summary.zip_path, self.zip_path)
        self.assertTrue(summary.packet_dir.exists())
        self.assertTrue(summary.zip_path.exists())
        self.assertTrue(summary.repo_build_verification_tightened)
        self.assertTrue(summary.mounted_path_acceptance_checks_added)
        self.assertFalse(summary.worker_slash_normalization_improved)
        self.assertEqual(summary.biggest_remaining_blocker, wave.BIGGEST_REMAINING_BLOCKER)

        for relative_path in [
            "reports/protocol_lab/wave4e9_deployment_truth_audit.md",
            "reports/protocol_lab/wave4e9_deploy_mount_runbook.md",
            "reports/protocol_lab/wave4e9_live_acceptance_checklist.md",
            "reports/protocol_lab/wave4e9_deployment_sync_report.md",
            "reports/protocol_lab/wave4e9_mount_normalization_decision.md",
            "public/_redirects",
            "scripts/lab_verify_social_preview_deploy.py",
            "scripts/tests/test_lab_verify_social_preview_deploy.py",
            "scripts/protocol_lab_wave4e9_deployment_sync.py",
            "scripts/tests/test_protocol_lab_wave4e9_deployment_sync.py",
            "README.md",
            wave.CHANGED_FILES_MANIFEST_NAME,
            wave.PACKET_README_NAME,
            wave.LIVE_VERIFIER_OUTPUT_NAME,
            wave.DIST_INDEX_EXCERPT_NAME,
            wave.METADATA_EXCERPT_NAME,
            wave.SLASH_PREVIEW_NAME,
        ]:
            self.assertTrue((summary.packet_dir / relative_path).is_file(), relative_path)

        changed_manifest = (summary.packet_dir / wave.CHANGED_FILES_MANIFEST_NAME).read_text(
            encoding="utf-8"
        )
        packet_readme = (summary.packet_dir / wave.PACKET_README_NAME).read_text(
            encoding="utf-8"
        )
        live_output = (summary.packet_dir / wave.LIVE_VERIFIER_OUTPUT_NAME).read_text(
            encoding="utf-8"
        )
        slash_preview = (summary.packet_dir / wave.SLASH_PREVIEW_NAME).read_text(
            encoding="utf-8"
        )

        self.assertIn("Wave 4E9", changed_manifest)
        self.assertIn("public/_redirects", changed_manifest)
        self.assertIn("mounted-path verifier", packet_readme.lower())
        self.assertIn("deterministic packet test mode", live_output)
        self.assertIn("Slash Normalization Evidence Preview", slash_preview)

        console_text = "\n".join(summary.console_summary_lines)
        self.assertIn(str(summary.packet_dir.resolve()), console_text)
        self.assertIn(str(summary.zip_path.resolve()), console_text)
        self.assertIn("whether repo/build verification was tightened: yes", console_text)
        self.assertIn("whether mounted-path acceptance checks were added: yes", console_text)
        self.assertIn(
            "whether Worker slash-normalization was improved: no (manual-only; external Worker source unavailable in repo)",
            console_text,
        )


if __name__ == "__main__":
    unittest.main()
