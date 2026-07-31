from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from submit_indexnow_v334 import (  # noqa: E402
    MAX_URLS_PER_BATCH,
    discover_urls,
    prepare_key,
    submit_urls,
)

BASE = "https://healthrenewal.org/"
KEY = "a4f9d7c2e81b4630b5d6f7a912ce3048"


class IndexNowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "robots.txt").write_text(
            f"User-agent: *\nAllow: /\nSitemap: {BASE}sitemap-index.xml\n",
            encoding="utf-8",
        )
        (self.root / "sitemap-index.xml").write_text(
            f'''<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap><loc>{BASE}sitemap-a.xml</loc></sitemap>
            <sitemap><loc>{BASE}sitemap-b.xml</loc></sitemap>
            </sitemapindex>''',
            encoding="utf-8",
        )
        (self.root / "sitemap-a.xml").write_text(
            f'''<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>{BASE}</loc></url>
            <url><loc>{BASE}library/?x=1#top</loc></url>
            </urlset>''',
            encoding="utf-8",
        )
        (self.root / "sitemap-b.xml").write_text(
            f'''<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>{BASE}library/</loc></url>
            <url><loc>https://example.com/external/</loc></url>
            </urlset>''',
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_recursive_discovery_filters_and_deduplicates(self) -> None:
        urls, warnings = discover_urls(self.root, BASE)
        self.assertEqual(urls, [BASE, BASE + "library/"])
        self.assertTrue(any("external URL" in warning for warning in warnings))

    def test_prepare_key_writes_public_proof(self) -> None:
        path, location = prepare_key(self.root, BASE, KEY)
        self.assertEqual(path.read_text(encoding="utf-8"), KEY)
        self.assertEqual(location, BASE + KEY + ".txt")

    def test_submit_batches_and_payload(self) -> None:
        urls = [BASE + f"p/{index}/" for index in range(MAX_URLS_PER_BATCH + 1)]
        payloads: list[dict[str, object]] = []

        def sender(endpoint: str, payload: bytes, timeout: int) -> int:
            payloads.append(json.loads(payload.decode("utf-8")))
            return 200

        results = submit_urls(
            urls,
            base_url=BASE,
            key=KEY,
            key_location=BASE + KEY + ".txt",
            batch_size=MAX_URLS_PER_BATCH,
            sender=sender,
        )
        self.assertEqual([item.url_count for item in results], [10000, 1])
        self.assertTrue(all(item.accepted for item in results))
        self.assertEqual(payloads[0]["host"], "khaledaltheeb.github.io")
        self.assertEqual(len(payloads[0]["urlList"]), 10000)

    def test_non_success_status_fails_without_retry_for_403(self) -> None:
        calls = 0

        def sender(endpoint: str, payload: bytes, timeout: int) -> int:
            nonlocal calls
            calls += 1
            return 403

        results = submit_urls(
            [BASE],
            base_url=BASE,
            key=KEY,
            key_location=BASE + KEY + ".txt",
            sender=sender,
        )
        self.assertEqual(calls, 1)
        self.assertFalse(results[0].accepted)
        self.assertEqual(results[0].status, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
