from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


SCRIPT_VERSION = "lab_verify_social_preview_deploy.py@v2"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO_HTML = REPO_ROOT / "index.html"
DEFAULT_DIST_HTML = REPO_ROOT / "dist" / "index.html"
DEFAULT_EXPECTED_BASE_PATH = "/sec-narrative-drift/"
USER_AGENT = "sec-narrative-drift-lab-social-preview-verifier/1.0"

REQUIRED_META_TAGS = [
    ("property", "og:title"),
    ("property", "og:description"),
    ("property", "og:type"),
    ("property", "og:url"),
    ("property", "og:image"),
    ("property", "og:image:alt"),
    ("name", "twitter:card"),
    ("name", "twitter:title"),
    ("name", "twitter:description"),
    ("name", "twitter:image"),
    ("name", "twitter:image:alt"),
]

CLOUDFLARE_CHALLENGE_MARKERS = (
    "Just a moment...",
    "cf-mitigated",
    "__cf_chl_",
    "challenge-error-text",
    "/cdn-cgi/challenge-platform/",
)

TAG_RE = re.compile(r"<(?P<tag>meta|link|script)\b[^>]*>", re.IGNORECASE)
ATTR_RE = re.compile(r'([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*("([^"]*)"|\'([^\']*)\')')
TITLE_RE = re.compile(r"<title>(?P<title>.*?)</title>", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class ExpectedMetaTag:
    attr_name: str
    attr_value: str
    content: str


@dataclass(frozen=True)
class ExpectedSurfaceTruth:
    title: str
    description: str
    meta_tags: tuple[ExpectedMetaTag, ...]
    favicon_href: str
    apple_touch_icon_href: str
    canonical_url: str
    share_image_url: str
    share_image_alt: str


@dataclass(frozen=True)
class UrlFetchResult:
    url: str
    final_url: str
    status: int | None
    content_type: str
    headers: dict[str, str]
    body: str
    error: str | None


@dataclass(frozen=True)
class HtmlSurfaceCheck:
    title: str | None
    has_root_div: bool
    is_cloudflare_challenge: bool
    challenge_markers: list[str]
    missing_meta_tags: list[str]
    mismatched_meta_tags: list[str]
    share_image_url: str | None
    favicon_url: str | None
    apple_touch_icon_url: str | None
    runtime_asset_urls: list[str]
    runtime_asset_paths: list[str]
    runtime_asset_prefix_ok: bool
    stale_markers: list[str]


@dataclass(frozen=True)
class LocalDistAudit:
    ok: bool
    issues: list[str]
    runtime_asset_paths: list[str]
    required_asset_paths: list[str]


@dataclass(frozen=True)
class SurfaceClassification:
    kind: str
    ready: bool
    reasons: list[str]


def normalize_site_url(value: str) -> str:
    return value.rstrip("/") + "/"


def normalize_expected_base_path(raw_value: str) -> str:
    candidate = raw_value.strip()
    if not candidate:
        return "/"
    if not candidate.startswith("/"):
        candidate = f"/{candidate}"
    candidate = re.sub(r"/{2,}", "/", candidate)
    return candidate if candidate.endswith("/") else f"{candidate}/"


def normalize_mounted_base(raw_value: str) -> tuple[str, str]:
    candidate = raw_value.strip().rstrip("/")
    if not candidate:
        raise SystemExit("--mounted-base must not be empty.")
    return candidate, f"{candidate}/"


def parse_attrs(tag_text: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in ATTR_RE.finditer(tag_text):
        key = match.group(1).lower()
        value = match.group(3) if match.group(3) is not None else match.group(4) or ""
        attrs[key] = value
    return attrs


def rel_tokens(rel_value: str) -> set[str]:
    return {token.strip().lower() for token in rel_value.split() if token.strip()}


def find_title(html: str) -> str | None:
    match = TITLE_RE.search(html)
    if match is None:
        return None
    return re.sub(r"\s+", " ", match.group("title")).strip()


def find_challenge_markers(text: str, headers: dict[str, str] | None = None) -> list[str]:
    header_values = " ".join((headers or {}).values())
    haystack = f"{text}\n{header_values}"
    return [marker for marker in CLOUDFLARE_CHALLENGE_MARKERS if marker in haystack]


def contains_cloudflare_challenge(text: str, headers: dict[str, str] | None = None) -> bool:
    return len(find_challenge_markers(text, headers)) > 0


def find_meta_content(html: str, attr_name: str, attr_value: str) -> str | None:
    for match in TAG_RE.finditer(html):
        if match.group("tag").lower() != "meta":
            continue
        attrs = parse_attrs(match.group(0))
        if attrs.get(attr_name) == attr_value and "content" in attrs:
            return attrs["content"]
    return None


def find_link_href(html: str, rel_name: str) -> str | None:
    for match in TAG_RE.finditer(html):
        if match.group("tag").lower() != "link":
            continue
        attrs = parse_attrs(match.group(0))
        rel = rel_tokens(attrs.get("rel", ""))
        href = attrs.get("href")
        if href and rel_name in rel:
            return href
    return None


def find_favicon_href(html: str) -> str | None:
    for match in TAG_RE.finditer(html):
        if match.group("tag").lower() != "link":
            continue
        attrs = parse_attrs(match.group(0))
        rel = rel_tokens(attrs.get("rel", ""))
        href = attrs.get("href")
        if href and "icon" in rel and "apple-touch-icon" not in rel:
            return href
    return None


def compare_meta_tags(html: str, expected: ExpectedSurfaceTruth | None) -> tuple[list[str], list[str]]:
    if expected is None:
        found: set[tuple[str, str]] = set()
        for match in TAG_RE.finditer(html):
            if match.group("tag").lower() != "meta":
                continue
            attrs = parse_attrs(match.group(0))
            if "content" not in attrs:
                continue
            for attr_name, attr_value in REQUIRED_META_TAGS:
                if attrs.get(attr_name) == attr_value:
                    found.add((attr_name, attr_value))

        missing: list[str] = []
        for attr_name, attr_value in REQUIRED_META_TAGS:
            if (attr_name, attr_value) not in found:
                missing.append(f"{attr_name}={attr_value}")
        return missing, []

    missing: list[str] = []
    mismatched: list[str] = []
    for tag in expected.meta_tags:
        actual = find_meta_content(html, tag.attr_name, tag.attr_value)
        key = f"{tag.attr_name}={tag.attr_value}"
        if actual is None:
            missing.append(key)
        elif actual != tag.content:
            mismatched.append(key)
    return missing, mismatched


def list_runtime_asset_urls(html: str, page_url: str) -> list[str]:
    assets: list[str] = []
    seen: set[str] = set()
    for match in TAG_RE.finditer(html):
        tag = match.group("tag").lower()
        attrs = parse_attrs(match.group(0))
        href_or_src: str | None = None
        if tag == "script":
            href_or_src = attrs.get("src")
        elif tag == "link":
            rel = rel_tokens(attrs.get("rel", ""))
            if "modulepreload" in rel or "stylesheet" in rel:
                href_or_src = attrs.get("href")
        if not href_or_src:
            continue
        resolved = urljoin(page_url, href_or_src)
        if resolved in seen:
            continue
        seen.add(resolved)
        assets.append(resolved)
    return assets


def list_runtime_asset_paths(urls: list[str]) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for asset_url in urls:
        path = urlparse(asset_url).path or asset_url
        if path in seen:
            continue
        seen.add(path)
        paths.append(path)
    return paths


def find_stale_markers(html: str, title: str | None) -> list[str]:
    markers: list[str] = []
    if title == "sec-narrative-drift":
        markers.append("legacy_title")
    if "vite.svg" in html:
        markers.append("legacy_vite_favicon")
    return markers


def build_expected_surface_truth(repo_html_path: Path = DEFAULT_REPO_HTML) -> ExpectedSurfaceTruth:
    html = repo_html_path.read_text(encoding="utf-8")
    title = find_title(html)
    description = find_meta_content(html, "name", "description")
    favicon_href = find_favicon_href(html)
    apple_touch_icon_href = find_link_href(html, "apple-touch-icon")

    if title is None:
        raise SystemExit(f"Missing <title> in {repo_html_path}")
    if description is None:
        raise SystemExit(f"Missing description meta tag in {repo_html_path}")
    if favicon_href is None:
        raise SystemExit(f"Missing favicon href in {repo_html_path}")
    if apple_touch_icon_href is None:
        raise SystemExit(f"Missing apple-touch-icon href in {repo_html_path}")

    tags: list[ExpectedMetaTag] = []
    for attr_name, attr_value in REQUIRED_META_TAGS:
        content = find_meta_content(html, attr_name, attr_value)
        if content is None:
            raise SystemExit(f"Missing required meta tag {attr_name}={attr_value} in {repo_html_path}")
        tags.append(ExpectedMetaTag(attr_name=attr_name, attr_value=attr_value, content=content))

    canonical_url = find_meta_content(html, "property", "og:url")
    share_image_url = find_meta_content(html, "property", "og:image")
    share_image_alt = find_meta_content(html, "property", "og:image:alt")
    if canonical_url is None or share_image_url is None or share_image_alt is None:
        raise SystemExit(f"Missing canonical social metadata in {repo_html_path}")

    return ExpectedSurfaceTruth(
        title=title,
        description=description,
        meta_tags=tuple(tags),
        favicon_href=favicon_href,
        apple_touch_icon_href=apple_touch_icon_href,
        canonical_url=canonical_url,
        share_image_url=share_image_url,
        share_image_alt=share_image_alt,
    )


def evaluate_html_surface(
    html: str,
    page_url: str,
    expected: ExpectedSurfaceTruth | None = None,
    expected_base_path: str = DEFAULT_EXPECTED_BASE_PATH,
) -> HtmlSurfaceCheck:
    title = find_title(html)
    missing_meta_tags, mismatched_meta_tags = compare_meta_tags(html, expected)
    share_image = find_meta_content(html, "property", "og:image") or find_meta_content(
        html, "name", "twitter:image"
    )
    favicon_href = find_favicon_href(html)
    apple_touch_icon_href = find_link_href(html, "apple-touch-icon")
    runtime_asset_urls = list_runtime_asset_urls(html, page_url)
    runtime_asset_paths = list_runtime_asset_paths(runtime_asset_urls)
    expected_asset_prefix = f"{normalize_expected_base_path(expected_base_path)}assets/"
    runtime_asset_prefix_ok = bool(runtime_asset_paths) and all(
        path.startswith(expected_asset_prefix) for path in runtime_asset_paths
    )
    challenge_markers = find_challenge_markers(html)

    return HtmlSurfaceCheck(
        title=title,
        has_root_div='<div id="root"></div>' in html or '<div id="root">' in html,
        is_cloudflare_challenge=len(challenge_markers) > 0,
        challenge_markers=challenge_markers,
        missing_meta_tags=missing_meta_tags,
        mismatched_meta_tags=mismatched_meta_tags,
        share_image_url=urljoin(page_url, share_image) if share_image else None,
        favicon_url=urljoin(page_url, favicon_href) if favicon_href else None,
        apple_touch_icon_url=urljoin(page_url, apple_touch_icon_href)
        if apple_touch_icon_href
        else None,
        runtime_asset_urls=runtime_asset_urls,
        runtime_asset_paths=runtime_asset_paths,
        runtime_asset_prefix_ok=runtime_asset_prefix_ok,
        stale_markers=find_stale_markers(html, title),
    )


def fetch_url(url: str, accept: str) -> UrlFetchResult:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": accept,
        },
    )

    try:
        with urlopen(request, timeout=20) as response:
            body = response.read()
            headers = {key.lower(): value for key, value in response.headers.items()}
            content_type = response.headers.get_content_type()
            return UrlFetchResult(
                url=url,
                final_url=response.geturl(),
                status=response.status,
                content_type=content_type,
                headers=headers,
                body=body.decode("utf-8", errors="replace"),
                error=None,
            )
    except HTTPError as error:
        headers = {key.lower(): value for key, value in error.headers.items()}
        content_type = error.headers.get_content_type()
        body = error.read().decode("utf-8", errors="replace")
        return UrlFetchResult(
            url=url,
            final_url=error.geturl(),
            status=error.code,
            content_type=content_type,
            headers=headers,
            body=body,
            error=str(error),
        )
    except URLError as error:
        return UrlFetchResult(
            url=url,
            final_url=url,
            status=None,
            content_type="",
            headers={},
            body="",
            error=str(error),
        )


