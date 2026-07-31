from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDITOR = ROOT / "scripts" / "audit_content_quality_v32.py"


class ContentQualityDiagnosticsV313Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="content-quality-v313-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))

    def write_page(
        self,
        route: str,
        *,
        title: str,
        description: str,
        h1: str,
        robots: str = "index,follow",
    ) -> None:
        path = self.site / route / "index.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        canonical_route = f"{route}/" if route else ""
        path.write_text(
            "<!doctype html><html lang=\"ar\" dir=\"rtl\"><head>"
            f"<title>{title}</title>"
            f"<meta name=\"description\" content=\"{description}\">"
            f"<meta name=\"robots\" content=\"{robots}\">"
            f"<link rel=\"canonical\" href=\"https://healthrenewal.org/{canonical_route}\">"
            f"<meta property=\"og:title\" content=\"{title}\">"
            f"<meta property=\"og:description\" content=\"{description}\">"
            "<meta name=\"twitter:card\" content=\"summary\">"
            "<script type=\"application/ld+json\">{}</script>"
            "</head><body>"
            f"<h1>{h1}</h1>"
            "<p>هذه صفحة اختبار تحتوي كلمات عربية كافية للتحقق من التقرير ومساراته الدقيقة دون إنشاء خطأ حرج.</p>"
            "<a href=\"../\">رابط داخلي أول</a><a href=\"../../\">رابط داخلي ثان</a>"
            "</body></html>",
            encoding="utf-8",
        )

    def test_duplicate_groups_include_every_path_and_preserve_unique_values(self) -> None:
        duplicate_title = "عنوان عربي مكرر | المنصة"
        duplicate_description = "وصف عربي مؤسسي مكرر يشرح الغرض من الصفحة وحدودها بطريقة واضحة ومناسبة للفهرسة."
        self.write_page("alpha", title=duplicate_title, description=duplicate_description, h1="الصفحة ألف")
        self.write_page("beta", title=duplicate_title, description=duplicate_description, h1="الصفحة باء")
        self.write_page(
            "gamma",
            title="عنوان فريد | المنصة",
            description="وصف فريد لصفحة مستقلة يختلف عن بقية الصفحات ويثبت عدم إدخاله في مجموعات التكرار.",
            h1="الصفحة جيم",
        )

        result = subprocess.run(
            ["python", str(AUDITOR), str(self.site)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

        report = json.loads(
            (self.site / "api" / "content-quality-v32.json").read_text(encoding="utf-8")
        )
        self.assertEqual(report["version"], "32-content-quality")
        self.assertEqual(report["diagnostic_contract_version"], 313)
        self.assertEqual(report["duplicate_title_values"], 1)
        self.assertEqual(report["duplicate_description_values"], 1)

        title_group = report["duplicate_title_groups"][0]
        self.assertEqual(title_group["value"], duplicate_title)
        self.assertEqual(title_group["count"], 2)
        self.assertEqual(title_group["path_count"], 2)
        self.assertEqual(title_group["paths"], ["alpha/index.html", "beta/index.html"])

        description_group = report["duplicate_description_groups"][0]
        self.assertEqual(description_group["value"], duplicate_description)
        self.assertEqual(description_group["paths"], ["alpha/index.html", "beta/index.html"])

        duplicate_warnings = [
            warning for warning in report["warnings"] if warning.startswith("Duplicate")
        ]
        self.assertTrue(any("alpha/index.html" in warning and "beta/index.html" in warning for warning in duplicate_warnings))
        self.assertFalse(any("gamma/index.html" in warning for warning in duplicate_warnings))

    def test_noindex_alias_is_excluded_from_depth_and_duplicate_metrics(self) -> None:
        for route in ("legacy-one", "legacy-two"):
            self.write_page(
                route,
                title="تم تحديث المسار",
                description="تحويل داخلي إلى المسار الحالي.",
                h1="تم تحديث هذا المسار",
                robots="noindex,follow",
            )
        self.write_page(
            "current",
            title="المسار الحالي",
            description="مسار حالي غني ومستقل يظل داخل تقرير جودة المحتوى المنشور.",
            h1="المسار الحالي",
        )

        result = subprocess.run(
            ["python", str(AUDITOR), str(self.site)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        report = json.loads(
            (self.site / "api" / "content-quality-v32.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(report["html_files_seen"], 3)
        self.assertEqual(report["noindex_pages_skipped"], 2)
        self.assertEqual(report["pages_scanned"], 1)
        self.assertEqual(report["duplicate_title_values"], 0)
        self.assertFalse(
            any("legacy-" in warning for warning in report["warnings"])
        )


if __name__ == "__main__":
    unittest.main()
