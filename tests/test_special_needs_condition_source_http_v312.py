from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_special_needs_condition_source_http_v312 as http312


class SpecialNeedsConditionSourceHTTPV312Tests(unittest.TestCase):
    def attempt(
        self,
        method: str,
        status: int | None,
        final_url: str | None = "https://example.org/source",
        error: str | None = None,
    ) -> http312.Attempt:
        return http312.Attempt(
            method=method,
            status=status,
            final_url=final_url,
            content_type="text/html" if status else None,
            elapsed_ms=10,
            error=error,
        )

    def test_real_source_manifest_contains_seventeen_unique_https_sources_and_applies_override(self) -> None:
        rows = http312.load_sources()
        self.assertEqual(len(rows), 17)
        self.assertEqual({row["condition"] for row in rows}, {"autism", "down-syndrome"})
        self.assertEqual(len({row["source_id"] for row in rows}), 17)
        self.assertTrue(all(row["url"].startswith("https://") for row in rows))
        by_id = {row["source_id"]: row for row in rows}
        self.assertEqual(
            by_id["A9"]["url"],
            "https://apps.asha.org/EvidenceMaps/Maps/LandingPage/990772a6-9cd8-4203-a76c-6ccd91eac874",
        )
        self.assertEqual(
            by_id["A9"]["title"],
            "Augmentative and Alternative Communication (AAC) Evidence Map",
        )
        self.assertEqual(len(http312.load_url_overrides()), 1)

    def test_official_subdomain_is_allowed_but_external_domain_is_rejected(self) -> None:
        original = "https://www.asha.org/Practice-Portal/Professional-Issues/Augmentative-and-Alternative-Communication/"
        official = "https://apps.asha.org/EvidenceMaps/Maps/LandingPage/example"
        external = "https://asha.example.org/aac"
        self.assertTrue(http312.is_organization_domain("ASHA", original, official))
        self.assertFalse(http312.is_organization_domain("ASHA", original, external))
        self.assertFalse(http312.is_organization_domain("Other", original, official))

    def test_successful_response_is_reachable(self) -> None:
        result = http312.classify_attempts([self.attempt("HEAD", 200)])
        self.assertEqual(result, ("reachable", False, "http-200"))

    def test_redirect_to_https_is_reachable(self) -> None:
        result = http312.classify_attempts(
            [self.attempt("HEAD", 301, "https://www.example.org/final")]
        )
        self.assertEqual(result, ("reachable", False, "http-301"))

    def test_redirect_to_http_is_blocking(self) -> None:
        result = http312.classify_attempts(
            [self.attempt("HEAD", 301, "http://example.org/final")]
        )
        self.assertTrue(result[1])
        self.assertEqual(result[0], "insecure-redirect")

    def test_confirmed_not_found_is_blocking(self) -> None:
        result = http312.classify_attempts(
            [self.attempt("HEAD", 404), self.attempt("GET", 404)]
        )
        self.assertEqual(result, ("broken", True, "http-404"))

    def test_bot_restriction_is_reported_but_not_blocking(self) -> None:
        result = http312.classify_attempts(
            [self.attempt("HEAD", 403), self.attempt("GET", 403)]
        )
        self.assertEqual(result, ("access-restricted", False, "http-403"))

    def test_legal_restriction_is_separate_and_non_blocking(self) -> None:
        result = http312.classify_attempts(
            [self.attempt("HEAD", 451), self.attempt("GET", 451)]
        )
        self.assertEqual(result, ("legally-restricted", False, "http-451"))

    def test_timeout_is_indeterminate_not_false_broken(self) -> None:
        result = http312.classify_attempts(
            [
                self.attempt("HEAD", None, None, "TimeoutError: timed out"),
                self.attempt("GET", None, None, "TimeoutError: timed out"),
            ]
        )
        self.assertEqual(result[0], "transport-indeterminate")
        self.assertFalse(result[1])


if __name__ == "__main__":
    unittest.main()
