from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "content_discovery_v219.py"
spec = importlib.util.spec_from_file_location("content_discovery_v219", SCRIPT)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader is not None
spec.loader.exec_module(module)


def page(*, title: str, canonical: str, keywords: str, h1: str, robots: str = "index,follow") -> str:
    return f'''<!doctype html><html lang="ar" dir="rtl"><head>
<title>{title}</title><meta name="description" content="وصف موثوق وموسع للصفحة يخدم المستخدم ومحركات البحث.">
<meta name="keywords" content="{keywords}"><meta name="robots" content="{robots}">
<link rel="canonical" href="{canonical}"></head><body><main><h1>{h1}</h1></main></body></html>'''


class ContentDiscoveryTests(unittest.TestCase):
    def build_site(self, root: Path) -> Path:
        site = root / "site"
        (site / "api" / "v1").mkdir(parents=True)
        (site / "developers").mkdir(parents=True)
        (site / "api" / "v1" / "openapi.json").write_text(
            json.dumps({"openapi": "3.1.0", "info": {}, "paths": {}, "components": {"schemas": {}}}),
            encoding="utf-8",
        )
        (site / "developers" / "index.html").write_text(
            page(
                title="واجهة المطورين وAPI",
                canonical=module.BASE_URL + "developers/",
                keywords="واجهة API,بيانات منظمة,تكامل المواقع,OpenAPI",
                h1="واجهة المطورين وAPI",
            ).replace("</main>", "<table><tbody><tr><td>أصل</td></tr></tbody></table></main>"),
            encoding="utf-8",
        )
        (site / "index.html").write_text(
            page(
                title="منصة روافد",
                canonical=module.BASE_URL,
                keywords="الصحة النفسية,علم النفس,مصطلحات علم النفس,الدعم النفسي",
                h1="منصة الصحة النفسية",
            ),
            encoding="utf-8",
        )
        autism = site / "encyclopedia" / "autism" / "index.html"
        autism.parent.mkdir(parents=True)
        autism.write_text(
            page(
                title="اضطراب طيف التوحد",
                canonical=module.BASE_URL + "encyclopedia/autism/",
                keywords="اضطراب طيف التوحد,التوحد,التدخل المبكر,الدعم الأسري",
                h1="اضطراب طيف التوحد",
            ),
            encoding="utf-8",
        )
        private = site / "private" / "index.html"
        private.parent.mkdir()
        private.write_text(
            page(
                title="صفحة خاصة",
                canonical=module.BASE_URL + "private/",
                keywords="خاص,داخلي,غير مفهرس,اختبار",
                h1="خاص",
                robots="noindex,nofollow",
            ),
            encoding="utf-8",
        )
        return site

    def test_prepare_publish_and_idempotency(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = self.build_site(root)
            prepared = module.prepare(site, root)
            self.assertTrue(prepared["openapi"])
            self.assertTrue((site / "developers" / "content-discovery" / "index.html").is_file())
            self.assertTrue((site / "sitemap-content-discovery.xml").is_file())

            developers = (site / "developers" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(developers.count("data-content-discovery-v219"), 3)

            report = module.publish(site, root)
            self.assertEqual(report["pages"], 4)
            self.assertEqual(report["shards"], 1)
            self.assertFalse(report["personal_data"])
            self.assertFalse(report["clinical_records"])

            manifest = json.loads((site / "api" / "v1" / "content-index.json").read_text(encoding="utf-8"))
            taxonomy = json.loads((site / "api" / "v1" / "taxonomy.json").read_text(encoding="utf-8"))
            shard = json.loads((site / "api" / "v1" / "content-index-001.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["total"], 4)
            self.assertEqual(manifest["shards"][0]["count"], 4)
            self.assertEqual(shard["count"], 4)
            self.assertFalse(any(item["path"] == "/private/" for item in shard["items"]))
            self.assertEqual(taxonomy["total_pages"], 4)
            self.assertTrue(any(topic["label"] == "التوحد" for topic in taxonomy["topics"]))

            openapi = json.loads((site / "api" / "v1" / "openapi.json").read_text(encoding="utf-8"))
            self.assertIn("/api/v1/content-index.json", openapi["paths"])
            self.assertIn("/api/v1/taxonomy.json", openapi["paths"])
            self.assertIn("ContentIndexManifest", openapi["components"]["schemas"])

            first_manifest = (site / "api" / "v1" / "content-index.json").read_text(encoding="utf-8")
            module.prepare(site, root)
            module.publish(site, root)
            self.assertEqual(first_manifest, (site / "api" / "v1" / "content-index.json").read_text(encoding="utf-8"))
            developers = (site / "developers" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(developers.count("data-content-discovery-v219"), 3)

    def test_removes_stale_shards_when_page_count_decreases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = self.build_site(root)
            module.prepare(site, root)
            original_size = module.SHARD_SIZE
            try:
                module.SHARD_SIZE = 1
                module.publish(site, root)
                self.assertTrue((site / "api" / "v1" / "content-index-004.json").is_file())
                module.SHARD_SIZE = 400
                module.publish(site, root)
                self.assertFalse((site / "api" / "v1" / "content-index-004.json").exists())
            finally:
                module.SHARD_SIZE = original_size

    def test_rejects_duplicate_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = self.build_site(root)
            duplicate = site / "duplicate" / "index.html"
            duplicate.parent.mkdir()
            duplicate.write_text(
                page(
                    title="نسخة مكررة",
                    canonical=module.BASE_URL + "encyclopedia/autism/",
                    keywords="نسخة مكررة,اختبار,علم النفس,الصحة النفسية",
                    h1="نسخة مكررة",
                ),
                encoding="utf-8",
            )
            module.prepare(site, root)
            with self.assertRaisesRegex(module.ContentDiscoveryError, "duplicate canonical"):
                module.publish(site, root)

    def test_production_order_is_locked(self):
        source = (ROOT / "scripts" / "apply_homepage_v20.py").read_text(encoding="utf-8")
        public_api = source.index('run_publisher("publish_public_api_v215.py")')
        prepare = source.index('run_publisher("prepare_content_discovery_v219.py")')
        enhance = source.index('run_publisher("enhance_sitewide_seo_v216.py")')
        catalog = source.index('run_publisher("publish_content_catalog_v219.py")')
        verify = source.index('run_publisher("verify_sitewide_seo_v216.py")')
        self.assertLess(public_api, prepare)
        self.assertLess(prepare, enhance)
        self.assertLess(enhance, catalog)
        self.assertLess(catalog, verify)


if __name__ == "__main__":
    unittest.main()
