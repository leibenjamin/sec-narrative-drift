import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence, cast
from urllib.parse import urlparse

import requests

from sec_extract_item1a import extract_item1a_from_html, split_paragraphs
from sec_metrics import SectionYear as MetricsSectionYear, ShiftsPayload, build_metrics
from sec_quality import (
    SectionYear as QualitySectionYear,
    ShiftPair as QualityShiftPair,
    ShiftTerm as QualityShiftTerm,
    build_excerpt_pairs,
)

SEC_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"
SEC_SUBMISSIONS_FILE_URL = "https://data.sec.gov/submissions/{filename}"
SEC_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"
MAX_REQUESTS_PER_SECOND = 10
SECTION_NAME = "10k_item1a"
MIN_PRIMARY_DOC_BYTES = 10000
META_NOTES = [
    "Ticker/CIK mapping is SEC-provided and may be incomplete or outdated.",
    "Narrative Drift is descriptive; causal explanations are hypotheses.",
]

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


def normalize_text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if text else None


def resolve_company_name(map_name: Any, submissions_name: Any, fallback: str) -> str:
    map_value = normalize_text(map_name)
    if map_value:
        return map_value
    submissions_value = normalize_text(submissions_name)
    if submissions_value:
        return submissions_value
    return fallback


def load_ticker_cik_map(force_live: bool = False) -> dict[str, dict[str, str]]:
    fixture_path = FIXTURES_DIR / "company_tickers_exchange.json"
    if fixture_path.exists() and not force_live:
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


def fetch_submissions_json(
    cik10: str,
    session: Optional[requests.Session] = None,
    limiter: Optional[RateLimiter] = None,
) -> dict[str, Any]:
    fixture_path = FIXTURES_DIR / f"CIK{cik10}.json"
    if fixture_path.exists():
        return load_fixture_json(fixture_path)

    session = session or requests.Session()
    limiter = limiter or RateLimiter(MAX_REQUESTS_PER_SECOND)
    url = SEC_SUBMISSIONS_URL.format(cik10=cik10)
    return json.loads(download(url, session, limiter).decode("utf-8"))


def iter_recent_filings(
    submissions: dict[str, Any],
    allowed_forms: set[str],
) -> list[dict[str, str]]:
    filings = as_str_dict(submissions.get("filings"))
    if filings is None:
        return []
    recent = as_str_dict(filings.get("recent"))
    if recent is None:
        return []
    forms = as_list(recent.get("form")) or []
    filing_dates = as_list(recent.get("filingDate")) or []
    report_dates = as_list(recent.get("reportDate")) or []
    accession_numbers = as_list(recent.get("accessionNumber")) or []
    primary_docs = as_list(recent.get("primaryDocument")) or []

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
        if not isinstance(form, str):
            continue
        if form not in allowed_forms:
            continue
        filing_date = filing_dates[idx]
        if not isinstance(filing_date, str):
            continue
        accession = accession_numbers[idx]
        if not isinstance(accession, str):
            continue
        primary_doc = primary_docs[idx]
        if not isinstance(primary_doc, str):
            continue
        report_date = report_dates[idx] if report_dates else ""
        if not isinstance(report_date, str):
            report_date = ""
        rows.append(
            {
                "form": form,
                "filingDate": filing_date,
                "reportDate": report_date,
                "accessionNumber": accession,
                "primaryDocument": primary_doc,
            }
        )

    return sorted(rows, key=lambda row: row["filingDate"], reverse=True)


def fetch_submissions_file_json(
    filename: str, session: requests.Session, limiter: RateLimiter
) -> Optional[dict[str, Any]]:
    url = SEC_SUBMISSIONS_FILE_URL.format(filename=filename)
    try:
        payload = json.loads(download(url, session, limiter).decode("utf-8"))
    except Exception as exc:  # pragma: no cover - defensive for offline runs
        print(f"warning: unable to fetch {url}: {exc}")
        return None
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        return None
    return payload_dict


