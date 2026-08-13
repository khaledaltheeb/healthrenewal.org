#!/usr/bin/env python3
"""Validate the complete capabilities publication before and after deployment.

The gate checks the 100-condition v280 library, the 50-condition v281
expansion, the registry and methodology surfaces, public metadata, direct
sources, sitemap coverage, and the absence of accidental duplicate/noindex
publication. It does not claim external clinical review.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from ensure_special_needs_publication_v1 import collect_inventory, validate_counts

BASE_URL = "https://healthrenewal.org"
REPORT_RELATIVE = Path("api/capabilities-production-gate-v1.json")
ARABIC_WORD_RE = re.compile(r"[\u0600-\u06ffA-Za-z0-9]+")
CANONICAL_RE = re.compile(
    r'<link\b(?=[^>]*\brel=["\'][^"\']*canonical[^"\']*["\'])[^>]*\bhref=["\']([^"\']+)["\'][^>]*>',
    re.I | re.S,
)
DESCRIPTION_RE = re.compile(
    r'<meta\b(?=[^>]*\bname=["\']description["\'])[^>]*\bcontent=["\']([^"\']+)["\'][^>]*>',
    re.I | re.S,
)
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
    descriptions = [value.strip() for value in DESCRIPTION_RE.findall(text) if value.strip()]
    if not descriptions:
        issues.append("missing_description")
    canonicals = canonical_values(text)
    if not canonicals:
        issues.append("missing_canonical")
    elif expected not in canonicals:
        issues.append("canonical_mismatch")
    if len(set(canonicals)) > 1:
        issues.append("conflicting_canonicals")
    if ROBOTS_NOINDEX_RE.search(text):
        issues.append("noindex")
    if 'application/ld+json' not in text:
        issues.append("missing_json_ld")
    if "khaledaltheeb.github.io/pterminology-site" in text:
        issues.append("legacy_canonical_origin")
    return issues


def load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected object in {path}")
    return value


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
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        failures["missing_or_invalid_reports"] = str(exc)
        v280, v281, source = {}, {}, {}

    if v280:
        expected_v280 = {
            "version": 280,
            "status": "passed",
            "condition_count": 100,
            "detailed_guide_count": 100,
        }
        mismatches = {
            key: {"expected": expected, "actual": v280.get(key)}
            for key, expected in expected_v280.items()
            if v280.get(key) != expected
        }
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
        mismatches = {
            key: {"expected": expected, "actual": v281.get(key)}
            for key, expected in expected_v281.items()
            if v281.get(key) != expected
        }
        if mismatches:
            failures["v281_contract"] = mismatches
        if int(v281.get("minimum_page_word_count", 0) or 0) < minimum_v281_words:
            failures["v281_minimum_page_word_count"] = {
                "expected": minimum_v281_words,
                "actual": v281.get("minimum_page_word_count"),
            }
        raw_slugs = v281.get("slugs", [])
        if isinstance(raw_slugs, list):
            slugs = [str(item) for item in raw_slugs]
        if len(slugs) != 50 or len(set(slugs)) != 50:
            failures["v281_slugs"] = {"count": len(slugs), "unique": len(set(slugs))}

    source_conditions = source.get("conditions", []) if source else []
    source_map: dict[str, dict[str, object]] = {}
    if isinstance(source_conditions, list):
        for item in source_conditions:
            if isinstance(item, dict) and item.get("slug"):
                source_map[str(item["slug"])] = item
    if source and len(source_map) != 50:
        failures["source_condition_count"] = len(source_map)

    source_urls = [str(item.get("source_url", "")) for item in source_map.values()]
    if source_urls:
        if len(set(source_urls)) != 50 or not all(url.startswith("https://") for url in source_urls):
            failures["source_urls"] = {
                "count": len(source_urls),
                "unique": len(set(source_urls)),
                "invalid": sorted(url for url in source_urls if not url.startswith("https://")),
            }

    evidence = source.get("evidence_overrides", {}) if source else {}
    reviewed_conditions = int(evidence.get("applied", 0) or 0) if isinstance(evidence, dict) else 0
    if reviewed_conditions < 42:
        failures["reviewed_condition_floor"] = {"minimum": 42, "actual": reviewed_conditions}
    if reviewed_conditions < 50:
        warnings["conditions_without_evidence_override"] = 50 - reviewed_conditions

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

    sitemap_urls: set[str] = set()
    for sitemap in sorted(root.glob("sitemap*.xml")):
        text = sitemap.read_text(encoding="utf-8", errors="replace")
        sitemap_urls.update(value.strip().rstrip("/") for value in re.findall(r"<loc>(.*?)</loc>", text, re.I | re.S))
    sitemap_missing = [route for route in public_routes if (BASE_URL + route).rstrip("/") not in sitemap_urls]
    aliases_in_sitemap = [route for route in aliases if (BASE_URL + route).rstrip("/") in sitemap_urls]
    if sitemap_missing:
        failures["sitemap_missing_routes"] = sitemap_missing
    if aliases_in_sitemap:
        failures["redirect_aliases_in_sitemap"] = aliases_in_sitemap

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
        registry_issues = validate_public_page(registry_text, "/capabilities/registry/", minimum_words=1000)
        if registry_issues:
            failures["registry"] = registry_issues

    source_domains = Counter(urlparse(url).netloc for url in source_urls if url)
    status = "passed" if not failures else "failed"
    report: dict[str, object] = {
        "schemaVersion": 1,
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
        "sourceDomains": dict(sorted(source_domains.items())),
        "warnings": warnings,
        "failures": failures,
    }
    destination = root / REPORT_RELATIVE
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
