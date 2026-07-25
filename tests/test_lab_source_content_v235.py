from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPAND = ROOT / "scripts" / "expand_v12_direct.py"
LEGACY = ROOT / "scripts" / "enrich_lab_content_v193.py"
ADVANCED = ROOT / "scripts" / "deepen_assessment_cognitive_hubs_v233.py"
ORIGIN = ROOT / "scripts" / "audit_source_origin_depth_v234.py"


class VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack.append(tag.lower())

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if not any(tag in self.stack for tag in ("script", "style", "svg", "template", "noscript")):
            self.parts.append(data)

    @property
    def words(self) -> int:
        return len(re.findall(r"[\w\u0600-\u06ff]+", " ".join(self.parts)))


def word_count(path: Path) -> int:
    parser = VisibleText()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.words


def digest(paths: list[Path]) -> dict[str, str]:
    return {
        path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


class LabSourceContentV235Tests(unittest.TestCase):
    def build(self, site: Path) -> tuple[list[Path], list[Path]]:
        env = {**os.environ, "SITE_BASE": "https://khaledaltheeb.github.io/pterminology-site/"}
        subprocess.run([sys.executable, str(EXPAND), str(site)], cwd=ROOT, env=env, check=True)
        assessment = sorted((site / "assessment-lab").glob("*/index.html"))
        cognitive = sorted((site / "cognitive-lab").glob("*/index.html"))
        return assessment, cognitive

    def test_builds_all_pages_at_source_depth_without_post_build_markers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary) / "site"
            assessment, cognitive = self.build(site)
            self.assertEqual(len(assessment), 40)
            self.assertEqual(len(cognitive), 48)

            for kind, minimum, pages in (
                ("assessment", 750, assessment),
                ("cognitive", 700, cognitive),
            ):
                for page in pages:
                    source = page.read_text(encoding="utf-8")
                    self.assertEqual(source.count(f'data-lab-source-v235="{kind}"'), 1, page)
                    self.assertNotIn("lab-depth-v193:head:start", source, page)
                    self.assertNotIn("lab-depth-v193:body:start", source, page)
                    self.assertNotIn("advanced-content-depth-v233:start", source, page)
                    self.assertIn('name="twitter:title"', source, page)
                    self.assertIn('name="twitter:description"', source, page)
                    self.assertIn('"@type": "FAQPage"', source, page)
                    self.assertIn("/pterminology-site/privacy/", source, page)
                    self.assertGreaterEqual(word_count(page), minimum, page)

            report = json.loads((site / "api" / "build-report-v12.json").read_text(encoding="utf-8"))
            self.assertEqual(report["lab_source_content_version"], 235)
            self.assertEqual(report["source_integrated_assessment_pages"], 40)
            self.assertEqual(report["source_integrated_cognitive_pages"], 48)

    def test_legacy_and_advanced_publishers_leave_source_pages_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary) / "site"
            assessment, cognitive = self.build(site)
            pages = assessment + cognitive
            before = digest(pages)

            subprocess.run([sys.executable, str(LEGACY), str(site)], cwd=ROOT, check=True)
            after_legacy = digest(pages)
            self.assertEqual(before, after_legacy)
            legacy_report = json.loads((site / "api" / "lab-depth-v193.json").read_text(encoding="utf-8"))
            self.assertEqual(legacy_report["source_integrated_pages"], 88)
            self.assertEqual(legacy_report["fallback_pages_enriched"], 0)

            subprocess.run([sys.executable, str(ADVANCED), str(site)], cwd=ROOT, check=True)
            after_advanced = digest(pages)
            self.assertEqual(before, after_advanced)
            advanced = json.loads((site / "api" / "advanced-content-depth-v233.json").read_text(encoding="utf-8"))
            child_rows = [
                row for row in advanced["pages"]
                if (
                    row["path"].startswith("assessment-lab/")
                    or row["path"].startswith("cognitive-lab/")
                )
                and row["path"].count("/") == 2
            ]
            self.assertEqual(len(child_rows), 88)
            self.assertTrue(all(row["status"] == "sufficient" for row in child_rows), child_rows[:5])

    def test_origin_audit_does_not_classify_lab_children_as_generated_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary) / "site"
            assessment, cognitive = self.build(site)
            subprocess.run([sys.executable, str(LEGACY), str(site)], cwd=ROOT, check=True)
            subprocess.run([sys.executable, str(ADVANCED), str(site)], cwd=ROOT, check=True)
            subprocess.run(
                [sys.executable, str(ORIGIN), str(site), "--repository", str(ROOT), "--fail-on-malformed"],
                cwd=ROOT,
                check=True,
            )
            origin = json.loads((site / "api" / "source-origin-depth-v234.json").read_text(encoding="utf-8"))
            child_routes = {
                "/" + page.relative_to(site).parent.as_posix() + "/"
                for page in assessment + cognitive
            }
            dependency_routes = {row["route"] for row in origin["dependencies"]}
            self.assertTrue(child_routes.isdisjoint(dependency_routes))
            self.assertEqual(origin["malformed_marker_count"], 0)

    def test_source_copy_retains_safety_and_methodological_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary) / "site"
            assessment, cognitive = self.build(site)
            phq = (site / "assessment-lab" / "phq-9-plus" / "index.html").read_text(encoding="utf-8")
            cognitive_text = cognitive[0].read_text(encoding="utf-8")
            monitor = (site / "assessment-lab" / "mood-daily" / "index.html").read_text(encoding="utf-8")
            self.assertIn("تنبيه أمان مهم", phq)
            self.assertIn("خدمات الطوارئ المحلية", phq)
            self.assertIn("لا تستخدم عينة معيارية", monitor)
            self.assertIn("ليست اختبار ذكاء", cognitive_text)
            self.assertIn("لا يثبت تلقائيًا", cognitive_text)
            combined = "\n".join(page.read_text(encoding="utf-8") for page in assessment + cognitive)
            for forbidden in (
                "يشخص الاكتئاب نهائيًا",
                "يرفع الذكاء",
                "يمنع الخرف",
                "معتمد سريريًا لكل الفئات",
                "راجعها طبيب",
                "معاقين",
            ):
                self.assertNotIn(forbidden, combined)


if __name__ == "__main__":
    unittest.main()
