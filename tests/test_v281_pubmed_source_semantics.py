from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_conditions_v281_data.py"

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
    "https://pubmed.ncbi.nlm.nih.gov/34942083/",  # "Jab"; unrelated to MPS VI.
}


def load_builder():
    spec = importlib.util.spec_from_file_location("v281_builder_source_semantics", BUILDER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class V281PubmedSourceSemanticsContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_builder().load_sources()
        cls.conditions = {item["slug"]: item for item in cls.data["conditions"]}

    def test_verified_pubmed_sources_remain_bound_to_the_intended_conditions(self):
        for slug, (expected_url, required_title_token) in VERIFIED_PUBMED_SOURCES.items():
            with self.subTest(slug=slug):
                condition = self.conditions[slug]
                self.assertEqual(condition["source_url"], expected_url)
                self.assertIn(required_title_token.casefold(), condition["source_title"].casefold())

    def test_known_unrelated_pubmed_sources_are_rejected(self):
        source_urls = {item["source_url"] for item in self.data["conditions"]}
        self.assertTrue(KNOWN_WRONG_SOURCE_URLS.isdisjoint(source_urls))


if __name__ == "__main__":
    unittest.main()
