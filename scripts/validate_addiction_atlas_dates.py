from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/addiction-atlas/substance-waves.json"
COMPARISONS = ROOT / "data/addiction-atlas/comparison-intents-v2.json"
COMPARISON_DATES = ROOT / "data/addiction-atlas/comparison-dates-v1.json"
SITEMAP = ROOT / "sitemap-addiction-atlas.xml"
PROJECT_TODAY = datetime.now(ZoneInfo("Asia/Amman")).date()

AR_MONTHS = {
    1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
    7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_iso(value: str, label: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise AssertionError(f"{label}: invalid ISO date {value!r}")
    if parsed > PROJECT_TODAY:
        raise AssertionError(f"{label}: date is in the future relative to Asia/Amman: {value}")
    return parsed


def arabic_date(value: str) -> str:
    parsed = parse_iso(value, "display date")
    return f"{parsed.day} {AR_MONTHS[parsed.month]} {parsed.year}"


def sitemap_dates() -> dict[str, str]:
    root = ET.parse(SITEMAP).getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    result: dict[str, str] = {}
    for node in root.findall("sm:url", ns):
        loc = node.findtext("sm:loc", namespaces=ns)
        lastmod = node.findtext("sm:lastmod", namespaces=ns)
        if not loc or not lastmod:
            raise AssertionError("sitemap URL missing loc or lastmod")
        parse_iso(lastmod, f"sitemap {loc}")
        if loc in result:
            raise AssertionError(f"duplicate sitemap URL: {loc}")
        result[loc] = lastmod
    return result


def expected_substance_dates() -> dict[str, tuple[str, str]]:
    manifest = load(MANIFEST)
    result: dict[str, tuple[str, str]] = {}
    for route in manifest.get("waves") or []:
        path = ROOT / route.lstrip("/")
        payload = load(path)
        updated_on = payload.get("updated_on")
        parse_iso(updated_on, f"{path.name}.updated_on")
        for item in payload.get("substances", []):
            slug = item["slug"]
            if slug in result:
                raise AssertionError(f"duplicate substance slug: {slug}")
            result[slug] = (updated_on, item["display_name_ar"])
    return result


def expected_comparison_dates() -> dict[str, tuple[str, str]]:
    comparisons = {
        item["slug"]: item
        for item in (load(COMPARISONS).get("comparisons") or [])
        if item.get("indexable")
    }
    date_payload = load(COMPARISON_DATES)
    baseline = date_payload.get("baseline_updated_on")
    parse_iso(baseline, f"{COMPARISON_DATES.name}.baseline_updated_on")
    overrides = date_payload.get("overrides") or {}
    unknown = sorted(set(overrides) - set(comparisons))
    if unknown:
        raise AssertionError(f"comparison date overrides reference unknown slugs: {unknown}")
    for slug, value in overrides.items():
        parse_iso(value, f"comparison override {slug}")

    result: dict[str, tuple[str, str]] = {}
    for slug, item in comparisons.items():
        result[slug] = (overrides.get(slug, baseline), item["title_ar"])
    return result


def validate_page(path: Path, *, url: str, updated_on: str) -> None:
    if not path.is_file():
        raise AssertionError(f"missing page: {path}")
    page = path.read_text(encoding="utf-8")
    expected_display = arabic_date(updated_on)
    if expected_display not in page:
        raise AssertionError(f"visible last-update date mismatch: {path} expected {expected_display}")
    if not re.search(rf'"dateModified"\s*:\s*"{re.escape(updated_on)}"', page):
        raise AssertionError(f"structured dateModified mismatch: {path} expected {updated_on}")
    if f'"url":"{url}"' not in page and f'"url": "{url}"' not in page:
        raise AssertionError(f"structured WebPage URL missing or mismatched: {path}")


def main() -> None:
    sitemap = sitemap_dates()
    substances = expected_substance_dates()
    comparisons = expected_comparison_dates()

    for slug, (updated_on, _) in substances.items():
        url = f"https://healthrenewal.org/addiction/substances/{slug}/"
        if sitemap.get(url) != updated_on:
            raise AssertionError(f"substance sitemap lastmod mismatch: {slug}: {sitemap.get(url)} != {updated_on}")
        validate_page(
            ROOT / "addiction/substances" / slug / "index.html",
            url=url,
            updated_on=updated_on,
        )

    for slug, (updated_on, _) in comparisons.items():
        url = f"https://healthrenewal.org/addiction/compare/{slug}/"
        if sitemap.get(url) != updated_on:
            raise AssertionError(f"comparison sitemap lastmod mismatch: {slug}: {sitemap.get(url)} != {updated_on}")
        validate_page(
            ROOT / "addiction/compare" / slug / "index.html",
            url=url,
            updated_on=updated_on,
        )

    atlas_hub = "https://healthrenewal.org/addiction/substances/"
    compare_hub = "https://healthrenewal.org/addiction/compare/"
    latest_wave = max(value for value, _ in substances.values())
    comparison_hub_date = load(COMPARISONS).get("updated_on")
    parse_iso(comparison_hub_date, f"{COMPARISONS.name}.updated_on")
    if sitemap.get(atlas_hub) != latest_wave:
        raise AssertionError(f"atlas hub lastmod mismatch: {sitemap.get(atlas_hub)} != {latest_wave}")
    if sitemap.get(compare_hub) != comparison_hub_date:
        raise AssertionError(f"compare hub lastmod mismatch: {sitemap.get(compare_hub)} != {comparison_hub_date}")

    print(
        json.dumps(
            {
                "status": "passed",
                "substanceDatesValidated": len(substances),
                "comparisonDatesValidated": len(comparisons),
                "sitemapUrls": len(sitemap),
                "atlasHubLastmod": latest_wave,
                "compareHubLastmod": comparison_hub_date,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