def verify_asset(url: str | None) -> UrlFetchResult | None:
    if not url:
        return None
    return fetch_url(url, accept="image/*,*/*;q=0.8")


def asset_fetch_issue(label: str, fetch: UrlFetchResult | None) -> str | None:
    if fetch is None:
        return f"{label} asset missing"
    if fetch.status != 200:
        return f"{label} asset status {fetch.status if fetch.status is not None else 'unreachable'}"
    if not fetch.content_type.startswith("image/"):
        return f"{label} asset content-type {fetch.content_type or '<unknown>'}"
    return None


def summarize_values(values: Iterable[str]) -> str:
    items = list(values)
    if not items:
        return "none"
    return ", ".join(items)


def audit_local_dist_html(
    dist_html_path: Path,
    expected: ExpectedSurfaceTruth | None = None,
    expected_base_path: str = DEFAULT_EXPECTED_BASE_PATH,
) -> LocalDistAudit:
    if not dist_html_path.is_file():
        return LocalDistAudit(
            ok=False,
            issues=[f"missing {dist_html_path}"],
            runtime_asset_paths=[],
            required_asset_paths=[],
        )

    expected_truth = expected or build_expected_surface_truth()
    html = dist_html_path.read_text(encoding="utf-8")
    page_url = f"https://expected.example{normalize_expected_base_path(expected_base_path)}"
    check = evaluate_html_surface(
        html,
        page_url=page_url,
        expected=expected_truth,
        expected_base_path=expected_base_path,
    )

    required_asset_paths = [
        "favicon.svg",
        "apple-touch-icon.png",
        "social/sec-narrative-drift-lab-share-1200x630.png",
    ]
    missing_required_assets = [
        relative_path
        for relative_path in required_asset_paths
        if not (dist_html_path.parent / relative_path).is_file()
    ]

    issues: list[str] = []
    if not check.has_root_div:
        issues.append("root div missing from dist/index.html")
    if check.title != expected_truth.title:
        issues.append("title mismatch in dist/index.html")
    issues.extend(f"missing {item}" for item in check.missing_meta_tags)
    issues.extend(f"mismatched {item}" for item in check.mismatched_meta_tags)
    if check.favicon_url != urljoin(page_url, expected_truth.favicon_href):
        issues.append("favicon href mismatch in dist/index.html")
    if check.apple_touch_icon_url != urljoin(page_url, expected_truth.apple_touch_icon_href):
        issues.append("apple-touch-icon href mismatch in dist/index.html")
    if check.share_image_url != expected_truth.share_image_url:
        issues.append("share image URL mismatch in dist/index.html")
    if not check.runtime_asset_prefix_ok:
        issues.append(
            f"runtime asset prefix mismatch (expected {normalize_expected_base_path(expected_base_path)}assets/)"
        )
    if check.stale_markers:
        issues.extend(f"stale marker {marker}" for marker in check.stale_markers)
    if missing_required_assets:
        issues.extend(f"missing built asset {item}" for item in missing_required_assets)

    return LocalDistAudit(
        ok=len(issues) == 0,
        issues=issues,
        runtime_asset_paths=check.runtime_asset_paths,
        required_asset_paths=required_asset_paths,
    )


