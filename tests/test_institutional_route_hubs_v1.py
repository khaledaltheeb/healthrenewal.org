from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InstitutionalRouteHubsV1Tests(unittest.TestCase):
    def read_page(self, route: str) -> str:
        page = ROOT / route / "index.html"
        self.assertTrue(page.is_file(), f"Missing institutional route: /{route}/")
        return page.read_text(encoding="utf-8")

    def test_required_route_targets_exist(self) -> None:
        for route in ("safety", "services", "sectors/family"):
            with self.subTest(route=route):
                self.assertTrue((ROOT / route / "index.html").is_file())

    def test_safety_hub_is_substantive_and_governed(self) -> None:
        page = self.read_page("safety")
        self.assertGreater(len(page), 9000)
        self.assertIn(
            '<link rel="canonical" href="https://healthrenewal.org/safety/">',
            page,
        )
        self.assertIn("عند وجود خطر مباشر أو وشيك", page)
        self.assertIn("لا تعتمد على هذه الصفحة أو على اختبار إلكتروني", page)
        self.assertIn("العناصر الستة لخطة سلامة شخصية", page)
        self.assertIn("لا تنشر المنصة رقمًا عالميًا للطوارئ", page)
        self.assertIn("المراجعة الخارجية", page)
        self.assertGreaterEqual(page.count("<h2"), 7)
        self.assertIn('href="/services/"', page)
        self.assertIn('href="/sectors/family/"', page)

    def test_services_hub_is_substantive_and_noncommercial(self) -> None:
        page = self.read_page("services")
        self.assertGreater(len(page), 10000)
        self.assertIn(
            '<link rel="canonical" href="https://healthrenewal.org/services/">',
            page,
        )
        self.assertIn("منصة روافد منصة معرفية وتثقيفية", page)
        self.assertIn("عند البحث عن خدمة خارج المنصة", page)
        self.assertIn("معايير تحميك من الادعاءات المضللة", page)
        self.assertIn("الانتقال بين خدمات الطفولة والرشد", page)
        self.assertGreaterEqual(page.count('class="card"'), 13)
        for route in (
            "/start-here/",
            "/encyclopedia/",
            "/mental-health/",
            "/special-needs/",
            "/sectors/family/",
            "/care-guides/",
            "/daily-tools/",
            "/assessment-lab/",
            "/learning-paths/",
            "/specialists-partners/",
            "/safety/",
        ):
            with self.subTest(route=route):
                self.assertIn(f'href="{route}"', page)

    def test_hubs_have_no_placeholder_or_prohibited_language(self) -> None:
        combined = self.read_page("safety") + self.read_page("services")
        for phrase in (
            "TODO",
            "Lorem ipsum",
            "قيد التطوير",
            "سيتم إضافة المحتوى",
            "معاقين",
            "نضمن الشفاء",
        ):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, combined)
        self.assertIsNone(re.search(r'href=["\']/(family)/["\']', combined))


if __name__ == "__main__":
    unittest.main()