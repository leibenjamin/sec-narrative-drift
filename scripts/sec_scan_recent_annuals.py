from __future__ import annotations

import argparse
import csv
import json
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, cast

import requests

from lab_output_tracks import CORE4_SHOWCASE_TICKERS
from lab_script_version import build_script_version
from sec_fetch_and_build import (
    DEFAULT_SUBMISSIONS_ZIP,
    MAX_REQUESTS_PER_SECOND,
    RateLimiter,
    derive_filing_year,
    fetch_submissions_json,
    iter_recent_filings,
    load_ticker_cik_map,
)

SCRIPT_VERSION = build_script_version(Path(__file__), "v1")
REPO_ROOT = Path(__file__).resolve().parents[1]
SECTIONS_DIR = REPO_ROOT / "scripts" / "_reports" / "risk_extraction_bundle" / "sections"
DEFAULT_OUT_JSON = REPO_ROOT / "reports" / "sec_recent_annual_scan.json"
DEFAULT_OUT_CSV = REPO_ROOT / "reports" / "sec_recent_annual_scan.csv"
DEFAULT_OUT_MD = REPO_ROOT / "reports" / "sec_recent_annual_scan.md"
def _get_default_user_agent() -> str:
    value = os.environ.get("SEC_USER_AGENT", "").strip()
    if not value:
        raise RuntimeError(
            "SEC_USER_AGENT env var is required. "
            "Set it to your name and contact email per SEC EDGAR fair-access policy."
        )
    return value


def parse_iso_date(value: str) -> Optional[date]:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_csv_tokens(raw: str) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for token in raw.split(","):
        cleaned = token.strip().upper()
        if not cleaned:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        output.append(cleaned)
    return output


def section_path_for(ticker: str, fiscal_year: int) -> Path:
    return SECTIONS_DIR / f"{ticker.upper()}_{fiscal_year}_item_1a.txt"


