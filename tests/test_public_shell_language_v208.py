from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_public_shell_language_v208.py"

spec = importlib.util.spec_from_file_location("public_shell_language_v208", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def write_page(root: Path, relative: str, body: str, *, header: bool = True, footer: bool = True) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    shell_header = '<header><nav aria-label="الرئيسية"></nav></header>' if header else ""
    shell_footer = '<footer><p>منصة روافد</p></footer>' if footer else ""
    path.write_text(
        f'<!doctype html><html lang="ar" dir="rtl"><body>{shell_header}<main><h1>اختبار</h1>{body}</main>{shell_footer}</body></html>',
        encoding="utf-8",
    )
    return path


class PublicShellLanguageV208Tests(unittest.TestCase):
    def test_clean_pages_pass_with_preferred_and_scientific_terms(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            write_page(
                site,
                "index.html",
                "<p>خدمات للأشخاص ذوي الاحتياجات الخاصة، مع شرح علمي لمفهوم الإعاقة عند الحاجة.</p>",
            )
            write_page(site, "special-needs/index.html", "<p>تربية دامجة ودعم عملي.</p>")
            report = module.audit_site(site)
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["pages_scanned"], 2)
            self.assertEqual(report["prohibited_person_label_occurrences"], 0)
            self.assertEqual(report["missing_header_pages"], 0)
            self.assertEqual(report["missing_footer_pages"], 0)

    def test_all_prohibited_person_label_forms_are_detected(self):
        forms = ["معاق", "معاقة", "معاقون", "معاقين", "المعاق", "المعاقة", "المعاقون", "المعاقين"]
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            write_page(site, "index.html", "<p>" + "، ".join(forms) + "</p>")
            report = module.audit_site(site)
            self.assertEqual(report["status"], "fail")
            self.assertEqual(report["prohibited_person_label_pages"], 1)
            self.assertEqual(report["prohibited_person_label_occurrences"], len(forms))
            prohibited = [item for item in report["findings"] if item["kind"] == "prohibited-person-label"]
            self.assertEqual(len(prohibited), len(forms))
            self.assertTrue(all(item["path"] == "index.html" for item in prohibited))

    def test_missing_header_and_footer_are_reported_independently(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            write_page(site, "missing-header/index.html", "<p>محتوى</p>", header=False)
            write_page(site, "missing-footer/index.html", "<p>محتوى</p>", footer=False)
            report = module.audit_site(site)
            self.assertEqual(report["status"], "fail")
            self.assertEqual(report["missing_header"], ["missing-header/index.html"])
            self.assertEqual(report["missing_footer"], ["missing-footer/index.html"])

    def test_root_verification_artifact_is_excluded_without_weakening_nested_pages(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            (site / "google123.html").write_text(
                "google-site-verification: google123.html",
                encoding="utf-8",
            )
            write_page(site, "index.html", "<p>صفحة كاملة</p>")
            nested = site / "nested/google123.html"
            nested.parent.mkdir(parents=True)
            nested.write_text("google-site-verification: google123.html", encoding="utf-8")
            report = module.audit_site(site)
            self.assertEqual(report["excluded_verification_artifacts"], 1)
            self.assertEqual(report["pages_scanned"], 2)
            self.assertIn("nested/google123.html", report["missing_header"])
            self.assertIn("nested/google123.html", report["missing_footer"])

    def test_report_is_written_as_utf8_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            write_page(site, "index.html", "<p>ذوو الاحتياجات الخاصة</p>")
            report = module.audit_site(site)
            output = module.write_report(site, report)
            loaded = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(output, site / "api/public-shell-language-v208.json")
            self.assertEqual(loaded["status"], "pass")
            self.assertEqual(loaded["policy"]["preferred_platform_term"], "ذوو الاحتياجات الخاصة")


if __name__ == "__main__":
    unittest.main()