def collect_filings(
    submissions: dict[str, Any],
    allowed_forms: set[str],
    session: requests.Session,
    limiter: RateLimiter,
    max_items: int,
) -> list[dict[str, str]]:
    filings = iter_recent_filings(submissions, allowed_forms)
    if max_items <= 0 or len(filings) >= max_items:
        return filings[:max_items] if max_items > 0 else filings

    seen = {row.get("accessionNumber", "") for row in filings}
    filings_root = as_str_dict(submissions.get("filings"))
    if filings_root is None:
        return filings[:max_items]
    files = as_list(filings_root.get("files")) or []
    for entry in files:
        entry_dict = as_str_dict(entry)
        if entry_dict is None:
            continue
        name = entry_dict.get("name")
        if not isinstance(name, str) or not name:
            continue
        payload = fetch_submissions_file_json(name, session, limiter)
        if payload is None:
            continue
        more = iter_recent_filings(payload, allowed_forms)
        for row in more:
            accession = row.get("accessionNumber", "")
            if not accession or accession in seen:
                continue
            seen.add(accession)
            filings.append(row)
        if len(filings) >= max_items:
            break

    return sorted(filings, key=lambda row: row["filingDate"], reverse=True)[:max_items]


def build_primary_doc_url(cik10: str, accession: str, primary_doc: str) -> str:
    cik_no_leading = str(int(cik10))
    acc_no_dashes = accession.replace("-", "")
    return f"{SEC_ARCHIVES_BASE}/{cik_no_leading}/{acc_no_dashes}/{primary_doc}"


def load_fixture_html(primary_doc: str) -> Optional[bytes]:
    fixture_path = FIXTURES_DIR / primary_doc
    if fixture_path.exists():
        return fixture_path.read_bytes()
    return None


def build_index_json_url(cik10: str, accession: str) -> str:
    cik_no_leading = str(int(cik10))
    acc_no_dashes = accession.replace("-", "")
    return f"{SEC_ARCHIVES_BASE}/{cik_no_leading}/{acc_no_dashes}/index.json"


def is_primary_doc_suspect(html_bytes: bytes) -> bool:
    return len(html_bytes) < MIN_PRIMARY_DOC_BYTES


def is_html_filename(name: str) -> bool:
    lowered = name.lower()
    return lowered.endswith(".htm") or lowered.endswith(".html")


def is_txt_filename(name: str) -> bool:
    return name.lower().endswith(".txt")


def parse_size(value: Any) -> Optional[int]:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


DOCUMENT_BLOCK = re.compile(r"<DOCUMENT>(.*?)</DOCUMENT>", re.IGNORECASE | re.DOTALL)
DOCUMENT_TYPE = re.compile(r"<TYPE>([^\\r\\n<]+)", re.IGNORECASE)
DOCUMENT_TEXT = re.compile(r"<TEXT>(.*?)</TEXT>", re.IGNORECASE | re.DOTALL)


def matches_allowed_form(doc_type: str, allowed_forms: set[str]) -> bool:
    normalized = doc_type.strip().upper()
    if normalized in allowed_forms:
        return True
    if normalized.endswith("/A") and normalized[:-2] in allowed_forms:
        return True
    return False


def extract_submission_text(html_bytes: bytes, allowed_forms: set[str]) -> Optional[str]:
    text = html_bytes.decode("utf-8", errors="replace")
    if "<DOCUMENT>" not in text.upper():
        return None
    for match in DOCUMENT_BLOCK.finditer(text):
        block = match.group(1)
        type_match = DOCUMENT_TYPE.search(block)
        if not type_match:
            continue
        doc_type = type_match.group(1)
        if not matches_allowed_form(doc_type, allowed_forms):
            continue
        text_match = DOCUMENT_TEXT.search(block)
        if not text_match:
            continue
        return text_match.group(1)
    return None


def load_index_json(
    cik10: str, accession: str, session: requests.Session, limiter: RateLimiter
) -> Optional[dict[str, Any]]:
    url = build_index_json_url(cik10, accession)
    try:
        payload = json.loads(download(url, session, limiter).decode("utf-8"))
    except Exception as exc:  # pragma: no cover - defensive for offline runs
        print(f"warning: unable to fetch {url}: {exc}")
        return None
    return cast(dict[str, Any], payload)


