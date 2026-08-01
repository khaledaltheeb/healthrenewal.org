from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_sitemap_index_v304.py"

EXPECTED_AI_AGENTS = (
    "OAI-SearchBot",
    "GPTBot",
    "ChatGPT-User",
    "ClaudeBot",
    "Claude-SearchBot",
    "Claude-User",
    "Claude-Web",
    "PerplexityBot",
    "Perplexity-User",
    "Google-Extended",
)


def load_module():
    import sys

    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location("machine_readable_sitemap_v1", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load sitemap generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AICrawlerMachineReadableV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()
        self.temp = tempfile.TemporaryDirectory(prefix="ai-crawler-machine-readable-v1-")
        self.site = Path(self.temp.name)
        (self.site / "index.html").write_text(
            """<!doctype html>
<html lang="ar" dir="rtl">
<head>
<title>منصة اختبار</title>
<meta name="description" content="وصف عربي واضح">
<link rel="canonical" href="https://healthrenewal.org/">
</head>
<body><header></header><main><h1>منصة اختبار</h1><article>محتوى</article></main></body>
</html>
""",
            encoding="utf-8",
        )
        (self.site / "en").mkdir()
        (self.site / "en" / "index.html").write_text(
            """<!doctype html>
<html lang="en">
<head><title>English page</title></head>
<body><main><h1>English page</h1></main></body>
</html>
""",
            encoding="utf-8",
        )
        (self.site / "private").mkdir()
        (self.site / "private" / "index.html").write_text(
            """<!doctype html>
<html lang="ar"><head><title>Private</title><meta name="robots" content="noindex,nofollow"></head>
<body><main><h1>Private</h1></main></body></html>
""",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_generates_explicit_ai_policy_and_machine_readable_surface(self) -> None:
        report = self.module.generate(self.site)
        robots = (self.site / "robots.txt").read_text(encoding="utf-8")

        self.assertEqual(report["version"], 305)
        self.assertEqual(report["robots_policy"], "explicit-ai-and-public-crawling")
        self.assertEqual(report["indexable_pages"], 2)
        self.assertNotIn("Disallow:", robots)
        for agent in EXPECTED_AI_AGENTS:
            self.assertEqual(robots.count(f"User-agent: {agent}\nAllow: /"), 1)

        self.assertEqual(robots.count("Sitemap: https://healthrenewal.org/sitemap.xml"), 1)
        self.assertEqual(robots.count("Sitemap: https://healthrenewal.org/sitemap-index.xml"), 1)

        required = (
            "feed.xml",
            "atom.xml",
            "llms-full.txt",
            "api/v1/content-index.json",
            "api/v1/ai-discovery.json",
            "api/v1/ai-discovery.openapi.json",
            "api/sitemap-index-v305.json",
        )
        for relative in required:
            self.assertTrue((self.site / relative).is_file(), relative)

        content_index = json.loads(
            (self.site / "api/v1/content-index.json").read_text(encoding="utf-8")
        )
        self.assertEqual(content_index["count"], 2)
        self.assertEqual(
            {item["url"] for item in content_index["items"]},
            {"https://healthrenewal.org/", "https://healthrenewal.org/en/"},
        )

        discovery = json.loads(
            (self.site / "api/v1/ai-discovery.json").read_text(encoding="utf-8")
        )
        self.assertEqual(discovery["rendering"]["mode"], "static-generated-html")
        self.assertFalse(discovery["rendering"]["javascriptRequiredForPrimaryText"])
        self.assertEqual(discovery["contentCount"], 2)
        self.assertIn("https://openai.com/searchbot.json", discovery["security"]["openAiIpManifest"])

        openapi = json.loads(
            (self.site / "api/v1/ai-discovery.openapi.json").read_text(encoding="utf-8")
        )
        self.assertEqual(openapi["openapi"], "3.1.0")
        self.assertIn("/api/v1/content-index.json", openapi["paths"])

        ET.parse(self.site / "feed.xml")
        ET.parse(self.site / "atom.xml")

    def test_enriches_indexable_html_without_overriding_noindex(self) -> None:
        self.module.generate(self.site)

        home = (self.site / "index.html").read_text(encoding="utf-8")
        self.assertIn('type="application/rss+xml"', home)
        self.assertIn('type="application/atom+xml"', home)
        self.assertIn("/api/v1/content-index.json", home)
        self.assertIn('type="application/ld+json"', home)
        self.assertIn('name="robots"', home)

        private = (self.site / "private/index.html").read_text(encoding="utf-8")
        self.assertNotIn('type="application/rss+xml"', private)
        self.assertNotIn("/api/v1/content-index.json", private)
        sitemap = (self.site / "sitemap.xml").read_text(encoding="utf-8")
        self.assertNotIn("https://healthrenewal.org/private/", sitemap)


if __name__ == "__main__":
    unittest.main()
