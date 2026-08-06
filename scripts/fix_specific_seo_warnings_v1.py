#!/usr/bin/env python3
from __future__ import annotations

"""Fix reviewed deterministic SEO issues on explicitly scoped pages.

The scope is deliberately explicit. It enforces reviewed search metadata on
three pages and a fixed contextual internal-links block on the accessible travel
guide. It does not rewrite H1 content, citations, structured data, or unrelated
body copy.
"""

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROBOTS = "index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"
CLINICAL_TITLE = "القلق والهلع والوسواس: الفروق وطلب المساعدة | منصة روافد"
TRAVEL_DESCRIPTION = (
    "دليل عربي عملي للتخطيط لسفر ميسّر: توثيق احتياجات الحركة والتواصل، "
    "والتحقق من الإقامة والنقل والأدوية والطوارئ والإلغاء قبل الدفع، مع أسئلة "
    "قابلة للقياس وخطة بديلة."
)
TRAVEL_LINKS_MARKER = 'data-seo-internal-links="v1"'
TRAVEL_LINKS_SECTION = """<section class="related-resources" data-seo-internal-links="v1" aria-labelledby="related-resources-heading">
<h2 id="related-resources-heading">موارد مرتبطة للتخطيط الآمن والميسّر</h2>
<ul>
<li><a href="/accessibility/accessible-participation-travel/">المشاركة والسفر الميسّر للأشخاص ذوي الاحتياجات الخاصة</a></li>
<li><a href="/accessibility/">دليل الإتاحة والمشاركة الشاملة</a></li>
<li><a href="/safety/">معايير السلامة وحدود المحتوى الصحي</a></li>
</ul>
</section>"""

TARGETS = {
    "clinical": Path("evidence-guides/clinical-anxiety/index.html"),
    "travel": Path("guides/accessible-travel-planning/index.html"),
    "books": Path("resources/open-books-discovery/index.html"),
}


class SeoFixError(RuntimeError):
    pass


def _replace_title(source: str, value: str) -> str:
    updated, count = re.subn(
        r"<title>.*?</title>",
        f"<title>{value}</title>",
        source,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if count != 1:
        raise SeoFixError("Expected exactly one <title> element.")
    return updated


def _replace_description(source: str, value: str) -> str:
    pattern = r'<meta\s+name=["\']description["\']\s+content=["\'][^"\']*["\']\s*/?>'
    replacement = f'<meta name="description" content="{value}">'
    updated, count = re.subn(
        pattern,
        replacement,
        source,
        count=1,
        flags=re.IGNORECASE,
    )
    if count != 1:
        raise SeoFixError("Expected exactly one meta description.")
    return updated


def _ensure_robots(source: str) -> str:
    pattern = r'<meta\s+name=["\']robots["\']\s+content=["\'][^"\']*["\']\s*/?>'
    replacement = f'<meta name="robots" content="{ROBOTS}">'
    if re.search(pattern, source, flags=re.IGNORECASE):
        return re.sub(pattern, replacement, source, count=1, flags=re.IGNORECASE)

    description = re.search(
        r'<meta\s+name=["\']description["\']\s+content=["\'][^"\']*["\']\s*/?>',
        source,
        flags=re.IGNORECASE,
    )
    if not description:
        raise SeoFixError("Cannot insert robots metadata without a description anchor.")
    return source[: description.end()] + "\n" + replacement + source[description.end() :]


def _ensure_travel_internal_links(source: str) -> str:
    if TRAVEL_LINKS_MARKER in source:
        return source

    anchor = '<section aria-labelledby="sources-heading">'
    if source.count(anchor) != 1:
        raise SeoFixError("Expected exactly one travel sources section anchor.")
    return source.replace(anchor, TRAVEL_LINKS_SECTION + "\n" + anchor, 1)


def expected_sources(root: Path) -> dict[Path, str]:
    paths = {name: root / relative for name, relative in TARGETS.items()}
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise SeoFixError(f"Missing SEO target pages: {missing}")

    clinical = _replace_title(paths["clinical"].read_text(encoding="utf-8"), CLINICAL_TITLE)

    travel = paths["travel"].read_text(encoding="utf-8")
    travel = _replace_description(travel, TRAVEL_DESCRIPTION)
    travel = _ensure_robots(travel)
    travel = _ensure_travel_internal_links(travel)

    books = _ensure_robots(paths["books"].read_text(encoding="utf-8"))

    return {
        paths["clinical"]: clinical,
        paths["travel"]: travel,
        paths["books"]: books,
    }


def apply(root: Path, *, write: bool) -> dict[str, object]:
    expected = expected_sources(root)
    changed: list[str] = []
    for path, source in expected.items():
        current = path.read_text(encoding="utf-8")
        if current == source:
            continue
        changed.append(path.relative_to(root).as_posix())
        if write:
            path.write_text(source, encoding="utf-8")

    if changed and not write:
        raise SeoFixError(f"SEO fixes are stale: {changed}")

    return {
        "version": 1,
        "write": write,
        "changed": changed,
        "targets": [path.relative_to(root).as_posix() for path in expected],
        "clinical_title_length": len(CLINICAL_TITLE),
        "travel_description_length": len(TRAVEL_DESCRIPTION),
        "travel_internal_links": 3,
        "robots": ROBOTS,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=ROOT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    report = apply(args.root.resolve(), write=args.write)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