def rank_row(row: dict[str, Any], window_days: int) -> float:
    score = 0.0
    if row.get("latest_filing_in_window") is True:
        score += 5.0
    if row.get("has_latest_two_adjacent") is True:
        score += 3.0
    if row.get("section_pair_available") is True:
        score += 2.0
    if row.get("latest_form") == "20-F":
        score += 0.3
    days_since_latest = row.get("days_since_latest_filing")
    if isinstance(days_since_latest, int) and days_since_latest >= 0:
        freshness = max(0.0, 1.0 - (days_since_latest / float(max(window_days, 1))))
        score += freshness
    return round(score, 4)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "ticker",
        "cik",
        "latest_form",
        "latest_filing_date",
        "latest_report_date",
        "latest_fiscal_year",
        "latest_two_fiscal_years",
        "latest_pair",
        "latest_filing_in_window",
        "days_since_latest_filing",
        "has_latest_two_adjacent",
        "section_pair_available",
        "rank_score",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "ticker": row.get("ticker", ""),
                    "cik": row.get("cik", ""),
                    "latest_form": row.get("latest_form", ""),
                    "latest_filing_date": row.get("latest_filing_date", ""),
                    "latest_report_date": row.get("latest_report_date", ""),
                    "latest_fiscal_year": row.get("latest_fiscal_year", ""),
                    "latest_two_fiscal_years": ",".join(
                        str(item)
                        for item in row.get("latest_two_fiscal_years", [])
                        if isinstance(item, int)
                    ),
                    "latest_pair": row.get("latest_pair", ""),
                    "latest_filing_in_window": row.get("latest_filing_in_window", False),
                    "days_since_latest_filing": row.get("days_since_latest_filing", ""),
                    "has_latest_two_adjacent": row.get("has_latest_two_adjacent", False),
                    "section_pair_available": row.get("section_pair_available", False),
                    "rank_score": row.get("rank_score", ""),
                }
            )


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    rows = payload.get("rows", [])
    summary = payload.get("summary", {})
    shortlist = payload.get("shortlist", {})
    lines: list[str] = []
    lines.append("# SEC Recent Annual Scan")
    lines.append("")
    lines.append(f"- script: `{SCRIPT_VERSION}`")
    lines.append(f"- generated_at_utc: `{payload.get('generated_at_utc', '')}`")
    lines.append(f"- window_days: `{payload.get('window_days', '')}`")
    lines.append(f"- forms: `{', '.join(payload.get('forms', []))}`")
    lines.append(f"- tickers_scanned: `{summary.get('tickers_scanned', 0)}`")
    lines.append(f"- fetch_failures: `{summary.get('fetch_failures', 0)}`")
    lines.append(f"- latest_filing_in_window_count: `{summary.get('latest_filing_in_window_count', 0)}`")
    lines.append(f"- latest_two_adjacent_count: `{summary.get('latest_two_adjacent_count', 0)}`")
    lines.append(f"- section_pair_available_count: `{summary.get('section_pair_available_count', 0)}`")
    lines.append("")

    lines.append("## Core4 Snapshot")
    core4_rows = [row for row in rows if row.get("ticker") in set(CORE4_SHOWCASE_TICKERS)]
    if not core4_rows:
        lines.append("- none")
    else:
        for row in core4_rows:
            lines.append(
                "- "
                + f"{row.get('ticker')}: latest_pair={row.get('latest_pair') or 'none'}, "
                + f"latest_form={row.get('latest_form') or 'n/a'}, "
                + f"latest_filing_date={row.get('latest_filing_date') or 'n/a'}, "
                + f"in_window={row.get('latest_filing_in_window')}"
            )
    lines.append("")

    lines.append("## Ranked Shortlist (Ex-Core4)")
    shortlist_tickers = shortlist.get("tickers", [])
    if not shortlist_tickers:
        lines.append("- none")
    else:
        for ticker in shortlist_tickers:
            lines.append(f"- {ticker}")
    lines.append("")

    lines.append("## Top 30 Candidates")
    lines.append("| ticker | latest_pair | latest_form | latest_filing_date | in_window | adjacent | section_pair_available | rank_score |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    ranked_rows = sorted(
        [row for row in rows if isinstance(row.get("rank_score"), (int, float))],
        key=lambda row: (float(row.get("rank_score", 0.0)), str(row.get("latest_filing_date", "")), str(row.get("ticker", ""))),
        reverse=True,
    )
    for row in ranked_rows[:30]:
        lines.append(
            "| "
            + f"{row.get('ticker', '')} | {row.get('latest_pair') or 'none'} | {row.get('latest_form') or ''} | "
            + f"{row.get('latest_filing_date') or ''} | {row.get('latest_filing_in_window')} | "
            + f"{row.get('has_latest_two_adjacent')} | {row.get('section_pair_available')} | {row.get('rank_score')} |"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Scan SEC annual filings (10-K/20-F) and compute latest-two fiscal-year pairs "
            "using fiscal-year-safe derivation."
        )
    )
    parser.add_argument("--window-days", type=int, default=90, help="Recent filing window in days.")
    parser.add_argument("--forms", default="10-K,20-F", help="Comma-separated annual forms to include.")
    parser.add_argument("--tickers", default="", help="Optional comma-separated ticker filter.")
    parser.add_argument("--max-tickers", type=int, default=0, help="Optional cap on tickers scanned (0 = all).")
    parser.add_argument("--sleep-ms", type=int, default=120, help="Extra sleep per ticker in milliseconds.")
    parser.add_argument("--submissions-zip", default="", help="Optional submissions.zip path to avoid live submissions calls.")
    parser.add_argument("--force-live-ticker-map", action="store_true", help="Force live SEC ticker-map fetch.")
    parser.add_argument(
        "--user-agent",
        default=None,
        help="SEC User-Agent header. Falls back to SEC_USER_AGENT env var.",
    )
    parser.add_argument("--top-shortlist", type=int, default=12, help="Ranked ex-Core4 shortlist size.")
    parser.add_argument("--out-json", default=str(DEFAULT_OUT_JSON), help="Output JSON report path.")
    parser.add_argument("--out-csv", default=str(DEFAULT_OUT_CSV), help="Output CSV report path.")
    parser.add_argument("--out-md", default=str(DEFAULT_OUT_MD), help="Output markdown report path.")
    parser.add_argument("--verbose-progress", action="store_true", help="Emit per-ticker progress lines.")
    parser.add_argument("--progress-interval-sec", type=int, default=30, help="Heartbeat interval in seconds.")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    user_agent = (args.user_agent or "").strip() or _get_default_user_agent()
    os.environ["SEC_USER_AGENT"] = user_agent

    forms = parse_csv_tokens(args.forms)
    if not forms:
        raise SystemExit("No forms provided via --forms.")
    allowed_forms = set(forms)

    ticker_map = load_ticker_cik_map(force_live=bool(args.force_live_ticker_map), use_cache=True)
    selected_tickers = sorted(ticker_map.keys())
    if args.tickers:
        requested = set(parse_csv_tokens(args.tickers))
        selected_tickers = [ticker for ticker in selected_tickers if ticker in requested]

    if args.max_tickers > 0:
        selected_tickers = selected_tickers[: args.max_tickers]

    if not selected_tickers:
        raise SystemExit("No tickers selected for scan.")

    submissions_zip_path: Optional[Path] = None
    if args.submissions_zip:
        submissions_zip_path = Path(args.submissions_zip)
        if not submissions_zip_path.is_absolute():
            submissions_zip_path = (REPO_ROOT / submissions_zip_path).resolve()
        if not submissions_zip_path.exists():
            raise SystemExit(f"submissions.zip not found: {submissions_zip_path}")
    elif DEFAULT_SUBMISSIONS_ZIP.exists():
        submissions_zip_path = DEFAULT_SUBMISSIONS_ZIP

    today = datetime.now(timezone.utc).date()
    window_start = today - timedelta(days=max(1, int(args.window_days)))

    rows: list[dict[str, Any]] = []
    fetch_failures = 0
    session = requests.Session()
    limiter = RateLimiter(MAX_REQUESTS_PER_SECOND)
    started = time.monotonic()
    last_heartbeat = started

    for idx, ticker in enumerate(selected_tickers, start=1):
        now = time.monotonic()
        if args.verbose_progress or now - last_heartbeat >= max(1, int(args.progress_interval_sec)):
            print(
                "[progress] recent_annual_scan "
                + f"tickers={idx}/{len(selected_tickers)} failures={fetch_failures} elapsed={int(now-started)}s",
                flush=True,
            )
            last_heartbeat = now

        entry = ticker_map.get(ticker, {})
        cik = str(entry.get("cik", "")).zfill(10)
        company_name = str(entry.get("name") or ticker)

        try:
            submissions = fetch_submissions_json(
                cik,
                session=cast(Any, session),
                limiter=limiter,
                submissions_zip=submissions_zip_path,
                allow_fixture=False,
            )
            filing_rows = iter_recent_filings(submissions, allowed_forms, cik)
        except Exception as exc:  # pragma: no cover - network/runtime defensive
            fetch_failures += 1
            rows.append(
                {
                    "ticker": ticker,
                    "company_name": company_name,
                    "cik": cik,
                    "error": f"fetch_failed:{type(exc).__name__}",
                    "latest_form": None,
                    "latest_filing_date": None,
                    "latest_report_date": None,
                    "latest_fiscal_year": None,
                    "latest_two_fiscal_years": [],
                    "latest_pair": None,
                    "latest_filing_in_window": False,
                    "days_since_latest_filing": None,
                    "has_latest_two_adjacent": False,
                    "section_pair_available": False,
                    "section_prev_exists": False,
                    "section_curr_exists": False,
                    "rank_score": 0.0,
                }
            )
            if args.sleep_ms > 0:
                time.sleep(args.sleep_ms / 1000)
            continue

        seen_years: set[int] = set()
        annual_by_fiscal: list[dict[str, Any]] = []
        for filing in filing_rows:
            report_date = str(filing.get("reportDate") or "")
            filing_date = str(filing.get("filingDate") or "")
            fiscal_year = derive_filing_year(report_date, filing_date, seen_years)
            if fiscal_year is None:
                continue
            seen_years.add(fiscal_year)
            annual_by_fiscal.append(
                {
                    "form": str(filing.get("form") or ""),
                    "filing_date": filing_date,
                    "report_date": report_date,
                    "fiscal_year": fiscal_year,
                    "accession": str(filing.get("accessionNumber") or ""),
                }
            )

        annual_by_fiscal.sort(
            key=lambda item: (int(item.get("fiscal_year", 0)), str(item.get("filing_date", ""))),
            reverse=True,
        )
        latest_two = annual_by_fiscal[:2]

        latest_form = latest_two[0]["form"] if latest_two else None
        latest_filing_date = latest_two[0]["filing_date"] if latest_two else None
        latest_report_date = latest_two[0]["report_date"] if latest_two else None
        latest_fiscal_year = latest_two[0]["fiscal_year"] if latest_two else None

        latest_date_obj = parse_iso_date(str(latest_filing_date or ""))
        latest_in_window = bool(latest_date_obj is not None and latest_date_obj >= window_start)
        days_since_latest: Optional[int] = None
        if latest_date_obj is not None:
            days_since_latest = (today - latest_date_obj).days

        has_adjacent = False
        latest_pair: Optional[str] = None
        section_prev_exists = False
        section_curr_exists = False
        section_pair_available = False
        latest_two_years: list[int] = [
            int(item["fiscal_year"])
            for item in latest_two
            if isinstance(item.get("fiscal_year"), int)
        ]

        if len(latest_two_years) >= 2:
            prev_year = latest_two_years[1]
            curr_year = latest_two_years[0]
            has_adjacent = curr_year == prev_year + 1
            if has_adjacent:
                latest_pair = f"{prev_year}-{curr_year}"
                prev_path = section_path_for(ticker, prev_year)
                curr_path = section_path_for(ticker, curr_year)
                section_prev_exists = prev_path.exists()
                section_curr_exists = curr_path.exists()
                section_pair_available = section_prev_exists and section_curr_exists

        row: dict[str, Any] = {
            "ticker": ticker,
            "company_name": company_name,
            "cik": cik,
            "error": None,
            "latest_form": latest_form,
            "latest_filing_date": latest_filing_date,
            "latest_report_date": latest_report_date,
            "latest_fiscal_year": latest_fiscal_year,
            "latest_two_fiscal_years": latest_two_years,
            "latest_pair": latest_pair,
            "latest_filing_in_window": latest_in_window,
            "days_since_latest_filing": days_since_latest,
            "has_latest_two_adjacent": has_adjacent,
            "section_pair_available": section_pair_available,
            "section_prev_exists": section_prev_exists,
            "section_curr_exists": section_curr_exists,
            "latest_two": latest_two,
        }
        row["rank_score"] = rank_row(row, int(args.window_days))
        rows.append(row)

        if args.sleep_ms > 0:
            time.sleep(args.sleep_ms / 1000)

    core4_set = set(CORE4_SHOWCASE_TICKERS)
    ranked_candidates = sorted(
        [
            row
            for row in rows
            if row.get("error") in {None, ""}
            and row.get("latest_filing_in_window") is True
            and row.get("has_latest_two_adjacent") is True
        ],
        key=lambda item: (
            float(item.get("rank_score", 0.0)),
            str(item.get("latest_filing_date") or ""),
            str(item.get("ticker") or ""),
        ),
        reverse=True,
    )
    shortlist_tickers: list[str] = []
    for row in ranked_candidates:
        ticker = str(row.get("ticker") or "")
        if not ticker or ticker in core4_set:
            continue
        shortlist_tickers.append(ticker)
        if len(shortlist_tickers) >= max(0, int(args.top_shortlist)):
            break

    latest_filing_in_window_count = sum(1 for row in rows if row.get("latest_filing_in_window") is True)
    latest_two_adjacent_count = sum(1 for row in rows if row.get("has_latest_two_adjacent") is True)
    section_pair_available_count = sum(1 for row in rows if row.get("section_pair_available") is True)

    payload: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script_version": SCRIPT_VERSION,
        "user_agent": user_agent,
        "window_days": int(args.window_days),
        "window_start_date": window_start.isoformat(),
        "today_date": today.isoformat(),
        "forms": forms,
        "summary": {
            "tickers_scanned": len(selected_tickers),
            "fetch_failures": fetch_failures,
            "latest_filing_in_window_count": latest_filing_in_window_count,
            "latest_two_adjacent_count": latest_two_adjacent_count,
            "section_pair_available_count": section_pair_available_count,
        },
        "shortlist": {
            "top_shortlist": int(args.top_shortlist),
            "core4": list(CORE4_SHOWCASE_TICKERS),
            "tickers": shortlist_tickers,
        },
        "rows": rows,
    }

    out_json = Path(args.out_json)
    if not out_json.is_absolute():
        out_json = (REPO_ROOT / out_json).resolve()
    out_csv = Path(args.out_csv)
    if not out_csv.is_absolute():
        out_csv = (REPO_ROOT / out_csv).resolve()
    out_md = Path(args.out_md)
    if not out_md.is_absolute():
        out_md = (REPO_ROOT / out_md).resolve()

    write_json(out_json, payload)
    write_csv(out_csv, rows)
    write_markdown(out_md, payload)

    elapsed = int(time.monotonic() - started)
    print(
        "SEC recent annual scan complete: "
        + f"tickers={len(selected_tickers)} failures={fetch_failures} "
        + f"shortlist={len(shortlist_tickers)} elapsed={elapsed}s"
    )
    print(f"Wrote json: {out_json}")
    print(f"Wrote csv: {out_csv}")
    print(f"Wrote md: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
