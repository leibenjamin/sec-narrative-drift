import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Optional, Sequence, cast
from urllib.parse import urlparse

import requests


SEC_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"
SEC_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"
MAX_REQUESTS_PER_SECOND = 10

ROOT_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = ROOT_DIR / "sample_fixtures"
CACHE_DIR = ROOT_DIR / "_cache"


class RateLimiter:
    def __init__(self, max_requests_per_second: float) -> None:
        self.min_interval = 1.0 / max_requests_per_second
        self.last_time = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        wait_for = self.min_interval - (now - self.last_time)
        if wait_for > 0:
            time.sleep(wait_for)
        self.last_time = time.monotonic()


def get_user_agent() -> str:
    user_agent = os.environ.get("SEC_USER_AGENT")
    if not user_agent:
        raise RuntimeError("SEC_USER_AGENT env var is required for live SEC requests.")
    return user_agent


def build_headers(url: str) -> dict[str, str]:
    host = urlparse(url).hostname or ""
    return {
        "User-Agent": get_user_agent(),
        "Accept-Encoding": "gzip, deflate, br",
        "Host": host,
    }


def download(url: str, session: requests.Session, limiter: RateLimiter) -> bytes:
    last_response: Optional[requests.Response] = None
    for attempt in range(5):
        limiter.wait()
        response = session.get(url, headers=build_headers(url), timeout=30)
        last_response = response
        if response.status_code in {403, 429}:
            backoff = min(2 ** attempt, 8)
            time.sleep(backoff)
            continue
        response.raise_for_status()
        return response.content

    if last_response is not None:
        last_response.raise_for_status()
    raise RuntimeError(f"Failed to download {url}")


def load_fixture_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8", errors="replace")))


def as_str_dict(value: Any) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    out: dict[str, Any] = {}
    for key, item in cast(dict[object, object], value).items():
        if not isinstance(key, str):
            return None
        out[key] = item
    return out


def as_str_list(value: Any) -> Optional[list[str]]:
    if not isinstance(value, list):
        return None
    out: list[str] = []
    for item in cast(list[object], value):
        if not isinstance(item, str):
            return None
        out.append(item)
    return out


def as_list(value: Any) -> Optional[list[Any]]:
    if not isinstance(value, list):
        return None
    return list(cast(list[Any], value))


def load_ticker_cik_map() -> dict[str, dict[str, str]]:
    fixture_path = FIXTURES_DIR / "company_tickers_exchange.json"
    if fixture_path.exists():
        payload = load_fixture_json(fixture_path)
    else:
        session = requests.Session()
        limiter = RateLimiter(MAX_REQUESTS_PER_SECOND)
        payload = json.loads(download(SEC_TICKER_MAP_URL, session, limiter).decode("utf-8"))

    mapping: dict[str, dict[str, str]] = {}

    payload_dict = as_str_dict(payload)

    if payload_dict is not None and "fields" in payload_dict and "data" in payload_dict:
        fields = as_str_list(payload_dict.get("fields"))
        data = as_list(payload_dict.get("data"))
        if fields is None or data is None:
            raise RuntimeError("Unexpected ticker map structure")

        for row in data:
            if not isinstance(row, Sequence) or isinstance(row, (str, bytes)):
                continue
            row_seq = cast(Sequence[Any], row)
            limit = min(len(fields), len(row_seq))
            record: dict[str, Any] = {}
            for idx in range(limit):
                record[fields[idx]] = row_seq[idx]
            ticker_value = record.get("ticker")
            if not isinstance(ticker_value, str):
                continue
            ticker = ticker_value.upper().strip()
            if not ticker:
                continue
            cik = str(record.get("cik", "")).zfill(10)
            mapping[ticker] = {
                "cik": cik,
                "name": str(record.get("title", "")),
                "exchange": str(record.get("exchange", "")),
            }
        return mapping

    if payload_dict is not None:
        for entry in payload_dict.values():
            entry_dict = as_str_dict(entry)
            if entry_dict is None:
                continue
            ticker_value = entry_dict.get("ticker")
            if not isinstance(ticker_value, str):
                continue
            ticker = ticker_value.upper().strip()
            if not ticker:
                continue
            mapping[ticker] = {
                "cik": str(entry_dict.get("cik_str", "")).zfill(10),
                "name": str(entry_dict.get("title", "")),
                "exchange": str(entry_dict.get("exchange", "")),
            }
        return mapping

    raise RuntimeError("Unexpected ticker map format")


