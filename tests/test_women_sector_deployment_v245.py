from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_women_sector_deployment_v245.py"
spec = importlib.util.spec_from_file_location("women_live_v245", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class WomenSectorDeploymentV245Tests(unittest.TestCase):
    SHA = "a" * 40

    def fixture(self, root: Path) -> tuple[Path, Path]:
        site = root / "site"
        source = root / "women.json"
        required = ["perinatal-mental-health", "pmdd", "perimenopause", "women-adhd", "women-autism", "domestic-violence"]
        slugs = required + [f"guide-{index:02d}" for index in range(1, 15)]
        articles = [{"slug": slug, "title": f"دليل صحة المرأة {index:02d}"} for index, slug in enumerate(slugs, 1)]
        source.write_text(json.dumps({"articles": articles}, ensure_ascii=False), encoding="utf-8")
        (site / "api").mkdir(parents=True)
        (site / "deployment.json").write_text(json.dumps({
            "schema_version": 30,
            "commit": self.SHA,
            "women_sector_version": 244,
            "women_sector_articles": 20,
            "women_sector_hub_words": 2300,
            "women_sector_minimum_article_words": 900,
        }), encoding="utf-8")
        (site / "api/women-sector-v244.json").write_text(json.dumps({
            "version": 244,
            "status": "passed",
            "source_articles": 20,
            "hub_h1": 1,
            "hub_words": 2300,
            "minimum_article_words": 900,
            "faq_items": 6,
            "institutional_sources": 12,
            "banned_term_present": False,
            "diagnostic_claim_present": False,
        }, ensure_ascii=False), encoding="utf-8")

        links = "".join(f'<a href="/sectors/women/{item["slug"]}/">{item["title"]}</a>' for item in articles)
        filler = " ".join(f"مركز{i}" for i in range(2250))
        hub = (
            f'<!doctype html><html lang="ar"><head><meta name="description" content="وصف"><meta name="keywords" content="كلمات">'
            f'<meta name="googlebot" content="index,follow"><meta name="robots" content="index,follow">'
            f'<link rel="canonical" href="{module.BASE}/sectors/women/"></head><body><main><h1>صحة المرأة</h1>'
            f'<p>ذهان ما بعد الولادة حالة طارئة السلامة قبل المواجهة ذات الاحتياجات الخاصة خطة 30 يومًا {filler}</p>{links}'
            '<script type="application/ld+json">{"schemas":"CollectionPage BreadcrumbList ItemList FAQPage"}</script></main></body></html>'
        )
        (site / "sectors/women").mkdir(parents=True)
        (site / "sectors/women/index.html").write_text(hub, encoding="utf-8")

        for item in articles:
            folder = site / "sectors/women" / item["slug"]
            folder.mkdir(parents=True)
            words = " ".join(f"كلمة{i}" for i in range(760))
            page = (
                f'<!doctype html><html lang="ar"><head><meta name="description" content="وصف"><meta name="keywords" content="كلمات">'
                f'<meta name="googlebot" content="index,follow"><meta name="robots" content="index,follow">'
                f'<link rel="canonical" href="{module.BASE}/sectors/women/{item["slug"]}/"></head><body><main>'
                f'<h1>{item["title"]}</h1><p>متابعة لمدة أسبوعين متى تصبح الاستجابة عاجلة؟ ذات الاحتياجات الخاصة {words}</p>'
                '<script type="application/ld+json">{"@type":"Article"}</script></main></body></html>'
            )
            (folder / "index.html").write_text(page, encoding="utf-8")

        (site / "robots.txt").write_text(
            "Allow: /sectors/women/\nSitemap: https://healthrenewal.org/sitemap.xml\n",
            encoding="utf-8",
        )
        return site, source

    def test_valid_fixture_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            result = module.verify(site, source, self.SHA, "live")
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["article_pages_verified"], 20)
            self.assertGreaterEqual(result["minimum_live_article_words"], 700)
            self.assertTrue(result["all_indexable"])
            self.assertTrue(result["institutional_markers_verified"])
            self.assertTrue((site / "api/women-sector-deployment-v245.json").is_file())

    def test_wrong_sha_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            with self.assertRaisesRegex(AssertionError, "Deployment SHA"):
                module.verify(site, source, "b" * 40, "live")

    def test_missing_guide_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            (site / "sectors/women/guide-04/index.html").unlink()
            with self.assertRaisesRegex(AssertionError, "Missing deployed page"):
                module.verify(site, source, self.SHA, "live")

    def test_noindex_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            page = site / "sectors/women/pmdd/index.html"
            text = page.read_text(encoding="utf-8").replace(
                '<meta name="robots" content="index,follow">',
                '<meta name="robots" content="noindex,follow">',
                1,
            )
            page.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "must not be noindex"):
                module.verify(site, source, self.SHA, "live")

    def test_missing_safety_marker_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            page = site / "sectors/women/index.html"
            page.write_text(page.read_text(encoding="utf-8").replace("ذهان ما بعد الولادة حالة طارئة", "تنبيه عام"), encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "institutional marker"):
                module.verify(site, source, self.SHA, "live")

    def test_low_depth_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            page = site / "sectors/women/guide-06/index.html"
            text = page.read_text(encoding="utf-8")
            text = re.sub(r"كلمة\d+(?:\s+كلمة\d+)*", "قصير", text)
            page.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "below its minimum depth"):
                module.verify(site, source, self.SHA, "live")


if __name__ == "__main__":
    unittest.main()
