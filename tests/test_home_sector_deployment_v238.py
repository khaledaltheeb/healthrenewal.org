from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_home_sector_deployment_v238.py"
spec = importlib.util.spec_from_file_location("home_live_v238", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class HomeSectorDeploymentV238Tests(unittest.TestCase):
    SHA = "a" * 40

    def fixture(self, root: Path) -> tuple[Path, Path]:
        site = root / "site"
        source = root / "home.json"
        articles = [{"slug": f"guide-{i:02d}", "title": f"دليل الأسرة رقم {i:02d}"} for i in range(20)]
        source.write_text(json.dumps({"articles": articles}, ensure_ascii=False), encoding="utf-8")
        (site / "api").mkdir(parents=True)
        (site / "deployment.json").write_text(
            json.dumps({"schema_version": 29, "commit": self.SHA}), encoding="utf-8"
        )
        (site / "api/home-sector-v234.json").write_text(
            json.dumps({
                "version": 234,
                "status": "passed",
                "source_articles": 20,
                "hub_words": 1900,
                "minimum_article_words": 500,
                "banned_term_present": False,
                "diagnostic_claim_present": False,
            }), encoding="utf-8"
        )
        filler_hub = " ".join(f"مركز{i}" for i in range(1850))
        links = "".join(f'<a href="/pterminology-site/sectors/home/{item["slug"]}/">{item["title"]}</a>' for item in articles)
        schemas = "CollectionPage BreadcrumbList ItemList FAQPage"
        hub = f'<!doctype html><html lang="ar"><head><link rel="canonical" href="{module.BASE}/sectors/home/"></head><body><h1>قطاع الأسرة</h1><p>{filler_hub}</p>{links}<script type="application/ld+json">{{"schemas":"{schemas}"}}</script></body></html>'
        (site / "sectors/home").mkdir(parents=True)
        (site / "sectors/home/index.html").write_text(hub, encoding="utf-8")
        for item in articles:
            folder = site / "sectors/home" / item["slug"]
            folder.mkdir(parents=True)
            filler = " ".join(f"كلمة{i}" for i in range(500))
            page = f'<!doctype html><html lang="ar"><head><link rel="canonical" href="{module.BASE}/sectors/home/{item["slug"]}/"></head><body><h1>{item["title"]}</h1><p>{filler}</p><script type="application/ld+json">{{"@type":"Article"}}</script></body></html>'
            (folder / "index.html").write_text(page, encoding="utf-8")
        (site / "robots.txt").write_text(
            "Allow: /pterminology-site/sectors/home/\nSitemap: https://khaledaltheeb.github.io/pterminology-site/sitemap.xml\n",
            encoding="utf-8",
        )
        return site, source

    def test_valid_live_fixture_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            result = module.verify(site, source, self.SHA, "live")
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["source_articles"], 20)
            self.assertEqual(result["article_pages_verified"], 20)
            self.assertGreaterEqual(result["minimum_live_article_words"], 450)
            self.assertTrue(result["all_indexable"])
            self.assertTrue((site / "api/home-sector-deployment-v238.json").is_file())

    def test_wrong_deployment_sha_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            with self.assertRaisesRegex(AssertionError, "Deployment SHA"):
                module.verify(site, source, "b" * 40, "live")

    def test_missing_article_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            (site / "sectors/home/guide-07/index.html").unlink()
            with self.assertRaisesRegex(AssertionError, "Missing deployed page"):
                module.verify(site, source, self.SHA, "live")

    def test_noindex_article_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            page = site / "sectors/home/guide-03/index.html"
            text = page.read_text(encoding="utf-8").replace("</head>", '<meta name="robots" content="noindex"></head>')
            page.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "must not be noindex"):
                module.verify(site, source, self.SHA, "live")

    def test_low_depth_article_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            page = site / "sectors/home/guide-05/index.html"
            page.write_text(
                f'<!doctype html><html><head><link rel="canonical" href="{module.BASE}/sectors/home/guide-05/"></head><body><h1>قصير</h1><p>نص قصير</p><script type="application/ld+json">{{"@type":"Article"}}</script></body></html>',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(AssertionError, "below its minimum depth"):
                module.verify(site, source, self.SHA, "live")


if __name__ == "__main__":
    unittest.main()
