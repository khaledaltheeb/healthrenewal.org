from __future__ import annotations

import importlib.util
import sys
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "audit_live_search_discovery_v1.py"
SPEC = importlib.util.spec_from_file_location(
    "audit_live_search_discovery_v1",
    MODULE_PATH,
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


class LiveSearchDiscoveryAuditTests(unittest.TestCase):
    def test_normalize_url_removes_fragments_and_default_port(self) -> None:
        self.assertEqual(
            audit.normalize_url(
                "HTTPS://HealthRenewal.org:443/path#fragment"
            ),
            "https://healthrenewal.org/path",
        )

    def test_normalize_url_percent_encodes_arabic_path(self) -> None:
        self.assertEqual(
            audit.normalize_url(
                "https://healthrenewal.org/categories/الأساسيات/"
            ),
            (
                "https://healthrenewal.org/categories/"
                "%D8%A7%D9%84%D8%A3%D8%B3%D8%A7%D8%B3%D9%8A%D8%A7%D8%AA/"
            ),
        )

    def test_robots_sitemaps_are_resolved_and_deduplicated(self) -> None:
        text = """
        User-agent: *
        Allow: /
        Sitemap: /sitemap.xml
        Sitemap: https://healthrenewal.org/sitemap.xml
        Sitemap: /sitemap-index.xml
        """
        self.assertEqual(
            audit.robots_sitemaps(
                text,
                "https://healthrenewal.org/",
            ),
            [
                "https://healthrenewal.org/sitemap.xml",
                "https://healthrenewal.org/sitemap-index.xml",
            ],
        )

    def test_parse_urlset(self) -> None:
        kind, values = audit.parse_sitemap(
            """<?xml version="1.0"?>
            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
              <url><loc>https://healthrenewal.org/</loc></url>
              <url><loc>/family-guide/</loc></url>
            </urlset>""",
            "https://healthrenewal.org/sitemap.xml",
        )
        self.assertEqual(kind, "urlset")
        self.assertEqual(
            values,
            [
                "https://healthrenewal.org/",
                "https://healthrenewal.org/family-guide/",
            ],
        )

    def test_parse_sitemap_index(self) -> None:
        kind, values = audit.parse_sitemap(
            """<?xml version="1.0"?>
            <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
              <sitemap><loc>/sitemap.xml</loc></sitemap>
              <sitemap><loc>/sitemap-special-needs.xml</loc></sitemap>
            </sitemapindex>""",
            "https://healthrenewal.org/sitemap-index.xml",
        )
        self.assertEqual(kind, "sitemapindex")
        self.assertEqual(len(values), 2)

    def test_head_parser_reads_canonical_robots_and_hreflang(self) -> None:
        parser = audit.HeadParser()
        parser.feed(
            """
            <html lang="ar"><head>
              <title>اختبار</title>
              <meta name="robots" content="noindex,follow">
              <link rel="canonical" href="/guide/">
              <link rel="alternate" hreflang="ar" href="/guide/">
              <link rel="alternate" hreflang="x-default" href="/guide/">
            </head><body></body></html>
            """
        )
        signals = parser.signals("https://healthrenewal.org/source/")
        self.assertEqual(
            signals.canonical,
            "https://healthrenewal.org/guide/",
        )
        self.assertTrue(signals.noindex)
        self.assertEqual(signals.title, "اختبار")
        self.assertEqual(
            signals.hreflang,
            (
                ("ar", "https://healthrenewal.org/guide/"),
                ("x-default", "https://healthrenewal.org/guide/"),
            ),
        )

    def test_fetch_with_retries_recovers_from_transient_503(self) -> None:
        first = audit.FetchResult(
            requested_url="https://healthrenewal.org/a/",
            final_url="https://healthrenewal.org/a/",
            status=503,
            content_type="text/html",
            body=b"",
            elapsed_ms=1,
            error="HTTP 503",
        )
        second = audit.FetchResult(
            requested_url="https://healthrenewal.org/a/",
            final_url="https://healthrenewal.org/a/",
            status=200,
            content_type="text/html",
            body=b"<html></html>",
            elapsed_ms=1,
        )
        with (
            mock.patch.object(
                audit,
                "request_url",
                side_effect=[first, second],
            ) as request,
            mock.patch.object(audit.time, "sleep"),
        ):
            result = audit.fetch_with_retries(
                "https://healthrenewal.org/a/",
                timeout=1,
                limit=100,
            )
        self.assertEqual(result.status, 200)
        self.assertEqual(request.call_count, 2)

    def test_same_origin_rejects_www_variant(self) -> None:
        self.assertTrue(
            audit.same_origin(
                "https://healthrenewal.org/a/",
                "https://healthrenewal.org/",
            )
        )
        self.assertFalse(
            audit.same_origin(
                "https://www.healthrenewal.org/a/",
                "https://healthrenewal.org/",
            )
        )


if __name__ == "__main__":
    unittest.main()
