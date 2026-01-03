from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Optional

DEFAULT_CACHE_ROOT = Path(__file__).resolve().parents[1] / "data" / "sec_cache"
EXTRACTOR_VERSION = "1.0"
NORMALIZER_VERSION = "1.0"
MAX_CACHE_GB = 5


def get_cache_root() -> Path:
    override = os.environ.get("SEC_CACHE_ROOT")
    if override:
        return Path(override)
    return DEFAULT_CACHE_ROOT


def filing_dir(cik: str, accession: str) -> Path:
    return get_cache_root() / "filings" / cik / accession


def filing_text_path(cik: str, accession: str) -> Path:
    return filing_dir(cik, accession) / "filing.txt.gz"


def filing_html_path(cik: str, accession: str) -> Path:
    return filing_dir(cik, accession) / "filing.html.gz"


def filing_meta_path(cik: str, accession: str) -> Path:
    return filing_dir(cik, accession) / "filing_meta.json"


def risk_dir(cik: str, accession: str) -> Path:
    return filing_dir(cik, accession) / "risk"


def risk_text_path(cik: str, accession: str, form_type: str) -> Path:
    return risk_dir(cik, accession) / _risk_filename_for_form(form_type)


def risk_meta_path(cik: str, accession: str) -> Path:
    return risk_dir(cik, accession) / "rf_meta.json"


def ticker_year_index_path() -> Path:
    return get_cache_root() / "indexes" / "ticker_year_index.json"


def extraction_version_path() -> Path:
    return get_cache_root() / "indexes" / "extraction_version.json"


def cache_usage_path() -> Path:
    return get_cache_root() / "reports" / "cache_usage.json"


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    with tmp_path.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, path)


def atomic_write_json(path: Path, payload: Any, sort_keys: bool = True) -> None:
    content = json.dumps(payload, indent=2, sort_keys=sort_keys)
    atomic_write_bytes(path, content.encode("utf-8"))


def load_json(path: Path) -> Optional[Any]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_gz_text(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    data = path.read_bytes()
    return gzip.decompress(data).decode("utf-8", errors="replace")


def save_gz_text_atomic(path: Path, text: str) -> None:
    data = gzip.compress(text.encode("utf-8"), compresslevel=9)
    atomic_write_bytes(path, data)


def compute_sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cache_size_report() -> dict[str, Any]:
    root = get_cache_root()
    total_bytes = 0
    total_files = 0
    per_cik: dict[str, dict[str, Any]] = {}

    if not root.exists():
        return {"totalBytes": 0, "totalFiles": 0, "perCik": {}}

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        size = path.stat().st_size
        total_bytes += size
        total_files += 1
        parts = path.parts
        if "filings" in parts:
            idx = parts.index("filings")
            if idx + 1 < len(parts):
                cik = parts[idx + 1]
                entry = per_cik.setdefault(cik, {"bytes": 0, "files": 0})
                entry["bytes"] += size
                entry["files"] += 1

    return {"totalBytes": total_bytes, "totalFiles": total_files, "perCik": per_cik}


def enforce_cache_size_limit(max_gb: float = MAX_CACHE_GB) -> dict[str, Any]:
    limit_bytes = int(max_gb * 1024 * 1024 * 1024)
    report = cache_size_report()
    total_bytes = report["totalBytes"]
    removed: list[str] = []

    if total_bytes <= limit_bytes:
        return {
            "limitBytes": limit_bytes,
            "totalBytes": total_bytes,
            "removedFiles": removed,
            "overLimit": False,
        }

    root = get_cache_root()
    optional_files = list(root.rglob("filing.html.gz"))
    optional_files.extend(root.rglob("debug_snippets.json"))
    optional_files.sort(key=lambda path: path.stat().st_mtime)

    for path in optional_files:
        if total_bytes <= limit_bytes:
            break
        try:
            size = path.stat().st_size
            path.unlink()
            removed.append(str(path))
            total_bytes -= size
        except OSError:
            continue

    return {
        "limitBytes": limit_bytes,
        "totalBytes": total_bytes,
        "removedFiles": removed,
        "overLimit": total_bytes > limit_bytes,
    }


def _risk_filename_for_form(form_type: str) -> str:
    normalized = form_type.upper().strip()
    if normalized.startswith("20-F"):
        return "item_3d.txt.gz"
    return "item_1a.txt.gz"
