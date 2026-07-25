from __future__ import annotations

import html
from typing import Iterable

import enrich_lab_content_v193_core_v235 as legacy

VERSION = 235
SOURCE_MARKER = "data-lab-source-v235"
CONTRACT = legacy.load_contract()


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _without_legacy_markers(fragment: str) -> str:
    for marker in (legacy.HEAD_START, legacy.HEAD_END, legacy.BODY_START, legacy.BODY_END):
        fragment = fragment.replace(marker, "")
    return fragment


def rich_description(definition: dict, kind: str) -> str:
    return legacy.rich_description(definition, kind)


def head_fragment(definition: dict, kind: str) -> str:
    fragment = _without_legacy_markers(legacy.head_fragment(definition, kind, CONTRACT))
    fragment = fragment.replace(
        '<meta name="twitter:title"',
        '<meta data-lab-source-v235-head="twitter-title" name="twitter:title"',
        1,
    )
    fragment = fragment.replace(
        '<meta name="twitter:description"',
        '<meta data-lab-source-v235-head="twitter-description" name="twitter:description"',
        1,
    )
    fragment = fragment.replace(
        '<script type="application/ld+json">',
        '<script data-lab-source-v235-head="schema" type="application/ld+json">',
    )
    return fragment


def _focus(definition: dict) -> list[str]:
    values = legacy.unique_focus(definition)
    if values:
        return values
    category = str(definition.get("category") or definition.get("mode") or "الأداء")
    return [category, "السياق", "الأثر اليومي", "المتابعة"]


def _list(items: Iterable[str]) -> str:
    return "".join(f"<li>{esc(item)}</li>" for item in items)


def _assessment_extension(definition: dict) -> str:
    title = str(definition.get("title", "الأداة"))
    period = str(definition.get("period", "الفترة المحددة"))
    category = str(definition.get("category", "المتابعة"))
    focus = _focus(definition)
    focus_items = []
    for domain in focus:
        focus_items.append(
            f"في محور {domain}: اكتب مثالًا واقعيًا واحدًا، وحدد متى ظهر، وما الذي سبقه، "
            "وكيف أثر في الدراسة أو العمل أو العلاقات أو العناية بالنفس، وما الدعم الذي خفف الأثر."
        )
    decision_limits = [
        "لا تثبت الدرجة سبب الأعراض، ولا تميز وحدها بين أثر الضغط والنوم والمرض الجسدي والدواء أو اختلاف فهم السؤال.",
        "لا تسمح الصفحة بتأكيد اضطراب أو استبعاده، ولا بتحديد خطة علاج أو تغيير دواء أو تقرير أهلية تعليمية أو وظيفية.",
        "لا تقارن نتيجتك بنتيجة شخص آخر ما لم تكن الأداة الأصلية مطبقة بالشروط نفسها وعلى فئة معيارية مناسبة.",
        "لا تحول التسجيل المتكرر إلى بحث قهري عن الطمأنة؛ التكرار المفيد يتبع الفترة المحددة ويخدم سؤال متابعة واضحًا.",
    ]
    follow_up = [
        f"ثبّت سؤال المتابعة: ما الذي تريد فهمه من {title} خلال {period}؟",
        "سجل تاريخ التطبيق والوقت والظروف المهمة، مثل النوم أو الألم أو حدث ضاغط أو تغيير دوائي.",
        "اكتب مثالين من الحياة اليومية يوضحان الشدة أو التعطيل، بدل الاكتفاء بالرقم أو الوصف العام.",
        "اختر خطوة دعم صغيرة قابلة للتنفيذ، وحدد من سيساعد ومتى تبدأ وكيف ستقيس التغير.",
        "راجع الاتجاه بعد المدة المناسبة، واحتفظ بما تغير وما بقي ثابتًا وما يحتاج سؤالًا مهنيًا.",
        "عند استمرار الضيق أو تدهور الوظيفة أو وجود خطر على السلامة، انتقل إلى دعم بشري مؤهل دون انتظار تسجيل إضافي.",
    ]
    return f'''
<section class="lab-source-v235__card"><h2>حدد القرار قبل استخدام {esc(title)}</h2>
<p>ابدأ بتحديد الغرض بدقة: هل تريد وصف نمط، متابعة تغير، تجهيز أمثلة لموعد مهني، أم معرفة ما يحتاج إلى دعم عملي؟ اختلاف الغرض يغير طريقة القراءة. في فئة {esc(category)} لا ينبغي أن يصبح الرقم هدفًا مستقلًا؛ القيمة الحقيقية هي ربط الإجابات بالزمن والسياق والأثر الوظيفي، ثم تحديد معلومة ناقصة أو خطوة متابعة قابلة للمراجعة.</p>
<p>دوّن مسبقًا القرار الذي قد يتغير بعد القراءة، ومن يملك اتخاذه، وما المعلومات الأخرى اللازمة. القرارات العالية الأثر تحتاج تاريخًا صحيًا وسياقًا أسريًا أو تعليميًا وفحصًا مناسبًا، ولا تعتمد على صفحة ذاتية واحدة.</p></section>
<section class="lab-source-v235__card"><h2>مصفوفة المحاور والسياق</h2><p>استخدم المحاور الآتية لبناء سجل قابل للفهم بدل إجابات منفصلة:</p><ul>{_list(focus_items)}</ul>
<p>وجود مثال مضاد مهم أيضًا: متى كان المحور أفضل؟ وما البيئة أو الشخص أو الروتين الذي ساعد؟ هذه المقارنة تكشف الموارد والتكييفات الممكنة، وتمنع تفسير الصعوبة بوصفها صفة ثابتة في الشخص.</p></section>
<section class="lab-source-v235__card"><h2>قراءة التغير عبر الزمن</h2>
<p>التسجيل الواحد لقطة محدودة. عند المتابعة، حافظ قدر الإمكان على الفترة والتعليمات والوقت والبيئة وطريقة الإدخال. قارن الاتجاه لا الرقم المنفرد: هل تحركت عدة محاور في الاتجاه نفسه؟ هل تغير الأداء اليومي؟ هل سبق التغير حدث معروف؟ وهل استمر بعد زواله؟</p>
<p>فرّق بين تغير حقيقي وتقلب متوقع وخطأ قياس أو اختلاف في فهم العبارة. إذا تعارضت النتيجة مع ملاحظات الحياة اليومية، لا تلغ أحد المصدرين؛ حوّل التعارض إلى سؤال يحتاج معلومات إضافية أو تقييمًا أوسع.</p></section>
<section class="lab-source-v235__card"><h2>استنتاجات لا تدعمها الصفحة</h2><ul>{_list(decision_limits)}</ul>
<p>يمكن استخدام النتيجة كبداية حوار أو سجل منظم، بشرط التصريح بعدم اليقين وحماية الخصوصية وحق الشخص في فهم ما يسجل عنه والاعتراض عليه.</p></section>
<section class="lab-source-v235__card"><h2>خطة توثيق ومتابعة</h2><ol>{_list(follow_up)}</ol>
<p>المتابعة الجيدة تنتهي بخطوة ومسؤول وموعد مراجعة، لا بملصق أو حكم نهائي. شارك أقل قدر لازم من البيانات، واحذف الأسماء والتفاصيل الحساسة عندما لا تكون ضرورية للغرض.</p></section>'''


