from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "sectors" / "all-pages" / "index.html"
PLATFORM_CSS = ROOT / "assets" / "platform" / "platform-core.css"
EXPECTED_CANONICAL = "https://healthrenewal.org/sectors/all-pages/"
EXPECTED_COUNT = 69


def internal_target(href: str) -> Path:
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc or not parsed.path.startswith("/"):
        raise AssertionError(f"invalid internal target: {href}")
    relative = parsed.path.lstrip("/")
    if not relative:
        return ROOT / "index.html"
    target = ROOT / relative
    return target / "index.html" if parsed.path.endswith("/") else target


class CompleteSectorsIndexV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.cards = re.findall(
            r'<article\s+class="[^"]*\bcomplete-discovery-card\b[^"]*"[^>]*>(.*?)</article>',
            cls.html,
            flags=re.DOTALL,
        )
        cls.links: list[str] = []
        cls.titles: list[str] = []
        for card in cls.cards:
            href = re.search(r'<a\s+href="([^"]+)"', card)
            title = re.search(
                r'<h[23][^>]*>(?:<a[^>]*>)?\s*(.*?)\s*(?:</a>)?</h[23]>',
                card,
                flags=re.DOTALL,
            )
            if not href or not title:
                raise AssertionError("sector card is missing its link or heading")
            cls.links.append(href.group(1))
            cls.titles.append(re.sub(r'<[^>]+>', '', title.group(1)).strip())

    def test_publication_identity_and_accessibility(self) -> None:
        self.assertIn('<html lang="ar" dir="rtl">', self.html)
        self.assertEqual(self.html.count("<h1>"), 1)
        self.assertIn(
            f'<link rel="canonical" href="{EXPECTED_CANONICAL}">',
            self.html,
        )
        self.assertIn('data-pt-normalized="1.1.0"', self.html)
        self.assertIn('<label for="q">', self.html)
        self.assertIn('id="q"', self.html)
        self.assertNotIn("معاقين", self.html)

    def test_visible_inventory_is_complete_and_unique(self) -> None:
        self.assertEqual(len(self.cards), EXPECTED_COUNT)
        self.assertEqual(len(self.links), len(set(self.links)))
        self.assertEqual(len(self.titles), len(set(self.titles)))
        self.assertTrue(all(len(title) >= 4 for title in self.titles))

    def test_collection_schema_matches_visible_inventory(self) -> None:
        collections = []
        for raw in re.findall(
            r'<script\s+type="application/ld\+json">(.*?)</script>',
            self.html,
            flags=re.DOTALL,
        ):
            payload = json.loads(raw)
            if isinstance(payload, dict) and payload.get("@type") == "CollectionPage":
                collections.append(payload)
        self.assertEqual(len(collections), 1)
        self.assertEqual(collections[0]["url"], EXPECTED_CANONICAL)
        self.assertEqual(collections[0]["numberOfItems"], EXPECTED_COUNT)

    def test_every_sector_card_has_a_published_destination(self) -> None:
        missing = [href for href in self.links if not internal_target(href).is_file()]
        self.assertEqual(missing, [], f"missing sector targets: {missing}")

    def test_shared_shell_supports_print(self) -> None:
        css = PLATFORM_CSS.read_text(encoding="utf-8")
        self.assertIn("@media print", css)
        self.assertIn(".pt-global-shell", css)
        self.assertIn(".pt-global-footer", css)


def load_tests(loader, tests, pattern):
    """Extend the sectors contract with the inclusive-education guide contract."""
    from tests import test_inclusive_education_foundations_v2 as inclusive_education

    tests.addTests(loader.loadTestsFromModule(inclusive_education))
    return tests


if __name__ == "__main__":
    unittest.main()
