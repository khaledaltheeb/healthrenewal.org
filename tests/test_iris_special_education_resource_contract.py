import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/institutional-resources/iris-special-education.json"
PAGE = ROOT / "learning-paths/iris-special-education/index.html"


class LinkCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.images = []
        self.h1_count = 0
        self.main_ids = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
        if tag == "img":
            self.images.append(values)
        if tag == "h1":
            self.h1_count += 1
        if tag == "main" and values.get("id"):
            self.main_ids.append(values["id"])


class IrisSpecialEducationResourceContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(DATA.read_text(encoding="utf-8"))
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.parser = LinkCollector()
        cls.parser.feed(cls.html)

    def test_registry_identity_and_review(self):
        self.assertEqual(self.registry["resource_family_id"], "iris-special-education")
        self.assertEqual(self.registry["provider"]["name"], "IRIS Center")
        self.assertEqual(self.registry["verification"]["verified_at"], "2026-08-05")
        self.assertEqual(
            self.registry["verification"]["review_status"],
            "rights-verified-content-link-only",
        )
        self.assertFalse(self.registry["rights"]["partnership_claim"])

    def test_module_inventory_is_unique_and_official(self):
        modules = self.registry["modules"]
        self.assertGreaterEqual(len(modules), 15)
        ids = [module["id"] for module in modules]
        urls = [module["url"] for module in modules]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(urls), len(set(urls)))
        for module in modules:
            self.assertTrue(module["title_ar"].strip())
            self.assertGreaterEqual(len(module["arabic_description"]), 70)
            self.assertGreaterEqual(len(module["local_action"]), 45)
            parsed = urlparse(module["url"])
            self.assertEqual(parsed.scheme, "https")
            self.assertEqual(parsed.netloc, "iris.peabody.vanderbilt.edu")
            self.assertTrue(parsed.path.startswith("/module/"))
            self.assertEqual(module["certificate_status"], "check-provider-page")
            self.assertEqual(module["estimated_time"], "check-provider-page")

    def test_rights_contract_blocks_unlicensed_uses(self):
        rights = " ".join(self.registry["rights"]["prohibited"])
        for required in ("ترجمة", "اختبارات", "صور", "شعارات", "شراكة", "اعتماد"):
            self.assertIn(required, rights)
        attribution = self.registry["rights"]["required_attribution_ar"]
        self.assertIn("IRIS Center", attribution)
        self.assertIn("Health Renewal", attribution)
        self.assertIn("موقع IRIS الرسمي", attribution)

    def test_page_has_publication_metadata_and_accessibility(self):
        self.assertIn('<html lang="ar" dir="rtl">', self.html)
        self.assertEqual(self.parser.h1_count, 1)
        self.assertIn("main-content", self.parser.main_ids)
        self.assertIn('href="#main-content"', self.html)
        self.assertIn(
            '<link rel="canonical" href="https://healthrenewal.org/learning-paths/iris-special-education/">',
            self.html,
        )
        self.assertIn('"@type":"LearningResource"', self.html)
        self.assertIn("@media(prefers-reduced-motion:reduce)", self.html)
        self.assertIn("@media print", self.html)
        self.assertIn("pt-platform-shell:v1", self.html)

    def test_page_does_not_embed_iris_images_or_claim_partnership(self):
        self.assertEqual(self.parser.images, [])
        lowered = self.html.lower()
        self.assertNotIn("iris-logo", lowered)
        self.assertNotIn("partner of iris", lowered)
        self.assertIn("لا توجد شراكة", self.html)
        self.assertIn("لا نترجم وحدات IRIS", self.html)
        self.assertIn("لا نستضيفها", self.html)
        self.assertIn("لا ننسخ اختباراتها", self.html)

    def test_every_registry_module_is_linked_from_page(self):
        page_links = set(self.parser.links)
        for module in self.registry["modules"]:
            self.assertIn(module["url"], page_links)

    def test_external_links_are_https_and_safe(self):
        external_links = [link for link in self.parser.links if link.startswith("http")]
        self.assertGreaterEqual(len(external_links), 16)
        for link in external_links:
            self.assertTrue(link.startswith("https://"))
        iris_anchors = re.findall(
            r'<a class="module" href="(https://iris\.peabody\.vanderbilt\.edu/[^"]+)" rel="([^"]+)"',
            self.html,
        )
        self.assertGreaterEqual(len(iris_anchors), 15)
        for _, rel in iris_anchors:
            self.assertIn("noopener", rel)
            self.assertIn("noreferrer", rel)


if __name__ == "__main__":
    unittest.main()