def _cognitive_extension(definition: dict) -> str:
    title = str(definition.get("title", "المهمة"))
    category = str(definition.get("category") or definition.get("mode") or "القدرات المعرفية")
    category_text = CONTRACT["cognitive_categories"].get(
        category,
        f"تعرض المهمة نشاطًا رقميًا محدودًا في {category} ولا تمثل تقييمًا معياريًا شاملًا.",
    )
    conditions = [
        "استخدم الجهاز نفسه وحجم الشاشة نفسه وطريقة الإدخال نفسها عند مقارنة أكثر من جلسة.",
        "سجل النوم والتعب والألم والضوضاء والقلق والمشتتات، لأنها قد تغير السرعة والدقة بصورة ملحوظة.",
        "نفذ تجربة قصيرة لفهم القاعدة، ثم ميز بين محاولات التعلم والمحاولات التي تريد مقارنتها.",
        "توقف عند الصداع أو الدوار أو الإجهاد البصري أو الحسي؛ الاستمرار تحت الإجهاد لا يعطي مقارنة مفيدة.",
        "لا تقارن النتائج بين أشخاص يستخدمون أجهزة أو لغات أو خبرات مختلفة، ولا تحول الترتيب إلى حكم على القدرة العامة.",
    ]
    reading = [
        "السرعة وحدها: قد تعكس تعجلًا أو جهازًا أسرع، لذلك لا تقرأها دون الدقة ونوع الخطأ.",
        "الدقة وحدها: قد ترتفع مع التباطؤ الشديد؛ راجع التوازن بين الفهم والسرعة والاستمرار.",
        "الأخطاء: صنفها إلى سوء فهم للقاعدة، نقرات عارضة، فقدان تركيز، أو استراتيجية غير مناسبة.",
        "التغير بين المراحل: افحص أثر صعوبة المهمة والتعلم والتعب، بدل افتراض تحسن أو تدهور في القدرة.",
        "التكرار: قد ينتج تحسنًا خاصًا بالمهمة؛ انتقال الفائدة إلى الدراسة والعمل والحياة اليومية يحتاج دليلًا منفصلًا.",
    ]
    limits = [
        "لا تنتج المهمة درجة ذكاء، ولا تشخص اضطرابًا معرفيًا أو عصبيًا، ولا تحدد سبب النسيان أو بطء الأداء.",
        "لا تصلح النتيجة منفردة لقرار دراسي أو وظيفي أو طبي أو قانوني أو لتقدير أهلية شخص لخدمة.",
        "لا يثبت الأداء المرتفع غياب صعوبة يومية، كما لا يثبت الأداء المنخفض وجود مرض أو عجز ثابت.",
        "لا تستخدم التحسن داخل اللعبة كدليل على علاج اضطراب أو الوقاية من الخرف أو انتقال التدريب إلى كل القدرات.",
    ]
    log = [
        f"اسم المهمة: {title}، والمجال المعلن: {category}.",
        "الجهاز والمتصفح وطريقة الإدخال وحجم الشاشة.",
        "الوقت والنوم والتعب والأدوية أو الألم والمشتتات.",
        "المرحلة والمحاولات الصحيحة ونوع الأخطاء وزمن الاستجابة عند توفره.",
        "ملاحظة عن فهم القاعدة والاستراتيجية المستخدمة وأي توقف أو تكييف.",
        "مثال من الحياة اليومية يوضح هل توجد صعوبة مستمرة خارج المهمة أم لا.",
    ]
    return f'''
<section class="lab-source-v235__card"><h2>النطاق المعرفي الفعلي</h2>
<p><strong>{esc(category_text)}</strong> لذلك يصف اسم {esc(title)} المهمة المعروضة فقط. الأداء المعرفي الواقعي أوسع، ويتداخل مع اللغة والحواس والتعليم والدافعية والصحة والمزاج والبيئة. لا يجوز اختزال هذه المنظومة في زمن استجابة أو عدد إجابات صحيحة داخل جلسة قصيرة.</p>
<p>حدد قبل البدء ما إذا كان الغرض تدريب فهم قاعدة، أو ملاحظة استراتيجية، أو مقارنة الشخص بنفسه في ظروف متقاربة. أي غرض آخر يحتاج أداة وتصميمًا ودليل صلاحية يناسب القرار المطلوب.</p></section>
<section class="lab-source-v235__card"><h2>توحيد ظروف الجلسة</h2><ul>{_list(conditions)}</ul>
<p>تسجيل الظروف ليس تفصيلًا إضافيًا؛ إنه شرط لفهم التغير. اختلاف الشاشة أو طريقة اللمس أو الضوضاء قد يصنع فرقًا أكبر من التغير الذي تحاول قياسه.</p></section>
<section class="lab-source-v235__card"><h2>قراءة السرعة والدقة والأخطاء</h2><ul>{_list(reading)}</ul>
<p>الأفضل وصف نمط الأداء: سريع مع أخطاء اندفاعية، بطيء ودقيق، متذبذب مع التعب، أو متحسن بعد فهم القاعدة. الوصف المنهجي أكثر فائدة من ترتيب إجمالي غير معياري.</p></section>
<section class="lab-source-v235__card"><h2>حدود التدريب والانتقال</h2>
<p>قد تتحسن النتيجة لأن الشخص حفظ القاعدة أو توقع المثيرات أو طور استراتيجية خاصة. هذا تعلم حقيقي داخل المهمة، لكنه لا يثبت تلقائيًا تحسن الذاكرة أو الانتباه أو التخطيط في مواقف أخرى. إثبات الانتقال يحتاج مقارنة مضبوطة ومقاييس مستقلة ومتابعة زمنية.</p>
<ul>{_list(limits)}</ul></section>
<section class="lab-source-v235__card"><h2>سجل مقارنة قابل للتفسير</h2><ol>{_list(log)}</ol>
<p>عند ظهور تغير جديد ومستمر في الذاكرة أو اللغة أو الانتباه أو القدرة على أداء المهام اليومية، اجمع أمثلة واقعية واطلب تقييمًا مهنيًا. التقييم الأوسع يراجع التاريخ الصحي والدواء والنوم والمزاج والسمع والبصر واللغة، وقد يستخدم أدوات معيارية لا توفرها هذه المهمة.</p></section>'''


def body_fragment(definition: dict, kind: str, prefix: str) -> str:
    if kind == "assessment":
        base = legacy.assessment_body(definition, CONTRACT, prefix)
        extension = _assessment_extension(definition)
    elif kind == "cognitive":
        base = legacy.cognitive_body(definition, CONTRACT, prefix)
        extension = _cognitive_extension(definition)
    else:
        raise ValueError(f"Unsupported lab kind: {kind}")

    base = _without_legacy_markers(base).strip()
    base = base.replace(
        '<section class="lab-depth-v193"',
        f'<section class="lab-depth-v193 lab-source-v235" {SOURCE_MARKER}="{esc(kind)}"',
        1,
    )
    head, separator, tail = base.rpartition("</section>")
    if not separator:
        raise ValueError("Source body is missing its outer closing section")
    return head + extension + separator + tail
