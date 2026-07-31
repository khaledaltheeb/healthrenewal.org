from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_child_sector_deployment_v240.py"
spec = importlib.util.spec_from_file_location("child_live_v240", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class ChildSectorDeploymentV240Tests(unittest.TestCase):
    SHA = "a" * 40

    def fixture(self, root: Path) -> tuple[Path, Path]:
        site = root / "site"
        source = root / "child.json"
        articles = [{"slug": "child-grief", "title": "الحزن والفقد عند الطفل"}]
        articles.extend({"slug": f"guide-{i:02d}", "title": f"دليل الطفل رقم {i:02d}"} for i in range(1, 20))
        source.write_text(json.dumps({"articles": articles}, ensure_ascii=False), encoding="utf-8")
        (site / "api").mkdir(parents=True)
        (site / "deployment.json").write_text(
            json.dumps({"schema_version": 30, "commit": self.SHA}), encoding="utf-8"
        )
        (site / "api/child-sector-v239.json").write_text(
            json.dumps({
                "version": 239,
                "status": "passed",
                "source_articles": 20,
                "source_corrections": ["child-grief"],
                "hub_words": 2300,
                "minimum_article_words": 700,
                "banned_term_present": False,
                "diagnostic_claim_present": False,
            }, ensure_ascii=False),
            encoding="utf-8",
        )

        filler_hub = " ".join(f"مركز{i}" for i in range(2250))
        links = "".join(
            f'<a href="/sectors/child/{item["slug"]}/">{item["title"]}</a>'
            for item in articles
        )
        schemas = "CollectionPage BreadcrumbList ItemList FAQPage"
        hub = (
            f'<!doctype html><html lang="ar"><head><meta name="robots" content="index,follow">'
            f'<link rel="canonical" href="{module.BASE}/sectors/child/"></head><body>'
            f'<h1>قطاع الطفل</h1><p>{filler_hub}</p>{links}'
            f'<script type="application/ld+json">{{"schemas":"{schemas}"}}</script></body></html>'
        )
        (site / "sectors/child").mkdir(parents=True)
        (site / "sectors/child/index.html").write_text(hub, encoding="utf-8")

        for item in articles:
            folder = site / "sectors/child" / item["slug"]
            folder.mkdir(parents=True)
            filler = " ".join(f"كلمة{i}" for i in range(700))
            correction = module.CORRECTED_GRIEF_TEXT if item["slug"] == "child-grief" else ""
            page = (
                f'<!doctype html><html lang="ar"><head><meta name="robots" content="index,follow">'
                f'<link rel="canonical" href="{module.BASE}/sectors/child/{item["slug"]}/"></head><body>'
                f'<h1>{item["title"]}</h1><p>{correction} {filler}</p>'
                f'<script type="application/ld+json">{{"@type":"Article"}}</script></body></html>'
            )
            (folder / "index.html").write_text(page, encoding="utf-8")

        (site / "robots.txt").write_text(
            "Allow: /sectors/child/\n"
            "Sitemap: https://healthrenewal.org/sitemap.xml\n",
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
            self.assertGreaterEqual(result["minimum_live_article_words"], 650)
            self.assertTrue(result["all_indexable"])
            self.assertTrue(result["grief_correction_verified"])
            self.assertTrue((site / "api/child-sector-deployment-v240.json").is_file())

    def test_wrong_deployment_sha_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            with self.assertRaisesRegex(AssertionError, "Deployment SHA"):
                module.verify(site, source, "b" * 40, "live")

    def test_missing_article_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            (site / "sectors/child/guide-07/index.html").unlink()
            with self.assertRaisesRegex(AssertionError, "Missing deployed page"):
                module.verify(site, source, self.SHA, "live")

    def test_noindex_article_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            page = site / "sectors/child/guide-03/index.html"
            text = page.read_text(encoding="utf-8").replace("index,follow", "noindex,follow")
            page.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "must not be noindex"):
                module.verify(site, source, self.SHA, "live")

    def test_low_depth_article_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            page = site / "sectors/child/guide-05/index.html"
            page.write_text(
                f'<!doctype html><html><head><meta name="robots" content="index,follow">'
                f'<link rel="canonical" href="{module.BASE}/sectors/child/guide-05/"></head>'
                '<body><h1>قصير</h1><p>نص قصير</p>'
                '<script type="application/ld+json">{"@type":"Article"}</script></body></html>',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(AssertionError, "below its minimum depth"):
                module.verify(site, source, self.SHA, "live")

    def test_corrupted_grief_wording_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            page = site / "sectors/child/child-grief/index.html"
            text = page.read_text(encoding="utf-8").replace(
                module.CORRECTED_GRIEF_TEXT,
                module.CORRUPTED_GRIEF_TEXT,
            )
            page.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "Corrected child-grief wording"):
                module.verify(site, source, self.SHA, "live")


if __name__ == "__main__":
    unittest.main()
