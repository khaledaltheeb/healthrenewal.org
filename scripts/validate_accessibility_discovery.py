#!/usr/bin/env python3
"""Validate that the accessibility statement stays publicly discoverable and useful."""

from __future__ import annotations

import argparse
import sys
import tempfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

PAGE = Path("accessibility/index.html")
SHELL = Path("assets/platform/platform-core.js")
INDEX = Path("sitemap-index.xml")
SITEMAP = Path("sitemap-accessibility.xml")
PAGE_URL = "https://healthrenewal.org/accessibility/"
MAP_URL = "https://healthrenewal.org/sitemap-accessibility.xml"
REPORT_URL = "https://github.com/khaledaltheeb/healthrenewal.org/issues/new/choose"
FOOTER_FRAGMENT = "element('a', { href: url('accessibility/'), text: 'الإتاحة' })"
REQUIRED_PAGE_MARKERS = (
    'id="display-preferences"',
    '<h2>اضبط طريقة العرض</h2>',
    'id="alternative-format"',
    '<h2>طلب صيغة بديلة</h2>',
    "تقليل الحركة",
    "التكبير",
    "الخصوصية",
)
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class CanonicalParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonicals: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "link":
            return
        values = {key.lower(): value for key, value in attrs}
        rel = set((values.get("rel") or "").lower().split())
        if "canonical" in rel and values.get("href"):
            self.canonicals.append(values["href"] or "")


def parse_xml(path: Path, errors: list[str]) -> ET.Element | None:
    try:
        return ET.parse(path).getroot()
    except FileNotFoundError:
        errors.append(f"missing file: {path}")
    except ET.ParseError as exc:
        errors.append(f"invalid XML in {path}: {exc}")
    return None


def validate(root: Path) -> list[str]:
    errors: list[str] = []

    page_path = root / PAGE
    try:
        page_text = page_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"missing file: {PAGE}")
        page_text = ""
    if page_text:
        parser = CanonicalParser()
        parser.feed(page_text)
        if parser.canonicals != [PAGE_URL]:
            errors.append(f"{PAGE} must expose exactly one canonical URL: {PAGE_URL}")
        if 'meta name="robots" content="index,follow' not in page_text:
            errors.append(f"{PAGE} must remain indexable")
        for marker in REQUIRED_PAGE_MARKERS:
            if page_text.count(marker) != 1:
                errors.append(f"{PAGE} must contain exactly one required accessibility marker: {marker}")
        if page_text.count(REPORT_URL) < 2:
            errors.append("accessibility statement must link both barrier reporting and alternative-format requests to the reviewed reporting route")
        if "<script" in page_text.split("<main", 1)[-1].split("</main>", 1)[0]:
            errors.append("practical accessibility guidance must remain available without JavaScript")

    shell_path = root / SHELL
    try:
        shell_text = shell_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"missing file: {SHELL}")
        shell_text = ""
    if shell_text.count(FOOTER_FRAGMENT) != 1:
        errors.append("global footer must contain exactly one reviewed accessibility link")
    if shell_text and "روابط الحوكمة والشفافية" not in shell_text:
        errors.append("accessibility link must stay inside the governance footer navigation")

    index_root = parse_xml(root / INDEX, errors)
    if index_root is not None:
        locations = [node.text or "" for node in index_root.findall("sm:sitemap/sm:loc", NS)]
        if locations.count(MAP_URL) != 1:
            errors.append("sitemap index must reference the accessibility sitemap exactly once")
        if len(locations) != len(set(locations)):
            errors.append("sitemap index contains duplicate sitemap locations")

    sitemap_root = parse_xml(root / SITEMAP, errors)
    if sitemap_root is not None:
        locations = [node.text or "" for node in sitemap_root.findall("sm:url/sm:loc", NS)]
        if locations != [PAGE_URL]:
            errors.append("accessibility sitemap must contain only the canonical statement URL")
        lastmods = [node.text or "" for node in sitemap_root.findall("sm:url/sm:lastmod", NS)]
        if len(lastmods) != 1 or not lastmods[0].startswith("2026-"):
            errors.append("accessibility sitemap must contain one reviewed ISO lastmod date")

    return errors


def write_fixture(root: Path) -> None:
    (root / PAGE.parent).mkdir(parents=True, exist_ok=True)
    (root / SHELL.parent).mkdir(parents=True, exist_ok=True)
    markers = "".join(REQUIRED_PAGE_MARKERS)
    (root / PAGE).write_text(
        f'<html><head><meta name="robots" content="index,follow"><link rel="canonical" href="{PAGE_URL}"></head>'
        f'<body><main>{markers}<a href="{REPORT_URL}">طلب صيغة بديلة</a><a href="{REPORT_URL}">الإبلاغ عن عائق</a></main></body></html>',
        encoding="utf-8",
    )
    (root / SHELL).write_text(
        "روابط الحوكمة والشفافية\n" + FOOTER_FRAGMENT,
        encoding="utf-8",
    )
    (root / INDEX).write_text(
        f'<?xml version="1.0"?><sitemapindex xmlns="{NS["sm"]}"><sitemap><loc>{MAP_URL}</loc></sitemap></sitemapindex>',
        encoding="utf-8",
    )
    (root / SITEMAP).write_text(
        f'<?xml version="1.0"?><urlset xmlns="{NS["sm"]}"><url><loc>{PAGE_URL}</loc><lastmod>2026-08-22</lastmod></url></urlset>',
        encoding="utf-8",
    )


def run_self_test() -> int:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        write_fixture(root)
        if errors := validate(root):
            print("valid fixture failed:", *errors, sep="\n- ", file=sys.stderr)
            return 1

        shell = root / SHELL
        shell.write_text(shell.read_text(encoding="utf-8") + "\n" + FOOTER_FRAGMENT, encoding="utf-8")
        if not any("exactly one" in error for error in validate(root)):
            print("self-test failed to reject duplicate footer link", file=sys.stderr)
            return 1

        write_fixture(root)
        page = root / PAGE
        page.write_text(page.read_text(encoding="utf-8").replace('id="alternative-format"', ""), encoding="utf-8")
        if not any("required accessibility marker" in error for error in validate(root)):
            print("self-test failed to reject missing alternative-format guidance", file=sys.stderr)
            return 1

        write_fixture(root)
        page = root / PAGE
        page.write_text(page.read_text(encoding="utf-8").replace(REPORT_URL, "https://example.com/report", 1), encoding="utf-8")
        if not any("alternative-format requests" in error for error in validate(root)):
            print("self-test failed to reject missing reviewed reporting route", file=sys.stderr)
            return 1

        write_fixture(root)
        sitemap = root / SITEMAP
        sitemap.write_text(
            sitemap.read_text(encoding="utf-8").replace(PAGE_URL, "https://example.com/accessibility/"),
            encoding="utf-8",
        )
        if not any("canonical statement URL" in error for error in validate(root)):
            print("self-test failed to reject off-origin sitemap URL", file=sys.stderr)
            return 1

    print("accessibility discovery validator self-test: passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    errors = validate(args.root.resolve())
    if errors:
        print("accessibility discovery validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("accessibility discovery validation: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
