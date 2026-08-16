from __future__ import annotations

import unittest

from scripts.verify_homepage_v19 import StrictHTMLParser, has_link


class HomepageDiscoveryMetadataTests(unittest.TestCase):
    def parse_links(self, source: str) -> list[dict[str, str]]:
        parser = StrictHTMLParser()
        parser.feed(source)
        return parser.links

    def test_favicon_attributes_are_order_independent(self) -> None:
        variants = (
            '<link rel="icon" type="image/svg+xml" href="/assets/brand/logo-mark.svg">',
            '<link href="/assets/brand/logo-mark.svg" rel="icon" type="image/svg+xml">',
            '<link type="image/svg+xml" href="/assets/brand/logo-mark.svg" rel="icon">',
        )
        for source in variants:
            with self.subTest(source=source):
                self.assertTrue(
                    has_link(
                        self.parse_links(source),
                        rel="icon",
                        href="/assets/brand/logo-mark.svg",
                        type="image/svg+xml",
                    )
                )

    def test_favicon_requires_all_contract_attributes(self) -> None:
        invalid = (
            '<link type="image/svg+xml" href="/assets/brand/logo-mark.svg">',
            '<link rel="icon" type="image/png" href="/assets/brand/logo-mark.svg">',
            '<link rel="icon" type="image/svg+xml" href="/favicon.svg">',
        )
        for source in invalid:
            with self.subTest(source=source):
                self.assertFalse(
                    has_link(
                        self.parse_links(source),
                        rel="icon",
                        href="/assets/brand/logo-mark.svg",
                        type="image/svg+xml",
                    )
                )

    def test_rel_token_list_is_semantic(self) -> None:
        links = self.parse_links(
            '<link href="/assets/brand/logo-mark.svg" rel="shortcut icon" type="image/svg+xml">'
        )
        self.assertTrue(
            has_link(
                links,
                rel="icon",
                href="/assets/brand/logo-mark.svg",
                type="image/svg+xml",
            )
        )


if __name__ == "__main__":
    unittest.main()
