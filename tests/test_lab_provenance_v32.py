import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "attach_lab_provenance_v32.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


provenance = load_module("attach_lab_provenance_v32", SCRIPT)


def page(definition: dict, kind: str) -> str:
    payload = json.dumps(definition, ensure_ascii=False, separators=(",", ":"))
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>{definition['title']}</title><script type="application/json" id="lab-definition">{payload}</script></head><body><main><h1>{definition['title']}</h1><div data-v12-lab="{kind}"></div></main><footer>نهاية الصفحة</footer></body></html>'''


class LaboratoryProvenanceV32Tests(unittest.TestCase):
    def make_site(self, temporary: str) -> Path:
        site = Path(temporary) / "_site"
        contract, official, methods = provenance.load_contracts(ROOT)

        official_slugs = {
            "phq9": "phq-9-plus",
            "gad7": "gad-7-plus",
            "who5": "who-5-plus",
            "audit_guided": "audit-10-guided",
        }
        for score_type, slug in official_slugs.items():
            definition = {
                "slug": slug,
                "title": official["profiles"][score_type]["title_ar"],
                "score_type": score_type,
                "questions": ["بند تجريبي"],
                "options": ["0", "1"],
            }
            target = site / "assessment-lab" / slug / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(page(definition, "assessment"), encoding="utf-8")

        monitor_slugs = []
        for group in contract["monitor_source_groups"].values():
            monitor_slugs.extend(group["slugs"])
        self.assertEqual(len(monitor_slugs), 36)
        self.assertEqual(len(set(monitor_slugs)), 36)
        for slug in monitor_slugs:
            definition = {
                "slug": slug,
                "title": slug,
                "score_type": "monitor",
                "monitor_policy": "burden_tracking",
                "questions": ["محور: بند سلوكي محدد"],
                "options": ["0", "1"],
            }
            target = site / "assessment-lab" / slug / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(page(definition, "assessment"), encoding="utf-8")

        categories = list(contract["cognitive_category_sources"])
        task_slugs = list(methods["task_methods"])
        self.assertEqual(len(task_slugs), 53)
        for index, slug in enumerate(task_slugs):
            definition = {
                "slug": slug,
                "title": slug,
                "mode": slug.replace("-", "_"),
                "category": categories[index % len(categories)],
                "stages": 5,
                "trials_per_stage": 6,
            }
            target = site / "cognitive-lab" / slug / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(page(definition, "cognitive"), encoding="utf-8")
        return site

    def test_attaches_explicit_provenance_to_all_93_pages(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = self.make_site(temporary)
            first = provenance.attach_provenance(site, ROOT)
            self.assertEqual(first["status"], "passed")
            self.assertEqual(first["totalPages"], 93)
            self.assertEqual(first["assessmentPages"], 40)
            self.assertEqual(first["cognitivePages"], 53)
            self.assertEqual(first["officialInstrumentPages"], 4)
            self.assertEqual(first["originalMonitorPages"], 36)
            self.assertEqual(first["siteSpecificCognitivePages"], 53)
            self.assertEqual(first["classificationCounts"], {
                "official_instrument": 4,
                "original_monitor": 36,
                "site_cognitive_task": 53,
            })
            self.assertGreaterEqual(first["totalSources"], 20)
            self.assertEqual(first["referencedSources"], first["totalSources"])
            self.assertEqual(first["unusedSourceIds"], [])
            self.assertEqual(first["missingSourceIds"], [])
            self.assertEqual(first["duplicateMonitorSlugs"], [])
            self.assertEqual(first["pagesMissingProvenance"], [])
            self.assertEqual(first["pageErrors"], [])
            self.assertEqual(first["sourceErrors"], [])
            self.assertEqual(first["brokenSourceUrls"], [])
            self.assertEqual(first["writtenFailures"], [])
            self.assertEqual(first["changedPages"], 93)

            snapshots = {
                path: path.read_text(encoding="utf-8")
                for path in site.glob("*-lab/*/index.html")
            }
            second = provenance.attach_provenance(site, ROOT)
            self.assertEqual(second["status"], "passed")
            self.assertEqual(second["changedPages"], 0)
            self.assertEqual(
                snapshots,
                {
                    path: path.read_text(encoding="utf-8")
                    for path in site.glob("*-lab/*/index.html")
                },
            )

    def test_visible_blocks_distinguish_source_from_validation(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = self.make_site(temporary)
            provenance.attach_provenance(site, ROOT)
            samples = {
                "assessment-lab/phq-9-plus/index.html": [
                    "نسخة عربية رقمية تثقيفية",
                    "لا يثبت وحده تكافؤ هذه الصياغة",
                    "المصدرية وحالة القياس",
                ],
                "assessment-lab/relationship-safety/index.html": [
                    "أداة متابعة أصلية غير معيارية",
                    "غير متحققة سيكومتريًا",
                    "لا ينتج من مؤشر الموقع حكم قانوني",
                ],
                "cognitive-lab/simple-reaction/index.html": [
                    "مهمة معرفية تجريبية خاصة بالموقع",
                    "لا توجد معايير عمرية",
                    "مولد المحاولات والتدرج",
                ],
            }
            for relative, markers in samples.items():
                source = (site / relative).read_text(encoding="utf-8")
                self.assertEqual(source.count(provenance.MARK_START), 1)
                self.assertEqual(source.count(provenance.MARK_END), 1)
                definition = provenance.load_definition(source)
                self.assertEqual(definition["provenance_version"], 32)
                self.assertTrue(definition["provenance_source_ids"])
                self.assertTrue(definition["provenance_source_urls"])
                self.assertTrue(definition["provenance_validation_status"])
                for marker in markers:
                    self.assertIn(marker, source)

    def test_rejects_untrusted_or_non_https_source(self):
        valid = {
            "title_ar": "مصدر",
            "publisher": "جهة",
            "url": "http://example.com/source",
            "supports_ar": "يسند تعريفًا",
            "does_not_support_ar": "لا يسند التحقق",
            "kind": "test",
        }
        errors = provenance.validate_source("bad", valid)
        self.assertTrue(any("invalid https URL" in error for error in errors))
        valid["url"] = "https://example.com/source"
        errors = provenance.validate_source("bad", valid)
        self.assertTrue(any("host not allowlisted" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
