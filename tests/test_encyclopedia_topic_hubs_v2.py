from __future__ import annotations

import html
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_encyclopedia_topic_hubs_v2.py"

FACET_KEYS = (
    "definition",
    "signs",
    "factors",
    "assessment",
    "differential",
    "psychotherapy",
    "cbt",
    "self_help",
    "coping",
    "prevention",
    "early",
    "children",
    "adolescents",
    "adults",
    "older",
    "family",
    "relationships",
    "work",
    "school",
    "quality",
)


class EncyclopediaTopicHubsV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("topic_hubs_v2", PUBLISHER)
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load topic-hub publisher")
        cls.publisher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.publisher)

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ency-topic-v2-")
        self.site = Path(self.temp.name)
        (self.site / "hubs").mkdir(parents=True)
        (self.site / "assets/css").mkdir(parents=True)
        (self.site / "api").mkdir(parents=True)
        (self.site / "sitemap-hubs.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://example.test/hubs/</loc><lastmod>2026-07-27</lastmod></url>'
            '</urlset>',
            encoding="utf-8",
        )
        self.builder = self.fake_builder()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def fake_builder(self):
        facets = [
            {
                "key": key,
                "ar": f"زاوية {index:02d}",
                "en": f"facet {index:02d}",
                "focus": f"تركيز الزاوية {index:02d}",
            }
            for index, key in enumerate(FACET_KEYS, 1)
        ]
        items = []
        item_id = 1
        for topic_index in range(1, 101):
            domain = f"الموضوع {topic_index:03d}"
            for facet_index, facet in enumerate(facets, 1):
                items.append(
                    {
                        "id": item_id,
                        "slug": f"concept-{item_id:04d}",
                        "ar": f"{domain}: {facet['ar']}",
                        "en": f"Topic {topic_index:03d}: {facet['en']}",
                        "domain_ar": domain,
                        "domain_en": f"Topic {topic_index:03d}",
                        "category": f"تصنيف {(topic_index - 1) % 10 + 1:02d}",
                        "facet": facet,
                        "domain_index": topic_index,
                        "facet_index": facet_index,
                    }
                )
                item_id += 1

        def write(path: Path, text: str) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

        def head(title, description, path, schema, keywords):
            canonical = "https://example.test/" + path.lstrip("/")
            return (
                '<meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                f"<title>{html.escape(title)}</title>"
                f'<meta name="description" content="{html.escape(description, quote=True)}">'
                f'<link rel="canonical" href="{canonical}">'
                f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>'
            )

        return SimpleNamespace(
            SITE=self.site,
            BASE="https://example.test/",
            TODAY="2026-07-27",
            FACETS=facets,
            entries=lambda: list(items),
            esc=lambda value: html.escape(str(value), quote=True),
            normalize=lambda value: re.sub(r"\s+", " ", str(value)).strip().lower(),
            write=write,
            head=head,
            profile_for=lambda domain, category: {
                "definition": f"تعريف متكامل لـ{domain} ضمن {category}.",
                "observations": ["ملاحظة أولى", "ملاحظة ثانية", "ملاحظة ثالثة"],
                "distinctions": ["فرق أول", "فرق ثان"],
                "related": [],
            },
            choose_sources=lambda domain, facet, category: [
                ("مصدر مؤسسي أول", "https://www.who.int/"),
                ("مصدر مؤسسي ثان", "https://www.nimh.nih.gov/"),
            ],
            source_links=lambda sources: "".join(
                f'<li><a href="{html.escape(url, quote=True)}">{html.escape(title)}</a></li>'
                for title, url in sources
            ),
        )

    def test_publisher_creates_topic_first_navigation_without_losing_details(self):
        report = self.publisher.publish(self.builder)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["topic_hubs"], 100)
        self.assertEqual(report["facets_per_topic"], 20)
        self.assertEqual(report["detail_pages_preserved"], 2000)
        self.assertEqual(report["primary_index_cards"], 100)
        self.assertEqual(report["detail_archive_cards"], 2000)

        index = (self.site / "encyclopedia/index.html").read_text(encoding="utf-8")
        archive = (self.site / "encyclopedia/all/index.html").read_text(encoding="utf-8")
        hubs = (self.site / "hubs/index.html").read_text(encoding="utf-8")
        self.assertEqual(index.count('class="ency-topic-v2__card topic-item"'), 100)
        self.assertEqual(archive.count('class="ency-topic-v2__card detail-item"'), 2000)
        self.assertIn("الموضوعات المرجعية المئة", hubs)
        self.assertIn("زوايا المقارنة العشرون", hubs)
        self.assertIn("المسارات التطبيقية الثمانون", hubs)

    def test_every_topic_hub_links_exactly_twenty_unique_detail_pages(self):
        self.publisher.publish(self.builder)
        pages = sorted((self.site / "hubs").glob("topic-*/index.html"))
        self.assertEqual(len(pages), 100)
        for page in pages:
            text = page.read_text(encoding="utf-8")
            self.assertEqual(text.count("<h1"), 1, page.name)
            self.assertIn('data-topic-hub-v2="true"', text)
            detail_links = set(re.findall(r'/encyclopedia/(concept-\d{4})/', text))
            self.assertEqual(len(detail_links), 20, page)
            for group_title in ("الفهم الأساسي", "التقييم والتدخل المهني", "الدعم والتكيف والعلاقات", "العمر والبيئة وجودة الحياة"):
                self.assertIn(group_title, text, page)

    def test_archive_is_registered_in_sitemap_and_api_report_is_written(self):
        first = self.publisher.publish(self.builder)
        second = self.publisher.publish(self.builder)
        self.assertEqual(first["primary_index_cards"], second["primary_index_cards"])
        sitemap = (self.site / "sitemap-hubs.xml").read_text(encoding="utf-8")
        self.assertEqual(sitemap.count("https://example.test/encyclopedia/all/"), 1)
        report = json.loads((self.site / "api/encyclopedia-topic-hubs-v2.json").read_text(encoding="utf-8"))
        self.assertEqual(report["primary_navigation"], "topic-first")
        self.assertEqual(report["topic_hubs"], 100)

    def test_run_script_integrates_publisher_before_focused_audit(self):
        runner = (ROOT / "scripts/run_encyclopedia_v13.py").read_text(encoding="utf-8")
        self.assertIn('Path(__file__).with_name("publish_encyclopedia_topic_hubs_v2.py")', runner)
        self.assertIn("topic_report = topic_module.publish(module)", runner)
        self.assertIn("audit_report = audit_encyclopedia_surface(module.SITE)", runner)
        self.assertLess(runner.index("topic_report = topic_module.publish(module)"), runner.index("audit_report = audit_encyclopedia_surface(module.SITE)"))


if __name__ == "__main__":
    unittest.main()
