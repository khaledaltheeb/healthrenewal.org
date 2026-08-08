import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENRICH = ROOT / "scripts" / "enrich_lab_content_v32.py"
HARDEN = ROOT / "scripts" / "harden_lab_runtime_v32.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


enrich = load("lab_depth_v32", ENRICH)
harden = load("lab_runtime_v32", HARDEN)


def page(definition: dict, kind: str) -> str:
    payload = json.dumps(definition, ensure_ascii=False).replace("</", "<\\/")
    title = definition["title"]
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{title}</title><meta name="description" content="وصف"><meta name="twitter:card" content="summary"><link rel="canonical" href="https://healthrenewal.org/{kind}-lab/{definition['slug']}/"><link rel="manifest" href="/manifest.webmanifest"><script type="application/json" id="lab-definition">{payload}</script></head><body><main><h1>{title}</h1><div data-v12-lab="{kind}"></div></main><footer>نهاية الصفحة</footer></body></html>'''


class Issue20V32Tests(unittest.TestCase):
    def build_fixture(self, site: Path) -> None:
        scales = [
            {"slug": "phq-9-plus", "title": "PHQ-9", "category": "مقياس موثق", "period": "الأسبوعان الماضيان", "score_type": "phq9", "questions": [f"بند {i}" for i in range(9)], "options": ["أبدًا", "عدة أيام", "أكثر من نصف الأيام", "تقريبًا كل يوم"]},
            {"slug": "gad-7-plus", "title": "GAD-7", "category": "مقياس موثق", "period": "الأسبوعان الماضيان", "score_type": "gad7", "questions": [f"بند {i}" for i in range(7)], "options": ["أبدًا", "عدة أيام", "أكثر من نصف الأيام", "تقريبًا كل يوم"]},
            {"slug": "who-5-plus", "title": "WHO-5", "category": "مقياس موثق", "period": "الأسبوعان الماضيان", "score_type": "who5", "questions": [f"بند {i}" for i in range(5)], "options": ["في أي وقت", "قليلًا", "أقل من نصف الوقت", "أكثر من نصف الوقت", "معظم الوقت", "طوال الوقت"]},
            {"slug": "audit-10-guided", "title": "AUDIT الإرشادي", "category": "فحص إرشادي", "period": "السنة الماضية", "score_type": "audit_guided", "questions": [f"بند {i}" for i in range(10)], "options": ["أبدًا", "نادرًا", "أحيانًا", "غالبًا", "بصورة شديدة"]},
        ]
        for index in range(36):
            domains = [f"المحور {index}-{n}" for n in range(4)]
            questions = [f"{domain}: كان هذا الجانب صعبًا أو أثر في يومي" for domain in domains]
            questions += [f"{domain}: احتجت إلى دعم إضافي" for domain in domains]
            questions += [f"{domain}: أريد متابعة تغير هذا الجانب" for domain in domains]
            scales.append({"slug": f"monitor-{index:02}", "title": f"متابعة {index}", "category": "المتابعة", "period": "الأسبوع الماضي", "score_type": "monitor", "questions": questions, "options": ["لا ينطبق", "قليلًا", "أحيانًا", "غالبًا", "بدرجة شديدة"]})
        for definition in scales:
            target = site / "assessment-lab" / definition["slug"] / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(page(definition, "assessment"), encoding="utf-8")

        for slug, method in enrich.TASK_METHODS.items():
            definition = {"slug": slug, "title": slug, "category": "الانتباه", "mode": "الانتباه", "summary": method, "stages": 5, "trials_per_stage": 6}
            target = site / "cognitive-lab" / slug / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(page(definition, "cognitive"), encoding="utf-8")

    def test_depth_profiles_scoring_boundaries_and_idempotence(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary) / "site"
            self.build_fixture(site)
            first = enrich.enrich(site)
            self.assertEqual(first["status"], "passed")
            self.assertEqual(first["assessment_pages"], 40)
            self.assertEqual(first["cognitive_pages"], 53)
            self.assertGreaterEqual(first["minimum_actual_words"], enrich.MIN_VISIBLE_WORDS)
            self.assertEqual(first["missing_task_profiles"], [])
            phq = (site / "assessment-lab/phq-9-plus/index.html").read_text(encoding="utf-8")
            self.assertIn("20–27", phq)
            self.assertIn("البند التاسع", phq)
            self.assertIn("التعطل الوظيفي", phq)
            gad = (site / "assessment-lab/gad-7-plus/index.html").read_text(encoding="utf-8")
            self.assertIn("15–21", gad)
            who = (site / "assessment-lab/who-5-plus/index.html").read_text(encoding="utf-8")
            self.assertIn("لم أشعر بذلك في أي وقت", who)
            self.assertIn("بضرب الخام في أربعة", who)
            audit = (site / "assessment-lab/audit-10-guided/index.html").read_text(encoding="utf-8")
            self.assertIn("لا تُحتسب في هذه الصفحة درجة AUDIT الرسمية", audit)
            monitor = (site / "assessment-lab/monitor-00/index.html").read_text(encoding="utf-8")
            self.assertIn("لا توجد فئات «خفيف» أو «متوسط» أو «شديد»", monitor)
            cognitive = (site / "cognitive-lab/three-back/index.html").read_text(encoding="utf-8")
            self.assertIn(enrich.TASK_METHODS["three-back"], cognitive)
            self.assertIn("70% من الدقة و30%", cognitive)
            snapshot = {path: path.read_text(encoding="utf-8") for path in site.rglob("index.html")}
            second = enrich.enrich(site)
            self.assertEqual(second["status"], "passed")
            self.assertEqual(snapshot, {path: path.read_text(encoding="utf-8") for path in site.rglob("index.html")})

    def test_runtime_patch_removes_generic_clinical_bands_and_hardens_state(self):
        fixture = """(()=>{'use strict';const q=()=>null,qa=()=>[],clamp=(v,a,b)=>v,load=()=>null,save=()=>{},clear=()=>{},button=()=>'';function resultBand(p){return['x','y']}function assessmentScore(d,a){return{}}function showAssessmentResult(d,s,f=false){}function assessmentEngine(h,d){}function seeded(seed){return()=>0}function cognitiveResult(d,state,final=false){return 1}function cognitiveEngine(host,d){} })();"""
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary) / "site"
            runtime = site / "assets/js/lab-v12.js"
            runtime.parent.mkdir(parents=True)
            runtime.write_text(fixture, encoding="utf-8")
            report = harden.patch_runtime(site)
            self.assertEqual(report["status"], "passed")
            text = runtime.read_text(encoding="utf-8")
            self.assertNotIn("function resultBand(p)", text)
            for marker in ["missingInStage", "لم تُحسب درجة AUDIT رسمية", "لا توجد نقاط قطع", "Number.isFinite(value)&&value>=0", "70% دقة و30% سرعة"]:
                self.assertIn(marker, text)
            again = harden.patch_runtime(site)
            self.assertEqual(again["status"], "passed")
            self.assertEqual(text, runtime.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
