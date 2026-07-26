from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_core_sections_v15.py"
REQUIRED = (
    "متى يفيد هذا الدليل؟",
    "خطة التنفيذ خطوة بخطوة",
    "جملة جاهزة للاستخدام",
    "ما الذي يجب تجنبه؟",
    "كيف تعرف أن الخطة تتحسن؟",
    "متى تحتاج إلى مساعدة؟",
    "مصادر موثوقة للتوسع",
)


class VerifyCoreSectionsV244Tests(unittest.TestCase):
    def make_site(self, root: Path, *, upgraded: bool) -> Path:
        site = root / "site"
        (site / "api").mkdir(parents=True)
        (site / "assets/js").mkdir(parents=True)
        (site / "tips").mkdir(parents=True)
        (site / "assessment-lab").mkdir(parents=True)
        (site / "cognitive-lab").mkdir(parents=True)

        (site / "api/core-sections-v15.json").write_text(
            json.dumps(
                {
                    "tips_guides": 20,
                    "assessment_pages": 40,
                    "cognitive_pages": 48,
                }
            ),
            encoding="utf-8",
        )
        if upgraded:
            (site / "api/practical-tips-v237.json").write_text(
                json.dumps(
                    {
                        "version": 237,
                        "status": "passed",
                        "guide_count": 100,
                        "preserved_existing_guides": 20,
                        "new_guides": 80,
                        "pillar_count": 10,
                        "category_count": 29,
                        "minimum_after_words": 812,
                        "remaining_below_minimum": 0,
                        "missing_or_failed": 0,
                        "duplicate_slugs": 0,
                        "duplicate_titles": 0,
                        "sitemap_urls": 111,
                        "core_sections_compatibility": "passed",
                        "compatibility_pages": 100,
                        "unique_titles": 100,
                        "unique_descriptions": 100,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

        runtime = "\n".join(
            (
                "__PTERMINOLOGY_LAB_V15__",
                "answer=target.value",
                "showAssessmentResult cognitiveResult",
                "maxAnswered",
                "أجب عن ${missing.length}",
                "globalThis.__PTERMINOLOGY_LAB_V15__",
            )
        )
        (site / "assets/js/lab-v12.js").write_text(runtime, encoding="utf-8")
        (site / "sw.js").write_text(
            "pterminology-v23-resilient-core Promise.allSettled cached===0",
            encoding="utf-8",
        )

        page_count = 100 if upgraded else 20
        step_class = "tip237-step" if upgraded else "tips-v15__step"
        filler = "محتوى عربي عملي واضح يحفظ الكرامة ويشرح السياق والخطوات والمتابعة. " * 40
        for index in range(page_count):
            page = site / "tips" / f"guide-{index:03d}" / "index.html"
            page.parent.mkdir(parents=True)
            steps = "".join(
                f'<section class="{step_class}"><h3>{step}</h3><p>{filler}</p></section>'
                for step in range(1, 7)
            )
            page.write_text(
                "<!doctype html><html lang=\"ar\" dir=\"rtl\"><head>"
                f"<title>عنوان فريد {index}</title>"
                f'<meta name="description" content="وصف فريد للدليل {index}">'
                '<script type="application/ld+json">{"@type":"HowTo"}</script>'
                "</head><body><main><h1>دليل</h1>"
                + "".join(f"<h2>{marker}</h2><p>{filler}</p>" for marker in REQUIRED)
                + steps
                + "</main></body></html>",
                encoding="utf-8",
            )

        definition_template = (
            '<script type="application/json" id="lab-definition">'
            '{{"slug":"{slug}","title":"{title}"}}</script>'
            '<script src="lab-v12.js?v=15"></script>'
            '<link rel="stylesheet" href="core-v15.css">'
        )
        for root_name, count in (("assessment-lab", 40), ("cognitive-lab", 48)):
            for index in range(count):
                page = site / root_name / f"tool-{index:03d}" / "index.html"
                page.parent.mkdir(parents=True)
                page.write_text(
                    definition_template.format(
                        slug=f"{root_name}-{index}",
                        title=f"أداة {index}",
                    ),
                    encoding="utf-8",
                )

        sitemap_count = 111 if upgraded else 21
        namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
        urlset = ET.Element(f"{{{namespace}}}urlset")
        for index in range(sitemap_count):
            url = ET.SubElement(urlset, f"{{{namespace}}}url")
            ET.SubElement(url, f"{{{namespace}}}loc").text = (
                f"https://example.test/tips/item-{index}/"
            )
        ET.ElementTree(urlset).write(
            site / "sitemap-tips.xml",
            encoding="utf-8",
            xml_declaration=True,
        )
        return site

    def run_verifier(self, site: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(site)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_v237_hundred_guide_contract_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site = self.make_site(Path(temporary_directory), upgraded=True)
            completed = self.run_verifier(site)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            report = json.loads(
                (site / "api/core-sections-audit-v15.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["tips_contract_version"], 237)
            self.assertEqual(report["tips_pages"], 100)
            self.assertEqual(report["tips_sitemap_urls"], 111)
            self.assertEqual(report["unique_tip_titles"], 100)
            self.assertEqual(report["unique_tip_descriptions"], 100)
            self.assertEqual(report["errors"], [])

    def test_legacy_twenty_guide_contract_remains_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site = self.make_site(Path(temporary_directory), upgraded=False)
            completed = self.run_verifier(site)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            report = json.loads(
                (site / "api/core-sections-audit-v15.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["tips_contract_version"], 15)
            self.assertEqual(report["tips_pages"], 20)
            self.assertEqual(report["tips_sitemap_urls"], 21)
            self.assertEqual(report["errors"], [])


if __name__ == "__main__":
    unittest.main()
