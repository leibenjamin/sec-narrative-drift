import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, TypedDict, cast
from unittest.mock import patch

import requests

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import sec_fetch_and_build  # noqa: E402
from sec_cache import (  # noqa: E402
    EXTRACTOR_VERSION,
    NORMALIZER_VERSION,
    atomic_write_json,
    compute_sha256_text,
    enforce_cache_size_limit,
    filing_html_path,
    filing_meta_path,
    filing_text_path,
    risk_meta_path,
    risk_text_path,
    save_gz_text_atomic,
)
from sec_extract_item1a import clean_html_to_text, extract_item1a_from_html  # noqa: E402


class FilingRow(TypedDict):
    cik: str
    form: str
    filingDate: str
    reportDate: str
    accessionNumber: str
    primaryDocument: str


def get_first_filing(ticker: str, submissions_zip: Path) -> tuple[FilingRow, str]:
    mapping = sec_fetch_and_build.load_ticker_cik_map()
    if ticker not in mapping:
        raise unittest.SkipTest(f"Ticker not found in mapping: {ticker}")
    primary_cik = mapping[ticker]["cik"]
    session = requests.Session()
    limiter = sec_fetch_and_build.RateLimiter(1)
    submissions = sec_fetch_and_build.fetch_submissions_json(
        primary_cik, session=session, limiter=limiter, submissions_zip=submissions_zip
    )
    filings = sec_fetch_and_build.collect_filings(
        submissions,
        {"10-K"},
        session,
        limiter,
        max_items=1,
        submissions_zip=submissions_zip,
        cik10=primary_cik,
    )
    if not filings:
        raise unittest.SkipTest(f"No filings found for {ticker}")
    rows = cast(list[FilingRow], filings)
    return rows[0], primary_cik


