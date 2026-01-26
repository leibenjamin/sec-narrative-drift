import argparse
import json
import os
import re
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Protocol, Sequence, TYPE_CHECKING, TypedDict, cast
from urllib.parse import urlparse

class RequestsResponse(Protocol):
    status_code: int
    content: bytes

    def raise_for_status(self) -> None: ...

    def iter_content(self, chunk_size: int = ...) -> Iterable[bytes]: ...


class RequestsSession(Protocol):
    def get(
        self,
        url: str,
        headers: Optional[dict[str, str]] = ...,
        timeout: Optional[float] = ...,
        stream: bool = ...,
    ) -> RequestsResponse: ...


class RequestsModule(Protocol):
    Session: type[RequestsSession]
    Response: type[RequestsResponse]


class YamlModule(Protocol):
    def safe_load(self, stream: Any) -> Any: ...


if TYPE_CHECKING:
    requests: RequestsModule
    yaml: YamlModule
else:
    import requests
    import yaml

from sec_cache import (
    EXTRACTOR_VERSION,
    MAX_CACHE_GB,
    NORMALIZER_VERSION,
    atomic_write_json,
    compute_sha256_text,
    enforce_cache_size_limit,
    extraction_version_path,
    filing_html_path,
    filing_meta_path,
    filing_text_path,
    load_gz_text,
    load_json,
    risk_meta_path,
    risk_text_path,
    save_gz_text_atomic,
    ticker_year_index_path,
)
from sec_extract_item1a import (
    clean_html_to_text,
    extract_item1a_from_html,
    extract_item1a_from_text,
    split_paragraphs,
)
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
SEC_SUBMISSIONS_ZIP_URL = "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip"
SEC_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"
MAX_REQUESTS_PER_SECOND = 10
SECTION_NAME = "10k_item1a"
MIN_PRIMARY_DOC_BYTES = 10000
MIN_RISK_TOKENS = 400
MIN_RISK_UNIQUE = 150
ENCODING_REPLACEMENT_RATIO = 0.005
LENGTH_JUMP_RATIO = 0.5
DEFAULT_START_YEAR = 2015
TICKER_CIK_OVERRIDES = {
    "BLK": "0002012383",
}
TICKER_CIK_MERGE = {
    "BLK": ["0002012383", "0001364742"],
}
META_NOTES = [
    "Ticker/CIK mapping is SEC-provided and may be incomplete or outdated.",
    "Narrative Drift is descriptive; causal explanations are hypotheses.",
]

ROOT_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = ROOT_DIR / "sample_fixtures"
CACHE_DIR = ROOT_DIR / "_cache"
DEFAULT_SUBMISSIONS_ZIP = CACHE_DIR / "submissions.zip"
UNUSABLE_LIST_PATH = ROOT_DIR / "resources" / "risk_extraction_unusable.yml"


class ExtractionResult(TypedDict):
    section: str
    paragraphs: list[str]
    confidence: float
    method: str
    warnings: list[str]
    debug_meta: dict[str, Any]
    raw_section: str
    raw_paragraphs: list[str]


class TickerYearEntry(TypedDict):
    cik: str
    accession: str
    formType: str
    filingDate: str


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
        "Accept-Encoding": "gzip, deflate",
        "Host": host,
    }


def _looks_like_html(text: str) -> bool:
    lower = text.lower()
    if "<html" in lower or "<!doctype" in lower or "<xbrl" in lower or "<document" in lower:
        return True
    return text.count("<") >= 10 and text.count(">") >= 10


def decode_html_bytes(raw: bytes) -> tuple[str, list[str]]:
    try:
        return raw.decode("utf-8"), []
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
        replacement_count = text.count("\ufffd")
        if replacement_count == 0:
            return text, []
        ratio = replacement_count / max(len(text), 1)
        warnings: list[str] = []
        if ratio >= ENCODING_REPLACEMENT_RATIO:
            warnings.append("encoding_replacement_high")
            fallback = raw.decode("cp1252", errors="replace")
            if _looks_like_html(fallback) and not _looks_like_html(text):
                warnings.append("encoding_fallback_cp1252")
                return fallback, warnings
        else:
            warnings.append("encoding_replacement_low")
        return text, warnings


def download(url: str, session: RequestsSession, limiter: RateLimiter) -> bytes:
    last_response: Optional[RequestsResponse] = None
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


