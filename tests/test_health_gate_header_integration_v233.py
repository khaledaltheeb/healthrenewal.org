from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import enforce_health_publication_gate_v192 as entry


LEGACY_PAGE = """<!doctype html><html lang="ar" dir="rtl"><head><title>اختبار</title></head><body>
<header aria-label="الترويسة الرئيسية"><div class="wrap"><a class="brand" href="./">المنصة</a><nav class="nav"><a href="encyclopedia/">الموسوعة</a></nav></div></header>
<main id="main"><h1>اختبار</h1></main></body></html>
"""


class HealthGateHeaderIntegrationV233Tests(unittest.TestCase):
    def write_sector_image_fixture(self, site: Path) -> Path:
        illustrations = site / "assets" / "illustrations"
        illustrations.mkdir(parents=True, exist_ok=True)
        (illustrations / "child.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800"><rect width="1200" height="800"/></svg>',
            encoding="utf-8",
        )
        page = site / "sectors" / "child" / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head><title>الطفل</title></head><body>'
            '<main><h1>الصحة النفسية للطفل</h1>'
            '<img src="https://healthrenewal.org/assets/illustrations/child.svg" alt="رسم توضيحي للطفل">'
            '</main></body></html>',
            encoding="utf-8",
        )
        return page

    def write_semantic_fixture(self, site: Path) -> tuple[Path, Path]:
        category = site / "categories" / "index.html"
        category.parent.mkdir(parents=True, exist_ok=True)
        category.write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head><title>التصنيفات</title></head><body>'
            '<main><h1>التصنيفات</h1><h3>الفئة الأولى</h3><h3>الفئة الثانية</h3></main>'
            '</body></html>',
            encoding="utf-8",
        )
        error = site / "404.html"
        error.write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head><title>الصفحة غير موجودة</title></head><body>'
            '<main><h1>الصفحة غير موجودة</h1><h3>روابط مفيدة</h3></main></body></html>',
            encoding="utf-8",
        )
        return category, error

    def test_header_dimensions_and_semantics_run_after_successful_health_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site = Path(temporary_directory)
            homepage = site / "index.html"
            homepage.write_text(LEGACY_PAGE, encoding="utf-8")
            sector_page = self.write_sector_image_fixture(site)
            category_page, error_page = self.write_semantic_fixture(site)
            previous_site = entry.SITE
            entry.SITE = site
            try:
                with patch.object(
                    entry._base,
                    "enforce",
                    return_value={"version": 192, "status": "passed"},
                ) as health_gate:
                    report = entry.enforce()
            finally:
                entry.SITE = previous_site

            health_gate.assert_called_once_with()
            page = homepage.read_text(encoding="utf-8")
            sector = sector_page.read_text(encoding="utf-8")
            category = category_page.read_text(encoding="utf-8")
            error = error_page.read_text(encoding="utf-8")
            self.assertEqual(report["institutional_header_version"], 233)
            self.assertEqual(report["institutional_header_status"], "passed")
            self.assertEqual(report["institutional_header_section_links"], 12)
            self.assertEqual(report["institutional_header_language_links"], 3)
            self.assertTrue(report["institutional_header_care_guide_link_compatible"])
            self.assertTrue(report["institutional_header_care_guide_link_normalized"])
            self.assertEqual(report["institutional_header_care_guide_link"], "care-guides/")
            self.assertEqual(report["sector_image_dimensions_version"], 236)
            self.assertEqual(report["sector_image_dimensions_status"], "passed")
            self.assertEqual(report["sector_image_dimensions_target_images"], 1)
            self.assertEqual(report["sector_image_dimensions_images_updated"], 1)
            self.assertEqual(report["sector_image_dimensions_remaining"], 0)
            self.assertEqual(report["semantic_structure_version"], 237)
            self.assertEqual(report["semantic_structure_status"], "passed")
            self.assertEqual(report["semantic_structure_heading_pages_updated"], 2)
            self.assertEqual(report["semantic_structure_heading_tags_updated"], 3)
            self.assertEqual(report["semantic_structure_remaining_heading_jumps"], 0)
            self.assertTrue(report["semantic_structure_error_page_jsonld_present"])
            self.assertIn('width="1200"', sector)
            self.assertIn('height="800"', sector)
            self.assertEqual(category.count("<h2"), 2)
            self.assertNotIn("<h3", category)
            self.assertIn("data-error-page-jsonld-v237", error)
            self.assertIn('"@type":"WebPage"', error)
            self.assertEqual(page.count("data-institutional-header-v233"), 1)
            self.assertEqual(page.count("<details"), 2)
            self.assertEqual(page.count(entry.CARE_GUIDE_RELATIVE_LINK), 1)
            self.assertEqual(page.count(entry.CARE_GUIDE_ABSOLUTE_LINK), 0)
            self.assertFalse(entry.ensure_care_guide_link_compatibility(homepage))
            self.assertNotIn('<nav class="nav"', page)

            second_dimensions = entry._finalize_image_dimensions(site)
            self.assertEqual(second_dimensions["status"], "passed")
            self.assertEqual(second_dimensions["images_updated"], 0)
            self.assertEqual(second_dimensions["attributes_added"], 0)
            self.assertEqual(second_dimensions["remaining_missing_dimensions"], 0)
            self.assertEqual(sector_page.read_text(encoding="utf-8"), sector)

            second_semantics = entry._finalize_semantic_structure(site)
            self.assertEqual(second_semantics["status"], "passed")
            self.assertEqual(second_semantics["heading_pages_updated"], 0)
            self.assertEqual(second_semantics["heading_tags_updated"], 0)
            self.assertFalse(second_semantics["error_page_jsonld_added"])
            self.assertEqual(second_semantics["error_page_marker_count"], 1)
            self.assertEqual(category_page.read_text(encoding="utf-8"), category)
            self.assertEqual(error_page.read_text(encoding="utf-8"), error)

    def test_finishers_are_skipped_without_homepage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site = Path(temporary_directory)
            previous_site = entry.SITE
            entry.SITE = site
            try:
                with patch.object(
                    entry._base,
                    "enforce",
                    return_value={"version": 192, "status": "passed"},
                ), patch.object(entry, "_publish_header") as publisher, patch.object(
                    entry, "_finalize_image_dimensions"
                ) as dimensions, patch.object(entry, "_finalize_semantic_structure") as semantics:
                    report = entry.enforce()
            finally:
                entry.SITE = previous_site

            publisher.assert_not_called()
            dimensions.assert_not_called()
            semantics.assert_not_called()
            self.assertEqual(report, {"version": 192, "status": "passed"})

    def test_duplicate_or_missing_care_guide_link_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            homepage = Path(temporary_directory) / "index.html"
            homepage.write_text("<html><body><main></main></body></html>", encoding="utf-8")
            with self.assertRaises(SystemExit):
                entry.ensure_care_guide_link_compatibility(homepage)

    def test_original_health_gate_contract_is_reexported(self) -> None:
        self.assertIs(entry.load_guides, entry._base.load_guides)
        self.assertIs(entry.remove_blocked_references, entry._base.remove_blocked_references)
        self.assertEqual(entry.BLOCKED_REVIEW_STATUSES, {"needs-specialist-review"})


if __name__ == "__main__":
    unittest.main()
