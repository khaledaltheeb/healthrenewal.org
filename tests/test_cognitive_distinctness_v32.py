import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "harden_cognitive_distinctness_v32.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


patcher = load_module("cognitive_distinctness_v32", SCRIPT)


def page(slug: str) -> str:
    definition = {
        "slug": slug,
        "title": slug,
        "mode": slug.replace("-", "_"),
        "stages": 5,
        "trials_per_stage": 10,
    }
    payload = json.dumps(definition, ensure_ascii=False, separators=(",", ":"))
    return (
        '<!doctype html><html lang="ar" dir="rtl"><head>'
        f'<script type="application/json" id="lab-definition">{payload}</script>'
        f'</head><body><h1>{slug}</h1></body></html>'
    )


RUNTIME_FIXTURE = r"""(()=>{'use strict';
function seeded(seed){return()=>0.5}
function shuffle(items,rnd){return [...items]}
function v202Val(x){return String(typeof x==='object'?x.value:x)}
function v202Opt(x){return x}
function v202Finish(d,stage,rnd,data){let answer=String(data.answer),options=[...new Map((data.options||[]).map(x=>[v202Val(x),x])).values()];const fallback=['أ','ب','ج','د'];for(const item of fallback){if(options.length>=4)break;if(String(item)!==answer&&!options.some(x=>v202Val(x)===String(item)))options.push(v202Opt(item))}options=shuffle(options,rnd);const values=options.map(v202Val);if(values.length<2)throw new Error(`Insufficient choices after repair: ${d.slug}`);return{...data,answer,options,difficulty:stage+1}}
function makeTrial(d,stage,index,sessionSeed=0){const rnd=seeded(sessionSeed),ri=(a,b)=>a,pick=a=>a[0],symbols=['●','▲','■','◆','★','⬟'],arrows=['↑','→','↓','←'];const gradedV212=null;return v202Finish(d,stage,rnd,{prompt:'قديم',answer:'أ',options:['أ','ب'],explanation:'قديم'})}
})();"""


class CognitiveDistinctnessV32Tests(unittest.TestCase):
    def make_site(self, temporary: str) -> Path:
        site = Path(temporary) / "_site"
        runtime = site / "assets/js/lab-v12.js"
        runtime.parent.mkdir(parents=True)
        runtime.write_text(RUNTIME_FIXTURE, encoding="utf-8")
        for slug in patcher.DEFINITION_UPDATES:
            target = site / "cognitive-lab" / slug / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(page(slug), encoding="utf-8")
        return site

    def test_patch_covers_all_specialized_routes_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = self.make_site(temporary)
            first = patcher.patch_runtime(site)
            self.assertEqual(first["status"], "passed")
            self.assertEqual(first["specialized_mode_count"], 12)
            self.assertEqual(first["missing_pages"], [])
            self.assertEqual(len(first["updated_pages"]), 12)
            text = (site / "assets/js/lab-v12.js").read_text(encoding="utf-8")
            for marker in (
                "singleResponse:true",
                "choiceReactionMapping:'arrow-direction'",
                "visualReactionTargetSize:targetSize",
                "sustainedTarget:target",
                "visualSearchSetSize:size",
                "guidedSemanticRetrieval:true",
                "switchTrial",
                "spanLength:length",
                "uniqueStudyTokens:new Set(sequence).size",
            ):
                self.assertIn(marker, text)
            snapshots = {
                path: path.read_text(encoding="utf-8")
                for path in site.rglob("index.html")
            }
            second = patcher.patch_runtime(site)
            self.assertEqual(second["status"], "passed")
            self.assertEqual(second["updated_pages"], [])
            self.assertEqual(text, (site / "assets/js/lab-v12.js").read_text(encoding="utf-8"))
            self.assertEqual(
                snapshots,
                {path: path.read_text(encoding="utf-8") for path in site.rglob("index.html")},
            )

    def test_definitions_disclose_actual_task_not_standardized_test(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = self.make_site(temporary)
            patcher.patch_runtime(site)
            for slug, expected in {
                "simple-reaction": "أحادية الزر",
                "choice-reaction": "أربعة اتجاهات",
                "visual-reaction": "موضع إشارة",
                "semantic-fluency": "موجّه متعدد الخيارات",
                "attention-switch": "تبديل قاعدة",
                "digit-span-forward": "بعد إخفاء العرض",
            }.items():
                source = (site / "cognitive-lab" / slug / "index.html").read_text(
                    encoding="utf-8"
                )
                definition = patcher.load_definition(source)
                self.assertEqual(definition["distinctness_version"], 32)
                self.assertIn(expected, definition["instrument_type"])
            semantic = patcher.load_definition(
                (
                    site / "cognitive-lab/semantic-fluency/index.html"
                ).read_text(encoding="utf-8")
            )
            self.assertIn("ليست هذه الصيغة اختبار طلاقة لفظية", semantic["summary"])


if __name__ == "__main__":
    unittest.main()
