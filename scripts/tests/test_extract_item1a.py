import re
import sys
import unittest
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from sec_extract_item1a import extract_item1a_from_html  # noqa: E402


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


class TestExtractItem1A(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
