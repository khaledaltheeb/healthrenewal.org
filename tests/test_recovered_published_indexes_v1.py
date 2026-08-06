from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
PLATFORM_CSS = ROOT / "assets" / "platform" / "platform-core.css"

INDEX_PAGES = {
    "learning-paths/all-pages/index.html": {
        "canonical": "https://healthrenewal.org/learning-paths/all-pages/",
        "count": 43,
        "card_class": "complete-discovery-card",
    },
    "sectors/all-pages/index.html": {
        "canonical": "https://healthrenewal.org/sectors/all-pages/",
        "count": 69,
        "card_class": "complete-discovery-card",
    },
    "special-needs/all-pages/index.html": {
        "canonical": "https://healthrenewal.org/special-needs/all-pages/",
        "count": 149,
        "card_class": "complete-discovery-card",
    },
}

COMMUNICATION_HUB = {
    "path": "special-needs/guides/communication/index.html",
    "canonical": "https://healthrenewal.org/special-needs/guides/communication/",
    "count": 6,
}


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def canonical_from(html: str) -> str:
    match = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', html)
    assert match, "missing canonical"
    return match.group(1)


def json_ld_documents(html: str) -> list[dict]:
    documents: list[dict] = []
    for raw in re.findall(
        r'<script\s+type="application/ld\+json">(.*?)</script>',
        html,
        flags=re.DOTALL,
    ):
        value = json.loads(raw)
        if isinstance(value, dict):
            documents.append(value)
    return documents


def article_blocks(html: str, card_class: str | None = None) -> list[str]:
    if card_class:
        pattern = rf'<article\s+class="[^"]*\b{re.escape(card_class)}\b[^"]*"[^>]*>(.*?)</article>'
    else:
        pattern = r'<article(?:\s[^>]*)?>(.*?)</article>'
    return re.findall(pattern, html, flags=re.DOTALL)


def links_and_titles(blocks: list[str]) -> tuple[list[str], list[str]]:
    links: list[str] = []
    titles: list[str] = []
    for block in blocks:
        href = re.search(r'<a\s+href="([^"]+)"', block)
        title = re.search(r'<h[23][^>]*>(?:<a[^>]*>)?\s*(.*?)\s*(?:</a>)?</h[23]>', block, flags=re.DOTALL)
        assert href, "card without link"
        assert title, "card without heading"
        links.append(href.group(1))
        titles.append(re.sub(r'<[^>]+>', '', title.group(1)).strip())
    return links, titles


def internal_target(href: str) -> Path:
    parsed = urlsplit(href)
    assert not parsed.scheme and not parsed.netloc, href
    assert parsed.path.startswith("/"), href
    relative = parsed.path.lstrip("/")
    if not relative:
        return ROOT / "index.html"
    target = ROOT / relative
    if parsed.path.endswith("/"):
        target = target / "index.html"
    return target


class RecoveredPublishedIndexesV1Tests(unittest.TestCase):
    def test_all_pages_indexes_are_complete_and_schema_counts_match(self) -> None:
        for path, expected in INDEX_PAGES.items():
            with self.subTest(path=path):
                html = read(path)
                self.assertIn('<html lang="ar" dir="rtl">', html)
                self.assertEqual(html.count("<h1>"), 1)
                self.assertEqual(canonical_from(html), expected["canonical"])
                self.assertIn('data-pt-normalized="1.1.0"', html)
                self.assertIn("assets/platform/platform-core.css", html)
                self.assertIn('<label for="q">', html)
                self.assertIn('id="q"', html)
                self.assertNotIn("معاقين", html)

                blocks = article_blocks(html, expected["card_class"])
                links, titles = links_and_titles(blocks)
                self.assertEqual(len(blocks), expected["count"])
                self.assertEqual(len(links), len(set(links)))
                self.assertEqual(len(titles), len(set(titles)))
                self.assertTrue(all(len(title) >= 4 for title in titles))

                collections = [
                    item
                    for item in json_ld_documents(html)
                    if item.get("@type") == "CollectionPage"
                ]
                self.assertEqual(len(collections), 1)
                self.assertEqual(collections[0]["numberOfItems"], expected["count"])
                self.assertEqual(collections[0]["url"], expected["canonical"])

                missing = [href for href in links if not internal_target(href).is_file()]
                self.assertEqual(missing, [], f"missing card targets in {path}: {missing}")

    def test_communication_hub_is_substantive_and_all_six_guides_exist(self) -> None:
        html = read(COMMUNICATION_HUB["path"])
        self.assertIn('<html lang="ar" dir="rtl">', html)
        self.assertEqual(html.count("<h1>"), 1)
        self.assertEqual(canonical_from(html), COMMUNICATION_HUB["canonical"])
        self.assertIn('data-pt-normalized="1.1.0"', html)
        self.assertNotIn("معاقين", html)

        blocks = article_blocks(html)
        links, titles = links_and_titles(blocks)
        self.assertEqual(len(blocks), COMMUNICATION_HUB["count"])
        self.assertEqual(len(links), len(set(links)))
        self.assertEqual(len(titles), len(set(titles)))
        self.assertGreaterEqual(len(re.sub(r'<[^>]+>', ' ', html).split()), 100)
        missing = [href for href in links if not internal_target(href).is_file()]
        self.assertEqual(missing, [], f"missing communication guide targets: {missing}")

        article_schema = [
            item
            for item in json_ld_documents(html)
            if item.get("@type") == "Article"
        ]
        self.assertEqual(len(article_schema), 1)
        self.assertEqual(article_schema[0]["url"], COMMUNICATION_HUB["canonical"])

    def test_shared_platform_layer_provides_print_support(self) -> None:
        css = PLATFORM_CSS.read_text(encoding="utf-8")
        self.assertIn("@media print", css)
        self.assertIn(".pt-global-shell", css)
        self.assertIn(".pt-global-footer", css)


if __name__ == "__main__":
    unittest.main()
