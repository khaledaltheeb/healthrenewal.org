#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://khaledaltheeb.github.io/pterminology-site"
INTEGRATION_SHA = "ce993959f283de4d374c8777c8446c5c26077e7d"
MANIFEST = ROOT / "content" / "v221" / "special-needs-guides-production-manifest-ar.json"
BANNED = re.compile(r"(?<!\w)(?:المعاقين|معاقين|المعاقون|معاقون|المعاقة|معاقة|المعاق|معاق)(?!\w)")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class VerificationError(RuntimeError):
    pass


def request_bytes(path: str, attempts: int = 6, timeout: int = 35) -> tuple[bytes, dict[str, str]]:
    url = f"{BASE}/{path.lstrip('/')}"
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        token = f"v236-{int(time.time())}-{attempt}"
        separator = "&" if "?" in url else "?"
        request = urllib.request.Request(
            f"{url}{separator}proof={token}",
            headers={
                "User-Agent": "pterminology-live-special-needs-v236",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Accept": "*/*",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = getattr(response, "status", response.getcode())
                data = response.read()
                headers = {key.lower(): value for key, value in response.headers.items()}
                if status != 200:
                    raise VerificationError(f"Unexpected HTTP status {status}: {url}")
                if not data:
                    raise VerificationError(f"Empty live response: {url}")
                return data, headers
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, VerificationError) as exc:
            last = exc
            if attempt < attempts:
                time.sleep(min(2 * attempt, 10))
    raise VerificationError(f"Failed to fetch {url}: {last}")


def request_text(path: str) -> tuple[str, dict[str, str]]:
    payload, headers = request_bytes(path)
    try:
        return payload.decode("utf-8"), headers
    except UnicodeDecodeError as exc:
        raise VerificationError(f"Live response is not UTF-8: {path}") from exc


def request_json(path: str) -> dict[str, Any]:
    text, _ = request_text(path)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise VerificationError(f"Invalid live JSON: {path}") from exc
    if not isinstance(data, dict):
        raise VerificationError(f"Expected JSON object: {path}")
    return data


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def assert_git_ancestry(live_sha: str) -> None:
    if not SHA_RE.fullmatch(live_sha):
        raise VerificationError(f"Invalid live deployment SHA: {live_sha!r}")
    if git("cat-file", "-e", f"{live_sha}^{{commit}}", check=False).returncode != 0:
        raise VerificationError(f"Live deployment commit is absent from checked-out history: {live_sha}")
    if git("merge-base", "--is-ancestor", INTEGRATION_SHA, live_sha, check=False).returncode != 0:
        raise VerificationError(
            f"Live deployment {live_sha} predates the 25-guide integration {INTEGRATION_SHA}"
        )
    if git("show-ref", "--verify", "--quiet", "refs/remotes/origin/main", check=False).returncode == 0:
        if git("merge-base", "--is-ancestor", live_sha, "origin/main", check=False).returncode != 0:
            raise VerificationError(f"Live deployment SHA is not an ancestor of current origin/main: {live_sha}")


def load_expected() -> tuple[dict[str, Any], list[str]]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    sources = manifest.get("source_files", [])
    if manifest.get("version") != 221 or manifest.get("status") != "production-integrated":
        raise VerificationError("Invalid local special-needs v221 production manifest")
    if len(sources) != 25 or len(sources) != len(set(sources)):
        raise VerificationError("Production manifest must contain 25 unique source paths")
    slugs: list[str] = []
    for relative in sources:
        path = ROOT / relative
        if not path.is_file():
            raise VerificationError(f"Missing local guide source: {relative}")
        data = json.loads(path.read_text(encoding="utf-8"))
        slug = data.get("slug")
        if not isinstance(slug, str) or not slug or slug in slugs:
            raise VerificationError(f"Invalid or duplicate slug in {relative}")
        slugs.append(slug)
    return manifest, slugs


def visible_contract(source: str, slug: str) -> dict[str, Any]:
    lower = source.lower()
    if len(source.encode("utf-8")) < 6000:
        raise VerificationError(f"Live guide is unexpectedly small: {slug}")
    if len(re.findall(r"<h1\b", source, flags=re.I)) != 1:
        raise VerificationError(f"Live guide does not contain exactly one H1: {slug}")
    required = (
        '<html lang="ar" dir="rtl">',
        'rel="canonical"',
        'application/ld+json',
        "مصادر",
        "محتوى تثقيفي",
    )
    missing = [marker for marker in required if marker not in source]
    if missing:
        raise VerificationError(f"Live guide is missing required markers {missing}: {slug}")
    if "noindex" in lower:
        raise VerificationError(f"Live guide is noindex: {slug}")
    if BANNED.search(source):
        raise VerificationError(f"Live guide contains prohibited person-label language: {slug}")
    return {
        "slug": slug,
        "bytes": len(source.encode("utf-8")),
        "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "h2": len(re.findall(r"<h2\b", source, flags=re.I)),
        "citations": source.count("data-citation"),
    }


def verify(output: Path | None = None) -> dict[str, Any]:
    _, expected_slugs = load_expected()

    deployment = request_json("deployment.json")
    live_sha = str(deployment.get("commit", ""))
    if deployment.get("schema_version") != 29:
        raise VerificationError(f"Unexpected live deployment schema: {deployment}")
    assert_git_ancestry(live_sha)

    report = request_json("api/special-needs-guides-v221.json")
    report_slugs = report.get("guide_slugs")
    expected_set = set(expected_slugs)
    if report.get("version") != 221 or report.get("status") != "passed":
        raise VerificationError(f"Live special-needs production report failed: {report}")
    if report.get("production_status") != "integrated":
        raise VerificationError(f"Live special-needs production status is not integrated: {report}")
    if report.get("guide_count") != 25 or report.get("batch_count") != 5:
        raise VerificationError(f"Live special-needs guide/batch counts are wrong: {report}")
    if report.get("production_source_file_count") != 25:
        raise VerificationError(f"Live production source count is wrong: {report}")
    if not isinstance(report_slugs, list) or set(report_slugs) != expected_set or len(report_slugs) != 25:
        raise VerificationError("Live report guide slugs do not match the production manifest")
    if report.get("external_review_completed") is not False:
        raise VerificationError("Live report makes an unsupported external-review claim")

    sitemap_text, _ = request_text("sitemap-special-needs.xml")
    try:
        root = ET.fromstring(sitemap_text)
    except ET.ParseError as exc:
        raise VerificationError("Live special-needs sitemap is malformed") from exc
    locs = {(node.text or "").strip() for node in root.findall(".//{*}loc")}
    expected_urls = {f"{BASE}/special-needs/"} | {
        f"{BASE}/special-needs/{slug}/" for slug in expected_slugs
    }
    missing_urls = sorted(expected_urls - locs)
    if missing_urls:
        raise VerificationError(f"Live special-needs sitemap misses routes: {missing_urls}")
    if len([url for url in locs if url.startswith(f"{BASE}/special-needs/")]) < 26:
        raise VerificationError("Live special-needs sitemap contains fewer than 26 hub/guide routes")

    robots, _ = request_text("robots.txt")
    sitemap_line = f"Sitemap: {BASE}/sitemap-special-needs.xml"
    if robots.count(sitemap_line) != 1:
        raise VerificationError("Live robots.txt must register the special-needs sitemap exactly once")

    hub, hub_headers = request_text("special-needs/")
    if len(hub.encode("utf-8")) < 25000:
        raise VerificationError("Live special-needs hub is unexpectedly small")
    if len(re.findall(r"<h1\b", hub, flags=re.I)) != 1:
        raise VerificationError("Live special-needs hub must contain exactly one H1")
    if "noindex" in hub.lower():
        raise VerificationError("Live special-needs hub is noindex")
    if '<section><h2>مصادر الوحدة الحالية</h2>' not in hub:
        raise VerificationError("Live special-needs hub is missing the guide injection marker")
    missing_hub_links = [
        slug for slug in expected_slugs
        if f"/pterminology-site/special-needs/{slug}/" not in hub
    ]
    if missing_hub_links:
        raise VerificationError(f"Live hub misses guide links: {missing_hub_links}")
    if BANNED.search(hub):
        raise VerificationError("Live special-needs hub contains prohibited person-label language")

    pages: list[dict[str, Any]] = []
    for slug in expected_slugs:
        source, headers = request_text(f"special-needs/{slug}/")
        evidence = visible_contract(source, slug)
        evidence["content_type"] = headers.get("content-type", "")
        pages.append(evidence)

    result = {
        "version": 236,
        "status": "passed",
        "base_url": BASE,
        "deployment": {
            "commit": live_sha,
            "schema_version": deployment["schema_version"],
            "validated_at": deployment.get("validated_at"),
            "workflow_run": deployment.get("workflow_run"),
            "contains_25_guide_integration": True,
            "integration_sha": INTEGRATION_SHA,
        },
        "production_report": {
            "version": report["version"],
            "status": report["status"],
            "guide_count": report["guide_count"],
            "batch_count": report["batch_count"],
            "production_source_file_count": report["production_source_file_count"],
            "external_review_completed": report["external_review_completed"],
        },
        "live": {
            "hub_status": 200,
            "hub_bytes": len(hub.encode("utf-8")),
            "hub_sha256": hashlib.sha256(hub.encode("utf-8")).hexdigest(),
            "hub_content_type": hub_headers.get("content-type", ""),
            "robots_child_sitemap_count": robots.count(sitemap_line),
            "sitemap_special_needs_routes": len(
                [url for url in locs if url.startswith(f"{BASE}/special-needs/")]
            ),
            "guide_pages_verified": len(pages),
            "minimum_guide_bytes": min(page["bytes"] for page in pages),
            "minimum_guide_h2": min(page["h2"] for page in pages),
            "guide_page_evidence": pages,
        },
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(args.output.resolve() if args.output else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
