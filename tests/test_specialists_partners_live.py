from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_specialists_partners_live import BASE_URL, validate_root


class SpecialistsPartnersLiveTests(unittest.TestCase):
    def make_root(self, base: Path) -> Path:
        root = base / "site"
        files = {
            "specialists-partners/index.html": """<!doctype html><html lang=\"ar\" dir=\"rtl\"><head><title>فريقنا وشركاؤنا ذوو الاختصاص | التربية الخاصة والسمع والنطق</title><link rel=\"canonical\" href=\"https://healthrenewal.org/specialists-partners/\"><script type=\"application/ld+json\">{\"@context\":\"https://schema.org\",\"@graph\":[{\"@type\":\"CollectionPage\"},{\"@type\":\"BreadcrumbList\"}]}</script><script defer src=\"assets/directory-core.js?v=4.1.0\"></script></head><body><main><h1>فريقنا وشركاؤنا ذوو الاختصاص</h1><p>التربية الخاصة والسمع والنطق</p><section id=\"matcher\"></section><section id=\"directory\"><div id=\"directory-health\"></div><h2>لا توجد ملفات مهنية منشورة حاليًا</h2></section><section><h2>ستة أسئلة قبل حجز الخدمة</h2></section></main></body></html>""",
            "specialists-partners/join.html": """<!doctype html><html lang=\"ar\" dir=\"rtl\"><body><main><h1>إضافة مختص أو مركز</h1><p>الموافقة الكتابية مطلوبة قبل النشر.</p></main></body></html>""",
            "specialists-partners/verification.html": """<!doctype html><html lang=\"ar\" dir=\"rtl\"><body><main><h1>سياسة التحقق من المختصين والمراكز</h1><p>معايير التحقق المهني والتعليق والإزالة عند تعذر التحقق.</p></main></body></html>""",
            "specialists-partners/assets/sector.js": """const api='/v1/providers?limit=250';const fallback='data/providers.json';const allowed=['https:','mailto:','tel:'];const protocol='https:';const safe=protocol === 'https:';const visible=core.prepareProviders([]);""",
            "specialists-partners/assets/directory-core.js": """const specialtyAny=[];function normalizeArabic(){} function ageMatches(){} const visible=(provider)=>provider?.publicationStatus === 'published'&&provider?.verification?.status === 'verified'&&provider?.consent?.publicProfileApproved === true;""",
            "robots.txt": f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}sitemap-index.xml\n",
            "assets/platform/platform-core.js": "const navItems=[['الفريق والشركاء', 'specialists-partners/']];",
        }
        for relative, content in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        data_files = {
            "specialists-partners/data/providers.json": {
                "schemaVersion": "1.0.0",
                "publicationPolicy": "Only records with written publication consent may be published.",
                "providers": [],
            },
            "specialists-partners/data/provider.schema.json": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "required": [
                    "id",
                    "entityType",
                    "displayName",
                    "specialties",
                    "verification",
                    "publicationStatus",
                    "consent",
                ],
                "properties": {
                    "consent": {
                        "type": "object",
                        "properties": {"publicProfileApproved": {"const": True}},
                    }
                },
            },
            "api/v1/specialists-partners.json": {
                "status": "active",
                "directory": f"{BASE_URL}specialists-partners/data/providers.json",
                "qualityReport": f"{BASE_URL}api/specialists-partners-quality-v354.json",
            },
            "api/v1/platform.json": {
                "resources": [{"id": "specialists-partners"}],
                "endpoints": {
                    "specialistsPartners": f"{BASE_URL}api/v1/specialists-partners.json",
                    "specialistsPartnersDirectory": f"{BASE_URL}specialists-partners/data/providers.json",
                    "specialistsPartnersQuality": f"{BASE_URL}api/specialists-partners-quality-v354.json",
                },
            },
            "api/specialists-partners-quality-v354.json": {
                "version": 354,
                "status": "passed",
                "interfaceCount": 9,
                "errorCount": 0,
                "unsafePublishedProviderIds": [],
            },
        }
        for relative, payload in data_files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        (root / "sitemap-specialists-partners.xml").write_text(
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
            "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
            f"<url><loc>{BASE_URL}specialists-partners/</loc></url>"
            f"<url><loc>{BASE_URL}specialists-partners/join.html</loc></url>"
            f"<url><loc>{BASE_URL}specialists-partners/verification.html</loc></url>"
            f"<url><loc>{BASE_URL}api/v1/specialists-partners.json</loc></url>"
            "</urlset>",
            encoding="utf-8",
        )
        (root / "sitemap-index.xml").write_text(
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
            "<sitemapindex xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
            f"<sitemap><loc>{BASE_URL}sitemap-specialists-partners.xml</loc></sitemap>"
            "</sitemapindex>",
            encoding="utf-8",
        )
        return root

    def test_static_contract_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = validate_root(self.make_root(Path(tmp)))
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["sitemap_routes"], 4)
            self.assertTrue(report["publication_guard"])
            self.assertEqual(report["quality_report_version"], 354)
            self.assertEqual(report["interface_count"], 9)

    def test_published_provider_requires_verification_and_consent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(Path(tmp))
            providers_path = root / "specialists-partners" / "data" / "providers.json"
            payload = json.loads(providers_path.read_text(encoding="utf-8"))
            payload["providers"] = [
                {
                    "id": "unsafe-record",
                    "publicationStatus": "published",
                    "verification": {"status": "pending", "sources": []},
                    "consent": {"publicProfileApproved": False},
                }
            ]
            providers_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "not verified"):
                validate_root(root)


if __name__ == "__main__":
    unittest.main()
