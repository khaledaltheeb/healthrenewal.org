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
PUBLISHER = ROOT / "scripts" / "publish_capabilities_v280.py"
BUILDER = ROOT / "scripts" / "build_capabilities_evidence_v280.py"
DATA = ROOT / "content" / "v280" / "capabilities-100-ar.json"
PROFILE_DIR = ROOT / "content" / "v280" / "profiles"
EVIDENCE_DIR = ROOT / "content" / "v280" / "evidence"
CSS = ROOT / "assets" / "css" / "capabilities-v280.css"
JS = ROOT / "assets" / "js" / "capabilities-v280.js"
INTEGRATION = ROOT / "scripts" / "apply_homepage_v20.py"
BASE = "https://healthrenewal.org/"


def load_publisher():
    spec = importlib.util.spec_from_file_location("capabilities_v280", PUBLISHER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_capabilities_evidence_v280", BUILDER
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CapabilitiesSourceContractV280(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads(DATA.read_text(encoding="utf-8"))

    def test_registry_has_exactly_one_hundred_distinct_ranked_conditions(self) -> None:
        conditions = self.data["conditions"]
        self.assertEqual(self.data["version"], 280)
        self.assertEqual(self.data["language"], "ar")
        self.assertEqual(len(conditions), 100)
        self.assertEqual([item["rank"] for item in conditions], list(range(1, 101)))
        self.assertEqual(len({item["slug"] for item in conditions}), 100)
        self.assertTrue(all(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", item["slug"]) for item in conditions))
        self.assertEqual(
            conditions[84]["slug"],
            "inflammatory-bowel-disease",
        )
        self.assertEqual(conditions[98]["slug"], "schizophrenia-functional-support")
        self.assertEqual(conditions[99]["slug"], "bipolar-disorder-functional-support")
        self.assertNotIn(
            "schizophrenia-bipolar-functional-support",
            {item["slug"] for item in conditions},
        )
        self.assertEqual(
            set(item["category"] for item in conditions),
            set(self.data["categories"]),
        )
        self.assertTrue(
            set(item["evidence_route"] for item in conditions).issubset(
                self.data["evidence_routes"]
            )
        )

    def test_first_wave_has_five_complete_guides_and_testable_hypotheses(self) -> None:
        guides = self.data["guides"]
        self.assertEqual(
            [item["slug"] for item in guides],
            ["autism", "adhd", "dyslexia", "down-syndrome", "cerebral-palsy"],
        )
        flagged = [
            item["slug"]
            for item in self.data["conditions"]
            if item["first_wave_guide"]
        ]
        self.assertEqual(flagged, [item["slug"] for item in guides])
        source_ids = {item["id"] for item in self.data["sources"]}
        for guide in guides:
            self.assertEqual(len(guide["evidence_summary"]), 3)
            self.assertGreaterEqual(len(guide["do_not_assume"]), 5)
            self.assertGreaterEqual(len(guide["health_first"]), 3)
            self.assertEqual(len(guide["hypotheses"]), 4)
            self.assertGreaterEqual(len(guide["adaptations"]), 5)
            self.assertGreaterEqual(len(guide["twelve_week_plan"]), 5)
            self.assertTrue(set(guide["source_ids"]).issubset(source_ids))
            for hypothesis in guide["hypotheses"]:
                self.assertEqual(
                    set(hypothesis),
                    {
                        "name",
                        "claim",
                        "microtrial",
                        "support",
                        "measure",
                        "stop_rule",
                    },
                )
                self.assertTrue(all(str(value).strip() for value in hypothesis.values()))

    def test_one_hundred_condition_specific_profiles_are_complete(self) -> None:
        profiles = []
        for path in sorted(PROFILE_DIR.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["version"], 280)
            self.assertEqual(payload["language"], "ar")
            self.assertIn(payload["category"], self.data["categories"])
            profiles.extend(
                (payload["category"], item) for item in payload["profiles"]
            )
        self.assertEqual(len(profiles), 100)
        self.assertEqual(len({item["slug"] for _, item in profiles}), 100)
        expected = {item["slug"]: item["category"] for item in self.data["conditions"]}
        self.assertEqual({item["slug"] for _, item in profiles}, set(expected))
        required = {
            "slug",
            "position",
            "ability_focus",
            "access_priority",
            "safety_priority",
            "task_trial",
            "functional_goal",
        }
        for category, profile in profiles:
            self.assertEqual(set(profile), required)
            self.assertEqual(category, expected[profile["slug"]])
            for key in required - {"slug"}:
                self.assertGreaterEqual(
                    len(profile[key]),
                    60,
                    (profile["slug"], key),
                )

    def test_every_condition_has_a_direct_authority_reference(self) -> None:
        publisher = load_publisher()
        references = publisher.load_direct_reference_map(self.data)
        self.assertEqual(len(references), 100)
        self.assertEqual(
            set(references),
            {condition["slug"] for condition in self.data["conditions"]},
        )
        for slug, reference in references.items():
            self.assertEqual(set(reference), {"publisher", "title", "url"}, slug)
            self.assertTrue(reference["publisher"].strip(), slug)
            self.assertTrue(reference["title"].strip(), slug)
            self.assertTrue(reference["url"].startswith("https://"), slug)

    def test_scientific_boundaries_are_explicit_not_inspirational_claims(self) -> None:
        text = DATA.read_text(encoding="utf-8")
        self.assertIn("ليس لكل مرض فائدة", text)
        self.assertIn("مسؤوليتنا ليست تجميل المرض", text)
        self.assertIn("فرضية قابلة للاختبار", text)
        self.assertIn("لا تثبت", text)
        self.assertIn("لا توجد موهبة ناتجة عن الشلل الدماغي", text)
        self.assertIn("لم تجد المراجعة التجميعية فرقًا عامًا دالًا في الإبداع", text)
        self.assertIn("الاستقرار والصحة أولًا", text)
        self.assertIn("الألم أو الهوس أو الذهان أو النوبات", text)
        for banned in (
            "كل مرض هبة",
            "ميزة اضطراب ما بعد الصدمة",
            "تحمل الألم موهبة",
            "المراجعة الخارجية مكتملة",
            "اعتماد عالمي",
            "معاقين",
        ):
            self.assertNotIn(banned, text)

    def test_sources_use_complete_claim_level_contract(self) -> None:
        sources = self.data["sources"]
        self.assertGreaterEqual(len(sources), 20)
        self.assertEqual(len({item["id"] for item in sources}), len(sources))
        required = {
            "id",
            "publisher",
            "title",
            "url",
            "year",
            "source_type",
            "verified_at",
            "claims_supported",
            "status",
        }
        for source in sources:
            self.assertEqual(set(source), required)
            self.assertRegex(source["id"], r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
            self.assertTrue(source["url"].startswith("https://"))
            self.assertIsInstance(source["year"], int)
            self.assertRegex(source["verified_at"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertTrue(source["claims_supported"])
            self.assertEqual(source["status"], "current")

    def test_selected_evidence_covers_all_one_hundred_conditions(self) -> None:
        payloads = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(EVIDENCE_DIR.glob("*.json"))
        ]
        self.assertTrue(payloads)
        base_source_ids = {item["id"] for item in self.data["sources"]}
        selected_sources = [
            source for payload in payloads for source in payload["sources"]
        ]
        packets = [
            packet
            for payload in payloads
            for packet in payload["evidence_packets"]
        ]
        claims = [claim for packet in packets for claim in packet["claims"]]

        self.assertEqual(len(payloads), 6)
        self.assertEqual(len(selected_sources), 112)
        self.assertEqual(len(packets), 100)
        self.assertEqual(len(claims), 300)
        self.assertEqual(
            {packet["slug"] for packet in packets},
            {item["slug"] for item in self.data["conditions"]},
        )

        required_source_fields = {
            "id",
            "publisher",
            "title",
            "url",
            "year",
            "source_type",
            "verified_at",
            "claims_supported",
            "status",
        }
        selected_source_ids = {item["id"] for item in selected_sources}
        self.assertEqual(len(selected_source_ids), 112)
        self.assertFalse(base_source_ids.intersection(selected_source_ids))
        for source in selected_sources:
            self.assertEqual(set(source), required_source_fields)
            self.assertTrue(source["url"].startswith("https://"))
            self.assertEqual(source["verified_at"], "2026-07-26")
            self.assertEqual(source["status"], "current")
            self.assertTrue(source["claims_supported"])

        all_source_ids = base_source_ids | selected_source_ids
        claim_ids = {claim["id"] for claim in claims}
        cited_source_ids = {
            source_id for claim in claims for source_id in claim["source_ids"]
        }
        self.assertEqual(len(claim_ids), 300)
        self.assertTrue(selected_source_ids.issubset(cited_source_ids))
        for packet in packets:
            self.assertEqual(packet["search_updated"], "2026-07-27")
            self.assertEqual(
                packet["review_state"],
                "curated-not-externally-reviewed",
            )
            self.assertEqual(
                [claim["type"] for claim in packet["claims"]],
                [
                    "profile-boundary",
                    "access-and-intervention",
                    "safety-and-differential",
                ],
            )
            for claim in packet["claims"]:
                self.assertEqual(
                    set(claim),
                    {
                        "id",
                        "type",
                        "statement",
                        "what_it_supports",
                        "what_it_does_not_support",
                        "evidence_character",
                        "source_ids",
                    },
                )
                for field in (
                    "statement",
                    "what_it_supports",
                    "what_it_does_not_support",
                ):
                    self.assertGreaterEqual(len(claim[field]), 70)
                self.assertTrue(set(claim["source_ids"]).issubset(all_source_ids))

        for payload in payloads:
            self.assertFalse(payload["external_review_completed"])
            method = payload["selection_method"]
            self.assertEqual(
                set(method),
                {
                    "scope",
                    "selection_order",
                    "exclusions",
                    "certainty_policy",
                    "live_search_boundary",
                    "review_boundary",
                },
            )
            exclusions = " ".join(method["exclusions"])
            for marker in ("الترويجية", "قصص النجاح", "البحث الحي", "بروتوكولات"):
                self.assertIn(marker, exclusions)
            self.assertIn("لا يعيّن المشروع درجة GRADE", method["certainty_policy"])
            self.assertIn("لم تكتمل مراجعة خارجية", method["review_boundary"])

    def test_evidence_builder_reproduces_all_five_generated_categories(self) -> None:
        builder = load_builder()
        for category in builder.SOURCES:
            profiles = json.loads(
                (PROFILE_DIR / f"{category}.json").read_text(encoding="utf-8")
            )["profiles"]
            generated = builder.build_category(self.data, category, profiles)
            checked_in = json.loads(
                (EVIDENCE_DIR / f"{category}-ar.json").read_text(encoding="utf-8")
            )
            self.assertEqual(generated, checked_in, category)

    def test_protocol_measures_benefit_burden_and_stop_rules(self) -> None:
        protocol = self.data["protocol"]
        self.assertEqual([item["number"] for item in protocol["stages"]], list(range(1, 10)))
        self.assertEqual(protocol["stages"][0]["title"], "الأمان والاستقرار")
        self.assertEqual(protocol["stages"][-1]["title"], "المراجعة والقرار")
        joined = " ".join(protocol["minimum_measures"])
        for marker in ("جودة", "المساعدة", "التعب", "رغبة", "التعميم", "جودة الحياة"):
            self.assertIn(marker, joined)
        stops = " ".join(protocol["stop_rules"])
        for marker in ("ألم", "نوبة", "سحب الموافقة", "الاستغلال", "عدم وجود فائدة"):
            self.assertIn(marker, stops)


class CapabilitiesPublisherV280(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="capabilities-v280-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))
        (self.site / "special-needs").mkdir(parents=True)
        (self.site / "outside-the-box").mkdir(parents=True)
        (self.site / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head></head><body>'
            '<main><h1>الرئيسية</h1></main></body></html>',
            encoding="utf-8",
        )
        (self.site / "special-needs/index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head></head><body>'
            '<main><h1>مركز ذوي الاحتياجات الخاصة</h1></main></body></html>',
            encoding="utf-8",
        )
        (self.site / "outside-the-box/index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head></head><body>'
            '<main><h1>أفكار خارج الصندوق</h1></main></body></html>',
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

    def test_generates_one_hundred_complete_protocols_registry_and_api(self) -> None:
        report = self.publish()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["condition_count"], 100)
        self.assertEqual(report["detailed_guide_count"], 100)
        self.assertEqual(report["bespoke_research_synthesis_count"], 5)
        self.assertEqual(report["condition_profile_count"], 100)
        self.assertEqual(report["direct_condition_reference_count"], 100)
        self.assertEqual(report["generated_page_count"], 104)
        self.assertEqual(report["sitemap_url_count"], 104)
        self.assertEqual(report["protocol_stage_count"], 9)
        self.assertEqual(report["source_count"], 132)
        self.assertEqual(report["curated_evidence_packet_count"], 100)
        self.assertEqual(report["curated_evidence_claim_count"], 300)
        self.assertEqual(report["curated_evidence_source_count"], 112)
        self.assertEqual(report["curated_evidence_remaining_count"], 0)
        self.assertEqual(
            report["curated_evidence_covered_categories"],
            [
                "chronic-health",
                "genetic-metabolic",
                "motor-neurological",
                "neurodevelopmental-learning",
                "progressive-psychosocial",
                "sensory-communication",
            ],
        )
        self.assertFalse(report["external_clinical_review_completed"])
        self.assertFalse(report["diagnostic_automation"])
        self.assertFalse(report["condition_implies_strength"])

        pages = sorted((self.site / "capabilities").rglob("index.html"))
        self.assertEqual(len(pages), 104)
        for path in pages:
            text = path.read_text(encoding="utf-8")
            self.assertEqual(len(re.findall(r"<h1\b", text)), 1, path)
            for marker in (
                'lang="ar"',
                'dir="rtl"',
                'name="description"',
                'rel="canonical"',
                "application/ld+json",
                "capabilities-v280.css",
                "capabilities-v280.js",
                "المراجعة السريرية",
            ):
                self.assertIn(marker, text, (path, marker))

        registry = (self.site / "capabilities/registry/index.html").read_text(
            encoding="utf-8"
        )
        self.assertEqual(registry.count("data-cap-condition"), 100)
        self.assertEqual(registry.count("البروتوكول الكامل"), 100)
        self.assertIn("inflammatory-bowel-disease", registry)
        self.assertIn("schizophrenia-functional-support", registry)
        self.assertIn("bipolar-disorder-functional-support", registry)

        api = json.loads(
            (self.site / "api/capabilities-v280.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(api["conditions"]), 100)
        self.assertEqual(len(api["guides"]), 100)
        self.assertEqual(len(api["sources"]), 132)
        self.assertEqual(len(api["evidence_packets"]), 100)
        self.assertEqual(
            sum(len(item["claims"]) for item in api["evidence_packets"]),
            300,
        )
        self.assertEqual(len(api["protocol"]["stages"]), 9)
        packet_slugs = {item["slug"] for item in api["evidence_packets"]}
        for guide in api["guides"]:
            self.assertEqual(len(guide["hypotheses"]), 4)
            self.assertEqual(len(guide["research_links"]), 2)
            self.assertEqual(
                set(guide["profile"]),
                {
                    "slug",
                    "position",
                    "ability_focus",
                    "access_priority",
                    "safety_priority",
                    "task_trial",
                    "functional_goal",
                },
            )
            if guide["slug"] in packet_slugs:
                self.assertIsInstance(guide["evidence_packet"], dict)
                self.assertEqual(len(guide["evidence_packet"]["claims"]), 3)
            else:
                self.assertIsNone(guide["evidence_packet"])

    def test_all_one_hundred_guides_have_full_protocol_and_research_routes(self) -> None:
        self.publish()
        data = json.loads(DATA.read_text(encoding="utf-8"))
        bespoke = {item["slug"]: item for item in data["guides"]}
        selected_payloads = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in EVIDENCE_DIR.glob("*.json")
        ]
        selected_packets = {
            packet["slug"]: packet
            for payload in selected_payloads
            for packet in payload["evidence_packets"]
        }
        for condition in data["conditions"]:
            path = self.site / "capabilities" / condition["slug"] / "index.html"
            text = path.read_text(encoding="utf-8")
            for marker in (
                "طبقة الحالة الخاصة",
                "الموقف العلمي",
                "سؤال القدرة",
                "أولوية الوصول",
                "فحص الأمان",
                "التجربة المصغرة",
                "مثال هدف وظيفي",
                "ماذا يقول الدليل، وماذا لا يقول؟",
                "لا تفترض",
                "الصحة والأمان أولًا",
                "فرضيات قدرة قابلة للدحض",
                "تجربة مهمة صغيرة",
                "ما الذي نقيسه؟",
                "متى نتوقف أو نعيد الصياغة؟",
                "البروتوكول الكامل لهذه الحالة",
                "المرحلة 1: الأمان والاستقرار",
                "المرحلة 9: المراجعة والقرار",
                "خطة 12 أسبوعًا",
                "قواعد توقف عامة",
                "المصادر التي تسند هذا الدليل",
                "تحقق خاص بالحالة ومسار للبحث الأحدث",
                "بحث PubMed محدث",
                "لا توجد مصادقة أو مراجعة خارجية مستقلة",
            ):
                self.assertIn(marker, text, (condition["slug"], marker))
            self.assertEqual(text.count('class="cap-hypothesis"'), 4)
            self.assertEqual(text.count('class="cap-stage"'), 9)
            self.assertGreater(len(text), 18000, condition["slug"])
            if condition["slug"] in selected_packets:
                self.assertIn("خلاصة الأدلة المنتقاة", text)
                self.assertIn('data-evidence-packet="selected"', text)
                self.assertEqual(
                    text.count('class="cap-evidence-claim"'),
                    3,
                )
                self.assertEqual(
                    text.count("ما الذي يدعمه الدليل؟"),
                    3,
                )
                self.assertEqual(
                    text.count("ما الذي لا يدعمه الدليل؟"),
                    3,
                )
                for claim in selected_packets[condition["slug"]]["claims"]:
                    for source_id in claim["source_ids"]:
                        self.assertIn(f'id="source-{source_id}"', text)
            else:
                self.assertNotIn("خلاصة الأدلة المنتقاة", text)
                self.assertIn(
                    "لم تكتمل لهذه الحالة بعد حزمة أدلة منتقاة مكافئة",
                    text,
                )
                self.assertIn('data-evidence-packet="not-selected"', text)
            if condition["slug"] in bespoke:
                for source_id in bespoke[condition["slug"]]["source_ids"]:
                    self.assertIn(f'id="source-{source_id}"', text)

    def test_protocol_is_printable_and_registry_runtime_is_local_only(self) -> None:
        self.publish()
        protocol = (self.site / "capabilities/protocol/index.html").read_text(
            encoding="utf-8"
        )
        runtime = (self.site / "assets/js/capabilities-v280.js").read_text(
            encoding="utf-8"
        )
        stylesheet = (self.site / "assets/css/capabilities-v280.css").read_text(
            encoding="utf-8"
        )
        for marker in (
            "المراحل التسع",
            "الحد الأدنى للقياس",
            "قواعد التوقف",
            "ورقة عمل قابلة للطباعة",
            "رأي الشخص في الاستمرار أو التعديل أو التوقف",
            "data-cap-print",
        ):
            self.assertIn(marker, protocol)
        for forbidden in (
            "fetch(",
            "XMLHttpRequest",
            "sendBeacon",
            "WebSocket",
            "localStorage",
            "sessionStorage",
            "document.cookie",
        ):
            self.assertNotIn(forbidden, runtime)
        self.assertIn("window.print()", runtime)
        self.assertIn("@media print", stylesheet)
        self.assertIn("prefers-reduced-motion", stylesheet)

    def test_integrates_gateways_sitemap_and_robots_idempotently(self) -> None:
        self.publish()
        tracked = [
            self.site / "index.html",
            self.site / "special-needs/index.html",
            self.site / "outside-the-box/index.html",
            self.site / "sitemap.xml",
            self.site / "sitemap-capabilities.xml",
            self.site / "robots.txt",
        ]
        before = [digest(path) for path in tracked]
        self.publish()
        after = [digest(path) for path in tracked]
        self.assertEqual(before, after)

        for path in tracked[:3]:
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count("capabilities-v280:start"), 1)
            self.assertEqual(text.count("capabilities-v280:end"), 1)
            self.assertIn('/capabilities/', text)

        robots = tracked[-1].read_text(encoding="utf-8")
        self.assertEqual(
            robots.count(f"Sitemap: {BASE}sitemap-capabilities.xml"),
            1,
        )
        root_urls = [
            node.text
            for node in ET.parse(self.site / "sitemap.xml")
            .getroot()
            .findall("{*}sitemap/{*}loc")
            if node.text
        ]
        self.assertEqual(root_urls.count(BASE + "sitemap-capabilities.xml"), 1)
        section_urls = [
            node.text
            for node in ET.parse(self.site / "sitemap-capabilities.xml")
            .getroot()
            .findall("{*}url/{*}loc")
            if node.text
        ]
        self.assertEqual(len(section_urls), 104)
        self.assertEqual(len(section_urls), len(set(section_urls)))

    def test_public_copy_is_person_first_and_review_state_is_honest(self) -> None:
        self.publish()
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (self.site / "capabilities").rglob("index.html")
        )
        for banned in (
            "معاقين",
            "كل مرض هبة",
            "المراجعة الخارجية مكتملة",
            "معتمد سريريًا",
            "اعتماد عالمي",
            "شفاء مضمون",
            "نتيجة مضمونة",
            "قيد الإعداد",
        ):
            self.assertNotIn(banned, text)
        self.assertIn("لا يشخّص", text)
        self.assertIn("لا توجد مصادقة أو مراجعة خارجية مستقلة", text)
        self.assertIn("لا نبحث عن قيمة الشخص في تشخيصه", text)

    def test_main_build_pipeline_invokes_v280_after_provider_pathways(self) -> None:
        text = INTEGRATION.read_text(encoding="utf-8")
        outside = text.index('run_publisher("publish_outside_the_box_v254.py")')
        capabilities = text.index('run_publisher("publish_capabilities_v280.py")')
        self.assertLess(outside, capabilities)
        self.assertIn('"capabilities_publisher": 280', text)


if __name__ == "__main__":
    unittest.main()
