from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "verify_live_special_needs_publication_v1.py"
SPEC = importlib.util.spec_from_file_location("verify_live_special_needs_publication_v1", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class VerifyLiveSpecialNeedsPublicationTests(unittest.TestCase):
    def complete_payload(self) -> dict[str, object]:
        return {
            "status": "passed",
            "counts": dict(MODULE.MINIMUM_COUNTS),
            "missingRoots": [],
            "pageIssues": {},
            "sitemapMissingRoutes": [],
            "targetRouteCount": 2,
            "routes": {
                "capability_pages": ["/capabilities/", "/capabilities/autism/"],
                "special_needs_practical_guides": [
                    "/special-needs/practical/functional-communication-profile/"
                ],
            },
        }

    def test_complete_inventory_passes(self) -> None:
        self.assertEqual(MODULE.validate_inventory(self.complete_payload()), [])

    def test_underfilled_family_fails_closed(self) -> None:
        payload = self.complete_payload()
        counts = dict(payload["counts"])
        counts["special_needs_practical_guides"] = 59
        payload["counts"] = counts
        self.assertIn(
            "special_needs_practical_guides: 59 < 60",
            MODULE.validate_inventory(payload),
        )

    def test_inventory_routes_include_required_roots_and_are_unique(self) -> None:
        payload = self.complete_payload()
        routes = MODULE.inventory_routes(payload)
        self.assertEqual(routes, sorted(set(routes)))
        for route in MODULE.REQUIRED_ROOT_ROUTES:
            self.assertIn(route, routes)
        self.assertIn("/capabilities/autism/", routes)

    def test_inventory_routes_reject_malformed_routes(self) -> None:
        payload = self.complete_payload()
        payload["routes"] = {"bad": ["capabilities/autism"]}
        with self.assertRaises(ValueError):
            MODULE.inventory_routes(payload)

    def test_cache_buster_preserves_existing_query(self) -> None:
        value = MODULE.cache_busted("https://example.org/path/?a=1", "nonce")
        self.assertIn("a=1", value)
        self.assertIn("publication-proof=nonce", value)

    def test_intentional_noindex_alias_with_redirect_passes(self) -> None:
        body = b'''<!doctype html><html><head>
<meta name="robots" content="noindex,follow">
<link rel="canonical" href="https://healthrenewal.org/learning-paths/new-path/">
<meta http-equiv="refresh" content="0;url=/learning-paths/new-path/">
</head><body><h1>Moved</h1></body></html>'''
        result = MODULE.FetchResult(
            url="https://healthrenewal.org/learning-paths/old-path/",
            status=200,
            body=body,
            content_type="text/html; charset=utf-8",
        )
        with patch.object(MODULE, "fetch", return_value=result):
            failure = MODULE.validate_live_page(
                "https://healthrenewal.org",
                "/learning-paths/old-path/",
                timeout=1,
                retries=1,
            )
        self.assertIsNone(failure)

    def test_noindex_canonical_mismatch_without_redirect_still_fails(self) -> None:
        body = b'''<!doctype html><html><head>
<meta name="robots" content="noindex,follow">
<link rel="canonical" href="https://healthrenewal.org/learning-paths/other-path/">
</head><body><h1>Page</h1></body></html>'''
        result = MODULE.FetchResult(
            url="https://healthrenewal.org/learning-paths/broken-path/",
            status=200,
            body=body,
            content_type="text/html; charset=utf-8",
        )
        with patch.object(MODULE, "fetch", return_value=result):
            failure = MODULE.validate_live_page(
                "https://healthrenewal.org",
                "/learning-paths/broken-path/",
                timeout=1,
                retries=1,
            )
        self.assertIsNotNone(failure)
        assert failure is not None
        self.assertIn("noindex", failure["problems"])
        self.assertTrue(any(problem.startswith("canonical mismatch") for problem in failure["problems"]))


if __name__ == "__main__":
    unittest.main()
