from __future__ import annotations

import difflib
import hashlib
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "content" / "v281" / "metadata-ar.json"
CONDITIONS_DIR = ROOT / "content" / "v281" / "conditions"
V280 = ROOT / "content" / "v280" / "capabilities-100-ar.json"
BUILDER = ROOT / "scripts" / "build_conditions_v281_data.py"
PUBLISHER = ROOT / "scripts" / "publish_conditions_v281.py"
PRODUCTION_GATE = ROOT / "scripts" / "validate_capabilities_production_v1.py"
PUB_WORKFLOW = ROOT / ".github" / "workflows" / "publish-capabilities-v281.yml"
DEPLOY_WORKFLOW = ROOT / ".github" / "workflows" / "deploy-production-v3.yml"

TRUSTED_SOURCE_HOSTS = {
    "www.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "pubmed.ncbi.nlm.nih.gov",
    "medlineplus.gov",
    "rarediseases.info.nih.gov",
    "www.orpha.net",
    "orpha.net",
    "www.who.int",
}

VERIFIED_PUBMED_SOURCES = {
    "setd5-related-neurodevelopmental-disorder": (
        "https://pubmed.ncbi.nlm.nih.gov/40265665/",
        "SETD5",
    ),
    "scn2a-related-disorder": (
        "https://pubmed.ncbi.nlm.nih.gov/38651838/",
        "SCN2A",
    ),
    "cacna1a-related-disorder": (
        "https://pubmed.ncbi.nlm.nih.gov/37555011/",
        "CACNA1A",
    ),
    "mucopolysaccharidosis-type-vi": (
        "https://pubmed.ncbi.nlm.nih.gov/31142378/",
        "MPS VI",
    ),
}

