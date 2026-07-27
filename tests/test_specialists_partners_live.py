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
            "specialists-partners/index.html": """<!doctype html><html lang=\"ar\" dir=\"rtl\"><head><title>فريقنا وشركاؤنا ذوو الاختصاص | التربية الخاصة والسمع والنطق</title><link rel=\"canonical\" href=\"https://khaledaltheeb.github.io/pterminology-site/specialists-partners/\"><script type=\"application/ld+json\">{\"@context\":\"https://schema.org\",\"@graph\":[{\"@type\":\"CollectionPage\"},{\"@type\":\"BreadcrumbList\"}]}</script></head><body><main><h1>فريقنا وشركاؤنا ذوو الاختصاص</h1><p>التربية الخاصة والسمع والنطق</p><section id=\"directory\"></section><section id=\"matcher\"></section></main></body></html>""",
            "specialists-partners/join.html": """<!doctype html><html lang=\"ar\" dir=\"rtl\"><body><main><h1>إضافة مختص أو مركز</h1><p>الموافقة الكتابية مطلوبة قبل النشر.</p></main></body></html>""",
            "specialists-partners/verification.html": """<!doctype html><html lang=\"ar\" dir=\"rtl\"><body><main><h1>سياسة التحقق من المختصين والمراكز</h1><p>معايير التحقق المهني والتعليق والإزالة عند تعذر التحقق.</p></main></body></html>""",
            "specialists-partners/assets/sector.js": """const allowed=['http:','https:','mailto:','tel:'];const visible=(p)=>p.publicationStatus==='published'&&p.verification?.status==='verified'&&p.consent?.publicProfileApproved===true;""",
            "robots.txt": f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}sitemap-specialists-partners.xml\n",
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
            },
            "api/v1/platform.json": {
                "resources": [{"id": "specialists-partners"}],
                "endpoints": {
                    "specialistsPartners": f"{BASE_URL}api/v1/specialists-partners.json",
                    "specialistsPartnersDirectory": f"{BASE_URL}specialists-partners/data/providers.json",
                },
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
        return root

    def test_static_contract_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = validate_root(self.make_root(Path(tmp)))
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["sitemap_routes"], 4)
            self.assertTrue(report["publication_guard"])

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
