import xml.etree.ElementTree as ET
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReleaseDiscoveryContract(unittest.TestCase):
    def test_rss_contains_only_verified_public_hubs(self):
        feed = (ROOT / "feed.xml").read_text(encoding="utf-8")
        ET.fromstring(feed)
        self.assertIn('rel="self"', feed)
        for missing_route in (
            "/encyclopedia/",
            "/library/",
            "/care-guides/",
            "/daily-tools/",
            "/comparisons/",
        ):
            self.assertNotIn(missing_route, feed)
        for published_route in (
            "/start-here/",
            "/special-needs/",
            "/family-guide/",
            "/magazine/",
            "/addiction/",
            "/learning-paths/",
            "/api/",
        ):
            self.assertIn(published_route, feed)

    def test_ai_catalogues_do_not_claim_unpublished_routes_or_locales(self):
        llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
        llms_full = (ROOT / "llms-full.txt").read_text(encoding="utf-8")
        self.assertIn("Published languages: Arabic (ar)", llms)
        self.assertIn("Published language: Arabic (ar).", llms_full)
        for unsupported in (
            "Additional languages:",
            "/en/",
            "/es/",
            "/encyclopedia/",
            "/library/",
            "/care-guides/",
            "/daily-tools/",
            "/comparisons/",
        ):
            self.assertNotIn(unsupported, llms + llms_full)

    def test_url_sitemaps_do_not_publish_json_api_endpoints(self):
        for filename in (
            "sitemap-specialists-partners.xml",
            "sitemap-source-registry.xml",
            "sitemap-outside-the-box-evidence.xml",
        ):
            text = (ROOT / filename).read_text(encoding="utf-8")
            ET.fromstring(text)
            self.assertNotIn(".json</loc>", text)

    def test_crawler_and_opensearch_contracts_are_explicit(self):
        robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("User-agent: OAI-SearchBot", robots)
        self.assertIn("Sitemap: https://healthrenewal.org/sitemap-index.xml", robots)

        sitemap_index = (ROOT / "sitemap-index.xml").read_text(encoding="utf-8")
        ET.fromstring(sitemap_index)
        self.assertIn("https://healthrenewal.org/sitemap.xml", sitemap_index)

        opensearch = (ROOT / "opensearch.xml").read_text(encoding="utf-8")
        ET.fromstring(opensearch)
        self.assertIn("<Language>ar</Language>", opensearch)
        self.assertIn('rel="self"', opensearch)
        self.assertIn('rel="results"', opensearch)


if __name__ == "__main__":
    unittest.main()
