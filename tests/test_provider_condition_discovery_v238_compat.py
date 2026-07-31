from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_provider_condition_discovery_v238_compat.py"
BASE = "https://healthrenewal.org"
BASE_PATH = "/"
CHILD_SITEMAP = f"{BASE}/sitemap-provider-assessment.xml"
SLUGS = (
    "aac",
    "adhd",
    "autism",
    "behavioral-emotional-disorders",
    "brain-injury-memory-executive",
    "cerebral-palsy",
    "developmental-coordination-disorder",
    "down-syndrome",
    "genetic-syndromes",
    "global-developmental-delay",
    "hearing-loss-deafness",
    "intellectual-disability",
    "language-speech-disorders",
    "multiple-disabilities-deafblindness",
    "physical-motor-disabilities",
    "sensory-processing",
    "severe-behavior-self-injury",
    "specific-learning-disabilities",
    "transition-adulthood",
    "visual-impairment",
)
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ET.register_namespace("", SITEMAP_NS)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(str(href))


def route_for(path: Path, site: Path) -> str:
    relative = path.relative_to(site).as_posix()
    return "" if relative == "index.html" else relative.removesuffix("index.html")


def resolve_route(source: Path, href: str, site: Path) -> str | None:
    parsed = urlparse(href)
    if parsed.scheme in {"http", "https"}:
        if parsed.netloc != "healthrenewal.org" or not parsed.path.startswith(BASE_PATH):
            return None
        raw = parsed.path[len(BASE_PATH):]
    elif parsed.scheme or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    elif parsed.path.startswith(BASE_PATH):
        raw = parsed.path[len(BASE_PATH):]
    else:
        raw = (source.parent.relative_to(site) / unquote(parsed.path)).as_posix()
    target = (site / unquote(raw).lstrip("/")).resolve()
    try:
        target.relative_to(site)
    except ValueError:
        return None
    if href.endswith("/") or not target.suffix:
        target /= "index.html"
    if target.name != "index.html":
        return None
    return route_for(target, site)


def provider_discovery_failures(site: Path) -> tuple[list[str], list[str]]:
    pages = sorted(site.rglob("index.html"))
    routes = {route_for(page, site): page for page in pages}
    inbound: Counter[str] = Counter()
    for page in pages:
        parser = LinkParser()
        parser.feed(page.read_text(encoding="utf-8"))
        for href in parser.links:
            target = resolve_route(page, href, site)
            if target in routes and target != route_for(page, site):
                inbound[target] += 1

    mapped: set[str] = set()
    for sitemap in site.glob("sitemap*.xml"):
        root = ET.parse(sitemap).getroot()
        for node in root.findall("{*}url/{*}loc"):
            if not node.text:
                continue
            parsed = urlparse(node.text.strip())
            if parsed.scheme == "https" and parsed.netloc == "healthrenewal.org":
                mapped.add(unquote(parsed.path.lstrip("/")))

    provider = sorted(route for route in routes if route.startswith("provider-assessment-demo/"))
    return (
        [route for route in provider if inbound[route] == 0],
        [route for route in provider if route not in mapped],
    )