KNOWN_WRONG_SOURCE_URLS = {
    "https://pubmed.ncbi.nlm.nih.gov/34942083/",
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class ConditionsV281Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = load_module("v281_builder", BUILDER)
        cls.publisher = load_module("v281_publisher", PUBLISHER)
        cls.data = cls.builder.load_sources()
        cls.builder.build()

    def test_exactly_fifty_non_repeated_conditions(self):
        items = self.data["conditions"]
        self.assertEqual(self.data["version"], 281)
        self.assertEqual(len(items), 50)
        self.assertEqual([item["rank"] for item in items], list(range(101, 151)))
        self.assertEqual(len({item["slug"] for item in items}), 50)
        self.assertTrue(
            all(
                re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", item["slug"])
                for item in items
            )
        )
        old = {
            item["slug"]
            for item in json.loads(V280.read_text(encoding="utf-8"))["conditions"]
        }
        self.assertFalse(old.intersection({item["slug"] for item in items}))
        self.assertEqual(len(list(CONDITIONS_DIR.glob("*.jsonl"))), 3)
        self.assertTrue(METADATA.is_file())

    def test_required_depth_sources_and_boundaries(self):
        required = {
            "rank",
            "slug",
            "title_ar",
            "title_en",
            "category",
            "cause",
            "pattern",
            "medical_focus",
            "diagnosis",
            "care",
            "safety",
            "opportunity",
            "source_title",
            "source_url",
        }
        allowed_categories = {
            "chromatin-syndromic",
            "developmental-epileptic",
            "metabolic-neurodegenerative",
        }
        items = self.data["conditions"]
        for item in items:
            self.assertEqual(set(item), required, item["slug"])
            self.assertIn(item["category"], allowed_categories)
            for key in (
                "cause",
                "pattern",
                "medical_focus",
                "diagnosis",
                "care",
                "safety",
                "opportunity",
            ):
                self.assertGreaterEqual(len(item[key]), 70, (item["slug"], key))
            parsed = urlparse(item["source_url"])
            self.assertEqual(parsed.scheme, "https", item["slug"])
            self.assertIn(parsed.netloc.lower(), TRUSTED_SOURCE_HOSTS, item["slug"])
            self.assertTrue(item["source_title"].strip(), item["slug"])

        self.assertEqual(len({item["source_url"] for item in items}), 50)
        for key in (
            "cause",
            "pattern",
            "medical_focus",
            "diagnosis",
            "care",
            "safety",
            "opportunity",
        ):
            self.assertEqual(len({item[key] for item in items}), 50, key)

        evidence = self.data.get("evidence_overrides", {})
        self.assertGreaterEqual(int(evidence.get("applied", 0)), 42)
        self.assertGreaterEqual(len(evidence.get("waves", [])), 1)

        text = json.dumps(self.data, ensure_ascii=False)
        for banned in (
            "معاقين",
            "اعتماد عالمي",
            "علاج مضمون",
            "أوقف الدواء",
            "غيّر الجرعة",
        ):
            self.assertNotIn(banned, text)
        self.assertIn("لا توجد مصادقة أو مراجعة سريرية خارجية مستقلة", text)

    def test_verified_pubmed_sources_match_the_intended_conditions(self):
        by_slug = {item["slug"]: item for item in self.data["conditions"]}
        for slug, (expected_url, title_token) in VERIFIED_PUBMED_SOURCES.items():
            with self.subTest(slug=slug):
                item = by_slug[slug]
                self.assertEqual(item["source_url"], expected_url)
                self.assertIn(title_token.casefold(), item["source_title"].casefold())

        source_urls = {item["source_url"] for item in self.data["conditions"]}
        self.assertTrue(KNOWN_WRONG_SOURCE_URLS.isdisjoint(source_urls))

    def test_condition_specific_packets_are_not_near_duplicates(self):
        packets = []
        for item in self.data["conditions"]:
            packet = " ".join(
                item[key]
                for key in (
                    "cause",
                    "pattern",
                    "medical_focus",
                    "diagnosis",
                    "care",
                    "safety",
                    "opportunity",
                )
            )
            packets.append((item["slug"], re.sub(r"\s+", " ", packet)))

        maximum = (0.0, "", "")
        for index, (left_slug, left) in enumerate(packets):
            for right_slug, right in packets[index + 1 :]:
                ratio = difflib.SequenceMatcher(
                    None, left, right, autojunk=False
                ).ratio()
                if ratio > maximum[0]:
                    maximum = (ratio, left_slug, right_slug)
                self.assertLess(ratio, 0.88, maximum)
        self.assertLess(maximum[0], 0.88, maximum)

    def test_builder_is_deterministic_and_publisher_generates_deep_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            first = temp / "first.b64"
            second = temp / "second.b64"
            self.builder.build(first)
            self.builder.build(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())

            root = temp / "site"
            (root / "capabilities").mkdir(parents=True)
            (root / "special-needs").mkdir()
            (root / "capabilities" / "index.html").write_text(
                "<html><body><main><h1>hub</h1></main></body></html>",
                encoding="utf-8",
            )
            (root / "special-needs" / "index.html").write_text(
                "<html><body><main><h1>sector</h1></main></body></html>",
                encoding="utf-8",
            )
            (root / "sitemap.xml").write_text(
                '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>',
                encoding="utf-8",
            )

            report = self.publisher.publish(root)
            self.assertEqual(
                (
                    report["condition_count"],
                    report["detail_page_count"],
                    report["generated_page_count"],
                ),
                (50, 50, 51),
            )
            self.assertEqual(report["source_count"], 50)
            self.assertEqual(report["unique_source_count"], 50)
            self.assertGreaterEqual(report["minimum_page_word_count"], 1300)

            pages = [
                root / "capabilities" / item["slug"] / "index.html"
                for item in self.data["conditions"]
            ]
            self.assertTrue(all(path.is_file() for path in pages))
            hashes = set()
            for condition, path in zip(self.data["conditions"], pages):
                text = path.read_text(encoding="utf-8")
                plain = re.sub(r"<[^>]+>", " ", text)
                self.assertGreaterEqual(
                    len(re.findall(r"[\u0600-\u06ffA-Za-z0-9]+", plain)),
                    1300,
                    path,
                )
                self.assertEqual(text.count("<h1"), 1, path)
                self.assertGreaterEqual(text.count("<h2>"), 14, path)
                self.assertIn(condition["source_url"], text)
                self.assertIn('"@type": "MedicalWebPage"', text)
                self.assertIn('rel="canonical"', text)
                self.assertNotIn("معاقين", text)
                digest = hashlib.sha256(
                    re.sub(r"\s+", " ", plain).encode()
                ).hexdigest()
                self.assertNotIn(digest, hashes)
                hashes.add(digest)

            sitemap = (root / "sitemap-capabilities-v281.xml").read_text(
                encoding="utf-8"
            )
            self.assertEqual(sitemap.count("<url>"), 51)
            source_copy = json.loads(
                (root / "api" / "capabilities-v281-source.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(len(source_copy["conditions"]), 50)
            self.publisher.publish(root)
            self.assertEqual(
                (root / "capabilities" / "index.html")
                .read_text(encoding="utf-8")
                .count("capabilities-v281:start"),
                1,
            )
            self.assertEqual(
                (root / "special-needs" / "index.html")
                .read_text(encoding="utf-8")
                .count("capabilities-v281:start"),
                1,
            )

    def test_publication_chain_builds_and_verifies_v281(self):
        publish = PUB_WORKFLOW.read_text(encoding="utf-8")
        deploy = DEPLOY_WORKFLOW.read_text(encoding="utf-8")
        self.assertTrue(PRODUCTION_GATE.is_file())
        self.assertIn("python scripts/build_conditions_v281_data.py", publish)
        self.assertIn("python scripts/publish_conditions_v281.py validated-site", publish)
        self.assertIn("Publish capabilities library v280", publish)
        self.assertIn("capabilities-v281.json", publish)
        self.assertIn("sitemap-capabilities-v281.xml", publish)
        self.assertIn("capabilities-v281-source.json", publish)

        self.assertIn("publish_capabilities_v280.py", deploy)
        self.assertIn("build_conditions_v281_data.py", deploy)
        self.assertIn("publish_conditions_v281.py", deploy)
        self.assertIn("validate_capabilities_production_v1.py", deploy)
        self.assertIn("validated-production-site", deploy)
        self.assertIn("actions/deploy-pages@v4", deploy)
        self.assertIn("Verify exact capabilities publication live", deploy)
        self.assertIn("https://healthrenewal.org/deployment.json", deploy)
        self.assertIn("https://healthrenewal.org/api/capabilities-production-gate-v1.json", deploy)


if __name__ == "__main__":
    unittest.main()