class TestSecCache(unittest.TestCase):
    def test_atomic_write_removes_tmp(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "meta.json"
            atomic_write_json(target, {"ok": True})
            self.assertTrue(target.exists())
            self.assertFalse((Path(temp_dir) / "meta.json.tmp").exists())

    def test_enforce_cache_size_limit_prunes_optional(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env = {"SEC_CACHE_ROOT": temp_dir}
            with patch.dict(os.environ, env, clear=False):
                cik = "0000000001"
                accession = "000000-00-000001"
                save_gz_text_atomic(filing_text_path(cik, accession), "ok")
                save_gz_text_atomic(filing_html_path(cik, accession), "x" * 5000)
                report = enforce_cache_size_limit(max_gb=0.0)
                removed_files = report.get("removedFiles")
                self.assertIsInstance(removed_files, list)
                self.assertTrue(removed_files)
                self.assertTrue(filing_text_path(cik, accession).exists())
                self.assertFalse(filing_html_path(cik, accession).exists())

    def test_cache_reuse_avoids_download(self) -> None:
        submissions_zip = ROOT_DIR / "_cache" / "submissions.zip"
        if not submissions_zip.exists():
            self.skipTest("submissions.zip not found for cache reuse test")

        fixture = ROOT_DIR / "sample_fixtures" / "aapl-20240928.htm"
        if not fixture.exists():
            self.skipTest("AAPL fixture missing for cache reuse test")

        html = fixture.read_text(encoding="utf-8", errors="replace")
        filing_text = clean_html_to_text(html)
        section, confidence, method, warnings, debug_meta = extract_item1a_from_html(html)

        with tempfile.TemporaryDirectory() as temp_dir:
            env = {"SEC_CACHE_ROOT": temp_dir, "SEC_USER_AGENT": "test@example.com"}
            with patch.dict(os.environ, env, clear=False):
                filing, primary_cik = get_first_filing("AAPL", submissions_zip)
                accession = filing["accessionNumber"]
                form_type = filing["form"]
                filing_date = filing["filingDate"]
                report_date = filing["reportDate"]
                url = sec_fetch_and_build.build_primary_doc_url(
                    primary_cik, accession, filing["primaryDocument"]
                )

                save_gz_text_atomic(filing_text_path(primary_cik, accession), filing_text)
                atomic_write_json(
                    filing_meta_path(primary_cik, accession),
                    {
                        "cik": primary_cik,
                        "accessionNumber": accession,
                        "formType": form_type,
                        "primaryDocument": filing["primaryDocument"],
                        "filingDate": filing_date,
                        "reportDate": report_date,
                        "secUrl": url,
                        "extractorVersion": EXTRACTOR_VERSION,
                        "normalizerVersion": NORMALIZER_VERSION,
                        "source": "fixture",
                        "charCount": len(filing_text),
                        "tokenCount": 0,
                        "uniqueTokens": 0,
                        "paragraphCount": 0,
                        "textBytes": len(filing_text.encode("utf-8")),
                        "sha256FilingText": compute_sha256_text(filing_text),
                        "generatedAtUtc": "2025-01-01T00:00:00Z",
                    },
                )
                save_gz_text_atomic(risk_text_path(primary_cik, accession, form_type), section)
                atomic_write_json(
                    risk_meta_path(primary_cik, accession),
                    {
                        "cik": primary_cik,
                        "accessionNumber": accession,
                        "formType": form_type,
                        "filingDate": filing_date,
                        "reportDate": report_date,
                        "secUrl": url,
                        "section": "item_1a",
                        "extractorVersion": EXTRACTOR_VERSION,
                        "normalizerVersion": NORMALIZER_VERSION,
                        "confidence": confidence,
                        "method": method,
                        "warnings": warnings,
                        "startMarker": debug_meta.get("startMarker"),
                        "endMarker": debug_meta.get("endMarkerUsed"),
                        "tocDetected": debug_meta.get("tocDetected", False),
                        "tocRemoved": debug_meta.get("tocRemoved", False),
                        "charCount": len(section),
                        "tokenCount": 0,
                        "uniqueTokens": 0,
                        "paragraphCount": 0,
                        "sha256RiskText": compute_sha256_text(section),
                        "includedInMetrics": True,
                        "qualityGateFailed": False,
                        "hasItem1C": bool(debug_meta.get("hasItem1C", False)),
                        "generatedAtUtc": "2025-01-01T00:00:00Z",
                    },
                )

                out_dir = Path(temp_dir) / "out"
                args = [
                    "--ticker",
                    "AAPL",
                    "--limit",
                    "1",
                    "--out",
                    str(out_dir),
                    "--submissions-zip",
                    str(submissions_zip),
                ]
                with patch("sec_fetch_and_build.download", side_effect=AssertionError("download called")):
                    result = sec_fetch_and_build.main(args)
                self.assertEqual(result, 0)

    def test_version_bump_rebuilds_from_cached_html(self) -> None:
        submissions_zip = ROOT_DIR / "_cache" / "submissions.zip"
        if not submissions_zip.exists():
            self.skipTest("submissions.zip not found for cache version test")

        fixture = ROOT_DIR / "sample_fixtures" / "aapl-20240928.htm"
        if not fixture.exists():
            self.skipTest("AAPL fixture missing for cache version test")

        html = fixture.read_text(encoding="utf-8", errors="replace")
        with tempfile.TemporaryDirectory() as temp_dir:
            env = {"SEC_CACHE_ROOT": temp_dir, "SEC_USER_AGENT": "test@example.com"}
            with patch.dict(os.environ, env, clear=False):
                filing, primary_cik = get_first_filing("AAPL", submissions_zip)
                accession = filing["accessionNumber"]
                form_type = filing["form"]
                save_gz_text_atomic(filing_html_path(primary_cik, accession), html)
                atomic_write_json(
                    filing_meta_path(primary_cik, accession),
                    {
                        "normalizerVersion": "0.0",
                        "extractorVersion": "0.0",
                    },
                )
                save_gz_text_atomic(risk_text_path(primary_cik, accession, form_type), "old")
                atomic_write_json(
                    risk_meta_path(primary_cik, accession),
                    {
                        "extractorVersion": "0.0",
                        "normalizerVersion": "0.0",
                    },
                )

                out_dir = Path(temp_dir) / "out"
                args = [
                    "--ticker",
                    "AAPL",
                    "--limit",
                    "1",
                    "--out",
                    str(out_dir),
                    "--submissions-zip",
                    str(submissions_zip),
                ]
                with patch("sec_fetch_and_build.download", side_effect=AssertionError("download called")):
                    result = sec_fetch_and_build.main(args)
                self.assertEqual(result, 0)

                updated_filing_meta = sec_fetch_and_build.load_json(
                    filing_meta_path(primary_cik, accession)
                )
                updated_risk_meta = sec_fetch_and_build.load_json(
                    risk_meta_path(primary_cik, accession)
                )
                if not isinstance(updated_filing_meta, dict):
                    self.fail("Missing updated filing_meta.json")
                if not isinstance(updated_risk_meta, dict):
                    self.fail("Missing updated rf_meta.json")
                filing_meta = cast(dict[str, Any], updated_filing_meta)
                risk_meta = cast(dict[str, Any], updated_risk_meta)
                self.assertEqual(filing_meta.get("normalizerVersion"), NORMALIZER_VERSION)
                self.assertEqual(filing_meta.get("extractorVersion"), EXTRACTOR_VERSION)
                self.assertEqual(risk_meta.get("normalizerVersion"), NORMALIZER_VERSION)
                self.assertEqual(risk_meta.get("extractorVersion"), EXTRACTOR_VERSION)


if __name__ == "__main__":
    unittest.main()
