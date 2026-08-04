from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import generate_sitemap_index_v304 as sitemap  # noqa: E402
import normalize_rawafid_production_v1 as rawafid  # noqa: E402


class RecoveredContentPublicationTests(unittest.TestCase):
    def test_recovery_runs_only_for_production_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "_site"
            root.mkdir()
            repo = Path(temporary) / "repo"
            repo.mkdir()
            special = {
                "status": "passed",
                "condition_count": 3,
                "generated_pages": ["cluster", "one", "two", "three"],
                "external_clinical_review_completed": False,
            }
            women = {
                "status": "passed",
                "page_count": 30,
                "hub_count": 2,
                "external_specialist_review_completed": False,
            }
            with patch.object(sitemap.special_needs_v323, "publish", return_value=special) as first, patch.object(
                sitemap.women_youth_v406, "publish", return_value=women
            ) as second:
                report = sitemap.recover_previously_published_content(root, repo)
            self.assertEqual(report["status"], "published")
            self.assertEqual(report["publishers"]["special_needs_v323"]["condition_count"], 3)
            self.assertEqual(report["publishers"]["women_youth_v406"]["page_count"], 30)
            first.assert_called_once_with(root)
            second.assert_called_once_with(root)

    def test_source_checkout_is_never_materialized(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(sitemap.special_needs_v323, "publish") as first, patch.object(
                sitemap.women_youth_v406, "publish"
            ) as second:
                report = sitemap.recover_previously_published_content(root, root)
            self.assertEqual(report["status"], "skipped-non-production-artifact")
            first.assert_not_called()
            second.assert_not_called()

    def test_rawafid_normalizer_removes_retired_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "assets/brand").mkdir(parents=True)
            required = (
                "assets/brand/logo-mark.svg",
                "assets/brand/logo-lockup.svg",
                "assets/brand/rawafid-brand.css",
                "assets/brand/rawafid-brand.js",
                "assets/brand/rawafid-social-card.jpg",
                "favicon.ico",
                "favicon-16x16.png",
                "favicon-32x32.png",
                "apple-touch-icon.png",
                "android-chrome-192x192.png",
                "android-chrome-512x512.png",
            )
            for relative in required:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"asset")
            (root / "manifest.webmanifest").write_text(
                json.dumps({"name": "Health Renewal", "short_name": "Health Renewal"}),
                encoding="utf-8",
            )
            (root / "index.html").write_text(
                "<!doctype html><html lang='ar'><head><title>Health Renewal</title>"
                "<meta property='og:image' content='https://healthrenewal.org/assets/brand/rawafid-social-card.jpg'>"
                "</head><body><img src='/assets/brand/logo-mark.svg' alt='شعار منصة روافد'>"
                "<h1>Health Renewal</h1><p>للعافية النفسية والدمج والتمكين</p></body></html>",
                encoding="utf-8",
            )
            report = rawafid.normalize(root)
            page = (root / "index.html").read_text(encoding="utf-8")
            self.assertEqual(report["status"], "passed")
            self.assertNotIn("Health Renewal", page)
            self.assertIn("منصة روافد", page)
            self.assertEqual(page.count("rawafid-brand.css"), 1)
            self.assertEqual(page.count("rawafid-brand.js"), 1)
            self.assertTrue((root / "api/rawafid-production-normalization-v1.json").is_file())

    def test_canonical_generator_contains_recovery_and_identity_gates(self) -> None:
        source = (SCRIPTS / "generate_sitemap_index_v304.py").read_text(encoding="utf-8")
        for marker in (
            "recover_previously_published_content(root, repo_root)",
            "normalize_production_identity(root, repo_root)",
            "publish_new_special_needs_conditions_v323",
            "publish_women_youth_v406",
            'report["recovered_previously_published_content"]',
            'report["rawafid_production_identity"]',
        ):
            self.assertIn(marker, source)


if __name__ == "__main__":
    unittest.main()
