from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_PUBLISHER = ROOT / "scripts" / "publish_outside_the_box_v254.py"
PUBLISHER = ROOT / "scripts" / "publish_outside_the_box_ten_plans_v302.py"
DATA = ROOT / "content" / "v254" / "outside-the-box-conditions-ar.json"
FRAMEWORK = ROOT / "content" / "v302" / "outside-the-box-ten-plan-framework-ar.json"
BASE = "https://healthrenewal.org/"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TenPlanSourceContractV302(unittest.TestCase):
    def test_framework_declares_exact_complete_contract(self) -> None:
        data = json.loads(DATA.read_text(encoding="utf-8"))
        framework = json.loads(FRAMEWORK.read_text(encoding="utf-8"))
        self.assertEqual(len(data["conditions"]), 100)
        self.assertEqual(framework["version"], 302)
        self.assertEqual(framework["scope"]["plans_per_condition"], 10)
        self.assertEqual(framework["scope"]["total_plan_instances"], 1000)
        self.assertEqual(len(framework["plan_families"]), 10)
        self.assertEqual(
            [item["order"] for item in framework["plan_families"]],
            list(range(1, 11)),
        )
        self.assertEqual(len({item["id"] for item in framework["plan_families"]}), 10)
        self.assertGreaterEqual(len(framework["required_fields"]), 13)
        self.assertIn("المراجعة التخصصية الخارجية", framework["scope"]["status"])
        self.assertNotIn("اعتماد عالمي مكتمل", framework["scope"]["status"])

    def test_every_condition_can_generate_ten_evidence_linked_plans(self) -> None:
        module = load_module(PUBLISHER, "outside_ten_plans_source_v302")
        data, framework = module.load_sources()
        for condition in data["conditions"]:
            plans = module.build_plans(data, framework, condition)
            self.assertEqual(len(plans), 10, condition["slug"])
            self.assertEqual([plan["order"] for plan in plans], list(range(1, 11)))
            self.assertEqual(len({plan["id"] for plan in plans}), 10)
            for plan in plans:
                self.assertGreaterEqual(len(plan["steps"]), 5)
                self.assertGreaterEqual(len(plan["source_keys"]), 2)
                self.assertTrue(set(plan["source_keys"]).issubset(data["sources"]))
                for required in (
                    "goal",
                    "when_to_use",
                    "do_not_use",
                    "prerequisites",
                    "baseline",
                    "dose",
                    "outcomes",
                    "fidelity",
                    "adaptations",
                    "team",
                    "stop_rule",
                    "evidence_relation",
                    "review_timing",
                    "review_status",
                ):
                    self.assertTrue(plan[required], (condition["slug"], plan["id"], required))


