from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/addiction-atlas/substance-waves.json"
COMPARISONS = ROOT / "data/addiction-atlas/comparison-intents-v2.json"
COMPARISON_DATES = ROOT / "data/addiction-atlas/comparison-dates-v1.json"

AR_MONTHS = {
    1: "يناير",
    2: "فبراير",
    3: "مارس",
    4: "أبريل",
    5: "مايو",
    6: "يونيو",
    7: "يوليو",
    8: "أغسطس",
    9: "سبتمبر",
    10: "أكتوبر",
    11: "نوفمبر",
    12: "ديسمبر",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_iso(value: str, label: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise SystemExit(f"{label} must be an ISO date, got {value!r}")


def arabic_date(value: str) -> str:
    parsed = parse_iso(value, "date")
    return f"{parsed.day} {AR_MONTHS[parsed.month]} {parsed.year}"


def replace_visible_lastmod(page: str, value: str) -> tuple[str, bool]:
    desired = arabic_date(value)
    pattern = r"(آخر تحديث\s+)(\d{1,2}\s+[اأإآء-ي]+\s+\d{4})"
    updated, count = re.subn(pattern, lambda m: m.group(1) + desired, page)
    return updated, bool(count)


def upsert_webpage_schema(page: str, *, name: str, url: str, value: str) -> tuple[str, bool]:
    # Prefer updating the existing dateModified in atlas-generated structured data.
    updated, count = re.subn(
        r'("dateModified"\s*:\s*")\d{4}-\d{2}-\d{2}(\")',
        lambda m: m.group(1) + value + m.group(2),
        page,
        count=1,
    )
    if count:
        return updated, True

    schema = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "inLanguage": "ar",
            "name": name,
            "url": url,
            "dateModified": value,
            "publisher": {
                "@type": "Organization",
                "name": "منصة روافد",
                "url": "https://healthrenewal.org/",
            },
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    marker = "</head>"
    if marker not in page:
        raise SystemExit(f"cannot insert structured data; missing </head> for {url}")
    return page.replace(marker, f'<script type="application/ld+json">{schema}</script>{marker}', 1), True


def substance_dates() -> dict[str, tuple[str, str]]:
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
                raise SystemExit(f"duplicate substance slug: {slug}")
            result[slug] = (updated_on, item["display_name_ar"])
    return result


def comparison_overrides() -> dict[str, tuple[str, str]]:
    comparisons = load(COMPARISONS).get("comparisons") or []
    by_slug = {item["slug"]: item for item in comparisons if item.get("indexable")}
    dates = load(COMPARISON_DATES)
    overrides = dates.get("overrides") or {}
    result: dict[str, tuple[str, str]] = {}
    for slug, updated_on in overrides.items():
        parse_iso(updated_on, f"comparison date {slug}")
        if slug not in by_slug:
            raise SystemExit(f"comparison date override references unknown slug: {slug}")
        result[slug] = (updated_on, by_slug[slug]["title_ar"])
    return result


def patch_page(path: Path, *, name: str, url: str, updated_on: str) -> bool:
    if not path.is_file():
        raise SystemExit(f"missing atlas page: {path}")
    original = path.read_text(encoding="utf-8")
    page, _ = replace_visible_lastmod(original, updated_on)
    page, _ = upsert_webpage_schema(page, name=name, url=url, value=updated_on)
    if page == original:
        return False
    path.write_text(page, encoding="utf-8")
    return True


def main() -> None:
    changed_substances = 0
    for slug, (updated_on, name) in substance_dates().items():
        path = ROOT / "addiction/substances" / slug / "index.html"
        changed_substances += int(
            patch_page(
                path,
                name=f"{name} | أطلس المواد والإدمان | روافد",
                url=f"https://healthrenewal.org/addiction/substances/{slug}/",
                updated_on=updated_on,
            )
        )

    changed_comparisons = 0
    for slug, (updated_on, title) in comparison_overrides().items():
        path = ROOT / "addiction/compare" / slug / "index.html"
        changed_comparisons += int(
            patch_page(
                path,
                name=title,
                url=f"https://healthrenewal.org/addiction/compare/{slug}/",
                updated_on=updated_on,
            )
        )

    print(
        json.dumps(
            {
                "substancePagesChecked": len(substance_dates()),
                "substancePagesChanged": changed_substances,
                "comparisonOverridesChecked": len(comparison_overrides()),
                "comparisonPagesChanged": changed_comparisons,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
