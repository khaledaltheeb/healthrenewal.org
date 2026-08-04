from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "materialize_sectors_v10_v1.py"
SPEC = importlib.util.spec_from_file_location("materialize_sectors_v10_v1", SCRIPT_PATH)
assert SPEC and SPEC.loader
publisher = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = publisher
SPEC.loader.exec_module(publisher)


def source_payload(index: int) -> dict[str, object]:
    return {
        "key": f"guide-{index:02d}",
        "title": f"دليل اختباري متكامل رقم {index}",
        "subtitle": "محتوى عربي اختباري يوضح الغرض والحدود والخطوات العملية المبنية على مصادر موثوقة.",
        "reviewed_at": "2026-08-04",
        "sources": [
            {"name": "World Health Organization", "url": f"https://www.who.int/example-{index}"},
            {"name": "UNICEF", "url": f"https://www.unicef.org/example-{index}"},
        ],
        "articles": [
            {
                "slug": f"topic-{index}-a",
                "title": "فهم الموضوع والسياق",
                "summary": "هذا ملخص عربي اختباري طويل بما يكفي لتوضيح الفكرة والسياق والحدود بصورة عملية وآمنة.",
                "signals": ["علامة أولى", "علامة ثانية", "علامة ثالثة"],
                "steps": ["خطوة أولى", "خطوة ثانية", "خطوة ثالثة", "خطوة رابعة"],
                "phrases": ["صياغة عملية أولى", "صياغة عملية ثانية"],
                "avoid": "تجنب التعميم والتشخيص الذاتي والوعود غير الواقعية.",
            },
            {
                "slug": f"topic-{index}-b",
                "title": "خطة تطبيق عملية",
                "summary": "هذا ملخص عربي اختباري ثان يشرح التنفيذ والمتابعة والتقييم الحذر دون تقديم قرار فردي.",
                "signals": ["موقف أول", "موقف ثان", "موقف ثالث"],
                "steps": ["إجراء أول", "إجراء ثان", "إجراء ثالث", "إجراء رابع"],
                "phrases": ["عبارة دعم أولى", "عبارة دعم ثانية"],
                "avoid": "تجنب الضغط والإكراه وتجاهل السلامة والسياق الفردي.",
            },
        ],
    }


class MaterializeSectorsV10Tests(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp())
        content = root / "content" / "sectors-v10"
        content.mkdir(parents=True)
        for index in range(20):
            (content / f"guide-{index:02d}.json").write_text(
                json.dumps(source_payload(index), ensure_ascii=False),
                encoding="utf-8",
            )
        for name in publisher.LEGACY_SOURCES:
            (content / name).write_text(json.dumps(source_payload(90), ensure_ascii=False), encoding="utf-8")
        for name in publisher.MANUAL_REVIEW_SOURCES:
            (content / name).write_text(json.dumps(source_payload(91), ensure_ascii=False), encoding="utf-8")
        return root

    def test_materializes_hub_pages_and_report(self) -> None:
        root = self.make_repo()
        report = publisher.write_publication(root)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["pageCount"], 20)
        self.assertEqual(report["hubCount"], 1)
        self.assertEqual(len(report["routes"]), 20)
        self.assertTrue((root / "evidence-guides" / "index.html").is_file())
        page = (root / "evidence-guides" / "guide-00" / "index.html").read_text(encoding="utf-8")
        self.assertIn("منصة روافد", page)
        self.assertIn('rel="canonical" href="https://healthrenewal.org/evidence-guides/guide-00/"', page)
        self.assertIn("حدود الاستخدام والسلامة", page)
        skipped_reasons = {entry["reason"] for entry in report["skipped"]}
        self.assertIn("legacy-already-published", skipped_reasons)
        self.assertIn("manual-publication-review-required", skipped_reasons)

    def test_check_mode_detects_drift_and_escapes_content(self) -> None:
        root = self.make_repo()
        payload_path = root / "content" / "sectors-v10" / "guide-00.json"
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        payload["title"] = "<script>alert(1)</script> عنوان آمن"
        payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        publisher.write_publication(root)
        page_path = root / "evidence-guides" / "guide-00" / "index.html"
        page = page_path.read_text(encoding="utf-8")
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        publisher.write_publication(root, check=True)
        page_path.write_text(page + "\n<!-- drift -->\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            publisher.write_publication(root, check=True)


if __name__ == "__main__":
    unittest.main()