def fetch_submissions_json(cik10: str) -> dict[str, Any]:
    fixture_path = FIXTURES_DIR / f"CIK{cik10}.json"
    if fixture_path.exists():
        return load_fixture_json(fixture_path)

    session = requests.Session()
    limiter = RateLimiter(MAX_REQUESTS_PER_SECOND)
    url = SEC_SUBMISSIONS_URL.format(cik10=cik10)
    return json.loads(download(url, session, limiter).decode("utf-8"))


def iter_recent_filings(submissions: dict[str, Any]) -> list[dict[str, str]]:
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    filing_dates = recent.get("filingDate", [])
    report_dates = recent.get("reportDate", [])
    accession_numbers = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    length = min(
        len(forms),
        len(filing_dates),
        len(accession_numbers),
        len(primary_docs),
        len(report_dates) if report_dates else len(filing_dates),
    )

    rows: list[dict[str, str]] = []
    for idx in range(length):
        form = forms[idx]
        if form != "10-K":
            continue
        rows.append(
            {
                "form": form,
                "filingDate": filing_dates[idx],
                "reportDate": report_dates[idx] if report_dates else "",
                "accessionNumber": accession_numbers[idx],
                "primaryDocument": primary_docs[idx],
            }
        )

    return sorted(rows, key=lambda row: row["filingDate"], reverse=True)


def build_primary_doc_url(cik10: str, accession: str, primary_doc: str) -> str:
    cik_no_leading = str(int(cik10))
    acc_no_dashes = accession.replace("-", "")
    return f"{SEC_ARCHIVES_BASE}/{cik_no_leading}/{acc_no_dashes}/{primary_doc}"


def load_fixture_html(primary_doc: str) -> Optional[bytes]:
    fixture_path = FIXTURES_DIR / primary_doc
    if fixture_path.exists():
        return fixture_path.read_bytes()
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch SEC filings (fixtures first).")
    parser.add_argument("--ticker", required=True, help="Ticker symbol (e.g., AAPL).")
    parser.add_argument(
        "--years",
        type=int,
        default=10,
        help="Number of years to include (default: 10).",
    )
    parser.add_argument("--out", help="Output folder for JSON artifacts.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of filings to process.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    ticker = args.ticker.upper().strip()
    mapping = load_ticker_cik_map()
    if ticker not in mapping:
        raise SystemExit(f"Ticker not found in mapping: {ticker}")

    cik10 = mapping[ticker]["cik"]
    submissions = fetch_submissions_json(cik10)
    filings = iter_recent_filings(submissions)

    if args.limit:
        filings = filings[: args.limit]

    if not filings:
        raise SystemExit("No 10-K filings found for ticker.")

    cache_dir = CACHE_DIR / ticker
    cache_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    limiter = RateLimiter(MAX_REQUESTS_PER_SECOND)

    for filing in filings:
        url = build_primary_doc_url(cik10, filing["accessionNumber"], filing["primaryDocument"])
        html_bytes = load_fixture_html(filing["primaryDocument"])
        if html_bytes is None:
            html_bytes = download(url, session, limiter)

        filename = f"{filing['accessionNumber'].replace('-', '')}_{filing['primaryDocument']}"
        output_path = cache_dir / filename
        output_path.write_bytes(html_bytes)
        print(f"saved: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
