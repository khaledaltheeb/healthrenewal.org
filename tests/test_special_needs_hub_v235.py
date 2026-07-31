from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_special_needs_guides_v217.py"
LIVE_VERIFIER = ROOT / "scripts" / "verify_special_needs_hub_live_v241.py"
BASE = "https://healthrenewal.org"
TEST_SHA = "a" * 40
BANNED = re.compile(r"(?<!\w)(?:المعاقين|معاقين|المعاقون|معاقون|المعاقة|معاقة|المعاق|معاق)(?!\w)")


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hidden = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "nav", "footer"}:
            self.hidden += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "nav", "footer"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def visible_words(source: str) -> int:
    parser = VisibleTextParser()
    parser.feed(source)
    return len(re.findall(r"[\w\u0600-\u06FF]+", " ".join(parser.parts), flags=re.UNICODE))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SpecialNeedsHubV235Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="special-needs-hub-v235-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))
        (self.site / "special-needs").mkdir(parents=True)
        (self.site / "special-needs/index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head></head><body><main>'
            '<section><h1>مركز ذوي الاحتياجات الخاصة</h1></section>'
            '<section><h2>مصادر الوحدة الحالية</h2></section>'
            '</main></body></html>',
            encoding="utf-8",
        )
        for name in ("sitemap.xml", "sitemap-special-needs.xml"):
            (self.site / name).write_text(
                '<?xml version="1.0" encoding="utf-8"?>'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
                encoding="utf-8",
            )
        (self.site / "robots.txt").write_text(
            "User-agent: *\nAllow: /\nSitemap: https://healthrenewal.org/sitemap.xml\n",
            encoding="utf-8",
        )

    def publish(self) -> dict:
        result = subprocess.run(
            ["python3", str(PUBLISHER), str(self.site)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return json.loads((self.site / "api/special-needs-guides-v221.json").read_text(encoding="utf-8"))

    def test_hub_is_deep_institutional_accessible_and_indexable(self) -> None:
        report = self.publish()
        source = (self.site / "special-needs/index.html").read_text(encoding="utf-8")

        self.assertEqual(report["version"], 221)
        self.assertEqual(report["hub_contract"], 235)
        self.assertEqual(report["hub_release"], 241)
        self.assertEqual(report["guide_count"], 25)
        self.assertEqual(report["hub"]["pathway_count"], 8)
        self.assertEqual(report["hub"]["faq_count"], 8)
        self.assertEqual(report["hub"]["source_count"], 10)
        self.assertEqual(report["hub"]["jordan_source_count"], 3)
        self.assertTrue(report["hub"]["asha_aac_source_updated"])

        self.assertEqual(len(re.findall(r"<h1\b", source)), 1)
        self.assertGreaterEqual(len(re.findall(r"<h2\b", source)), 15)
        self.assertGreaterEqual(len(re.findall(r"<h3\b", source)), 40)
        self.assertGreaterEqual(visible_words(source), 1400)

        required = (
            '<meta name="description"',
            '<meta name="keywords"',
            '<meta name="robots"',
            '<meta name="googlebot"',
            '<meta name="bingbot"',
            '<link rel="canonical"',
            'hreflang="ar"',
            'hreflang="x-default"',
            'property="og:image"',
            'name="twitter:image"',
            'application/ld+json',
            '"@type": "Organization"',
            '"@type": "WebSite"',
            '"@type": "CollectionPage"',
            '"@type": "BreadcrumbList"',
            '"@type": "ItemList"',
            '"@type": "FAQPage"',
            'prefers-reduced-motion',
            'prefers-contrast:more',
            '@media print',
            'انتقل إلى المحتوى الرئيسي',
            'مصفوفة قرار سريعة',
            'معايير جودة الخطة أو الخدمة',
            'المنهجية التحريرية وحدود الاستخدام',
            'متى تكون الأولوية للأمان؟',
            'الطوارئ المحلية',
            '<strong>10</strong><span>مراجع مؤسسية أصلية</span>',
            'data-special-needs-jordan-sources-v241',
            'jordan-launches-national-framework-inclusion-and-diversity-education-unesco',
            'jordans-education-strategic-plan-2026-2030',
            'unicef.org/jordan/education',
            'Practice-Portal/Professional-Issues/Augmentative-and-Alternative-Communication',
        )
        missing = [marker for marker in required if marker not in source]
        self.assertFalse(missing, missing)
        self.assertEqual(source.count('data-special-needs-jordan-sources-v241'), 3)
        self.assertNotIn('www.asha.org/public/speech/disorders/aac/', source)
        self.assertIsNone(BANNED.search(source))
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)
        self.assertNotIn("eval(", source)

        for anchor in (
            "pathway-communication",
            "pathway-inclusive-learning",
            "pathway-daily-skills",
            "pathway-sensory-regulation",
            "pathway-family-care",
            "pathway-safeguarding",
            "pathway-sensory-mobility-access",
            "pathway-adulthood",
        ):
            self.assertEqual(source.count(f'id="{anchor}"'), 1)
            self.assertIn(f'href="#{anchor}"', source)

        for slug in report["guide_slugs"]:
            route = f"/special-needs/{slug}/"
            self.assertEqual(source.count(route), 1, slug)

    def test_live_verifier_accepts_exact_generated_contract(self) -> None:
        self.publish()
        (self.site / "deployment.json").write_text(
            json.dumps({"schema_version": 30, "commit": TEST_SHA}, ensure_ascii=False),
            encoding="utf-8",
        )
        result = subprocess.run(
            ["python3", str(LIVE_VERIFIER), str(self.site), "--expected-sha", TEST_SHA],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        evidence = json.loads((self.site / "api/special-needs-hub-live-v241.json").read_text(encoding="utf-8"))
        self.assertEqual(evidence["version"], 241)
        self.assertEqual(evidence["status"], "passed")
        self.assertEqual(evidence["deployment_commit"], TEST_SHA)
        self.assertEqual(evidence["guide_count"], 25)
        self.assertEqual(evidence["source_count"], 10)
        self.assertEqual(evidence["jordan_source_count"], 3)
        self.assertFalse(evidence["external_review_completed"])

    def test_robots_and_complete_output_are_idempotent(self) -> None:
        first = self.publish()
        tracked = [
            self.site / "special-needs/index.html",
            self.site / "robots.txt",
            self.site / "sitemap.xml",
            self.site / "sitemap-special-needs.xml",
            self.site / "api/special-needs-hub-v235.json",
            self.site / "api/special-needs-guides-v221.json",
        ]
        before = [digest(path) for path in tracked]
        second = self.publish()
        after = [digest(path) for path in tracked]

        self.assertEqual(first["guide_count"], second["guide_count"])
        self.assertEqual(before, after)
        robots = (self.site / "robots.txt").read_text(encoding="utf-8")
        child = f"Sitemap: {BASE}/sitemap-special-needs.xml"
        self.assertEqual(robots.count(child), 1)
        self.assertIn(f"Sitemap: {BASE}/sitemap.xml", robots)


if __name__ == "__main__":
    unittest.main()
