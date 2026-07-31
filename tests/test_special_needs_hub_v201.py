from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_special_needs_hub_v201.py"
FINALIZER = ROOT / "scripts" / "finalize_special_needs_hub_accessibility_v201.py"


class TextParser(HTMLParser):
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


class SpecialNeedsHubV201Tests(unittest.TestCase):
    def make_site(self) -> Path:
        site = Path(tempfile.mkdtemp(prefix="special-needs-v201-"))
        self.addCleanup(lambda: shutil.rmtree(site, ignore_errors=True))
        (site / "special-needs/executable-instructions-adhd-learning-difficulties").mkdir(parents=True)
        (site / "special-needs/executable-instructions-adhd-learning-difficulties/index.html").write_text("existing", encoding="utf-8")
        (site / "special-needs/inclusive-language-disability").mkdir(parents=True)
        (site / "special-needs/inclusive-language-disability/index.html").write_text("existing", encoding="utf-8")
        (site / "sitemap-special-needs.xml").write_text(
            '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
            encoding="utf-8",
        )
        return site

    def publish(self, site: Path) -> None:
        completed = subprocess.run(["python3", str(SCRIPT), str(site)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        finalized = subprocess.run(["python3", str(FINALIZER), str(site)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(finalized.returncode, 0, finalized.stderr)

    def test_publishes_complete_searchable_hub_without_placeholders(self) -> None:
        site = self.make_site()
        self.publish(site)
        output = site / "special-needs/index.html"
        text = output.read_text(encoding="utf-8")
        self.assertIn("منصة الصحة النفسية وذوي الاحتياجات الخاصة", text)
        self.assertIn("معرفة تحترم الإنسان. دعم يوسّع الإمكانات.", text)
        self.assertEqual(len(re.findall(r'class="detail" id="', text)), 16)
        self.assertEqual(len(re.findall(r'class="path-card"', text)), 16)
        self.assertNotIn("قيد الإعداد", text)
        self.assertNotIn("قيد التوسع", text)
        self.assertIn('id="hub-search"', text)
        self.assertEqual(text.count('for="hub-search"'), 1)
        self.assertEqual(text.count('aria-label="البحث داخل مركز ذوي الاحتياجات الخاصة"'), 1)
        self.assertIn("application/ld+json", text)
        self.assertIn("sitemap-special-needs.xml", str(site / "sitemap-special-needs.xml"))
        parser = TextParser()
        parser.feed(text)
        words = re.findall(r"[\w\u0600-\u06ff]+", " ".join(parser.parts))
        self.assertGreaterEqual(len(words), 1200)
        report = json.loads((site / "api/special-needs-hub-v201.json").read_text(encoding="utf-8"))
        self.assertEqual(report["pathways"], 16)
        self.assertEqual(report["existing_resources"], 2)
        self.assertEqual(report["placeholder_phrases"], [])
        self.assertEqual(report["review_status"], "internally-reviewed")
        self.assertEqual(report["external_review"], "recommended-not-completed")
        self.assertTrue(report["search_accessibility"]["explicit_label_for"])
        self.assertTrue(report["search_accessibility"]["accessible_name"])

    def test_resource_links_are_emitted_only_for_existing_pages(self) -> None:
        site = self.make_site()
        self.publish(site)
        text = (site / "special-needs/index.html").read_text(encoding="utf-8")
        self.assertIn("executable-instructions-adhd-learning-difficulties", text)
        self.assertIn("inclusive-language-disability", text)
        self.assertNotIn('href="/special-needs/caregiver-wellbeing/"', text)
        self.assertNotIn('href="/special-needs/accessible-arabic-digital-content/"', text)


if __name__ == "__main__":
    unittest.main()
