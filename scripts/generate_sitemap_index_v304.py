#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

BASE_URL = "https://khaledaltheeb.github.io/pterminology-site/"
EXCLUDED_PARTS = {".git", "node_modules", "tests", "tmp", "vendor"}
EXCLUDED_FILES = {"404.html", "google644f1f7a8b7aaa2b.html"}
FAMILY_PREFIX = "sitemap-family-"
INDEX_FILENAME = "sitemap-index.xml"
REPORT_FILENAME = "sitemap-index-v305.json"
VERIFICATION_CONTENT = re.compile(
    r"^(?:google-site-verification|msvalidate\.01|p:domain_verify|facebook-domain-verification)\s*[:=]",
    re.IGNORECASE,
)

# Order matters: language trees must not be absorbed by a nested subject family.
FAMILIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("languages", ("en/", "es/")),
    ("encyclopedia", ("encyclopedia/",)),
    ("glossary", ("glossary/", "terms/")),
    ("hubs", ("hubs/",)),
    ("comparisons", ("comparisons/",)),
    ("care-guides", ("care-guides/",)),
    ("guided-assessment", ("guided-assessment/",)),
    ("library", ("library/",)),
    ("magazine", ("magazine/",)),
    ("special-needs", ("special-needs/",)),
    (
        "tools",
        (
            "daily-tools/",
            "tools/",
            "assessments/",
            "assessment-lab/",
            "cognitive-tests/",
            "cognitive-lab/",
        ),
    ),
    ("learning-paths", ("learning-paths/",)),
    ("provider-platform", ("provider-assessment-demo/",)),
)


class MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.robots: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta":
            return
        values = {str(key).lower(): value or "" for key, value in attrs}
        if values.get("name", "").lower() in {"robots", "googlebot"}:
            self.robots.append(values.get("content", ""))


def metadata(path: Path) -> MetadataParser:
    parser = MetadataParser()
    parser.feed(path.read_text(encoding="utf-8", errors="strict"))
    return parser


def is_verification_artifact(path: Path, root: Path) -> bool:
    if path.name in EXCLUDED_FILES:
        return True
    if path.parent != root:
        return False
    return bool(VERIFICATION_CONTENT.match(path.read_text(encoding="utf-8", errors="strict").strip()))


def normalized_url(path: Path, root: Path, base_url: str = BASE_URL) -> str:
    rel = path.relative_to(root).as_posix()
    if rel == "index.html":
        return base_url
    if rel.endswith("/index.html"):
        rel = rel[: -len("index.html")]
    return base_url + rel


def family_for(url: str) -> str:
    path = urlparse(url).path.removeprefix("/pterminology-site/")
    for family, prefixes in FAMILIES:
        if any(path.startswith(prefix) for prefix in prefixes):
            return family
    return "main"


def is_indexable(page: Path) -> bool:
    values = " ".join(metadata(page).robots).lower()
    return "noindex" not in values


def write_urlset(path: Path, urls: list[str]) -> None:
    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for url in urls:
        item = ET.SubElement(urlset, "url")
        ET.SubElement(item, "loc").text = url
    ET.indent(urlset, space="  ")
    ET.ElementTree(urlset).write(path, encoding="utf-8", xml_declaration=True)


def sync_robots(root: Path, base_url: str = BASE_URL) -> None:
    robots_path = root / "robots.txt"
    if robots_path.is_file():
        lines = [line.rstrip() for line in robots_path.read_text(encoding="utf-8").splitlines()]
    else:
        lines = ["User-agent: *", "Allow: /"]
    directive = f"Sitemap: {base_url}{INDEX_FILENAME}"
    lines = [line for line in lines if line != directive]
    lines.append(directive)
    robots_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    if robots_path.read_text(encoding="utf-8").count(directive) != 1:
        raise ValueError("robots.txt must register sitemap-index.xml exactly once")


def generate(root: Path, base_url: str = BASE_URL) -> dict[str, object]:
    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Site root not found: {root}")

    grouped: dict[str, list[str]] = defaultdict(list)
    skipped_noindex = 0
    skipped_verification = 0

    for page in sorted(root.rglob("*.html")):
        if any(part in EXCLUDED_PARTS for part in page.relative_to(root).parts):
            continue
        if is_verification_artifact(page, root):
            skipped_verification += 1
            continue
        if not is_indexable(page):
            skipped_noindex += 1
            continue
        url = normalized_url(page, root, base_url)
        grouped[family_for(url)].append(url)

    for stale in root.glob(f"{FAMILY_PREFIX}*.xml"):
        stale.unlink()

    generated: list[dict[str, object]] = []
    for family in sorted(grouped):
        urls = sorted(set(grouped[family]))
        filename = f"{FAMILY_PREFIX}{family}.xml"
        write_urlset(root / filename, urls)
        generated.append({"family": family, "filename": filename, "urls": len(urls)})

    sitemap_index = ET.Element("sitemapindex", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for item in generated:
        sitemap = ET.SubElement(sitemap_index, "sitemap")
        ET.SubElement(sitemap, "loc").text = base_url + str(item["filename"])
    ET.indent(sitemap_index, space="  ")
    ET.ElementTree(sitemap_index).write(root / INDEX_FILENAME, encoding="utf-8", xml_declaration=True)
    sync_robots(root, base_url)

    report: dict[str, object] = {
        "version": 305,
        "status": "generated",
        "base_url": base_url,
        "indexable_pages": sum(int(item["urls"]) for item in generated),
        "families": {str(item["family"]): int(item["urls"]) for item in generated},
        "sitemaps": generated,
        "skipped_noindex": skipped_noindex,
        "skipped_verification": skipped_verification,
        "index": INDEX_FILENAME,
        "family_prefix": FAMILY_PREFIX,
    }
    api = root / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / REPORT_FILENAME).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".", type=Path)
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()
    report = generate(args.root, args.base_url.rstrip("/") + "/")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
