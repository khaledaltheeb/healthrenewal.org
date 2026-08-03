from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_content_targets_v201.py"


def page(title: str, canonical: str, words: int = 30, placeholder: str = "") -> str:
    body = " ".join(["محتوى"] * words)
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{title}</title><meta name="description" content="وصف عربي منظم وكامل يشرح الغرض والخطوات العملية والحدود المهنية بصورة واضحة ودقيقة للزائر."><link rel="canonical" href="{canonical}"><script type="application/ld+json">{{"@context":"https://schema.org","@type":"Article"}}</script></head><body><header>هيدر</header><main><h1>{title}</h1><p>{body}</p><p>{placeholder}</p><a href="/trust/">الثقة</a><a href="../">الرئيسية</a><a href="other/">مرتبط</a></main><footer>فوتر</footer></body></html>'''


class ContentTargetsV201Tests(unittest.TestCase):
    def make_fixture(self) -> tuple[Path, Path, Path]:
        root = Path(tempfile.mkdtemp(prefix="targets-v201-root-"))
        site = root / "_site"
        site.mkdir(parents=True)
        roadmap = root / "roadmap.json"
        roadmap.write_text(json.dumps({
            "version": 201,
            "status": "test",
            "platform_name": "منصة روافد",
            "quality_contract": {"forbid_placeholder_phrases": ["قيد الإعداد"]},
            "targets": {
                "practical_tips": {
                    "label": "النصائح",
                    "route": "tips",
                    "minimum_count": 2,
                    "minimum_visible_words": 20,
                    "current_confirmed_count": 1
                },
                "special_needs": {
                    "label": "ذوو الاحتياجات الخاصة",
                    "route": "special-needs",
                    "minimum_count": 3,
                    "minimum_visible_words": 20,
                    "current_confirmed_count": None
                }
            }
        }, ensure_ascii=False), encoding="utf-8")
        for route in ("tips", "special-needs"):
            (site / route).mkdir()
            (site / route / "index.html").write_text(page(route, f"https://example.test/{route}/"), encoding="utf-8")
        tip = site / "tips" / "one"
        tip.mkdir()
        (tip / "index.html").write_text(page("نصيحة فريدة", "https://example.test/tips/one/"), encoding="utf-8")
        special = site / "special-needs" / "one"
        special.mkdir()
        (special / "index.html").write_text(page("دليل دامج", "https://example.test/special-needs/one/"), encoding="utf-8")
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root, site, roadmap

    def run_audit(self, site: Path, roadmap: Path, fail: bool = False) -> subprocess.CompletedProcess[str]:
        command = ["python3", str(SCRIPT), str(site), "--roadmap", str(roadmap)]
        if fail:
            command.append("--fail-on-regressions")
        return subprocess.run(command, cwd=ROOT, capture_output=True, text=True)

    def test_reports_counts_and_target_gaps_without_counting_hubs(self) -> None:
        _, site, roadmap = self.make_fixture()
        completed = self.run_audit(site, roadmap)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads((site / "api/content-targets-v201.json").read_text(encoding="utf-8"))
        self.assertEqual(report["targets"]["practical_tips"]["published_count"], 1)
        self.assertEqual(report["targets"]["practical_tips"]["target_gap"], 1)
        self.assertEqual(report["targets"]["special_needs"]["published_count"], 1)
        self.assertEqual(report["targets"]["special_needs"]["target_gap"], 2)
        self.assertEqual(report["targets"]["practical_tips"]["missing_structure_count"], 0)
        self.assertEqual(report["status"], "passed")

    def test_fails_for_placeholder_or_missing_structure(self) -> None:
        _, site, roadmap = self.make_fixture()
        target = site / "special-needs/one/index.html"
        target.write_text(page("دليل دامج", "https://example.test/special-needs/one/", placeholder="قيد الإعداد"), encoding="utf-8")
        completed = self.run_audit(site, roadmap, fail=True)
        self.assertNotEqual(completed.returncode, 0)
        report = json.loads((site / "api/content-targets-v201.json").read_text(encoding="utf-8"))
        self.assertEqual(report["targets"]["special_needs"]["placeholder_page_count"], 1)
        self.assertEqual(report["status"], "regressions-detected")

    def test_fails_when_confirmed_baseline_regresses(self) -> None:
        _, site, roadmap = self.make_fixture()
        shutil.rmtree(site / "tips/one")
        completed = self.run_audit(site, roadmap, fail=True)
        self.assertNotEqual(completed.returncode, 0)
        report = json.loads((site / "api/content-targets-v201.json").read_text(encoding="utf-8"))
        self.assertTrue(any("below confirmed baseline" in item for item in report["regressions"]))


if __name__ == "__main__":
    unittest.main()
