from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://healthrenewal.org"
MANIFEST = ROOT / "data/addiction-atlas/substance-waves.json"
COMPARISONS = ROOT / "data/addiction-atlas/comparison-intents-v2.json"
SITEMAP = ROOT / "sitemap-addiction-atlas.xml"

STATIC_URLS = [
    f"{ORIGIN}/addiction/substances/methodology/",
    f"{ORIGIN}/addiction/substances/data/",
    f"{ORIGIN}/addiction/substances/classes/",
    f"{ORIGIN}/addiction/substances/learn/",
]
CLASS_SLUGS = [
    "opioids",
    "stimulants",
    "sedatives",
    "cannabinoids",
    "dissociatives",
    "psychedelics",
    "inhalants",
    "nps",
]
LEARN_SLUGS = [
    "addiction-dependence-tolerance",
    "overdose",
    "withdrawal",
    "polysubstance-risk",
    "evidence-strength",
    "lower-risk-not-safe",
    "mortality-data",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def iso_date(value: str, label: str) -> str:
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        raise SystemExit(f"{label} must be an ISO date, got {value!r}")
    return value


def existing_lastmods() -> dict[str, str]:
    if not SITEMAP.is_file():
        return {}
    root = ET.parse(SITEMAP).getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    result: dict[str, str] = {}
    for node in root.findall("sm:url", ns):
        loc = node.findtext("sm:loc", namespaces=ns)
        lastmod = node.findtext("sm:lastmod", namespaces=ns)
        if loc and lastmod:
            result[loc] = lastmod
    return result


def latest(values: list[str]) -> str:
    if not values:
        raise SystemExit("cannot compute latest date from an empty list")
    return max(values)


def main() -> None:
    old = existing_lastmods()
    manifest = load(MANIFEST)
    routes = manifest.get("waves") or []
    if not routes:
        raise SystemExit("empty addiction atlas wave manifest")

    substance_lastmods: dict[str, str] = {}
    wave_dates: list[str] = []
    for route in routes:
        path = ROOT / route.lstrip("/")
        if not path.is_file():
            raise SystemExit(f"missing registered wave: {route}")
        payload = load(path)
        updated_on = iso_date(payload.get("updated_on"), f"{path.name}.updated_on")
        wave_dates.append(updated_on)
        for item in payload.get("substances", []):
            slug = item.get("slug")
            if not slug:
                raise SystemExit(f"missing substance slug in {path.name}")
            if slug in substance_lastmods:
                raise SystemExit(f"duplicate substance slug: {slug}")
            substance_lastmods[slug] = updated_on

    comparison_payload = load(COMPARISONS)
    comparison_date = iso_date(
        comparison_payload.get("updated_on"),
        f"{COMPARISONS.name}.updated_on",
    )
    comparisons = [
        item for item in comparison_payload.get("comparisons", []) if item.get("indexable")
    ]

    atlas_date = latest(wave_dates)
    records: list[tuple[str, str]] = [
        (f"{ORIGIN}/addiction/substances/", atlas_date),
        (f"{ORIGIN}/addiction/compare/", comparison_date),
    ]

    # Static editorial hubs keep their previously published lastmod unless their
    # own content is explicitly regenerated. This avoids falsely refreshing every
    # URL whenever a new evidence wave is added.
    for url in STATIC_URLS:
        records.append((url, old.get(url, "2026-08-25")))
    for slug in CLASS_SLUGS:
        url = f"{ORIGIN}/addiction/substances/classes/{slug}/"
        records.append((url, old.get(url, "2026-08-25")))
    for slug in LEARN_SLUGS:
        url = f"{ORIGIN}/addiction/substances/learn/{slug}/"
        records.append((url, old.get(url, "2026-08-25")))

    for slug, updated_on in sorted(substance_lastmods.items()):
        records.append((f"{ORIGIN}/addiction/substances/{slug}/", updated_on))
    for item in comparisons:
        records.append((f"{ORIGIN}/addiction/compare/{item['slug']}/", comparison_date))

    urls = [url for url, _ in records]
    if len(urls) != len(set(urls)):
        raise SystemExit("duplicate URL generated for addiction atlas sitemap")

    for url, _ in records:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "healthrenewal.org":
            raise SystemExit(f"invalid sitemap URL: {url}")
        route = parsed.path.strip("/")
        local = ROOT / route / "index.html"
        if not local.is_file():
            raise SystemExit(f"sitemap URL has no static page: {url} -> {local}")

    urlset = ET.Element("urlset", {"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"})
    for url, lastmod in records:
        node = ET.SubElement(urlset, "url")
        ET.SubElement(node, "loc").text = url
        ET.SubElement(node, "lastmod").text = lastmod
    ET.indent(urlset, space="  ")
    ET.ElementTree(urlset).write(SITEMAP, encoding="utf-8", xml_declaration=True)

    print(
        json.dumps(
            {
                "atlasSitemapUrls": len(records),
                "substances": len(substance_lastmods),
                "registeredWaves": len(routes),
                "indexableComparisons": len(comparisons),
                "atlasLastmod": atlas_date,
                "comparisonLastmod": comparison_date,
                "preservedStaticLastmods": sum(1 for url in STATIC_URLS if url in old),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
