from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "term_content_v224", ROOT / "scripts" / "enrich_term_pages_v224.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class TermContentDepthV224Tests(unittest.TestCase):
    def make_site(self, *, rich: bool = False, noindex: bool = False):
        temp = tempfile.TemporaryDirectory()
        site = Path(temp.name)
        api = site / "api"
        api.mkdir()
        categories = list(MODULE.CATEGORY_PROFILE)
        terms = []
        for index in range(200):
            slug = f"term-{index:03d}"
            term = {
                "ar": f"المفهوم {index}",
                "en": f"Concept {index}",
                "category": categories[index % len(categories)],
                "description": f"تعريف علمي مختصر للمفهوم رقم {index}.",
                "slug": slug,
            }
            terms.append(term)
            page = site / "terms" / slug / "index.html"
            page.parent.mkdir(parents=True)
            robots = '<meta name="robots" content="noindex">' if noindex and index == 0 else ""
            filler = " كلمة" * 700 if rich else ""
            page.write_text(
                f'<!doctype html><html lang="ar"><head>{robots}<title>اختبار</title></head>'
                f'<body><main><h1>المفهوم {index}</h1><p>{filler}</p></main></body></html>',
                encoding="utf-8",
            )
        (api / "terms.json").write_text(
            json.dumps({"terms": terms}, ensure_ascii=False), encoding="utf-8"
        )
        return temp, site

    def test_enriches_all_short_pages_with_unique_evidence_content(self):
        temp, site = self.make_site()
        self.addCleanup(temp.cleanup)
        report = MODULE.run(site)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["enriched_pages"], 200)
        self.assertEqual(report["remaining_below_minimum"], 0)
        self.assertEqual(report["duplicate_generated_blocks"], 0)
        page = (site / "terms" / "term-000" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Concept 0", page)
        self.assertIn("مصطلحات مرتبطة", page)
        self.assertIn("مصادر مؤسسية ومنهجية", page)
        self.assertIn("لا يثبت تشخيصًا", page)

    def test_second_run_is_idempotent(self):
        temp, site = self.make_site()
        self.addCleanup(temp.cleanup)
        MODULE.run(site)
        report = MODULE.run(site)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["already_enriched_pages"], 200)
        page = (site / "terms" / "term-000" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(page.count("data-term-depth-v224="), 1)

    def test_rich_pages_are_not_rewritten(self):
        temp, site = self.make_site(rich=True)
        self.addCleanup(temp.cleanup)
        page = site / "terms" / "term-000" / "index.html"
        before = page.read_text(encoding="utf-8")
        report = MODULE.run(site)
        self.assertEqual(report["sufficient_pages"], 200)
        self.assertEqual(page.read_text(encoding="utf-8"), before)

    def test_noindex_page_is_skipped(self):
        temp, site = self.make_site(noindex=True)
        self.addCleanup(temp.cleanup)
        report = MODULE.run(site)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["pages"][0]["status"], "skipped_noindex")

    def test_missing_term_page_fails_release(self):
        temp, site = self.make_site()
        self.addCleanup(temp.cleanup)
        (site / "terms" / "term-010" / "index.html").unlink()
        report = MODULE.run(site)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["missing_or_failed"], 1)


if __name__ == "__main__":
    unittest.main()
