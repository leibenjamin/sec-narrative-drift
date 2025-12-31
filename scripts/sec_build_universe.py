import argparse
import json
import os
import subprocess
import sys
import time
from urllib.parse import urlparse
from pathlib import Path
from typing import Any, Optional, cast

import requests


ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parent
DATA_DIR = REPO_ROOT / "public" / "data" / "sec_narrative_drift"
UNIVERSE_PATH = ROOT_DIR / "universe_featured.json"
CACHE_DIR = ROOT_DIR / "_cache"
DEFAULT_SUBMISSIONS_ZIP = CACHE_DIR / "submissions.zip"
SEC_SUBMISSIONS_ZIP_URL = "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip"
MAX_REQUESTS_PER_SECOND = 10


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


def download_to_file(
    url: str, session: requests.Session, limiter: RateLimiter, path: Path
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    last_response: Optional[requests.Response] = None
    for attempt in range(5):
        limiter.wait()
        response = session.get(url, headers=build_headers(url), timeout=60, stream=True)
        last_response = response
        if response.status_code in {403, 429}:
            backoff = min(2 ** attempt, 8)
            time.sleep(backoff)
            continue
        response.raise_for_status()
        with path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
        return

    if last_response is not None:
        last_response.raise_for_status()
    raise RuntimeError(f"Failed to download {url}")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def as_str_dict(value: Any) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    out: dict[str, Any] = {}
    for key, item in cast(dict[object, object], value).items():
        if not isinstance(key, str):
            return None
        out[key] = item
    return out


def as_list(value: Any) -> Optional[list[Any]]:
    if not isinstance(value, list):
        return None
    return list(cast(list[Any], value))


def normalize_ticker(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip().upper()
    return text if text else None


def load_universe(path: Path) -> tuple[list[str], list[str]]:
    payload = read_json(path)
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        raise SystemExit("universe_featured.json has unexpected structure.")

    anchors_raw = as_list(payload_dict.get("anchors")) or []
    stories_raw = as_list(payload_dict.get("stories")) or []

    anchors: list[str] = []
    for row in anchors_raw:
        row_dict = as_str_dict(row)
        if row_dict is None:
            continue
        ticker = normalize_ticker(row_dict.get("ticker"))
        if ticker:
            anchors.append(ticker)

    stories: list[str] = []
    for row in stories_raw:
        row_dict = as_str_dict(row)
        if row_dict is None:
            continue
        ticker = normalize_ticker(row_dict.get("ticker"))
        if ticker:
            stories.append(ticker)

    return anchors, stories


def append_log(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{line}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch-build universe tickers.")
    parser.add_argument(
        "--only",
        choices=["anchors", "stories", "all"],
        default="all",
        help="Subset to build (default: all).",
    )
    parser.add_argument(
        "--start-at",
        dest="start_at",
        default=None,
        help="Start at this ticker (inclusive).",
    )
    parser.add_argument(
        "--sleep-ms",
        type=int,
        default=250,
        help="Sleep between tickers (default: 250ms).",
    )
    parser.add_argument(
        "--submissions-zip",
        default=None,
        help="Path to submissions.zip (bulk submissions archive).",
    )
    parser.add_argument(
        "--download-submissions-zip",
        action="store_true",
        help="Download latest submissions.zip to cache (or --submissions-zip path).",
    )
    parser.add_argument(
        "--include-20f",
        action="store_true",
        help="Include 20-F filings when available.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not UNIVERSE_PATH.exists():
        raise SystemExit(f"Universe config not found: {UNIVERSE_PATH}")

    anchors, stories = load_universe(UNIVERSE_PATH)

    if args.only == "anchors":
        tickers = anchors
    elif args.only == "stories":
        tickers = stories
    else:
        tickers = anchors + stories

    start_at = normalize_ticker(args.start_at) if args.start_at else None
    started = start_at is None

    log_path = CACHE_DIR / "build_universe.log"
    append_log(log_path, f"Start build: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    submissions_zip: Optional[Path] = None
    if args.submissions_zip:
        submissions_zip = Path(args.submissions_zip)
    if args.download_submissions_zip:
        target = submissions_zip or DEFAULT_SUBMISSIONS_ZIP
        session = requests.Session()
        limiter = RateLimiter(MAX_REQUESTS_PER_SECOND)
        append_log(log_path, f"Downloading submissions.zip to {target}")
        download_to_file(SEC_SUBMISSIONS_ZIP_URL, session, limiter, target)
        submissions_zip = target
    if submissions_zip is not None and not submissions_zip.exists():
        append_log(
            log_path,
            f"warning: submissions zip not found at {submissions_zip}; "
            "falling back to live submissions API",
        )
        submissions_zip = None

    for ticker in tickers:
        if not started:
            if ticker == start_at:
                started = True
            else:
                continue

        out_dir = DATA_DIR / ticker
        cmd = [
            sys.executable,
            str(ROOT_DIR / "sec_fetch_and_build.py"),
            "--ticker",
            ticker,
            "--years",
            "10",
            "--out",
            str(out_dir),
        ]
        if args.include_20f:
            cmd.append("--include-20f")
        if submissions_zip is not None:
            cmd.extend(["--submissions-zip", str(submissions_zip)])

        append_log(log_path, f"[{ticker}] start")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.stdout:
            append_log(log_path, f"[{ticker}] stdout: {result.stdout.strip()}")
        if result.stderr:
            append_log(log_path, f"[{ticker}] stderr: {result.stderr.strip()}")
        append_log(log_path, f"[{ticker}] exit={result.returncode}")

        if args.sleep_ms > 0:
            time.sleep(args.sleep_ms / 1000)

    append_log(log_path, f"Done build: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
