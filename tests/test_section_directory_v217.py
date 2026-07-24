from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_section_directory_v217.py"
NORMALIZER = ROOT / "scripts" / "normalize_section_directory_api_v217.py"
SEO_WRAPPER = ROOT / "scripts" / "enhance_sitewide_seo_v216.py"
SEO_CORE = ROOT / "scripts" / "enhance_sitewide_seo_core_v216.py"
BANNED = (
    "مولدة أثناء البناء",
    "مولّد أثناء البناء",
    "لا تظهر في القوائم",
    "خطة العمل",
    "ما تم إنجازه",
    "سيتم إنجازه",
    "قيد التطوير",
)
COURSES_ENDPOINT = "https://khaledaltheeb.github.io/pterminology-site/api/v1/courses.json"


class SectionDirectoryV217Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = Path(tempfile.mkdtemp(prefix="section-directory-v217-"))
        self.addCleanup(lambda: shutil.rmtree(self.temp, ignore_errors=True))
        (self.temp / "assets" / "brand").mkdir(parents=True)
        (self.temp / "assets" / "brand" / "logo-mark.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"></svg>',
            encoding="utf-8",
        )
        (self.temp / "assets" / "brand" / "social-card.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630"></svg>',
            encoding="utf-8",
        )
        (self.temp / "manifest.webmanifest").write_text("{}", encoding="utf-8")
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
        self.write_page(
            "encyclopedia/concept-1/index.html",
            "مفهوم نفسي",
            "شرح المفهوم.",
        )
        api = self.temp / "api" / "v1"
        api.mkdir(parents=True)
        (api / "openapi.json").write_text(
            json.dumps(
                {
                    "openapi": "3.1.0",
                    "paths": {
                        "/api/v1/platform.json": {"get": {}},
                        "/api/v1/courses.json": {"get": {"summary": "Courses"}},
                    },
                    "components": {
                        "schemas": {
                            "Course": {"type": "object"},
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        (api / "platform.json").write_text(
            json.dumps(
                {
                    "resources": [
                        {
                            "id": "courses",
                            "type": "collection",
                            "title": "الدورات المصرح بها",
                            "url": COURSES_ENDPOINT,
                        }
                    ],
                    "endpoints": {"courses": COURSES_ENDPOINT},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (self.temp / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>',
            encoding="utf-8",
        )

    def write_page(
        self,
        relative: str,
        title: str,
        description: str,
        nav: bool = False,
    ) -> None:
        path = self.temp / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        navigation = (
            '<nav><a href="encyclopedia/">الموسوعة</a></nav>' if nav else ""
        )
        path.write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
            f'<title>{title}</title><meta name="description" content="{description}"></head>'
            f"<body>{navigation}<main><h1>{title}</h1><p>{description}</p></main></body></html>",
            encoding="utf-8",
        )

    def run_release(self) -> dict[str, object]:
        for script in (PUBLISHER, NORMALIZER):
            result = subprocess.run(
                ["python3", str(script), str(self.temp)],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return json.loads(
            (self.temp / "api" / "section-directory-v217.json").read_text(
                encoding="utf-8"
            )
        )

    def test_directory_homepage_api_sitemap_and_public_copy(self) -> None:
        report = self.run_release()
        self.assertEqual(report["version"], 217)
        self.assertEqual(report["status"], "passed")
        self.assertGreaterEqual(report["section_count"], 11)
        self.assertGreaterEqual(report["html_page_count"], 12)
        self.assertEqual(report["featured_on_home"], 8)
        self.assertTrue(report["operational_copy_absent"])
        self.assertTrue(report["platform_resource_normalized"])
        self.assertTrue(report["platform_endpoint_registered"])

        homepage = (self.temp / "index.html").read_text(encoding="utf-8")
        directory = (self.temp / "sections" / "index.html").read_text(
            encoding="utf-8"
        )
        for marker in (
            'href="sections/"',
            'id="institutional-section-directory-v217"',
            'href="encyclopedia/"',
            'href="special-needs/"',
            'href="care-guides/"',
            'href="library/"',
        ):
            self.assertIn(marker, homepage)
        for marker in (
            "<h1>دليل جميع أقسام المنصة</h1>",
            "application/ld+json",
            'name="keywords"',
            'property="og:image"',
            'name="twitter:image"',
            'href="https://khaledaltheeb.github.io/pterminology-site/encyclopedia/"',
        ):
            self.assertIn(marker, directory)
        for phrase in BANNED:
            self.assertNotIn(phrase, homepage)
            self.assertNotIn(phrase, directory)

        sections = json.loads(
            (self.temp / "api" / "v1" / "sections.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(sections["release"], 217)
        self.assertEqual(sections["section_count"], report["section_count"])
        routes = {item["route"] for item in sections["items"]}
        self.assertTrue(
            {"encyclopedia/", "special-needs/", "care-guides/", "api/"}
            <= routes
        )
        encyclopedia = next(
            item for item in sections["items"] if item["route"] == "encyclopedia/"
        )
        self.assertEqual(encyclopedia["page_count"], 2)

        platform = json.loads(
            (self.temp / "api" / "v1" / "platform.json").read_text(
                encoding="utf-8"
            )
        )
        resource = next(
            item for item in platform["resources"] if item.get("id") == "sections"
        )
        self.assertEqual(resource["type"], "collection")
        self.assertTrue(resource["url"].endswith("/api/v1/sections.json"))
        self.assertEqual(platform["endpoints"]["sections"], resource["url"])
        courses_resource = next(
            item for item in platform["resources"] if item.get("id") == "courses"
        )
        self.assertEqual(courses_resource["url"], COURSES_ENDPOINT)
        self.assertEqual(platform["endpoints"]["courses"], COURSES_ENDPOINT)

        openapi = json.loads(
            (self.temp / "api" / "v1" / "openapi.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(
            any(path.endswith("/api/v1/sections.json") for path in openapi["paths"])
        )
        self.assertIn("/api/v1/courses.json", openapi["paths"])
        self.assertIn("Course", openapi["components"]["schemas"])
        sitemap = (self.temp / "sitemap.xml").read_text(encoding="utf-8")
        self.assertEqual(sitemap.count("sitemap-sections-v217.xml"), 1)

    def test_second_run_is_idempotent(self) -> None:
        self.run_release()
        tracked = (
            self.temp / "index.html",
            self.temp / "sections" / "index.html",
            self.temp / "api" / "v1" / "sections.json",
            self.temp / "api" / "v1" / "platform.json",
            self.temp / "api" / "v1" / "openapi.json",
            self.temp / "sitemap.xml",
        )
        before = {path: path.read_bytes() for path in tracked}
        self.run_release()
        after = {path: path.read_bytes() for path in tracked}
        self.assertEqual(before, after)
        homepage = (self.temp / "index.html").read_text(encoding="utf-8")
        self.assertEqual(
            homepage.count('id="institutional-section-directory-v217"'),
            1,
        )
        self.assertEqual(homepage.count('href="sections/"'), 2)

    def test_seo_wrapper_preserves_import_contract_and_runs_directory_first(self) -> None:
        wrapper = SEO_WRAPPER.read_text(encoding="utf-8")
        self.assertTrue(SEO_CORE.is_file())
        self.assertIn("publish_section_directory_v217.py", wrapper)
        self.assertIn("normalize_section_directory_api_v217.py", wrapper)
        self.assertLess(wrapper.index("publish_section_directory()"), wrapper.rindex("main()"))
        spec = importlib.util.spec_from_file_location(
            "seo_wrapper_v216_test",
            SEO_WRAPPER,
        )
        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        module.SITE = self.temp
        page = self.temp / "encyclopedia" / "concept-1" / "index.html"
        changed, result = module.enrich_page(page)
        self.assertTrue(changed)
        self.assertEqual(result["status"], "modified")
        self.assertIn('name="keywords"', page.read_text(encoding="utf-8"))

    def test_production_orchestrator_still_calls_seo_wrapper(self) -> None:
        source = (ROOT / "scripts" / "apply_homepage_v20.py").read_text(
            encoding="utf-8"
        )
        enhancer = 'run_publisher("enhance_sitewide_seo_v216.py")'
        verifier = 'run_publisher("verify_sitewide_seo_v216.py")'
        gate = 'run_publisher("enforce_health_publication_gate_v192.py")'
        self.assertIn(enhancer, source)
        self.assertIn(verifier, source)
        self.assertIn(gate, source)
        self.assertLess(source.index(enhancer), source.index(verifier))
        self.assertLess(source.index(verifier), source.index(gate))


if __name__ == "__main__":
    unittest.main()
