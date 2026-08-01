#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AiSearchRouteDeploymentGuardTests(unittest.TestCase):
    def test_ai_search_surface_exists(self) -> None:
        required = (
            "ai-search/index.html",
            "ai-search/assets/app.js",
            "ai-search/assets/search-core.js",
            "ai-search/assets/search-worker.js",
            "ai-search/assets/search.css",
            "ai-search/data/manifest.json",
            "ai-search/data/coverage.json",
        )
        for relative in required:
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_complete_pages_workflow_protects_route(self) -> None:
        workflow = ROOT / ".github/workflows/deploy-complete-pages-with-ai-search.yml"
        source = workflow.read_text(encoding="utf-8")
        self.assertIn("cp", source)
        self.assertIn("ai-search/index.html", source)
        self.assertIn("https://healthrenewal.org/ai-search/", source)
        self.assertIn("actions/deploy-pages@v4", source)
        self.assertIn("schedule:", source)
        self.assertIn("github-pages-production", source)

    def test_retired_partial_publisher_is_absent(self) -> None:
        self.assertFalse(
            (ROOT / ".github/workflows/publish-women-youth-v406-on-issue.yml").exists()
        )


if __name__ == "__main__":
    unittest.main()