def check_local_dist_html(
    dist_html_path: Path,
    expected: ExpectedSurfaceTruth | None = None,
    expected_base_path: str = DEFAULT_EXPECTED_BASE_PATH,
) -> tuple[bool, list[str]]:
    audit = audit_local_dist_html(
        dist_html_path=dist_html_path,
        expected=expected,
        expected_base_path=expected_base_path,
    )
    return audit.ok, audit.issues


def check_repo_source_html(repo_html_path: Path) -> tuple[bool, list[str], ExpectedSurfaceTruth]:
    expected = build_expected_surface_truth(repo_html_path)
    html = repo_html_path.read_text(encoding="utf-8")
    issues: list[str] = []
    if "vite.svg" in html:
        issues.append("placeholder vite.svg reference still present")
    if expected.favicon_href != "./favicon.svg":
        issues.append("favicon href no longer points at ./favicon.svg")
    if expected.apple_touch_icon_href != "./apple-touch-icon.png":
        issues.append("apple-touch-icon href no longer points at ./apple-touch-icon.png")
    return len(issues) == 0, issues, expected


def classify_surface(
    fetch: UrlFetchResult,
    check: HtmlSurfaceCheck,
    expected: ExpectedSurfaceTruth,
    expected_runtime_asset_paths: set[str],
    expected_base_path: str,
    expected_favicon_url: str,
    expected_apple_touch_icon_url: str,
    expected_share_image_url: str,
    share_asset_fetch: UrlFetchResult | None = None,
    favicon_asset_fetch: UrlFetchResult | None = None,
    apple_touch_asset_fetch: UrlFetchResult | None = None,
    required_final_url: str | None = None,
) -> SurfaceClassification:
    reasons: list[str] = []

    if fetch.status != 200:
        reasons.append(f"status {fetch.status if fetch.status is not None else 'unreachable'}")
    if check.is_cloudflare_challenge:
        reasons.append(f"challenge markers present: {summarize_values(check.challenge_markers)}")
    if not check.has_root_div:
        reasons.append("root div missing")
    if check.title != expected.title:
        reasons.append("title mismatch")
    if check.missing_meta_tags:
        reasons.append(f"missing meta tags: {summarize_values(check.missing_meta_tags)}")
    if check.mismatched_meta_tags:
        reasons.append(f"mismatched meta tags: {summarize_values(check.mismatched_meta_tags)}")
    if check.share_image_url != expected_share_image_url:
        reasons.append("share image URL mismatch")
    if check.favicon_url != expected_favicon_url:
        reasons.append("favicon URL mismatch")
    if check.apple_touch_icon_url != expected_apple_touch_icon_url:
        reasons.append("apple touch icon URL mismatch")
    if not check.runtime_asset_prefix_ok:
        reasons.append(
            f"runtime asset prefix mismatch (expected {normalize_expected_base_path(expected_base_path)}assets/)"
        )
    if set(check.runtime_asset_paths) != expected_runtime_asset_paths:
        reasons.append("runtime asset set differs from dist build")
    if required_final_url and fetch.final_url != required_final_url:
        reasons.append(f"final URL mismatch (expected {required_final_url})")
    if check.stale_markers:
        reasons.append(f"stale markers present: {summarize_values(check.stale_markers)}")

    for issue in (
        asset_fetch_issue("share image", share_asset_fetch),
        asset_fetch_issue("favicon", favicon_asset_fetch),
        asset_fetch_issue("apple touch icon", apple_touch_asset_fetch),
    ):
        if issue is not None:
            reasons.append(issue)

    if check.is_cloudflare_challenge:
        return SurfaceClassification(
            kind="challenge/interstitial interference",
            ready=False,
            reasons=reasons,
        )

    stale_metadata = surface_looks_stale(
        check=check,
        expected=expected,
        expected_runtime_asset_paths=expected_runtime_asset_paths,
    )
    if stale_metadata:
        return SurfaceClassification(kind="stale deploy", ready=False, reasons=reasons)

    mount_mismatch = surface_looks_mount_mismatched(
        fetch=fetch,
        check=check,
        expected_favicon_url=expected_favicon_url,
        expected_apple_touch_icon_url=expected_apple_touch_icon_url,
        expected_share_image_url=expected_share_image_url,
        share_asset_fetch=share_asset_fetch,
        favicon_asset_fetch=favicon_asset_fetch,
        apple_touch_asset_fetch=apple_touch_asset_fetch,
        required_final_url=required_final_url,
    )
    if mount_mismatch:
        return SurfaceClassification(kind="mount mismatch", ready=False, reasons=reasons)

    return SurfaceClassification(kind="pass", ready=True, reasons=reasons)


