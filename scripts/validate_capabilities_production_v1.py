#!/usr/bin/env python3
"""Validate the complete capabilities publication before and after deployment.

The gate checks the 100-condition v280 library, the 50-condition v281
expansion, registry/methodology surfaces, direct sources, final on-page SEO,
structured data, sitemap coverage and the absence of accidental duplicate or
noindex publication. It does not claim external clinical review.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from ensure_special_needs_publication_v1 import collect_inventory, validate_counts

BASE_URL = "https://healthrenewal.org"
REPORT_RELATIVE = Path("api/capabilities-production-gate-v1.json")
SEO_REPORT_RELATIVE = Path("api/capabilities-seo-v1.json")
CAPABILITY_HUB_ROUTES = {
    "/capabilities/",
    "/capabilities/registry/",
    "/capabilities/expanded/",
    "/capabilities/methodology/",
    "/capabilities/behavioral-disorders/",
    "/capabilities/developmental-disorders/",
    "/capabilities/hearing-loss/",
    "/capabilities/intellectual-disabilities/",
    "/capabilities/learning-disabilities/",
}
ARABIC_WORD_RE = re.compile(r"[\u0600-\u06ffA-Za-z0-9]+")
CANONICAL_RE = re.compile(
    r'<link\b(?=[^>]*\brel=["\'][^"\']*canonical[^"\']*["\'])[^>]*\bhref=["\']([^"\']+)["\'][^>]*>',
    re.I | re.S,
)
DESCRIPTION_RE = re.compile(
    r'<meta\b(?=[^>]*\bname=["\']description["\'])[^>]*\bcontent=["\']([^"\']+)["\'][^>]*>',
    re.I | re.S,
)
TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.I | re.S)
ROBOTS_NOINDEX_RE = re.compile(
    r'<meta\b(?=[^>]*\bname=["\']robots["\'])[^>]*\bcontent=["\'][^"\']*noindex[^"\']*["\'][^>]*>',
    re.I | re.S,
)
REFRESH_RE = re.compile(r'<meta\b[^>]*http-equiv=["\']?refresh["\']?[^>]*>', re.I | re.S)
JS_REDIRECT_RE = re.compile(r'\b(?:location\.(?:replace|assign)|location\s*=|window\.location)\b', re.I)


def normalize_route(url: str) -> str:
    path = urlparse(url.strip()).path.strip("/")
    return f"/{path}/" if path else "/"


def page_path(root: Path, route: str) -> Path:
    return root / route.strip("/") / "index.html"


def word_count(text: str) -> int:
    plain = re.sub(r"<[^>]+>", " ", text)
    return len(ARABIC_WORD_RE.findall(plain))


def canonical_values(text: str) -> list[str]:
    return [value.strip().rstrip("/") for value in CANONICAL_RE.findall(text) if value.strip()]


def redirect_target(text: str, route: str) -> str | None:
    if not ROBOTS_NOINDEX_RE.search(text):
        return None
    canonicals = canonical_values(text)
    if len(canonicals) != 1:
        return None
    target = normalize_route(canonicals[0])
    if target == route or not (REFRESH_RE.search(text) or JS_REDIRECT_RE.search(text)):
        return None
    return target


def validate_public_page(text: str, route: str, *, minimum_words: int = 250) -> list[str]:
    issues: list[str] = []
    expected = (BASE_URL + route).rstrip("/")
    if len(text.encode("utf-8")) < 500:
        issues.append("too_small")
    if word_count(text) < minimum_words:
        issues.append("too_few_words")

    h1_count = len(re.findall(r"<h1\b", text, re.I))
    if h1_count != 1:
        issues.append(f"h1_count:{h1_count}")
    if len(re.findall(r"<h2\b", text, re.I)) < 1:
        issues.append("missing_h2")

    titles = [html.unescape(re.sub(r"<[^>]+>", " ", value)).strip() for value in TITLE_RE.findall(text)]
    titles = [value for value in titles if value]
    if not titles:
        issues.append("missing_title")
    elif len(titles) != 1:
        issues.append("multiple_titles")
    elif len(titles[0]) > 90:
        issues.append("title_too_long")

    descriptions = [html.unescape(value).strip() for value in DESCRIPTION_RE.findall(text) if value.strip()]
    if not descriptions:
        issues.append("missing_description")
    elif len(descriptions[0]) < 110:
        issues.append("short_description")

    canonicals = canonical_values(text)
    if not canonicals:
        issues.append("missing_canonical")
    elif expected not in canonicals:
        issues.append("canonical_mismatch")
    if len(set(canonicals)) > 1:
        issues.append("conflicting_canonicals")

    if ROBOTS_NOINDEX_RE.search(text):
        issues.append("noindex")
    if "application/ld+json" not in text:
        issues.append("missing_json_ld")
    if "BreadcrumbList" not in text:
        issues.append("missing_breadcrumb_schema")

    required_social = {
        "og_title": r'<meta\b(?=[^>]*\bproperty=["\']og:title["\'])',
        "og_description": r'<meta\b(?=[^>]*\bproperty=["\']og:description["\'])',
        "og_url": r'<meta\b(?=[^>]*\bproperty=["\']og:url["\'])',
        "og_image": r'<meta\b(?=[^>]*\bproperty=["\']og:image["\'])',
        "twitter_card": r'<meta\b(?=[^>]*\bname=["\']twitter:card["\'])[^>]*\bcontent=["\']summary_large_image["\']',
        "twitter_title": r'<meta\b(?=[^>]*\bname=["\']twitter:title["\'])',
        "twitter_description": r'<meta\b(?=[^>]*\bname=["\']twitter:description["\'])',
        "twitter_image": r'<meta\b(?=[^>]*\bname=["\']twitter:image["\'])',
    }
    for label, pattern in required_social.items():
        if not re.search(pattern, text, re.I | re.S):
            issues.append(f"missing_{label}")

    if "khaledaltheeb.github.io/pterminology-site" in text or "/pterminology-site/" in text:
        issues.append("legacy_internal_origin")
    return issues


def load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected object in {path}")
    return value


def sitemap_records(root: Path) -> tuple[set[str], set[str]]:
    urls: set[str] = set()
    with_lastmod: set[str] = set()
    for sitemap in sorted(root.glob("sitemap*.xml")):
        text = sitemap.read_text(encoding="utf-8", errors="replace")
        for block in re.findall(r"<url\b[^>]*>(.*?)</url>", text, re.I | re.S):
            loc = re.search(r"<loc>(.*?)</loc>", block, re.I | re.S)
            if not loc:
                continue
            url = html.unescape(loc.group(1)).strip().rstrip("/")
            urls.add(url)
            if re.search(r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>", block, re.I):
                with_lastmod.add(url)
        urls.update(
            html.unescape(value).strip().rstrip("/")
            for value in re.findall(r"<loc>(.*?)</loc>", text, re.I | re.S)
        )
    return urls, with_lastmod


def run(root: Path, *, minimum_v281_words: int = 1300) -> dict[str, object]:
    root = root.resolve()
    inventory = collect_inventory(root)
    count_failures = validate_counts(inventory.counts)
    failures: dict[str, object] = {}
    warnings: dict[str, object] = {}

    if count_failures:
        failures["count_failures"] = count_failures
    if inventory.missing_roots:
        failures["missing_roots"] = inventory.missing_roots

    try:
        v280 = load_json(root / "api" / "capabilities-v280.json")
        v281 = load_json(root / "api" / "capabilities-v281.json")
        source = load_json(root / "api" / "capabilities-v281-source.json")
        seo = load_json(root / SEO_REPORT_RELATIVE)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        failures["missing_or_invalid_reports"] = str(exc)
        v280, v281, source, seo = {}, {}, {}, {}

    if v280:
        expected_v280 = {"version": 280, "status": "passed", "condition_count": 100, "detailed_guide_count": 100}
        mismatches = {key: {"expected": expected, "actual": v280.get(key)} for key, expected in expected_v280.items() if v280.get(key) != expected}
        if mismatches:
            failures["v280_contract"] = mismatches

    slugs: list[str] = []
    if v281:
        expected_v281 = {
            "version": 281,
            "status": "passed",
            "condition_count": 50,
            "detail_page_count": 50,
            "generated_page_count": 51,
            "sitemap_url_count": 51,
            "source_count": 50,
            "unique_source_count": 50,
            "external_clinical_review_completed": False,
            "diagnostic_automation": False,
        }
        mismatches = {key: {"expected": expected, "actual": v281.get(key)} for key, expected in expected_v281.items() if v281.get(key) != expected}
        if mismatches:
            failures["v281_contract"] = mismatches
        if int(v281.get("minimum_page_word_count", 0) or 0) < minimum_v281_words:
            failures["v281_minimum_page_word_count"] = {"expected": minimum_v281_words, "actual": v281.get("minimum_page_word_count")}
        raw_slugs = v281.get("slugs", [])
        if isinstance(raw_slugs, list):
            slugs = [str(item) for item in raw_slugs]
        if len(slugs) != 50 or len(set(slugs)) != 50:
            failures["v281_slugs"] = {"count": len(slugs), "unique": len(set(slugs))}

    if seo:
        if seo.get("status") != "passed":
            failures["seo_gate_status"] = seo
        if int(seo.get("pages_processed", 0) or 0) < 155:
            failures["seo_page_coverage"] = seo.get("pages_processed")
        legacy_origin_count = seo.get("legacy_internal_origin_occurrences")
        if legacy_origin_count is None or int(legacy_origin_count) != 0:
            failures["seo_legacy_origin"] = legacy_origin_count

    source_conditions = source.get("conditions", []) if source else []
    source_map: dict[str, dict[str, object]] = {}
    if isinstance(source_conditions, list):
        for item in source_conditions:
            if isinstance(item, dict) and item.get("slug"):
                source_map[str(item["slug"])] = item
    if source and len(source_map) != 50:
        failures["source_condition_count"] = len(source_map)

    source_urls = [str(item.get("source_url", "")) for item in source_map.values()]
    if source_urls and (len(set(source_urls)) != 50 or not all(url.startswith("https://") for url in source_urls)):
        failures["source_urls"] = {
            "count": len(source_urls),
            "unique": len(set(source_urls)),
            "invalid": sorted(url for url in source_urls if not url.startswith("https://")),
        }

    evidence = source.get("evidence_overrides", {}) if source else {}
    reviewed_conditions = int(evidence.get("applied", 0) or 0) if isinstance(evidence, dict) else 0
    if reviewed_conditions < 50:
        failures["reviewed_condition_floor"] = {"minimum": 50, "actual": reviewed_conditions}

    public_routes: list[str] = []
    aliases: dict[str, str] = {}
    page_issues: dict[str, list[str]] = {}
    for route in inventory.routes.get("capability_pages", []):
        path = page_path(root, route)
        if not path.is_file():
            page_issues[route] = ["missing_file"]
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        target = redirect_target(text, route)
        if target:
            aliases[route] = target
            continue
        public_routes.append(route)
        issues = validate_public_page(text, route)
        if issues:
            page_issues[route] = issues
    if page_issues:
        failures["capability_page_issues"] = page_issues

    sitemap_urls, sitemap_urls_with_lastmod = sitemap_records(root)
    sitemap_missing = [route for route in public_routes if (BASE_URL + route).rstrip("/") not in sitemap_urls]
    aliases_in_sitemap = [route for route in aliases if (BASE_URL + route).rstrip("/") in sitemap_urls]
    if sitemap_missing:
        failures["sitemap_missing_routes"] = sitemap_missing
    if aliases_in_sitemap:
        failures["redirect_aliases_in_sitemap"] = aliases_in_sitemap

    # Only condition-guide routes require condition-level lastmod. Category and
    # navigation hubs are intentionally excluded from this contract.
    condition_routes = [
        route
        for route in public_routes
        if route.count("/") == 3 and route not in CAPABILITY_HUB_ROUTES
    ]
    no_lastmod = [
        route
        for route in condition_routes
        if (BASE_URL + route).rstrip("/") not in sitemap_urls_with_lastmod
    ]
    if no_lastmod:
        failures["condition_routes_without_lastmod"] = no_lastmod

    v281_page_issues: dict[str, list[str]] = {}
    for slug in slugs:
        route = f"/capabilities/{slug}/"
        path = page_path(root, route)
        if not path.is_file():
            v281_page_issues[slug] = ["missing_file"]
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        issues = validate_public_page(text, route, minimum_words=minimum_v281_words)
        source_item = source_map.get(slug, {})
        source_url = str(source_item.get("source_url", ""))
        if not source_url or source_url not in text:
            issues.append("direct_source_missing_from_page")
        if len(re.findall(r"<h2\b", text, re.I)) < 14:
            issues.append("insufficient_h2_depth")
        if "محتوى تثقيفي" not in text:
            issues.append("missing_educational_boundary")
        if issues:
            v281_page_issues[slug] = sorted(set(issues))
    if v281_page_issues:
        failures["v281_page_issues"] = v281_page_issues

    registry = root / "capabilities" / "registry" / "index.html"
    if not registry.is_file():
        failures["registry"] = "missing"
    else:
        registry_text = registry.read_text(encoding="utf-8", errors="replace")
        registry_issues = validate_public_page(
            registry_text,
            "/capabilities/registry/",
            minimum_words=1000,
        )
        if "150 حالة" not in registry_text:
            registry_issues.append("registry_count_not_150")
        if "100 حالة" in registry_text:
            registry_issues.append("stale_registry_count_100")
        if registry_issues:
            failures["registry"] = sorted(set(registry_issues))

    source_domains = Counter(urlparse(url).netloc for url in source_urls if url)
    status = "passed" if not failures else "failed"
    report: dict[str, object] = {
        "schemaVersion": 2,
        "status": status,
        "baseUrl": BASE_URL,
        "counts": inventory.counts,
        "v280ConditionCount": v280.get("condition_count") if v280 else None,
        "v281ConditionCount": v281.get("condition_count") if v281 else None,
        "v281MinimumPageWordCount": v281.get("minimum_page_word_count") if v281 else None,
        "reviewedConditionCount": reviewed_conditions,
        "publicCapabilityRouteCount": len(public_routes),
        "redirectAliasCount": len(aliases),
        "sitemapUrlCount": len(sitemap_urls),
        "sitemapConditionRoutesWithLastmod": len(condition_routes) - len(no_lastmod),
        "capabilityHubRouteCount": len([route for route in public_routes if route in CAPABILITY_HUB_ROUTES]),
        "seo": seo,
        "sourceDomains": dict(sorted(source_domains.items())),
        "warnings": warnings,
        "failures": failures,
    }
    destination = root / REPORT_RELATIVE
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if failures:
        raise SystemExit(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    parser.add_argument("--minimum-v281-words", type=int, default=1300)
    args = parser.parse_args()
    report = run(args.site, minimum_v281_words=args.minimum_v281_words)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())