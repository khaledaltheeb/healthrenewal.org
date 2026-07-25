from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_home_sector_deployment_v238.py"
spec = importlib.util.spec_from_file_location("home_live_v244", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class HomeSectorDeploymentV244Tests(unittest.TestCase):
    SHA = "a" * 40

    def fixture(self, root: Path) -> tuple[Path, Path]:
        site = root / "site"
        source = root / "home.json"
        articles = [{"slug": f"guide-{i:02d}", "title": f"دليل الأسرة رقم {i:02d}"} for i in range(20)]
        source.write_text(json.dumps({"articles": articles}, ensure_ascii=False), encoding="utf-8")
        (site / "api").mkdir(parents=True)
        (site / "deployment.json").write_text(json.dumps({"schema_version": 29, "commit": self.SHA}), encoding="utf-8")
        (site / "api/home-sector-v234.json").write_text(
            json.dumps({
                "version": 234,
                "status": "passed",
                "source_articles": 20,
                "hub_words": 3000,
                "minimum_article_words": 850,
                "banned_term_present": False,
                "diagnostic_claim_present": False,
            }),
            encoding="utf-8",
        )
        filler_hub = " ".join(f"مركز{i}" for i in range(3000))
        links = "".join(f'<a href="/pterminology-site/sectors/home/{item["slug"]}/">{item["title"]}</a>' for item in articles)
        schemas = "CollectionPage BreadcrumbList ItemList FAQPage"
        chrome = '<header id="global-header">الهيدر</header>{body}<footer id="global-footer">الفوتر</footer><script>navigator.serviceWorker.register("/sw.js")</script>'
        hub_body = f'<main><h1>قطاع الأسرة</h1><p>{filler_hub}</p>{links}<script type="application/ld+json">{{"schemas":"{schemas}"}}</script></main>'
        hub = f'<!doctype html><html lang="ar"><head><link rel="canonical" href="{module.BASE}/sectors/home/"></head><body>{chrome.format(body=hub_body)}</body></html>'
        (site / "sectors/home").mkdir(parents=True)
        (site / "sectors/home/index.html").write_text(hub, encoding="utf-8")
        for item in articles:
            folder = site / "sectors/home" / item["slug"]
            folder.mkdir(parents=True)
            filler = " ".join(f"كلمة{i}" for i in range(850))
            article_body = f'<article><h1>{item["title"]}</h1><p>{filler}</p><script type="application/ld+json">{{"@type":"Article"}}</script></article>'
            page = f'<!doctype html><html lang="ar"><head><link rel="canonical" href="{module.BASE}/sectors/home/{item["slug"]}/"></head><body>{chrome.format(body=article_body)}</body></html>'
            (folder / "index.html").write_text(page, encoding="utf-8")
        for name in ("sitemap-provider-assessment.xml", "sitemap-special-needs.xml"):
            (site / name).write_text("<urlset></urlset>", encoding="utf-8")
        (site / "robots.txt").write_text(
            "Allow: /pterminology-site/sectors/home/\n"
            f"Sitemap: {module.BASE}/sitemap.xml\n"
            f"Sitemap: {module.BASE}/sitemap-provider-assessment.xml\n"
            f"Sitemap: {module.BASE}/sitemap-special-needs.xml\n",
            encoding="utf-8",
        )
        return site, source

    def test_valid_live_fixture_passes_full_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            result = module.verify(site, source, self.SHA, "live")
            self.assertEqual(result["status"], "passed")
            self.assertGreaterEqual(result["hub_words"], 2919)
            self.assertGreaterEqual(result["minimum_live_article_words"], 819)
            self.assertTrue(result["header_footer_pwa_verified"])
            self.assertTrue(result["optional_sitemaps_verified"])

    def test_wrong_deployment_sha_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            with self.assertRaisesRegex(AssertionError, "Deployment SHA"):
                module.verify(site, source, "b" * 40, "live")

    def test_depth_below_explicit_floor_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            page = site / "sectors/home/guide-05/index.html"
            text = page.read_text(encoding="utf-8")
            text = text.replace(" ".join(f"كلمة{i}" for i in range(850)), " ".join(f"كلمة{i}" for i in range(818)))
            page.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "below its minimum depth"):
                module.verify(site, source, self.SHA, "live")

    def test_duplicate_or_missing_sitemap_registration_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            robots = site / "robots.txt"
            robots.write_text(robots.read_text(encoding="utf-8") + f"Sitemap: {module.BASE}/sitemap-special-needs.xml\n", encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "registered exactly once"):
                module.verify(site, source, self.SHA, "live")

        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            (site / "sitemap-special-needs.xml").unlink()
            with self.assertRaisesRegex(AssertionError, "Missing sitemap must not be registered"):
                module.verify(site, source, self.SHA, "live")

    def test_header_footer_pwa_and_banned_term_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            page = site / "sectors/home/guide-03/index.html"
            page.write_text(page.read_text(encoding="utf-8").replace('id="global-footer"', 'id="missing-footer"'), encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "header or footer"):
                module.verify(site, source, self.SHA, "live")

        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            page = site / "sectors/home/guide-04/index.html"
            page.write_text(page.read_text(encoding="utf-8").replace("كلمة0", "معاقين", 1), encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "Banned terminology"):
                module.verify(site, source, self.SHA, "live")


if __name__ == "__main__":
    unittest.main()
