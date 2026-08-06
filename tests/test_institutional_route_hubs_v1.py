from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ROBOTS_META = '<meta name="robots" content="index,follow,'
SITEMAP_SCRIPT = ROOT / "scripts" / "publish_complete_sitemap_v360.py"
PRODUCTION_PIPELINE = ROOT / "scripts" / "apply_homepage_v20.py"
CORE_WRAPPER = ROOT / "scripts" / "complete_core_sections_v15.py"
CORE_PUBLISHER = ROOT / "scripts" / "complete_core_sections_v15_legacy_v1.py"
DAILY_TOOLS_PUBLISHER = ROOT / "scripts" / "publish_daily_tools_v24.py"
FULL_SITE_WORKFLOW = ROOT / ".github" / "workflows" / "validate-full-site-v16.yml"
GENERATED_ROUTE_PUBLISHERS = {
    "/mental-health/": CORE_PUBLISHER,
    "/daily-tools/": DAILY_TOOLS_PUBLISHER,
}
SITEMAP_SPEC = importlib.util.spec_from_file_location(
    "publish_complete_sitemap_v360", SITEMAP_SCRIPT
)
assert SITEMAP_SPEC and SITEMAP_SPEC.loader
sitemap_publisher = importlib.util.module_from_spec(SITEMAP_SPEC)
SITEMAP_SPEC.loader.exec_module(sitemap_publisher)