def select_alternate_document(
    payload: dict[str, Any], allowed_forms: set[str]
) -> Optional[str]:
    directory = as_str_dict(payload.get("directory"))
    if directory is None:
        return None
    items = as_list(directory.get("item"))
    if items is None:
        return None

    hinted_html: list[tuple[int, str]] = []
    hinted_txt: list[tuple[int, str]] = []
    any_html: list[tuple[int, str]] = []
    any_txt: list[tuple[int, str]] = []

    hints: list[str] = []
    for form in allowed_forms:
        normalized = form.lower()
        hints.append(normalized)
        hints.append(normalized.replace("-", ""))

    for raw in items:
        entry = as_str_dict(raw)
        if entry is None:
            continue
        name = entry.get("name")
        size = parse_size(entry.get("size"))
        if not isinstance(name, str):
            continue
        size_value = size if size is not None else 0
        if name.lower().startswith("index."):
            continue
        name_lower = name.lower()
        if (
            name_lower.startswith("index.")
            or "-index-headers" in name_lower
            or name_lower.endswith("-index.html")
            or name_lower.endswith("-index.htm")
        ):
            continue
        matches_hint = any(hint in name_lower for hint in hints)
        if is_html_filename(name):
            if matches_hint:
                hinted_html.append((size_value, name))
            else:
                any_html.append((size_value, name))
            continue
        if is_txt_filename(name):
            if matches_hint:
                hinted_txt.append((size_value, name))
            else:
                any_txt.append((size_value, name))

    if hinted_html:
        hinted_html.sort(reverse=True)
        return hinted_html[0][1]
    if any_html:
        any_html.sort(reverse=True)
        return any_html[0][1]
    if hinted_txt:
        hinted_txt.sort(reverse=True)
        return hinted_txt[0][1]
    if any_txt:
        any_txt.sort(reverse=True)
        return any_txt[0][1]
    return None


def maybe_fetch_alternate_html(
    cik10: str,
    accession: str,
    primary_doc: str,
    html_bytes: bytes,
    allowed_forms: set[str],
    session: requests.Session,
    limiter: RateLimiter,
    allow_live: bool,
) -> tuple[str, bytes, bool]:
    if not allow_live or not is_primary_doc_suspect(html_bytes):
        return primary_doc, html_bytes, False

    payload = load_index_json(cik10, accession, session, limiter)
    if payload is None:
        return primary_doc, html_bytes, False

    alternate_doc = select_alternate_document(payload, allowed_forms)
    if not alternate_doc or alternate_doc == primary_doc:
        return primary_doc, html_bytes, False

    alternate_bytes = load_fixture_html(alternate_doc)
    if alternate_bytes is None:
        alt_url = build_primary_doc_url(cik10, accession, alternate_doc)
        try:
            alternate_bytes = download(alt_url, session, limiter)
        except Exception as exc:  # pragma: no cover - defensive for offline runs
            print(f"warning: unable to fetch {alt_url}: {exc}")
            return primary_doc, html_bytes, False

    if len(alternate_bytes) <= len(html_bytes):
        return primary_doc, html_bytes, False

    print(
        f"warning: primary document {primary_doc} looks small ({len(html_bytes)} bytes), "
        f"using {alternate_doc} ({len(alternate_bytes)} bytes)"
    )
    return alternate_doc, alternate_bytes, True


def parse_year_from_date(value: str) -> Optional[int]:
    if not value:
        return None
    year_text = value[:4]
    if year_text.isdigit():
        return int(year_text)
    return None


def ensure_low_confidence(errors: list[str]) -> list[str]:
    if "low_confidence_item1a" not in errors:
        errors.append("low_confidence_item1a")
    return errors


def extract_item1a_from_html_bytes(
    html_bytes: bytes,
    extra_warnings: Optional[list[str]] = None,
) -> tuple[str, list[str], float, str, list[str], dict[str, Any]]:
    html_text = html_bytes.decode("utf-8", errors="replace")
    section, confidence, method, warnings, debug_meta = extract_item1a_from_html(html_text)
    warning_list = list(extra_warnings) if extra_warnings else []
    warning_list.extend(warnings)
    paragraphs = split_paragraphs(section) if section else []
    if confidence < 0.5 or not section.strip():
        return "", [], confidence, method, ensure_low_confidence(warning_list), debug_meta
    return section, paragraphs, confidence, method, warning_list, debug_meta


def build_missing_extraction() -> tuple[str, list[str], float, str, list[str], dict[str, Any]]:
    warnings = ensure_low_confidence(["html_missing"])
    return "", [], 0.0, "no_html", warnings, {"lengthChars": 0, "endMarkerUsed": None, "hasItem1C": False}


