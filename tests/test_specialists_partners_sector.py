from __future__ import annotations

import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTOR = ROOT / "specialists-partners"
BASE = "https://healthrenewal.org"


class SpecialistsPartnersSectorTests(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        required = (
            SECTOR / "index.html",
            SECTOR / "join.html",
            SECTOR / "verification.html",
            SECTOR / "assets" / "sector.css",
            SECTOR / "assets" / "directory-core.js",
            SECTOR / "assets" / "sector.js",
            SECTOR / "data" / "providers.json",
            SECTOR / "data" / "provider.schema.json",
            SECTOR / "data" / "provider-import-template.csv",
            ROOT / "team-and-partners" / "index.html",
            ROOT / "assets" / "platform" / "platform-core.js",
            ROOT / "api" / "v1" / "specialists-partners.json",
            ROOT / "api" / "specialists-partners-quality-v354.json",
            ROOT / "sitemap-specialists-partners.xml",
        )
        for path in required:
            self.assertTrue(path.is_file(), path)

    def test_public_pages_have_core_accessibility_and_seo_contracts(self) -> None:
        pages = {
            "index.html": "/specialists-partners/",
            "join.html": "/specialists-partners/join.html",
            "verification.html": "/specialists-partners/verification.html",
        }
        for filename, canonical_path in pages.items():
            text = (SECTOR / filename).read_text(encoding="utf-8")
            self.assertEqual(text.count("<h1"), 1, filename)
            self.assertIn('lang="ar"', text)
            self.assertIn('dir="rtl"', text)
            self.assertIn('href="#main"', text)
            self.assertIn(f'<link rel="canonical" href="{BASE}{canonical_path}">', text)
            self.assertIn("assets/sector.css", text)
            self.assertNotIn("معاقين", text)

    def test_global_navigation_exposes_sector(self) -> None:
        shell = (ROOT / "assets" / "platform" / "platform-core.js").read_text(encoding="utf-8")
        self.assertIn("['الفريق والشركاء', 'specialists-partners/']", shell)
        self.assertEqual(shell.count("'specialists-partners/'"), 1)

    def test_directory_data_starts_empty_and_enforces_verified_publication(self) -> None:
        payload = json.loads((SECTOR / "data" / "providers.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["schemaVersion"], "1.0.0")
        self.assertIsInstance(payload["providers"], list)
        self.assertEqual(payload["providers"], [])
        self.assertIn("written", payload["publicationPolicy"].lower())
        self.assertIn("Do not store", payload["privacyNotice"])

        for provider in payload["providers"]:
            if provider.get("publicationStatus") == "published":
                self.assertEqual(provider["verification"]["status"], "verified")
                self.assertTrue(provider["consent"]["publicProfileApproved"])
                self.assertTrue(provider["verification"]["sources"])

    def test_schema_requires_identity_scope_verification_and_consent(self) -> None:
        schema = json.loads((SECTOR / "data" / "provider.schema.json").read_text(encoding="utf-8"))
        required = set(schema["required"])
        self.assertTrue({"id", "entityType", "displayName", "specialties", "verification", "consent"} <= required)
        statuses = schema["properties"]["verification"]["properties"]["status"]["enum"]
        self.assertTrue(
            {"verified", "provisional", "pending", "unverified", "rejected", "expired"}
            <= set(statuses)
        )
        self.assertEqual(schema["properties"]["consent"]["properties"]["publicProfileApproved"]["const"], True)
        specialties = schema["properties"]["specialties"]["items"]["enum"]
        for item in ("speech_language", "audiology", "special_education", "early_intervention", "aac"):
            self.assertIn(item, specialties)

    def test_javascript_uses_local_dataset_and_safe_published_contacts(self) -> None:
        script = (SECTOR / "assets" / "sector.js").read_text(encoding="utf-8")
        core = (SECTOR / "assets" / "directory-core.js").read_text(encoding="utf-8")
        self.assertIn("data/providers.json", script)
        self.assertIn("cache:'no-store'", script)
        self.assertIn("core.prepareProviders", script)
        self.assertIn("provider?.publicationStatus === 'published'", core)
        self.assertIn("provider?.verification?.status === 'verified'", core)
        self.assertIn("provider?.consent?.publicProfileApproved === true", core)
        self.assertIn("normalizeArabic", core)
        self.assertIn("ageMatches", core)
        self.assertIn("['https:','mailto:','tel:']", script)
        self.assertIn("protocol === 'https:'", script)
        self.assertNotIn("XMLHttpRequest", script)
        self.assertNotIn("FormData", script)
        self.assertNotIn("sendBeacon", script)
        self.assertNotIn("localStorage", script)
        self.assertNotIn("sessionStorage", script)
        self.assertNotIn("javascript:", script.lower())

    def test_sitemap_and_robots_registration(self) -> None:
        sitemap = ROOT / "sitemap-specialists-partners.xml"
        locations = [
            (node.text or "").strip()
            for node in ET.parse(sitemap).getroot().findall("{*}url/{*}loc")
            if node.text
        ]
        expected = {
            f"{BASE}/specialists-partners/",
            f"{BASE}/specialists-partners/verification.html",
            f"{BASE}/specialists-partners/join.html",
            f"{BASE}/api/v1/specialists-partners.json",
        }
        self.assertEqual(set(locations), expected)
        self.assertEqual(len(locations), len(set(locations)))
        robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
        self.assertIn(f"Sitemap: {BASE}/sitemap-index.xml", robots)
        sitemap_index = ROOT / "sitemap-index.xml"
        index_locations = {
            (node.text or "").strip()
            for node in ET.parse(sitemap_index).getroot().findall("{*}sitemap/{*}loc")
            if node.text
        }
        self.assertIn(f"{BASE}/sitemap-specialists-partners.xml", index_locations)

    def test_platform_api_registers_sector(self) -> None:
        platform = json.loads((ROOT / "api" / "v1" / "platform.json").read_text(encoding="utf-8"))
        resources = {item["id"]: item for item in platform["resources"]}
        self.assertIn("specialists-partners", resources)
        self.assertEqual(resources["specialists-partners"]["type"], "directory")
        self.assertEqual(platform["endpoints"]["specialistsPartners"], f"{BASE}/api/v1/specialists-partners.json")
        self.assertEqual(
            platform["endpoints"]["specialistsPartnersQuality"],
            f"{BASE}/api/specialists-partners-quality-v354.json",
        )
        self.assertEqual(platform["integrationPolicy"]["providerPublication"], "verification_and_written_consent_required")
        self.assertIn("publishing client or child case data", platform["integrationPolicy"]["prohibited"])


if __name__ == "__main__":
    unittest.main()
