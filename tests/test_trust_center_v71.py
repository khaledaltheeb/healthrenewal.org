import importlib.util
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "publish_trust_center_v71.py"


def load_module():
    spec = importlib.util.spec_from_file_location("publish_trust_center_v71", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TrustCenterPublisherTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.site = self.root / "_site"
        self.site.mkdir()
        (self.site / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><body><header><nav>'
            '<a href="encyclopedia/">الموسوعة</a></nav></header>'
            '<main><h1>الرئيسية</h1></main><footer><p>النهاية</p></footer>'
            '</body></html>',
            encoding="utf-8",
        )
        self.write_sitemap_index()
        self.claims = self.root / "claims.json"
        self.urgent = self.root / "urgent.json"
        self.disability = self.root / "disability.json"
        self.claims.write_text(
            json.dumps(
                {
                    "updated_at": "2026-07-20",
                    "policy": {
                        "default_publishable": False,
                        "required_status_for_publication": "verified",
                    },
                    "claims": [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.urgent.write_text(
            json.dumps(
                {
                    "updated_at": "2026-07-21",
                    "review_status": "needs-external-review",
                    "default_publishable": False,
                    "services": [],
                    "fallback_when_local_service_unverified": [
                        "اطلب خدمات الطوارئ المحلية عند الخطر الوشيك."
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.disability.write_text(
            json.dumps(
                {
                    "updated_at": "2026-07-22",
                    "review_status": "needs-external-review",
                    "default_publishable": False,
                    "required_principles": {
                        "person_not_diagnosis": True,
                        "consent_and_assent": True,
                        "privacy_and_data_minimization": True,
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.module.CLAIMS_PATH = self.claims
        self.module.URGENT_PATH = self.urgent
        self.module.DISABILITY_PATH = self.disability

    def tearDown(self):
        self.temp.cleanup()

    def write_sitemap_index(self):
        (self.site / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<sitemap><loc>https://healthrenewal.org/sitemap-core.xml</loc></sitemap>'
            "</sitemapindex>",
            encoding="utf-8",
        )

    def test_publish_creates_accessible_indexable_page_and_report(self):
        report = self.module.publish(self.site)
        page = (self.site / "trust" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(page.count("<h1>"), 1)
        self.assertIn('<html lang="ar" dir="rtl">', page)
        self.assertIn(
            '<link rel="canonical" href="https://healthrenewal.org/trust/">',
            page,
        )
        self.assertIn('type="application/ld+json"', page)
        self.assertIn('datetime="2026-07-22"', page)
        self.assertIn("تحتاج مراجعة خارجية متخصصة", page)
        self.assertNotIn("تمت مراجعتها خارجيًا", page)
        self.assertTrue(report["default_deny"])
        self.assertEqual(report["institutional_claims_verified"], 0)
        stored = json.loads(
            (self.site / "api" / "trust-center-v71.json").read_text(encoding="utf-8")
        )
        self.assertEqual(stored, report)

    def test_homepage_and_sitemap_are_idempotent(self):
        self.module.publish(self.site)
        self.module.publish(self.site)
        homepage = (self.site / "index.html").read_text(encoding="utf-8")
        self.assertEqual(homepage.count('href="trust/"'), 2)
        tree = ET.parse(self.site / "sitemap.xml")
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        refs = [
            node.text
            for node in tree.findall("s:sitemap/s:loc", ns)
            if node.text == "https://healthrenewal.org/sitemap-trust.xml"
        ]
        self.assertEqual(len(refs), 1)
        trust_tree = ET.parse(self.site / "sitemap-trust.xml")
        urls = trust_tree.findall("s:url/s:loc", ns)
        self.assertEqual(
            [node.text for node in urls],
            ["https://healthrenewal.org/trust/"],
        )

    def test_urlset_root_is_supported_without_mixing_contracts(self):
        (self.site / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://healthrenewal.org/</loc></url>'
            "</urlset>",
            encoding="utf-8",
        )
        self.module.publish(self.site)
        tree = ET.parse(self.site / "sitemap.xml")
        root = tree.getroot()
        self.assertTrue(root.tag.endswith("urlset"))
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = [node.text for node in tree.findall("s:url/s:loc", ns)]
        self.assertEqual(locs.count("https://healthrenewal.org/trust/"), 1)
        self.assertEqual(tree.findall("s:sitemap", ns), [])

    def test_unverified_urgent_service_blocks_publication(self):
        payload = json.loads(self.urgent.read_text(encoding="utf-8"))
        payload["services"] = [{"status": "pending_verification"}]
        self.urgent.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(SystemExit):
            self.module.publish(self.site)
        self.assertFalse((self.site / "trust" / "index.html").exists())

    def test_non_deny_policy_blocks_publication(self):
        payload = json.loads(self.claims.read_text(encoding="utf-8"))
        payload["policy"]["default_publishable"] = True
        self.claims.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(SystemExit):
            self.module.publish(self.site)

    def test_page_does_not_claim_external_review_when_status_needs_review(self):
        self.module.publish(self.site)
        page = (self.site / "trust" / "index.html").read_text(encoding="utf-8")
        self.assertIn("وجود سياسة أو اختبار آلي لا يعني مراجعة سريرية", page)
        self.assertIn("تحتاج مراجعة خارجية متخصصة", page)
        self.assertNotIn("مراجع من خبراء", page)


if __name__ == "__main__":
    unittest.main()
