from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.verify_homepage_release_contract_v230 import (
    FORBIDDEN_MARKERS,
    INSTITUTIONAL_NAME,
    REQUIRED_HREFS,
    inspect_html,
    verify,
)


def valid_html() -> str:
    links = "".join(f'<a href="{href}">{href}</a>' for href in REQUIRED_HREFS)
    return f'''<!doctype html><html lang="ar" dir="rtl"><head>
<title>{INSTITUTIONAL_NAME} | موسوعة ومكتبة عربية</title>
<meta name="description" content="وصف مؤسسي موثق">
<meta name="robots" content="index,follow,max-snippet:-1">
<link rel="canonical" href="https://example.test/">
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Organization","name":"{INSTITUTIONAL_NAME}"}}</script>
</head><body><strong>2,000+</strong><strong>93</strong>{links}</body></html>'''


class HomepageReleaseContractV230Tests(unittest.TestCase):
    def test_current_contract_passes(self) -> None:
        report = inspect_html(valid_html())
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["missing_gateways"], [])

    def test_each_gateway_is_required(self) -> None:
        for href in REQUIRED_HREFS:
            with self.subTest(href=href):
                report = inspect_html(valid_html().replace(f'href="{href}"', 'href="missing/"'))
                self.assertEqual(report["status"], "failed")
                self.assertIn(href, report["missing_gateways"])

    def test_legacy_markers_are_rejected(self) -> None:
        for marker in FORBIDDEN_MARKERS:
            with self.subTest(marker=marker):
                report = inspect_html(valid_html().replace("</body>", marker + "</body>"))
                self.assertEqual(report["status"], "failed")
                self.assertIn(marker, report["forbidden_markers_found"])

    def test_old_brand_title_is_rejected(self) -> None:
        report = inspect_html(valid_html().replace(
            f"<title>{INSTITUTIONAL_NAME}", "<title>مصطلحات علم النفس"
        ))
        self.assertEqual(report["status"], "failed")
        self.assertIn("institutional title is missing", report["errors"])

    def test_duplicate_primary_metadata_is_rejected(self) -> None:
        html = valid_html().replace(
            "</head>", '<meta name="description" content="مكرر"></head>'
        )
        report = inspect_html(html)
        self.assertEqual(report["status"], "failed")
        self.assertIn("homepage must contain exactly one meta description", report["errors"])

    def test_report_is_written_only_after_real_file_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            homepage = root / "index.html"
            report_path = root / "api/homepage-release-v230.json"
            homepage.write_text(valid_html(), encoding="utf-8")
            report = verify(homepage, report_path)
            self.assertEqual(report["status"], "passed")
            self.assertTrue(report_path.is_file())


if __name__ == "__main__":
    unittest.main()
