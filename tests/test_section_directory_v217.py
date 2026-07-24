from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_section_directory_v217.py"
BANNED = (
    "مولدة أثناء البناء", "مولّد أثناء البناء", "لا تظهر في القوائم",
    "خطة العمل", "ما تم إنجازه", "سيتم إنجازه", "قيد التطوير",
)


class SectionDirectoryV217Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = Path(tempfile.mkdtemp(prefix="section-directory-v217-"))
        self.addCleanup(lambda: shutil.rmtree(self.temp, ignore_errors=True))
        (self.temp / "assets" / "brand").mkdir(parents=True)
        (self.temp / "assets" / "brand" / "logo-mark.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"></svg>', encoding="utf-8"
        )
        (self.temp / "assets" / "brand" / "social-card.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630"></svg>', encoding="utf-8"
        )
        (self.temp / "manifest.webmanifest").write_text('{}', encoding="utf-8")
        self.write_page("index.html", "الرئيسية", "بوابة المنصة", nav=True)
        for route, title in (
            ("encyclopedia/index.html", "الموسوعة النفسية"),
            ("special-needs/index.html", "ذوو الاحتياجات الخاصة"),
            ("care-guides/index.html", "أدلة التعامل"),
            ("comparisons/index.html", "المقارنات النفسية"),
            ("library/index.html", "المكتبة الأكاديمية"),
            ("assessment-lab/index.html", "مختبر المقاييس"),
            ("cognitive-lab/index.html", "مختبر القدرات"),
            ("magazine/index.html", "المجلة والأبحاث"),
            ("api/index.html", "واجهة API"),
            ("en/index.html", "English homepage"),
            ("es/index.html", "Página en español"),
        ):
            self.write_page(route, title, f"وصف منظم لقسم {title} داخل المنصة.")
        (self.temp / "encyclopedia" / "concept-1").mkdir(parents=True)
        self.write_page("encyclopedia/concept-1/index.html", "مفهوم نفسي", "شرح المفهوم.")
        api = self.temp / "api" / "v1"
        api.mkdir(parents=True)
        (api / "openapi.json").write_text(
            json.dumps({"openapi": "3.1.0", "paths": {"/api/v1/platform.json": {"get": {}}}}),
            encoding="utf-8",
        )
        (api / "platform.json").write_text(
            json.dumps({"resources": [], "endpoints": {}}, ensure_ascii=False), encoding="utf-8"
        )
        (self.temp / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>',
            encoding="utf-8",
        )

    def write_page(self, relative: str, title: str, description: str, nav: bool = False) -> None:
        path = self.temp / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        navigation = '<nav><a href="encyclopedia/">الموسوعة</a></nav>' if nav else ""
        path.write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
            f'<title>{title}</title><meta name="description" content="{description}"></head>'
            f'<body>{navigation}<main><h1>{title}</h1><p>{description}</p></main></body></html>',
            encoding="utf-8",
        )

    def run_publisher(self) -> dict[str, object]:
        result = subprocess.run(
            ["python3", str(SCRIPT), str(self.temp)], cwd=ROOT,
            text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return json.loads((self.temp / "api" / "section-directory-v217.json").read_text(encoding="utf-8"))

    def test_directory_homepage_api_and_sitemap(self) -> None:
        report = self.run_publisher()
        self.assertEqual(report["version"], 217)
        self.assertEqual(report["status"], "passed")
        self.assertGreaterEqual(report["section_count"], 11)
        self.assertGreaterEqual(report["html_page_count"], 12)
        self.assertEqual(report["featured_on_home"], 8)
        self.assertTrue(report["operational_copy_absent"])

        homepage = (self.temp / "index.html").read_text(encoding="utf-8")
        directory = (self.temp / "sections" / "index.html").read_text(encoding="utf-8")
        for marker in (
            'href="sections/"', 'id="institutional-section-directory-v217"',
            'href="encyclopedia/"', 'href="special-needs/"',
            'href="care-guides/"', 'href="library/"',
        ):
            self.assertIn(marker, homepage)
        for marker in (
            '<h1>دليل جميع أقسام المنصة</h1>', 'application/ld+json',
            'name="keywords"', 'property="og:image"', 'name="twitter:image"',
            'href="https://khaledaltheeb.github.io/pterminology-site/encyclopedia/"',
        ):
            self.assertIn(marker, directory)
        for phrase in BANNED:
            self.assertNotIn(phrase, homepage)
            self.assertNotIn(phrase, directory)

        payload = json.loads((self.temp / "api" / "v1" / "sections.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["release"], 217)
        self.assertEqual(payload["section_count"], report["section_count"])
        routes = {item["route"] for item in payload["items"]}
        self.assertTrue({"encyclopedia/", "special-needs/", "care-guides/", "api/"} <= routes)
        encyclopedia = next(item for item in payload["items"] if item["route"] == "encyclopedia/")
        self.assertEqual(encyclopedia["page_count"], 2)

        openapi = json.loads((self.temp / "api" / "v1" / "openapi.json").read_text(encoding="utf-8"))
        self.assertIn("/api/v1/sections.json", openapi["paths"])
        platform = json.loads((self.temp / "api" / "v1" / "platform.json").read_text(encoding="utf-8"))
        self.assertTrue(any(
            isinstance(item, dict) and item.get("url", "").endswith("/api/v1/sections.json")
            for item in platform["resources"]
        ))
        sitemap = (self.temp / "sitemap.xml").read_text(encoding="utf-8")
        self.assertEqual(sitemap.count("sitemap-sections-v217.xml"), 1)

    def test_second_run_is_structurally_idempotent(self) -> None:
        self.run_publisher()
        homepage_before = (self.temp / "index.html").read_text(encoding="utf-8")
        directory_before = (self.temp / "sections" / "index.html").read_text(encoding="utf-8")
        sections_before = (self.temp / "api" / "v1" / "sections.json").read_text(encoding="utf-8")
        self.run_publisher()
        homepage_after = (self.temp / "index.html").read_text(encoding="utf-8")
        directory_after = (self.temp / "sections" / "index.html").read_text(encoding="utf-8")
        sections_after = (self.temp / "api" / "v1" / "sections.json").read_text(encoding="utf-8")
        self.assertEqual(homepage_before, homepage_after)
        self.assertEqual(directory_before, directory_after)
        self.assertEqual(sections_before, sections_after)
        self.assertEqual(homepage_after.count('id="institutional-section-directory-v217"'), 1)
        self.assertEqual(homepage_after.count('href="sections/"'), 2)
        sitemap = (self.temp / "sitemap.xml").read_text(encoding="utf-8")
        self.assertEqual(sitemap.count("sitemap-sections-v217.xml"), 1)

    def test_production_orchestrator_wires_publisher_before_health_gate(self) -> None:
        source = (ROOT / "scripts" / "apply_homepage_v20.py").read_text(encoding="utf-8")
        publisher = 'run_publisher("publish_section_directory_v217.py")'
        gate = 'run_publisher("enforce_health_publication_gate_v192.py")'
        self.assertIn('"section_directory_publisher": 217', source)
        self.assertIn(publisher, source)
        self.assertIn(gate, source)
        self.assertLess(source.index(publisher), source.index(gate))


if __name__ == "__main__":
    unittest.main()
