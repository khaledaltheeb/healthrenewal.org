from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_trust_guides_v201.py"
BASE = "https://healthrenewal.org"
EXPECTED = {
    "editorial-methodology/index.html": BASE + "/editorial-methodology/",
    "evaluate-mental-health-information/index.html": BASE + "/evaluate-mental-health-information/",
    "guides/source-citation-and-update-transparency/index.html": BASE + "/guides/source-citation-and-update-transparency/",
}


class VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "svg"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "svg"} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data.strip())


def visible_words(text: str) -> int:
    parser = VisibleText()
    parser.feed(text)
    return len(re.findall(r"[\w\u0600-\u06ff]+", " ".join(parser.parts)))


class TrustGuidesV201Tests(unittest.TestCase):
    def make_site(self) -> Path:
        site = Path(tempfile.mkdtemp(prefix="trust-guides-v201-"))
        self.addCleanup(lambda: shutil.rmtree(site, ignore_errors=True))
        (site / "trust").mkdir(parents=True)
        (site / "magazine").mkdir(parents=True)
        (site / "trust/index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><body><main><h1>الثقة</h1></main></body></html>',
            encoding="utf-8",
        )
        (site / "magazine/index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><body><main><h1>المجلة</h1></main></body></html>',
            encoding="utf-8",
        )
        (site / "sitemap.xml").write_text(
            '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
            encoding="utf-8",
        )
        return site

    def publish(self, site: Path) -> None:
        completed = subprocess.run(
            ["python3", str(SCRIPT), str(site)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_publishes_three_complete_honest_pages(self) -> None:
        site = self.make_site()
        self.publish(site)
        for relative, canonical in EXPECTED.items():
            path = site / relative
            self.assertTrue(path.is_file(), relative)
            text = path.read_text(encoding="utf-8")
            self.assertIn('<html lang="ar" dir="rtl">', text)
            self.assertEqual(len(re.findall(r"<h1\b", text)), 1)
            self.assertIn(f'<link rel="canonical" href="{canonical}">', text)
            self.assertIn("application/ld+json", text)
            self.assertIn("منصة روافد", text)
            self.assertIn("للعافية النفسية والدمج والتمكين", text)
            self.assertIn("لا توجد دعوى مراجعة اختصاصية خارجية أو اعتماد رسمي", text)
            self.assertNotIn("معتمد دوليًا", text)
            self.assertGreaterEqual(visible_words(text), 500)

        citation = (site / "guides/source-citation-and-update-transparency/index.html").read_text(encoding="utf-8")
        inputs = re.findall(r'<input id="citation-check-(\d+)" type="checkbox" aria-label="بند التحقق رقم \d+">', citation)
        labels = re.findall(r'<label for="citation-check-(\d+)">', citation)
        self.assertGreaterEqual(len(inputs), 8)
        self.assertEqual(inputs, labels)

        report = json.loads((site / "api/trust-guides-v201.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "built-not-published")
        self.assertEqual(report["page_count"], 3)
        self.assertFalse(report["external_specialist_review_claimed"])
        risks = {item["key"]: item["risk_level"] for item in report["pages"]}
        self.assertEqual(risks["evaluate"], "moderate")
        self.assertEqual(risks["citation"], "low")

    def test_sitemap_and_discovery_links_are_idempotent(self) -> None:
        site = self.make_site()
        self.publish(site)
        self.publish(site)
        child = ET.parse(site / "sitemap-trust-guides.xml").getroot()
        urls = [(node.text or "").strip() for node in child.findall("{*}url/{*}loc")]
        self.assertEqual(set(urls), set(EXPECTED.values()))
        self.assertEqual(len(urls), 3)
        main = ET.parse(site / "sitemap.xml").getroot()
        main_urls = [(node.text or "").strip() for node in main.findall("{*}url/{*}loc")]
        for url in EXPECTED.values():
            self.assertEqual(main_urls.count(url), 1)
        for relative in ("trust/index.html", "magazine/index.html"):
            text = (site / relative).read_text(encoding="utf-8")
            self.assertEqual(text.count("trust-guides-v201"), 1)
            for canonical in EXPECTED.values():
                route = canonical.removeprefix(BASE + "/")
                self.assertIn(f'/{route}', text)

    def test_sources_retain_declared_review_states(self) -> None:
        sources = [
            ROOT / "content/v178/editorial-methodology-ar.json",
            ROOT / "content/v181/evaluate-mental-health-information-ar.json",
            ROOT / "content/v191/source-citation-guide-ar.json",
        ]
        payloads = [json.loads(path.read_text(encoding="utf-8")) for path in sources]
        self.assertTrue(all(item["status"] == "internally-reviewed" for item in payloads))
        self.assertEqual(payloads[1]["risk_level"], "moderate")
        self.assertEqual(payloads[2]["risk_level"], "low")


if __name__ == "__main__":
    unittest.main()
