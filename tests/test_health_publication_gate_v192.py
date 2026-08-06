import importlib.util
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "enforce_health_publication_gate_v192.py"
APPLY = ROOT / "scripts" / "apply_homepage_v20.py"

spec = importlib.util.spec_from_file_location("health_publication_gate_v192", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

BLOCKED_SLUG = "autism-family-practical-guide"
APPROVED_SLUG = "adhd-family-practical-guide"
BLOCKED_ROUTE = f"care-guides/{BLOCKED_SLUG}/"
APPROVED_ROUTE = f"care-guides/{APPROVED_SLUG}/"
BASE = "https://healthrenewal.org/"


class HealthPublicationGateV192Tests(unittest.TestCase):
    def write(self, site: Path, relative: str, content: str) -> Path:
        path = site / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def build_fixture(self, site: Path) -> None:
        approved_url = BASE + APPROVED_ROUTE
        blocked_url = BASE + BLOCKED_ROUTE
        care_schema = {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "hasPart": [
                {"@type": "Article", "name": "ADHD", "url": approved_url},
                {"@type": "Article", "name": "Autism", "url": blocked_url},
            ],
        }
        care_hub = (
            '<html lang="ar" dir="rtl"><main>'
            f'<script type="application/ld+json">{json.dumps(care_schema)}</script>'
            f'<article id="approved"><h2>دليل ADHD المعتمد</h2><a href="/{APPROVED_ROUTE}">افتح المعتمد</a></article>'
            f'<article id="blocked"><h2>دليل يحتاج مراجعة</h2><a href="/{BLOCKED_ROUTE}">افتح المحجوب</a></article>'
            '</main></html>'
        )
        family = (
            '<html><main><section id="approved-family">مسار عائلي معتمد</section>'
            '<!-- autism-family-journey-v73 -->'
            f'<section><a href="/{BLOCKED_ROUTE}">رابط محجوب</a></section>'
            '<!-- /autism-family-journey-v73 -->'
            '</main></html>'
        )
        encyclopedia = (
            '<html><main><section id="approved-encyclopedia">محتوى موسوعي معتمد</section>'
            f'<p><a href="{BASE}{BLOCKED_ROUTE}">تفاصيل محجوبة</a></p>'
            '</main></html>'
        )
        self.write(site, "care-guides/index.html", care_hub)
        self.write(site, f"care-guides/{APPROVED_SLUG}/index.html", "<html><main>approved</main></html>")
        self.write(site, f"care-guides/{BLOCKED_SLUG}/index.html", "<html><main>blocked</main></html>")
        self.write(site, "sectors/family/index.html", family)
        self.write(site, "encyclopedia/index.html", encyclopedia)

        namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
        care_root = ET.Element("urlset", xmlns=namespace)
        for url in [BASE + "care-guides/", approved_url, blocked_url]:
            node = ET.SubElement(care_root, "url")
            ET.SubElement(node, "loc").text = url
        ET.ElementTree(care_root).write(site / "sitemap-care-guides.xml", encoding="utf-8", xml_declaration=True)

        main_root = ET.Element("urlset", xmlns=namespace)
        for url in [BASE, approved_url, blocked_url]:
            node = ET.SubElement(main_root, "url")
            ET.SubElement(node, "loc").text = url
        ET.ElementTree(main_root).write(site / "sitemap.xml", encoding="utf-8", xml_declaration=True)

        self.write(
            site,
            "api/care-guides-v21.json",
            json.dumps(
                {
                    "version": 178,
                    "guides": 2,
                    "pages": 3,
                    "sitemap_urls": 3,
                    "autism_review_status": "needs-specialist-review",
                    "autism_human_specialist_review_claimed": False,
                },
                ensure_ascii=False,
            ),
        )
        self.write(
            site,
            "api/care-guides-homepage-v21.json",
            json.dumps(
                {
                    "version": 73,
                    "adhd_inbound_from_care_hub": True,
                    "autism_inbound_from_care_hub": True,
                    "autism_inbound_from_family_hub": True,
                    "autism_inbound_from_encyclopedia_hub": True,
                    "autism_outgoing_to_care_hub": True,
                    "changed": {},
                },
                ensure_ascii=False,
            ),
        )

    def test_blocks_specialist_review_content_without_removing_approved_sibling(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            self.build_fixture(site)
            original_site = module.SITE
            module.SITE = site
            try:
                report = module.enforce()
            finally:
                module.SITE = original_site

            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["blocked_slugs"], [BLOCKED_SLUG])
            self.assertFalse((site / "care-guides" / BLOCKED_SLUG).exists())
            self.assertTrue((site / "care-guides" / APPROVED_SLUG / "index.html").is_file())

            care_hub = (site / "care-guides" / "index.html").read_text(encoding="utf-8")
            family = (site / "sectors" / "family" / "index.html").read_text(encoding="utf-8")
            encyclopedia = (site / "encyclopedia" / "index.html").read_text(encoding="utf-8")
            for text in [care_hub, family, encyclopedia]:
                self.assertNotIn(BLOCKED_ROUTE, text)
            self.assertIn(APPROVED_ROUTE, care_hub)
            self.assertIn('id="approved"', care_hub)
            self.assertNotIn('id="blocked"', care_hub)
            self.assertIn("approved-family", family)
            self.assertIn("approved-encyclopedia", encyclopedia)

            for relative in ["sitemap-care-guides.xml", "sitemap.xml"]:
                text = (site / relative).read_text(encoding="utf-8")
                self.assertNotIn(BLOCKED_ROUTE, text)
                self.assertIn(APPROVED_ROUTE, text)

            care_report = json.loads((site / "api" / "care-guides-v21.json").read_text(encoding="utf-8"))
            self.assertEqual(care_report["publication_gate_version"], 192)
            self.assertFalse(care_report["needs_specialist_review_published"])
            self.assertFalse(care_report["autism_published"])
            self.assertEqual(care_report["pages"], 2)
            self.assertEqual(care_report["sitemap_urls"], 2)

            journey = json.loads((site / "api" / "care-guides-homepage-v21.json").read_text(encoding="utf-8"))
            self.assertFalse(journey["autism_inbound_from_care_hub"])
            self.assertTrue(journey["blocked_review_links_removed"])
            self.assertTrue(journey["no_blocked_review_routes"])

    def test_pipeline_runs_gate_once_and_last(self):
        text = APPLY.read_text(encoding="utf-8")
        gate = 'run_publisher("enforce_health_publication_gate_v192.py")'
        accessible_sitemap = 'register_sitemap("sitemap-accessible-arabic-content.xml")'
        self.assertEqual(text.count(gate), 1)
        self.assertLess(text.index(accessible_sitemap), text.index(gate))
        self.assertLess(text.index(gate), text.index("print(json.dumps(report"))
        self.assertIn('"health_publication_gate": 192', text)


def load_tests(loader, tests, pattern):
    """Run institutional route contracts inside the active publication gate."""
    from tests import test_institutional_route_hubs_v1 as institutional_routes

    tests.addTests(loader.loadTestsFromModule(institutional_routes))
    return tests


if __name__ == "__main__":
    unittest.main()
