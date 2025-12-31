import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional, cast


ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parent
DATA_DIR = REPO_ROOT / "public" / "data" / "sec_narrative_drift"
UNIVERSE_PATH = ROOT_DIR / "universe_featured.json"
CACHE_DIR = ROOT_DIR / "_cache"


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