class TenPlanPublisherV302(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="outside-ten-plans-v302-"))
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
        self.base = load_module(BASE_PUBLISHER, "outside_base_for_ten_plans_v302")
        self.publisher = load_module(PUBLISHER, "outside_ten_plans_v302")

    def publish(self) -> dict:
        self.base.publish(self.site)
        return self.publisher.publish(self.site)

    def test_publishes_one_thousand_complete_plan_instances(self) -> None:
        report = self.publish()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["condition_count"], 100)
        self.assertEqual(report["plans_per_condition"], 10)
        self.assertEqual(report["total_plan_instances"], 1000)
        self.assertFalse(report["external_clinical_review_completed"])
        self.assertFalse(report["diagnostic_automation"])
        self.assertFalse(report["proprietary_test_items_published"])

        for item in report["conditions"]:
            page = self.site / "outside-the-box" / item["slug"] / "index.html"
            text = page.read_text(encoding="utf-8")
            self.assertEqual(text.count('data-ten-plan="'), 10, item["slug"])
            self.assertEqual(text.count("الخطة 1 من 10"), 1)
            self.assertEqual(text.count("الخطة 10 من 10"), 1)
            self.assertIn('href="#ten-plans"', text)
            self.assertIn("عشر خطط كاملة قابلة للتخصيص والقياس", text)
            for marker in (
                "متى تستخدم؟",
                "متى لا تستخدم؟",
                "المتطلبات السابقة",
                "خط الأساس",
                "خطوات التنفيذ",
                "الجرعة أو الوتيرة",
                "مؤشرات النتيجة",
                "جودة التنفيذ",
                "التكييفات والوصول",
                "الفريق والمسؤوليات",
                "قاعدة التوقف أو التصعيد",
                "صلة الخطة بالدليل",
                "موعد إعادة القرار",
            ):
                self.assertGreaterEqual(text.count(marker), 10, (item["slug"], marker))

        api = json.loads(
            (self.site / "api/outside-the-box-ten-plans-v302.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(len(api["conditions"]), 100)
        self.assertEqual(sum(item["plan_count"] for item in api["conditions"]), 1000)
        self.assertTrue(all(len(item["plans"]) == 10 for item in api["conditions"]))

    def test_hub_methodology_sitemap_and_base_api_are_integrated(self) -> None:
        report = self.publish()
        hub = (self.site / "outside-the-box/index.html").read_text(encoding="utf-8")
        self.assertEqual(hub.count("outside-the-box-ten-plans-v302-hub:start"), 1)
        self.assertIn("1000", hub)
        self.assertIn("ten-plan-methodology/", hub)

        methodology = (
            self.site / "outside-the-box/ten-plan-methodology/index.html"
        ).read_text(encoding="utf-8")
        self.assertIn("100 حالة × 10 خطط = 1000", methodology)
        self.assertEqual(methodology.count("class=\"otb10-condition-index\""), 1)
        for condition in report["conditions"]:
            self.assertIn(f'../{condition["slug"]}/#ten-plans', methodology)

        sitemap_urls = [
            (node.text or "").strip()
            for node in ET.parse(self.site / "sitemap-outside-the-box.xml")
            .getroot()
            .findall("{*}url/{*}loc")
        ]
        self.assertIn(BASE + "outside-the-box/ten-plan-methodology/", sitemap_urls)
        self.assertEqual(len(sitemap_urls), len(set(sitemap_urls)))

        base_api = json.loads(
            (self.site / "api/outside-the-box-v254.json").read_text(encoding="utf-8")
        )
        extension = base_api["ten_plan_extension"]
        self.assertEqual(extension["version"], 302)
        self.assertEqual(extension["plans_per_condition"], 10)
        self.assertEqual(extension["total_plan_instances"], 1000)

    def test_extension_is_idempotent(self) -> None:
        self.publish()
        tracked = [
            self.site / "outside-the-box/index.html",
            self.site / "outside-the-box/speech-sound-disorder/index.html",
            self.site / "outside-the-box/ten-plan-methodology/index.html",
            self.site / "api/outside-the-box-ten-plans-v302.json",
            self.site / "sitemap-outside-the-box.xml",
        ]
        before = [digest(path) for path in tracked]
        self.publisher.publish(self.site)
        after = [digest(path) for path in tracked]
        self.assertEqual(before, after)

    def test_language_is_responsible_and_review_state_is_honest(self) -> None:
        self.publish()
        pages = list((self.site / "outside-the-box").rglob("index.html"))
        text = "\n".join(path.read_text(encoding="utf-8") for path in pages)
        for banned in (
            "معاقين",
            "شفاء مضمون",
            "نتيجة مضمونة",
            "اعتماد عالمي مكتمل",
            "كل المصابين متفوقون",
            "الخطة تصلح للجميع",
        ):
            self.assertNotIn(banned, text)
        self.assertIn("المراجعة التخصصية الخارجية", text)
        self.assertIn("لا تفترض موهبة حسابية أو فنية أو رياضية بسبب التشخيص", text)


if __name__ == "__main__":
    unittest.main()
