import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_monitor_items_v32.py"
RUNTIME = ROOT / "scripts" / "harden_monitor_runtime_v32.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


publisher = load("publish_monitor_items_v32", PUBLISHER)
runtime_patch = load("harden_monitor_runtime_v32", RUNTIME)


def page(definition: dict) -> str:
    payload = json.dumps(definition, ensure_ascii=False, separators=(",", ":"))
    return (
        '<!doctype html><html lang="ar" dir="rtl"><head>'
        '<meta charset="utf-8"><title>'
        + definition["title"]
        + '</title><script type="application/json" id="lab-definition">'
        + payload
        + '</script></head><body><main><h1>'
        + definition["title"]
        + '</h1><div data-v12-lab="assessment"></div></main></body></html>'
    )


class MonitorItemsV32Tests(unittest.TestCase):
    def make_site(self, temporary: str) -> Path:
        site = Path(temporary) / "_site"
        profiles, _ = publisher.load_profiles(ROOT)
        for slug, profile in profiles.items():
            definition = {
                "slug": slug,
                "title": profile["title"],
                "category": "متابعة",
                "period": "الأسبوع الماضي",
                "score_type": "monitor",
                "questions": [
                    f"محور {index % 4}: كان هذا الجانب صعبًا أو أثر في يومي"
                    for index in range(12)
                ],
                "options": ["لا ينطبق", "قليلًا", "أحيانًا", "غالبًا", "بدرجة شديدة"],
            }
            target = site / "assessment-lab" / slug / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(page(definition), encoding="utf-8")
        return site

    def test_publishes_exact_unique_behavioral_bank_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = self.make_site(temporary)
            first = publisher.publish(site, ROOT)
            self.assertEqual(first["status"], "passed")
            self.assertEqual(first["shard_count"], 6)
            self.assertEqual(first["monitor_pages"], 36)
            self.assertEqual(first["profiles"], 36)
            self.assertEqual(first["total_items"], 432)
            self.assertEqual(first["unique_items"], 432)
            self.assertEqual(first["written_total_items"], 432)
            self.assertEqual(first["written_unique_items"], 432)
            self.assertEqual(first["generic_template_items"], 0)
            self.assertEqual(
                first["policies"],
                {"burden_tracking": 34, "readiness_gaps": 1, "safety_flags": 1},
            )
            self.assertEqual(len(first["critical_profiles"]), 7)
            self.assertEqual(first["changed_pages"], 36)
            snapshots = {
                path: path.read_text(encoding="utf-8")
                for path in site.glob("assessment-lab/*/index.html")
            }

            second = publisher.publish(site, ROOT)
            self.assertEqual(second["status"], "passed")
            self.assertEqual(second["changed_pages"], 0)
            self.assertEqual(
                snapshots,
                {
                    path: path.read_text(encoding="utf-8")
                    for path in site.glob("assessment-lab/*/index.html")
                },
            )

            relationship = publisher.load_definition(
                (site / "assessment-lab/relationship-safety/index.html").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(relationship["monitor_policy"], "safety_flags")
            self.assertEqual(
                relationship["critical_item_indices"], list(range(3, 12))
            )
            self.assertNotIn("كان هذا الجانب صعبًا", " ".join(relationship["questions"]))

            recovery = publisher.load_definition(
                (site / "assessment-lab/recovery-safety/index.html").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(recovery["monitor_policy"], "readiness_gaps")
            self.assertEqual(recovery["critical_item_indices"], [8, 9, 10, 11])

            postpartum = publisher.load_definition(
                (site / "assessment-lab/postpartum-support/index.html").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(postpartum["critical_item_indices"], [2, 5])
            self.assertIn("إيذاء نفسي أو الطفل", postpartum["questions"][2])

    def test_rejects_duplicate_or_generic_items(self):
        profiles, _ = publisher.load_profiles(ROOT)
        broken = json.loads(json.dumps(profiles["attention-daily"], ensure_ascii=False))
        broken["items"][1] = broken["items"][0]
        self.assertIn("duplicate items inside profile", publisher.validate_profile("x", broken))
        broken = json.loads(json.dumps(profiles["attention-daily"], ensure_ascii=False))
        broken["items"][0] = "الانتباه: كان هذا الجانب صعبًا أو أثر في يومي"
        errors = publisher.validate_profile("x", broken)
        self.assertIn("item 0 contains generic template", errors)

    def test_runtime_policy_patch_is_idempotent_and_preserves_phq_safety(self):
        fixture = r'''function showAssessmentResult(d,state,final=false){
 const box=q('.result-card');if(!box)return;
 const score=assessmentScore(d,state.answers),total=(d.questions||[]).length,complete=score.answered===total,partial=!complete;
 let heading='',primary='',interpretation='',range='',safety='';
 if(score.type==='phq9'||score.type==='gad7'){
 }else if(score.type==='who5'){
 }else if(score.type==='audit_guided'){
 }else{
  heading='مؤشر متابعة وصفي داخل هذه الأداة';primary=`<div class="result-score">${score.percent}%</div>`;
  interpretation=`الدرجة الخام ${score.raw} من ${score.max}. النسبة لتتبع نمطك أنت عبر ظروف متقاربة فقط؛ لا توجد نقاط قطع أو فئات خفيف/متوسط/شديد لهذه الأداة الأصلية غير المعيارية.`;
 }
 if(d.slug==='phq-9-plus'&&Number((state.answers||{})[8]||0)>0){
  safety='<aside class="lab-safety-alert" role="alert"><strong>تنبيه سلامة مستقل:</strong> أي إجابة أعلى من صفر في بند أفكار الموت أو إيذاء النفس تحتاج تواصلًا بشريًا مباشرًا وتقييمًا للسياق. إذا كان الخطر وشيكًا أو لا تستطيع ضمان سلامتك، تواصل فورًا مع شخص موثوق أو مختص أو خدمات الطوارئ المحلية، ولا تبق وحدك.</aside>';
 }
 box.innerHTML=safety;
}'''
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary) / "_site"
            js = site / "assets/js/lab-v12.js"
            js.parent.mkdir(parents=True)
            js.write_text(fixture, encoding="utf-8")
            first = runtime_patch.patch_runtime(site)
            self.assertEqual(first["status"], "passed")
            text = js.read_text(encoding="utf-8")
            for marker in (
                "d.monitor_policy==='safety_flags'",
                "d.monitor_policy==='readiness_gaps'",
                "لا تنتج هذه الأداة مجموع أمان",
                "لا تقيس شدة الاعتماد أو خطر الانسحاب",
                "إشارات تحتاج مراجعة مستقلة الآن",
                "بند أفكار الموت أو إيذاء النفس",
            ):
                self.assertIn(marker, text)
            second = runtime_patch.patch_runtime(site)
            self.assertEqual(second["status"], "passed")
            self.assertEqual(text, js.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
