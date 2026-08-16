from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://healthrenewal.org/"
DATA = ROOT / "content/v18/care-guides-ar.json"
TRUSTED_HOSTS = {"www.who.int", "www.unicef.org", "www.nice.org.uk", "www.cuh.nhs.uk"}


class CareGuidesV234Tests(unittest.TestCase):
    def test_core_content_depth_v235(self) -> None:
        payload = json.loads(DATA.read_text(encoding="utf-8"))
        self.assertGreaterEqual(payload.get("version", 0), 235)
        self.assertEqual(len(payload.get("guides", [])), 6)
        for guide in payload["guides"]:
            joined = json.dumps(guide, ensure_ascii=False)
            word_count = len(re.findall(r"[\w\u0600-\u06ff]+", joined, flags=re.UNICODE))
            actionable_items = sum(
                len(value)
                for key, value in guide.items()
                if isinstance(value, list) and key not in {"audience", "search_intent", "sources"}
            )
            self.assertGreaterEqual(word_count, 700, guide["slug"])
            self.assertGreaterEqual(actionable_items, 50, guide["slug"])
            self.assertGreaterEqual(len(guide["summary"]), 150, guide["slug"])
            self.assertEqual(guide.get("review_status"), "internally-reviewed", guide["slug"])
            self.assertRegex(guide.get("reviewed_at", ""), r"^20\d{2}-\d{2}-\d{2}$")
            self.assertGreaterEqual(len(guide.get("sources", [])), 3, guide["slug"])
            for source in guide["sources"]:
                parsed = urlparse(source["url"])
                self.assertEqual(parsed.scheme, "https", source)
                self.assertIn(parsed.netloc, TRUSTED_HOSTS, source)
            for prohibited in ("تشخيص مؤكد", "يغني عن الطبيب", "بديل عن العلاج", "نتيجة نهائية", "معاقين"):
                self.assertNotIn(prohibited, joined, guide["slug"])

    def test_light_hero_contrast_contract(self) -> None:
        care_css = (ROOT / "assets/css/care-guides-v234.css").read_text(encoding="utf-8")
        polish_css = (ROOT / "assets/platform/sitewide-polish.css").read_text(encoding="utf-8")
        platform_js = (ROOT / "assets/platform/platform-core.js").read_text(encoding="utf-8")
        normalizer = (ROOT / "scripts/normalize_platform_shell.py").read_text(encoding="utf-8")

        self.assertRegex(
            care_css,
            r"\.care-v21__hero\{[^}]*color:var\(--care-ink\)",
            "Care-guide light hero must set an explicit dark inherited text color.",
        )
        self.assertRegex(
            care_css,
            r"\.care-v21__hero h1\{[^}]*color:var\(--care-ink\)",
            "Care-guide H1 must never inherit a legacy white header color.",
        )
        self.assertRegex(
            care_css,
            r"\.care-v21__audience span,\.care-tag\{[^}]*color:var\(--care-ink\)",
            "Audience tags need an explicit readable foreground on their light background.",
        )
        self.assertIn(".care-stat span{color:var(--care-muted)}", care_css)
        self.assertIn('[data-pt-contrast-fix="dark"]', polish_css)
        self.assertIn('[data-pt-contrast-fix="dark-muted"]', polish_css)
        self.assertIn("const auditHeroContrast = () =>", platform_js)
        self.assertIn("contrastRatio(foreground, background) >= 4.5", platform_js)
        self.assertIn("background) < 0.62", platform_js)
        self.assertIn("SHELL_VERSION = \"1.2.0\"", normalizer)

    def test_institutional_publication_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="care-v246-") as temp:
            site = Path(temp)
            extension = site / "care-guides/extension-guide/index.html"
            extension.parent.mkdir(parents=True)
            (site / "api").mkdir()
            extension.write_text(
                '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
                '<title>دليل اختيار المختص</title><meta name="description" content="دليل عملي لاختيار المختص.">'
                f'<meta property="og:url" content="{BASE}care-guides/extension-guide/">'
                '<script type="application/ld+json">{"@type":"Article","x":"HowTo"}</script></head>'
                '<body><main id="legacy-main"><header><h1>دليل اختيار المختص</h1></header>'
                '<section><h2>الخصوصية</h2><p>محتوى.</p></section>'
                '<section><h2>مصادر مؤسسية للمراجعة</h2><p>خدمات الطوارئ المحلية.</p></section>'
                '</main></body></html>', encoding="utf-8"
            )
            (site / "sitemap.xml").write_text(
                '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f'<sitemap><loc>{BASE}sitemap-main.xml</loc></sitemap></sitemapindex>', encoding="utf-8"
            )
            (site / "sitemap-care-guides.xml").write_text(
                '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f'<url><loc>{BASE}care-guides/</loc></url>'
                f'<url><loc>{BASE}care-guides/extension-guide/</loc></url></urlset>', encoding="utf-8"
            )
            run = subprocess.run(
                [sys.executable, "scripts/publish_care_guides_v21.py", str(site)],
                cwd=ROOT, text=True, capture_output=True, check=False
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            legacy = json.loads((site / "api/care-guides-v21.json").read_text(encoding="utf-8"))
            report = json.loads((site / "api/care-guides-v234.json").read_text(encoding="utf-8"))
            self.assertEqual(report["version"], 246)
            self.assertEqual(report["status"], "passed")
            self.assertGreaterEqual(legacy["published_core_guides"], 100)
            self.assertTrue(legacy["minimum_published_guides_met"])
            self.assertEqual(report["published_pages"], legacy["pages"])
            self.assertEqual(report["sitemap_urls"], legacy["sitemap_urls"])
            self.assertEqual(report["pages_with_keywords"], legacy["pages"])
            self.assertEqual(report["pages_with_faq_schema"], legacy["pages"])
            self.assertEqual(report["pages_with_canonical"], legacy["pages"])
            self.assertEqual(report["pages_with_single_h1"], legacy["pages"])
            self.assertEqual(report["guide_pages_with_toc"], legacy["guides"])
            self.assertFalse(report["duplicate_ids"])
            self.assertTrue(report["specialist_review_gate_preserved"])
            self.assertEqual(report["blocked_term_occurrences"], 0)
            self.assertTrue((site / "assets/css/care-guides-v234.css").is_file())
            self.assertTrue((site / "assets/js/care-guides-v234.js").is_file())
            hub = (site / "care-guides/index.html").read_text(encoding="utf-8")
            for token in ("data-care-library", "CollectionPage", "ItemList", "FAQPage", "المنهجية التحريرية وضبط الجودة"):
                self.assertIn(token, hub)
            for page in sorted((site / "care-guides").glob("*/index.html")):
                text = page.read_text(encoding="utf-8")
                for token in ('data-care-guides-v234="1"', 'name="keywords"', 'rel="canonical"', "FAQPage", "care-toc"):
                    self.assertIn(token, text, page)
                ids = re.findall(r'\bid="([^"]+)"', text)
                self.assertEqual(len(ids), len(set(ids)), page)
            robots = (site / "robots.txt").read_text(encoding="utf-8")
            self.assertIn(f"Sitemap: {BASE}sitemap-care-guides.xml", robots)
            self.assertIn("Disallow: /api/", robots)


if __name__ == "__main__":
    unittest.main()
