import re
import sys
import unittest
from pathlib import Path
from typing import Any, Optional, cast

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from sec_extract_item1a import extract_item1a_from_html  # noqa: E402
from sec_extract_item1a import (  # noqa: E402
    END_MARKERS_10K,
    build_blockdoc_from_text,
    find_end_marker_in_text,
    score_toc_window,
)


def pick_best_fixture(files: list[Path]) -> Optional[Path]:
    if not files:
        return None
    files.sort(key=lambda path: path.stat().st_size)
    large_files = [path for path in files if path.stat().st_size >= 8000]
    return large_files[-1] if large_files else files[-1]


def find_fixture(ticker: str) -> Optional[Path]:
    sample_dir = ROOT_DIR / "sample_fixtures"
    if sample_dir.exists():
        sample_files = list(sample_dir.glob(f"{ticker.lower()}-*.htm"))
        sample_pick = pick_best_fixture(sample_files)
        if sample_pick:
            return sample_pick

    cache_dir = ROOT_DIR / "_cache" / ticker
    if not cache_dir.exists():
        return None
    return pick_best_fixture(list(cache_dir.glob("*.htm")))


def find_fixture_by_name(filename: str) -> Optional[Path]:
    fixture = ROOT_DIR / "sample_fixtures" / filename
    return fixture if fixture.exists() else None


def as_dict(value: Any) -> Optional[dict[str, Any]]:
    if isinstance(value, dict):
        return cast(dict[str, Any], value)
    return None


def as_str(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    return None


def as_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    return None


class TestExtractItem1A(unittest.TestCase):
    def test_toc_score_numeric_only(self) -> None:
        lines = [
            "Table of Contents",
            "Risk Factors",
            "1A",
            "11",
            "Item 1. Business",
            "1",
            "Item 1A. Risk Factors",
            "12",
            "Item 1B. Unresolved Staff Comments",
            "13",
            "Item 2. Properties",
            "14",
            "7A",
            "58",
        ]
        doc = build_blockdoc_from_text("\n\n".join(lines))
        score = score_toc_window(doc.blocks)
        self.assertTrue(score["tocLike"], msg=f"tocLike false for score={score}")
        self.assertGreaterEqual(score["pageNumBlocks"], 4)
        self.assertGreaterEqual(score["itemCodeBlocks"], 2)

    def test_heading_like_classification(self) -> None:
        sample = "\n\n".join(
            [
                "ITEM 1A—RISK FACTORS",
                "See Item 1A. Risk Factors",
                "Item 1A, \"Risk Factors.\"",
            ]
        )
        doc = build_blockdoc_from_text(sample)
        self.assertEqual(len(doc.blocks), 3)
        self.assertTrue(doc.blocks[0].is_heading_like)
        self.assertFalse(doc.blocks[1].is_heading_like)
        self.assertFalse(doc.blocks[2].is_heading_like)

    def test_end_marker_without_blank_line(self) -> None:
        text = "\n".join(
            [
                "Item 1A. Risk Factors",
                "Item 1B. Unresolved Staff Comments",
                "Item 2. Properties",
            ]
        )
        start_idx = text.lower().find("item 1a")
        end_idx, end_marker = find_end_marker_in_text(text, start_idx, END_MARKERS_10K)
        self.assertIsNotNone(end_idx)
        self.assertEqual(end_marker, "1B")

    def assert_fixture(self, ticker: str) -> None:
        fixture = find_fixture(ticker)
        if fixture is None:
            self.skipTest(f"Missing cached fixture for {ticker}")
        if fixture.stat().st_size < 8000:
            self.skipTest(f"{ticker} fixture too small for a normal extract ({fixture.stat().st_size} bytes)")
        html = fixture.read_text(encoding="utf-8", errors="replace")
        section, confidence, _method, warnings, _debug = extract_item1a_from_html(html)

        self.assertGreaterEqual(
            len(section),
            8000,
            msg=f"{ticker} extraction too short ({len(section)} chars)",
        )

        head = section[:500]
        toc_hits = re.findall(r"(?m)^\\s*item\\s+\\d", head, flags=re.IGNORECASE)
        self.assertLess(
            len(toc_hits),
            3,
            msg=f"{ticker} extraction looks like a TOC cluster in the first 500 chars",
        )

        if confidence < 0.55:
            print(f"warning: low confidence {confidence:.2f} for {ticker}: {warnings}")

    def test_nvda_fixture(self) -> None:
        self.assert_fixture("NVDA")

    def test_aapl_fixture(self) -> None:
        self.assert_fixture("AAPL")

    def test_tsla_fixture(self) -> None:
        self.assert_fixture("TSLA")

    def test_tsm_fixture(self) -> None:
        self.assert_fixture("TSM")

    def test_ms_fixture_toc_guard(self) -> None:
        fixture = find_fixture_by_name("ms-20191231.htm")
        if fixture is None:
            self.skipTest("Missing ms-20191231.htm fixture")
        html = fixture.read_text(encoding="utf-8", errors="replace")
        section, _confidence, _method, _warnings, debug = extract_item1a_from_html(html)
        debug_info = as_dict(debug.get("debug"))
        if debug_info is None:
            self.fail("Missing debug output")
        toc_score = as_dict(debug_info.get("tocScoreSliceHead"))
        if toc_score is None:
            self.fail("Missing tocScoreSliceHead in debug output")
        toc_like = as_bool(toc_score.get("tocLike"))
        if toc_like is None:
            self.fail("tocLike missing in tocScoreSliceHead")
        self.assertFalse(toc_like, msg=f"toc_like_head true: {toc_score}")
        head = section[:500].lower()
        self.assertIn("risk factors", head, msg="Risk Factors heading not found near slice head")

    def test_cost_fixture_item1_order(self) -> None:
        fixture = find_fixture_by_name("cost-20190901.htm")
        if fixture is None:
            self.skipTest("Missing cost-20190901.htm fixture")
        html = fixture.read_text(encoding="utf-8", errors="replace")
        section, _confidence, _method, _warnings, _debug = extract_item1a_from_html(html)
        lower = section.lower()
        idx_item1a = lower.find("item 1a")
        idx_item1_business = lower.find("item 1. business")
        if idx_item1_business != -1 and idx_item1a != -1:
            self.assertGreater(idx_item1_business, idx_item1a)

    def test_pfe_fixture_end_marker(self) -> None:
        fixture = find_fixture_by_name("pfe-20151231.htm")
        if fixture is None:
            self.skipTest("Missing pfe-20151231.htm fixture")
        html = fixture.read_text(encoding="utf-8", errors="replace")
        _section, _confidence, _method, warnings, debug = extract_item1a_from_html(html)
        end_marker = as_str(debug.get("endMarkerUsed"))
        if end_marker is None:
            self.assertIn("end_fallback_used", warnings)

    def test_tsm_20f_bounds(self) -> None:
        fixture = find_fixture_by_name("tsm-2018-20f.htm")
        if fixture is None:
            self.skipTest("Missing tsm-2018-20f.htm fixture")
        html = fixture.read_text(encoding="utf-8", errors="replace")
        _section, _confidence, _method, _warnings, debug = extract_item1a_from_html(html)
        start_marker = as_str(debug.get("startMarker")) or ""
        end_marker = as_str(debug.get("endMarkerUsed")) or ""
        self.assertIn(
            start_marker,
            {"item3d_risk_heading", "item3d_heading_followed_by_risk", "d_risk_factors_heading"},
        )
        self.assertIn(end_marker, {"4", "4A", "4B"})


if __name__ == "__main__":
    unittest.main()
