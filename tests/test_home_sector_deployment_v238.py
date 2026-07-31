from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_home_sector_deployment_v238.py"
spec = importlib.util.spec_from_file_location("home_live_v238", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class HomeSectorDeploymentV238Tests(unittest.TestCase):
    SHA = "a" * 40

    @staticmethod
    def shell(title: str, canonical: str, body: str) -> str:
        return (
            '<!doctype html><html lang="ar" dir="rtl"><head>'
            f'<title>{title}</title>'
            '<meta name="description" content="وصف مؤسسي واضح للصفحة ومحتواها التطبيقي">'
            '<meta name="robots" content="index,follow">'
            f'<meta property="og:title" content="{title}">'
            '<meta name="twitter:card" content="summary_large_image">'
            f'<link rel="canonical" href="{canonical}">'
            '</head><body>'
            '<header class="site-header-v10">التنقل</header>'
            f'<main>{body}</main>'
            '<footer class="site-footer-v10">الحقوق</footer>'
            '<script>navigator.serviceWorker.register("/sw.js")</script>'
            '</body></html>'
        )

    def fixture(self, root: Path) -> tuple[Path, Path]:
        site = root / "site"
        source = root / "home.json"
        articles = [{"slug": f"guide-{i:02d}", "title": f"دليل الأسرة رقم {i:02d}"} for i in range(20)]
        source.write_text(json.dumps({"articles": articles}, ensure_ascii=False), encoding="utf-8")
        (site / "api").mkdir(parents=True)
        (site / "deployment.json").write_text(
            json.dumps({"schema_version": 29, "commit": self.SHA}), encoding="utf-8"
        )

        filler_hub = " ".join(f"مركز{i}" for i in range(3000))
        links = "".join(f'<a href="/sectors/home/{item["slug"]}/">{item["title"]}</a>' for item in articles)
        schemas = "CollectionPage BreadcrumbList ItemList FAQPage"
        hub = self.shell(
            "قطاع الأسرة",
            f"{module.BASE}/sectors/home/",
            f'<h1>قطاع الأسرة</h1><p>{filler_hub}</p>{links}<script type="application/ld+json">{{"schemas":"{schemas}"}}</script>',
        )
        (site / "sectors/home").mkdir(parents=True)
        hub_path = site / "sectors/home/index.html"
        hub_path.write_text(hub, encoding="utf-8")

        article_paths: list[Path] = []
        for item in articles:
            folder = site / "sectors/home" / item["slug"]
            folder.mkdir(parents=True)
            filler = " ".join(f"كلمة{i}" for i in range(850))
            page = self.shell(
                item["title"],
                f'{module.BASE}/sectors/home/{item["slug"]}/',
                f'<h1>{item["title"]}</h1><p>{filler}</p><script type="application/ld+json">{{"@type":"Article"}}</script>',
            )
            page_path = folder / "index.html"
            page_path.write_text(page, encoding="utf-8")
            article_paths.append(page_path)

        hub_words = module.visible_words(hub_path.read_text(encoding="utf-8"))
        minimum_article_words = min(module.visible_words(path.read_text(encoding="utf-8")) for path in article_paths)
        (site / "api/home-sector-v234.json").write_text(
            json.dumps({
                "version": 234,
                "status": "passed",
                "source_articles": 20,
                "hub_words": hub_words,
                "minimum_article_words": minimum_article_words,
                "word_count_method": module.WORD_COUNT_METHOD,
                "depth_contract_version": 244,
                "banned_term_present": False,
                "diagnostic_claim_present": False,
            }), encoding="utf-8"
        )
        (site / "robots.txt").write_text(
            "Allow: /sectors/home/\nSitemap: https://healthrenewal.org/sitemap.xml\n",
            encoding="utf-8",
        )
        return site, source

    def test_valid_live_fixture_passes_with_production_v10_shell(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            result = module.verify(site, source, self.SHA, "live")
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["version"], 244)
            self.assertEqual(result["source_articles"], 20)
            self.assertEqual(result["article_pages_verified"], 20)
            self.assertGreaterEqual(result["hub_words"], module.MINIMUM_HUB_WORDS)
            self.assertGreaterEqual(result["minimum_live_article_words"], module.MINIMUM_ARTICLE_WORDS)
            self.assertEqual(result["word_count_method"], module.WORD_COUNT_METHOD)
            self.assertTrue(result["all_indexable"])
            self.assertTrue(result["all_have_shell"])
            self.assertTrue(result["all_have_pwa"])
            self.assertTrue((site / "api/home-sector-deployment-v238.json").is_file())

    def test_retained_global_id_shell_variant_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            for page in (site / "sectors/home").rglob("index.html"):
                text = page.read_text(encoding="utf-8")
                text = text.replace('class="site-header-v10"', 'id="global-header"')
                text = text.replace('class="site-footer-v10"', 'id="global-footer"')
                page.write_text(text, encoding="utf-8")
            result = module.verify(site, source, self.SHA, "live")
            self.assertTrue(result["all_have_shell"])

    def test_missing_institutional_header_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            page = site / "sectors/home/index.html"
            text = page.read_text(encoding="utf-8").replace('<header class="site-header-v10">التنقل</header>', "")
            page.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "missing institutional header"):
                module.verify(site, source, self.SHA, "live")

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
            text = page.read_text(encoding="utf-8").replace('content="index,follow"', 'content="noindex"')
            page.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "must not be noindex"):
                module.verify(site, source, self.SHA, "live")

    def test_low_depth_article_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            page = site / "sectors/home/guide-05/index.html"
            page.write_text(
                self.shell(
                    "دليل قصير",
                    f"{module.BASE}/sectors/home/guide-05/",
                    '<h1>دليل قصير</h1><p>نص قصير</p><script type="application/ld+json">{"@type":"Article"}</script>',
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(AssertionError, "below its minimum depth"):
                module.verify(site, source, self.SHA, "live")

    def test_report_and_live_counts_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, source = self.fixture(Path(tmp))
            report_path = site / "api/home-sector-v234.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["hub_words"] += 1
            report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "report and live semantic word counts differ"):
                module.verify(site, source, self.SHA, "live")


if __name__ == "__main__":
    unittest.main()
