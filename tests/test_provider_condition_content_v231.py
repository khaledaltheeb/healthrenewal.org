from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/enrich_provider_condition_pages_v231.py'
spec = importlib.util.spec_from_file_location('provider_condition_v231', SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)

SLUGS = tuple(module.PROFILE_BY_SLUG)


def fixture_js() -> str:
    objects = []
    for index, slug in enumerate(SLUGS, 1):
        title = f'الحالة التجريبية {index}'
        profile = module.PROFILE_BY_SLUG[slug]
        objects.append('''{
slug: %s,
title: %s,
summary: %s,
team: ["مختص أول", "مختص ثان", "الأسرة"],
primary: ["أداة أساسية أ", "أداة أساسية ب"],
supporting: ["أداة داعمة"],
external: ["فحص خارجي"],
focus: ["التواصل", "الاستقلال", "المشاركة"],
deliverables: ["ملف نقاط القوة", "خطة متابعة"],
alerts: ["لا تعتمد على أداة واحدة", "راع الإتاحة واللغة"]
}''' % (json.dumps(slug), json.dumps(title, ensure_ascii=False), json.dumps(f'ملخص {title} ضمن ملف {profile}.', ensure_ascii=False)))
    return '''"use strict";
window.PA_CONDITION_PATHWAYS = {
workflowStages: [
"تحديد سؤال الإحالة والهدف العملي من التقييم.",
"جمع التاريخ النمائي والطبي والتعليمي والبيئي من أكثر من مصدر.",
"اختيار حزمة متوازنة تغطي الوظيفة والمشاركة ولا تعتمد على مقياس واحد.",
"تطبيق الأدوات أو استيراد النتائج الرسمية وتوثيق النسخة واللغة والمنفذ والتكييفات.",
"دمج النتائج مع الملاحظة المباشرة والسياق والفرص المتاحة للشخص.",
"صياغة نقاط القوة والاحتياجات وخطة الدعم ومؤشرات المتابعة دون تشخيص آلي.",
"تحديد ما إذا كان المسار يغلق أو يحتاج أداة مكملة أو إحالة لفريق آخر."
],
conditions: [
%s
]
};''' % ',\n'.join(objects)


def page(title: str) -> str:
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>تقييم {title}</title><meta name="description" content="وصف قصير"><link rel="canonical" href="https://example.test/"></head><body><main><div id="condition-root" aria-busy="true"></div><noscript><h1>تقييم {title}</h1><p>نص قصير.</p></noscript></main><script src="../conditions-data-v1.js" defer></script><script src="../conditions-ui-v1.js" defer></script></body></html>'''


class ProviderConditionContentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.site = Path(self.tmp.name)
        conditions_dir = self.site / 'provider-assessment-demo/conditions'
        conditions_dir.mkdir(parents=True)
        (conditions_dir / 'conditions-data-v1.js').write_text(fixture_js(), encoding='utf-8')
        for index, slug in enumerate(SLUGS, 1):
            target = conditions_dir / slug / 'index.html'
            target.parent.mkdir(parents=True)
            target.write_text(page(f'الحالة التجريبية {index}'), encoding='utf-8')

    def tearDown(self) -> None:
        self.tmp.cleanup()


    def test_repository_contract_parses_all_twenty_conditions(self) -> None:
        source = ROOT / 'provider-assessment-demo/conditions/conditions-data-v1.js'
        conditions, stages = module.load_contract(source)
        self.assertEqual(len(conditions), 20)
        self.assertGreaterEqual(len(stages), 7)
        self.assertEqual({item['slug'] for item in conditions}, set(SLUGS))

    def test_parses_exact_contract_and_expands_all_pages(self) -> None:
        conditions, stages = module.load_contract(self.site / 'provider-assessment-demo/conditions/conditions-data-v1.js')
        self.assertEqual(len(conditions), 20)
        self.assertEqual(len(stages), 7)
        report = module.run(self.site)
        self.assertEqual(report['status'], 'passed')
        self.assertEqual(report['conditions'], 20)
        self.assertEqual(report['enriched_pages'], 20)
        self.assertEqual(report['remaining_below_minimum'], 0)
        self.assertGreaterEqual(report['minimum_after_words'], module.MIN_WORDS)
        self.assertEqual(report['duplicate_generated_blocks'], 0)

    def test_static_content_preserves_interactive_runtime_and_updates_description(self) -> None:
        module.run(self.site)
        path = self.site / 'provider-assessment-demo/conditions/autism/index.html'
        text = path.read_text(encoding='utf-8')
        self.assertIn('id="condition-root"', text)
        self.assertIn('conditions-ui-v1.js', text)
        self.assertIn(module.START, text)
        self.assertEqual(text.count(module.MARKER), 1)
        self.assertEqual(text.count('data-provider-condition-depth-v231-style'), 1)
        self.assertIn('سؤال الإحالة', text)
        self.assertIn('حقوق الاستخدام', text)
        self.assertIn('التكييفات المعقولة', text)
        self.assertIn('provider-condition-content-v231', (self.site / 'api/provider-condition-content-v231.json').as_posix())
        self.assertIn('دليل مؤسسي موسع', text)
        self.assertGreaterEqual(module.visible_words(text), module.MIN_WORDS)

    def test_rich_page_still_receives_the_required_depth_contract(self) -> None:
        path = self.site / 'provider-assessment-demo/conditions/global-developmental-delay/index.html'
        rich_source = path.read_text(encoding='utf-8').replace(
            '</main>',
            '<section data-existing-specialist-content><h2>محتوى تخصصي قائم</h2><p>'
            + ' '.join(['معلومة موثقة'] * 950)
            + '</p></section></main>',
            1,
        )
        path.write_text(rich_source, encoding='utf-8')
        self.assertGreaterEqual(module.visible_words(rich_source), module.MIN_WORDS)

        report = module.run(self.site)
        text = path.read_text(encoding='utf-8')

        self.assertEqual(report['status'], 'passed')
        self.assertIn('data-existing-specialist-content', text)
        self.assertEqual(text.count(module.START), 1)
        self.assertEqual(text.count(module.MARKER), 1)
        self.assertEqual(text.count('data-provider-condition-depth-v231-style'), 1)
        self.assertIn('id="condition-root"', text)
        self.assertIn('conditions-ui-v1.js', text)

    def test_is_idempotent(self) -> None:
        module.run(self.site)
        path = self.site / 'provider-assessment-demo/conditions/aac/index.html'
        first = path.read_text(encoding='utf-8')
        second_report = module.run(self.site)
        second = path.read_text(encoding='utf-8')
        self.assertEqual(first, second)
        self.assertEqual(second_report['already_enriched_pages'], 20)
        self.assertEqual(second.count(module.START), 1)

    def test_missing_page_blocks_release(self) -> None:
        (self.site / 'provider-assessment-demo/conditions/autism/index.html').unlink()
        report = module.run(self.site)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['missing_or_failed'], 1)

    def test_profile_sources_and_rights_language_exist(self) -> None:
        module.run(self.site)
        for slug in SLUGS:
            text = (self.site / 'provider-assessment-demo/conditions' / slug / 'index.html').read_text(encoding='utf-8')
            self.assertIn('testingstandards.net', text)
            self.assertIn('who.int', text)
            self.assertIn('لا تشخّص الحالة', text)
            self.assertNotIn('شفاء مضمون', text)
            self.assertNotIn('بديل عن الطبيب', text)


if __name__ == '__main__':
    unittest.main()