def build_expected_live_urls(
    canonical_page_url: str,
    expected: ExpectedSurfaceTruth,
) -> tuple[str, str, str]:
    return (
        urljoin(canonical_page_url, expected.favicon_href),
        urljoin(canonical_page_url, expected.apple_touch_icon_href),
        expected.share_image_url,
    )


def describe_slash_divergence(
    slashless_fetch: UrlFetchResult,
    slashless_check: HtmlSurfaceCheck,
    slashed_fetch: UrlFetchResult,
    slashed_check: HtmlSurfaceCheck,
) -> list[str]:
    differences: list[str] = []
    if slashless_fetch.final_url != slashed_fetch.final_url:
        differences.append(
            f"final_url: {slashless_fetch.final_url} vs {slashed_fetch.final_url}"
        )
    if slashless_check.title != slashed_check.title:
        differences.append(f"title: {slashless_check.title!r} vs {slashed_check.title!r}")
    if slashless_check.favicon_url != slashed_check.favicon_url:
        differences.append(
            f"favicon_url: {slashless_check.favicon_url or '<missing>'} vs {slashed_check.favicon_url or '<missing>'}"
        )
    if slashless_check.apple_touch_icon_url != slashed_check.apple_touch_icon_url:
        differences.append(
            "apple_touch_icon_url: "
            f"{slashless_check.apple_touch_icon_url or '<missing>'} vs "
            f"{slashed_check.apple_touch_icon_url or '<missing>'}"
        )
    if slashless_check.share_image_url != slashed_check.share_image_url:
        differences.append(
            f"share_image_url: {slashless_check.share_image_url or '<missing>'} vs {slashed_check.share_image_url or '<missing>'}"
        )
    if slashless_check.missing_meta_tags != slashed_check.missing_meta_tags:
        differences.append(
            "missing_meta_tags: "
            f"{summarize_values(slashless_check.missing_meta_tags)} vs "
            f"{summarize_values(slashed_check.missing_meta_tags)}"
        )
    if slashless_check.runtime_asset_paths != slashed_check.runtime_asset_paths:
        differences.append(
            f"runtime_asset_paths: {summarize_values(slashless_check.runtime_asset_paths)} vs {summarize_values(slashed_check.runtime_asset_paths)}"
        )
    return differences


