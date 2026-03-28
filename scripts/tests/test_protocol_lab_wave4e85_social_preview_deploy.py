import shutil
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))

import protocol_lab_wave4e85_social_preview_deploy as wave  # noqa: E402


STAMP = "20990101_0945"


class Wave4E85SocialPreviewDeployPacketTest(unittest.TestCase):
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
        self.assertTrue(summary.demo_share_v3_created)
        self.assertTrue(summary.og_twitter_static_tags_added)
        self.assertTrue(summary.real_share_image_created)
        self.assertTrue(summary.default_favicon_replaced)
        self.assertEqual(summary.biggest_remaining_blocker, wave.BIGGEST_REMAINING_BLOCKER)

        for relative_path in [
            "reports/protocol_lab/wave4e85_social_preview_audit.md",
            "reports/protocol_lab/wave4e85_deploy_acceptance_checklist.md",
            "reports/protocol_lab/wave4e85_demo_kit.md",
            "reports/protocol_lab/wave4e85_share_deploy_report.md",
            "reports/protocol_lab/wave4e85_public_asset_decisions.md",
            "src/pages/Home.tsx",
            "src/lib/protocolLabProductPositioning.ts",
            "public/data/business_document_protocol_lab/product_positioning/demo_share_v3.json",
            "public/favicon.svg",
            "public/apple-touch-icon.png",
            "public/social/sec-narrative-drift-lab-share-1200x630.png",
            "public/social/sec-narrative-drift-lab-icon-512.png",
            "README.md",
            "index.html",
            "scripts/lab_generate_social_preview_assets.py",
            "scripts/lab_verify_social_preview_deploy.py",
            "scripts/tests/test_lab_verify_social_preview_deploy.py",
            "scripts/tests/test_protocol_lab_product_positioning_data.mjs",
            "scripts/protocol_lab_wave4e85_social_preview_deploy.py",
            "scripts/tests/test_protocol_lab_wave4e85_social_preview_deploy.py",
        ]:
            self.assertTrue((summary.packet_dir / relative_path).is_file(), relative_path)

        changed_manifest = (summary.packet_dir / wave.CHANGED_FILES_MANIFEST_NAME).read_text(
            encoding="utf-8"
        )
        packet_readme = (summary.packet_dir / wave.PACKET_README_NAME).read_text(
            encoding="utf-8"
        )
        render_preview = (summary.packet_dir / wave.RENDER_PREVIEW_NAME).read_text(
            encoding="utf-8"
        )

        self.assertIn("Wave 4E8.5", changed_manifest)
        self.assertIn("demo_share_v3.json", changed_manifest)
        self.assertIn("sec-narrative-drift-lab-share-1200x630.png", changed_manifest)
        self.assertIn("packet-local replay", packet_readme.lower())
        self.assertIn("Metadata Excerpt", render_preview)
        self.assertIn("Cloudflare Note", render_preview)

        console_text = "\n".join(summary.console_summary_lines)
        self.assertIn(str(summary.packet_dir.resolve()), console_text)
        self.assertIn(str(summary.zip_path.resolve()), console_text)
        self.assertIn("whether demo_share_v3.json was created: yes", console_text)
        self.assertIn("whether OG/Twitter static tags were added: yes", console_text)
        self.assertIn("whether a real share image was created: yes", console_text)
        self.assertIn("whether the default favicon was replaced: yes", console_text)


if __name__ == "__main__":
    unittest.main()
