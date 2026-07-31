from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

BASE_URL = "https://healthrenewal.org/"
MINIMUM_SHA = "5851636aff33ed79f222ded748a9b43c437178e4"
DEFAULT_REPOSITORY = "khaledaltheeb/"
BANNED = re.compile(r"\bمعاق(?:ون|ين)?\b")
SHA_PATTERN = re.compile(r"[0-9a-f]{40}")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(read_text(path))
    if not isinstance(payload, dict):
        raise AssertionError(f"Expected JSON object: {path}")
    return payload


def require(text: str, phrase: str, label: str) -> None:
    if phrase not in text:
        raise AssertionError(f"Missing {label}: {phrase}")


def validate_root(root: Path) -> dict[str, Any]:
    root = root.resolve()
    paths = {
        "main": root / "specialists-partners" / "index.html",
        "join": root / "specialists-partners" / "join.html",
        "verification": root / "specialists-partners" / "verification.html",
        "runtime": root / "specialists-partners" / "assets" / "sector.js",
        "directory_core": root / "specialists-partners" / "assets" / "directory-core.js",
        "providers": root / "specialists-partners" / "data" / "providers.json",
        "schema": root / "specialists-partners" / "data" / "provider.schema.json",
        "quality": root / "api" / "specialists-partners-quality-v354.json",
        "api": root / "api" / "v1" / "specialists-partners.json",
        "platform": root / "api" / "v1" / "platform.json",
        "sitemap": root / "sitemap-specialists-partners.xml",
        "sitemap_index": root / "sitemap-index.xml",
        "robots": root / "robots.txt",
        "shell": root / "assets" / "platform" / "platform-core.js",
    }
    missing = [str(path.relative_to(root)) for path in paths.values() if not path.is_file()]
    if missing:
        raise AssertionError(f"Missing specialists-partners production files: {missing}")

    main = read_text(paths["main"])
    join = read_text(paths["join"])
    verification = read_text(paths["verification"])
    runtime = read_text(paths["runtime"])
    directory_core = read_text(paths["directory_core"])
    robots = read_text(paths["robots"])
    shell = read_text(paths["shell"])

    if main.count("<h1") != 1:
        raise AssertionError("The directory page must contain exactly one h1")
    for phrase, label in (
        ("فريقنا وشركاؤنا ذوو الاختصاص", "directory title"),
        ("التربية الخاصة", "special-education focus"),
        ("السمع والنطق", "hearing and speech focus"),
        ("CollectionPage", "structured data"),
        ("BreadcrumbList", "breadcrumbs"),
        ('rel="canonical" href="https://healthrenewal.org/specialists-partners/"', "canonical"),
        ('id="directory"', "directory landmark"),
        ('id="matcher"', "matching journey"),
        ('id="directory-health"', "live registry status"),
        ("لا توجد ملفات مهنية منشورة حاليًا", "truthful empty state"),
        ("ستة أسئلة قبل حجز الخدمة", "before-booking quality guidance"),
        ("assets/directory-core.js?v=4.1.0", "directory core asset"),
    ):
        require(main, phrase, label)

    require(join, "إضافة مختص أو مركز", "join workflow")
    require(join, "الموافقة الكتابية", "written-consent requirement")
    require(verification, "سياسة التحقق من المختصين والمراكز", "verification policy")
    require(verification, "التعليق والإزالة", "suspension and removal policy")

    for text, label in ((main, "main"), (join, "join"), (verification, "verification")):
        if BANNED.search(text):
            raise AssertionError(f"Disallowed terminology in {label} page")

    for marker in (
        "/v1/providers?limit=250",
        "data/providers.json",
        "core.prepareProviders",
        "['https:','mailto:','tel:']",
        "protocol === 'https:'",
    ):
        require(runtime, marker, "runtime publication guard")
    for marker in (
        "provider?.publicationStatus === 'published'",
        "provider?.verification?.status === 'verified'",
        "provider?.consent?.publicProfileApproved === true",
        "normalizeArabic",
        "ageMatches",
        "specialtyAny",
    ):
        require(directory_core, marker, "directory-core publication and matching guard")

    providers = read_json(paths["providers"])
    require(str(providers.get("publicationPolicy", "")), "written publication consent", "publication policy")
    records = providers.get("providers")
    if not isinstance(records, list):
        raise AssertionError("providers.json must contain a providers array")
    for record in records:
        if not isinstance(record, dict):
            raise AssertionError("Provider records must be objects")
        if record.get("publicationStatus") != "published":
            continue
        if record.get("verification", {}).get("status") != "verified":
            raise AssertionError(f"Published record is not verified: {record.get('id')}")
        if record.get("consent", {}).get("publicProfileApproved") is not True:
            raise AssertionError(f"Published record lacks explicit consent: {record.get('id')}")
        if not record.get("verification", {}).get("sources"):
            raise AssertionError(f"Published record lacks verification evidence: {record.get('id')}")

    schema = read_json(paths["schema"])
    required_schema_fields = set(schema.get("required", []))
    expected_schema_fields = {
        "id",
        "entityType",
        "displayName",
        "specialties",
        "verification",
        "publicationStatus",
        "consent",
    }
    missing_schema = sorted(expected_schema_fields - required_schema_fields)
    if missing_schema:
        raise AssertionError(f"Provider schema missing required fields: {missing_schema}")
    consent_schema = schema.get("properties", {}).get("consent", {}).get("properties", {})
    if consent_schema.get("publicProfileApproved", {}).get("const") is not True:
        raise AssertionError("Provider schema must require explicit public-profile consent")

    api = read_json(paths["api"])
    if api.get("status") != "active":
        raise AssertionError(f"Specialists API is not active: {api.get('status')}")
    require(json.dumps(api, ensure_ascii=False), "/specialists-partners/data/providers.json", "directory endpoint")
    require(
        json.dumps(api, ensure_ascii=False),
        "/api/specialists-partners-quality-v354.json",
        "quality report endpoint",
    )

    quality = read_json(paths["quality"])
    if (
        quality.get("version") != 354
        or quality.get("status") != "passed"
        or quality.get("interfaceCount") != 9
        or quality.get("errorCount") != 0
        or quality.get("unsafePublishedProviderIds") != []
    ):
        raise AssertionError(f"Invalid specialists quality report: {quality}")

    platform = read_json(paths["platform"])
    resource_ids = {item.get("id") for item in platform.get("resources", []) if isinstance(item, dict)}
    if "specialists-partners" not in resource_ids:
        raise AssertionError("Platform API does not register specialists-partners")
    endpoints = platform.get("endpoints", {})
    if (
        "specialistsPartners" not in endpoints
        or "specialistsPartnersDirectory" not in endpoints
        or "specialistsPartnersQuality" not in endpoints
    ):
        raise AssertionError("Platform API is missing specialists-partners endpoints")

    locations = [
        (node.text or "").strip()
        for node in ET.parse(paths["sitemap"]).getroot().findall("{*}url/{*}loc")
        if node.text
    ]
    expected_locations = {
        f"{BASE_URL}specialists-partners/",
        f"{BASE_URL}specialists-partners/join.html",
        f"{BASE_URL}specialists-partners/verification.html",
        f"{BASE_URL}api/v1/specialists-partners.json",
    }
    if set(locations) != expected_locations or len(locations) != len(set(locations)):
        raise AssertionError(f"Unexpected specialists sitemap routes: {locations}")
    require(robots, f"Sitemap: {BASE_URL}sitemap-index.xml", "robots sitemap-index registration")
    index_locations = {
        (node.text or "").strip()
        for node in ET.parse(paths["sitemap_index"]).getroot().findall("{*}sitemap/{*}loc")
        if node.text
    }
    if f"{BASE_URL}sitemap-specialists-partners.xml" not in index_locations:
        raise AssertionError("The sitemap index does not register specialists-partners")
    require(shell, "['الفريق والشركاء', 'specialists-partners/']", "global navigation link")

    return {
        "status": "passed",
        "contract": "specialists-partners-production-v354",
        "provider_count": len(records),
        "sitemap_routes": len(locations),
        "global_navigation": True,
        "publication_guard": True,
        "written_consent_required": True,
        "live_registry_with_static_fallback": True,
        "quality_report_version": quality["version"],
        "interface_count": quality["interfaceCount"],
    }


