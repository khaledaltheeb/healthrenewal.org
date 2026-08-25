from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
DATA_FILES = [
    ROOT / "data/addiction-atlas/substances-v1.json",
    ROOT / "data/addiction-atlas/substances-v2.json",
    ROOT / "data/addiction-atlas/substances-v3.json",
]
METHOD = ROOT / "data/addiction-atlas/methodology-v1.json"
COMPARISONS = ROOT / "data/addiction-atlas/comparison-intents-v2.json"
EPIDEMIOLOGY = ROOT / "data/addiction-atlas/epidemiology-v1.json"
MORTALITY = ROOT / "data/addiction-atlas/mortality-v1.json"
SOURCES = ROOT / "data/addiction-atlas/source-registry-v1.json"
SOURCE_MAPS = sorted((ROOT / "data/addiction-atlas").glob("source-map-v*.json"))
SITEMAP = ROOT / "sitemap-addiction-atlas.xml"

RISK_KEYS = {
    "acute_toxicity",
    "overdose_risk",
    "dependence",
    "withdrawal_medical_risk",
    "neuro_harm",
    "cardio_harm",
    "respiratory_harm",
    "polysubstance_risk",
}
SUPPORTED_CLAIMS = RISK_KEYS | {
    "mechanism",
    "single_exposure_harm",
    "emergency_response",
    "treatment",
    "withdrawal",
}
ALIAS_KEYS = (
    "english_name_ar_transliteration",
    "search_aliases_ar",
    "search_aliases_en",
    "common_misspellings_ar",
    "common_misspellings_en",
    "spacing_variants",
    "hyphenation_variants",
    "legacy_spellings",
)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def fail(message: str):
    raise AssertionError(message)


