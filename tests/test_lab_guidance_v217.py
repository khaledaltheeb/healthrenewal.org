from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "expand_lab_guidance_v217.py"
BANNED = re.compile(r"(?<!\w)(?:المعاقين|معاقين|المعاقون|معاقون|المعاقة|معاقة|المعاق|معاق)(?!\w)")


class LabGuidanceV217Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="lab-v217-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))
        (self.site / "api").mkdir(parents=True)
        self.tools = [
            {
                "kind": "assessment", "slug": "anxiety-daily", "title": "متابعة القلق اليومية",
                "category": "القلق", "mode": "", "path": "assessment-lab/anxiety-daily/index.html",
                "questions": 12, "score_type": "monitor",
            },
            {
                "kind": "cognitive", "slug": "attention-switch", "title": "تحويل الانتباه",
                "category": "المرونة الانتباهية", "mode": "attention_switch",
                "path": "cognitive-lab/attention-switch/index.html", "stages": 5,
                "trials_per_stage": 10, "total_trials": 50,
            },
        ]
        inventory = {"assessment_count": 1, "cognitive_count": 1, "tools": self.tools}
        (self.site / "api" / "all-labs-v22.json").write_text(json.dumps(inventory, ensure_ascii=False), encoding="utf-8")
        for tool in self.tools:
            page = self.site / tool["path"]
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text(
                f'<!doctype html><html lang="ar" dir="rtl"><head><title>{tool["title"]}</title></head>'
                f'<body><main><h1>{tool["title"]}</h1><div class="lab"></div></main></body></html>',
                encoding="utf-8",
            )

    def run_publisher(self) -> dict[str, object]:
        result = subprocess.run(["python3", str(SCRIPT), str(self.site)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return json.loads((self.site / "api" / "lab-guidance-v217.json").read_text(encoding="utf-8"))

    def test_depth_sources_safety_and_idempotence(self) -> None:
        first = self.run_publisher()
        second = self.run_publisher()
        self.assertEqual((first["assessment_pages"], first["cognitive_pages"]), (1, 1))
        self.assertEqual(first["pages_changed"], 2)
        self.assertEqual(second["pages_changed"], 0)
        self.assertGreaterEqual(first["minimum_added_words"], 430)
        for tool in self.tools:
            text = (self.site / tool["path"]).read_text(encoding="utf-8")
            self.assertEqual(text.count("lab-guidance-v217:start"), 1)
            self.assertEqual(text.count("lab-guidance-v217:end"), 1)
            self.assertEqual(text.count('id="lab-guidance-v217-style"'), 1)
            self.assertIn("pubmed.ncbi.nlm.nih.gov", text)
            self.assertIn("www.cochrane.org/evidence", text)
            self.assertIsNone(BANNED.search(text))
        assessment = (self.site / self.tools[0]["path"]).read_text(encoding="utf-8")
        cognitive = (self.site / self.tools[1]["path"]).read_text(encoding="utf-8")
        self.assertIn("متى نطلب مساعدة متخصصة؟", assessment)
        self.assertIn("هذه متابعة محلية غير معيارية", assessment)
        self.assertIn("الاستخدام المسؤول وإمكانية الوصول", cognitive)
        self.assertIn("ليست اختبار ذكاء أو أداة تشخيص", cognitive)


if __name__ == "__main__":
    unittest.main()