def http_json(url: str, token: str | None = None) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "Cache-Control": "no-cache",
        "User-Agent": "specialists-partners-live-verifier",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"Expected JSON object from {url}")
    return payload


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"Cache-Control": "no-cache", "User-Agent": "specialists-partners-live-verifier"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def valid_sha(value: Any) -> str | None:
    return value if isinstance(value, str) and SHA_PATTERN.fullmatch(value) else None


def receipt_candidate(path: Path | None) -> tuple[str | None, str | None]:
    if path is None or not path.is_file():
        return None, None
    payload = read_json(path)
    if payload.get("status") != "deployed":
        return None, None
    candidate = valid_sha(payload.get("source_commit"))
    return candidate, "repository-pages-receipt" if candidate else (None, None)


def remote_candidate(base_url: str, attempt: int) -> tuple[str | None, str | None]:
    token = f"{int(time.time())}-{attempt}"
    sources = (
        ("pages-deployment-status.json", "source_commit", "live-pages-receipt"),
        ("deployment.json", "commit", "legacy-live-deployment"),
    )
    for route, field, label in sources:
        try:
            payload = http_json(f"{base_url}{route}?v={token}")
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
            continue
        candidate = valid_sha(payload.get(field))
        if candidate:
            return candidate, label
    return None, None