class ProviderConditionDiscoveryCompatV238Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="provider-condition-discovery-v238-compat-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))
        self._write_fixture()

    def _write(self, relative: str, source: str) -> None:
        path = self.site / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")

    def _write_fixture(self) -> None:
        self._write(
            "index.html",
            f'<!doctype html><html lang="ar" dir="rtl"><head><title>الرئيسية</title>'
            f'<meta name="description" content="الرئيسية"><link rel="canonical" href="{BASE}/">'
            '</head><body><main><h1>الرئيسية</h1><a href="provider-assessment-demo/">منصة التقييم</a></main></body></html>',
        )
        self._write(
            "provider-assessment-demo/index.html",
            f'<!doctype html><html lang="ar" dir="rtl"><head><title>منصة التقييم</title>'
            f'<meta name="description" content="منصة التقييم"><link rel="canonical" href="{BASE}/provider-assessment-demo/">'
            '</head><body><main><h1>منصة التقييم</h1>'
            '<a href="conditions/">مسارات الحالات</a></main></body></html>',
        )
        self._write(
            "provider-assessment-demo/conditions/index.html",
            f'<!doctype html><html lang="ar" dir="rtl"><head><title>مسارات الحالات</title>'
            f'<meta name="description" content="مسارات الحالات"><link rel="canonical" href="{BASE}/provider-assessment-demo/conditions/">'
            '</head><body><main><h1>مسارات الحالات</h1></main></body></html>',
        )
        self._write(
            "provider-assessment-demo/training/index.html",
            f'<!doctype html><html lang="ar" dir="rtl"><head><title>أكاديمية التقييم المهني</title>'
            f'<meta name="description" content="أكاديمية التقييم"><meta name="robots" content="index,follow">'
            f'<link rel="canonical" href="{BASE}/provider-assessment-demo/training/">'
            '</head><body><main><h1>أكاديمية التقييم المهني</h1></main></body></html>',
        )
        for index, slug in enumerate(SLUGS, 1):
            self._write(
                f"provider-assessment-demo/conditions/{slug}/index.html",
                f'<!doctype html><html lang="ar" dir="rtl"><head>'
                f'<title>تقييم الحالة {index} | المسار المهني</title>'
                f'<meta name="description" content="تقييم الحالة {index}">'
                f'<meta name="robots" content="index,follow">'
                f'<link rel="canonical" href="{BASE}/provider-assessment-demo/conditions/{slug}/">'
                f'</head><body><main><h1>تقييم الحالة {index}</h1></main></body></html>',
            )

        root = ET.Element(f"{{{SITEMAP_NS}}}sitemapindex")
        child = ET.SubElement(root, f"{{{SITEMAP_NS}}}sitemap")
        ET.SubElement(child, f"{{{SITEMAP_NS}}}loc").text = f"{BASE}/sitemap-core.xml"
        ET.ElementTree(root).write(self.site / "sitemap.xml", encoding="utf-8", xml_declaration=True)

        core = ET.Element(f"{{{SITEMAP_NS}}}urlset")
        node = ET.SubElement(core, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(node, f"{{{SITEMAP_NS}}}loc").text = f"{BASE}/"
        ET.ElementTree(core).write(self.site / "sitemap-core.xml", encoding="utf-8", xml_declaration=True)

        self._write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")

    def publish(self) -> dict:
        result = subprocess.run(
            ["python3", str(PUBLISHER), str(self.site)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return json.loads((self.site / "api/provider-condition-discovery-v238.json").read_text(encoding="utf-8"))

    def test_static_links_complete_primary_sitemap_robots_and_orphan_audit(self) -> None:
        root_before = digest(self.site / "sitemap.xml")
        report = self.publish()

        self.assertEqual(report["version"], 238)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["condition_count"], 20)
        self.assertEqual(report["directory_links"], 20)
        self.assertEqual(report["training_links"], 1)
        self.assertEqual(report["sitemap_routes"], 23)
        self.assertTrue(report["robots_sitemap_registered"])
        self.assertTrue(report["root_sitemap_unchanged"])
        self.assertTrue(report["primary_sitemap_complete"])
        self.assertEqual(report["custom_domain"], BASE)
        self.assertNotEqual(digest(self.site / "sitemap.xml"), root_before)

        gateway = (self.site / "provider-assessment-demo/index.html").read_text(encoding="utf-8")
        directory = (self.site / "provider-assessment-demo/conditions/index.html").read_text(encoding="utf-8")
        robots = (self.site / "robots.txt").read_text(encoding="utf-8")
        self.assertEqual(gateway.count('href="training/"'), 1)
        self.assertEqual(directory.count("provider-condition-discovery-v238:directory:start"), 1)
        self.assertEqual(directory.count("data-provider-condition-discovery-v238-style"), 1)
        self.assertEqual(directory.count("data-provider-condition-discovery-v238-schema"), 1)
        self.assertIn('"@type": "ItemList"', directory)
        self.assertEqual(robots.count(f"Sitemap: {CHILD_SITEMAP}"), 1)
        self.assertNotIn("khaledaltheeb.github.io/pterminology-site", robots)
        self.assertFalse(any(line.lower().startswith("disallow:") for line in robots.splitlines()))
        for slug in SLUGS:
            self.assertEqual(directory.count(f'href="{slug}/"'), 1)

        provider = ET.parse(self.site / "sitemap-provider-assessment.xml").getroot()
        urls = [(node.text or "").strip() for node in provider.findall("{*}url/{*}loc") if node.text]
        self.assertEqual(len(urls), 23)
        self.assertEqual(len(urls), len(set(urls)))
        self.assertIn(f"{BASE}/provider-assessment-demo/training/", urls)

        primary = ET.parse(self.site / "sitemap.xml").getroot()
        primary_urls = [(node.text or "").strip() for node in primary.findall("{*}url/{*}loc") if node.text]
        self.assertEqual(len(primary_urls), 24)
        self.assertEqual(len(primary_urls), len(set(primary_urls)))
        self.assertEqual(primary_urls[0], f"{BASE}/")
        self.assertTrue(all(url.startswith(f"{BASE}/") for url in primary_urls))

        orphans, unmapped = provider_discovery_failures(self.site)
        self.assertEqual(orphans, [])
        self.assertEqual(unmapped, [])

    def test_complete_output_is_idempotent(self) -> None:
        self.publish()
        tracked = (
            self.site / "provider-assessment-demo/index.html",
            self.site / "provider-assessment-demo/conditions/index.html",
            self.site / "sitemap.xml",
            self.site / "sitemap-index.xml",
            self.site / "sitemap-provider-assessment.xml",
            self.site / "robots.txt",
            self.site / "api/provider-condition-discovery-v238.json",
        )
        before = [digest(path) for path in tracked]
        self.publish()
        after = [digest(path) for path in tracked]
        self.assertEqual(before, after)

    def test_rejects_incomplete_condition_inventory(self) -> None:
        shutil.rmtree(self.site / "provider-assessment-demo/conditions" / SLUGS[-1])
        result = subprocess.run(
            ["python3", str(PUBLISHER), str(self.site)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Expected 20 provider conditions", result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
