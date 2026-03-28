import shutil
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))

import protocol_lab_wave4e75_first_run_demo_readiness as wave  # noqa: E402


STAMP = "20990101_0755"


class Wave4E75FirstRunDemoReadinessPacketTest(unittest.TestCase):
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

    def test_generate_wave_builds_packet_and_includes_targeted_support(self) -> None:
        summary = wave.generate_wave(stamp=STAMP)

        self.assertEqual(summary.packet_dir, self.packet_dir)
        self.assertEqual(summary.zip_path, self.zip_path)
        self.assertTrue(summary.packet_dir.exists())
        self.assertTrue(summary.zip_path.exists())
        self.assertTrue(summary.first_run_qa_added)
        self.assertTrue(summary.demo_share_created)
        self.assertEqual(summary.biggest_remaining_blocker, wave.BIGGEST_REMAINING_BLOCKER)

        for relative_path in [
            "reports/protocol_lab/wave4e75_first_run_ux_audit.md",
            "reports/protocol_lab/wave4e75_narrow_width_review.md",
            "reports/protocol_lab/wave4e75_demo_readiness_report.md",
            "reports/protocol_lab/wave4e75_first_run_copy_decisions.md",
            "src/pages/Home.tsx",
            "src/pages/Companies.tsx",
            "src/pages/Company.tsx",
            "src/components/LabPanel.tsx",
            "src/components/ProtocolLabUseCaseGuide.tsx",
            "public/data/business_document_protocol_lab/product_positioning/current_case_mix_v2.json",
            "public/data/business_document_protocol_lab/product_positioning/start_here_v1.json",
            "public/data/business_document_protocol_lab/product_positioning/demo_share_v1.json",
            "scripts/tests/test_protocol_lab_product_positioning_data.mjs",
            "scripts/protocol_lab_wave4e75_first_run_demo_readiness.py",
            "scripts/tests/test_protocol_lab_wave4e75_first_run_demo_readiness.py",
        ]:
            self.assertTrue((summary.packet_dir / relative_path).is_file(), relative_path)

        for relative_path in [
            "src/App.tsx",
            "src/lib/protocolLabProductPositioning.ts",
            "src/components/ProtocolLabPilotMatrixPanel.tsx",
            "public/data/sec_narrative_drift_lab/lab_cases_v1.json",
        ]:
            self.assertTrue(
                (summary.packet_dir / relative_path).is_file(),
                f"packet-local replay dependency missing: {relative_path}",
            )

        changed_manifest = (summary.packet_dir / wave.CHANGED_FILES_MANIFEST_NAME).read_text(
            encoding="utf-8"
        )
        packet_readme = (summary.packet_dir / wave.ROOT_README_NAME).read_text(encoding="utf-8")
        render_preview = (summary.packet_dir / wave.RENDER_PREVIEW_NAME).read_text(
            encoding="utf-8"
        )

        self.assertIn("Wave 4E7.5", changed_manifest)
        self.assertIn("demo_share_v1.json", changed_manifest)
        self.assertIn("packet-local replay", packet_readme.lower())
        self.assertIn("Company / NVDA", render_preview)
        self.assertIn("Narrow Width Note", render_preview)

        console_text = "\n".join(summary.console_summary_lines)
        self.assertIn(str(summary.packet_dir.resolve()), console_text)
        self.assertIn(str(summary.zip_path.resolve()), console_text)
        self.assertIn("whether first-run QA was added or expanded: yes", console_text)
        self.assertIn("whether demo_share_v1.json was created: yes", console_text)


if __name__ == "__main__":
    unittest.main()
