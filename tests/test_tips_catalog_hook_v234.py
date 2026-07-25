#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
BASE = "https://khaledaltheeb.github.io/pterminology-site/"


class TipsCatalogHookV234Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        sys.path.insert(0, str(SCRIPTS))
        spec = importlib.util.spec_from_file_location(
            "publish_content_catalog_v219_under_test",
            SCRIPTS / "publish_content_catalog_v219.py",
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("Cannot load production catalog publisher")
        cls.catalog = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.catalog)

    def fixture(self, include_homepage_marker: bool) -> Path:
        site = Path(tempfile.mkdtemp(prefix="tips-catalog-v234-"))
        (site / "assets").mkdir(parents=True)
        (site / "tips").mkdir(parents=True)
        (site / "api").mkdir(parents=True)
        (site / "robots.txt").write_text(
            "User-agent: *\nAllow: /\nSitemap: " + BASE + "sitemap.xml\n",
            encoding="utf-8",
        )
        (site / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>',
            encoding="utf-8",
        )
        (site / "api/core-sections-v15.json").write_text(
            json.dumps({"version": 15, "tips_guides": 20}),
            encoding="utf-8",
        )
        if include_homepage_marker:
            (site / "api/homepage-v20.json").write_text(
                json.dumps({"version": 219}),
                encoding="utf-8",
            )
        return site

    def test_production_markers_publish_and_verify_v234(self) -> None:
        site = self.fixture(include_homepage_marker=True)
        original_site = self.catalog.SITE
        try:
            self.catalog.SITE = site
            self.assertTrue(self.catalog.publish_tips_v234_when_production_ready())
        finally:
            self.catalog.SITE = original_site

        verification = json.loads(
            (site / "api/tips-verification-v234.json").read_text(encoding="utf-8")
        )
        self.assertEqual(verification["status"], "passed")
        self.assertEqual(verification["pages"], 49)
        self.assertEqual(len(list((site / "tips").rglob("index.html"))), 49)

    def test_focused_fixture_does_not_publish_without_homepage_marker(self) -> None:
        site = self.fixture(include_homepage_marker=False)
        original_site = self.catalog.SITE
        try:
            self.catalog.SITE = site
            self.assertFalse(self.catalog.publish_tips_v234_when_production_ready())
        finally:
            self.catalog.SITE = original_site
        self.assertFalse((site / "api/tips-verification-v234.json").exists())


if __name__ == "__main__":
    unittest.main()