def download_to_file(
    url: str, session: RequestsSession, limiter: RateLimiter, path: Path
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    last_response: Optional[RequestsResponse] = None
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


def get_str(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    return None


def get_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    return None


def get_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def get_float(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def normalize_text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if text else None


def load_risk_extraction_unusable(path: Path) -> dict[str, set[int]]:
    if not path.exists():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    output: dict[str, set[int]] = {}
    for key, value in cast(dict[object, object], raw).items():
        if not isinstance(key, str):
            continue
        ticker = key.upper().strip()
        if not ticker:
            continue
        years: set[int] = set()
        if isinstance(value, list):
            for item in cast(list[object], value):
                if isinstance(item, int):
                    years.add(item)
                elif isinstance(item, str) and item.isdigit():
                    years.add(int(item))
        if years:
            output[ticker] = years
    return output


def is_unusable_ticker_year(
    ticker: str, year: int, unusable_map: dict[str, set[int]]
) -> bool:
    years = unusable_map.get(ticker.upper())
    if years is None:
        return False
    return year in years


def build_unusable_reason(ticker: str, year: int) -> str:
    if ticker.upper() == "JNJ" and year == 2015:
        return (
            "JNJ 2015 uses Exhibit 99-style cautionary note; not comparable to Item 1A risk section."
        )
    return "Marked unusable for comparability by risk_extraction_unusable.yml."


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
        apply_cik_overrides(mapping)
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
        apply_cik_overrides(mapping)
        return mapping

    raise RuntimeError("Unexpected ticker map format")


def apply_cik_overrides(mapping: dict[str, dict[str, str]]) -> None:
    for ticker, cik in TICKER_CIK_OVERRIDES.items():
        entry = mapping.get(ticker)
        if entry is None:
            mapping[ticker] = {"cik": cik, "name": ticker, "exchange": ""}
            continue
        entry["cik"] = cik


def get_cik_candidates(ticker: str, primary_cik: str) -> list[str]:
    merged = TICKER_CIK_MERGE.get(ticker, [])
    candidates = list(merged) if merged else [primary_cik]
    if primary_cik not in candidates:
        candidates.insert(0, primary_cik)
    seen: set[str] = set()
    ordered: list[str] = []
    for cik in candidates:
        if cik in seen:
            continue
        seen.add(cik)
        ordered.append(cik)
    return ordered


def load_json_from_zip(zip_path: Path, filename: str) -> Optional[dict[str, Any]]:
    if not zip_path.exists():
        return None
    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            try:
                raw = archive.read(filename)
            except KeyError:
                return None
    except (OSError, zipfile.BadZipFile):
        return None
    try:
        payload = json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None
    payload_dict = as_str_dict(payload)
    if payload_dict is None:
        return None
    return payload_dict


def load_submissions_from_zip(zip_path: Path, cik10: str) -> Optional[dict[str, Any]]:
    return load_json_from_zip(zip_path, f"CIK{cik10}.json")


def fetch_submissions_json(
    cik10: str,
    session: Optional[RequestsSession] = None,
    limiter: Optional[RateLimiter] = None,
    submissions_zip: Optional[Path] = None,
    allow_fixture: bool = True,
) -> dict[str, Any]:
    fixture_path = FIXTURES_DIR / f"CIK{cik10}.json"
    if allow_fixture and fixture_path.exists():
        return load_fixture_json(fixture_path)

    if submissions_zip:
        zip_payload = load_submissions_from_zip(submissions_zip, cik10)
        if zip_payload is not None:
            return zip_payload

    session = session or requests.Session()
    limiter = limiter or RateLimiter(MAX_REQUESTS_PER_SECOND)
    url = SEC_SUBMISSIONS_URL.format(cik10=cik10)
    return json.loads(download(url, session, limiter).decode("utf-8"))


def get_filings_table(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    filings = as_str_dict(payload.get("filings"))
    if filings is not None:
        recent = as_str_dict(filings.get("recent"))
        if recent is not None:
            return recent

    if isinstance(payload.get("form"), list):
        return payload

    return None


def iter_recent_filings(
    submissions: dict[str, Any],
    allowed_forms: set[str],
    cik10: str,
) -> list[dict[str, str]]:
    table = get_filings_table(submissions)
    if table is None:
        return []
    forms = as_list(table.get("form")) or []
    filing_dates = as_list(table.get("filingDate")) or []
    report_dates = as_list(table.get("reportDate")) or []
    accession_numbers = as_list(table.get("accessionNumber")) or []
    primary_docs = as_list(table.get("primaryDocument")) or []

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
                "cik": cik10,
                "form": form,
                "filingDate": filing_date,
                "reportDate": report_date,
                "accessionNumber": accession,
                "primaryDocument": primary_doc,
            }
        )

    return sorted(rows, key=lambda row: row["filingDate"], reverse=True)


def fetch_submissions_file_json(
    filename: str,
    session: RequestsSession,
    limiter: RateLimiter,
    submissions_zip: Optional[Path] = None,
) -> Optional[dict[str, Any]]:
    if submissions_zip:
        zip_payload = load_json_from_zip(submissions_zip, filename)
        if zip_payload is not None:
            return zip_payload
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
    session: RequestsSession,
    limiter: RateLimiter,
    max_items: int,
    submissions_zip: Optional[Path] = None,
    cik10: str = "",
) -> list[dict[str, str]]:
    filings = iter_recent_filings(submissions, allowed_forms, cik10)
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
        payload = fetch_submissions_file_json(name, session, limiter, submissions_zip)
        if payload is None:
            continue
        more = iter_recent_filings(payload, allowed_forms, cik10)
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


def load_fixture_html(primary_doc: str, allow_sample: bool) -> Optional[bytes]:
    if not allow_sample:
        return None
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


def dedupe_filings(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for row in rows:
        accession = row.get("accessionNumber", "")
        if not accession:
            continue
        cik = row.get("cik", "")
        key = f"{cik}:{accession}" if cik else accession
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def extract_submission_text(
    html_bytes: bytes,
    allowed_forms: set[str],
    decode_warnings: Optional[list[str]] = None,
) -> Optional[str]:
    text, warnings = decode_html_bytes(html_bytes)
    if decode_warnings is not None:
        for warning in warnings:
            add_warning(decode_warnings, warning)
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
    cik10: str, accession: str, session: RequestsSession, limiter: RateLimiter
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


def select_exhibit_99_document(payload: dict[str, Any]) -> Optional[str]:
    directory = as_str_dict(payload.get("directory"))
    if directory is None:
        return None
    items = as_list(directory.get("item"))
    if items is None:
        return None

    candidates: list[tuple[int, int, str]] = []
    for entry in items:
        entry_dict = as_str_dict(entry)
        if entry_dict is None:
            continue
        name = get_str(entry_dict.get("name"))
        if not name:
            continue
        doc_type = get_str(entry_dict.get("type")) or ""
        size = parse_size(entry_dict.get("size")) or 0
        lower_name = name.lower()
        score = 0
        if doc_type.upper().startswith("EX-99"):
            score += 3
        if re.search(r"ex-?99", lower_name):
            score += 1
        if re.search(r"\br99\b", lower_name) or lower_name.startswith("r99"):
            score += 2
        if "risk" in lower_name or "factor" in lower_name:
            score += 2
        if score <= 0:
            continue
        candidates.append((score, size, name))

    if candidates:
        candidates.sort(key=lambda item: (-item[0], -item[1]))
        return candidates[0][2]
    return None


def fetch_exhibit_99_text(
    cik10: str,
    accession: str,
    session: RequestsSession,
    limiter: RateLimiter,
    decode_warnings: Optional[list[str]] = None,
) -> Optional[str]:
    payload = load_index_json(cik10, accession, session, limiter)
    if payload is None:
        return None
    exhibit_name = select_exhibit_99_document(payload)
    if exhibit_name is None:
        return None
    url = build_primary_doc_url(cik10, accession, exhibit_name)
    try:
        raw_bytes = download(url, session, limiter)
    except Exception as exc:  # pragma: no cover - defensive for offline runs
        print(f"warning: unable to fetch {url}: {exc}")
        return None
    if is_txt_filename(exhibit_name):
        extracted = extract_submission_text(
            raw_bytes,
            {"EX-99", "EX-99.1", "EX-99.2", "EX-99.3"},
            decode_warnings=decode_warnings,
        )
        if extracted:
            return extracted
    text, warnings = decode_html_bytes(raw_bytes)
    if decode_warnings is not None:
        for warning in warnings:
            add_warning(decode_warnings, warning)
    return text


def maybe_fetch_alternate_html(
    cik10: str,
    accession: str,
    primary_doc: str,
    html_bytes: bytes,
    allowed_forms: set[str],
    session: RequestsSession,
    limiter: RateLimiter,
    allow_live: bool,
    allow_sample_fixtures: bool,
    force_alternate: bool,
) -> tuple[str, bytes, bool]:
    if not allow_live:
        return primary_doc, html_bytes, False
    if not force_alternate and not is_primary_doc_suspect(html_bytes):
        return primary_doc, html_bytes, False

    payload = load_index_json(cik10, accession, session, limiter)
    if payload is None:
        return primary_doc, html_bytes, False

    alternate_doc = select_alternate_document(payload, allowed_forms)
    if not alternate_doc or alternate_doc == primary_doc:
        return primary_doc, html_bytes, False

    alternate_bytes = load_fixture_html(alternate_doc, allow_sample_fixtures)
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


def parse_month_from_date(value: str) -> Optional[int]:
    if len(value) >= 7 and value[4] == "-":
        month_text = value[5:7]
    elif len(value) >= 6 and value[:6].isdigit():
        month_text = value[4:6]
    else:
        return None
    if not month_text.isdigit():
        return None
    return int(month_text)

def parse_day_from_date(value: str) -> Optional[int]:
    if len(value) >= 10 and value[4] == "-" and value[7] == "-":
        day_text = value[8:10]
    elif len(value) >= 8 and value[:8].isdigit():
        day_text = value[6:8]
    else:
        return None
    if not day_text.isdigit():
        return None
    return int(day_text)


def should_backshift_year(report_date: str) -> bool:
    report_month = parse_month_from_date(report_date)
    report_day = parse_day_from_date(report_date)
    return report_month == 1 and report_day is not None and report_day <= 10


def derive_filing_year(
    report_date: str,
    filing_date: str,
    seen_years: set[int],
) -> Optional[int]:
    report_year = parse_year_from_date(report_date)
    filing_year = parse_year_from_date(filing_date)
    year = report_year or filing_year
    if year is None:
        return None
    if report_year is not None and should_backshift_year(report_date):
        adjusted = year - 1
        if adjusted not in seen_years:
            return adjusted
    if report_year is None:
        filing_month = parse_month_from_date(filing_date)
        if filing_month is not None and filing_month <= 2:
            adjusted = year - 1
            if adjusted not in seen_years:
                return adjusted
    if year not in seen_years:
        return year
    if report_year is not None and should_backshift_year(report_date):
        adjusted = year - 1
        if adjusted not in seen_years:
            return adjusted
    if filing_year is not None and filing_year not in seen_years:
        return filing_year
    return None


def ensure_low_confidence(errors: list[str]) -> list[str]:
    if "low_confidence_item1a" not in errors:
        errors.append("low_confidence_item1a")
    return errors


def extract_item1a_from_html_bytes(
    html_bytes: bytes,
    extra_warnings: Optional[list[str]] = None,
) -> ExtractionResult:
    html_text = html_bytes.decode("utf-8", errors="replace")
    raw_section, confidence, method, warnings, debug_meta = extract_item1a_from_html(html_text)
    warning_list = list(extra_warnings) if extra_warnings else []
    warning_list.extend(warnings)
    raw_paragraphs = split_paragraphs(raw_section) if raw_section else []
    debug_gate_failed = get_bool(debug_meta.get("qualityGateFailed")) or False
    if debug_gate_failed or not raw_section.strip():
        return {
            "section": "",
            "paragraphs": [],
            "confidence": confidence,
            "method": method,
            "warnings": ensure_low_confidence(warning_list),
            "debug_meta": debug_meta,
            "raw_section": raw_section,
            "raw_paragraphs": raw_paragraphs,
        }
    if confidence < 0.5:
        warning_list = ensure_low_confidence(warning_list)
    return {
        "section": raw_section,
        "paragraphs": raw_paragraphs,
        "confidence": confidence,
        "method": method,
        "warnings": warning_list,
        "debug_meta": debug_meta,
        "raw_section": raw_section,
        "raw_paragraphs": raw_paragraphs,
    }


def extract_item1a_from_text_only(
    text: str,
    extra_warnings: Optional[list[str]] = None,
) -> ExtractionResult:
    raw_section, confidence, method, warnings, debug_meta = extract_item1a_from_text(text)
    warning_list = list(extra_warnings) if extra_warnings else []
    warning_list.extend(warnings)
    raw_paragraphs = split_paragraphs(raw_section) if raw_section else []
    debug_gate_failed = get_bool(debug_meta.get("qualityGateFailed")) or False
    if debug_gate_failed or not raw_section.strip():
        return {
            "section": "",
            "paragraphs": [],
            "confidence": confidence,
            "method": method,
            "warnings": ensure_low_confidence(warning_list),
            "debug_meta": debug_meta,
            "raw_section": raw_section,
            "raw_paragraphs": raw_paragraphs,
        }
    if confidence < 0.5:
        warning_list = ensure_low_confidence(warning_list)
    return {
        "section": raw_section,
        "paragraphs": raw_paragraphs,
        "confidence": confidence,
        "method": method,
        "warnings": warning_list,
        "debug_meta": debug_meta,
        "raw_section": raw_section,
        "raw_paragraphs": raw_paragraphs,
    }


def build_missing_extraction() -> ExtractionResult:
    warnings = ensure_low_confidence(["html_missing"])
    return {
        "section": "",
        "paragraphs": [],
        "confidence": 0.0,
        "method": "no_html",
        "warnings": warnings,
        "debug_meta": {"lengthChars": 0, "endMarkerUsed": None, "hasItem1C": False},
        "raw_section": "",
        "raw_paragraphs": [],
    }


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
        if cand_conf > curr_conf:
            return candidate
        if cand_conf < curr_conf:
            return current
    curr_warn = len(current.get("warnings") or [])
    cand_warn = len(candidate.get("warnings") or [])
    if cand_warn < curr_warn:
        return candidate
    curr_len = current.get("lengthChars")
    cand_len = candidate.get("lengthChars")
    if isinstance(curr_len, int) and isinstance(cand_len, int) and cand_len > curr_len:
        return candidate
    return current


WORD_PATTERN = re.compile(r"[A-Za-z0-9]+")


def count_tokens(text: str) -> tuple[int, int]:
    tokens = WORD_PATTERN.findall(text.lower())
    unique = len(set(tokens))
    return len(tokens), unique


def count_paragraphs(text: str) -> int:
    chunks = [chunk for chunk in re.split(r"\n{2,}", text) if chunk.strip()]
    return len(chunks)


def add_warning(warnings: list[str], value: str) -> None:
    if value not in warnings:
        warnings.append(value)


def parse_cache_max(value: Optional[str], default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def parse_ticker_year_index(raw: Any) -> dict[str, dict[str, TickerYearEntry]]:
    payload = as_str_dict(raw)
    if payload is None:
        return {}
    output: dict[str, dict[str, TickerYearEntry]] = {}
    for ticker_key, value in payload.items():
        year_map = as_str_dict(value)
        if year_map is None:
            continue
        parsed_years: dict[str, TickerYearEntry] = {}
        for year_key, entry_value in year_map.items():
            entry = as_str_dict(entry_value)
            if entry is None:
                continue
            cik = get_str(entry.get("cik"))
            accession = get_str(entry.get("accession"))
            form_type = get_str(entry.get("formType"))
            filing_date = get_str(entry.get("filingDate"))
            if cik is None or accession is None or form_type is None or filing_date is None:
                continue
            parsed_years[year_key] = {
                "cik": cik,
                "accession": accession,
                "formType": form_type,
                "filingDate": filing_date,
            }
        if parsed_years:
            output[ticker_key] = parsed_years
    return output


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch SEC filings and build JSON outputs.")
    parser.add_argument("--ticker", required=True, help="Ticker symbol (e.g., AAPL).")
    parser.add_argument(
        "--years",
        type=int,
        default=None,
        help="Number of years to include (default: cover years since --start-year).",
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=DEFAULT_START_YEAR,
        help=f"Minimum fiscal year to include (default: {DEFAULT_START_YEAR}).",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output folder for JSON artifacts (default: public/data/sec_narrative_drift/<ticker>).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of filings to process.",
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
    parser.add_argument(
        "--cache-debug-html",
        action="store_true",
        help="Store filing HTML in the local cache for debugging.",
    )
    parser.add_argument(
        "--force-html-cache",
        action="store_true",
        help="Fetch/store filing HTML even if normalized text is already cached.",
    )
    parser.add_argument(
        "--force-alternate-doc",
        action="store_true",
        help="Try an alternate primary document even if the current one is not suspect.",
    )
    parser.add_argument(
        "--cache-max-gb",
        type=float,
        default=None,
        help="Maximum cache size in GB before pruning optional artifacts.",
    )
    parser.add_argument(
        "--force-live-submissions",
        action="store_true",
        help="Bypass local CIK submissions fixtures for this run.",
    )
    parser.add_argument(
        "--allow-sample-fixtures",
        action="store_true",
        help="Allow use of scripts/sample_fixtures for submissions and filings.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    ticker = args.ticker.upper().strip()
    default_out_dir = (
        Path(__file__).resolve().parents[1]
        / "public"
        / "data"
        / "sec_narrative_drift"
        / ticker
    )
    out_dir = Path(args.out) if args.out else default_out_dir
    mapping = load_ticker_cik_map()
    if ticker not in mapping:
        mapping = load_ticker_cik_map(force_live=True)
    if ticker not in mapping:
        raise SystemExit(f"Ticker not found in mapping: {ticker}")

    primary_cik = mapping[ticker]["cik"]
    session = requests.Session()
    limiter = RateLimiter(MAX_REQUESTS_PER_SECOND)

    submissions_zip: Optional[Path] = None
    if args.submissions_zip:
        submissions_zip = Path(args.submissions_zip)
    if args.download_submissions_zip:
        target = submissions_zip or DEFAULT_SUBMISSIONS_ZIP
        print(f"downloading submissions zip to {target}")
        download_to_file(SEC_SUBMISSIONS_ZIP_URL, session, limiter, target)
        submissions_zip = target
    if submissions_zip is not None and not submissions_zip.exists():
        print(
            f"warning: submissions zip not found at {submissions_zip}; "
            "falling back to live submissions API"
        )
        submissions_zip = None

    allow_sample_fixtures = bool(args.allow_sample_fixtures)
    allow_fixture = allow_sample_fixtures and not args.force_live_submissions
    submissions_primary = fetch_submissions_json(
        primary_cik,
        session=session,
        limiter=limiter,
        submissions_zip=submissions_zip,
        allow_fixture=allow_fixture,
    )
    company_name = resolve_company_name(
        mapping[ticker].get("name"), submissions_primary.get("name"), ticker
    )
    allowed_forms = {"10-K"}
    if args.include_20f:
        allowed_forms.add("20-F")

    start_year = args.start_year if args.start_year and args.start_year > 0 else None
    if args.years is None:
        current_year = datetime.now(timezone.utc).year
        if start_year is not None:
            years = max(current_year - start_year + 1, 1)
        else:
            years = 10
    else:
        years = args.years

    max_items = args.limit if args.limit is not None else years
    cik_candidates = get_cik_candidates(ticker, primary_cik)
    submissions_by_cik: dict[str, dict[str, Any]] = {primary_cik: submissions_primary}
    filings_all: list[dict[str, str]] = []
    for cik10 in cik_candidates:
        submissions = submissions_by_cik.get(cik10)
        if submissions is None:
            submissions = fetch_submissions_json(
                cik10,
                session=session,
                limiter=limiter,
                submissions_zip=submissions_zip,
                allow_fixture=allow_fixture,
            )
            submissions_by_cik[cik10] = submissions
        filings_all.extend(
            collect_filings(
                submissions,
                allowed_forms,
                session,
                limiter,
                max_items,
                submissions_zip=submissions_zip,
                cik10=cik10,
            )
        )

    filings = sorted(
        dedupe_filings(filings_all), key=lambda row: row.get("filingDate", ""), reverse=True
    )
    if max_items > 0:
        filings = filings[:max_items]

    if not filings:
        if args.include_20f:
            raise SystemExit("No 10-K or 20-F filings found for ticker.")
        raise SystemExit("No 10-K filings found for ticker.")

    cache_debug_html = args.cache_debug_html
    force_html_cache = args.force_html_cache
    force_alternate_doc = args.force_alternate_doc
    cache_max_gb = (
        args.cache_max_gb
        if args.cache_max_gb is not None
        else parse_cache_max(os.environ.get("SEC_CACHE_MAX_GB"), float(MAX_CACHE_GB))
    )
    run_timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
    unusable_map = load_risk_extraction_unusable(UNUSABLE_LIST_PATH)

    seen_years: set[int] = set()
    filings_out: list[dict[str, Any]] = []
    metrics_sections: list[MetricsSectionYear] = []
    quality_sections: list[QualitySectionYear] = []
    ticker_year_entries: dict[str, TickerYearEntry] = {}
    meta_extraction: Optional[dict[str, Any]] = None

    for filing in filings:
        report_date = filing.get("reportDate", "")
        filing_date = filing.get("filingDate", "")
        year = derive_filing_year(report_date, filing_date, seen_years)
        if year is None:
            continue
        if start_year is not None and year < start_year:
            continue
        seen_years.add(year)

        filing_cik = filing.get("cik", primary_cik)
        if not filing_cik:
            filing_cik = primary_cik
        accession = filing["accessionNumber"]
        form_type = filing.get("form", "")
        primary_doc = filing["primaryDocument"]
        url = build_primary_doc_url(filing_cik, accession, primary_doc)

        extra_warnings: list[str] = []
        decode_warnings: list[str] = []
        html_text: Optional[str] = None
        filing_text: Optional[str] = None
        filing_source = "unknown"
        section_text = ""
        paragraphs: list[str] = []
        confidence = 0.0
        method = "missing"
        warnings: list[str] = []
        raw_section = ""
        raw_paragraphs: list[str] = []
        included_in_metrics = False
        end_marker_value: Optional[str] = None
        start_marker_value: Optional[str] = None
        has_item1c = False
        toc_detected = False
        toc_removed = False
        risk_token_count = 0
        risk_unique = 0
        risk_paragraph_count = 0
        quality_gate_failed = False
        unusable_override = is_unusable_ticker_year(ticker, year, unusable_map)
        unusable_reason = build_unusable_reason(ticker, year) if unusable_override else ""

        cached_filing_meta = as_str_dict(load_json(filing_meta_path(filing_cik, accession)))
        cached_normalizer = (
            get_str(cached_filing_meta.get("normalizerVersion")) if cached_filing_meta else None
        )
        cached_text: Optional[str] = None
        if cached_normalizer == NORMALIZER_VERSION:
            cached_text = load_gz_text(filing_text_path(filing_cik, accession))

        cached_html = load_gz_text(filing_html_path(filing_cik, accession))
        if cached_html is not None:
            html_text = cached_html
            filing_text = clean_html_to_text(html_text)
            filing_source = "cache_html"
        elif not force_html_cache and cached_text is not None:
            filing_text = cached_text
            filing_source = "cache_text"

        if filing_text is None:
            html_bytes = load_fixture_html(primary_doc, allow_sample_fixtures)
            from_fixture = html_bytes is not None
            if html_bytes is None:
                try:
                    html_bytes = download(url, session, limiter)
                except Exception as exc:  # pragma: no cover - defensive for offline runs
                    print(f"warning: unable to fetch {url}: {exc}")
                    html_bytes = None

            if html_bytes is not None:
                allow_live = (not from_fixture) or is_primary_doc_suspect(html_bytes)
                primary_doc, html_bytes, alternate_used = maybe_fetch_alternate_html(
                    filing_cik,
                    accession,
                    primary_doc,
                    html_bytes,
                    allowed_forms,
                    session,
                    limiter,
                    allow_live=allow_live,
                    allow_sample_fixtures=allow_sample_fixtures,
                    force_alternate=force_alternate_doc,
                )
                url = build_primary_doc_url(filing_cik, accession, primary_doc)
                raw_bytes = html_bytes
                submission_text = None
                if primary_doc.lower().endswith(".txt"):
                    submission_text = extract_submission_text(
                        raw_bytes,
                        allowed_forms,
                        decode_warnings=decode_warnings,
                    )
                if alternate_used:
                    extra_warnings.append("alternate_primary_doc_used")
                if is_primary_doc_suspect(raw_bytes):
                    extra_warnings.append("primary_doc_too_small")
                if submission_text:
                    extra_warnings.append("submission_text_extracted")
                    html_text = submission_text
                else:
                    html_text, decode_notes = decode_html_bytes(raw_bytes)
                    for warning in decode_notes:
                        add_warning(decode_warnings, warning)
                if decode_warnings:
                    for warning in decode_warnings:
                        add_warning(extra_warnings, warning)
                filing_text = clean_html_to_text(html_text)
                filing_source = "fixture" if from_fixture else "download"
            else:
                if cached_text is not None:
                    filing_text = cached_text
                    filing_source = "cache_text_fallback"
                else:
                    filing_text = ""
                    filing_source = "missing_html"

        cached_filing_extractor = (
            get_str(cached_filing_meta.get("extractorVersion")) if cached_filing_meta else None
        )
        write_filing_cache = bool(filing_text.strip())
        if (
            filing_source == "cache_text"
            and cached_filing_meta is not None
            and cached_filing_extractor == EXTRACTOR_VERSION
        ):
            write_filing_cache = False
        if write_filing_cache:
            filing_token_count, filing_unique = count_tokens(filing_text)
            filing_paragraph_count = count_paragraphs(filing_text)
            filing_meta_payload: dict[str, Any] = {
                "cik": filing_cik,
                "accessionNumber": accession,
                "formType": form_type,
                "primaryDocument": primary_doc,
                "filingDate": filing_date,
                "reportDate": report_date,
                "secUrl": url,
                "extractorVersion": EXTRACTOR_VERSION,
                "normalizerVersion": NORMALIZER_VERSION,
                "source": filing_source,
                "charCount": len(filing_text),
                "tokenCount": filing_token_count,
                "uniqueTokens": filing_unique,
                "paragraphCount": filing_paragraph_count,
                "textBytes": len(filing_text.encode("utf-8")),
                "sha256FilingText": compute_sha256_text(filing_text),
                "generatedAtUtc": run_timestamp,
            }
            if decode_warnings:
                filing_meta_payload["decodeWarnings"] = decode_warnings
            save_gz_text_atomic(filing_text_path(filing_cik, accession), filing_text)
            atomic_write_json(filing_meta_path(filing_cik, accession), filing_meta_payload)

        cached_risk_meta = as_str_dict(load_json(risk_meta_path(filing_cik, accession)))
        cached_risk_ok = False
        if not unusable_override and cached_risk_meta is not None:
            cached_extractor = get_str(cached_risk_meta.get("extractorVersion"))
            if cached_extractor == EXTRACTOR_VERSION:
                cached_risk_text = load_gz_text(risk_text_path(filing_cik, accession, form_type))
                if cached_risk_text is not None:
                    cached_risk_ok = True
                    raw_section = cached_risk_text
                    raw_paragraphs = split_paragraphs(raw_section) if raw_section else []
                    confidence = get_float(cached_risk_meta.get("confidence")) or 0.0
                    method = get_str(cached_risk_meta.get("method")) or "cached"
                    warnings = as_str_list(cached_risk_meta.get("warnings")) or []
                    included_in_metrics_value = get_bool(cached_risk_meta.get("includedInMetrics"))
                    included_in_metrics = (
                        included_in_metrics_value
                        if included_in_metrics_value is not None
                        else True
                    )
                    section_text = raw_section if included_in_metrics else ""
                    paragraphs = raw_paragraphs if included_in_metrics else []
                    end_marker_value = get_str(cached_risk_meta.get("endMarker"))
                    start_marker_value = get_str(cached_risk_meta.get("startMarker"))
                    has_item1c = get_bool(cached_risk_meta.get("hasItem1C")) or False
                    toc_detected = get_bool(cached_risk_meta.get("tocDetected")) or False
                    toc_removed = get_bool(cached_risk_meta.get("tocRemoved")) or False
                    token_value = get_int(cached_risk_meta.get("tokenCount"))
                    unique_value = get_int(cached_risk_meta.get("uniqueTokens"))
                    paragraph_value = get_int(cached_risk_meta.get("paragraphCount"))
                    tokens, uniques = count_tokens(raw_section)
                    risk_token_count = token_value if token_value is not None else tokens
                    risk_unique = unique_value if unique_value is not None else uniques
                    risk_paragraph_count = (
                        paragraph_value if paragraph_value is not None else len(raw_paragraphs)
                    )
                    quality_gate_failed = get_bool(cached_risk_meta.get("qualityGateFailed")) or False

        if unusable_override:
            warnings = ["unusable_incomparable_format"]
            confidence = 0.0
            method = "unusable_override"
            raw_section = ""
            raw_paragraphs = []
            section_text = ""
            paragraphs = []
            included_in_metrics = False
            quality_gate_failed = True
            risk_token_count = 0
            risk_unique = 0
            risk_paragraph_count = 0
            end_marker_value = None
            start_marker_value = None
            has_item1c = False
            toc_detected = False
            toc_removed = False

            risk_section_label = "item_3d" if form_type.upper().startswith("20-F") else "item_1a"
            risk_meta_payload: dict[str, Any] = {
                "cik": filing_cik,
                "accessionNumber": accession,
                "formType": form_type,
                "filingDate": filing_date,
                "reportDate": report_date,
                "secUrl": url,
                "section": risk_section_label,
                "extractorVersion": EXTRACTOR_VERSION,
                "normalizerVersion": NORMALIZER_VERSION,
                "confidence": confidence,
                "method": method,
                "warnings": warnings,
                "status": "UNUSABLE",
                "gateReasons": ["unusable_incomparable_format"],
                "unusableReason": unusable_reason,
                "startMarker": start_marker_value,
                "endMarker": end_marker_value,
                "tocDetected": toc_detected,
                "tocRemoved": toc_removed,
                "charCount": len(raw_section),
                "tokenCount": risk_token_count,
                "uniqueTokens": risk_unique,
                "paragraphCount": risk_paragraph_count,
                "sha256RiskText": "",
                "includedInMetrics": included_in_metrics,
                "qualityGateFailed": quality_gate_failed,
                "hasItem1C": has_item1c,
                "generatedAtUtc": run_timestamp,
                "debug": {},
            }
            save_gz_text_atomic(risk_text_path(filing_cik, accession, form_type), raw_section)
            atomic_write_json(risk_meta_path(filing_cik, accession), risk_meta_payload)
        elif not cached_risk_ok:
            if html_text is not None:
                extraction = extract_item1a_from_html_bytes(
                    html_text.encode("utf-8"), extra_warnings
                )
            elif filing_text:
                extraction = extract_item1a_from_text_only(filing_text, extra_warnings)
            else:
                extraction = build_missing_extraction()

            section_text = extraction["section"]
            paragraphs = extraction["paragraphs"]
            confidence = extraction["confidence"]
            method = extraction["method"]
            warnings = list(extraction["warnings"])
            debug_meta = extraction["debug_meta"]
            raw_section = extraction["raw_section"]
            raw_paragraphs = extraction["raw_paragraphs"]

            end_marker_value = get_str(debug_meta.get("endMarkerUsed"))
            start_marker_value = get_str(debug_meta.get("startMarker"))
            has_item1c = get_bool(debug_meta.get("hasItem1C")) or False
            toc_detected = get_bool(debug_meta.get("tocDetected")) or False
            toc_removed = get_bool(debug_meta.get("tocRemoved")) or False
            debug_gate_failed = get_bool(debug_meta.get("qualityGateFailed")) or False
            status_value = get_str(debug_meta.get("status"))
            gate_reasons = as_str_list(debug_meta.get("gateReasons")) or []
            start_snippet = get_str(debug_meta.get("startSnippet"))
            end_snippet = get_str(debug_meta.get("endSnippet"))
            first_lines = as_str_list(debug_meta.get("firstLines")) or []
            last_lines = as_str_list(debug_meta.get("lastLines")) or []
            candidate_count = get_int(debug_meta.get("candidateCount"))
            top_candidates = as_list(debug_meta.get("topCandidates"))

            risk_token_count, risk_unique = count_tokens(raw_section)
            risk_paragraph_count = len(raw_paragraphs)

            exhibit_99_reference = "exhibit 99" in raw_section.lower()
            if (
                risk_token_count < MIN_RISK_TOKENS
                and raw_section
                and exhibit_99_reference
            ):
                exhibit_text = fetch_exhibit_99_text(
                    filing_cik,
                    accession,
                    session,
                    limiter,
                    decode_warnings=decode_warnings,
                )
                if decode_warnings:
                    for warning in decode_warnings:
                        add_warning(warnings, warning)
                if exhibit_text:
                    exhibit_section, _conf, _method, _warn, _debug = extract_item1a_from_html(
                        exhibit_text
                    )
                    fallback_section: Optional[str] = None
                    min_len = max(len(raw_section), 2000)
                    if exhibit_section and len(exhibit_section) >= min_len:
                        fallback_section = exhibit_section
                    else:
                        cleaned = clean_html_to_text(exhibit_text)
                        if "risk factors" in cleaned.lower() and len(cleaned) >= min_len:
                            fallback_section = cleaned
                    if fallback_section:
                        raw_section = fallback_section
                        section_text = fallback_section
                        raw_paragraphs = split_paragraphs(raw_section)
                        paragraphs = list(raw_paragraphs)
                        warnings.append("exhibit_99_fallback")
                        debug_meta["exhibit99Fallback"] = True
                        confidence = min(confidence, 0.6)
                        risk_token_count, risk_unique = count_tokens(raw_section)
                        risk_paragraph_count = len(raw_paragraphs)
                add_warning(warnings, "exhibit_99_reference")

            short_risk_allowed = (
                exhibit_99_reference
                and end_marker_value in {"1B", "1C", "2"}
                and not debug_gate_failed
            )

            quality_gate_failed = debug_gate_failed
            if risk_token_count < MIN_RISK_TOKENS:
                add_warning(warnings, "risk_too_short")
                if not short_risk_allowed:
                    quality_gate_failed = True
            if risk_unique < MIN_RISK_UNIQUE:
                add_warning(warnings, "risk_low_unique")
                if not short_risk_allowed:
                    quality_gate_failed = True
            if toc_detected and not toc_removed:
                add_warning(warnings, "toc_detected")
            if not raw_section.strip():
                quality_gate_failed = True

            if quality_gate_failed:
                add_warning(warnings, "quality_gate_failed")
                warnings = ensure_low_confidence(warnings)
                section_text = ""
                paragraphs = []
                confidence = min(confidence, 0.25)

            included_in_metrics = bool(section_text)

            risk_section_label = "item_3d" if form_type.upper().startswith("20-F") else "item_1a"
            risk_meta_payload: dict[str, Any] = {
                "cik": filing_cik,
                "accessionNumber": accession,
                "formType": form_type,
                "filingDate": filing_date,
                "reportDate": report_date,
                "secUrl": url,
                "section": risk_section_label,
                "extractorVersion": EXTRACTOR_VERSION,
                "normalizerVersion": NORMALIZER_VERSION,
                "confidence": confidence,
                "method": method,
                "warnings": warnings,
                "status": status_value or ("FAIL" if quality_gate_failed else "PASS"),
                "gateReasons": gate_reasons,
                "startSnippet": start_snippet or "",
                "endSnippet": end_snippet or "",
                "firstLines": first_lines,
                "lastLines": last_lines,
                "candidateCount": candidate_count if candidate_count is not None else 0,
                "topCandidates": top_candidates or [],
                "startMarker": start_marker_value,
                "endMarker": end_marker_value,
                "tocDetected": toc_detected,
                "tocRemoved": toc_removed,
                "charCount": len(raw_section),
                "tokenCount": risk_token_count,
                "uniqueTokens": risk_unique,
                "paragraphCount": risk_paragraph_count,
                "sha256RiskText": compute_sha256_text(raw_section) if raw_section else "",
                "includedInMetrics": included_in_metrics,
                "qualityGateFailed": quality_gate_failed,
                "hasItem1C": has_item1c,
                "generatedAtUtc": run_timestamp,
                "debug": debug_meta,
            }
            save_gz_text_atomic(risk_text_path(filing_cik, accession, form_type), raw_section)
            atomic_write_json(risk_meta_path(filing_cik, accession), risk_meta_payload)

        should_store_html = False
        if html_text is not None:
            if cache_debug_html:
                should_store_html = True
            elif quality_gate_failed or confidence < 0.5:
                should_store_html = True
        if should_store_html and html_text is not None:
            html_path = filing_html_path(filing_cik, accession)
            if not html_path.exists():
                save_gz_text_atomic(html_path, html_text)

        extraction_summary = {
            "section": "item1a",
            "method": method,
            "confidence": confidence,
            "warnings": warnings,
            "lengthChars": len(raw_section),
            "endMarkerUsed": end_marker_value,
            "hasItem1C": has_item1c,
        }
        meta_extraction = choose_meta_extraction(meta_extraction, extraction_summary)

        filings_out.append(
            {
                "year": year,
                "form": form_type,
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
        ticker_year_entries[str(year)] = {
            "cik": filing_cik,
            "accession": accession,
            "formType": form_type,
            "filingDate": filing_date,
        }

    filings_by_year: dict[int, dict[str, Any]] = {}
    for row in filings_out:
        year_value = row.get("year")
        if isinstance(year_value, int):
            filings_by_year[year_value] = row

    year_entries: list[tuple[int, str, str]] = []
    for year_key, entry in ticker_year_entries.items():
        try:
            year_value = int(year_key)
        except ValueError:
            continue
        year_entries.append((year_value, entry["cik"], entry["accession"]))
    year_entries.sort(key=lambda item: item[0])

    prev_len = 0
    for year_value, cik_value, accession_value in year_entries:
        meta_path = risk_meta_path(cik_value, accession_value)
        meta = as_str_dict(load_json(meta_path))
        if meta is None:
            prev_len = 0
            continue
        curr_len = get_int(meta.get("charCount")) or 0
        warnings = as_str_list(meta.get("warnings")) or []
        if prev_len > 0 and curr_len > 0:
            jump_ratio = abs(curr_len - prev_len) / prev_len
            if jump_ratio >= LENGTH_JUMP_RATIO:
                if "length_jump_vs_prev_year" not in warnings:
                    warnings.append("length_jump_vs_prev_year")
                    meta["warnings"] = warnings
                    atomic_write_json(meta_path, meta)
                row = filings_by_year.get(year_value)
                if row is not None:
                    extraction = row.get("extraction")
                    if isinstance(extraction, dict):
                        extraction["errors"] = warnings
        prev_len = curr_len

    meta_extraction = None
    for _year_value, cik_value, accession_value in year_entries:
        meta = as_str_dict(load_json(risk_meta_path(cik_value, accession_value)))
        if meta is None:
            continue
        warnings = as_str_list(meta.get("warnings")) or []
        extraction_summary = {
            "section": "item1a",
            "method": get_str(meta.get("method")) or "",
            "confidence": get_float(meta.get("confidence")) or 0.0,
            "warnings": warnings,
            "lengthChars": get_int(meta.get("charCount")) or 0,
            "endMarkerUsed": get_str(meta.get("endMarker")),
            "hasItem1C": get_bool(meta.get("hasItem1C")) or False,
        }
        meta_extraction = choose_meta_extraction(meta_extraction, extraction_summary)

    metrics_sections.sort(key=lambda section: section.year)
    quality_sections.sort(key=lambda section: section.year)
    filings_out = sorted(filings_out, key=lambda row: row["year"])

    metrics, similarity, shifts = build_metrics(metrics_sections)
    quality_shifts = build_quality_shifts(shifts)
    excerpt_pairs = build_excerpt_pairs(quality_sections, quality_shifts)
    excerpts: dict[str, Any] = {"section": SECTION_NAME, "pairs": excerpt_pairs}

    out_dir.mkdir(parents=True, exist_ok=True)

    forms_included = build_forms_included(filings_out)
    meta_payload: dict[str, Any] = {
        "ticker": ticker,
        "cik": primary_cik,
        "companyName": company_name,
        "lastUpdatedUtc": run_timestamp,
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

    ticker_index_payload = parse_ticker_year_index(load_json(ticker_year_index_path()))
    ticker_year_sorted: dict[str, TickerYearEntry] = {}
    for year_key in sorted(ticker_year_entries.keys()):
        ticker_year_sorted[year_key] = ticker_year_entries[year_key]
    ticker_index_payload[ticker] = ticker_year_sorted
    ordered_index: dict[str, dict[str, TickerYearEntry]] = {}
    for key in sorted(ticker_index_payload.keys()):
        ordered_index[key] = ticker_index_payload[key]
    atomic_write_json(ticker_year_index_path(), ordered_index)
    atomic_write_json(
        extraction_version_path(),
        {
            "extractorVersion": EXTRACTOR_VERSION,
            "normalizerVersion": NORMALIZER_VERSION,
            "generatedAtUtc": run_timestamp,
        },
    )

    cache_report = enforce_cache_size_limit(cache_max_gb)
    removed_files = cache_report.get("removedFiles")
    removed_files_list: list[str] = []
    if isinstance(removed_files, list):
        for item in cast(list[object], removed_files):
            if isinstance(item, str):
                removed_files_list.append(item)
    if removed_files_list:
        print(f"cache: pruned {len(removed_files_list)} optional files")
    if cache_report.get("overLimit") is True:
        print("warning: cache exceeds limit after pruning")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
