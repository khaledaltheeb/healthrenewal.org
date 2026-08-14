#!/usr/bin/env python3
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

MARKER = '<!-- research-evidence-editorial-v4 -->'
SECTION = Path('sections/research-evidence-learning')

INTENT_GOALS = {
    'basics': 'بناء تعريف عملي وحدود واضحة للمفهوم قبل الانتقال إلى التفاصيل',
    'read-paper': 'استخراج عناصر الدراسة من الورقة الأصلية وربط كل عنصر بما يغيّر التفسير',
    'critical-checklist': 'تحويل التقييم النقدي من قائمة شكلية إلى أسئلة تكشف العيوب القادرة على تغيير الاستنتاج',
    'interpret-results': 'فصل مقدار النتيجة عن عدم اليقين والقيود والسياق الذي يمكن تعميمها عليه',
    'common-errors': 'التعرّف على الأخطاء المتكررة قبل أن تتحول إلى استنتاجات أو قرارات مضللة',
    'compare': 'مقارنة البدائل وفق سؤال محدد ومعايير معلنة بدل المفاضلة الانطباعية',
    'advanced': 'تفكيك الافتراضات المنهجية المتقدمة واختبار حساسية الاستنتاج لها',
    'questions': 'صياغة أسئلة تحقق تكشف ما إذا كانت البيانات والتصميم يجيبان فعلًا عن السؤال المطروح',
    'practice': 'تحويل المعرفة النظرية إلى خطوات قابلة للتنفيذ والمراجعة في حالة تطبيقية',
    'researcher': 'اتخاذ قرارات تصميم وتحليل موثقة تقلل المرونة غير المبررة وتزيد قابلية التدقيق',
    'reporting': 'الإبلاغ عن القرارات والنتائج والقيود بما يسمح للقارئ بفهم ما فُعل وما لم يُفعل',
    'decision-making': 'ربط الدليل بالقرار مع إظهار البدائل وعدم اليقين والقيم والسياق',
    'school': 'ترجمة الدليل إلى سياق مدرسي دون تجاوز حدود الدراسة أو تجاهل اختلاف البيئة التعليمية',
    'family': 'شرح معنى الدليل للأسرة بلغة عملية دون تحويله إلى تشخيص أو وعد فردي',
    'healthcare': 'استخدام الدليل داخل سياق الرعاية مع مراعاة خط الأساس والمخاطر والتفضيلات والبدائل',
    'limitations': 'تحديد القيود التي تغيّر الثقة في النتيجة بدل سرد تحفظات عامة لا تؤثر في الحكم',
    'search-strategy': 'بناء بحث قابل للتكرار يوازن الحساسية والدقة ويوثق مصادر الاسترجاع والاستبعاد',
    'data-extraction': 'استخراج البيانات بطريقة تمنع الخلط بين ما أبلغته الدراسة وما استنتجه المراجع',
    'quality-assessment': 'تقييم المصداقية مجالًا بمجال وربط كل مشكلة بأثرها المحتمل على النتيجة',
    'synthesis': 'دمج الأدلة مع الحفاظ على الاختلافات المهمة بدل إخفائها داخل خلاصة واحدة',
    'analysis': 'اختيار التحليل وقراءة مخرجاته على ضوء التصميم والافتراضات ومصادر عدم اليقين',
    'bias': 'تحديد مسار التحيز واتجاهه المحتمل ومدى قدرته على تغيير التقدير',
    'design': 'مطابقة بنية الدراسة مع السؤال والزمن والمقارنة المطلوبة قبل تقييم النتائج',
    'quality': 'تحديد عناصر المصداقية التي تستحق وزنًا أكبر في الحكم النهائي',
    'example': 'اختبار المفهوم على حالة محددة مع فصل المعطيات عن الاستنتاج',
    'certainty': 'تمييز حجم الأثر عن مقدار الثقة في أن التقدير قريب من الحقيقة',
    'application': 'تحويل الاستنتاج إلى إجراء مشروط بالسياق مع تحديد ما قد يبطل النقل',
    'professional': 'استخدام الدليل ضمن مسؤولية مهنية واضحة وحدود اختصاص ومراجعة قابلة للتوثيق',
}


def detect_intent(slug: str) -> str:
    for key in sorted(INTENT_GOALS, key=len, reverse=True):
        if slug.endswith('-' + key):
            return key
    return slug.rsplit('-', 1)[-1]


def clean(text: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', text)).strip()


def enrich(path: Path) -> bool:
    source = path.read_text(encoding='utf-8')
    if MARKER in source:
        return False

    h1_match = re.search(r'<h1>(.*?)</h1>', source, re.S | re.I)
    canonical_match = re.search(r'<link rel="canonical" href="([^"]+)"', source, re.I)
    if not h1_match or not canonical_match:
        raise ValueError(f'missing h1/canonical: {path}')

    title = clean(h1_match.group(1))
    slug = path.parent.name
    intent = detect_intent(slug)
    goal = INTENT_GOALS.get(intent, 'فحص السؤال والافتراضات والنتيجة والقيود بطريقة قابلة للمراجعة')
    canonical = canonical_match.group(1)

    block = f'''{MARKER}<section class="editorial-differentiation" aria-labelledby="page-specific-purpose"><h2 id="page-specific-purpose">ما الذي يميّز هدف هذه الصفحة؟</h2><p>في مسار «{html.escape(title)}» لا يكفي تكرار تعريفات الموضوع العامة؛ الهدف المحدد هنا هو {html.escape(goal)}. لذلك يجب أن تنتهي القراءة بمخرج يمكن فحصه: سؤال أو حكم أو مقارنة أو إجراء موثّق يرتبط مباشرة بزاوية هذه الصفحة، لا بخلاصة عامة تصلح لأي صفحة أخرى.</p><p>اختبار الاكتمال لهذه الصفحة هو أن يستطيع القارئ شرح لماذا يقود المسار «{html.escape(slug)}» إلى قرار تحليلي مختلف عن المسارات المجاورة، ثم يحدد معلومة واحدة على الأقل لو تغيّرت لتغيّر معها النتيجة. المرجع الثابت لهذا المسار هو عنوانه القانوني {html.escape(canonical)}، ما يمنع الخلط بين النية التعليمية الحالية وصفحات الموضوع الأخرى.</p></section>'''

    anchor = '<section><h2>مصادر أساسية للتحقق والتوسع</h2>'
    if anchor not in source:
        raise ValueError(f'missing source anchor: {path}')
    source = source.replace(anchor, block + anchor, 1)
    path.write_text(source, encoding='utf-8')
    return True


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
    section = root / SECTION
    pages = sorted(section.glob('*/index.html'))
    if len(pages) < 500:
        raise SystemExit(f'expected at least 500 child pages, got {len(pages)}')
    changed = sum(1 for page in pages if enrich(page))
    print({'status': 'passed', 'pages': len(pages), 'diversified': changed, 'marker': MARKER})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
