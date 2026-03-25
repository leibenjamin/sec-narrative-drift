import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import lab_verify_social_preview_deploy as verify  # noqa: E402


def build_html(
    expected: verify.ExpectedSurfaceTruth,
    *,
    title: str | None = None,
    favicon_href: str | None = None,
    apple_touch_icon_href: str | None = None,
    include_share_image: bool = True,
    asset_prefix: str = "/sec-narrative-drift/assets/",
    extra_tail: str = "",
) -> str:
    meta_lines: list[str] = []
    for tag in expected.meta_tags:
        if not include_share_image and tag.attr_value in {"og:image", "twitter:image"}:
            continue
        meta_lines.append(
            f'    <meta {tag.attr_name}="{tag.attr_value}" content="{tag.content}" />'
        )
    return "\n".join(
        [
            "<!doctype html>",
            "<html lang=\"en\">",
            "  <head>",
            f'    <link rel="icon" type="image/svg+xml" href="{favicon_href or expected.favicon_href}" />',
            f'    <link rel="apple-touch-icon" href="{apple_touch_icon_href or expected.apple_touch_icon_href}" />',
            *meta_lines,
            f"    <title>{title or expected.title}</title>",
            f'    <script type="module" crossorigin src="{asset_prefix}index-built.js"></script>',
            f'    <link rel="modulepreload" crossorigin href="{asset_prefix}react-vendor-built.js">',
            f'    <link rel="stylesheet" crossorigin href="{asset_prefix}index-built.css">',
            "  </head>",
            "  <body>",
            '    <div id="root"></div>',
            f"    {extra_tail}",
            "  </body>",
            "</html>",
        ]
    )


class SocialPreviewDeployVerifierTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.expected = verify.build_expected_surface_truth()
        cls.good_html = build_html(cls.expected)
        cls.build_page_url = "https://expected.example/sec-narrative-drift/"
        cls.build_check = verify.evaluate_html_surface(
            cls.good_html,
            cls.build_page_url,
            cls.expected,
            "/sec-narrative-drift/",
        )

    def test_evaluate_html_surface_extracts_required_share_urls_with_exact_metadata(self) -> None:
        check = verify.evaluate_html_surface(
            self.good_html,
            "https://benlei.org/sec-narrative-drift/",
            self.expected,
            "/sec-narrative-drift/",
        )

        self.assertTrue(check.has_root_div)
        self.assertFalse(check.is_cloudflare_challenge)
        self.assertEqual(check.title, self.expected.title)
        self.assertEqual(check.missing_meta_tags, [])
        self.assertEqual(check.mismatched_meta_tags, [])
        self.assertEqual(check.stale_markers, [])
        self.assertTrue(check.runtime_asset_prefix_ok)
        self.assertEqual(
            check.share_image_url,
            self.expected.share_image_url,
        )
        self.assertEqual(
            check.favicon_url,
            "https://benlei.org/sec-narrative-drift/favicon.svg",
        )
        self.assertEqual(
            check.apple_touch_icon_url,
            "https://benlei.org/sec-narrative-drift/apple-touch-icon.png",
        )

    def test_stale_html_is_classified_as_stale_deploy(self) -> None:
        stale_html = build_html(
            self.expected,
            title="sec-narrative-drift",
            favicon_href="/sec-narrative-drift/vite.svg",
            include_share_image=False,
            asset_prefix="/sec-narrative-drift/assets/",
        )
        fetch = verify.UrlFetchResult(
            url="https://benlei.org/sec-narrative-drift/",
            final_url="https://benlei.org/sec-narrative-drift/",
            status=200,
            content_type="text/html",
            headers={},
            body=stale_html,
            error=None,
        )
        check = verify.evaluate_html_surface(
            stale_html,
            fetch.final_url,
            self.expected,
            "/sec-narrative-drift/",
        )
        classification = verify.classify_surface(
            fetch=fetch,
            check=check,
            expected=self.expected,
            expected_runtime_asset_paths=set(self.build_check.runtime_asset_paths),
            expected_base_path="/sec-narrative-drift/",
            expected_favicon_url="https://benlei.org/sec-narrative-drift/favicon.svg",
            expected_apple_touch_icon_url="https://benlei.org/sec-narrative-drift/apple-touch-icon.png",
            expected_share_image_url=self.expected.share_image_url,
        )

        self.assertEqual(classification.kind, "stale deploy")
        self.assertIn("title mismatch", classification.reasons)
        self.assertIn("share image URL mismatch", classification.reasons)
        self.assertTrue(check.stale_markers)

    def test_slashless_and_slashed_behavior_divergence_is_detected(self) -> None:
        slashless_fetch = verify.UrlFetchResult(
            url="https://benlei.org/sec-narrative-drift",
            final_url="https://benlei.org/sec-narrative-drift",
            status=200,
            content_type="text/html",
            headers={},
            body=self.good_html,
            error=None,
        )
        slashed_fetch = verify.UrlFetchResult(
            url="https://benlei.org/sec-narrative-drift/",
            final_url="https://benlei.org/sec-narrative-drift/",
            status=200,
            content_type="text/html",
            headers={},
            body=self.good_html,
            error=None,
        )

        slashless_check = verify.evaluate_html_surface(
            self.good_html,
            slashless_fetch.final_url,
            self.expected,
            "/sec-narrative-drift/",
        )
        slashed_check = verify.evaluate_html_surface(
            self.good_html,
            slashed_fetch.final_url,
            self.expected,
            "/sec-narrative-drift/",
        )
        differences = verify.describe_slash_divergence(
            slashless_fetch,
            slashless_check,
            slashed_fetch,
            slashed_check,
        )

        self.assertIn("final_url", differences[0])
        self.assertTrue(any("favicon_url" in item for item in differences))
        self.assertEqual(slashless_check.favicon_url, "https://benlei.org/favicon.svg")
        self.assertEqual(
            slashed_check.favicon_url,
            "https://benlei.org/sec-narrative-drift/favicon.svg",
        )

    def test_interstitial_markers_are_reported_distinctly_from_hard_challenge_pages(self) -> None:
        interstitial_html = build_html(
            self.expected,
            extra_tail=(
                "<script>"
                "var a=document.createElement('script');"
                "a.src='/cdn-cgi/challenge-platform/scripts/jsd/main.js';"
                "</script>"
            ),
        )
        check = verify.evaluate_html_surface(
            interstitial_html,
            "https://benlei.org/sec-narrative-drift/",
            self.expected,
            "/sec-narrative-drift/",
        )

        self.assertTrue(check.is_cloudflare_challenge)
        self.assertIn("/cdn-cgi/challenge-platform/", check.challenge_markers)
        self.assertEqual(check.title, self.expected.title)
        self.assertNotIn("Just a moment...", check.challenge_markers)

    def test_missing_dist_assets_fail_local_build_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dist_root = Path(tmpdir)
            dist_index = dist_root / "index.html"
            dist_index.write_text(self.good_html, encoding="utf-8")
            (dist_root / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")
            (dist_root / "assets").mkdir()
            (dist_root / "assets" / "index-built.js").write_text("console.log('x')", encoding="utf-8")
            (dist_root / "assets" / "react-vendor-built.js").write_text(
                "console.log('vendor')",
                encoding="utf-8",
            )
            (dist_root / "assets" / "index-built.css").write_text("body{}", encoding="utf-8")

            ok, issues = verify.check_local_dist_html(dist_index)

        self.assertFalse(ok)
        self.assertTrue(any("apple-touch-icon.png" in issue for issue in issues))
        self.assertTrue(
            any("social/sec-narrative-drift-lab-share-1200x630.png" in issue for issue in issues)
        )


if __name__ == "__main__":
    unittest.main()