def visible_text(html: str) -> str:
    text = re.sub(r"(?is)<script\b.*?</script>", " ", html)
    text = re.sub(r"(?is)<style\b.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def validate_data():
    substances = {}
    for path in DATA_FILES:
        for item in load(path).get("substances", []):
            slug = item.get("slug")
            if not slug:
                fail(f"missing slug in {path}")
            if slug in substances:
                fail(f"duplicate substance slug: {slug}")
            substances[slug] = item
            for key in ("display_name_ar", "display_name_en", "class_ar", "summary_ar", "source_urls"):
                if not item.get(key):
                    fail(f"{slug}: missing {key}")
            if set(item.get("risk", {})) != RISK_KEYS:
                fail(f"{slug}: risk dimensions do not match methodology")
            for risk_key, value in item["risk"].items():
                if value is not None and (type(value) is not int or value < 1 or value > 5):
                    fail(f"{slug}: invalid {risk_key}={value!r}")
            for key in ALIAS_KEYS:
                values = item.get(key) or []
                normalized = [str(v).strip().casefold() for v in values if str(v).strip()]
                if len(normalized) != len(set(normalized)):
                    fail(f"{slug}: duplicate aliases within {key}")
            for url in item["source_urls"]:
                parsed = urlparse(url)
                if parsed.scheme != "https" or not parsed.netloc:
                    fail(f"{slug}: invalid source URL {url}")
    return substances


def validate_registry():
    sources = load(SOURCES).get("sources", [])
    source_ids = {s.get("id") for s in sources}
    if None in source_ids or "" in source_ids:
        fail("source registry contains a missing id")
    if len(source_ids) != len(sources):
        fail("duplicate source registry IDs")
    for source in sources:
        source_id = source["id"]
        for key in ("organization", "title", "source_type", "geography", "verified_on"):
            if not source.get(key):
                fail(f"{source_id}: missing registry field {key}")
        parsed = urlparse(source.get("url", ""))
        if parsed.scheme != "https" or not parsed.netloc:
            fail(f"invalid registry source URL: {source_id}")
        try:
            verified = date.fromisoformat(source["verified_on"])
        except ValueError:
            fail(f"{source_id}: verified_on must be ISO date")
        if verified > date.today():
            fail(f"{source_id}: verified_on cannot be in the future")
        year = source.get("publication_year")
        if year is not None and (type(year) is not int or year < 1900 or year > date.today().year):
            fail(f"{source_id}: invalid publication_year={year!r}")
    return source_ids


def validate_records(source_ids):
    for path in (EPIDEMIOLOGY, MORTALITY):
        payload = load(path)
        ids = set()
        for item in payload.get("records", []):
            if item["id"] in ids:
                fail(f"{path.name}: duplicate id {item['id']}")
            ids.add(item["id"])
            if not item.get("year") or not item.get("geography") or not item.get("definition_ar"):
                fail(f"{item['id']}: year/geography/definition required")
            if item.get("source_id") not in source_ids:
                fail(f"{item['id']}: unknown source_id {item.get('source_id')}")


def validate_source_maps(substances, source_ids):
    mapped = set()
    record_count = 0
    if not SOURCE_MAPS:
        fail("no source maps discovered")
    for path in SOURCE_MAPS:
        if not path.is_file():
            fail(f"missing source map: {path}")
        payload = load(path)
        records = payload.get("records") or []
        if not records:
            fail(f"empty source map: {path.name}")
        wave = payload.get("wave")
        wave_path = ROOT / f"data/addiction-atlas/substances-{wave}.json" if wave else None
        expected_wave_slugs = set()
        if wave_path and wave_path.is_file():
            expected_wave_slugs = {item["slug"] for item in load(wave_path).get("substances", [])}
        seen_in_map = set()
        for record in records:
            record_count += 1
            slug = record.get("substance_slug")
            if not slug or slug not in substances:
                fail(f"{path.name}: unknown substance_slug {slug!r}")
            if slug in seen_in_map:
                fail(f"{path.name}: duplicate source-map record for {slug}")
            seen_in_map.add(slug)
            mapped.add(slug)
            ids = record.get("source_ids") or []
            if not ids:
                fail(f"{path.name}:{slug}: at least one source_id required")
            if len(ids) != len(set(ids)):
                fail(f"{path.name}:{slug}: duplicate source_ids")
            unknown_sources = sorted(set(ids) - source_ids)
            if unknown_sources:
                fail(f"{path.name}:{slug}: unknown source_ids {unknown_sources}")
            supports = record.get("supports") or []
            if not supports:
                fail(f"{path.name}:{slug}: supports cannot be empty")
            if len(supports) != len(set(supports)):
                fail(f"{path.name}:{slug}: duplicate supports values")
            unknown_claims = sorted(set(supports) - SUPPORTED_CLAIMS)
            if unknown_claims:
                fail(f"{path.name}:{slug}: unsupported claim labels {unknown_claims}")
            substance_urls = set(substances[slug].get("source_urls") or [])
            registry_by_id = {s["id"]: s["url"] for s in load(SOURCES).get("sources", [])}
            for source_id in ids:
                registry_url = registry_by_id[source_id]
                if registry_url not in substance_urls:
                    fail(f"{path.name}:{slug}: registered source {source_id} is not present in substance source_urls")
        if expected_wave_slugs and seen_in_map != expected_wave_slugs:
            missing = sorted(expected_wave_slugs - seen_in_map)
            extra = sorted(seen_in_map - expected_wave_slugs)
            fail(f"{path.name}: source coverage mismatch missing={missing} extra={extra}")
    return {"mappedSubstances": len(mapped), "sourceMapRecords": record_count}


def validate_comparisons(substances):
    payload = load(COMPARISONS)
    slugs = set()
    pair_keys = set()
    comparisons = payload.get("comparisons", [])
    for c in comparisons:
        if c["a"] not in substances or c["b"] not in substances:
            fail(f"comparison {c.get('slug')}: unknown substance")
        pair = tuple(sorted((c["a"], c["b"])))
        if pair in pair_keys:
            fail(f"duplicate comparison pair: {pair}")
        pair_keys.add(pair)
        if c["slug"] in slugs:
            fail(f"duplicate comparison slug: {c['slug']}")
        slugs.add(c["slug"])
        if c["a"] == c["b"]:
            fail(f"comparison {c['slug']}: same substance on both sides")
        if c.get("indexable") and (not c.get("title_ar") or not c.get("intent_ar")):
            fail(f"comparison {c['slug']}: indexable page requires title and intent")
    return comparisons


def validate_no_hidden_keyword_patterns():
    roots = (ROOT / "addiction/substances", ROOT / "addiction/compare")
    for directory in roots:
        for path in directory.rglob("*.html"):
            page = path.read_text(encoding="utf-8").lower()
            if '<meta name="keywords"' in page:
                fail(f"meta keywords prohibited in atlas: {path}")
            if re.search(r'class="[^"]*(?:seo-keywords|hidden-keywords|keyword-cloud)[^"]*"', page):
                fail(f"keyword dump block prohibited: {path}")


def validate_sitemap():
    root = ElementTree.parse(SITEMAP).getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = []
    for node in root.findall("sm:url", ns):
        loc = node.findtext("sm:loc", namespaces=ns)
        lastmod = node.findtext("sm:lastmod", namespaces=ns)
        if not loc or not lastmod:
            fail("every atlas sitemap URL requires loc and lastmod")
        if loc in urls:
            fail(f"duplicate sitemap URL: {loc}")
        urls.append(loc)
        parsed = urlparse(loc)
        if parsed.scheme != "https" or parsed.netloc != "healthrenewal.org":
            fail(f"invalid sitemap origin: {loc}")
        route = parsed.path.strip("/")
        local = ROOT / route / "index.html" if route else ROOT / "index.html"
        if not local.is_file():
            fail(f"sitemap points to missing static page: {loc} -> {local}")
        page = local.read_text(encoding="utf-8")
        lower = page.lower()
        if re.search(r'<meta\s+name="robots"\s+content="[^"]*noindex', lower):
            fail(f"noindex URL present in sitemap: {loc}")
        canonical = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', page, flags=re.I)
        if not canonical:
            fail(f"missing canonical: {local}")
        if canonical.group(1).rstrip("/") != loc.rstrip("/"):
            fail(f"canonical mismatch: sitemap={loc} page={canonical.group(1)}")
        if 'meta name="description"' not in lower:
            fail(f"missing meta description: {local}")
        if "<h1" not in lower:
            fail(f"missing H1: {local}")
        words = len(visible_text(page).split())
        if words < 80:
            fail(f"thin atlas page: {local} ({words} visible words)")
    return urls


def main():
    method = load(METHOD)
    if set(method.get("risk_dimensions", {})) != RISK_KEYS:
        fail("methodology risk dimensions mismatch")
    source_ids = validate_registry()
    substances = validate_data()
    validate_records(source_ids)
    source_map_report = validate_source_maps(substances, source_ids)
    comparisons = validate_comparisons(substances)
    validate_no_hidden_keyword_patterns()
    sitemap_urls = validate_sitemap()
    report = {
        "status": "passed",
        "substances": len(substances),
        "comparisonIntents": len(comparisons),
        "sourceRegistryEntries": len(source_ids),
        "sourceMapRecords": source_map_report["sourceMapRecords"],
        "mappedSubstances": source_map_report["mappedSubstances"],
        "sitemapUrls": len(sitemap_urls),
        "unknownRiskValues": sum(1 for s in substances.values() for v in s["risk"].values() if v is None),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