class InstitutionalRouteHubsV1Tests(unittest.TestCase):
    def read_page(self, route: str) -> str:
        page = ROOT / route / "index.html"
        self.assertTrue(page.is_file(), f"Missing institutional route: /{route}/")
        return page.read_text(encoding="utf-8")

    def visible_word_count(self, page: str) -> int:
        source = re.sub(
            r"<(?:script|style)\b[^>]*>.*?</(?:script|style)>",
            " ",
            page,
            flags=re.IGNORECASE | re.DOTALL,
        )
        source = re.sub(r"<[^>]+>", " ", source)
        return len(re.findall(r"[\u0600-\u06FF]{2,}|[A-Za-z]{2,}", source))

    def internal_target(self, href: str) -> Path:
        parsed = urlsplit(href)
        relative = parsed.path.lstrip("/")
        if not relative:
            return ROOT / "index.html"
        target = ROOT / relative
        return target / "index.html" if parsed.path.endswith("/") else target

    def test_required_route_targets_exist(self) -> None:
        for route in (
            "about",
            "safety",
            "services",
            "sectors/family",
            "privacy-policy",
            "rights",
            "schools",
        ):
            with self.subTest(route=route):
                self.assertTrue((ROOT / route / "index.html").is_file())

    def test_generated_navigation_routes_have_production_publishers(self) -> None:
        for route, publisher in GENERATED_ROUTE_PUBLISHERS.items():
            with self.subTest(route=route):
                self.assertTrue(publisher.is_file(), f"Missing publisher for {route}")

        pipeline = PRODUCTION_PIPELINE.read_text(encoding="utf-8")
        workflow = FULL_SITE_WORKFLOW.read_text(encoding="utf-8")
        wrapper = CORE_WRAPPER.read_text(encoding="utf-8")
        daily_tools = DAILY_TOOLS_PUBLISHER.read_text(encoding="utf-8")

        self.assertIn('run_publisher("publish_daily_tools_v24.py")', pipeline)
        self.assertIn("python scripts/complete_core_sections_v15.py _site", workflow)
        self.assertIn('with_name("complete_core_sections_v15_legacy_v1.py")', wrapper)
        self.assertIn("legacy.main()", wrapper)
        self.assertIn('"daily-tools"', daily_tools)

    def test_about_page_is_substantive_and_transparent(self) -> None:
        page = self.read_page("about")
        self.assertGreaterEqual(self.visible_word_count(page), 850)
        self.assertIn(
            '<link rel="canonical" href="https://healthrenewal.org/about/">',
            page,
        )
        self.assertIn(ROBOTS_META, page)
        for phrase in (
            "لماذا أُنشئت المنصة",
            "كيف يُبنى المحتوى",
            "درجات المادة وحدودها",
            "الاستقلال والتمويل والادعاءات",
            "كيف نصحح الخطأ",
            "ما الذي لا تدعيه المنصة",
            "المراجعة القانونية والمؤسسية الخارجية",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, page)
        self.assertGreaterEqual(page.count("<h2"), 10)
        self.assertGreaterEqual(page.count('class="card"'), 13)

    def test_safety_hub_is_substantive_and_governed(self) -> None:
        page = self.read_page("safety")
        self.assertGreater(len(page), 9000)
        self.assertIn(
            '<link rel="canonical" href="https://healthrenewal.org/safety/">',
            page,
        )
        self.assertIn(ROBOTS_META, page)
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
        self.assertIn(ROBOTS_META, page)
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

    def test_privacy_policy_matches_operational_data_surfaces(self) -> None:
        page = self.read_page("privacy-policy")
        self.assertGreaterEqual(self.visible_word_count(page), 600)
        self.assertIn(
            '<link rel="canonical" href="https://healthrenewal.org/privacy-policy/">',
            page,
        )
        self.assertIn(ROBOTS_META, page)
        for phrase in (
            "بيانات تقنية وتشغيلية",
            "بيانات تحليل الاستخدام",
            "localStorage",
            "النماذج والحسابات",
            "البيانات الحساسة والأطفال",
            "لا ضمان للسرية العلاجية",
            "المراجعة القانونية",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, page)
        self.assertGreaterEqual(page.count("<h2"), 9)
        self.assertIn('href="/contact/"', page)
        self.assertIn('href="/rights/"', page)
        self.assertIn('href="/about/"', page)

    def test_rights_charter_is_substantive_and_nonlegal(self) -> None:
        page = self.read_page("rights")
        self.assertGreaterEqual(self.visible_word_count(page), 550)
        self.assertIn(
            '<link rel="canonical" href="https://healthrenewal.org/rights/">',
            page,
        )
        self.assertIn(ROBOTS_META, page)
        for phrase in (
            "الكرامة وعدم الوصم",
            "معلومة صحيحة ومفهومة",
            "التواصل المتاح",
            "المشاركة في القرار",
            "عدم التشخيص الآلي",
            "آلية الإبلاغ والمعالجة",
            "ليست استشارة قانونية",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, page)
        self.assertGreaterEqual(page.count('class="card"'), 10)
        self.assertIn('href="/privacy-policy/"', page)
        self.assertIn('href="/safety/"', page)

    def test_schools_hub_is_substantive_and_actionable(self) -> None:
        page = self.read_page("schools")
        self.assertGreaterEqual(self.visible_word_count(page), 650)
        self.assertIn(
            '<link rel="canonical" href="https://healthrenewal.org/schools/">',
            page,
        )
        self.assertIn(ROBOTS_META, page)
        for phrase in (
            "دورة العمل المدرسي من ثماني مراحل",
            "صوت الطالب",
            "تحديد الحاجز",
            "الدعم الفردي",
            "الأدوار دون تداخل أو فراغ",
            "الحد الأدنى لخطة دعم جيدة",
            "إشارات تستدعي تصحيحًا مؤسسيًا",
            "مؤشرات متابعة شهرية",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, page)
        self.assertEqual(page.count("<tbody>"), 1)
        self.assertGreaterEqual(page.count('class="card"'), 18)
        self.assertIn(
            'href="/learning-paths/evidence-guided/inclusive-education-foundations/"',
            page,
        )
        self.assertIn('href="/rights/"', page)

    def test_new_hubs_have_valid_internal_destinations(self) -> None:
        for route in ("about", "privacy-policy", "rights", "schools"):
            page = self.read_page(route)
            hrefs = re.findall(r'href=["\']([^"\']+)["\']', page)
            missing = []
            for href in hrefs:
                parsed = urlsplit(href)
                if (
                    parsed.scheme
                    or parsed.netloc
                    or href.startswith("#")
                    or not parsed.path.startswith("/")
                ):
                    continue
                if href in GENERATED_ROUTE_PUBLISHERS:
                    continue
                if not self.internal_target(href).is_file():
                    missing.append(href)
            with self.subTest(route=route):
                self.assertEqual(missing, [], f"Missing internal targets in /{route}/: {missing}")

    def test_hubs_have_no_placeholder_or_prohibited_language(self) -> None:
        combined = "".join(
            self.read_page(route)
            for route in (
                "about",
                "safety",
                "services",
                "privacy-policy",
                "rights",
                "schools",
            )
        )
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

    def test_generated_evidence_guides_do_not_restore_legacy_family_route(self) -> None:
        guides = sorted((ROOT / "evidence-guides").glob("*/index.html"))
        self.assertGreaterEqual(len(guides), 30)
        legacy_pattern = re.compile(r'href=["\']/family/["\']')
        canonical_link_count = 0

        for guide in guides:
            page = guide.read_text(encoding="utf-8")
            with self.subTest(guide=guide.relative_to(ROOT).as_posix()):
                self.assertIsNone(legacy_pattern.search(page))
            canonical_link_count += page.count('href="/sectors/family/"')

        self.assertGreaterEqual(canonical_link_count, 10)

    def test_institutional_routes_are_discovered_by_production_sitemap_publisher(self) -> None:
        urls, discovery = sitemap_publisher.discover(ROOT)
        url_set = set(urls)
        required = {
            "https://healthrenewal.org/about/",
            "https://healthrenewal.org/privacy-policy/",
            "https://healthrenewal.org/rights/",
            "https://healthrenewal.org/safety/",
            "https://healthrenewal.org/schools/",
            "https://healthrenewal.org/services/",
            "https://healthrenewal.org/sectors/family/",
        }
        self.assertTrue(required.issubset(url_set), sorted(required - url_set))
        self.assertEqual(len(urls), len(url_set))
        self.assertGreaterEqual(discovery["html_files_discovered"], len(urls))


if __name__ == "__main__":
    unittest.main()
