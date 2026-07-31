from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import publish_autism_clinical_pathways_v324 as module


class AutismClinicalPathwaysV324Tests(unittest.TestCase):
    def make_site(self, root: Path) -> Path:
        site = root / "_site"
        parent = site / "special-needs" / "autism" / "index.html"
        parent.parent.mkdir(parents=True)
        parent.write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head>'
            '<meta charset="utf-8"><title>التوحد</title>'
            '<link rel="canonical" href="https://khaledaltheeb.github.io/pterminology-site/special-needs/autism/">'
            '<script type="application/ld+json">{"@context":"https://schema.org","@type":"MedicalWebPage"}</script>'
            '</head><body><main><h1>دليل التوحد</h1>'
            '<section class="source-area" id="sources"><h2>المراجع</h2></section>'
            '</main></body></html>',
            encoding="utf-8",
        )
        (site / "sitemap-special-needs.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://khaledaltheeb.github.io/pterminology-site/special-needs/</loc></url>'
            '<url><loc>https://khaledaltheeb.github.io/pterminology-site/special-needs/autism/</loc></url>'
            '</urlset>',
            encoding="utf-8",
        )
        return site

    @staticmethod
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_source_parts_digests_manifest_depth_evidence_and_boundaries(self) -> None:
        actual = tuple(sorted(path.name for path in module.PARTS_DIR.glob("*.b64")))
        self.assertEqual(actual, module.PART_NAMES)
        encoded = "".join(
            "".join((module.PARTS_DIR / name).read_text(encoding="ascii").split())
            for name in module.PART_NAMES
        )
        self.assertEqual(len(encoded), module.EXPECTED_B64_LENGTH)
        self.assertEqual(module.sha256(encoded.encode("ascii")), module.EXPECTED_B64_SHA256)

        payload = module.read_payload()
        guides = module.validate_payload(payload)
        self.assertEqual(payload["version"], 324)
        self.assertEqual(payload["language"], "ar")
        self.assertEqual(
            payload["review_status"],
            "internally-reviewed-external-clinical-review-required",
        )
        self.assertEqual(tuple(guide["slug"] for guide in guides), module.EXPECTED)
        self.assertEqual(len(guides), 4)
        self.assertEqual(sum(len(guide["sections"]) for guide in guides), 28)
        self.assertEqual(sum(len(guide["sources"]) for guide in guides), 26)
        self.assertEqual(sum(len(guide["action_steps"]) for guide in guides), 24)
        self.assertEqual(sum(len(guide["urgent"]) for guide in guides), 12)
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertIsNone(module.BANNED.search(serialized))
        for phrase in (
            "التقييم الشامل ليس جلسة واحدة ولا درجة في أداة",
            "التمويه مفهوم بحثي متطور وليس اختبارًا تشخيصيًا مستقلًا",
            "التواصل المعزز والبديل ليس حلًا أخيرًا بعد فشل الكلام",
            "الاستخلاب أو السيكريتين أو الأكسجين عالي الضغط",
            "غياب نتيجة جينية لا ينفي التوحد",
            "لا يُسحب نظام AAC لإجبار الشخص على الكلام",
        ):
            self.assertIn(phrase, serialized)

    def test_publish_depth_parent_links_sitemap_schema_shell_and_idempotence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            first = module.publish(site)
            tracked = [
                site / "special-needs" / "autism" / "index.html",
                site / "sitemap-special-needs.xml",
                site / "api" / "autism-clinical-pathways-v324.json",
                *(site / "special-needs" / slug / "index.html" for slug in module.EXPECTED),
            ]
            before = [self.digest(path) for path in tracked]
            second = module.publish(site)
            after = [self.digest(path) for path in tracked]

            self.assertEqual(first, second)
            self.assertEqual(before, after)
            self.assertEqual(first["version"], 324)
            self.assertEqual(first["status"], "passed")
            self.assertEqual(first["guide_count"], 4)
            self.assertEqual(first["section_count"], 28)
            self.assertEqual(first["source_count"], 26)
            self.assertEqual(first["action_step_count"], 24)
            self.assertEqual(first["urgent_item_count"], 12)
            self.assertEqual(first["parent_links_added"], 4)
            self.assertGreaterEqual(first["minimum_guide_words"], 1250)
            self.assertTrue(first["sitemap_registered"])
            self.assertTrue(first["platform_shell_normalized"])
            self.assertEqual(first["source_part_count"], 5)
            self.assertEqual(first["source_base64_sha256"], module.EXPECTED_B64_SHA256)
            self.assertEqual(first["source_gzip_sha256"], module.EXPECTED_GZIP_SHA256)
            self.assertEqual(first["source_json_sha256"], module.EXPECTED_JSON_SHA256)
            self.assertFalse(first["external_clinical_review_completed"])

            parent = (site / "special-needs" / "autism" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(parent.count(module.PARENT_MARKER), 1)
            for slug in module.EXPECTED:
                self.assertEqual(parent.count(f"/pterminology-site/special-needs/{slug}/"), 1)
                page = site / "special-needs" / slug / "index.html"
                self.assertTrue(page.is_file(), slug)
                source = page.read_text(encoding="utf-8")
                self.assertEqual(source.lower().count("<h1"), 1)
                self.assertEqual(source.count('class="section-card"'), 7)
                self.assertGreaterEqual(module.words(source), 1250)
                self.assertIn('type="application/ld+json"', source)
                self.assertIn("MedicalWebPage", source)
                self.assertIn("BreadcrumbList", source)
                self.assertIn("لم تكتمل مراجعة سريرية خارجية مستقلة", source)
                self.assertEqual(source.count(module.SHELL_MARKER), 1)
                self.assertIn('data-pt-normalized="1.1.0"', source)
                self.assertIsNone(module.BANNED.search(source))

            urls = [
                (node.text or "").strip()
                for node in ET.parse(site / "sitemap-special-needs.xml").getroot().findall("{*}url/{*}loc")
                if node.text
            ]
            for slug in module.EXPECTED:
                expected = f"{module.BASE}/special-needs/{slug}/"
                self.assertEqual(urls.count(expected), 1)
            self.assertEqual(len(urls), len(set(urls)))

            api = json.loads(
                (site / "api" / "autism-clinical-pathways-v324.json").read_text(encoding="utf-8")
            )
            self.assertEqual(api, first)
            self.assertEqual(api["content_source"], "content/v324/autism-clinical-pathways-ar.parts")

    def test_rejects_dishonest_review_and_unknown_evidence(self) -> None:
        payload = module.read_payload()
        payload["review_status"] = "externally-reviewed"
        with self.assertRaises(SystemExit):
            module.validate_payload(payload)

        payload = module.read_payload()
        payload["guides"][0]["sections"][0]["source_ids"] = ["MISSING"]
        with self.assertRaises(SystemExit):
            module.validate_payload(payload)


if __name__ == "__main__":
    unittest.main()