def build_quality_terms(value: Any) -> list[QualityShiftTerm]:
    items = as_list(value)
    if items is None:
        return []
    terms: list[QualityShiftTerm] = []
    for item in items:
        entry = as_str_dict(item)
        if entry is None:
            continue
        term_value = entry.get("term")
        score_value = entry.get("score")
        if not isinstance(term_value, str):
            continue
        if not isinstance(score_value, (int, float)):
            continue
        terms.append(QualityShiftTerm(term=term_value, score=float(score_value)))
    return terms


def build_quality_shifts(payload: ShiftsPayload) -> list[QualityShiftPair]:
    pairs = as_list(payload.get("yearPairs"))
    if pairs is None:
        return []
    output: list[QualityShiftPair] = []
    for item in pairs:
        entry = as_str_dict(item)
        if entry is None:
            continue
        from_year = entry.get("from")
        to_year = entry.get("to")
        if not isinstance(from_year, int) or not isinstance(to_year, int):
            continue
        top_risers = build_quality_terms(entry.get("topRisers"))
        top_fallers = build_quality_terms(entry.get("topFallers"))
        output.append(
            QualityShiftPair(
                from_year=from_year,
                to_year=to_year,
                top_risers=top_risers,
                top_fallers=top_fallers,
            )
        )
    return output


def build_forms_included(rows: list[dict[str, Any]]) -> list[str]:
    forms: list[str] = []
    for row in rows:
        form_value = row.get("form")
        if not isinstance(form_value, str):
            continue
        if form_value and form_value not in forms:
            forms.append(form_value)
    return forms


