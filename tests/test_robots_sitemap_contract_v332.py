from __future__ import annotations

import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ROBOTS = ROOT / "robots.txt"
BASE_PATH = "/pterminology-site/"


class RobotsSitemapContractV332Tests(unittest.TestCase):
    def test_sitemap_directives_are_unique_and_supported(self) -> None:
        lines = [line.strip() for line in ROBOTS.read_text(encoding="utf-8").splitlines()]
        sitemap_urls = [line.split(":", 1)[1].strip() for line in lines if line.lower().startswith("sitemap:")]

        self.assertGreaterEqual(len(sitemap_urls), 1)
        self.assertEqual(len(sitemap_urls), len(set(sitemap_urls)))
        self.assertNotIn(
            "https://khaledaltheeb.github.io/pterminology-site/sitemap-index.xml",
            sitemap_urls,
            "robots.txt must not advertise an index that is absent from source and build publishers",
        )

        for url in sitemap_urls:
            parsed = urlparse(url)
            self.assertEqual(parsed.scheme, "https")
            self.assertEqual(parsed.netloc, "khaledaltheeb.github.io")
            self.assertTrue(parsed.path.startswith(BASE_PATH))
            self.assertTrue(parsed.path.endswith(".xml"))

    def test_public_crawling_contract_remains_open(self) -> None:
        text = ROBOTS.read_text(encoding="utf-8")
        self.assertIn("User-agent: *", text)
        self.assertIn("Allow: /", text)
        self.assertNotIn("Disallow: /", text)


if __name__ == "__main__":
    unittest.main()
