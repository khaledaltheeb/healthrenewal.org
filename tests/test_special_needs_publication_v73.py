import json
import re
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "v73" / "special-needs-executable-instructions-ar.json"
PUBLISHER = ROOT / "scripts" / "publish_special_needs_v73.py"
PIPELINE = ROOT / "scripts" / "apply_homepage_v20.py"
SOURCE_HOME = ROOT / "index.html"
SOURCE_SITEMAP = ROOT / "sitemap.xml"
BASE = "https://healthrenewal.org"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "nav", "footer"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "nav", "footer"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data):
        if not self.hidden_depth:
            self.parts.append(data)


def visible_words(text: str) -> int:
    parser = TextParser()
    parser.feed(text)
    normalized = re.sub(r"\s+", " ", " ".join(parser.parts))
    return len(re.findall(r"[\w\u0600-\u06FF]+", normalized, flags=re.UNICODE))


class SpecialNeedsPublicationV73Tests(unittest.TestCase):
    def build_fixture(self) -> Path:
        site = Path(tempfile.mkdtemp(prefix="special-needs-v73-"))
        shutil.copy2(SOURCE_HOME, site / "index.html")
        shutil.copy2(SOURCE_SITEMAP, site / "sitemap.xml")
        return site

    def publish(self, site: Path) -> None:
        subprocess.run(
            ["python3", str(PUBLISHER), str(site)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_source_is_complete_honest_and_institutionally_sourced(self):
        data = json.loads(DATA.read_text(encoding="utf-8"))
        self.assertEqual(data["version"], 73)
        self.assertEqual(data["review_status"], "needs-external-review")
        self.assertEqual(len(data["units"]), 3)
        self.assertGreaterEqual(len(data["learning_outcomes"]), 5)
        self.assertGreaterEqual(len(data["core_principles"]), 4)
        self.assertGreaterEqual(len(data["sources"]), 4)
        self.assertEqual([unit["number"] for unit in data["units"]], [1, 2, 3])
        for unit in data["units"]:
            self.assertGreaterEqual(len(unit["objectives"]), 3)
            self.assertGreaterEqual(len(unit["explanation"]), 5)
            self.assertGreaterEqual(len(unit["practice"]), 4)
            self.assertGreaterEqual(len(unit["checklist"]), 5)
        allowed = {"www.cdc.gov", "www.unicef.org", "www.unesco.org"}
        for source in data["sources"]:
            parsed = urlparse(source["url"])
            self.assertEqual(parsed.scheme, "https")
            self.assertIn(parsed.netloc, allowed)
            self.assertTrue(source["use"].strip())
        serialized = json.dumps(data, ensure_ascii=False)
        for phrase in ["غير تشخيصية", "لا تحدد أهلية", "تحتاج مراجعة خارجية"]:
            self.assertIn(phrase, serialized)
        for prohibited in ["معتمد دوليًا", "مراجعة سريرية مكتملة", "يعالج نهائيًا", "تشخيصك"]:
            self.assertNotIn(prohibited, serialized)

    def test_production_pipeline_invokes_course_and_final_hub_publishers(self):
        text = PIPELINE.read_text(encoding="utf-8")
        self.assertIn("publish_special_needs_v73.py", text)
        self.assertIn('"special_needs_publisher": 201', text)
        identity = (ROOT / "scripts" / "enforce_platform_identity_v201.py").read_text(encoding="utf-8")
        self.assertIn("publish_special_needs_hub_v201.py", identity)

    def test_publisher_generates_center_course_units_metadata_and_depth(self):
        site = self.build_fixture()
        self.addCleanup(shutil.rmtree, site, True)
        self.publish(site)
        data = json.loads(DATA.read_text(encoding="utf-8"))
        slug = data["slug"]
        pages = [
            site / "special-needs" / "index.html",
            site / "special-needs" / slug / "index.html",
            *[
                site / "special-needs" / slug / f"unit-{number}" / "index.html"
                for number in (1, 2, 3)
            ],
        ]
        self.assertEqual(len(pages), 5)
        total_words = 0
        for index, path in enumerate(pages):
            self.assertTrue(path.is_file(), path)
            text = path.read_text(encoding="utf-8")
            self.assertIn('<html lang="ar" dir="rtl">', text)
            self.assertEqual(len(re.findall(r"<h1\b", text)), 1)
            self.assertEqual(text.count('rel="canonical"'), 1)
            self.assertIn('application/ld+json', text)
            self.assertIn('name="description"', text)
            self.assertIn('property="og:title"', text)
            self.assertIn('name="twitter:card"', text)
            self.assertIn('rel="manifest"', text)
            self.assertIn(data["reviewed_at"], text)
            self.assertIn("غير تشخيص", text)
            count = visible_words(text)
            total_words += count
            minimum = 180 if index == 0 else 300
            self.assertGreaterEqual(count, minimum, f"{path}: {count} visible words")
        self.assertGreaterEqual(total_words, 2200)

    def test_homepage_and_sitemaps_are_linked_without_duplicates(self):
        site = self.build_fixture()
        self.addCleanup(shutil.rmtree, site, True)
        self.publish(site)
        first = (site / "index.html").read_text(encoding="utf-8")
        self.publish(site)
        homepage = (site / "index.html").read_text(encoding="utf-8")
        self.assertEqual(first, homepage)
        self.assertGreaterEqual(homepage.count('href="special-needs/"'), 2)
        self.assertEqual(homepage.count('data-special-needs-v73'), 1)
        header = re.search(r"<header\b[^>]*>.*?</header>", homepage, re.I | re.S)
        self.assertIsNotNone(header)
        self.assertEqual(header.group(0).count('<a href="special-needs/">ذوو الاحتياجات الخاصة</a>'), 1)
        self.assertIn("ذوو الاحتياجات الخاصة", homepage)

        child = ET.parse(site / "sitemap-special-needs.xml").getroot()
        child_urls = [node.text for node in child.findall("sm:url/sm:loc", NS)]
        self.assertEqual(len(child_urls), 5)
        self.assertEqual(len(child_urls), len(set(child_urls)))
        self.assertTrue(all(url.startswith(BASE + "/special-needs/") for url in child_urls))

        root = ET.parse(site / "sitemap.xml").getroot()
        local = root.tag.rsplit("}", 1)[-1]
        self.assertEqual(local, "urlset")
        main_urls = [node.text for node in root.findall("sm:url/sm:loc", NS)]
        for url in child_urls:
            self.assertEqual(main_urls.count(url), 1)
        self.assertFalse(root.findall("sm:sitemap", NS))

    def test_report_matches_generated_output_and_preexisting_homepage_links(self):
        site = self.build_fixture()
        self.addCleanup(shutil.rmtree, site, True)
        self.publish(site)
        report = json.loads((site / "api" / "special-needs-v73.json").read_text(encoding="utf-8"))
        self.assertEqual(report["version"], 73)
        self.assertEqual(report["generated_page_count"], 5)
        self.assertEqual(report["course_count"], 1)
        self.assertEqual(report["unit_count"], 3)
        self.assertGreaterEqual(report["source_count"], 4)
        self.assertEqual(report["review_status"], "needs-external-review")
        self.assertEqual(report["sitemap_urls"], 5)
        self.assertEqual(report["sitemap_mode"], "urlset")
        self.assertFalse(report["homepage"]["nav_added"])
        self.assertFalse(report["homepage"]["card_added"])

    def test_generated_pages_avoid_prohibited_claims(self):
        site = self.build_fixture()
        self.addCleanup(shutil.rmtree, site, True)
        self.publish(site)
        joined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (site / "special-needs").rglob("index.html")
        )
        for prohibited in [
            "يؤكد التشخيص",
            "بديل عن الطبيب",
            "أوقف الدواء",
            "غيّر الجرعة",
            "مراجعة اختصاصي مكتملة",
            "اعتماد دولي",
        ]:
            self.assertNotIn(prohibited, joined)
        for required in [
            "الألم",
            "النوم",
            "الحواس",
            "البيئة",
            "الطوارئ المحلية",
        ]:
            self.assertIn(required, joined)


if __name__ == "__main__":
    unittest.main()
