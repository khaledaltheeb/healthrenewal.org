from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "upgrade_institutional_seo_v215.py"


class InstitutionalSeoV215Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="seo-v215-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))
        (self.site / "assets" / "brand").mkdir(parents=True)
        (self.site / "assets" / "brand" / "sample.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360"><rect width="640" height="360"/></svg>',
            encoding="utf-8",
        )
        (self.site / "library").mkdir()
        (self.site / "library" / "index.html").write_text(
            '''<!doctype html><html lang="ar" dir="rtl"><head>
            <meta charset="utf-8"><title>مكتبة علم النفس | المنصة</title>
            <meta name="description" content="مكتبة عربية منظمة للمصادر النفسية الموثوقة والأدلة العملية والدراسات المختارة.">
            <link rel="canonical" href="https://khaledaltheeb.github.io/pterminology-site/library/">
            </head><body><h1>مكتبة علم النفس</h1><h3>المصادر المعتمدة</h3>
            <a href="../"><img src="../assets/brand/sample.svg" alt="العودة إلى المنصة"></a>
            <p>خارطة الطريق الداخلية لا ينبغي أن تتحول إلى رسالة عامة للمستخدم.</p>
            </body></html>''',
            encoding="utf-8",
        )
        (self.site / "404.html").write_text(
            '''<!doctype html><html lang="ar" dir="rtl"><head><title>غير موجود</title>
            <meta name="description" content="تعذر العثور على الصفحة المطلوبة ويمكن العودة إلى الصفحة الرئيسية أو البحث في الموسوعة.">
            <meta name="robots" content="index,follow"><link rel="canonical" href="https://khaledaltheeb.github.io/pterminology-site/404.html">
            </head><body><h1>الصفحة غير موجودة</h1></body></html>''',
            encoding="utf-8",
        )

    def run_script(self) -> dict[str, object]:
        result = subprocess.run(
            ["python3", str(SCRIPT), str(self.site)], cwd=ROOT,
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads((self.site / "api" / "institutional-seo-v215.json").read_text(encoding="utf-8"))

    def test_metadata_accessibility_dimensions_and_report(self) -> None:
        report = self.run_script()
        page = (self.site / "library" / "index.html").read_text(encoding="utf-8")
        for marker in (
            'name="keywords"', 'property="og:title"', 'property="og:description"',
            'property="og:image"', 'name="twitter:title"', 'name="twitter:description"',
            'name="twitter:image"', 'application/ld+json', '<h2>المصادر المعتمدة</h2>',
            'width="640" height="360"', 'class="visually-hidden-v215"',
        ):
            self.assertIn(marker, page)
        keywords = re.search(r'name="keywords" content="([^"]+)"', page).group(1).split(", ")
        self.assertLessEqual(len(keywords), 12)
        self.assertEqual(len(keywords), len(set(keywords)))
        self.assertEqual(report["pages"], 2)
        self.assertGreaterEqual(report["og"], 1)
        self.assertGreaterEqual(report["twitter"], 1)
        self.assertGreaterEqual(report["heading_repairs"], 1)
        self.assertGreaterEqual(report["empty_link_names"], 1)
        self.assertGreaterEqual(report["image_dimensions"], 1)
        self.assertEqual(report["operational_copy_pages"], 1)
        self.assertTrue(report["content_expansion_required"])

    def test_404_is_noindex_and_processing_is_idempotent(self) -> None:
        self.run_script()
        second = self.run_script()
        missing = (self.site / "404.html").read_text(encoding="utf-8")
        self.assertIn('content="noindex,follow,max-image-preview:large"', missing)
        library = (self.site / "library" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(library.count('name="keywords"'), 1)
        self.assertEqual(library.count('name="twitter:title"'), 1)
        self.assertEqual(library.count('id="a11y-v215"'), 1)
        self.assertEqual(second["keywords"], 0)
        self.assertEqual(second["heading_repairs"], 0)
        self.assertEqual(second["empty_link_names"], 0)
        self.assertEqual(second["image_dimensions"], 0)


if __name__ == "__main__":
    unittest.main()
