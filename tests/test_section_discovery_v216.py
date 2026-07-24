from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_section_discovery_v216.py"
BASE = "https://khaledaltheeb.github.io/pterminology-site/"


class SectionDiscoveryV216Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="sections-v216-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))
        (self.site / "index.html").write_text(
            '''<!doctype html><html lang="ar" dir="rtl"><head><title>المنصة</title></head><body>
            <header><nav><a href="encyclopedia/">الموسوعة</a></nav></header>
            <main><section><h1>منصة الصحة النفسية وذوي الاحتياجات الخاصة</h1></section></main>
            <footer></footer></body></html>''',
            encoding="utf-8",
        )
        for route, title, children in (
            ("encyclopedia", "الموسوعة النفسية العربية", 2),
            ("comparisons", "مكتبة المقارنات النفسية", 3),
            ("library", "المكتبة الأكاديمية", 4),
            ("guided-assessment", "الأسئلة الموجهة", 2),
            ("hubs", "المراكز الموضوعية", 2),
            ("assessments", "المقاييس التثقيفية", 2),
            ("cognitive-tests", "المهام المعرفية", 2),
        ):
            root = self.site / route
            root.mkdir(parents=True)
            (root / "index.html").write_text(
                f'<!doctype html><html lang="ar" dir="rtl"><head><title>{title}</title><meta name="description" content="وصف عربي منظم للقسم المنشور ومحتواه."></head><body><h1>{title}</h1></body></html>',
                encoding="utf-8",
            )
            for index in range(children - 1):
                child = root / f"item-{index + 1}"
                child.mkdir()
                (child / "index.html").write_text(
                    f'<!doctype html><html lang="ar" dir="rtl"><head><title>{title} {index + 1}</title></head><body><h1>{title}</h1></body></html>',
                    encoding="utf-8",
                )
        self.write_sitemap_index()
        api = self.site / "api" / "v1"
        api.mkdir(parents=True)
        (api / "openapi.json").write_text(
            json.dumps({"openapi": "3.1.0", "paths": {"/pterminology-site/api/v1/platform.json": {"get": {}}}}, ensure_ascii=False),
            encoding="utf-8",
        )

    def write_sitemap_index(self) -> None:
        (self.site / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f'  <sitemap><loc>{BASE}sitemap-core.xml</loc></sitemap>\n'
            '</sitemapindex>\n',
            encoding="utf-8",
        )

    def run_script(self) -> dict[str, object]:
        result = subprocess.run(
            ["python3", str(SCRIPT), str(self.site)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads((self.site / "api" / "section-discovery-v216.json").read_text(encoding="utf-8"))

    def test_generated_sections_are_visible_and_counted(self) -> None:
        report = self.run_script()
        homepage = (self.site / "index.html").read_text(encoding="utf-8")
        for route in ("comparisons/", "library/", "guided-assessment/", "hubs/", "assessments/", "cognitive-tests/"):
            self.assertIn(f'href="{route}"', homepage)
        self.assertIn('href="sections/"', homepage)
        self.assertEqual(homepage.count('id="platform-directory-v216"'), 1)
        directory = (self.site / "sections" / "index.html").read_text(encoding="utf-8")
        self.assertIn("مكتبة المقارنات النفسية", directory)
        self.assertIn("المكتبة الأكاديمية", directory)
        self.assertIn(f'href="{BASE}comparisons/"', directory)
        self.assertIn(f'href="{BASE}library/"', directory)
        self.assertNotIn('href="library/"', directory)
        payload = json.loads((self.site / "api" / "v1" / "sections.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["section_count"], 7)
        self.assertEqual(payload["html_page_count"], 17)
        self.assertIn("comparisons/", payload["unlinked_from_home_before"])
        self.assertTrue(report["comparisons_linked"])
        self.assertTrue(report["library_linked"])
        self.assertEqual(report["featured_on_home"], 6)

    def test_sitemap_openapi_and_idempotency(self) -> None:
        first = self.run_script()
        second = self.run_script()
        homepage = (self.site / "index.html").read_text(encoding="utf-8")
        self.assertEqual(homepage.count('id="platform-directory-v216"'), 1)
        self.assertEqual(homepage.count('id="directory-style-v216"'), 1)
        self.assertEqual(homepage.count('href="sections/"'), 2)
        self.assertEqual(first["sections"], second["sections"])
        self.assertEqual(first["pages"], second["pages"])
        refs = [(node.text or "").strip() for node in ET.parse(self.site / "sitemap.xml").getroot().findall("{*}sitemap/{*}loc")]
        self.assertEqual(refs.count(BASE + "sitemap-sections-v216.xml"), 1)
        openapi = json.loads((self.site / "api" / "v1" / "openapi.json").read_text(encoding="utf-8"))
        self.assertIn("/pterminology-site/api/v1/sections.json", openapi["paths"])


if __name__ == "__main__":
    unittest.main()