def choose_meta_extraction(
    current: Optional[dict[str, Any]], candidate: dict[str, Any]
) -> dict[str, Any]:
    if current is None:
        return candidate
    curr_conf = current.get("confidence")
    cand_conf = candidate.get("confidence")
    if isinstance(curr_conf, (int, float)) and isinstance(cand_conf, (int, float)):
        if cand_conf < curr_conf:
            return candidate
        if cand_conf > curr_conf:
            return current
    curr_warn = len(current.get("warnings") or [])
    cand_warn = len(candidate.get("warnings") or [])
    if cand_warn > curr_warn:
        return candidate
    curr_len = current.get("lengthChars")
    cand_len = candidate.get("lengthChars")
    if isinstance(curr_len, int) and isinstance(cand_len, int) and cand_len < curr_len:
        return candidate
    return current


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch SEC filings and build JSON outputs.")
    parser.add_argument("--ticker", required=True, help="Ticker symbol (e.g., AAPL).")
    parser.add_argument(
        "--years",
        type=int,
        default=10,
        help="Number of years to include (default: 10).",
    )
    parser.add_argument(
        "--out",
        default=str(Path.cwd()),
        help="Output folder for JSON artifacts.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of filings to process.",
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

    ticker = args.ticker.upper().strip()
    mapping = load_ticker_cik_map()
    if ticker not in mapping:
        mapping = load_ticker_cik_map(force_live=True)
    if ticker not in mapping:
        raise SystemExit(f"Ticker not found in mapping: {ticker}")

    cik10 = mapping[ticker]["cik"]
    session = requests.Session()
    limiter = RateLimiter(MAX_REQUESTS_PER_SECOND)

    submissions = fetch_submissions_json(cik10, session=session, limiter=limiter)
    company_name = resolve_company_name(mapping[ticker].get("name"), submissions.get("name"), ticker)
    allowed_forms = {"10-K"}
    if args.include_20f:
        allowed_forms.add("20-F")

    max_items = args.limit if args.limit is not None else args.years
    filings = collect_filings(submissions, allowed_forms, session, limiter, max_items)

    if not filings:
        if args.include_20f:
            raise SystemExit("No 10-K or 20-F filings found for ticker.")
        raise SystemExit("No 10-K filings found for ticker.")

    cache_dir = CACHE_DIR / ticker
    cache_dir.mkdir(parents=True, exist_ok=True)

    seen_years: set[int] = set()
    filings_out: list[dict[str, Any]] = []
    metrics_sections: list[MetricsSectionYear] = []
    quality_sections: list[QualitySectionYear] = []
    meta_extraction: Optional[dict[str, Any]] = None

    for filing in filings:
        report_date = filing.get("reportDate", "")
        filing_date = filing.get("filingDate", "")
        year = parse_year_from_date(report_date) or parse_year_from_date(filing_date)
        if year is None or year in seen_years:
            continue
        seen_years.add(year)

        accession = filing["accessionNumber"]
        primary_doc = filing["primaryDocument"]
        url = build_primary_doc_url(cik10, accession, primary_doc)
        html_bytes = load_fixture_html(primary_doc)
        from_fixture = html_bytes is not None
        if html_bytes is None:
            try:
                html_bytes = download(url, session, limiter)
            except Exception as exc:  # pragma: no cover - defensive for offline runs
                print(f"warning: unable to fetch {url}: {exc}")
                html_bytes = None

        if html_bytes is None:
            section_text, paragraphs, confidence, method, warnings, debug_meta = (
                build_missing_extraction()
            )
        else:
            allow_live = (not from_fixture) or is_primary_doc_suspect(html_bytes)
            primary_doc, html_bytes, alternate_used = maybe_fetch_alternate_html(
                cik10,
                accession,
                primary_doc,
                html_bytes,
                allowed_forms,
                session,
                limiter,
                allow_live=allow_live,
            )
            url = build_primary_doc_url(cik10, accession, primary_doc)
            raw_bytes = html_bytes
            submission_text = None
            if primary_doc.lower().endswith(".txt"):
                submission_text = extract_submission_text(raw_bytes, allowed_forms)
            if submission_text:
                html_bytes = submission_text.encode("utf-8")
            filename = (
                f"{accession.replace('-', '')}_{primary_doc}"
            )
            output_path = cache_dir / filename
            output_path.write_bytes(raw_bytes)
            print(f"saved: {output_path}")
            extra_warnings: list[str] = []
            if alternate_used:
                extra_warnings.append("alternate_primary_doc_used")
            if is_primary_doc_suspect(raw_bytes):
                extra_warnings.append("primary_doc_too_small")
            if submission_text:
                extra_warnings.append("submission_text_extracted")
            section_text, paragraphs, confidence, method, warnings, debug_meta = (
                extract_item1a_from_html_bytes(html_bytes, extra_warnings)
            )

        extraction_summary = {
            "section": "item1a",
            "method": method,
            "confidence": confidence,
            "warnings": warnings,
            "lengthChars": debug_meta.get("lengthChars"),
            "endMarkerUsed": debug_meta.get("endMarkerUsed"),
            "hasItem1C": debug_meta.get("hasItem1C"),
        }
        meta_extraction = choose_meta_extraction(meta_extraction, extraction_summary)

        filings_out.append(
            {
                "year": year,
                "form": filing.get("form", ""),
                "filingDate": filing_date,
                "reportDate": report_date,
                "accessionNumber": filing.get("accessionNumber", ""),
                "primaryDocument": primary_doc,
                "secUrl": url,
                "extraction": {
                    "confidence": confidence,
                    "method": method,
                    "errors": warnings,
                },
            }
        )

        metrics_sections.append(
            MetricsSectionYear(
                year=year,
                text=section_text,
                paragraphs=paragraphs,
                confidence=confidence,
            )
        )
        quality_sections.append(
            QualitySectionYear(
                year=year,
                paragraphs=paragraphs,
                confidence=confidence,
            )
        )

    metrics_sections.sort(key=lambda section: section.year)
    quality_sections.sort(key=lambda section: section.year)
    filings_out = sorted(filings_out, key=lambda row: row["year"])

    metrics, similarity, shifts = build_metrics(metrics_sections)
    quality_shifts = build_quality_shifts(shifts)
    excerpt_pairs = build_excerpt_pairs(quality_sections, quality_shifts)
    excerpts: dict[str, Any] = {"section": SECTION_NAME, "pairs": excerpt_pairs}

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    forms_included = build_forms_included(filings_out)
    meta_payload: dict[str, Any] = {
        "ticker": ticker,
        "cik": cik10,
        "companyName": company_name,
        "lastUpdatedUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        ),
        "formsIncluded": forms_included if forms_included else sorted(allowed_forms),
        "sectionsIncluded": [SECTION_NAME],
        "notes": META_NOTES,
    }
    if meta_extraction is not None:
        meta_payload["extraction"] = meta_extraction

    write_json(out_dir / "meta.json", meta_payload)
    write_json(out_dir / "filings.json", filings_out)
    write_json(out_dir / "metrics_10k_item1a.json", metrics)
    write_json(out_dir / "similarity_10k_item1a.json", similarity)
    write_json(out_dir / "shifts_10k_item1a.json", shifts)
    write_json(out_dir / "excerpts_10k_item1a.json", excerpts)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