def surface_looks_stale(
    check: HtmlSurfaceCheck,
    expected: ExpectedSurfaceTruth,
    expected_runtime_asset_paths: set[str],
) -> bool:
    return (
        check.title != expected.title
        or bool(check.missing_meta_tags)
        or bool(check.mismatched_meta_tags)
        or bool(check.stale_markers)
        or set(check.runtime_asset_paths) != expected_runtime_asset_paths
    )


def surface_looks_mount_mismatched(
    fetch: UrlFetchResult,
    check: HtmlSurfaceCheck,
    expected_favicon_url: str,
    expected_apple_touch_icon_url: str,
    expected_share_image_url: str,
    share_asset_fetch: UrlFetchResult | None,
    favicon_asset_fetch: UrlFetchResult | None,
    apple_touch_asset_fetch: UrlFetchResult | None,
    required_final_url: str | None = None,
) -> bool:
    return (
        fetch.status != 200
        or not check.has_root_div
        or check.share_image_url != expected_share_image_url
        or check.favicon_url != expected_favicon_url
        or check.apple_touch_icon_url != expected_apple_touch_icon_url
        or not check.runtime_asset_prefix_ok
        or required_final_url is not None
        and fetch.final_url != required_final_url
        or asset_fetch_issue("share image", share_asset_fetch) is not None
        or asset_fetch_issue("favicon", favicon_asset_fetch) is not None
        or asset_fetch_issue("apple touch icon", apple_touch_asset_fetch) is not None
    )


def print_asset_result(label: str, fetch: UrlFetchResult | None) -> None:
    if fetch is None:
        print(f"{label}_asset_status: <missing>")
        return
    print(f"{label}_asset_status: {fetch.status if fetch.status is not None else 'unreachable'}")
    print(f"{label}_asset_content_type: {fetch.content_type or '<unknown>'}")
    print(f"{label}_asset_final_url: {fetch.final_url}")


