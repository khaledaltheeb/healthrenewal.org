from __future__ import annotations

import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT / "sectors" / "youth" / "digital-safety" / "index.html"
YOUTH = ROOT / "sectors" / "youth" / "index.html"
YOUTH_SITEMAP = ROOT / "sitemap-sector-youth.xml"
SITEMAP_INDEX = ROOT / "sitemap-index.xml"
ROUTE = "https://healthrenewal.org/sectors/youth/digital-safety/"


class YouthDigitalSafetyV407Tests(unittest.TestCase):
    def test_hub_has_required_identity_safety_and_rights_boundaries(self) -> None:
        source = HUB.read_text(encoding="utf-8")
        self.assertIn("السلامة الرقمية وحماية الأطفال واليافعين", source)
        self.assertIn(f'<link rel="canonical" href="{ROUTE}">', source)
        self.assertIn('data-content-engine="v407"', source)
        self.assertIn("إذا كان هناك خطر مباشر", source)
        self.assertIn("مسار الاستجابة المشترك", source)
        self.assertIn("حالة الحقوق والمراجعة الخارجية", source)
        self.assertIn("لا تمثل الصفحة اعتمادًا أو شراكة أو مراجعة خارجية من e-Enfance / 3018", source)
        self.assertIn("لا تعيد روافد إنتاج الأداة أو ترجمتها في هذه الصفحة", source)
        self.assertNotIn("logo 3018", source.lower())
        self.assertNotIn("e-enfance-logo", source.lower())

    def test_hub_covers_required_action_paths(self) -> None:
        source = HUB.read_text(encoding="utf-8")
        for required in (
            "تنمر أو تهديد أو إقصاء متكرر",
            "ابتزاز أو استدراج أو استغلال جنسي رقمي",
            "نشر صور أو محتوى حميمي دون موافقة",
            "انتحال هوية أو اختراق أو كشف معلومات",
            "محتوى مخيف أو عنيف أو جنسي أو مؤذٍ",
            "مشكلة داخل لعبة أو شبكة اجتماعية",
            "قلق حول وقت الشاشة أو الاستخدام الرقمي",
            "لا أعرف ماذا أحفظ أو أين أبلغ",
        ):
            self.assertIn(required, source)

    def test_partner_references_are_links_not_endorsement_claims(self) -> None:
        source = HUB.read_text(encoding="utf-8")
        self.assertIn("https://e-enfance.org/le3018/", source)
        self.assertIn("https://e-enfance.org/ressources/cyberharcelometre/", source)
        self.assertIn("https://www.unicef.org/stories/how-to-stop-cyberbullying", source)
        self.assertIn("https://www.itu.int/pub/S-GEN-COP.EDUC-2020", source)
        self.assertIn("https://www.unesco.org/en/health-education/safe-learning-environments", source)
        self.assertNotRegex(source, re.compile(r"(?:معتمد|بإشراف|شريك رسمي)\s+(?:من|مع)\s+e-Enfance", re.I))

    def test_parent_sector_surfaces_the_hub_without_replacing_existing_guides(self) -> None:
        source = YOUTH.read_text(encoding="utf-8")
        self.assertIn('href="digital-safety/"', source)
        self.assertIn("قسم متخصص جديد", source)
        self.assertEqual(source.count('class="card"'), 15)
        self.assertIn("guides/bullying-cyberbullying-response/", source)
        self.assertIn("guides/sleep-digital-habits/", source)

    def test_youth_sitemap_and_index_register_the_hub(self) -> None:
        root = ET.parse(YOUTH_SITEMAP).getroot()
        urls = [(node.text or "").strip() for node in root.findall("{*}url/{*}loc")]
        self.assertIn(ROUTE, urls)
        self.assertEqual(len(urls), len(set(urls)))
        self.assertEqual(len(urls), 17)

        index = ET.parse(SITEMAP_INDEX).getroot()
        sitemaps = [(node.text or "").strip() for node in index.findall("{*}sitemap/{*}loc")]
        self.assertIn("https://healthrenewal.org/sitemap-sector-youth.xml", sitemaps)

    def test_jsonld_is_parseable(self) -> None:
        source = HUB.read_text(encoding="utf-8")
        match = re.search(r'<script type="application/ld\+json">(.*?)</script>', source, re.S)
        self.assertIsNotNone(match)
        payload = json.loads(match.group(1))
        self.assertEqual(payload["@context"], "https://schema.org")
        graph = payload["@graph"]
        page = next(item for item in graph if item.get("@type") == "CollectionPage")
        self.assertEqual(page["url"], ROUTE)
        self.assertEqual(page["mainEntity"]["numberOfItems"], 8)


if __name__ == "__main__":
    unittest.main()
