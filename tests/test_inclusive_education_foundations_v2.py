from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, urlsplit


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "learning-paths/evidence-guided/inclusive-education-foundations/index.html"
RECORD = ROOT / "learning-paths/evidence-guided/inclusive-education-foundations/source-verification.json"
CANONICAL = "https://healthrenewal.org/learning-paths/evidence-guided/inclusive-education-foundations/"


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.ids: set[str] = set()
        self.h1_count = 0
        self.images = 0

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.links.append((values["href"], values.get("rel", "")))
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "h1":
            self.h1_count += 1
        if tag == "img":
            self.images += 1


def internal_target(href: str) -> Path:
    parsed = urlsplit(href)
    relative = parsed.path.lstrip("/")
    if not relative:
        return ROOT / "index.html"
    target = ROOT / relative
    return target / "index.html" if parsed.path.endswith("/") else target


class InclusiveEducationFoundationsV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.record = json.loads(RECORD.read_text(encoding="utf-8"))
        cls.parser = PageParser()
        cls.parser.feed(cls.html)
        cls.visible_text = re.sub(r"<[^>]+>", " ", cls.html)
        cls.visible_text = re.sub(r"\s+", " ", cls.visible_text).strip()

    def test_page_is_substantive_and_not_templated_filler(self) -> None:
        self.assertGreaterEqual(len(self.visible_text.split()), 1500)
        for phrase in (
            "الوصول والمشاركة والتعلم والشعور بالانتماء",
            "التصميم الشامل للتعلم",
            "الترتيب التيسيري",
            "علامات الدمج الزائف",
            "لوحة قياس لا تختزل الدمج في الحضور",
            "الخطة التنفيذية 2024–2027",
        ):
            self.assertIn(phrase, self.visible_text)
        self.assertNotIn("في موضوع أسس التعليم الدامج، تُفهم هذه النقطة", self.visible_text)
        self.assertNotIn("شراء أداة؛ الدليل هو تغير وظيفي", self.visible_text)
        self.assertNotIn("معاقين", self.visible_text)

    def test_metadata_schema_accessibility_and_print(self) -> None:
        self.assertIn('<html lang="ar" dir="rtl">', self.html)
        self.assertEqual(self.parser.h1_count, 1)
        self.assertIn("main-content", self.parser.ids)
        self.assertIn('href="#main-content"', self.html)
        self.assertIn(f'<link rel="canonical" href="{CANONICAL}">', self.html)
        self.assertIn('"@type":"LearningResource"', self.html)
        self.assertIn('"dateModified":"2026-08-06"', self.html)
        self.assertIn("pt-platform-shell:v1", self.html)
        self.assertIn('data-pt-normalized="1.1.0"', self.html)
        self.assertIn("@media print", self.html)
        self.assertIn("@media(prefers-reduced-motion:reduce)", self.html)
        self.assertEqual(self.parser.images, 0)

    def test_decision_sections_and_table_are_complete(self) -> None:
        required_ids = {
            "meaning", "distinctions", "barriers", "udl", "cycle", "plan",
            "measurement", "redflags", "jordan", "meeting", "faq", "sources",
        }
        self.assertTrue(required_ids <= self.parser.ids)
        self.assertGreaterEqual(self.html.count("<article"), 20)
        self.assertGreaterEqual(self.html.count("<table"), 2)
        self.assertGreaterEqual(self.html.count("<details>"), 4)
        self.assertEqual(self.html.count("class=\"step\""), 11)

    def test_source_record_is_governed_and_claims_resolve(self) -> None:
        self.assertEqual(self.record["page"], "/learning-paths/evidence-guided/inclusive-education-foundations/")
        self.assertEqual(self.record["canonical"], CANONICAL)
        self.assertEqual(self.record["review_status"], "internally-reviewed")
        self.assertEqual(self.record["external_review"], "recommended-not-completed")
        self.assertEqual(self.record["verified_at"], "2026-08-06")
        self.assertGreater(self.record["next_review_at"], self.record["verified_at"])
        self.assertGreaterEqual(len(self.record["professional_limits"]), 180)
        sources = self.record["sources"]
        self.assertEqual(len(sources), 8)
        ids = {source["id"] for source in sources}
        self.assertEqual(len(ids), len(sources))
        for claim in self.record["editorial_claims"]:
            self.assertTrue(set(claim["source_ids"]) <= ids)
            self.assertGreaterEqual(len(claim["claim"]), 80)

    def test_sources_are_https_first_party_and_linked(self) -> None:
        allowed_domains = {
            "www.unesco.org", "www.unicef.org", "www.ohchr.org",
            "udlguidelines.cast.org", "hcd.gov.jo",
        }
        page_links = {href for href, _ in self.parser.links}
        for source in self.record["sources"]:
            parsed = urlparse(source["url"])
            self.assertEqual(parsed.scheme, "https")
            self.assertIn(parsed.netloc, allowed_domains)
            self.assertEqual(source["verified_at"], "2026-08-06")
            self.assertEqual(source["rights"], "link-and-summarize-only")
            self.assertIn(source["url"], page_links)
        for href, rel in self.parser.links:
            if href.startswith("http"):
                self.assertIn("noopener", rel)
                self.assertIn("noreferrer", rel)

    def test_internal_navigation_targets_exist(self) -> None:
        missing = []
        for href, _ in self.parser.links:
            if href.startswith("/") and not internal_target(href).is_file():
                missing.append(href)
        self.assertEqual(missing, [], f"missing internal targets: {missing}")

    def test_rights_and_non_affiliation_are_visible(self) -> None:
        self.assertIn("لا توجد شراكة أو مصادقة أو مراجعة خارجية", self.visible_text)
        self.assertIn("ليست فتوى قانونية", self.visible_text)
        non_claims = " ".join(self.record["non_claims"])
        self.assertIn("لا توجد شراكة", non_claims)
        self.assertIn("لا يُستخدم التصميم الشامل", non_claims)


if __name__ == "__main__":
    unittest.main()
