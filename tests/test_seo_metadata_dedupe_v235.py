from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENHANCER = ROOT / "scripts" / "enhance_sitewide_seo_v216.py"
VERIFIER = ROOT / "scripts" / "verify_sitewide_seo_v216.py"


def load_enhancer(site: Path):
    spec = importlib.util.spec_from_file_location("enhance_sitewide_seo_v216_v235_test", ENHANCER)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load SEO enhancer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.SITE = site
    return module


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SeoMetadataDedupeV235Tests(unittest.TestCase):
    def build_fixture(self, root: Path) -> Path:
        page = root / "cognitive-lab" / "example" / "index.html"
        page.parent.mkdir(parents=True)
        (root / "assets" / "brand").mkdir(parents=True)
        (root / "assets" / "brand" / "social-card.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"></svg>', encoding="utf-8"
        )
        page.write_text(
            '''<!doctype html><html lang="ar" dir="rtl"><head>
<title>مهمة معرفية تجريبية | منصة الصحة النفسية وذوي الاحتياجات الخاصة</title>
<meta name="description" content="صفحة عربية منظمة لمهمة معرفية تجريبية مع حدود واضحة للاستخدام والتفسير.">
<meta name="robots" content="index,follow">
<link rel="canonical" href="https://khaledaltheeb.github.io/pterminology-site/cognitive-lab/example/">
<link rel="canonical" href="https://example.invalid/duplicate">
<meta name="twitter:title" content="العنوان الأول">
<meta name="twitter:title" content="العنوان المكرر">
<meta name="twitter:description" content="الوصف الأول">
<meta name="twitter:description" content="الوصف المكرر">
<meta property="og:title" content="عنوان Open Graph الأول">
<meta property="og:title" content="عنوان Open Graph المكرر">
</head><body><main><h1>مهمة معرفية تجريبية</h1><p>محتوى عربي واضح يشرح الغرض والسياق والحدود المهنية وطريقة القراءة الآمنة.</p></main></body></html>''',
            encoding="utf-8",
        )
        return page

    def test_removes_only_duplicate_managed_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary) / "site"
            page = self.build_fixture(site)
            module = load_enhancer(site)
            changed, result = module.enrich_page(page)
            self.assertTrue(changed)
            self.assertEqual(result["metadata_dedupe_version"], 235)
            self.assertEqual(result["metadata_duplicates_removed"], 4)
            source = page.read_text(encoding="utf-8")
            self.assertEqual(source.count('name="twitter:title"'), 1)
            self.assertEqual(source.count('name="twitter:description"'), 1)
            self.assertEqual(source.count('property="og:title"'), 1)
            self.assertEqual(source.count('rel="canonical"'), 1)
            self.assertIn('content="العنوان الأول"', source)
            self.assertNotIn("العنوان المكرر", source)

    def test_full_enhancer_and_verifier_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary) / "site"
            page = self.build_fixture(site)
            subprocess.run([sys.executable, str(ENHANCER), str(site)], cwd=ROOT, check=True)
            subprocess.run([sys.executable, str(VERIFIER), str(site)], cwd=ROOT, check=True)
            first = digest(page)
            report = json.loads((site / "api" / "sitewide-seo-v216.json").read_text(encoding="utf-8"))
            verification = json.loads((site / "api" / "sitewide-seo-verification-v216.json").read_text(encoding="utf-8"))
            self.assertEqual(report["metadata_dedupe_version"], 235)
            self.assertGreaterEqual(report["totals"].get("metadata_duplicates_removed", 0), 4)
            self.assertEqual(report["failure_count"], 0)
            self.assertEqual(verification["status"], "passed")
            self.assertEqual(verification["failure_count"], 0)

            subprocess.run([sys.executable, str(ENHANCER), str(site)], cwd=ROOT, check=True)
            subprocess.run([sys.executable, str(VERIFIER), str(site)], cwd=ROOT, check=True)
            self.assertEqual(first, digest(page))


if __name__ == "__main__":
    unittest.main()
