import shutil
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))

import protocol_lab_wave4e8_external_demo_share as wave  # noqa: E402


STAMP = "20990101_0855"


class Wave4E8ExternalDemoSharePacketTest(unittest.TestCase):
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

    def test_generate_wave_builds_packet_and_includes_required_files(self) -> None:
        summary = wave.generate_wave(stamp=STAMP)

        self.assertEqual(summary.packet_dir, self.packet_dir)
        self.assertEqual(summary.zip_path, self.zip_path)
        self.assertTrue(summary.packet_dir.exists())
        self.assertTrue(summary.zip_path.exists())
        self.assertTrue(summary.demo_share_v2_created)
        self.assertTrue(summary.readme_top_section_updated)
        self.assertTrue(summary.public_metadata_improved)
        self.assertEqual(summary.biggest_remaining_blocker, wave.BIGGEST_REMAINING_BLOCKER)

        for relative_path in [
            "reports/protocol_lab/wave4e8_public_surface_language_audit.md",
            "reports/protocol_lab/wave4e8_external_demo_readiness.md",
            "reports/protocol_lab/wave4e8_share_pass_report.md",
            "reports/protocol_lab/wave4e8_public_wording_decisions.md",
            "src/pages/Home.tsx",
            "src/pages/Companies.tsx",
            "src/pages/Company.tsx",
            "src/components/LabPanel.tsx",
            "src/components/ProtocolLabPilotMatrixPanel.tsx",
            "src/components/PageMetadata.tsx",
            "src/lib/protocolLabProductPositioning.ts",
            "public/data/business_document_protocol_lab/product_positioning/current_case_mix_v2.json",
            "public/data/business_document_protocol_lab/product_positioning/start_here_v1.json",
            "public/data/business_document_protocol_lab/product_positioning/demo_share_v2.json",
            "README.md",
            "index.html",
            "scripts/tests/test_protocol_lab_product_positioning_data.mjs",
            "scripts/protocol_lab_wave4e8_external_demo_share.py",
            "scripts/tests/test_protocol_lab_wave4e8_external_demo_share.py",
        ]:
            self.assertTrue((summary.packet_dir / relative_path).is_file(), relative_path)

        for relative_path in [
            "src/App.tsx",
            "src/components/ProtocolLabUseCaseGuide.tsx",
            "public/data/sec_narrative_drift_lab/lab_cases_v1.json",
        ]:
            self.assertTrue(
                (summary.packet_dir / relative_path).is_file(),
                f"packet-local replay dependency missing: {relative_path}",
            )

        changed_manifest = (summary.packet_dir / wave.CHANGED_FILES_MANIFEST_NAME).read_text(
            encoding="utf-8"
        )
        packet_readme = (summary.packet_dir / wave.PACKET_README_NAME).read_text(
            encoding="utf-8"
        )
        render_preview = (summary.packet_dir / wave.RENDER_PREVIEW_NAME).read_text(
            encoding="utf-8"
        )

        self.assertIn("Wave 4E8", changed_manifest)
        self.assertIn("demo_share_v2.json", changed_manifest)
        self.assertIn("README.md", changed_manifest)
        self.assertIn("packet-local replay", packet_readme.lower())
        self.assertIn("Company / LLY", render_preview)
        self.assertIn("README Top Section", render_preview)

        console_text = "\n".join(summary.console_summary_lines)
        self.assertIn(str(summary.packet_dir.resolve()), console_text)
        self.assertIn(str(summary.zip_path.resolve()), console_text)
        self.assertIn("whether demo_share_v2.json was created: yes", console_text)
        self.assertIn("whether README top section was updated: yes", console_text)
        self.assertIn("whether lightweight public metadata was improved: yes", console_text)


if __name__ == "__main__":
    unittest.main()
