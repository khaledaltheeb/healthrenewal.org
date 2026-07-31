import json
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from scripts.audit_search_architecture_v162 import audit, write_csv


BASE = "https://healthrenewal.org/"
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def page(title: str, canonical: str, body: str, *, robots: str = "index,follow", lang: str = "ar", description: str | None = None, schema_type: str = "Article") -> str:
    description = description or f"وصف عربي موسع ومفيد لصفحة {title} يوضح الغرض والمحتوى بصورة دقيقة للقارئ ومحركات البحث."
    return f'''<!doctype html><html lang="{lang}" dir="rtl"><head><meta charset="utf-8"><title>{title}</title><meta name="description" content="{description}"><meta name="robots" content="{robots}"><link rel="canonical" href="{canonical}"><script type="application/ld+json">{{"@context":"https://schema.org","@type":"{schema_type}"}}</script></head><body><main>{body}</main></body></html>'''


def write_sitemap(path: Path, urls: list[str]) -> None:
    ET.register_namespace("", NS)
    root = ET.Element(f"{{{NS}}}urlset")
    for url in urls:
        node = ET.SubElement(root, f"{{{NS}}}url")
        ET.SubElement(node, f"{{{NS}}}loc").text = url
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


class SearchArchitectureV162Tests(unittest.TestCase):
    def make_site(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temp = tempfile.TemporaryDirectory()
        site = Path(temp.name)
        self.addCleanup(temp.cleanup)
        return temp, site

    def test_valid_small_site_has_no_blocking_errors(self):
        _temp, site = self.make_site()
        (site / "guide").mkdir()
        (site / "index.html").write_text(
            page("الرئيسية", BASE, '<h1>الرئيسية</h1><h2>ابدأ</h2><a href="guide/">دليل القلق</a>', schema_type="WebSite"),
            encoding="utf-8",
        )
        guide_url = BASE + "guide/"
        (site / "guide" / "index.html").write_text(
            page("دليل القلق", guide_url, '<h1>دليل القلق</h1><h2>الفهم</h2><a href="../">العودة إلى الرئيسية</a>'),
            encoding="utf-8",
        )
        write_sitemap(site / "sitemap.xml", [BASE, guide_url])

        report = audit(site)
        self.assertEqual(report["error_count"], 0, report["errors"])
        self.assertEqual(report["pages_scanned"], 2)
        self.assertEqual(report["pages_in_sitemap"], 2)
        self.assertEqual(report["orphan_pages"], 0)
        self.assertEqual(report["duplicate_canonical_values"], 0)
        self.assertTrue(report["policy"]["advisory_only"])
        self.assertFalse(report["policy"]["automatic_url_or_canonical_changes"])

    def test_duplicate_canonical_and_noindex_sitemap_conflict_block(self):
        _temp, site = self.make_site()
        (site / "a").mkdir()
        (site / "b").mkdir()
        canonical = BASE + "a/"
        (site / "index.html").write_text(page("الرئيسية", BASE, '<h1>الرئيسية</h1><a href="a/">أ</a><a href="b/">ب</a>'), encoding="utf-8")
        (site / "a" / "index.html").write_text(page("صفحة أ", canonical, '<h1>صفحة أ</h1><a href="../">الرئيسية</a>'), encoding="utf-8")
        (site / "b" / "index.html").write_text(page("صفحة ب", canonical, '<h1>صفحة ب</h1><a href="../">الرئيسية</a>', robots="noindex,follow"), encoding="utf-8")
        write_sitemap(site / "sitemap.xml", [BASE, canonical, BASE + "b/"])

        report = audit(site)
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("duplicate-canonical", codes)
        self.assertIn("noindex-in-sitemap", codes)
        self.assertGreaterEqual(report["error_count"], 2)

    def test_orphan_and_generic_anchor_are_advisory_signals(self):
        _temp, site = self.make_site()
        (site / "linked").mkdir()
        (site / "orphan").mkdir()
        linked_url = BASE + "linked/"
        orphan_url = BASE + "orphan/"
        (site / "index.html").write_text(page("الرئيسية", BASE, '<h1>الرئيسية</h1><a href="linked/">اقرأ المزيد</a>'), encoding="utf-8")
        (site / "linked" / "index.html").write_text(page("مرتبطة", linked_url, '<h1>مرتبطة</h1><a href="../">الرئيسية</a>'), encoding="utf-8")
        (site / "orphan" / "index.html").write_text(page("يتيمة", orphan_url, '<h1>يتيمة</h1>'), encoding="utf-8")
        write_sitemap(site / "sitemap.xml", [BASE, linked_url, orphan_url])

        report = audit(site)
        warning_codes = {item["code"] for item in report["warnings"]}
        self.assertIn("orphan-page", warning_codes)
        self.assertEqual(report["orphan_pages"], 1)
        self.assertEqual(report["generic_or_empty_internal_anchors"], 1)
        self.assertEqual(report["error_count"], 0)

    def test_sitemap_index_and_hreflang_scope_are_validated(self):
        _temp, site = self.make_site()
        (site / "en").mkdir()
        root_html = page("الرئيسية", BASE, '<h1>الرئيسية</h1><a href="en/">English</a>', schema_type="WebSite").replace(
            '</head>', f'<link rel="alternate" hreflang="en" href="{BASE}en/"><link rel="alternate" hreflang="x-default" href="{BASE}"></head>'
        )
        en_url = BASE + "en/"
        en_html = page("Home", en_url, '<h1>Home</h1><a href="../">Arabic</a>', lang="en", description="A complete English description for the localized psychology platform homepage.", schema_type="WebSite").replace(
            '</head>', f'<link rel="alternate" hreflang="ar" href="{BASE}"><link rel="alternate" hreflang="x-default" href="{BASE}"></head>'
        )
        (site / "index.html").write_text(root_html, encoding="utf-8")
        (site / "en" / "index.html").write_text(en_html, encoding="utf-8")
        write_sitemap(site / "sitemap-core.xml", [BASE, en_url])
        ET.register_namespace("", NS)
        root = ET.Element(f"{{{NS}}}sitemapindex")
        node = ET.SubElement(root, f"{{{NS}}}sitemap")
        ET.SubElement(node, f"{{{NS}}}loc").text = BASE + "sitemap-core.xml"
        ET.ElementTree(root).write(site / "sitemap.xml", encoding="utf-8", xml_declaration=True)

        report = audit(site)
        self.assertEqual(report["error_count"], 0, report["errors"])
        self.assertEqual(report["sitemap_urls"], 2)

    def test_json_and_csv_outputs_match_page_count(self):
        _temp, site = self.make_site()
        (site / "index.html").write_text(page("الرئيسية", BASE, '<h1>الرئيسية</h1>', schema_type="WebSite"), encoding="utf-8")
        write_sitemap(site / "sitemap.xml", [BASE])
        report = audit(site)
        csv_path = site / "report.csv"
        json_path = site / "report.json"
        write_csv(report, csv_path)
        json_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        self.assertTrue(csv_path.read_text(encoding="utf-8-sig").startswith("path,url,lang"))
        self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["pages_scanned"], 1)


if __name__ == "__main__":
    unittest.main()