def sha_contains_minimum(live_sha: str, repository: str, token: str | None) -> bool:
    if live_sha == MINIMUM_SHA:
        return True
    comparison = http_json(
        f"https://api.github.com/repos/{repository}/compare/{MINIMUM_SHA}...{live_sha}",
        token,
    )
    return comparison.get("status") in {"ahead", "identical"}


def validate_live(
    base_url: str,
    repository: str,
    token: str | None,
    attempts: int,
    delay: int,
    receipt_path: Path | None = None,
) -> dict[str, Any]:
    base_url = base_url.rstrip("/") + "/"
    last_error: Exception | None = None
    routes = {
        "specialists-partners/index.html": "specialists-partners/",
        "specialists-partners/join.html": "specialists-partners/join.html",
        "specialists-partners/verification.html": "specialists-partners/verification.html",
        "specialists-partners/assets/sector.js": "specialists-partners/assets/sector.js",
        "specialists-partners/assets/directory-core.js": "specialists-partners/assets/directory-core.js",
        "specialists-partners/data/providers.json": "specialists-partners/data/providers.json",
        "specialists-partners/data/provider.schema.json": "specialists-partners/data/provider.schema.json",
        "api/v1/specialists-partners.json": "api/v1/specialists-partners.json",
        "api/specialists-partners-quality-v354.json": "api/specialists-partners-quality-v354.json",
        "api/v1/platform.json": "api/v1/platform.json",
        "sitemap-specialists-partners.xml": "sitemap-specialists-partners.xml",
        "robots.txt": "robots.txt",
        "assets/platform/platform-core.js": "assets/platform/platform-core.js",
    }

    local_sha, local_source = receipt_candidate(receipt_path)
    for attempt in range(1, attempts + 1):
        try:
            candidate_sha, candidate_source = (local_sha, local_source)
            if not candidate_sha:
                candidate_sha, candidate_source = remote_candidate(base_url, attempt)
            sha_verified = False
            if candidate_sha:
                try:
                    sha_verified = sha_contains_minimum(candidate_sha, repository, token)
                except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
                    sha_verified = False

            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                cache_token = candidate_sha or f"content-{int(time.time())}-{attempt}"
                for relative, route in routes.items():
                    target = root / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(fetch_bytes(f"{base_url}{route}?v={cache_token}-{attempt}"))
                report = validate_root(root)
            return {
                **report,
                "live_commit": candidate_sha,
                "sha_source": candidate_source,
                "sha_contains_sector_merge": sha_verified,
                "publication_proof": "sha-and-content" if sha_verified else "live-content-contract",
                "attempt": attempt,
                "base_url": base_url,
            }
        except (
            AssertionError,
            OSError,
            urllib.error.URLError,
            urllib.error.HTTPError,
            json.JSONDecodeError,
        ) as error:
            last_error = error
            if attempt < attempts:
                time.sleep(delay)
    raise AssertionError(
        f"Live specialists-partners verification failed after {attempts} attempts: {last_error}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify the specialists and partners sector locally or on GitHub Pages."
    )
    parser.add_argument("--root", default=".", help="Local repository or artifact root")
    parser.add_argument("--live", action="store_true", help="Verify the public GitHub Pages deployment")
    parser.add_argument("--receipt-path", default="")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPOSITORY))
    parser.add_argument("--attempts", type=int, default=30)
    parser.add_argument("--delay", type=int, default=10)
    args = parser.parse_args()

    if args.live:
        result = validate_live(
            args.base_url,
            args.repository,
            os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"),
            args.attempts,
            args.delay,
            Path(args.receipt_path) if args.receipt_path else None,
        )
    else:
        result = validate_root(Path(args.root))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
