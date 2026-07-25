from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import audit_source_origin_depth_v234 as audit


def arabic_words(count: int, prefix: str = "كلمة") -> str:
    return " ".join(f"{prefix}{index}" for index in range(count))


def page(body: str, *, lang: str = "ar", robots: str = "index,follow", title: str = "عنوان الصفحة") -> str:
    return (
        f'<!doctype html><html lang="{lang}" dir="rtl"><head><title>{title}</title>'
        f'<meta name="robots" content="{robots}"></head><body><main><h1>{title}</h1>'
        f'{body}</main></body></html>'
    )


class SourceOriginDepthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.site = self.root / "site"
        self.repo = self.root / "repo"
        self.site.mkdir()
        (self.repo / "scripts").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, relative: str, source: str) -> None:
        target = self.site / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")

    def test_strips_nested_current_generation_blocks(self) -> None:
        body = (
            f'<p>{arabic_words(35, "أصل")}</p>'
            '<!-- content-depth-v222:start -->'
            f'<section><p>{arabic_words(80, "عام")}</p>'
            '<!-- advanced-content-depth-v233:start -->'
            f'<article><p>{arabic_words(700, "متقدم")}</p></article>'
            '<!-- advanced-content-depth-v233:end -->'
            '</section><!-- content-depth-v222:end -->'
        )
        self.write("assessment-lab/anxiety/index.html", page(body, title="متابعة القلق"))
        report = audit.audit(self.site)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["generated_dependency_pages"], 1)
        self.assertEqual(report["origin_below_minimum_count"], 1)
        item = report["dependencies"][0]
        self.assertEqual(item["minimum_words"], 750)
        self.assertLess(item["origin_words"], 80)
        self.assertGreater(item["generated_words"], 700)
        self.assertEqual(set(item["markers"]), {"content-depth-v222", "advanced-content-depth-v233"})

    def test_preserves_rich_origin_as_sufficient_dependency(self) -> None:
        body = (
            f'<p>{arabic_words(760, "أصل")}</p>'
            '<!-- term-content-depth-v224:start -->'
            f'<section><p>{arabic_words(100, "إضافة")}</p></section>'
            '<!-- term-content-depth-v224:end -->'
        )
        self.write("terms/example/index.html", page(body))
        report = audit.audit(self.site)
        self.assertEqual(report["origin_below_minimum_count"], 0)
        self.assertEqual(report["origin_sufficient_count"], 1)
        self.assertGreaterEqual(report["dependencies"][0]["origin_words"], 650)

    def test_provider_condition_uses_900_word_contract_and_finds_producer(self) -> None:
        (self.repo / "scripts/enrich_provider_condition_pages_v231.py").write_text(
            "provider-condition-depth-v231\nwrite_text\n", encoding="utf-8"
        )
        body = (
            f'<p>{arabic_words(100, "أصل")}</p>'
            '<!-- provider-condition-depth-v231:start -->'
            f'<section><p>{arabic_words(850, "إضافة")}</p></section>'
            '<!-- provider-condition-depth-v231:end -->'
        )
        self.write("provider-assessment-demo/conditions/adhd/index.html", page(body))
        report = audit.audit(self.site, self.repo)
        item = report["dependencies"][0]
        self.assertEqual(item["route_group"], "provider-conditions")
        self.assertEqual(item["minimum_words"], 900)
        self.assertIn("scripts/enrich_provider_condition_pages_v231.py", item["producer_candidates"])

    def test_skips_noindex_and_non_arabic_pages(self) -> None:
        block = '<!-- residual-public-content-v232:start --><p>إضافة</p><!-- residual-public-content-v232:end -->'
        self.write("about/index.html", page(block, robots="noindex,follow"))
        self.write("privacy/index.html", page(block, lang="en"))
        report = audit.audit(self.site)
        self.assertEqual(report["eligible_pages"], 0)
        self.assertEqual(report["skipped_noindex"], 1)
        self.assertEqual(report["skipped_non_arabic"], 1)

    def test_rejects_mismatched_or_unclosed_markers(self) -> None:
        body = (
            '<!-- content-depth-v222:start --><p>محتوى</p>'
            '<!-- advanced-content-depth-v233:end -->'
        )
        self.write("library/index.html", page(body))
        report = audit.audit(self.site)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["malformed_marker_count"], 1)

    def test_ignores_non_content_operational_markers(self) -> None:
        body = (
            f'<p>{arabic_words(50)}</p>'
            '<!-- homepage-links-v229:start --><nav>روابط</nav><!-- homepage-links-v229:end -->'
        )
        self.write("about/index.html", page(body))
        report = audit.audit(self.site)
        self.assertEqual(report["generated_dependency_pages"], 0)
        self.assertEqual(report["malformed_marker_count"], 0)

    def test_writes_json_and_markdown_reports(self) -> None:
        body = (
            f'<p>{arabic_words(30, "أصل")}</p>'
            '<!-- residual-public-content-v232:start -->'
            f'<section><p>{arabic_words(220, "إضافة")}</p></section>'
            '<!-- residual-public-content-v232:end -->'
        )
        self.write("methodology/index.html", page(body))
        report = audit.audit(self.site)
        json_path = self.root / "report.json"
        markdown_path = self.root / "report.md"
        audit.write_reports(report, json_path, markdown_path)
        loaded = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(loaded["version"], 234)
        self.assertIn("residual-public-content-v232", loaded["marker_counts"])
        self.assertIn("/methodology/", markdown_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