def print_surface_result(
    label: str,
    fetch: UrlFetchResult,
    check: HtmlSurfaceCheck,
    classification: SurfaceClassification,
    share_asset: UrlFetchResult | None,
    favicon_asset: UrlFetchResult | None,
    apple_touch_asset: UrlFetchResult | None,
) -> None:
    print(f"## {label}")
    print(f"requested_url: {fetch.url}")
    print(f"final_url: {fetch.final_url}")
    print(f"status: {fetch.status if fetch.status is not None else 'unreachable'}")
    print(f"content_type: {fetch.content_type or '<unknown>'}")
    print(f"classification: {classification.kind}")
    print(f"classification_reasons: {summarize_values(classification.reasons)}")
    print(f"challenge_markers: {summarize_values(check.challenge_markers)}")
    print(f"root_div_present: {'yes' if check.has_root_div else 'no'}")
    print(f"title: {check.title or '<missing>'}")
    print(f"missing_meta_tags: {summarize_values(check.missing_meta_tags)}")
    print(f"mismatched_meta_tags: {summarize_values(check.mismatched_meta_tags)}")
    print(f"stale_markers: {summarize_values(check.stale_markers)}")
    print(f"share_image_url: {check.share_image_url or '<missing>'}")
    print(f"favicon_url: {check.favicon_url or '<missing>'}")
    print(f"apple_touch_icon_url: {check.apple_touch_icon_url or '<missing>'}")
    print(f"runtime_asset_paths: {summarize_values(check.runtime_asset_paths)}")
    print(f"runtime_asset_prefix_ok: {'yes' if check.runtime_asset_prefix_ok else 'no'}")
    print_asset_result("share_image", share_asset)
    print_asset_result("favicon", favicon_asset)
    print_asset_result("apple_touch_icon", apple_touch_asset)
    print("")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify social preview deploy surfaces.")
    url_group = parser.add_mutually_exclusive_group(required=True)
    url_group.add_argument(
        "--site-url",
        help="Single mounted public URL to verify (legacy mode, normalized to a trailing slash).",
    )
    url_group.add_argument(
        "--mounted-base",
        help="Mounted base URL to verify in both slashless and slashed forms.",
    )
    parser.add_argument("--origin-url", default="", help="Optional direct Pages/custom-domain URL.")
    parser.add_argument(
        "--dist-html",
        default=str(DEFAULT_DIST_HTML),
        help="Optional local built HTML path for repo/build verification.",
    )
    parser.add_argument(
        "--expected-base-path",
        default=DEFAULT_EXPECTED_BASE_PATH,
        help="Expected deployed base path for JS/CSS asset URLs.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    expected_base_path = normalize_expected_base_path(args.expected_base_path)
    repo_ok, repo_issues, expected = check_repo_source_html(DEFAULT_REPO_HTML)

    dist_html_path = Path(args.dist_html)
    if not dist_html_path.is_absolute():
        dist_html_path = REPO_ROOT / dist_html_path
    build_audit = audit_local_dist_html(
        dist_html_path=dist_html_path,
        expected=expected,
        expected_base_path=expected_base_path,
    )

    print("# Deployment Sync Verification")
    print("")
    print(f"script: {SCRIPT_VERSION}")
    print(f"repo_html: {DEFAULT_REPO_HTML}")
    print(f"dist_html: {dist_html_path}")
    print(f"expected_base_path: {expected_base_path}")
    print("")
    print("## Repo source truth")
    print(f"repo_truth_ready: {'yes' if repo_ok else 'no'}")
    print(f"repo_truth_issues: {summarize_values(repo_issues)}")
    print(f"expected_title: {expected.title}")
    print(f"expected_canonical_url: {expected.canonical_url}")
    print(f"expected_share_image_url: {expected.share_image_url}")
    print(f"expected_favicon_href: {expected.favicon_href}")
    print(f"expected_apple_touch_icon_href: {expected.apple_touch_icon_href}")
    print("")
    print("## Built dist truth")
    print(f"build_output_ready: {'yes' if build_audit.ok else 'no'}")
    print(f"build_output_issues: {summarize_values(build_audit.issues)}")
    print(f"build_runtime_asset_paths: {summarize_values(build_audit.runtime_asset_paths)}")
    print(
        f"required_built_assets: {summarize_values(build_audit.required_asset_paths)}"
    )
    print("")

    expected_runtime_asset_paths = set(build_audit.runtime_asset_paths)
    mounted_ready = False
    origin_ready = True

    if args.mounted_base:
        slashless_url, slashed_url = normalize_mounted_base(args.mounted_base)
        expected_favicon_url, expected_apple_touch_icon_url, expected_share_image_url = (
            build_expected_live_urls(slashed_url, expected)
        )

        slashless_fetch = fetch_url(slashless_url, accept="text/html,application/xhtml+xml")
        slashless_check = evaluate_html_surface(
            slashless_fetch.body,
            page_url=slashless_fetch.final_url,
            expected=expected,
            expected_base_path=expected_base_path,
        )
        slashless_share_asset = verify_asset(slashless_check.share_image_url)
        slashless_favicon_asset = verify_asset(slashless_check.favicon_url)
        slashless_apple_touch_asset = verify_asset(slashless_check.apple_touch_icon_url)
        slashless_classification = classify_surface(
            fetch=slashless_fetch,
            check=slashless_check,
            expected=expected,
            expected_runtime_asset_paths=expected_runtime_asset_paths,
            expected_base_path=expected_base_path,
            expected_favicon_url=expected_favicon_url,
            expected_apple_touch_icon_url=expected_apple_touch_icon_url,
            expected_share_image_url=expected_share_image_url,
            share_asset_fetch=slashless_share_asset,
            favicon_asset_fetch=slashless_favicon_asset,
            apple_touch_asset_fetch=slashless_apple_touch_asset,
            required_final_url=slashed_url,
        )
        print_surface_result(
            "Mounted public path (slashless)",
            slashless_fetch,
            slashless_check,
            slashless_classification,
            slashless_share_asset,
            slashless_favicon_asset,
            slashless_apple_touch_asset,
        )

        slashed_fetch = fetch_url(slashed_url, accept="text/html,application/xhtml+xml")
        slashed_check = evaluate_html_surface(
            slashed_fetch.body,
            page_url=slashed_fetch.final_url,
            expected=expected,
            expected_base_path=expected_base_path,
        )
        slashed_share_asset = verify_asset(slashed_check.share_image_url)
        slashed_favicon_asset = verify_asset(slashed_check.favicon_url)
        slashed_apple_touch_asset = verify_asset(slashed_check.apple_touch_icon_url)
        slashed_classification = classify_surface(
            fetch=slashed_fetch,
            check=slashed_check,
            expected=expected,
            expected_runtime_asset_paths=expected_runtime_asset_paths,
            expected_base_path=expected_base_path,
            expected_favicon_url=expected_favicon_url,
            expected_apple_touch_icon_url=expected_apple_touch_icon_url,
            expected_share_image_url=expected_share_image_url,
            share_asset_fetch=slashed_share_asset,
            favicon_asset_fetch=slashed_favicon_asset,
            apple_touch_asset_fetch=slashed_apple_touch_asset,
        )
        print_surface_result(
            "Mounted public path (slashed)",
            slashed_fetch,
            slashed_check,
            slashed_classification,
            slashed_share_asset,
            slashed_favicon_asset,
            slashed_apple_touch_asset,
        )

        slash_differences = describe_slash_divergence(
            slashless_fetch=slashless_fetch,
            slashless_check=slashless_check,
            slashed_fetch=slashed_fetch,
            slashed_check=slashed_check,
        )
        slashless_redirects_to_slashed = slashless_fetch.final_url == slashed_url
        mounted_ready = (
            build_audit.ok
            and slashed_classification.ready
            and slashless_redirects_to_slashed
        )

        print("## Slash normalization")
        print(f"slashless_requested_url: {slashless_url}")
        print(f"slashed_requested_url: {slashed_url}")
        print(f"slashless_redirects_to_slashed: {'yes' if slashless_redirects_to_slashed else 'no'}")
        print(f"slash_behavior_diverges: {'yes' if slash_differences else 'no'}")
        print(f"slash_divergence_details: {summarize_values(slash_differences)}")
        print("")

        if args.origin_url.strip():
            origin_url = normalize_site_url(args.origin_url)
            origin_fetch = fetch_url(origin_url, accept="text/html,application/xhtml+xml")
            origin_check = evaluate_html_surface(
                origin_fetch.body,
                page_url=origin_fetch.final_url,
                expected=expected,
                expected_base_path=expected_base_path,
            )
            origin_share_asset = verify_asset(origin_check.share_image_url)
            origin_favicon_asset = verify_asset(origin_check.favicon_url)
            origin_apple_touch_asset = verify_asset(origin_check.apple_touch_icon_url)
            origin_classification = classify_surface(
                fetch=origin_fetch,
                check=origin_check,
                expected=expected,
                expected_runtime_asset_paths=expected_runtime_asset_paths,
                expected_base_path=expected_base_path,
                expected_favicon_url=urljoin(origin_url, expected.favicon_href),
                expected_apple_touch_icon_url=urljoin(origin_url, expected.apple_touch_icon_href),
                expected_share_image_url=expected_share_image_url,
                share_asset_fetch=origin_share_asset,
                favicon_asset_fetch=origin_favicon_asset,
                apple_touch_asset_fetch=origin_apple_touch_asset,
            )
            print_surface_result(
                "Origin path",
                origin_fetch,
                origin_check,
                origin_classification,
                origin_share_asset,
                origin_favicon_asset,
                origin_apple_touch_asset,
            )
            origin_ready = origin_classification.ready

        print("## Summary")
        print(f"repo_truth_ready: {'yes' if repo_ok else 'no'}")
        print(f"build_output_ready: {'yes' if build_audit.ok else 'no'}")
        print(f"mounted_public_path_ready: {'yes' if mounted_ready else 'no'}")
        print(
            "mounted_primary_classification: "
            f"{slashed_classification.kind if slashed_classification.kind else '<unknown>'}"
        )
        print(
            "origin_path_ready: "
            f"{'not checked' if not args.origin_url.strip() else ('yes' if origin_ready else 'no')}"
        )
        print(
            "stale_deploy_suspected: "
            f"{'yes' if surface_looks_stale(slashed_check, expected, expected_runtime_asset_paths) else 'no'}"
        )
        print(
            "mount_mismatch_suspected: "
            f"{'yes' if surface_looks_mount_mismatched(slashed_fetch, slashed_check, expected_favicon_url, expected_apple_touch_icon_url, expected_share_image_url, slashed_share_asset, slashed_favicon_asset, slashed_apple_touch_asset) else 'no'}"
        )
        print(
            "challenge_or_interstitial_suspected: "
            f"{'yes' if slashed_classification.kind == 'challenge/interstitial interference' else 'no'}"
        )
        print(
            "slash_normalization_intentional: "
            f"{'yes' if slashless_redirects_to_slashed else 'no'}"
        )
        return 0 if repo_ok and build_audit.ok and mounted_ready and origin_ready else 1

    site_url = normalize_site_url(args.site_url)
    expected_favicon_url, expected_apple_touch_icon_url, expected_share_image_url = (
        build_expected_live_urls(site_url, expected)
    )

    site_fetch = fetch_url(site_url, accept="text/html,application/xhtml+xml")
    site_check = evaluate_html_surface(
        site_fetch.body,
        page_url=site_fetch.final_url,
        expected=expected,
        expected_base_path=expected_base_path,
    )
    site_share_asset = verify_asset(site_check.share_image_url)
    site_favicon_asset = verify_asset(site_check.favicon_url)
    site_apple_touch_asset = verify_asset(site_check.apple_touch_icon_url)
    site_classification = classify_surface(
        fetch=site_fetch,
        check=site_check,
        expected=expected,
        expected_runtime_asset_paths=expected_runtime_asset_paths,
        expected_base_path=expected_base_path,
        expected_favicon_url=expected_favicon_url,
        expected_apple_touch_icon_url=expected_apple_touch_icon_url,
        expected_share_image_url=expected_share_image_url,
        share_asset_fetch=site_share_asset,
        favicon_asset_fetch=site_favicon_asset,
        apple_touch_asset_fetch=site_apple_touch_asset,
    )
    print_surface_result(
        "Mounted public path",
        site_fetch,
        site_check,
        site_classification,
        site_share_asset,
        site_favicon_asset,
        site_apple_touch_asset,
    )
    mounted_ready = build_audit.ok and site_classification.ready

    if args.origin_url.strip():
        origin_url = normalize_site_url(args.origin_url)
        origin_fetch = fetch_url(origin_url, accept="text/html,application/xhtml+xml")
        origin_check = evaluate_html_surface(
            origin_fetch.body,
            page_url=origin_fetch.final_url,
            expected=expected,
            expected_base_path=expected_base_path,
        )
        origin_share_asset = verify_asset(origin_check.share_image_url)
        origin_favicon_asset = verify_asset(origin_check.favicon_url)
        origin_apple_touch_asset = verify_asset(origin_check.apple_touch_icon_url)
        origin_classification = classify_surface(
            fetch=origin_fetch,
            check=origin_check,
            expected=expected,
            expected_runtime_asset_paths=expected_runtime_asset_paths,
            expected_base_path=expected_base_path,
            expected_favicon_url=urljoin(origin_url, expected.favicon_href),
            expected_apple_touch_icon_url=urljoin(origin_url, expected.apple_touch_icon_href),
            expected_share_image_url=expected_share_image_url,
            share_asset_fetch=origin_share_asset,
            favicon_asset_fetch=origin_favicon_asset,
            apple_touch_asset_fetch=origin_apple_touch_asset,
        )
        print_surface_result(
            "Origin path",
            origin_fetch,
            origin_check,
            origin_classification,
            origin_share_asset,
            origin_favicon_asset,
            origin_apple_touch_asset,
        )
        origin_ready = origin_classification.ready

    print("## Summary")
    print(f"repo_truth_ready: {'yes' if repo_ok else 'no'}")
    print(f"build_output_ready: {'yes' if build_audit.ok else 'no'}")
    print(f"mounted_public_path_ready: {'yes' if mounted_ready else 'no'}")
    print(f"mounted_primary_classification: {site_classification.kind}")
    print(
        "origin_path_ready: "
        f"{'not checked' if not args.origin_url.strip() else ('yes' if origin_ready else 'no')}"
    )
    print(
        "stale_deploy_suspected: "
        f"{'yes' if surface_looks_stale(site_check, expected, expected_runtime_asset_paths) else 'no'}"
    )
    print(
        "mount_mismatch_suspected: "
        f"{'yes' if surface_looks_mount_mismatched(site_fetch, site_check, expected_favicon_url, expected_apple_touch_icon_url, expected_share_image_url, site_share_asset, site_favicon_asset, site_apple_touch_asset) else 'no'}"
    )
    print(
        "challenge_or_interstitial_suspected: "
        f"{'yes' if site_classification.kind == 'challenge/interstitial interference' else 'no'}"
    )
    return 0 if repo_ok and build_audit.ok and mounted_ready and origin_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
