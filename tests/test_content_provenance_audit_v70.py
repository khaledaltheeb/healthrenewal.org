import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_content_provenance_v70.py"


def page(*, title="Page", h1="Heading", canonical="https://healthrenewal.org/", body="", json_ld=None):
    ld = ""
    if json_ld is not None:
        ld = f'<script type="application/ld+json">{json_ld}</script>'
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><title>{title}</title><meta name="description" content="Description"><link rel="canonical" href="{canonical}">{ld}</head><body><h1>{h1}</h1>{body}</body></html>'''


class ContentProvenanceAuditTests(unittest.TestCase):
    def run_audit(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            for rel, content in files.items():
                path = site / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            result = subprocess.run(
                ["python", str(SCRIPT), str(site)],
                text=True,
                capture_output=True,
                check=False,
            )
            report_path = site / "api" / "content-provenance-v70.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            return result, report

    def test_valid_root_and_sensitive_page_pass_structural_contract(self):
        files = {
            "index.html": page(),
            "encyclopedia/anxiety/index.html": page(
                title="القلق",
                h1="القلق",
                canonical="https://healthrenewal.org/encyclopedia/anxiety/",
                body='<h2>المصادر</h2><p>آخر مراجعة: 2026-07-22</p><a href="https://www.who.int/">WHO</a>',
                json_ld='{"@context":"https://schema.org","@type":"Article","dateModified":"2026-07-22","citation":"https://www.who.int/"}',
            ),
        }
        result, report = self.run_audit(files)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(report["critical_error_count"], 0)
        self.assertEqual(report["sensitive_pages"], 1)
        self.assertEqual(report["sensitive_pages_with_review_evidence"], 1)
        self.assertEqual(report["sensitive_pages_with_source_evidence"], 1)

    def test_multiple_h1_and_wrong_canonical_fail(self):
        invalid = page(
            canonical="https://example.com/wrong/",
            body="<h1>Second heading</h1>",
        )
        result, report = self.run_audit({"index.html": invalid})
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["critical_error_count"], 2)
        self.assertTrue(any("Expected exactly one H1" in item for item in report["critical_errors"]))
        self.assertTrue(any("Invalid canonical" in item for item in report["critical_errors"]))

    def test_invalid_json_ld_fails(self):
        result, report = self.run_audit({"index.html": page(json_ld="{not-json}")})
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any("Invalid JSON-LD" in item for item in report["critical_errors"]))

    def test_sensitive_missing_provenance_is_measured_not_hidden(self):
        result, report = self.run_audit({
            "care-guides/example/index.html": page(
                canonical="https://healthrenewal.org/care-guides/example/"
            )
        })
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["warning_count"], 2)
        self.assertEqual(report["sensitive_pages_with_review_evidence"], 0)
        self.assertEqual(report["sensitive_pages_with_source_evidence"], 0)
        self.assertEqual(len(report["weak_provenance_pages"]), 1)

    def test_verification_file_is_skipped(self):
        result, report = self.run_audit({
            "google-check.html": "google-site-verification: google-check.html",
            "index.html": page(),
        })
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["pages_scanned"], 1)


if __name__ == "__main__":
    unittest.main()
