from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENHANCER = ROOT / "scripts" / "enhance_hidden_collections_seo_v217.py"
ROUTES = (
    "comparisons", "library", "guided-assessment", "hubs",
    "assessments", "cognitive-tests", "sections",
)


class HiddenCollectionsSeoV217Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = Path(tempfile.mkdtemp(prefix="hidden-seo-v217-"))
        self.addCleanup(lambda: shutil.rmtree(self.temp, ignore_errors=True))
        for route in ROUTES:
            self.write_page(route, f"صفحة {route}")
            self.write_page(f"{route}/item-one", f"موضوع تفصيلي في {route}")

    def write_page(self, route: str, title: str) -> None:
        path = self.temp / route / "index.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
            f'<title>{title} | منصة الصحة النفسية</title>'
            f'<meta name="description" content="وصف عربي منظم ومفيد حول {title} ضمن المنصة.">'
            '<meta name="keywords" content="الصحة النفسية, علم النفس">'
            '</head><body><main><h1>' + title + '</h1><p>محتوى الصفحة.</p></main></body></html>',
            encoding="utf-8",
        )

    def run_enhancer(self) -> dict[str, object]:
        result = subprocess.run(
            ["python3", str(ENHANCER), str(self.temp)], cwd=ROOT,
            text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return json.loads((self.temp / "api" / "hidden-collections-seo-v217.json").read_text(encoding="utf-8"))

    def test_pages_receive_specialized_metadata_links_and_schema(self) -> None:
        report = self.run_enhancer()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["collections"], 7)
        self.assertEqual(report["pages_scanned"], 14)
        expectations = {
            "comparisons": "مقارنات نفسية",
            "library": "المكتبة الأكاديمية",
            "guided-assessment": "أسئلة التقييم النفسي",
            "hubs": "مراكز موضوعية نفسية",
            "assessments": "المقاييس النفسية",
            "cognitive-tests": "الاختبارات المعرفية",
            "sections": "أقسام الصحة النفسية",
        }
        for route, expected_keyword in expectations.items():
            for page in sorted((self.temp / route).rglob("*.html")):
                source = page.read_text(encoding="utf-8")
                self.assertEqual(source.count('id="hidden-collection-links-v217"'), 1)
                self.assertEqual(source.count("data-hidden-collection-breadcrumb-v217"), 1)
                self.assertIn(f'rel="up" href="https://khaledaltheeb.github.io/pterminology-site/{route}/"', source)
                self.assertIn('title="دليل أقسام المنصة"', source)
                keywords = re.search(r'<meta name="keywords" content="([^"]+)"', source)
                self.assertIsNotNone(keywords)
                values = [item.strip() for item in keywords.group(1).split(",") if item.strip()]
                self.assertGreaterEqual(len(values), 7)
                self.assertEqual(len(values), len(set(values)))
                self.assertIn(expected_keyword, values)
                breadcrumb = re.search(
                    r'<script type="application/ld\+json" data-hidden-collection-breadcrumb-v217>(.*?)</script>',
                    source, re.S,
                )
                self.assertIsNotNone(breadcrumb)
                payload = json.loads(breadcrumb.group(1))
                self.assertEqual(payload["@type"], "BreadcrumbList")
                self.assertGreaterEqual(len(payload["itemListElement"]), 2)

    def test_second_run_is_idempotent(self) -> None:
        self.run_enhancer()
        before = {
            page.relative_to(self.temp).as_posix(): page.read_text(encoding="utf-8")
            for route in ROUTES for page in (self.temp / route).rglob("*.html")
        }
        report = self.run_enhancer()
        after = {
            page.relative_to(self.temp).as_posix(): page.read_text(encoding="utf-8")
            for route in ROUTES for page in (self.temp / route).rglob("*.html")
        }
        self.assertEqual(before, after)
        self.assertEqual(report["pages_changed"], 0)

    def test_production_wrapper_runs_hidden_seo_after_core(self) -> None:
        source = (ROOT / "scripts" / "enhance_sitewide_seo_v216.py").read_text(encoding="utf-8")
        self.assertIn("HIDDEN_COLLECTIONS_ENHANCER", source)
        self.assertIn("HIDDEN_COLLECTIONS_VERIFIER", source)
        core_call = source.index("status = main()")
        hidden_call = source.index("    enhance_hidden_collections()", core_call)
        self.assertLess(core_call, hidden_call)


if __name__ == "__main__":
    unittest.main()
