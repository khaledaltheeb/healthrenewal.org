from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_outside_the_box_v254.py"
DATA = ROOT / "content" / "v254" / "outside-the-box-conditions-ar.json"
INSTRUMENTS = ROOT / "content" / "v254" / "outside-the-box-instruments-ar.json"
BASE = "https://healthrenewal.org/"


def load_publisher():
    spec = importlib.util.spec_from_file_location("outside_the_box_v254", PUBLISHER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class OutsideTheBoxSourceContractV254(unittest.TestCase):
    def test_data_has_one_hundred_ranked_and_referenced_conditions(self) -> None:
        data = json.loads(DATA.read_text(encoding="utf-8"))
        instruments = json.loads(INSTRUMENTS.read_text(encoding="utf-8"))
        self.assertEqual(data["version"], 254)
        self.assertEqual(instruments["version"], 254)
        self.assertEqual(
            data["review_status"],
            "مراجعة منهجية داخلية مكتملة؛ المراجعة السريرية الخارجية لكل مسار مطلوبة قبل ادعاء الاعتماد",
        )
        self.assertIn("تخطيطي", data["scope_note"])
        self.assertNotIn("دقيق عالمي", data["scope_note"])
        conditions = data["conditions"]
        self.assertEqual(len(conditions), 100)
        self.assertEqual([item["rank"] for item in conditions], list(range(1, 101)))
        self.assertEqual(len({item["slug"] for item in conditions}), 100)
        self.assertEqual(set(data["clusters"]), set(instruments["clusters"]))
        self.assertGreaterEqual(len(data["sources"]), 25)
        self.assertGreaterEqual(len(data["protocols"]), 20)
        for item in conditions:
            self.assertRegex(item["slug"], r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
            self.assertEqual(len(item["focus"]), 3)
            self.assertEqual(len(item["assessment_extras"]), 3)
            self.assertEqual(len(item["protocol_keys"]), 3)
            self.assertGreaterEqual(len(item["source_keys"]), 2)
            self.assertTrue(item["reference_url"].startswith("https://"))
            self.assertIn(item["cluster"], data["clusters"])
            self.assertTrue(
                set(item["protocol_keys"]).issubset(data["protocols"]),
                item["slug"],
            )
            self.assertTrue(
                set(item["source_keys"]).issubset(data["sources"]),
                item["slug"],
            )

    def test_instrument_registry_preserves_rights_and_interpretation_boundaries(self) -> None:
        instruments = json.loads(INSTRUMENTS.read_text(encoding="utf-8"))
        notice = instruments["rights_notice"]
        for marker in ("أسماء", "بنود", "مفاتيح تصحيح", "النسخة الأصلية", "مؤهل"):
            self.assertIn(marker, notice)
        for cluster, tools in instruments["clusters"].items():
            self.assertGreaterEqual(len(tools), 4, cluster)
            for tool in tools:
                self.assertEqual(
                    set(tool),
                    {"name", "owner", "use", "access", "caution"},
                )
                self.assertTrue(all(str(value).strip() for value in tool.values()))


class OutsideTheBoxPublisherV254(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="outside-the-box-v254-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))
        (self.site / "special-needs").mkdir(parents=True)
        (self.site / "provider-assessment-demo").mkdir(parents=True)
        (self.site / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head></head><body>'
            '<header><nav class="nav"><a href="special-needs/">المركز</a></nav></header>'
            '<main><h1>الرئيسية</h1></main></body></html>',
            encoding="utf-8",
        )
        (self.site / "special-needs/index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head></head><body>'
            '<main><h1>مركز ذوي الاحتياجات الخاصة</h1></main></body></html>',
            encoding="utf-8",
        )
        (self.site / "provider-assessment-demo/index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head></head><body>'
            '<main><h1>منصة مقدم الخدمة</h1></main></body></html>',
            encoding="utf-8",
        )
        (self.site / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<sitemap><loc>https://example.test/sitemap-core.xml</loc></sitemap>'
            "</sitemapindex>",
            encoding="utf-8",
        )
        (self.site / "robots.txt").write_text(
            "User-agent: *\nAllow: /\n", encoding="utf-8"
        )
        self.publisher = load_publisher()

    def publish(self) -> dict:
        return self.publisher.publish(self.site)

    def test_generates_complete_static_library_and_machine_contract(self) -> None:
        report = self.publish()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["condition_count"], 100)
        self.assertEqual(report["generated_page_count"], 103)
        self.assertEqual(report["sitemap_url_count"], 103)
        self.assertFalse(report["external_clinical_review_completed"])
        self.assertFalse(report["diagnostic_automation"])
        self.assertFalse(report["proprietary_test_items_published"])
        self.assertFalse(report["original_tracker_validated_scale"])
        self.assertTrue(report["local_only_monitoring"])

        pages = sorted((self.site / "outside-the-box").rglob("index.html"))
        self.assertEqual(len(pages), 103)
        hub = (self.site / "outside-the-box/index.html").read_text(encoding="utf-8")
        for item in json.loads(DATA.read_text(encoding="utf-8"))["conditions"]:
            path = self.site / "outside-the-box" / item["slug"] / "index.html"
            self.assertTrue(path.is_file(), item["slug"])
            self.assertEqual(hub.count(f'href="{item["slug"]}/"'), 2)
            text = path.read_text(encoding="utf-8")
            self.assertEqual(len(re.findall(r"<h1\b", text)), 1)
            self.assertGreaterEqual(len(re.findall(r"<h2\b", text)), 7)
            self.assertGreater(len(text), 20000)
            for marker in (
                "تحديد الحالة",
                "اختبار الحالة",
                "تقييم الحالة",
                "الأفكار المناسبة",
                "ما المتوقع",
                "الجدول الزمني",
                "إعادة التقييم",
                "قاعدة التوقف",
                "الأسبوع 24",
                "مفاتيح تصحيح",
                "المراجعة الخارجية",
                "application/ld+json",
            ):
                self.assertIn(marker, text, (item["slug"], marker))

        api = json.loads(
            (self.site / "api/outside-the-box-v254.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(api["conditions"]), 100)
        self.assertEqual(api["conditions"][0]["rank"], 1)
        self.assertEqual(api["conditions"][-1]["rank"], 100)
        sitemap_urls = [
            node.text
            for node in ET.parse(self.site / "sitemap-outside-the-box.xml")
            .getroot()
            .findall("{*}url/{*}loc")
            if node.text
        ]
        self.assertEqual(len(sitemap_urls), 103)
        self.assertEqual(len(sitemap_urls), len(set(sitemap_urls)))
        self.assertEqual(sitemap_urls[0], BASE + "outside-the-box/")
        self.assertEqual(
            sitemap_urls[-1],
            BASE + "outside-the-box/rare-neurodevelopmental-undiagnosed/",
        )

    def test_integrates_three_gateways_idempotently(self) -> None:
        self.publish()
        tracked = [
            self.site / "index.html",
            self.site / "special-needs/index.html",
            self.site / "provider-assessment-demo/index.html",
            self.site / "sitemap.xml",
            self.site / "sitemap-outside-the-box.xml",
            self.site / "robots.txt",
        ]
        before = [digest(path) for path in tracked]
        self.publish()
        after = [digest(path) for path in tracked]
        self.assertEqual(before, after)
        for path in tracked[:3]:
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count("outside-the-box-v254:start"), 1)
            self.assertEqual(text.count("outside-the-box-v254:end"), 1)
            self.assertIn("outside-the-box/", text)
        home = tracked[0].read_text(encoding="utf-8")
        self.assertEqual(home.count("data-outside-the-box-v254-nav"), 1)
        robots = tracked[-1].read_text(encoding="utf-8")
        self.assertEqual(
            robots.count(
                "Sitemap: "
                + BASE
                + "sitemap-outside-the-box.xml"
            ),
            1,
        )
        root_locations = [
            node.text
            for node in ET.parse(self.site / "sitemap.xml")
            .getroot()
            .findall("{*}sitemap/{*}loc")
            if node.text
        ]
        self.assertEqual(
            root_locations.count(BASE + "sitemap-outside-the-box.xml"),
            1,
        )

    def test_monitoring_record_is_local_only_and_non_diagnostic(self) -> None:
        self.publish()
        matrix = (
            self.site / "outside-the-box/monitoring-matrix/index.html"
        ).read_text(encoding="utf-8")
        runtime = (
            self.site / "assets/js/outside-the-box-v254.js"
        ).read_text(encoding="utf-8")
        for marker in (
            "غير تشخيصي",
            "لا توجد مزامنة أو إرسال إلى خادم",
            "عدد الفرص",
            "نجاح مستقل",
            "جودة التنفيذ",
            "العبء/الضيق",
            "الأسبوع 0",
            "الأسبوع 24",
            "تصدير CSV",
            "تصدير JSON",
        ):
            self.assertIn(marker, matrix)
        for network_api in ("fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket"):
            self.assertNotIn(network_api, runtime)
        self.assertIn("localStorage", runtime)
        self.assertIn("لا يمكن استعادتها", runtime)
        self.assertIn("^[=+\\-@]", runtime)

    def test_final_special_needs_hub_rebuild_preserves_section_gateway(self) -> None:
        self.publish()
        hub_publisher_path = ROOT / "scripts/publish_special_needs_hub_v201.py"
        spec = importlib.util.spec_from_file_location(
            "special_needs_hub_v201_for_outside_box", hub_publisher_path
        )
        hub_publisher = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(hub_publisher)
        hub_publisher.publish(self.site)
        hub = (self.site / "special-needs/index.html").read_text(encoding="utf-8")
        self.assertEqual(hub.count("outside-the-box-v254:start"), 1)
        self.assertEqual(hub.count("outside-the-box-v254:end"), 1)
        self.assertIn(
            'href="/outside-the-box/"',
            hub,
        )
        self.assertIn("تصفح 100 حالة", hub)
        block = hub.split("outside-the-box-v254:start", 1)[1].split(
            "outside-the-box-v254:end", 1
        )[0]
        self.assertIn("outside-box-resources-v254", block)
        self.assertNotIn('<div class="resources">', block)
        self.assertNotIn("special-needs-guides-v", block)

    def test_pages_use_responsible_language_and_honest_review_state(self) -> None:
        self.publish()
        pages = list((self.site / "outside-the-box").rglob("index.html"))
        text = "\n".join(path.read_text(encoding="utf-8") for path in pages)
        for banned in (
            "معاقين",
            "شفاء مضمون",
            "نتيجة مضمونة",
            "اعتماد عالمي مكتمل",
            "مراجعة خارجية مكتملة",
        ):
            self.assertNotIn(banned, text)
        self.assertIn("المراجعة السريرية الخارجية مطلوبة", text)
        self.assertIn("ليس مقياسًا مقننًا", text)


if __name__ == "__main__":
    unittest.main()
